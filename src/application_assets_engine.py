"""Application assets stage for the career strategy pipeline."""

from __future__ import annotations

from typing import Any

try:
    from .llm_client import generate_json_strict
    from .schemas import (
        ApplicationAssetsResult,
        CompanyStrategyResult,
        GrowthPlanResult,
        JobTargetingResult,
        RolePathResult,
        UserProfile,
        ensure_user_profile,
    )
except ImportError:
    from llm_client import generate_json_strict
    from schemas import (
        ApplicationAssetsResult,
        CompanyStrategyResult,
        GrowthPlanResult,
        JobTargetingResult,
        RolePathResult,
        UserProfile,
        ensure_user_profile,
    )


def _clean_string_list(value: Any, limit: int | None = None) -> list[str]:
    if not isinstance(value, list):
        return []
    cleaned = [str(item).strip() for item in value if str(item).strip()]
    if limit is not None:
        return cleaned[:limit]
    return cleaned


def run_application_assets(
    user_profile: UserProfile | dict[str, Any],
    company_result: CompanyStrategyResult,
    role_result: RolePathResult,
    job_targeting_result: JobTargetingResult,
    growth_result: GrowthPlanResult,
) -> ApplicationAssetsResult:
    """Turn alignment and growth context into candidate-facing application assets."""
    profile = ensure_user_profile(user_profile)
    prompt = f"""
You are generating application assets for a layered career strategy system.

User profile:
{profile.to_dict()}

Company result:
{company_result}

Role result:
{role_result}

Job targeting result:
{job_targeting_result}

Growth result:
{growth_result}

Return strict JSON with this shape:
{{
  "tailored_resume_bullets": ["bullet 1", "bullet 2", "bullet 3"],
  "cover_letter_draft": "short paragraph",
  "cold_email_message": "short email",
  "networking_message": "short networking message",
  "why_this_role_answer": "short answer",
  "linkedin_summary": "short summary",
  "explanation": "2 concise sentences"
}}

Instructions:
- Results must be fully model-derived from the upstream stages.
- Keep the language specific to the chosen path and target role, not generic.
- Only return valid JSON.
"""
    payload = generate_json_strict(prompt, profile="balanced")

    tailored_resume_bullets = _clean_string_list(payload.get("tailored_resume_bullets"), limit=6)
    cover_letter_draft = str(payload.get("cover_letter_draft", "")).strip()
    cold_email_message = str(payload.get("cold_email_message", "")).strip()
    networking_message = str(payload.get("networking_message", "")).strip()
    why_this_role_answer = str(payload.get("why_this_role_answer", "")).strip()
    linkedin_summary = str(payload.get("linkedin_summary", "")).strip()
    explanation = str(payload.get("explanation", "")).strip()

    if not tailored_resume_bullets:
        raise ValueError("Application assets response must include tailored_resume_bullets.")
    if not all(
        [
            cover_letter_draft,
            cold_email_message,
            networking_message,
            why_this_role_answer,
            linkedin_summary,
            explanation,
        ]
    ):
        raise ValueError("Application assets response is missing required text fields.")

    return ApplicationAssetsResult(
        tailored_resume_bullets=tailored_resume_bullets,
        cover_letter_draft=cover_letter_draft,
        cold_email_message=cold_email_message,
        networking_message=networking_message,
        why_this_role_answer=why_this_role_answer,
        linkedin_summary=linkedin_summary,
        explanation=explanation,
    )
