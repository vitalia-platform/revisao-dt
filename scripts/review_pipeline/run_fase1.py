import os
import sys
import csv
import json
import yaml
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Garante import do core
sys.path.insert(0, os.path.dirname(__file__))
from core.lib_llm_router import LLMRouter
from core.prompt_engine import build_prompt
from core.terminal import RichDashboard, setup_interrupt_handler

def load_config(config_path="criteria_config.yaml"):
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def build_prompt_config(criteria: dict) -> dict:
    inc_text = "\n".join([f"- {i}" for i in criteria.get("inclusion", [])])
    exc_text = "\n".join([f"- {e}" for e in criteria.get("exclusion", [])])
    
    rule = f"""CRITÉRIOS DE INCLUSÃO OBRIGATÓRIOS:
{inc_text}

CRITÉRIOS DE EXCLUSÃO IMEDIATA:
{exc_text}

DEVE RESPONDER APENAS JSON VÁLIDO.
"""
    return {
        "cot_questions": [
            {"id": "q1", "question": "O artigo aborda metodologias de Design Thinking, Co-design ou similares?"},
            {"id": "q2", "question": "O artigo inclui intervenção de atividade física, esporte ou exercício ativo?"},
            {"id": "q3", "question": "O artigo está dentro do período temporal (2010-2026) e tem aderência aos critérios?"}
        ],
        "decision_rule": rule,
        "extraction_fields": [
            {"id": "main_topic", "description": "Tópico central em uma frase"},
            {"id": "methodology", "description": "Breve descrição do método mencionado"}
        ],
        "few_shot_examples": []
    }

import argparse

def parse_args():
    parser = argparse.ArgumentParser(description="Triagem da Fase 1")
    parser.add_argument("--config", default="./criteria_config.yaml")
    parser.add_argument("--overnight", action="store_true", help="Modo autônomo (não interativo). Pula erros.")
    parser.add_argument("--default-action", choices=["1", "2", "3"], default="2", help="Ação padrão em erro (1=Retry, 2=Skip, 3=Pause).")
    parser.add_argument("--retry", type=int, default=3, help="Retentativas automáticas por artigo.")
    parser.add_argument("--max", type=int, default=0, help="Limita o número de artigos para testar.")
    return parser.parse_args()

