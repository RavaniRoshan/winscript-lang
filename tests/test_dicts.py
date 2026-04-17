import pytest
from pathlib import Path
from winscript.dicts.loader import DictLoader, AppDict, ObjectDef, CommandDef, PropertyDef
from winscript.dicts.validator import validate_dict
from winscript.errors import WinScriptDictNotFound

DICTS_DIR = Path(__file__).parent.parent / "dicts"

# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def chrome_dict():
    loader = DictLoader(extra_paths=[str(DICTS_DIR)])
    return loader.load("Chrome")

# ---------------------------------------------------------------------------
# loader tests
# ---------------------------------------------------------------------------

def test_load_chrome_returns_appdict(chrome_dict):
    assert isinstance(chrome_dict, AppDict)
    assert chrome_dict.name == "Chrome"
    assert chrome_dict.backend == "cdp"

def test_chrome_root_object(chrome_dict):
    root = chrome_dict.root_object()
    assert isinstance(root, ObjectDef)
    assert root.is_root is True

def test_find_command_navigate(chrome_dict):
    tab_obj = chrome_dict.objects["Tab"]
    cmd = tab_obj.find_command("navigate")
    assert isinstance(cmd, CommandDef)
    assert cmd.name == "navigate"
    assert cmd.backend_method == "Page.navigate"

def test_find_property_title(chrome_dict):
    tab_obj = chrome_dict.objects["Tab"]
    prop = tab_obj.find_property("title")
    assert isinstance(prop, PropertyDef)
    assert prop.name == "title"
    assert prop.backend_expression == "document.title"

def test_command_names(chrome_dict):
    tab_obj = chrome_dict.objects["Tab"]
    names = tab_obj.command_names()
    assert "navigate" in names
    assert "click" in names
    assert "type" in names

def test_load_nonexistent_raises(tmp_path):
    loader = DictLoader(extra_paths=[str(tmp_path)])
    with pytest.raises(WinScriptDictNotFound) as exc_info:
        loader.load("NonExistentApp")
    assert "NonExistentApp" in str(exc_info.value)
    assert exc_info.value.searched_paths

def test_loader_caches(chrome_dict):
    loader = DictLoader(extra_paths=[str(DICTS_DIR)])
    first = loader.load("Chrome")
    second = loader.load("Chrome")
    assert first is second   # same object from cache

# ---------------------------------------------------------------------------
# validator tests
# ---------------------------------------------------------------------------

VALID_DICT = {
    "meta": {"name": "TestApp", "version": "1.0", "backend": "cdp"},
    "connection": {"method": "cdp_websocket"},
    "objects": {
        "App": {
            "is_root": True,
            "description": "Root object",
            "properties": [
                {"name": "title", "type": "string", "cdp_method": "Runtime.evaluate"}
            ],
            "commands": [
                {"name": "quit", "syntax": "quit", "cdp_method": "Browser.close"}
            ],
        }
    },
}

def test_validate_valid_dict():
    errs = validate_dict(VALID_DICT)
    assert errs == []

def test_validate_missing_meta_name():
    data = {
        "meta": {"version": "1.0", "backend": "cdp"},
        "connection": {"method": "cdp_websocket"},
        "objects": {"App": {"is_root": True, "commands": [], "properties": []}},
    }
    errs = validate_dict(data)
    assert any("meta.name" in e for e in errs)

def test_validate_bad_backend():
    data = {
        "meta": {"name": "X", "version": "1", "backend": "rest"},
        "connection": {"method": "http"},
        "objects": {"App": {"is_root": True, "commands": [], "properties": []}},
    }
    errs = validate_dict(data)
    assert any("backend" in e for e in errs)

def test_validate_no_root():
    data = {
        "meta": {"name": "X", "version": "1", "backend": "cdp"},
        "connection": {"method": "cdp_websocket"},
        "objects": {"App": {"is_root": False, "commands": [], "properties": []}},
    }
    errs = validate_dict(data)
    assert any("is_root" in e for e in errs)

def test_validate_duplicate_command():
    data = {
        "meta": {"name": "X", "version": "1", "backend": "cdp"},
        "connection": {"method": "cdp_websocket"},
        "objects": {
            "App": {
                "is_root": True,
                "commands": [
                    {"name": "quit", "syntax": "quit", "cdp_method": "Browser.close"},
                    {"name": "quit", "syntax": "quit", "cdp_method": "Browser.close"},
                ],
                "properties": [],
            }
        },
    }
    errs = validate_dict(data)
    assert any("duplicate" in e for e in errs)

def test_validate_command_no_method():
    data = {
        "meta": {"name": "X", "version": "1", "backend": "cdp"},
        "connection": {"method": "cdp_websocket"},
        "objects": {
            "App": {
                "is_root": True,
                "commands": [{"name": "doThing", "syntax": "do thing"}],
                "properties": [],
            }
        },
    }
    errs = validate_dict(data)
    assert any("cdp_method" in e or "method" in e for e in errs)
