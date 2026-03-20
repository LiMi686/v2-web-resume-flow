"""Entry point for the unified career pipeline."""

from __future__ import annotations

import json

try:
    from .career_pipeline import run_career_pipeline
except ImportError:
    from career_pipeline import run_career_pipeline


def main() -> None:
    """Run a sample user profile through the pipeline and print the result."""
    user_profile = {
        "name": "Alex",
        "target_role": "Data Scientist",
        "skills": ["Python", "SQL", "Analytics", "Machine Learning"],
        "interests": ["Healthcare", "Climate", "AI Products"],
        "years_experience": 2,
        "preferred_regions": ["US", "Canada", "UK"],
        "needs_visa_sponsorship": True,
        "has_work_authorization": False,
        "open_to_remote": True,
        "constraints": ["Needs sponsorship", "Wants growth-oriented industry"],
    }

    result = run_career_pipeline(user_profile)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
