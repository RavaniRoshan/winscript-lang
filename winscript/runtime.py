"""
winscript.runtime — The main WinScript script executor.

Orchestrates the full pipeline:  source code → parse → walk AST → resolve
commands via .wsdict → dispatch to backends → return result.

Usage:
    from winscript.runtime import WinScriptRuntime

    runtime = WinScriptRuntime(extra_dict_paths=["./dicts"])
    result = runtime.execute('''
        tell Chrome
            navigate to "https://github.com"
            wait until loaded
            return title of active tab
        end tell
    ''')
    print(result)  # "GitHub"
"""

import time
from typing import Any

from winscript.ast_nodes import (
    BoolLiteral,
    CommandStatement,
    ConcatExpr,
    Condition,
    Identifier,
    IfStatement,
    NumberLiteral,
    PropertyAccess,
    ReturnStatement,
    SetStatement,
    StringLiteral,
    TellBlock,
    TryBlock,
    WaitDurationStatement,
    WaitUntilStatement,
    FunctionDef,
    FunctionCall,
    ScopeDeclaration,
    DeclareStatement,
    UsingStatement,
    RepeatTimesBlock,
    RepeatWhileBlock,
    RepeatWithBlock,
    ListLiteral,
    ArithExpr,
    SessionSaveStatement,
    SessionLoadStatement,
)
from winscript.context import ExecutionContext
from winscript.dicts.loader import DictLoader
from winscript.dispatcher import Dispatcher
from winscript.errors import (
    WinScriptError,
    WinScriptSyntaxError,
    WinScriptTimeoutError,
)
from winscript.parser import parse, validate_v2
from winscript.resolver import Resolver
from winscript.types import WSType


from winscript.library import LibraryLoader
from winscript.session import SessionManager

