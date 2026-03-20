"""Policy analysis stage for the career pipeline."""

from __future__ import annotations

from typing import Any

try:
    from .llm_client import generate_text
except ImportError:
    from llm_client import generate_text


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return [str(value).strip()]


def _safe_generate_text(prompt: str) -> str | None:
    try:
        return generate_text(prompt)
    except Exception:
        return None


def run_policy_analysis(user_profile: dict[str, Any]) -> dict[str, Any]:
    """Return lightweight policy guidance based on user constraints."""
    preferences = _as_list(user_profile.get("preferred_regions"))
    constraints = _as_list(user_profile.get("constraints"))
    visa_required = bool(user_profile.get("needs_visa_sponsorship"))
    has_work_auth = bool(user_profile.get("has_work_authorization"))
    open_to_remote = bool(user_profile.get("open_to_remote"))

    if has_work_auth:
        visa_risk = "low"
    elif visa_required:
        visa_risk = "high"
        constraints.append("Needs employer visa sponsorship")
    else:
        visa_risk = "medium"

    if open_to_remote:
        constraints.append("Remote-friendly roles can widen options")

    recommended_regions = preferences[:] if preferences else ["US", "Canada", "UK"]
    if visa_required and not has_work_auth:
        recommended_regions = [
            region
            for region in recommended_regions
            if region in {"Canada", "UK", "Germany", "Singapore", "Remote"}
        ] or ["Canada", "UK", "Germany", "Remote"]

    explanation_prompt = f"""
You are helping an AI job search assistant summarize policy implications.

User profile:
{user_profile}

Return a concise explanation covering:
1. visa or mobility risk
2. practical constraints
3. recommended regions to prioritize
"""
    raw_text = _safe_generate_text(explanation_prompt)

    return {
        "visa_risk": visa_risk,
        "constraints": sorted(set(constraints)),
        "recommended_regions": recommended_regions,
        "raw_text": raw_text,
    }
