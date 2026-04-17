"""
winscript.dispatcher — Routes ResolvedActions to the correct backend.

The dispatcher is the last step before a command hits a real application.
It receives a ResolvedAction (from the resolver), looks up or creates the
right backend connection, calls the method, and returns the result.

Backend connections are cached per app name so a single script only
connects once per target application.
"""

from typing import Any

from winscript.context import ExecutionContext
from winscript.errors import WinScriptError, WinScriptConnectionError
from winscript.resolver import ResolvedAction


# ---------------------------------------------------------------------------
# Backend class registry
# ---------------------------------------------------------------------------

def _get_backend_class(backend_type: str):
    """
    Lazy-import backend classes so missing optional deps (pywin32, pywinauto)
    don't break the dispatcher for CDP-only users.
    """
    if backend_type == "cdp":
        from winscript.backends.cdp import CDPBackend
        return CDPBackend
    elif backend_type == "com":
        from winscript.backends.com import COMBackend
        return COMBackend
    elif backend_type == "uia":
        from winscript.backends.uia import UIABackend
        return UIABackend
    else:
        raise WinScriptError(f"Unknown backend type: '{backend_type}'")


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

class Dispatcher:
    """
    Routes resolved commands to the correct backend, managing connection
    lifecycles and caching open connections.
    """

    def __init__(self):
        self._backends: dict[str, Any] = {}

    def execute(self, action: ResolvedAction, context: ExecutionContext | None = None) -> Any:
        """
        Execute a resolved command.

        1. Get (or create + connect) the backend for *action.app_name*.
        2. Call ``backend.execute(method, args)``.
        3. Return the result.
        """
        backend = self._get_backend(action)
        return backend.execute(action.backend_method, action.args)

    def get_property(self, action: ResolvedAction) -> Any:
        """
        Read a property through the backend.

        Uses ``backend.get_property(method, expression)`` which handles
        the CDP Runtime.evaluate path for expression-based properties.
        """
        backend = self._get_backend(action)
        return backend.get_property(
            action.backend_method,
            action.backend_expression or None,
        )

    def close_all(self) -> None:
        """Disconnect every cached backend. Safe to call multiple times."""
        for backend in self._backends.values():
            try:
                backend.disconnect()
            except Exception:
                pass
        self._backends.clear()

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _get_backend(self, action: ResolvedAction) -> Any:
        """
        Return the cached backend for *action.app_name*, or create a new
        one from the connection info in the ResolvedAction.
        """
        key = action.app_name
        if key in self._backends:
            return self._backends[key]

        BackendClass = _get_backend_class(action.backend_type)

        # Build constructor kwargs from the .wsdict connection section.
        # Each backend accepts different params; pass only what it needs.
        conn = action.connection_info or {}
        init_kwargs = self._build_init_kwargs(action.backend_type, conn)

        backend = BackendClass(**init_kwargs)
        backend.connect()
        self._backends[key] = backend
        return backend

    @staticmethod
    def _build_init_kwargs(backend_type: str, conn: dict) -> dict:
        """
        Map .wsdict ``connection:`` fields to backend constructor kwargs.
        """
        if backend_type == "cdp":
            kwargs: dict[str, Any] = {}
            if "host" in conn:
                kwargs["host"] = conn["host"]
            if "port" in conn:
                kwargs["port"] = int(conn["port"])
            if "launch_command" in conn:
                kwargs["launch_command"] = conn["launch_command"]
            if "launch_wait_ms" in conn:
                kwargs["launch_wait_ms"] = int(conn["launch_wait_ms"])
            return kwargs

        # COM and UIA stubs — pass through whatever is available
        return conn
