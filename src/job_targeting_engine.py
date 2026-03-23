"""Job alignment stage for the career strategy pipeline."""

from __future__ import annotations

from typing import Any

try:
    from .llm_client import generate_optional_json
    from .schemas import (
        CompanyStrategyResult,
        InternshipExperience,
        JobTargetingResult,
        RequirementMatch,
        RolePathResult,
        UserProfile,
        ensure_user_profile,
    )
except ImportError:
    from llm_client import generate_optional_json
    from schemas import (
        CompanyStrategyResult,
        InternshipExperience,
        JobTargetingResult,
        RequirementMatch,
        RolePathResult,
        UserProfile,
        ensure_user_profile,
    )

REQUIREMENT_CATALOG = {
    "Python": ["python"],
    "SQL": ["sql"],
    "Machine Learning": ["machine learning", "ml", "predictive modeling"],
    "Analytics": ["analytics", "analysis", "analytical"],
    "Experimentation": ["experimentation", "a/b", "ab testing", "hypothesis"],
    "Dashboarding": ["dashboard", "reporting", "tableau", "power bi"],
    "Stakeholder Communication": ["stakeholder", "cross-functional", "communicate", "present"],
    "Data Pipelines": ["pipeline", "etl", "data modeling", "data warehouse"],
    "Statistics": ["statistics", "statistical", "causal", "regression"],
    "Forecasting": ["forecast", "forecasting", "planning"],
    "Optimization": ["optimization", "optimize", "operations research"],
}


def _clean_string_list(value: Any, limit: int | None = None) -> list[str]:
    if not isinstance(value, list):
        return []
    cleaned = [str(item).strip() for item in value if str(item).strip()]
    if limit is not None:
        return cleaned[:limit]
    return cleaned


def _guess_job_title(job_description: str, role_result: RolePathResult) -> str:
    first_line = next((line.strip() for line in job_description.splitlines() if line.strip()), "")
    if len(first_line) <= 80:
        return first_line
    for path in role_result.recommended_paths:
        if path.role_title.lower() in job_description.lower():
            return path.role_title
    return role_result.recommended_paths[0].role_title if role_result.recommended_paths else "Target Role"


def _extract_requirements(job_description: str) -> list[str]:
    jd_text = job_description.lower()
    requirements = [
        name
        for name, keywords in REQUIREMENT_CATALOG.items()
        if any(keyword in jd_text for keyword in keywords)
    ]
    if not requirements:
        requirements = ["Analytics", "Stakeholder Communication", "SQL"]
    return requirements


def _llm_job_alignment_payload(
    profile: UserProfile,
    role_result: RolePathResult,
    company_result: CompanyStrategyResult,
    job_description: str,
    fallback_requirements: list[str],
) -> dict[str, Any] | None:
    prompt = f"""
You are helping with job alignment for a layered career strategy system.

User profile:
{profile.to_dict()}

Recommended role paths:
{role_result.recommended_paths}

Shortlisted companies:
{company_result.shortlisted_companies[:3]}

Job description:
{job_description}

Deterministic fallback requirements:
{fallback_requirements}

Return strict JSON with this shape:
{{
  "jd_summary": "short paragraph",
  "key_requirements": ["requirement 1", "requirement 2"],
  "positioning_strategy": ["point 1", "point 2", "point 3"],
  "resume_rewrite_points": ["point 1", "point 2", "point 3"],
  "cover_letter_inputs": ["point 1", "point 2", "point 3"],
  "tailored_resume_bullets": ["bullet 1", "bullet 2", "bullet 3"],
  "why_this_role_answer": "short answer"
}}
Only return valid JSON.
"""
    payload = generate_optional_json(prompt, fallback=None)
    return payload if isinstance(payload, dict) else None


