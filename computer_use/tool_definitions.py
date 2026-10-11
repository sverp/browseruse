"""
Agent Tool Declarations and Dispatcher for Gemma 4.
Maps Gemma 4 function declarations to browser_tools implementations.
"""

from typing import Dict, Any, Callable
import browser_tools

GEMMA_TOOL_DECLARATIONS = [
    {
        "function_declarations": [
            {
                "name": "navigate",
                "description": "Navigate the browser to a URL (e.g. 'https://www.instagram.com', 'https://mail.google.com').",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "Full destination URL.",
                        }
                    },
                    "required": ["url"],
                },
            },
            {
                "name": "click",
                "description": "Click an element matching a CSS, text, or aria selector (e.g. 'svg[aria-label=\"Like\"]', 'button:has-text(\"Follow\")').",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "selector": {
                            "type": "string",
                            "description": "Selector string matching the element to click.",
                        }
                    },
                    "required": ["selector"],
                },
            },
            {
                "name": "double_click",
                "description": "Double click an element on screen (useful to like photos/memes on Instagram).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "selector": {
                            "type": "string",
                            "description": "Selector of the element to double click.",
                        }
                    },
                    "required": ["selector"],
                },
            },
            {
                "name": "type_text",
                "description": "Type text into an input box or comment field and optionally press Enter.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "selector": {
                            "type": "string",
                            "description": "Selector of the input element.",
                        },
                        "text": {
                            "type": "string",
                            "description": "Text string to enter.",
                        },
                        "press_enter": {
                            "type": "boolean",
                            "description": "Press Enter key after typing.",
                        },
                    },
                    "required": ["selector", "text"],
                },
            },
            {
                "name": "press_key",
                "description": "Press a keyboard key (e.g. 'PageDown', 'ArrowDown', 'j', 'Escape').",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "key": {
                            "type": "string",
                            "description": "Key name to press.",
                        }
                    },
                    "required": ["key"],
                },
            },
            {
                "name": "scroll",
                "description": "Scroll the feed or page vertically by delta_y pixels (positive = scroll down, negative = scroll up).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "delta_y": {
                            "type": "integer",
                            "description": "Pixels to scroll down (e.g. 500, 800) or up (-500).",
                        }
                    },
                    "required": ["delta_y"],
                },
            },
            {
                "name": "wait",
                "description": "Wait / pause execution for a given number of seconds (e.g. to let dynamic feed content load).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "seconds": {
                            "type": "number",
                            "description": "Seconds to wait (e.g. 2.0).",
                        }
                    },
                    "required": ["seconds"],
                },
            },
            {
                "name": "capture_screenshot",
                "description": "Capture screenshot of current screen for visual verification and save to output_path.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "output_path": {
                            "type": "string",
                            "description": "Destination file path.",
                        }
                    },
                    "required": ["output_path"],
                },
            },
            {
                "name": "get_page_summary",
                "description": "Get current page URL, title, and preview snippet of visible text content.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
            {
                "name": "send_email",
                "description": "Compose and send an email via Gmail using the saved logged-in session.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "recipient": {
                            "type": "string",
                            "description": "Destination email address (e.g. 'friend@example.com').",
                        },
                        "subject": {
                            "type": "string",
                            "description": "Subject line of the email.",
                        },
                        "body": {
                            "type": "string",
                            "description": "Text body of the email.",
                        },
                    },
                    "required": ["recipient", "subject", "body"],
                },
            },
        ]
    }
]

TOOL_REGISTRY: Dict[str, Callable[..., Dict[str, Any]]] = {
    "navigate": browser_tools.navigate,
    "click": browser_tools.click,
    "double_click": browser_tools.double_click,
    "type_text": browser_tools.type_text,
    "press_key": browser_tools.press_key,
    "scroll": browser_tools.scroll,
    "wait": browser_tools.wait,
    "capture_screenshot": browser_tools.capture_screenshot,
    "get_page_summary": browser_tools.get_page_summary,
    "send_email": browser_tools.send_email,
}


def execute_tool_call(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Executes a tool call requested by Gemma 4 and returns the structured result."""
    func = TOOL_REGISTRY.get(name)
    if not func:
        return {"status": "error", "message": f"Unknown tool: '{name}'"}
    try:
        print(f"\n[Tool Execution] Calling {name}({args})")
        result = func(**args)
        print(f"[Tool Execution] Result: {result}")
        return result
    except Exception as e:
        err_msg = str(e)
        print(f"[Tool Execution Error] {err_msg}")
        return {"status": "error", "message": err_msg}
