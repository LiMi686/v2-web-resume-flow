"""Interactive entry point for the layered career strategy pipeline."""

from __future__ import annotations

import json
import os
from pathlib import Path

try:
    from .application_assets_engine import run_application_assets
    from .company_engine import run_company_strategy
    from .growth_engine import run_growth_plan
    from .industry_engine import run_industry_selection
    from .job_targeting_engine import run_job_targeting
    from .llm_client import llm_status, refresh_llm_environment
    from .policy_engine import run_policy_analysis
    from .role_engine import run_role_path
    from .schemas import CareerState, UserProfile, create_initial_state
except ImportError:
    from application_assets_engine import run_application_assets
    from company_engine import run_company_strategy
    from growth_engine import run_growth_plan
    from industry_engine import run_industry_selection
    from job_targeting_engine import run_job_targeting
    from llm_client import llm_status, refresh_llm_environment
    from policy_engine import run_policy_analysis
    from role_engine import run_role_path
    from schemas import CareerState, UserProfile, create_initial_state


def _sample_user_profile() -> UserProfile:
    return UserProfile(
        name="Leon",
        target_role="Data Analyst",
        skills=["Python", "SQL", "Analytics", "Machine Learning"],
        years_experience=0,
        preferred_regions=["US", "Canada"],
        needs_visa_sponsorship=True,
        open_to_remote=True,
        constraints=["Needs sponsorship", "Wants growth-oriented industry"],
        experience_highlights=[
            "Built SQL dashboards for business reviews",
            "Shipped a forecasting model for demand planning",
            "Partnered with stakeholders on analytics roadmaps",
        ],
        internship_experiences=[
            {
                "company": "Arizona List Organization",
                "title": "Data Analyst Intern",
                "industry": "Political Data / Nonprofit Analytics",
                "summary": "Improved voter outreach data quality and built KPI reporting to support campaign decision-making.",
                "skills_used": ["SQL", "Python", "Data Cleaning", "KPI Reporting", "Data Validation"],
                "impact_points": [
                    "Cleaned and standardized weekly voter-contact data to improve data integrity and reporting accuracy.",
                    "Built reusable SQL query templates and KPI dashboards for leadership reporting.",
                    "Delivered structured insights to support outreach strategy and campaign operations decisions.",
                ],
            },
            {
                "company": "University of Arizona - Lung Cancer Research Institute",
                "title": "Student Researcher",
                "industry": "Healthcare / Biomedical Data Science",
                "summary": "Developed reproducible data analysis workflows to identify effective cancer cell reversal patterns.",
                "skills_used": ["Python", "Clustering", "Data Visualization", "Outlier Detection", "Statistical Analysis"],
                "impact_points": [
                    "Built end-to-end analysis pipeline (cleaning, clustering, visualization) for multi-dataset research.",
                    "Applied K-means clustering to identify stable vs. significant biological response patterns.",
                    "Improved classification efficiency by 10% through optimized workflow design.",
                ],
            },
            {
                "company": "USHER Technologies Inc.",
                "title": "Data Analyst Intern",
                "industry": "AI / Infrastructure / Disaster Analytics",
                "summary": "Developed predictive models for earthquake damage assessment using sensor data.",
                "skills_used": ["Machine Learning", "Python", "Time Series", "Data Validation"],
                "impact_points": [
                    "Built ML model to predict post-earthquake sensor readings and detect anomalies.",
                    "Reduced manual inspection workload by 15% through automated damage assessment.",
                    "Validated model predictions against real-world inspection data for reliability.",
                ],
            },
        ],
    )


def _print_section(title: str) -> None:
    print(f"\n=== {title} ===")


def _print_list(label: str, items: list[str]) -> None:
    print(f"{label}:")
    if not items:
        print("- None")
        return
    for item in items:
        print(f"- {item}")


def _prompt_yes_no(prompt: str, default: bool = True) -> bool:
    suffix = "[Y/n]" if default else "[y/N]"
    try:
        raw = input(f"{prompt} {suffix} ").strip().lower()
    except EOFError:
        return default
    if not raw:
        return default
    return raw in {"y", "yes"}


def _pause_for_next_step(next_label: str) -> bool:
    return _prompt_yes_no(f"Continue to {next_label}?", default=True)


def _print_explanation_if_present(explanation: str | None) -> None:
    if explanation:
        print("\nLLM explanation:")
        print(explanation)


