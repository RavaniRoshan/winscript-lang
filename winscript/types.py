from enum import Enum
from typing import Any
from winscript.errors import WinScriptTypeError

class WSType(Enum):
    STRING  = "string"
    INTEGER = "integer"
    DECIMAL = "decimal"
    BOOLEAN = "boolean"
    LIST    = "list"
    DICT    = "dict"
    ANY     = "any"

PYTHON_TO_WS = {
    str:   WSType.STRING,
    int:   WSType.INTEGER,
    float: WSType.DECIMAL,
    bool:  WSType.BOOLEAN,
    list:  WSType.LIST,
    dict:  WSType.DICT,
}

def infer_type(value: Any) -> WSType:
    """Infer WSType from a Python value."""
    return PYTHON_TO_WS.get(type(value), WSType.ANY)

def coerce(value: Any, target_type: WSType) -> Any:
    """
    Attempt safe coercion. Returns coerced value or raises WinScriptTypeError.

    Safe coercions:
    - integer <-> decimal (int(3.0) = 3, float(3) = 3.0)
    - any -> string (via str()) ONLY if target is string
    - integer string -> integer ("42" -> 42) ONLY if value is a digit string

    Unsafe (always error):
    - string -> boolean
    - list -> any scalar
    - arbitrary string -> integer (non-digit string)
    """
    actual = infer_type(value)
    if actual == target_type or target_type == WSType.ANY:
        return value

    # Safe coercions
    if actual == WSType.INTEGER and target_type == WSType.DECIMAL:
        return float(value)
    if actual == WSType.DECIMAL and target_type == WSType.INTEGER:
        if value == int(value):
            return int(value)
    if target_type == WSType.STRING:
        return str(value)
    if actual == WSType.STRING and target_type == WSType.INTEGER:
        if str(value).lstrip("-").isdigit():
            return int(value)

    raise WinScriptTypeError(
        arg="",
        expected=target_type.value,
        got=actual.value,
        command="set"
    )

def check(value: Any, declared_type: WSType, variable_name: str) -> Any:
    """
    Enforce type on assignment. Returns possibly coerced value.
    Raises WinScriptTypeError with variable name if incompatible.
    """
    try:
        return coerce(value, declared_type)
    except WinScriptTypeError:
        raise WinScriptTypeError(
            arg=variable_name,
            expected=declared_type.value,
            got=infer_type(value).value,
            command="set"
        )