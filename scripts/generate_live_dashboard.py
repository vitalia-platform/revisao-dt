# scripts/generate_live_dashboard.py | Atualizado em: 11-06-2026 12:30:00(GMT-04:00)
import os
import sys
import json
import time
import logging
import argparse
import datetime
import yaml
import re
from pathlib import Path
from collections import Counter

# Jinja2 — Template Engine real (P1)
from jinja2 import Environment, FileSystemLoader, select_autoescape

logging.basicConfig(level=logging.WARNING, format="[%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# Tenta adicionar o diretório raiz ao path para garantir import de scripts se chamado do auditor
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.review_pipeline.core.state_manager import StateManager
from scripts.review_pipeline.core.metrics_engine import MetricsEngine


# ---------------------------------------------------------------------------
# P6 — Carrega base_dir a partir do criteria_config.yaml
# ---------------------------------------------------------------------------
def _load_data_storage_path() -> str:
    """Lê o data_storage do criteria_config.yaml, com fallback para o padrão."""
    config_path = "criteria_config.yaml"
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f)
            return cfg.get("infrastructure", {}).get("data_storage", ".agent/data_storage")
        except Exception:
            logger.error("Falha ao ler criteria_config.yaml para data_storage", exc_info=True)
    return ".agent/data_storage"


def get_latest_phase(base_dir: str, audit_dir: str) -> tuple[str, str, dict]:
    """Lê o ACTIVE_STATE.json como fonte da verdade, ou faz fallback se não existir."""
    state_file = os.path.join(base_dir, "ACTIVE_STATE.json")
    if os.path.exists(state_file):
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
            return state.get("phase_dir", ""), state.get("phase_name", "Desconhecido"), state
        except Exception:
            logger.error("Falha ao ler ACTIVE_STATE.json", exc_info=True)

    phases = {
        "fase0_ingestion": "Ingestão API",
        "fase1_screening": "Fase 1: Triagem LLM",
        "fase2a_download": "Fase 2a: Download de PDFs",
        "fase2b_extraction": "Fase 2b: Extração Profunda",
    }

    latest_time = 0
    active_phase_dir = ""
    active_phase_name = "Aguardando Inicialização"

    for d_name, label in phases.items():
        d_path = os.path.join(audit_dir, d_name)
        if os.path.exists(d_path):
            try:
                files = [os.path.join(d_path, f) for f in os.listdir(d_path) if f.endswith(".json")]
                if files:
                    mod_time = max(os.path.getmtime(f) for f in files)
                    if mod_time > latest_time:
                        latest_time = mod_time
                        active_phase_dir = d_name
                        active_phase_name = label
            except Exception:
                logger.error("Erro ao escanear diretório de fase: %s", d_path, exc_info=True)

    return active_phase_dir, active_phase_name, {}


def read_recent_shards(audit_dir: str, phase_dir: str, limit: int = 10):
    d_path = os.path.join(audit_dir, phase_dir)
    if not os.path.exists(d_path):
        return []

    files = [os.path.join(d_path, f) for f in os.listdir(d_path) if f.endswith(".json")]
    files.sort(key=os.path.getmtime, reverse=True)

    shards = []
    for f in files[:limit]:
        try:
            with open(f, "r", encoding="utf-8") as jf:
                shards.append(json.load(jf))
        except Exception:
            logger.error("Falha ao ler shard de auditoria: %s", f, exc_info=True)
    return shards


def load_criteria_map():
    map_dict = {}
    config_path = "criteria_config.yaml"
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
                for q in config.get("screening_phase", {}).get("cot_questions", []):
                    map_dict[q["id"].upper()] = q["question"]
        except Exception:
            logger.error("Falha ao carregar mapa de critérios", exc_info=True)
    return map_dict


