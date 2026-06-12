# scripts/review_pipeline/core/terminal.py
import sys
import time
import datetime
import termios
import tty
import select
import signal

try:
    from rich.live import Live
    from rich.table import Table
    from rich.panel import Panel
    from rich.layout import Layout
    from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn, TimeElapsedColumn
    from rich.console import Console
    _RICH_AVAILABLE = True
except ImportError:
    _RICH_AVAILABLE = False

_interrupt_context = {}
_terminal_old_settings = None
_terminal_fd = None

def setup_interrupt_handler(router, get_context_fn=None):
    """Instala handler global para SIGINT (Ctrl+C)."""
    global _interrupt_context
    _interrupt_context['router'] = router
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
            
        print(f"Hora do cancelamento  : {datetime.datetime.now().strftime('%d-%m-%Y %H:%M:%S')}")
        print("Dados preservados     : Logs CSV e relatórios de auditoria parciais mantidos.\n")

        print("✔ Cancelamento concluído. O progresso foi retido.")
        sys.exit(0)

    signal.signal(signal.SIGINT, sigint_handler)

def handle_error_menu(title, error, default_action="2", timeout=120, phase_label=""):
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
                if ch == '\x1b': # Escape seq
                    ch2 = sys.stdin.read(2)
                    if ch2 == '[A': current_idx = (current_idx - 1) % len(options)
                    elif ch2 == '[B': current_idx = (current_idx + 1) % len(options)
                elif ch == '\n':
                    sys.stdout.write("\n")
                    return options[current_idx], False
    finally:
        termios.tcsetattr(_terminal_fd, termios.TCSADRAIN, _terminal_old_settings)
        _terminal_fd = None
        _terminal_old_settings = None
        
    sys.stdout.write("\n")
    return options[current_idx], True


def print_section_header(title: str):
    if _RICH_AVAILABLE:
        from rich.console import Console
        from rich.panel import Panel
        Console().print(Panel(f"[bold cyan]{title}[/bold cyan]", style="blue"))
    else:
        print(f"\n{'='*60}\n{title}\n{'='*60}\n")

def show_progress_bar(current: int, total: int, success: int = 0, skipped: int = 0, erros: int = 0, title: str = ""):
    pct = (current / total) * 100 if total > 0 else 0
    status = f"[{current}/{total} | {pct:.1f}%]"
    if title:
        status += f" {title[:60]}..."
    
    if _RICH_AVAILABLE:
        from rich.console import Console
        Console().print(f"[bold blue]{status}[/bold blue] (✓: {success} | ⏭: {skipped} | ✗: {erros})")
    else:
        print(status)

def print_step(title: str):
    if _RICH_AVAILABLE:
        from rich.console import Console
        Console().print(f"  [cyan]Analisando:[/cyan] {title}")
    else:
        print(f"  Analisando: {title}")

def print_success(msg: str):
    if _RICH_AVAILABLE:
        from rich.console import Console
        Console().print(f"    [green]✔ {msg}[/green]")
    else:
        print(f"    ✔ {msg}")

def print_error(msg: str):
    if _RICH_AVAILABLE:
        from rich.console import Console
        Console().print(f"    [red]✘ {msg}[/red]")
    else:
        print(f"    ✘ {msg}")
        
def print_warning(msg: str):
    if _RICH_AVAILABLE:
        from rich.console import Console
        Console().print(f"    [yellow]⚠️ {msg}[/yellow]")
    else:
        print(f"    ⚠️ {msg}")
