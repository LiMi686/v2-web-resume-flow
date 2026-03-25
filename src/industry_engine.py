"""Industry selection stage for the career strategy pipeline."""

from __future__ import annotations

from typing import Any

try:
    from .llm_client import generate_optional_json, generate_optional_text
    from .schemas import (
        IndustryRecommendation,
        IndustryResult,
        PolicyResult,
        UserProfile,
        ensure_user_profile,
    )
except ImportError:
    from llm_client import generate_optional_json, generate_optional_text
    from schemas import (
        IndustryRecommendation,
        IndustryResult,
        PolicyResult,
        UserProfile,
        ensure_user_profile,
    )

INDUSTRY_KB = [
    {
        "name": "Healthcare AI",
        "attractiveness": 9,
        "entry_friendliness": 6,
        "visa_friendliness": 6,
        "skills": {"python", "sql", "machine learning", "analytics", "healthcare"},
        "interests": {"healthcare", "biotech", "patient", "clinical"},
        "policy_keywords": {"ai", "healthcare", "digital", "clinical"},
        "policy_alignment": [
            "Healthcare digitization budgets",
            "AI-enabled clinical workflow adoption",
            "Data infrastructure modernization",
        ],
        "company_types": [
            "Clinical AI platform companies",
            "Healthcare data infrastructure vendors",
            "Provider workflow software companies",
        ],
        "market_stage": "Incumbents are digitizing while AI-native specialists open new workflow wedges.",
        "sample_companies": ["Tempus", "Abridge", "Flatiron Health"],
        "roles": {
            "direct": "Healthcare Data Scientist",
            "bridge": "Healthcare Data Analyst",
            "stretch": "Applied AI Scientist",
        },
    },
    {
        "name": "Fintech",
        "attractiveness": 8,
        "entry_friendliness": 7,
        "visa_friendliness": 5,
        "skills": {"python", "sql", "analytics", "risk", "experimentation"},
        "interests": {"fintech", "payments", "risk", "banking"},
        "policy_keywords": {"ai", "digital", "productivity", "analytics"},
        "policy_alignment": [
            "Digital financial operations",
            "Risk automation and trust infrastructure",
            "Product analytics and growth efficiency",
        ],
        "company_types": [
            "Payments and infrastructure platforms",
            "Risk and fraud analytics companies",
            "Finance operations automation companies",
        ],
        "market_stage": "The sector keeps rewarding companies that reduce friction, fraud, and manual finance work.",
        "sample_companies": ["Stripe", "Plaid", "Ramp"],
        "roles": {
            "direct": "Product Data Scientist",
            "bridge": "Business Intelligence Analyst",
            "stretch": "Fraud ML Engineer",
        },
    },
    {
        "name": "Enterprise SaaS",
        "attractiveness": 8,
        "entry_friendliness": 8,
        "visa_friendliness": 6,
        "skills": {"python", "sql", "dashboarding", "experimentation", "analytics"},
        "interests": {"ai products", "saas", "b2b", "product"},
        "policy_keywords": {"ai", "productivity", "digital", "analytics"},
        "policy_alignment": [
            "Enterprise productivity demand",
            "AI copilots and workflow automation",
            "Decision intelligence in software platforms",
        ],
        "company_types": [
            "Product-led SaaS platforms",
            "AI-native workflow software companies",
            "Infrastructure and observability vendors",
        ],
        "market_stage": "AI is reshaping product design, analytics ownership, and software buyer expectations.",
        "sample_companies": ["Datadog", "HubSpot", "Notion"],
        "roles": {
            "direct": "Product Analyst",
            "bridge": "Data Analyst",
            "stretch": "Senior Product Data Scientist",
        },
    },
    {
        "name": "Climate and Energy Tech",
        "attractiveness": 9,
        "entry_friendliness": 6,
        "visa_friendliness": 7,
        "skills": {"python", "sql", "forecasting", "optimization", "analytics"},
        "interests": {"climate", "energy", "sustainability", "industrial"},
        "policy_keywords": {"energy", "climate", "manufacturing", "grid"},
        "policy_alignment": [
            "Energy transition and grid modernization",
            "Industrial efficiency and optimization",
            "Public-private climate investment",
        ],
        "company_types": [
            "Grid and energy analytics companies",
            "Industrial optimization platforms",
            "Climate software and infrastructure companies",
        ],
        "market_stage": "Policy support and infrastructure investment are expanding demand for data-heavy operations roles.",
        "sample_companies": ["Aurora Solar", "AutoGrid", "Stem"],
        "roles": {
            "direct": "Energy Data Scientist",
            "bridge": "Operations Analyst",
            "stretch": "Optimization ML Engineer",
        },
    },
    {
        "name": "Semiconductors and Advanced Manufacturing",
        "attractiveness": 9,
        "entry_friendliness": 5,
        "visa_friendliness": 5,
        "skills": {"python", "statistics", "quality", "forecasting", "automation"},
        "interests": {"semiconductor", "manufacturing", "hardware", "supply chain"},
        "policy_keywords": {"manufacturing", "semiconductor", "chip", "supply"},
        "policy_alignment": [
            "CHIPS-style industrial policy",
            "Supply-chain resilience",
            "Factory automation and yield optimization",
        ],
        "company_types": [
            "Chip design and platform companies",
            "Semiconductor equipment companies",
            "Advanced manufacturing analytics teams",
        ],
        "market_stage": "Industrial policy and compute demand are strengthening the full semiconductor value chain.",
        "sample_companies": ["NVIDIA", "ASML", "Applied Materials"],
        "roles": {
            "direct": "Manufacturing Data Scientist",
            "bridge": "Process Data Analyst",
            "stretch": "Computer Vision Engineer",
        },
    },
]


