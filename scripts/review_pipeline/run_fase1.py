# scripts/review_pipeline/run_fase1.py | Última Atualização: 21-05-2026 11:31:00(GMT-04:00)
"""
run_fase1.py — Orquestrador do Processamento LLM de Triagem (Fase 1)

Uso:
    python run_fase1.py [--config ./criteria_config.yaml] [--overnight] [--force-restart]
"""

import argparse
import csv
import os
import sys
import time
import json

# Garante que o pacote core seja encontrado
sys.path.insert(0, os.path.dirname(__file__))

from core.config_manager import load_config
from core.ollama_client import query_ollama, check_ollama_alive, unload_model
from core.prompt_engine import build_prompt
from core.prisma_logger import PrismaLogger
from core import terminal

def run_screening(config: dict, config_path: str, args: argparse.Namespace):
    # 1. Configurar caminhos e parâmetros
    paths = config.get("paths", {})
    prisma_log_path = os.path.join(paths.get("output_prisma", "saida"), "PRISMA_LOG.csv")
    shards_dir = os.path.join(paths.get("output_prisma", "saida"), "shards")
    
    ollama_cfg = config.get("ollama", {})
    base_url = ollama_cfg.get("base_url", "http://localhost:11434")
    api_url = f"{base_url.rstrip('/')}/api/generate"
    model = ollama_cfg.get("model", "llama3.2:3b")
    options = ollama_cfg.get("options", {})
    
    prompt_config = config.get("prompt_configuration", {})
    
    # Define parâmetros do overnight e timeout
    is_overnight = getattr(args, 'overnight', False)
    timeout_duration = 0 if is_overnight else 120
    default_error_action = "2" if is_overnight else "1"
    
    # 2. Inicializar loggers
    logger = PrismaLogger(prisma_log_path, shards_dir)
    
    # Variáveis globais para o handler de interrupção
    global processed_count, current_article_title, total_to_process
    processed_count = 0
    current_article_title = ""
    total_to_process = 0
    
    # Instalar handler de Ctrl+C unificado
    terminal.setup_interrupt_handler(
        api_url=api_url, 
        model=model, 
        log_fn=logger.write_execution_log,
        get_context_fn=lambda: {"idx": processed_count, "total": total_to_process, "current_article": current_article_title}
    )

    # Pre-flight check do Ollama
    print("\nVerificando conexão com Ollama...")
    if not check_ollama_alive(api_url):
        print(f"\033[91m[ERRO] Ollama não está rodando no endpoint: {api_url}\033[0m")
        sys.exit(1)
    print(f"\033[92mOllama ativo! Iniciando triagem (Overnight: {is_overnight})...\033[0m")
    
    # 3. Ler artigos que precisam de triagem
    if not os.path.exists(prisma_log_path):
        print(f"\033[91m[ERRO] PRISMA_LOG.csv não encontrado em {prisma_log_path}.\033[0m")
        sys.exit(1)
        
    articles_to_process = []
    # Conta totais do PRISMA e processados anteriormente para banner de retomada
    stats = logger.get_stats()
    total_in_prisma = stats["total"]
    already_done = total_in_prisma - stats["aguardando"]
    
    with open(prisma_log_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("Status", "").strip() == "Aguardando Fase 1" or args.force_restart:
                articles_to_process.append(row)
                
    total_to_process = len(articles_to_process)
    if total_to_process == 0:
        print("\n\033[92m✔ Nenhum artigo aguardando triagem no PRISMA_LOG.csv!\033[0m")
        sys.exit(0)
        
    terminal.show_session_resume_banner(already_done, total_in_prisma, "FASE 1 - TRIAGEM")
    
    # Circuit Breaker state
    cb_state = {"consecutive_failures": 0}
    
    # 4. Loop de Processamento
    session_id = f"sess_f1_{time.strftime('%Y%m%d%H%M%S')}"
    
    try:
        for idx, article in enumerate(articles_to_process, 1):
            title = article.get("Title", "").strip()
            abstract = article.get("Abstract", "").strip()
            current_article_title = title
            
            terminal.show_article_header(idx, total_to_process, title)
            
            prompt = build_prompt(title, abstract, prompt_config)
            success = False
            
            while not success:
                try:
                    response_json = query_ollama(
                        prompt=prompt,
                        api_url=api_url,
                        model=model,
                        options=options,
                        log_file_path=logger.log_file_path,
                        circuit_breaker_state=cb_state
                    )
                    
                    raw_text = response_json.get("response", "").strip()
                    if raw_text.startswith("```json"):
                        raw_text = raw_text.split("```json", 1)[1]
                    if "```" in raw_text:
                        raw_text = raw_text.split("```", 1)[0]
                    raw_text = raw_text.strip()
                    
                    parsed_res = json.loads(raw_text)
                    decision = parsed_res.get("final_decision", "EXCLUIR").strip().upper()
                    
                    status_log = "Incluido Fase 1" if decision == "INCLUIR" else "Excluido Fase 1"
                    reason = parsed_res.get("reasoning", "Sem justificativa")
                    
                    terminal.show_article_decision(status_log, reason)
                    
                    logger.save_decision(
                        article_title=title, 
                        decision=status_log, 
                        exclusion_reason=reason, 
                        raw_response=raw_text, 
                        article_data=article, 
                        full_prompt=prompt, 
                        model_name=model
                    )
                    success = True
                    processed_count += 1
                    
                    current_stats = logger.get_stats()
                    terminal.show_progress_bar(processed_count, total_to_process, **current_stats)
                    
                except Exception as e:
                    choice, is_timeout = terminal.handle_error_menu(
                        title, str(e), default_action=default_error_action, timeout=timeout_duration, phase_label="FASE 1"
                    )
                    
                    if choice == "1":
                        continue
                    elif choice == "2":
                        logger.update_csv_row(title, f"Erro: {str(e)[:150]}", "Falha de processamento")
                        success = True
                        processed_count += 1
                    elif choice == "3":
                        print("\nProcessamento pausado pelo usuário.")
                        return
                        
    finally:
        print("\n\nLiberando recursos de VRAM do Ollama...")
        unload_model(api_url, model)
        
        final_stats = logger.get_stats()
        terminal.print_section_header("TRIAGEM DA FASE 1 CONCLUÍDA")
        
        report_path = logger.auditor.generate_session_summary(
            session_id=session_id, 
            stats={"Processados": processed_count, "Incluídos": final_stats['incluidos'], "Excluídos": final_stats['excluidos']},
            config_hash="N/A", 
            model=model, 
            phase_label="Fase 1 - Screening"
        )
        print(f"Relatório da sessão salvo em: {report_path}")

def main():
    parser = argparse.ArgumentParser(description="Fase 1 Screening via Ollama")
    parser.add_argument("--config", default="./criteria_config.yaml")
    parser.add_argument("--overnight", action="store_true", help="Modo não interativo. Pula erros automaticamente.")
    parser.add_argument("--force-restart", action="store_true", help="Reinicia processamento")
    args = parser.parse_args()
    
    config = load_config(args.config)
    run_screening(config, args.config, args)

if __name__ == "__main__":
    main()
