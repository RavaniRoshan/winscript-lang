<p align="center">
  <img src="https://img.shields.io/badge/WinScript-v1.0-blue?style=for-the-badge&logo=windows&logoColor=white" alt="WinScript v1.0"/>
  <img src="https://img.shields.io/badge/license-MIT-green?style=for-the-badge" alt="MIT License"/>
  <img src="https://img.shields.io/badge/python-3.11+-yellow?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.11+"/>
  <img src="https://img.shields.io/badge/tests-130%20passing-brightgreen?style=for-the-badge" alt="130 Tests Passing"/>
</p>

<h1 align="center">🪟 WinScript</h1>

<p align="center">
  <strong>The open scripting language for Windows automation.</strong><br/>
  AppleScript had 40 years. Windows had nothing.<br/>
  Until now.
</p>

<p align="center">
  <a href="#-quickstart">Quickstart</a> •
  <a href="#-language-overview">Language</a> •
  <a href="#-architecture">Architecture</a> •
  <a href="#-mcp-integration">MCP Integration</a> •
  <a href="#-write-your-own-dictionary">Extend</a> •
  <a href="#-roadmap">Roadmap</a>
</p>

---

## ✨ What is WinScript?

WinScript is a **real language** — not a tool wrapper — designed so AI agents and humans can automate any Windows application using natural, readable syntax.

```winscript
tell Chrome
    navigate to "https://github.com"
    wait until loaded
    set pageTitle to title of active tab
    return pageTitle
end tell
```

**No pyautogui. No pixel coordinates. No fragile screen scraping.**
Just structured commands that talk directly to application APIs.

---

## 🏗️ How it works

WinScript uses an **open dictionary format** (`.wsdict`) that maps natural-language commands to backend API calls:

```
your_script.ws  →  grammar.lark  →  AST  →  resolver + chrome.wsdict  →  CDP backend  →  Chrome
```

| Layer | What it does |
|-------|-------------|
| **Grammar** | Lark PEG parser — `tell/end tell`, `set`, `return`, `wait`, `try/catch` |
| **AST** | Clean dataclass nodes for every construct |
| **Resolver** | Maps commands to `.wsdict` definitions |
| **Dispatcher** | Routes resolved actions to the correct backend |
| **Backends** | CDP (Chrome/Electron), COM (Office), UIA (Win32) — pluggable |

---

## 🚀 Quickstart

### 1. Install

```bash
git clone https://github.com/winscript/winscript-lang.git
cd winscript-lang
pip install -r requirements.txt
```

### 2. Run a script

```bash
# Start Chrome with debugging enabled
chrome.exe --remote-debugging-port=9222

# Execute WinScript
python -c "
from winscript import WinScriptRuntime
rt = WinScriptRuntime(extra_dict_paths=['./dicts'])
print(rt.execute('''
    tell Chrome
        navigate to \"https://example.com\"
        wait until loaded
        return title of active tab
    end tell
'''))
"
```

### 3. Use with Claude Desktop (MCP)

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "winscript": {
      "command": "python",
      "args": ["-m", "winscript.mcp_server"],
      "cwd": "/path/to/winscript-lang",
      "env": { "PYTHONPATH": "/path/to/winscript-lang" }
    }
  }
}
```

Then ask Claude:
> *"Use WinScript to navigate Chrome to github.com and return the page title"*

Claude writes the script. WinScript executes it. Zero other tools needed.

---

## 📖 Language Overview

WinScript v1 has **5 core constructs** — intentionally minimal, intentionally powerful:

### `tell` / `end tell` — Target an app

```winscript
tell Chrome
    -- all commands here go to Chrome
end tell
```

### `set` — Assign variables

```winscript
set greeting to "Hello"
set url to "https://github.com"
set pageTitle to title of active tab
```

### `return` — Produce a result

```winscript
return title of active tab
return greeting & " from " & url
```

### `wait` — Pause or poll

```winscript
wait until loaded
wait 2 seconds
wait 500 milliseconds
```

### `try` / `catch` / `end try` — Handle errors

```winscript
try
    click element "#submit-button"
catch err
    return "Button not found: " & err
end try
```

### `if` / `then` / `end if` — Branch

```winscript
if title contains "GitHub" then
    return "Found it!"
