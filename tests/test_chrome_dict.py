import yaml
import pytest
from pathlib import Path
from winscript.dicts.loader import DictLoader, AppDict, CommandDef, PropertyDef
from winscript.dicts.validator import validate_dict

DICTS_DIR = Path(__file__).parent.parent / "dicts"
CHROME_PATH = DICTS_DIR / "chrome.wsdict"


@pytest.fixture(scope="module")
def chrome_raw():
    return yaml.safe_load(CHROME_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def chrome(chrome_raw):
    loader = DictLoader(extra_paths=[str(DICTS_DIR)])
    return loader.load("Chrome")


# ── YAML sanity ─────────────────────────────────────────────────────────────

def test_yaml_parses_cleanly(chrome_raw):
    """yaml.safe_load must succeed without errors."""
    assert isinstance(chrome_raw, dict)


# ── AppDict structure ────────────────────────────────────────────────────────

def test_appdict_returned(chrome):
    assert isinstance(chrome, AppDict)
    assert chrome.name == "Chrome"
    assert chrome.backend == "cdp"


def test_all_objects_present(chrome):
    assert "Browser" in chrome.objects
    assert "Tab" in chrome.objects
    assert "DOM" in chrome.objects


def test_root_object_is_browser(chrome):
    root = chrome.root_object()
    assert root.name == "Browser"
    assert root.is_root is True


# ── Browser commands ─────────────────────────────────────────────────────────

def test_browser_find_command_open(chrome):
    cmd = chrome.objects["Browser"].find_command("open")
    assert isinstance(cmd, CommandDef)
    assert cmd.name == "open"
    assert cmd.backend_method == "Target.createTarget"


def test_browser_commands_complete(chrome):
    names = chrome.objects["Browser"].command_names()
    for expected in ("open", "quit", "new_tab", "close_tab"):
        assert expected in names, f"Missing Browser command: {expected}"


def test_browser_property_active_tab(chrome):
    prop = chrome.objects["Browser"].find_property("active_tab")
    assert prop is not None
    assert prop.type == "Tab"


def test_browser_property_version(chrome):
    prop = chrome.objects["Browser"].find_property("version")
    assert prop is not None
    assert prop.backend_method == "Browser.getVersion"


# ── Tab properties ───────────────────────────────────────────────────────────

def test_tab_property_title(chrome):
    prop = chrome.objects["Tab"].find_property("title")
    assert isinstance(prop, PropertyDef)
    assert prop.backend_expression == "document.title"


def test_tab_property_url(chrome):
    prop = chrome.objects["Tab"].find_property("url")
    assert prop is not None
    assert prop.backend_expression == "location.href"


def test_tab_property_loaded(chrome):
    prop = chrome.objects["Tab"].find_property("loaded")
    assert prop is not None
    assert prop.type == "bool"
    assert "readyState" in prop.backend_expression


def test_tab_property_content(chrome):
    prop = chrome.objects["Tab"].find_property("content")
    assert prop is not None
    assert "innerText" in prop.backend_expression


def test_tab_property_html(chrome):
    prop = chrome.objects["Tab"].find_property("html")
    assert prop is not None
    assert "outerHTML" in prop.backend_expression


# ── Tab commands ─────────────────────────────────────────────────────────────

def test_tab_navigate_command(chrome):
    cmd = chrome.objects["Tab"].find_command("navigate")
    assert cmd is not None
    assert cmd.backend_method == "Page.navigate"
    assert len(cmd.args) == 1
    assert cmd.args[0]["name"] == "url"


def test_tab_click_command(chrome):
    cmd = chrome.objects["Tab"].find_command("click")
    assert cmd is not None
    assert cmd.backend_method == "_winscript_click"


def test_tab_type_command(chrome):
    cmd = chrome.objects["Tab"].find_command("type")
    assert cmd is not None
    assert cmd.backend_method == "_winscript_type"
    assert len(cmd.args) == 2


def test_tab_press_command(chrome):
    cmd = chrome.objects["Tab"].find_command("press")
    assert cmd is not None
    assert cmd.backend_method == "Input.dispatchKeyEvent"


def test_tab_run_script_command(chrome):
    cmd = chrome.objects["Tab"].find_command("run_script")
    assert cmd is not None
    assert cmd.backend_method == "Runtime.evaluate"


def test_tab_screenshot_command(chrome):
    cmd = chrome.objects["Tab"].find_command("screenshot")
    assert cmd is not None
    assert cmd.backend_method == "Page.captureScreenshot"


def test_tab_wait_until_loaded_command(chrome):
    cmd = chrome.objects["Tab"].find_command("wait_until_loaded")
    assert cmd is not None
    assert cmd.backend_method == "_winscript_wait_loaded"


def test_tab_advanced_commands(chrome):
    tab = chrome.objects["Tab"]
    for name in ("find_element", "scroll", "get_attribute", "fill_form"):
        cmd = tab.find_command(name)
        assert cmd is not None, f"Missing Tab command: {name}"
        assert cmd.backend_method.startswith("_winscript_")


# ── DOM commands ─────────────────────────────────────────────────────────────

def test_dom_query_command(chrome):
    cmd = chrome.objects["DOM"].find_command("query")
    assert cmd is not None
    assert cmd.backend_method == "_winscript_query_all"


def test_dom_evaluate_command(chrome):
    cmd = chrome.objects["DOM"].find_command("evaluate")
    assert cmd is not None
    assert cmd.backend_method == "Runtime.evaluate"


# ── Error definitions ────────────────────────────────────────────────────────

def test_error_definitions(chrome):
    codes = {e["code"] for e in chrome.errors}
    for expected in (
        "connection_refused", "element_not_found",
        "navigation_failed", "timeout", "javascript_error"
    ):
        assert expected in codes, f"Missing error code: {expected}"


# ── Validator ────────────────────────────────────────────────────────────────

def test_validate_chrome_dict_is_valid(chrome_raw):
    errs = validate_dict(chrome_raw)
    assert errs == [], f"Validation errors: {errs}"
