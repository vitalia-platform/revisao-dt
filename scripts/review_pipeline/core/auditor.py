# scripts/review_pipeline/core/auditor.py | Última Atualização: 21-05-2026 11:31:00(GMT-04:00)
"""
auditor.py — Sistema Centralizado de Rastreabilidade e Auditoria Forense

Responsabilidades (Princípio de Responsabilidade Única):
- Gravar Shards de Auditoria Absoluta (JSON Sharding) contendo Entrada, Saída, Metadata e Model.
- Centralizar o registro e tratamento de logs de erros (llm_errors, timeouts).
- Prover rastreabilidade irrefutável de inferência para comitês acadêmicos e revisores.
"""

import os
import json
import time

class ReviewAuditor:
    """Classe responsável pelo registro em trilha de auditoria e armazenamento estruturado (Sharding)."""
    
    def __init__(self, base_audit_dir: str = "saida/auditoria"):
        self.base_dir = base_audit_dir
        self.fase1_dir = os.path.join(self.base_dir, "fase1_screening")
        self.fase2_dir = os.path.join(self.base_dir, "fase2_extraction")
        self.logs_dir = os.path.join(self.base_dir, "logs_execucao")
        
        # Garante a existência das pastas raiz de auditoria
        for directory in [self.fase1_dir, self.fase2_dir, self.logs_dir]:
            os.makedirs(directory, exist_ok=True)
            
    def _sanitize_filename(self, filename: str) -> str:
        """Limpa o nome do arquivo para gravação segura no sistema de arquivos."""
        safe_name = "".join([c if c.isalnum() else "_" for c in filename])
        return safe_name[:80]

    def save_inference_shard(self, phase: int, item_id: str, payload: dict) -> None:
        """
        Salva um JSON Shard de auditoria com Schema Version dinâmico.
        """
        target_dir = self.fase1_dir if phase == 1 else self.fase2_dir
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
            
    def log_error(self, phase: int, error_type: str, details: str) -> None:
        log_file = "fase1_errors.log" if phase == 1 else "fase2_errors.log"
        log_path = os.path.join(self.logs_dir, log_file)
        
        timestamp = time.strftime("%d-%m-%Y %H:%M:%S(GMT-04:00)")
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] [FASE {phase}] [{error_type}]\n{details}\n{'='*60}\n")
        except Exception:
            pass

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
