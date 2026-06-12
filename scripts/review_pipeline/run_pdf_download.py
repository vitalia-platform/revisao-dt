# scripts/review_pipeline/run_pdf_download.py | Atualizado em: 11-06-2026 08:00:00(GMT-04:00)
"""
run_pdf_download.py — Recuperador Híbrido de Texto Completo (XML > PDF)

Funcionalidades:
    1. Prioriza o download do Full-Text XML nativo (via EuropePMC).
    2. Fallback resiliente para PDF via OpenAlex.
    3. Motor HTTP robusto com Exponential Backoff e Rate Limiting.
"""

import argparse
import csv
import os
import sys
import re
import time

# Garante que o pacote core seja encontrado
sys.path.insert(0, os.path.dirname(__file__))

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from core.config_manager import load_config
from core.ingestion.normalizer import normalize_doi
from core.http_client import RobustHTTPClient
from core.auditor import ReviewAuditor
from core.state_manager import StateManager
from core import terminal
from scripts.generate_live_dashboard import build_dashboard

def sanitize_filename(filename: str) -> str:
    filename = re.sub(r"[^\w\s-]", "", filename)
    filename = re.sub(r"[-\s]+", "_", filename).strip("_")
    return filename[:60]

def generate_base_filename(article: dict) -> str:
    authors_raw = article.get("Authors", article.get("authors", "SemAutor"))
    first_author = authors_raw.split(",")[0].split(" ")[0].strip() or "Autor"
    year = article.get("Year", article.get("year", "0000")).strip()
    title = article.get("Title", article.get("title", "SemTitulo")).strip()
    return f"{sanitize_filename(first_author)}_{year}_{sanitize_filename(title)}"

def fetch_europepmc_xml(doi: str, client: RobustHTTPClient, save_path: str) -> tuple[bool, str]:
    """Busca o PMCID e depois o arquivo XML completo."""
    search_url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
    params = {"query": f"DOI:{doi}", "format": "json", "resultType": "lite"}
    
    resp = client.get(search_url, params=params)
    if not resp or resp.status_code != 200:
        return False, f"EuropePMC Search Falhou (HTTP {resp.status_code if resp else 'Error'})"
        
    results = resp.json().get("resultList", {}).get("result", [])
    if not results:
        return False, "Nenhum resultado no EuropePMC"
        
    pmcid = results[0].get("pmcid")
    if not pmcid:
        return False, "PMCID não disponível"
        
    # Baixar XML
    xml_url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML"
    success, err = client.download_file(xml_url, save_path)
    if success:
        return True, "XML Success"
    return False, f"Falha download XML: {err}"

