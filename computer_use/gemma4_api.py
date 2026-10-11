import base64
import os
import requests
from typing import Any

API_KEY = os.getenv("GEMINI_API_KEY", "")
MODEL = "gemma-4-26b-a4b-it"
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"


def ask_gemma4(prompt: str, image_path: str | None = None) -> str:
    parts: list[dict[str, Any]] = [{"text": prompt}]

    if image_path:
        with open(image_path, "rb") as f:
            b64_data = base64.b64encode(f.read()).decode()
        parts.append({
            "inline_data": {
                "mime_type": "image/png",
                "data": b64_data,
            }
        })

    resp = requests.post(
        URL,
        headers={"Content-Type": "application/json", "X-goog-api-key": API_KEY},
        json={"contents": [{"parts": parts}]},
    )
    resp.raise_for_status()

    parts_out = resp.json()["candidates"][0]["content"]["parts"]
    return [p["text"] for p in parts_out if not p.get("thought")][-1].strip()


if __name__ == "__main__":
    print("AI explanation:")
    print(ask_gemma4("Explain how AI works in a few words"))

    # 2. Image
    sample_img = os.path.join(os.path.dirname(__file__), "sample.png")
    if os.path.exists(sample_img):
        print("\nImage analysis:")
        print(ask_gemma4("What UI element is in this image?", sample_img))
