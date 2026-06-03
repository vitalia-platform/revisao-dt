# scripts/review_pipeline/run_pdf_download.py | Atualizado em: 03-06-2026 12:02:36(GMT-04:00)
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

from core.config_manager import load_config
from core.ingestion.normalizer import normalize_doi
from core.http_client import RobustHTTPClient

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
    
    prisma_log_path = os.path.join(data_storage, "saida", "PRISMA_LOG.csv")
    pdf_dir = os.path.join(data_storage, "fichamentos", "pdfs")
    xml_dir = os.path.join(data_storage, "fichamentos", "xmls")
    
    os.makedirs(pdf_dir, exist_ok=True)
    os.makedirs(xml_dir, exist_ok=True)
    
    if not os.path.exists(prisma_log_path):
        print(f"\033[91m[ERRO] PRISMA_LOG.csv não encontrado.\033[0m")
        sys.exit(1)
        
    approved_articles = []
    with open(prisma_log_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("Status", "").strip() == "Incluido Fase 1":
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
    
    print(f"\n\033[94m  FASE 2 — RECUPERAÇÃO HÍBRIDA XML/PDF ({total_approved} artigo(s))\033[0m\n")

    for idx, article in enumerate(approved_articles, 1):
        title = article.get("Title", "").strip()
        doi = normalize_doi(article.get("DOI", "")).strip()
        base_name = generate_base_filename(article)
        
        xml_save_path = os.path.join(xml_dir, base_name + ".xml")
        pdf_save_path = os.path.join(pdf_dir, base_name + ".pdf")
        
        print(f"[{idx}/{total_approved}] {title[:70]}...")
        
        if os.path.exists(xml_save_path) and os.path.getsize(xml_save_path) > 1000:
            print("  \033[92m✔ XML já existe localmente.\033[0m")
            success_downloads.append((article, base_name + ".xml"))
            update_map_log(title, doi, base_name + ".xml", "Local/XML", "Downloaded", "None")
            continue
        if os.path.exists(pdf_save_path) and os.path.getsize(pdf_save_path) > 10000:
            print("  \033[92m✔ PDF já existe localmente.\033[0m")
            success_downloads.append((article, base_name + ".pdf"))
            update_map_log(title, doi, base_name + ".pdf", "Local/PDF", "Downloaded", "None")
            continue
            
        if not doi:
            print("  \033[93m[AVISO] Sem DOI. Download manual.\033[0m")
            failed_downloads.append((article, "Sem DOI"))
            update_map_log(title, doi, "", "None", "Pending", "DOI malformed")
            continue
            
        print("  → Buscando XML nativo (EuropePMC)...")
        xml_ok, xml_err = fetch_europepmc_xml(doi, client, xml_save_path)
        if xml_ok:
            print(f"  \033[92m✔ Download XML concluído.\033[0m")
            success_downloads.append((article, base_name + ".xml"))
            update_map_log(title, doi, base_name + ".xml", "EuropePMC/XML", "Downloaded", "None")
            time.sleep(1.0)
            continue
            
        print(f"  → Buscando PDF aberto (OpenAlex)...")
        pdf_ok, pdf_err = fetch_openalex_pdf(doi, client, pdf_save_path, args.email)
        if pdf_ok:
            print(f"  \033[92m✔ Download PDF concluído.\033[0m")
            success_downloads.append((article, base_name + ".pdf"))
            update_map_log(title, doi, base_name + ".pdf", "OpenAlex/PDF", "Downloaded", "None")
            time.sleep(1.0)
            continue
            
        last_error = f"XML: {xml_err} | PDF: {pdf_err}"
        print(f"  \033[91m✘ Falha: {last_error[:80]}...\033[0m")
        failed_downloads.append((article, last_error))
        update_map_log(title, doi, "", "None", "Pending", last_error)

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

    print(f"\n\033[92m  SUCESSO: {len(success_downloads)} | FALHAS: {len(failed_downloads)}\033[0m\n")

if __name__ == "__main__":
    main()
