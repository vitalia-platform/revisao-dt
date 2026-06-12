from scripts.review_pipeline.core.metrics_engine import MetricsEngine

def test_calculate_eta():
    shards = [
        {"inference_metrics": {"latency_seconds": 2.0}},
        {"inference_metrics": {"latency_seconds": 3.0}}
    ]
    
    active_state = {
        "total_target": 100,
        "total_processed": 50
    }
    
    # Média deve ser 2.5
    # Faltam 50. ETA = 50 * 2.5 = 125s = 0:02:05
    eta, avg_latency = MetricsEngine.calculate_eta(shards, active_state)
    assert avg_latency == 2.5
    assert eta == "0:02:05"
    
    # Teste de 0 shards
    eta, avg = MetricsEngine.calculate_eta([], active_state)
    assert eta == "N/A"
    
    print("Teste MetricsEngine: ETA Rule passou!")
