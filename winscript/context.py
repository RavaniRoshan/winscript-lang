from typing import Any
from winscript.errors import WinScriptError
from winscript.ast_nodes import FunctionDef
from winscript.types import WSType, check

class Scope:
    def __init__(self, name: str, scope_type: str):
        self.name = name
        self.scope_type = scope_type   # "global" | "function" | "block"
        self._vars: dict[str, Any] = {}
        self._declared_local: set[str] = set()  # names explicitly declared local
        self._declared_global: set[str] = set()  # names explicitly declared global
        self._declared_types: dict[str, WSType] = {}

    def declare_local(self, name: str):
        self._declared_local.add(name)

    def declare_global(self, name: str):
        self._declared_global.add(name)
        
    def declare_type(self, name: str, ws_type: WSType):
        self._declared_types[name] = ws_type

    def get_type(self, name: str) -> WSType | None:
        return self._declared_types.get(name)

    def set(self, name: str, value: Any):
        self._vars[name] = value

    def get(self, name: str) -> Any:
        if name not in self._vars:
            raise KeyError(name)
        return self._vars[name]

    def has(self, name: str) -> bool:
        return name in self._vars


class ExecutionContext:
    """
    Holds all state during script execution:
    - scopes and variables
    - current tell scope stack
    - return value
    - open backend connections
    - function registry
    """

    def __init__(self):
        self._scope_stack: list[Scope] = [Scope("global", "global")]
        self._tell_stack: list[str] = []
        self._return_value: Any = None
        self._returned: bool = False
        self._backends: dict[str, Any] = {}
        self._function_registry: dict[str, FunctionDef] = {}

    @property
    def current_scope(self) -> Scope:
        return self._scope_stack[-1]

    @property
    def global_scope(self) -> Scope:
        return self._scope_stack[0]

    # Scope management
    def push_scope(self, name: str, scope_type: str):
        self._scope_stack.append(Scope(name, scope_type))

    def push_function_scope(self, func_name: str):
        self.push_scope(func_name, "function")
        
    def push_block_scope(self, block_name: str):
        self.push_scope(block_name, "block")

    def pop_scope(self):
        if len(self._scope_stack) > 1:
            self._scope_stack.pop()

    def declare_local(self, name: str):
        """Register name as local in current function/block scope."""
        self.current_scope.declare_local(name)

    def declare_global(self, name: str):
        """Register name as explicitly global in current function/block scope."""
        self.current_scope.declare_global(name)

    def set_var(self, name: str, value: Any):
        """
        Resolution rules:
        1. If name declared local in current function/block scope -> set in local scope
        2. If name declared global in current function scope -> set in global scope
        3. If in function scope and name not declared -> set in global scope (default)
        4. If in global scope -> set in global scope
        """
        # Type Check
        declared_type = self.current_scope.get_type(name) or self.global_scope.get_type(name)
        if declared_type:
            value = check(value, declared_type, name)
            
        for scope in reversed(self._scope_stack):
            if name in scope._declared_local:
                scope.set(name, value)
                return
            if name in scope._declared_global:
                self.global_scope.set(name, value)
                return
            if scope.scope_type == "function":
                # Hit a function boundary. Any variable not explicitly local/global defaults to global.
                self.global_scope.set(name, value)
                return

        # If not caught by explicit local/global or function boundary, goes to global
        self.global_scope.set(name, value)

    def get_var(self, name: str) -> Any:
        """
        Resolution rules (search order):
        1. Current scope local declarations
        2. Global scope
        3. Raise WinScriptError(f"Variable '{name}' is not defined")
        """
        for scope in reversed(self._scope_stack):
            if name in scope._declared_local:
                if scope.has(name):
                    return scope.get(name)
                raise WinScriptError(f"Variable '{name}' is not defined")
            if name in scope._declared_global:
                break
            if scope.scope_type == "function":
                break

        if self.global_scope.has(name):
            return self.global_scope.get(name)

        raise WinScriptError(f"Variable '{name}' is not defined")

    def has_var(self, name: str) -> bool:
        for scope in reversed(self._scope_stack):
            if name in scope._declared_local:
                return scope.has(name)
            if name in scope._declared_global:
                break
            if scope.scope_type == "function":
                break

        return self.global_scope.has(name)

    # Function registry
    def register_function(self, func_def: FunctionDef):
        self._function_registry[func_def.name] = func_def

    def get_function(self, name: str) -> FunctionDef | None:
        return self._function_registry.get(name)

    def list_functions(self) -> list[str]:
        return list(self._function_registry.keys())

    # Tell scope
    def push_tell(self, app_name: str):
        self._tell_stack.append(app_name)

    def pop_tell(self):
        if self._tell_stack:
            self._tell_stack.pop()

    @property
    def current_app(self) -> str | None:
        return self._tell_stack[-1] if self._tell_stack else None

    @property
    def tell_depth(self) -> int:
        return len(self._tell_stack)

    # Return
    def set_return(self, value: Any):
        self._return_value = value
        self._returned = True
        
    def reset_return(self):
        self._return_value = None
        self._returned = False

    @property
    def has_returned(self) -> bool:
        return self._returned

    @property
    def return_value(self) -> Any:
        return self._return_value

    # Backend connections (cached per app)
    def get_backend(self, app_name: str) -> Any | None:
        return self._backends.get(app_name)

    def set_backend(self, app_name: str, backend: Any):
        self._backends[app_name] = backend

    def close_all_backends(self):
        # Called on script end or error.
        for backend in self._backends.values():
            if hasattr(backend, "close"):
                backend.close()
        self._backends.clear()
