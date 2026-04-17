"""
winscript.backends.com — COM/pywin32 backend for Office apps.

This backend will enable automation of Excel, Word, Outlook, and other
COM-compatible applications via the pywin32 library.

Status: Stub — will be implemented when community contributes excel.wsdict.
"""

from winscript.backends.base import Backend
from winscript.errors import WinScriptError


class COMBackend(Backend):
    """COM Automation backend (pywin32). Not yet implemented."""

    def connect(self):
        raise WinScriptError("COM backend is not yet implemented. Coming in v1.1.")

    def disconnect(self):
        pass

    def execute(self, method, params=None):
        raise WinScriptError("COM backend is not yet implemented.")

    def get_property(self, backend_method, backend_expression=None, params=None):
        raise WinScriptError("COM backend is not yet implemented.")
