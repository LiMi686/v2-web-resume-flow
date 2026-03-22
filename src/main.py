"""Entry point for the unified career strategy pipeline."""

from __future__ import annotations

import json

try:
    from .career_pipeline import run_career_pipeline
    from .schemas import UserProfile
except ImportError:
    from career_pipeline import run_career_pipeline
    from schemas import UserProfile


def main() -> None:
    """Run a sample profile through the end-to-end strategy pipeline."""
    user_profile = UserProfile(
        name="Lee",
        target_role="Data Scientist",
        skills=["Python", "SQL", "Analytics", "Machine Learning"],
        interests=["Healthcare", "Climate", "AI Products"],
        years_experience=2,
        preferred_regions=["US", "Canada"],
        needs_visa_sponsorship=True,
        has_work_authorization=False,
        open_to_remote=True,
        constraints=["Needs sponsorship", "Wants growth-oriented industry"],
        experience_highlights=[
            "Built SQL dashboards for business reviews",
            "Shipped a forecasting model for demand planning",
            "Partnered with stakeholders on analytics roadmaps",
        ],
        internship_experiences=[
            {
                "company": "CareOps Analytics",
                "title": "Data Analyst Intern",
                "industry": "Healthcare AI",
                "summary": "Supported healthcare operations analytics and automated weekly reporting for leadership.",
                "skills_used": ["SQL", "Python", "Dashboarding", "Stakeholder Communication"],
                "impact_points": [
                    "Built SQL pipelines and dashboards for clinical operations reviews.",
                    "Presented analysis to cross-functional stakeholders and translated findings into action items.",
                    "Improved reporting turnaround time through lightweight automation.",
                ],
            }
        ],
    )

    sample_job_description = """
Senior Data Scientist

We are looking for a data scientist with strong Python, SQL, experimentation,
stakeholder communication, and machine learning skills. You will partner with
product and operations teams to improve forecasting, analytics, and decision-making.
Experience with dashboarding and translating analysis into business action is preferred.
"""

    result = run_career_pipeline(user_profile, job_description=sample_job_description)
    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
