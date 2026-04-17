"""
winscript.backends.uia — UI Automation backend for generic Win32 apps.

This backend will enable automation of native Windows applications like
Notepad, File Explorer, Calculator, etc. via the pywinauto library.

Status: Stub — will be implemented when community contributes native app dicts.
"""

from winscript.backends.base import Backend
from winscript.errors import WinScriptError


class UIABackend(Backend):
    """UI Automation backend (pywinauto). Not yet implemented."""

    def connect(self):
        raise WinScriptError("UIA backend is not yet implemented. Coming in v1.1.")

    def disconnect(self):
        pass

    def execute(self, method, params=None):
        raise WinScriptError("UIA backend is not yet implemented.")

    def get_property(self, backend_method, backend_expression=None, params=None):
        raise WinScriptError("UIA backend is not yet implemented.")