def build_events_html(shards, phase_dir):
    criteria_map = load_criteria_map()
    html = ""
    for s in shards[-20:][::-1]:
        meta = s.get("article_metadata", {})
        title = meta.get("title", meta.get("Title", "Sem Título"))
        authors = meta.get("authors", meta.get("Authors", "Sem Autores"))
        year = meta.get("year", meta.get("Year", "Ano Desc."))
        journal = meta.get("journal", meta.get("Journal", "Revista Desc."))

        status = s.get("status", s.get("model_reasoning", {}).get("final_decision", "N/A"))

        # Color coding
        bg_color = "bg-gray-100"
        tx_color = "text-gray-800"
        if "INCLU" in status.upper() or "SUCCESS" in status.upper() or "INGESTED" in status.upper():
            bg_color = "bg-green-100"
            tx_color = "text-green-800"
        elif "EXCLU" in status.upper():
            # Exclusão científica: amarelo/âmbar (não vermelho — não é uma falha de máquina)
            bg_color = "bg-amber-100"
            tx_color = "text-amber-800"
        elif "FAIL" in status.upper() or "ERROR" in status.upper():
            bg_color = "bg-red-100"
            tx_color = "text-red-800"

        details_html = ""
        footer_tags = ""

        if phase_dir == "fase1_screening":
            reasoning = s.get("model_reasoning", {}).get("reasoning_summary", s.get("model_reasoning", {}).get("reasoning", "Sem raciocínio."))
            cot_tags_raw = s.get("model_reasoning", {}).get("cot_tags", "")
            time_str = s.get("inference_metrics", {}).get("latency_seconds", "")

            # Parse CoT Tags into Criteria Text
            parsed_tags_html = ""
            if cot_tags_raw:
                tags_matches = re.findall(r"\[(Q\d+):\s*([^\]]+)\]", cot_tags_raw)
                for q_id, ans in tags_matches:
                    q_text = criteria_map.get(q_id.upper(), f"Critério {q_id}")
                    ans_color = "text-green-600" if ans.strip().upper() == "YES" else "text-red-600"
                    parsed_tags_html += f'<li class="text-xs text-gray-600 truncate"><span class="font-bold {ans_color}">[{ans.strip().upper()}]</span> {q_text}</li>'

            details_html = f'''
                <div class="mt-2 mb-2 p-2 bg-gray-50 rounded text-xs text-gray-700 italic border-l-2 border-indigo-300 max-h-24 overflow-y-auto">
                    "{reasoning}"
                </div>
                <ul class="mb-2 list-none space-y-1">
                    {parsed_tags_html}
                </ul>
            '''
            footer_tags = f"Latência: {time_str}s | Triagem Fase 1"

        elif phase_dir == "fase2a_download":
            details_html = f'<p class="text-xs text-gray-600 mt-1">{s.get("source", s.get("error", ""))}</p>'
        elif phase_dir == "fase0_ingestion":
            details_html = f'<p class="text-xs text-gray-600 mt-1">Ingestão via: {meta.get("source", "API")}</p>'
        elif phase_dir == "fase2b_extraction":
            parsed = s.get("parsed_data", {})
            study_design = parsed.get("study_design", parsed.get("Study_Design", "N/A"))
            details_html = f'''
                <ul class="mb-2 list-none space-y-1 mt-2">
                    <li class="text-xs text-gray-600 truncate"><span class="font-bold text-indigo-600">[Design]</span> {study_design}</li>
                    <li class="text-xs text-gray-600 truncate"><span class="font-bold text-indigo-600">[Extraído]</span> {s.get("model", "Local")}</li>
                </ul>
            '''
            footer_tags = "Extração Fase 2"

        html += f'''
        <div class="event-card bg-white p-4 rounded-lg border border-gray-200 shadow-sm flex flex-col gap-1">
            <div class="flex justify-between items-start">
                <div class="flex flex-col">
                    <span class="text-sm font-semibold text-gray-900 leading-snug">{title}</span>
                    <span class="text-xs text-gray-500 mt-0.5">({year})</span>
                </div>
                <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-bold {bg_color} {tx_color} ml-3 whitespace-nowrap mt-1 shadow-sm border border-current opacity-80">
                    {status}
                </span>
            </div>
            {details_html}
            <div class="text-[10px] text-gray-400 font-mono text-right mt-1 border-t border-gray-100 pt-1">{footer_tags}</div>
        </div>
        '''
    if not html:
        html = '<p class="text-sm text-gray-500 text-center py-4">Nenhum evento detectado ainda.</p>'
    return html


