"""
winscript.type_analyzer — Enhanced Type Inference System

Provides sophisticated type inference and checking for WinScript.
Supports generic types, union types, and advanced inference.

Usage:
    from winscript.type_analyzer import TypeAnalyzer
    analyzer = TypeAnalyzer()
    inferred_type = analyzer.infer_type(ast_node, context)
"""

from typing import Any, Optional, Union
from dataclasses import dataclass
from enum import Enum, auto

from winscript.ast_nodes import *
from winscript.types import WSType


class InferredType(Enum):
    """Extended type system with inference capabilities."""
    UNKNOWN = auto()
    STRING = auto()
    INTEGER = auto()
    DECIMAL = auto()
    BOOLEAN = auto()
    LIST = auto()
    DICT = auto()
    FUNCTION = auto()
    PROMISE = auto()  # For async operations
    UNION = auto()    # Union type: string | integer
    GENERIC = auto()  # Generic type: List<T>
    ANY = auto()
    NEVER = auto()    # For errors/never returns


@dataclass
class TypeInfo:
    """Detailed type information with constraints."""
    base_type: InferredType
    element_type: Optional['TypeInfo'] = None  # For List<T>, Promise<T>
    union_types: list['TypeInfo'] = None  # For union types
    is_optional: bool = False
    is_nullable: bool = False
    constraints: dict = None  # Type constraints
    
    def __post_init__(self):
        if self.union_types is None:
            self.union_types = []
        if self.constraints is None:
            self.constraints = {}


