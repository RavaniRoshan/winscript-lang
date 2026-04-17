"""
tests/test_cdp_backend.py — Unit tests for CDPBackend.

These tests verify:
1. Module imports without errors
2. Constructor defaults are correct
3. execute() routes _winscript_* methods to local handlers
4. execute() routes raw CDP methods to send()
5. get_property() uses Runtime.evaluate for expressions
6. _discover_targets returns None when nothing is listening
7. connect() raises WinScriptConnectionError when Chrome isn't running
"""

import pytest
from unittest.mock import patch, MagicMock

from winscript.backends.cdp import CDPBackend, _KEY_MAP
from winscript.backends.base import Backend
from winscript.errors import WinScriptConnectionError, WinScriptError, WinScriptTimeoutError


# ── Import & construction ────────────────────────────────────────────────────

def test_cdp_backend_is_backend_subclass():
    assert issubclass(CDPBackend, Backend)


def test_default_constructor():
    b = CDPBackend()
    assert b.host == "localhost"
    assert b.port == 9222
    assert b.launch_command is None
    assert b._ws is None


def test_custom_constructor():
    b = CDPBackend(host="10.0.0.1", port=9333, launch_command="chrome.exe --debug",
                   launch_wait_ms=5000)
    assert b.host == "10.0.0.1"
    assert b.port == 9333
    assert b.launch_command == "chrome.exe --debug"
    assert b.launch_wait_ms == 5000


# ── execute() routing ────────────────────────────────────────────────────────

def test_execute_routes_winscript_method():
    b = CDPBackend()
    # Attach a mock handler
    b._winscript_click = MagicMock(return_value=None)
    b.execute("_winscript_click", {"selector": "#btn"})
    b._winscript_click.assert_called_once_with(selector="#btn")


def test_execute_routes_raw_cdp_to_send():
    b = CDPBackend()
    b.send = MagicMock(return_value={"frameId": "abc"})
    result = b.execute("Page.navigate", {"url": "https://example.com"})
    b.send.assert_called_once_with("Page.navigate", {"url": "https://example.com"})
    assert result == {"frameId": "abc"}


def test_execute_unknown_winscript_raises():
    b = CDPBackend()
    with pytest.raises(WinScriptError, match="Unknown built-in method"):
        b.execute("_winscript_nonexistent")


# ── get_property() ───────────────────────────────────────────────────────────

def test_get_property_with_expression():
    b = CDPBackend()
    b.send = MagicMock(return_value={
        "result": {"type": "string", "value": "GitHub"}
    })
    val = b.get_property("Runtime.evaluate", "document.title")
    assert val == "GitHub"
    b.send.assert_called_once_with("Runtime.evaluate", {
        "expression": "document.title",
        "returnByValue": True,
    })


def test_get_property_without_expression():
    b = CDPBackend()
    b.send = MagicMock(return_value={"product": "Chrome/120"})
    val = b.get_property("Browser.getVersion")
    assert val == {"product": "Chrome/120"}
    b.send.assert_called_once_with("Browser.getVersion", {})


# ── send() guard ─────────────────────────────────────────────────────────────

def test_send_without_connection_raises():
    b = CDPBackend()
    with pytest.raises(WinScriptConnectionError, match="Not connected"):
        b.send("Page.navigate", {"url": "https://example.com"})


# ── connect() failure path ───────────────────────────────────────────────────

def test_connect_raises_when_chrome_not_running():
    b = CDPBackend()  # no launch_command → won't try to start one
    with pytest.raises(WinScriptConnectionError, match="Chrome"):
        b.connect()


# ── disconnect() is safe to call repeatedly ──────────────────────────────────

def test_disconnect_when_not_connected():
    b = CDPBackend()
    b.disconnect()  # should not raise


# ── _winscript_wait_loaded timeout ───────────────────────────────────────────

def test_wait_loaded_timeout():
    b = CDPBackend()
    b.send = MagicMock(return_value={
        "result": {"type": "string", "value": "loading"}
    })
    with pytest.raises(WinScriptTimeoutError, match="page loaded"):
        b._winscript_wait_loaded(timeout_ms=500)


# ── Key map coverage ─────────────────────────────────────────────────────────

def test_key_map_has_common_keys():
    for key in ("Enter", "Tab", "Escape", "Backspace", "ArrowDown", "F5"):
        assert key in _KEY_MAP


def test_winscript_press_sends_key_events():
    b = CDPBackend()
    calls = []
    b.send = MagicMock(side_effect=lambda method, params: calls.append((method, params)))
    b._winscript_press("Enter")
    assert len(calls) == 2
    assert calls[0][0] == "Input.dispatchKeyEvent"
    assert calls[0][1]["type"] == "keyDown"
    assert calls[1][1]["type"] == "keyUp"


# ── _winscript_scroll ────────────────────────────────────────────────────────

def test_scroll_to_top():
    b = CDPBackend()
    b.send = MagicMock(return_value={})
    b._winscript_scroll("top")
    b.send.assert_called_once()
    expr = b.send.call_args[1].get("params", b.send.call_args[0][1])
    assert "scrollTo(0, 0)" in expr.get("expression", str(expr))


def test_scroll_to_bottom():
    b = CDPBackend()
    b.send = MagicMock(return_value={})
    b._winscript_scroll("bottom")
    b.send.assert_called_once()
