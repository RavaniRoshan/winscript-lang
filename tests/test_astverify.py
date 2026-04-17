# tests/test_astverify.py

import sys
from pathlib import Path
from winscript.parser import parse
from winscript.ast_nodes import *

def check_tell_block():
    code = 'tell Chrome\n  navigate to "https://github.com"\nend tell'
    ast = parse(code)
    try:
        assert len(ast.statements) == 1
        tell = ast.statements[0]
        assert isinstance(tell, TellBlock)
        assert tell.app_name == "Chrome"
        assert len(tell.statements) == 1
        cmd = tell.statements[0]
        assert isinstance(cmd, CommandStatement)
        assert cmd.name == "navigate"
        assert isinstance(cmd.kwargs["to"], StringLiteral)
        assert cmd.kwargs["to"].value == "https://github.com"
        print("TellBlock verified")
    except Exception as e:
        print(f"TellBlock verification failed!")
        raise

def check_property_access():
    code = 'set title to title of active tab'
    ast = parse(code)
    try:
        assert len(ast.statements) == 1
        set_node = ast.statements[0]
        assert isinstance(set_node, SetStatement)
        assert set_node.target == "title"
        val = set_node.value
        assert isinstance(val, PropertyAccess)
        assert val.prop == "title"
        assert isinstance(val.of_expr, PropertyAccess)
        assert val.of_expr.prop == "active"
        assert isinstance(val.of_expr.of_expr, Identifier)
        assert val.of_expr.of_expr.name == "tab"
        print("PropertyAccess verified")
    except Exception as e:
        print(f"PropertyAccess verification failed!")
        raise

def check_try_catch():
    code = '''try
    set a to 1
catch error_msg
    return error_msg
end try'''
    ast = parse(code)
    try:
        assert len(ast.statements) == 1
        try_node = ast.statements[0]
        assert isinstance(try_node, TryBlock)
        assert try_node.catch_var == "error_msg"
        assert len(try_node.try_stmts) == 1
        assert isinstance(try_node.try_stmts[0], SetStatement)
        assert len(try_node.catch_stmts) == 1
        assert isinstance(try_node.catch_stmts[0], ReturnStatement)
        print("TryBlock verified")
    except Exception as e:
        print(f"TryBlock verification failed!")
        raise

if __name__ == "__main__":
    check_tell_block()
    check_property_access()
    check_try_catch()
    print("All tests passed.")
