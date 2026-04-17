"""
tests/test_runtime.py — WinScript Runtime unit tests.

All tests mock the dispatcher so they run without Chrome.
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

from winscript.runtime import WinScriptRuntime
from winscript.errors import WinScriptError, WinScriptDictNotFound

DICTS_DIR = str(Path(__file__).parent.parent / "dicts")


@pytest.fixture
def runtime():
    return WinScriptRuntime(extra_dict_paths=[DICTS_DIR])


# ── Simple set / return (no tell block needed) ───────────────────────────

def test_set_and_return_number(runtime):
    result = runtime.execute("set x to 1\nreturn x")
    assert result == 1


def test_set_and_return_string(runtime):
    result = runtime.execute('set name to "WinScript"\nreturn name')
    assert result == "WinScript"


def test_return_without_set(runtime):
    result = runtime.execute('return "hello"')
    assert result == "hello"


def test_return_stops_execution(runtime):
    result = runtime.execute('return 1\nreturn 2')
    assert result == 1


def test_concat_expression(runtime):
    result = runtime.execute(
        'set greeting to "Hello"\n'
        'set name to "World"\n'
        'return greeting & " " & name'
    )
    assert result == "Hello World"


# ── If statement ─────────────────────────────────────────────────────────

def test_if_true_branch_executes(runtime):
    result = runtime.execute(
        'set x to 10\n'
        'if x is 10 then\n'
        '    return "yes"\n'
        'end if\n'
        'return "no"'
    )
    assert result == "yes"


def test_if_false_branch_skips(runtime):
    result = runtime.execute(
        'set x to 5\n'
        'if x is 10 then\n'
        '    return "yes"\n'
        'end if\n'
        'return "no"'
    )
    assert result == "no"


# ── try / catch ──────────────────────────────────────────────────────────

def test_try_catch_catches_error(runtime):
    """A command outside tell block raises WinScriptError → caught by catch."""
    result = runtime.execute(
        'try\n'
        '    navigate to "https://example.com"\n'
        'catch err\n'
        '    return err\n'
        'end try'
    )
    assert "outside tell block" in result.lower() or "tell block" in result.lower()


def test_try_catch_with_dict_not_found(runtime):
    result = runtime.execute(
        'try\n'
        '    tell NonExistentApp\n'
        '    end tell\n'
        'catch err\n'
        '    return err\n'
        'end try'
    )
    assert "NonExistentApp" in result


def test_try_no_error(runtime):
    result = runtime.execute(
        'try\n'
        '    set x to 1\n'
        'catch err\n'
        '    return err\n'
        'end try\n'
        'return x'
    )
    assert result == 1


# ── Tell block + command dispatch ────────────────────────────────────────

def test_tell_block_dispatches_command(runtime):
    """Mock the dispatcher to verify commands route correctly."""
    mock_execute = MagicMock(return_value=None)
    runtime.dispatcher.execute = mock_execute
    runtime.dispatcher.close_all = MagicMock()

    runtime.execute(
        'tell Chrome\n'
        '    navigate to "https://github.com"\n'
        'end tell'
    )

    mock_execute.assert_called_once()
    action = mock_execute.call_args[0][0]
    assert action.backend_method == "Page.navigate"
    assert action.args.get("url") == "https://github.com"


def test_tell_block_return_property(runtime):
    """Mock get_property to return a title string."""
    runtime.dispatcher.get_property = MagicMock(return_value="GitHub Homepage")
    runtime.dispatcher.close_all = MagicMock()

    result = runtime.execute(
        'tell Chrome\n'
        '    return title of active tab\n'
        'end tell'
    )
    assert result == "GitHub Homepage"


def test_tell_block_stores_result(runtime):
    """_last_result should be set after a command dispatch."""
    runtime.dispatcher.execute = MagicMock(return_value={"status": "ok"})
    runtime.dispatcher.close_all = MagicMock()

    result = runtime.execute(
        'tell Chrome\n'
        '    navigate to "https://example.com"\n'
        '    return _last_result\n'
        'end tell'
    )
    assert result == {"status": "ok"}


# ── Backends always cleaned up ───────────────────────────────────────────

def test_backends_closed_on_success(runtime):
    close_mock = MagicMock()
    runtime.dispatcher.close_all = close_mock
    runtime.execute('set x to 1\nreturn x')
    close_mock.assert_called_once()


def test_backends_closed_on_error(runtime):
    close_mock = MagicMock()
    runtime.dispatcher.close_all = close_mock
    try:
        runtime.execute('navigate to "bad"')  # will error: outside tell block
    except WinScriptError:
        pass
    close_mock.assert_called_once()


# ── validate() ───────────────────────────────────────────────────────────

def test_validate_valid_script(runtime):
    errors = runtime.validate('tell Chrome\n  navigate to "test"\nend tell')
    assert errors == []


def test_validate_invalid_script(runtime):
    errors = runtime.validate('tell\nend')
    assert len(errors) > 0


# ── Condition evaluation ─────────────────────────────────────────────────

def test_condition_is(runtime):
    result = runtime.execute(
        'set a to "hello"\n'
        'if a is "hello" then\n'
        '    return "match"\n'
        'end if\n'
        'return "no match"'
    )
    assert result == "match"


def test_condition_contains(runtime):
    result = runtime.execute(
        'set text to "hello world"\n'
        'if text contains "world" then\n'
        '    return "found"\n'
        'end if\n'
        'return "not found"'
    )
    assert result == "found"


# ── Command outside tell block ───────────────────────────────────────────

def test_command_outside_tell_raises():
    rt = WinScriptRuntime(extra_dict_paths=[DICTS_DIR])
    with pytest.raises(WinScriptError, match="outside tell block"):
        rt.execute('navigate to "https://example.com"')


# ── Dict not found propagates ────────────────────────────────────────────

def test_dict_not_found_propagates():
    rt = WinScriptRuntime(extra_dict_paths=[DICTS_DIR])
    with pytest.raises(WinScriptDictNotFound):
        rt.execute('tell NonExistentApp\nend tell')
