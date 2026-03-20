def create_initial_state(user_profile):
    return {
        "user_profile": user_profile,
        "policy_result": None,
        "industry_result": None,
        "role_result": None,
        "company_result": None,
        "job_targeting_result": None,
        "growth_result": None,
    }
