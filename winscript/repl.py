import sys
from pathlib import Path

# ANSI colors
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
GREY   = "\033[90m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

BANNER = f"""
{BOLD}{CYAN}WinScript{RESET} {CYAN}interactive shell{RESET}
Type WinScript to control any Windows app.
:help for commands · :quit to exit
"""

OPEN_KEYWORDS = {"tell", "try", "repeat", "on", "if"}
CLOSE_KEYWORDS = {"end"}

def _count_open_blocks(lines: list[str]) -> int:
    """
    Count how many unclosed blocks exist in buffered lines.
    Simple heuristic: count open keywords vs close keywords.
    """
    depth = 0
    for line in lines:
        stripped = line.strip().lower()
        first_word = stripped.split()[0] if stripped else ""
        if first_word in OPEN_KEYWORDS:
            depth += 1
        elif first_word in CLOSE_KEYWORDS:
            depth -= 1
    return max(depth, 0)

def _is_complete(buffer: list[str]) -> bool:
    """Return True if the buffered input forms a complete statement."""
    if not buffer:
        return False
    return _count_open_blocks(buffer) == 0

def _prompt(depth: int) -> str:
    if depth == 0:
        return f"{CYAN}ws>{RESET} "
    return f"{CYAN}{'  ' * depth}...{RESET} "

class WinScriptREPL:
    def __init__(self, runtime):
        self.runtime = runtime
        self._context = None
        self._history: list[str] = []
        self._reset_context()

    def _reset_context(self):
        from winscript.context import ExecutionContext
        self._context = ExecutionContext()

    def run(self):
        print(BANNER)

        # Try readline for history support
        try:
            import readline
            readline.parse_and_bind("tab: complete")
        except ImportError:
            pass  # Windows — readline not available, still works

        buffer = []

        while True:
            depth = _count_open_blocks(buffer)
            try:
                line = input(_prompt(depth))
            except (EOFError, KeyboardInterrupt):
                print(f"\n{GREY}Bye.{RESET}")
                break

            # Special REPL commands (only valid at top level)
            if not buffer and line.startswith(":"):
                self._handle_command(line.strip())
                continue

            buffer.append(line)

            if not _is_complete(buffer):
                continue

            # Execute complete buffer
            source = "\n".join(buffer)
            buffer = []
            self._history.append(source)
            self._execute_repl_input(source)

    def _execute_repl_input(self, source: str):
        """
        Execute source in the persistent REPL context.
        Unlike runtime.execute(), this does NOT create a new context
        and does NOT close backends between inputs.
        """
        from winscript.parser import parse
        from winscript.ast_nodes import FunctionDef
        from winscript.errors import WinScriptError, WinScriptSyntaxError

        try:
            ast = parse(source)
        except WinScriptSyntaxError as e:
            print(f"{RED}Syntax error: {e}{RESET}")
            return

        try:
            # Register any new functions
            for stmt in ast.statements:
                if isinstance(stmt, FunctionDef):
                    self._context.register_function(stmt)
                    print(f"{GREY}Function '{stmt.name}' defined.{RESET}")

            # Execute non-function statements
            self.runtime._execute_statements(
                [s for s in ast.statements if not isinstance(s, FunctionDef)],
                self._context
            )

            # Show return value if set
            if self._context.has_returned:
                result = self._context.return_value
                print(f"{GREEN}→ {result!r}{RESET}")
                # Reset return for next input (but keep variables)
                self._context._returned = False
                self._context._return_value = None

        except WinScriptError as e:
            print(f"{RED}Error: {e}{RESET}")
        except Exception as e:
            print(f"{RED}Unexpected error: {e}{RESET}")

    def _handle_command(self, cmd: str):
        parts = cmd.split(maxsplit=1)
        command = parts[0]
        arg = parts[1] if len(parts) > 1 else ""

        if command == ":quit":
            self._context.close_all_backends()
            print(f"{GREY}Bye.{RESET}")
            sys.exit(0)

        elif command == ":clear":
            self._reset_context()
            print(f"{GREY}Context cleared.{RESET}")

        elif command == ":vars":
            scope = self._context.global_scope
            if not scope._vars:
                print(f"{GREY}(no variables){RESET}")
            else:
                for name, value in scope._vars.items():
                    print(f"  {CYAN}{name}{RESET} = {value!r}")

        elif command == ":funcs":
            funcs = self._context.list_functions()
            if not funcs:
                print(f"{GREY}(no functions defined){RESET}")
            else:
                for fn in funcs:
                    print(f"  {CYAN}on {fn}(){RESET}")

        elif command == ":apps":
            print(self.runtime.dict_loader.list_all_formatted())

        elif command == ":load":
            if not arg:
                print(f"{RED}Usage: :load <script.ws>{RESET}")
                return
            path = Path(arg)
            if not path.exists():
                print(f"{RED}File not found: {arg}{RESET}")
                return
            source = path.read_text(encoding="utf-8")
            print(f"{GREY}Loading {arg}...{RESET}")
            self._execute_repl_input(source)

        elif command == ":help":
            print(f"""
{BOLD}WinScript REPL Commands:{RESET}
  :quit          Exit the REPL
  :clear         Clear all variables and functions
  :vars          Show all current variables
  :funcs         Show all defined functions
  :apps          List installed app dictionaries
  :load <file>   Execute a .ws file into current context
  :help          Show this help

{BOLD}WinScript Syntax:{RESET}
  tell Chrome / navigate to "url" / end tell
  set x to value
  return expression
  on myFunc(arg) / ... / end on
  repeat 5 times / ... / end repeat
""")
        else:
            print(f"{RED}Unknown command: {command}. Try :help{RESET}")

def launch_repl(runtime):
    repl = WinScriptREPL(runtime)
    repl.run()
