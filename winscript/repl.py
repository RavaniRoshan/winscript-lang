"""
winscript.repl — Rich Interactive REPL

A beautiful, feature-rich REPL with syntax highlighting, animations,
auto-completion, and rich output formatting.
"""

import sys
from pathlib import Path
from typing import Optional, List

from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree
from rich.align import Align
from rich import box

from winscript.rich_utils import (
    console, print_banner, print_success, print_error, print_warning,
    print_info, print_variables, print_functions, print_code,
    THEME, create_syntax_highlighted_prompt
)


# Syntax highlighting keywords
KEYWORDS = {
    'tell', 'end', 'set', 'return', 'if', 'then', 'else',
    'try', 'catch', 'repeat', 'while', 'for', 'in', 'times',
    'on', 'as', 'declare', 'global', 'local', 'using',
    'wait', 'until', 'loaded', 'contains', 'is',
}

COMMANDS = {
    'navigate', 'click', 'type', 'press', 'open', 'close',
    'quit', 'run', 'script', 'screenshot', 'save',
}


def highlight_code(code: str) -> str:
    """Add syntax highlighting to code."""
    result = code
    # This is a simple highlighting - proper highlighting would use lexer
    return result


def get_prompt(depth: int) -> str:
    """Get styled prompt based on block depth."""
    if depth == 0:
        return f"[bold {THEME['primary']}]ws›[/bold {THEME['primary']}] "
    else:
        return f"[dim]{' ' * (depth * 2)}...[/dim] "


