# WinScript Language Specification — v1

## Overview

WinScript is an open scripting language for Windows automation. It uses
natural-language syntax to control applications through their native APIs.

## File Extensions

| Extension | Purpose |
|-----------|---------|
| `.ws`     | WinScript source files |
| `.wsdict` | Application dictionary definitions |

## Constructs (v1)

WinScript v1 has exactly **5 constructs**:

### 1. tell / end tell

Target an application for automation.

```
tell Chrome
    navigate to "https://github.com"
end tell
```

The app name must match a `.wsdict` file. All commands inside the block
are dispatched to that app's backend.

### 2. set

Assign a value to a variable.

```
set url to "https://github.com"
set pageTitle to title of active tab
```

Variables are dynamically typed. Scope is flat within a script.

### 3. return

Stop execution and return a value.

```
return title of active tab
return greeting & " " & name
```

### 4. wait

Wait for a condition or a fixed duration.

```
wait until loaded
wait 2 seconds
wait 500 milliseconds
```

`wait until` polls the condition every 500ms with a default 10-second timeout.

### 5. try / catch / end try

Catch runtime errors without crashing the script.

```
try
    click element "#submit"
catch err
    return "Failed: " & err
end try
```

Only `WinScriptError` and its subclasses are catchable. Syntax errors
are never catchable.

## Control Flow

### if / then / end if

Single-condition branching (no else in v1).

```
if title contains "GitHub" then
    return "Found it"
end if
```

## Expressions

| Type | Syntax | Example |
|------|--------|---------|
| String | `"text"` | `"hello world"` |
| Number | `42`, `3.14` | `set x to 42` |
| Boolean | `true`, `false` | `set done to true` |
| Variable | `name` | `return name` |
| Concatenation | `& ` | `"Hello " & name` |
| Property access | `prop of object` | `title of active tab` |

## Conditions

| Operator | Syntax | Example |
|----------|--------|---------|
| Equality | `is` | `x is 10` |
| Contains | `contains` | `title contains "GitHub"` |
| Greater than | `is greater than` | `count is greater than 5` |
| Less than | `is less than` | `count is less than 100` |
| Page loaded | `loaded` | `wait until loaded` |

## Commands

Commands are defined per-application in `.wsdict` files. Built-in commands
for Chrome include:

```
navigate to "https://example.com"
click element "#button"
type "hello" into element "#input"
press "Enter"
take screenshot
run script "document.title"
open "https://new-tab.com"
quit
```

## Reserved Keywords

```
if, tell, set, return, wait, try, catch, end, true, false,
of, then, is, contains, loaded
```

## Comments

Single-line comments start with `--`:

```
-- This is a comment
set x to 42  -- inline comment
```
