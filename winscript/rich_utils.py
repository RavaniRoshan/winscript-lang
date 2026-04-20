"""
winscript.rich_utils — Rich Console Utilities

Provides beautiful, styled output using Rich for the WinScript CLI.
Includes tables, panels, syntax highlighting, progress indicators, and animations.
"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich.columns import Columns
from rich.tree import Tree
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.style import Style
from rich.text import Text
from rich.align import Align
from rich.rule import Rule
from rich.markdown import Markdown
from rich import box
import time

# Global console instance
console = Console()

# Color theme
THEME = {
    "primary": "cyan",
    "success": "green",
    "error": "red",
    "warning": "yellow",
    "info": "blue",
    "muted": "dim",
    "accent": "magenta",
    "highlight": "bright_cyan",
}


def print_banner():
    """Print the WinScript animated banner."""
    banner = """
    ╭───────────────────────────────────────────────────────────────╮
    │                                                               │
    │   🪟  [bold cyan]WinScript[/bold cyan] [cyan]v2.1 — The Windows Automation Language[/cyan]     │
    │                                                               │
    │   [dim]Type WinScript to control any Windows application[/dim]           │
    │                                                               │
    ╰───────────────────────────────────────────────────────────────╯
    """
    console.print(banner)


def print_success(message: str, details: str = None):
    """Print a success message with a checkmark."""
    text = f"[bold {THEME['success']}]✓[/bold {THEME['success']}] {message}"
    if details:
        text += f"\n[dim]{details}[/dim]"
    console.print(text)


def print_error(message: str, details: str = None, hint: str = None):
    """Print an error message with styling."""
    text = f"[bold {THEME['error']}]✗[/bold {THEME['error']}] {message}"
    if details:
        text += f"\n[dim]{details}[/dim]"
    if hint:
        text += f"\n[{THEME['info']}ℹ {hint}[/]"
    console.print(text)


def print_warning(message: str, details: str = None):
    """Print a warning message."""
    text = f"[bold {THEME['warning']}]⚠[/bold {THEME['warning']}] {message}"
    if details:
        text += f"\n[dim]{details}[/dim]"
    console.print(text)


def print_info(message: str, emoji: str = "ℹ"):
    """Print an info message."""
    console.print(f"[{THEME['info']}]{emoji} {message}[/]")


def print_code(code: str, language: str = "winscript", title: str = None):
    """Print syntax-highlighted code."""
    syntax = Syntax(code, language, theme="monokai", line_numbers=True)
    panel = Panel(syntax, title=title or f"[bold]{language.title()}[/bold]", border_style=THEME["primary"])
    console.print(panel)


def print_dict_table(apps: list[dict]):
    """Print available app dictionaries in a beautiful table."""
    table = Table(
        title="[bold]Available Applications[/bold]",
        box=box.ROUNDED,
        border_style=THEME["primary"],
        header_style=f"bold {THEME['primary']}",
    )
    
    table.add_column("App", style=THEME["highlight"], no_wrap=True)
    table.add_column("Backend", style=THEME["muted"])
    table.add_column("Description", style="white")
    table.add_column("Path", style=THEME["muted"])
    
    for app in apps:
        table.add_row(
            app.get("name", "N/A"),
            app.get("backend", "N/A"),
            app.get("description", "")[:60] + "..." if len(app.get("description", "")) > 60 else app.get("description", ""),
            app.get("path", "N/A"),
        )
    
    console.print(table)


def print_session_table(sessions: list[dict]):
    """Print saved sessions in a table."""
    if not sessions:
        console.print(Panel(
            "[dim]No saved sessions found.[/dim]\n\n"
            "Use [cyan]save session \"name\"[/cyan] in your scripts to save state.",
            title="[bold]Saved Sessions[/bold]",
            border_style=THEME["muted"]
        ))
        return
    
    table = Table(
        title="[bold]Saved Sessions[/bold]",
        box=box.ROUNDED,
        border_style=THEME["primary"],
        header_style=f"bold {THEME['primary']}",
    )
    
    table.add_column("Name", style=THEME["highlight"])
    table.add_column("Created", style=THEME["muted"])
    table.add_column("Variables", justify="right", style="white")
    table.add_column("Functions", justify="right", style="white")
    
    for s in sessions:
        table.add_row(
            s.get("name", "N/A"),
            s.get("created_at", "Unknown")[:19],  # Trim to date
            str(s.get("variable_count", 0)),
            str(s.get("function_count", 0)),
        )
    
    console.print(table)


def print_app_commands(app_info: dict):
    """Print app commands in a tree structure."""
    tree = Tree(f"[bold {THEME['primary']}]🛠 {app_info.get('name', 'Unknown')}[/bold {THEME['primary']}]")
    tree.add(f"[dim]Backend:[/dim] {app_info.get('backend', 'N/A')}")
    tree.add(f"[dim]{app_info.get('description', 'No description')}[/dim]")
    
    if app_info.get("objects"):
        objects_node = tree.add("[bold]Objects[/bold]")
        for obj_name, obj in app_info["objects"].items():
            obj_node = objects_node.add(f"[cyan]{obj_name}[/cyan]")
            
            if obj.get("properties"):
                props_node = obj_node.add("[dim]Properties[/dim]")
                for prop in obj["properties"]:
                    props_node.add(f"[green]{prop['name']}[/green] ({prop['type']})")
            
            if obj.get("commands"):
                cmds_node = obj_node.add("[dim]Commands[/dim]")
                for cmd in obj["commands"]:
                    cmds_node.add(f"[magenta]{cmd['syntax']}[/magenta]")
    
    console.print(tree)


def print_variables(variables: dict):
    """Print variables in a styled table."""
    if not variables:
        console.print("[dim](no variables)[/dim]")
        return
    
    table = Table(
        box=box.SIMPLE,
        show_header=True,
        header_style=f"bold {THEME['primary']}",
    )
    table.add_column("Variable", style=THEME["highlight"])
    table.add_column("Value", style="white")
    table.add_column("Type", style=THEME["muted"])
    
    for name, value in variables.items():
        type_name = type(value).__name__
        value_str = repr(value)
        if len(value_str) > 50:
            value_str = value_str[:47] + "..."
        table.add_row(name, value_str, type_name)
    
    console.print(table)


def print_functions(functions: list[str]):
    """Print defined functions."""
    if not functions:
        console.print("[dim](no functions defined)[/dim]")
        return
    
    console.print("[bold]🔧 Defined Functions:[/bold]")
    for fn in functions:
        console.print(f"  [cyan]on {fn}()[/cyan]")


def create_spinner(message: str):
    """Create a spinner context manager."""
    return console.status(f"[bold {THEME['primary']}]{message}[/bold {THEME['primary']}]", spinner="dots")


def print_progress_bar(description: str, total: int = 100):
    """Create a progress bar."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(bar_width=40),
        TaskProgressColumn(),
        console=console,
    )


