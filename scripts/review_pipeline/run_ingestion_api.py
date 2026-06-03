import os
import sys
import yaml
import json
import requests
import csv
import urllib.parse
from datetime import datetime

# Garante import do módulo core local
sys.path.insert(0, os.path.dirname(__file__))
from core.deduplicator import Deduplicator, normalize_doi

def load_config(config_path="criteria_config.yaml"):
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

import xml.etree.ElementTree as ET

def fetch_pubmed(query: str, limit: int = 50):
    print(f"\n[PubMed] Buscando {limit} artigos para query: {query[:50]}...")
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    
    # 1. eSearch para pegar os IDs
    search_url = f"{base_url}/esearch.fcgi?db=pubmed&term={urllib.parse.quote(query)}&retmax={limit}&sort=relevance&retmode=json"
    
    try:
        res = requests.get(search_url, timeout=30)
        res.raise_for_status()
        id_list = res.json().get("esearchresult", {}).get("idlist", [])
        
        if not id_list:
            print("    Nenhum artigo encontrado no PubMed.")
            return []
            
        print(f"    Encontrados {len(id_list)} IDs. Baixando metadados via eFetch...")
        
        # 2. eFetch para pegar o XML completo em lote (resolve o problema dos Abstracts vazios)
        fetch_url = f"{base_url}/efetch.fcgi?db=pubmed&id={','.join(id_list)}&retmode=xml"
        res_fetch = requests.get(fetch_url, timeout=60)
        res_fetch.raise_for_status()
        
        # Parse XML
        root = ET.fromstring(res_fetch.content)
        articles = []
        
        for article_elem in root.findall(".//PubmedArticle"):
            medline = article_elem.find(".//MedlineCitation")
            if medline is None: continue
            
            article_data = medline.find("Article")
            if article_data is None: continue
            
            # Título
            title = article_data.findtext("ArticleTitle", default="")
            
            # Abstract
            abstract_text = ""
            abstract_elem = article_data.find("Abstract")
            if abstract_elem is not None:
                texts = []
                for abs_txt in abstract_elem.findall("AbstractText"):
                    lbl = abs_txt.get("Label", "")
                    txt = abs_txt.text or ""
                    if lbl and txt:
                        texts.append(f"{lbl}: {txt}")
                    elif txt:
                        texts.append(txt)
                abstract_text = " ".join(texts)
                
            if not abstract_text:
                abstract_text = "Abstract não disponível no registro PubMed."
                
            # Ano
            year = "N/A"
            pubdate = article_data.find(".//PubDate")
            if pubdate is not None:
                year_elem = pubdate.find("Year")
                if year_elem is not None and year_elem.text:
                    year = year_elem.text
                else:
                    medlinedate = pubdate.find("MedlineDate")
                    if medlinedate is not None and medlinedate.text:
                        year = medlinedate.text[:4]
                        
            # Journal
            journal = article_data.findtext(".//Title", default="")
            
            # Autores
            authors = []
            author_list = article_data.find("AuthorList")
            if author_list is not None:
                for author in author_list.findall("Author"):
                    last = author.findtext("LastName", default="")
                    initials = author.findtext("Initials", default="")
                    if last or initials:
                        authors.append(f"{last} {initials}".strip())
                        
            # DOI
            doi = ""
            article_id_list = article_elem.find(".//PubmedData/ArticleIdList")
            if article_id_list is not None:
                for a_id in article_id_list.findall("ArticleId"):
                    if a_id.get("IdType") == "doi" and a_id.text:
                        doi = a_id.text
                        break
                        
            articles.append({
                "Title": title,
                "Authors": ", ".join(authors),
                "Year": year,
                "Journal": journal,
                "DOI": doi,
                "Abstract": abstract_text,
                "Source": "PubMed"
            })
            
        print(f"    Extraídos com sucesso {len(articles)} artigos do XML.")
        return articles
    except Exception as e:
        print(f"    [ERRO] PubMed falhou: {e}")
        return []

