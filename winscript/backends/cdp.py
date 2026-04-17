"""
winscript.backends.cdp — Chrome DevTools Protocol backend.

Connects to Chrome via WebSocket on the CDP debug port (default 9222).
Implements both raw CDP methods and _winscript_* smart methods.

Usage:
    backend = CDPBackend(port=9222)
    backend.connect()
    backend.get_property("Runtime.evaluate", "document.title")
    backend.execute("Page.navigate", {"url": "https://github.com"})
    backend.disconnect()
"""

import json
import subprocess
import time
from typing import Any

from winscript.backends.base import Backend
from winscript.errors import (
    WinScriptConnectionError,
    WinScriptError,
    WinScriptTimeoutError,
)

# ---------------------------------------------------------------------------
# Helpers for sync WebSocket usage (websockets 12+ is async-first)
# ---------------------------------------------------------------------------

def _ws_connect_sync(url: str, timeout: float = 5.0):
    """Open a WebSocket connection synchronously via websockets.sync.client."""
    from websockets.sync.client import connect
    return connect(url, open_timeout=timeout)


def _http_get_json(url: str, timeout: float = 3.0) -> Any:
    """Tiny HTTP GET → JSON without pulling in requests as a hard dep."""
    import urllib.request
    import urllib.error
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, OSError):
        return None


# ---------------------------------------------------------------------------
# Key-name → virtual-key-code map for _winscript_press
# ---------------------------------------------------------------------------

_KEY_MAP: dict[str, tuple[str, int]] = {
    "Enter":      ("Enter",      13),
    "Tab":        ("Tab",         9),
    "Escape":     ("Escape",     27),
    "Backspace":  ("Backspace",   8),
    "Delete":     ("Delete",     46),
    "Space":      (" ",          32),
    "ArrowUp":    ("ArrowUp",    38),
    "ArrowDown":  ("ArrowDown",  40),
    "ArrowLeft":  ("ArrowLeft",  37),
    "ArrowRight": ("ArrowRight", 39),
    "Home":       ("Home",       36),
    "End":        ("End",        35),
    "PageUp":     ("PageUp",     33),
    "PageDown":   ("PageDown",   34),
    "F1":         ("F1",        112),
    "F2":         ("F2",        113),
    "F3":         ("F3",        114),
    "F4":         ("F4",        115),
    "F5":         ("F5",        116),
    "F6":         ("F6",        117),
    "F7":         ("F7",        118),
    "F8":         ("F8",        119),
    "F9":         ("F9",        120),
    "F10":        ("F10",       121),
    "F11":        ("F11",       122),
    "F12":        ("F12",       123),
}


# ═══════════════════════════════════════════════════════════════════════════
# CDPBackend
# ═══════════════════════════════════════════════════════════════════════════

