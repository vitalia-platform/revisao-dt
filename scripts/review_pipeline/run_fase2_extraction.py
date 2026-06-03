# scripts/review_pipeline/run_fase2_extraction.py | Atualizado em: 03-06-2026 12:02:36(GMT-04:00)
"""
run_fase2_extraction.py — Extração Profunda e Fichamento Acadêmico dos Arquivos (Fase 2)

Uso:
    python run_fase2_extraction.py [--config ./criteria_config.yaml] [--overnight]
"""

import argparse
import csv
import hashlib
import json
import os
import re
import sys
import time
from pypdf import PdfReader

# Garante que o pacote core seja encontrado
sys.path.insert(0, os.path.dirname(__file__))

from core.config_manager import load_config
from core.ollama_client import query_ollama, check_ollama_alive, unload_model
from core.auditor import ReviewAuditor
from core import terminal

def calculate_sha256(filepath: str) -> str:
    sha256 = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()
    except Exception as e:
        print(f"    [SHA-256] Erro ao calcular hash: {e}")
        return "SHA_CALCULATION_ERROR"

def extract_xml_text(filepath: str, char_limit: int = 18000) -> str:
    """Extrai texto cirurgicamente de arquivos XML (JATS) usando BeautifulSoup."""
    try:
        from bs4 import BeautifulSoup
        with open(filepath, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f, "lxml-xml")
        
        text_blocks = []
        abstract = soup.find("abstract")
        if abstract:
            text_blocks.append("--- ABSTRACT ---")
            text_blocks.append(abstract.get_text(separator=" ", strip=True))
            
        body = soup.find("body")
        if body:
            sections = body.find_all("sec")
            if sections:
                for sec in sections:
                    title = sec.find("title")
                    sec_title = title.get_text(strip=True) if title else "SECTION"
                    text_blocks.append(f"--- {sec_title.upper()} ---")
                    text_blocks.append(sec.get_text(separator=" ", strip=True))
            else:
                text_blocks.append("--- BODY ---")
                text_blocks.append(body.get_text(separator=" ", strip=True))
                
        full_text = "\n\n".join(text_blocks)
        full_text = re.sub(r' {2,}', ' ', full_text)
        
        if len(full_text) > char_limit:
            full_text = full_text[:char_limit] + "\n\n[TEXTO OTIMIZADO/COMPRIMIDO PARA LIMITES DE VRAM]"
            
        return full_text
    except Exception as e:
        print(f"    [Extração XML] Falha crítica de leitura: {e}")
        return ""

def extract_pdf_text(filepath: str, char_limit: int = 18000) -> str:
    try:
        reader = PdfReader(filepath)
        num_pages = len(reader.pages)
        if num_pages == 0: return ""
            
        full_text_pages = [page.extract_text() or "" for page in reader.pages]
        
        ref_start_page = num_pages
        for i in range(num_pages - 1, max(-1, num_pages - 10), -1):
            page_text = full_text_pages[i].lower()
            if re.search(r'\n\s*(references|bibliography|referências)\s*\n', page_text):
                ref_start_page = i
                break
                
        valid_pages = full_text_pages[:min(ref_start_page + 1, num_pages)]
        
        pages_to_read = set()
        for idx in range(min(3, len(valid_pages))):
            pages_to_read.add(idx)
        for idx in range(max(0, len(valid_pages) - 2), len(valid_pages)):
            pages_to_read.add(idx)
            
        text_blocks = []
        for page_idx in sorted(list(pages_to_read)):
            text = valid_pages[page_idx]
            if text:
                text_blocks.append(f"--- PÁGINA {page_idx + 1} ---")
                text_blocks.append(text)
                
        full_text = "\n".join(text_blocks)
        
        full_text = re.sub(r'\n{3,}', '\n\n', full_text)
        full_text = re.sub(r' {2,}', ' ', full_text)
        full_text = re.sub(r'-\n', '', full_text)
        
        if len(full_text) > char_limit:
            full_text = full_text[:char_limit] + "\n\n[TEXTO OTIMIZADO/COMPRIMIDO PARA LIMITES DE VRAM]"
        return full_text
    except Exception as e:
        print(f"    [Extração PDF] Falha crítica de leitura: {e}")
        return ""

