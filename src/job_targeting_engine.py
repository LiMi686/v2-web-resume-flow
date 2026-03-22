"""Job alignment stage for the career strategy pipeline."""

from __future__ import annotations

import re
from typing import Any

try:
    from .schemas import (
        CompanyStrategyResult,
        JobTargetingResult,
        RequirementMatch,
        RolePathResult,
        UserProfile,
        ensure_user_profile,
    )
except ImportError:
    from schemas import (
        CompanyStrategyResult,
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
    key_requirements = _extract_requirements(job_description)

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
    lead_company = company_result.shortlisted_companies[0] if company_result.shortlisted_companies else None
    experience_alignment = [
        f"Target role path is {lead_path.role_title} in {lead_path.industry}." if lead_path else "Role path has not been selected.",
        f"Company strategy centers on {lead_company.company_type.lower()}." if lead_company else "No company strategy shortlist available.",
        f"User brings {profile.years_experience:g} years of experience plus skills in {', '.join(profile.skills[:4]) or 'foundational analytics'}."
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
        "The JD appears to value a mix of technical execution, business communication, and role-specific domain context."
    )
    positioning_strategy = [
        "Lead with industry context first, then show why your skills fit this role inside that market.",
        "Use evidence that connects analysis to business or operational decisions instead of listing tools alone.",
        f"Frame your story around being ready to contribute inside {lead_path.company_type.lower()}." if lead_path else "Frame your story around measurable contribution.",
    ]
    resume_rewrite_points = [
        f"Rewrite the summary to target {job_title} instead of a generic analytics profile.",
        "Add bullets that quantify business impact, stakeholder influence, and decision support.",
        "Mirror the JD's top requirements in project descriptions and ordering.",
    ]
    cover_letter_inputs = [
        f"Explain why {lead_path.industry} is the strategic industry choice for you." if lead_path else "Explain why this market matters to you.",
        f"Show why {lead_company.name} is an attractive operating context." if lead_company else "Show why this employer context matters.",
        "Connect previous work to the exact business outcomes the JD seems to value.",
    ]

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
        match_confidence=match_confidence,
    )
