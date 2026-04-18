"""
winscript.resolver — Maps AST nodes to dictionary definitions.

The resolver is the bridge between the parser output (AST nodes) and the
backend execution layer. For every command or property access inside a
tell block, it:

1. Looks up the .wsdict for the target app
2. Finds the matching command/property definition
3. Validates argument types
4. Returns a ResolvedAction with everything the dispatcher needs
"""

from dataclasses import dataclass, field
from typing import Any

from winscript.ast_nodes import (
    BoolLiteral,
    ConcatExpr,
    Condition,
    Identifier,
    NumberLiteral,
    PropertyAccess,
    StringLiteral,
)
from winscript.dicts.loader import AppDict, CommandDef, DictLoader, ObjectDef, PropertyDef
from winscript.errors import (
    WinScriptCommandNotFound,
    WinScriptError,
    WinScriptPropertyNotFound,
    WinScriptTypeError,
)


# ---------------------------------------------------------------------------
# ResolvedAction — everything the dispatcher needs to call a backend
# ---------------------------------------------------------------------------

@dataclass
class ResolvedAction:
    backend_type: str           # "cdp" | "com" | "uia"
    backend_method: str         # the actual method to call on the backend
    backend_expression: str     # for property reads that use expressions
    args: dict                  # resolved argument values
    app_name: str               # which app this targets
    connection_info: dict       # from .wsdict connection section


# ---------------------------------------------------------------------------
# Resolver
# ---------------------------------------------------------------------------