def format_fichamento(article_info: dict, ext_data: dict, sha256_hash: str, template_path: str) -> str:
    title = article_info.get("Original_Title", article_info.get("Title", "Sem Título")).strip()
    authors = article_info.get("Authors", "Não informado").strip()
    year = article_info.get("Year", "Não informado").strip()
    journal = article_info.get("Journal", "Não informado").strip()
    doi = article_info.get("DOI", "").strip()
    
    template = ""
    if os.path.exists(template_path):
        try:
            with open(template_path, "r", encoding="utf-8") as tf:
                template = tf.read()
        except Exception:
            pass
            
    if not template:
        template = f"# Fichamento: {title}\n**Status**: DRAFT\n**Data**: {time.strftime('%d-%m-%Y')}\n\n**Autores**: {authors}\n**Resultados**: {ext_data.get('key_findings', 'N/A')}\n"
        
    formatted = template.replace("| **Título** | |", f"| **Título** | {title} |") \
                        .replace("| **Autores** | |", f"| **Autores** | {authors} |") \
                        .replace("| **Ano** | |", f"| **Ano** | {year} |") \
                        .replace("| **Revista** | |", f"| **Revista** | {journal} |") \
                        .replace("| **DOI** | |", f"| **DOI** | {doi} |") \
                        .replace("| **Desenho do estudo** | |", f"| **Desenho do estudo** | {ext_data.get('study_design', 'Não identificado')} |") \
                        .replace("| **Nível de evidência** | |", f"| **Nível de evidência** | Nível {ext_data.get('evidence_level', 'Não identificado')} |") \
                        .replace("*Transcrição ou paráfrase fiel do objetivo declarado pelos autores.*", ext_data.get('study_objective', 'Não explicitado de forma curta.')) \
                        .replace("**População / Amostra:**", f"**População / Amostra:**\n{ext_data.get('population_profile', 'Não identificado')}") \
                        .replace("**Tecnologia(s) investigada(s):**", f"**Tecnologia(s) investigada(s):**\n{ext_data.get('technology_type', 'Não identificado')}") \
                        .replace("**Bases de dados / Fontes de dados:**", f"**Bases de dados / Fontes de dados:**\n{ext_data.get('data_sources', 'Não explicitado nas páginas selecionadas')}") \
                        .replace("**Período de análise:**", f"**Período de análise:**\n{ext_data.get('analysis_period', ext_data.get('intervention_duration', 'Não explicitado'))}") \
                        .replace("**Desfechos avaliados:**", f"**Desfechos avaliados:**\n{ext_data.get('evaluated_outcomes', 'Não identificado')}") \
                        .replace("*Síntese descritiva dos resultados reportados pelos autores. Sem interpretação pelo revisor.*", ext_data.get('key_findings', 'Não identificado')) \
                        .replace("*Limitações explicitamente reconhecidas no artigo original.*", ext_data.get('reported_limitations', 'Nenhuma limitação expressa no recorte analisado.')) \
                        .replace("**Categoria provisória:** [A, B, C, D ou Nova]", f"**Categoria provisória:** {ext_data.get('thematic_category', 'Outra')}") \
                        .replace("**Justificativa da classificação:**", f"**Justificativa da classificação:**\n{ext_data.get('thematic_justification', 'Não detalhado')}") \
                        .replace("*Como este estudo contribui para mapear as principais áreas e assuntos das pesquisas sobre exercício físico e tecnologias digitais?*", ext_data.get('relevance_to_question', 'Não analisado')) \
                        .replace("| **SHA-256 do PDF** | |", f"| **SHA-256 do PDF** | `{sha256_hash}` |") \
                        .replace("| **Data do fichamento** | |", f"| **Data do fichamento** | {time.strftime('%d-%m-%Y')} |") \
                        .replace("| **Status** | [DRAFT / REVISADO / APROVADO] |", f"| **Status** | `DRAFT` |")
    return formatted

