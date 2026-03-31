"""LLM integration layer for the career strategy pipeline."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv

load_dotenv()

DEFAULT_PROVIDER = "gemini"
DEFAULT_MODE = "auto"
DEFAULT_MODEL = "gemini-3.1-flash-lite-preview"
DEFAULT_GROUNDED_MODEL = "gemini-3-flash-preview"
DEFAULT_TIMEOUT_SECONDS = 20
DEFAULT_RESULT_MODE = "balanced"

TEXT_PROFILE_DEFAULTS: dict[str, dict[str, float]] = {
    "stable": {"temperature": 0.25, "top_p": 0.75},
    "balanced": {"temperature": 0.7, "top_p": 0.9},
    "creative": {"temperature": 1.0, "top_p": 0.95},
}

JSON_PROFILE_DEFAULTS: dict[str, dict[str, float]] = {
    "stable": {"temperature": 0.15, "top_p": 0.7},
    "balanced": {"temperature": 0.45, "top_p": 0.85},
    "creative": {"temperature": 0.7, "top_p": 0.92},
}


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
    result_mode: str


def _get_timeout_seconds() -> int:
    raw_timeout = os.getenv("LLM_TIMEOUT_SECONDS", os.getenv("GEMINI_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS)))
    try:
        return int(raw_timeout)
    except ValueError as exc:
        raise ValueError("LLM_TIMEOUT_SECONDS must be an integer.") from exc


def _normalize_result_mode(value: str | None) -> str:
    normalized = (value or "").strip().lower()
    if normalized in TEXT_PROFILE_DEFAULTS:
        return normalized
    return DEFAULT_RESULT_MODE


def get_llm_config() -> LLMConfig:
    return LLMConfig(
        provider=os.getenv("LLM_PROVIDER", DEFAULT_PROVIDER).strip().lower(),
        mode=os.getenv("LLM_MODE", DEFAULT_MODE).strip().lower(),
        model=os.getenv("LLM_MODEL", os.getenv("GEMINI_MODEL", DEFAULT_MODEL)).strip(),
        timeout_seconds=_get_timeout_seconds(),
        result_mode=_normalize_result_mode(os.getenv("LLM_RESULT_MODE", DEFAULT_RESULT_MODE)),
    )


class BaseLLMClient:
    def __init__(self, config: LLMConfig) -> None:
        self.config = config

    def is_available(self) -> bool:
        return False

    def generate(
        self,
        prompt: str,
        *,
        temperature: float | None = None,
        top_p: float | None = None,
        response_mime_type: str | None = None,
    ) -> str:
        raise LLMUnavailableError("LLM generation is disabled or unavailable.")


class DisabledLLMClient(BaseLLMClient):
    pass


class MockLLMClient(BaseLLMClient):
    def is_available(self) -> bool:
        return True

    def generate(
        self,
        prompt: str,
        *,
        temperature: float | None = None,
        top_p: float | None = None,
        response_mime_type: str | None = None,
    ) -> str:
        preview = " ".join(prompt.strip().split())[:180]
        config_preview = []
        if temperature is not None:
            config_preview.append(f"temperature={temperature}")
        if top_p is not None:
            config_preview.append(f"top_p={top_p}")
        if response_mime_type:
            config_preview.append(f"mime={response_mime_type}")
        prefix = ", ".join(config_preview) or "default-config"
        return f"[mock-llm:{prefix}] {preview}"


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

    def generate(
        self,
        prompt: str,
        *,
        temperature: float | None = None,
        top_p: float | None = None,
        response_mime_type: str | None = None,
    ) -> str:
        if not self._api_key or self._api_key == "your_gemini_api_key_here":
            raise LLMUnavailableError("Missing GEMINI_API_KEY.")

        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise LLMUnavailableError(
                "Missing dependency 'google-genai'. Install it in the active environment."
            ) from exc

        client = genai.Client(api_key=self._api_key)
        request_config = None
        if temperature is not None or top_p is not None or response_mime_type:
            request_config = types.GenerateContentConfig(
                temperature=temperature,
                top_p=top_p,
                response_mime_type=response_mime_type,
            )
        max_attempts = 3
        response = None
        last_error: Exception | None = None
        for attempt in range(1, max_attempts + 1):
            try:
                response = client.models.generate_content(
                    model=self.config.model,
                    contents=prompt,
                    config=request_config,
                )
                break
            except Exception as exc:
                last_error = exc
                status_code = getattr(exc, "status_code", None)
                message = str(exc).lower()
                retryable = status_code in {429, 500, 502, 503, 504} or any(
                    token in message for token in {"429", "500", "502", "503", "504", "rate limit", "unavailable"}
                )
                if retryable and attempt < max_attempts:
                    time.sleep(2 * attempt)
                    continue
                error_name = exc.__class__.__name__
                raise RuntimeError(
                    f"Gemini request failed. model={self.config.model}, "
                    f"timeout={self.config.timeout_seconds}s, "
                    f"error_type={error_name}, error={exc}"
                ) from exc

        if response is None:
            error_name = last_error.__class__.__name__ if last_error else "UnknownError"
            raise RuntimeError(
                f"Gemini request failed. model={self.config.model}, "
                f"timeout={self.config.timeout_seconds}s, "
                f"error_type={error_name}, error={last_error}"
            )

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
    return get_llm_client().generate(prompt, **_generation_kwargs(None, "text"))


def require_llm_client() -> BaseLLMClient:
    client = get_llm_client()
    if not client.is_available():
        config = get_llm_config()
        raise LLMUnavailableError(
            "LLM-powered pipeline requires a working provider. "
            f"provider={config.provider}, mode={config.mode}, model={config.model}"
        )
    return client


def _resolve_profile(profile: str | None) -> str:
    if profile:
        return _normalize_result_mode(profile)
    return get_llm_config().result_mode


def _generation_kwargs(profile: str | None, response_kind: str) -> dict[str, float | str]:
    resolved_profile = _resolve_profile(profile)
    defaults = TEXT_PROFILE_DEFAULTS if response_kind == "text" else JSON_PROFILE_DEFAULTS
    kwargs: dict[str, float | str] = {
        "temperature": defaults[resolved_profile]["temperature"],
        "top_p": defaults[resolved_profile]["top_p"],
    }
    if response_kind == "json":
        kwargs["response_mime_type"] = "application/json"
    return kwargs


def generate_optional_text(
    prompt: str,
    fallback: str | None = None,
    *,
    profile: str | None = None,
) -> str | None:
    try:
        return get_llm_client().generate(prompt, **_generation_kwargs(profile, "text"))
    except Exception:
        return fallback


def generate_text_strict(
    prompt: str,
    *,
    profile: str | None = None,
) -> str:
    client = require_llm_client()
    return client.generate(prompt, **_generation_kwargs(profile, "text"))


def _parse_first_json_object(text: str) -> dict[str, Any]:
    decoder = json.JSONDecoder()
    for start_index, char in enumerate(text):
        if char != "{":
            continue
        try:
            payload, _ = decoder.raw_decode(text[start_index:])
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    raise ValueError("No JSON object found in model response.")


def generate_optional_json(
    prompt: str,
    fallback: Any = None,
    *,
    profile: str | None = None,
) -> Any:
    try:
        raw_text = get_llm_client().generate(
            prompt,
            **_generation_kwargs(profile, "json"),
        )
        return _parse_first_json_object(raw_text)
    except Exception:
        return fallback


def generate_json_strict(
    prompt: str,
    *,
    profile: str | None = None,
) -> dict[str, Any]:
    client = require_llm_client()
    raw_text = client.generate(
        prompt,
        **_generation_kwargs(profile, "json"),
    )
    return _parse_first_json_object(raw_text)


def generate_multimodal_json_strict(
    prompt: str,
    *,
    parts: list[Any],
    profile: str | None = None,
) -> dict[str, Any]:
    client = require_llm_client()
    if not isinstance(client, GeminiLLMClient):
        raise LLMUnavailableError("Multimodal scanning requires the Gemini provider.")

    from google import genai
    from google.genai import types

    generation_kwargs = _generation_kwargs(profile, "json")
    multimodal_client = genai.Client(api_key=client._api_key)
    response = multimodal_client.models.generate_content(
        model=client.config.model,
        contents=types.UserContent(
            parts=[
                types.Part.from_text(text=prompt),
                *parts,
            ]
        ),
        config=types.GenerateContentConfig(
            temperature=float(generation_kwargs["temperature"]),
            top_p=float(generation_kwargs["top_p"]),
            response_mime_type=str(generation_kwargs["response_mime_type"]),
        ),
    )
    return _parse_first_json_object(getattr(response, "text", "") or "")


def _get_grounded_model() -> str:
    return os.getenv("GEMINI_GROUNDED_MODEL", DEFAULT_GROUNDED_MODEL).strip() or DEFAULT_GROUNDED_MODEL


def generate_optional_grounded_json(
    prompt: str,
    fallback: Any = None,
    *,
    profile: str | None = None,
) -> Any:
    try:
        client = get_llm_client()
        if not isinstance(client, GeminiLLMClient) or not client.is_available():
            return fallback

        from google import genai
        from google.genai import types

        generation_kwargs = _generation_kwargs(profile, "json")
        grounded_client = genai.Client(api_key=client._api_key)
        response = grounded_client.models.generate_content(
            model=_get_grounded_model(),
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=float(generation_kwargs["temperature"]),
                top_p=float(generation_kwargs["top_p"]),
                response_mime_type=str(generation_kwargs["response_mime_type"]),
                tools=[types.Tool(google_search=types.GoogleSearch())],
            ),
        )
        payload = _parse_first_json_object(getattr(response, "text", "") or "")

        candidate = response.candidates[0] if getattr(response, "candidates", None) else None
        grounding_metadata = getattr(candidate, "grounding_metadata", None)
        web_search_queries = list(getattr(grounding_metadata, "web_search_queries", []) or [])
        grounding_chunks = list(getattr(grounding_metadata, "grounding_chunks", []) or [])

        grounding_sources: list[dict[str, str]] = []
        seen_uris: set[str] = set()
        for chunk in grounding_chunks:
            web = getattr(chunk, "web", None)
            uri = str(getattr(web, "uri", "") or "").strip()
            title = str(getattr(web, "title", "") or "").strip()
            if not uri or uri in seen_uris:
                continue
            seen_uris.add(uri)
            grounding_sources.append({"title": title, "uri": uri})

        if isinstance(payload, dict):
            payload["_grounding"] = {
                "model": _get_grounded_model(),
                "queries": [str(item).strip() for item in web_search_queries if str(item).strip()],
                "sources": grounding_sources,
            }
            return payload
        return fallback
    except Exception:
        return fallback


def generate_grounded_json_strict(
    prompt: str,
    *,
    profile: str | None = None,
) -> dict[str, Any]:
    client = require_llm_client()
    if not isinstance(client, GeminiLLMClient):
        raise LLMUnavailableError("Grounded search requires the Gemini provider.")

    from google import genai
    from google.genai import types

    generation_kwargs = _generation_kwargs(profile, "json")
    grounded_client = genai.Client(api_key=client._api_key)
    response = grounded_client.models.generate_content(
        model=_get_grounded_model(),
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=float(generation_kwargs["temperature"]),
            top_p=float(generation_kwargs["top_p"]),
            response_mime_type=str(generation_kwargs["response_mime_type"]),
            tools=[types.Tool(google_search=types.GoogleSearch())],
        ),
    )
    payload = _parse_first_json_object(getattr(response, "text", "") or "")

    candidate = response.candidates[0] if getattr(response, "candidates", None) else None
    grounding_metadata = getattr(candidate, "grounding_metadata", None)
    web_search_queries = list(getattr(grounding_metadata, "web_search_queries", []) or [])
    grounding_chunks = list(getattr(grounding_metadata, "grounding_chunks", []) or [])

    grounding_sources: list[dict[str, str]] = []
    seen_uris: set[str] = set()
    for chunk in grounding_chunks:
        web = getattr(chunk, "web", None)
        uri = str(getattr(web, "uri", "") or "").strip()
        title = str(getattr(web, "title", "") or "").strip()
        if not uri or uri in seen_uris:
            continue
        seen_uris.add(uri)
        grounding_sources.append({"title": title, "uri": uri})

    payload["_grounding"] = {
        "model": _get_grounded_model(),
        "queries": [str(item).strip() for item in web_search_queries if str(item).strip()],
        "sources": grounding_sources,
    }
    return payload


def llm_status() -> dict[str, Any]:
    config = get_llm_config()
    client = get_llm_client()
    return {
        "provider": config.provider,
        "mode": config.mode,
        "model": config.model,
        "result_mode": config.result_mode,
        "available": client.is_available(),
        "client": client.__class__.__name__,
    }