def _as_lower_set(values: list[str]) -> set[str]:
    return {value.strip().lower() for value in values if value.strip()}


def _policy_fit_score(industry: dict[str, Any], policy_result: PolicyResult) -> int:
    policy_text = " ".join(policy_result.priority_policy_themes).lower()
    hits = sum(1 for keyword in industry["policy_keywords"] if keyword in policy_text)
    return min(hits * 3, 10)


def _recommendation_for_score(score: float, skill_fit: int) -> str:
    if score >= 7.8 and skill_fit >= 4:
        return "direct priority"
    if score >= 6.4:
        return "build bridge role path"
    return "monitor as secondary option"


def _trend_summary(industry: dict[str, Any]) -> str:
    return (
        f"{industry['market_stage']} Current momentum is reinforced by "
        f"{', '.join(industry['policy_alignment'][:2])}."
    )


def _entry_barriers(
    industry: dict[str, Any],
    profile: UserProfile,
    policy_result: PolicyResult,
    skill_overlap: int,
) -> list[str]:
    barriers = [
        f"This path usually rewards candidates who already show evidence in {', '.join(sorted(industry['skills'])[:3])}.",
    ]
    if skill_overlap < 2:
        barriers.append("Current skill overlap is still shallow, so a bridge role or stronger portfolio proof may be needed.")
    if industry["entry_friendliness"] <= 5:
        barriers.append("Entry is less forgiving because domain fluency and execution proof matter early.")
    if policy_result.visa_risk == "high" and industry["visa_friendliness"] <= 5:
        barriers.append("Mobility friction may narrow employer options unless the company has a global or sponsorship-friendly setup.")
    if profile.years_experience < 1.5:
        barriers.append("Early-career candidates should emphasize internships, projects, and fast ramp potential.")
    return barriers[:4]


def _long_term_growth(industry: dict[str, Any]) -> str:
    if industry["attractiveness"] >= 9:
        return "Long-term upside is strong because the market has durable demand, strategic data problems, and room for role expansion."
    if industry["attractiveness"] >= 8:
        return "Long-term growth looks healthy, especially if you build domain depth and move closer to strategic decision workflows."
    return "Long-term growth exists, but it will depend more on company choice and the specific role scope."


