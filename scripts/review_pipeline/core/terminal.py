# scripts/review_pipeline/core/terminal.py | Última Atualização: 21-05-2026 11:31:00(GMT-04:00)
"""
terminal.py — UI Unificada e Resiliência de Interface

Centraliza a exibição de barras de progresso, menus interativos, 
tratamento de Ctrl+C e relatórios de sessão.
"""
import sys
import time
import termios
import tty
import select
import signal
import datetime
import os
import requests

_interrupt_context = {}
_terminal_old_settings = None
_terminal_fd = None

def setup_interrupt_handler(api_url, model, log_fn=None, get_context_fn=None):
    """Instala handler global para SIGINT (Ctrl+C)."""
    global _interrupt_context
    _interrupt_context['api_url'] = api_url
    _interrupt_context['model'] = model
    _interrupt_context['log_fn'] = log_fn
    _interrupt_context['get_context_fn'] = get_context_fn

    def sigint_handler(signum, frame):
        if _terminal_fd is not None and _terminal_old_settings is not None:
            termios.tcsetattr(_terminal_fd, termios.TCSADRAIN, _terminal_old_settings)

        ctx = get_context_fn() if get_context_fn else {}
        
        print("\n\n\033[93m╔══════════════════════════════════════════════════════════╗")
        print("║       EXECUÇÃO INTERROMPIDA PELO USUÁRIO (Ctrl+C)        ║")
        print("╚══════════════════════════════════════════════════════════╝\033[0m")
        print("Motivo da interrupção : Ctrl+C (SIGINT)")
        
        if "current_article" in ctx:
            print(f"Artigo em processamento: {ctx['current_article']}")
        
        if "idx" in ctx and "total" in ctx:
            print(f"Progresso na sessão   : {ctx['idx']}/{ctx['total']} artigos")
            
        print(f"Hora do cancelamento  : {datetime.datetime.now().strftime('%d-%m-%Y %H:%M:%S(GMT-04:00)')}")
        print("Dados preservados     : PRISMA_LOG.csv e shards atualizados até o artigo anterior.\n")

        print("Liberando VRAM do Ollama...")
        _unload_model(api_url, model)
        print("✔ Modelo descarregado. Recursos liberados.")

        if log_fn:
            log_fn("SIGINT: Execução cancelada pelo usuário via Ctrl+C.")

        sys.exit(0)

    signal.signal(signal.SIGINT, sigint_handler)

def _unload_model(api_url, model):
    try:
        headers = {"Content-Type": "application/json"}
        payload = {"model": model, "prompt": "", "keep_alive": 0, "stream": False}
        requests.post(api_url, headers=headers, json=payload, timeout=5)
    except Exception:
        pass

def update_interrupt_context(**kwargs):
    global _interrupt_context
    _interrupt_context.update(kwargs)

