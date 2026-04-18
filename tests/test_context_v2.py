import pytest
from winscript.context import ExecutionContext
from winscript.errors import WinScriptError

def test_global_by_default():
    ctx = ExecutionContext()
    ctx.set_var("x", 1)
    
    ctx.push_function_scope("my_func")
    ctx.set_var("y", 2)
    assert ctx.get_var("x") == 1
    assert ctx.get_var("y") == 2
    ctx.pop_scope()
    
    assert ctx.get_var("x") == 1
    assert ctx.get_var("y") == 2

def test_local_declaration():
    ctx = ExecutionContext()
    ctx.set_var("x", 1)
    
    ctx.push_function_scope("my_func")
    ctx.declare_local("x")
    ctx.set_var("x", 2)
    assert ctx.get_var("x") == 2
    ctx.pop_scope()
    
    assert ctx.get_var("x") == 1

def test_global_declaration():
    ctx = ExecutionContext()
    ctx.set_var("x", 1)
    
    ctx.push_function_scope("my_func")
    ctx.declare_local("x")
    ctx.set_var("x", 2)
    
    ctx.push_block_scope("my_block")
    ctx.declare_global("x")
    ctx.set_var("x", 3)
    assert ctx.get_var("x") == 3
    ctx.pop_scope()
    
    assert ctx.get_var("x") == 2
    ctx.pop_scope()
    
    assert ctx.get_var("x") == 3

def test_repeat_with_scope():
    ctx = ExecutionContext()
    ctx.set_var("item", "global_item")
    
    ctx.push_function_scope("my_func")
    ctx.push_block_scope("repeat_with")
    ctx.declare_local("item")
    ctx.set_var("item", "loop_item")
    
    ctx.set_var("other", "goes_global")
    
    assert ctx.get_var("item") == "loop_item"
    assert ctx.get_var("other") == "goes_global"
    ctx.pop_scope()
    
    assert ctx.get_var("item") == "global_item"
    assert ctx.get_var("other") == "goes_global"
    ctx.pop_scope()
    
    assert ctx.get_var("item") == "global_item"
    assert ctx.get_var("other") == "goes_global"
