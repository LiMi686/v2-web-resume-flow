"""Ranking helpers for company discovery candidates."""

from __future__ import annotations

from dataclasses import replace

try:
    from .schemas import CompanySearchQuery, CompanyTarget, UserProfile
except ImportError:
    from schemas import CompanySearchQuery, CompanyTarget, UserProfile

DEFAULT_STAGE_PREFERENCE = ["Series A", "Series B", "Growth-stage"]


def _stage_score(stage: str, preferred_stages: list[str]) -> tuple[float, list[str]]:
    normalized_stage = stage.lower()
    reasons: list[str] = []

    for preferred in preferred_stages or DEFAULT_STAGE_PREFERENCE:
        preferred_lower = preferred.lower()
        if preferred_lower in normalized_stage:
            reasons.append(f"Matches preferred company stage: {preferred}")
            return 3.0, reasons

    if "growth" in normalized_stage:
        reasons.append("Growth-stage company, which is still closer to early expansion than mature incumbents.")
        return 2.2, reasons
    if "public" in normalized_stage or "mature" in normalized_stage:
        reasons.append("Mature company offers stronger stability but is less aligned with A/B-stage preference.")
        return 0.8, reasons
    return 1.2, reasons


def rank_company_candidates(
    candidates: list[CompanyTarget],
    query: CompanySearchQuery,
    user_profile: UserProfile,
) -> list[CompanyTarget]:
    """Assign fit scores and sort company candidates."""
    ranked_candidates: list[CompanyTarget] = []
    target_role_text = user_profile.target_role.lower()

    for candidate in candidates:
        score = 0.0
        reasons: list[str] = []

        score += 4.0
        reasons.append(f"Retrieved from the prioritized industry: {candidate.industry}.")

        stage_score, stage_reasons = _stage_score(candidate.stage, query.preferred_stages)
        score += stage_score
        reasons.extend(stage_reasons)

        if candidate.region and query.preferred_regions:
            if any(region.lower() in candidate.region.lower() for region in query.preferred_regions):
                score += 1.8
                reasons.append(f"Region aligns with preference: {candidate.region}.")
            elif query.open_to_remote and "remote" in candidate.region.lower():
                score += 1.4
                reasons.append("Remote option helps widen the search despite region mismatch.")

        if candidate.hiring_signal:
            score += 1.0
            reasons.append(f"Hiring signal: {candidate.hiring_signal}.")

        if candidate.international_environment:
            if candidate.international_environment in {"high", "medium-high"}:
                score += 0.8
                reasons.append("International operating context can widen communication patterns and mobility options.")
            elif candidate.international_environment == "medium":
                score += 0.4
                reasons.append("Moderate international exposure may still support broader collaboration experience.")

        candidate_text = " ".join(
            [candidate.company_type, candidate.focus, candidate.name, candidate.orientation]
        ).lower()
        if "analyst" in target_role_text and any(
            token in candidate_text for token in {"analytics", "product", "workflow", "operations"}
        ):
            score += 1.2
            reasons.append("Company context fits an analytics-first bridge role.")
        if "scientist" in target_role_text and any(
            token in candidate_text for token in {"ai", "model", "optimization", "intelligence"}
        ):
            score += 1.2
            reasons.append("Company context supports a data-science-heavy trajectory.")

        if candidate.orientation == "technical" and any(
            token in target_role_text for token in {"scientist", "ml", "engineer"}
        ):
            score += 0.8
            reasons.append("Technical orientation fits a model- or systems-heavy path.")
        if candidate.orientation == "business" and "analyst" in target_role_text:
            score += 0.8
            reasons.append("Business-facing operating model fits an analyst role centered on decisions.")

        if user_profile.needs_visa_sponsorship and (
            "global" in candidate.region.lower() or "remote" in candidate.region.lower()
        ):
            score += 0.8
            reasons.append("Global or remote context may reduce mobility friction.")
        if user_profile.needs_visa_sponsorship and candidate.visa_support_likelihood:
            if candidate.visa_support_likelihood in {"medium-high", "high"}:
                score += 0.9
                reasons.append("Profile indicates a comparatively better chance of visa support.")
            elif candidate.visa_support_likelihood == "medium":
                score += 0.4
                reasons.append("Visa support is not guaranteed, but the context looks more viable than average.")

        ranked_candidates.append(
            replace(
                candidate,
                fit_score=round(score, 2),
                why_match=reasons,
            )
        )

    ranked_candidates.sort(key=lambda item: item.fit_score, reverse=True)
    return ranked_candidates