class WinScriptRuntime:
    """
    Top-level entry point for executing WinScript source code.

    Manages the full lifecycle: parsing, AST walking, dictionary resolution,
    backend dispatch, and cleanup.
    """

    def __init__(self, extra_dict_paths: list[str] | None = None):
        self.dict_loader = DictLoader(extra_dict_paths)
        self.resolver = Resolver(self.dict_loader)
        self.dispatcher = Dispatcher()
        self.session_manager = SessionManager()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def execute(self, source_code: str, script_path: str | None = None) -> Any:
        """
        Full pipeline: parse → execute AST → return result.

        Always closes backend connections on completion or error.
        Returns the value passed to ``return`` in the script, or None.
        """
        try:
            ast = parse(source_code)
            context = ExecutionContext()
            
            # FIRST: load libraries
            self._load_libraries(ast.statements, context, script_path)
            
            # SECOND: register all script functions (can override library functions)
            self._register_functions(ast.statements, context)
            
            # THEN: execute statements (skip FunctionDef — already registered)
            self._execute_statements(ast.statements, context)
            return context.return_value
        finally:
            self.dispatcher.close_all()

    def validate(self, source_code: str) -> list[str]:
        """
        Parse-only validation. Returns a list of error strings (empty = valid).
        Does not execute anything.
        """
        errors: list[str] = []
        try:
            ast = parse(source_code)
            errors.extend(validate_v2(ast))
        except WinScriptSyntaxError as e:
            errors.append(str(e))
        return errors

    def parse(self, source_code: str) -> Any:
        """Parse source code into AST directly. Raises exception on error."""
        ast = parse(source_code)
        errors = validate_v2(ast)
        if errors:
            raise WinScriptSyntaxError("; ".join(errors))
        return ast

    def get_app_commands(self, app_name: str) -> str:
        """Show all commands and properties for an app."""
        app_dict = self.dict_loader.load(app_name)
        lines = [
            f"{app_dict.display_name} (backend: {app_dict.backend})",
            f"  {app_dict.description.strip()}",
            "",
        ]
        for obj_name, obj in app_dict.objects.items():
            root_marker = " [ROOT]" if obj.is_root else ""
            lines.append(f"Object: {obj_name}{root_marker}")
            lines.append(f"  {obj.description.strip()}")
            if obj.properties:
                lines.append("  Properties:")
                for prop in obj.properties:
                    lines.append(f"    {prop.name} ({prop.type}) — {prop.description}")
            if obj.commands:
                lines.append("  Commands:")
                for cmd in obj.commands:
                    lines.append(f"    {cmd.syntax}")
                    if cmd.description:
                        desc = cmd.description.strip().split("\n")[0]
                        lines.append(f"      {desc}")
            lines.append("")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # AST walker
    # ------------------------------------------------------------------

    def _load_libraries(self, statements: list, context: ExecutionContext, script_path: str | None = None) -> None:
        from pathlib import Path
        script_dir = Path(script_path).parent if script_path else None
        loader = LibraryLoader(script_dir=script_dir)
        for stmt in statements:
            if isinstance(stmt, UsingStatement):
                lib_functions = loader.load(stmt.path)
                for fn in lib_functions:
                    fn_copy = FunctionDef(
                        name=fn.name,
                        params=fn.params,
                        statements=fn.statements,
                        is_library=True
                    )
                    context.register_function(fn_copy)

    def _register_functions(self, statements: list, context: ExecutionContext) -> None:
        for stmt in statements:
            if isinstance(stmt, FunctionDef):
                context.register_function(stmt)

    def _execute_statements(self, statements: list, context: ExecutionContext) -> None:
        """Walk a list of statements, stopping early if ``return`` was hit."""
        for stmt in statements:
            if context.has_returned:
                break
            self._execute_statement(stmt, context)

    def _execute_statement(self, stmt: Any, context: ExecutionContext) -> None:
        """Dispatch a single AST statement node to the correct handler."""
        if isinstance(stmt, TellBlock):
            self._exec_tell(stmt, context)
        elif isinstance(stmt, SetStatement):
            self._exec_set(stmt, context)
        elif isinstance(stmt, ReturnStatement):
            self._exec_return(stmt, context)
        elif isinstance(stmt, WaitUntilStatement):
            self._exec_wait_until(stmt, context)
        elif isinstance(stmt, WaitDurationStatement):
            self._exec_wait_duration(stmt, context)
        elif isinstance(stmt, TryBlock):
            self._exec_try(stmt, context)
        elif isinstance(stmt, IfStatement):
            self._exec_if(stmt, context)
        elif isinstance(stmt, CommandStatement):
            self._exec_command(stmt, context)
        elif isinstance(stmt, FunctionDef):
            pass  # already registered in first pass, skip during execution
        elif isinstance(stmt, FunctionCall):
            self._exec_function_call(stmt, context)
        elif isinstance(stmt, ScopeDeclaration):
            self._exec_scope_declaration(stmt, context)
        elif isinstance(stmt, DeclareStatement):
            self._exec_declare(stmt, context)
        elif isinstance(stmt, UsingStatement):
            pass
        elif isinstance(stmt, SessionSaveStatement):
            self._exec_session_save(stmt, context)
        elif isinstance(stmt, SessionLoadStatement):
            self._exec_session_load(stmt, context)
        elif isinstance(stmt, RepeatTimesBlock):
            self._exec_repeat_times(stmt, context)
        elif isinstance(stmt, RepeatWhileBlock):
            self._exec_repeat_while(stmt, context)
        elif isinstance(stmt, RepeatWithBlock):
            self._exec_repeat_with(stmt, context)
        else:
            raise WinScriptError(f"Unknown statement type: {type(stmt).__name__}")

    # ------------------------------------------------------------------
    # Statement handlers
    # ------------------------------------------------------------------

    def _exec_tell(self, node: TellBlock, context: ExecutionContext) -> None:
        """
        Enter a tell block: load the .wsdict, push the tell scope,
        execute inner statements, then pop the scope.
        """
        if context.current_app:
            parent_app = context.current_app
            app_dict = context.get_var(f"__dict_{parent_app}")
            
            parts = node.app_name.split(' ', 1)
            obj_type = parts[0]
            identifier = parts[1].strip('"').strip("'") if len(parts) > 1 else ""
            
            matched_obj = None
            for obj_name, obj in app_dict.objects.items():
                if obj_name.lower() == obj_type.lower():
                    matched_obj = obj
                    break
                    
            if matched_obj:
                backend = self.dispatcher._backends.get(parent_app)
                if not backend:
                    from winscript.resolver import ResolvedAction
                    dummy = ResolvedAction(
                        backend_type=app_dict.backend,
                        backend_method="",
                        backend_expression="",
                        args={},
                        app_name=parent_app,
                        connection_info=app_dict.connection
                    )
                    backend = self.dispatcher._get_backend(dummy)

                if hasattr(backend, "push_context"):
                    backend.push_context(obj_type, identifier)
                    prev_obj = context.get_var(f"__obj_{parent_app}")
                    context.set_var(f"__obj_{parent_app}", matched_obj)
                    try:
                        self._execute_statements(node.statements, context)
                    finally:
                        backend.pop_context()
                        context.set_var(f"__obj_{parent_app}", prev_obj)
                    return

        app_dict, root_object = self.resolver.resolve_tell(node.app_name)
        context.push_tell(node.app_name)
        context.set_var(f"__dict_{node.app_name}", app_dict)
        context.set_var(f"__obj_{node.app_name}", root_object)
        try:
            self._execute_statements(node.statements, context)
        finally:
            context.pop_tell()

    def _exec_set(self, node: SetStatement, context: ExecutionContext) -> None:
        """Evaluate the RHS expression and assign to the target variable."""
        value = self._eval_expression(node.value, context)
        if isinstance(node.target, str):
            context.set_var(node.target, value)
        elif isinstance(node.target, PropertyAccess):
            if node.target.prop == "value" and isinstance(node.target.of_expr, PropertyAccess) and node.target.of_expr.prop == "cell":
                cell_name = self._eval_expression(node.target.of_expr.of_expr, context)
                app_name = context.current_app
                app_dict = context.get_var(f"__dict_{app_name}")
                current_object = context.get_var(f"__obj_{app_name}")
                action = self.resolver.resolve_command(
                    app_dict, current_object, "set_value_of_cell", {"cell": cell_name, "value": value}
                )
                self.dispatcher.execute(action, context)
            else:
                # Property mutation — not supported in v1 generally
                raise WinScriptError(
                    "Setting properties on objects is not supported in WinScript v1."
                )
        else:
            context.set_var(str(node.target), value)

    def _exec_return(self, node: ReturnStatement, context: ExecutionContext) -> None:
        """Evaluate the return value and mark the context as returned."""
        value = self._eval_expression(node.value, context)
        context.set_return(value)

    def _exec_wait_until(self, node: WaitUntilStatement, context: ExecutionContext) -> None:
        """Poll the condition every 500 ms until true or timeout."""
        deadline = time.time() + (node.timeout_ms / 1000)
        while time.time() < deadline:
            if self._eval_condition(node.condition, context):
                return
            time.sleep(0.5)
        raise WinScriptTimeoutError(str(node.condition), node.timeout_ms)

    def _exec_wait_duration(self, node: WaitDurationStatement, context: ExecutionContext) -> None:
        """Sleep for the specified duration."""
        time.sleep(node.duration_ms / 1000)

    def _exec_try(self, node: TryBlock, context: ExecutionContext) -> None:
        """
        Execute the try block. On WinScriptError, set the catch variable
        to the error message and execute the catch block.
        """
        try:
            self._execute_statements(node.try_stmts, context)
        except WinScriptError as e:
            context.set_var(node.catch_var, str(e))
            self._execute_statements(node.catch_stmts, context)

    def _exec_if(self, node: IfStatement, context: ExecutionContext) -> None:
        """Evaluate the condition; execute the then block if truthy."""
        if self._eval_condition(node.condition, context):
            self._execute_statements(node.then_stmts, context)

    def _exec_command(self, node: CommandStatement, context: ExecutionContext) -> None:
        """
        Resolve and dispatch a command to the appropriate backend.
        The command must be inside a tell block.
        """
        if not context.current_app:
            raise WinScriptError(
                f"Command '{node.name}' outside tell block. "
                "Wrap commands in 'tell AppName ... end tell'."
            )

        app_name = context.current_app
        app_dict = context.get_var(f"__dict_{app_name}")
        current_object = context.get_var(f"__obj_{app_name}")

        # Resolve kwargs (AST nodes → Python values)
        resolved_kwargs = {}
        for k, v in node.kwargs.items():
            resolved_kwargs[k] = self._eval_expression(v, context)
            
        resolved_args = [self._eval_expression(arg, context) for arg in node.args]

        action = self.resolver.resolve_command(
            app_dict, current_object, node.name, resolved_kwargs, resolved_args
        )
        result = self.dispatcher.execute(action, context)

        # Stash the last command result for implicit access
        if result is not None:
            context.set_var("_last_result", result)

    def _exec_function_call(self, node: FunctionCall, context: ExecutionContext) -> Any:
        func_def = context.get_function(node.name)
        if func_def is None:
            raise WinScriptError(
                f"Function '{node.name}' is not defined.\n"
                f"Available functions: {', '.join(context.list_functions())}"
            )

        # Validate arg count
        if len(node.args) != len(func_def.params):
            raise WinScriptError(
                f"Function '{node.name}' expects {len(func_def.params)} arguments, "
                f"got {len(node.args)}."
            )

        # Evaluate args in CALLER scope
        arg_values = [self._eval_expression(arg, context) for arg in node.args]

        # Push new scope for function
        context.push_function_scope(node.name)

        try:
            # Bind params as local variables
            for param_name, value in zip(func_def.params, arg_values):
                context.declare_local(param_name)
                context.set_var(param_name, value)

            # Execute function body
            self._execute_statements(func_def.statements, context)

            # Capture return value
            result = context.return_value

        finally:
            # Always pop scope and reset return flag
            context.pop_scope()
            context._returned = False  # reset for caller

        return result

    def _exec_scope_declaration(self, node: ScopeDeclaration, context: ExecutionContext):
        if node.scope == "local":
            context.declare_local(node.variable)
        else:
            context.declare_global(node.variable)

    def _exec_declare(self, node: DeclareStatement, context: ExecutionContext):
        ws_type = WSType(node.type_name)
        context.current_scope.declare_type(node.variable, ws_type)
        # Initialize with zero-value for the type
        zero_values = {
            WSType.STRING: "", WSType.INTEGER: 0, WSType.DECIMAL: 0.0,
            WSType.BOOLEAN: False, WSType.LIST: [], WSType.DICT: {}, WSType.ANY: None
        }
        context.set_var(node.variable, zero_values[ws_type])

    def _exec_repeat_times(self, node: RepeatTimesBlock, context: ExecutionContext):
        count = int(self._eval_expression(node.count_expr, context))
        for _ in range(count):
            if context.has_returned: break
            self._execute_statements(node.statements, context)

    def _exec_repeat_while(self, node: RepeatWhileBlock, context: ExecutionContext):
        iterations = 0
        while self._eval_condition(node.condition, context):
            if context.has_returned: break
            if iterations >= node.max_iterations:
                raise WinScriptError(
                    f"repeat while exceeded {node.max_iterations} iterations. "
                    f"Possible infinite loop. Use a counter or check your condition."
                )
            self._execute_statements(node.statements, context)
            iterations += 1

    def _exec_session_save(self, node: SessionSaveStatement, context: ExecutionContext):
        """Save the current execution context to a named session."""
        # Collect backend states from dispatcher
        backend_states = {}
        for app_name, backend in self.dispatcher._backends.items():
            if hasattr(backend, 'get_state'):
                try:
                    backend_states[app_name] = backend.get_state()
                except Exception:
                    pass
        
        self.session_manager.save_session(node.name, context, backend_states)

    def _exec_session_load(self, node: SessionLoadStatement, context: ExecutionContext):
        """Load a named session into the current execution context."""
        session_data = self.session_manager.load_session(node.name, context)
        
        # Restore backend connections if possible
        for app_name, state in session_data.get("backend_states", {}).items():
            # Backend reconnection would happen here
            pass

    def _exec_repeat_with(self, node: RepeatWithBlock, context: ExecutionContext):
        iterable = self._eval_expression(node.iterable_expr, context)
        if not isinstance(iterable, list):
            raise WinScriptError(
                f"repeat with expects a list, got {type(iterable).__name__}"
            )
        for item in iterable:
            if context.has_returned: break
            # loop var is local to this block
            context.set_var(node.variable, item)
            self._execute_statements(node.statements, context)

    # ------------------------------------------------------------------
    # Expression evaluation
    # ------------------------------------------------------------------

    def _eval_expression(self, expr: Any, context: ExecutionContext) -> Any:
        """Recursively evaluate an AST expression node to a Python value."""
        if isinstance(expr, StringLiteral):
            return expr.value

        if isinstance(expr, NumberLiteral):
            # Return int when the value is whole
            if expr.value == int(expr.value):
                return int(expr.value)
            return expr.value

        if isinstance(expr, BoolLiteral):
            return expr.value

        if isinstance(expr, Identifier):
            return context.get_var(expr.name)

        if isinstance(expr, ConcatExpr):
            left = self._eval_expression(expr.left, context)
            right = self._eval_expression(expr.right, context)
            return str(left) + str(right)

        if isinstance(expr, PropertyAccess):
            return self._eval_property(expr, context)

        if isinstance(expr, Condition):
            return self._eval_condition(expr, context)

        if isinstance(expr, FunctionCall):
            return self._exec_function_call(expr, context)
            
        if isinstance(expr, ArithExpr):
            return self._eval_arith(expr, context)
            
        if isinstance(expr, ListLiteral):
            return [self._eval_expression(item, context) for item in expr.items]

        # Fallback: return as-is (plain Python values, etc.)
        return expr

    def _eval_property(self, node: PropertyAccess, context: ExecutionContext) -> Any:
        """
        Evaluate property access chains like ``title of active tab``.

        Walks the chain from right to left:
        1. If inside a tell block → resolve property via .wsdict → dispatch
        2. If the inner expression is a variable → just return its attribute
        """
        if not context.current_app:
            raise WinScriptError(
                f"Property '{node.prop}' access outside tell block."
            )

        app_name = context.current_app
        app_dict = context.get_var(f"__dict_{app_name}")
        current_object = context.get_var(f"__obj_{app_name}")

        if node.prop == "value" and isinstance(node.of_expr, PropertyAccess) and node.of_expr.prop == "cell":
            cell_name = self._eval_expression(node.of_expr.of_expr, context)
            action = self.resolver.resolve_command(
                app_dict, current_object, "value_of_cell", {"cell": cell_name}
            )
            return self.dispatcher.execute(action, context)

        action = self.resolver.resolve_property(
            app_dict, current_object, node.prop
        )
        return self.dispatcher.get_property(action)

    def _eval_arith(self, node: ArithExpr, context: ExecutionContext) -> Any:
        left = self._eval_expression(node.left, context)
        right = self._eval_expression(node.right, context)
        ops = {"+": lambda a,b: a+b, "-": lambda a,b: a-b,
               "*": lambda a,b: a*b, "/": lambda a,b: a/b}
        return ops[node.operator](left, right)

    def _eval_condition(self, condition: Any, context: ExecutionContext) -> bool:
        """
        Evaluate a Condition node to a boolean.

        Supported operators:
            is, contains, greater_than, less_than, loaded, >, >=, !=
        """
        if isinstance(condition, Condition):
            left = self._eval_expression(condition.left, context)
            right = self._eval_expression(condition.right, context)
            op = condition.operator.lower()

            if op == "is":
                return left == right
            elif op == "contains":
                return str(right) in str(left)
            elif op == "greater_than" or op == ">":
                return float(left) > float(right)
            elif op == "less_than" or op == "<":
                return float(left) < float(right)
            elif op == ">=":
                return float(left) >= float(right)
            elif op == "!=":
                return left != right
            elif op == "loaded":
                return bool(left)
            else:
                raise WinScriptError(f"Unknown operator: '{op}'")

        if isinstance(condition, BoolLiteral):
            return condition.value

        if isinstance(condition, Identifier):
            return bool(context.get_var(condition.name))

        if isinstance(condition, PropertyAccess):
            return bool(self._eval_property(condition, context))

        # Fallback: truthy check
        val = self._eval_expression(condition, context)
        return bool(val)
