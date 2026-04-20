"""
winscript.utils — Utility Functions

Provides helper functions for WinScript including Chrome/Chromium detection,
path resolution, and platform-specific utilities.
"""

import os
import platform
import subprocess
from pathlib import Path
from typing import Optional, List, Tuple


# Chrome/Chromium variant detection
CHROME_VARIANTS = [
    # Windows
    ("google-chrome", "Chrome"),
    ("chrome", "Chrome"),
    ("msedge", "Edge"),
    ("brave", "Brave"),
    ("brave-browser", "Brave"),
    ("chromium", "Chromium"),
    ("vivaldi", "Vivaldi"),
    ("opera", "Opera"),
]


def get_platform() -> str:
    """Get the current platform (Windows, Darwin, Linux)."""
    system = platform.system()
    if system == "Windows":
        return "windows"
    elif system == "Darwin":
        return "macos"
    else:
        return "linux"


def find_chrome_executable() -> Optional[Path]:
    """
    Find the Chrome or Chromium executable on the system.
    
    Returns the path to the first found Chrome variant, or None.
    """
    plat = get_platform()
    
    if plat == "windows":
        return _find_chrome_windows()
    elif plat == "macos":
        return _find_chrome_macos()
    else:
        return _find_chrome_linux()


def _find_chrome_windows() -> Optional[Path]:
    """Find Chrome on Windows."""
    # Common installation paths
    program_files_paths = [
        os.environ.get("PROGRAMFILES", "C:\\Program Files"),
        os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)"),
        os.environ.get("LOCALAPPDATA", ""),
    ]
    
    chrome_paths = [
        "Google\\Chrome\\Application\\chrome.exe",
        "Microsoft\\Edge\\Application\\msedge.exe",
        "BraveSoftware\\Brave-Browser\\Application\\brave.exe",
        "Chromium\\Application\\chrome.exe",
        "Vivaldi\\Application\\vivaldi.exe",
    ]
    
    for base in program_files_paths:
        if not base:
            continue
        for chrome_path in chrome_paths:
            full_path = Path(base) / chrome_path
            if full_path.exists():
                return full_path
    
    # Try registry (if available)
    try:
        import winreg
        reg_paths = [
            (r"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths\\chrome.exe", winreg.HKEY_LOCAL_MACHINE),
            (r"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths\\msedge.exe", winreg.HKEY_LOCAL_MACHINE),
        ]
        
        for path, hive in reg_paths:
            try:
                with winreg.OpenKey(hive, path) as key:
                    exe_path, _ = winreg.QueryValueEx(key, None)
                    if exe_path and Path(exe_path).exists():
                        return Path(exe_path)
            except FileNotFoundError:
                continue
    except ImportError:
        pass
    
    return None


def _find_chrome_macos() -> Optional[Path]:
    """Find Chrome on macOS."""
    app_paths = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/Applications/Vivaldi.app/Contents/MacOS/Vivaldi",
        # User Applications folder
        Path.home() / "Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        Path.home() / "Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    ]
    
    for path in app_paths:
        if Path(path).exists():
            return Path(path)
    
    # Try which command
    for cmd in ["google-chrome", "chrome", "chromium", "brave"]:
        result = shutil_which(cmd)
        if result:
            return Path(result)
    
    return None


def _find_chrome_linux() -> Optional[Path]:
    """Find Chrome on Linux."""
    # Try common command names
    commands = [
        "google-chrome",
        "google-chrome-stable",
        "google-chrome-beta",
        "google-chrome-unstable",
        "chromium",
        "chromium-browser",
        "brave",
        "brave-browser",
        "microsoft-edge",
        "microsoft-edge-stable",
        "vivaldi",
    ]
    
    for cmd in commands:
        result = shutil_which(cmd)
        if result:
            return Path(result)
    
    return None