def fetch_openalex(query: str, limit: int = 50):
    print(f"\n[OpenAlex] Buscando {limit} artigos por relevância...")
    # OpenAlex funciona melhor convertendo a boolean string para um default.search
    # Extrai os termos principais
    search_term = "Design Thinking AND Physical Activity"
    
    # Monta a query URL
    url = f"https://api.openalex.org/works?search={urllib.parse.quote(search_term)}&per-page={limit}&sort=relevance_score:desc"
    
    try:
        res = requests.get(url, timeout=30)
        res.raise_for_status()
        results = res.json().get("results", [])
        
        if not results:
            print("    Nenhum artigo encontrado no OpenAlex.")
            return []
            
        print(f"    Encontrados {len(results)} artigos.")
        articles = []
        for item in results:
            authors = []
            for auth in (item.get("authorships") or []):
                author_dict = auth.get("author") or {}
                if isinstance(author_dict, dict):
                    name = author_dict.get("display_name")
                    if name: authors.append(name)
            doi = item.get("doi", "")
            if doi:
                doi = normalize_doi(doi)
                
            # Recupera abstract invertido (OpenAlex manda em index invertido)
            abstract_inv = item.get("abstract_inverted_index", {})
            abstract_text = ""
            if abstract_inv:
                words = {}
                for word, pos_list in abstract_inv.items():
                    for pos in pos_list:
                        words[pos] = word
                abstract_text = " ".join([words[i] for i in sorted(words.keys())])
                
            location = item.get("primary_location") or {}
            source = location.get("source") or {}
            journal = source.get("display_name", "")
            
            articles.append({
                "Title": item.get("title", ""),
                "Authors": ", ".join(authors),
                "Year": str(item.get("publication_year", "")),
                "Journal": journal,
                "DOI": doi,
                "Abstract": abstract_text,
                "Source": "OpenAlex"
            })
            
        return articles
    except Exception as e:
        print(f"    [ERRO] OpenAlex falhou: {e}")
        return []

def main():
    print("==================================================")
    print(" INGESTÃO API-FIRST — REVISÃO DT")
    print("==================================================")
    
    config = load_config()
    query_string = config.get("study", {}).get("query_string", "")
    
    if not query_string:
        print("[ERRO] query_string não definida no criteria_config.yaml")
        sys.exit(1)
        
    master_log_path = ".agent/data_storage/saida/PRISMA_LOG_MASTER.csv"
    os.makedirs(os.path.dirname(master_log_path), exist_ok=True)
    
    deduplicator = Deduplicator(master_log_path)
    
    # Define o limite de amostra fixo por requisição do usuário
    LIMIT = 50
    
    # 1. Fetch das bases
    pubmed_articles = fetch_pubmed(query_string, LIMIT)
    openalex_articles = fetch_openalex(query_string, LIMIT)
    
    all_articles = pubmed_articles + openalex_articles
    
    # 2. Processamento e Deduplicação
    final_list = []
    duplicatas_count = 0
    
    for art in all_articles:
        # Padroniza chaves do dict do deduplicator
        dedup_record = {"doi": art.get("DOI"), "title": art.get("Title")}
        
        if deduplicator.is_duplicate(dedup_record):
            duplicatas_count += 1
        else:
            final_list.append(art)
            deduplicator.add_to_seen(dedup_record)
            
    print(f"\n[Resumo da Ingestão]")
    print(f"Total coletado: {len(all_articles)}")
    print(f"Duplicatas removidas: {duplicatas_count}")
    print(f"Artigos válidos para o Master Log: {len(final_list)}")
    
    # 3. Gravar no Master Log
    file_exists = os.path.exists(master_log_path)
    
    fieldnames = [
        "Title", "Authors", "Year", "Journal", "DOI", 
        "Abstract", "Status", "Exclusion_Reason", "PDF_status",
        "Full_text_source", "Source", "Machine_ID", "Ingestion_Date"
    ]
    
    with open(master_log_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
            
        machine_id = os.environ.get("MACHINE_ID", "local")
        today = datetime.now().strftime("%Y-%m-%d")
        
        for art in final_list:
            art["Status"] = "Aguardando Triagem Fase 1"
            art["Exclusion_Reason"] = ""
            art["PDF_status"] = "pending"
            art["Full_text_source"] = ""
            art["Machine_ID"] = machine_id
            art["Ingestion_Date"] = today
            writer.writerow(art)
            
    print(f"\n[SUCESSO] PRISMA_LOG_MASTER.csv atualizado em {master_log_path}.")

if __name__ == "__main__":
    main()
