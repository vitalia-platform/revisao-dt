"""
run_pdf_download.py — Recuperação Automatizada de PDFs de Artigos Aprovados

Uso:
    python run_pdf_download.py [--config ./criteria_config.yaml] [--email vitalia.platform@gmail.com]

Funcionalidades:
    1. Filtra artigos com status "Incluido Fase 1" no PRISMA_LOG.csv
    2. Consulta APIs abertas (Unpaywall, Europe PMC) em busca de links de PDFs Open Access
    3. Resiliência máxima: 3 tentativas com backoff e logging de rede em caso de falha antes de desistir
    4. Gravação rica de logs: Captura detalhes de erros HTTP (ex: 403, 429), headers de resposta (Cloudflare, Rate-Limits)
       e snippets de resposta em saida/pdf_download_errors.log para auditoria técnica detalhada.
    5. Efetua download automático e armazena em fichamentos/pdfs/
    6. Gera o Relatório Ativo de Falhas (FALHAS_DOWNLOAD_PDF.md) com links diretos
       para os artigos cujos PDFs precisam ser baixados manualmente pelo pesquisador.
"""

import argparse
import csv
import json
import os
import sys
import re
import time
import requests

# Garante que o pacote core seja encontrado
sys.path.insert(0, os.path.dirname(__file__))

from core.config_manager import load_config
from core.ingestion.normalizer import normalize_doi

def sanitize_filename(filename: str) -> str:
    """Sanitiza strings para uso seguro como nome de arquivo."""
    # Remove acentos e caracteres não alfanuméricos
    filename = re.sub(r"[^\w\s-]", "", filename)
    # Substitui espaços e hifens múltiplos por underscore
    filename = re.sub(r"[-\s]+", "_", filename).strip("_")
    return filename[:60] # Limita tamanho para evitar caminhos muito longos

def generate_pdf_name(article: dict) -> str:
    """Gera um nome de arquivo padronizado: Autor_Ano_Titulo.pdf"""
    authors_raw = article.get("Authors", article.get("authors", "SemAutor"))
    # Pega o primeiro sobrenome ou os primeiros caracteres do autor
    first_author = authors_raw.split(",")[0].split(" ")[0].strip()
    if not first_author:
        first_author = "Autor"
        
    year = article.get("Year", article.get("year", "0000")).strip()
    title = article.get("Title", article.get("title", "SemTitulo")).strip()
    
    clean_author = sanitize_filename(first_author)
    clean_title = sanitize_filename(title)
    
    return f"{clean_author}_{year}_{clean_title}.pdf"

def log_download_error(doi: str, url: str, status_code: int | None, response_text: str | None, headers: dict | None, exception_msg: str | None = None):
    """Grava logs super detalhados de erros de download em saida/pdf_download_errors.log para auditoria do pesquisador."""
    os.makedirs("saida", exist_ok=True)
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open("saida/pdf_download_errors.log", "a", encoding="utf-8") as f:
            f.write(f"=== [{timestamp}] ERRO DE DOWNLOAD ===\n")
            f.write(f"DOI: {doi}\n")
            f.write(f"URL de Origem: {url}\n")
            if status_code:
                f.write(f"Status HTTP: {status_code}\n")
            if exception_msg:
                f.write(f"Exceção de Rede: {exception_msg}\n")
            if headers:
                # Transforma CaseInsensitiveDict do requests para dicionário serializável
                headers_serializable = {k: v for k, v in headers.items()}
                f.write(f"Headers da Resposta:\n{json.dumps(headers_serializable, indent=2)}\n")
            if response_text:
                # Salva os primeiros 1000 caracteres da resposta (pode ser HTML do Cloudflare ou JSON de API)
                snippet = response_text[:1000]
                f.write(f"Conteúdo da Resposta (Snippet):\n{snippet}\n")
            f.write("=" * 60 + "\n\n")
    except Exception as e:
        print(f"    [Logger] Falha crítica ao gravar log de erros: {e}")

