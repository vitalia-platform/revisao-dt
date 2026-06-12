import os
import sys
import csv
import json
import yaml
import re
from collections import Counter
from datetime import datetime
import webbrowser

# Add parent directory to path to allow importing from scripts module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from scripts.review_pipeline.core.config_manager import load_config
from jinja2 import Environment, FileSystemLoader, select_autoescape

def generate_dashboard():
    config = load_config()
    base_dir = config.get("data_storage_dir", ".agent/data_storage")
    log_path = os.path.join(base_dir, "saida", "PRISMA_LOG_MASTER.csv")
    template_path = "templates/progress_template.html"
    output_path = os.path.join(base_dir, "PROGRESS.html")
    audit_base = os.path.join(base_dir, "saida", "auditoria")
    
    if not os.path.exists(log_path):
        print(f"Log {log_path} não encontrado. Dashboard será gerado zerado.")
        # We don't return, we let it generate empty

    if not os.path.exists(template_path):
        print(f"Template {template_path} não encontrado.")
        return
        
    # Read criteria mapping
    criteria_map = {}
    if os.path.exists("criteria_config.yaml"):
        with open("criteria_config.yaml", "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
            for q in config.get("screening_phase", {}).get("cot_questions", []):
                criteria_map[q["id"].upper()] = q["question"]
                
    # Read methodology anchor texts
    methodology_texts = {}
    spec_path = "revisao_pipeline.spec.md"
    if os.path.exists(spec_path):
        with open(spec_path, "r", encoding="utf-8") as f:
            content = f.read()
            # Extract everything between <!-- BEGIN XYZ --> and <!-- END XYZ -->
            matches = re.finditer(r"<!-- BEGIN (.*?) -->(.*?)<!-- END \1 -->", content, re.DOTALL)
            for m in matches:
                tag = m.group(1).strip()
                text = m.group(2).strip()
                methodology_texts[tag] = text

    stats = {
        "total": 0,
        "pendentes_f1": 0,
        "incluidos_f1": 0,
        "excluidos_f1": 0,
        "needs_pdf": 0,
        "maquinas": Counter()
    }
    
    # Store article data for interactive modals
    articles_data = {
        "pendentes": [],
        "incluidos": [],
        "excluidos": [],
        "needs_pdf": []
    }

    # Pre-load live updates from phase 1 screening JSONs
    live_updates = {}
    audit_f1_dir = os.path.join(base_dir, "saida", "auditoria", "fase1_screening")
    if os.path.exists(audit_f1_dir):
        for root_dir, _, files in os.walk(audit_f1_dir):
            for fname in files:
                if fname.endswith(".json"):
                    with open(os.path.join(root_dir, fname), "r", encoding="utf-8") as af:
                        try:
                            data = json.load(af)
                            doi = data.get("article_metadata", {}).get("doi", "")
                            if doi:
                                decision = data.get("model_reasoning", {}).get("final_decision", "")
                                reason = data.get("model_reasoning", {}).get("reasoning_summary", "")
                                tags = data.get("model_reasoning", {}).get("cot_tags", "")
                                if decision:
                                    live_updates[doi] = {
                                        "status": "incluído" if decision.upper() == "INCLUIR" else "excluído",
                                        "reasoning": reason,
                                        "cot_tags": tags
                                    }
                        except Exception:
                            pass

    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                stats["total"] += 1
                doi = row.get("DOI", "")
            
                # Apply live overlay if available
                if doi in live_updates:
                    status = live_updates[doi]["status"]
                    cot_tags_raw = live_updates[doi]["cot_tags"]
                    row["Reasoning"] = live_updates[doi]["reasoning"]
                else:
                    status = row.get("Status", "").lower()
                    cot_tags_raw = row.get("CoT_Tags", "")
                    
                pdf_status = row.get("PDF_status", "").lower()
                machine = row.get("Machine_ID", "unknown")
                stats["maquinas"][machine] += 1
                
                # Parse CoT Tags into structured format
                parsed_tags = []
                tags_matches = re.findall(r"\[(Q\d+):\s*([^\]]+)\]", cot_tags_raw)
                for q_id, ans in tags_matches:
                    parsed_tags.append({
                        "id": q_id,
                        "text": criteria_map.get(q_id, f"Critério {q_id}"),
                        "answer": ans.strip().upper()
                    })
                
                art_info = {
                    "Title": row.get("Title", ""),
                    "Authors": row.get("Authors", ""),
                    "Year": row.get("Year", ""),
                    "Journal": row.get("Journal", ""),
                    "DOI": row.get("DOI", ""),
                    "Source": row.get("Source", ""),
                    "Reasoning": row.get("Reasoning", row.get("reasoning_summary", "")),
                    "CoT_Tags_Raw": cot_tags_raw,
                    "CoT_Tags_Parsed": parsed_tags,
                    "Evidence_Quote": row.get("Evidence_Quote", "")
                }
                
                if "aguardando triagem" in status or status == "pending":
                    stats["pendentes_f1"] += 1
                    articles_data["pendentes"].append(art_info)
                elif "incluído" in status or "incluido" in status:
                    stats["incluidos_f1"] += 1
                    articles_data["incluidos"].append(art_info)
                elif "excluído" in status or "excluido" in status:
                    stats["excluidos_f1"] += 1
                    articles_data["excluidos"].append(art_info)
                    
                if pdf_status == "needs_manual" or pdf_status == "pending":
                    if "incluído" in status or "incluido" in status:
                        stats["needs_pdf"] += 1
                        articles_data["needs_pdf"].append(art_info)

    # Calculate Audit Metrics (Lê todos os JSONs de todas as subpastas em auditoria)
    audit_stats = {
        "inferences": 0,
        "total_latency": 0,
        "models": Counter(),
        "tokens_in": 0,
        "tokens_out": 0,
        "tokens_total": 0
    }
    
    if os.path.exists(audit_base):
        for root_dir, _, files in os.walk(audit_base):
            for fname in files:
                if fname.endswith(".json"):
                    with open(os.path.join(root_dir, fname), "r", encoding="utf-8") as af:
                        try:
                            data = json.load(af)
                            metrics = data.get("inference_metrics", {})
                            if metrics:
                                audit_stats["inferences"] += 1
                                audit_stats["total_latency"] += metrics.get("latency_seconds", 0)
                                mod = metrics.get("model")
                                if mod and mod != "unknown":
                                    audit_stats["models"][mod] += 1
                                audit_stats["tokens_in"] += metrics.get("tokens_in", 0)
                                audit_stats["tokens_out"] += metrics.get("tokens_out", 0)
                                audit_stats["tokens_total"] += metrics.get("tokens_total", 0)
                        except:
                            pass
                        
    avg_latency = 0
    if audit_stats["inferences"] > 0:
        avg_latency = round(audit_stats["total_latency"] / audit_stats["inferences"], 2)
        
    most_used_model = "N/A"
    if audit_stats["models"]:
        most_used_model = audit_stats["models"].most_common(1)[0][0]

    # Render Jinja2 template
    template_dir = os.path.dirname(os.path.abspath(template_path))
    template_name = os.path.basename(template_path)
    
    jinja_env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True
    )
    template = jinja_env.get_template(template_name)
    
    json_payload = json.dumps(articles_data, ensure_ascii=False)
    methodology_json = json.dumps(methodology_texts, ensure_ascii=False)
    cost_usd = audit_stats["tokens_total"] * 0.000002

    def calc_percent(part, total):
        if total == 0: return 0
        return round((part / total) * 100, 1)

    tabela_maquinas = ""
    for mac, count in stats["maquinas"].most_common():
        tabela_maquinas += f"""
        <tr>
            <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{mac}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{count} artigos</td>
        </tr>
        """

    # Determine Macro Phase
    macro_phase = 1 # Ingestão concluída
    # 5-node logic (0 to 5)
    # 1: Ingestão, 2: Triagem, 3: Auditoria, 4: Extração, 5: Síntese
    macro_phase = 1 # Ingestão
    if stats["pendentes_f1"] > 0:
        macro_phase = 2 # Triagem
    # PROGRESS dashboard não tem granularidade fácil pra 1.5, então assumimos que se tem extração pendente passou pela auditoria
    elif stats["incluidos_f1"] > 0 and stats["needs_pdf"] > 0:
        macro_phase = 4 # Extração/Aquisição
    elif stats["incluidos_f1"] > 0 and stats["needs_pdf"] == 0:
        macro_phase = 5 # Síntese

    phase_widths = {1: "0%", 2: "24.1%", 3: "48.2%", 4: "72.3%", 5: "96.4%"}
    phase_labels = {1: "Fase 0: Ingestão", 2: "Fase 1: Triagem", 3: "Fase 1.5: Auditoria", 4: "Fase 2: Fichamento", 5: "Fase 3: Síntese"}
    
    # State mapping for template colors
    st_active_bg = "bg-indigo-600"
    st_active_tx = "text-indigo-700"
    st_active_badge = "bg-indigo-50 text-indigo-700 border-indigo-100"
    
    st_pending_bg = "bg-gray-200"
    st_pending_tx = "text-gray-400"
    st_pending_badge = "bg-gray-50 text-gray-500 border-gray-200"

    current_timestamp = int(datetime.now().timestamp() * 1000)

    # Ler estados para os tempos
    active_state = {}
    history = {}
    
    state_file = os.path.join(base_dir, "ACTIVE_STATE.json")
    if os.path.exists(state_file):
        try:
            with open(state_file, "r") as f:
                active_state = json.load(f)
        except Exception:
            pass

    history_file = os.path.join(base_dir, "PHASES_HISTORY.json")
    if os.path.exists(history_file):
        try:
            with open(history_file, "r") as f:
                history = json.load(f)
        except Exception:
            pass

    def format_dur(seconds):
        if seconds <= 0: return "00:00:00"
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    current_time_ts = datetime.now().timestamp()
    active_phase_id = active_state.get("phase_dir")
    global_start_ts = active_state.get("start_time_ts", 0)
    
    if not global_start_ts:
        f0 = history.get("fase0_ingestion")
        if f0:
            try:
                time_str = f0.get("last_updated", "").split("(GMT")[0].strip()
                global_start_ts = datetime.strptime(time_str, "%d-%m-%Y %H:%M:%S").timestamp()
            except Exception:
                pass

    if global_start_ts:
        global_start_time_str = datetime.fromtimestamp(global_start_ts).strftime("%d/%m/%Y %H:%M")
        # Global duration is from global_start_ts to either now (if active) or last history update
        if active_state.get("status") in ["RUNNING", "PAUSED", "IDLE"]:
            if active_state.get("status") == "IDLE" and not history:
                global_dur = "00:00:00"
            else:
                global_dur = format_dur(current_time_ts - global_start_ts)
        else:
            global_dur = format_dur(current_time_ts - global_start_ts) # default to now if we can't tell
    else:
        global_start_time_str = "--/--/---- --:--"
        global_dur = "00:00:00"

    def get_phase_duration_seconds(phase_key):
        if phase_key == active_phase_id:
            start_ts = active_state.get("start_time_ts", 0)
            if start_ts > 0:
                if active_state.get("status") == "FINISHED":
                    last_updated_str = active_state.get("last_updated", "")
                    try:
                        clean_str = last_updated_str.split("(GMT")[0].strip()
                        end_dt = datetime.strptime(clean_str, "%d-%m-%Y %H:%M:%S")
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
            end_dt = datetime.strptime(clean_str, "%d-%m-%Y %H:%M:%S")
            end_ts = end_dt.timestamp()
            if start_ts > 0:
                return end_ts - start_ts
        except Exception:
            pass
        return -1
        
    t_f0 = format_dur(get_phase_duration_seconds("fase0_ingestion"))
    t_f1 = format_dur(get_phase_duration_seconds("fase1_screening"))
    t_f1_5 = format_dur(get_phase_duration_seconds("fase1_5_auditoria"))
    
    sec_2a = get_phase_duration_seconds("fase2a_download")
    sec_2b = get_phase_duration_seconds("fase2b_extraction")
    if sec_2a < 0 and sec_2b < 0:
        t_f2 = "00:00:00"
    else:
        t_f2 = format_dur(max(0, sec_2a) + max(0, sec_2b))
        
    t_f3 = format_dur(get_phase_duration_seconds("fase3_synthesis"))

    context = {
        "TIMESTAMP_JS": current_timestamp,
        "DATA_ATUALIZACAO": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "MACRO_PHASE_WIDTH": phase_widths.get(macro_phase, "0%"),
        "MACRO_PHASE_LABEL": phase_labels.get(macro_phase, "Ingestão"),
        "MACRO_PHASE_2_COLOR": st_active_bg if macro_phase >= 2 else st_pending_bg,
        "MACRO_PHASE_2_TEXT": st_active_tx if macro_phase >= 2 else st_pending_tx,
        "MACRO_PHASE_2_BADGE": st_active_badge if macro_phase >= 2 else st_pending_badge,
        "MACRO_PHASE_1_5_COLOR": st_active_bg if macro_phase >= 3 else st_pending_bg,
        "MACRO_PHASE_1_5_TEXT": st_active_tx if macro_phase >= 3 else st_pending_tx,
        "MACRO_PHASE_1_5_BADGE": st_active_badge if macro_phase >= 3 else st_pending_badge,
        "MACRO_PHASE_3_COLOR": st_active_bg if macro_phase >= 4 else st_pending_bg,
        "MACRO_PHASE_3_TEXT": st_active_tx if macro_phase >= 4 else st_pending_tx,
        "MACRO_PHASE_3_BADGE": st_active_badge if macro_phase >= 4 else st_pending_badge,
        "MACRO_PHASE_4_COLOR": st_active_bg if macro_phase >= 5 else st_pending_bg,
        "MACRO_PHASE_4_TEXT": st_active_tx if macro_phase >= 5 else st_pending_tx,
        "MACRO_PHASE_4_BADGE": st_active_badge if macro_phase >= 5 else st_pending_badge,
        "ETA_TIME": "--:--:--",
        "GLOBAL_START_TIME": global_start_time_str,
        "GLOBAL_START_TS": int(global_start_ts * 1000) if global_start_ts else current_timestamp,
        "GLOBAL_DUR": global_dur,
        "T_DUR_F0": t_f0,
        "T_DUR_F1": t_f1,
        "T_DUR_F1_5": t_f1_5,
        "T_DUR_F2": t_f2,
        "T_DUR_F3": t_f3,
        "TOTAL_PENDENTES_F1": stats["pendentes_f1"],
        "TOTAL_INCLUIDOS_F1": stats["incluidos_f1"],
        "TOTAL_EXCLUIDOS_F1": stats["excluidos_f1"],
        "TOTAL_NEEDS_PDF": stats["needs_pdf"],
        "PERCENT_PENDENTES": calc_percent(stats["pendentes_f1"], stats["total"]),
        "PERCENT_INCLUIDOS": calc_percent(stats["incluidos_f1"], stats["total"]),
        "PERCENT_EXCLUIDOS": calc_percent(stats["excluidos_f1"], stats["total"]),
        "PERCENT_NEEDS_PDF": calc_percent(stats["needs_pdf"], stats["incluidos_f1"] if stats["incluidos_f1"] > 0 else 1),
        "AUDIT_INFERENCES": audit_stats["inferences"],
        "AUDIT_LATENCY": f"{avg_latency}s",
        "AUDIT_MODEL": most_used_model,
        "AUDIT_TOKENS_IN": audit_stats["tokens_in"],
        "AUDIT_TOKENS_OUT": audit_stats["tokens_out"],
        "AUDIT_TOKENS_TOTAL": audit_stats["tokens_total"],
        "AUDIT_COST": f"${cost_usd:.4f}",
        "TABELA_MAQUINAS": tabela_maquinas,
        "ARTICLES_JSON": json_payload,
        "METHODOLOGY_JSON": methodology_json
    }

    rendered = template.render(context)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(rendered)
        
    with open(os.path.join(base_dir, "PROGRESS_STATE.json"), "w", encoding="utf-8") as f:
        json.dump({"update_time": current_timestamp}, f)
        
    print(f"Dashboard gerado em {output_path}")
    print("Para visualizar, utilize 'python scripts/serve_dashboard.py'")

if __name__ == "__main__":
    generate_dashboard()


