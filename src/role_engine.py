"""Role selection stage for the career pipeline."""

from __future__ import annotations

from typing import Any

try:
    from .industry_engine import INDUSTRY_KB
except ImportError:
    from industry_engine import INDUSTRY_KB


def run_role_selection(
    user_profile: dict[str, Any], industry_result: dict[str, Any]
) -> dict[str, Any]:
    """Map prioritized industries to role paths."""
    years_experience = float(user_profile.get("years_experience", 0) or 0)
    role_map = {industry["name"]: industry["roles"] for industry in INDUSTRY_KB}

    recommended_roles: list[dict[str, Any]] = []
    for industry in industry_result.get("top_industries", []):
        roles = role_map.get(industry["name"], {})
        if years_experience >= 4:
            priority_note = "Can push for ideal roles sooner."
        elif industry.get("recommendation") == "bridge role entry":
            priority_note = "Bridge role is the safest way to enter the industry."
        else:
            priority_note = "Can pursue direct entry while keeping bridge options open."

        recommended_roles.append(
            {
                "industry": industry["name"],
                "entry_path": industry.get("recommendation", "direct entry"),
                "ideal_role": roles.get("ideal"),
                "bridge_role": roles.get("bridge"),
                "stretch_role": roles.get("stretch"),
                "reason": priority_note,
            }
        )

    return {
        "recommended_roles": recommended_roles,
        "raw_text": "Roles are recommended after industry prioritization to improve long-term positioning.",
    }
