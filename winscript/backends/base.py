"""winscript.backends.base — Abstract base class for all WinScript backends."""

from abc import ABC, abstractmethod
from typing import Any


class Backend(ABC):
    """
    Every backend (CDP, COM, UIA) must implement this interface.
    The dispatcher calls these methods — it never knows which backend is active.
    """

    @abstractmethod
    def connect(self) -> None:
        """Establish connection to the target application."""
        ...

    @abstractmethod
    def disconnect(self) -> None:
        """Cleanly shut down the connection."""
        ...

    # Alias so ExecutionContext.close_all_backends() works
    def close(self) -> None:
        self.disconnect()

    @abstractmethod
    def execute(self, method: str, params: dict | None = None) -> Any:
        """Execute a command defined in the .wsdict file."""
        ...

    @abstractmethod
    def get_property(self, backend_method: str, backend_expression: str | None = None,
                     params: dict | None = None) -> Any:
        """Read a property defined in the .wsdict file."""
        ...