def _personalized_reason(
    industry: dict[str, Any],
    profile: UserProfile,
    skill_overlap: int,
    interest_overlap: int,
) -> str:
    reasons: list[str] = []
    if skill_overlap:
        matched_skills = sorted(
            skill for skill in _as_lower_set(profile.skills) if skill in industry["skills"]
        )
        reasons.append(
            f"Your current toolkit already overlaps with this sector through {', '.join(matched_skills[:3]) or 'core analytics skills'}."
        )
    if interest_overlap:
        reasons.append("Your stated interests already point toward this market, which lowers the risk of pursuing a forced fit.")
    if profile.target_role:
        reasons.append(
            f"The industry also supports a credible path into {profile.target_role} via company environments that value applied analytics."
        )
    if not reasons:
        reasons.append("This is more of a strategic option than an obvious personal fit right now.")
    return " ".join(reasons[:3])


def _clean_string_list(value: Any, limit: int | None = None) -> list[str]:
    if not isinstance(value, list):
        return []
    cleaned = [str(item).strip() for item in value if str(item).strip()]
    if limit is not None:
        return cleaned[:limit]
    return cleaned


def _deterministic_industry_recommendations(
    profile: UserProfile,
    policy_result: PolicyResult,
) -> list[IndustryRecommendation]:
    user_skills = _as_lower_set(profile.skills)
    user_interests = _as_lower_set(profile.interests)
    visa_risk = policy_result.visa_risk.lower()

    ranked_industries: list[IndustryRecommendation] = []
    for industry in INDUSTRY_KB:
        skill_overlap = len(user_skills & industry["skills"])
        interest_overlap = len(user_interests & industry["interests"])
        skill_fit = min(skill_overlap * 2 + interest_overlap, 10)
        policy_fit = _policy_fit_score(industry, policy_result)
        visa_score = industry["visa_friendliness"]
        if visa_risk == "high":
            visa_score = max(0, visa_score - 2)

        score = (
            industry["attractiveness"] * 0.35
            + skill_fit * 0.30
            + industry["entry_friendliness"] * 0.15
            + policy_fit * 0.10
            + visa_score * 0.10
        )
        why_now = (
            f"{industry['market_stage']} Policy alignment comes from "
            f"{', '.join(industry['policy_alignment'][:2])}."
        )
        ranked_industries.append(
            IndustryRecommendation(
                name=industry["name"],
                score=round(score, 2),
                recommendation=_recommendation_for_score(score, skill_fit),
                why_now=why_now,
                key_skills=sorted(industry["skills"])[:5],
                policy_alignment=industry["policy_alignment"],
                company_strategy_hint=industry["company_types"][0],
                market_stage=industry["market_stage"],
                sample_companies=industry["sample_companies"],
                trend_summary=_trend_summary(industry),
                entry_barriers=_entry_barriers(industry, profile, policy_result, skill_overlap),
                long_term_growth=_long_term_growth(industry),
                personalized_reason=_personalized_reason(
                    industry,
                    profile,
                    skill_overlap,
                    interest_overlap,
                ),
            )
        )

    ranked_industries.sort(key=lambda item: item.score, reverse=True)
    return ranked_industries


def _sanitize_score(raw_score: object, fallback_score: float) -> float:
    try:
        score = float(raw_score)
    except (TypeError, ValueError):
        score = fallback_score
    return round(max(0.0, min(score, 10.0)), 2)


