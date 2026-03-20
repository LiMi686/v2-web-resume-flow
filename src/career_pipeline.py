from policy_engine import run_policy_analysis
from industry_engine import run_industry_selection
from role_engine import run_role_selection
from company_engine import run_company_analysis
from job_targeting_engine import run_job_targeting
from growth_engine import run_growth_plan


def run_career_pipeline(user_profile, job_description=""):
    state = {
        "user_profile": user_profile,
        "policy_result": None,
        "industry_result": None,
        "role_result": None,
        "company_result": None,
        "job_targeting_result": None,
        "growth_result": None,
    }

    # Step 1
    state["policy_result"] = run_policy_analysis(user_profile)

    # Step 2
    state["industry_result"] = run_industry_selection(
        user_profile,
        state["policy_result"]
    )

    # Step 3
    state["role_result"] = run_role_selection(
        user_profile,
        state["policy_result"],
        state["industry_result"]
    )

    # Step 4
    state["company_result"] = run_company_analysis(
        user_profile,
        state["policy_result"],
        state["industry_result"],
        state["role_result"]
    )

    # Step 5
    if job_description:
        state["job_targeting_result"] = run_job_targeting(
            user_profile,
            state["policy_result"],
            state["industry_result"],
            state["role_result"],
            state["company_result"],
            job_description
        )

        # Step 6
        state["growth_result"] = run_growth_plan(
            user_profile,
            state["policy_result"],
            state["industry_result"],
            state["role_result"],
            state["company_result"],
            state["job_targeting_result"]
        )

    return state