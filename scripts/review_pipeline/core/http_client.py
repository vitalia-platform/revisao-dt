# scripts/review_pipeline/core/http_client.py | Atualizado em: 03-06-2026 12:02:36(GMT-04:00)
"""
http_client.py — Motor de Resiliência de Rede Unificado

Implementa:
- Exponential Backoff (retentativas com espera exponencial)
- Rate Limiting (cortesia para APIs acadêmicas)
- Fallback de User-Agent básico
"""

import time
import requests

class RobustHTTPClient:
    def __init__(self, max_retries=3, base_wait=3, max_wait=30):
        self.max_retries = max_retries
        self.base_wait = base_wait
        self.max_wait = max_wait
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json,application/xml,application/pdf,text/html,*/*"
        })

    def request(self, method, url, **kwargs):
        last_exception = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.session.request(method, url, timeout=20, **kwargs)
                
                # Se for sucesso, retorna direto
                if response.status_code == 200:
                    return response
                
                # Falhas definitivas (não adianta retentar)
                if response.status_code in [404, 400]:
                    return response
                    
                # Too Many Requests
                if response.status_code == 429:
                    wait_time = int(response.headers.get("Retry-After", self.base_wait * (2 ** attempt)))
                else:
                    wait_time = min(self.base_wait * (2 ** (attempt - 1)), self.max_wait)
                    
                print(f"    \033[93m[RETRY {attempt}/{self.max_retries}] HTTP {response.status_code} na URL {url[:60]}... Aguardando {wait_time}s\033[0m")
                time.sleep(wait_time)
                
            except requests.exceptions.RequestException as e:
                last_exception = e
                wait_time = min(self.base_wait * (2 ** (attempt - 1)), self.max_wait)
                print(f"    \033[91m[RETRY {attempt}/{self.max_retries}] Falha de rede: {type(e).__name__}. Aguardando {wait_time}s\033[0m")
                time.sleep(wait_time)
                
        # Retorna a última resposta ou levanta a exceção
        if 'response' in locals() and response is not None:
            return response
        if last_exception:
            raise last_exception
        return None

    def get(self, url, **kwargs):
        return self.request('GET', url, **kwargs)

    def download_file(self, url, save_path, **kwargs):
        kwargs['stream'] = True
        response = self.request('GET', url, **kwargs)
        
        if response and response.status_code == 200:
            with open(save_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            return True, "Downloaded successfully"
        else:
            err = f"HTTP {response.status_code}" if response else "Network Error"
            return False, err
