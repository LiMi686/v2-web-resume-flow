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
    from .schemas import (
        CareerState,
        CompanyPreferenceProfile,
        ProjectExperience,
        UserProfile,
        create_initial_state,
    )
except ImportError:
    from application_assets_engine import run_application_assets
    from company_engine import run_company_strategy
    from growth_engine import run_growth_plan
    from industry_engine import run_industry_selection
    from job_targeting_engine import run_job_targeting
    from llm_client import llm_status, refresh_llm_environment
    from policy_engine import run_policy_analysis
    from role_engine import run_role_path
    from schemas import (
        CareerState,
        CompanyPreferenceProfile,
        ProjectExperience,
        UserProfile,
        create_initial_state,
    )


DEGREE_OPTIONS = [
    "Bachelor of Science in Data Science",
    "Master of Science in Data Science",
    "Bachelor's",
    "Master's",
]

SCHOOL_OPTIONS = [
    "Mapua University",
    "Arizona State University",
    "University of Arizona",
]

SKILL_OPTIONS = [
    "MySQL",
    "Snowflake",
    "Python",
    "R",
    "SQL",
    "Analytics",
    "Machine Learning",
    "Data Analysis",
    "Data Visualization",
    "Statistics",
    "Data Cleaning",
    "Dashboarding",
    "KPI Reporting",
    "ETL",
    "Excel",
    "Tableau",
    "Power BI",
    "Pandas",
    "Scikit-learn",
    "K-Means Clustering",
    "RFM Analysis",
    "Feature Engineering",
    "Customer Segmentation",
    "ggplot2",
    "Shiny",
    "Web Scraping",
    "rvest",
    "Apriori",
    "Association Rule Mining",
    "Market Basket Analysis",
]

COMPANY_ENVIRONMENT_OPTIONS = [
    "Big Tech / platform company",
    "Series A-B startup",
    "Late-stage growth company",
    "Established operator or mission-driven organization",
]

RISK_TOLERANCE_OPTIONS = ["low", "medium", "high"]
STABILITY_PRIORITY_OPTIONS = ["highest", "high", "balanced", "lower"]
WORK_STYLE_OPTIONS = [
    "Structured training and defined scope",
    "Balanced structure and ownership",
    "High ownership and ambiguity",
]
BRAND_VS_GROWTH_OPTIONS = [
    "Brand and structured training",
    "Balanced",
    "Rapid ownership and growth speed",
]


