"""
winscript.debugger — Interactive Debugger with Breakpoints

Provides step-through debugging, breakpoints, watch expressions,
and variable inspection for WinScript execution.

Usage:
    winscript script.ws --debug
    
    Debugger commands:
    (b)reak <line>    - Set breakpoint at line
    (c)ontinue       - Continue execution
    (s)tep           - Step to next line
    (n)ext           - Step over (don't enter functions)
    (p)rint <var>    - Print variable value
    (w)atch <expr>   - Add watch expression
    (q)uit           - Quit debugger
    (h)elp           - Show help
"""

import sys
import threading
from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum, auto

from winscript.ast_nodes import *
from winscript.context import ExecutionContext


class DebugAction(Enum):
    """Debugger control flow actions."""
    CONTINUE = auto()      # Continue execution normally
    STEP = auto()          # Step to next statement
    STEP_OVER = auto()    # Step over function calls
    STEP_OUT = auto()      # Step out of current function
    PAUSE = auto()         # Pause at next statement


@dataclass
class Breakpoint:
    """Represents a breakpoint in the source code."""
    line: int
    condition: Optional[str] = None  # Optional condition expression
    hit_count: int = 0
    enabled: bool = True
    
    def should_break(self, context: ExecutionContext) -> bool:
        """Check if breakpoint should trigger."""
        if not self.enabled:
            return False
        self.hit_count += 1
        # TODO: Evaluate condition if present
        return True


@dataclass
class WatchExpression:
    """A watch expression to monitor during execution."""
    expr: str
    last_value: Any = None
    
    def check_change(self, current_value: Any) -> bool:
        """Check if value changed since last check."""
        changed = current_value != self.last_value
        self.last_value = current_value
        return changed


