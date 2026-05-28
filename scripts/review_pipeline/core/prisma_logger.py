# scripts/review_pipeline/core/prisma_logger.py | Última Atualização: 21-05-2026 11:31:00(GMT-04:00)
"""
prisma_logger.py — Rastreabilidade, Estatísticas em Tempo Real e JSON Sharding

Responsabilidades:
- Escrever decisões da triagem direto no PRISMA_LOG.csv
- Salvar logs de auditoria detalhados e rastreáveis por artigo (JSON Sharding)
- Monitorar estatísticas de progresso em tempo real
"""

import csv
import os
import sys
import time

from .auditor import ReviewAuditor

class PrismaLogger:
    """Orquestrador de persistência de triagem com escrita no PRISMA_LOG.csv e delegação de auditoria."""
    
    def __init__(
        self,
        prisma_log_path: str,
        shards_dir: str = None, # Mantido para retrocompatibilidade mas ignorado
        log_file_path: str = "saida/auditoria/logs_execucao/execution_log.txt"
    ):
        self.prisma_log_path = prisma_log_path
        
        # Garante as pastas base (output_prisma)
        base_dir = os.path.dirname(prisma_log_path) if os.path.dirname(prisma_log_path) else "."
        os.makedirs(base_dir, exist_ok=True)
        
        # Log path default usa a pasta dinâmica do auditor
        if log_file_path == "saida/auditoria/logs_execucao/execution_log.txt":
            self.log_file_path = os.path.join(base_dir, "auditoria", "logs_execucao", "execution_log.txt")
        else:
            self.log_file_path = log_file_path
            
        audit_base_dir = os.path.join(base_dir, "auditoria")
        self.auditor = ReviewAuditor(base_audit_dir=audit_base_dir)
        
        os.makedirs(os.path.dirname(self.log_file_path), exist_ok=True)
        
        # Mapeia colunas canônicas
        self.fieldnames = [
            "Title", "Authors", "Year", "Journal", "DOI",
            "Abstract", "Status", "Exclusion_Reason", "Source"
        ]
        
    def get_stats(self) -> dict:
        """Calcula estatísticas de progresso lendo o PRISMA_LOG.csv em tempo real."""
        stats = {
            "total": 0,
            "aguardando": 0,
            "incluidos": 0,
            "excluidos": 0,
            "erros": 0
        }
        
        if not os.path.exists(self.prisma_log_path):
            return stats
            
        try:
            with open(self.prisma_log_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    stats["total"] += 1
                    status = row.get("Status", "").strip()
                    if status == "Aguardando Fase 1":
                        stats["aguardando"] += 1
                    elif status == "Incluido Fase 1":
                        stats["incluidos"] += 1
                    elif status == "Excluido Fase 1":
                        stats["excluidos"] += 1
                    elif "Erro" in status:
                        stats["erros"] += 1
        except Exception as e:
            print(f"\033[91m[ERRO] Falha ao ler estatísticas do PRISMA_LOG: {e}\033[0m")
            
        return stats

    def show_progress_bar(self, stats: dict) -> None:
        """Exibe uma barra de progresso formatada com detalhes estatísticos no terminal."""
        total = stats["total"]
        if total == 0:
            return
            
        concluidos = total - stats["aguardando"]
        porcentagem = (concluidos / total) * 100
        bar_length = 30
        filled_length = int(round(bar_length * concluidos / float(total)))
        bar = '█' * filled_length + '-' * (bar_length - filled_length)
        
        sys.stdout.write(
            f"\r\033[94mProgresso: [{bar}] {porcentagem:.1f}% ({concluidos}/{total}) "
            f"| Incluídos: \033[92m{stats['incluidos']}\033[94m | Excluídos: \033[91m{stats['excluidos']}\033[94m "
            f"| Erros: \033[93m{stats['erros']}\033[94m\033[0m"
        )
        sys.stdout.flush()

    def save_decision(
        self,
        article_title: str,
        decision: str,
        exclusion_reason: str,
        raw_response: str,
        article_data: dict,
        full_prompt: str = "",
        model_name: str = "unknown"
    ) -> None:
        """
        Salva o resultado da triagem:
        1. Protege contra regressão verificando o status anterior.
        2. Atualiza a linha correspondente no PRISMA_LOG.csv
        3. Delega a gravação do shard JSON para o ReviewAuditor
        """
        previous_decision = None
        try:
            if os.path.exists(self.prisma_log_path):
                with open(self.prisma_log_path, "r", encoding="utf-8") as f:
                    for row in csv.DictReader(f):
                        if row.get("Title", "").strip().lower() == article_title.strip().lower():
                            current_status = row.get("Status", "").strip()
                            if current_status and current_status != "Aguardando Fase 1":
                                previous_decision = current_status
                            break
        except Exception:
            pass

        # 1. JSON Sharding via Auditoria Centralizada
        audit_payload = {
            "timestamp": time.strftime("%d-%m-%Y %H:%M:%S(GMT-04:00)"),
            "model": model_name,
            "article_metadata": article_data,
            "full_prompt": full_prompt,
            "raw_llm_response": raw_response,
            "parsed_data": {"decision": decision, "reason": exclusion_reason}
        }
        
        if previous_decision:
            audit_payload["previous_decision_state"] = previous_decision
        
        self.auditor.save_inference_shard(phase=1, item_id=article_title, payload=audit_payload)
            
        # 2. Atualização atômica do CSV
        self.update_csv_row(article_title, decision, exclusion_reason)

    def update_csv_row(self, article_title: str, status: str, exclusion_reason: str) -> None:
        """Atualiza uma linha específica no PRISMA_LOG.csv baseado no Título."""
        if not os.path.exists(self.prisma_log_path):
            return
            
        rows = []
        updated = False
        
        with open(self.prisma_log_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("Title", "").strip().lower() == article_title.strip().lower():
                    row["Status"] = status
                    row["Exclusion_Reason"] = exclusion_reason
                    updated = True
                rows.append(row)
                
        if updated:
            with open(self.prisma_log_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=self.fieldnames)
                writer.writeheader()
                writer.writerows(rows)

    def write_execution_log(self, message: str) -> None:
        """Grava uma mensagem com timestamp no execution_log.txt."""
        timestamp = time.strftime("%d-%m-%Y %H:%M:%S(GMT-04:00)")
        try:
            with open(self.log_file_path, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] {message}\n")
        except Exception:
            pass
