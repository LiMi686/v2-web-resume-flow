"""Company strategy stage for the career strategy pipeline."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

try:
    from .company_search_provider import get_company_search_provider
    from .llm_client import generate_json_strict
    from .schemas import (
        CompanyArchetypeAssessment,
        CompanySearchQuery,
        CompanyStrategyResult,
        CompanyTarget,
        IndustryResult,
        PolicyResult,
        UserProfile,
        ensure_user_profile,
    )
except ImportError:
    from company_search_provider import get_company_search_provider
    from llm_client import generate_json_strict
    from schemas import (
        CompanyArchetypeAssessment,
        CompanySearchQuery,
        CompanyStrategyResult,
        CompanyTarget,
        IndustryResult,
        PolicyResult,
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


def _build_search_query(
    profile: UserProfile,
    industry_result: IndustryResult,
) -> CompanySearchQuery:
    preferred_stages = list(profile.company_preferences.preferred_environments)
    if not preferred_stages:
        preferred_stages = [
            "Big Tech / platform company",
            "Series A-B startup",
            "Late-stage growth company",
            "Established operator or mission-driven organization",
        ]
    else:
        fallback_stages = [
            "Big Tech / platform company",
            "Series A-B startup",
            "Late-stage growth company",
            "Established operator or mission-driven organization",
        ]
        seen = {item.lower() for item in preferred_stages}
        preferred_stages.extend(
            stage for stage in fallback_stages if stage.lower() not in seen
        )
    return CompanySearchQuery(
        industries=[industry.name for industry in industry_result.top_industries],
        preferred_regions=profile.preferred_regions,
        target_roles=[profile.target_role] if profile.target_role else [],
        preferred_stages=preferred_stages,
        needs_visa_sponsorship=profile.needs_visa_sponsorship,
        open_to_remote=profile.open_to_remote,
    )


def _sanitize_company_score(raw_score: object, default: float = 10.0) -> float:
    try:
        score = float(raw_score)
    except (TypeError, ValueError):
        score = default
    return round(max(0.0, min(score, 20.0)), 2)


def _company_from_payload(
    item: dict[str, Any],
    retrieved_map: dict[str, CompanyTarget],
) -> CompanyTarget | None:
    name = str(item.get("name", "")).strip()
    if not name:
        return None

    reference = retrieved_map.get(name.lower())
    industry = str(item.get("industry", "")).strip() or (reference.industry if reference else "")
    company_type = str(item.get("company_type", "")).strip() or (
        reference.company_type if reference else "Strategic operating company"
    )
    stage = str(item.get("stage", "")).strip() or (reference.stage if reference else "Growth-stage")
    focus = str(item.get("focus", "")).strip() or (reference.focus if reference else "Data-rich workflows")
    why_now = str(item.get("why_now", "")).strip() or (
        reference.why_now if reference else "This company is strategically relevant right now."
    )
    if not industry or not company_type or not stage or not focus or not why_now:
        return None

    return CompanyTarget(
        industry=industry,
        name=name,
        company_type=company_type,
        stage=stage,
        focus=focus,
        why_now=why_now,
        region=str(item.get("region", "")).strip() or (reference.region if reference else ""),
        hiring_signal=str(item.get("hiring_signal", "")).strip()
        or (reference.hiring_signal if reference else ""),
        source=str(item.get("source", "")).strip() or (reference.source if reference else ""),
        fit_score=_sanitize_company_score(
            item.get("fit_score"),
            reference.fit_score if reference and reference.fit_score else 10.0,
        ),
        why_match=_clean_string_list(item.get("why_match"), limit=5)
        or (reference.why_match if reference else []),
        international_environment=str(item.get("international_environment", "")).strip()
        or (reference.international_environment if reference else "medium"),
        orientation=str(item.get("orientation", "")).strip()
        or (reference.orientation if reference else "balanced"),
        visa_support_likelihood=str(item.get("visa_support_likelihood", "")).strip()
        or (reference.visa_support_likelihood if reference else "low-medium"),
        user_fit_summary=str(item.get("user_fit_summary", "")).strip(),
        candidate_explanation=str(item.get("candidate_explanation", "")).strip(),
        role_value_potential=str(item.get("role_value_potential", "")).strip(),
    )


def _company_archetype_from_payload(item: dict[str, Any]) -> CompanyArchetypeAssessment | None:
    archetype = str(item.get("archetype", "")).strip()
    recommendation_level = str(item.get("recommendation_level", "")).strip()
    competitiveness_level = str(item.get("competitiveness_level", "")).strip()
    fit_rationale = _clean_string_list(item.get("fit_rationale"), limit=5)
    watchouts = _clean_string_list(item.get("watchouts"), limit=4)
    development_value = str(item.get("development_value", "")).strip()
    entry_strategy = str(item.get("entry_strategy", "")).strip()
    example_companies = _clean_string_list(item.get("example_companies"), limit=5)

    if not all(
        [
            archetype,
            recommendation_level,
            competitiveness_level,
            development_value,
            entry_strategy,
        ]
    ):
        return None
    if not fit_rationale:
        return None

    return CompanyArchetypeAssessment(
        archetype=archetype,
        recommendation_level=recommendation_level,
        competitiveness_level=competitiveness_level,
        fit_rationale=fit_rationale,
        watchouts=watchouts,
        development_value=development_value,
        entry_strategy=entry_strategy,
        example_companies=example_companies,
    )


def _dedupe_companies(companies: list[CompanyTarget], limit: int | None = None) -> list[CompanyTarget]:
    deduped: list[CompanyTarget] = []
    seen_names: set[str] = set()
    for company in companies:
        key = company.name.strip().lower()
        if not key or key in seen_names:
            continue
        seen_names.add(key)
        deduped.append(company)
    deduped.sort(key=lambda item: item.fit_score, reverse=True)
    if limit is not None:
        return deduped[:limit]
    return deduped


def _preference_snapshot(profile: UserProfile) -> dict[str, Any]:
    preferences = profile.company_preferences
    return {
        "preferred_environments": preferences.preferred_environments,
        "risk_tolerance": preferences.risk_tolerance,
        "stability_priority": preferences.stability_priority,
        "work_style_preference": preferences.work_style_preference,
        "brand_vs_growth_preference": preferences.brand_vs_growth_preference,
        "notes": preferences.notes,
    }


def _normalize_primary_company_path(
    raw_path: str,
    assessments: list[CompanyArchetypeAssessment],
) -> str:
    normalized_raw = raw_path.strip().lower()
    if normalized_raw:
        for assessment in assessments:
            archetype = assessment.archetype.strip()
            lowered = archetype.lower()
            if normalized_raw == lowered or normalized_raw in lowered or lowered in normalized_raw:
                return archetype

    for assessment in assessments:
        if assessment.recommendation_level.strip().lower() == "primary":
            return assessment.archetype
    if assessments:
        return assessments[0].archetype
    return raw_path.strip()


def run_company_strategy(
    user_profile: UserProfile | dict[str, Any],
    policy_result: PolicyResult,
    industry_result: IndustryResult,
) -> CompanyStrategyResult:
    """Convert prioritized industries into a company strategy layer."""
    profile = ensure_user_profile(user_profile)
    search_query = _build_search_query(profile, industry_result)
    provider = get_company_search_provider()
    retrieved_companies = provider.search(search_query)
    retrieved_map = {company.name.lower(): company for company in retrieved_companies}

    archetype_prompt = f"""
