from typing import Any
from winscript.errors import WinScriptError

class ExecutionContext:
    """
    Holds all state during script execution:
    - local variables
    - current tell scope stack
    - return value
    - open backend connections
    """

    def __init__(self):
        self._variables: dict[str, Any] = {}
        self._tell_stack: list[str] = []
        self._return_value: Any = None
        self._returned: bool = False
        self._backends: dict[str, Any] = {}

    # Variable management
    def set_var(self, name: str, value: Any):
        self._variables[name] = value

    def get_var(self, name: str) -> Any:
        if name not in self._variables:
            raise WinScriptError(f"Variable '{name}' is not defined")
        return self._variables[name]

    def has_var(self, name: str) -> bool:
        return name in self._variables

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
