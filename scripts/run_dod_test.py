"""Definition of Done Test Script"""
import sys
sys.path.insert(0, ".")

from winscript.mcp_server import _run_winscript as run_winscript

script = '''
tell Chrome
    navigate to "https://github.com/search?q=winscript&type=repositories"
    wait 4000 milliseconds
    set searchTitle to title of active tab
    return searchTitle
end tell
'''

print("\n--- Running Definiton of Done Test ---\n")
print(f"Script:\n{script}")

result = run_winscript(script)

print(f"\nResult: {result}\n")
