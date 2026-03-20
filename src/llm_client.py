import os
from typing import Any

from dotenv import load_dotenv

load_dotenv()

DEFAULT_MODEL = "gemini-3.1-flash-lite-preview"
DEFAULT_TIMEOUT_SECONDS = 20


def _get_model_name() -> str:
    return os.getenv("GEMINI_MODEL", DEFAULT_MODEL)


def _get_timeout_seconds() -> int:
    raw_timeout = os.getenv("GEMINI_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS))
    try:
        return int(raw_timeout)
    except ValueError as exc:
        raise ValueError("GEMINI_TIMEOUT_SECONDS must be an integer.") from exc


def _get_client() -> Any:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_gemini_api_key_here":
        raise ValueError(
        )

    try:
        from google import genai
    except ImportError as exc:
        raise ImportError(
            "Missing dependency 'google-genai'. Install it in your active environment."
        ) from exc

    return genai.Client(api_key=api_key)


def generate_text(prompt: str) -> str:
    model_name = _get_model_name()
    timeout_seconds = _get_timeout_seconds()
    client = _get_client()

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
        )
    except Exception as exc:
        error_name = exc.__class__.__name__
        raise RuntimeError(
            f"Gemini request failed. model={model_name}, timeout={timeout_seconds}s, "
            f"error_type={error_name}, error={exc}"
        ) from exc

    text = getattr(response, "text", None)
    if not text:
        raise RuntimeError(
            f"Gemini returned an empty response for model={model_name}."
        )

    return text
