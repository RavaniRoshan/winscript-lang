from pathlib import Path
from lark import Lark, Transformer, UnexpectedInput, Token
from winscript.ast_nodes import (
    Script, TellBlock, SetStatement, ReturnStatement, WaitUntilStatement, 
    WaitDurationStatement, TryBlock, IfStatement, CommandStatement, PropertyAccess,
    ConcatExpr, Identifier, StringLiteral, NumberLiteral, BoolLiteral, Condition,
    RepeatTimesBlock, RepeatWhileBlock, RepeatWithBlock, FunctionDef, FunctionCall,
    ScopeDeclaration, DeclareStatement, UsingStatement, ListLiteral, ArithExpr,
    SessionSaveStatement, SessionLoadStatement, AsyncBlock, AwaitStatement, ParallelBlock
)
from winscript.session import SessionManager
from winscript.errors import WinScriptSyntaxError

class WinScriptTransformer(Transformer):

    def start(self, items) -> Script:
        statements = [item for item in items if not isinstance(item, Token)]
        return Script(statements=statements)

    def tell_block(self, items) -> TellBlock:
        app = items[0]
        if len(items) > 1 and isinstance(items[1], Token) and items[1].type == 'ESCAPED_STRING':
            app = f"{app} {items[1]}"
            stmts = [item for item in items[2:] if not isinstance(item, Token)]
        else:
            stmts = [item for item in items[1:] if not isinstance(item, Token)]
        return TellBlock(app_name=app, statements=stmts)

    def app_name(self, items):
        return ".".join(str(item) for item in items)

    def set_property(self, items) -> SetStatement:
        return SetStatement(target=items[0], value=items[1])

    def set_variable(self, items) -> SetStatement:
        return SetStatement(target=str(items[0]), value=items[1])

    def return_stmt(self, items) -> ReturnStatement:
        return ReturnStatement(value=items[0])

    def wait_until(self, items) -> WaitUntilStatement:
        return WaitUntilStatement(condition=items[0])

    def wait_duration(self, items) -> WaitDurationStatement:
        duration = float(items[0])
        unit = items[1]
        if unit == "seconds":
            duration *= 1000
        return WaitDurationStatement(duration_ms=int(duration))

    def seconds(self, items): return "seconds"
    def milliseconds(self, items): return "milliseconds"

    def try_block(self, items) -> TryBlock:
        # Find where the catch block begins using the IDENT for catch_var
        for i, item in enumerate(items):
            if isinstance(item, Token) and item.type == 'IDENT':
                try_stmts = [x for x in items[:i] if not isinstance(x, Token)]
                catch_var = str(item)
                catch_stmts = [x for x in items[i+1:] if not isinstance(x, Token)]
                return TryBlock(try_stmts=try_stmts, catch_var=catch_var, catch_stmts=catch_stmts)
        return TryBlock([], "", [])

    def if_block(self, items) -> IfStatement:
        condition = items[0]
        then_stmts = [x for x in items[1:] if not isinstance(x, Token)]
        return IfStatement(condition=condition, then_stmts=then_stmts)

    def contains_cond(self, items) -> Condition: return Condition(left=items[0], operator="contains", right=items[1])
    def gt_cond(self, items) -> Condition: return Condition(left=items[0], operator="greater_than", right=items[1])
    def lt_cond(self, items) -> Condition: return Condition(left=items[0], operator="less_than", right=items[1])
    def eq_cond(self, items) -> Condition: return Condition(left=items[0], operator="is", right=items[1])
    def gt_op_cond(self, items): return Condition(left=items[0], operator=">", right=items[1])
    def gte_op_cond(self, items): return Condition(left=items[0], operator=">=", right=items[1])
    def neq_op_cond(self, items): return Condition(left=items[0], operator="!=", right=items[1])
    def loaded_cond(self, items) -> Condition: return Condition(left=None, operator="loaded", right=None)

    def command_stmt(self, items) -> CommandStatement: return items[0]

    def navigate_cmd(self, items): return CommandStatement("navigate", [], {"to": items[0]})
    def click_cmd(self, items): return CommandStatement("click", [], {"element": items[0]})
    def type_cmd(self, items): return CommandStatement("type", [items[0]], {"element": items[1]})
    def press_cmd(self, items): return CommandStatement("press", [items[0]], {})
    def screenshot_cmd(self, items): return CommandStatement("screenshot", [], {})
    def open_cmd(self, items): return CommandStatement("open", [items[0]], {})
    def run_script_cmd(self, items): return CommandStatement("run_script", [items[0]], {})
    def save_cmd(self, items): return CommandStatement("save", [], {})
    def quit_cmd(self, items): return CommandStatement("quit", [], {})
    def generic_cmd(self, items):
        name_parts = []
        args = []
        for item in items:
            if isinstance(item, Token) and item.type == 'IDENT':
                name_parts.append(str(item))
            elif isinstance(item, Identifier):
                name_parts.append(str(item.name))
            else:
                args.append(item)
        return CommandStatement("_".join(name_parts), args, {})

    def property_access(self, items):
        return PropertyAccess(prop=str(items[0]), of_expr=items[1])

    def compound_name(self, items):
        # Create nested PropertyAccess nodes right-to-left
        if isinstance(items[-1], Token) and items[-1].type == 'ESCAPED_STRING':
            node = StringLiteral(value=str(items[-1])[1:-1])
        else:
            node = Identifier(name=str(items[-1]))
        for item in reversed(items[:-1]):
            node = PropertyAccess(prop=str(item), of_expr=node)
        return node

    def concat(self, items): return ConcatExpr(left=items[0], right=items[1])
    def add(self, items): return ArithExpr(left=items[0], operator="+", right=items[1])
    def sub(self, items): return ArithExpr(left=items[0], operator="-", right=items[1])
    def mul(self, items): return ArithExpr(left=items[0], operator="*", right=items[1])
    def div(self, items): return ArithExpr(left=items[0], operator="/", right=items[1])
    def string_lit(self, items): return StringLiteral(value=str(items[0])[1:-1])
    def number_lit(self, items): return NumberLiteral(value=float(items[0]))
    def true_lit(self, items): return BoolLiteral(value=True)
    def false_lit(self, items): return BoolLiteral(value=False)
    def prop_expr(self, items): return items[0]
    def ident_expr(self, items): return Identifier(name=str(items[0]))
    def func_call_expr(self, items): return items[0]
    def list_expr(self, items): return items[0]

    # V2 Nodes
    def repeat_block(self, items): return items[0]

    def repeat_times(self, items) -> RepeatTimesBlock:
        return RepeatTimesBlock(count_expr=items[0], statements=[x for x in items[1:] if not isinstance(x, Token)])

    def repeat_while(self, items) -> RepeatWhileBlock:
        return RepeatWhileBlock(condition=items[0], statements=[x for x in items[1:] if not isinstance(x, Token)])

    def repeat_with(self, items) -> RepeatWithBlock:
        return RepeatWithBlock(variable=str(items[0]), iterable_expr=items[1], statements=[x for x in items[2:] if not isinstance(x, Token)])

    def function_def(self, items) -> FunctionDef:
        name = str(items[0])
        params = []
        stmts = []
        for item in items[1:]:
            if isinstance(item, list) and (not item or isinstance(item[0], str)):
                params = item
            elif not isinstance(item, Token) and item is not None:
                stmts.append(item)
        return FunctionDef(name=name, params=params, statements=stmts)

    def param_list(self, items) -> list:
        return [str(i) for i in items]

    def function_call(self, items) -> FunctionCall:
        name = str(items[0])
        args = []
        for item in items[1:]:
            if isinstance(item, list):
                args = item
        return FunctionCall(name=name, args=args)

    def arg_list(self, items) -> list:
        return list(items)

    def scope_declaration(self, items) -> ScopeDeclaration:
        return ScopeDeclaration(scope=str(items[0]), variable=str(items[1]))

    def declare_statement(self, items) -> DeclareStatement:
        return DeclareStatement(variable=str(items[0]), type_name=str(items[1]))

    def type_name(self, items) -> str:
        return str(items[0])

    def using_statement(self, items) -> UsingStatement:
        return UsingStatement(path=str(items[0])[1:-1])

    def list_literal(self, items) -> ListLiteral:
        return ListLiteral(items=[x for x in items if not isinstance(x, Token)])

    def session_save(self, items) -> SessionSaveStatement:
        return SessionSaveStatement(name=str(items[0])[1:-1])

    def session_load(self, items) -> SessionLoadStatement:
        return SessionLoadStatement(name=str(items[0])[1:-1])

    def async_tell_block(self, items):
        # First item is app_name, rest are statements
        app_name = items[0]
        stmts = [item for item in items[1:] if not isinstance(item, Token)]
        return AsyncBlock(tell_block=TellBlock(app_name=app_name, statements=stmts))

    def await_statement(self, items):
        target = str(items[0]) if items and not isinstance(items[0], Token) else None
        return AwaitStatement(target=target)

    def parallel_block(self, items):
        tell_blocks = [item for item in items if isinstance(item, TellBlock)]
        return ParallelBlock(tell_blocks=tell_blocks)


