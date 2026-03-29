"""Policy and region stage for the career strategy pipeline."""

from __future__ import annotations

from typing import Any

try:
    from .llm_client import generate_grounded_json_strict, generate_json_strict
    from .schemas import GroundingSource, PolicyResult, UserProfile, ensure_user_profile
except ImportError:
    from llm_client import generate_grounded_json_strict, generate_json_strict
    from schemas import GroundingSource, PolicyResult, UserProfile, ensure_user_profile


def _clean_string_list(value: Any, limit: int | None = None) -> list[str]:
    if not isinstance(value, list):
        return []
    cleaned = [str(item).strip() for item in value if str(item).strip()]
    if limit is not None:
        return cleaned[:limit]
    return cleaned


def _clean_grounding_sources(value: Any, limit: int | None = None) -> list[GroundingSource]:
    if not isinstance(value, list):
        return []

    deduped_sources: list[GroundingSource] = []
    seen_uris: set[str] = set()
    for item in value:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", "")).strip()
        uri = str(item.get("uri", "")).strip()
        if not title and not uri:
            continue
        if uri and uri in seen_uris:
            continue
        if uri:
            seen_uris.add(uri)
        deduped_sources.append(GroundingSource(title=title, uri=uri))

    if limit is not None:
        return deduped_sources[:limit]
    return deduped_sources


def _policy_prompt(profile: UserProfile) -> str:
    return f"""
You are the policy and geography strategist in a layered career planning system.

User profile:
{profile.to_dict()}

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
- Results must be fully model-derived from the user profile.
- Keep the output realistic for data / analytics / AI career planning.
- Respect hard constraints such as work authorization, visa sponsorship, and remote openness.
- Recommended regions should stay concise and strategic, not exhaustive.
- Prefer policy and labor-market implications over generic motivational advice.
- Only return valid JSON.
"""


def _grounded_policy_prompt(profile: UserProfile) -> str:
    return f"""
You are the policy and geography strategist in a layered career planning system.

Use Google Search grounding to identify current policy and market signals that materially affect this user's career strategy.

User profile:
{profile.to_dict()}

Focus on current, decision-relevant signals such as:
- visa sponsorship, post-study work authorization, or cross-border hiring constraints
- industrial policy, public investment, digitization programs, and sector incentives
- regions where demand for data / analytics / AI talent appears strategically supported

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
- Results must be fully model-derived from grounded search and the user profile.
- Only make claims that can be supported by current search results.
- Keep recommended regions to at most 6.
- Prefer durable policy themes and structural labor-market signals over short-lived headlines.
- Respect hard constraints such as work authorization, visa sponsorship, and remote openness.
- Only return valid JSON.
"""


def _policy_result_from_payload(
    payload: dict[str, Any],
    *,
    analysis_mode: str,
) -> PolicyResult:
    visa_risk = str(payload.get("visa_risk", "")).strip().lower()
    if visa_risk not in {"low", "medium", "high"}:
        raise ValueError("Policy response must include visa_risk as low, medium, or high.")

    mobility_strategy = str(payload.get("mobility_strategy", "")).strip()
    recommended_regions = _clean_string_list(payload.get("recommended_regions"), limit=6)
    priority_policy_themes = _clean_string_list(payload.get("priority_policy_themes"), limit=5)
    opportunity_signals = _clean_string_list(payload.get("opportunity_signals"), limit=4)
    explanation = str(payload.get("explanation", "")).strip()

    if not mobility_strategy:
        raise ValueError("Policy response must include mobility_strategy.")
    if not recommended_regions:
        raise ValueError("Policy response must include recommended_regions.")
    if not priority_policy_themes:
        raise ValueError("Policy response must include priority_policy_themes.")
    if not opportunity_signals:
        raise ValueError("Policy response must include opportunity_signals.")
    if not explanation:
        raise ValueError("Policy response must include explanation.")

    grounding = payload.get("_grounding")
    grounding_queries = []
    grounding_sources: list[GroundingSource] = []
    if isinstance(grounding, dict):
        grounding_queries = _clean_string_list(grounding.get("queries"), limit=6)
        grounding_sources = _clean_grounding_sources(grounding.get("sources"), limit=6)

    return PolicyResult(
        visa_risk=visa_risk,
        mobility_strategy=mobility_strategy,
        recommended_regions=recommended_regions,
        priority_policy_themes=priority_policy_themes,
        constraints=_clean_string_list(payload.get("constraints"), limit=8),
        opportunity_signals=opportunity_signals,
        explanation=explanation,
        analysis_mode=analysis_mode,
        grounding_queries=grounding_queries,
        grounding_sources=grounding_sources,
    )


def run_policy_analysis(user_profile: UserProfile | dict[str, object]) -> PolicyResult:
    """Summarize region and policy constraints before industry selection."""
    profile = ensure_user_profile(user_profile)

    grounded_error: Exception | None = None
    try:
        grounded_payload = generate_grounded_json_strict(
            _grounded_policy_prompt(profile),
            profile="balanced",
        )
        return _policy_result_from_payload(
            grounded_payload,
            analysis_mode="gemini_grounded",
        )
    except Exception as exc:
        grounded_error = exc

    try:
        payload = generate_json_strict(
            _policy_prompt(profile),
            profile="balanced",
        )
        return _policy_result_from_payload(payload, analysis_mode="llm")
    except Exception as exc:
        raise RuntimeError(
            "Policy analysis failed in both grounded and non-grounded LLM modes. "
            f"grounded_error={grounded_error}; llm_error={exc}"
        ) from exc
