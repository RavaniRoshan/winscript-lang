"""
winscript.session — State Persistence & Session Management

Save and restore execution contexts for long-running automation workflows.
Sessions persist variables, functions, and backend connections across script runs.

Usage:
    # In WinScript:
    save session "my-automation"
    
    # Later:
    load session "my-automation"
"""

import json
import pickle
from pathlib import Path
from typing import Any
from datetime import datetime

from winscript.context import ExecutionContext
from winscript.ast_nodes import FunctionDef


class SessionManager:
    """Manages persistent sessions for WinScript execution contexts."""

    def __init__(self, session_dir: Path | None = None):
        self.session_dir = session_dir or Path.home() / ".winscript" / "sessions"
        self.session_dir.mkdir(parents=True, exist_ok=True)

    def _session_path(self, name: str) -> Path:
        """Get the file path for a session."""
        # Sanitize session name
        safe_name = "".join(c for c in name if c.isalnum() or c in "-_").lower()
        return self.session_dir / f"{safe_name}.json"

    def _metadata_path(self, name: str) -> Path:
        """Get the metadata file path for a session."""
        safe_name = "".join(c for c in name if c.isalnum() or c in "-_").lower()
        return self.session_dir / f"{safe_name}.meta.json"

    def save_session(self, name: str, context: ExecutionContext, backend_states: dict = None) -> None:
        """
        Save the current execution context to a session file.

        Persists:
        - All variables (global and local scope)
        - User-defined functions
        - Backend connection states (if serializable)
        - Tell stack state
        - Timestamp and metadata
        """
        session_path = self._session_path(name)
        metadata_path = self._metadata_path(name)

        # Extract serializable data from context
        session_data = {
            "version": "2.0.0",
            "saved_at": datetime.now().isoformat(),
            "variables": {},
            "functions": {},
            "tell_stack": context._tell_stack.copy(),
            "backend_states": {}
        }

        # Save global variables (exclude internal ones)
        global_scope = context.global_scope
        for var_name in global_scope._vars:
            if not var_name.startswith("__") and not var_name.startswith("_"):
                try:
                    # Try JSON serialization first
                    json.dumps(global_scope._vars[var_name])
                    session_data["variables"][var_name] = {
                        "value": global_scope._vars[var_name],
                        "scope": "global"
                    }
                except (TypeError, ValueError):
                    # Skip non-serializable values
                    session_data["variables"][var_name] = {
                        "value": str(global_scope._vars[var_name]),
                        "scope": "global",
                        "serialized": False
                    }

        # Save declared types
        session_data["declared_types"] = {
            name: str(ws_type) for name, ws_type in global_scope._declared_types.items()
        }

        # Save user-defined functions (not library functions)
        for func_name, func_def in context._function_registry.items():
            if not func_def.is_library:
                session_data["functions"][func_name] = {
                    "params": func_def.params,
                    "statement_count": len(func_def.statements)
                }

        # Save backend states if provided
        if backend_states:
            for app_name, state in backend_states.items():
                try:
                    json.dumps(state)
                    session_data["backend_states"][app_name] = state
                except (TypeError, ValueError):
                    pass  # Skip non-serializable backend states

        # Write session file
        with open(session_path, "w", encoding="utf-8") as f:
            json.dump(session_data, f, indent=2)

        # Write metadata
        metadata = {
            "name": name,
            "created_at": session_data["saved_at"],
            "variable_count": len(session_data["variables"]),
            "function_count": len(session_data["functions"])
        }
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

    def load_session(self, name: str, context: ExecutionContext) -> dict:
        """
        Load a session into the current execution context.

        Returns:
            dict: Session data including backend states that need reconnection
        """
        session_path = self._session_path(name)

        if not session_path.exists():
            raise FileNotFoundError(f"Session '{name}' not found. Use 'list sessions' to see available sessions.")

        with open(session_path, "r", encoding="utf-8") as f:
            session_data = json.load(f)

        # Restore global variables
        for var_name, var_data in session_data.get("variables", {}).items():
            context.global_scope.set(var_name, var_data["value"])

        # Restore declared types (if type system is available)
        # Note: Type restoration would need WSType reconstruction

        # Restore tell stack
        context._tell_stack = session_data.get("tell_stack", []).copy()

        return {
            "restored": True,
            "tell_stack": context._tell_stack,
            "backend_states": session_data.get("backend_states", {}),
            "saved_at": session_data.get("saved_at"),
            "session_name": name
        }

    def list_sessions(self) -> list[dict]:
        """List all available sessions with metadata."""
        sessions = []
        for meta_file in self.session_dir.glob("*.meta.json"):
            try:
                with open(meta_file, "r", encoding="utf-8") as f:
                    metadata = json.load(f)
                    sessions.append(metadata)
            except (json.JSONDecodeError, IOError):
                continue
        return sorted(sessions, key=lambda x: x.get("created_at", ""), reverse=True)

    def delete_session(self, name: str) -> bool:
        """Delete a session by name."""
        session_path = self._session_path(name)
        metadata_path = self._metadata_path(name)

        deleted = False
        if session_path.exists():
            session_path.unlink()
            deleted = True
        if metadata_path.exists():
            metadata_path.unlink()

        return deleted

    def session_exists(self, name: str) -> bool:
        """Check if a session exists."""
        return self._session_path(name).exists()

    def get_session_info(self, name: str) -> dict | None:
        """Get detailed information about a session."""
        metadata_path = self._metadata_path(name)
        if metadata_path.exists():
            try:
                with open(metadata_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return None
