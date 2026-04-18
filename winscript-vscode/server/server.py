import sys
from pygls.lsp.server import LanguageServer
from lsprotocol import types as lsp
from winscript.parser import parse
from winscript.errors import WinScriptSyntaxError
from winscript.dicts.loader import DictLoader

server = LanguageServer("winscript-lsp", "v2")
dict_loader = DictLoader()

@server.feature(lsp.TEXT_DOCUMENT_DID_OPEN)
@server.feature(lsp.TEXT_DOCUMENT_DID_CHANGE)
def on_change(ls: LanguageServer, params):
    """Validate script on every change. Report syntax errors as diagnostics."""
    uri = params.text_document.uri
    text = ls.workspace.get_text_document(uri).source

    diagnostics = []
    try:
        parse(text)
    except WinScriptSyntaxError as e:
        diag = lsp.Diagnostic(
            range=lsp.Range(
                start=lsp.Position(line=max(0, e.line - 1), character=0),
                end=lsp.Position(line=max(0, e.line - 1), character=100),
            ),
            message=str(e),
            severity=lsp.DiagnosticSeverity.Error,
            source="winscript",
        )
        diagnostics.append(diag)

    ls.publish_diagnostics(uri, diagnostics)

@server.feature(
    lsp.TEXT_DOCUMENT_COMPLETION,
    lsp.CompletionOptions(trigger_characters=[".", " "])
)
def on_completion(ls: LanguageServer, params: lsp.CompletionParams):
    uri = params.text_document.uri
    text = ls.workspace.get_text_document(uri).source
    lines = text.split("\n")
    if params.position.line >= len(lines):
        return lsp.CompletionList(is_incomplete=False, items=[])
    
    line_text = lines[params.position.line]

    items = []

    # After "tell " → app names
    if line_text.strip().startswith("tell "):
        apps = dict_loader.list_all()
        for app in apps:
            items.append(lsp.CompletionItem(
                label=app["name"],
                kind=lsp.CompletionItemKind.Class,
                detail=app.get("description", ""),
                documentation=f"Backend: {app.get('backend', '')}",
            ))

    # Top-level keywords
    elif not line_text.strip() or len(line_text.strip().split()) <= 1:
        keywords = [
            "tell", "set", "return", "try", "repeat", "on",
            "using", "declare", "global", "local", "if", "wait"
        ]
        for kw in keywords:
            items.append(lsp.CompletionItem(
                label=kw,
                kind=lsp.CompletionItemKind.Keyword,
            ))

    return lsp.CompletionList(is_incomplete=False, items=items)

def _get_word_at(line: str, char: int) -> str:
    if char >= len(line):
        char = len(line) - 1
    if char < 0:
        return ""
    start = char
    while start > 0 and line[start-1].isalnum() or line[start-1] == "_":
        start -= 1
    end = char
    while end < len(line) and line[end].isalnum() or line[end] == "_":
        end += 1
    return line[start:end]

@server.feature(lsp.TEXT_DOCUMENT_HOVER)
def on_hover(ls: LanguageServer, params: lsp.HoverParams):
    """
    Show hover docs for keywords and app names.
    """
    uri = params.text_document.uri
    text = ls.workspace.get_text_document(uri).source
    lines = text.split("\n")
    if params.position.line >= len(lines):
        return None
        
    line = lines[params.position.line]
    word = _get_word_at(line, params.position.character)

    KEYWORD_DOCS = {
        "tell": "**tell** *AppName*\n\nEstablish a scripting context with an app.\n\n```\ntell Chrome\n  navigate to \"url\"\nend tell\n```",
        "repeat": "**repeat** *N* **times** or **while** *condition* or **with** *var* **in** *list*",
        "on": "Define a function: **on** *name*(*params*) ... **end on**",
        "try": "Error handling: **try** ... **catch** *errVar* ... **end try**",
    }

    if word in KEYWORD_DOCS:
        return lsp.Hover(
            contents=lsp.MarkupContent(
                kind=lsp.MarkupKind.Markdown,
                value=KEYWORD_DOCS[word]
            )
        )

    # Check if it's a known app
    try:
        app_dict = dict_loader.load(word)
        commands = ", ".join(
            cmd.name for obj in app_dict.objects.values()
            for cmd in obj.commands[:5]
        )
        return lsp.Hover(
            contents=lsp.MarkupContent(
                kind=lsp.MarkupKind.Markdown,
                value=f"**{word}** — {app_dict.description}\n\nCommands: {commands}..."
            )
        )
    except Exception:
        pass

    return None

if __name__ == "__main__":
    server.start_io()
