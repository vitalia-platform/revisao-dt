import os
import sys
import csv
import json
from collections import Counter
from datetime import datetime
import webbrowser

def generate_dashboard(log_path=".agent/data_storage/saida/PRISMA_LOG_MASTER.csv", 
                      template_path="templates/progress_template.html", 
                      output_path=".agent/data_storage/PROGRESS.html"):
    
    if not os.path.exists(log_path):
        print(f"Log {log_path} não encontrado. Execute a ingestão primeiro.")
        return

    if not os.path.exists(template_path):
        print(f"Template {template_path} não encontrado.")
        return

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

    with open(log_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            stats["total"] += 1
            status = row.get("Status", "").lower()
            pdf_status = row.get("PDF_status", "").lower()
            machine = row.get("Machine_ID", "unknown")
            
            stats["maquinas"][machine] += 1
            
            art_info = {
                "Title": row.get("Title", ""),
                "Authors": row.get("Authors", ""),
                "Year": row.get("Year", ""),
                "Journal": row.get("Journal", ""),
                "DOI": row.get("DOI", ""),
                "Source": row.get("Source", ""),
                "Reasoning": row.get("Reasoning", ""),
                "CoT_Tags": row.get("CoT_Tags", "")
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

    # Calculate Audit Metrics
    audit_dir = ".agent/data_storage/saida/audit"
    audit_stats = {
        "inferences": 0,
        "total_latency": 0,
        "models": Counter(),
        "tokens_in": 0,
        "tokens_out": 0,
        "tokens_total": 0
    }
    
    if os.path.exists(audit_dir):
        for fname in os.listdir(audit_dir):
            if fname.endswith(".json"):
                with open(os.path.join(audit_dir, fname), "r", encoding="utf-8") as af:
                    try:
                        data = json.load(af)
                        audit_stats["inferences"] += 1
                        metrics = data.get("inference_metrics", {})
                        audit_stats["total_latency"] += metrics.get("latency_seconds", 0)
                        mod = metrics.get("model", "unknown")
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

    with open(template_path, "r", encoding="utf-8") as f:
        html = f.read()

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
    if stats["pendentes_f1"] > 0:
        macro_phase = 2 # Triagem
    elif stats["incluidos_f1"] > 0 and stats["needs_pdf"] > 0:
        macro_phase = 3 # Extração/Aquisição
    elif stats["incluidos_f1"] > 0 and stats["needs_pdf"] == 0:
        macro_phase = 4 # Síntese

    phase_widths = {1: "0%", 2: "33%", 3: "66%", 4: "100%"}
    phase_labels = {1: "Ingestão", 2: "Triagem Fase 1", 3: "Aquisição / Fichamento", 4: "Síntese DSR"}
    
    # State mapping for template colors
    st_active_bg = "bg-indigo-600"
    st_active_tx = "text-indigo-700"
    st_pending_bg = "bg-gray-300"
    st_pending_tx = "text-gray-400"
    
    html = html.replace("{{ PERCENT_PENDENTES }}", str(calc_percent(stats["pendentes_f1"], stats["total"])))
    html = html.replace("{{ PERCENT_NEEDS_PDF }}", str(calc_percent(stats["needs_pdf"], stats["incluidos_f1"] if stats["incluidos_f1"] > 0 else 1)))
    
    html = html.replace("{{ MACRO_PHASE_WIDTH }}", phase_widths[macro_phase])
    html = html.replace("{{ MACRO_PHASE_LABEL }}", phase_labels[macro_phase])
    html = html.replace("{{ MACRO_PHASE_2_COLOR }}", st_active_bg if macro_phase >= 2 else st_pending_bg)
    html = html.replace("{{ MACRO_PHASE_2_TEXT }}", st_active_tx if macro_phase >= 2 else st_pending_tx)
    html = html.replace("{{ MACRO_PHASE_3_COLOR }}", st_active_bg if macro_phase >= 3 else st_pending_bg)
    html = html.replace("{{ MACRO_PHASE_3_TEXT }}", st_active_tx if macro_phase >= 3 else st_pending_tx)
    html = html.replace("{{ MACRO_PHASE_4_COLOR }}", st_active_bg if macro_phase >= 4 else st_pending_bg)
    html = html.replace("{{ MACRO_PHASE_4_TEXT }}", st_active_tx if macro_phase >= 4 else st_pending_tx)
    
    html = html.replace("{{ TABELA_MAQUINAS }}", tabela_maquinas)
    
    html = html.replace("{{ AUDIT_INFERENCES }}", str(audit_stats["inferences"]))
    html = html.replace("{{ AUDIT_LATENCY }}", f"{avg_latency}s")
    html = html.replace("{{ AUDIT_MODEL }}", most_used_model)
    html = html.replace("{{ AUDIT_TOKENS_IN }}", str(audit_stats["tokens_in"]))
    html = html.replace("{{ AUDIT_TOKENS_OUT }}", str(audit_stats["tokens_out"]))
    html = html.replace("{{ AUDIT_TOKENS_TOTAL }}", str(audit_stats["tokens_total"]))
    
    # Replace placeholders
    html = html.replace("{{ DATA_ATUALIZACAO }}", datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
    html = html.replace("{{ TOTAL_ARTIGOS }}", str(stats["total"]))
    html = html.replace("{{ TOTAL_INCLUIDOS_F1 }}", str(stats["incluidos_f1"]))
    html = html.replace("{{ TOTAL_EXCLUIDOS_F1 }}", str(stats["excluidos_f1"]))
    html = html.replace("{{ TOTAL_PENDENTES_F1 }}", str(stats["pendentes_f1"]))
    html = html.replace("{{ TOTAL_NEEDS_PDF }}", str(stats["needs_pdf"]))
    
    html = html.replace("{{ PERCENT_INCLUIDOS }}", str(calc_percent(stats["incluidos_f1"], stats["total"])))
    html = html.replace("{{ PERCENT_EXCLUIDOS }}", str(calc_percent(stats["excluidos_f1"], stats["total"])))
    html = html.replace("{{ PERCENT_PENDENTES }}", str(calc_percent(stats["pendentes_f1"], stats["total"])))
    html = html.replace("{{ PERCENT_NEEDS_PDF }}", str(calc_percent(stats["needs_pdf"], stats["incluidos_f1"] if stats["incluidos_f1"] > 0 else 1)))
    
    html = html.replace("{{ MACRO_PHASE_WIDTH }}", phase_widths[macro_phase])
    html = html.replace("{{ MACRO_PHASE_LABEL }}", phase_labels[macro_phase])
    
    html = html.replace("{{ TABELA_MAQUINAS }}", tabela_maquinas)
    
    # Inject JSON data for JS interactions
    json_payload = json.dumps(articles_data, ensure_ascii=False)
    html = html.replace("{{ ARTICLES_JSON }}", json_payload)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
        
    print(f"Dashboard gerado em {output_path}")
    
    # Auto-abre no browser padrão
    try:
        webbrowser.open(f"file://{os.path.abspath(output_path)}")
    except:
        pass

if __name__ == "__main__":
    generate_dashboard()


