import os
import json
import time
import requests

class LLMRouter:
    def __init__(self, config_path="criteria_config.yaml"):
        self.config_path = config_path
        self._load_config()

    def _load_config(self):
        # Implementação minimalista de leitura YAML para evitar dependência extra
        import yaml
        import re
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                content = f.read()
                # Resolve ${VAR} using regex
                content = re.sub(r'\$\{([^}]+)\}', lambda m: os.environ.get(m.group(1), ''), content)
                self.config = yaml.safe_load(content)
        except Exception as e:
            print(f"[LLMRouter] Erro ao ler config: {e}")
            self.config = {}

        self.router_cfg = self.config.get("infrastructure", {}).get("llm_router", {})
        self.strategy = self.router_cfg.get("strategy", "local_first")
        self.local_cfg = self.router_cfg
        self.cloud_cfg = self.router_cfg

    def check_ollama_alive(self, base_url):
        try:
            response = requests.get(base_url, timeout=2.0)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False

    def query_ollama(self, prompt, model, base_url, json_format=True, max_retries=3):
        url = f"{base_url.rstrip('/')}/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }
        if json_format:
            payload["format"] = "json"

        for attempt in range(1, max_retries + 1):
            try:
                resp = requests.post(url, json=payload, timeout=120)
                if resp.status_code == 200:
                    data = resp.json()
                    response_text = data.get("response", "{}")
                    
                    tokens_dict = {
                        "prompt_eval_count": data.get("prompt_eval_count", 0),
                        "eval_count": data.get("eval_count", 0)
                    }
                    
                    if json_format:
                        try:
                            return json.loads(response_text), "local", model, tokens_dict
                        except json.JSONDecodeError:
                            return {"error": "Invalid JSON from Ollama", "raw": response_text}, "local", model, tokens_dict
                    return response_text, "local", model, tokens_dict
                else:
                    print(f"    [LLMRouter] Local HTTP {resp.status_code} (Tentativa {attempt}/{max_retries})")
            except Exception as e:
                print(f"    [LLMRouter] Falha Local: {e} (Tentativa {attempt}/{max_retries})")
                
            time.sleep(2 ** attempt)

        return None, "local", model, {}

    def query_cloud(self, prompt, model, api_key, provider, json_format=True):
        # Aqui podemos implementar a chamada pro Gemini ou OpenAI.
        # Por hora, logamos que precisa ser implementado, ou podemos delegar ao agent local de LLM se existir
        print(f"    [LLMRouter] Cloud route acionado ({provider} / {model}).")
        # To be fully implemented when cloud synthesis is needed.
        return {"error": "Cloud execution not fully implemented in script yet"}, "cloud", model, {}

    def generate(self, phase, prompt, json_format=True):
        """
        Roteia o prompt com base na configuração da fase e disponibilidade.
        Retorna: (resultado, backend_usado, modelo_usado)
        """
        backend = self.router_cfg.get("backend", "local")
        model = self.router_cfg.get("model_local", "qwen2.5-coder-vitalia:latest")

        local_base_url = self.router_cfg.get("ollama_url", os.environ.get("OLLAMA_BASE_URL", "http://192.168.0.254:11434"))

        if backend == "local" or (self.strategy == "local_first"):
            if self.check_ollama_alive(local_base_url):
                res, b_used, m_used, t_dict = self.query_ollama(prompt, model, local_base_url, json_format)
                if res is not None:
                    return res, b_used, m_used, t_dict
            
            # Se falhou e estrategia é local_first, tenta fallback
            if self.strategy == "local_first":
                print("    [LLMRouter] ⚠️ Local falhou. Tentando fallback para Cloud.")
                cloud_model = self.cloud_cfg.get("model", "gemini-2.0")
                cloud_key = self.cloud_cfg.get("api_key", os.environ.get("CLOUD_LLM_API_KEY", ""))
                return self.query_cloud(prompt, cloud_model, cloud_key, self.cloud_cfg.get("provider", "gemini"), json_format)

        elif backend == "cloud":
            cloud_model = self.cloud_cfg.get("model", "gemini-2.0")
            cloud_key = self.cloud_cfg.get("api_key", os.environ.get("CLOUD_LLM_API_KEY", ""))
            if not cloud_key:
                print("    [LLMRouter] ⚠️ Cloud solicitado mas chave ausente. Fallback para Local.")
                return self.query_ollama(prompt, model, local_base_url, json_format)
                
            return self.query_cloud(prompt, cloud_model, cloud_key, self.cloud_cfg.get("provider", "gemini"), json_format)

        return None, "none", "none", {}
