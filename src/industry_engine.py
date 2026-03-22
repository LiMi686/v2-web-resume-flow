"""Industry selection stage for the career strategy pipeline."""

from __future__ import annotations

from typing import Any

try:
    from .llm_client import generate_optional_text
    from .schemas import (
        IndustryRecommendation,
        IndustryResult,
        PolicyResult,
        UserProfile,
        ensure_user_profile,
    )
except ImportError:
    from llm_client import generate_optional_text
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


def run_industry_selection(
    user_profile: UserProfile | dict[str, Any], policy_result: PolicyResult
) -> IndustryResult:
    """Rank industries using skills, interests, and policy tailwinds."""
    profile = ensure_user_profile(user_profile)
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
            )
        )

    ranked_industries.sort(key=lambda item: item.score, reverse=True)
    top_industries = ranked_industries[:3]

    selection_logic = [
        "Industry is selected before role so the user can ride stronger policy and market tailwinds.",
        "Scoring combines macro attractiveness, current skill fit, entry friendliness, and visa friction.",
        "Top industries should feed company strategy before final role positioning.",
    ]

    explanation_prompt = f"""
You are explaining why industry should come before company and role in a career strategy system.

User profile:
{profile.to_dict()}

Policy result:
{policy_result}

Top industries:
{top_industries}

Return 3 concise sentences.
"""
    explanation = generate_optional_text(explanation_prompt)

    return IndustryResult(
        ranked_industries=ranked_industries,
        top_industries=top_industries,
        selection_logic=selection_logic,
        explanation=explanation,
    )
