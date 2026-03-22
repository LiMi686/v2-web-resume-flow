"""Shared typed schemas for the layered career strategy pipeline."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        items = value
    elif isinstance(value, tuple):
        items = list(value)
    elif isinstance(value, str):
        items = value.split(",")
    else:
        items = [value]
    return [str(item).strip() for item in items if str(item).strip()]


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        return normalized in {"1", "true", "yes", "y"}
    return bool(value)


def _as_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


@dataclass(slots=True)
class InternshipExperience:
    company: str = ""
    title: str = ""
    industry: str = ""
    summary: str = ""
    skills_used: list[str] = field(default_factory=list)
    impact_points: list[str] = field(default_factory=list)

    @classmethod
    def from_value(cls, data: Any) -> "InternshipExperience":
        if isinstance(data, cls):
            return data
        if isinstance(data, str):
            text = data.strip()
            return cls(summary=text, impact_points=[text] if text else [])
        if isinstance(data, dict):
            summary = str(data.get("summary", "")).strip()
            impact_points = _as_list(data.get("impact_points"))
            if summary and summary not in impact_points:
                impact_points = [summary, *impact_points]
            return cls(
                company=str(data.get("company", "")).strip(),
                title=str(data.get("title", "")).strip(),
                industry=str(data.get("industry", "")).strip(),
                summary=summary,
                skills_used=_as_list(data.get("skills_used")),
                impact_points=impact_points,
            )
        text = str(data).strip()
        return cls(summary=text, impact_points=[text] if text else [])


def _as_internships(value: Any) -> list[InternshipExperience]:
    if value is None:
        return []
    if isinstance(value, list):
        items = value
    elif isinstance(value, tuple):
        items = list(value)
    else:
        items = [value]
    return [InternshipExperience.from_value(item) for item in items]


@dataclass(slots=True)
class UserProfile:
    name: str = ""
    target_role: str = ""
    skills: list[str] = field(default_factory=list)
    interests: list[str] = field(default_factory=list)
    years_experience: float = 0.0
    preferred_regions: list[str] = field(default_factory=list)
    needs_visa_sponsorship: bool = False
    has_work_authorization: bool = False
    open_to_remote: bool = False
    constraints: list[str] = field(default_factory=list)
    experience_highlights: list[str] = field(default_factory=list)
    internship_experiences: list[InternshipExperience] = field(default_factory=list)
    target_companies: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.name = str(self.name).strip()
        self.target_role = str(self.target_role).strip()
        self.skills = _as_list(self.skills)
        self.interests = _as_list(self.interests)
        self.years_experience = _as_float(self.years_experience)
        self.preferred_regions = _as_list(self.preferred_regions)
        self.needs_visa_sponsorship = _as_bool(self.needs_visa_sponsorship)
        self.has_work_authorization = _as_bool(self.has_work_authorization)
        self.open_to_remote = _as_bool(self.open_to_remote)
        self.constraints = _as_list(self.constraints)
        self.experience_highlights = _as_list(self.experience_highlights)
        self.internship_experiences = _as_internships(self.internship_experiences)
        self.target_companies = _as_list(self.target_companies)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UserProfile":
        return cls(
            name=str(data.get("name", "")).strip(),
            target_role=str(data.get("target_role", "")).strip(),
            skills=_as_list(data.get("skills")),
            interests=_as_list(data.get("interests")),
            years_experience=_as_float(data.get("years_experience")),
            preferred_regions=_as_list(data.get("preferred_regions")),
            needs_visa_sponsorship=_as_bool(data.get("needs_visa_sponsorship")),
            has_work_authorization=_as_bool(data.get("has_work_authorization")),
            open_to_remote=_as_bool(data.get("open_to_remote")),
            constraints=_as_list(data.get("constraints")),
            experience_highlights=_as_list(data.get("experience_highlights")),
            internship_experiences=_as_internships(data.get("internship_experiences")),
            target_companies=_as_list(data.get("target_companies")),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class PolicyResult:
    visa_risk: str
    mobility_strategy: str
    recommended_regions: list[str]
    priority_policy_themes: list[str]
    constraints: list[str]
    opportunity_signals: list[str]
    explanation: str | None = None


@dataclass(slots=True)
class IndustryRecommendation:
    name: str
    score: float
    recommendation: str
    why_now: str
    key_skills: list[str]
    policy_alignment: list[str]
    company_strategy_hint: str
    market_stage: str
    sample_companies: list[str]


@dataclass(slots=True)
class IndustryResult:
    ranked_industries: list[IndustryRecommendation]
    top_industries: list[IndustryRecommendation]
    selection_logic: list[str]
    explanation: str | None = None


@dataclass(slots=True)
class CompanyTarget:
    industry: str
    name: str
    company_type: str
    stage: str
    focus: str
    why_now: str


@dataclass(slots=True)
class CompanyStrategyResult:
    target_company_types: list[str]
    company_selection_rules: list[str]
    industry_analysis: list[str]
    market_analysis: list[str]
    value_chain_analysis: list[str]
    competitor_map: list[str]
    shortlisted_companies: list[CompanyTarget]
    why_these_companies: list[str]
    explanation: str | None = None


@dataclass(slots=True)
class RolePathOption:
    industry: str
    company_type: str
    role_title: str
    path_type: str
    focus_areas: list[str]
    why_fit: list[str]
    success_metrics: list[str]
    example_companies: list[str]


@dataclass(slots=True)
class RolePathResult:
    recommended_paths: list[RolePathOption]
    decision_principles: list[str]
    explanation: str | None = None


@dataclass(slots=True)
class RequirementMatch:
    requirement: str
    importance: str
    matched: bool
    evidence: list[str]
    gap_notes: list[str]


@dataclass(slots=True)
class JobTargetingResult:
    job_title: str
    jd_summary: str
    key_requirements: list[str]
    requirement_matches: list[RequirementMatch]
    experience_alignment: list[str]
    evidence_map: dict[str, list[str]]
    gap_analysis: list[str]
    positioning_strategy: list[str]
    resume_rewrite_points: list[str]
    cover_letter_inputs: list[str]
    match_confidence: str


@dataclass(slots=True)
class GrowthPlanResult:
    first_month_plan: list[str]
    month_2_3_plan: list[str]
    one_year_plan: list[str]
    daily_skill_accumulation: list[str]
    value_creation_plan: list[str]
    cover_letter_growth_narrative: list[str]
    explanation: str | None = None


@dataclass(slots=True)
class CareerState:
    user_profile: UserProfile
    job_description: str = ""
    policy_result: PolicyResult | None = None
    industry_result: IndustryResult | None = None
    company_result: CompanyStrategyResult | None = None
    role_result: RolePathResult | None = None
    job_targeting_result: JobTargetingResult | None = None
    growth_result: GrowthPlanResult | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def ensure_user_profile(user_profile: UserProfile | dict[str, Any]) -> UserProfile:
    if isinstance(user_profile, UserProfile):
        return user_profile
    return UserProfile.from_dict(user_profile)


def create_initial_state(
    user_profile: UserProfile | dict[str, Any], job_description: str = ""
) -> CareerState:
    return CareerState(
        user_profile=ensure_user_profile(user_profile),
        job_description=job_description,
    )
