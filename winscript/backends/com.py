"""
winscript.backends.com — COM/pywin32 backend for Office apps.

This backend will enable automation of Excel, Word, Outlook, and other
COM-compatible applications via the pywin32 library.
"""

import sys
import os
from typing import Any
from winscript.backends.base import Backend
from winscript.errors import WinScriptError, WinScriptConnectionError


class COMBackend(Backend):
    def __init__(self, prog_id: str, visible: bool = False, quit_on_disconnect: bool = True, **kwargs):
        self.prog_id = prog_id
        self._should_visible = visible
        self._should_quit = quit_on_disconnect
        self._app = None
        self._context_stack: list[Any] = []

    def connect(self):
        try:
            import win32com.client
            self._app = win32com.client.Dispatch(self.prog_id)
            if hasattr(self._app, "Visible"):
                self._app.Visible = self._should_visible
        except ImportError:
            if sys.platform != "win32":
                self._app = MockCOMApp(self.prog_id)
            else:
                raise WinScriptConnectionError(self.prog_id, "Requires pywin32")

    def push_context(self, obj_type: str, identifier: str):
        """
        Push a sub-object context.
        For Excel: push_context("sheet", "Summary") → self._app.ActiveWorkbook.Sheets("Summary")
        """
        if obj_type.lower() == "sheet":
            # Access the sheet on the ActiveWorkbook
            sheet = self._app.ActiveWorkbook.Sheets(identifier)
            self._context_stack.append(sheet)
        else:
            raise WinScriptError(f"Unsupported COM sub-context type: {obj_type}")

    def pop_context(self):
        if self._context_stack:
            self._context_stack.pop()

    @property
    def current_context(self) -> Any:
        if self._context_stack:
            return self._context_stack[-1]
        return self._app

    def execute(self, method: str, params: dict = None) -> Any:
        ctx = self.current_context
        locs = dict(params or {})
        
        # Try routing to ActiveWorkbook or ActiveSheet if the method fails on ctx
        contexts_to_try = [ctx]
        if hasattr(ctx, "ActiveWorkbook") and ctx.ActiveWorkbook:
            contexts_to_try.append(ctx.ActiveWorkbook)
        if hasattr(ctx, "ActiveSheet") and ctx.ActiveSheet:
            contexts_to_try.append(ctx.ActiveSheet)
            
        for c in contexts_to_try:
            locs["ctx"] = c
            code = f"ctx.{method}"
            try:
                try:
                    return eval(code, {}, locs)
                except SyntaxError:
                    exec(code, {}, locs)
                    return None
            except AttributeError:
                continue
            except Exception as e:
                # If it failed for another reason (e.g. arg mismatch), raise it
                raise e
                
        # If all failed due to AttributeError, raise
        raise AttributeError(f"Method '{method}' not found on current context or active children.")

    def get_property(self, com_property: str, expression: str = None) -> Any:
        ctx = self.current_context
        code = f"ctx.{expression or com_property}"
        return eval(code, {}, {"ctx": ctx})

    def disconnect(self):
        try:
            if self._app and self._should_quit:
                self._app.Quit()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Mock for testing on Linux
# ---------------------------------------------------------------------------

class MockCOMApp:
    def __init__(self, prog_id):
        self.prog_id = prog_id
        self.Visible = False
        self.Workbooks = MockWorkbooks(self)
        self.ActiveWorkbook = None

    def Quit(self):
        pass

    def Calculate(self):
        pass


class MockWorkbooks:
    def __init__(self, app):
        self.app = app
        self.books = []
        
    def Open(self, filepath):
        book = MockWorkbook(filepath, self.app)
        self.books.append(book)
        self.app.ActiveWorkbook = book
        return book


class MockWorkbook:
    def __init__(self, filepath, app):
        self.Name = os.path.basename(filepath)
        self.FullName = filepath
        self.app = app
        self.Saved = True
        self._sheets_col = MockSheets()
        self.ActiveSheet = self._sheets_col("Sheet1")
        
    def Sheets(self, name):
        return self._sheets_col(name)
        
    def Save(self):
        self.Saved = True
        
    def SaveAs(self, filepath):
        self.FullName = filepath
        self.Name = os.path.basename(filepath)
        self.Saved = True

    def Close(self, SaveChanges=True):
        if self in self.app.Workbooks.books:
            self.app.Workbooks.books.remove(self)


class MockSheets:
    def __init__(self):
        self._sheets = {"Sheet1": MockSheet("Sheet1"), "Summary": MockSheet("Summary")}
        
    def __call__(self, name):
        if name not in self._sheets:
            self._sheets[name] = MockSheet(name)
        return self._sheets[name]

    def __iter__(self):
        return iter(self._sheets.values())


class MockSheet:
    def __init__(self, name):
        self.Name = name
        self.UsedRange = MockRange("A1:Z100")
        self._cells = {}
        
    def Activate(self):
        pass
        
    def Range(self, address):
        if address not in self._cells:
            self._cells[address] = MockRange(address)
        return self._cells[address]

    def Cells(self):
        return self

    def Find(self, What):
        for addr, cell in self._cells.items():
            if cell.Value == What:
                return MockRange(addr)
        return MockRange("")


class MockRange:
    def __init__(self, address):
        self.Address = address
        self.Value = None
        if address == "B2":
            self.Value = 100.0
        elif address == "C2":
            self.Value = 0.05
        self.NumberFormat = "General"
        
    def ClearContents(self):
        self.Value = None
        
    def Copy(self):
        pass