def _sample_user_profile() -> UserProfile:
    return UserProfile(
        name="Leon",
        target_role="Data Analyst",
        degree="Master of Science in Data Science",
        schools=["Mapua University", "Arizona State University", "University of Arizona"],
        education_history=[
            {
                "school": "Mapua University",
                "degree": "Bachelor of Science in Data Science",
                "start_year": "2019",
                "end_year": "2023",
                "location": "Manila, Philippines",
                "notes": "Joint program with Arizona State University.",
            },
            {
                "school": "University of Arizona",
                "degree": "Master of Science in Data Science",
                "start_year": "2024",
                "end_year": "2026",
                "notes": "",
            },
        ],
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
            {
                "company": "University of Arizona, James E. Rogers College of Law",
                "title": "Law Library Assistant",
                "industry": "Legal / Library Science",
                "summary": "Assisted with legal research and data management for library resources.",
                "skills_used": ["Data Management", "Research", "Python", "Data Visualization"],
                "impact_points": [
                    "Addressing direct questions at circulation desk from phone call or in-person.",
                    "Applied classification and organization principles (Library of Congress System) to manage large-scale collections.",
                    "Conducted targeted information retrieval in Nexis Uni, improving efficiency in sourcing case law and academic materials.",
                    "Maintained structured information management using ALMA, ensuring accurate cataloging and resource organization.",
                    "Tracked and logged service inquiries in LibAnswers, reinforcing structured problem-solving and data entry precision.",
                ],
            },
            {
                "company": "University of Arizona, Computer Vision Lab",
                "title": "Graduate Research Assistant",
                "industry": "Research / Computer Vision",
                "summary": "Assisted with research projects focused on computer vision and machine learning.",
                "skills_used": ["Computer Vision", "Python", "Research Assistance"],
                "impact_points": [
                    "Created an image dataset for AI medical model recognition, generating 300+ laparoscopic surgery images.",
                    "Designed and implemented a contamination pipeline that overlays surgical artifacts such as blood, smoke, and lens blur onto clean endoscopy images.",
                    "Using both coding based method and AI image generators (e.g., Sora, Gemini).",
                ],
            },
        ],
        project_experiences=[
            {
                "name": "Airbnb Relational Database Design - MySQL",
                "role": "Group Project",
                "summary": "Designed and implemented a normalized relational database modeling Airbnb's marketplace operations.",
                "skills_used": ["MySQL", "SQL", "Database Design", "ER Modeling", "Relational Databases"],
                "impact_points": [
                    "Built an ER model and translated it into 20 SQL tables with primary and foreign keys to ensure data integrity.",
                    "Defined 10 real-world business problems and developed SQL queries to generate revenue, risk, and performance insights.",
                    "Collaborated on a group project to model Airbnb marketplace operations through a normalized relational database.",
                ],
            },
            {
                "name": "Cloud-Based E-Commerce Customer Analytics",
                "role": "Project Team Member",
                "summary": "Developed a cloud-based customer analytics pipeline using Snowflake and Python to analyze e-commerce behavioral data.",
                "skills_used": [
                    "Snowflake",
                    "Python",
                    "Feature Engineering",
                    "RFM Analysis",
                    "K-Means Clustering",
                    "Customer Segmentation",
                ],
                "impact_points": [
                    "Performed feature engineering and aggregated customer-level metrics from e-commerce behavioral data.",
                    "Applied RFM analysis and K-Means clustering to identify distinct customer segments.",
                    "Generated insights into spending patterns, satisfaction levels, and delivery performance through the resulting clusters.",
                ],
            },
            {
                "name": "Pandemic Visualization & Analysis by R",
                "role": "Project",
                "summary": "Processed and analyzed global WHO datasets across 200+ countries to examine infection and mortality trends.",
                "skills_used": [
                    "R",
                    "Data Analysis",
                    "Data Visualization",
                    "ggplot2",
                    "Shiny",
                    "Web Scraping",
                    "rvest",
                ],
                "impact_points": [
                    "Built interactive geographic heatmaps using ggplot2 and Shiny for spatiotemporal analysis.",
                    "Applied web scraping with rvest to study correlations between media coverage and case growth.",
                    "Analyzed WHO data across 200+ countries to surface global infection and mortality patterns.",
                ],
            },
            {
                "name": "Online Retail Association Rule",
                "role": "Project",
                "summary": "Implemented association rule mining with the Apriori algorithm to identify frequent itemsets and co-purchasing patterns in transactional retail data.",
                "skills_used": [
                    "Python",
                    "Apriori",
                    "Association Rule Mining",
                    "Market Basket Analysis",
                    "Data Analysis",
                ],
                "impact_points": [
                    "Identified frequent itemsets and co-purchasing patterns from transactional retail data using the Apriori algorithm.",
                    "Computed Support, Confidence, and Lift to quantify product relationships.",
                    "Generated data-driven insights to inform bundling and cross-selling strategies.",
                ],
            },
        ],
        company_preferences=CompanyPreferenceProfile(
            preferred_environments=[
                "Late-stage growth company",
                "Established operator or mission-driven organization",
            ],
            risk_tolerance="medium",
            stability_priority="high",
            work_style_preference="Balanced structure and ownership",
            brand_vs_growth_preference="Balanced",
        ),
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


