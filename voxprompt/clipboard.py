"""Copy-to-clipboard utility."""

import pyperclip


def copy_to_clipboard(text: str) -> bool:
    """Copy text to system clipboard. Returns True on success, False on failure."""
    try:
        pyperclip.copy(text)
        return True
    except pyperclip.PyperclipException:
        return False
