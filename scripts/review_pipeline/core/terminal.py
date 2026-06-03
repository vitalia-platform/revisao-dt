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
                    return options[current_idx], False
    finally:
        termios.tcsetattr(_terminal_fd, termios.TCSADRAIN, _terminal_old_settings)
        _terminal_fd = None
        _terminal_old_settings = None
        
    return options[current_idx], True


class RichDashboard:
    """Componente de UI Unificado com Rich Dashboard para visualizações premium de terminal."""
    def __init__(self, title: str, total: int, console_title: str = "Console de Auditoria (trAIce)", stats_title: str = "Estatísticas da Sessão"):
        if not _RICH_AVAILABLE:
            raise RuntimeError("[ERRO] Biblioteca rich não está disponível.")
        self.title = title
        self.total = total
        self.console_title = console_title
        self.stats_title = stats_title
        self.current = 0
        self.success = 0
        self.fail = 0
        self.sources = {}
        self.logs = []
        self.console = Console()
        self.progress_bar = Progress(
            TextColumn("[progress.percentage]{task.percentage:>3.1f}%"),
            BarColumn(),
            TextColumn("({task.completed}/{task.total})"),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            expand=True
        )
        self.task_id = self.progress_bar.add_task("Running", total=total)
        self.live = None

    def add_log(self, msg: str, max_logs: int = 15):
        ts = time.strftime("%H:%M:%S")
        self.logs.append(f"[[dim]{ts}[/dim]] {msg}")
        if len(self.logs) > max_logs:
            self.logs.pop(0)
        self.update()

    def increment_success(self, source: str = None):
        self.current += 1
        self.success += 1
        if source:
            self.sources[source] = self.sources.get(source, 0) + 1
        self.progress_bar.advance(self.task_id)
        self.update()

    def increment_fail(self, source: str = "Falhas"):
        self.current += 1
        self.fail += 1
        if source:
            self.sources[source] = self.sources.get(source, 0) + 1
        self.progress_bar.advance(self.task_id)
        self.update()

    def generate_layout(self) -> Layout:
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main", size=8),
            Layout(name="footer")
        )
        
        layout["header"].update(Panel(f"[bold cyan]{self.title}[/bold cyan] - {self.current}/{self.total} Processados", style="blue"))
        
        stats_table = Table(show_header=True, header_style="bold magenta", expand=True)
        stats_table.add_column("Métrica")
        stats_table.add_column("Contagem", justify="right")
        
        for src, count in sorted(self.sources.items(), key=lambda x: -x[1]):
            stats_table.add_row(src, str(count))
            
        stats_table.add_row("[bold green]Total Incluídos[/bold green]", f"[bold green]{self.success}[/bold green]")
        stats_table.add_row("[bold red]Total Excluídos[/bold red]", f"[bold red]{self.fail}[/bold red]")
        
        layout["main"].split_row(
            Layout(Panel(stats_table, title=f"[yellow]{self.stats_title}[/yellow]")),
            Layout(Panel(self.progress_bar, title="[yellow]Progresso Global[/yellow]"))
        )
        
        logs_text = "\n".join(self.logs)
        layout["footer"].update(Panel(logs_text, title=f"[green]{self.console_title}[/green]", subtitle="Aperte Ctrl+C para parada segura"))
        
        return layout

    def __enter__(self):
        self.live = Live(self.generate_layout(), refresh_per_second=4, console=self.console)
        self.live.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.live:
            self.live.stop()
            self.live = None

    def update(self):
        if self.live:
            self.live.update(self.generate_layout())
