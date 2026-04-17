from winscript.context import ExecutionContext
from winscript.errors import *
import pytest

def test_execution_context_vars():
    ctx = ExecutionContext()
    ctx.set_var("test_var", "test_value")
    assert ctx.has_var("test_var")
    assert ctx.get_var("test_var") == "test_value"
    
    with pytest.raises(WinScriptError) as exc_info:
        ctx.get_var("undefined_var")
    assert "undefined" in str(exc_info.value)

def test_execution_context_tell_stack():
    ctx = ExecutionContext()
    assert ctx.current_app is None
    assert ctx.tell_depth == 0
    
    ctx.push_tell("Chrome")
    assert ctx.current_app == "Chrome"
    assert ctx.tell_depth == 1
    
    ctx.push_tell("Excel")
    assert ctx.current_app == "Excel"
    assert ctx.tell_depth == 2
    
    ctx.pop_tell()
    assert ctx.current_app == "Chrome"
    assert ctx.tell_depth == 1
    
    ctx.pop_tell()
    assert ctx.current_app is None
    assert ctx.tell_depth == 0

def test_execution_context_return():
    ctx = ExecutionContext()
    assert not ctx.has_returned
    ctx.set_return(42)
    assert ctx.has_returned
    assert ctx.return_value == 42
    
def test_error_formatting():
    e1 = WinScriptSyntaxError("test", line=5)
    assert str(e1) == "Syntax error at line 5: test"
    
    e2 = WinScriptDictNotFound("Notepad", ["path/a", "path/b"])
    assert "Notepad" in str(e2)
    assert "path/a" in str(e2)
    
    e3 = WinScriptCommandNotFound("print", "Notepad", ["save", "quit"])
    assert "print" in str(e3)
    assert "save, quit" in str(e3)

    e4 = WinScriptPropertyNotFound("title", "tab", "Chrome")
    assert "title" in str(e4)
    assert "tab" in str(e4)

    e5 = WinScriptTypeError("url", "string", "int", "navigate")
    assert "url" in str(e5)
    assert "string" in str(e5)
    
    e6 = WinScriptTimeoutError("loaded", 5000)
    assert "loaded" in str(e6)
    assert "5000" in str(e6)
    
    e7 = WinScriptConnectionError("Chrome", hint="Run it with debug flags.")
    assert "Chrome" in str(e7)
    assert "Hint:" in str(e7)
