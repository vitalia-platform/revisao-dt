import time
import sys
import os
import random
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.review_pipeline.core.state_manager import StateManager
from scripts.review_pipeline.core.auditor import ReviewAuditor
from scripts.generate_live_dashboard import build_dashboard

def main():
    print("Iniciando Mock E2E Pipeline Runner (Stress Test)")
    
    # 1. Configurar Base Limpa
    data_storage = ".agent/data_storage"
    audit_base_dir = os.path.join(data_storage, "saida", "auditoria")
    
    auditor = ReviewAuditor(base_output_dir=audit_base_dir)
    state_mgr = StateManager(on_event_callback=build_dashboard, base_dir=data_storage)
    
    # Purga da Fase mock
    target_dir = os.path.join(audit_base_dir, "fase2b_extraction")
    if os.path.exists(target_dir):
        shutil.rmtree(target_dir)
    os.makedirs(target_dir)
    
    total = 50
    state_mgr.set_active_state("fase2b_extraction", "Fase MOCK: E2E Test", total, current_task="Iniciando teste de estresse...")
    
    print(f"Mock iniciado. Verifique o LIVE_PROGRESS.html no navegador.")
    print("Simulando extração de 50 itens com latência variável...\n")
    
    try:
        for idx in range(1, total + 1):
            title = f"Artigo Simulado {idx}"
            state_mgr.update_state(current_task=f"Fichando: {title}...")
            
            # Simula latência variável (1 a 3 segundos)
            lat = random.uniform(1.0, 3.0)
            time.sleep(lat)
            
            # 80% sucesso, 10% falha, 10% skip
            r = random.random()
            if r < 0.1:
                state_mgr.update_state(skipped=1)
                print(f"[{idx}/{total}] SKIPPED (0s)")
                continue
                
            payload = {
                "article_metadata": {"Title": title},
                "inference_metrics": {"latency_seconds": lat, "model": "mock-llama"},
                "status": "SUCCESS" if r < 0.9 else "FAIL"
            }
            
            auditor.save_inference_shard(phase=2, item_id=f"mock_artigo_{idx}", payload=payload)
            
            if r < 0.9:
                state_mgr.update_state(processed=1, success=1)
                print(f"[{idx}/{total}] SUCCESS ({lat:.2f}s)")
            else:
                state_mgr.update_state(processed=1, fails=1)
                print(f"[{idx}/{total}] FAIL ({lat:.2f}s)")
                
    except KeyboardInterrupt:
        print("\nTeste abortado pelo usuário.")
        sys.exit(0)
        
    state_mgr.update_state(current_task="Finalizado", finish=True)
    print("\nTeste Concluído.")

if __name__ == "__main__":
    main()
