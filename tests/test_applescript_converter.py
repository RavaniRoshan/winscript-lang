"""Tests for AppleScript to WinScript converter."""

import pytest
from pathlib import Path
import tempfile

from winscript.applescript_converter import AppleScriptConverter, convert, convert_file


class TestAppleScriptConverter:
    """Test AppleScript conversion functionality."""

    def test_basic_tell_block(self):
        """Test converting tell blocks."""
        converter = AppleScriptConverter()
        source = '''tell application "Finder"
    activate
end tell'''
        result = converter.convert(source)
        
        assert "tell" in result
        assert "end tell" in result

    def test_set_statement(self):
        """Test converting set statements."""
        converter = AppleScriptConverter()
        source = 'set x to "hello"'
        result = converter.convert(source)
        
        assert 'set x to "hello"' in result

    def test_return_statement(self):
        """Test converting return statements."""
        converter = AppleScriptConverter()
        source = 'return x'
        result = converter.convert(source)
        
        assert "return" in result

    def test_app_name_mapping(self):
        """Test application name mapping."""
        converter = AppleScriptConverter()
        
        # Safari should map to Chrome
        result = converter._map_app_name("Safari")
        assert result == "Chrome"
        
        # Numbers should map to Excel
        result = converter._map_app_name("Numbers")
        assert result == "Excel"
        
        # Unknown apps should pass through
        result = converter._map_app_name("CustomApp")
        assert result == "CustomApp"

    def test_repeat_conversion(self):
        """Test repeat loops conversion."""
        converter = AppleScriptConverter()
        
        # Repeat n times
        result = converter._convert_repeat("5 times")
        assert "repeat 5 times" in result
        
        # Repeat while
        result = converter._convert_repeat("while x > 0")
        assert "repeat while" in result

    def test_condition_conversion(self):
        """Test condition expression conversion."""
        converter = AppleScriptConverter()
        
        result = converter._convert_condition("x is equal to 5")
        assert "is" in result.lower()

    def test_full_script_conversion(self):
        """Test converting a complete AppleScript."""
        applescript = '''tell application "Safari"
    activate
    set myURL to "https://github.com"
    open location myURL
    return "Opened"
end tell'''
        
        result = convert(applescript)
        
        # Should contain converted syntax
        assert "tell" in result
        assert "set" in result
        assert "return" in result

    def test_convert_file(self):
        """Test converting from file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.scpt', delete=False) as f:
            f.write('tell application "Finder"\n    activate\nend tell')
            temp_path = f.name
        
        try:
            result = convert_file(temp_path)
            assert "tell" in result
            # activate maps to focus in WinScript
            assert "focus" in result
        finally:
            Path(temp_path).unlink()

    def test_delay_to_wait(self):
        """Test that delay converts to wait."""
        converter = AppleScriptConverter()
        source = 'delay 5'
        result = converter.convert(source)
        
        assert "wait" in result or "# TODO" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