def print_validation_result(filepath: str, is_valid: bool, errors: list[str] = None):
    """Print validation result with styling."""
    if is_valid:
        print_success(f"{filepath} is valid WinScript", "Ready to execute!")
    else:
        print_error(f"{filepath} has errors", details="; ".join(errors) if errors else None)


def print_help_panel():
    """Print a beautiful help panel."""
    content = """
[b]WinScript Commands:[/b]

  [cyan]winscript script.ws[/cyan]              Run a script
  [cyan]winscript --validate script.ws[/cyan]    Validate without running
  [cyan]winscript --apps[/cyan]                   List available applications
  [cyan]winscript --commands Chrome[/cyan]        Show Chrome commands
  [cyan]winscript --list-sessions[/cyan]          List saved sessions
  [cyan]winscript --convert script.scpt[/cyan]    Convert AppleScript to WinScript
  [cyan]winscript --help[/cyan]                   Show full help

[b]REPL Commands:[/b]

  [cyan]:help[/cyan]        Show this help
  [cyan]:vars[/cyan]        Show all variables
  [cyan]:funcs[/cyan]       Show defined functions
  [cyan]:apps[/cyan]        List installed apps
  [cyan]:load <file>[/cyan] Execute a .ws file
  [cyan]:clear[/cyan]       Clear all variables
  [cyan]:quit[/cyan]        Exit REPL

[b]Quick Syntax:[/b]

  [green]tell Chrome[/green]                  Target an application
  [green]set x to "value"[/green]           Assign variable
  [green]return result[/green]              Return value
  [green]on myFunc(arg)[/green]            Define function
  [green]repeat 5 times[/green]            Loop
  [green]try / catch / end try[/green]    Error handling
    """
    
    panel = Panel(
        content,
        title="[bold]WinScript Help[/bold]",
        border_style=THEME["primary"],
        box=box.ROUNDED,
    )
    console.print(panel)


