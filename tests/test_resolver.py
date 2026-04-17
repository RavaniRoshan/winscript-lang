"""tests/test_resolver.py — Resolver unit tests."""

import pytest
from pathlib import Path

from winscript.dicts.loader import DictLoader
from winscript.resolver import Resolver, ResolvedAction
from winscript.context import ExecutionContext
from winscript.ast_nodes import StringLiteral, NumberLiteral, ConcatExpr, Identifier
from winscript.errors import (
    WinScriptCommandNotFound,
    WinScriptPropertyNotFound,
    WinScriptTypeError,
    WinScriptError,
)

DICTS_DIR = Path(__file__).parent.parent / "dicts"


@pytest.fixture(scope="module")
def resolver():
    loader = DictLoader(extra_paths=[str(DICTS_DIR)])
    return Resolver(loader)


@pytest.fixture(scope="module")
def chrome(resolver):
    return resolver.resolve_tell("Chrome")


# ── resolve_tell ─────────────────────────────────────────────────────────────

def test_resolve_tell_returns_appdict_and_root(chrome):
    app_dict, root_obj = chrome
    assert app_dict.name == "Chrome"
    assert root_obj.name == "Browser"
    assert root_obj.is_root is True


# ── resolve_command ──────────────────────────────────────────────────────────

def test_resolve_navigate_command(resolver, chrome):
    app_dict, browser = chrome
    action = resolver.resolve_command(
        app_dict, browser, "navigate", {"to": StringLiteral("https://test.com")}
    )
    assert isinstance(action, ResolvedAction)
    assert action.backend_type == "cdp"
    assert action.backend_method == "Page.navigate"
    assert action.app_name == "Chrome"


def test_resolve_browser_open_command(resolver, chrome):
    app_dict, browser = chrome
    action = resolver.resolve_command(
        app_dict, browser, "open", {"url": StringLiteral("https://github.com")}
    )
    assert action.backend_method == "Target.createTarget"


def test_resolve_click_command_from_browser_scope(resolver, chrome):
    """Tab commands should be discoverable from the Browser (root) scope."""
    app_dict, browser = chrome
    action = resolver.resolve_command(
        app_dict, browser, "click", {"element": StringLiteral("#btn")}
    )
    assert action.backend_method == "_winscript_click"


def test_resolve_unknown_command_raises(resolver, chrome):
    app_dict, browser = chrome
    with pytest.raises(WinScriptCommandNotFound) as exc_info:
        resolver.resolve_command(app_dict, browser, "does_not_exist", {})
    assert "does_not_exist" in str(exc_info.value)
    assert exc_info.value.available  # should list available commands


def test_resolve_command_wrong_type_raises(resolver, chrome):
    app_dict, browser = chrome
    with pytest.raises(WinScriptTypeError):
        resolver.resolve_command(
            app_dict, browser, "navigate", {"to": NumberLiteral(12345)}
        )


# ── resolve_property ─────────────────────────────────────────────────────────

def test_resolve_title_property(resolver, chrome):
    app_dict, browser = chrome
    # "title" lives on Tab, but should be found via fallback from Browser
    action = resolver.resolve_property(app_dict, browser, "title")
    assert isinstance(action, ResolvedAction)
    assert action.backend_expression == "document.title"
    assert action.backend_type == "cdp"


def test_resolve_url_property(resolver, chrome):
    app_dict, browser = chrome
    action = resolver.resolve_property(app_dict, browser, "url")
    assert action.backend_expression == "location.href"


def test_resolve_active_tab_property(resolver, chrome):
    app_dict, browser = chrome
    action = resolver.resolve_property(app_dict, browser, "active_tab")
    assert action.backend_method == "_winscript_get_active_tab"


def test_resolve_unknown_property_raises(resolver, chrome):
    app_dict, browser = chrome
    with pytest.raises(WinScriptPropertyNotFound):
        resolver.resolve_property(app_dict, browser, "nonexistent_prop")


# ── resolve_sub_object ───────────────────────────────────────────────────────

def test_resolve_tab_sub_object(resolver, chrome):
    app_dict, browser = chrome
    tab = resolver.resolve_sub_object(app_dict, browser, "Tab")
    assert tab.name == "Tab"


def test_resolve_dom_sub_object(resolver, chrome):
    app_dict, browser = chrome
    dom = resolver.resolve_sub_object(app_dict, browser, "DOM")
    assert dom.name == "DOM"


def test_resolve_unknown_sub_object_raises(resolver, chrome):
    app_dict, browser = chrome
    with pytest.raises(WinScriptError, match="not a recognized object"):
        resolver.resolve_sub_object(app_dict, browser, "Nonexistent")


# ── resolve_expression ───────────────────────────────────────────────────────

def test_resolve_string_literal(resolver):
    ctx = ExecutionContext()
    assert resolver.resolve_expression(StringLiteral("hello"), ctx) == "hello"


def test_resolve_number_literal(resolver):
    ctx = ExecutionContext()
    assert resolver.resolve_expression(NumberLiteral(42.0), ctx) == 42
    assert resolver.resolve_expression(NumberLiteral(3.14), ctx) == 3.14


def test_resolve_identifier_from_context(resolver):
    ctx = ExecutionContext()
    ctx.set_var("my_var", "some_value")
    assert resolver.resolve_expression(Identifier("my_var"), ctx) == "some_value"


def test_resolve_identifier_undefined_raises(resolver):
    ctx = ExecutionContext()
    with pytest.raises(WinScriptError, match="not defined"):
        resolver.resolve_expression(Identifier("undefined_var"), ctx)


def test_resolve_concat_expr(resolver):
    ctx = ExecutionContext()
    expr = ConcatExpr(StringLiteral("Hello "), StringLiteral("World"))
    assert resolver.resolve_expression(expr, ctx) == "Hello World"


def test_resolve_concat_with_variable(resolver):
    ctx = ExecutionContext()
    ctx.set_var("name", "WinScript")
    expr = ConcatExpr(StringLiteral("Hello "), Identifier("name"))
    assert resolver.resolve_expression(expr, ctx) == "Hello WinScript"
