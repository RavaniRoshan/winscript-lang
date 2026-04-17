-- test_chrome.ws
-- WinScript sample: Open Chrome, navigate to GitHub, get page title

try
    tell Chrome
        navigate to "https://github.com"
        wait until loaded
        wait 2 seconds

        set page_title to title of active_tab
        return page_title
    end tell
catch error_message
    return "Failed: " & error_message
end try
