"""Company strategy stage for the career strategy pipeline."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

try:
    from .company_ranker import rank_company_candidates
    from .company_search_provider import get_company_search_provider
    from .llm_client import generate_optional_json, generate_optional_text
    from .schemas import (
        CompanySearchQuery,
        CompanyStrategyResult,
        CompanyTarget,
        IndustryResult,
        PolicyResult,
        UserProfile,
        ensure_user_profile,
    )
except ImportError:
    from company_ranker import rank_company_candidates
    from company_search_provider import get_company_search_provider
    from llm_client import generate_optional_json, generate_optional_text
    from schemas import (
        CompanySearchQuery,
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


def _clean_string_list(value: Any, limit: int | None = None) -> list[str]:
    if not isinstance(value, list):
        return []
    cleaned = [str(item).strip() for item in value if str(item).strip()]
    if limit is not None:
        return cleaned[:limit]
    return cleaned


def _build_search_query(
    profile: UserProfile,
    industry_result: IndustryResult,
) -> CompanySearchQuery:
    return CompanySearchQuery(
        industries=[industry.name for industry in industry_result.top_industries],
        preferred_regions=profile.preferred_regions,
        target_roles=[profile.target_role] if profile.target_role else [],
        preferred_stages=["Series A", "Series B", "Growth-stage"],
        needs_visa_sponsorship=profile.needs_visa_sponsorship,
        open_to_remote=profile.open_to_remote,
    )


def _fallback_company_summary(company: CompanyTarget) -> tuple[str, str, str]:
    fit_summary = (
        f"{company.name} looks useful if you want exposure to {company.focus.lower()} "
        f"inside a {company.stage.lower()} company context."
    )
    candidate_explanation = (
        f"This company sits in {company.industry}, leans {company.orientation or 'balanced'} in its operating style, "
        f"and can help you build value near {company.focus.lower()}."
    )
    role_value_potential = (
        f"Potential value is strongest when you connect analytics work to {company.focus.lower()} "
        f"and the company's core operating decisions."
    )
    return fit_summary, candidate_explanation, role_value_potential


def _build_candidate_takeaways(shortlisted_companies: list[CompanyTarget]) -> list[str]:
    if not shortlisted_companies:
        return []
    takeaways = [
        "The shortlist favors companies where data work is tied to real operating decisions instead of isolated reporting.",
        "Stage preference leans toward A/B-style or growth-stage environments, while still keeping a few mature comparators for context.",
        "The best company choice is the one where your first year can produce visible business value and credible story-building evidence.",
    ]
    if any(company.international_environment in {"high", "medium-high"} for company in shortlisted_companies):
        takeaways.append("International or remote-friendly environments can improve flexibility for candidates with mobility constraints.")
    return takeaways[:4]


def _build_shortlist_rationales(
    profile: UserProfile,
    shortlisted_companies: list[CompanyTarget],
) -> list[str]:
    fallback = [
        f"{company.name} fits because {company.why_match[0].lower() if company.why_match else 'it aligns with the chosen industry and company strategy'}"
        for company in shortlisted_companies
    ]
    prompt = f"""
You are helping shortlist companies for a layered career strategy system.

User profile:
{profile.to_dict()}

Shortlisted companies:
{shortlisted_companies}

Return strict JSON with this shape:
{{
  "why_these_companies": ["reason 1", "reason 2", "reason 3"]
}}
Only return valid JSON.
"""
    llm_payload = generate_optional_json(prompt, fallback=None)
    if isinstance(llm_payload, dict):
        reasons = llm_payload.get("why_these_companies")
        if isinstance(reasons, list):
            cleaned = [str(item).strip() for item in reasons if str(item).strip()]
            if cleaned:
                return cleaned[: len(shortlisted_companies)]
    return fallback


def _apply_company_llm_enrichment(
    profile: UserProfile,
    industry_result: IndustryResult,
    shortlisted_companies: list[CompanyTarget],
) -> tuple[list[CompanyTarget], list[str]]:
    if not shortlisted_companies:
        return shortlisted_companies, []

    prompt = f"""
You are enriching company strategy for a layered career decision system.

User profile:
{profile.to_dict()}

Top industries:
{industry_result.top_industries}

Shortlisted companies:
{shortlisted_companies}

