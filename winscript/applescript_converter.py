"""
winscript.applescript_converter — AppleScript to WinScript Converter

Converts AppleScript syntax to WinScript syntax.
AppleScript is macOS automation language with similar concepts to WinScript.

Usage:
    winscript convert myscript.scpt -o output.ws
    
    # Or programmatically:
    from winscript.applescript_converter import convert
    winscript_code = convert(applescript_code)
"""

import re
from pathlib import Path
from typing import Optional


class AppleScriptConverter:
    """
    Converts AppleScript to WinScript.
    
    AppleScript concepts that map to WinScript:
    - tell / end tell → tell / end tell
    - set x to y → set x to y
    - return x → return x
    - repeat → repeat
    - if / then / end if → if / then / end if
    - try / on error → try / catch
    - my / of → property access
    - & → & (concatenation)
    """
    
    def __init__(self):
        # Application name mappings (macOS → Windows)
        self.app_mappings = {
            "Finder": "FileExplorer",  # No direct equivalent
            "Safari": "Chrome",
            "Google Chrome": "Chrome",
            "Mail": "Outlook",
            "Microsoft Outlook": "Outlook",
            "System Events": "WindowsAutomation",
            "Terminal": "WindowsTerminal",
            "iTunes": "Spotify",  # Different app, similar concept
            "Music": "Spotify",
            "Calendar": "Outlook",
            "Contacts": "Outlook",
            "Notes": "Notepad",
            "TextEdit": "Notepad",
            "Pages": "Word",
            "Numbers": "Excel",
            "Keynote": "PowerPoint",
            "Script Editor": "WinScript",
            "Photoshop": "Photoshop",
            "Adobe Photoshop": "Photoshop",
        }
        
        # Command mappings
        self.command_mappings = {
            # Common AppleScript commands → WinScript equivalents
            "activate": "focus",
            "quit": "quit",
            "open": "open",
            "close": "close",
            "make": "create",
            "delete": "delete",
            "move": "move",
            "copy": "copy",
            "duplicate": "duplicate",
            "select": "select",
            "run": "run",
            "launch": "launch",
            "display dialog": "show dialog",  # Would need custom implementation
            "choose file": "select file",      # Would need custom implementation
            "choose folder": "select folder",  # Would need custom implementation
            "delay": "wait",
            "beep": "play sound",
        }
        
        # Property mappings
        self.property_mappings = {
            "name": "name",
            "version": "version",
            "frontmost": "is_active",
            "visible": "is_visible",
            "bounds": "bounds",
            "position": "position",
            "size": "size",
            "contents": "content",
            "text": "text",
            "title": "title",
            "URL": "url",
        }
    
    def convert(self, source: str) -> str:
        """
        Convert AppleScript source code to WinScript.
        
        Returns the converted WinScript code.
        """
        lines = source.split('\n')
        result = []
        indent_level = 0
        in_tell_block = False
        
        for i, line in enumerate(lines):
            converted_line, new_indent = self._convert_line(line, indent_level)
            
            if converted_line:
                result.append(converted_line)
            
            indent_level = new_indent
        
        return '\n'.join(result)
    
    def _convert_line(self, line: str, current_indent: int) -> tuple[str, int]:
        """
        Convert a single line of AppleScript.
        
        Returns: (converted_line, new_indent_level)
        """
        original = line
        stripped = line.strip()
        
        # Skip empty lines and comments
        if not stripped or stripped.startswith('--') or stripped.startswith('#'):
            return (original, current_indent)
        
        # Handle multi-line comments
        if stripped.startswith('(*') or stripped.startswith('(*'):
            return (original, current_indent)
        
        # Convert tell blocks
        tell_match = re.match(r'tell\s+(?:application\s+)?["\']?([^"\']+)["\']?', stripped, re.IGNORECASE)
        if tell_match:
            app_name = tell_match.group(1)
            winscript_app = self._map_app_name(app_name)
            return (f'tell {winscript_app}', current_indent + 1)
        
        # Handle end tell
        if re.match(r'end\s+tell', stripped, re.IGNORECASE):
            return ('end tell', current_indent - 1)
        
        # Handle end repeat
        if re.match(r'end\s+repeat', stripped, re.IGNORECASE):
            return ('end repeat', current_indent - 1)
        
        # Handle end if
        if re.match(r'end\s+if', stripped, re.IGNORECASE):
            return ('end if', current_indent - 1)
        
        # Handle end try
        if re.match(r'end\s+try', stripped, re.IGNORECASE):
            return ('end try', current_indent - 1)
        
        # Handle on error / catch
        on_error_match = re.match(r'on\s+error\s*(\w+)?', stripped, re.IGNORECASE)
        if on_error_match:
            var_name = on_error_match.group(1) or 'err'
            return (f'catch {var_name}', current_indent)
        
        # Convert repeat blocks
        repeat_match = re.match(r'repeat\s+(.*)', stripped, re.IGNORECASE)
        if repeat_match:
            repeat_details = repeat_match.group(1).strip()
            return (self._convert_repeat(repeat_details), current_indent + 1)
        
        # Convert if statements
        if_match = re.match(r'if\s+(.+?)\s+then', stripped, re.IGNORECASE)
        if if_match:
            condition = self._convert_condition(if_match.group(1))
            return (f'if {condition} then', current_indent + 1)
        
        # Convert try blocks
        if re.match(r'try\s*$', stripped, re.IGNORECASE):
            return ('try', current_indent + 1)
        
        # Convert set statements
        set_match = re.match(r'set\s+(\w+)\s+to\s+(.+)', stripped, re.IGNORECASE)
        if set_match:
            var_name = set_match.group(1)
            value = self._convert_expression(set_match.group(2))
            return (f'set {var_name} to {value}', current_indent)
        
        # Convert copy statements
        copy_match = re.match(r'copy\s+(.+?)\s+to\s+(\w+)', stripped, re.IGNORECASE)
        if copy_match:
            value = self._convert_expression(copy_match.group(1))
            var_name = copy_match.group(2)
            return (f'set {var_name} to {value}', current_indent)
        
        # Convert return statements
        return_match = re.match(r'return\s+(.+)', stripped, re.IGNORECASE)
        if return_match:
            value = self._convert_expression(return_match.group(1))
            return (f'return {value}', current_indent)
        
        # Convert display dialog
        dialog_match = re.match(r'display\s+dialog\s+["\']([^"\']+)["\']', stripped, re.IGNORECASE)
        if dialog_match:
            message = dialog_match.group(1)
            return (f'# TODO: Implement dialog display: "{message}"', current_indent)
        
        # Convert delay
        delay_match = re.match(r'delay\s+(\d+\.?\d*)', stripped, re.IGNORECASE)
        if delay_match:
            seconds = delay_match.group(1)
            return (f'wait {seconds} seconds', current_indent)
        
        # Convert commands with "of" syntax
        of_match = re.match(r'(.+?)\s+of\s+(.+)', stripped, re.IGNORECASE)
        if of_match:
            prop = of_match.group(1)
            obj = of_match.group(2)
            converted = self._convert_property_access(prop, obj)
            return (converted, current_indent)
        
        # Convert generic commands
        converted = self._convert_command(stripped)
        return (converted, current_indent)
    
    def _convert_repeat(self, details: str) -> str:
        """Convert AppleScript repeat to WinScript repeat."""
        details = details.strip()
        
        # repeat n times
        times_match = re.match(r'(\d+)\s+times', details, re.IGNORECASE)
        if times_match:
            return f'repeat {times_match.group(1)} times'
        
        # repeat while condition
        while_match = re.match(r'while\s+(.+)', details, re.IGNORECASE)
        if while_match:
            condition = self._convert_condition(while_match.group(1))
            return f'repeat while {condition}'
        
        # repeat with var from start to end
        range_match = re.match(r'with\s+(\w+)\s+from\s+(\d+)\s+to\s+(\d+)', details, re.IGNORECASE)
        if range_match:
            var = range_match.group(1)
            start = range_match.group(2)
            end = range_match.group(3)
            return f'# TODO: Convert range loop: {var} from {start} to {end}'
        
        # repeat with var in list
        list_match = re.match(r'with\s+(\w+)\s+in\s+(.+)', details, re.IGNORECASE)
        if list_match:
            var = list_match.group(1)
            iterable = self._convert_expression(list_match.group(2))
            return f'repeat with {var} in {iterable}'
        
        # Simple repeat (infinite)
        if not details:
            return 'repeat while true'
        
        return f'# TODO: Convert repeat: {details}'
    
    def _convert_condition(self, condition: str) -> str:
        """Convert AppleScript condition to WinScript."""
        # AppleScript: is equal to, is not equal to, contains, etc.
        condition = condition.strip()
        
        # is equal to → is
        condition = re.sub(r'\bis\s+equal\s+to\b', 'is', condition, flags=re.IGNORECASE)
        
        # is not equal to → !=
        condition = re.sub(r'\bis\s+not\s+equal\s+to\b', '!=', condition, flags=re.IGNORECASE)
        
        # is greater than → >
        condition = re.sub(r'\bis\s+greater\s+than\b', '>', condition, flags=re.IGNORECASE)
        
        # is less than → <
        condition = re.sub(r'\bis\s+less\s+than\b', '<', condition, flags=re.IGNORECASE)
        
        # contains
        condition = re.sub(r'\bcontains\b', 'contains', condition, flags=re.IGNORECASE)
        
        # and → and
        condition = re.sub(r'\band\b', 'and', condition, flags=re.IGNORECASE)
        
        # or → or
        condition = re.sub(r'\bor\b', 'or', condition, flags=re.IGNORECASE)
        
        # not → not
        condition = re.sub(r'\bnot\b', 'not', condition, flags=re.IGNORECASE)
        
        return condition
    
    def _convert_expression(self, expr: str) -> str:
        """Convert an AppleScript expression to WinScript."""
        expr = expr.strip()
        
        # String concatenation in AppleScript uses &
        # WinScript also uses &, so we keep it
        
        # Quote handling - AppleScript uses "strings"
        # WinScript also uses "strings", so keep as-is
        
        # Convert "my" references
        expr = re.sub(r'\bmy\s+', '', expr, flags=re.IGNORECASE)
        
        # Convert POSIX paths
        if 'POSIX path' in expr:
            expr = re.sub(r'POSIX\s+path\s+of\s+', '', expr, flags=re.IGNORECASE)
        
        return expr
    
    def _convert_property_access(self, prop: str, obj: str) -> str:
        """Convert AppleScript property access to WinScript."""
        prop = prop.strip()
        obj = obj.strip()
        
        # Map property names
        if prop in self.property_mappings:
            prop = self.property_mappings[prop]
        
        # Convert object references
        obj = self._convert_expression(obj)
        
        return f'{prop} of {obj}'
    
    def _convert_command(self, command: str) -> str:
        """Convert AppleScript commands to WinScript."""
        command = command.strip()
        
        # Check for command mappings
        for apple_cmd, win_cmd in self.command_mappings.items():
            if command.lower().startswith(apple_cmd.lower()):
                return command.lower().replace(apple_cmd.lower(), win_cmd, 1)
        
        # Default: pass through with comment
        return f'{command}'
    
    def _map_app_name(self, app_name: str) -> str:
        """Map AppleScript application names to Windows equivalents."""
        app_name = app_name.strip().strip('"\'')
        
        # Check exact match
        if app_name in self.app_mappings:
            return self.app_mappings[app_name]
        
        # Check case-insensitive
        for apple_app, win_app in self.app_mappings.items():
            if app_name.lower() == apple_app.lower():
                return win_app
        
        # Return original with note
        return app_name


def convert(source: str) -> str:
    """
    Convenience function to convert AppleScript to WinScript.
    
    Args:
        source: AppleScript source code
    
    Returns:
        WinScript source code
    """
    converter = AppleScriptConverter()
    return converter.convert(source)


def convert_file(input_path: Path | str, output_path: Path | str | None = None) -> str:
    """
    Convert an AppleScript file to WinScript.
    
    Args:
        input_path: Path to AppleScript file (.scpt, .applescript, .sc)
        output_path: Optional output path. If None, returns the converted code.
    
    Returns:
        The converted WinScript code
    """
    input_path = Path(input_path)
    
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    
    source = input_path.read_text(encoding='utf-8')
    converted = convert(source)
    
    # Add header with conversion notice
    header = f'''-- Converted from AppleScript: {input_path.name}
-- Original: {input_path}
-- Conversion Date: Auto-generated
--
-- Note: Some AppleScript features may require manual adjustment
-- for Windows compatibility.

'''
    converted = header + converted
    
    if output_path:
        output_path = Path(output_path)
        output_path.write_text(converted, encoding='utf-8')
    
    return converted
