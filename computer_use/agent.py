"""
Autonomous Gemma 4 Continuous Browser Agent.
Runs an indefinite reactive tool-use loop:
- Continuously decides the next action (navigate, scroll, click/like, inspect, wait).
- Persists context across steps with automatic sliding window to avoid token overflows.
- Automatically handles tasks like doom-scrolling feeds (e.g. Instagram/Twitter), reacting to posts, and ignoring unwanted content.
"""

import os
import time
import requests
from typing import Dict, Any, List
from tool_definitions import GEMMA_TOOL_DECLARATIONS, execute_tool_call
import browser_tools

API_KEY = os.getenv("GEMINI_API_KEY", "")
MODEL = "gemma-4-26b-a4b-it"
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"

SYSTEM_INSTRUCTION = (
    "You are an autonomous web-browsing agent that performs tasks via Playwright browser tools. "
    "REGIONAL INSTRUCTION (INDIA): The user is located in India. Always use Indian regional services, domains, and settings (e.g. .in, google.co.in, amazon.in, en-IN, currency ₹ INR). "
    "NEVER navigate to US, EU, or other foreign regional URLs/domains (e.g. avoid .us, .co.uk, .de, .fr, .eu, or ?gl=us query parameters). "
    "1. When sending an email to a recipient (e.g. 'write a mail to user@gmail.com'): "
    "   - Always use the dedicated 'send_email' tool or compose from the currently active/logged-in account. "
    "   - NEVER try to switch accounts, log out, or sign in as the recipient address! The recipient is who receives the mail, not who sends it. "
    "   - As soon as the email is sent, STOP immediately! Inform the user that the email has been sent and DO NOT call any more tools. "
    "2. If browsing Instagram/social feeds: navigate to the site, inspect what's on screen (use get_page_summary), scroll through the feed, "
    "   identify memes/interesting posts, react (e.g., click Like or double click the post), and skip/scroll past reels or ads. "
    "3. STOPPING RULE: When a task is completed (email sent, page inspected, question answered), DO NOT call any more tools. "
    "   Provide a final summary message to the user and stop. Never make unnecessary or random tool calls once the goal is accomplished."
)


