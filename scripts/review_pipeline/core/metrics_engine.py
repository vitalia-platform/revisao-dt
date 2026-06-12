import datetime

class MetricsEngine:
    """
    Service focado unicamente no processamento matemático das métricas de auditoria (P11).
    Isola os cálculos complexos e projeções da View.
    """

    @staticmethod
    def calculate_eta(shards: list, active_state: dict) -> tuple[str, float]:
        """
        Calcula a latência média e o ETA real com base no estado e nos últimos shards.
        """
        total_target = active_state.get("total_target", 0)
        total_processed = active_state.get("total_processed", 0)
        
        latencies = [
            s.get("inference_metrics", {}).get("latency_seconds") 
            for s in shards 
            if isinstance(s.get("inference_metrics", {}).get("latency_seconds"), (int, float))
        ]
        
        avg_latency = 0.0
        if latencies:
            avg_latency = sum(latencies) / len(latencies)
            
        eta_rel = "N/A"
        if avg_latency > 0 and total_target > 0:
            remaining = max(0, total_target - total_processed)
            if remaining > 0:
                sec_left = remaining * avg_latency
                eta_rel = str(datetime.timedelta(seconds=int(sec_left)))
            else:
                eta_rel = "0:00:00"
                
        return eta_rel, avg_latency

    @staticmethod
    def format_duration(seconds: float) -> str:
        """Formata os segundos para a badge do Metrô."""
        if seconds < 0: return "--"
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        if h > 0: return f"⏱ {int(h)}h {int(m)}m"
        return f"⏱ {int(m)}m {int(s)}s"
