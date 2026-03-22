"""Growth planning stage for the career strategy pipeline."""

from __future__ import annotations

from typing import Any

try:
    from .llm_client import generate_optional_text
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
    from llm_client import generate_optional_text
    from schemas import (
        CompanyStrategyResult,
        GrowthPlanResult,
        JobTargetingResult,
        PolicyResult,
        RolePathResult,
        UserProfile,
        ensure_user_profile,
    )


def run_growth_plan(
    user_profile: UserProfile | dict[str, Any],
    policy_result: PolicyResult,
    industry_result,
    company_result: CompanyStrategyResult,
    role_result: RolePathResult,
    job_targeting_result: JobTargetingResult | None = None,
) -> GrowthPlanResult:
    """Build a growth plan from macro context down to role execution."""
    profile = ensure_user_profile(user_profile)
    lead_industry = industry_result.top_industries[0] if industry_result.top_industries else None
    lead_role = role_result.recommended_paths[0] if role_result.recommended_paths else None
    lead_company = company_result.shortlisted_companies[0] if company_result.shortlisted_companies else None
    job_title = job_targeting_result.job_title if job_targeting_result else lead_role.role_title if lead_role else "target role"

    first_month_plan = [
        f"Map the operating context of {lead_industry.name if lead_industry else 'the target industry'} and learn its core metrics.",
        f"Build stakeholder understanding around {lead_company.focus.lower()}." if lead_company else "Identify the team workflows that generate the most decision value.",
        "Ship one small but visible analysis, dashboard, or workflow improvement that proves execution speed.",
        "Translate job requirements into a 30-day proof-of-value checklist.",
    ]
    month_2_3_plan = [
        "Own a recurring analysis or decision-support workflow instead of one-off reporting.",
        "Develop domain fluency so recommendations reflect industry economics, not just data outputs.",
        "Turn one technical capability into a reusable artifact such as a dashboard, model, template, or playbook.",
        "Strengthen cross-functional trust by connecting analysis to a business decision or operational win.",
    ]
    one_year_plan = [
        f"Become the go-to operator for {lead_role.role_title.lower()} problems." if lead_role else "Own a strategic problem area end-to-end.",
        "Build a portfolio of impact stories that compound into promotion or stronger external positioning.",
        "Expand from execution into prioritization by influencing what should be measured, automated, or changed.",
        "Create option value for the next move across stronger roles, better companies, or deeper domain specialization.",
    ]
    daily_skill_accumulation = [
        "Spend 30-45 minutes strengthening one role-critical skill with a concrete artifact every day.",
        "Maintain a running evidence log of business impact, stakeholder wins, and domain insights.",
        "Read one company, industry, or market note daily to stay macro-aware instead of tool-focused.",
        "Refine one resume or narrative bullet each week using fresh evidence from projects.",
    ]
    value_creation_plan = [
        f"Target value creation where {lead_industry.name if lead_industry else 'the industry'} has active tailwinds.",
        f"Focus on problems close to {lead_company.focus.lower()}." if lead_company else "Focus on problems tied to measurable business or operational outcomes.",
        "Prefer work that reduces decision latency, improves forecast quality, or creates reusable operational leverage.",
        "Document outcomes in a way that can later power interviews, resumes, and promotion cases.",
    ]
    cover_letter_growth_narrative = [
        f"I am targeting {lead_industry.name if lead_industry else 'this market'} because the macro and policy context supports durable demand.",
        f"I am especially interested in {lead_company.name if lead_company else 'companies in this category'} because they sit close to strategic operating problems.",
        f"My role path centers on becoming a high-leverage {job_title} who can translate analysis into decisions.",
        "I want my first year to compound into both immediate contribution and long-term industry positioning.",
    ]

    explanation_prompt = f"""
You are refining a growth plan for a layered career strategy system.

User profile:
{profile.to_dict()}

Lead industry:
{lead_industry}

Lead role:
{lead_role}

Return 3 concise sentences on how growth planning should connect to industry, company strategy, and role path.
"""
    explanation = generate_optional_text(explanation_prompt)

    return GrowthPlanResult(
        first_month_plan=first_month_plan,
        month_2_3_plan=month_2_3_plan,
        one_year_plan=one_year_plan,
        daily_skill_accumulation=daily_skill_accumulation,
        value_creation_plan=value_creation_plan,
        cover_letter_growth_narrative=cover_letter_growth_narrative,
        explanation=explanation,
    )
