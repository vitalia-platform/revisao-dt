#!/usr/bin/env python3
import os
import sys
import http.server
import socketserver
import webbrowser
import threading
import time

def start_server(base_dir, port=8000):
    if not os.path.exists(base_dir):
        print(f"Diretório base não encontrado: {base_dir}")
        return

    os.chdir(base_dir)
    Handler = http.server.SimpleHTTPRequestHandler

    # Tenta usar a porta, incrementa se estiver em uso
    while True:
        try:
            httpd = socketserver.TCPServer(("", port), Handler)
            break
        except OSError:
            port += 1

    print(f"Servindo dashboard em http://localhost:{port}")
    
    # Abre o browser em thread separada
    def open_browser():
        time.sleep(1)
        webbrowser.open(f"http://localhost:{port}/LIVE_PROGRESS.html")
        webbrowser.open(f"http://localhost:{port}/PROGRESS.html")
        
    threading.Thread(target=open_browser, daemon=True).start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor encerrado.")
        httpd.server_close()

if __name__ == "__main__":
    # Carrega config para pegar o data_storage_dir
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from scripts.review_pipeline.core.config_manager import load_config
    config = load_config()
    base_dir = config.get("data_storage_dir", ".agent/data_storage")
    
    start_server(base_dir)
