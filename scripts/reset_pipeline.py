import argparse
import os
import shutil
import csv
import json
import time
import subprocess
from datetime import datetime
import sys

# Adiciona a raiz do projeto no PYTHONPATH para que 'scripts.X' funcione
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

def print_warning(msg):
    print(f"\033[91m\033[1m[ATENÇÃO]\033[0m {msg}")

def print_info(msg):
    print(f"\033[94m[INFO]\033[0m {msg}")

def print_success(msg):
    print(f"\033[92m[SUCESSO]\033[0m {msg}")

def create_backup():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"backup_revisao_{timestamp}"
    backup_path = os.path.join(".agent", "data_storage", backup_filename)
    
    print_info(f"Criando backup em {backup_path}.zip ...")
    
    # Precisamos zipar a raiz inteira ignorando .git e .venv
    # Para simplificar e garantir portabilidade, usamos o comando zip via subprocess
    try:
        subprocess.run(
            ["zip", "-r", f"{backup_path}.zip", ".", "-x", "*.git*", "*.venv*", "*/__pycache__/*"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )
        print_success("Backup criado com sucesso.")
        return f"{backup_path}.zip"
    except Exception as e:
        print_warning(f"Falha ao criar backup via comando zip: {e}")
        return None

def push_to_cloud(backup_file):
    print_info("Iniciando push para a nuvem...")
    try:
        subprocess.run(["git", "add", backup_file], check=True)
        subprocess.run(["git", "commit", "-m", f"chore: Backup pré-purga {os.path.basename(backup_file)}"], check=True)
        subprocess.run(["git", "push"], check=True)
        print_success("Backup enviado para a nuvem com sucesso!")
        return True
    except subprocess.CalledProcessError as e:
        print_warning(f"Falha ao fazer push para a nuvem: {e}")
        return False

def wipe_data_storage():
    data_storage_path = os.path.join(".agent", "data_storage")
    if os.path.exists(data_storage_path):
        shutil.rmtree(data_storage_path)
    os.makedirs(data_storage_path, exist_ok=True)
    os.makedirs(os.path.join(data_storage_path, "saida", "auditoria"), exist_ok=True)
    os.makedirs(os.path.join(data_storage_path, "fichamentos", "pdfs"), exist_ok=True)
    os.makedirs(os.path.join(data_storage_path, "fichamentos", "xmls"), exist_ok=True)

def reset_dashboard_state():
    data_storage_path = os.path.join(".agent", "data_storage")
    
    # 1. Limpar ACTIVE_STATE.json
    active_state_path = os.path.join(data_storage_path, "ACTIVE_STATE.json")
    empty_state = {
        "phase_id": "idle",
        "phase_dir": "idle",
        "description": "Aguardando Ingestão...",
        "total_target": 0,
        "total_processed": 0,
        "total_success": 0,
        "total_fails": 0,
        "total_excluded": 0,
        "total_skipped": 0,
        "current_task": "Aguardando Início",
        "status": "IDLE",
        "start_time": "",
        "start_time_ts": 0,
        "last_updated": time.strftime("%d-%m-%Y %H:%M:%S") + "(GMT-04:00)"
    }
    with open(active_state_path, "w", encoding="utf-8") as f:
        json.dump(empty_state, f, indent=2, ensure_ascii=False)
        
    # 2. Limpar PHASES_HISTORY.json
    history_path = os.path.join(data_storage_path, "PHASES_HISTORY.json")
    with open(history_path, "w", encoding="utf-8") as f:
        json.dump({}, f, indent=2, ensure_ascii=False)

    # 3. Invocar gerador de dashboards para injetar os zeros
    try:
        from scripts.generate_live_dashboard import build_dashboard as build_live_dashboard
        from scripts.generate_progress import generate_dashboard as build_progress_dashboard
        build_live_dashboard()
        build_progress_dashboard()
        print_success("Dashboards resetados e atualizados.")
    except Exception as e:
        print_warning(f"Não foi possível atualizar os dashboards automaticamente: {e}")

def update_prisma_log_status(target_statuses, new_status):
    prisma_log_path = os.path.join(".agent", "data_storage", "saida", "PRISMA_LOG_MASTER.csv")
    if not os.path.exists(prisma_log_path):
        return

    updated_rows = []
    modifications = 0
    with open(prisma_log_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            if row.get("Status") in target_statuses:
                row["Status"] = new_status
                modifications += 1
            updated_rows.append(row)
            
    if modifications > 0:
        with open(prisma_log_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(updated_rows)
        print_info(f"PRISMA_LOG_MASTER: {modifications} registros revertidos para '{new_status}'.")

def delete_directory(path):
    if os.path.exists(path):
        shutil.rmtree(path)
        print_info(f"Deletado: {path}")

def delete_file(path):
    if os.path.exists(path):
        os.remove(path)
        print_info(f"Deletado: {path}")

def main():
    parser = argparse.ArgumentParser(description="Script central de reset e limpeza do pipeline.")
    parser.add_argument("--fase0", action="store_true", help="Reseta Fase 0 e todas as subsequentes.")
    parser.add_argument("--fase1", action="store_true", help="Reseta Fase 1 e subsequentes.")
    parser.add_argument("--fase2a", action="store_true", help="Reseta Fase 2a (Download) e subsequentes.")
    parser.add_argument("--fase2b", action="store_true", help="Reseta Fase 2b (Extração) e subsequentes.")
    parser.add_argument("--fase3", action="store_true", help="Reseta Fase 3 (Síntese).")
    parser.add_argument("--all", action="store_true", help="HARD WIPE: Apaga absolutamente tudo, voltando o sistema à estaca zero.")
    
    args = parser.parse_args()

    # Lógica de Cascata
    if args.all:
        pass # Trata separado
    else:
        if args.fase0: args.fase1 = True
        if args.fase1: args.fase2a = True
        if args.fase2a: args.fase2b = True
        if args.fase2b: args.fase3 = True

    if not any([args.all, args.fase0, args.fase1, args.fase2a, args.fase2b, args.fase3]):
        parser.print_help()
        sys.exit(0)

    # ------------------- HARD WIPE (--all) -------------------
    if args.all:
        print_warning("!!! ATENÇÃO: VOCÊ ESCOLHEU A OPÇÃO --all !!!")
        print_warning("Isso fará um HARD WIPE. A pasta data_storage inteira será DESTRUÍDA,")
        print_warning("incluindo configs de fontes (sources_config.yaml) e critérios (criteria_config.yaml)!")
        
        resp = input("Deseja criar um arquivo de backup ZIP contendo o estado atual? (s/N): ").strip().lower()
        if resp == 's':
            backup_file = create_backup()
            if backup_file:
                print_warning(f"Backup criado em {backup_file}.")
                print_warning("IMPORTANTE: Como o backup foi salvo dentro de data_storage, ele SERÁ APAGADO na próxima etapa")
                print_warning("a menos que você faça o push dele para a nuvem AGORA.")
                
                resp_push = input("Deseja fazer push do backup para o repositório git remoto agora? (s/N): ").strip().lower()
                if resp_push == 's':
                    push_to_cloud(backup_file)
                else:
                    print_warning("Push cancelado. O backup local será DESTRUÍDO permanentemente.")
        
        final_resp = input("TEM CERTEZA ABSOLUTA QUE DESEJA APAGAR TUDO? (Digite 'DESTRUIR' para confirmar): ").strip()
        if final_resp != "DESTRUIR":
            print_info("Operação cancelada pelo usuário.")
            sys.exit(0)
            
        print_info("Iniciando HARD WIPE...")
        wipe_data_storage()
        delete_file("criteria_config.yaml")
        delete_file("sources_config.yaml")
        delete_file(os.path.join("scripts", "review_pipeline", "sources_config.yaml"))
        reset_dashboard_state()
        print_success("O sistema foi resetado à estaca zero absoluto.")
        sys.exit(0)

    # ------------------- CASCATA PARCIAL -------------------
    base_data = os.path.join(".agent", "data_storage")
    saida = os.path.join(base_data, "saida")
    auditoria = os.path.join(saida, "auditoria")
    
    if args.fase3:
        print_info("Limpando Fase 3...")
        delete_directory(os.path.join(auditoria, "fase3_synthesis"))
        # Deletar arquivos de sintese no data_storage
        for file in os.listdir(saida) if os.path.exists(saida) else []:
            if file.startswith("SYNTHESIS_") and file.endswith(".md"):
                delete_file(os.path.join(saida, file))
        
    if args.fase2b:
        print_info("Limpando Fase 2b (Extração)...")
        delete_directory(os.path.join(auditoria, "fase2b_extraction"))
        delete_directory(os.path.join(auditoria, "fase2_extraction")) # old name fallback
        delete_directory(os.path.join(base_data, "fichamentos"))
        delete_file(os.path.join(saida, "EXTRACTION_LOG.csv"))
        update_prisma_log_status(["Extração Concluída"], "Download Concluído")
        
    if args.fase2a:
        print_info("Limpando Fase 2a (Download)...")
        delete_directory(os.path.join(auditoria, "fase2a_download"))
        delete_file(os.path.join(saida, "DOWNLOAD_MAP.csv"))
        delete_directory(os.path.join(base_data, "fichamentos", "pdfs"))
        delete_directory(os.path.join(base_data, "fichamentos", "xmls"))
        update_prisma_log_status(["Download Concluído", "Download Falhou"], "Incluído")
        
    if args.fase1:
        print_info("Limpando Fase 1 e 1.5 (Triagem/Auditoria)...")
        delete_directory(os.path.join(auditoria, "fase1_screening"))
        delete_directory(os.path.join(auditoria, "fase1_5_auditoria"))
        update_prisma_log_status(["Incluído", "Excluído (Critérios)", "Excluído (LLM)"], "Aguardando Triagem")

    if args.fase0:
        print_info("Limpando Fase 0 (Ingestão)...")
        delete_directory(os.path.join(auditoria, "fase0_ingestion"))
        delete_file(os.path.join(saida, "PRISMA_LOG_MASTER.csv"))

    # Finalmente, reseta estado visual base
    reset_dashboard_state()
    print_success("Limpeza em cascata concluída!")

if __name__ == "__main__":
    main()