class GemmaContinuousAgent:
    """Continuous agent loop driven by Gemma 4 tool calling."""

    def __init__(self, max_history_turns: int = 12, headless: bool = True):
        self.max_history_turns = max_history_turns
        self.history: List[Dict[str, Any]] = []
        browser_tools.browser_tool.headless = headless

    def _call_model(self, emit_callback=None) -> Dict[str, Any]:
        """Dispatches current conversation state to Gemma 4 API with automatic 429 retry backoff."""
        payload = {
            "system_instruction": {
                "parts": [{"text": SYSTEM_INSTRUCTION}],
            },
            "contents": self.history,
            "tools": GEMMA_TOOL_DECLARATIONS,
        }

        max_retries = 5
        base_delay = 3.0

        for attempt in range(max_retries):
            try:
                resp = requests.post(
                    URL,
                    headers={"Content-Type": "application/json", "X-goog-api-key": API_KEY},
                    json=payload,
                    timeout=50,
                )

                if resp.status_code in (429, 500, 502, 503, 504):
                    wait_time = base_delay * (2 ** attempt)
                    reason = "Rate limit (429)" if resp.status_code == 429 else f"Server error ({resp.status_code})"
                    msg = f"{reason} from API. Retrying in {wait_time:.1f}s (attempt {attempt + 1}/{max_retries})..."
                    print(f"[API Retry] {msg}")
                    if emit_callback:
                        emit_callback("API Retry", msg)
                    time.sleep(wait_time)
                    continue

                resp.raise_for_status()
                return resp.json()
            except requests.exceptions.RequestException as req_err:
                if attempt < max_retries - 1:
                    wait_time = base_delay * (2 ** attempt)
                    msg = f"Network/API error ({req_err}). Retrying in {wait_time:.1f}s (attempt {attempt + 1}/{max_retries})..."
                    print(f"[API Retry] {msg}")
                    if emit_callback:
                        emit_callback("API Retry", msg)
                    time.sleep(wait_time)
                    continue
                raise req_err

        resp.raise_for_status()
        return resp.json()

    def _trim_history(self) -> None:
        """Keeps initial goal and sliding window of recent steps to prevent context explosion."""
        if len(self.history) > self.max_history_turns * 2 + 1:
            initial_prompt = self.history[0]
            self.history = [initial_prompt] + self.history[-(self.max_history_turns * 2):]

    def run(self, user_goal: str, loop_steps: int = 20, log_callback=None) -> None:
        """
        Runs the continuous agent loop.
        :param user_goal: The user command (e.g., 'Doom scroll instagram, see memes, ignore reels, like memes').
        :param loop_steps: Total continuous actions to take before pausing for user input.
        :param log_callback: Optional callable(type, text) for streaming logs to UI.
        """
        def emit(log_type: str, text: str):
            print(f"[{log_type}] {text}")
            if log_callback:
                try:
                    log_callback(log_type, text)
                except Exception:
                    pass

        emit("Goal", user_goal)

        self.history = [
            {
                "role": "user",
                "parts": [{"text": user_goal}],
            }
        ]

        step = 0
        try:
            while step < loop_steps:
                step += 1
                print(f"\n>>> [Loop Step {step}/{loop_steps}] <<<")
                self._trim_history()

                response_json = self._call_model(emit_callback=emit)
                candidate = response_json.get("candidates", [{}])[0]
                content = candidate.get("content", {})
                parts = content.get("parts", [])

                self.history.append({"role": "model", "parts": parts})

                tool_calls = []
                for part in parts:
                    if part.get("thought"):
                        emit("Thought", part["text"].strip())
                    elif "text" in part:
                        emit("Agent Message", part["text"].strip())
                    elif "functionCall" in part:
                        tool_calls.append(part["functionCall"])

                if not tool_calls:
                    is_continuous_feed = any(kw in user_goal.lower() for kw in ["doom scroll", "doomscroll", "keep scrolling", "endless scroll", "browse continuously"])
                    agent_text = " ".join(part.get("text", "") for part in parts).lower()
                    done_signals = ["sent", "completed", "finished", "done", "success", "here is", "fare is", "receipt", "task complete"]

                    if not is_continuous_feed or any(sig in agent_text for sig in done_signals):
                        emit("Status", "Task completed successfully.")
                        break

                    emit("Info", "Continuous feed browsing: continuing next step...")
                    self.history.append({
                        "role": "user",
                        "parts": [{"text": "Continue browsing: inspect screen, scroll down, interact, or react as instructed."}],
                    })
                    time.sleep(1)
                    continue

                tool_responses = []
                for call in tool_calls:
                    func_name = call["name"]
                    args = call.get("args", {})
                    emit("Tool Call", f"{func_name}({args})")
                    result = execute_tool_call(func_name, args)
                    emit("Tool Result", str(result))
                    tool_responses.append({
                        "functionResponse": {
                            "name": func_name,
                            "response": result,
                        }
                    })

                self.history.append({"role": "user", "parts": tool_responses})
                time.sleep(1.5)

        except KeyboardInterrupt:
            emit("Status", "Stopped by user interrupt.")
        finally:
            emit("Status", "Session completed.")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        task = " ".join(sys.argv[1:])
    else:
        print("Enter a task for the autonomous agent (or press Enter for default Instagram doom-scroll):")
        user_input = input("> ").strip()
        task = user_input or (
            "Doom scroll Instagram: Go to https://www.instagram.com. "
            "Inspect the feed, scroll down continuously to see the memes, ignore reels, "
            "and react/like the memes."
        )

    agent = GemmaContinuousAgent(headless=True)
    agent.run(task, loop_steps=15)
