import pytest
import os
from pathlib import Path
from winscript.library import LibraryLoader
from winscript.runtime import WinScriptRuntime
from winscript.errors import WinScriptError
from winscript.parser import parse
from winscript.context import ExecutionContext

@pytest.fixture(autouse=True)
def setup_dummy_lib():
    libs_dir = Path.cwd() / "libs"
    libs_dir.mkdir(exist_ok=True)
    
    dummy_code = """
on dummy_func()
    return "dummy"
end on
"""
    (libs_dir / "dummy_lib.wslib").write_text(dummy_code, encoding="utf-8")
    
    bad_code = """
on valid()
end on
set x to 1
"""
    (libs_dir / "bad_lib.wslib").write_text(bad_code, encoding="utf-8")
    yield
    # Cleanup optional, but we leave it for inspection

def test_load_chrome_helpers():
    loader = LibraryLoader()
    funcs = loader.load("chrome_helpers.wslib")
    assert len(funcs) == 3
    names = {f.name for f in funcs}
    assert names == {"search_google", "get_page_text", "take_named_screenshot"}

def test_script_using_library_callable():
    runtime = WinScriptRuntime()
    # Check if search_google is callable by parsing and loading into context
    ast = parse('using "chrome_helpers.wslib"')
    context = ExecutionContext()
    runtime._load_libraries(ast.statements, context)
    assert context.get_function("search_google") is not None

def test_library_function_overridden():
    runtime = WinScriptRuntime()
    code = """
using "dummy_lib.wslib"
on dummy_func()
    return "script version"
end on
return dummy_func()
"""
    assert runtime.execute(code) == "script version"

def test_library_with_non_function():
    runtime = WinScriptRuntime()
    code = 'using "bad_lib.wslib"'
    with pytest.raises(WinScriptError) as exc:
        runtime.execute(code)
    assert "contains non-function statements" in str(exc.value)

def test_library_not_found():
    runtime = WinScriptRuntime()
    code = 'using "does_not_exist"'
    with pytest.raises(WinScriptError) as exc:
        runtime.execute(code)
    assert "Library not found" in str(exc.value)
    assert "Searched:" in str(exc.value)

def test_using_absolute_path():
    runtime = WinScriptRuntime()
    abs_path = (Path.cwd() / "libs" / "dummy_lib.wslib").absolute()
    # Handle windows/linux paths in string safely
    abs_path_str = str(abs_path).replace("\\\\", "/")
    code = f'using "{abs_path_str}"\nreturn dummy_func()'
    assert runtime.execute(code) == "dummy"

def test_using_no_extension():
    loader = LibraryLoader()
    funcs = loader.load("chrome_helpers")
    assert len(funcs) == 3
    assert funcs[0].name == "search_google"

    runtime = WinScriptRuntime()
    code = 'using "dummy_lib"\nreturn dummy_func()'
    assert runtime.execute(code) == "dummy"
