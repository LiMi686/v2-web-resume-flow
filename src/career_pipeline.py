"""Unified career pipeline orchestration."""

from __future__ import annotations

try:
    from .industry_engine import run_industry_selection
    from .policy_engine import run_policy_analysis
    from .role_engine import run_role_selection
    from .schemas import CareerPipelineResult, UserProfile
except ImportError:
    from industry_engine import run_industry_selection
    from policy_engine import run_policy_analysis
    from role_engine import run_role_selection
    from schemas import CareerPipelineResult, UserProfile


def run_career_pipeline(user_profile: UserProfile) -> CareerPipelineResult:
    """Run the full career pipeline from policy to roles."""
    policy_result = run_policy_analysis(user_profile)
    industry_result = run_industry_selection(user_profile, policy_result)
    role_result = run_role_selection(user_profile, industry_result)

    return {
        "user_profile": user_profile,
        "policy_result": policy_result,
        "industry_result": industry_result,
        "role_result": role_result,
    }
