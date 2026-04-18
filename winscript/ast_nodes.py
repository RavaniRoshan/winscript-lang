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

# Loops
@dataclass
class RepeatTimesBlock:
    count_expr: Any        # expression evaluating to integer
    statements: list

@dataclass
class RepeatWhileBlock:
    condition: Any         # Condition node
    statements: list
    max_iterations: int = 10000  # safety limit — no infinite loops

@dataclass
class RepeatWithBlock:
    variable: str          # loop variable name (local to block)
    iterable_expr: Any     # expression evaluating to list
    statements: list

# Functions
@dataclass
class FunctionDef:
    name: str
    params: list[str]      # parameter names in order
    statements: list
    is_library: bool = False  # True if loaded from .wslib

@dataclass
class FunctionCall:
    name: str
    args: list             # positional arg expressions

# Scope
@dataclass
class ScopeDeclaration:
    scope: str             # "global" | "local"
    variable: str

# Types
@dataclass
class DeclareStatement:
    variable: str
    type_name: str         # "string"|"integer"|"decimal"|"boolean"|"list"|"dict"|"any"

# Libraries
@dataclass
class UsingStatement:
    path: str              # path to .wslib file

# List literal
@dataclass
class ListLiteral:
    items: list            # list of expression nodes

# Arithmetic
@dataclass
class ArithExpr:
    left: Any
    operator: str          # "+" | "-" | "*" | "/"
    right: Any
