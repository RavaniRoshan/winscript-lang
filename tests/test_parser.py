# tests/test_parser.py — Parser tests for WinScript grammar
# Verifies that the Lark grammar correctly parses all 5 constructs.

import pytest
from pathlib import Path
from lark import Lark

# ---------------------------------------------------------------------------
# Fixture: load the grammar once for all tests
# ---------------------------------------------------------------------------

GRAMMAR_PATH = Path(__file__).parent.parent / "winscript" / "grammar.lark"


@pytest.fixture(scope="module")
def parser():
    """Load the WinScript Lark grammar."""
    grammar_text = GRAMMAR_PATH.read_text(encoding="utf-8")
    return Lark(grammar_text, parser="earley", start="start")


def _parse(parser, code: str):
    """Helper: ensure code ends with a newline, then parse."""
    if not code.endswith("\n"):
        code += "\n"
    return parser.parse(code)


# ---------------------------------------------------------------------------
# Test 1 — Simple tell block
# ---------------------------------------------------------------------------

def test_parse_tell_block(parser):
    code = '''tell Chrome
    navigate to "https://github.com"
end tell
'''
    tree = _parse(parser, code)
    assert tree is not None
    assert tree.data == "start"
    # Should contain a tell_block
    tell_blocks = tree.find_data("tell_block")
    assert len(list(tell_blocks)) >= 1


# ---------------------------------------------------------------------------
# Test 2 — Set statement
# ---------------------------------------------------------------------------

def test_parse_set_statement(parser):
    code = 'set page_title to "Hello World"\n'
    tree = _parse(parser, code)
    assert tree is not None
    # Should contain a set_variable node
    set_nodes = list(tree.find_data("set_variable"))
    assert len(set_nodes) >= 1


# ---------------------------------------------------------------------------
# Test 3 — Try/catch block
# ---------------------------------------------------------------------------

def test_parse_try_catch(parser):
    code = '''try
    set x to "test"
catch err
    return err
end try
'''
    tree = _parse(parser, code)
    assert tree is not None
    try_blocks = list(tree.find_data("try_block"))
    assert len(try_blocks) >= 1


# ---------------------------------------------------------------------------
# Test 4 — Wait until
# ---------------------------------------------------------------------------

def test_parse_wait_until(parser):
    code = '''tell Chrome
    wait until loaded
end tell
'''
    tree = _parse(parser, code)
    assert tree is not None
    wait_nodes = list(tree.find_data("wait_until"))
    assert len(wait_nodes) >= 1


# ---------------------------------------------------------------------------
# Test 5 — Property access ("title of active_tab")
# ---------------------------------------------------------------------------

def test_parse_property_access(parser):
    code = 'set t to title of active_tab\n'
    tree = _parse(parser, code)
    assert tree is not None
    prop_nodes = list(tree.find_data("property_access"))
    assert len(prop_nodes) >= 1