class Resolver:
    """
    Resolves AST nodes to backend-ready ResolvedAction objects by looking
    up command and property definitions in loaded .wsdict files.
    """

    def __init__(self, dict_loader: DictLoader):
        self.dict_loader = dict_loader

    # ------------------------------------------------------------------
    # Tell block resolution
    # ------------------------------------------------------------------

    def resolve_tell(self, app_name: str) -> tuple[AppDict, ObjectDef]:
        """
        Load the .wsdict for *app_name* and return its root object.

        Returns:
            (AppDict, root ObjectDef)

        Raises:
            WinScriptDictNotFound — if no .wsdict file exists for app_name
        """
        app_dict = self.dict_loader.load(app_name)
        root = app_dict.root_object()
        return app_dict, root

    # ------------------------------------------------------------------
    # Command resolution
    # ------------------------------------------------------------------

    def resolve_command(
        self,
        app_dict: AppDict,
        current_object: ObjectDef,
        command_name: str,
        kwargs: dict,
        args: list = None,
    ) -> ResolvedAction:
        """
        Look up *command_name* in the current object's command list,
        validate the provided arguments, and return a ResolvedAction.

        The resolver also searches all other objects in the dict if the
        command isn't found on the current object — commands on Tab are
        available from Browser-level tell blocks (active tab routing).

        Raises:
            WinScriptCommandNotFound — command doesn't exist
            WinScriptTypeError       — argument type mismatch
        """
        if args is None:
            args = []
        cmd_def = current_object.find_command(command_name)

        # Fall back: search all objects (e.g. Tab commands from Browser scope)
        if cmd_def is None:
            for obj in app_dict.objects.values():
                if obj.name == current_object.name:
                    continue
                cmd_def = obj.find_command(command_name)
                if cmd_def:
                    break

        if cmd_def is None:
            # Collect all available command names for the error message
            all_commands = set()
            for obj in app_dict.objects.values():
                all_commands.update(obj.command_names())
            raise WinScriptCommandNotFound(
                command_name, app_dict.name, sorted(all_commands)
            )

        # Validate arguments against the command definition
        resolved_args = self._validate_args(cmd_def, kwargs, args)

        return ResolvedAction(
            backend_type=app_dict.backend,
            backend_method=cmd_def.backend_method,
            backend_expression=cmd_def.backend_expression,
            args=resolved_args,
            app_name=app_dict.name,
            connection_info=app_dict.connection,
        )

    # ------------------------------------------------------------------
    # Property resolution
    # ------------------------------------------------------------------

    def resolve_property(
        self,
        app_dict: AppDict,
        current_object: ObjectDef,
        prop_name: str,
    ) -> ResolvedAction:
        """
        Look up *prop_name* in the current object's properties.
        Falls back to searching all objects (e.g. Tab props from Browser scope).

        Raises:
            WinScriptPropertyNotFound — property doesn't exist
        """
        prop_def = current_object.find_property(prop_name)

        # Fall back: search all objects
        if prop_def is None:
            for obj in app_dict.objects.values():
                if obj.name == current_object.name:
                    continue
                prop_def = obj.find_property(prop_name)
                if prop_def:
                    break

        if prop_def is None:
            raise WinScriptPropertyNotFound(
                prop_name, current_object.name, app_dict.name
            )

        return ResolvedAction(
            backend_type=app_dict.backend,
            backend_method=prop_def.backend_method,
            backend_expression=prop_def.backend_expression,
            args={},
            app_name=app_dict.name,
            connection_info=app_dict.connection,
        )

    # ------------------------------------------------------------------
    # Sub-object resolution (nested tell blocks)
    # ------------------------------------------------------------------

    def resolve_sub_object(
        self,
        app_dict: AppDict,
        current_object: ObjectDef,
        sub_object_name: str,
    ) -> ObjectDef:
        """
        Resolve a nested tell target (e.g. ``tell sheet "Summary"``).
        Looks through the current object's property types and all
        objects in the dict for a matching name.

        Returns:
            The ObjectDef for the sub-object.

        Raises:
            WinScriptError — sub-object not found
        """
        # Check property types on the current object
        for prop in current_object.properties:
            # Type might be "Tab", "Sheet", "list[Tab]", etc.
            base_type = prop.type.split("[")[-1].rstrip("]").strip()
            if base_type.lower() == sub_object_name.lower():
                if base_type in app_dict.objects:
                    return app_dict.objects[base_type]

        # Direct lookup by object name (case-insensitive)
        for obj_name, obj_def in app_dict.objects.items():
            if obj_name.lower() == sub_object_name.lower():
                return obj_def

        raise WinScriptError(
            f"'{sub_object_name}' is not a recognized object in {app_dict.name}.\n"
            f"Available objects: {', '.join(app_dict.objects.keys())}"
        )

    # ------------------------------------------------------------------
    # Expression resolution (AST nodes → Python values)
    # ------------------------------------------------------------------

    def resolve_expression(self, expr: Any, context) -> Any:
        """
        Recursively evaluate an AST expression node to a Python value.

        Handles:
        - StringLiteral → str
        - NumberLiteral → float/int
        - BoolLiteral   → bool
        - Identifier    → variable lookup from context
        - ConcatExpr    → string concatenation with &
        - PropertyAccess → deferred (returns the AST node for the runtime
                          to resolve with backend calls)
        - Condition     → deferred (returned as-is for runtime evaluation)
        """
        if isinstance(expr, StringLiteral):
            return expr.value

        if isinstance(expr, NumberLiteral):
            # Return int when possible for cleaner output
            if expr.value == int(expr.value):
                return int(expr.value)
            return expr.value

        if isinstance(expr, BoolLiteral):
            return expr.value

        if isinstance(expr, Identifier):
            return context.get_var(expr.name)

        if isinstance(expr, ConcatExpr):
            left = self.resolve_expression(expr.left, context)
            right = self.resolve_expression(expr.right, context)
            return str(left) + str(right)

        if isinstance(expr, PropertyAccess):
            # PropertyAccess nodes need backend calls to resolve.
            # Return the AST node so the runtime can handle it.
            return expr

        if isinstance(expr, Condition):
            return expr

        # Fallback: return as-is (shouldn't happen with well-formed AST)
        return expr

    # ------------------------------------------------------------------
    # Argument validation
    # ------------------------------------------------------------------

    def _validate_args(self, cmd_def: CommandDef, provided: dict, pos_args: list = None) -> dict:
        """
        Check provided args against the command's arg definitions.
        Returns a clean dict of validated argument values.
        """
        if pos_args is None:
            pos_args = []
        resolved: dict = {}

        for i, arg_def in enumerate(cmd_def.args):
            arg_name = arg_def.get("name", "")
            arg_type = arg_def.get("type", "any")
            required = arg_def.get("required", False)

            # Find the value: check by exact name, then positional kwargs
            value = provided.get(arg_name)

            if value is None and i < len(pos_args):
                value = pos_args[i]

            # Also check common alias mappings from the grammar transformer:
            # navigate_cmd puts url in kwargs["to"]
            # click_cmd puts selector in kwargs["element"]
            if value is None:
                alias_map = {
                    "url": "to",
                    "selector": "element",
                    "text": None,         # text is in args[0]
                    "code": None,
                    "target": None,
                    "attr": None,
                    "value": None,
                    "expression": None,
                    "key": None,
                }
                alias = alias_map.get(arg_name)
                if alias and alias in provided:
                    value = provided[alias]

            if value is None and required:
                raise WinScriptError(
                    f"Required argument '{arg_name}' missing for command '{cmd_def.name}'",
                    command=cmd_def.name,
                )

            if value is not None:
                self._check_type(arg_name, arg_type, value, cmd_def.name)
                resolved[arg_name] = value

        return resolved

    def _check_type(self, arg_name: str, expected: str, value: Any, command: str) -> None:
        """Raise WinScriptTypeError if value doesn't match expected type."""
        # Unwrap AST literal nodes to their Python values for type-checking
        if isinstance(value, StringLiteral):
            value = value.value
        elif isinstance(value, NumberLiteral):
            value = value.value
        elif isinstance(value, BoolLiteral):
            value = value.value

        type_map = {
            "string": str,
            "int": (int, float),
            "float": (int, float),
            "bool": bool,
            "any": object,  # matches everything
        }
        expected_types = type_map.get(expected.lower())
        if expected_types is None:
            return  # Unknown type in dict → skip check (custom types like Tab)

        if not isinstance(value, expected_types):
            got = type(value).__name__
            raise WinScriptTypeError(arg_name, expected, got, command)