def fetch_openalex_pdf(doi: str, client: RobustHTTPClient, save_path: str, email: str) -> tuple[bool, str]:
    """Usa OpenAlex para encontrar a melhor URL Open Access em PDF."""
    url = f"https://api.openalex.org/works/https://doi.org/{doi}"
    headers = {"User-Agent": f"mailto:{email}"}
    
    resp = client.get(url, headers=headers)
    if not resp or resp.status_code != 200:
        return False, f"OpenAlex Falhou (HTTP {resp.status_code if resp else 'Error'})"
        
    oa_data = resp.json().get("open_access", {})
    if not oa_data or not oa_data.get("is_oa"):
        return False, "Artigo não é Open Access no OpenAlex"
        
    pdf_url = oa_data.get("oa_url")
    if not pdf_url:
        return False, "URL do PDF ausente no OpenAlex"
        
    success, err = client.download_file(pdf_url, save_path)
    if success:
        return True, "PDF Success"
    return False, f"Falha download PDF: {err}"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="./criteria_config.yaml")
    parser.add_argument("--email", default="vitalia.platform@gmail.com")
    args = parser.parse_args()

    config = load_config(args.config)
    data_storage = config.get("infrastructure", {}).get("data_storage", ".agent/data_storage")
    
    prisma_log_path = os.path.join(data_storage, "saida", "PRISMA_LOG_MASTER.csv")
    pdf_dir = os.path.join(data_storage, "fichamentos", "pdfs")
    xml_dir = os.path.join(data_storage, "fichamentos", "xmls")
    
    os.makedirs(pdf_dir, exist_ok=True)
    os.makedirs(xml_dir, exist_ok=True)
    
    if not os.path.exists(prisma_log_path):
        print(f"\033[91m[ERRO] PRISMA_LOG_MASTER.csv não encontrado.\033[0m")
        sys.exit(1)
        
    approved_articles = []
    with open(prisma_log_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            status = row.get("Status", "").strip().lower()
            if "inclu" in status and "fase 1" in status:
                approved_articles.append(row)
                
    total_approved = len(approved_articles)
    if total_approved == 0:
        print("\033[92m✔ Nenhum artigo aprovado pendente.\033[0m")
        sys.exit(0)
        
    map_log_path = os.path.join(data_storage, "saida", "DOWNLOAD_MAP.csv")
    existing_map = {}
    if os.path.exists(map_log_path):
        with open(map_log_path, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                existing_map[row.get("Original_Title", "")] = row

    def update_map_log(original_title: str, doi_str: str, saved_filename: str, source: str, status: str, error_detail: str = "None"):
        existing_map[original_title] = {
            "Original_Title": original_title, "DOI": doi_str, "Saved_Filename": saved_filename,
            "Source": source, "Status": status, "Error_Detail": error_detail
        }
        with open(map_log_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["Original_Title", "DOI", "Saved_Filename", "Source", "Status", "Error_Detail"])
            writer.writeheader()
            for k, v in sorted(existing_map.items()): writer.writerow(v)

    success_downloads = []
    failed_downloads = []
    client = RobustHTTPClient()
    auditor = ReviewAuditor(base_output_dir=os.path.join(data_storage, "saida", "auditoria"))
    def update_dashboards():
        try:
            from scripts.generate_live_dashboard import build_dashboard as build_live_dashboard
            from scripts.generate_progress import generate_dashboard as build_progress_dashboard
            build_live_dashboard()
            build_progress_dashboard()
        except Exception as e:
            print(f"Erro ao atualizar dashboard: {e}")

    state_mgr = StateManager(on_event_callback=update_dashboards)
    
    
    terminal.print_section_header(f"FASE 2a — RECUPERAÇÃO HÍBRIDA XML/PDF ({total_approved} artigo(s))")
    state_mgr.set_active_state("fase2a_download", "Fase 2a: Download de PDFs", total_approved, current_task="Preparando Downloads...")

    for idx, article in enumerate(approved_articles, 1):
        terminal.show_progress_bar(idx, total_approved, success=len(success_downloads), skipped=0, erros=len(failed_downloads))
        title = article.get("Title", "").strip()
        doi = normalize_doi(article.get("DOI", "")).strip()
        base_name = generate_base_filename(article)
        item_start_time = time.time()
        
        xml_save_path = os.path.join(xml_dir, base_name + ".xml")
        pdf_save_path = os.path.join(pdf_dir, base_name + ".pdf")
        
        terminal.print_step(title[:60] + "...")
        state_mgr.update_state(current_task=f"Tentando baixar: {title[:50]}...")
        
        if os.path.exists(xml_save_path) and os.path.getsize(xml_save_path) > 1000:
            terminal.print_success("XML já existe localmente.")
            success_downloads.append((article, base_name + ".xml"))
            update_map_log(title, doi, base_name + ".xml", "Local/XML", "Downloaded", "None")
            lat = round(time.time() - item_start_time, 2)
            auditor.save_inference_shard(phase=20, item_id=base_name, payload={"article_metadata": article, "status": "SUCCESS", "source": "Local/XML", "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"), "inference_metrics": {"latency_seconds": lat}})
            state_mgr.update_state(processed=1, skipped=1)
            continue
        if os.path.exists(pdf_save_path) and os.path.getsize(pdf_save_path) > 10000:
            terminal.print_success("PDF já existe localmente.")
            success_downloads.append((article, base_name + ".pdf"))
            update_map_log(title, doi, base_name + ".pdf", "Local/PDF", "Downloaded", "None")
            lat = round(time.time() - item_start_time, 2)
            auditor.save_inference_shard(phase=20, item_id=base_name, payload={"article_metadata": article, "status": "SUCCESS", "source": "Local/PDF", "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"), "inference_metrics": {"latency_seconds": lat}})
            state_mgr.update_state(processed=1, skipped=1)
            continue
            
        if not doi:
            terminal.print_warning("Sem DOI. Download manual.")
            failed_downloads.append((article, "Sem DOI"))
            update_map_log(title, doi, "", "None", "Pending", "DOI malformed")
            lat = round(time.time() - item_start_time, 2)
            auditor.save_inference_shard(phase=20, item_id=base_name, payload={"article_metadata": article, "status": "FAIL", "error": "Sem DOI", "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"), "inference_metrics": {"latency_seconds": lat}})
            state_mgr.update_state(processed=1, fails=1)
            continue
            
        xml_ok, xml_err = fetch_europepmc_xml(doi, client, xml_save_path)
        if xml_ok:
            terminal.print_success("Download XML concluído (EuropePMC).")
            success_downloads.append((article, base_name + ".xml"))
            update_map_log(title, doi, base_name + ".xml", "EuropePMC/XML", "Downloaded", "None")
            lat = round(time.time() - item_start_time, 2)
            auditor.save_inference_shard(phase=20, item_id=base_name, payload={"article_metadata": article, "status": "SUCCESS", "source": "EuropePMC/XML", "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"), "inference_metrics": {"latency_seconds": lat}})
            state_mgr.update_state(processed=1, success=1)
            time.sleep(1.0)
            continue
            
        pdf_ok, pdf_err = fetch_openalex_pdf(doi, client, pdf_save_path, args.email)
        if pdf_ok:
            terminal.print_success("Download PDF concluído (OpenAlex).")
            success_downloads.append((article, base_name + ".pdf"))
            update_map_log(title, doi, base_name + ".pdf", "OpenAlex/PDF", "Downloaded", "None")
            lat = round(time.time() - item_start_time, 2)
            auditor.save_inference_shard(phase=20, item_id=base_name, payload={"article_metadata": article, "status": "SUCCESS", "source": "OpenAlex/PDF", "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"), "inference_metrics": {"latency_seconds": lat}})
            state_mgr.update_state(processed=1, success=1)
            time.sleep(1.0)
            continue
            
        last_error = f"XML: {xml_err} | PDF: {pdf_err}"
        terminal.print_error(f"Falha no download: {last_error[:80]}...")
        failed_downloads.append((article, last_error))
        update_map_log(title, doi, "", "None", "Pending", last_error)
        lat = round(time.time() - item_start_time, 2)
        auditor.save_inference_shard(phase=20, item_id=base_name, payload={"article_metadata": article, "status": "FAIL", "error": last_error, "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"), "inference_metrics": {"latency_seconds": lat}})
        state_mgr.update_state(processed=1, fails=1)

    failures_report_path = os.path.join(data_storage, "saida", "FALHAS_DOWNLOAD_MANUAL.md")
    with open(failures_report_path, "w", encoding="utf-8") as rf:
        rf.write("# Relatório de Downloads Manuais\n\n")
        rf.write(f"| # | Título | Autor/Ano | DOI | Nomenclatura Esperada | Erro |\n")
        rf.write(f"|---|---|---|---|---|---|\n")
        for idx, (art, reason) in enumerate(failed_downloads, 1):
            doi = art.get("DOI", "").strip()
            title = art.get("Title", "").strip()
            authors = art.get("Authors", "").strip()
            year = art.get("Year", "").strip()
            expected_name = generate_base_filename(art) + ".pdf"
            doi_link = f"[doi](https://doi.org/{doi})" if doi else ""
            rf.write(f"| {idx} | {title} | {authors.split(',')[0]} ({year}) | {doi_link} | `{expected_name}` | {reason} |\n")

    state_mgr.update_state(finish=True)
    print(f"\n\033[92m  SUCESSO: {len(success_downloads)} | FALHAS: {len(failed_downloads)}\033[0m\n")

if __name__ == "__main__":
    main()
