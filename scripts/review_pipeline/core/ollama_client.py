# scripts/review_pipeline/core/ollama_client.py | Última Atualização: 21-05-2026 11:31:00(GMT-04:00)
"""
ollama_client.py — Cliente de Comunicação com API Local do Ollama

Responsabilidades:
- Conectar via requisições HTTP (POST) à API local do Ollama
- Implementar pre-flight check de conexão
- Retry automático com backoff exponencial e log/report terminal de tentativas
- Forçar liberação de VRAM (keep_alive: 0)
"""

import time
import requests
import json
import os
import sys

def check_model_available(api_url: str, model: str) -> tuple[bool, list[str]]:
    """Verifica se o modelo específico está disponível. Retorna (is_available, lista_modelos)."""
    base_url = api_url.rsplit("/api/", 1)[0]
    try:
        resp = requests.get(f"{base_url}/api/tags", timeout=5.0)
        if resp.status_code == 200:
            models = [m["name"] for m in resp.json().get("models", [])]
            return model in models, models
    except Exception:
        pass
    return False, []

def check_ollama_alive(api_url: str) -> bool:
    """Verifica se o servidor Ollama está ativo e respondendo na porta."""
    try:
        base_url = api_url.rsplit("/api/", 1)[0]
        response = requests.get(base_url, timeout=2.0)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False

def query_ollama(
    prompt: str,
    api_url: str,
    model: str,
    options: dict | None = None,
    log_file_path: str = None,
    circuit_breaker_state: dict = None
) -> dict:
    """
    Envia prompt para o Ollama com retry, backoff exponencial e circuit breaker.
    """
    if circuit_breaker_state is None:
        circuit_breaker_state = {"consecutive_failures": 0}
        
    if circuit_breaker_state.get("consecutive_failures", 0) >= 5:
        raise ConnectionError("CIRCUIT BREAKER ATIVADO: Mais de 5 falhas de rede consecutivas. Execução abortada.")

    headers = {"Content-Type": "application/json"}
    final_options = {"num_ctx": 8192}
    if options:
        final_options.update(options)

    payload = {
        "model": model,
        "prompt": prompt,
        "format": "json",
        "stream": False,
        "options": final_options
    }
    
    max_retries = 3
    wait_times = [5, 15, 30]
    
    def _log_attempt(attempt: int, error_msg: str):
        if not log_file_path: return
        timestamp = time.strftime("%d-%m-%Y %H:%M:%S(GMT-04:00)")
        log_line = f"[{timestamp}] [RETRY {attempt}/{max_retries}] Erro: {error_msg}\n"
        try:
            with open(log_file_path, "a", encoding="utf-8") as lf:
                lf.write(log_line)
        except Exception:
            pass

    start_time = time.time()
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=120)
            if response.status_code == 200:
                circuit_breaker_state["consecutive_failures"] = 0
                result = response.json()
                result["_latency_ms"] = int((time.time() - start_time) * 1000)
                result["_attempt"] = attempt
                return result
            else:
                err_msg = f"HTTP {response.status_code}: {response.text}"
                print(f"\033[93m[RETRY {attempt}/{max_retries}] Ollama retornou erro {response.status_code}. Aguardando {wait_times[attempt-1]}s...\033[0m")
                _log_attempt(attempt, err_msg)
        except requests.exceptions.RequestException as e:
            err_msg = str(e)
            print(f"\033[93m[RETRY {attempt}/{max_retries}] Falha de conexão com Ollama. Aguardando {wait_times[attempt-1]}s...\033[0m")
            _log_attempt(attempt, err_msg)
            
        if attempt < max_retries:
            time.sleep(wait_times[attempt - 1])
            
    circuit_breaker_state["consecutive_failures"] = circuit_breaker_state.get("consecutive_failures", 0) + 1
    raise ConnectionError("Falha de conexão com o Ollama após 3 tentativas.")

def unload_model(api_url: str, model: str) -> None:
    """Força o descarregamento da VRAM (keep_alive: 0)."""
    headers = {"Content-Type": "application/json"}
    payload = {"model": model, "prompt": "", "keep_alive": 0, "stream": False}
    try:
        requests.post(api_url, headers=headers, json=payload, timeout=5)
    except Exception:
        pass