def main():
    parser = argparse.ArgumentParser(description="Fase 2 — Extração Profunda Híbrida (XML/PDF)")
    parser.add_argument("--config", default="./criteria_config.yaml")
    parser.add_argument("--force-restart", action="store_true")
    parser.add_argument("--overnight", action="store_true", help="Pula erros sem bloqueio.")
    args = parser.parse_args()

    config = load_config(args.config)
    infrastructure = config.get("infrastructure", {})
    data_storage = infrastructure.get("data_storage", ".agent/data_storage")
    
    audit_base_dir = os.path.join(data_storage, "saida", "auditoria")
    auditor = ReviewAuditor(base_audit_dir=audit_base_dir)
    
    ollama_config = infrastructure.get("llm_router", {})
    base_url = ollama_config.get("ollama_url", "http://192.168.0.254:11434")
    api_url = f"{base_url.rstrip('/')}/api/generate"
    model = ollama_config.get("model_local", "qwen2.5-coder-vitalia:latest")
    options = ollama_config.get("options", {})
    
    is_overnight = getattr(args, 'overnight', False)
    timeout_duration = 0 if is_overnight else 120
    default_error_action = "2" if is_overnight else "1"
    
    global processed_this_session, current_file_name, total_files
    processed_this_session = 0
    current_file_name = ""
    total_files = 0

    terminal.setup_interrupt_handler(
        api_url=api_url, 
        model=model, 
        get_context_fn=lambda: {"idx": processed_this_session, "total": total_files, "current_article": current_file_name}
    )

    print(f"\n\033[94m🔍 Pré-flight check: Verificando conexão com Ollama em {base_url}...\033[0m")
    if not check_ollama_alive(api_url):
        print(f"\033[91m[ERRO] Servidor Ollama inativo ou inacessível no endpoint {base_url}.\033[0m")
        sys.exit(1)
    print(f"\033[92m✔ Ollama ativo! Iniciando (Overnight: {is_overnight}).\033[0m\n")

    prisma_log_path = os.path.join(data_storage, "saida", "PRISMA_LOG.csv")
    download_map_path = os.path.join(data_storage, "saida", "DOWNLOAD_MAP.csv")
    pdf_dir = os.path.join(data_storage, "fichamentos", "pdfs")
    xml_dir = os.path.join(data_storage, "fichamentos", "xmls")
    fichamentos_dir = os.path.join(data_storage, "fichamentos")
    template_path = os.path.join("inicio", "TEMPLATE_FICHAMENTO.md")
    extraction_csv_path = os.path.join(data_storage, "saida", "EXTRACTION_LOG.csv")
    
    os.makedirs(fichamentos_dir, exist_ok=True)
        
    articles_map = {}
    if os.path.exists(download_map_path):
        with open(download_map_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("Status") in ["Downloaded", "Local/Existing", "Local/XML", "Local/PDF", "EuropePMC/XML", "OpenAlex/PDF"]:
                    articles_map[row.get("Saved_Filename", "")] = row
                    
    if not articles_map and os.path.exists(prisma_log_path):
        with open(prisma_log_path, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                title = row.get("Title", "").strip()
                first_author = row.get("Authors", "SemAutor").split(",")[0].split(" ")[0].strip()
                first_author = re.sub(r"[^\w\s-]", "", first_author)
                first_author = re.sub(r"[-\s]+", "_", first_author).strip("_")
                clean_title = re.sub(r"[^\w\s-]", "", title)
                clean_title = re.sub(r"[-\s]+", "_", clean_title).strip("_")[:60]
                expected_pdf_name = f"{first_author}_{row.get('Year', '0000')}_{clean_title}.pdf"
                expected_xml_name = f"{first_author}_{row.get('Year', '0000')}_{clean_title}.xml"
                row["Original_Title"] = title
                articles_map[expected_pdf_name] = row
                articles_map[expected_xml_name] = row

    files_to_process = []
    xml_bases = set()
    
    if os.path.exists(xml_dir):
        for f in os.listdir(xml_dir):
            if f.endswith(".xml"):
                files_to_process.append((f, os.path.join(xml_dir, f), "xml"))
                xml_bases.add(os.path.splitext(f)[0])
                
    if os.path.exists(pdf_dir):
        for f in os.listdir(pdf_dir):
            if f.endswith(".pdf"):
                base_name = os.path.splitext(f)[0]
                if base_name not in xml_bases:
                    files_to_process.append((f, os.path.join(pdf_dir, f), "pdf"))

    total_files = len(files_to_process)
    if total_files == 0:
        print("\033[91m[ERRO] Nenhum arquivo PDF ou XML encontrado.\033[0m")
        sys.exit(1)
        
    terminal.print_section_header(f"FASE 2 — EXTRAÇÃO PROFUNDA ({total_files} Arquivo(s) para fichamento)")

    existing_extractions = {}
    if not args.force_restart and os.path.exists(extraction_csv_path):
        try:
            with open(extraction_csv_path, "r", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    existing_extractions[row.get("Filename", "")] = row
        except Exception:
            pass

    def update_extraction_csv(row_data: dict):
        fieldnames = [
            "Filename", "Original_Title", "DOI", "Study_Design", "Evidence_Level", 
            "Population_Profile", "Country", "Intervention_Duration", 
            "Technology_Type", "Key_Numerical_Results", "SHA256", "Model_Used", "Extraction_Date"
        ]
        all_rows = {}
        if os.path.exists(extraction_csv_path):
            try:
                with open(extraction_csv_path, "r", encoding="utf-8") as f:
                    for line in csv.DictReader(f):
                        all_rows[line["Filename"]] = line
            except Exception:
                pass
                
        all_rows[row_data["Filename"]] = row_data
        
        with open(extraction_csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for fn in sorted(all_rows.keys()):
                writer.writerow(all_rows[fn])

    success_count = 0
    skipped_count = 0
    errors_count = 0
    cb_state = {"consecutive_failures": 0}
    session_id = f"sess_f2_{time.strftime('%Y%m%d%H%M%S')}"

    try:
        for idx, (filename, filepath, ftype) in enumerate(files_to_process, 1):
            current_file_name = filename
            terminal.show_progress_bar(idx, total_files, success=success_count, skipped=skipped_count, erros=errors_count)
            
            fichamento_name = f"FICHAMENTO_{os.path.splitext(filename)[0]}.md"
            fichamento_save_path = os.path.join(fichamentos_dir, fichamento_name)
            
            if os.path.exists(fichamento_save_path) and filename in existing_extractions:
                skipped_count += 1
                continue
                
            sha256_hash = calculate_sha256(filepath)
            
            article_info = articles_map.get(filename, {})
            if not article_info:
                deduced_parts = os.path.splitext(filename)[0].split("_")
                deduced_title = " ".join(deduced_parts[2:]) if len(deduced_parts) > 2 else os.path.splitext(filename)[0]
                article_info = {
                    "Original_Title": deduced_title,
                    "Title": deduced_title,
                    "Authors": deduced_parts[0] if len(deduced_parts) > 0 else "Não identificado",
                    "Year": deduced_parts[1] if len(deduced_parts) > 1 else "Não identificado",
                    "DOI": "", "Journal": "Não identificado"
                }

            if ftype == "xml":
                file_text = extract_xml_text(filepath)
            else:
                file_text = extract_pdf_text(filepath)
                
            if not file_text.strip():
                print(f"\n\033[93m[AVISO] Texto do arquivo {filename} vazio ou ilegível.\033[0m")
                errors_count += 1
                continue
                
            prompt = f"""You are a scientific expert conducting an integrative literature review on Digital Technologies in Physical Exercise.
Analyze the provided scientific text excerpt and extract the structured details.

TEXT EXCERPT:
{file_text}

INSTRUCTIONS:
You MUST respond with a valid JSON object matching the exact structure below. 
Do not include markdown formatting like ```json or any extra text outside the JSON object. Keep descriptions concise, factual, and strictly grounded in the text. Do not hallucinate.

EXPECTED JSON FORMAT:
{{
  "_context_title": "{article_info.get('Original_Title', '').replace('"', "'")}",
  "_context_authors": "{article_info.get('Authors', '').replace('"', "'")}",
  "_context_year": "{article_info.get('Year', '').replace('"', "'")}",
  "study_design": "[Type of study design]",
  "evidence_level": "[Grade from 1 to 6]",
  "study_objective": "[A short, factual summary]",
  "population_profile": "[Detailed profile of participants]",
  "country": "[Country where the study was conducted]",
  "intervention_duration": "[Duration of the intervention]",
  "technology_type": "[Specific digital tool, wearable, app]",
  "data_sources": "[Databases or data collection methods]",
  "evaluated_outcomes": "[Main outcomes evaluated]",
  "key_findings": "[Significant numerical results]",
  "reported_limitations": "[Limitations explicitly recognized]",
  "thematic_category": "[Category]",
  "thematic_justification": "[Brief justification]",
  "relevance_to_question": "[Relevance]"
}}"""

            success = False
            while not success:
                try:
                    response = query_ollama(prompt, api_url, model, options, circuit_breaker_state=cb_state)
                    resp_text = response.get("response", "").strip()
                    resp_text = re.sub(r"^```(?:json)?|```$", "", resp_text, flags=re.MULTILINE).strip()
                    
                    extracted_json = json.loads(resp_text)
                    for k, v in list(extracted_json.items()):
                        if isinstance(v, list): extracted_json[k] = ", ".join(map(str, v))
                        elif isinstance(v, dict): extracted_json[k] = json.dumps(v, ensure_ascii=False)
                        elif v is None: extracted_json[k] = ""
                        else: extracted_json[k] = str(v)
                            
                    fichamento_md_content = format_fichamento(article_info, extracted_json, sha256_hash, template_path)
                    
                    with open(fichamento_save_path, "w", encoding="utf-8") as f:
                        f.write(fichamento_md_content)
                        
                    audit_payload = {
                        "timestamp": time.strftime("%d-%m-%Y %H:%M:%S(GMT-04:00)"),
                        "model": model,
                        "article_metadata": article_info,
                        "full_prompt": prompt,
                        "raw_llm_response": resp_text,
                        "parsed_data": extracted_json
                    }
                    auditor.save_inference_shard(phase=2, item_id=filename, payload=audit_payload)
                    
                    csv_row = {
                        "Filename": filename,
                        "Original_Title": article_info.get("Original_Title", ""),
                        "DOI": article_info.get("DOI", ""),
                        "Study_Design": extracted_json.get("study_design", "Não especificado"),
                        "Evidence_Level": extracted_json.get("evidence_level", "Não especificado"),
                        "Population_Profile": extracted_json.get("population_profile", "Não especificado"),
                        "Country": extracted_json.get("country", "Não especificado"),
                        "Intervention_Duration": extracted_json.get("intervention_duration", "Não especificado"),
                        "Technology_Type": extracted_json.get("technology_type", "Não especificado"),
                        "Key_Numerical_Results": extracted_json.get("key_findings", "Não especificado"),
                        "SHA256": sha256_hash,
                        "Model_Used": model,
                        "Extraction_Date": time.strftime("%d-%m-%Y")
                    }
                    update_extraction_csv(csv_row)
                    
                    success = True
                    success_count += 1
                    processed_this_session += 1
                    
                except Exception as e:
                    choice, is_timeout = terminal.handle_error_menu(
                        article_info.get("Original_Title", filename), str(e), default_action=default_error_action, timeout=timeout_duration, phase_label="FASE 2"
                    )

                    if choice == "1":
                        continue
                            
                    if choice == "2":
                        csv_row = {
                            "Filename": filename,
                            "Original_Title": article_info.get("Original_Title", ""),
                            "DOI": article_info.get("DOI", ""),
                            "Study_Design": "Falha na extração",
                            "Evidence_Level": "Erro",
                            "Population_Profile": "Erro",
                            "Country": "Erro",
                            "Intervention_Duration": "Erro",
                            "Technology_Type": "Erro",
                            "Key_Numerical_Results": f"Erro de processamento: {str(e)[:150]}",
                            "SHA256": sha256_hash,
                            "Model_Used": model,
                            "Extraction_Date": time.strftime("%d-%m-%Y")
                        }
                        update_extraction_csv(csv_row)
                        errors_count += 1
                        success = True
                    elif choice == "3":
                        print("\nProcessamento pausado pelo usuário.")
                        return

            if processed_this_session > 0 and processed_this_session % 10 == 0:
                unload_model(api_url, model)

    finally:
        print("\n\nLiberando recursos de VRAM do Ollama...")
        unload_model(api_url, model)
        
        terminal.print_section_header("SESSÃO DE EXTRAÇÃO DA FASE 2 FINALIZADA")
        report_path = auditor.generate_session_summary(
            session_id=session_id, 
            stats={"Processados": success_count, "Pulados": skipped_count, "Erros": errors_count},
            config_hash="N/A", 
            model=model, 
            phase_label="Fase 2 - Extração (Híbrida)"
        )
        print(f"Relatório da sessão salvo em: {report_path}")

if __name__ == "__main__":
    main()
