# scripts/review_pipeline/core/auditor.py | Atualizado em: 11-06-2026 08:00:00(GMT-04:00)
"""
auditor.py — Sistema Centralizado de Rastreabilidade e Auditoria Forense

Responsabilidades (Princípio de Responsabilidade Única):
- Gravar Shards de Auditoria Absoluta (JSON Sharding) contendo Entrada, Saída, Metadata e Model.
- Centralizar o registro e tratamento de logs de erros (llm_errors, timeouts).
- Prover rastreabilidade irrefutável de inferência para comitês acadêmicos e revisores.
"""

import os
import json
import logging
import datetime
import time
from .state_manager import StateManager

# <!-- core/auditor.py | Atualizado em: 11-06-2026 08:00:00(GMT-04:00) -->

class ReviewAuditor:
    """Classe responsável pelo registro em trilha de auditoria e armazenamento estruturado (Sharding)."""
    
    def __init__(self, base_output_dir: str = ".agent/data_storage/saida/auditoria", on_event_callback=None):
        self.base_dir = base_output_dir
        self.on_event_callback = on_event_callback
        self.fase0_dir = os.path.join(self.base_dir, "fase0_ingestion")
        self.fase1_dir = os.path.join(self.base_dir, "fase1_screening")
        self.fase2a_dir = os.path.join(self.base_dir, "fase2a_download")
        self.fase2_dir = os.path.join(self.base_dir, "fase2b_extraction")
        self.logs_dir = os.path.join(self.base_dir, "logs_execucao")
        self.active_state_file = os.path.join(self.base_dir, "ACTIVE_STATE.json")
        self.phases_history_file = os.path.join(self.base_dir, "PHASES_HISTORY.json")
        
        # Garante a existência das pastas raiz de auditoria
        for directory in [self.fase0_dir, self.fase1_dir, self.fase2a_dir, self.fase2_dir, self.logs_dir]:
            os.makedirs(directory, exist_ok=True)
            
    def _sanitize_filename(self, filename: str) -> str:
        """Limpa o nome do arquivo para gravação segura no sistema de arquivos."""
        safe_name = "".join([c if c.isalnum() else "_" for c in filename])
        return safe_name[:80]

    def save_inference_shard(self, phase: int, item_id: str, payload: dict) -> None:
        """
        Salva um JSON Shard de auditoria com Schema Version dinâmico.
        """
        target_dir = {
            0: self.fase0_dir,
            1: self.fase1_dir,
            2: self.fase2_dir,
            20: self.fase2a_dir # 20 representa 2a (download) para simplificar a chamada
        }.get(phase, self.base_dir)
        safe_name = f"{self._sanitize_filename(item_id)}.json"
        shard_path = os.path.join(target_dir, safe_name)
        
        # Auditoria V2 - Schema Timestamp Dinâmico Obrigatório
        if "schema_version" not in payload:
            timestamp_str = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
            payload["schema_version"] = f"2.0-{timestamp_str}"
            
        try:
            with open(shard_path, "w", encoding="utf-8") as jf:
                json.dump(payload, jf, indent=2, ensure_ascii=False)
        except Exception as e:
            self.log_error(phase, "SHARDING_ERROR", f"Falha ao salvar auditoria de '{item_id}': {e}")
            
        # [Gatilho de Evento Desacoplado] Atualiza o Dashboard Web instantaneamente via callback
        if self.on_event_callback:
            try:
                self.on_event_callback()
            except Exception as e:
                print(f"[DEBUG UI] Falha no callback do dashboard: {e}")
                pass # Falhas de UI não devem quebrar o pipeline
            
    def log_error(self, phase: int, error_type: str, details: str) -> None:
        log_file_map = {
            0: "fase0_errors.log",
            1: "fase1_errors.log",
            20: "fase2a_errors.log",
            2: "fase2b_errors.log"
        }
        log_file = log_file_map.get(phase, "general_errors.log")
        log_path = os.path.join(self.logs_dir, log_file)
        
        timestamp = time.strftime("%d-%m-%Y %H:%M:%S(GMT-04:00)")
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] [FASE {phase}] [{error_type}]\n{details}\n{'='*60}\n")
        except Exception:
            pass

    # [REMOVIDO] set_active_state, update_state e _save_to_history foram movidos para StateManager

    def reset_phase(self, phase: int, prisma_csv_path: str) -> None:
        """
        Executa a migração destrutiva controlada.
        Apaga o diretório de auditoria da fase e os artefatos secundários.
        Reverte o status no PRISMA_LOG_MASTER.csv.
        """
        import shutil
        import csv
        
        # 1. Identificar o alvo
        target_audit_dir = {
            1: self.fase1_dir,
            20: self.fase2a_dir,
            2: self.fase2_dir
        }.get(phase)
        
        if not target_audit_dir:
            return
            
        if os.path.exists(target_audit_dir):
            shutil.rmtree(target_audit_dir)
            os.makedirs(target_audit_dir) # Recria vazio
            
        # Limpar do histórico de fases delegando ao StateManager
        phase_dir_name = os.path.basename(target_audit_dir)
        StateManager(base_dir=os.path.dirname(self.base_dir)).reset_phase_history(phase_dir_name)
            
        # Deletar artefatos secundários (PDFs / Fichamentos)
        parent_dir = os.path.dirname(self.base_dir) # base_dir é saida/auditoria, parent é saida/
        if phase == 20: # Download
            pdfs_dir = os.path.join(parent_dir, "pdfs")
            if os.path.exists(pdfs_dir):
                shutil.rmtree(pdfs_dir)
                os.makedirs(pdfs_dir)
        elif phase == 2: # Extraction
            mds_dir = os.path.join(parent_dir, "fichamentos")
            if os.path.exists(mds_dir):
                shutil.rmtree(mds_dir)
                os.makedirs(mds_dir)
                
        # 3. Rollback no PRISMA_LOG_MASTER.csv
        if os.path.exists(prisma_csv_path):
            rows = []
            with open(prisma_csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                fieldnames = reader.fieldnames
                for row in reader:
                    status = row.get("Status", "").lower()
                    if phase == 1:
                        # Fase 1 reset: Volta tudo que foi tocado pela triagem para pending
                        if "inclu" in status or "exclu" in status:
                            row["Status"] = "pending"
                            row["Exclusion_Reason"] = ""
                            row["Reasoning"] = ""
                    elif phase == 20:
                        # Fase 2a reset: Volta para Incluído (Fase 1)
                        if "download" in status or "extra" in status or "fichamento" in status or "sintese" in status:
                            row["Status"] = "Incluído (Fase 1)"
                            row["PDF_status"] = ""
                    elif phase == 2:
                        # Fase 2b reset: Volta para Download Concluído
                        if "extra" in status or "fichamento" in status or "sintese" in status:
                            row["Status"] = "Download Concluído"
                    rows.append(row)
                    
            with open(prisma_csv_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)

    def generate_session_summary(self, session_id: str, stats: dict, config_hash: str, model: str, phase_label: str) -> str:
        """Gera e salva o relatório final da sessão na pasta logs_execucao."""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        report_path = os.path.join(self.logs_dir, f"session_{timestamp}.md")
        
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(f"# Resumo de Sessão: {phase_label}\n\n")
            f.write(f"- **Data de Conclusão**: {time.strftime('%d-%m-%Y %H:%M:%S(GMT-04:00)')}\n")
            f.write(f"- **Session ID**: `{session_id}`\n")
            f.write(f"- **Config Hash**: `{config_hash}`\n")
            f.write(f"- **Modelo**: `{model}`\n\n")
            f.write("## Estatísticas da Execução\n")
            for k, v in stats.items():
                f.write(f"- **{str(k).capitalize()}**: {v}\n")
                
        return report_path
