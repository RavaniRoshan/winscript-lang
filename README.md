<p align="center">
<img src="https://img.shields.io/badge/WinScript-v2.1-blue?style=for-the-badge&logo=windows&logoColor=white" alt="WinScript v2.1"/>
<img src="https://img.shields.io/badge/license-MIT-green?style=for-the-badge" alt="MIT License"/>
<img src="https://img.shields.io/badge/python-3.11+-yellow?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.11+"/>
<img src="https://img.shields.io/badge/tests-197%20passing-brightgreen?style=for-the-badge" alt="197 Tests Passing"/>
</p>

<h1 align="center">🪟 WinScript</h1>

<p align="center">
<strong>The open scripting language for Windows automation.</strong><br/>
AppleScript had 40 years. Windows had nothing.<br/>
Until now.
</p>

<p align="center">
<a href="#-quickstart">Quickstart</a> •
<a href="#-installation">Installation</a> •
<a href="#-chrome-setup">Chrome Setup</a> •
<a href="#-language-reference">Language</a> •
<a href="#-cli-reference">CLI</a> •
<a href="#-troubleshooting">Troubleshooting</a> •
<a href="#-mcp-integration">MCP</a>
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

## 🚀 Quickstart

### 1️⃣ Install WinScript

```bash
# Clone the repository
git clone https://github.com/winscript/winscript-lang.git
cd winscript-lang

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install WinScript
pip install -e .
```

### 2️⃣ Set up Chrome (for web automation)

WinScript uses Chrome DevTools Protocol (CDP) to control Chrome.

**Option A: Automatic setup**
```bash
# Check if Chrome is installed and ready
winscript --check-chrome

# See detailed setup guide
winscript --setup-chrome
```

**Option B: Manual setup**

<details>
<summary><b>Windows</b></summary>

```powershell
# In Command Prompt or PowerShell
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222
```

Chrome variants supported:
- Google Chrome: `C:\Program Files\Google\Chrome\Application\chrome.exe`
- Microsoft Edge: `C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe`
- Brave: `%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe`
- Chromium: `C:\Program Files\Chromium\Application\chrome.exe`

</details>

<details>
<summary><b>macOS</b></summary>

```bash
# In Terminal
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222
```

Chrome variants supported:
- Google Chrome: `/Applications/Google Chrome.app`
- Microsoft Edge: `/Applications/Microsoft Edge.app`
- Brave Browser: `/Applications/Brave Browser.app`

</details>

<details>
<summary><b>Linux</b></summary>

```bash
# One of these should work:
google-chrome --remote-debugging-port=9222
chromium --remote-debugging-port=9222
brave --remote-debugging-port=9222
```

</details>

### 3️⃣ Verify Chrome is connected

```bash
# In another terminal window
winscript --check-chrome
```

You should see:
```
✓ Chrome executable found at: <path>
✓ Chrome DevTools Protocol active (http://localhost:9222)
💡 Chrome is ready for WinScript automation!
```

### 4️⃣ Run your first script

Create a file `hello.ws`:

```winscript
-- hello.ws - Your first WinScript

set message to "Hello from WinScript!"
return message
```

Run it:
```bash
winscript hello.ws
```

Output:
```
"Hello from WinScript!"
```

🎉 **Success!** You've run your first WinScript.

---

## 🛠️ Chrome Setup Guide

### Finding Chrome on Your System

WinScript automatically detects Chrome from common locations:

| Platform | Chrome | Edge | Brave | Chromium |
|----------|--------|------|-------|----------|
| Windows | `%PROGRAMFILES%` | `%PROGRAMFILES(X86)%` | `%LOCALAPPDATA%` | `%PROGRAMFILES%` |
| macOS | `/Applications` | `/Applications` | `/Applications` | `/Applications` |
| Linux | `which google-chrome` | `which microsoft-edge` | `which brave` | `which chromium` |

### Verifying Chrome is Running

**Check if Chrome is accepting connections:**
```bash
# Method 1: Use WinScript
winscript --check-chrome

# Method 2: Open in browser
open http://localhost:9222/json
```

If you see a JSON response, Chrome is ready!

### Common Chrome Path Issues

**Issue: "Chrome not found"**
```
⚠ Chrome not found automatically
```

**Solutions:**
1. **Install Chrome** if not already installed
2. **Use full path**: `winscript --setup-chrome` to see platform-specific paths
3. **Add to PATH**: Ensure Chrome is in your system PATH
4. **Specify alternative**: Use Edge, Brave, or Chromium instead

**Issue: "Port 9222 already in use"**

