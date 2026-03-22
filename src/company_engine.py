"""Company strategy stage for the career strategy pipeline."""

from __future__ import annotations

from typing import Any

try:
    from .llm_client import generate_optional_text
    from .schemas import (
        CompanyStrategyResult,
        CompanyTarget,
        IndustryResult,
        PolicyResult,
        UserProfile,
        ensure_user_profile,
    )
except ImportError:
    from llm_client import generate_optional_text
    from schemas import (
        CompanyStrategyResult,
        CompanyTarget,
        IndustryResult,
        PolicyResult,
        UserProfile,
        ensure_user_profile,
    )

COMPANY_STRATEGY_KB = {
    "Healthcare AI": {
        "industry_analysis": [
            "Healthcare AI rewards companies that connect model performance to clinical workflow adoption.",
            "Data access, regulatory trust, and integration depth are stronger moats than generic model novelty.",
        ],
        "market_analysis": [
            "Hospitals and providers buy cautiously, so workflow ROI and trust are critical.",
            "Platform businesses that embed into existing systems often scale better than point tools.",
        ],
        "value_chain_analysis": [
            "High-value positions sit near clinical data infrastructure, documentation workflows, and decision support.",
            "The best operating leverage comes from turning fragmented healthcare processes into repeatable data products.",
        ],
        "competitor_map": [
            "Clinical AI platforms: Tempus, Abridge, Suki",
            "Data and oncology infrastructure: Flatiron Health, Guardant Health",
        ],
        "company_types": [
            "Workflow-embedded healthcare AI platforms",
            "Healthcare analytics and data infrastructure vendors",
        ],
        "shortlisted_companies": [
            ("Tempus", "Growth-stage/public", "Precision medicine and clinical data products"),
            ("Abridge", "Growth-stage", "Clinical documentation and workflow AI"),
            ("Flatiron Health", "Mature", "Oncology data infrastructure"),
        ],
    },
    "Fintech": {
        "industry_analysis": [
            "Fintech companies create strong data roles where analytics links directly to growth, fraud, and retention.",
            "The highest leverage teams sit close to risk, monetization, and operational automation.",
        ],
        "market_analysis": [
            "Efficiency-focused buyers reward products that reduce manual operations and trust failures.",
            "Infrastructure and B2B fintech often provide clearer data ownership than consumer-only products.",
        ],
        "value_chain_analysis": [
            "Payments rails, underwriting, and finance automation are strong analytics-heavy layers.",
            "Companies with both product telemetry and transaction data tend to create richer role scope.",
        ],
        "competitor_map": [
            "Payments infrastructure: Stripe, Adyen, Checkout.com",
            "Finance operations: Ramp, Brex, Airbase",
        ],
        "company_types": [
            "Payments and financial infrastructure platforms",
            "Finance operations automation companies",
        ],
        "shortlisted_companies": [
            ("Stripe", "Mature/private", "Payments infrastructure and product analytics"),
            ("Ramp", "Growth-stage", "Finance automation and spend intelligence"),
            ("Plaid", "Growth-stage", "Financial data connectivity"),
        ],
    },
    "Enterprise SaaS": {
        "industry_analysis": [
            "Enterprise SaaS gives broad access to product, revenue, and usage data with relatively clear experimentation loops.",
            "AI-native workflow software creates strong openings for analytics-driven product strategy roles.",
        ],
        "market_analysis": [
            "B2B buyers now expect AI augmentation and measurable productivity gains.",
            "Companies with product-led data loops often develop stronger analyst and data scientist scope.",
        ],
        "value_chain_analysis": [
            "The most strategic teams sit between product usage, monetization, and go-to-market efficiency.",
            "Observability, collaboration, and workflow software each create strong instrumentation surfaces.",
        ],
        "competitor_map": [
            "Observability and infrastructure: Datadog, New Relic",
            "Collaboration and workflow: Notion, Asana, Airtable",
        ],
        "company_types": [
            "AI-native workflow software companies",
            "Product-led SaaS platforms",
        ],
        "shortlisted_companies": [
            ("Datadog", "Public", "Instrumentation-heavy SaaS with strong product analytics"),
            ("HubSpot", "Public", "Growth, lifecycle, and customer platform analytics"),
            ("Notion", "Growth-stage", "AI-enhanced collaboration software"),
        ],
    },
    "Climate and Energy Tech": {
        "industry_analysis": [
            "Climate and energy roles become strategic when analytics improves physical operations or resource allocation.",
            "Companies tied to infrastructure workflows often sustain demand better than narrative-only climate products.",
        ],
        "market_analysis": [
            "Grid, storage, and industrial efficiency markets are benefiting from multi-year investment cycles.",
            "The strongest company choices expose the user to operational datasets, forecasting, and optimization problems.",
        ],
        "value_chain_analysis": [
            "Data leverage sits near energy demand forecasting, asset performance, and system optimization.",
            "Software layers attached to physical infrastructure can create durable analytics roles.",
        ],
        "competitor_map": [
            "Energy optimization: AutoGrid, Stem",
            "Climate workflow software: Aurora Solar, Arcadia",
        ],
        "company_types": [
            "Grid and energy analytics companies",
            "Industrial optimization platforms",
        ],
        "shortlisted_companies": [
            ("Stem", "Public", "Energy storage analytics and optimization"),
            ("Aurora Solar", "Growth-stage", "Solar design and workflow software"),
            ("AutoGrid", "Growth-stage", "Grid flexibility and analytics"),
        ],
    },
    "Semiconductors and Advanced Manufacturing": {
        "industry_analysis": [
            "This space rewards people who can turn process data into yield, throughput, or quality improvements.",
            "The best company targets expose the user to factory, supply-chain, or vision-driven analytics workflows.",
        ],
        "market_analysis": [
            "Industrial policy and compute demand support sustained investment across design, equipment, and fabrication.",
            "Operationally critical teams often value deterministic analysis more than flashy AI branding.",
        ],
        "value_chain_analysis": [
            "High-value layers include yield optimization, process control, equipment analytics, and supply forecasting.",
            "Companies with deep sensor data and process complexity create stronger long-term learning curves.",
        ],
        "competitor_map": [
            "Chip platform leaders: NVIDIA, AMD, Qualcomm",
            "Equipment and manufacturing stack: ASML, Applied Materials, Lam Research",
        ],
        "company_types": [
            "Semiconductor equipment and process analytics companies",
            "Chip platform and manufacturing analytics teams",
        ],
        "shortlisted_companies": [
            ("Applied Materials", "Public", "Manufacturing and equipment analytics"),
            ("ASML", "Public", "Complex systems and process intelligence"),
            ("NVIDIA", "Public", "Platform analytics tied to compute demand"),
        ],
    },
}