You are the company-archetype strategist in a layered career planning system.

User profile:
{profile.to_dict()}

Policy result:
{policy_result}

Industry result:
{industry_result}

Grounded retrieved companies:
{retrieved_companies}

Explicit company preferences:
{_preference_snapshot(profile)}

Return strict JSON with this shape:
{{
  "user_preference_summary": "what the user explicitly says they want",
  "preference_alignment_summary": "how those preferences align or conflict with profile competitiveness and constraints",
  "company_archetype_assessments": [
    {{
      "archetype": "Big Tech / platform company",
      "recommendation_level": "primary|secondary|stretch|deprioritize",
      "competitiveness_level": "strong|competitive|developing|weak",
      "fit_rationale": ["reason 1", "reason 2"],
      "watchouts": ["risk 1", "risk 2"],
      "development_value": "how this environment helps or hurts long-term growth",
      "entry_strategy": "how the user should approach this archetype right now",
      "example_companies": ["company 1", "company 2"]
    }}
  ],
  "primary_company_path": "single best near-term company path",
  "competitiveness_summary": "clear summary of current competitiveness across company archetypes",
  "development_recommendation": "what company environment the user should prioritize for best development"
}}

Instructions:
- Results must be fully model-derived from the profile, policy result, industry result, and grounded retrieval context.
- Take the explicit company preferences seriously, but do not follow them blindly when they conflict with competitiveness, sponsorship reality, or development logic.
- Return exactly 4 company_archetype_assessments covering these four options in order:
  1. Big Tech / platform company
  2. Series A-B startup
  3. Late-stage growth company
  4. Established operator or mission-driven organization
