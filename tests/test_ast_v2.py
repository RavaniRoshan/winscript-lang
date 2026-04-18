import pytest
from winscript.parser import parse, validate_v2
from winscript.ast_nodes import *

def test_repeat_times_ast():
    code = "repeat 5 times\n  set x to 1\nend repeat"
    ast = parse(code)
    assert isinstance(ast.statements[0], RepeatTimesBlock)
    assert isinstance(ast.statements[0].count_expr, NumberLiteral)
    assert ast.statements[0].count_expr.value == 5.0
    assert isinstance(ast.statements[0].statements[0], SetStatement)

def test_function_def_ast():
    code = "on greet(name)\n  return name\nend on"
    ast = parse(code)
    assert isinstance(ast.statements[0], FunctionDef)
    assert ast.statements[0].name == "greet"
    assert ast.statements[0].params == ["name"]
    assert isinstance(ast.statements[0].statements[0], ReturnStatement)

def test_declare_statement_ast():
    code = "declare count as integer"
    ast = parse(code)
    assert isinstance(ast.statements[0], DeclareStatement)
    assert ast.statements[0].variable == "count"
    assert ast.statements[0].type_name == "integer"

def test_list_literal_ast():
    code = 'set my_list to ["a", "b", "c"]'
    ast = parse(code)
    assert isinstance(ast.statements[0], SetStatement)
    assert isinstance(ast.statements[0].value, ListLiteral)
    assert len(ast.statements[0].value.items) == 3
    assert isinstance(ast.statements[0].value.items[0], StringLiteral)
    assert ast.statements[0].value.items[0].value == "a"

def test_validate_v2_using_order():
    code = 'tell app\nend tell\nusing "lib.wslib"'
    ast = parse(code)
    errors = validate_v2(ast)
    assert errors == ["UsingStatement must appear at top of file"]

def test_validate_v2_nested_function():
    code = "on outer()\n  on inner()\n  end on\nend on"
    ast = parse(code)
    errors = validate_v2(ast)
    assert errors == ["Nested functions are not allowed in v2"]
