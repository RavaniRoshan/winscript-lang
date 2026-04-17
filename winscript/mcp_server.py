"""
winscript.mcp_server — MCP (Model Context Protocol) server for WinScript.

Exposes WinScript as 5 tools that any MCP client (Claude Desktop, etc.)
can call to automate Windows applications.

Usage:
    python -m winscript.mcp_server

Tools:
    run_winscript       — Execute WinScript source code
    run_winscript_file  — Execute a .ws file from disk
    list_available_apps — Show all discoverable .wsdict dictionaries
    get_app_commands    — Show commands/properties for an app
    validate_script     — Parse-check a script without executing
"""

import sys
from pathlib import Path

from fastmcp import FastMCP

from winscript.runtime import WinScriptRuntime
from winscript.dicts.loader import DictLoader

# ---------------------------------------------------------------------------
# Singleton runtime (created once, reused across tool calls)
# ---------------------------------------------------------------------------

_DICTS_DIR = str(Path(__file__).parent.parent / "dicts")
_runtime = WinScriptRuntime(extra_dict_paths=[_DICTS_DIR])


# ---------------------------------------------------------------------------
# Core tool logic — plain functions, testable without MCP
# ---------------------------------------------------------------------------

def _run_winscript(code: str) -> str:
    """Execute WinScript source code and return the result."""
    try:
        result = _runtime.execute(code)
        if result is None:
            return "Script executed successfully (no return value)."
        return str(result)
    except Exception as e:
        return f"ERROR: {type(e).__name__}: {e}"


def _run_winscript_file(path: str) -> str:
    """Execute a WinScript file (.ws) from disk."""
    try:
        file_path = Path(path)
        if not file_path.exists():
            return f"ERROR: File not found: {path}"
        if not file_path.suffix == ".ws":
            return f"ERROR: Expected .ws file, got: {file_path.suffix}"

        source = file_path.read_text(encoding="utf-8")
        script_runtime = WinScriptRuntime(
            extra_dict_paths=[_DICTS_DIR, str(file_path.parent / "dicts")]
        )
        result = script_runtime.execute(source)
        if result is None:
            return "Script executed successfully (no return value)."
        return str(result)
    except Exception as e:
        return f"ERROR: {type(e).__name__}: {e}"


def _list_available_apps() -> str:
    """List all discoverable .wsdict dictionaries."""
    try:
        loader = DictLoader(extra_paths=[_DICTS_DIR])
        apps = loader.list_all()
        if not apps:
            return "No .wsdict files found in any search path."

        lines = ["Available WinScript Applications:", ""]
        for app in apps:
            lines.append(f"  {app['name']} ({app['backend']})")
            if app.get("description"):
                desc = app["description"].strip().split("\n")[0]
                lines.append(f"    {desc}")
            lines.append(f"    Path: {app['path']}")
            lines.append("")
        return "\n".join(lines)
    except Exception as e:
        return f"ERROR: {type(e).__name__}: {e}"


def _get_app_commands(app_name: str) -> str:
    """Show all commands and properties for an app."""
    try:
        loader = DictLoader(extra_paths=[_DICTS_DIR])
        app_dict = loader.load(app_name)

        lines = [
            f"{app_dict.display_name} (backend: {app_dict.backend})",
            f"  {app_dict.description.strip()}",
            "",
        ]

        for obj_name, obj in app_dict.objects.items():
            root_marker = " [ROOT]" if obj.is_root else ""
            lines.append(f"Object: {obj_name}{root_marker}")
            lines.append(f"  {obj.description.strip()}")

            if obj.properties:
                lines.append("  Properties:")
                for prop in obj.properties:
                    lines.append(f"    {prop.name} ({prop.type}) — {prop.description}")

            if obj.commands:
                lines.append("  Commands:")
                for cmd in obj.commands:
                    lines.append(f"    {cmd.syntax}")
                    if cmd.description:
                        desc = cmd.description.strip().split("\n")[0]
                        lines.append(f"      {desc}")
            lines.append("")

        return "\n".join(lines)
    except Exception as e:
        return f"ERROR: {type(e).__name__}: {e}"


def _validate_script(code: str) -> str:
    """Parse-check a script without executing."""
    try:
        errors = _runtime.validate(code)
        if not errors:
            return "VALID"
        return "INVALID: " + "; ".join(errors)
    except Exception as e:
        return f"INVALID: {type(e).__name__}: {e}"


# ---------------------------------------------------------------------------
# MCP Server  — thin wrappers register the logic as MCP tools
# ---------------------------------------------------------------------------

mcp = FastMCP(
    name="WinScript",
    instructions=(
        "WinScript is a scripting language for automating Windows applications. "
        "Use the run_winscript tool to execute WinScript code that controls "
        "Chrome, Excel, Notepad, and other apps. Scripts use a natural-language "
        "syntax with 'tell AppName ... end tell' blocks."
    ),
    version="1.0.0",
)


@mcp.tool()
def run_winscript(code: str) -> str:
    """
    Execute WinScript source code and return the result.

    The code should use 'tell AppName ... end tell' blocks to target
    applications. Use 'return <expr>' to produce a result.

    Example:
        tell Chrome
            navigate to "https://github.com"
            wait until loaded
            return title of active tab
        end tell

    Returns the script's return value as a string, or an error message.
    """
    return _run_winscript(code)


@mcp.tool()
def run_winscript_file(path: str) -> str:
    """
    Execute a WinScript file (.ws) from disk.

    Args:
        path: Absolute or relative path to a .ws file.

    Returns the script's return value as a string, or an error message.
    """
    return _run_winscript_file(path)


@mcp.tool()
def list_available_apps() -> str:
    """
    List all discoverable WinScript application dictionaries (.wsdict files).

    Returns a formatted list showing each app's name, backend type,
    and description.
    """
    return _list_available_apps()


@mcp.tool()
def get_app_commands(app_name: str) -> str:
    """
    Show all commands and properties available for a given application.

    Args:
        app_name: The app name (e.g. "Chrome", "Excel").

    Returns a formatted reference of all objects, commands, and properties
    defined in the app's .wsdict file.
    """
    return _get_app_commands(app_name)


@mcp.tool()
def validate_script(code: str) -> str:
    """
    Parse-check a WinScript script without executing it.

    Returns "VALID" if the script parses successfully,
    or "INVALID: <error details>" if there are syntax errors.
    """
    return _validate_script(code)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()