def main():
    args = parse_args()
    config = load_config(args.config)
    router = LLMRouter()
    
    log_path = ".agent/data_storage/saida/PRISMA_LOG_MASTER.csv"
    audit_dir = ".agent/data_storage/saida/audit"
    os.makedirs(audit_dir, exist_ok=True)
    
    if not os.path.exists(log_path):
        print(f"[ERRO] Log mestre não encontrado em {log_path}. Rode a Ingestão primeiro.")
        sys.exit(1)
        
    articles = []
    with open(log_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            articles.append(row)
            
    prompt_config = build_prompt_config(config.get("criteria", {}))
    
    # Filtrar pendentes
    pending_articles = [art for art in articles if "aguardando" in art.get("Status", "").lower() or art.get("Status", "").lower() == "pending"]
    if args.max > 0:
        pending_articles = pending_articles[:args.max]
    total_to_process = len(pending_articles)
    
    if total_to_process == 0:
        print("\nNenhum artigo pendente de triagem encontrado.")
        sys.exit(0)

    # Variável de contexto para o Ctrl+C
    context = {"idx": 0, "total": total_to_process, "current_article": ""}
    
    # Grava estado no handler de interrupção
    setup_interrupt_handler(router, get_context_fn=lambda: context)

    processed = 0
    inclusions = 0
    exclusions = 0

    with RichDashboard("Triagem Fase 1 (Screening LLM)", total=total_to_process) as dashboard:
        dashboard.add_log(f"[bold green]Iniciando triagem de {total_to_process} artigos...[/bold green]")
        
        for art in pending_articles:
            title = art.get('Title', '')
            title_short = title[:60] + "..." if len(title) > 60 else title
            
            context["idx"] = processed + 1
            context["current_article"] = title
            
            dashboard.add_log(f"[cyan]Analisando:[/cyan] {title_short}")
            
            prompt = build_prompt(
                article=art,
                prompt_config=prompt_config
            )
            
            retry_count = 0
            success = False
            
            while retry_count <= args.retry and not success:
                start_time = datetime.now()
                res_json, backend, model = router.generate("screening", prompt, json_format=True)
                end_time = datetime.now()
                latency = (end_time - start_time).total_seconds()
                
                if res_json and isinstance(res_json, dict) and "error" not in res_json:
                    success = True
                    decision = res_json.get("final_decision", "").upper()
                    reasoning = res_json.get("reasoning", "")
                    
                    if "INCLUIR" in decision or "INCLUDE" in decision:
                        art["Status"] = "Incluído (Fase 1)"
                        art["Exclusion_Reason"] = ""
                        art["PDF_status"] = "pending"
                        inclusions += 1
                        dashboard.increment_success(f"{backend}/{model}")
                        dashboard.add_log(f"  [green]➜ INCLUIR[/green] ({latency:.1f}s)")
                    else:
                        art["Status"] = "Excluído (Fase 1)"
                        art["Exclusion_Reason"] = reasoning
                        art["PDF_status"] = "not_needed"
                        exclusions += 1
                        dashboard.increment_fail(f"{backend}/{model}")
                        dashboard.add_log(f"  [red]➜ EXCLUIR[/red] ({latency:.1f}s)")
                        
                    processed += 1
                    
                    # DIRETRIZ DE AUDITORIA ESTRITA: Salvar PRISMA-S / trAIce
                    audit_id = art.get("DOI", "").replace("/", "_") if art.get("DOI") else f"NO_DOI_{processed}"
                    if not audit_id: audit_id = f"NO_DOI_{processed}"
                    
                    audit_payload = {
                        "timestamp": end_time.isoformat(),
                        "backend_used": backend,
                        "model_used": model,
                        "latency_seconds": latency,
                        "decision": decision,
                        "reasoning": reasoning,
                        "prompt_used": prompt,
                        "raw_response": res_json
                    }
                    
                    audit_file = os.path.join(audit_dir, f"audit_{audit_id}.json")
                    with open(audit_file, "w", encoding="utf-8") as af:
                        json.dump(audit_payload, af, ensure_ascii=False, indent=2)
                        
                    # Grava no CSV iterativamente (salva progresso a cada artigo)
                    with open(log_path, "w", newline="", encoding="utf-8") as f:
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        writer.writeheader()
                        writer.writerows(articles)
                else:
                    error_msg = res_json.get("error", "Erro desconhecido ou formato inválido") if isinstance(res_json, dict) else "Resposta não é JSON válido"
                    dashboard.add_log(f"  [yellow]⚠️ ERRO na inferência ({error_msg})[/yellow]")
                    
                    if args.overnight:
                        dashboard.add_log(f"  [dim]Modo overnight: Pulando artigo.[/dim]")
                        dashboard.increment_fail("Erros (Overnight)")
                        break
                        
                    # Pausa o dashboard temporariamente para mostrar o menu
                    dashboard.live.stop()
                    from core.terminal import handle_error_menu
                    action, timeout_reached = handle_error_menu(
                        title=title_short,
                        error=error_msg,
                        default_action=args.default_action,
                        timeout=30,
                        phase_label="Fase 1 - Screening"
                    )
                    dashboard.live.start()
                    
                    if action == "1":
                        retry_count += 1
                        dashboard.add_log(f"  [cyan]Retentativa {retry_count}/{args.retry}...[/cyan]")
                    elif action == "2":
                        dashboard.add_log(f"  [yellow]⚠️ Pulando artigo por decisão do usuário.[/yellow]")
                        dashboard.increment_fail("Erros (Skipped)")
                        break
                    elif action == "3":
                        dashboard.add_log(f"  [red]🛑 Pausando execução por decisão do usuário.[/red]")
                        sys.exit(1)
        
        dashboard.add_log(f"[bold green]✔ Triagem concluída! {processed} avaliados.[/bold green]")
        
    # Relatório Final simples ao sair do Dashboard
    print(f"\n[SUCESSO] Sessão finalizada. {processed} artigos processados.")
    print(f"Incluídos: {inclusions} | Excluídos: {exclusions}")
    print("Execute 'python scripts/generate_progress.py' para atualizar o HTML.")

if __name__ == "__main__":
    main()