class RichWinScriptREPL:
    """Rich-enhanced WinScript REPL."""
    
    def __init__(self, runtime):
        self.runtime = runtime
        self._context = None
        self._history: List[str] = []
        self._reset_context()
        
        # REPL state
        self.buffer: List[str] = []
        self.multi_line_mode = False
        
    def _reset_context(self):
        """Reset the execution context."""
        from winscript.context import ExecutionContext
        self._context = ExecutionContext()
    
    def run(self):
        """Run the REPL main loop."""
        print_banner()
        
        # Print welcome tip
        print_info("Type :help for commands, :quit to exit")
        console.print()
        
        # Try to enable readline
        self._setup_readline()
        
        while True:
            try:
                depth = self._count_open_blocks(self.buffer)
                prompt = get_prompt(depth)
                
                # Get input
                line = console.input(prompt)
                
            except (EOFError, KeyboardInterrupt):
                console.print(f"\n[dim]👋 Goodbye![/dim]")
                break
            
            # Handle REPL commands
            if not self.buffer and line.startswith(":"):
                self._handle_command(line.strip())
                continue
            
            # Add to buffer
            self.buffer.append(line)
            
            # Check if complete
            if not self._is_complete(self.buffer):
                continue
            
            # Execute complete statement
            source = "\n".join(self.buffer)
            self.buffer = []
            self._history.append(source)
            
            # Execute with animation
            self._execute(source)
    
    def _setup_readline(self):
        """Setup readline for history support."""
        try:
            import readline
            readline.parse_and_bind("tab: complete")
            
            # History file
            import os
            histfile = Path.home() / ".winscript_history"
            if histfile.exists():
                readline.read_history_file(str(histfile))
        except ImportError:
            pass
    
    def _count_open_blocks(self, lines: List[str]) -> int:
        """Count unclosed blocks."""
        depth = 0
        for line in lines:
            stripped = line.strip().lower()
            first_word = stripped.split()[0] if stripped else ""
            
            if first_word in ('tell', 'try', 'repeat', 'on', 'if'):
                depth += 1
            elif first_word == 'end':
                depth -= 1
        
        return max(depth, 0)
    
    def _is_complete(self, buffer: List[str]) -> bool:
        """Check if the buffer forms a complete statement."""
        return self._count_open_blocks(buffer) == 0
    
    def _execute(self, source: str):
        """Execute source code with rich output."""
        from winscript.parser import parse
        from winscript.ast_nodes import FunctionDef, ReturnStatement
        from winscript.errors import WinScriptError, WinScriptSyntaxError
        
        try:
            # Show parsing animation
            with console.status("[cyan]Parsing...[/cyan]", spinner="dots"):
                ast = parse(source)
        except WinScriptSyntaxError as e:
            print_error("Syntax Error", details=str(e))
            return
        
        # Register functions
        registered_functions = []
        for stmt in ast.statements:
            if isinstance(stmt, FunctionDef):
                self._context.register_function(stmt)
                registered_functions.append(stmt.name)
        
        if registered_functions:
            for fn in registered_functions:
                print_info(f"Function '{fn}' defined", emoji="🔧")
        
        # Execute statements
        try:
            with console.status("[cyan]Executing...[/cyan]", spinner="dots"):
                self.runtime._execute_statements(
                    [s for s in ast.statements if not isinstance(s, FunctionDef)],
                    self._context
                )
            
            # Show return value
            if self._context.has_returned:
                result = self._context.return_value
                console.print()
                
                if result is None:
                    console.print("[dim](no return value)[/dim]")
                elif isinstance(result, str):
                    console.print(f"[green]→[/green] \"[green]{result}[/green]\"")
                elif isinstance(result, (int, float)):
                    console.print(f"[green]→[/green] [magenta]{result}[/magenta]")
                elif isinstance(result, bool):
                    console.print(f"[green]→[/green] [cyan]{result}[/cyan]")
                elif isinstance(result, list):
                    console.print(f"[green]→[/green] [magenta]{result}[/magenta]")
                else:
                    console.print(f"[green]→[/green] {repr(result)}")
                
                # Reset for next execution
                self._context._returned = False
                self._context._return_value = None
        
        except WinScriptError as e:
            print_error("Runtime Error", details=str(e))
        except Exception as e:
            print_error("Unexpected Error", details=str(e))
    
    def _handle_command(self, cmd: str):
        """Handle REPL commands."""
        parts = cmd.split(maxsplit=1)
        command = parts[0] if parts else ""
        arg = parts[1] if len(parts) > 1 else ""
        
        if command == ":quit" or command == ":q":
            console.print("[dim]👋 Goodbye![/dim]")
            sys.exit(0)
        
        elif command == ":clear" or command == ":c":
            self._reset_context()
            print_success("Context cleared", "All variables and functions removed")
        
        elif command == ":vars" or command == ":v":
            self._show_variables()
        
        elif command == ":funcs" or command == ":f":
            self._show_functions()
        
        elif command == ":apps":
            self._show_apps()
        
        elif command == ":load":
            self._load_file(arg)
        
        elif command == ":save":
            self._save_session(arg)
        
        elif command == ":help" or command == ":h":
            self._show_help()
        
        elif command == ":history":
            self._show_history()
        
        else:
            print_error(f"Unknown command: {command}", hint="Try :help for available commands")
    
    def _show_variables(self):
        """Show current variables in a table."""
        variables = {}
        scope = self._context.global_scope
        
        for name in scope._vars:
            if not name.startswith("__"):
                variables[name] = scope._vars[name]
        
        if not variables:
            console.print("[dim](no variables defined)[/dim]")
            return
        
        print_variables(variables)
    
    def _show_functions(self):
        """Show defined functions."""
        funcs = self._context.list_functions()
        print_functions(funcs)
    
    def _show_apps(self):
        """Show available applications."""
        console.print("[bold]Available Applications:[/bold]\n")
        
        table = Table(
            box=box.ROUNDED,
            border_style=THEME["primary"]
        )
        table.add_column("App", style=THEME["highlight"])
        table.add_column("Backend", style="dim")
        table.add_column("Description")
        
        # Add known apps
        apps = [
            ("Chrome", "cdp", "Full Chrome automation via CDP"),
            ("Excel", "com", "Microsoft Excel via COM"),
        ]
        
        for name, backend, desc in apps:
            table.add_row(name, backend, desc)
        
        console.print(table)
    
    def _load_file(self, filepath: str):
        """Load and execute a script file."""
        if not filepath:
            print_error("Usage: :load <file.ws>")
            return
        
        path = Path(filepath)
        if not path.exists():
            print_error(f"File not found: {filepath}")
            return
        
        console.print(f"[dim]Loading {filepath}...[/dim]")
        source = path.read_text(encoding="utf-8")
        
        # Show loaded code
        print_code(source, language="winscript", title=f"Loaded: {path.name}")
        
        # Execute
        self._execute(source)
    
    def _save_session(self, name: str):
        """Save current session."""
        if not name:
            print_error("Usage: :save <session_name>")
            return
        
        # Save using session manager
        backend_states = {}
        for app_name, backend in self.runtime.dispatcher._backends.items():
            if hasattr(backend, 'get_state'):
                try:
                    backend_states[app_name] = backend.get_state()
                except Exception:
                    pass
        
        self.runtime.session_manager.save_session(name, self._context, backend_states)
        print_success(f"Session '{name}' saved")
    
    def _show_help(self):
        """Show REPL help."""
        content = """
[bold cyan]REPL Commands:[/bold cyan]

  :help, :h              Show this help
  :quit, :q              Exit the REPL
  :clear, :c             Clear all variables and functions
  :vars, :v              Show all variables
  :funcs, :f             Show defined functions
  :apps                  List available applications
  :load <file>           Execute a .ws file
  :save <name>           Save session to file
  :history               Show command history

[bold cyan]Quick Examples:[/bold cyan]

  [green]tell Chrome[/green]
  [green]  navigate to "https://github.com"[/green]
  [green]  return title of active tab[/green]
  [green]end tell[/green]

  [green]on greet(name)[/green]
  [green]  return "Hello " & name[/green]
  [green]end on[/green]

  [green]repeat 5 times[/green]
  [green]  -- do something[/green]
  [green]end repeat[/green]
"""
        panel = Panel(
            content,
            title="[bold]WinScript REPL Help[/bold]",
            border_style=THEME["primary"],
            box=box.ROUNDED
        )
        console.print(panel)
    
    def _show_history(self):
        """Show command history."""
        if not self._history:
            console.print("[dim](no history yet)[/dim]")
            return
        
        console.print("[bold]Command History:[/bold]\n")
        for i, cmd in enumerate(self._history, 1):
            lines = cmd.split('\n')
            first_line = lines[0][:50]
            if len(lines) > 1:
                first_line += " ..."
            console.print(f"  [dim]{i:3}[/dim] [cyan]{first_line}[/cyan]")


def launch_repl(runtime):
    """Launch the Rich-enhanced REPL."""
    repl = RichWinScriptREPL(runtime)
    repl.run()
