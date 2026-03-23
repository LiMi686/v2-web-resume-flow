"""Application assets stage for the career strategy pipeline."""

from __future__ import annotations

from typing import Any

try:
    from .llm_client import generate_optional_json, generate_optional_text
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
    from llm_client import generate_optional_json, generate_optional_text
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


def _select_lead_company(
    company_result: CompanyStrategyResult,
    role_result: RolePathResult,
):
    if not company_result.shortlisted_companies:
        return None
    lead_path = role_result.recommended_paths[0] if role_result.recommended_paths else None
    if not lead_path:
        return company_result.shortlisted_companies[0]
    for company in company_result.shortlisted_companies:
        if company.industry == lead_path.industry:
            return company
    return company_result.shortlisted_companies[0]


def _fallback_cover_letter(
    profile: UserProfile,
    lead_company,
    role_result: RolePathResult,
    job_result: JobTargetingResult,
    growth_result: GrowthPlanResult,
) -> str:
    lead_path = role_result.recommended_paths[0] if role_result.recommended_paths else None
    company_name = lead_company.name if lead_company else "your team"
    role_title = job_result.job_title or (lead_path.role_title if lead_path else profile.target_role or "this role")
    return (
        f"I am excited about {role_title} because it sits in a market where data work can shape real decisions. "
        f"My background combines internships and project work in analytics-heavy environments, and I am especially drawn to {company_name} "
        f"because the company appears close to strategic operating problems. I would bring a bias toward measurable execution, clear stakeholder communication, "
        f"and the kind of learning plan reflected in my near-term growth priorities: {', '.join(growth_result.prioritized_skills[:3]) or 'analytics depth and business context'}."
    )


def _fallback_cold_email(
    profile: UserProfile,
    lead_company,
    job_result: JobTargetingResult,
) -> str:
    company_name = lead_company.name if lead_company else "your company"
    return (
        f"Hi, I am {profile.name or 'a candidate'} exploring {job_result.job_title} opportunities at {company_name}. "
        f"My background includes analytics, Python/SQL work, and internship experience that maps well to the role's focus areas. "
        f"I would love to learn more about how your team uses data to drive decisions and whether my profile could be a fit."
    )


def _fallback_networking_message(
    profile: UserProfile,
    lead_company,
    role_result: RolePathResult,
) -> str:
    lead_path = role_result.recommended_paths[0] if role_result.recommended_paths else None
    company_name = lead_company.name if lead_company else "your team"
    return (
        f"Hi, I am {profile.name or 'a candidate'} and I am exploring {lead_path.role_title if lead_path else profile.target_role or 'analytics'} paths in "
        f"{lead_path.industry if lead_path else 'this market'}. I am particularly interested in {company_name} because of its operating context, "
        f"and I would appreciate any advice on what your team values most in early-career candidates."
    )


def _fallback_linkedin_summary(
    profile: UserProfile,
    role_result: RolePathResult,
    growth_result: GrowthPlanResult,
) -> str:
    lead_path = role_result.recommended_paths[0] if role_result.recommended_paths else None
    headline_role = lead_path.role_title if lead_path else profile.target_role or "Data / AI Candidate"
    return (
        f"Early-career {headline_role} focused on turning analytics, SQL, Python, and internship-based execution into measurable business impact. "
        f"Interested in {lead_path.industry if lead_path else 'data-rich industries'} and currently strengthening {', '.join(growth_result.prioritized_skills[:3]) or 'industry-relevant skills'}."
    )


def run_application_assets(
    user_profile: UserProfile | dict[str, Any],
    company_result: CompanyStrategyResult,
    role_result: RolePathResult,
    job_targeting_result: JobTargetingResult,
    growth_result: GrowthPlanResult,
) -> ApplicationAssetsResult:
    """Turn alignment and growth context into candidate-facing application assets."""
    profile = ensure_user_profile(user_profile)
    lead_company = _select_lead_company(company_result, role_result)

    tailored_resume_bullets = job_targeting_result.tailored_resume_bullets[:4]
    cover_letter_draft = _fallback_cover_letter(
        profile,
        lead_company,
        role_result,
        job_targeting_result,
        growth_result,
    )
    cold_email_message = _fallback_cold_email(profile, lead_company, job_targeting_result)
    networking_message = _fallback_networking_message(profile, lead_company, role_result)
    why_this_role_answer = job_targeting_result.why_this_role_answer
    linkedin_summary = _fallback_linkedin_summary(profile, role_result, growth_result)

    prompt = f"""
You are generating application assets for a layered career strategy system.

User profile:
{profile.to_dict()}

Lead company:
{lead_company}

Role result:
{role_result}

Job targeting result:
{job_targeting_result}

Growth result:
{growth_result}

Deterministic baseline:
tailored_resume_bullets={tailored_resume_bullets}
cover_letter_draft={cover_letter_draft}
cold_email_message={cold_email_message}
networking_message={networking_message}
why_this_role_answer={why_this_role_answer}
linkedin_summary={linkedin_summary}

Return strict JSON with this shape:
{{
  "tailored_resume_bullets": ["bullet 1", "bullet 2", "bullet 3"],
  "cover_letter_draft": "short paragraph",
  "cold_email_message": "short email",
  "networking_message": "short networking message",
  "why_this_role_answer": "short answer",
  "linkedin_summary": "short summary"
}}
Only return valid JSON.
"""
    llm_payload = generate_optional_json(prompt, fallback=None)
    if isinstance(llm_payload, dict):
        tailored_resume_bullets = _clean_string_list(
            llm_payload.get("tailored_resume_bullets"),
            limit=4,
        ) or tailored_resume_bullets
        cover_letter_draft = str(llm_payload.get("cover_letter_draft", "")).strip() or cover_letter_draft
        cold_email_message = str(llm_payload.get("cold_email_message", "")).strip() or cold_email_message
        networking_message = str(llm_payload.get("networking_message", "")).strip() or networking_message
        why_this_role_answer = str(llm_payload.get("why_this_role_answer", "")).strip() or why_this_role_answer
        linkedin_summary = str(llm_payload.get("linkedin_summary", "")).strip() or linkedin_summary

    explanation_prompt = f"""
You are summarizing why application assets matter in a layered career strategy system.

Job targeting result:
{job_targeting_result}

Growth result:
{growth_result}

Return 2 concise sentences.
"""
    explanation = generate_optional_text(explanation_prompt)

    return ApplicationAssetsResult(
        tailored_resume_bullets=tailored_resume_bullets,
        cover_letter_draft=cover_letter_draft,
        cold_email_message=cold_email_message,
        networking_message=networking_message,
        why_this_role_answer=why_this_role_answer,
        linkedin_summary=linkedin_summary,
        explanation=explanation,
    )