class WinScriptDebugger:
    """
    Interactive debugger for WinScript execution.
    
    Provides:
    - Line-by-line stepping
    - Breakpoint management
    - Variable inspection
    - Watch expressions
    - Call stack tracking
    """
    
    def __init__(self):
        self.breakpoints: dict[int, Breakpoint] = {}
        self.watch_expressions: list[WatchExpression] = []
        self.call_stack: list[dict] = []
        self.current_line: int = 0
        self.current_statement: Any = None
        self.step_depth: int = 0
        self.target_depth: int = 0
        self.action: DebugAction = DebugAction.CONTINUE
        self.paused: bool = False
        self.paused_event = threading.Event()
        self.output_buffer: list[str] = []
        self.interactive: bool = True
        
    def add_breakpoint(self, line: int, condition: Optional[str] = None) -> Breakpoint:
        """Add a breakpoint at the specified line."""
        bp = Breakpoint(line=line, condition=condition)
        self.breakpoints[line] = bp
        return bp
    
    def remove_breakpoint(self, line: int) -> bool:
        """Remove breakpoint at the specified line."""
        if line in self.breakpoints:
            del self.breakpoints[line]
            return True
        return False
    
    def clear_breakpoints(self):
        """Remove all breakpoints."""
        self.breakpoints.clear()
    
    def add_watch(self, expr: str) -> WatchExpression:
        """Add a watch expression."""
        watch = WatchExpression(expr=expr)
        self.watch_expressions.append(watch)
        return watch
    
    def remove_watch(self, expr: str) -> bool:
        """Remove a watch expression."""
        for i, w in enumerate(self.watch_expressions):
            if w.expr == expr:
                self.watch_expressions.pop(i)
                return True
        return False
    
    def push_frame(self, name: str, line: int = 0):
        """Push a new stack frame."""
        self.call_stack.append({
            "name": name,
            "line": line,
            "locals": {}
        })
        self.step_depth += 1
    
    def pop_frame(self):
        """Pop the current stack frame."""
        if self.call_stack:
            self.call_stack.pop()
            self.step_depth -= 1
    
    def should_pause(self, line: int, context: ExecutionContext) -> bool:
        """Determine if execution should pause at this line."""
        # Check for breakpoint
        if line in self.breakpoints:
            bp = self.breakpoints[line]
            if bp.should_break(context):
                return True
        
        # Check for step actions
        if self.action == DebugAction.STEP:
            return True
        elif self.action == DebugAction.STEP_OVER:
            if self.step_depth <= self.target_depth:
                return True
        elif self.action == DebugAction.STEP_OUT:
            if self.step_depth < self.target_depth:
                return True
        
        return False
    
    def pause(self, line: int, statement: Any, context: ExecutionContext):
        """Pause execution and enter interactive mode."""
        self.current_line = line
        self.current_statement = statement
        self.paused = True
        
        if self.interactive:
            self._interactive_loop(context)
        else:
            # Non-interactive: just report and continue
            self._report_state(context)
            self.paused = False
    
    def _get_line_number(self, node: Any) -> int:
        """Extract line number from AST node if available."""
        # Lark doesn't preserve line numbers by default in transformed tree
        # This is a placeholder - would need to modify parser to preserve line info
        return getattr(node, "line", 0)
    
    def _format_value(self, value: Any) -> str:
        """Format a value for display."""
        if isinstance(value, str):
            return f'"{value}"'
        if isinstance(value, list):
            return f"[{', '.join(self._format_value(v) for v in value)}]"
        return str(value)
    
    def _report_state(self, context: ExecutionContext):
        """Report current execution state."""
        print(f"\n{'─' * 60}")
        print(f"  Line {self.current_line}: {type(self.current_statement).__name__}")
        print(f"{'─' * 60}")
        
        # Show call stack
        if self.call_stack:
            print("\n  Call Stack:")
            for i, frame in enumerate(reversed(self.call_stack)):
                print(f"    {i}: {frame['name']} (line {frame['line']})")
        
        # Show current scope variables
        print("\n  Variables:")
        try:
            # Get variables from current scope
            scope_vars = {}
            for name in context.current_scope._vars:
                if not name.startswith("__"):
                    scope_vars[name] = context.current_scope._vars[name]
            
            if scope_vars:
                for name, value in sorted(scope_vars.items()):
                    formatted = self._format_value(value)
                    print(f"    {name} = {formatted}")
            else:
                print("    (no variables)")
        except Exception as e:
            print(f"    (error reading variables: {e})")
        
        # Show global variables
        print("\n  Global Variables:")
        try:
            global_vars = {}
            for name in context.global_scope._vars:
                if not name.startswith("__"):
                    global_vars[name] = context.global_scope._vars[name]
            
            if global_vars:
                for name, value in sorted(global_vars.items())[:10]:  # Limit to 10
                    formatted = self._format_value(value)
                    print(f"    {name} = {formatted}")
                if len(global_vars) > 10:
                    print(f"    ... and {len(global_vars) - 10} more")
            else:
                print("    (no global variables)")
        except Exception as e:
            print(f"    (error reading globals: {e})")
        
        print(f"{'─' * 60}\n")
    
    def _interactive_loop(self, context: ExecutionContext):
        """Interactive debugging loop."""
        self._report_state(context)
        
        while self.paused:
            try:
                cmd = input("  (wsdb) ").strip().lower()
            except EOFError:
                cmd = "quit"
            
            if not cmd:
                continue
            
            parts = cmd.split(None, 1)
            action = parts[0] if parts else ""
            arg = parts[1] if len(parts) > 1 else ""
            
            if action in ("c", "continue", "run"):
                self.action = DebugAction.CONTINUE
                self.paused = False
                
            elif action in ("s", "step"):
                self.action = DebugAction.STEP
                self.target_depth = self.step_depth
                self.paused = False
                
            elif action in ("n", "next"):
                self.action = DebugAction.STEP_OVER
                self.target_depth = self.step_depth
                self.paused = False
                
            elif action in ("o", "out"):
                self.action = DebugAction.STEP_OUT
                self.target_depth = self.step_depth
                self.paused = False
                
            elif action in ("b", "break"):
                if arg:
                    try:
                        line = int(arg)
                        self.add_breakpoint(line)
                        print(f"  Breakpoint set at line {line}")
                    except ValueError:
                        print(f"  Error: Invalid line number '{arg}'")
                else:
                    print("  Usage: break <line>")
                    
            elif action in ("d", "delete"):
                if arg:
                    try:
                        line = int(arg)
                        if self.remove_breakpoint(line):
                            print(f"  Breakpoint removed from line {line}")
                        else:
                            print(f"  No breakpoint at line {line}")
                    except ValueError:
                        print(f"  Error: Invalid line number '{arg}'")
                else:
                    print("  Usage: delete <line>")
                    
            elif action in ("l", "list"):
                if self.breakpoints:
                    print("  Breakpoints:")
                    for line, bp in sorted(self.breakpoints.items()):
                        status = "enabled" if bp.enabled else "disabled"
                        cond = f" (condition: {bp.condition})" if bp.condition else ""
                        print(f"    Line {line} [{status}] {cond}")
                else:
                    print("  No breakpoints set")
                    
            elif action in ("p", "print"):
                if arg:
                    try:
                        value = context.get_var(arg)
                        print(f"  {arg} = {self._format_value(value)}")
                    except Exception as e:
                        print(f"  Error: {e}")
                else:
                    print("  Usage: print <variable>")
                    
            elif action in ("w", "watch"):
                if arg:
                    self.add_watch(arg)
                    print(f"  Watching expression: {arg}")
                else:
                    if self.watch_expressions:
                        print("  Watch expressions:")
                        for w in self.watch_expressions:
                            print(f"    {w.expr}")
                    else:
                        print("  No watch expressions")
                        
            elif action in ("q", "quit", "exit"):
                print("  Quitting debugger...")
                sys.exit(0)
                
            elif action in ("h", "help", "?"):
                self._print_help()
                
            else:
                print(f"  Unknown command: '{action}'. Type 'help' for commands.")
    
    def _print_help(self):
        """Print debugger help."""
        print("""
  Debugger Commands:
    (c)ontinue           Resume execution until next breakpoint
    (s)tep               Step to next statement (enter functions)
    (n)ext               Step over function calls
    (o)ut                Step out of current function
    (b)reak <line>       Set breakpoint at line
    (d)elete <line>      Remove breakpoint at line
    (l)ist               List all breakpoints
    (p)rint <var>        Print variable value
    (w)atch <expr>       Add watch expression
    (q)uit               Quit debugger
    (h)elp               Show this help
        """)


class DebugRuntime:
    """
    Debugging wrapper for WinScriptRuntime.
    Integrates the debugger with script execution.
    """
    
    def __init__(self, runtime):
        self.runtime = runtime
        self.debugger = WinScriptDebugger()
        self._original_execute_statement = None
    
    def enable(self):
        """Enable debugging by wrapping the execute_statement method."""
        # This would require modifying Runtime to check debugger before each statement
        # For now, we'll provide a hook-based approach
        pass
    
    def disable(self):
        """Disable debugging."""
        pass
