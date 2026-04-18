from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import os
import yaml

from winscript.errors import WinScriptDictNotFound, WinScriptError


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class CommandDef:
    name: str
    syntax: str
    description: str = ""
    backend_method: str = ""   # cdp_method, com_method, or uia_method
    backend_expression: str = ""
    args: list = field(default_factory=list)


@dataclass
class PropertyDef:
    name: str
    type: str
    description: str = ""
    backend_method: str = ""
    backend_expression: str = ""


@dataclass
class ObjectDef:
    name: str
    description: str
    is_root: bool
    properties: list[PropertyDef]
    commands: list[CommandDef]

    def find_command(self, name: str) -> "CommandDef | None":
        for cmd in self.commands:
            if cmd.name == name:
                return cmd
        return None

    def find_property(self, name: str) -> "PropertyDef | None":
        for prop in self.properties:
            if prop.name == name:
                return prop
        return None

    def command_names(self) -> list[str]:
        return [cmd.name for cmd in self.commands]


@dataclass
class AppDict:
    name: str
    display_name: str
    version: str
    backend: str   # "cdp" | "com" | "uia"
    description: str
    connection: dict
    objects: dict[str, ObjectDef]
    errors: list[dict]

    def root_object(self) -> ObjectDef:
        """The is_root=True object — default context for tell blocks."""
        for obj in self.objects.values():
            if obj.is_root:
                return obj
        raise WinScriptError(f"No root object defined in {self.name} dictionary")


# ---------------------------------------------------------------------------
# DictLoader
# ---------------------------------------------------------------------------

class DictLoader:
    def __init__(self, extra_paths: list[str] = None):
        self._cache: dict[str, AppDict] = {}
        self._extra_paths = [Path(p) for p in (extra_paths or [])]

    def search_paths(self) -> list[Path]:
        """Return all paths to search for .wsdict files, in priority order."""
        paths: list[Path] = []

        # 1-3. Standard WinScript install locations
        for env_var in ["APPDATA", "PROGRAMFILES", "PROGRAMFILES(X86)"]:
            val = os.environ.get(env_var)
            if val:
                paths.append(Path(val) / "WinScript" / "dicts")

        # 4. Relative to CWD
        paths.append(Path.cwd() / "dicts")

        # 5. Caller-supplied extra paths (script directory, etc.)
        paths.extend(self._extra_paths)

        return paths

    def load(self, app_name: str) -> AppDict:
        """
        Load the .wsdict for *app_name*.
        Returns a cached copy on subsequent calls.
        Raises WinScriptDictNotFound if no file is found.
        """
        if app_name in self._cache:
            return self._cache[app_name]

        filename = f"{app_name.lower()}.wsdict"
        searched: list[str] = []

        for search_path in self.search_paths():
            candidate = search_path / filename
            searched.append(str(candidate))
            if candidate.exists():
                raw = yaml.safe_load(candidate.read_text(encoding="utf-8"))
                app_dict = self._parse_dict(raw)
                self._cache[app_name] = app_dict
                return app_dict

        raise WinScriptDictNotFound(app_name, searched)

    def list_all(self) -> list[dict]:
        """Return metadata for every discoverable .wsdict file."""
        seen: set[str] = set()
        results: list[dict] = []

        for search_path in self.search_paths():
            if not search_path.exists():
                continue
            for wsdict_file in search_path.glob("*.wsdict"):
                if wsdict_file.name in seen:
                    continue
                seen.add(wsdict_file.name)
                try:
                    raw = yaml.safe_load(wsdict_file.read_text(encoding="utf-8"))
                    meta = raw.get("meta", {})
                    results.append({
                        "name": meta.get("name", wsdict_file.stem),
                        "display_name": meta.get("display_name", ""),
                        "version": meta.get("version", ""),
                        "backend": meta.get("backend", ""),
                        "description": meta.get("description", ""),
                        "path": str(wsdict_file),
                    })
                except Exception:
                    pass  # Skip malformed files silently

        return results

    def list_all_formatted(self) -> str:
        apps = self.list_all()
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

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _parse_dict(self, data: dict) -> AppDict:
        """Parse raw YAML dict into an AppDict dataclass tree."""
        meta = data.get("meta", {})
        connection = data.get("connection", {})
        objects_raw = data.get("objects", {})
        errors_raw = data.get("errors", [])

        objects: dict[str, ObjectDef] = {}
        for obj_name, obj_data in objects_raw.items():
            objects[obj_name] = self._parse_object(obj_name, obj_data)

        return AppDict(
            name=meta.get("name", ""),
            display_name=meta.get("display_name", meta.get("name", "")),
            version=str(meta.get("version", "")),
            backend=meta.get("backend", ""),
            description=meta.get("description", ""),
            connection=connection,
            objects=objects,
            errors=errors_raw or [],
        )

    def _parse_object(self, name: str, data: dict) -> ObjectDef:
        props = [self._parse_property(p) for p in data.get("properties", [])]
        cmds = [self._parse_command(c) for c in data.get("commands", [])]
        return ObjectDef(
            name=name,
            description=data.get("description", ""),
            is_root=bool(data.get("is_root", False)),
            properties=props,
            commands=cmds,
        )

    def _parse_property(self, data: dict) -> PropertyDef:
        return PropertyDef(
            name=data.get("name", ""),
            type=str(data.get("type", "string")),
            description=data.get("description", ""),
            backend_method=(
                data.get("cdp_method") or
                data.get("com_method") or
                data.get("uia_method") or ""
            ),
            backend_expression=(
                data.get("cdp_expression") or
                data.get("com_expression") or ""
            ),
        )

    def _parse_command(self, data: dict) -> CommandDef:
        return CommandDef(
            name=data.get("name", ""),
            syntax=data.get("syntax", ""),
            description=data.get("description", ""),
            backend_method=(
                data.get("cdp_method") or
                data.get("com_method") or
                data.get("uia_method") or ""
            ),
            backend_expression=(
                data.get("cdp_expression") or ""
            ),
            args=data.get("args") or [],
        )
