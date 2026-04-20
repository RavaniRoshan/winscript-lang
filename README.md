<p align="center">
  <img src="https://img.shields.io/badge/WinScript-v2.0-blue?style=for-the-badge&logo=windows&logoColor=white" alt="WinScript v2.0"/>
  <img src="https://img.shields.io/badge/license-MIT-green?style=for-the-badge" alt="MIT License"/>
  <img src="https://img.shields.io/badge/python-3.11+-yellow?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.11+"/>
  <img src="https://img.shields.io/badge/tests-171%20passing-brightgreen?style=for-the-badge" alt="171 Tests Passing"/>
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
  <a href="#-whats-new-in-v20">What's New in v2.0</a> •
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

## 🚀 What's New in v2.0

WinScript v2.0 brings massive improvements to the language, turning it into a complete, robust automation ecosystem.

### Major Changelog
* **Interactive REPL (`winscript`)**: A stateful, colorful terminal interface for live-coding with multi-line buffering, command history, and environment commands (`:vars`, `:funcs`, `:clear`).
* **Command-Line Interface**: Execute scripts directly from the terminal (`winscript script.ws`), pass arguments (`--args`), validate syntax (`--validate`), and list dictionaries (`--apps`, `--commands`).
* **VSCode Extension & Language Server**: Professional IDE support via an LSP (`pygls`). Features real-time error diagnostics, syntax highlighting (`.tmLanguage.json`), smart autocomplete for apps/commands, and Markdown hover docs.
* **Microsoft Excel COM Integration**: Official v2 reference implementation for interacting with Windows COM. Includes nested context routing (`tell Excel` -> `tell sheet "Summary"`) natively executing `pywin32` methods.
* **Script Library System (`using`)**: Share code and import reusable `.wslib` modules into your scripts.
* **Expanded Language Grammar**:
  * **Functions**: Define and call user-functions (`on ... end on`), fully hoisted.
  * **Loops**: Iterate with `repeat times`, `repeat while`, and `repeat with ... in`.
  * **Variables & Types**: Lexical scope stack (`global` / `local`) and strict runtime typing (`declare x as integer`).
  * **Arithmetic & Lists**: Added math operators (`+`, `-`, `*`, `/`), list literals (`[1, 2, 3]`), and more comparisons.
* **Session Persistence** (`save session`, `load session`): Save and restore execution state across script runs.
* **Interactive Debugger** (`--debug`): Step-through debugging with breakpoints, variable inspection, and watch expressions.
* **Async/Await Support** (`async tell`, `await`): Execute tell blocks asynchronously and wait for completion.
* **Type Analyzer**: Advanced type inference system with flow-sensitive typing and generic support.
* **AppleScript Converter** (`--convert`): Convert AppleScript files to WinScript syntax.

---

## 🏗️ How it works

WinScript uses an **open dictionary format** (`.wsdict`) that maps natural-language commands to backend API calls:

```
your_script.ws  →  grammar.lark  →  AST  →  resolver + chrome.wsdict  →  CDP backend  →  Chrome
```

| Layer | What it does |
|-------|-------------|
| **Grammar** | Lark PEG parser — `tell/end tell`, `set`, `return`, `wait`, `try/catch`, `repeat`, `on` |
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
pip install -e .
```

### 2. Run a script

```bash
# Start Chrome with debugging enabled
chrome.exe --remote-debugging-port=9222

# Execute WinScript via the new CLI
winscript my_script.ws

# Or launch the interactive REPL
winscript
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

WinScript is built on natural, powerful constructs:

### `tell` / `end tell` — Target an app

```winscript
tell Chrome
    -- all commands here go to Chrome
end tell
```

### Variables and Types

```winscript
declare count as integer
set count to 5
set url to "https://github.com"
local message
set message to "Started"
```

### Functions

```winscript
on greet(name)
    return "Hello " & name
end on

set result to greet("World")
```

### Loops

```winscript
repeat 5 times
    -- do something
end repeat

repeat with item in ["A", "B", "C"]
    -- do something
end repeat
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

---

## 🏛️ Architecture

```
winscript-lang/
├── winscript-vscode/           ← VSCode Extension & Language Server (v2)
├── spec/                       ← Language & Dictionary specs
├── winscript/
│   ├── grammar.lark            ← Lark PEG grammar
│   ├── parser.py               ← Grammar → AST transformer
│   ├── ast_nodes.py            ← Dataclass AST nodes
│   ├── context.py              ← Lexical scopes, variables, functions (v2)
│   ├── runtime.py              ← Main orchestrator
│   ├── cli.py                  ← Command-line entry point (v2)
│   ├── repl.py                 ← Interactive shell (v2)
│   ├── library.py              ← Module loader for .wslib (v2)
│   ├── types.py                ← Type system & coercion (v2)
│   ├── mcp_server.py           ← MCP tool interface
│   ├── backends/               ← CDP, COM, UIA backend handlers
│   └── dicts/                  ← Dictionary discovery/loader
├── dicts/
│   ├── chrome.wsdict           ← CDP Dictionary
│   └── excel.wsdict            ← COM Dictionary (v2)
├── libs/                       ← Reusable .wslib modules
├── tests/                      ← 171 robust tests
└── setup.py                    ← Pip installer (v2)
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
| `excel.wsdict` | COM | ✅ Ships with v2 |
| `word.wsdict` | COM | 🔜 Community |
| `outlook.wsdict` | COM | 🔜 Community |
| `vscode.wsdict` | CDP | 🔜 Community (Electron!) |
| `slack.wsdict` | CDP | 🔜 Community (Electron!) |
| `discord.wsdict` | CDP | 🔜 Community (Electron!) |
| `spotify.wsdict` | CDP | 🔜 Community (Electron!) |
| `notepad.wsdict` | UIA | 🔜 Community |
| `terminal.wsdict` | UIA | 🔜 Community |

---

## 🧪 Testing

```bash
# Run full test suite (171 tests)
pytest tests/ -v

# Run with Chrome integration tests
chrome.exe --remote-debugging-port=9222
pytest tests/ -v  # Chrome tests run automatically when Chrome is available
```

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

### v2.0 — Language Expansion & Tooling ✅
- [x] CLI package & Interactive REPL
- [x] VSCode Extension & Language Server (LSP)
- [x] Excel COM backend & nested tell routing
- [x] User-defined functions (`on ... end on`) & module libraries (`.wslib`)
- [x] `repeat` loops & lexical scoping
- [x] Runtime type system & lists/math
- [x] 171 passing tests

### v2.1 — UI Automation & Community
- [ ] UIA backend (Notepad, Calculator, Explorer)
- [ ] Multi-tab targeting & advanced DOM handling
- [ ] Community `.wsdict` contributions

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