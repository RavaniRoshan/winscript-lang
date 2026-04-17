"""
winscript/__main__.py — Allow running as `python -m winscript`.

Launches the MCP server.
"""

from winscript.mcp_server import mcp

if __name__ == "__main__":
    mcp.run()