def _build_evidence(
    requirement: str,
    profile: UserProfile,
    role_result: RolePathResult,
    company_result: CompanyStrategyResult,
) -> list[str]:
    evidence: list[str] = []
    requirement_lower = requirement.lower()
    for skill in profile.skills:
        if requirement_lower in skill.lower() or skill.lower() in requirement_lower:
            evidence.append(f"Existing skill: {skill}")
    for highlight in profile.experience_highlights:
        if requirement_lower in highlight.lower():
            evidence.append(f"Experience highlight: {highlight}")
    for internship in profile.internship_experiences:
        evidence.extend(_build_internship_evidence(requirement_lower, internship))

    lead_path = role_result.recommended_paths[0] if role_result.recommended_paths else None
    if lead_path and requirement in lead_path.focus_areas:
        evidence.append(f"Aligned with role path focus area in {lead_path.industry}")
    if requirement == "Stakeholder Communication":
        evidence.append("Can frame work around measurable business decisions and stakeholder influence")
    if requirement == "Analytics" and company_result.shortlisted_companies:
        evidence.append(
            f"Target companies expect analytics tied to {company_result.shortlisted_companies[0].focus.lower()}"
        )

    deduped: list[str] = []
    for item in evidence:
        if item not in deduped:
            deduped.append(item)
    return deduped


def _build_internship_evidence(
    requirement_lower: str,
    internship: InternshipExperience,
) -> list[str]:
    evidence: list[str] = []
    internship_label = "Internship"
    if internship.company and internship.title:
        internship_label = f"Internship at {internship.company} as {internship.title}"
    elif internship.company:
        internship_label = f"Internship at {internship.company}"
    elif internship.title:
        internship_label = f"Internship as {internship.title}"

    for skill in internship.skills_used:
        skill_lower = skill.lower()
        if requirement_lower in skill_lower or skill_lower in requirement_lower:
            evidence.append(f"{internship_label}: used {skill}")

    internship_texts = [internship.summary, *internship.impact_points]
    for text in internship_texts:
        cleaned = text.strip()
        if cleaned and requirement_lower in cleaned.lower():
            evidence.append(f"{internship_label}: {cleaned}")

    return evidence


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


def _build_tailored_resume_bullets(
    profile: UserProfile,
    role_result: RolePathResult,
    key_requirements: list[str],
    evidence_map: dict[str, list[str]],
) -> list[str]:
    lead_path = role_result.recommended_paths[0] if role_result.recommended_paths else None
    bullets: list[str] = []

    for requirement in key_requirements[:3]:
        evidence_items = evidence_map.get(requirement, [])
        evidence_text = evidence_items[0] if evidence_items else "Built a project or workflow that shows direct execution."
        bullets.append(
            f"Demonstrated {requirement.lower()} capability through {evidence_text.lower()}, aligned with the target path into {lead_path.role_title if lead_path else profile.target_role or 'the role'}."
        )

    if not bullets:
        bullets.append(
            f"Positioned for {lead_path.role_title if lead_path else profile.target_role or 'this role'} through a mix of internships, project execution, and business-facing analytics work."
        )
    return bullets[:4]


def _build_why_this_role_answer(
    profile: UserProfile,
    lead_path,
    lead_company,
    job_title: str,
    match_confidence: str,
) -> str:
    industry_name = lead_path.industry if lead_path else "this market"
    company_context = lead_company.name if lead_company else "companies in this category"
    return (
        f"I am targeting {job_title} because it sits at the intersection of {industry_name}, "
        f"measurable business impact, and the kind of operating context represented by {company_context}. "
        f"My background already shows early evidence in analytics execution, and the current fit is {match_confidence}, "
        f"which makes this role a realistic but still growth-oriented next step."
    )


