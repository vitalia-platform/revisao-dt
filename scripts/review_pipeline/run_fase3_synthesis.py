#!/usr/bin/env python3
# scripts/review_pipeline/run_fase3_synthesis.py

import argparse
import json
import os
import sys
import time
from dotenv import load_dotenv

load_dotenv()

# Garante que o pacote core seja encontrado
sys.path.insert(0, os.path.dirname(__file__))

import re
from core.config_manager import load_config
from core.lib_llm_router import LLMRouter
from core.state_manager import StateManager
from core.auditor import ReviewAuditor
from core import terminal

root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

def update_dashboards():
    try:
        from scripts.generate_live_dashboard import build_dashboard as build_live_dashboard
        from scripts.generate_progress import generate_dashboard as build_progress_dashboard
        build_live_dashboard()
        build_progress_dashboard()
    except Exception as e:
        print(f"Erro ao atualizar dashboard: {e}")

def main():
    parser = argparse.ArgumentParser(description="Motor de Síntese Temática (Fase 3)")
    parser.add_argument("--config", default="criteria_config.yaml", help="Caminho para criteria_config.yaml")
    args = parser.parse_args()

    terminal.print_section_header("FASE 3 — SÍNTESE TEMÁTICA CRUZADA")
    config = load_config(args.config)
    project_title = config.get("project", {}).get("title", "Revisão")
    pico_question = config.get("project", {}).get("pico_question", "")
    
    data_storage = config.get("infrastructure", {}).get("data_storage", ".agent/data_storage")
    fichamentos_dir = os.path.join(data_storage, "fichamentos")
    saida_dir = os.path.join(data_storage, "saida", "fase3_sintese")
    os.makedirs(saida_dir, exist_ok=True)
    
    state_mgr = StateManager(on_event_callback=update_dashboards)
    
    # 1. Coleta os fichamentos
    if not os.path.exists(fichamentos_dir):
        terminal.print_error(f"Diretório {fichamentos_dir} não encontrado.")
        sys.exit(1)
        
    arquivos = [f for f in os.listdir(fichamentos_dir) if f.endswith('.md') or f.endswith('.json')]
    total_fichamentos = len(arquivos)
    
    if total_fichamentos == 0:
        terminal.print_warning("Nenhum fichamento encontrado para síntese.")
        sys.exit(0)
        
    state_mgr.set_active_state("fase3_synthesis", "Fase 3: Síntese Temática", total_target=1, current_task="Carregando extrações...")
    
    terminal.print_step(f"Carregando {total_fichamentos} fichamentos...")
    
    corpus_text = ""
    for idx, arq in enumerate(arquivos):
        path = os.path.join(fichamentos_dir, arq)
        try:
            with open(path, "r", encoding="utf-8") as f:
                conteudo = f.read()
                corpus_text += f"\n\n--- INÍCIO DO ARTIGO {idx+1}: {arq} ---\n{conteudo}\n--- FIM DO ARTIGO {idx+1} ---\n"
        except Exception as e:
            terminal.print_error(f"Erro ao ler {arq}: {e}")
            
    # 2. Configura a Sintese no LLM
    terminal.print_step("Invocando LLM em Nuvem/Local (Long Context) para Síntese Indutiva...")
    state_mgr.update_state(current_task="Redigindo Draft Acadêmico...")
    
    llm = LLMRouter(args.config)
    
    prompt = f"""Você é o Pesquisador Chefe conduzindo a Fase 3 (Síntese) de uma Revisão Integrativa.
Seu objetivo é ler a extração de dados de {total_fichamentos} artigos científicos e redigir o draft final acadêmico.

PROJETO: {project_title}
PERGUNTA NORTEADORA: {pico_question}

O draft deve conter:
1. Uma introdução consolidando o panorama dos estudos.
2. Análise Temática (extraia indutivamente categorias emergentes a partir dos métodos, ferramentas de design e resultados relatados).
3. Discussão cruzada evidenciando consensos e lacunas (gaps) na literatura.
4. Conclusão voltada para a prática (projetos de extensão, saúde, etc.).

Aqui estão os fichamentos extraídos dos artigos:
{corpus_text}

INSTRUÇÃO CRÍTICA DE FORMATAÇÃO:
Você DEVE estruturar sua resposta OBRIGATORIAMENTE usando as tags XML <reasoning> e <draft>.
1. Primeiro, pense alto sobre os temas que encontrou, justifique os agrupamentos e planeje a estrutura da síntese dentro das tags <reasoning> ... </reasoning>.
2. Depois, escreva o texto acadêmico final impecável em Markdown, em Português do Brasil, dentro das tags <draft> ... </draft>.
3. META-VERIFICAÇÃO: Imediatamente antes de finalizar sua resposta, faça uma verificação cruzada para garantir que você não esqueceu de incluir a tag de fechamento </draft> no final do texto.

EXEMPLO DE SAÍDA ESPERADA:
<reasoning>
Notei que 15 artigos focam em Gamificação e 10 em Saúde Coletiva... Vou dividir a análise temática em 3 blocos. A lacuna principal identificada foi X...
</reasoning>
<draft>
# Introdução
A literatura sobre Design Thinking tem se expandido...
(restante do texto formatado em Markdown com citações)
</draft>
"""

    start_time = time.time()
    try:
        # Chama o LLM usando a infraestrutura unificada que agora extrai o num_ctx diretamente do criteria_config.yaml
        result, backend_used, model_used, t_dict = llm.generate(
            "fase3_synthesis", 
            prompt, 
            json_format=False
        )
        
        lat = time.time() - start_time
        terminal.print_success(f"Síntese concluída em {lat:.1f}s via {backend_used} ({model_used}).")
        
        # Parseando as tags XML com fallback resiliente
        if isinstance(result, dict):
            if "error" in result:
                raise Exception(f"Erro do LLM: {result['error']}")
            else:
                result = str(result)
                
        reasoning = ""
        draft_final = result
        
        reasoning_match = re.search(r"<reasoning>(.*?)</reasoning>", result, re.DOTALL | re.IGNORECASE)
        draft_match = re.search(r"<draft>(.*?)</draft>", result, re.DOTALL | re.IGNORECASE)
        
        if reasoning_match:
            reasoning = reasoning_match.group(1).strip()
            
        if draft_match:
            draft_final = draft_match.group(1).strip()
        else:
            terminal.print_warning("Tag <draft> não detectada pelo Regex! Acionando fallback de segurança (usando texto cru).")
            if reasoning_match:
                # Remove apenas o raciocínio para não sujar o texto
                draft_final = result.replace(reasoning_match.group(0), "").strip()

        # Auditoria: Salva TUDO para rastreabilidade máxima
        auditor = ReviewAuditor()
        audit_payload = {
            "prompt": prompt,
            "raw_response": result,
            "parsed_reasoning": reasoning,
            "parsed_draft": draft_final,
            "metrics": {
                "latency_seconds": round(lat, 2),
                "backend": backend_used,
                "model": model_used
            }
        }
        auditor.save_inference_shard(phase=3, item_id="sintese_tematica_final", payload=audit_payload)
        
        output_file = os.path.join(saida_dir, "draft_final.md")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(draft_final)
            
        terminal.print_success(f"Rascunho salvo em: {output_file}")
        state_mgr.update_state(processed=1, success=1)
        
    except Exception as e:
        terminal.print_error(f"Falha na síntese via nuvem: {e}")
        state_mgr.update_state(processed=1, fails=1)
        
    state_mgr.update_state(finish=True)
    terminal.print_section_header("FIM DA REVISÃO SISTEMÁTICA")

if __name__ == "__main__":
    main()