def build_phases_history_rows(phases_history_file: str) -> str:
    """Constrói as linhas HTML da tabela de histórico de fases. (P8 — placeholder órfão corrigido)"""
    history = {}
    if not os.path.exists(phases_history_file):
        return '<tr><td colspan="5" class="py-6 text-center text-sm text-gray-400">Nenhuma fase concluída ainda.</td></tr>'

    try:
        with open(phases_history_file, "r", encoding="utf-8") as f:
            history = json.load(f)
    except Exception:
        logger.error("Falha ao ler PHASES_HISTORY.json para o modal de histórico", exc_info=True)
        return '<tr><td colspan="5" class="py-6 text-center text-sm text-red-400">Erro ao carregar histórico.</td></tr>'

    rows_html = ""
    phase_display = {
        "fase0_ingestion": "Fase 0: Ingestão",
        "fase1_screening": "Fase 1: Triagem",
        "fase2_extraction": "Fase 2: Extração",
        "fase2a_download": "Fase 2a: Download",
        "fase2b_extraction": "Fase 2b: Extração",
        "fase3_synthesis": "Fase 3: Síntese",
    }
    
    # Sort history chronologically (by start_time_ts or parsed last_updated)
    def get_sort_key(item):
        _, data = item
        ts = data.get("start_time_ts")
        if ts: return ts
        try:
            return datetime.datetime.strptime(data.get("last_updated", "").split("(GMT")[0].strip(), "%d-%m-%Y %H:%M:%S").timestamp()
        except:
            return 0
            
    sorted_history = sorted(history.items(), key=get_sort_key, reverse=True)
    
    for phase_id, data in sorted_history:
        label = phase_display.get(phase_id, data.get("phase_name", phase_id))
        processed = data.get("total_processed", data.get("processed", 0))
        success = data.get("total_success", data.get("success", 0))
        fails = data.get("total_fails", data.get("fails", 0))
        last_updated = data.get("last_updated", "—")
        rows_html += f'''
        <tr class="border-b border-gray-100 hover:bg-gray-50">
            <td class="py-3 px-4 text-sm font-medium text-gray-800">{label}</td>
            <td class="py-3 px-4 text-sm text-gray-600">{processed}</td>
            <td class="py-3 px-4 text-sm text-green-600 font-medium">{success}</td>
            <td class="py-3 px-4 text-sm text-red-500">{fails}</td>
            <td class="py-3 px-4 text-sm text-gray-400 font-mono">{last_updated}</td>
        </tr>'''

    return rows_html if rows_html else '<tr><td colspan="5" class="py-6 text-center text-sm text-gray-400">Nenhuma fase concluída ainda.</td></tr>'