def try_unpaywall(doi: str, email: str, base_url: str = "https://api.unpaywall.org/v2") -> tuple[str | None, str]:
    """
    Busca o link do PDF de acesso aberto via API do Unpaywall com 3 retries em falha de rede.
    Retorna uma tupla (pdf_url, detalhe_do_erro).
    """
    url = f"{base_url.rstrip('/')}/{doi}"
    params = {"email": email}
    max_retries = 3
    wait_times = [3, 5, 10]
    last_error = "Não processado"
    
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("is_oa"):
                    best_location = data.get("best_oa_location") or {}
                    pdf_url = best_location.get("url_for_pdf") or best_location.get("url")
                    if pdf_url:
                        return pdf_url, "Success"
                return None, "Open Access PDF URL not found in Unpaywall response"
            elif resp.status_code == 404:
                return None, "DOI not found on Unpaywall (HTTP 404)"
            else:
                last_error = f"HTTP {resp.status_code}"
                print(f"    \033[93m[RETRY {attempt}/{max_retries}] Unpaywall retornou HTTP {resp.status_code}. Aguardando {wait_times[attempt-1]}s...\033[0m")
                log_download_error(doi, url, resp.status_code, resp.text, resp.headers)
        except requests.exceptions.RequestException as e:
            last_error = f"Network Exception: {type(e).__name__}"
            print(f"    \033[93m[RETRY {attempt}/{max_retries}] Falha de rede Unpaywall: {e}. Aguardando {wait_times[attempt-1]}s...\033[0m")
            log_download_error(doi, url, None, None, None, exception_msg=str(e))
            
        if attempt < max_retries:
            time.sleep(wait_times[attempt - 1])
            
    return None, f"Unpaywall falhou após 3 tentativas. Último erro: {last_error}"

def try_europe_pmc(doi: str, base_url: str = "https://www.ebi.ac.uk/europepmc/webservices/rest") -> tuple[str | None, str]:
    """
    Busca link do PDF ou ID PMC via Europe PMC API com 3 retries em falha de rede.
    Retorna uma tupla (pdf_url, detalhe_do_erro).
    """
    url = f"{base_url.rstrip('/')}/search"
    params = {
        "query": f"DOI:{doi}",
        "format": "json",
        "resultType": "lite"
    }
    max_retries = 3
    wait_times = [3, 5, 10]
    last_error = "Não processado"
    
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code == 200:
                results = resp.json().get("resultList", {}).get("result", [])
                if results:
                    result = results[0]
                    pmcid = result.get("pmcid")
                    if pmcid:
                        pmcid_clean = pmcid.replace("PMC", "").strip()
                        return f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmcid_clean}/pdf/", "Success"
                return None, "No PMCID found in Europe PMC response"
            else:
                last_error = f"HTTP {resp.status_code}"
                print(f"    \033[93m[RETRY {attempt}/{max_retries}] Europe PMC retornou HTTP {resp.status_code}. Aguardando {wait_times[attempt-1]}s...\033[0m")
                log_download_error(doi, url, resp.status_code, resp.text, resp.headers)
        except requests.exceptions.RequestException as e:
            last_error = f"Network Exception: {type(e).__name__}"
            print(f"    \033[93m[RETRY {attempt}/{max_retries}] Falha de rede Europe PMC: {e}. Aguardando {wait_times[attempt-1]}s...\033[0m")
            log_download_error(doi, url, None, None, None, exception_msg=str(e))
            
        if attempt < max_retries:
            time.sleep(wait_times[attempt - 1])
            
    return None, f"Europe PMC falhou após 3 tentativas. Último erro: {last_error}"

