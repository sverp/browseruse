"""
Input Controller for Computer Use (Mouse & Keyboard automation via X11).
Supports relative clicking in focused windows, scrolling, and keyboard typing.
"""

import time
import subprocess
from typing import Optional, List
from Xlib import X, display, XK
from Xlib.ext import xtest
from backend_adapter import I3Adapter

disp = display.Display()
adapter = I3Adapter()

# Common key mappings for easy naming
KEY_MAP = {
    "enter": "Return",
    "return": "Return",
    "tab": "Tab",
    "space": "space",
    "backspace": "BackSpace",
    "delete": "Delete",
    "escape": "Escape",
    "esc": "Escape",
    "up": "Up",
    "down": "Down",
    "left": "Left",
    "right": "Right",
    "ctrl": "Control_L",
    "alt": "Alt_L",
    "shift": "Shift_L",
    "super": "Super_L",
    "pagedown": "Page_Down",
    "pageup": "Page_Up",
}


def _get_keycode(key: str) -> int:
    """Translates key name or character to an X11 keycode."""
    mapped = KEY_MAP.get(key.lower(), key)
    keysym = XK.string_to_keysym(mapped)
    if keysym == 0:
        # Try single char keysym (e.g., 'a', 'b', '1')
        keysym = ord(key)
    keycode = disp.keysym_to_keycode(keysym)
    if keycode == 0:
        raise ValueError(f"Unknown key: {key}")
    return keycode


def click_focused(rel_x: int, rel_y: int, button: int = 1, double: bool = False) -> None:
    """
    Clicks at (rel_x, rel_y) inside the currently focused window.

    :param rel_x: X offset from the top-left of the focused window.
    :param rel_y: Y offset from the top-left of the focused window.
    :param button: 1 = Left click, 2 = Middle, 3 = Right click.
    :param double: If True, performs a double-click.
    """
    focused = adapter.get_focused()
    if not focused:
        raise RuntimeError("No focused window found.")

    abs_x = focused.rect.x + rel_x
    abs_y = focused.rect.y + rel_y

    # Move cursor
    xtest.fake_input(disp, X.MotionNotify, x=abs_x, y=abs_y)
    disp.sync()
    time.sleep(0.02)

    # Click
    clicks = 2 if double else 1
    for _ in range(clicks):
        xtest.fake_input(disp, X.ButtonPress, button)
        disp.sync()
        time.sleep(0.02)
        xtest.fake_input(disp, X.ButtonRelease, button)
        disp.sync()
        if clicks > 1:
            time.sleep(0.05)


def scroll(direction: str = "down", amount: int = 5) -> None:
    """
    Scrolls the mouse wheel.

    :param direction: 'down' (Button 5) or 'up' (Button 4).
    :param amount: Number of scroll ticks.
    """
    btn = 5 if direction.lower() == "down" else 4
    for _ in range(amount):
        xtest.fake_input(disp, X.ButtonPress, btn)
        disp.sync()
        xtest.fake_input(disp, X.ButtonRelease, btn)
        disp.sync()
        time.sleep(0.02)


def press_key(key: str) -> None:
    """Presses and releases a single key (e.g. 'Return', 'BackSpace', 'Tab')."""
    kc = _get_keycode(key)
    xtest.fake_input(disp, X.KeyPress, kc)
    disp.sync()
    time.sleep(0.02)
    xtest.fake_input(disp, X.KeyRelease, kc)
    disp.sync()


def hotkey(*keys: str) -> None:
    """
    Executes a key combination in order (e.g. hotkey('ctrl', 'l')).
    """
    keycodes = [_get_keycode(k) for k in keys]
    for kc in keycodes:
        xtest.fake_input(disp, X.KeyPress, kc)
    disp.sync()
    time.sleep(0.02)
    for kc in reversed(keycodes):
        xtest.fake_input(disp, X.KeyRelease, kc)
    disp.sync()


def type_text(text: str, via_paste: bool = True) -> None:
    """
    Types text into the focused window.

    :param text: Text string to type.
    :param via_paste: If True (recommended), uses clipboard paste for instant,
                      reliable typing of symbols and unicode without layout issues.
    """
    if via_paste:
        subprocess.run(["xclip", "-selection", "clipboard"], input=text.encode("utf-8"), check=True)
        time.sleep(0.02)
        hotkey("ctrl", "v")
    else:
        for char in text:
            if char == " ":
                press_key("space")
            elif char == "\n":
                press_key("Return")
            else:
                try:
                    kc = _get_keycode(char)
                    xtest.fake_input(disp, X.KeyPress, kc)
                    disp.sync()
                    xtest.fake_input(disp, X.KeyRelease, kc)
                    disp.sync()
                    time.sleep(0.01)
                except ValueError:
                    # Fallback to paste for unrecognized characters
                    subprocess.run(["xclip", "-selection", "clipboard"], input=char.encode("utf-8"), check=True)
                    hotkey("ctrl", "v")