class CDPBackend(Backend):
    """
    Chrome DevTools Protocol backend.

    Connects to a running Chrome instance (or launches one) over the
    CDP WebSocket debug port.  Exposes both raw CDP calls and higher-level
    ``_winscript_*`` smart methods.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 9222,
        launch_command: str | None = None,
        launch_wait_ms: int = 2500,
    ):
        self.host = host
        self.port = port
        self.launch_command = launch_command
        self.launch_wait_ms = launch_wait_ms

        self._ws = None            # websockets sync connection
        self._target_id: str = ""
        self._session_id: str = ""
        self._msg_id: int = 0

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    def connect(self) -> None:
        """
        Connect to Chrome's CDP endpoint.

        1. Try ``GET http://<host>:<port>/json`` → list of targets.
        2. If unreachable and *launch_command* is set → launch Chrome,
           sleep, retry once.
        3. Pick the first ``page``-type target.
        4. Open a WebSocket to that target's ``webSocketDebuggerUrl``.
        """
        targets = self._discover_targets()

        if targets is None and self.launch_command:
            self._launch_chrome()
            targets = self._discover_targets()

        if targets is None:
            raise WinScriptConnectionError(
                "Chrome",
                hint=f"Start Chrome with --remote-debugging-port={self.port}",
            )

        # Find the first page target
        page_target = None
        for t in targets:
            if t.get("type") == "page":
                page_target = t
                break

        if page_target is None:
            # No page tab open — create one by connecting to browser endpoint
            ws_url = self._browser_ws_url()
            if ws_url:
                try:
                    tmp_ws = _ws_connect_sync(ws_url)
                    self._msg_id += 1
                    tmp_ws.send(json.dumps({
                        "id": self._msg_id,
                        "method": "Target.createTarget",
                        "params": {"url": "about:blank"},
                    }))
                    tmp_ws.recv()
                    tmp_ws.close()
                except Exception:
                    pass
                time.sleep(0.5)
                targets = self._discover_targets() or []
                for t in targets:
                    if t.get("type") == "page":
                        page_target = t
                        break

        if page_target is None:
            raise WinScriptConnectionError(
                "Chrome",
                hint="Could not find any open tab to attach to.",
            )

        ws_url = page_target.get("webSocketDebuggerUrl", "")
        if not ws_url:
            raise WinScriptConnectionError(
                "Chrome",
                hint="Target has no webSocketDebuggerUrl. Is another debugger attached?",
            )

        self._target_id = page_target.get("id", "")
        self._ws = _ws_connect_sync(ws_url)

    def disconnect(self) -> None:
        """Close the WebSocket connection."""
        if self._ws:
            try:
                self._ws.close()
            except Exception:
                pass
            self._ws = None

    # ------------------------------------------------------------------
    # Core CDP communication
    # ------------------------------------------------------------------

    def send(self, method: str, params: dict | None = None) -> dict:
        """
        Send a single CDP command and wait for the matching response.
        Returns the ``result`` dict from the CDP response.
        Raises ``WinScriptError`` on CDP error responses.
        """
        if self._ws is None:
            raise WinScriptConnectionError(
                "Chrome",
                hint="Not connected. Call connect() first.",
            )

        self._msg_id += 1
        msg_id = self._msg_id
        message = {"id": msg_id, "method": method}
        if params:
            message["params"] = params

        self._ws.send(json.dumps(message))

        # Read responses until we get the one matching our msg_id.
        # Skip CDP events (no "id" field) along the way.
        while True:
            raw = self._ws.recv()
            resp = json.loads(raw)
            if resp.get("id") == msg_id:
                if "error" in resp:
                    err = resp["error"]
                    raise WinScriptError(
                        f"CDP error in {method}: {err.get('message', str(err))}",
                        app="Chrome",
                        command=method,
                    )
                return resp.get("result", {})
            # else: it's an async event — discard and keep reading

    # ------------------------------------------------------------------
    # Backend interface
    # ------------------------------------------------------------------

    def execute(self, method: str, params: dict | None = None) -> Any:
        """
        Execute a command from the .wsdict definition.
        Routes ``_winscript_*`` methods to the local smart handler;
        everything else goes as a raw CDP call.
        """
        if method.startswith("_winscript_"):
            handler = getattr(self, method, None)
            if handler is None:
                raise WinScriptError(f"Unknown built-in method: {method}")
            return handler(**(params or {}))
        return self.send(method, params)

    def get_property(
        self,
        backend_method: str,
        backend_expression: str | None = None,
        params: dict | None = None,
    ) -> Any:
        """
        Read a property value.

        If *backend_expression* is set → ``Runtime.evaluate(expression)``.
        Otherwise → raw CDP method call.
        """
        if backend_expression:
            result = self.send("Runtime.evaluate", {
                "expression": backend_expression,
                "returnByValue": True,
            })
            remote = result.get("result", {})
            if remote.get("type") == "undefined":
                return None
            return remote.get("value")

        return self.send(backend_method, params or {})

    # ------------------------------------------------------------------
    # _winscript_* smart methods
    # ------------------------------------------------------------------

    def _winscript_click(self, selector: str) -> None:
        """
        Smart click — tries CSS selector, then text content match, then XPath.
        Scrolls element into view, computes center coords, dispatches
        mousePressed + mouseReleased.
        """
        js = f"""
        (function() {{
            let sel = {json.dumps(selector)};
            let el = document.querySelector(sel);
            if (!el) {{
                let all = document.querySelectorAll(
                    'button,a,input,select,textarea,label,[role="button"],[role="link"],[role="tab"]'
                );
                for (let e of all) {{
                    if (e.innerText && e.innerText.trim().includes(sel)) {{
                        el = e; break;
                    }}
                }}
            }}
            if (!el) {{
                try {{
                    let xr = document.evaluate(
                        sel, document, null,
                        XPathResult.FIRST_ORDERED_NODE_TYPE, null
                    );
                    el = xr.singleNodeValue;
                }} catch(e) {{}}
            }}
            if (!el) return null;
            el.scrollIntoView({{block: 'center'}});
            let rect = el.getBoundingClientRect();
            return {{x: rect.x + rect.width / 2, y: rect.y + rect.height / 2}};
        }})()
        """
        result = self.send("Runtime.evaluate", {
            "expression": js,
            "returnByValue": True,
        })
        coords = result.get("result", {}).get("value")
        if not coords:
            raise WinScriptError(
                f"Element not found: '{selector}'",
                app="Chrome",
                command="click",
            )

        x, y = coords["x"], coords["y"]
        self.send("Input.dispatchMouseEvent", {
            "type": "mousePressed", "x": x, "y": y,
            "button": "left", "clickCount": 1,
        })
        self.send("Input.dispatchMouseEvent", {
            "type": "mouseReleased", "x": x, "y": y,
            "button": "left", "clickCount": 1,
        })

    def _winscript_type(self, text: str, selector: str = "") -> None:
        """
        Focus an element (if *selector* given), clear it, then insert *text*.
        Uses ``Input.insertText`` for clean, framework-friendly input.
        """
        if selector:
            self._winscript_click(selector)
            time.sleep(0.05)  # tiny pause for focus to settle

        # Select all existing content → delete
        self.send("Input.dispatchKeyEvent", {
            "type": "keyDown", "key": "a",
            "code": "KeyA", "windowsVirtualKeyCode": 65,
            "modifiers": 2,  # Ctrl
        })
        self.send("Input.dispatchKeyEvent", {
            "type": "keyUp", "key": "a",
            "code": "KeyA", "windowsVirtualKeyCode": 65,
        })
        self.send("Input.dispatchKeyEvent", {
            "type": "keyDown", "key": "Backspace",
            "code": "Backspace", "windowsVirtualKeyCode": 8,
        })
        self.send("Input.dispatchKeyEvent", {
            "type": "keyUp", "key": "Backspace",
            "code": "Backspace", "windowsVirtualKeyCode": 8,
        })

        # Insert text in one shot
        self.send("Input.insertText", {"text": text})

    def _winscript_wait_loaded(self, timeout_ms: int = 10000) -> None:
        """Poll ``document.readyState`` every 500 ms until ``'complete'``."""
        deadline = time.time() + (timeout_ms / 1000)
        while time.time() < deadline:
            state = self.get_property("Runtime.evaluate", "document.readyState")
            if state == "complete":
                return
            time.sleep(0.5)
        raise WinScriptTimeoutError("page loaded", timeout_ms)

    def _winscript_find_element(self, selector: str) -> str:
        """Return the visible text content of the first matching element."""
        js = f"""
        (function() {{
            let el = document.querySelector({json.dumps(selector)});
            return el ? el.innerText : '';
        }})()
        """
        result = self.send("Runtime.evaluate", {
            "expression": js, "returnByValue": True,
        })
        return result.get("result", {}).get("value", "")

    def _winscript_scroll(self, target: str) -> None:
        """
        Scroll to *target*: ``"top"``, ``"bottom"``, or a CSS selector.
        """
        if target.lower() == "top":
            js = "window.scrollTo(0, 0)"
        elif target.lower() == "bottom":
            js = "window.scrollTo(0, document.body.scrollHeight)"
        else:
            js = f"""
            (function() {{
                let el = document.querySelector({json.dumps(target)});
                if (el) el.scrollIntoView({{behavior: 'smooth', block: 'center'}});
            }})()
            """
        self.send("Runtime.evaluate", {"expression": js})

    def _winscript_get_attribute(self, attr: str, selector: str) -> str | None:
        """Read a DOM attribute from the first matching element."""
        js = f"""
        (function() {{
            let el = document.querySelector({json.dumps(selector)});
            return el ? el.getAttribute({json.dumps(attr)}) : null;
        }})()
        """
        result = self.send("Runtime.evaluate", {
            "expression": js, "returnByValue": True,
        })
        val = result.get("result", {}).get("value")
        return val

    def _winscript_fill_form(self, selector: str, value: str) -> None:
        """
        Fill a form field. Works for ``<input>``, ``<textarea>``, ``<select>``.
        Fires native ``input`` and ``change`` events so React/Vue pick it up.
        """
        js = f"""
        (function() {{
            let el = document.querySelector({json.dumps(selector)});
            if (!el) return false;
            let nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                window.HTMLInputElement.prototype, 'value'
            );
            let nativeTextareaValueSetter = Object.getOwnPropertyDescriptor(
                window.HTMLTextAreaElement.prototype, 'value'
            );
            if (el.tagName === 'SELECT') {{
                el.value = {json.dumps(value)};
            }} else if (el.tagName === 'TEXTAREA' && nativeTextareaValueSetter) {{
                nativeTextareaValueSetter.set.call(el, {json.dumps(value)});
            }} else if (nativeInputValueSetter) {{
                nativeInputValueSetter.set.call(el, {json.dumps(value)});
            }} else {{
                el.value = {json.dumps(value)};
            }}
            el.dispatchEvent(new Event('input', {{bubbles: true}}));
            el.dispatchEvent(new Event('change', {{bubbles: true}}));
            return true;
        }})()
        """
        result = self.send("Runtime.evaluate", {
            "expression": js, "returnByValue": True,
        })
        success = result.get("result", {}).get("value")
        if not success:
            raise WinScriptError(
                f"Could not fill form field: '{selector}'",
                app="Chrome",
                command="fill_form",
            )

    def _winscript_query_all(self, selector: str) -> list[str]:
        """Return a list of innerText from all matching elements."""
        js = f"""
        Array.from(document.querySelectorAll({json.dumps(selector)}))
             .map(el => el.innerText)
        """
        result = self.send("Runtime.evaluate", {
            "expression": js, "returnByValue": True,
        })
        return result.get("result", {}).get("value", [])

    def _winscript_get_active_tab(self) -> dict:
        """Return metadata about the active tab (via /json endpoint)."""
        targets = self._discover_targets()
        if targets:
            for t in targets:
                if t.get("type") == "page":
                    return {"id": t.get("id"), "title": t.get("title", ""),
                            "url": t.get("url", "")}
        return {}

    def _winscript_get_windows(self) -> list[dict]:
        """List all browser windows via CDP."""
        try:
            result = self.send("Browser.getWindowForTarget", {
                "targetId": self._target_id,
            })
            return [result] if result else []
        except WinScriptError:
            return []

    def _winscript_press(self, key: str) -> None:
        """Dispatch a keyboard event for the given key name."""
        key_info = _KEY_MAP.get(key, (key, 0))
        key_name, vk_code = key_info

        self.send("Input.dispatchKeyEvent", {
            "type": "keyDown",
            "key": key_name,
            "windowsVirtualKeyCode": vk_code,
        })
        self.send("Input.dispatchKeyEvent", {
            "type": "keyUp",
            "key": key_name,
            "windowsVirtualKeyCode": vk_code,
        })

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _discover_targets(self) -> list[dict] | None:
        """GET /json → list of CDP targets, or None if unreachable."""
        url = f"http://{self.host}:{self.port}/json"
        return _http_get_json(url)

    def _browser_ws_url(self) -> str | None:
        """GET /json/version → webSocketDebuggerUrl of the browser."""
        url = f"http://{self.host}:{self.port}/json/version"
        data = _http_get_json(url)
        if data and isinstance(data, dict):
            return data.get("webSocketDebuggerUrl")
        return None

    def _launch_chrome(self) -> None:
        """Launch Chrome in the background and wait for it to start."""
        if not self.launch_command:
            return
        try:
            subprocess.Popen(
                self.launch_command,
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError as e:
            raise WinScriptConnectionError(
                "Chrome",
                hint=f"Failed to launch: {self.launch_command}\n{e}",
            )
        # Wait for CDP port to become available
        deadline = time.time() + (self.launch_wait_ms / 1000)
        while time.time() < deadline:
            if self._discover_targets() is not None:
                return
            time.sleep(0.3)
