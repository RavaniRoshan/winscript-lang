import pytest
from winscript.runtime import WinScriptRuntime
from winscript.errors import WinScriptTypeError
from winscript.types import infer_type, WSType

@pytest.fixture
def runtime():
    return WinScriptRuntime()

def test_declare_and_set_ok(runtime):
    code = """
    declare count as integer
    set count to 5
    return count
    """
    assert runtime.execute(code) == 5

def test_declare_and_set_error(runtime):
    code = """
    declare count as integer
    set count to "hello"
    """
    with pytest.raises(WinScriptTypeError) as excinfo:
        runtime.execute(code)
    assert "Argument 'count' in 'set' expects integer, got string" in str(excinfo.value)

def test_declare_coercion_decimal_to_int(runtime):
    code = """
    declare count as integer
    set count to 3.0
    return count
    """
    assert runtime.execute(code) == 3

def test_declare_coercion_to_string(runtime):
    code = """
    declare name as string
    set name to 42
    return name
    """
    assert runtime.execute(code) == "42"

def test_declare_boolean_error(runtime):
    code = """
    declare flag as boolean
    set flag to "true"
    """
    with pytest.raises(WinScriptTypeError) as excinfo:
        runtime.execute(code)
    assert "Argument 'flag' in 'set' expects boolean, got string" in str(excinfo.value)

def test_undeclared_var_no_type_checking(runtime):
    code = """
    set x to 5
    set x to "hello"
    return x
    """
    assert runtime.execute(code) == "hello"

def test_declare_list(runtime):
    code = """
    declare items as list
    set items to ["a", "b"]
    return items
    """
    assert runtime.execute(code) == ["a", "b"]

def test_infer_type():
    assert infer_type("hello") == WSType.STRING
    assert infer_type(42) == WSType.INTEGER