- Use `deprioritize` when an archetype is a poor current bet for this candidate.
- Choose `primary_company_path` based on both near-term competitiveness and long-term development value, not prestige alone.
- Only return valid JSON.
"""
    archetype_payload = generate_json_strict(archetype_prompt, profile="balanced")
    raw_archetypes = archetype_payload.get("company_archetype_assessments")
    if not isinstance(raw_archetypes, list):
        raise ValueError("Company strategy response must include company_archetype_assessments.")

    company_archetype_assessments: list[CompanyArchetypeAssessment] = []
    for item in raw_archetypes:
        if not isinstance(item, dict):
            continue
        parsed_archetype = _company_archetype_from_payload(item)
        if parsed_archetype is not None:
            company_archetype_assessments.append(parsed_archetype)

    if len(company_archetype_assessments) < 3:
        raise ValueError(
            "Company strategy response must include at least three valid company_archetype_assessments."
        )

    user_preference_summary = str(archetype_payload.get("user_preference_summary", "")).strip()
    preference_alignment_summary = str(
        archetype_payload.get("preference_alignment_summary", "")
    ).strip()
    raw_primary_company_path = str(archetype_payload.get("primary_company_path", "")).strip()
    primary_company_path = _normalize_primary_company_path(
        raw_primary_company_path,
        company_archetype_assessments,
    )
    competitiveness_summary = str(archetype_payload.get("competitiveness_summary", "")).strip()
    development_recommendation = str(archetype_payload.get("development_recommendation", "")).strip()
    if (
        not user_preference_summary
        or not preference_alignment_summary
        or not primary_company_path
        or not competitiveness_summary
        or not development_recommendation
    ):
        raise ValueError(
            "Company strategy response must include preference summaries, primary_company_path, competitiveness_summary, and development_recommendation."
        )

    company_prompt = f"""
You are the company strategy layer in a layered career planning system.

User profile:
{profile.to_dict()}

Policy result:
{policy_result}

Industry result:
{industry_result}

Grounded retrieved companies:
{retrieved_companies}

Explicit company preferences:
{_preference_snapshot(profile)}

Company archetype assessment:
{company_archetype_assessments}

User preference summary:
{user_preference_summary}

Preference alignment summary:
{preference_alignment_summary}

Recommended company path:
{primary_company_path}

Development recommendation:
{development_recommendation}

