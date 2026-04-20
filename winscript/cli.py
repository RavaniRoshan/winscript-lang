"""
winscript.cli — Rich Interactive Command-Line Interface

A beautiful, feature-rich CLI for WinScript with animations,
syntax highlighting, tables, panels, and comprehensive help.
"""

import sys
import argparse
from pathlib import Path
from typing import Optional

from winscript.rich_utils import (
    console, print_banner, print_success, print_error, print_warning,
    print_info, print_dict_table, print_session_table, print_app_commands,
    print_validation_result, print_help_panel, print_chrome_setup_guide,
    print_tip, create_spinner, format_error_with_context, THEME
)
from winscript.utils import (
    find_chrome_executable, is_chrome_running, get_chrome_launch_command,
    get_chrome_setup_help, ChromeNotFoundError
)


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser with Rich formatting."""
    parser = argparse.ArgumentParser(
        prog="winscript",
        description="WinScript — The Windows Automation Language",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s script.ws                    Run a .ws script
  %(prog)s script.ws --args "hello"   Pass arguments to script
  %(prog)s --validate script.ws        Validate without running
  %(prog)s --apps                      List available applications
  %(prog)s --commands Chrome           Show Chrome commands
  %(prog)s --convert script.scpt       Convert AppleScript
  %(prog)s --setup-chrome              Show Chrome setup guide

For more help: %(prog)s --help
        """
    )
    
    # Main arguments
    parser.add_argument(
        "script",
        nargs="?",
        help=".ws script file to run"
    )
    
    # Execution options
    exec_group = parser.add_argument_group("Execution Options")
    exec_group.add_argument(
        "--args", "-a",
        nargs="*",
        metavar="ARG",
        help="Arguments passed as $1, $2, ..."
    )
    exec_group.add_argument(
        "--validate", "-c",
        action="store_true",
        help="Parse and validate without executing"
    )
    exec_group.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress output except return value"
    )
    exec_group.add_argument(
        "--debug", "-d",
        action="store_true",
        help="Run with interactive debugger"
    )
    
    # Application discovery
    app_group = parser.add_argument_group("Application Discovery")
    app_group.add_argument(
        "--apps",
        action="store_true",
        help="List all available app dictionaries"
    )
    app_group.add_argument(
        "--commands", "-C",
        metavar="APP",
        help="List all commands for an app"
    )
    app_group.add_argument(
        "--dict-path",
        metavar="PATH",
        action="append",
        help="Add a dictionary search path"
    )
    
    # Session management
    session_group = parser.add_argument_group("Session Management")
    session_group.add_argument(
        "--save-session",
        metavar="NAME",
        help="Save execution state after running"
    )
    session_group.add_argument(
        "--load-session",
        metavar="NAME",
        help="Load execution state before running"
    )
    session_group.add_argument(
        "--list-sessions", "-L",
        action="store_true",
        help="List all saved sessions"
    )
    session_group.add_argument(
        "--delete-session",
        metavar="NAME",
        help="Delete a saved session"
    )
    
    # Conversion
    conv_group = parser.add_argument_group("Conversion Tools")
    conv_group.add_argument(
        "--convert",
        metavar="FILE",
        help="Convert AppleScript to WinScript"
    )
    conv_group.add_argument(
        "--output", "-o",
        metavar="FILE",
        help="Output file for conversion"
    )
    
    # Chrome setup
    chrome_group = parser.add_argument_group("Chrome Setup")
    chrome_group.add_argument(
        "--setup-chrome",
        action="store_true",
        help="Show Chrome setup guide"
    )
    chrome_group.add_argument(
        "--check-chrome",
        action="store_true",
        help="Check if Chrome is available and running"
    )
    
    # Analysis
    analysis_group = parser.add_argument_group("Analysis")
    analysis_group.add_argument(
        "--analyze-types",
        action="store_true",
        help="Analyze script and show type information"
    )
    
    # Info
    parser.add_argument(
        "--version", "-v",
        action="store_true",
        help="Print WinScript version"
    )
    
    return parser


def handle_list_sessions(runtime) -> int:
    """Handle --list-sessions command."""
    sessions = runtime.session_manager.list_sessions()
    print_session_table(sessions)
    return 0


def handle_delete_session(runtime, session_name: str) -> int:
    """Handle --delete-session command."""
    with create_spinner(f"Deleting session '{session_name}'..."):
        if runtime.session_manager.delete_session(session_name):
            print_success(f"Session '{session_name}' deleted")
            return 0
        else:
            print_error(f"Session '{session_name}' not found")
            return 1


def handle_conversion(input_path: Path, output_path: Optional[Path]) -> int:
    """Handle --convert command."""
    from winscript.applescript_converter import convert_file
    
    if not input_path.exists():
        print_error(f"File not found: {input_path}")
        return 1
    
    with create_spinner(f"Converting {input_path.name}..."):
        try:
            converted = convert_file(input_path, output_path)
            
            if output_path:
                print_success(
                    f"Converted {input_path.name} → {output_path.name}",
                    f"Output saved to: {output_path.absolute()}"
                )
            else:
                console.print()
                console.print(converted)
            
            return 0
        except Exception as e:
            print_error(f"Conversion failed", details=str(e))
            return 1


def handle_apps(runtime) -> int:
    """Handle --apps command."""
    with create_spinner("Loading dictionaries..."):
        # Get apps data
        apps_data = []
        for app_name in ["Chrome", "Excel"]:
            try:
                from winscript.dicts.loader import DictLoader
                loader = DictLoader()
                app_dict = loader.load(app_name)
                apps_data.append({
                    "name": app_name,
                    "backend": app_dict.backend,
                    "description": app_dict.description,
                    "path": str(Path(f"dicts/{app_name.lower()}.wsdict").absolute())
                })
            except Exception:
                pass
        
        if apps_data:
            print_dict_table(apps_data)
        else:
            print_warning("No dictionaries found", "Check your dicts/ directory")
        
        return 0