def run_company_strategy(
    user_profile: UserProfile | dict[str, Any],
    policy_result: PolicyResult,
    industry_result: IndustryResult,
) -> CompanyStrategyResult:
    """Convert prioritized industries into a company strategy layer."""
    profile = ensure_user_profile(user_profile)
    target_company_types: list[str] = []
    company_selection_rules = [
        "Prioritize companies where data work influences revenue, product adoption, or operational efficiency.",
        "Prefer teams where analytics sits close to decision-makers rather than isolated reporting functions.",
        "Use industry tailwinds to narrow company types before narrowing exact job titles.",
    ]
    if profile.years_experience < 3:
        company_selection_rules.append(
            "Favor companies with clear analyst-to-strategic-role progression and measurable first-project scope."
        )
    if policy_result.visa_risk == "high":
        company_selection_rules.append(
            "Add screening for international hiring maturity, remote flexibility, and globally distributed teams."
        )

    industry_analysis: list[str] = []
    market_analysis: list[str] = []
    value_chain_analysis: list[str] = []
    competitor_map: list[str] = []
    shortlisted_companies: list[CompanyTarget] = []
    why_these_companies: list[str] = []

    for industry in industry_result.top_industries:
        config = COMPANY_STRATEGY_KB.get(industry.name)
        if not config:
            continue

        target_company_types.extend(config["company_types"])
        industry_analysis.extend(config["industry_analysis"])
        market_analysis.extend(config["market_analysis"])
        value_chain_analysis.extend(config["value_chain_analysis"])
        competitor_map.extend(config["competitor_map"])

        for name, stage, focus in config["shortlisted_companies"][:2]:
            company_type = config["company_types"][0]
            shortlisted_companies.append(
                CompanyTarget(
                    industry=industry.name,
                    name=name,
                    company_type=company_type,
                    stage=stage,
                    focus=focus,
                    why_now=industry.why_now,
                )
            )
            why_these_companies.append(
                f"{name} fits because it sits inside {industry.name} tailwinds and gives exposure to {focus.lower()}."
            )

    explanation_prompt = f"""
You are explaining company strategy in an industry-first career decision system.

User profile:
{profile.to_dict()}

Top industries:
{industry_result.top_industries}

Return 3 concise sentences on why company selection should be strategic instead of just a list of names.
"""
    explanation = generate_optional_text(explanation_prompt)

    return CompanyStrategyResult(
        target_company_types=sorted(set(target_company_types)),
        company_selection_rules=company_selection_rules,
        industry_analysis=industry_analysis,
        market_analysis=market_analysis,
        value_chain_analysis=value_chain_analysis,
        competitor_map=competitor_map,
        shortlisted_companies=shortlisted_companies[:6],
        why_these_companies=why_these_companies[:6],
        explanation=explanation,
    )


def run_company_analysis(
    user_profile: UserProfile | dict[str, Any],
    policy_result: PolicyResult,
    industry_result: IndustryResult,
    role_result: object | None = None,
) -> CompanyStrategyResult:
    """Compatibility wrapper for older callers."""
    return run_company_strategy(user_profile, policy_result, industry_result)
