import sys, argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(
        prog="winscript",
        description="WinScript — The scripting language for Windows automation.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  winscript script.ws                    Run a .ws script
  winscript script.ws --args "hello"     Pass arguments to script
  winscript --validate script.ws         Validate without running
  winscript --apps                       List installed app dictionaries
  winscript --commands Chrome            List Chrome commands
  winscript --version                    Show version
"""
    )

    parser.add_argument("script", nargs="?", help=".ws script file to run")
    parser.add_argument("--args", nargs="*", metavar="ARG",
                        help="Arguments passed to the script as $1, $2, ...")
    parser.add_argument("--validate", action="store_true",
                        help="Parse and validate without executing")
    parser.add_argument("--apps", action="store_true",
                        help="List all available app dictionaries")
    parser.add_argument("--commands", metavar="APP",
                        help="List all commands for an app")
    parser.add_argument("--dict-path", metavar="PATH", action="append",
                        help="Add a dictionary search path")
    parser.add_argument("--version", action="store_true",
                        help="Print WinScript version")
    parser.add_argument("--quiet", action="store_true",
                        help="Suppress output except return value")
    parser.add_argument("--save-session", metavar="NAME",
                        help="Save execution state to session after running")
    parser.add_argument("--load-session", metavar="NAME",
                        help="Load execution state from session before running")
    parser.add_argument("--list-sessions", action="store_true",
                        help="List all saved sessions")
    parser.add_argument("--delete-session", metavar="NAME",
                        help="Delete a saved session")
    parser.add_argument("--debug", action="store_true",
                        help="Run with interactive debugger")
    parser.add_argument("--convert", metavar="FILE",
                        help="Convert AppleScript to WinScript")
    parser.add_argument("--output", "-o", metavar="FILE",
                        help="Output file for conversion")
    parser.add_argument("--analyze-types", action="store_true",
                        help="Analyze script and show type information")

    args = parser.parse_args()

    from winscript.runtime import WinScriptRuntime
    from winscript import __version__

    if args.version:
        print(f"WinScript {__version__}")
        sys.exit(0)

    runtime = WinScriptRuntime(extra_dict_paths=args.dict_path)

    # Session management commands
    if args.list_sessions:
        sessions = runtime.session_manager.list_sessions()
        if not sessions:
            print("No saved sessions found.")
        else:
            print("Saved Sessions:")
            print("-" * 60)
            for s in sessions:
                print(f"  {s['name']}")
                print(f"    Created: {s.get('created_at', 'Unknown')}")
                print(f"    Variables: {s.get('variable_count', 0)}, Functions: {s.get('function_count', 0)}")
        sys.exit(0)

    if args.delete_session:
        if runtime.session_manager.delete_session(args.delete_session):
            print(f"Session '{args.delete_session}' deleted.")
        else:
            print(f"Session '{args.delete_session}' not found.", file=sys.stderr)
            sys.exit(1)
        sys.exit(0)

    # AppleScript conversion
    if args.convert:
        from winscript.applescript_converter import convert_file
        try:
            input_path = Path(args.convert)
            if not input_path.exists():
                print(f"Error: File not found: {input_path}", file=sys.stderr)
                sys.exit(1)
            
            converted = convert_file(input_path, args.output)
            
            if args.output:
                print(f"Converted {input_path} → {args.output}")
            else:
                print(converted)
            sys.exit(0)
        except Exception as e:
            print(f"Conversion error: {e}", file=sys.stderr)
            sys.exit(1)

    if args.apps:
        print(runtime.dict_loader.list_all_formatted())
        sys.exit(0)

    if args.commands:
        print(runtime.get_app_commands(args.commands))
        sys.exit(0)

    if not args.script:
        # No script given → launch REPL (deferred to Prompt 8)
        from winscript.repl import launch_repl
        launch_repl(runtime)
        sys.exit(0)

    script_path = Path(args.script)
    if not script_path.exists():
        print(f"Error: Script not found: {args.script}", file=sys.stderr)
        sys.exit(1)
    if script_path.suffix != ".ws":
        print(f"Warning: Expected .ws extension, got {script_path.suffix}", file=sys.stderr)

    source = script_path.read_text(encoding="utf-8")

    if args.validate:
        try:
            runtime.parse(source)
            print(f"✓ {args.script} is valid WinScript")
            sys.exit(0)
        except Exception as e:
            print(f"✗ {args.script}: {e}", file=sys.stderr)
            sys.exit(1)

    # Inject CLI args as $1, $2, ... variables
    # Done by prepending set statements to source
    if args.args:
        injected = "\n".join(
            f'set ${i+1} to "{arg}"'
            for i, arg in enumerate(args.args)
        )
        source = injected + "\n" + source

    try:
        result = runtime.execute(source, script_path=str(script_path))
        if result is not None and not args.quiet:
            print(result)
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