def handle_commands(runtime, app_name: str) -> int:
    """Handle --commands command."""
    with create_spinner(f"Loading commands for {app_name}..."):
        try:
            output = runtime.get_app_commands(app_name)
            # Parse and display with Rich
            lines = output.split('\n')
            app_info = {
                "name": lines[0].split('(')[0].strip() if lines else app_name,
                "backend": "unknown",
                "description": lines[1].strip() if len(lines) > 1 else "",
            }
            print_app_commands(app_info)
            console.print()
            console.print(output)
            return 0
        except Exception as e:
            print_error(f"Failed to load commands for '{app_name}'", details=str(e))
            return 1


def handle_validate(runtime, script_path: Path) -> int:
    """Handle --validate command."""
    with create_spinner(f"Validating {script_path.name}..."):
        try:
            runtime.parse(script_path.read_text(encoding="utf-8"))
            print_validation_result(str(script_path), True)
            return 0
        except Exception as e:
            print_validation_result(str(script_path), False, [str(e)])
            return 1


def handle_run(runtime, script_path: Path, args: list, quiet: bool) -> int:
    """Handle script execution."""
    source = script_path.read_text(encoding="utf-8")
    
    # Inject CLI args
    if args:
        injected = "\n".join(
            f'set ${i+1} to "{arg}"'
            for i, arg in enumerate(args)
        )
        source = injected + "\n" + source
    
    with create_spinner(f"Running {script_path.name}..."):
        try:
            result = runtime.execute(source, script_path=str(script_path))
            
            if result is not None and not quiet:
                console.print()
                from winscript.rich_utils import print_result
                print_result(result)
            
            return 0
        except Exception as e:
            console.print()
            format_error_with_context(e)
            return 1


def handle_setup_chrome() -> int:
    """Handle --setup-chrome command."""
    print_chrome_setup_guide()
    
    console.print()
    console.print("[bold]Detected Chrome Installation:[/bold]")
    
    chrome_path = find_chrome_executable()
    if chrome_path:
        print_success(f"Chrome found at: {chrome_path}")
    else:
        print_warning("Chrome not found automatically", "Using common paths...")
    
    console.print()
    console.print("[bold]Chrome Status:[/bold]")
    if is_chrome_running():
        print_success("Chrome is running with debugging enabled (port 9222)")
    else:
        print_warning("Chrome is not running with debugging", 
                     "Start Chrome with --remote-debugging-port=9222")
    
    return 0


def handle_check_chrome() -> int:
    """Handle --check-chrome command."""
    console.print("[bold]🔍 Chrome Diagnostic[/bold]\n")
    
    # Check Chrome installation
    chrome_path = find_chrome_executable()
    if chrome_path:
        print_success("Chrome executable found", str(chrome_path))
    else:
        print_error("Chrome not found", "Install Chrome or add to PATH")
        return 1
    
    # Check debugging port
    if is_chrome_running():
        print_success("Chrome DevTools Protocol active", "http://localhost:9222")
        print_tip("Chrome is ready for WinScript automation!")
    else:
        print_warning(
            "Chrome DevTools Protocol not responding",
            "Port 9222 is not active"
        )
        print_info("Start Chrome with:")
        cmd = get_chrome_launch_command()
        if cmd:
            console.print(f"  [cyan]{' '.join(cmd)}[/cyan]")
    
    return 0


def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Version check (before importing runtime)
    if args.version:
        from winscript import __version__
        console.print(f"[bold cyan]WinScript[/bold cyan] [white]v{__version__}[/white]")
        sys.exit(0)
    
    # Chrome setup guide (before runtime)
    if args.setup_chrome:
        print_banner()
        sys.exit(handle_setup_chrome())
    
    if args.check_chrome:
        sys.exit(handle_check_chrome())
    
    # Help panel
    if not args.script and not any([
        args.apps, args.commands, args.list_sessions, args.delete_session,
        args.convert, args.validate
    ]):
        print_banner()
        print_help_panel()
        sys.exit(0)
    
    # Import runtime
    from winscript.runtime import WinScriptRuntime
    runtime = WinScriptRuntime(extra_dict_paths=args.dict_path)
    
    # Handle commands
    if args.list_sessions:
        sys.exit(handle_list_sessions(runtime))
    
    if args.delete_session:
        sys.exit(handle_delete_session(runtime, args.delete_session))
    
    if args.convert:
        sys.exit(handle_conversion(Path(args.convert), Path(args.output) if args.output else None))
    
    if args.apps:
        sys.exit(handle_apps(runtime))
    
    if args.commands:
        sys.exit(handle_commands(runtime, args.commands))
    
    # No script file provided - launch REPL
    if not args.script:
        print_banner()
        from winscript.repl import launch_repl
        launch_repl(runtime)
        sys.exit(0)
    
    # Script file provided
    script_path = Path(args.script)
    
    if not script_path.exists():
        print_error(f"Script not found: {args.script}")
        sys.exit(1)
    
    if script_path.suffix != ".ws":
        print_warning(
            f"Expected .ws extension",
            f"Got: {script_path.suffix}"
        )
    
    # Validate only
    if args.validate:
        sys.exit(handle_validate(runtime, script_path))
    
    # Execute script
    sys.exit(handle_run(runtime, script_path, args.args or [], args.quiet))


if __name__ == "__main__":
    main()