def _configure_llm_interactively() -> None:
    _print_section("LLM Setup")
    wants_llm = _prompt_yes_no(
        "Enable optional Gemini explanations for each stage?", default=False
    )
    if not wants_llm:
        os.environ["LLM_MODE"] = "disabled"
        os.environ["COMPANY_SEARCH_PROVIDER"] = "local"
        print("Gemini explanations disabled. The deterministic pipeline will still run.")
        return

    os.environ["LLM_MODE"] = "auto"
    refresh_llm_environment()
    status = llm_status()
    if status["available"]:
        print(f"Gemini is ready with model: {status['model']}")
        return

    print("Gemini is not ready yet.")
    print("To enable it, add GEMINI_API_KEY to your .env file and make sure google-genai is installed.")
    print(f"Current .env path: {Path('.env').resolve()}")

    while True:
        try:
            action = input(
                "After updating .env, press Enter to re-check, or type 'skip' to continue without Gemini: "
            ).strip().lower()
        except EOFError:
            action = "skip"
        if action == "skip":
            os.environ["LLM_MODE"] = "disabled"
            os.environ["COMPANY_SEARCH_PROVIDER"] = "local"
            print("Continuing without Gemini explanations.")
            return

        refresh_llm_environment()
        status = llm_status()
        if status["available"]:
            print(f"Gemini is ready with model: {status['model']}")
            return
        print("Gemini is still unavailable. Check GEMINI_API_KEY and dependency installation, or type 'skip'.")


def _configure_company_search_interactively() -> None:
    _print_section("Company Search Setup")
    if os.environ.get("LLM_MODE", "disabled").strip().lower() == "disabled":
        os.environ["COMPANY_SEARCH_PROVIDER"] = "local"
        print("Gemini is disabled, so Company Strategy will use the local provider.")
        return

    refresh_llm_environment()
    status = llm_status()
    if not status["available"]:
        os.environ["COMPANY_SEARCH_PROVIDER"] = "local"
        print("Gemini is unavailable right now, so Company Strategy will use the local provider.")
        return

    use_grounded_company_search = _prompt_yes_no(
        "Use Gemini-grounded company search here to prioritize A/B-stage companies?", default=True
    )
    os.environ["COMPANY_SEARCH_PROVIDER"] = (
        "gemini_grounded" if use_grounded_company_search else "local"
    )
    if use_grounded_company_search:
        print("Company Strategy will try live grounded search first, then fall back to local results if needed.")
    else:
        print("Company Strategy will stay on the local provider.")


def _collect_job_description() -> str:
    _print_section("Job Description")
    print("Paste the target JD below. Type a single line with END when finished.")
    lines: list[str] = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip() == "END":
            break
        lines.append(line)
    return "\n".join(lines).strip()


def _show_policy_stage(state: CareerState) -> None:
    result = state.policy_result
    if result is None:
        return
    _print_section("Policy / Region")
    print(f"Visa risk: {result.visa_risk}")
    print(f"Mobility strategy: {result.mobility_strategy}")
    _print_list("Recommended regions", result.recommended_regions)
    _print_list("Priority policy themes", result.priority_policy_themes)
    _print_list("Constraints", result.constraints)
    _print_explanation_if_present(result.explanation)


def _show_industry_stage(state: CareerState) -> None:
    result = state.industry_result
    if result is None:
        return
    _print_section("Industry")
    for index, industry in enumerate(result.top_industries, start=1):
        print(f"{index}. {industry.name} | score={industry.score} | {industry.recommendation}")
        print(f"   Why now: {industry.why_now}")
        print(f"   Trend summary: {industry.trend_summary}")
        print(f"   Long-term growth: {industry.long_term_growth}")
        print(f"   Why you: {industry.personalized_reason}")
        print(f"   Company hint: {industry.company_strategy_hint}")
    _print_list("Selection logic", result.selection_logic)
    _print_explanation_if_present(result.explanation)


def _show_company_stage(state: CareerState) -> None:
    result = state.company_result
    if result is None:
        return
    _print_section("Company Strategy")
    _print_list("Discovery strategy", result.discovery_strategy)
    _print_list("Target company types", result.target_company_types)
    _print_list("Company selection rules", result.company_selection_rules)
    _print_list("Ranking logic", result.ranking_logic)
    print(f"Retrieved company candidates: {len(result.retrieved_companies)}")
    print("Shortlisted companies:")
    for company in result.shortlisted_companies:
        print(f"- {company.name} | {company.industry} | {company.company_type} | score={company.fit_score}")
        print(f"  Focus: {company.focus}")
        print(
            f"  Region: {company.region} | Intl: {company.international_environment} | "
            f"Orientation: {company.orientation} | Stage: {company.stage} | Visa: {company.visa_support_likelihood}"
        )
        if company.source:
            print(f"  Source: {company.source}")
        if company.why_match:
            print(f"  Why match: {company.why_match[0]}")
        if company.user_fit_summary:
            print(f"  Fit summary: {company.user_fit_summary}")
    _print_list("Candidate-facing takeaways", result.candidate_facing_takeaways)
    _print_explanation_if_present(result.explanation)


def _show_role_stage(state: CareerState) -> None:
    result = state.role_result
    if result is None:
        return
    _print_section("Role Path")
    for index, path in enumerate(result.recommended_paths, start=1):
        print(f"{index}. {path.role_title} | {path.path_type} path | {path.industry}")
        print(f"   Company context: {path.company_type}")
        print(f"   Focus areas: {', '.join(path.focus_areas)}")
        print(f"   Example companies: {', '.join(path.example_companies)}")
    _print_list("Decision principles", result.decision_principles)
    _print_explanation_if_present(result.explanation)