def handle_error_menu(title, error, default_action="2", timeout=120, phase_label=""):
    """
    Exibe menu interativo não bloqueante com timeout.
    Se o timeout <= 0 (ex: modo overnight), retorna a default action imediatamente.
    Retorna: (choice, is_timeout)
    """
    if timeout <= 0:
        return default_action, True

    options = ["1", "2", "3"]
    labels = ["Tentar novamente", "Pular artigo (Erro)", "Pausar e Sair"]
    
    try:
        current_idx = options.index(default_action)
    except ValueError:
        current_idx = 1
        
    start_time = time.time()
    
    print(f"\n\n\033[91m╔══════════════════════════════════════════════════════════╗")
    print(f"║ ERRO NO PROCESSAMENTO — {phase_label.ljust(35)}║")
    print(f"╚══════════════════════════════════════════════════════════╝\033[0m")
    print(f"Artigo: {title}")
    print(f"Erro: {error}")
    
    print("\n\033[93mSelecione a ação:\033[0m")
    for _ in range(len(options)):
        print()
        
    def draw_menu(remaining_time):
        sys.stdout.write(f"\r\033[{len(options)}A")
        for i, label in enumerate(labels):
            cursor = "->" if i == current_idx else "  "
            sys.stdout.write(f"\033[K{cursor}[{options[i]}] {label}\n")
        sys.stdout.write(f"\033[KEscolha [1/2/3] ou setas (Padrão '{options[current_idx]}' em {remaining_time}s): ")
        sys.stdout.flush()

    global _terminal_fd, _terminal_old_settings
    _terminal_fd = sys.stdin.fileno()
    _terminal_old_settings = termios.tcgetattr(_terminal_fd)
    
    try:
        tty.setcbreak(_terminal_fd)
        while time.time() - start_time < timeout:
            remaining = int(timeout - (time.time() - start_time))
            draw_menu(remaining)
            
            i, o, e = select.select([sys.stdin], [], [], 1)
            if i:
                ch = sys.stdin.read(1)
                if ch == '\x03': # Ctrl+C
                    raise KeyboardInterrupt
                if ch == '\x1b': # Escape seq (setas)
                    ch2 = sys.stdin.read(2)
                    if ch2 == '[A': # Up
                        current_idx = (current_idx - 1) % len(options)
                    elif ch2 == '[B': # Down
                        current_idx = (current_idx + 1) % len(options)
                elif ch in options:
                    current_idx = options.index(ch)
                    return options[current_idx], False
                elif ch == '\n':
                    return options[current_idx], False
    finally:
        termios.tcsetattr(_terminal_fd, termios.TCSADRAIN, _terminal_old_settings)
        _terminal_fd = None
        _terminal_old_settings = None
        
    return options[current_idx], True

def show_article_header(idx, total, title):
    title_disp = title[:70] + "..." if len(title) > 70 else title
    print(f"\n[{idx}/{total}] 📄 Processando: \033[96m{title_disp}\033[0m")

def show_article_decision(decision, reason):
    if "INCLUIR" in decision or "Aprovado" in decision:
        print("\033[92m-> DECISÃO: INCLUIR\033[0m")
    elif "EXCLUIR" in decision or "Excluido" in decision:
        print("\033[91m-> DECISÃO: EXCLUIR\033[0m")
    else:
        print(f"\033[93m-> DECISÃO: INCERTA ({decision})\033[0m")
    
    reason_disp = reason[:120] + "..." if len(reason) > 120 else reason
    print(f"   \033[3mMotivo:\033[0m {reason_disp}")

def show_progress_bar(current, total, **counters):
    if total == 0: return
    percent = float(current) * 100 / total
    filled = int(30 * current // total)
    bar = '█' * filled + '-' * (30 - filled)
    
    base_str = f"\r\033[94mProgresso: [{bar}] {percent:.1f}% ({current}/{total})\033[0m"
    details = []
    if "incluidos" in counters and "excluidos" in counters:
        details.append(f"Incluídos: \033[92m{counters['incluidos']}\033[0m")
        details.append(f"Excluídos: \033[91m{counters['excluidos']}\033[0m")
    if "erros" in counters and counters["erros"] > 0:
        details.append(f"Erros: \033[93m{counters['erros']}\033[0m")
    if "success" in counters:
        details.append(f"Sucesso: \033[92m{counters['success']}\033[0m")
        
    sys.stdout.write(f"{base_str} | {' | '.join(details)} ")
    sys.stdout.flush()

def print_section_header(title, width=60):
    print(f"\n\033[94m{'═'*width}\033[0m")
    print(f"\033[92m  {title}\033[0m")
    print(f"\033[94m{'═'*width}\033[0m")

def show_session_resume_banner(already_done, total, phase_label):
    if already_done <= 0: return
    restante = total - already_done
    print("\n\033[93m╔══════════════════════════════════════════════════════════╗")
    print(f"║  ▶ RETOMANDO SESSÃO PARCIAL — {phase_label.ljust(26)}║")
    print("╠══════════════════════════════════════════════════════════╣")
    print(f"║  Artigos processados na sessão anterior: {str(already_done).ljust(16)}║")
    print(f"║  Artigos restantes nesta sessão:         {str(restante).ljust(16)}║")
    print("╚══════════════════════════════════════════════════════════╝\033[0m\n")