```bash
# Find and kill process on port 9222

# Windows (PowerShell)
netstat -ano | findstr :9222
taskkill /PID <PID> /F

# macOS/Linux
lsof -ti:9222 | xargs kill -9
```

**Issue: "Connection refused"**

Make sure Chrome was started with the `--remote-debugging-port=9222` flag.

---

## 📖 Language Reference

### Core Constructs

#### `tell` / `end tell` — Target an application

```winscript
tell Chrome
  navigate to "https://github.com"
end tell
```

**Supported Applications:**
- `Chrome` — Chrome/Edge/Brave/Chromium via CDP
- `Excel` — Microsoft Excel via COM

#### `set` — Assign variables

```winscript
set x to "Hello"
set y to 42
set z to x & " World"  -- Concatenation with &
```

#### `return` — Produce a result

```winscript
set result to calculate()
return result
```

#### `declare` — Type declarations

```winscript
declare count as integer
set count to 5

declare names as list
set names to ["Alice", "Bob", "Charlie"]
```

**Available types:** `string`, `integer`, `decimal`, `boolean`, `list`, `dict`, `any`

#### `if` / `then` / `end if` — Conditional branching

```winscript
if title contains "GitHub" then
  return "Found it!"
end if

-- Comparison operators: is, contains, >, <, >=, <=, !=
if count > 10 then
  return "Many"
end if
```

#### `try` / `catch` / `end try` — Error handling

```winscript
try
  click element "#submit"
catch err
  return "Error: " & err
end try
```

#### `repeat` — Loops

```winscript
-- Repeat N times
repeat 5 times
  -- do something
end repeat

-- Repeat while condition
set x to 0
repeat while x < 10
  set x to x + 1
end repeat

-- Repeat with list
repeat with item in ["A", "B", "C"]
  return item
end repeat
```

#### `on` / `end on` — Functions

```winscript
on greet(name)
  return "Hello " & name
end on

set result to greet("World")
return result
```

#### `wait` — Pause execution

```winscript
wait until loaded      -- Wait for page to load
wait 2 seconds         -- Wait 2 seconds
wait 500 milliseconds  -- Wait 500ms
```

#### `using` — Import libraries

```winscript
using "helpers.wslib"

-- Functions from library are now available
set result to helper_function()
```

---

## 💻 CLI Reference

### Basic Commands

| Command | Description |
|---------|-------------|
| `winscript script.ws` | Run a WinScript file |
| `winscript` | Launch interactive REPL |
| `winscript --help` | Show full help |

### Execution Options

| Flag | Description | Example |
|------|-------------|---------|
| `--args, -a` | Pass arguments as `$1`, `$2`... | `--args "hello" 42` |
| `--validate, -c` | Check syntax without running | `--validate script.ws` |
| `--quiet, -q` | Suppress output except return | `--quiet script.ws` |
| `--debug, -d` | Run with debugger | `--debug script.ws` |

### Application Discovery

| Flag | Description | Example |
|------|-------------|---------|
| `--apps` | List available apps | `--apps` |
| `--commands, -C` | Show app commands | `--commands Chrome` |
| `--dict-path` | Add dictionary path | `--dict-path ./custom` |

### Session Management

| Flag | Description | Example |
|------|-------------|---------|
| `--save-session` | Save state after run | `--save-session my-session` |
| `--load-session` | Load state before run | `--load-session my-session` |
| `--list-sessions, -L` | List saved sessions | `--list-sessions` |
| `--delete-session` | Delete a session | `--delete-session my-session` |

### Conversion & Setup

| Flag | Description | Example |
|------|-------------|---------|
| `--convert` | Convert AppleScript | `--convert script.scpt -o output.ws` |
| `--setup-chrome` | Show Chrome setup | `--setup-chrome` |
| `--check-chrome` | Check Chrome status | `--check-chrome` |

### Examples

```bash
# Run with arguments
winscript script.ws --args "username" "password"

# Validate syntax
winscript --validate script.ws

# List Chrome commands
winscript --commands Chrome

# Convert AppleScript
winscript --convert old_script.scpt -o new_script.ws

# Save session for resuming later
winscript long_script.ws --save-session progress

# Resume from saved session
winscript resume.ws --load-session progress
```

---

## 🖥️ REPL (Interactive Shell)

Launch the REPL:
```bash
winscript
```

### REPL Commands

| Command | Alias | Description |
|---------|-------|-------------|
| `:help` | `:h` | Show help |
| `:quit` | `:q` | Exit REPL |
| `:clear` | `:c` | Clear context |
| `:vars` | `:v` | Show variables |
| `:funcs` | `:f` | Show functions |
| `:apps` | | List apps |
| `:load <file>` | | Load script |
| `:save <name>` | | Save session |
| `:history` | | Show history |

