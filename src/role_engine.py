"""Role path stage for the career strategy pipeline."""

from __future__ import annotations

from typing import Any

try:
    from .llm_client import generate_json_strict
    from .schemas import (
        CompanyStrategyResult,
        PolicyResult,
        RolePathOption,
        RolePathResult,
        UserProfile,
        ensure_user_profile,
    )
except ImportError:
    from llm_client import generate_json_strict
    from schemas import (
        CompanyStrategyResult,
        PolicyResult,
        RolePathOption,
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


def _role_path_from_payload(item: dict[str, Any]) -> RolePathOption:
    industry = str(item.get("industry", "")).strip()
    company_type = str(item.get("company_type", "")).strip()
    role_title = str(item.get("role_title", "")).strip()
    path_type = str(item.get("path_type", "")).strip().lower()
    focus_areas = _clean_string_list(item.get("focus_areas"), limit=5)
    why_fit = _clean_string_list(item.get("why_fit"), limit=5)
    success_metrics = _clean_string_list(item.get("success_metrics"), limit=5)
    example_companies = _clean_string_list(item.get("example_companies"), limit=5)

    if path_type not in {"bridge", "direct", "stretch"}:
        raise ValueError(f"Invalid role path_type: {path_type}")
    if not all([industry, company_type, role_title]):
        raise ValueError("Role path is missing required fields.")
    if not focus_areas or not why_fit or not success_metrics:
        raise ValueError("Role path must include focus_areas, why_fit, and success_metrics.")

    return RolePathOption(
        industry=industry,
        company_type=company_type,
        role_title=role_title,
        path_type=path_type,
        focus_areas=focus_areas,
        why_fit=why_fit,
        success_metrics=success_metrics,
        example_companies=example_companies,
    )


def run_role_path(
    user_profile: UserProfile | dict[str, Any],
    policy_result: PolicyResult,
    industry_result,
    company_result: CompanyStrategyResult,
) -> RolePathResult:
    """Translate industry and company choices into role path options."""
    profile = ensure_user_profile(user_profile)
    role_prompt = f"""
You are the role-path strategist in a layered career planning system.

User profile:
{profile.to_dict()}

Policy result:
{policy_result}

Industry result:
{industry_result}

Company result:
{company_result}

Return strict JSON with this shape:
{{
  "recommended_paths": [
    {{
      "industry": "industry name",
      "company_type": "company environment",
      "role_title": "specific role title",
      "path_type": "bridge|direct|stretch",
      "focus_areas": ["focus 1", "focus 2"],
      "why_fit": ["reason 1", "reason 2"],
      "success_metrics": ["metric 1", "metric 2"],
      "example_companies": ["company 1", "company 2"]
    }}
  ],
  "decision_principles": ["principle 1", "principle 2", "principle 3"],
  "explanation": "3 concise sentences"
}}

Instructions:
- Results must be fully model-derived from the prior stages and the user's background.
- Keep path_type realistic given years of experience and current evidence.
- Prefer role paths that can create visible first-year business impact.
- Return at least 3 recommended paths.
- Only return valid JSON.
"""
    payload = generate_json_strict(role_prompt, profile="balanced")
    raw_paths = payload.get("recommended_paths")
    if not isinstance(raw_paths, list):
        raise ValueError("Role response must include recommended_paths.")

    recommended_paths: list[RolePathOption] = []
    for item in raw_paths:
        if not isinstance(item, dict):
            continue
        recommended_paths.append(_role_path_from_payload(item))

    if len(recommended_paths) < 3:
        raise ValueError("Role response must include at least 3 valid recommended_paths.")

    decision_principles = _clean_string_list(payload.get("decision_principles"), limit=5)
    explanation = str(payload.get("explanation", "")).strip()
    if not decision_principles:
        raise ValueError("Role response must include decision_principles.")
    if not explanation:
        raise ValueError("Role response must include explanation.")

    return RolePathResult(
        recommended_paths=recommended_paths,
        decision_principles=decision_principles,
        explanation=explanation,
    )


def run_role_selection(
    user_profile: UserProfile | dict[str, Any],
    *args: Any,
) -> RolePathResult:
    """Compatibility wrapper for older callers."""
    if len(args) == 3:
        policy_result, industry_result, company_result = args
    elif len(args) == 2:
        policy_result, industry_result = args
        company_result = CompanyStrategyResult(
            user_preference_summary="",
            preference_alignment_summary="",
            discovery_strategy=[],
            target_company_types=[],
            company_selection_rules=[],
            company_archetype_assessments=[],
            primary_company_path="",
            competitiveness_summary="",
            development_recommendation="",
            ranking_logic=[],
            industry_analysis=[],
            market_analysis=[],
            value_chain_analysis=[],
            competitor_map=[],
            retrieved_companies=[],
            shortlisted_companies=[],
            why_these_companies=[],
        )
    else:
        raise TypeError(
            "run_role_selection expects (user_profile, policy_result, industry_result[, company_result])."
        )
    return run_role_path(user_profile, policy_result, industry_result, company_result)
