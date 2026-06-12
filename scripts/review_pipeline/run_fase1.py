# scripts/review_pipeline/run_fase1.py | Atualizado em: 11-06-2026 12:30:00(GMT-04:00)
import os
import sys
import csv
import json
import yaml
import argparse
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Garante import do core
sys.path.insert(0, os.path.dirname(__file__))
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from core.lib_llm_router import LLMRouter
from core.prompt_engine import build_prompt
from core.terminal import (
    print_section_header, show_progress_bar, print_step,
    print_success, print_error, print_warning, setup_interrupt_handler,
    handle_error_menu,
)
from core.auditor import ReviewAuditor
from core.state_manager import StateManager
from scripts.generate_live_dashboard import build_dashboard as build_live_dashboard
from scripts.generate_progress import generate_dashboard as build_progress_dashboard


def load_config(config_path="criteria_config.yaml"):
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_prompt_config(screening_config: dict) -> dict:
    criteria = screening_config.get("criteria", {})
    inc_text = "\n".join([f"- {i}" for i in criteria.get("inclusion", [])])
    exc_text = "\n".join([f"- {e}" for e in criteria.get("exclusion", [])])

    rule_base = screening_config.get("decision_rule", "")
    rule = f"""CRITÉRIOS DE INCLUSÃO OBRIGATÓRIOS:
{inc_text}

CRITÉRIOS DE EXCLUSÃO IMEDIATA:
{exc_text}

REGRA LOGICA:
{rule_base}

DEVE RESPONDER APENAS JSON VÁLIDO.
"""
    return {
        "cot_questions": screening_config.get("cot_questions", []),
        "decision_rule": rule,
        "extraction_fields": [],
        "few_shot_examples": [],
    }


def parse_args():
    parser = argparse.ArgumentParser(description="Triagem da Fase 1")
    parser.add_argument("--config", default="./criteria_config.yaml")
    parser.add_argument("--overnight", action="store_true", help="Modo autônomo (não interativo). Pula erros.")
    parser.add_argument("--default-action", choices=["1", "2", "3"], default="2", help="Ação padrão em erro (1=Retry, 2=Skip, 3=Pause).")
    parser.add_argument("--retry", type=int, default=3, help="Retentativas automáticas por artigo.")
    parser.add_argument("--max", type=int, default=0, help="Limita o número de artigos para testar.")
    return parser.parse_args()


# ---------------------------------------------------------------------------
# P7 — Idempotência via Shards + I/O Cirúrgico
# ---------------------------------------------------------------------------

def load_processed_ids_from_shards(fase1_audit_dir: str) -> set:
    """Retorna o conjunto de audit_ids já processados lendo o diretório de shards da Fase 1.

    Esta é a fonte de verdade para idempotência — não o campo Status do CSV.
    O nome do arquivo shard é `{sanitized_audit_id}.json`, logo o stem do filename
    é o audit_id sanitizado. Usamos o mesmo algoritmo de sanitização do Auditor.
    """
    processed = set()
    if not os.path.exists(fase1_audit_dir):
        return processed
    for fname in os.listdir(fase1_audit_dir):
        if fname.endswith(".json"):
            processed.add(fname[:-5])  # remove .json
    return processed


def _sanitize_audit_id(raw_id: str) -> str:
    """Espelha a lógica de _sanitize_filename do ReviewAuditor para comparação correta."""
    safe = "".join([c if c.isalnum() else "_" for c in raw_id])
    return safe[:80]


