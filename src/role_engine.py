"""Role path stage for the career strategy pipeline."""

from __future__ import annotations

from typing import Any

try:
    from .industry_engine import INDUSTRY_KB
    from .llm_client import generate_optional_text
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
    from llm_client import generate_optional_text
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


def run_role_path(
    user_profile: UserProfile | dict[str, Any],
    policy_result: PolicyResult,
    industry_result,
    company_result: CompanyStrategyResult,
) -> RolePathResult:
    """Translate industry and company choices into role path options."""
    profile = ensure_user_profile(user_profile)
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

    explanation_prompt = f"""
You are explaining role path design inside an industry-first and company-strategy-centered system.

User profile:
{profile.to_dict()}

Recommended paths:
{recommended_paths}

Return 3 concise sentences.
"""
    explanation = generate_optional_text(explanation_prompt)

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
            target_company_types=[],
            company_selection_rules=[],
            industry_analysis=[],
            market_analysis=[],
            value_chain_analysis=[],
            competitor_map=[],
            shortlisted_companies=[],
            why_these_companies=[],
        )
    else:
        raise TypeError(
            "run_role_selection expects (user_profile, policy_result, industry_result[, company_result])."
        )
    return run_role_path(user_profile, policy_result, industry_result, company_result)
