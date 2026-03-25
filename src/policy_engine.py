"""Policy and region stage for the career strategy pipeline."""

from __future__ import annotations

try:
    from .llm_client import generate_optional_json, generate_optional_text
    from .schemas import PolicyResult, UserProfile, ensure_user_profile
except ImportError:
    from llm_client import generate_optional_json, generate_optional_text
    from schemas import PolicyResult, UserProfile, ensure_user_profile


def _collect_policy_themes(user_profile: UserProfile) -> list[str]:
    combined_text = " ".join(
        user_profile.skills + user_profile.interests + [user_profile.target_role]
    ).lower()

    themes: list[str] = []
    if any(keyword in combined_text for keyword in {"ai", "machine learning", "ml", "llm"}):
        themes.append("National AI investment and enterprise AI adoption")
    if any(keyword in combined_text for keyword in {"health", "healthcare", "biotech"}):
        themes.append("Healthcare digitization and AI-enabled clinical workflows")
    if any(keyword in combined_text for keyword in {"energy", "climate", "sustainability"}):
        themes.append("Energy transition, grid modernization, and industrial efficiency")
    if any(keyword in combined_text for keyword in {"semiconductor", "chip", "manufacturing", "hardware"}):
        themes.append("Advanced manufacturing and semiconductor supply-chain incentives")
    if any(keyword in combined_text for keyword in {"analytics", "product", "saas", "experimentation"}):
        themes.append("Enterprise software productivity and decision intelligence")

    if not themes:
        themes.append("Broad digital transformation and analytics modernization")
    return themes


def _clean_string_list(value: object, limit: int | None = None) -> list[str]:
    if not isinstance(value, list):
        return []
    cleaned = [str(item).strip() for item in value if str(item).strip()]
    if limit is not None:
        return cleaned[:limit]
    return cleaned


def _deterministic_policy_result(profile: UserProfile) -> PolicyResult:
    recommended_regions = profile.preferred_regions[:] or ["US", "Canada", "UK"]
    constraints = profile.constraints[:]

    if profile.has_work_authorization:
        visa_risk = "low"
        mobility_strategy = "Can target local hiring markets first, then add selective global opportunities."
    elif profile.needs_visa_sponsorship:
        visa_risk = "high"
        mobility_strategy = (
            "Prioritize regions and employers with stronger sponsorship patterns, global mobility, "
            "or remote-compatible operating models."
        )
        constraints.append("Needs employer visa sponsorship")
    else:
        visa_risk = "medium"
        mobility_strategy = "Can pursue multiple regions, but should validate work authorization early."

    if profile.open_to_remote:
        constraints.append("Remote-friendly teams expand the opportunity set")
        if "Remote" not in recommended_regions:
            recommended_regions.append("Remote")

    if profile.needs_visa_sponsorship and not profile.has_work_authorization:
        recommended_regions = [
            region
            for region in recommended_regions
            if region in {"Canada", "UK", "Germany", "Singapore", "Remote"}
        ] or ["Canada", "UK", "Germany", "Singapore", "Remote"]

    priority_policy_themes = _collect_policy_themes(profile)
    opportunity_signals = [
        f"Policy tailwinds suggest prioritizing industries connected to: {priority_policy_themes[0]}.",
        f"Recommended regions to investigate first: {', '.join(recommended_regions)}.",
        "Use macro tailwinds to narrow industries before narrowing roles or specific employers.",
    ]
    return PolicyResult(
        visa_risk=visa_risk,
        mobility_strategy=mobility_strategy,
        recommended_regions=recommended_regions,
        priority_policy_themes=priority_policy_themes,
        constraints=sorted(set(constraints)),
        opportunity_signals=opportunity_signals,
        explanation=None,
    )


def run_policy_analysis(user_profile: UserProfile | dict[str, object]) -> PolicyResult:
    """Summarize region and policy constraints before industry selection."""
    profile = ensure_user_profile(user_profile)
    fallback_result = _deterministic_policy_result(profile)

    policy_prompt = f"""
You are the policy and geography strategist in a layered career planning system.

User profile:
{profile.to_dict()}

Deterministic fallback result:
{fallback_result}

Return strict JSON with this shape:
{{
  "visa_risk": "low|medium|high",
  "mobility_strategy": "2-3 sentences",
  "recommended_regions": ["region 1", "region 2"],
  "priority_policy_themes": ["theme 1", "theme 2"],
  "constraints": ["constraint 1", "constraint 2"],
  "opportunity_signals": ["signal 1", "signal 2", "signal 3"],
  "explanation": "3-4 concise sentences"
}}

Instructions:
- Be LLM-first: you may refine or replace the fallback if a better strategic framing exists.
- Keep the result realistic for data / analytics / AI career planning.
- Respect hard constraints such as work authorization, visa sponsorship, and remote openness.
- Prefer strategic themes over generic motivational advice.
- Only return valid JSON.
"""
    payload = generate_optional_json(policy_prompt, fallback=None, profile="balanced")

    explanation_prompt = f"""
You are summarizing policy and region implications for a layered career strategy system.

User profile:
{profile.to_dict()}

Return 3-4 concise sentences that explain:
1. mobility or visa risk
2. which regions to prioritize
3. which policy themes create opportunity
"""
    fallback_explanation = generate_optional_text(explanation_prompt, profile="creative")
    if not isinstance(payload, dict):
        fallback_result.explanation = fallback_explanation
        return fallback_result

    visa_risk = str(payload.get("visa_risk", "")).strip().lower()
    if visa_risk not in {"low", "medium", "high"}:
        visa_risk = fallback_result.visa_risk

    mobility_strategy = str(payload.get("mobility_strategy", "")).strip() or fallback_result.mobility_strategy
    recommended_regions = _clean_string_list(payload.get("recommended_regions"), limit=6) or fallback_result.recommended_regions
    priority_policy_themes = _clean_string_list(payload.get("priority_policy_themes"), limit=5) or fallback_result.priority_policy_themes
    constraints = sorted(
        set(
            fallback_result.constraints
            + _clean_string_list(payload.get("constraints"), limit=8)
        )
    )
    opportunity_signals = _clean_string_list(payload.get("opportunity_signals"), limit=4) or fallback_result.opportunity_signals
    explanation = str(payload.get("explanation", "")).strip() or fallback_explanation

    return PolicyResult(
        visa_risk=visa_risk,
        mobility_strategy=mobility_strategy,
        recommended_regions=recommended_regions,
        priority_policy_themes=priority_policy_themes,
        constraints=constraints,
        opportunity_signals=opportunity_signals,
        explanation=explanation,
    )
