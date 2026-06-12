import os
import json
import time
from datetime import datetime, timedelta
from scripts.review_pipeline.core.state_manager import StateManager

def test_state_manager_reset_rule(tmp_path):
    base_dir = str(tmp_path)
    mgr = StateManager(base_dir=base_dir)
    history_file = mgr.phases_history_file
    
    # Criar histórico fake
    now = datetime.now()
    old_date = now - timedelta(days=2) # Mais de 24h
    recent_date = now - timedelta(hours=5) # Menos de 24h
    
    history_data = {
        "fase1_screening": {
            "last_updated": old_date.strftime('%d-%m-%Y %H:%M:%S(GMT-04:00)')
        },
        "fase2_extraction": {
            "last_updated": recent_date.strftime('%d-%m-%Y %H:%M:%S(GMT-04:00)')
        }
    }
    with open(history_file, "w") as f:
        json.dump(history_data, f)
        
    # Reset na fase antiga (deve sumir)
    mgr.reset_phase_history("fase1_screening")
    
    # Reset na fase nova (deve manter)
    mgr.reset_phase_history("fase2_extraction")
    
    with open(history_file, "r") as f:
        final_history = json.load(f)
        
    assert "fase1_screening" not in final_history, "Fase antiga deveria ter sido apagada."
    assert "fase2_extraction" in final_history, "Fase recente (<24h) NÃO deveria ter sido apagada."
    print("Teste StateManager: Reset Rule passou!")
