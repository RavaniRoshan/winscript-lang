# WinScript Dictionary Format Specification — v1

## Overview

A `.wsdict` file defines how WinScript talks to a specific application.
It maps natural-language commands to backend API calls using a structured
YAML format.

**Anyone can write a `.wsdict` file.** No changes to the WinScript runtime
are needed — just drop a new `.wsdict` in any search path and the language
instantly supports that app.

## File Format

`.wsdict` files use YAML syntax with the following top-level keys:

```yaml
meta:
  name: Chrome
  display_name: Google Chrome
  version: "1.0"
  backend: cdp          # cdp | com | uia
  description: |
    Full Chrome automation via Chrome DevTools Protocol.

connection:
  host: localhost
  port: 9222
  launch_command: "chrome.exe --remote-debugging-port=9222"
  launch_wait_ms: 2000

objects:
  Browser:
    # ... object definition
  Tab:
    # ... object definition

errors:
  - code: ERR_NOT_CONNECTED
    message: "Chrome is not running with --remote-debugging-port=9222"
```

## Meta Section

| Field | Required | Description |
|-------|----------|-------------|
| `name` | ✅ | App identifier (matches `tell <name>`) |
| `display_name` | ❌ | Human-friendly name |
| `version` | ✅ | Dictionary version |
| `backend` | ✅ | Backend type: `cdp`, `com`, or `uia` |
| `description` | ❌ | What this dictionary automates |

## Connection Section

Backend-specific connection parameters. The runtime passes these
directly to the backend constructor.

### CDP backend

```yaml
connection:
  host: localhost
  port: 9222
  launch_command: "chrome.exe --remote-debugging-port=9222"
  launch_wait_ms: 2000
```

### COM backend

```yaml
connection:
  prog_id: "Excel.Application"
  visible: true
```

### UIA backend

```yaml
connection:
  process_name: "notepad.exe"
  window_title: "Untitled - Notepad"
```

## Objects Section

Each object defines a scope of commands and properties.

```yaml
objects:
  Browser:
    description: "The root browser object"
    is_root: true
    properties:
      - name: active_tab
        type: Tab
        description: "The currently focused tab"
        cdp_method: _winscript_get_active_tab
    commands:
      - name: open
        syntax: 'open {url}'
        description: "Open a URL in a new tab"
        cdp_method: Target.createTarget
        args:
          - name: url
            type: string
            required: true
```

### Object Fields

| Field | Required | Description |
|-------|----------|-------------|
| `description` | ❌ | What this object represents |
| `is_root` | ❌ | If `true`, this is the default scope for `tell` blocks. Exactly one object must be root. |
| `properties` | ❌ | List of readable properties |
| `commands` | ❌ | List of executable commands |

### Property Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | ✅ | Property name (used in `prop of object`) |
| `type` | ✅ | Value type: `string`, `int`, `bool`, `list[Tab]`, etc. |
| `description` | ❌ | What this property returns |
| `cdp_method` | depends | Backend method to call (CDP) |
| `cdp_expression` | depends | JS expression for `Runtime.evaluate` |
| `com_method` | depends | COM method to call |
| `uia_method` | depends | UIA pattern/property to read |

### Command Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | ✅ | Command name (used in WinScript syntax) |
| `syntax` | ✅ | Human-readable syntax with `{arg}` placeholders |
| `description` | ❌ | What this command does |
| `cdp_method` | depends | CDP method or `_winscript_*` smart method |
| `args` | ❌ | List of argument definitions |

### Argument Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | ✅ | Argument name |
| `type` | ✅ | Expected type: `string`, `int`, `bool`, `any` |
| `required` | ❌ | Whether the argument is mandatory (default: `false`) |

## Smart Methods (`_winscript_*`)

When a simple CDP/COM/UIA call isn't enough, backends implement
"smart methods" prefixed with `_winscript_`. These handle complex
multi-step operations as a single atomic action.

| Method | Purpose |
|--------|---------|
| `_winscript_click` | Smart click: CSS → text fallback → XPath |
| `_winscript_type` | Focus + clear + type with key events |
| `_winscript_wait_loaded` | Poll `document.readyState === 'complete'` |
| `_winscript_find_element` | Get element text/HTML by selector |
| `_winscript_get_active_tab` | Return active tab metadata |

## Backend Types

| Backend | Library | Apps |
|---------|---------|------|
| `cdp` | websockets | Chrome, Edge, any Electron app |
| `com` | pywin32 | Excel, Word, Outlook, Access |
| `uia` | pywinauto | Notepad, Calculator, File Explorer |

## Discovery Paths

`.wsdict` files are searched in this order (first match wins):

1. `%APPDATA%\WinScript\dicts\`
2. `%PROGRAMFILES%\WinScript\dicts\`
3. `%PROGRAMFILES(X86)%\WinScript\dicts\`
4. `./dicts/` (relative to CWD)
5. Caller-supplied extra paths

## Validation Rules

1. `meta.name` is required and must be non-empty
2. `meta.backend` must be one of: `cdp`, `com`, `uia`
3. Exactly one object must have `is_root: true`
4. Command names must be unique within an object
5. All `args` entries must have `name` and `type`

## Example: Minimal Dictionary

```yaml
meta:
  name: Notepad
  version: "1.0"
  backend: uia
  description: "Automate Windows Notepad"

connection:
  process_name: "notepad.exe"

objects:
  Editor:
    description: "The main text editor"
    is_root: true
    properties:
      - name: text
        type: string
        uia_method: GetWindowText
    commands:
      - name: type
        syntax: 'type {text}'
        uia_method: TypeKeys
        args:
          - name: text
            type: string
            required: true
      - name: save
        syntax: 'save'
        uia_method: MenuSelect("File->Save")
```
