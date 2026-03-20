"""Shared lightweight schemas for the career pipeline."""

from __future__ import annotations

from typing import TypedDict


class UserProfile(TypedDict, total=False):
    """Input profile used across pipeline stages."""

    name: str
    target_role: str
    skills: list[str]
    interests: list[str]
    years_experience: int | float
    preferred_regions: list[str]
    needs_visa_sponsorship: bool
    has_work_authorization: bool
    open_to_remote: bool
    constraints: list[str]


class PolicyResult(TypedDict):
    """Output of the policy analysis stage."""

    visa_risk: str
    constraints: list[str]
    recommended_regions: list[str]
    raw_text: str | None


class IndustryRecommendation(TypedDict):
    """Single industry recommendation item."""

    name: str
    score: float
    reason: str
    recommendation: str


class IndustryResult(TypedDict):
    """Output of the industry ranking stage."""

    top_industries: list[IndustryRecommendation]
    raw_text: str | None


class RoleRecommendation(TypedDict):
    """Single role recommendation item."""

    industry: str
    entry_path: str
    ideal_role: str | None
    bridge_role: str | None
    stretch_role: str | None
    reason: str


class RoleResult(TypedDict):
    """Output of the role selection stage."""

    recommended_roles: list[RoleRecommendation]
    raw_text: str | None


class CareerPipelineResult(TypedDict):
    """Top-level pipeline result."""

    user_profile: UserProfile
    policy_result: PolicyResult
    industry_result: IndustryResult
    role_result: RoleResult