def _industry_from_payload(
    item: dict[str, Any],
    fallback_map: dict[str, IndustryRecommendation],
    profile: UserProfile,
) -> IndustryRecommendation | None:
    name = str(item.get("name", "")).strip()
    if not name:
        return None

    fallback = fallback_map.get(name)
    key_skills = _clean_string_list(item.get("key_skills"), limit=5) or (
        fallback.key_skills if fallback else profile.skills[:5]
    )
    policy_alignment = _clean_string_list(item.get("policy_alignment"), limit=4) or (
        fallback.policy_alignment if fallback else []
    )
    sample_companies = _clean_string_list(item.get("sample_companies"), limit=4) or (
        fallback.sample_companies if fallback else []
    )
    entry_barriers = _clean_string_list(item.get("entry_barriers"), limit=4) or (
        fallback.entry_barriers if fallback else []
    )
    market_stage = str(item.get("market_stage", "")).strip() or (
        fallback.market_stage
        if fallback
        else "This market offers enough strategic data and AI work to justify active exploration."
    )
    why_now = str(item.get("why_now", "")).strip() or (
        fallback.why_now
        if fallback
        else f"{market_stage} The sector appears relevant for the next career move."
    )
    trend_summary = str(item.get("trend_summary", "")).strip() or (
        fallback.trend_summary if fallback else why_now
    )
    long_term_growth = str(item.get("long_term_growth", "")).strip() or (
        fallback.long_term_growth
        if fallback
        else "Long-term upside depends on building domain fluency and visible business impact."
    )
    personalized_reason = str(item.get("personalized_reason", "")).strip() or (
        fallback.personalized_reason
        if fallback
        else "This industry has enough overlap with the profile to justify a focused exploration path."
    )
    recommendation = str(item.get("recommendation", "")).strip().lower() or (
        fallback.recommendation if fallback else "build bridge role path"
    )
    if recommendation not in {"direct priority", "build bridge role path", "monitor as secondary option"}:
        recommendation = fallback.recommendation if fallback else "build bridge role path"

    company_strategy_hint = str(item.get("company_strategy_hint", "")).strip() or (
        fallback.company_strategy_hint
        if fallback
        else "Target operating environments where analytics informs measurable decisions."
    )

    return IndustryRecommendation(
        name=name,
        score=_sanitize_score(item.get("score"), fallback.score if fallback else 6.5),
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
    """Rank industries using skills, interests, and policy tailwinds."""
    profile = ensure_user_profile(user_profile)
    fallback_ranked_industries = _deterministic_industry_recommendations(profile, policy_result)
    fallback_map = {industry.name: industry for industry in fallback_ranked_industries}
    fallback_selection_logic = [
        "Industry is selected before role so the user can ride stronger policy and market tailwinds.",
        "Scoring combines macro attractiveness, current skill fit, entry friendliness, and visa friction.",
        "Top industries should feed company strategy before final role positioning.",
    ]
    industry_prompt = f"""
You are the industry prioritization strategist in a layered career planning system.

User profile:
{profile.to_dict()}

Policy result:
{policy_result}

Deterministic baseline industries:
{fallback_ranked_industries}

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
- Be LLM-first: you may keep, reorder, refine, or replace baseline industries.
- Stay realistic for data / analytics / AI career paths.
- Prefer specific sectors over vague labels like "tech" or "business".
- Return between 4 and 6 ranked industries.
- Only return valid JSON.
"""
    payload = generate_optional_json(industry_prompt, fallback=None, profile="balanced")

    explanation_prompt = f"""
You are explaining why industry should come before company and role in a career strategy system.

User profile:
{profile.to_dict()}

Policy result:
{policy_result}

Top industries:
{fallback_ranked_industries[:3]}

Return 3 concise sentences.
"""
    fallback_explanation = generate_optional_text(explanation_prompt, profile="creative")

    ranked_industries = fallback_ranked_industries
    selection_logic = fallback_selection_logic
    explanation = fallback_explanation

    if isinstance(payload, dict):
        raw_ranked = payload.get("ranked_industries")
        if isinstance(raw_ranked, list):
            parsed_ranked: list[IndustryRecommendation] = []
            for item in raw_ranked:
                if not isinstance(item, dict):
                    continue
                parsed = _industry_from_payload(item, fallback_map, profile)
                if parsed is not None:
                    parsed_ranked.append(parsed)
            if parsed_ranked:
                ranked_industries = parsed_ranked

        selection_logic = (
            _clean_string_list(payload.get("selection_logic"), limit=4)
            or fallback_selection_logic
        )
        explanation = str(payload.get("explanation", "")).strip() or fallback_explanation

    ranked_industries.sort(key=lambda item: item.score, reverse=True)
    top_industries = ranked_industries[:3]

    return IndustryResult(
        ranked_industries=ranked_industries,
        top_industries=top_industries,
        selection_logic=selection_logic,
        explanation=explanation,
    )
