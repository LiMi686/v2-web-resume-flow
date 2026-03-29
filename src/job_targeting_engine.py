"""Job alignment stage for the career strategy pipeline."""

from __future__ import annotations

from typing import Any

try:
    from .llm_client import generate_json_strict
    from .schemas import (
        CompanyStrategyResult,
        JobTargetingResult,
        RequirementMatch,
        RolePathResult,
        UserProfile,
        ensure_user_profile,
    )
except ImportError:
    from llm_client import generate_json_strict
    from schemas import (
        CompanyStrategyResult,
        JobTargetingResult,
        RequirementMatch,
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


def _requirement_match_from_payload(item: dict[str, Any]) -> RequirementMatch:
    requirement = str(item.get("requirement", "")).strip()
    importance = str(item.get("importance", "")).strip().lower()
    matched = bool(item.get("matched"))
    evidence = _clean_string_list(item.get("evidence"), limit=5)
    gap_notes = _clean_string_list(item.get("gap_notes"), limit=4)

    if importance not in {"high", "medium", "low"}:
        raise ValueError(f"Invalid requirement importance: {importance}")
    if not requirement:
        raise ValueError("Requirement match is missing requirement.")

    return RequirementMatch(
        requirement=requirement,
        importance=importance,
        matched=matched,
        evidence=evidence,
        gap_notes=gap_notes,
    )


def run_job_targeting(
    user_profile: UserProfile | dict[str, Any],
    policy_result,
    industry_result,
    company_result: CompanyStrategyResult,
    role_result: RolePathResult,
    job_description: str,
) -> JobTargetingResult:
    """Convert a job description into alignment, evidence, and positioning guidance."""
    profile = ensure_user_profile(user_profile)
    prompt = f"""
You are helping with job alignment for a layered career strategy system.

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

Job description:
{job_description}

Return strict JSON with this shape:
{{
  "job_title": "specific job title",
  "jd_summary": "short paragraph",
  "key_requirements": ["requirement 1", "requirement 2"],
  "requirement_matches": [
    {{
      "requirement": "requirement text",
      "importance": "high|medium|low",
      "matched": true,
      "evidence": ["evidence 1", "evidence 2"],
      "gap_notes": ["gap note 1"]
    }}
  ],
  "experience_alignment": ["point 1", "point 2"],
  "evidence_map": {{
    "Requirement A": ["evidence 1", "evidence 2"]
  }},
  "gap_analysis": ["gap 1", "gap 2"],
  "positioning_strategy": ["point 1", "point 2", "point 3"],
  "resume_rewrite_points": ["point 1", "point 2", "point 3"],
  "cover_letter_inputs": ["point 1", "point 2", "point 3"],
  "tailored_resume_bullets": ["bullet 1", "bullet 2", "bullet 3"],
  "why_this_role_answer": "short answer",
  "match_confidence": "high|medium|low"
}}

Instructions:
- Results must be fully model-derived from the user's experience and the target JD.
- Use the user's internships, projects, and experience highlights as evidence when appropriate.
- Keep evidence grounded in information present in the profile.
- Only return valid JSON.
"""
    payload = generate_json_strict(prompt, profile="balanced")

    job_title = str(payload.get("job_title", "")).strip()
    jd_summary = str(payload.get("jd_summary", "")).strip()
    why_this_role_answer = str(payload.get("why_this_role_answer", "")).strip()
    match_confidence = str(payload.get("match_confidence", "")).strip().lower()
    if match_confidence not in {"high", "medium", "low"}:
        raise ValueError("Job targeting response must include match_confidence as high, medium, or low.")
    if not all([job_title, jd_summary, why_this_role_answer]):
        raise ValueError("Job targeting response is missing job_title, jd_summary, or why_this_role_answer.")

    key_requirements = _clean_string_list(payload.get("key_requirements"), limit=10)
    experience_alignment = _clean_string_list(payload.get("experience_alignment"), limit=6)
    gap_analysis = _clean_string_list(payload.get("gap_analysis"), limit=6)
    positioning_strategy = _clean_string_list(payload.get("positioning_strategy"), limit=5)
    resume_rewrite_points = _clean_string_list(payload.get("resume_rewrite_points"), limit=6)
    cover_letter_inputs = _clean_string_list(payload.get("cover_letter_inputs"), limit=6)
    tailored_resume_bullets = _clean_string_list(payload.get("tailored_resume_bullets"), limit=6)
    if not key_requirements:
        raise ValueError("Job targeting response must include key_requirements.")

    raw_requirement_matches = payload.get("requirement_matches")
    if not isinstance(raw_requirement_matches, list):
        raise ValueError("Job targeting response must include requirement_matches.")
    requirement_matches = [
        _requirement_match_from_payload(item)
        for item in raw_requirement_matches
        if isinstance(item, dict)
    ]
    if not requirement_matches:
        raise ValueError("Job targeting response must include at least one valid requirement match.")

    raw_evidence_map = payload.get("evidence_map")
    evidence_map: dict[str, list[str]] = {}
    if isinstance(raw_evidence_map, dict):
        for key, value in raw_evidence_map.items():
            cleaned_key = str(key).strip()
            cleaned_value = _clean_string_list(value, limit=5)
            if cleaned_key:
                evidence_map[cleaned_key] = cleaned_value

    if not evidence_map:
        evidence_map = {
            requirement_match.requirement: requirement_match.evidence
            for requirement_match in requirement_matches
        }

    return JobTargetingResult(
        job_title=job_title,
        jd_summary=jd_summary,
        key_requirements=key_requirements,
        requirement_matches=requirement_matches,
        experience_alignment=experience_alignment,
        evidence_map=evidence_map,
        gap_analysis=gap_analysis,
        positioning_strategy=positioning_strategy,
        resume_rewrite_points=resume_rewrite_points,
        cover_letter_inputs=cover_letter_inputs,
        tailored_resume_bullets=tailored_resume_bullets,
        why_this_role_answer=why_this_role_answer,
        match_confidence=match_confidence,
    )