def build_dashboard():
    # P6 — base_dir lido do config, não hardcoded
    base_dir = _load_data_storage_path()
    audit_dir = os.path.join(base_dir, "saida", "auditoria")
    template_dir = "templates"
    template_name = "live_progress_template.html"
    output_path = os.path.join(base_dir, "LIVE_PROGRESS.html")

    if not os.path.exists(os.path.join(template_dir, template_name)):
        print(f"[ERRO] Template {template_dir}/{template_name} não encontrado.")
        return

    phase_dir, phase_name, _ = get_latest_phase(base_dir, audit_dir)
    shards = read_recent_shards(audit_dir, phase_dir, limit=20)
    events_html = build_events_html(shards, phase_dir)

    state_mgr = StateManager(base_dir=base_dir)
    active_state = state_mgr.get_active_state()

    eta_rel, avg_latency = MetricsEngine.calculate_eta(shards, active_state)

    total_target = active_state.get("total_target", 0)
    total_processed = active_state.get("total_processed", 0)
    total_success = active_state.get("total_success", 0)
    total_fails = active_state.get("total_fails", 0)
    # P3 — Novo contador semântico: exclusões científicas (não são falhas de máquina)
    total_excluded = active_state.get("total_excluded", 0)

    audit_stats = {
        "tokens_in": sum(s.get("inference_metrics", {}).get("tokens_in", 0) for s in shards),
        "tokens_out": sum(s.get("inference_metrics", {}).get("tokens_out", 0) for s in shards),
        "tokens_total": sum(s.get("inference_metrics", {}).get("tokens_total", 0) for s in shards),
        "models": Counter(s.get("inference_metrics", {}).get("model", "unknown") for s in shards),
    }

    # Rótulos semânticos dos cards
    success_label = "Sucessos"
    fail_label = "Erros de Máquina"
    if phase_dir == "fase1_screening":
        success_label = "Incluídos"

    # P2 — Target dinâmico: a View NÃO mascara mais o total_target.
    # O StateManager é a única fonte de verdade. A Fase 0 chama update_target() quando sabe o real.
    if total_target == 0:
        total_target = 1
    progress_pct = min(100, round((total_processed / total_target) * 100, 1))

    actual_success = total_success
    if phase_dir == "fase1_screening":
        actual_success = total_success - total_excluded if total_success >= total_excluded else total_success

    if (actual_success + total_excluded + total_fails) > 0:
        denom = actual_success + total_excluded + total_fails
        succ_pct = round((actual_success / denom) * 100, 1)
        fail_pct = round((total_fails / denom) * 100, 1)
        excl_pct = round((total_excluded / denom) * 100, 1)
    else:
        succ_pct = 0
        fail_pct = 0
        excl_pct = 0

    most_used_model = "N/A"
    if audit_stats["models"]:
        most_used_model = audit_stats["models"].most_common(1)[0][0]

    total_skipped = active_state.get("total_skipped", 0) if isinstance(active_state, dict) else 0

    metrics_html = f"""
    <div class="space-y-4">
        <div>
            <p class="text-xs text-gray-500 uppercase">Arquivos Processados</p>
            <p class="text-2xl font-bold text-indigo-600">{total_processed} <span class="text-sm font-normal text-gray-400">({total_skipped} pulados)</span></p>
            <p class="text-xs text-gray-400 mt-1">{total_excluded} excl. cient. · {total_fails} erros máq.</p>
        </div>
        <div class="grid grid-cols-2 gap-4">
            <div>
                <p class="text-xs text-gray-500 uppercase">Tokens Input</p>
                <p class="text-sm font-medium text-gray-900">{audit_stats['tokens_in']:,}</p>
            </div>
            <div>
                <p class="text-xs text-gray-500 uppercase">Tokens Output</p>
                <p class="text-sm font-medium text-gray-900">{audit_stats['tokens_out']:,}</p>
            </div>
        </div>
        <div class="pt-2 border-t border-gray-100">
            <p class="text-xs text-gray-500 uppercase">Modelo Predominante</p>
            <p class="text-sm font-semibold text-gray-800">{most_used_model}</p>
            <p class="text-xs text-gray-400 mt-1">Total Tokens: {audit_stats['tokens_total']:,}</p>
        </div>
    </div>
    """

    methodology_texts = {}
    spec_path = "revisao_pipeline.spec.md"
    if os.path.exists(spec_path):
        try:
            with open(spec_path, "r", encoding="utf-8") as f:
                content = f.read()
                matches = re.finditer(r"<!-- BEGIN (.*?) -->(.*?)<!-- END \1 -->", content, re.DOTALL)
                for m in matches:
                    tag = m.group(1).strip()
                    text = m.group(2).strip()
                    methodology_texts[tag] = text
        except Exception:
            logger.error("Falha ao ler revisao_pipeline.spec.md para metodologia", exc_info=True)

    node_index = 0
    if phase_dir == "fase1_screening":
        node_index = 1
    elif phase_dir in ("fase2a_download", "fase2b_extraction"):
        node_index = 3
    elif phase_dir == "fase3_synthesis":
        node_index = 4

    base_pct = node_index * 25.0
    intra_pct = (progress_pct / 100.0) * 25.0
    macro_width_pct = min(100.0, base_pct + intra_pct)
    macro_width_str = f"{macro_width_pct:.1f}%"

    macro_phase = node_index + 1

    st_active_bg = "bg-indigo-600"
    st_active_tx = "text-indigo-700"
    st_active_badge = "bg-indigo-100 !text-indigo-800 border-indigo-300 shadow"
    st_pending_bg = "bg-gray-300"
    st_pending_tx = "text-gray-400"
    st_pending_badge = ""

    current_timestamp = int(datetime.datetime.now().timestamp() * 1000)

    global_start_ts = active_state.get("start_time_ts", 0)
    
    # Always load history for duration calculation
    history = {}
    phases_history_file = os.path.join(base_dir, "PHASES_HISTORY.json")
    if os.path.exists(phases_history_file):
        try:
            with open(phases_history_file) as f:
                history = json.load(f)
        except Exception:
            logger.error("Falha ao ler histórico de fases", exc_info=True)
            
    if not global_start_ts:
        # Fallback to f0 start time if current phase doesn't have it
        f0 = history.get("fase0_ingestion")
        if f0:
            try:
                time_str = f0.get("last_updated", "").split("(GMT")[0].strip()
                global_start_ts = datetime.datetime.strptime(time_str, "%d-%m-%Y %H:%M:%S").timestamp()
            except Exception:
                pass

    # P8 — Injetar GLOBAL_START_TIME
    if global_start_ts:
        global_start_time_str = datetime.datetime.fromtimestamp(global_start_ts).strftime("%d/%m/%Y %H:%M")
    else:
        global_start_time_str = "—"

    # Calculate durations based on history and active state
    current_time_ts = datetime.datetime.now().timestamp()
    active_phase_id = active_state.get("phase_dir")

    def get_phase_duration_seconds(phase_key):
        if phase_key == active_phase_id:
            start_ts = active_state.get("start_time_ts", 0)
            if start_ts > 0:
                if active_state.get("status") == "FINISHED":
                    last_updated_str = active_state.get("last_updated", "")
                    try:
                        clean_str = last_updated_str.split("(GMT")[0].strip()
                        end_dt = datetime.datetime.strptime(clean_str, "%d-%m-%Y %H:%M:%S")
                        return end_dt.timestamp() - start_ts
                    except Exception:
                        pass
                return current_time_ts - start_ts
                
        hist = history.get(phase_key)
        if not hist or not hist.get("start_time_ts"):
            return -1
        last_updated_str = hist.get("last_updated", "")
        start_ts = hist.get("start_time_ts", 0)
        try:
            clean_str = last_updated_str.split("(GMT")[0].strip()
            end_dt = datetime.datetime.strptime(clean_str, "%d-%m-%Y %H:%M:%S")
            end_ts = end_dt.timestamp()
            if start_ts > 0:
                return end_ts - start_ts
        except Exception as e:
            logger.error(f"Erro ao calcular duração: {e}")
            pass
        return -1

    t_f0 = MetricsEngine.format_duration(get_phase_duration_seconds("fase0_ingestion"))
    t_f1 = MetricsEngine.format_duration(get_phase_duration_seconds("fase1_screening"))
    t_f1_5 = MetricsEngine.format_duration(get_phase_duration_seconds("fase1_5_auditoria"))
    
    sec_2a = get_phase_duration_seconds("fase2a_download")
    sec_2b = get_phase_duration_seconds("fase2b_extraction")
    if sec_2a < 0 and sec_2b < 0:
        sec_f2 = -1
    else:
        sec_f2 = max(0, sec_2a) + max(0, sec_2b)
    t_f2 = MetricsEngine.format_duration(sec_f2)
    
    t_f3 = MetricsEngine.format_duration(get_phase_duration_seconds("fase3_synthesis"))

    # P8 — Construir linhas do modal de histórico
    phases_history_rows_html = build_phases_history_rows(phases_history_file)

    # --- Jinja2 Environment ---
    jinja_env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape(["html"]),
    )
    template = jinja_env.get_template(template_name)

    context = {
        "TIMESTAMP_JS": current_timestamp,
        "LAST_UPDATED": datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "CURRENT_PHASE_NAME": phase_name,
        "LIVE_EVENTS": events_html,
        "PHASE_METRICS": metrics_html,
        "PHASES_HISTORY_ROWS": phases_history_rows_html,
        "TOTAL_PROCESSED": total_processed,
        "TOTAL_TARGET": total_target,
        "SUCCESS_LABEL": success_label,
        "TOTAL_SUCCESS": actual_success,
        "SUCCESS_PERCENT": succ_pct,
        "TOTAL_EXCLUDED": total_excluded,
        "EXCLUDED_PERCENT": excl_pct,
        "FAIL_LABEL": fail_label,
        "TOTAL_FAILS": total_fails,
        "FAIL_PERCENT": fail_pct,
        "PROGRESS_PERCENT": progress_pct,
        "ITEMS_PER_SECOND": round(avg_latency, 2) if avg_latency else 0,
        "MACRO_PHASE_WIDTH": macro_width_str,
        "MACRO_PHASE_1_5_BADGE": st_active_badge if macro_phase >= 2 else st_pending_badge,
        "MACRO_PHASE_1_5_COLOR": st_active_bg if macro_phase >= 2 else "bg-gray-200",
        "MACRO_PHASE_1_5_TEXT": st_active_tx if macro_phase >= 2 else st_pending_tx,
        "MACRO_PHASE_2_BADGE": st_active_badge if macro_phase >= 3 else st_pending_badge,
        "MACRO_PHASE_2_COLOR": st_active_bg if macro_phase >= 3 else "bg-gray-200",
        "MACRO_PHASE_2_TEXT": st_active_tx if macro_phase >= 3 else st_pending_tx,
        "MACRO_PHASE_3_BADGE": st_active_badge if macro_phase >= 4 else st_pending_badge,
        "MACRO_PHASE_3_COLOR": st_active_bg if macro_phase >= 4 else "bg-gray-200",
        "MACRO_PHASE_3_TEXT": st_active_tx if macro_phase >= 4 else st_pending_tx,
        "MACRO_PHASE_4_BADGE": st_active_badge if macro_phase >= 5 else st_pending_badge,
        "MACRO_PHASE_4_COLOR": st_active_bg if macro_phase >= 5 else "bg-gray-200",
        "MACRO_PHASE_4_TEXT": st_active_tx if macro_phase >= 5 else st_pending_tx,
        "CURRENT_TASK_TEXT": active_state.get("current_task", "Em andamento..."),
        "CURRENT_TASK_COLOR": "text-gray-500" if active_state.get("status") == "FINISHED" else "text-indigo-600",
        "CURRENT_TASK_PULSE": "" if active_state.get("status") == "FINISHED" else "animate-pulse",
        "METHODOLOGY_JSON": json.dumps(methodology_texts),
        "ETA_TIME": eta_rel,
        "GLOBAL_START_TS": int(global_start_ts),
        "GLOBAL_START_TIME": global_start_time_str,
        "T_DUR_F0": t_f0,
        "T_DUR_F1": t_f1,
        "T_DUR_F1_5": t_f1_5,
        "T_DUR_F2": t_f2,
        "T_DUR_F3": t_f3,
    }

    rendered = template.render(context)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(rendered)

    # Export state as JSON
    with open(os.path.join(base_dir, "LIVE_PROGRESS_STATE.json"), "w", encoding="utf-8") as f:
        json.dump({"update_time": current_timestamp}, f)

    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Dashboard Atualizado: {output_path}")
    print("Para visualizar, utilize 'python -m http.server 8000' na pasta de saída.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--watch", action="store_true", help="Mantém o script rodando e atualiza a cada 3 segundos.")
    args = parser.parse_args()

    if args.watch:
        print("Iniciando Live Dashboard Tracker (Atualização a cada 3s)...")
        print("Pressione Ctrl+C para sair.")
        try:
            while True:
                build_dashboard()
                time.sleep(3)
        except KeyboardInterrupt:
            print("\nTracker encerrado.")
    else:
        build_dashboard()


if __name__ == "__main__":
    main()