def run_job_targeting(
    user_profile: UserProfile | dict[str, Any],
    policy_result,
    industry_result,
    company_result: CompanyStrategyResult,
    role_result: RolePathResult,
    job_description: str,
) -> JobTargetingResult:
    """Convert a job description into evidence mapping and positioning guidance."""
    profile = ensure_user_profile(user_profile)
    job_title = _guess_job_title(job_description, role_result)
    fallback_requirements = _extract_requirements(job_description)
    llm_payload = _llm_job_alignment_payload(
        profile,
        role_result,
        company_result,
        job_description,
        fallback_requirements,
    )
    key_requirements = _clean_string_list(
        llm_payload.get("key_requirements") if llm_payload else None,
        limit=8,
    ) or fallback_requirements

    requirement_matches: list[RequirementMatch] = []
    evidence_map: dict[str, list[str]] = {}
    gap_analysis: list[str] = []
    for index, requirement in enumerate(key_requirements):
        evidence = _build_evidence(requirement, profile, role_result, company_result)
        matched = bool(evidence)
        gap_notes = [] if matched else [f"Need stronger proof for {requirement} in role-specific stories or projects."]
        if not matched:
            gap_analysis.append(
                f"{requirement}: add a concrete project, quantified example, or domain-specific case to strengthen credibility."
            )
        requirement_matches.append(
            RequirementMatch(
                requirement=requirement,
                importance="high" if index < 4 else "medium",
                matched=matched,
                evidence=evidence,
                gap_notes=gap_notes,
            )
        )
        evidence_map[requirement] = evidence

    lead_path = role_result.recommended_paths[0] if role_result.recommended_paths else None
    lead_company = _select_lead_company(company_result, role_result)
    experience_alignment = [
        f"Target role path is {lead_path.role_title} in {lead_path.industry}." if lead_path else "Role path has not been selected.",
        f"Company strategy centers on {lead_company.company_type.lower()}." if lead_company else "No company strategy shortlist available.",
        f"User brings {profile.years_experience:g} years of experience plus skills in {', '.join(profile.skills[:4]) or 'foundational analytics'}.",
        f"Internship evidence available from {len(profile.internship_experiences)} role(s)." if profile.internship_experiences else "No structured internship evidence added yet.",
    ]

    matched_count = sum(match.matched for match in requirement_matches)
    match_ratio = matched_count / max(len(requirement_matches), 1)
    if match_ratio >= 0.75:
        match_confidence = "high"
    elif match_ratio >= 0.45:
        match_confidence = "medium"
    else:
        match_confidence = "low"

    jd_summary = (
        str(llm_payload.get("jd_summary")).strip()
        if llm_payload and str(llm_payload.get("jd_summary", "")).strip()
        else "The JD appears to value a mix of technical execution, business communication, and role-specific domain context."
    )
    positioning_strategy = _clean_string_list(
        llm_payload.get("positioning_strategy") if llm_payload else None,
        limit=4,
    ) or [
        "Lead with industry context first, then show why your skills fit this role inside that market.",
        "Use evidence that connects analysis to business or operational decisions instead of listing tools alone.",
        f"Frame your story around being ready to contribute inside {lead_path.company_type.lower()}." if lead_path else "Frame your story around measurable contribution.",
    ]
    resume_rewrite_points = _clean_string_list(
        llm_payload.get("resume_rewrite_points") if llm_payload else None,
        limit=5,
    ) or [
        f"Rewrite the summary to target {job_title} instead of a generic analytics profile.",
        "Add bullets that quantify business impact, stakeholder influence, and decision support.",
        "Mirror the JD's top requirements in project descriptions and ordering.",
        "Turn internship outcomes into evidence bullets when they directly match the JD requirements.",
    ]
    cover_letter_inputs = _clean_string_list(
        llm_payload.get("cover_letter_inputs") if llm_payload else None,
        limit=5,
    ) or [
        f"Explain why {lead_path.industry} is the strategic industry choice for you." if lead_path else "Explain why this market matters to you.",
        f"Show why {lead_company.name} is an attractive operating context." if lead_company else "Show why this employer context matters.",
        "Connect previous work to the exact business outcomes the JD seems to value.",
        "Reference internship work when it proves domain fit or early execution ability.",
    ]
    tailored_resume_bullets = _clean_string_list(
        llm_payload.get("tailored_resume_bullets") if llm_payload else None,
        limit=4,
    ) or _build_tailored_resume_bullets(
        profile,
        role_result,
        key_requirements,
        evidence_map,
    )
    why_this_role_answer = (
        str(llm_payload.get("why_this_role_answer", "")).strip()
        if llm_payload
        else ""
    ) or _build_why_this_role_answer(
        profile,
        lead_path,
        lead_company,
        job_title,
        match_confidence,
    )

    return JobTargetingResult(
        job_title=job_title,
        jd_summary=jd_summary,
        key_requirements=key_requirements,
        requirement_matches=requirement_matches,
        experience_alignment=experience_alignment,
        evidence_map=evidence_map,
        gap_analysis=gap_analysis or ["No major gaps detected from the deterministic screen."],
        positioning_strategy=positioning_strategy,
        resume_rewrite_points=resume_rewrite_points,
        cover_letter_inputs=cover_letter_inputs,
        tailored_resume_bullets=tailored_resume_bullets,
        why_this_role_answer=why_this_role_answer,
        match_confidence=match_confidence,
    )
