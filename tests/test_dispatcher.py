"""tests/test_dispatcher.py — Dispatcher unit tests."""

import pytest
from unittest.mock import MagicMock, patch

from winscript.dispatcher import Dispatcher, _get_backend_class
from winscript.resolver import ResolvedAction
from winscript.context import ExecutionContext
from winscript.errors import WinScriptError


def _make_action(**overrides) -> ResolvedAction:
    defaults = {
        "backend_type": "cdp",
        "backend_method": "Page.navigate",
        "backend_expression": "",
        "args": {"url": "https://example.com"},
        "app_name": "Chrome",
        "connection_info": {"host": "localhost", "port": 9222},
    }
    defaults.update(overrides)
    return ResolvedAction(**defaults)


# ── Backend class registry ───────────────────────────────────────────────

def test_get_backend_class_cdp():
    from winscript.backends.cdp import CDPBackend
    assert _get_backend_class("cdp") is CDPBackend


def test_get_backend_class_unknown():
    with pytest.raises(WinScriptError, match="Unknown backend type"):
        _get_backend_class("rest")


# ── execute() routing ────────────────────────────────────────────────────

def test_execute_creates_backend_and_calls():
    d = Dispatcher()
    mock_backend = MagicMock()
    mock_backend.execute.return_value = {"frameId": "abc"}

    with patch("winscript.dispatcher._get_backend_class") as mock_cls:
        mock_cls.return_value = MagicMock(return_value=mock_backend)
        action = _make_action()
        result = d.execute(action)

    mock_backend.connect.assert_called_once()
    mock_backend.execute.assert_called_once_with("Page.navigate", {"url": "https://example.com"})
    assert result == {"frameId": "abc"}


def test_execute_reuses_cached_backend():
    d = Dispatcher()
    mock_backend = MagicMock()
    mock_backend.execute.return_value = {}

    with patch("winscript.dispatcher._get_backend_class") as mock_cls:
        mock_cls.return_value = MagicMock(return_value=mock_backend)
        action = _make_action()

        d.execute(action)
        d.execute(action)

    # connect() called only once — second call reuses cached backend
    mock_backend.connect.assert_called_once()
    assert mock_backend.execute.call_count == 2


# ── get_property() ───────────────────────────────────────────────────────

def test_get_property_calls_backend():
    d = Dispatcher()
    mock_backend = MagicMock()
    mock_backend.get_property.return_value = "GitHub"

    with patch("winscript.dispatcher._get_backend_class") as mock_cls:
        mock_cls.return_value = MagicMock(return_value=mock_backend)
        action = _make_action(
            backend_method="Runtime.evaluate",
            backend_expression="document.title",
            args={},
        )
        result = d.get_property(action)

    mock_backend.get_property.assert_called_once_with("Runtime.evaluate", "document.title")
    assert result == "GitHub"


# ── close_all() ──────────────────────────────────────────────────────────

def test_close_all_disconnects_backends():
    d = Dispatcher()
    mock_backend = MagicMock()

    with patch("winscript.dispatcher._get_backend_class") as mock_cls:
        mock_cls.return_value = MagicMock(return_value=mock_backend)
        d.execute(_make_action())

    d.close_all()
    mock_backend.disconnect.assert_called_once()
    assert d._backends == {}


def test_close_all_safe_when_empty():
    d = Dispatcher()
    d.close_all()  # should not raise


def test_close_all_swallows_disconnect_errors():
    d = Dispatcher()
    mock_backend = MagicMock()
    mock_backend.disconnect.side_effect = RuntimeError("boom")

    with patch("winscript.dispatcher._get_backend_class") as mock_cls:
        mock_cls.return_value = MagicMock(return_value=mock_backend)
        d.execute(_make_action())

    d.close_all()  # should not raise despite disconnect error
    assert d._backends == {}


# ── Different apps get different backends ────────────────────────────────

def test_different_apps_get_separate_backends():
    d = Dispatcher()
    mock_backend_1 = MagicMock()
    mock_backend_2 = MagicMock()
    call_count = {"n": 0}

    def make_backend(**kwargs):
        call_count["n"] += 1
        return mock_backend_1 if call_count["n"] == 1 else mock_backend_2

    with patch("winscript.dispatcher._get_backend_class") as mock_cls:
        mock_cls.return_value = make_backend
        d.execute(_make_action(app_name="Chrome"))
        d.execute(_make_action(app_name="Excel", backend_type="cdp"))

    assert "Chrome" in d._backends
    assert "Excel" in d._backends
    assert d._backends["Chrome"] is not d._backends["Excel"]