def _prompt_text(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    try:
        raw = input(f"{prompt}{suffix} ").strip()
    except EOFError:
        return default
    return raw or default


def _deduplicate(items: list[str]) -> list[str]:
    deduplicated: list[str] = []
    seen: set[str] = set()
    for item in items:
        cleaned = item.strip()
        if not cleaned:
            continue
        lowered = cleaned.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        deduplicated.append(cleaned)
    return deduplicated


def _split_csv_values(raw: str) -> list[str]:
    return _deduplicate([item.strip() for item in raw.split(",") if item.strip()])


def _print_options(options: list[str], selected: list[str] | None = None) -> None:
    selected = selected or []
    selected_lookup = {item.lower() for item in selected}
    for index, option in enumerate(options, start=1):
        marker = " (current)" if option.lower() in selected_lookup else ""
        print(f"{index}. {option}{marker}")


def _prompt_single_choice(prompt: str, options: list[str], default: str = "") -> str:
    print(prompt)
    _print_options(options, [default] if default else [])
    response = _prompt_text(
        "Choose one number or type a custom value. Press Enter to keep the current value",
        default=default,
    )
    if response.isdigit():
        selected_index = int(response) - 1
        if 0 <= selected_index < len(options):
            return options[selected_index]
        return default
    return response.strip()


def _prompt_multi_choice(prompt: str, options: list[str], default: list[str] | None = None) -> list[str]:
    default = default or []
    print(prompt)
    _print_options(options, default)
    raw = _prompt_text(
        "Choose comma-separated numbers and/or custom values. Press Enter to keep the current values",
        default=", ".join(default),
    )
    if not raw.strip():
        return default

    selected_items: list[str] = []
    for token in raw.split(","):
        item = token.strip()
        if not item:
            continue
        if item.isdigit():
            selected_index = int(item) - 1
            if 0 <= selected_index < len(options):
                selected_items.append(options[selected_index])
            continue
        selected_items.append(item)
    return _deduplicate(selected_items)


def _collect_multiline_items(prompt: str) -> list[str]:
    print(prompt)
    print("Type one line per item. Type END when finished.")
    items: list[str] = []
    while True:
        try:
            line = input().strip()
        except EOFError:
            break
        if line == "END":
            break
        if line:
            items.append(line)
    return items


def _configure_projects_interactively(user_profile: UserProfile) -> UserProfile:
    print("Project records:")
    if user_profile.project_experiences:
        for project in user_profile.project_experiences:
            print(f"- {project.name or 'Untitled project'}")
    else:
        print("- None")

    if not _prompt_yes_no("Review or add project records now?", default=True):
        return user_profile

    if user_profile.project_experiences and _prompt_yes_no(
        "Replace the current project list before adding new projects?",
        default=False,
    ):
        user_profile.project_experiences = []

    while _prompt_yes_no("Add a project record?", default=False):
        project_name = _prompt_text("Project name")
        if not project_name:
            print("Skipped an empty project entry.")
            continue

        role = _prompt_text("Your role in the project", default="")
        summary = _prompt_text("One-line project summary", default="")
        skills_used = _prompt_multi_choice(
            "Select or type the skills used in this project:",
            SKILL_OPTIONS,
            default=[],
        )
        impact_points = _collect_multiline_items(
            "Add project impact points or outcomes for this project:"
        )
        user_profile.project_experiences.append(
            ProjectExperience(
                name=project_name,
                role=role,
                summary=summary,
                skills_used=skills_used,
                impact_points=impact_points,
            )
        )

    return user_profile


def _configure_company_preferences_interactively(user_profile: UserProfile) -> UserProfile:
    _print_section("Company Preference")
    print("These inputs help Company Strategy balance your stated preferences with your actual competitiveness.")

    if not _prompt_yes_no(
        "Review company environment preferences before Company Strategy?",
        default=True,
    ):
        return user_profile

    preferences = user_profile.company_preferences
    preferences.preferred_environments = _prompt_multi_choice(
        "Which company environments should the system seriously consider?",
        COMPANY_ENVIRONMENT_OPTIONS,
        default=preferences.preferred_environments,
    )
    preferences.risk_tolerance = _prompt_single_choice(
        "What is your current risk tolerance?",
        RISK_TOLERANCE_OPTIONS,
        default=preferences.risk_tolerance or "medium",
    )
    preferences.stability_priority = _prompt_single_choice(
        "How important are stability and sponsorship infrastructure right now?",
        STABILITY_PRIORITY_OPTIONS,
        default=preferences.stability_priority or "high",
    )
    preferences.work_style_preference = _prompt_single_choice(
        "Which work style fits you best right now?",
        WORK_STYLE_OPTIONS,
        default=preferences.work_style_preference or "Balanced structure and ownership",
    )
    preferences.brand_vs_growth_preference = _prompt_single_choice(
        "Which do you value more at this stage?",
        BRAND_VS_GROWTH_OPTIONS,
        default=preferences.brand_vs_growth_preference or "Balanced",
    )
    notes_default = ", ".join(preferences.notes)
    notes_raw = _prompt_text(
        "Any extra context to consider, such as family, finances, location, or lifestyle? Use commas to separate ideas",
        default=notes_default,
    )
    preferences.notes = _split_csv_values(notes_raw)
    return user_profile


def _pause_for_next_step(next_label: str) -> bool:
    return _prompt_yes_no(f"Continue to {next_label}?", default=True)


def _print_explanation_if_present(explanation: str | None) -> None:
    if explanation:
        print("\nLLM explanation:")
        print(explanation)


def _configure_llm_interactively() -> None:
    _print_section("LLM Setup")
    os.environ["LLM_MODE"] = "auto"
    os.environ["POLICY_SEARCH_PROVIDER"] = "gemini_grounded"
    os.environ["COMPANY_SEARCH_PROVIDER"] = "gemini_grounded"
    refresh_llm_environment()
    status = llm_status()
    if status["available"]:
        print(f"Gemini is required for this pipeline and is ready with model: {status['model']}")
        return

    print("Gemini is required for this pipeline and is not ready yet.")
    print("Add GEMINI_API_KEY to your .env file and make sure google-genai is installed.")
    print(f"Current .env path: {Path('.env').resolve()}")

    while True:
        try:
            action = input(
                "After updating .env, press Enter to re-check, or type 'exit' to stop: "
            ).strip().lower()
        except EOFError:
            action = "exit"
        if action == "exit":
            raise RuntimeError("Gemini is required for the LLM-only pipeline.")

        refresh_llm_environment()
        status = llm_status()
        if status["available"]:
            print(f"Gemini is ready with model: {status['model']}")
            return
        print("Gemini is still unavailable. Check GEMINI_API_KEY and dependency installation, or type 'exit'.")


def _configure_policy_search_interactively() -> None:
    _print_section("Policy Search Setup")
    os.environ["POLICY_SEARCH_PROVIDER"] = "gemini_grounded"
    print("Policy / Region will use Gemini-grounded search with no local baseline.")


def _configure_company_search_interactively() -> None:
    _print_section("Company Search Setup")
    os.environ["COMPANY_SEARCH_PROVIDER"] = "gemini_grounded"
    print("Company Strategy will use Gemini-grounded search with no local provider.")


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


def _configure_profile_interactively(user_profile: UserProfile) -> UserProfile:
    _print_section("Profile Setup")
    if not _prompt_yes_no(
        "Review or update your education, skills, and projects before running the pipeline?",
        default=True,
    ):
        return user_profile

    user_profile.degree = _prompt_single_choice(
        "Select your highest degree:",
        DEGREE_OPTIONS,
        default=user_profile.degree,
    )
    user_profile.schools = _prompt_multi_choice(
        "Select the schools you attended:",
        SCHOOL_OPTIONS,
        default=user_profile.schools,
    )
    user_profile.skills = _prompt_multi_choice(
        "Select the skills you want the pipeline to use:",
        SKILL_OPTIONS,
        default=user_profile.skills,
    )
    return _configure_projects_interactively(user_profile)


def _print_profile_summary(user_profile: UserProfile) -> None:
    _print_section("Profile")
    print("Using the current profile from src/main.py.")
    print(f"Target role: {user_profile.target_role}")
    print(f"Degree: {user_profile.degree or 'Not set'}")
    print(f"Schools: {', '.join(user_profile.schools) if user_profile.schools else 'Not set'}")
    if user_profile.education_history:
        print("Education history:")
        for education in user_profile.education_history:
            years = " - ".join(
                part for part in [education.start_year, education.end_year] if part
            )
            detail_parts = [education.school, education.degree]
            if years:
                detail_parts.append(years)
            if education.location:
                detail_parts.append(education.location)
            print(f"- {' | '.join(part for part in detail_parts if part)}")
            if education.notes:
                print(f"  Notes: {education.notes}")
    print(f"Skills: {', '.join(user_profile.skills) if user_profile.skills else 'Not set'}")
    print(f"Internship records: {len(user_profile.internship_experiences)}")
    print(f"Project records: {len(user_profile.project_experiences)}")
    if user_profile.company_preferences.preferred_environments:
        print(
            "Company preferences: "
            f"{', '.join(user_profile.company_preferences.preferred_environments)}"
        )
    if user_profile.project_experiences:
        for project in user_profile.project_experiences:
            print(f"- {project.name} | {project.role or 'Role not set'}")
            if project.summary:
                print(f"  Summary: {project.summary}")
            if project.skills_used:
                print(f"  Skills: {', '.join(project.skills_used)}")


def _show_company_preference_summary(user_profile: UserProfile) -> None:
    preferences = user_profile.company_preferences
    _print_section("Company Preference")
    _print_list("Preferred environments", preferences.preferred_environments)
    print(f"Risk tolerance: {preferences.risk_tolerance or 'Not set'}")
    print(f"Stability priority: {preferences.stability_priority or 'Not set'}")
    print(f"Work style: {preferences.work_style_preference or 'Not set'}")
    print(
        "Brand vs growth: "
        f"{preferences.brand_vs_growth_preference or 'Not set'}"
    )
    _print_list("Extra context", preferences.notes)


def _show_policy_stage(state: CareerState) -> None:
    result = state.policy_result
    if result is None:
        return
    _print_section("Policy / Region")
    print(f"Analysis mode: {result.analysis_mode}")
    print(f"Visa risk: {result.visa_risk}")
    print(f"Mobility strategy: {result.mobility_strategy}")
    _print_list("Recommended regions", result.recommended_regions)
    _print_list("Priority policy themes", result.priority_policy_themes)
    _print_list("Constraints", result.constraints)
    _print_list("Opportunity signals", result.opportunity_signals)
    if result.grounding_queries:
        _print_list("Grounded search queries", result.grounding_queries)
    if result.grounding_sources:
        print("Grounded sources:")
        for source in result.grounding_sources:
            label = source.title or source.uri
            if source.uri and source.title:
                print(f"- {label} | {source.uri}")
            else:
                print(f"- {label}")
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
    print(f"Your stated preference: {result.user_preference_summary}")
    print(f"Preference alignment: {result.preference_alignment_summary}")
    print(f"Recommended company path: {result.primary_company_path}")
    print(f"Competitiveness summary: {result.competitiveness_summary}")
    print(f"Development recommendation: {result.development_recommendation}")
    _print_list("Discovery strategy", result.discovery_strategy)
    _print_list("Target company types", result.target_company_types)
    _print_list("Company selection rules", result.company_selection_rules)
    print("Company archetype assessment:")
    for assessment in result.company_archetype_assessments:
        print(
            f"- {assessment.archetype} | {assessment.recommendation_level} | "
            f"competitiveness={assessment.competitiveness_level}"
        )
        print(f"  Development value: {assessment.development_value}")
        print(f"  Entry strategy: {assessment.entry_strategy}")
        if assessment.fit_rationale:
            print(f"  Why fit: {assessment.fit_rationale[0]}")
        if assessment.watchouts:
            print(f"  Watchout: {assessment.watchouts[0]}")
        if assessment.example_companies:
            print(f"  Example companies: {', '.join(assessment.example_companies)}")
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
    user_profile = _configure_profile_interactively(user_profile)
    state = create_initial_state(user_profile)

    _print_profile_summary(state.user_profile)

    _configure_llm_interactively()
    _configure_policy_search_interactively()

    state.policy_result = run_policy_analysis(state.user_profile)
    _show_policy_stage(state)
    if not _pause_for_next_step("Industry"):
        _save_state_snapshot(state)
        return

    state.industry_result = run_industry_selection(state.user_profile, state.policy_result)
    _show_industry_stage(state)
    if not _pause_for_next_step("Company Preference"):
        _save_state_snapshot(state)
        return

    state.user_profile = _configure_company_preferences_interactively(state.user_profile)
    _show_company_preference_summary(state.user_profile)
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
