"""Industry selection stage for the career pipeline."""

from __future__ import annotations

from typing import Any

try:
    from .llm_client import generate_text
except ImportError:
    from llm_client import generate_text

INDUSTRY_KB = [
    {
        "name": "Healthcare AI",
        "attractiveness": 9,
        "entry_friendliness": 6,
        "visa_friendliness": 6,
        "skills": {"python", "sql", "machine learning", "analytics", "healthcare"},
        "roles": {
            "ideal": "Healthcare Data Scientist",
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
        "roles": {
            "ideal": "Product Data Scientist",
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
        "roles": {
            "ideal": "Product Analyst",
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
        "roles": {
            "ideal": "Energy Data Scientist",
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
        "roles": {
            "ideal": "Manufacturing Data Scientist",
            "bridge": "Process Data Analyst",
            "stretch": "Computer Vision Engineer",
        },
    },
]


def _as_lower_set(value: Any) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, list):
        items = value
    elif isinstance(value, str):
        items = value.split(",")
    else:
        items = [value]
    return {str(item).strip().lower() for item in items if str(item).strip()}


def _safe_generate_text(prompt: str) -> str | None:
    try:
        return generate_text(prompt)
    except Exception:
        return None


def run_industry_selection(
    user_profile: dict[str, Any], policy_result: dict[str, Any]
) -> dict[str, Any]:
    """Rank industries before final role selection."""
    user_skills = _as_lower_set(user_profile.get("skills"))
    user_interests = _as_lower_set(user_profile.get("interests"))
    combined_profile = user_skills | user_interests
    visa_risk = str(policy_result.get("visa_risk", "medium")).lower()

    ranked_industries: list[dict[str, Any]] = []
    for industry in INDUSTRY_KB:
        overlap = len(combined_profile & industry["skills"])
        skill_fit = min(overlap * 3, 10)
        visa_score = industry["visa_friendliness"]
        if visa_risk == "high":
            visa_score = max(0, visa_score - 2)

        score = (
            industry["attractiveness"] * 0.4
            + skill_fit * 0.3
            + industry["entry_friendliness"] * 0.2
            + visa_score * 0.1
        )

        if score >= 7.5 and skill_fit >= 5:
            recommendation = "direct entry"
        elif score >= 6:
            recommendation = "bridge role entry"
        else:
            recommendation = "lower priority"

        reason = (
            f"Growth outlook={industry['attractiveness']}/10, "
            f"skill fit={skill_fit}/10, "
            f"entry friendliness={industry['entry_friendliness']}/10, "
            f"visa friendliness adjusted={visa_score}/10."
        )
        ranked_industries.append(
            {
                "name": industry["name"],
                "score": round(score, 2),
                "reason": reason,
                "recommendation": recommendation,
            }
        )

    ranked_industries.sort(key=lambda item: item["score"], reverse=True)
    top_industries = ranked_industries[:3]

    explanation_prompt = f"""
You are helping with industry selection before role selection.

User profile:
{user_profile}

Policy result:
{policy_result}

Top industries:
{top_industries}

Briefly explain why prioritizing industry before role can be strategically useful.
"""
    raw_text = _safe_generate_text(explanation_prompt)

    return {
        "top_industries": top_industries,
        "raw_text": raw_text,
    }
