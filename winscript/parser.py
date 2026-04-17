from pathlib import Path
from lark import Lark, Transformer, UnexpectedInput, Token
from winscript.ast_nodes import *
from winscript.errors import WinScriptSyntaxError

class WinScriptTransformer(Transformer):

    def start(self, items) -> Script:
        statements = [item for item in items if not isinstance(item, Token)]
        return Script(statements=statements)

    def tell_block(self, items) -> TellBlock:
        app = items[0]
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
    def generic_cmd(self, items): return CommandStatement(str(items[0]), items[1:], {})

    def property_access(self, items):
        return PropertyAccess(prop=str(items[0]), of_expr=items[1])

    def compound_name(self, items):
        # Create nested PropertyAccess nodes right-to-left
        # ex: ["active", "tab"] -> PropertyAccess("active", Identifier("tab"))
        node = Identifier(name=str(items[-1]))
        for item in reversed(items[:-1]):
            node = PropertyAccess(prop=str(item), of_expr=node)
        return node

    def concat(self, items): return ConcatExpr(left=items[0], right=items[1])
    def string_lit(self, items): return StringLiteral(value=str(items[0])[1:-1])
    def number_lit(self, items): return NumberLiteral(value=float(items[0]))
    def true_lit(self, items): return BoolLiteral(value=True)
    def false_lit(self, items): return BoolLiteral(value=False)
    def prop_expr(self, items): return items[0]
    def ident_expr(self, items): return Identifier(name=str(items[0]))

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
