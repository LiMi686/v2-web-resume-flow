"""Optional LLM integration layer with graceful fallback."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv

load_dotenv()

DEFAULT_PROVIDER = "gemini"
DEFAULT_MODE = "auto"
DEFAULT_MODEL = "gemini-3.1-flash-lite-preview"
DEFAULT_TIMEOUT_SECONDS = 20


def refresh_llm_environment() -> None:
    """Reload environment variables so interactive CLI changes to .env take effect."""
    load_dotenv(override=True)


class LLMUnavailableError(RuntimeError):
    """Raised when a requested provider cannot be used."""


@dataclass(frozen=True, slots=True)
class LLMConfig:
    provider: str
    mode: str
    model: str
    timeout_seconds: int


def _get_timeout_seconds() -> int:
    raw_timeout = os.getenv("LLM_TIMEOUT_SECONDS", os.getenv("GEMINI_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS)))
    try:
        return int(raw_timeout)
    except ValueError as exc:
        raise ValueError("LLM_TIMEOUT_SECONDS must be an integer.") from exc


def get_llm_config() -> LLMConfig:
    return LLMConfig(
        provider=os.getenv("LLM_PROVIDER", DEFAULT_PROVIDER).strip().lower(),
        mode=os.getenv("LLM_MODE", DEFAULT_MODE).strip().lower(),
        model=os.getenv("LLM_MODEL", os.getenv("GEMINI_MODEL", DEFAULT_MODEL)).strip(),
        timeout_seconds=_get_timeout_seconds(),
    )


class BaseLLMClient:
    def __init__(self, config: LLMConfig) -> None:
        self.config = config

    def is_available(self) -> bool:
        return False

    def generate(self, prompt: str) -> str:
        raise LLMUnavailableError("LLM generation is disabled or unavailable.")


class DisabledLLMClient(BaseLLMClient):
    pass


class MockLLMClient(BaseLLMClient):
    def is_available(self) -> bool:
        return True

    def generate(self, prompt: str) -> str:
        preview = " ".join(prompt.strip().split())[:180]
        return f"[mock-llm] {preview}"


class GeminiLLMClient(BaseLLMClient):
    def __init__(self, config: LLMConfig) -> None:
        super().__init__(config)
        self._api_key = os.getenv("GEMINI_API_KEY", "").strip()

    def is_available(self) -> bool:
        if not self._api_key or self._api_key == "your_gemini_api_key_here":
            return False
        try:
            from google import genai  # noqa: F401
        except ImportError:
            return False
        return True

    def generate(self, prompt: str) -> str:
        if not self._api_key or self._api_key == "your_gemini_api_key_here":
            raise LLMUnavailableError("Missing GEMINI_API_KEY.")

        try:
            from google import genai
        except ImportError as exc:
            raise LLMUnavailableError(
                "Missing dependency 'google-genai'. Install it in the active environment."
            ) from exc

        client = genai.Client(api_key=self._api_key)
        try:
            response = client.models.generate_content(
                model=self.config.model,
                contents=prompt,
            )
        except Exception as exc:
            error_name = exc.__class__.__name__
            raise RuntimeError(
                f"Gemini request failed. model={self.config.model}, "
                f"timeout={self.config.timeout_seconds}s, "
                f"error_type={error_name}, error={exc}"
            ) from exc

        text = getattr(response, "text", None)
        if not text:
            raise RuntimeError(
                f"Gemini returned an empty response for model={self.config.model}."
            )

        return text


def get_llm_client() -> BaseLLMClient:
    config = get_llm_config()

    if config.mode == "disabled":
        return DisabledLLMClient(config)
    if config.mode == "mock":
        return MockLLMClient(config)

    if config.provider == "gemini":
        client = GeminiLLMClient(config)
        if client.is_available():
            return client
        if config.mode == "auto":
            return DisabledLLMClient(config)
        raise LLMUnavailableError("Gemini provider requested but unavailable.")

    if config.mode == "auto":
        return DisabledLLMClient(config)

    raise LLMUnavailableError(f"Unsupported LLM provider: {config.provider}")


def generate_text(prompt: str) -> str:
    return get_llm_client().generate(prompt)


def generate_optional_text(prompt: str, fallback: str | None = None) -> str | None:
    try:
        return get_llm_client().generate(prompt)
    except Exception:
        return fallback


def llm_status() -> dict[str, Any]:
    config = get_llm_config()
    client = get_llm_client()
    return {
        "provider": config.provider,
        "mode": config.mode,
        "model": config.model,
        "available": client.is_available(),
        "client": client.__class__.__name__,
    }