Return strict JSON with this shape:
{{
  "discovery_strategy": ["step 1", "step 2", "step 3"],
  "target_company_types": ["type 1", "type 2"],
  "company_selection_rules": ["rule 1", "rule 2"],
  "ranking_logic": ["logic 1", "logic 2"],
  "industry_analysis": ["point 1", "point 2"],
  "market_analysis": ["point 1", "point 2"],
  "value_chain_analysis": ["point 1", "point 2"],
  "competitor_map": ["cluster 1", "cluster 2"],
  "shortlisted_companies": [
    {{
      "industry": "industry name",
      "name": "company name",
      "company_type": "type",
      "stage": "Growth-stage",
      "focus": "what the company does",
      "why_now": "why it matters now",
      "region": "region",
      "hiring_signal": "why it is relevant for hiring",
      "source": "where this came from",
      "fit_score": 11.2,
      "why_match": ["reason 1", "reason 2"],
      "international_environment": "high|medium-high|medium|low",
      "orientation": "technical|business|balanced",
      "visa_support_likelihood": "high|medium-high|medium|low-medium|low",
      "user_fit_summary": "short fit summary",
      "candidate_explanation": "candidate-facing explanation",
      "role_value_potential": "career value potential"
    }}
  ],
  "why_these_companies": ["reason 1", "reason 2", "reason 3"],
  "candidate_facing_takeaways": ["takeaway 1", "takeaway 2", "takeaway 3"],
  "explanation": "3 concise sentences"
}}

Instructions:
- Results must be fully model-derived from the profile, policy result, industry result, and grounded retrieval context.
- Select at most 6 shortlisted companies from the retrieved list.
- Let the shortlist reflect both the user's stated preferences and the system's corrected recommendation when they differ.
- Make the shortlist consistent with the recommended company path while still showing useful adjacent options.
- Favor companies where data work has first-year strategic visibility.
- Only return valid JSON.
"""
    payload = generate_json_strict(company_prompt, profile="balanced")
    raw_shortlist = payload.get("shortlisted_companies")
    if not isinstance(raw_shortlist, list):
        raise ValueError("Company strategy response must include shortlisted_companies.")

    shortlisted_companies: list[CompanyTarget] = []
    for item in raw_shortlist:
        if not isinstance(item, dict):
            continue
        parsed_company = _company_from_payload(item, retrieved_map)
        if parsed_company is not None:
            shortlisted_companies.append(parsed_company)

    shortlisted_companies = _dedupe_companies(shortlisted_companies, limit=6)
    if not shortlisted_companies:
        raise ValueError("Company strategy response must include at least one valid shortlisted company.")

    # Preserve grounded retrieval details while letting the model define strategy and shortlist.
    retrieved_companies = _dedupe_companies(
        [
            replace(
                company,
                fit_score=company.fit_score or 10.0,
            )
            for company in retrieved_companies
        ],
        limit=12,
    )

    explanation = str(payload.get("explanation", "")).strip()
    if not explanation:
        raise ValueError("Company strategy response must include explanation.")

    return CompanyStrategyResult(
        user_preference_summary=user_preference_summary,
        preference_alignment_summary=preference_alignment_summary,
        discovery_strategy=_clean_string_list(payload.get("discovery_strategy"), limit=5),
        target_company_types=_clean_string_list(payload.get("target_company_types"), limit=6),
        company_selection_rules=_clean_string_list(payload.get("company_selection_rules"), limit=6),
        company_archetype_assessments=company_archetype_assessments,
        primary_company_path=primary_company_path,
        competitiveness_summary=competitiveness_summary,
        development_recommendation=development_recommendation,
        ranking_logic=_clean_string_list(payload.get("ranking_logic"), limit=5),
        industry_analysis=_clean_string_list(payload.get("industry_analysis"), limit=6),
        market_analysis=_clean_string_list(payload.get("market_analysis"), limit=6),
        value_chain_analysis=_clean_string_list(payload.get("value_chain_analysis"), limit=6),
        competitor_map=_clean_string_list(payload.get("competitor_map"), limit=6),
        retrieved_companies=retrieved_companies,
        shortlisted_companies=shortlisted_companies,
        why_these_companies=_clean_string_list(payload.get("why_these_companies"), limit=6),
        candidate_facing_takeaways=_clean_string_list(
            payload.get("candidate_facing_takeaways"),
            limit=5,
        ),
        explanation=explanation,
    )