def consolidate_csv(original_path: str, delta_path: str, fieldnames: list) -> None:
    """Mescla o CSV original com o delta de novos resultados em uma única passagem de escrita.

    Estratégia (O(N) total, não O(N²)):
    1. Lê o delta (somente artigos desta sessão).
    2. Lê o original linha a linha, substituindo as linhas que aparecem no delta.
    3. Grava o CSV final uma única vez.
    """
    delta_rows: dict = {}
    if os.path.exists(delta_path):
        with open(delta_path, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                key = row.get("DOI") or row.get("Title", "")
                delta_rows[key] = row

    if not os.path.exists(original_path):
        return

    merged_rows = []
    with open(original_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        original_fieldnames = list(reader.fieldnames or fieldnames)
        for row in reader:
            key = row.get("DOI") or row.get("Title", "")
            merged_rows.append(delta_rows.get(key, row))

    # Garante que as colunas do delta existam na lista final
    all_fields = original_fieldnames[:]
    for fn in fieldnames:
        if fn not in all_fields:
            all_fields.append(fn)

    with open(original_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=all_fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(merged_rows)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    args = parse_args()
    config = load_config(args.config)
    router = LLMRouter()

    data_storage = config.get("infrastructure", {}).get("data_storage", ".agent/data_storage")
    log_path = os.path.join(data_storage, "saida", "PRISMA_LOG_MASTER.csv")
    audit_base_dir = os.path.join(data_storage, "saida", "auditoria")
    fase1_audit_dir = os.path.join(audit_base_dir, "fase1_screening")
    auditor = ReviewAuditor(base_output_dir=audit_base_dir)
    def update_dashboards():
        build_live_dashboard()
        build_progress_dashboard()

    state_mgr = StateManager(on_event_callback=update_dashboards)

    if not os.path.exists(log_path):
        print(f"[ERRO] Log mestre não encontrado em {log_path}. Rode a Ingestão primeiro.")
        sys.exit(1)

    
    articles = []
    with open(log_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        for row in reader:
            articles.append(row)

    # Garantir que os campos de triagem existam na lista de colunas
    for extra_field in ["Reasoning", "CoT_Tags", "Evidence_Quote"]:
        if extra_field not in fieldnames:
            fieldnames.append(extra_field)

    prompt_config = build_prompt_config(config.get("screening_phase", {}))

    if args.max > 0:
        articles = articles[:args.max]

    total_to_process = len(articles)

    if total_to_process == 0:
        print("\nNenhum artigo encontrado no PRISMA_LOG_MASTER.")
        sys.exit(0)

    # --- P7: Idempotência via Shards ---
    # Fonte de verdade: arquivos JSON no diretório de auditoria, NÃO o campo Status do CSV.
    already_processed_ids = load_processed_ids_from_shards(fase1_audit_dir)

    state_mgr.set_active_state("fase1_screening", "Fase 1: Triagem LLM", total_to_process)

    # Contexto para o Ctrl+C handler
    context = {"idx": 0, "total": total_to_process, "current_article": ""}
    setup_interrupt_handler(router, get_context_fn=lambda: context)

    processed = 0
    inclusions = 0
    exclusions = 0

    # Arquivo delta: apenas novas linhas desta sessão (append seguro, O(1) por artigo)
    delta_csv_path = log_path + ".delta"

    print_section_header(f"TRIAGEM FASE 1 (SCREENING LLM) - {total_to_process} artigos carregados")

    try:
        for art in articles:
            title = art.get("Title", "")
            title_short = title[:60] + "..." if len(title) > 60 else title

            # Derivar o audit_id (mesmo algoritmo usado na gravação do shard)
            raw_audit_id = art.get("DOI", "").replace("/", "_") if art.get("DOI") else f"NO_DOI_{processed}"
            if not raw_audit_id:
                raw_audit_id = f"NO_DOI_{processed}"
            sanitized_id = _sanitize_audit_id(raw_audit_id)

            # Idempotência: pula se já existe shard para este artigo
            if sanitized_id in already_processed_ids:
                state_mgr.update_state(processed=1, skipped=1)
                processed += 1
                continue

            context["idx"] = processed + 1
            context["current_article"] = title

            state_mgr.update_state(current_task=f"Analisando: {title_short}")
            show_progress_bar(processed + 1, total_to_process, success=inclusions, skipped=0, erros=exclusions)
            print_step(title_short)

            prompt = build_prompt(article=art, prompt_config=prompt_config)

            retry_count = 0
            success = False

            while retry_count <= args.retry and not success:
                start_time = datetime.now()
                res_json, backend, model, tokens_dict = router.generate("screening", prompt, json_format=True)
                end_time = datetime.now()
                latency = (end_time - start_time).total_seconds()

                if res_json and isinstance(res_json, dict) and "error" not in res_json:
                    success = True
                    decision = res_json.get("final_decision", "").upper()
                    reasoning = res_json.get("reasoning", "")

                    # Extração avançada das CoT tags
                    cot_analysis = res_json.get("cot_analysis", {})
                    cot_tags = []

                    if isinstance(cot_analysis, list):
                        _cot_dict = {}
                        for item in cot_analysis:
                            if isinstance(item, dict):
                                _cot_dict.update(item)
                            elif isinstance(item, str) and ":" in item:
                                k, v = item.split(":", 1)
                                _cot_dict[k.strip()] = v.strip()
                        cot_analysis = _cot_dict

                    if isinstance(cot_analysis, dict):
                        for k, v in cot_analysis.items():
                            if isinstance(v, str):
                                if "yes" in v.lower() or "sim" in v.lower():
                                    cot_tags.append(f"[{k.upper()}: YES]")
                                elif "no" in v.lower() or "não" in v.lower() or "nao" in v.lower():
                                    cot_tags.append(f"[{k.upper()}: NO]")
                                else:
                                    cot_tags.append(f"[{k.upper()}: ?]")
                    cot_tags_str = " ".join(cot_tags)

                    evidence = res_json.get("evidence_quote", "")
                    is_inclusion = "INCLUIR" in decision or "INCLUDE" in decision

                    if is_inclusion:
                        art["Status"] = "Incluído (Fase 1)"
                        art["Exclusion_Reason"] = ""
                        art["PDF_status"] = "pending"
                        inclusions += 1
                        print_success(f"INCLUIR ({latency:.1f}s) {cot_tags_str}")
                    else:
                        art["Status"] = "Excluído (Fase 1)"
                        art["Exclusion_Reason"] = reasoning
                        art["PDF_status"] = "not_needed"
                        exclusions += 1
                        print_error(f"EXCLUIR ({latency:.1f}s) {cot_tags_str}")

                    art["Reasoning"] = reasoning
                    art["CoT_Tags"] = cot_tags_str
                    art["Evidence_Quote"] = evidence
                    processed += 1

                    # Montar shard de auditoria
                    audit_id = art.get("DOI", "").replace("/", "_") if art.get("DOI") else f"NO_DOI_{processed}"
                    if not audit_id:
                        audit_id = f"NO_DOI_{processed}"

                    audit_payload = {
                        "article_metadata": {
                            "title": title,
                            "authors": art.get("Authors", "N/A"),
                            "year": art.get("Year", "N/A"),
                            "journal": art.get("Journal", "N/A"),
                            "doi": art.get("DOI", "N/A"),
                        },
                        "inference_metrics": {
                            "backend": backend,
                            "model": model,
                            "latency_seconds": round(latency, 2),
                            "tokens_in": tokens_dict.get("prompt_eval_count", 0),
                            "tokens_out": tokens_dict.get("eval_count", 0),
                            "tokens_total": tokens_dict.get("prompt_eval_count", 0) + tokens_dict.get("eval_count", 0),
                        },
                        "model_reasoning": {
                            "cot_tags": cot_tags_str,
                            "raw_cot_analysis": cot_analysis,
                            "final_decision": decision,
                            "reasoning_summary": reasoning,
                        },
                        "prompt_used": prompt,
                        "raw_response": res_json,
                    }

                    # --- P4: Transacionalidade — shard + estado em bloco atômico ---
                    try:
                        auditor.save_inference_shard(phase=1, item_id=audit_id, payload=audit_payload)
                    finally:
                        # P3 — Semântica correta:
                        # `success=1`  → a máquina operou sem crash (sempre verdadeiro aqui)
                        # `excluded=1` → decisão científica de exclusão (não é uma "falha")
                        # `fails`      → reservado para crashes de API/timeout (tratado no else abaixo)
                        state_mgr.update_state(
                            processed=1,
                            success=1,
                            excluded=0 if is_inclusion else 1,
                        )

                    # --- P7: Append O(1) ao delta CSV desta sessão ---
                    delta_exists = os.path.exists(delta_csv_path)
                    with open(delta_csv_path, "a", newline="", encoding="utf-8") as f:
                        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
                        if not delta_exists:
                            writer.writeheader()
                        writer.writerow(art)

                else:
                    error_msg = (
                        res_json.get("error", "Erro desconhecido ou formato inválido")
                        if isinstance(res_json, dict)
                        else "Resposta não é JSON válido"
                    )
                    print_warning(f"ERRO na inferência ({error_msg})")

                    if args.overnight:
                        print_warning("Modo overnight: Pulando artigo.")
                        state_mgr.update_state(processed=1, fails=1)
                        break

                    action, timeout_reached = handle_error_menu(
                        title=title_short,
                        error=error_msg,
                        default_action=args.default_action,
                        timeout=30,
                        phase_label="Fase 1 - Screening",
                    )

                    if action == "1":
                        retry_count += 1
                        print_step(f"Retentativa {retry_count}/{args.retry}...")
                    elif action == "2":
                        print_warning("Pulando artigo por decisão do usuário.")
                        state_mgr.update_state(processed=1, fails=1)
                        break
                    elif action == "3":
                        print_error("Pausando execução por decisão do usuário.")
                        state_mgr.update_state(finish=True)
                        sys.exit(1)

    finally:
        # --- P7: Consolidação única do CSV — O(N) no final, não O(N²) durante o loop ---
        if os.path.exists(delta_csv_path):
            print("\n[Fase 1] Consolidando resultados no PRISMA_LOG_MASTER.csv...")
            consolidate_csv(log_path, delta_csv_path, fieldnames)
            os.remove(delta_csv_path)
            print("[Fase 1] Consolidação concluída.")

        auditor.generate_session_summary(
            session_id=f"sess_f1_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            stats={"Processados": processed, "Incluídos": inclusions, "Excluídos": exclusions},
            config_hash="N/A",
            model="LLMRouter",
            phase_label="Fase 1 - Screening",
        )
        state_mgr.update_state(finish=True)

    print_section_header(f"SUCESSO: {processed} processados (Incluídos: {inclusions} | Excluídos: {exclusions})")
    print("Iniciando geração do relatório estático (PROGRESS.html)...")
    import subprocess
    try:
        subprocess.run([sys.executable, "scripts/generate_progress.py"], check=True)
    except Exception as e:
        print(f"Erro ao gerar PROGRESS.html: {e}")


if __name__ == "__main__":
    main()