### REPL Features

- **Syntax highlighting** — Code is colorized as you type
- **Multi-line editing** — Automatically detects incomplete blocks
- **Command history** — Navigate with ↑/↓ arrows
- **Auto-completion** — Tab completion for commands
- **Live validation** — Instant feedback on syntax errors

---

## 🔌 MCP Integration

WinScript exposes MCP tools for AI agent integration:

| Tool | Description |
|------|-------------|
| `run_winscript(code)` | Execute WinScript source code |
| `run_winscript_file(path)` | Execute a `.ws` file from disk |
| `list_available_apps()` | List all discoverable `.wsdict` files |
| `get_app_commands(app_name)` | Show commands/properties for an app |
| `validate_script(code)` | Parse-check without executing |

### Claude Desktop Configuration

Add to `claude_desktop_config.json`:

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

---

## 🔧 Troubleshooting

### Common Issues

#### Issue: Script file not found
```
✗ Error: Script not found: myscript.ws
```
**Solution:** Ensure you're in the correct directory or provide the full path.

#### Issue: Chrome not responding
```
✗ Error: Connection refused
```
**Solution:**
1. Check Chrome is running with debugging: `winscript --check-chrome`
2. Restart Chrome with the debugging flag
3. Try a different port: `--remote-debugging-port=9223`

#### Issue: Application not found
```
✗ Dictionary 'MyApp' not found
```
**Solution:**
1. Check available apps: `winscript --apps`
2. Ensure `.wsdict` file exists in `dicts/` directory
3. Use correct app name (case-insensitive)

#### Issue: Command outside tell block
```
✗ Runtime Error: Command 'navigate' outside tell block
```
**Solution:** Wrap commands in a tell block:
```winscript
tell Chrome
  navigate to "https://example.com"
end tell
```

#### Issue: Permission denied
```
✗ Error: Permission denied
```
**Solution:**
- Windows: Run as Administrator if needed
- macOS: Grant accessibility permissions in System Preferences
- Linux: Check file permissions with `ls -la`

### Debug Mode

Enable debug mode for detailed execution tracing:
```bash
winscript script.ws --debug
```

Debugger commands:
- `c` / `continue` — Resume execution
- `s` / `step` — Step to next line
- `n` / `next` — Step over function calls
- `b <line>` — Set breakpoint
- `p <var>` — Print variable value
- `q` — Quit debugger

### Getting Help

```bash
# Show CLI help
winscript --help

# Show Chrome setup guide
winscript --setup-chrome

# Check system status
winscript --check-chrome
winscript --apps
winscript --list-sessions
```

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_session.py -v

# Run with coverage
pytest tests/ --cov=winscript --cov-report=html
```

---

## 📝 Advanced Features

### Session Persistence

Save execution state and resume later:

```winscript
-- fetch_data.ws
set page to 1
set allData to []

tell Chrome
  repeat 10 times
    navigate to "https://api.example.com/data?page=" & page
    wait until loaded
    set data to content
    set allData to allData & [data]
    set page to page + 1
    
    -- Save progress every iteration
    if page mod 5 is 0 then
      save session "data-collection"
    end if
  end repeat
end tell

return allData
```

Resume later:
```bash
winscript fetch_data.ws --load-session data-collection
```

### Async Operations

Execute tell blocks asynchronously:

```winscript
-- Parallel operations
async tell Chrome
  navigate to "https://site1.com"
end tell

async tell Chrome
  navigate to "https://site2.com"
end tell

await  -- Wait for both to complete
```

### AppleScript Conversion

Convert existing AppleScripts:

```bash
winscript --convert my_mac_script.scpt -o my_windows_script.ws
```

Supports conversion of:
- Tell blocks → WinScript tell blocks
- Set statements → WinScript set
- If/then → WinScript if/then
- Repeat loops → WinScript repeat
- Common application mappings (Safari→Chrome, etc.)

---

## 🤝 Contributing

WinScript is **MIT licensed** and designed for community extension.

### Contributing a Dictionary

1. Create a `.wsdict` file in `dicts/`
2. Follow the spec in `spec/wsdict-v1.md`
3. Test against the runtime
4. Submit a PR

### Reporting Issues

1. Run diagnostics: `winscript --check-chrome`
2. Test your script: `winscript --validate script.ws`
3. Include error output and system info

---

## 📄 License

MIT License — See [LICENSE](LICENSE) for details.

---

<p align="center">
<strong>WinScript</strong> — because Windows deserved a scripting language.<br/>
<sub>Built with 🪟 for the Windows community.</sub>
</p>
