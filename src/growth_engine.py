"""Growth planning stage for the career strategy pipeline."""

from __future__ import annotations

from typing import Any

try:
    from .llm_client import generate_optional_json, generate_optional_text
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
    from llm_client import generate_optional_json, generate_optional_text
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


def _derive_priority_gaps(job_targeting_result: JobTargetingResult | None) -> list[str]:
    if not job_targeting_result:
        return [
            "Strengthen domain evidence in the chosen industry.",
            "Build one visible project that links analysis to business decisions.",
        ]
    if job_targeting_result.gap_analysis:
        return job_targeting_result.gap_analysis[:4]
    return ["No critical gaps detected, so the next focus is depth and sharper positioning."]


def _derive_prioritized_skills(
    profile: UserProfile,
    role_result: RolePathResult,
    job_targeting_result: JobTargetingResult | None,
) -> list[str]:
    profile_skills = {skill.lower() for skill in profile.skills}
    priorities: list[str] = []
    if job_targeting_result:
        for requirement in job_targeting_result.key_requirements:
            if requirement.lower() not in profile_skills:
                priorities.append(requirement)
    lead_role = role_result.recommended_paths[0] if role_result.recommended_paths else None
    if lead_role:
        for focus in lead_role.focus_areas:
            if focus.lower() not in profile_skills and focus not in priorities:
                priorities.append(focus)
    return priorities[:4] or ["SQL", "Stakeholder Communication", "Domain Fluency"]


def _project_suggestion(skill: str) -> str:
    normalized = skill.lower()
    if "sql" in normalized or "dashboard" in normalized or "analytics" in normalized:
        return "Build an end-to-end business metrics or dashboard case study with clear KPI movement and stakeholder recommendations."
    if "experiment" in normalized or "statistics" in normalized:
        return "Create an experimentation or causal analysis project that shows hypothesis design, metric choice, and decision impact."
    if "machine learning" in normalized or "forecast" in normalized or "optimization" in normalized:
        return "Ship a forecasting or predictive modeling project with business framing, validation, and deployment-ready storytelling."
    if "communication" in normalized:
        return "Write a decision memo or stakeholder readout that turns analysis into prioritization guidance."
    return "Build a scoped project that produces one reusable artifact and one quantified business story."


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
    lead_company = _select_lead_company(company_result, role_result)
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
    priority_gaps = _derive_priority_gaps(job_targeting_result)
    prioritized_skills = _derive_prioritized_skills(profile, role_result, job_targeting_result)
    project_recommendations = [_project_suggestion(skill) for skill in prioritized_skills[:3]]
    if job_targeting_result and job_targeting_result.match_confidence == "high":
        job_search_strategy = [
            "You can already pursue direct applications while tightening narrative precision for the best-fit roles.",
            "Prioritize roles where the JD mirrors your strongest evidence instead of overreaching on title alone.",
            "Use tailored bullets and concise networking outreach to increase interview conversion.",
        ]
    elif job_targeting_result and job_targeting_result.match_confidence == "medium":
        job_search_strategy = [
            "Apply to both bridge and direct roles, but close the top one or two evidence gaps in parallel.",
            "Prioritize roles where your internships and projects can be mapped cleanly to business outcomes.",
            "Use each application cycle to sharpen one stronger proof point for the next wave.",
        ]
    else:
        job_search_strategy = [
            "Bias toward bridge roles such as DA, BI, or analytics-heavy operations paths before stretching too early.",
            "Use the next 4-8 weeks to build one portfolio project and one clearer narrative around business impact.",
            "Treat applications and skill-building as one loop: every gap should inform what you build next.",
        ]

    llm_growth_prompt = f"""
You are building a growth plan for a layered career strategy system.

User profile:
{profile.to_dict()}

Policy result:
{policy_result}

Lead industry:
{lead_industry}

Lead company:
{lead_company}

Lead role:
{lead_role}

Job targeting result:
{job_targeting_result}

Deterministic baseline:
first_month_plan={first_month_plan}
month_2_3_plan={month_2_3_plan}
one_year_plan={one_year_plan}
daily_skill_accumulation={daily_skill_accumulation}
value_creation_plan={value_creation_plan}
cover_letter_growth_narrative={cover_letter_growth_narrative}
priority_gaps={priority_gaps}
prioritized_skills={prioritized_skills}
project_recommendations={project_recommendations}
job_search_strategy={job_search_strategy}

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
  "job_search_strategy": ["..."]
}}
Only return valid JSON.
"""
    llm_growth_payload = generate_optional_json(llm_growth_prompt, fallback=None)
    if isinstance(llm_growth_payload, dict):
        first_month_plan = _clean_string_list(
            llm_growth_payload.get("first_month_plan"),
            limit=5,
        ) or first_month_plan
        month_2_3_plan = _clean_string_list(
            llm_growth_payload.get("month_2_3_plan"),
            limit=5,
        ) or month_2_3_plan
        one_year_plan = _clean_string_list(
            llm_growth_payload.get("one_year_plan"),
            limit=5,
        ) or one_year_plan
        daily_skill_accumulation = _clean_string_list(
            llm_growth_payload.get("daily_skill_accumulation"),
            limit=5,
        ) or daily_skill_accumulation
        value_creation_plan = _clean_string_list(
            llm_growth_payload.get("value_creation_plan"),
            limit=5,
        ) or value_creation_plan
        cover_letter_growth_narrative = _clean_string_list(
            llm_growth_payload.get("cover_letter_growth_narrative"),
            limit=5,
        ) or cover_letter_growth_narrative
        priority_gaps = _clean_string_list(
            llm_growth_payload.get("priority_gaps"),
            limit=5,
        ) or priority_gaps
        prioritized_skills = _clean_string_list(
            llm_growth_payload.get("prioritized_skills"),
            limit=5,
        ) or prioritized_skills
        project_recommendations = _clean_string_list(
            llm_growth_payload.get("project_recommendations"),
            limit=5,
        ) or project_recommendations
        job_search_strategy = _clean_string_list(
            llm_growth_payload.get("job_search_strategy"),
            limit=5,
        ) or job_search_strategy

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
        priority_gaps=priority_gaps,
        prioritized_skills=prioritized_skills,
        project_recommendations=project_recommendations,
        job_search_strategy=job_search_strategy,
        explanation=explanation,
    )
