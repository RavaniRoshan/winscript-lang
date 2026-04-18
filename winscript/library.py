from pathlib import Path
import os
from winscript.parser import parse
from winscript.ast_nodes import FunctionDef, UsingStatement, Script
from winscript.errors import WinScriptError

LIBRARY_PATHS = [
    Path(os.environ.get("APPDATA", "")) / "WinScript" / "libs",
    Path.cwd() / "libs",
]

class LibraryLoader:
    def __init__(self, extra_paths: list[str] = None, script_dir: Path = None):
        self._cache: dict[str, list[FunctionDef]] = {}
        self._extra_paths = [Path(p) for p in (extra_paths or [])]
        self._script_dir = script_dir

    def search_paths(self) -> list[Path]:
        paths = list(LIBRARY_PATHS)
        if self._script_dir:
            paths.insert(0, self._script_dir)
        paths.extend(self._extra_paths)
        return paths

    def load(self, lib_path: str) -> list[FunctionDef]:
        """
        Load a .wslib file. Return list of FunctionDef nodes.
        Cache by resolved path — same file loaded once.
        Raises WinScriptError if:
        - File not found
        - File contains non-FunctionDef statements
        """
        resolved = self._resolve_path(lib_path)
        if not resolved:
            searched = [str(p / lib_path) for p in self.search_paths()]
            raise WinScriptError(
                f"Library not found: '{lib_path}'\n"
                f"Searched:\n" + "\n".join(f"  {p}" for p in searched)
            )

        cache_key = str(resolved)
        if cache_key in self._cache:
            return self._cache[cache_key]

        source = resolved.read_text(encoding="utf-8")
        ast = parse(source)

        # Validate: only FunctionDef allowed at top level
        non_functions = [
            type(s).__name__ for s in ast.statements
            if not isinstance(s, FunctionDef)
        ]
        if non_functions:
            raise WinScriptError(
                f"Library '{lib_path}' contains non-function statements: "
                f"{non_functions}. Libraries may only contain 'on...end on' definitions."
            )

        functions = [s for s in ast.statements]
        self._cache[cache_key] = functions
        return functions

    def _resolve_path(self, lib_path: str) -> Path | None:
        # Absolute or explicit relative path
        p = Path(lib_path)
        if p.is_absolute() or lib_path.startswith("./") or lib_path.startswith("../"):
            if p.exists(): return p
            # Try adding .wslib extension
            with_ext = p.with_suffix(".wslib")
            if with_ext.exists(): return with_ext
            return None

        # Search standard paths
        for search_path in self.search_paths():
            candidate = search_path / lib_path
            if candidate.exists(): return candidate
            with_ext = candidate.with_suffix(".wslib")
            if with_ext.exists(): return with_ext

        return None