end if
```

### Operators

| Operator | Example |
|----------|---------|
| `is` | `if x is 10 then` |
| `contains` | `if title contains "GitHub" then` |
| `is greater than` | `if count is greater than 5 then` |
| `is less than` | `if count is less than 100 then` |
| `&` | `greeting & " " & name` |

---

## 🏛️ Architecture

```
winscript-lang/
├── spec/
│   ├── language-v1.md          ← Language specification
│   └── wsdict-v1.md            ← Dictionary format specification
├── winscript/
│   ├── grammar.lark            ← Lark PEG grammar
│   ├── parser.py               ← Grammar → AST transformer
│   ├── ast_nodes.py            ← Dataclass AST nodes
│   ├── context.py              ← Execution state (variables, scopes)
│   ├── errors.py               ← Error hierarchy
│   ├── resolver.py             ← AST → .wsdict lookup → ResolvedAction
│   ├── dispatcher.py           ← ResolvedAction → backend call
│   ├── runtime.py              ← Main orchestrator (walks AST)
│   ├── mcp_server.py           ← MCP tool interface (5 tools)
│   ├── backends/
│   │   ├── base.py             ← Abstract base class
│   │   ├── cdp.py              ← Chrome DevTools Protocol ✅
│   │   ├── com.py              ← COM/pywin32 (stub)
│   │   └── uia.py              ← UI Automation (stub)
│   └── dicts/
│       ├── loader.py           ← .wsdict discovery + YAML parsing
│       └── validator.py        ← Schema validation
├── dicts/
│   └── chrome.wsdict           ← Reference dictionary (ships with core)
├── tests/                      ← 130 tests across 10 test files
├── requirements.txt
└── LICENSE                     ← MIT
```

---

## 🔌 MCP Integration

WinScript exposes **5 MCP tools** for AI agent integration:

| Tool | Description |
|------|-------------|
| `run_winscript(code)` | Execute WinScript source code |
| `run_winscript_file(path)` | Execute a `.ws` file from disk |
| `list_available_apps()` | List all discoverable `.wsdict` files |
| `get_app_commands(app_name)` | Show commands/properties for an app |
| `validate_script(code)` | Parse-check without executing |

### How it works with Claude

```
User: "Navigate Chrome to GitHub and return the title"
  ↓
Claude writes a WinScript script
  ↓
Calls run_winscript() MCP tool
  ↓
WinScript runtime executes against Chrome via CDP
  ↓
Returns: "GitHub: Let's build from here · GitHub"
```

---

## 📝 Write Your Own Dictionary

The `.wsdict` format is **open and community-driven**. Anyone can add support for any app — no runtime changes needed.

### Minimal example: `notepad.wsdict`

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
```

Drop it in `dicts/` and instantly:

```winscript
tell Notepad
    type "Hello from WinScript!"
end tell
```

### Community dictionary roadmap

| Dictionary | Backend | Status |
|-----------|---------|--------|
| `chrome.wsdict` | CDP | ✅ Ships with v1 |
| `excel.wsdict` | COM | 🔜 Community |
| `word.wsdict` | COM | 🔜 Community |
| `outlook.wsdict` | COM | 🔜 Community |
| `vscode.wsdict` | CDP | 🔜 Community (Electron!) |
| `slack.wsdict` | CDP | 🔜 Community (Electron!) |
| `discord.wsdict` | CDP | 🔜 Community (Electron!) |
| `spotify.wsdict` | CDP | 🔜 Community (Electron!) |
| `notepad.wsdict` | UIA | 🔜 Community |
| `terminal.wsdict` | UIA | 🔜 Community |

> 💡 **Any Electron app** (VS Code, Slack, Discord, Figma, Notion) works with the CDP backend — same as Chrome. That's ~30% of apps people care about on Windows.

---

## 🧪 Testing

```bash
# Run full test suite (130 tests)
pytest tests/ -v

# Run with Chrome integration tests
chrome.exe --remote-debugging-port=9222
pytest tests/ -v  # Chrome tests run automatically when Chrome is available
```

### Test coverage

| Module | Tests | Status |
|--------|-------|--------|
| Parser & AST | 10 | ✅ |
| Context & Errors | 8 | ✅ |
| Dictionary Loader | 12 | ✅ |
| Dictionary Validator | 15 | ✅ |
| Chrome Dict | 16 | ✅ |
| CDP Backend | 20 | ✅ |
| Resolver | 19 | ✅ |
| Dispatcher | 9 | ✅ |
| Runtime | 21 | ✅ |
| End-to-End | 20 | ✅ (2 skipped w/o Chrome) |

---

## 🗺️ Roadmap

### v1.0 — MVP ✅
- [x] Lark grammar with 5 constructs
- [x] AST nodes + transformer
- [x] Execution context + error hierarchy
- [x] Dictionary loader + validator
- [x] Chrome reference dictionary
- [x] CDP backend with smart methods
- [x] Resolver (AST → dictionary lookup)
- [x] Dispatcher (resolved actions → backends)
- [x] Runtime orchestrator
- [x] MCP server (5 tools)
- [x] 130 tests passing

### v1.1 — Community backends
- [ ] COM backend (Excel, Word, Outlook)
- [ ] UIA backend (Notepad, Calculator, Explorer)
- [ ] Community `.wsdict` contributions

### v2.0 — Language expansion
- [ ] `repeat` loops
- [ ] `else` / `else if`
- [ ] User-defined functions
- [ ] List/array support
- [ ] Multi-tab targeting

---

## 📄 Specifications

| Document | Description |
|----------|-------------|
| [`spec/language-v1.md`](spec/language-v1.md) | WinScript language specification |
| [`spec/wsdict-v1.md`](spec/wsdict-v1.md) | Dictionary format specification |
| [`dicts/chrome.wsdict`](dicts/chrome.wsdict) | Reference dictionary implementation |

---

## 🤝 Contributing

WinScript is **MIT licensed** and designed to be community-extended.

The fastest way to contribute:
1. **Write a `.wsdict`** for an app you use daily
2. **Test it** against the runtime
3. **Submit a PR** — no runtime changes needed

See [`spec/wsdict-v1.md`](spec/wsdict-v1.md) for the format reference and [`dicts/chrome.wsdict`](dicts/chrome.wsdict) for the reference implementation.

---

<p align="center">
  <strong>WinScript</strong> — because Windows deserved a scripting language.<br/>
  <sub>Built with 🪟 for the Windows community.</sub>
</p>