def download_pdf(pdf_url: str, save_path: str, doi_context: str = "") -> tuple[bool, str]:
    """
    Efetua o download do arquivo PDF com 3 retries em falha de rede.
    Retorna uma tupla (sucesso_bool, detalhe_do_erro).
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/pdf,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }
    max_retries = 3
    wait_times = [3, 5, 10]
    last_error = "Não iniciado"
    
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(pdf_url, headers=headers, timeout=20, stream=True)
            if resp.status_code == 200:
                content_type = resp.headers.get("Content-Type", "").lower()
                if "pdf" in content_type or pdf_url.endswith(".pdf"):
                    with open(save_path, "wb") as f:
                        for chunk in resp.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                    return True, "Downloaded successfully"
                else:
                    err_msg = f"Invalid Content-Type: {content_type} (not PDF)"
                    log_download_error(doi_context, pdf_url, resp.status_code, resp.text[:1000], resp.headers)
                    return False, err_msg
            else:
                last_error = f"HTTP {resp.status_code}"
                print(f"    \033[93m[RETRY {attempt}/{max_retries}] Download retornou HTTP {resp.status_code}. Aguardando {wait_times[attempt-1]}s...\033[0m")
                log_download_error(doi_context, pdf_url, resp.status_code, resp.text, resp.headers)
        except requests.exceptions.RequestException as e:
            last_error = f"Network Exception: {type(e).__name__}"
            print(f"    \033[93m[RETRY {attempt}/{max_retries}] Falha de rede no Download: {e}. Aguardando {wait_times[attempt-1]}s...\033[0m")
            log_download_error(doi_context, pdf_url, None, None, None, exception_msg=str(e))
            
        if attempt < max_retries:
            time.sleep(wait_times[attempt - 1])
            
    return False, f"Download falhou após 3 tentativas. Último erro: {last_error}"

def main():
    parser = argparse.ArgumentParser(
        description="Recuperação de PDFs em lote para a Fase 2 (Leitura Completa)"
    )
    parser.add_argument(
        "--config",
        default="./criteria_config.yaml",
        help="Caminho para o criteria_config.yaml (default: ./criteria_config.yaml)",
    )
    parser.add_argument(
        "--email",
        default="vitalia.platform@gmail.com",
        help="E-mail para identificação nas requisições da API do Unpaywall",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    paths = config.get("paths", {})
    
    prisma_log_path = os.path.join(paths.get("output_prisma", "saida"), "PRISMA_LOG.csv")
    pdf_dir = os.path.join(paths.get("output_fichamentos", "fichamentos"), "pdfs")
    
    os.makedirs(pdf_dir, exist_ok=True)
    
    if not os.path.exists(prisma_log_path):
        print(f"\033[91m[ERRO] PRISMA_LOG.csv não encontrado em {prisma_log_path}.\033[0m")
        sys.exit(1)
        
    # 1. Carrega os artigos que foram incluídos na Fase 1
    approved_articles = []
    with open(prisma_log_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("Status", "").strip() == "Incluido Fase 1":
                approved_articles.append(row)
                
    total_approved = len(approved_articles)
    if total_approved == 0:
        print("\n\033[92m✔ Nenhum artigo com status 'Incluido Fase 1' encontrado no PRISMA_LOG.csv para download.\033[0m")
        sys.exit(0)
        
    print(f"\n\033[94m{'═'*60}\033[0m")
    print(f"\033[94m  FASE 2 — RECUPERAÇÃO DE PDFs ({total_approved} artigo(s) aprovado(s))\033[0m")
    print(f"\033[94m{'═'*60}\033[0m")
    print(f"  Diretório de destino: {pdf_dir}\n")
    
    # Caminho do log de mapeamento de nomes de arquivos
    map_log_path = os.path.join(paths.get("output_prisma", "saida"), "DOWNLOAD_MAP.csv")
    
    # Carrega mapeamentos existentes se houver, para manter histórico
    existing_map = {}
    if os.path.exists(map_log_path):
        try:
            with open(map_log_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    existing_map[row.get("Original_Title", "")] = row
        except Exception as e:
            print(f"  [Aviso] Falha ao carregar DOWNLOAD_MAP.csv existente: {e}")

    def update_map_log(original_title: str, doi_str: str, saved_filename: str, source: str, status: str, error_detail: str = "None"):
        """Atualiza a planilha DOWNLOAD_MAP.csv mantendo a correspondência de nomes e enriquecendo com detalhes de erro."""
        existing_map[original_title] = {
            "Original_Title": original_title,
            "DOI": doi_str,
            "Saved_Filename": saved_filename,
            "Source": source,
            "Status": status,
            "Error_Detail": error_detail
        }
        try:
            with open(map_log_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["Original_Title", "DOI", "Saved_Filename", "Source", "Status", "Error_Detail"])
                writer.writeheader()
                for k, v in sorted(existing_map.items()):
                    writer.writerow(v)
        except Exception as e:
            print(f"  [Erro] Falha ao salvar DOWNLOAD_MAP.csv: {e}")

    success_downloads = []
    failed_downloads = []
    
    # Resolvendo os endpoints dinamicamente do config se definidos
    pdf_sources = {s["name"]: s.get("base_url") for s in config.get("pdf_retrieval_sources", []) if s.get("enabled")}
    unpaywall_base = pdf_sources.get("unpaywall", "https://api.unpaywall.org/v2")
    europepmc_base = pdf_sources.get("europepmc", "https://www.ebi.ac.uk/europepmc/webservices/rest")
    
    for idx, article in enumerate(approved_articles, 1):
        title = article.get("Title", "").strip()
        doi = normalize_doi(article.get("DOI", "")).strip()
        
        pdf_filename = generate_pdf_name(article)
        pdf_save_path = os.path.join(pdf_dir, pdf_filename)
        
        print(f"[{idx}/{total_approved}] {title[:70]}...")
        
        # Se o PDF já foi baixado ou existe na pasta, pula para economizar banda
        if os.path.exists(pdf_save_path) and os.path.getsize(pdf_save_path) > 10000:
            print("  \033[92m✔ PDF já existe localmente. Pulando.\033[0m")
            success_downloads.append((article, pdf_filename))
            update_map_log(title, doi, pdf_filename, "Local/Existing", "Downloaded", "None")
            continue
            
        if not doi:
            print("  \033[93m[AVISO] Artigo sem DOI. Adicionado para download manual.\033[0m")
            failed_downloads.append((article, "Sem DOI cadastrado"))
            update_map_log(title, doi, pdf_filename, "None", "Pending", "DOI field is empty or malformed")
            continue
            
        # 1ª Tentativa: Unpaywall
        print(f"  → Buscando no Unpaywall...")
        pdf_url, unpay_err = try_unpaywall(doi, args.email, unpaywall_base)
        source_used = "Unpaywall" if pdf_url else None
        last_error = unpay_err
        
        # 2ª Tentativa: Europe PMC
        if not pdf_url:
            print(f"  → Não encontrado. Buscando no Europe PMC...")
            pdf_url, eur_err = try_europe_pmc(doi, europepmc_base)
            source_used = "EuropePMC" if pdf_url else None
            last_error = f"{unpay_err} | {eur_err}"
            
        if pdf_url:
            print(f"  → Link localizado: {pdf_url[:60]}...")
            print(f"  → Baixando arquivo...")
            down_success, down_err = download_pdf(pdf_url, pdf_save_path, doi_context=doi)
            if down_success:
                print(f"  \033[92m✔ Download concluído: {pdf_filename}\033[0m")
                success_downloads.append((article, pdf_filename))
                update_map_log(title, doi, pdf_filename, source_used, "Downloaded", "None")
                # Cortesia de taxa de requisição para as APIs abertas
                time.sleep(1.0)
                continue
            else:
                last_error = f"Download failed: {down_err}"
                
        print(f"  \033[91m✘ Falha na recuperação automática de PDF: {last_error[:80]}...\033[0m")
        failed_downloads.append((article, last_error))
        update_map_log(title, doi, pdf_filename, "None", "Pending", last_error)
        time.sleep(0.5)

    # 4. Geração do Relatório Ativo de Falhas (FALHAS_DOWNLOAD_PDF.md)
    failures_report_path = os.path.join(paths.get("output_prisma", "saida"), "FALHAS_DOWNLOAD_PDF.md")
    
    with open(failures_report_path, "w", encoding="utf-8") as rf:
        rf.write("# Relatório Ativo de Falhas — Downloads de PDF (Fase 2)\n")
        rf.write(f"**Data:** {time.strftime('%Y-%m-%d %H:%M:%S')}  \n")
        rf.write(f"**Status:** {len(failed_downloads)} PDFs pendentes de download manual.  \n\n")
        rf.write("---\n\n")
        rf.write("> [!NOTE]\n")
        rf.write("> Os artigos listados abaixo foram aprovados na triagem da Fase 1, mas seus PDFs completos não puderam ser recuperados automaticamente através das APIs do Unpaywall e Europe PMC.  \n")
        rf.write("> **Por favor, use os links do DOI abaixo para baixá-los manualmente (ex: via CAFe/RNP) e salve-os em `fichamentos/pdfs/` seguindo a nomenclatura indicada.**\n\n")
        rf.write("## Lista de Downloads Manuais Pendentes\n\n")
        rf.write("| # | Artigo (Título) | Autor/Ano | DOI / Link de Acesso | Nomenclatura Esperada | Detalhe do Erro |\n")
        rf.write("|---|---|---|---|---|---|\n")
        
        for idx, (art, reason) in enumerate(failed_downloads, 1):
            doi = art.get("DOI", "").strip()
            title = art.get("Title", "").strip()
            authors = art.get("Authors", "").strip()
            year = art.get("Year", "").strip()
            expected_name = generate_pdf_name(art)
            
            doi_link = f"[doi: {doi}](https://doi.org/{doi})" if doi else "*Sem DOI*"
            
            rf.write(f"| {idx} | {title} | {authors.split(',')[0]} ({year}) | {doi_link} | `{expected_name}` | {reason} |\n")

    print(f"\n\033[94m{'═'*60}\033[0m")
    print(f"\033[92m  RECUPERAÇÃO DE PDFs CONCLUÍDA\033[0m")
    print(f"\033[94m{'═'*60}\033[0m")
    print(f"  PDFs recuperados com sucesso:   \033[92m{len(success_downloads)}\033[0m")
    print(f"  PDFs com falha (manual):        \033[91m{len(failed_downloads)}\033[0m")
    print(f"  Relatório de falhas gerado:     {failures_report_path}")
    print(f"  Planilha de mapeamento (CSV):   {map_log_path}")
    print(f"  Arquivo detalhado de erros:     saida/pdf_download_errors.log")
    print(f"\033[94m{'═'*60}\033[0m\n")

if __name__ == "__main__":
    main()
