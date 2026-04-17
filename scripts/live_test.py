"""
Live WinScript E2E test — exercises the full pipeline against real Chrome.

Tests:
1. Navigate + return title
2. Set variable + concat + return 
3. Try/catch error handling
4. Property access (url)
5. Full agent scenario: navigate → wait → return title
"""
import sys
sys.path.insert(0, ".")

from winscript.mcp_server import _run_winscript as run_winscript

def divider(label):
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")

# ── Test 1: Navigate to example.com and return title ──────────────
divider("Test 1: Navigate + Return Title")
result = run_winscript('''
tell Chrome
    navigate to "https://example.com"
    wait 2 seconds
    return title of active tab
end tell
''')
print(f"  Result: {result}")
assert "ERROR" not in result, f"FAILED: {result}"
print("  [PASS]")

# ── Test 2: Variable set + concat ─────────────────────────────────
divider("Test 2: Variables + Concatenation")
result = run_winscript('''
set greeting to "Hello"
set target to "WinScript"
return greeting & " from " & target
''')
print(f"  Result: {result}")
assert result == "Hello from WinScript", f"FAILED: {result}"
print("  [PASS]")

# ── Test 3: If condition ──────────────────────────────────────────
divider("Test 3: If Condition")
result = run_winscript('''
set x to 42
if x is 42 then
    return "The answer"
end if
return "Not found"
''')
print(f"  Result: {result}")
assert result == "The answer", f"FAILED: {result}"
print("  [PASS]")

# ── Test 4: Return URL property ───────────────────────────────────
divider("Test 4: Property Access (URL)")
result = run_winscript('''
tell Chrome
    navigate to "https://example.com"
    wait 2 seconds
    return url of active tab
end tell
''')
print(f"  Result: {result}")
assert "example.com" in result, f"FAILED: {result}"
print("  [PASS]")

# ── Test 5: Try/catch with bad selector ───────────────────────────
divider("Test 5: Try/Catch Error Handling")
result = run_winscript('''
try
    tell Chrome
        click element "#nonexistent_xyz_button_that_does_not_exist_at_all"
    end tell
catch err
    return "caught: " & err
end try
''')
print(f"  Result: {result}")
assert result.startswith("caught: "), f"FAILED: {result}"
print("  [PASS]")

# ── Test 6: Full Agent Scenario ───────────────────────────────────
divider("Test 6: Full Agent Scenario — Navigate GitHub + Return Title")
result = run_winscript('''
tell Chrome
    navigate to "https://github.com"
    wait 3 seconds
    return title of active tab
end tell
''')
print(f"  Result: {result}")
assert "GitHub" in result, f"FAILED: {result}"
print("  [PASS]")

# ── Summary ───────────────────────────────────────────────────────
divider("ALL 6 TESTS PASSED")
print("  WinScript v1 is fully operational!\n")
