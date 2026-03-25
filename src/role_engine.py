"""Role path stage for the career strategy pipeline."""

from __future__ import annotations

from typing import Any

try:
    from .industry_engine import INDUSTRY_KB
    from .llm_client import generate_optional_json, generate_optional_text
    from .schemas import (
        CompanyStrategyResult,
        PolicyResult,
        RolePathOption,
        RolePathResult,
        UserProfile,
        ensure_user_profile,
    )
except ImportError:
    from industry_engine import INDUSTRY_KB
    from llm_client import generate_optional_json, generate_optional_text
    from schemas import (
        CompanyStrategyResult,
        PolicyResult,
        RolePathOption,
        RolePathResult,
        UserProfile,
        ensure_user_profile,
    )


def _matching_company_names(
    industry_name: str, company_result: CompanyStrategyResult
) -> tuple[str, list[str]]:
    matching = [
        company for company in company_result.shortlisted_companies if company.industry == industry_name
    ]
    if not matching:
        return "Strategic operating companies", []
    return matching[0].company_type, [company.name for company in matching[:3]]


def _clean_string_list(value: Any, limit: int | None = None) -> list[str]:
    if not isinstance(value, list):
        return []
    cleaned = [str(item).strip() for item in value if str(item).strip()]
    if limit is not None:
        return cleaned[:limit]
    return cleaned


def _deterministic_role_path_result(
    profile: UserProfile,
    policy_result: PolicyResult,
    industry_result,
    company_result: CompanyStrategyResult,
) -> RolePathResult:
    years_experience = profile.years_experience
    target_role_text = profile.target_role.lower()
    role_map = {industry["name"]: industry["roles"] for industry in INDUSTRY_KB}

    recommended_paths: list[RolePathOption] = []
    for industry in industry_result.top_industries:
        roles = role_map.get(industry.name, {})
        company_type, example_companies = _matching_company_names(industry.name, company_result)

        if years_experience < 2:
            role_title = roles.get("bridge") or roles.get("direct") or profile.target_role
            path_type = "bridge"
        elif years_experience < 5:
            role_title = roles.get("direct") or roles.get("bridge") or profile.target_role
            path_type = "direct"
        else:
            role_title = roles.get("stretch") or roles.get("direct") or profile.target_role
            path_type = "stretch"

        if target_role_text and any(target_role_text in value.lower() for value in roles.values()):
            role_title = profile.target_role

        recommended_paths.append(
            RolePathOption(
                industry=industry.name,
                company_type=company_type,
                role_title=role_title,
                path_type=path_type,
                focus_areas=industry.key_skills[:3],
                why_fit=[
                    f"Industry selected first because {industry.why_now}",
                    f"Company strategy points toward {company_type.lower()} rather than generic employer lists.",
                    f"Policy mobility context is currently {policy_result.visa_risk} risk.",
                ],
                success_metrics=[
                    "Own a measurable business or operational metric in the first 90 days",
                    "Demonstrate domain fluency in the chosen industry",
                    "Translate analysis into a decision, automation, or workflow improvement",
                ],
                example_companies=example_companies or industry.sample_companies,
            )
        )

    decision_principles = [
        "Role path comes after industry and company strategy so the title reflects the market context.",
        "Bridge roles are valid when they improve industry entry speed and future option value.",
        "Choose roles where the first year can produce visible business impact, not just technical exposure.",
    ]
    explanation = generate_optional_text(
        f"""
You are explaining role path design inside an industry-first and company-strategy-centered system.

User profile:
{profile.to_dict()}

Recommended paths:
{recommended_paths}

Return 3 concise sentences.
""",
        profile="creative",
    )
    return RolePathResult(
        recommended_paths=recommended_paths,
        decision_principles=decision_principles,
        explanation=explanation,
    )


def run_role_path(
    user_profile: UserProfile | dict[str, Any],
    policy_result: PolicyResult,
    industry_result,
    company_result: CompanyStrategyResult,
) -> RolePathResult:
    """Translate industry and company choices into role path options."""
    profile = ensure_user_profile(user_profile)
    fallback_result = _deterministic_role_path_result(
        profile,
        policy_result,
        industry_result,
        company_result,
    )
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

Deterministic fallback role paths:
{fallback_result}

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
- Be LLM-first: you may revise the fallback paths or create more specific titles.
- Keep path_type realistic given years of experience and current evidence.
- Prefer roles that connect to measurable first-year business impact.
- Only return valid JSON.
"""
    payload = generate_optional_json(role_prompt, fallback=None, profile="balanced")
    if not isinstance(payload, dict):
        return fallback_result

    raw_paths = payload.get("recommended_paths")
    recommended_paths: list[RolePathOption] = []
    if isinstance(raw_paths, list):
        for item in raw_paths:
            if not isinstance(item, dict):
                continue
            role_title = str(item.get("role_title", "")).strip()
            industry_name = str(item.get("industry", "")).strip()
            if not role_title or not industry_name:
                continue
            path_type = str(item.get("path_type", "")).strip().lower() or "bridge"
            if path_type not in {"bridge", "direct", "stretch"}:
                path_type = "bridge"
            recommended_paths.append(
                RolePathOption(
                    industry=industry_name,
                    company_type=str(item.get("company_type", "")).strip() or "Strategic operating companies",
                    role_title=role_title,
                    path_type=path_type,
                    focus_areas=_clean_string_list(item.get("focus_areas"), limit=4) or ["analytics"],
                    why_fit=_clean_string_list(item.get("why_fit"), limit=4) or [
                        f"This path creates a plausible next step into {role_title}."
                    ],
                    success_metrics=_clean_string_list(item.get("success_metrics"), limit=4) or [
                        "Own a visible metric or workflow within the first 90 days"
                    ],
                    example_companies=_clean_string_list(item.get("example_companies"), limit=4),
                )
            )

    if not recommended_paths:
        recommended_paths = fallback_result.recommended_paths

    return RolePathResult(
        recommended_paths=recommended_paths,
        decision_principles=_clean_string_list(payload.get("decision_principles"), limit=4)
        or fallback_result.decision_principles,
        explanation=str(payload.get("explanation", "")).strip() or fallback_result.explanation,
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
            discovery_strategy=[],
            target_company_types=[],
            company_selection_rules=[],
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
