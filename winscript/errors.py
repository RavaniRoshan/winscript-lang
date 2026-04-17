class WinScriptError(Exception):
    """Runtime error. Caught by try/catch in scripts."""
    def __init__(self, message: str, app: str = "", command: str = ""):
        self.app = app
        self.command = command
        super().__init__(message)

class WinScriptSyntaxError(Exception):
    """Parse failure. Never catchable. Fix the script."""
    def __init__(self, message: str, line: int = 0):
        self.line = line
        super().__init__(f"Syntax error{' at line ' + str(line) if line else ''}: {message}")

class WinScriptDictNotFound(WinScriptError):
    def __init__(self, app_name: str, searched_paths: list[str]):
        self.searched_paths = searched_paths
        super().__init__(
            f"No dictionary found for '{app_name}'.\n"
            f"Searched paths:\n" + "\n".join(f"  {p}" for p in searched_paths) + "\n"
            f"Fix: create {app_name.lower()}.wsdict in one of those paths."
        )

class WinScriptCommandNotFound(WinScriptError):
    def __init__(self, command: str, app: str, available: list[str]):
        self.available = available
        super().__init__(
            f"'{command}' is not a valid command for {app}.\n"
            f"Available commands: {', '.join(available[:10])}"
        )

class WinScriptPropertyNotFound(WinScriptError):
    def __init__(self, prop: str, obj: str, app: str):
        super().__init__(f"'{prop}' is not a property of {obj} in {app}.")

class WinScriptTypeError(WinScriptError):
    def __init__(self, arg: str, expected: str, got: str, command: str):
        super().__init__(
            f"Argument '{arg}' in '{command}' expects {expected}, got {got}."
        )

class WinScriptTimeoutError(WinScriptError):
    def __init__(self, condition: str, timeout_ms: int):
        super().__init__(
            f"Timeout after {timeout_ms}ms waiting for: {condition}"
        )

class WinScriptConnectionError(WinScriptError):
    def __init__(self, app: str, hint: str = ""):
        super().__init__(
            f"Could not connect to {app}."
            + (f"\nHint: {hint}" if hint else "")
        )
