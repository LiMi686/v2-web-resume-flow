"""Industry selection stage for the career strategy pipeline."""

from __future__ import annotations

from typing import Any

try:
    from .llm_client import generate_json_strict
    from .schemas import (
        IndustryRecommendation,
        IndustryResult,
        PolicyResult,
        UserProfile,
        ensure_user_profile,
    )
except ImportError:
    from llm_client import generate_json_strict
    from schemas import (
        IndustryRecommendation,
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


def _sanitize_score(raw_score: object) -> float:
    try:
        score = float(raw_score)
    except (TypeError, ValueError):
        raise ValueError("Industry score must be numeric.")
    return round(max(0.0, min(score, 10.0)), 2)


def _industry_from_payload(item: dict[str, Any]) -> IndustryRecommendation:
    name = str(item.get("name", "")).strip()
    recommendation = str(item.get("recommendation", "")).strip().lower()
    why_now = str(item.get("why_now", "")).strip()
    market_stage = str(item.get("market_stage", "")).strip()
    trend_summary = str(item.get("trend_summary", "")).strip()
    long_term_growth = str(item.get("long_term_growth", "")).strip()
    personalized_reason = str(item.get("personalized_reason", "")).strip()
    company_strategy_hint = str(item.get("company_strategy_hint", "")).strip()

    if recommendation not in {
        "direct priority",
        "build bridge role path",
        "monitor as secondary option",
    }:
        raise ValueError(f"Invalid industry recommendation label: {recommendation}")

    if not all(
        [
            name,
            why_now,
            market_stage,
            trend_summary,
            long_term_growth,
            personalized_reason,
            company_strategy_hint,
        ]
    ):
        raise ValueError("Industry response is missing required descriptive fields.")

    key_skills = _clean_string_list(item.get("key_skills"), limit=6)
    policy_alignment = _clean_string_list(item.get("policy_alignment"), limit=5)
    sample_companies = _clean_string_list(item.get("sample_companies"), limit=5)
    entry_barriers = _clean_string_list(item.get("entry_barriers"), limit=5)

    if not key_skills:
        raise ValueError(f"Industry {name} is missing key_skills.")
    if not policy_alignment:
        raise ValueError(f"Industry {name} is missing policy_alignment.")

    return IndustryRecommendation(
        name=name,
        score=_sanitize_score(item.get("score")),
        recommendation=recommendation,
        why_now=why_now,
        key_skills=key_skills,
        policy_alignment=policy_alignment,
        company_strategy_hint=company_strategy_hint,
        market_stage=market_stage,
        sample_companies=sample_companies,
        trend_summary=trend_summary,
        entry_barriers=entry_barriers,
        long_term_growth=long_term_growth,
        personalized_reason=personalized_reason,
    )


def run_industry_selection(
    user_profile: UserProfile | dict[str, Any], policy_result: PolicyResult
) -> IndustryResult:
    """Rank industries using the LLM's synthesis of profile and policy context."""
    profile = ensure_user_profile(user_profile)
    industry_prompt = f"""
You are the industry prioritization strategist in a layered career planning system.

User profile:
{profile.to_dict()}

Policy result:
{policy_result}

Return strict JSON with this shape:
{{
  "ranked_industries": [
    {{
      "name": "industry name",
      "score": 8.4,
      "recommendation": "direct priority|build bridge role path|monitor as secondary option",
      "why_now": "1-2 sentences",
      "key_skills": ["skill 1", "skill 2"],
      "policy_alignment": ["theme 1", "theme 2"],
      "company_strategy_hint": "what company type to target",
      "market_stage": "1-2 sentences",
      "sample_companies": ["company 1", "company 2"],
      "trend_summary": "1-2 sentences",
      "entry_barriers": ["barrier 1", "barrier 2"],
      "long_term_growth": "1-2 sentences",
      "personalized_reason": "why this user fits"
    }}
  ],
  "selection_logic": ["logic 1", "logic 2", "logic 3"],
  "explanation": "3 concise sentences"
}}

Instructions:
- Results must be fully model-derived from the profile and policy result.
- Return between 4 and 6 ranked industries.
- Stay realistic for data / analytics / AI career paths.
- Prefer specific industries over vague labels like "tech".
- Rank industries by a mix of demand, entry viability, sponsorship realism, and long-term option value.
- Only return valid JSON.
"""
    payload = generate_json_strict(industry_prompt, profile="balanced")

    raw_ranked = payload.get("ranked_industries")
    if not isinstance(raw_ranked, list):
        raise ValueError("Industry response must include ranked_industries.")

    ranked_industries: list[IndustryRecommendation] = []
    for item in raw_ranked:
        if not isinstance(item, dict):
            continue
        ranked_industries.append(_industry_from_payload(item))

    if len(ranked_industries) < 3:
        raise ValueError("Industry response must include at least 3 valid industries.")

    ranked_industries.sort(key=lambda item: item.score, reverse=True)
    selection_logic = _clean_string_list(payload.get("selection_logic"), limit=5)
    explanation = str(payload.get("explanation", "")).strip()
    if not selection_logic:
        raise ValueError("Industry response must include selection_logic.")
    if not explanation:
        raise ValueError("Industry response must include explanation.")

    return IndustryResult(
        ranked_industries=ranked_industries,
        top_industries=ranked_industries[:3],
        selection_logic=selection_logic,
        explanation=explanation,
    )
