import os
import csv
import json
import yaml
import requests
import argparse

def carregar_config():
    config_path = "criteria_config.yaml"
    if not os.path.exists(config_path):
        config_path = "inicio/criteria_config.template.yaml"
    
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def detectar_colunas(reader):
    """
    Tenta detectar as colunas de Título e Resumo a partir do cabeçalho
    (suporta padrões do Scopus, WoS, PubMed, etc.)
    """
    headers = reader.fieldnames
    title_col = None
    abstract_col = None
    
    title_aliases = ["Title", "Article Title", "Document Title"]
    abstract_aliases = ["Abstract", "Summary"]
    
    for h in headers:
        for alias in title_aliases:
            if alias.lower() in h.lower():
                title_col = h
        for alias in abstract_aliases:
            if alias.lower() in h.lower():
                abstract_col = h
                
    return title_col, abstract_col

def avaliar_artigo(titulo, abstract, config):
    ollama_url = config.get("ollama", {}).get("base_url", "http://192.168.0.254:11434")
    model = config.get("ollama", {}).get("model", "llama3.2:3b")
    
    incl_criteria = "\n".join([f"- {c}" for c in config.get("criteria", {}).get("inclusion", ["O estudo é relevante."])])
    excl_criteria = "\n".join([f"- {c}" for c in config.get("criteria", {}).get("exclusion", ["O estudo é irrelevante."])])
    
    prompt = f"""You are an expert scientific researcher conducting an integrative review.
    
Based on the following Title and Abstract, evaluate if the article should be INCLUDED or EXCLUDED.

**Inclusion Criteria:**
{incl_criteria}

**Exclusion Criteria:**
{excl_criteria}

**Article:**
Title: {titulo}
Abstract: {abstract}

Respond ONLY with a valid JSON object in the following format. Do NOT add markdown, explanations, or text outside the JSON.
{{
    "include": true or false,
    "confidence": "High", "Medium", or "Low",
    "reason": "Brief justification citing specific criteria",
    "key_pico_elements": "Identified PICO elements (Population, Intervention, Comparison, Outcome) or None",
    "methodology": "Study design (e.g. RCT, Review, Observational) or Unknown"
}}
"""
    try:
        response = requests.post(
            f"{ollama_url}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "format": "json"
            },
            timeout=60
        )
        response.raise_for_status()
        result = response.json()
        return json.loads(result["response"])
    except Exception as e:
        return {"error": str(e)}

def main():
    parser = argparse.ArgumentParser(description="Piloto de triagem de artigos com Ollama Local")
    parser.add_argument("input_csv", help="Caminho para o CSV bruto de entrada")
    parser.add_argument("--limit", type=int, default=10, help="Número de artigos a processar no piloto")
    args = parser.parse_args()

    config = carregar_config()
    print(f"[*] Configuração carregada. Modelo: {config.get('ollama', {}).get('model')} em {config.get('ollama', {}).get('base_url')}")
    
    if not os.path.exists(args.input_csv):
        print(f"[!] Erro: Arquivo {args.input_csv} não encontrado.")
        return

    saida_csv = "saida/pilot_results.csv"
    os.makedirs(os.path.dirname(saida_csv), exist_ok=True)

    with open(args.input_csv, "r", encoding="utf-8") as f_in, \
         open(saida_csv, "w", encoding="utf-8", newline="") as f_out:
        
        reader = csv.DictReader(f_in)
        title_col, abstract_col = detectar_colunas(reader)
        
        if not title_col or not abstract_col:
            print(f"[!] Erro: Não foi possível detectar as colunas 'Title' ou 'Abstract' automaticamente.")
            print(f"Colunas disponíveis: {reader.fieldnames}")
            return
            
        print(f"[*] Colunas detectadas -> Título: '{title_col}', Resumo: '{abstract_col}'")
        
        fieldnames = [title_col, "include", "confidence", "reason", "key_pico_elements", "methodology", "error"]
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()

        count = 0
        for row in reader:
            if count >= args.limit:
                break
                
            titulo = row.get(title_col, "")
            abstract = row.get(abstract_col, "")
            
            if not abstract or len(abstract) < 50:
                print(f"[-] Pulando '{titulo[:30]}...' (Sem abstract)")
                continue
                
            print(f"\n[{count+1}/{args.limit}] Avaliando: {titulo[:50]}...")
            
            resultado = avaliar_artigo(titulo, abstract, config)
            
            linha_saida = {
                title_col: titulo,
                "include": resultado.get("include", ""),
                "confidence": resultado.get("confidence", ""),
                "reason": resultado.get("reason", ""),
                "key_pico_elements": resultado.get("key_pico_elements", ""),
                "methodology": resultado.get("methodology", ""),
                "error": resultado.get("error", "")
            }
            writer.writerow(linha_saida)
            count += 1
            
            # Print rápido do resultado
            inc = "✅ SIM" if resultado.get("include") else "❌ NÃO"
            print(f"    Decisão: {inc} | Confiança: {resultado.get('confidence')} | Motivo: {resultado.get('reason')}")
            
    print(f"\n[*] Piloto concluído. Resultados salvos em {saida_csv}")

if __name__ == "__main__":
    main()
