# ==============================================================================
# DEPRECATED — Este script monolítico foi substituído por uma arquitetura modular.
# Novo entrypoint canônico: scripts/review_pipeline/run_ingestion.py
# Mantido aqui sem alterações para evitar quebras em fluxos secundários legados.
# ==============================================================================
import csv
import os
import re
import sys

def normalize_doi(doi_str):
    if not doi_str:
        return ""
    # Remove prefixos como https://doi.org/
    doi_str = doi_str.replace("https://doi.org/", "").replace("http://dx.doi.org/", "").strip()
    return doi_str

def process_wos_csv(file_path, output_path):
    print(f"Processando {file_path}...")
    
    unique_articles = {}
    total_read = 0
    
    # Tentaremos ler com utf-8, com fallback
    try:
        f = open(file_path, "r", encoding="utf-8", errors="replace")
        # WoS CSVs podem ter diferentes separadores. Pela análise anterior, parece ser ';'
        reader = csv.DictReader(f, delimiter=";")
        
        for row in reader:
            total_read += 1
            
            title = row.get("Article Title", row.get("Title", "")).strip()
            abstract = row.get("Abstract", "").strip()
            doi = normalize_doi(row.get("DOI", ""))
            authors = row.get("Authors", row.get("Author(s)", "")).strip()
            year = row.get("Publication Year", row.get("Year", "")).strip()
            journal = row.get("Source Title", row.get("Journal", "")).strip()
            
            if not title:
                continue
                
            # Chave de unicidade primária: DOI, secundária: Título
            key = doi.lower() if doi else title.lower()
            
            if key not in unique_articles:
                unique_articles[key] = {
                    "Title": title,
                    "Abstract": abstract,
                    "DOI": doi,
                    "Authors": authors,
                    "Year": year,
                    "Journal": journal,
                    "Status": "Aguardando Fase 1"
                }
                
        f.close()
    except Exception as e:
        print(f"Erro lendo o arquivo: {e}")
        return
        
    print(f"Registros lidos: {total_read}")
    print(f"Artigos únicos identificados: {len(unique_articles)}")
    
    # Salvar PRISMA Log
    fieldnames = ["Title", "Authors", "Year", "Journal", "DOI", "Abstract", "Status", "Exclusion_Reason"]
    
    try:
        with open(output_path, "w", encoding="utf-8", newline="") as out:
            writer = csv.DictWriter(out, fieldnames=fieldnames)
            writer.writeheader()
            for key, data in unique_articles.items():
                data["Exclusion_Reason"] = ""
                writer.writerow(data)
        print(f"PRISMA Log gerado com sucesso em: {output_path}")
    except Exception as e:
        print(f"Erro gravando arquivo de saída: {e}")

if __name__ == "__main__":
    input_file = "exportacao/savedrecs.csv"
    output_file = "saida/PRISMA_LOG.csv"
    
    if os.path.exists(input_file):
        process_wos_csv(input_file, output_file)
    else:
        print(f"Arquivo não encontrado: {input_file}")
