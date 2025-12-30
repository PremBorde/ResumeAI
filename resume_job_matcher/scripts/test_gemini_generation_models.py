from __future__ import annotations

import httpx

import os
import sys


# Allow running this script directly from repo root on Windows without installing as a package.
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from app.utils.config import settings  # noqa: E402


def _short(text: str, n: int = 260) -> str:
    t = " ".join((text or "").split())
    return t if len(t) <= n else t[:n] + "..."


def main() -> None:
    if not settings.gemini_api_key:
        raise SystemExit("GEMINI_API_KEY is not set.")

    models = [
        "gemini-2.0-flash-lite",
        "gemini-2.0-flash-lite-001",
        "gemini-2.0-flash-001",
        "gemini-2.0-flash",
        "gemini-2.5-flash-lite",
        "gemini-2.5-flash",
        "gemini-2.5-pro",
    ]

    body = {"contents": [{"parts": [{"text": "hello"}]}]}

    print("Testing Gemini generateContent across models")
    print(f"Base URL: {settings.gemini_base_url}")
    print(f"Configured model: {settings.gemini_generation_model}")
    print()

    with httpx.Client(timeout=20.0) as client:
        for model in models:
            url = f"{settings.gemini_base_url}/v1/models/{model}:generateContent"
            resp = client.post(url, params={"key": settings.gemini_api_key}, json=body)
            print(f"- {model}: {resp.status_code} {_short(resp.text)}")

    print()
    print("Notes:")
    print("- If all models return 429 with 'limit: 0', your project has no free-tier generation quota.")
    print("- If ANY model returns 200, set GEMINI_GENERATION_MODEL to that model and restart the server.")


if __name__ == "__main__":
    main()


