"""Tests for session persistence feature."""

import pytest
import tempfile
from pathlib import Path

from winscript.session import SessionManager
from winscript.context import ExecutionContext


class TestSessionManager:
    """Test session persistence functionality."""

    def test_session_save_and_load(self):
        """Test basic session save and load."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager(session_dir=Path(tmpdir))
            
            # Create a context with some data
            context = ExecutionContext()
            context.set_var("user_name", "test_user")
            context.set_var("count", 42)
            
            # Save session
            manager.save_session("test-session", context)
            
            # Verify session exists
            assert manager.session_exists("test-session")
            
            # Create new context and load
            new_context = ExecutionContext()
            result = manager.load_session("test-session", new_context)
            
            # Verify data restored
            assert new_context.get_var("user_name") == "test_user"
            assert new_context.get_var("count") == 42
            assert result["restored"] is True

    def test_list_sessions(self):
        """Test listing saved sessions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager(session_dir=Path(tmpdir))
            
            context = ExecutionContext()
            manager.save_session("session-1", context)
            manager.save_session("session-2", context)
            
            sessions = manager.list_sessions()
            session_names = [s["name"] for s in sessions]
            
            assert "session-1" in session_names
            assert "session-2" in session_names

    def test_delete_session(self):
        """Test deleting a session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager(session_dir=Path(tmpdir))
            
            context = ExecutionContext()
            manager.save_session("to-delete", context)
            
            assert manager.session_exists("to-delete")
            
            result = manager.delete_session("to-delete")
            assert result is True
            assert not manager.session_exists("to-delete")
            
            # Deleting non-existent returns False
            result = manager.delete_session("non-existent")
            assert result is False

    def test_session_not_found(self):
        """Test loading non-existent session raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager(session_dir=Path(tmpdir))
            context = ExecutionContext()
            
            with pytest.raises(FileNotFoundError):
                manager.load_session("non-existent", context)

    def test_session_info(self):
        """Test getting session info."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager(session_dir=Path(tmpdir))
            
            context = ExecutionContext()
            context.set_var("var1", "value1")
            context.set_var("var2", "value2")
            
            manager.save_session("info-test", context)
            
            info = manager.get_session_info("info-test")
            assert info is not None
            assert info["name"] == "info-test"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