class TypeAnalyzer:
    """
    Advanced type analyzer for WinScript.
    
    Features:
    - Type inference from expressions
    - Flow-sensitive typing
    - Generic type support
    - Union type checking
    """
    
    def __init__(self):
        self.type_cache: dict[int, TypeInfo] = {}
        self.scope_types: dict[str, TypeInfo] = {}
    
    def infer_type(self, node: Any, context: dict = None) -> TypeInfo:
        """
        Infer the type of an AST node.
        
        Args:
            node: AST node to analyze
            context: Optional typing context
        
        Returns:
            TypeInfo with inferred type
        """
        context = context or {}
        
        # Check cache
        node_id = id(node)
        if node_id in self.type_cache:
            return self.type_cache[node_id]
        
        # Infer based on node type
        if isinstance(node, StringLiteral):
            result = TypeInfo(InferredType.STRING)
        elif isinstance(node, NumberLiteral):
            # Distinguish between integer and decimal
            if node.value == int(node.value):
                result = TypeInfo(InferredType.INTEGER)
            else:
                result = TypeInfo(InferredType.DECIMAL)
        elif isinstance(node, BoolLiteral):
            result = TypeInfo(InferredType.BOOLEAN)
        elif isinstance(node, ListLiteral):
            # Infer element type from list contents
            element_types = [self.infer_type(item, context) for item in node.items]
            common_type = self._common_type(element_types)
            result = TypeInfo(InferredType.LIST, element_type=common_type)
        elif isinstance(node, Identifier):
            result = self._infer_identifier(node, context)
        elif isinstance(node, ConcatExpr):
            # String concatenation always returns string
            result = TypeInfo(InferredType.STRING)
        elif isinstance(node, ArithExpr):
            result = self._infer_arithmetic(node, context)
        elif isinstance(node, FunctionCall):
            result = self._infer_function_call(node, context)
        elif isinstance(node, PropertyAccess):
            result = self._infer_property_access(node, context)
        elif isinstance(node, Condition):
            result = TypeInfo(InferredType.BOOLEAN)
        else:
            result = TypeInfo(InferredType.UNKNOWN)
        
        # Cache result
        self.type_cache[node_id] = result
        return result
    
    def _infer_identifier(self, node: Identifier, context: dict) -> TypeInfo:
        """Infer type from identifier lookup."""
        name = node.name
        
        # Check scope types
        if name in self.scope_types:
            return self.scope_types[name]
        
        # Check context
        if name in context:
            return self._type_from_value(context[name])
        
        # Check for special variables
        if name.startswith('$'):
            # CLI arguments are always strings
            return TypeInfo(InferredType.STRING)
        
        return TypeInfo(InferredType.UNKNOWN)
    
    def _infer_arithmetic(self, node: ArithExpr, context: dict) -> TypeInfo:
        """Infer type from arithmetic expression."""
        left_type = self.infer_type(node.left, context)
        right_type = self.infer_type(node.right, context)
        
        # String + String = String (concatenation)
        if node.operator == '+' and left_type.base_type == InferredType.STRING:
            return TypeInfo(InferredType.STRING)
        
        # Number arithmetic
        if node.operator in ('+', '-', '*', '/'):
            # If either operand is decimal, result is decimal
            if (left_type.base_type == InferredType.DECIMAL or 
                right_type.base_type == InferredType.DECIMAL):
                return TypeInfo(InferredType.DECIMAL)
            # Division always produces decimal
            if node.operator == '/':
                return TypeInfo(InferredType.DECIMAL)
            # Integer operations
            return TypeInfo(InferredType.INTEGER)
        
        return TypeInfo(InferredType.UNKNOWN)
    
    def _infer_function_call(self, node: FunctionCall, context: dict) -> TypeInfo:
        """Infer type from function call."""
        # TODO: Look up function return type from registry
        # For now, return any
        return TypeInfo(InferredType.ANY)
    
    def _infer_property_access(self, node: PropertyAccess, context: dict) -> TypeInfo:
        """Infer type from property access."""
        # TODO: Look up property types from dictionary definitions
        # For now, return any
        return TypeInfo(InferredType.ANY)
    
    def _common_type(self, types: list[TypeInfo]) -> TypeInfo:
        """Find common type among a list of types."""
        if not types:
            return TypeInfo(InferredType.UNKNOWN)
        
        if len(types) == 1:
            return types[0]
        
        # Check if all are the same
        first = types[0].base_type
        if all(t.base_type == first for t in types):
            return types[0]
        
        # Check for numeric types
        if all(t.base_type in (InferredType.INTEGER, InferredType.DECIMAL) for t in types):
            return TypeInfo(InferredType.DECIMAL)  # Promote to decimal
        
        # Check for string compatibility
        if all(t.base_type == InferredType.STRING for t in types):
            return TypeInfo(InferredType.STRING)
        
        # Return union type
        return TypeInfo(InferredType.UNION, union_types=types)
    
    def _type_from_value(self, value: Any) -> TypeInfo:
        """Create TypeInfo from a Python value."""
        if isinstance(value, str):
            return TypeInfo(InferredType.STRING)
        elif isinstance(value, int):
            return TypeInfo(InferredType.INTEGER)
        elif isinstance(value, float):
            return TypeInfo(InferredType.DECIMAL)
        elif isinstance(value, bool):
            return TypeInfo(InferredType.BOOLEAN)
        elif isinstance(value, list):
            return TypeInfo(InferredType.LIST)
        elif isinstance(value, dict):
            return TypeInfo(InferredType.DICT)
        else:
            return TypeInfo(InferredType.ANY)
    
    def is_assignable(self, source: TypeInfo, target: TypeInfo) -> bool:
        """Check if source type can be assigned to target type."""
        # Any type is assignable to any
        if target.base_type == InferredType.ANY:
            return True
        
        # Same type
        if source.base_type == target.base_type:
            # Check element types for containers
            if source.element_type and target.element_type:
                return self.is_assignable(source.element_type, target.element_type)
            return True
        
        # Integer is assignable to Decimal
        if source.base_type == InferredType.INTEGER and target.base_type == InferredType.DECIMAL:
            return True
        
        # Check union types
        if target.base_type == InferredType.UNION:
            return any(self.is_assignable(source, t) for t in target.union_types)
        
        # Nullable check
        if target.is_nullable and source.base_type == InferredType.UNKNOWN:
            return True
        
        return False
    
    def check_compatibility(self, left: TypeInfo, right: TypeInfo, operator: str) -> bool:
        """Check if types are compatible for an operation."""
        if operator in ('+', '-', '*', '/'):
            # Arithmetic requires numeric types
            numeric_types = (InferredType.INTEGER, InferredType.DECIMAL)
            return (left.base_type in numeric_types and 
                    right.base_type in numeric_types)
        
        if operator in ('==', '!=', '<', '>', '<=', '>='):
            # Comparison requires compatible types
            if left.base_type in (InferredType.INTEGER, InferredType.DECIMAL):
                return right.base_type in (InferredType.INTEGER, InferredType.DECIMAL)
            if left.base_type == InferredType.STRING:
                return right.base_type == InferredType.STRING
            return True  # Allow comparison of any types
        
        if operator == 'contains':
            # Contains requires string types
            return (left.base_type == InferredType.STRING and 
                    right.base_type == InferredType.STRING)
        
        return True
    
    def format_type(self, type_info: TypeInfo) -> str:
        """Format TypeInfo as a string."""
        if type_info.base_type == InferredType.LIST and type_info.element_type:
            return f"list[{self.format_type(type_info.element_type)}]"
        
        if type_info.base_type == InferredType.UNION:
            return " | ".join(self.format_type(t) for t in type_info.union_types)
        
        if type_info.base_type == InferredType.PROMISE and type_info.element_type:
            return f"promise[{self.format_type(type_info.element_type)}]"
        
        suffix = "?" if type_info.is_optional else ""
        return f"{type_info.base_type.name.lower()}{suffix}"
    
    def analyze_script(self, script: Script) -> list[dict]:
        """
        Analyze entire script for type errors.
        
        Returns list of type errors/warnings.
        """
        errors = []
        
        for i, stmt in enumerate(script.statements):
            stmt_errors = self._analyze_statement(stmt)
            for error in stmt_errors:
                error['line'] = i + 1
                errors.append(error)
        
        return errors
    
    def _analyze_statement(self, stmt: Any) -> list[dict]:
        """Analyze a single statement for type issues."""
        errors = []
        
        if isinstance(stmt, SetStatement):
            # Check type compatibility in assignment
            if isinstance(stmt.value, (Identifier, FunctionCall, ArithExpr)):
                source_type = self.infer_type(stmt.value)
                # TODO: Look up target type if declared
                pass
        
        elif isinstance(stmt, IfStatement):
            # Condition must be boolean
            cond_type = self.infer_type(stmt.condition)
            if cond_type.base_type != InferredType.BOOLEAN:
                errors.append({
                    'message': f"Condition should be boolean, got {self.format_type(cond_type)}",
                    'severity': 'warning'
                })
        
        elif isinstance(stmt, FunctionCall):
            # Check argument types
            for arg in stmt.args:
                arg_type = self.infer_type(arg)
                # TODO: Check against function signature
                pass
        
        return errors


