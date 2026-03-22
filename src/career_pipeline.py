"""Orchestrator for the layered progressive career strategy system."""

from __future__ import annotations

from typing import Any

try:
    from .company_engine import run_company_strategy
    from .growth_engine import run_growth_plan
    from .industry_engine import run_industry_selection
    from .job_targeting_engine import run_job_targeting
    from .policy_engine import run_policy_analysis
    from .role_engine import run_role_path
    from .schemas import CareerState, UserProfile, create_initial_state
except ImportError:
    from company_engine import run_company_strategy
    from growth_engine import run_growth_plan
    from industry_engine import run_industry_selection
    from job_targeting_engine import run_job_targeting
    from policy_engine import run_policy_analysis
    from role_engine import run_role_path
    from schemas import CareerState, UserProfile, create_initial_state


def run_career_pipeline(
    user_profile: UserProfile | dict[str, Any],
    job_description: str = "",
) -> CareerState:
    """Run the policy -> industry -> company -> role -> job -> growth pipeline."""
    state = create_initial_state(user_profile, job_description=job_description.strip())

    state.policy_result = run_policy_analysis(state.user_profile)
    state.industry_result = run_industry_selection(state.user_profile, state.policy_result)
    state.company_result = run_company_strategy(
        state.user_profile,
        state.policy_result,
        state.industry_result,
    )
    state.role_result = run_role_path(
        state.user_profile,
        state.policy_result,
        state.industry_result,
        state.company_result,
    )

    if state.job_description:
        state.job_targeting_result = run_job_targeting(
            state.user_profile,
            state.policy_result,
            state.industry_result,
            state.company_result,
            state.role_result,
            state.job_description,
        )

    state.growth_result = run_growth_plan(
        state.user_profile,
        state.policy_result,
        state.industry_result,
        state.company_result,
        state.role_result,
        state.job_targeting_result,
    )

    return state
