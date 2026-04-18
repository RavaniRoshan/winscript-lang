import pytest
from lark import Lark

with open("winscript/grammar.lark", "r", encoding="utf-8") as f:
    grammar_text = f.read()

parser = Lark(grammar_text, start='start', parser='earley')

def test_repeat_times():
    code = """
repeat 5 times
    set x to 1
end repeat
"""
    tree = parser.parse(code)
    assert tree is not None
    assert "repeat_times" in [t.data for t in tree.find_data("repeat_times")]

def test_repeat_while():
    code = """
repeat while count is less than 10
    set count to count + 1
end repeat
"""
    tree = parser.parse(code)
    assert tree is not None
    assert "repeat_while" in [t.data for t in tree.find_data("repeat_while")]

def test_repeat_with():
    code = """
repeat with item in my_list
    print item
end repeat
"""
    tree = parser.parse(code)
    assert tree is not None
    assert "repeat_with" in [t.data for t in tree.find_data("repeat_with")]

def test_function_def():
    code = """
on myFunc(arg1, arg2)
    return arg1 + arg2
end on
"""
    tree = parser.parse(code)
    assert tree is not None
    assert "function_def" in [t.data for t in tree.find_data("function_def")]

def test_function_call_stmt():
    code = """
doSomething("arg")
"""
    tree = parser.parse(code)
    assert tree is not None
    assert "function_call" in [t.data for t in tree.find_data("function_call")]

def test_scope_declaration():
    code = """
global counter
"""
    tree = parser.parse(code)
    assert tree is not None
    assert "scope_declaration" in [t.data for t in tree.find_data("scope_declaration")]

def test_declare_statement():
    code = """
declare count as integer
"""
    tree = parser.parse(code)
    assert tree is not None
    assert "declare_statement" in [t.data for t in tree.find_data("declare_statement")]

def test_using_statement():
    code = """
using "helpers.wslib"
"""
    tree = parser.parse(code)
    assert tree is not None
    assert "using_statement" in [t.data for t in tree.find_data("using_statement")]

