"""Legacy helper for free-form policy analysis prompts."""

try:
    from .llm_client import generate_text
except ImportError:
    from llm_client import generate_text


def analyze_policy_sources(policy_text: str, target_role: str) -> str:
    """Return a free-form policy analysis summary for a target role."""
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
    return generate_text(prompt)