def _show_job_stage(state: CareerState) -> None:
    result = state.job_targeting_result
    if result is None:
        return
    _print_section("Job Alignment")
    print(f"Job title: {result.job_title}")
    print(f"Match confidence: {result.match_confidence}")
    print(f"Summary: {result.jd_summary}")
    _print_list("Key requirements", result.key_requirements)
    print("Requirement matches:")
    for match in result.requirement_matches:
        status = "matched" if match.matched else "gap"
        print(f"- {match.requirement} ({match.importance}) -> {status}")
        for evidence in match.evidence[:2]:
            print(f"  Evidence: {evidence}")
    _print_list("Gap analysis", result.gap_analysis)
    _print_list("Resume rewrite points", result.resume_rewrite_points)
    _print_list("Tailored resume bullets", result.tailored_resume_bullets)
    print(f"Why this role: {result.why_this_role_answer}")


def _show_growth_stage(state: CareerState) -> None:
    result = state.growth_result
    if result is None:
        return
    _print_section("Growth Plan")
    _print_list("First month plan", result.first_month_plan)
    _print_list("Month 2-3 plan", result.month_2_3_plan)
    _print_list("One year plan", result.one_year_plan)
    _print_list("Priority gaps", result.priority_gaps)
    _print_list("Prioritized skills", result.prioritized_skills)
    _print_list("Project recommendations", result.project_recommendations)
    _print_list("Job search strategy", result.job_search_strategy)
    _print_list("Value creation plan", result.value_creation_plan)
    _print_list("Cover letter narrative inputs", result.cover_letter_growth_narrative)
    _print_explanation_if_present(result.explanation)


def _show_application_stage(state: CareerState) -> None:
    result = state.application_assets_result
    if result is None:
        return
    _print_section("Application Assets")
    _print_list("Tailored resume bullets", result.tailored_resume_bullets)
    print(f"Cover letter draft: {result.cover_letter_draft}")
    print(f"Cold email: {result.cold_email_message}")
    print(f"Networking message: {result.networking_message}")
    print(f"Why this role: {result.why_this_role_answer}")
    print(f"LinkedIn summary: {result.linkedin_summary}")
    _print_explanation_if_present(result.explanation)


def _save_state_snapshot(state: CareerState) -> None:
    output_path = Path("outputs/interactive_career_state.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(state.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"\nSaved session snapshot to {output_path}")


def main() -> None:
    """Run the strategy flow one stage at a time."""
    user_profile = _sample_user_profile()
    state = create_initial_state(user_profile)

    _print_section("Profile")
    print("Using the current profile from src/main.py.")
    print(f"Target role: {state.user_profile.target_role}")
    print(f"Skills: {', '.join(state.user_profile.skills)}")
    print(f"Internship records: {len(state.user_profile.internship_experiences)}")

    _configure_llm_interactively()

    state.policy_result = run_policy_analysis(state.user_profile)
    _show_policy_stage(state)
    if not _pause_for_next_step("Industry"):
        _save_state_snapshot(state)
        return

    state.industry_result = run_industry_selection(state.user_profile, state.policy_result)
    _show_industry_stage(state)
    if not _pause_for_next_step("Company Strategy"):
        _save_state_snapshot(state)
        return

    _configure_company_search_interactively()
    state.company_result = run_company_strategy(
        state.user_profile,
        state.policy_result,
        state.industry_result,
    )
    _show_company_stage(state)
    if not _pause_for_next_step("Role Path"):
        _save_state_snapshot(state)
        return

    state.role_result = run_role_path(
        state.user_profile,
        state.policy_result,
        state.industry_result,
        state.company_result,
    )
    _show_role_stage(state)

    if _prompt_yes_no("Do you want to add a target job description now?", default=False):
        state.job_description = _collect_job_description()
        if state.job_description:
            state.job_targeting_result = run_job_targeting(
                state.user_profile,
                state.policy_result,
                state.industry_result,
                state.company_result,
                state.role_result,
                state.job_description,
            )
            _show_job_stage(state)
        else:
            print("No job description entered. Skipping job alignment.")

    if _pause_for_next_step("Growth Plan"):
        state.growth_result = run_growth_plan(
            state.user_profile,
            state.policy_result,
            state.industry_result,
            state.company_result,
            state.role_result,
            state.job_targeting_result,
            state.job_description,
        )
        _show_growth_stage(state)
        if state.job_targeting_result and _pause_for_next_step("Application Assets"):
            state.application_assets_result = run_application_assets(
                state.user_profile,
                state.company_result,
                state.role_result,
                state.job_targeting_result,
                state.growth_result,
            )
            _show_application_stage(state)

    _save_state_snapshot(state)


if __name__ == "__main__":
    main()