Return strict JSON with this shape:
{{
  "company_evaluations": [
    {{
      "name": "company name",
      "user_fit_summary": "short paragraph",
      "candidate_explanation": "candidate-facing explanation",
      "role_value_potential": "how this company could create career value"
    }}
  ],
  "candidate_facing_takeaways": ["takeaway 1", "takeaway 2", "takeaway 3"]
}}
Only return valid JSON.
"""
    payload = generate_optional_json(prompt, fallback=None)
    fallback_takeaways = _build_candidate_takeaways(shortlisted_companies)
    if not isinstance(payload, dict):
        enriched_companies = []
        for company in shortlisted_companies:
            fit_summary, candidate_explanation, role_value_potential = _fallback_company_summary(company)
            enriched_companies.append(
                replace(
                    company,
                    user_fit_summary=fit_summary,
                    candidate_explanation=candidate_explanation,
                    role_value_potential=role_value_potential,
                )
            )
        return enriched_companies, fallback_takeaways

    raw_evaluations = payload.get("company_evaluations")
    evaluation_map: dict[str, dict[str, Any]] = {}
    if isinstance(raw_evaluations, list):
        evaluation_map = {
            str(item.get("name", "")).strip(): item
            for item in raw_evaluations
            if isinstance(item, dict) and str(item.get("name", "")).strip()
        }

    enriched_companies: list[CompanyTarget] = []
    for company in shortlisted_companies:
        fit_summary, candidate_explanation, role_value_potential = _fallback_company_summary(company)
        evaluation = evaluation_map.get(company.name, {})
        enriched_companies.append(
            replace(
                company,
                user_fit_summary=str(evaluation.get("user_fit_summary", "")).strip() or fit_summary,
                candidate_explanation=str(evaluation.get("candidate_explanation", "")).strip()
                or candidate_explanation,
                role_value_potential=str(evaluation.get("role_value_potential", "")).strip()
                or role_value_potential,
            )
        )

    candidate_facing_takeaways = _clean_string_list(
        payload.get("candidate_facing_takeaways"),
        limit=4,
    ) or fallback_takeaways
    return enriched_companies, candidate_facing_takeaways


def run_company_strategy(
    user_profile: UserProfile | dict[str, Any],
    policy_result: PolicyResult,
    industry_result: IndustryResult,
) -> CompanyStrategyResult:
    """Convert prioritized industries into a company strategy layer."""
    profile = ensure_user_profile(user_profile)
    search_query = _build_search_query(profile, industry_result)
    discovery_strategy = [
        "Use retrieval to find industry-matched companies before asking the model to summarize them.",
        "Prioritize A/B-stage signals when the provider has stage data; otherwise prefer growth-stage companies over mature incumbents.",
        "Bias toward regions and operating models that fit the user's mobility constraints.",
    ]
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

    ranking_logic = [
        "Industry alignment is the base score because company discovery starts from the chosen sectors.",
        "Company stage gets extra weight, with a preference for A/B-stage signals and then growth-stage firms.",
        "Region fit, remote flexibility, and hiring signal quality help break ties.",
    ]
    industry_analysis: list[str] = []
    market_analysis: list[str] = []
    value_chain_analysis: list[str] = []
    competitor_map: list[str] = []
    retrieved_companies: list[CompanyTarget] = []

    for industry in industry_result.top_industries:
        config = COMPANY_STRATEGY_KB.get(industry.name)
        if not config:
            continue

        target_company_types.extend(config["company_types"])
        industry_analysis.extend(config["industry_analysis"])
        market_analysis.extend(config["market_analysis"])
        value_chain_analysis.extend(config["value_chain_analysis"])
        competitor_map.extend(config["competitor_map"])

    provider = get_company_search_provider()
    retrieved_companies = provider.search(search_query)
    ranked_companies = rank_company_candidates(retrieved_companies, search_query, profile)
    shortlisted_companies = ranked_companies[:6]
    for company in shortlisted_companies:
        company.why_now = next(
            (industry.why_now for industry in industry_result.top_industries if industry.name == company.industry),
            company.why_now,
        )

    shortlisted_companies, candidate_facing_takeaways = _apply_company_llm_enrichment(
        profile,
        industry_result,
        shortlisted_companies,
    )
    why_these_companies = _build_shortlist_rationales(profile, shortlisted_companies)

    explanation_prompt = f"""
You are explaining company strategy in an industry-first career decision system.

User profile:
{profile.to_dict()}

Top industries:
{industry_result.top_industries}

Retrieved companies:
{shortlisted_companies}

Return 3 concise sentences on why company selection should be strategic instead of just a list of names.
"""
    explanation = generate_optional_text(explanation_prompt)

    return CompanyStrategyResult(
        discovery_strategy=discovery_strategy,
        target_company_types=sorted(set(target_company_types)),
        company_selection_rules=company_selection_rules,
        ranking_logic=ranking_logic,
        industry_analysis=industry_analysis,
        market_analysis=market_analysis,
        value_chain_analysis=value_chain_analysis,
        competitor_map=competitor_map,
        retrieved_companies=ranked_companies,
        shortlisted_companies=shortlisted_companies,
        why_these_companies=why_these_companies[:6],
        candidate_facing_takeaways=candidate_facing_takeaways,
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