def print_chrome_setup_guide():
    """Print a comprehensive Chrome setup guide."""
    content = """
[b]Chrome Setup Guide for WinScript[/b]

WinScript uses Chrome DevTools Protocol (CDP) to control Chrome.

[u]Step 1: Start Chrome with debugging enabled[/u]

Windows:
  [dim]C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe --remote-debugging-port=9222[/dim]

macOS:
  [dim]/Applications/Google Chrome.app/Contents/MacOS/Google Chrome --remote-debugging-port=9222[/dim]

Linux:
  [dim]google-chrome --remote-debugging-port=9222[/dim]

[u]Step 2: Verify Chrome is accessible[/u]

  Open http://localhost:9222/json in your browser

[u]Step 3: Run your WinScript[/u]

  [cyan]winscript my_script.ws[/cyan]

[u]Chrome Variants Supported:[/u]

  • Google Chrome (google-chrome, chrome)
  • Microsoft Edge (msedge)
  • Brave Browser (brave)
  • Chromium (chromium)
  • Vivaldi (vivaldi)

[u]Troubleshooting:[/u]

  [yellow]⚠[/yellow] Port 9222 already in use? Kill process or use --remote-debugging-port=9223
  [yellow]⚠[/yellow] Permission denied? Run as administrator or check Chrome path
  [yellow]⚠[/yellow] Connection refused? Make sure Chrome started with the flag
    """
    
    panel = Panel(
        content,
        title="[bold]🔍 Chrome Setup Guide[/bold]",
        border_style=THEME["info"],
        box=box.ROUNDED,
    )
    console.print(panel)


def print_tip(message: str):
    """Print a helpful tip."""
    console.print(Panel(
        f"💡 {message}",
        border_style=THEME["accent"],
        box=box.SIMPLE,
    ))


def print_result(value: any):
    """Print a return value with nice formatting."""
    if value is None:
        console.print("[dim](no return value)[/dim]")
    elif isinstance(value, str):
        console.print(f"[green]→[/green] \"{value}\"")
    elif isinstance(value, (list, dict)):
        console.print_json(data=value)
    else:
        console.print(f"[green]→[/green] {repr(value)}")


def print_loading_animation(message: str, duration: float = 0.5):
    """Print a brief loading animation."""
    with console.status(f"[bold cyan]{message}[/bold cyan]", spinner="dots"):
        time.sleep(duration)


def format_error_with_context(error: Exception, source: str = None, line_no: int = None):
    """Format an error with context and suggestions."""
    error_msg = str(error)
    
    # Create error panel
    content = f"[bold red]{error.__class__.__name__}:[/bold red]\n\n{error_msg}"
    
    if line_no:
        content += f"\n\n[dim]Line {line_no}[/dim]"
    
    # Add suggestions based on error type
    suggestions = []
    if "outside tell" in error_msg.lower():
        suggestions.append("Commands must be inside a 'tell' block. Try: tell Chrome \n  <command>\nend tell")
    elif "not defined" in error_msg.lower():
        suggestions.append("Use 'declare' or 'local' to define variables before using them")
    elif "tell" in error_msg.lower() and "not found" in error_msg.lower():
        suggestions.append("Make sure the .wsdict file exists in dicts/ directory")
    
    if suggestions:
        content += "\n\n[yellow]💡 Suggestions:[/yellow]"
        for s in suggestions:
            content += f"\n  • {s}"
    
    panel = Panel(
        content,
        title="[bold red]✗ Error[/bold red]",
        border_style="red",
        box=box.ROUNDED,
    )
    console.print(panel)


class LivePanel:
    """A live-updating panel for showing execution progress."""
    
    def __init__(self, title: str = "Executing"):
        self.title = title
        self.lines = []
        self._live = None
    
    def __enter__(self):
        from rich.live import Live
        self._live = Live(self._render(), refresh_per_second=4)
        self._live.__enter__()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self._live.__exit__(exc_type, exc_val, exc_tb)
    
    def _render(self):
        content = "\n".join(self.lines[-20:])  # Show last 20 lines
        return Panel(
            content or "[dim]Starting...[/dim]",
            title=f"[bold]{self.title}[/bold]",
            border_style=THEME["primary"],
        )
    
    def log(self, message: str, level: str = "info"):
        """Add a log line."""
        colors = {"info": "cyan", "success": "green", "warning": "yellow", "error": "red"}
        color = colors.get(level, "white")
        self.lines.append(f"[{color}]{message}[/]")
        self._live.update(self._render())


def create_syntax_highlighted_prompt(code: str) -> Text:
    """Create a syntax-highlighted version of code for display."""
    lines = code.split('\n')
    result = Text()
    
    keywords = ['tell', 'end', 'set', 'return', 'if', 'then', 'else', 'try', 'catch', 
                'repeat', 'while', 'for', 'in', 'on', 'as', 'declare', 'global', 'local']
    
    for line in lines:
        words = line.split()
        for word in words:
            if word.lower() in keywords:
                result.append(word + ' ', style=f"bold {THEME['primary']}")
            elif word.startswith('"') or word.startswith("'"):
                result.append(word + ' ', style="green")
            elif word.isdigit():
                result.append(word + ' ', style="magenta")
            else:
                result.append(word + ' ')
        result.append('\n')
    
    return result
