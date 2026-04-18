-- hello_windows.ws
-- Basic demo: opens Notepad, types a message, reads it back

try
    tell Chrome
        navigate to "https://winscript.dev"
        wait until loaded
        return "WinScript is running. Page title: " & title of active tab
    end tell
catch err
    return "Demo error (Chrome may not be running): " & err
end try
