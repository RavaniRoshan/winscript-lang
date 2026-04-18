import pytest
from winscript.runtime import WinScriptRuntime
from winscript.errors import WinScriptError

@pytest.fixture
def runtime():
    return WinScriptRuntime()

def test_function_defined_and_called(runtime):
    code = """
    on double(n)
        return n * 2
    end on
    set x to double(5)
    return x
    """
    assert runtime.execute(code) == 10.0

def test_function_hoisting(runtime):
    code = """
    set x to greet("World")
    on greet(name)
        return "Hello " & name
    end on
    return x
    """
    assert runtime.execute(code) == "Hello World"

def test_local_variable_does_not_leak(runtime):
    code = """
    on setIt()
        local secret
        set secret to 99
    end on
    setIt()
    return secret
    """
    with pytest.raises(WinScriptError) as excinfo:
        runtime.execute(code)
    assert "Variable 'secret' is not defined" in str(excinfo.value)

def test_global_variable_accessible_in_function(runtime):
    code = """
    global counter
    set counter to 0
    on inc()
        set counter to counter + 1
    end on
    inc()
    inc()
    return counter
    """
    assert runtime.execute(code) == 2.0

def test_repeat_times_block(runtime):
    code = """
    set x to 0
    repeat 3 times
        set x to x + 1
    end repeat
    return x
    """
    assert runtime.execute(code) == 3.0

def test_repeat_with_list(runtime):
    code = """
    set result to ""
    set my_list to ["a", "b", "c"]
    repeat with item in my_list
        set result to result & item
    end repeat
    return result
    """
    assert runtime.execute(code) == "abc"

def test_nested_tell_inside_function(runtime):
    code = """
    on doSomething()
        tell Chrome
            return "ok"
        end tell
    end on
    set result to doSomething()
    return result
    """
    # Just mock resolving tell Chrome to avoid dict loader errors
    # Wait, the runtime fixture doesn't mock dictionaries. We can test with a mocked resolver or just use a dummy dictate.
    # We can use a try catch block if Chrome isn't loaded, or provide an empty dict.
    # Actually Chrome dict is in dicts/chrome.wsdict. It should load.
    assert runtime.execute(code) == "ok"

def test_wrong_arg_count(runtime):
    code = """
    on greet(name)
        return name
    end on
    greet("A", "B")
    """
    with pytest.raises(WinScriptError) as excinfo:
        runtime.execute(code)
    assert "expects 1 arguments, got 2" in str(excinfo.value)
