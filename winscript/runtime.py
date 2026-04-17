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
)
from winscript.context import ExecutionContext
from winscript.dicts.loader import DictLoader
from winscript.dispatcher import Dispatcher
from winscript.errors import (
    WinScriptError,
    WinScriptSyntaxError,
    WinScriptTimeoutError,
)
from winscript.parser import parse
from winscript.resolver import Resolver


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

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def execute(self, source_code: str) -> Any:
        """
        Full pipeline: parse → execute AST → return result.

        Always closes backend connections on completion or error.
        Returns the value passed to ``return`` in the script, or None.
        """
        try:
            ast = parse(source_code)
            context = ExecutionContext()
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
            parse(source_code)
        except WinScriptSyntaxError as e:
            errors.append(str(e))
        return errors

    # ------------------------------------------------------------------
    # AST walker
    # ------------------------------------------------------------------

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
            # Property mutation — not supported in v1
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
        resolved_args = {}
        for k, v in node.kwargs.items():
            resolved_args[k] = self._eval_expression(v, context)

        action = self.resolver.resolve_command(
            app_dict, current_object, node.name, resolved_args
        )
        result = self.dispatcher.execute(action, context)

        # Stash the last command result for implicit access
        if result is not None:
            context.set_var("_last_result", result)

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

        action = self.resolver.resolve_property(
            app_dict, current_object, node.prop
        )
        return self.dispatcher.get_property(action)

    def _eval_condition(self, condition: Any, context: ExecutionContext) -> bool:
        """
        Evaluate a Condition node to a boolean.

        Supported operators:
            is, contains, greater_than, less_than, loaded
        """
        if isinstance(condition, Condition):
            left = self._eval_expression(condition.left, context)
            right = self._eval_expression(condition.right, context)
            op = condition.operator.lower()

            if op == "is":
                return left == right
            elif op == "contains":
                return str(right) in str(left)
            elif op == "greater_than":
                return float(left) > float(right)
            elif op == "less_than":
                return float(left) < float(right)
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
