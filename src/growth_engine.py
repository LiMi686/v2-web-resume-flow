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


def _trim_text(value: str, limit: int = 2400) -> str:
    cleaned = " ".join(str(value).split())
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[: limit - 3].rstrip()}..."


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
        if priorities:
            return priorities[:4]
    lead_role = role_result.recommended_paths[0] if role_result.recommended_paths else None
    if lead_role:
        for focus in lead_role.focus_areas:
            if focus.lower() not in profile_skills and focus not in priorities:
                priorities.append(focus)
    return priorities[:4] or ["SQL", "Stakeholder Communication", "Domain Fluency"]


def _requirements_by_match(
    job_targeting_result: JobTargetingResult | None,
    *,
    matched: bool | None = None,
    limit: int = 3,
) -> list[str]:
    if not job_targeting_result:
        return []

    requirements: list[str] = []
    for requirement_match in job_targeting_result.requirement_matches:
        if matched is not None and requirement_match.matched != matched:
            continue
        requirement = requirement_match.requirement.strip()
        if requirement and requirement not in requirements:
            requirements.append(requirement)
    if matched is None and not requirements:
        requirements = [item.strip() for item in job_targeting_result.key_requirements if item.strip()]
    return requirements[:limit]


def _job_alignment_focus(job_targeting_result: JobTargetingResult | None) -> dict[str, list[str]]:
    if not job_targeting_result:
        return {
            "top_requirements": [],
            "matched_requirements": [],
            "gap_requirements": [],
            "positioning_strategy": [],
            "resume_rewrite_points": [],
            "cover_letter_inputs": [],
            "evidence_examples": [],
        }

    evidence_examples: list[str] = []
    for requirement_match in job_targeting_result.requirement_matches:
        if requirement_match.evidence:
            evidence_examples.append(
                f"{requirement_match.requirement}: {requirement_match.evidence[0]}"
            )

    return {
        "top_requirements": _requirements_by_match(job_targeting_result, matched=None, limit=3),
        "matched_requirements": _requirements_by_match(job_targeting_result, matched=True, limit=3),
        "gap_requirements": _requirements_by_match(job_targeting_result, matched=False, limit=3),
        "positioning_strategy": job_targeting_result.positioning_strategy[:3],
        "resume_rewrite_points": job_targeting_result.resume_rewrite_points[:3],
        "cover_letter_inputs": job_targeting_result.cover_letter_inputs[:3],
        "evidence_examples": evidence_examples[:3],
    }


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
    job_description: str = "",
) -> GrowthPlanResult:
    """Build a growth plan from macro context down to role execution."""
    profile = ensure_user_profile(user_profile)
    lead_industry = industry_result.top_industries[0] if industry_result.top_industries else None
    lead_role = role_result.recommended_paths[0] if role_result.recommended_paths else None
    lead_company = _select_lead_company(company_result, role_result)
    job_title = job_targeting_result.job_title if job_targeting_result else lead_role.role_title if lead_role else "target role"
    alignment_focus = _job_alignment_focus(job_targeting_result)
    top_requirements = alignment_focus["top_requirements"]
    matched_requirements = alignment_focus["matched_requirements"]
    gap_requirements = alignment_focus["gap_requirements"]
    positioning_strategy = alignment_focus["positioning_strategy"]
    resume_rewrite_points = alignment_focus["resume_rewrite_points"]
    cover_letter_inputs = alignment_focus["cover_letter_inputs"]
    evidence_examples = alignment_focus["evidence_examples"]
    job_description_text = job_description.strip()
    if job_targeting_result:
        jd_summary = job_targeting_result.jd_summary.strip()
        market_context_label = f"the market implied by the target {job_title} JD"
        problem_focus_label = "the operating problems highlighted in the target job description"
        company_context_label = "the employer implied by this pasted JD"
        market_growth_narrative = (
            f"I am targeting this {job_title} path because the pasted job description points to a role where data work is expected to shape concrete decisions."
        )
        if jd_summary:
            market_growth_narrative = f"{market_growth_narrative} The core brief is: {jd_summary}"
        planning_anchor = (
            "Primary anchor: the pasted job description and its Job Alignment result. "
            "Earlier policy, industry, company, and role recommendations are background context only."
        )
        job_description_context = _trim_text(job_description_text or jd_summary)
    else:
        market_context_label = lead_industry.name if lead_industry else "the target industry"
        problem_focus_label = (
            lead_company.focus.lower()
            if lead_company
            else "the team workflows that generate the most decision value"
        )
        company_context_label = lead_company.name if lead_company else "companies in this category"
        market_growth_narrative = (
            f"I am targeting {lead_industry.name if lead_industry else 'this market'} because the macro and policy context supports durable demand."
        )
        planning_anchor = (
            "Primary anchor: the layered recommendation chain from policy to industry, company, and role."
        )
        job_description_context = "No target job description provided."

    first_month_plan = [
        f"Map the operating context of {market_context_label} and learn its core metrics.",
        f"Build stakeholder understanding around {problem_focus_label}.",
        (
            f"Turn the JD's top requirements ({', '.join(top_requirements)}) into a 30-day proof-of-value checklist."
            if top_requirements
            else "Translate job requirements into a 30-day proof-of-value checklist."
        ),
        (
            f"Close the most urgent credibility gap in {gap_requirements[0]} with one scoped artifact and one quantified story."
            if gap_requirements
            else "Ship one small but visible analysis, dashboard, or workflow improvement that proves execution speed."
        ),
        (
            f"Package your strongest matched evidence into interview-ready stories, starting with {evidence_examples[0]}."
            if evidence_examples
            else "Package your strongest matched requirements into interview-ready examples."
        ),
    ]
    month_2_3_plan = [
        (
            f"Own a recurring workflow that demonstrates {top_requirements[0]} in practice instead of one-off reporting."
            if top_requirements
            else "Own a recurring analysis or decision-support workflow instead of one-off reporting."
        ),
        "Develop domain fluency so recommendations reflect industry economics, not just data outputs.",
        (
            f"Turn one positioning move into a reusable execution habit: {positioning_strategy[0]}"
            if positioning_strategy
            else "Turn one technical capability into a reusable artifact such as a dashboard, model, template, or playbook."
        ),
        (
            f"Convert this resume-level improvement into a shipped artifact: {resume_rewrite_points[0]}"
            if resume_rewrite_points
            else "Strengthen cross-functional trust by connecting analysis to a business decision or operational win."
        ),
        (
            f"Strengthen one remaining JD gap in {gap_requirements[0]} with domain-specific proof."
            if gap_requirements
            else "Strengthen cross-functional trust by connecting analysis to a business decision or operational win."
        ),
    ]
    one_year_plan = [
        (
            f"Become the go-to operator for {job_title.lower()} problems tied to {', '.join(top_requirements[:2])}."
            if top_requirements
            else f"Become the go-to operator for {lead_role.role_title.lower()} problems." if lead_role else "Own a strategic problem area end-to-end."
        ),
        (
            f"Build a portfolio of impact stories that compounds your strongest evidence in {', '.join(matched_requirements[:2])}."
            if matched_requirements
            else "Build a portfolio of impact stories that compound into promotion or stronger external positioning."
        ),
        "Expand from execution into prioritization by influencing what should be measured, automated, or changed.",
        (
            f"Create option value by turning current gaps in {', '.join(gap_requirements[:2])} into visible strengths."
            if gap_requirements
            else "Create option value for the next move across stronger roles, better companies, or deeper domain specialization."
        ),
    ]
    daily_skill_accumulation = [
        (
            f"Spend 30-45 minutes rotating through JD-critical requirements such as {', '.join(top_requirements[:3])}."
            if top_requirements
            else "Spend 30-45 minutes strengthening one role-critical skill with a concrete artifact every day."
        ),
        "Maintain a running evidence log of business impact, stakeholder wins, and domain insights.",
        (
            f"Rewrite one example each week so it better supports this positioning move: {positioning_strategy[0]}"
            if positioning_strategy
            else "Refine one resume or narrative bullet each week using fresh evidence from projects."
        ),
        (
            f"Close one JD gap at a time, starting with {gap_requirements[0]}."
            if gap_requirements
            else "Read one company, industry, or market note daily to stay macro-aware instead of tool-focused."
        ),
        "Read one company, industry, or market note daily to stay macro-aware instead of tool-focused.",
    ]
    value_creation_plan = [
        f"Target value creation inside {market_context_label}.",
        f"Focus on problems close to {problem_focus_label}.",
        (
            f"Prioritize work that proves the JD's highest-value requirement: {top_requirements[0]}."
            if top_requirements
            else "Prefer work that reduces decision latency, improves forecast quality, or creates reusable operational leverage."
        ),
        (
            f"Choose projects that convert your current gap in {gap_requirements[0]} into shipping evidence."
            if gap_requirements
            else "Document outcomes in a way that can later power interviews, resumes, and promotion cases."
        ),
        "Prefer work that reduces decision latency, improves forecast quality, or creates reusable operational leverage.",
        "Document outcomes in a way that can later power interviews, resumes, and promotion cases.",
    ]
    cover_letter_growth_narrative = [
        market_growth_narrative,
        f"I am especially interested in {company_context_label} because the role appears close to strategic operating problems.",
        f"My role path centers on becoming a high-leverage {job_title} who can translate analysis into decisions.",
        (
            f"My near-term growth plan is built around proving {', '.join(top_requirements[:2])} with concrete evidence."
            if top_requirements
            else "I want my first year to compound into both immediate contribution and long-term industry positioning."
        ),
        (
            f"I am intentionally closing gaps in {', '.join(gap_requirements[:2])} so my profile becomes stronger with each application cycle."
            if gap_requirements
            else "I want my first year to compound into both immediate contribution and long-term industry positioning."
        ),
        (
            f"My application narrative keeps reinforcing this fit: {cover_letter_inputs[0]}"
            if cover_letter_inputs
            else "I want my first year to compound into both immediate contribution and long-term industry positioning."
        ),
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

Planning anchor:
{planning_anchor}

Active market context:
{market_context_label}

Active company context:
{company_context_label}

Active role context:
{job_title}

Raw target job description:
{job_description_context}

Job targeting result:
{job_targeting_result}

Job-alignment focus:
top_requirements={top_requirements}
matched_requirements={matched_requirements}
gap_requirements={gap_requirements}
positioning_strategy={positioning_strategy}
resume_rewrite_points={resume_rewrite_points}
cover_letter_inputs={cover_letter_inputs}
evidence_examples={evidence_examples}

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

Instructions:
- If a Job targeting result or raw target job description is present, treat it as the primary source of truth.
- Earlier policy, industry, company, and role outputs are background only and must not override the pasted JD.
- Reuse earlier-stage context only when it directly supports the chosen JD.
- Every section must clearly reflect the pasted JD's business problems, required skills, evidence gaps, and positioning strategy.
- Anchor the plan to the JD's key requirements, evidence, gaps, positioning strategy, and resume rewrite priorities.
- Avoid generic growth advice when specific job-alignment context is available.
- Only return valid JSON.

Only return valid JSON.
"""
    llm_growth_payload = generate_optional_json(
        llm_growth_prompt,
        fallback=None,
        profile="balanced",
    )
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

Active market context:
{market_context_label}

Active role context:
{job_title}

Planning anchor:
{planning_anchor}

Target JD context:
{job_description_context}

Return 3 concise sentences on how growth planning should connect to the target JD's business problems, evidence gaps, and near-term execution priorities.
"""
    explanation = generate_optional_text(explanation_prompt, profile="creative")

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
