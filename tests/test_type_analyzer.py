"""Tests for the type analyzer."""

import pytest
from winscript.type_analyzer import (
    TypeAnalyzer, TypeInfo, InferredType, TypeHintGenerator
)
from winscript.ast_nodes import (
    StringLiteral, NumberLiteral, BoolLiteral, ListLiteral,
    ConcatExpr, ArithExpr, Identifier, FunctionDef, ReturnStatement
)


class TestTypeAnalyzer:
    """Test type inference functionality."""

    def test_string_literal(self):
        """Test inferring string literals."""
        analyzer = TypeAnalyzer()
        result = analyzer.infer_type(StringLiteral(value="hello"))
        
        assert result.base_type == InferredType.STRING

    def test_integer_literal(self):
        """Test inferring integer literals."""
        analyzer = TypeAnalyzer()
        result = analyzer.infer_type(NumberLiteral(value=42.0))
        
        assert result.base_type == InferredType.INTEGER

    def test_decimal_literal(self):
        """Test inferring decimal literals."""
        analyzer = TypeAnalyzer()
        result = analyzer.infer_type(NumberLiteral(value=3.14))
        
        assert result.base_type == InferredType.DECIMAL

    def test_boolean_literal(self):
        """Test inferring boolean literals."""
        analyzer = TypeAnalyzer()
        result = analyzer.infer_type(BoolLiteral(value=True))
        
        assert result.base_type == InferredType.BOOLEAN

    def test_list_literal(self):
        """Test inferring list literals."""
        analyzer = TypeAnalyzer()
        result = analyzer.infer_type(ListLiteral(items=[
            StringLiteral(value="a"),
            StringLiteral(value="b")
        ]))
        
        assert result.base_type == InferredType.LIST
        assert result.element_type is not None
        assert result.element_type.base_type == InferredType.STRING

    def test_concat_expression(self):
        """Test inferring string concatenation."""
        analyzer = TypeAnalyzer()
        result = analyzer.infer_type(ConcatExpr(
            left=StringLiteral(value="hello"),
            right=StringLiteral(value=" world")
        ))
        
        assert result.base_type == InferredType.STRING

    def test_arithmetic_addition(self):
        """Test inferring integer addition."""
        analyzer = TypeAnalyzer()
        result = analyzer.infer_type(ArithExpr(
            left=NumberLiteral(value=5.0),
            operator="+",
            right=NumberLiteral(value=3.0)
        ))
        
        assert result.base_type == InferredType.INTEGER

    def test_arithmetic_division(self):
        """Test that division produces decimal."""
        analyzer = TypeAnalyzer()
        result = analyzer.infer_type(ArithExpr(
            left=NumberLiteral(value=10.0),
            operator="/",
            right=NumberLiteral(value=3.0)
        ))
        
        assert result.base_type == InferredType.DECIMAL

    def test_decimal_arithmetic(self):
        """Test that mixed int/decimal produces decimal."""
        analyzer = TypeAnalyzer()
        result = analyzer.infer_type(ArithExpr(
            left=NumberLiteral(value=5.0),  # Integer
            operator="+",
            right=NumberLiteral(value=2.5)  # Decimal
        ))
        
        assert result.base_type == InferredType.DECIMAL

    def test_type_assignability(self):
        """Test type compatibility checking."""
        analyzer = TypeAnalyzer()
        
        int_type = TypeInfo(InferredType.INTEGER)
        decimal_type = TypeInfo(InferredType.DECIMAL)
        string_type = TypeInfo(InferredType.STRING)
        
        # Integer is assignable to Decimal
        assert analyzer.is_assignable(int_type, decimal_type)
        
        # Integer is not assignable to String
        assert not analyzer.is_assignable(int_type, string_type)
        
        # Any type is assignable to Any
        any_type = TypeInfo(InferredType.ANY)
        assert analyzer.is_assignable(string_type, any_type)

    def test_type_formatting(self):
        """Test type formatting."""
        analyzer = TypeAnalyzer()
        
        assert analyzer.format_type(TypeInfo(InferredType.STRING)) == "string"
        assert analyzer.format_type(TypeInfo(InferredType.INTEGER)) == "integer"
        
        # List with element type
        list_type = TypeInfo(InferredType.LIST, element_type=TypeInfo(InferredType.STRING))
        assert "list[string]" == analyzer.format_type(list_type)


class TestTypeHintGenerator:
    """Test type hint generation."""

    def test_function_signature(self):
        """Test generating function signatures."""
        generator = TypeHintGenerator()
        
        func = FunctionDef(
            name="greet",
            params=["name"],
            statements=[
                ReturnStatement(value=ConcatExpr(
                    left=StringLiteral(value="Hello "),
                    right=Identifier(name="name")
                ))
            ]
        )
        
        # Generate signature
        signature = generator.generate_function_signature(func)
        assert "greet" in signature
        assert "on " in signature


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
