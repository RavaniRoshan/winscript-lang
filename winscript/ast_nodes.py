from dataclasses import dataclass, field
from typing import Any, List, Optional, Union

@dataclass
class Script:
    statements: list

@dataclass
class TellBlock:
    app_name: str
    statements: list

@dataclass
class SetStatement:
    target: Any
    value: Any

@dataclass
class ReturnStatement:
    value: Any

@dataclass
class WaitUntilStatement:
    condition: Any
    timeout_ms: int = 10000

@dataclass
class WaitDurationStatement:
    duration_ms: int

@dataclass
class TryBlock:
    try_stmts: list
    catch_var: str
    catch_stmts: list

@dataclass
class IfStatement:
    condition: Any
    then_stmts: list

@dataclass
class CommandStatement:
    name: str
    args: list
    kwargs: dict

@dataclass
class PropertyAccess:
    prop: str
    of_expr: Any

@dataclass
class ConcatExpr:
    left: Any
    right: Any

@dataclass
class Identifier:
    name: str

@dataclass
class StringLiteral:
    value: str

@dataclass
class NumberLiteral:
    value: float

@dataclass
class BoolLiteral:
    value: bool

@dataclass
class Condition:
    left: Any
    operator: str
    right: Any
