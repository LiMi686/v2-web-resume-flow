"""Growth planning stage for the career strategy pipeline."""

from __future__ import annotations

from typing import Any

try:
    from .llm_client import generate_json_strict
    from .schemas import (
        CompanyStrategyResult,
        GrowthPlanResult,
        JobTargetingResult,
        PolicyResult,
        RolePathResult,
        UserProfile,
        ensure_user_profile,
    )
except ImportError:
    from llm_client import generate_json_strict
    from schemas import (
        CompanyStrategyResult,
        GrowthPlanResult,
        JobTargetingResult,
        PolicyResult,
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


def run_growth_plan(
    user_profile: UserProfile | dict[str, Any],
    policy_result: PolicyResult,
    industry_result,
    company_result: CompanyStrategyResult,
    role_result: RolePathResult,
    job_targeting_result: JobTargetingResult | None = None,
    job_description: str = "",
) -> GrowthPlanResult:
    """Build a growth plan from macro context down to role execution."""
    profile = ensure_user_profile(user_profile)
    prompt = f"""
You are building a growth plan for a layered career strategy system.

User profile:
{profile.to_dict()}

Policy result:
{policy_result}

Industry result:
{industry_result}

Company result:
{company_result}

Role result:
{role_result}

Job targeting result:
{job_targeting_result}

Raw target job description:
{job_description}

Return strict JSON with this shape:
{{
  "first_month_plan": ["..."],
  "month_2_3_plan": ["..."],
  "one_year_plan": ["..."],
  "daily_skill_accumulation": ["..."],
  "value_creation_plan": ["..."],
  "cover_letter_growth_narrative": ["..."],
  "priority_gaps": ["..."],
  "prioritized_skills": ["..."],
  "project_recommendations": ["..."],
  "job_search_strategy": ["..."],
  "explanation": "3 concise sentences"
}}

Instructions:
- Results must be fully model-derived from the upstream stages.
- If a target JD is present, use it as the primary execution anchor.
- Avoid generic advice; make the plan specific to the user's profile and chosen path.
- Only return valid JSON.
"""
    payload = generate_json_strict(prompt, profile="balanced")

    explanation = str(payload.get("explanation", "")).strip()
    if not explanation:
        raise ValueError("Growth plan response must include explanation.")

    first_month_plan = _clean_string_list(payload.get("first_month_plan"), limit=6)
    month_2_3_plan = _clean_string_list(payload.get("month_2_3_plan"), limit=6)
    one_year_plan = _clean_string_list(payload.get("one_year_plan"), limit=6)
    daily_skill_accumulation = _clean_string_list(payload.get("daily_skill_accumulation"), limit=6)
    value_creation_plan = _clean_string_list(payload.get("value_creation_plan"), limit=6)
    cover_letter_growth_narrative = _clean_string_list(
        payload.get("cover_letter_growth_narrative"),
        limit=6,
    )
    priority_gaps = _clean_string_list(payload.get("priority_gaps"), limit=6)
    prioritized_skills = _clean_string_list(payload.get("prioritized_skills"), limit=6)
    project_recommendations = _clean_string_list(payload.get("project_recommendations"), limit=6)
    job_search_strategy = _clean_string_list(payload.get("job_search_strategy"), limit=6)

    required_sections = [
        first_month_plan,
        month_2_3_plan,
        one_year_plan,
        daily_skill_accumulation,
        value_creation_plan,
        cover_letter_growth_narrative,
        priority_gaps,
        prioritized_skills,
        project_recommendations,
        job_search_strategy,
    ]
    if any(not section for section in required_sections):
        raise ValueError("Growth plan response is missing one or more required sections.")

    return GrowthPlanResult(
        first_month_plan=first_month_plan,
        month_2_3_plan=month_2_3_plan,
        one_year_plan=one_year_plan,
        daily_skill_accumulation=daily_skill_accumulation,
        value_creation_plan=value_creation_plan,
        cover_letter_growth_narrative=cover_letter_growth_narrative,
        priority_gaps=priority_gaps,
        prioritized_skills=prioritized_skills,
        project_recommendations=project_recommendations,
        job_search_strategy=job_search_strategy,
        explanation=explanation,
    )