def shutil_which(cmd: str) -> Optional[str]:
    """Cross-platform which command."""
    try:
        import shutil
        return shutil.which(cmd)
    except (ImportError, AttributeError):
        # Fallback for older Python
        try:
            result = subprocess.run(
                ["which", cmd],
                capture_output=True,
                text=True,
                check=False
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except (FileNotFoundError, subprocess.SubprocessError):
            pass
    return None


def get_chrome_launch_command(port: int = 9222, user_data_dir: Optional[str] = None) -> List[str]:
    """
    Get the command to launch Chrome with remote debugging enabled.
    
    Args:
        port: The debugging port (default: 9222)
        user_data_dir: Optional separate user data directory
    
    Returns:
        List of command arguments
    """
    chrome_path = find_chrome_executable()
    
    if not chrome_path:
        return []
    
    cmd = [str(chrome_path)]
    
    # Remote debugging flag
    cmd.append(f"--remote-debugging-port={port}")
    
    # Optional: Use separate user data to avoid conflicts
    if user_data_dir:
        cmd.append(f"--user-data-dir={user_data_dir}")
    
    return cmd


def is_chrome_running(port: int = 9222) -> bool:
    """
    Check if Chrome is running with remote debugging on the given port.
    
    Args:
        port: The port to check (default: 9222)
    
    Returns:
        True if Chrome is responding on the port
    """
    import urllib.request
    import urllib.error
    
    try:
        response = urllib.request.urlopen(
            f"http://localhost:{port}/json",
            timeout=2
        )
        return response.status == 200
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
        return False


def get_chrome_setup_help() -> str:
    """Get platform-specific Chrome setup instructions."""
    plat = get_platform()
    chrome_path = find_chrome_executable()
    
    if plat == "windows":
        chrome_cmd = str(chrome_path) if chrome_path else r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        return f"""
Windows Chrome Setup:

  1. Open Command Prompt or PowerShell as Administrator
  2. Run:
     
     "{chrome_cmd}" --remote-debugging-port=9222

  3. Chrome will start with debugging enabled

Alternative paths to try:
  - C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe
  - %LOCALAPPDATA%\\Programs\\Google\\Chrome\\Application\\chrome.exe
        """
    
    elif plat == "macos":
        chrome_cmd = str(chrome_path) if chrome_path else "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        return f"""
macOS Chrome Setup:

  1. Open Terminal
  2. Run:
     
     "{chrome_cmd}" --remote-debugging-port=9222

  3. Chrome will start with debugging enabled

Alternative paths:
  - /Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge
  - /Applications/Brave Browser.app/Contents/MacOS/Brave Browser
        """
    
    else:
        chrome_cmd = str(chrome_path) if chrome_path else "google-chrome"
        return f"""
Linux Chrome Setup:

  1. Open Terminal
  2. Run:
     
     {chrome_cmd} --remote-debugging-port=9222

  3. Chrome will start with debugging enabled

Alternative commands to try:
  - chromium --remote-debugging-port=9222
  - chromium-browser --remote-debugging-port=9222
  - brave --remote-debugging-port=9222
        """


def find_available_port(start: int = 9222, end: int = 9232) -> Optional[int]:
    """
    Find an available port in the given range.
    
    Returns the first available port, or None if none found.
    """
    import socket
    
    for port in range(start, end + 1):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            
            if result != 0:  # Port is available
                return port
        except Exception:
            continue
    
    return None


def get_wsl_path(windows_path: str) -> str:
    """
    Convert a Windows path to WSL path format if running in WSL.
    
    Args:
        windows_path: Windows-style path
    
    Returns:
        WSL path or original path
    """
    if "WSL_DISTRO_NAME" in os.environ or "WSLENV" in os.environ:
        # Running in WSL
        if windows_path.startswith("C:"):
            return "/mnt/c" + windows_path[2:].replace("\\", "/")
        elif windows_path.startswith("D:"):
            return "/mnt/d" + windows_path[2:].replace("\\", "/")
    return windows_path


def ensure_dir(path: Path) -> Path:
    """Ensure directory exists, creating it if necessary."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def truncate_string(s: str, max_length: int, suffix: str = "...") -> str:
    """Truncate a string to max_length, adding suffix if truncated."""
    if len(s) <= max_length:
        return s
    return s[:max_length - len(suffix)] + suffix


def format_bytes(size: int) -> str:
    """Format byte size to human readable string."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


class ChromeNotFoundError(Exception):
    """Raised when Chrome/Chromium cannot be found on the system."""
    pass


class ChromeConnectionError(Exception):
    """Raised when cannot connect to Chrome debugging port."""
    pass
