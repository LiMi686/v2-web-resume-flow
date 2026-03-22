"""Legacy helper for free-form policy analysis prompts."""

from __future__ import annotations

try:
    from .llm_client import generate_optional_text
except ImportError:
    from llm_client import generate_optional_text


def _deterministic_policy_summary(policy_text: str, target_role: str) -> str:
    lower_text = policy_text.lower()
    industry_signals: list[str] = []
    if "health" in lower_text:
        industry_signals.append("Healthcare AI and digital health appear supported by the collected policy sources.")
    if "energy" in lower_text or "climate" in lower_text:
        industry_signals.append("Climate and energy technology show support through public investment and modernization themes.")
    if "semiconductor" in lower_text or "chips" in lower_text:
        industry_signals.append("Semiconductors and advanced manufacturing look strategically important in the policy landscape.")
    if "ai" in lower_text:
        industry_signals.append("Applied AI and enterprise automation appear to have broad macro support.")
    if not industry_signals:
        industry_signals.append("The policy sources point toward digital transformation and analytics-led sectors.")

    role_text = target_role.strip() or "Data / AI professional"
    relevant_roles = [
        f"{role_text} roles linked to industry transformation programs",
        "Industry-facing analyst or data scientist roles with strong domain context",
        "Bridge roles that combine analytics execution with operational decision support",
    ]
    skills_to_build = [
        "SQL and Python for practical analytics execution",
        "Domain knowledge in the policy-supported industries you choose",
        "Storytelling that connects data work to business or operational impact",
    ]
    job_search_suggestions = [
        "Use policy signals to narrow industries before narrowing job titles.",
        "Prioritize companies whose products or operations clearly benefit from the policy themes.",
        "Build resume bullets that show measurable impact, not just tool exposure.",
    ]

    return "\n".join(
        [
            "Industry Signals",
            *industry_signals,
            "",
            "Relevant Roles",
            *relevant_roles,
            "",
            "Skills to Build",
            *skills_to_build,
            "",
            "Job Search Suggestions",
            *job_search_suggestions,
        ]
    )


def analyze_policy_sources(policy_text: str, target_role: str) -> str:
    """Return a free-form policy analysis summary for a target role."""
    fallback = _deterministic_policy_summary(policy_text, target_role)
    prompt = f"""
You are a career strategy assistant for data and AI job seekers.

The user has collected policy-related sources. Based on these sources, identify:
1. the key industries or domains receiving support
2. the data / analytics / AI roles that may benefit
3. the skills the user should build
4. 3 practical job search suggestions

Target role:
{target_role}

Policy sources:
{policy_text}

Please return the answer with these section headers:
Industry Signals
Relevant Roles
Skills to Build
Job Search Suggestions
"""
    return generate_optional_text(prompt, fallback=fallback) or fallback
