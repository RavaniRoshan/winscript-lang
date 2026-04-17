"""
tests/test_e2e.py — End-to-end tests for the full WinScript pipeline.

Tests 1-3 run without Chrome.
Tests 4-5 require Chrome with --remote-debugging-port=9222 and are
marked with @pytest.mark.chrome so they can be skipped.
"""

import pytest
from pathlib import Path

from winscript.parser import parse
from winscript.ast_nodes import Script, TellBlock, CommandStatement, TryBlock
from winscript.dicts.loader import DictLoader
from winscript.mcp_server import (
    _run_winscript as run_winscript,
    _validate_script as validate_script,
    _list_available_apps as list_available_apps,
    _get_app_commands as get_app_commands,
)

DICTS_DIR = str(Path(__file__).parent.parent / "dicts")


# ═════════════════════════════════════════════════════════════════════════════
# Test 1: Parser round-trip — 3 valid scripts parse without exception
# ═════════════════════════════════════════════════════════════════════════════

VALID_SCRIPTS = [
    # Script A: navigate + wait + return
    (
        'tell Chrome\n'
        '    navigate to "https://example.com"\n'
        '    wait until loaded\n'
        '    return title of active tab\n'
        'end tell\n'
    ),
    # Script B: set/return with concatenation
    (
        'set greeting to "Hello"\n'
        'set name to "World"\n'
        'return greeting & " " & name\n'
    ),
    # Script C: try/catch with if
    (
        'try\n'
        '    tell Chrome\n'
        '        navigate to "https://example.com"\n'
        '    end tell\n'
        'catch err\n'
        '    if err contains "connect" then\n'
        '        return "Chrome not running"\n'
        '    end if\n'
        '    return err\n'
        'end try\n'
    ),
]


@pytest.mark.parametrize("script", VALID_SCRIPTS, ids=["navigate", "concat", "trycatch"])
def test_parser_roundtrip(script):
    """Valid scripts must parse to a Script AST without exceptions."""
    ast = parse(script)
    assert isinstance(ast, Script)
    assert len(ast.statements) >= 1


def test_parser_tell_produces_tell_block():
    ast = parse(VALID_SCRIPTS[0])
    assert isinstance(ast.statements[0], TellBlock)
    assert ast.statements[0].app_name == "Chrome"


def test_parser_try_produces_try_block():
    ast = parse(VALID_SCRIPTS[2])
    assert isinstance(ast.statements[0], TryBlock)


# ═════════════════════════════════════════════════════════════════════════════
# Test 2: Dict loading — chrome.wsdict loads correctly
# ═════════════════════════════════════════════════════════════════════════════

def test_dict_loading_chrome():
    loader = DictLoader(extra_paths=[DICTS_DIR])
    app_dict = loader.load("Chrome")

    assert app_dict.name == "Chrome"
    assert app_dict.backend == "cdp"

    # Tab object exists
    assert "Tab" in app_dict.objects
    tab = app_dict.objects["Tab"]

    # "navigate" command found
    nav = tab.find_command("navigate")
    assert nav is not None
    assert nav.backend_method == "Page.navigate"

    # "title" property found
    title = tab.find_property("title")
    assert title is not None
    assert title.backend_expression == "document.title"


def test_dict_loading_root_is_browser():
    loader = DictLoader(extra_paths=[DICTS_DIR])
    app_dict = loader.load("Chrome")
    root = app_dict.root_object()
    assert root.name == "Browser"
    assert root.is_root is True


# ═════════════════════════════════════════════════════════════════════════════
# Test 3: validate_script tool
# ═════════════════════════════════════════════════════════════════════════════

def test_validate_script_valid():
    result = validate_script('tell Chrome\n  navigate to "https://test.com"\nend tell')
    assert result == "VALID"


def test_validate_script_simple_valid():
    result = validate_script('set x to 1\nreturn x')
    assert result == "VALID"


def test_validate_script_invalid():
    result = validate_script('tell\nend')
    assert result.startswith("INVALID")


# ═════════════════════════════════════════════════════════════════════════════
# Test 3b: list_available_apps / get_app_commands tools
# ═════════════════════════════════════════════════════════════════════════════

def test_list_available_apps():
    result = list_available_apps()
    assert "Chrome" in result


def test_get_app_commands_chrome():
    result = get_app_commands("Chrome")
    assert "navigate" in result
    assert "click" in result
    assert "title" in result


def test_get_app_commands_unknown():
    result = get_app_commands("NonExistentApp")
    assert "ERROR" in result


# ═════════════════════════════════════════════════════════════════════════════
# Test 3c: run_winscript tool — non-Chrome tests
# ═════════════════════════════════════════════════════════════════════════════

def test_run_winscript_set_return():
    result = run_winscript('set x to 42\nreturn x')
    assert result == "42"


def test_run_winscript_concat():
    result = run_winscript(
        'set a to "Hello"\n'
        'set b to "WinScript"\n'
        'return a & " " & b'
    )
    assert result == "Hello WinScript"


def test_run_winscript_if_condition():
    result = run_winscript(
        'set x to 10\n'
        'if x is 10 then\n'
        '    return "match"\n'
        'end if\n'
        'return "no match"'
    )
    assert result == "match"


def test_run_winscript_try_catch():
    result = run_winscript(
        'try\n'
        '    navigate to "https://example.com"\n'
        'catch err\n'
        '    return "caught: " & err\n'
        'end try'
    )
    assert result.startswith("caught: ")


def test_run_winscript_no_return():
    result = run_winscript('set x to 1')
    assert "successfully" in result.lower()


# ═════════════════════════════════════════════════════════════════════════════
# Test 4 & 5: Live Chrome tests (require Chrome with --remote-debugging-port)
# ═════════════════════════════════════════════════════════════════════════════

def _chrome_available() -> bool:
    """Check if Chrome CDP is reachable."""
    import urllib.request
    try:
        urllib.request.urlopen("http://localhost:9222/json", timeout=2)
        return True
    except Exception:
        return False


chrome = pytest.mark.skipif(
    not _chrome_available(),
    reason="Chrome not running with --remote-debugging-port=9222"
)


@chrome
def test_e2e_chrome_navigate_return_title():
    """Full pipeline: navigate → wait → return title."""
    result = run_winscript(
        'tell Chrome\n'
        '    navigate to "https://example.com"\n'
        '    wait until loaded\n'
        '    return title of active tab\n'
        'end tell'
    )
    assert "Example" in result


@chrome
def test_e2e_chrome_error_handling():
    """try/catch wraps Chrome errors cleanly."""
    result = run_winscript(
        'try\n'
        '    tell Chrome\n'
        '        click element "nonexistent_xyz_button_that_does_not_exist"\n'
        '    end tell\n'
        'catch err\n'
        '    return "caught: " & err\n'
        'end try'
    )
    assert result.startswith("caught: ")
