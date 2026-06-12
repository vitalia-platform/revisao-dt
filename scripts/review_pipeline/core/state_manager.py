import os
import json
import logging
import time
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class StateManager:
    """
    Client responsável puramente por gerenciar o estado volátil da UI (ACTIVE_STATE)
    e o histórico de fases (PHASES_HISTORY). Não toca em logs de inferência (trAIce).
    """
    def __init__(self, base_dir: str = ".agent/data_storage", on_event_callback=None):
        self.base_dir = base_dir
        self.active_state_file = os.path.join(self.base_dir, "ACTIVE_STATE.json")
        self.phases_history_file = os.path.join(self.base_dir, "PHASES_HISTORY.json")
        self.on_event_callback = on_event_callback
        
        os.makedirs(self.base_dir, exist_ok=True)

    def set_active_state(self, phase_dir: str, phase_name: str, total_target: int = 0, current_task: str = "Iniciando...") -> None:
        """Inicializa ou sobrescreve o estado ativo da fase atual."""
        state = {
            "phase_dir": phase_dir,
            "phase_name": phase_name,
            "total_target": total_target,
            "total_processed": 0,
            "total_success": 0,
            "total_fails": 0,
            "total_excluded": 0,
            "total_skipped": 0,
            "current_task": current_task,
            "status": "RUNNING",
            "last_updated": time.strftime('%d-%m-%Y %H:%M:%S(GMT-04:00)'),
            "start_time_ts": time.time()
        }
        with open(self.active_state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        
        self._trigger_callback()

    def update_state(self, processed: int = 0, success: int = 0, fails: int = 0, excluded: int = 0, skipped: int = 0, current_task: str = None, finish: bool = False) -> None:
        """Atualiza incrementos do estado ativo e salva o histórico se finish=True.

        Args:
            processed: Número de itens processados (tentativa, independente do resultado).
            success: Incremento de sucessos de máquina (LLM respondeu sem crash).
            fails: Incremento de falhas de máquina (timeout, crash de API, erro técnico).
            excluded: Incremento de exclusões científicas (máquina operou, LLM decidiu excluir).
            skipped: Incremento de itens pulados (já processados em sessão anterior).
            current_task: Descrição textual da tarefa atual (para display no dashboard).
            finish: Se True, marca a fase como FINISHED e salva no histórico.
        """
        if not os.path.exists(self.active_state_file):
            return
            
        try:
            with open(self.active_state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
        except Exception:
            return
            
        state["total_processed"] += processed
        state["total_success"] += success
        state["total_fails"] += fails
        state["total_excluded"] = state.get("total_excluded", 0) + excluded
        state["total_skipped"] += skipped
        state["last_updated"] = time.strftime('%d-%m-%Y %H:%M:%S(GMT-04:00)')
        
        if current_task is not None:
            state["current_task"] = current_task
            
        if finish:
            state["status"] = "FINISHED"
            if current_task is None:
                state["current_task"] = "Concluído"
            
        with open(self.active_state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
            
        if finish:
            self._save_to_history(state)
            
        self._trigger_callback()

    def update_target(self, new_target: int) -> None:
        """Atualiza dinamicamente o total_target da fase ativa.

        Usado por fases dinâmicas (ex: Fase 0 de Ingestão) que só conhecem
        o número real de itens a processar DURANTE a execução, após deduplicação.
        Responsabilidade exclusiva do StateManager — a View nunca deve mascarar este valor.
        """
        if not os.path.exists(self.active_state_file):
            return
        try:
            with open(self.active_state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
            state["total_target"] = new_target
            state["last_updated"] = time.strftime('%d-%m-%Y %H:%M:%S(GMT-04:00)')
            with open(self.active_state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
        except Exception:
            logger.error("Falha ao atualizar total_target no ACTIVE_STATE.json", exc_info=True)
            return
        self._trigger_callback()

    def get_active_state(self) -> dict:
        """Lê o estado ativo atual, retornando dicionário vazio se não existir."""
        if os.path.exists(self.active_state_file):
            try:
                with open(self.active_state_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_to_history(self, state: dict) -> None:
        """Salva a fase finalizada no histórico."""
        history = {}
        if os.path.exists(self.phases_history_file):
            try:
                with open(self.phases_history_file, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except Exception:
                pass
                
        phase_id = state.get("phase_dir", "unknown")
        history[phase_id] = {
            "phase_name": state.get("phase_name", phase_id),
            "processed": state.get("total_processed", 0),
            "success": state.get("total_success", 0),
            "fails": state.get("total_fails", 0),
            "excluded": state.get("total_excluded", 0),
            "target": state.get("total_target", 0),
            "last_updated": datetime.now().strftime("%d-%m-%Y %H:%M:%S(GMT-04:00)"),
            "start_time_ts": state.get("start_time_ts", 0)
        }
        
        with open(self.phases_history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)

    def reset_phase_history(self, phase_id: str) -> None:
        """
        Limpa entradas do histórico (PHASES_HISTORY.json) para uma fase específica,
        MAS mantendo entradas que tenham ocorrido há menos de 24 horas.
        """
        if not os.path.exists(self.phases_history_file):
            return
            
        try:
            with open(self.phases_history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            return

        if phase_id in history:
            entry = history[phase_id]
            last_updated_str = entry.get("last_updated", "")
            try:
                # O formato é DD-MM-YYYY HH:MM:SS(GMT-04:00)
                time_str = last_updated_str.split("(GMT")[0].strip()
                dt_obj = datetime.strptime(time_str, '%d-%m-%Y %H:%M:%S')
                now = datetime.now()
                
                # Se a diferença for menor que 1 dia (24h), NÃO apaga
                if now - dt_obj < timedelta(days=1):
                    # Mantém no histórico
                    return
            except Exception:
                pass
                
            # Apaga do histórico se tiver mais de 24h ou houver erro no parse
            del history[phase_id]
            
            with open(self.phases_history_file, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2, ensure_ascii=False)

    def _trigger_callback(self):
        if self.on_event_callback:
            try: 
                self.on_event_callback()
            except Exception as e:
                logger.warning("Falha no callback do dashboard (não fatal): %s", e, exc_info=True)