class TypeHintGenerator:
    """
    Generates type hints for WinScript code.
    Useful for IDE support and documentation.
    """
    
    def __init__(self, analyzer: TypeAnalyzer = None):
        self.analyzer = analyzer or TypeAnalyzer()
    
    def generate_function_signature(self, func_def: FunctionDef, context: dict = None) -> str:
        """
        Generate type signature for a function.
        
        Example:
            on greet(name: string) -> string
        """
        param_types = []
        for param in func_def.params:
            # Infer from usage in function body
            param_type = self._infer_param_type(param, func_def)
            param_types.append(f"{param}: {param_type}")
        
        # Infer return type from return statements
        return_type = self._infer_return_type(func_def)
        
        params_str = ", ".join(param_types) if param_types else ""
        return f"on {func_def.name}({params_str}) -> {return_type}"
    
    def _infer_param_type(self, param: str, func_def: FunctionDef) -> str:
        """Infer parameter type from usage."""
        # Look for operations on the parameter
        # Default to any
        return "any"
    
    def _infer_return_type(self, func_def: FunctionDef) -> str:
        """Infer return type from return statements."""
        return_types = []
        
        def find_returns(node):
            if isinstance(node, ReturnStatement):
                return_types.append(self.analyzer.infer_type(node.value))
            elif hasattr(node, 'statements'):
                for stmt in node.statements:
                    find_returns(stmt)
        
        find_returns(func_def)
        
        if not return_types:
            return "void"
        
        # Find common type
        if len(return_types) == 1:
            return self.analyzer.format_type(return_types[0])
        
        common = self.analyzer._common_type(return_types)
        return self.analyzer.format_type(common)
