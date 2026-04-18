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

    args = parser.parse_args()

    from winscript.runtime import WinScriptRuntime
    from winscript import __version__

    if args.version:
        print(f"WinScript {__version__}")
        sys.exit(0)

    runtime = WinScriptRuntime(extra_dict_paths=args.dict_path)

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