def validate_v2(ast: Script) -> list[str]:
    errors = []
    has_seen_non_using = False

    def walk(node):
        nonlocal has_seen_non_using
        
        # Check using statements are at the top
        if isinstance(node, UsingStatement):
            if has_seen_non_using:
                errors.append("UsingStatement must appear at top of file")
        elif isinstance(node, Script):
            pass # Script doesn't count as a real statement
        else:
            has_seen_non_using = True

        # Check no nested function defs
        if isinstance(node, FunctionDef):
            def check_nested(child_node):
                if isinstance(child_node, FunctionDef):
                    errors.append("Nested functions are not allowed in v2")
                elif hasattr(child_node, "statements"):
                    for stmt in child_node.statements:
                        check_nested(stmt)
            
            for stmt in node.statements:
                check_nested(stmt)

        # Traverse children
        if hasattr(node, "statements"):
            for stmt in node.statements:
                walk(stmt)

    walk(ast)
    return errors


def parse(source_code: str) -> Script:
    """
    Parse WinScript source code. Returns Script AST node.
    Raises WinScriptSyntaxError on parse failure.
    """
    if not source_code.endswith("\n"):
        source_code += "\n"
        
    grammar_path = Path(__file__).parent / "grammar.lark"
    parser = Lark.open(str(grammar_path), parser="earley", start="start")
    
    try:
        tree = parser.parse(source_code)
        return WinScriptTransformer().transform(tree)
    except UnexpectedInput as e:
        raise WinScriptSyntaxError(str(e), line=getattr(e, "line", 0))

def get_parser() -> Lark:
    """Return a configured Lark parser for WinScript."""
    grammar_path = Path(__file__).parent / "grammar.lark"
    return Lark.open(str(grammar_path), parser="earley", start="start")
