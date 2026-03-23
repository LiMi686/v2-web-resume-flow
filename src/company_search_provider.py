"""Company discovery providers for the career strategy system."""

from __future__ import annotations

import os
from urllib.parse import urlparse
from typing import Protocol

try:
    from .llm_client import generate_optional_grounded_json
    from .schemas import CompanySearchQuery, CompanyTarget
except ImportError:
    from llm_client import generate_optional_grounded_json
    from schemas import CompanySearchQuery, CompanyTarget

LOCAL_COMPANY_DISCOVERY_KB: dict[str, list[dict[str, str]]] = {
    "Healthcare AI": [
        {
            "name": "Tempus",
            "company_type": "Workflow-embedded healthcare AI platforms",
            "stage": "Public",
            "region": "US",
            "focus": "Precision medicine and clinical data products",
            "hiring_signal": "Data and analytics work ties closely to clinical and product decisions",
        },
        {
            "name": "Abridge",
            "company_type": "Workflow-embedded healthcare AI platforms",
            "stage": "Growth-stage",
            "region": "US",
            "focus": "Clinical documentation and workflow AI",
            "hiring_signal": "AI workflow teams often hire analytics and product-minded operators",
        },
        {
            "name": "Flatiron Health",
            "company_type": "Healthcare analytics and data infrastructure vendors",
            "stage": "Mature",
            "region": "US",
            "focus": "Oncology data infrastructure",
            "hiring_signal": "Data-heavy operating environment with healthcare domain depth",
        },
    ],
    "Fintech": [
        {
            "name": "Ramp",
            "company_type": "Finance operations automation companies",
            "stage": "Growth-stage",
            "region": "US",
            "focus": "Finance automation and spend intelligence",
            "hiring_signal": "High-leverage analytics roles tied to product and operations",
        },
        {
            "name": "Plaid",
            "company_type": "Payments and financial infrastructure platforms",
            "stage": "Growth-stage",
            "region": "US",
            "focus": "Financial data connectivity",
            "hiring_signal": "Strong product analytics and data platform surface area",
        },
        {
            "name": "Stripe",
            "company_type": "Payments and financial infrastructure platforms",
            "stage": "Mature/private",
            "region": "Global/Remote",
            "focus": "Payments infrastructure and product analytics",
            "hiring_signal": "Large analytics footprint across payments, risk, and product growth",
        },
    ],
    "Enterprise SaaS": [
        {
            "name": "Notion",
            "company_type": "AI-native workflow software companies",
            "stage": "Growth-stage",
            "region": "US/Remote",
            "focus": "AI-enhanced collaboration software",
            "hiring_signal": "Product analytics and AI workflow instrumentation are strategically important",
        },
        {
            "name": "Datadog",
            "company_type": "AI-native workflow software companies",
            "stage": "Public",
            "region": "US",
            "focus": "Instrumentation-heavy SaaS with strong product analytics",
            "hiring_signal": "Strong data and experimentation opportunities in product-led software",
        },
        {
            "name": "HubSpot",
            "company_type": "Product-led SaaS platforms",
            "stage": "Public",
            "region": "US/Remote",
            "focus": "Growth, lifecycle, and customer platform analytics",
            "hiring_signal": "Analytics often sits close to go-to-market and product decisions",
        },
    ],
    "Climate and Energy Tech": [
        {
            "name": "Aurora Solar",
            "company_type": "Climate software and infrastructure companies",
            "stage": "Growth-stage",
            "region": "US/Remote",
            "focus": "Solar design and workflow software",
            "hiring_signal": "Analytics roles support operational workflows and customer outcomes",
        },
        {
            "name": "AutoGrid",
            "company_type": "Grid and energy analytics companies",
            "stage": "Growth-stage",
            "region": "US",
            "focus": "Grid flexibility and analytics",
            "hiring_signal": "Optimization and forecasting problems create strong analytics demand",
        },
        {
            "name": "Stem",
            "company_type": "Grid and energy analytics companies",
            "stage": "Public",
            "region": "US",
            "focus": "Energy storage analytics and optimization",
            "hiring_signal": "Rich operational datasets tied to energy decisions",
        },
    ],
    "Semiconductors and Advanced Manufacturing": [
        {
            "name": "Applied Materials",
            "company_type": "Semiconductor equipment and process analytics companies",
            "stage": "Public",
            "region": "US",
            "focus": "Manufacturing and equipment analytics",
            "hiring_signal": "Process, yield, and equipment data create strategic analytics opportunities",
        },
        {
            "name": "ASML",
            "company_type": "Semiconductor equipment and process analytics companies",
            "stage": "Public",
            "region": "Global",
            "focus": "Complex systems and process intelligence",
            "hiring_signal": "Operational intelligence and system performance data are core to the business",
        },
        {
            "name": "NVIDIA",
            "company_type": "Chip platform and manufacturing analytics teams",
            "stage": "Public",
            "region": "US",
            "focus": "Platform analytics tied to compute demand",
            "hiring_signal": "Cross-functional analytics spans product, demand, and ecosystem decisions",
        },
    ],
}


class CompanySearchProvider(Protocol):
    def search(self, query: CompanySearchQuery) -> list[CompanyTarget]:
        """Return candidate companies for the given search query."""


def _region_matches(candidate_region: str, preferred_regions: list[str]) -> bool:
    if not preferred_regions:
        return True
    candidate_region_lower = candidate_region.lower()
    return any(region.lower() in candidate_region_lower for region in preferred_regions)


def _infer_international_environment(item: dict[str, str]) -> str:
    region_text = item.get("region", "").lower()
    if "global" in region_text or "remote" in region_text:
        return "high"
    if "us" in region_text:
        return "medium"
    return "medium"


def _infer_orientation(item: dict[str, str]) -> str:
    combined = " ".join([item.get("company_type", ""), item.get("focus", "")]).lower()
    if any(token in combined for token in {"infrastructure", "platform", "ai", "analytics", "optimization"}):
        return "technical"
    if any(token in combined for token in {"operations", "workflow", "finance", "growth"}):
        return "business"
    return "balanced"


def _infer_visa_support_likelihood(item: dict[str, str]) -> str:
    combined = " ".join(
        [
            item.get("region", ""),
            item.get("stage", ""),
            item.get("hiring_signal", ""),
        ]
    ).lower()
    if "global" in combined or "remote" in combined:
        return "medium-high"
    if "public" in combined or "mature" in combined:
        return "medium"
    return "low-medium"


class LocalCompanySearchProvider:
    """Local knowledge-base provider used as the deterministic baseline."""

    def search(self, query: CompanySearchQuery) -> list[CompanyTarget]:
        candidates: list[CompanyTarget] = []
        for industry in query.industries:
            for item in LOCAL_COMPANY_DISCOVERY_KB.get(industry, []):
                if not _region_matches(item["region"], query.preferred_regions):
                    if not (query.open_to_remote and "remote" in item["region"].lower()):
                        continue
                candidates.append(
                    CompanyTarget(
                        industry=industry,
                        name=item["name"],
                        company_type=item["company_type"],
                        stage=item["stage"],
                        focus=item["focus"],
                        why_now=f"Retrieved for {industry} from the local company discovery knowledge base.",
                        region=item["region"],
                        hiring_signal=item["hiring_signal"],
                        source="local_kb",
                        international_environment=item.get(
                            "international_environment",
                            _infer_international_environment(item),
                        ),
                        orientation=item.get("orientation", _infer_orientation(item)),
                        visa_support_likelihood=item.get(
                            "visa_support_likelihood",
                            _infer_visa_support_likelihood(item),
                        ),
                    )
                )
        return candidates


def _format_source_label(uri: str) -> str:
    parsed = urlparse(uri)
    return parsed.netloc or uri


class GeminiGroundedCompanySearchProvider:
    """Gemini grounded search provider for live company discovery."""

    def __init__(self) -> None:
        self._fallback_provider = LocalCompanySearchProvider()

    def search(self, query: CompanySearchQuery) -> list[CompanyTarget]:
        prompt = f"""
You are discovering real companies for a layered career strategy system.

Search goal:
- Prioritize Series A and Series B companies first
- If not enough, include growth-stage companies
- Stay inside these industries: {query.industries}
- Prefer these regions: {query.preferred_regions or ['no strict region preference']}
- Target roles: {query.target_roles or ['analytics / data / AI roles']}
- Needs visa sponsorship: {query.needs_visa_sponsorship}
- Open to remote: {query.open_to_remote}

For each company, infer:
- industry
- name
- company_type
- stage
- focus
- region
- international_environment (high|medium-high|medium|low)
- orientation (technical|business|balanced)
- visa_support_likelihood (high|medium-high|medium|low-medium|low)
- hiring_signal
- why_now
- source

Return strict JSON with this shape:
{{
  "companies": [
    {{
      "industry": "industry name",
      "name": "company name",
      "company_type": "type",
      "stage": "Series A",
      "focus": "what the company does",
      "region": "region",
      "international_environment": "medium",
      "orientation": "technical",
      "visa_support_likelihood": "low-medium",
      "hiring_signal": "evidence they hire data / AI / analytics talent",
      "why_now": "why this company matters now",
      "source": "https://..."
    }}
  ]
}}
Only include companies that are supported by grounded search results. Prefer at most 8 companies.
Only return valid JSON.
"""
        payload = generate_optional_grounded_json(prompt, fallback=None)
        if not isinstance(payload, dict):
            return self._fallback_provider.search(query)

        raw_companies = payload.get("companies")
        if not isinstance(raw_companies, list):
            return self._fallback_provider.search(query)

        grounding = payload.get("_grounding", {})
        sources = grounding.get("sources") if isinstance(grounding, dict) else []
        fallback_source = ""
        if isinstance(sources, list) and sources:
            first_source = sources[0]
            if isinstance(first_source, dict):
                fallback_source = str(first_source.get("uri", "")).strip()

        candidates: list[CompanyTarget] = []
        for item in raw_companies:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "")).strip()
            industry = str(item.get("industry", "")).strip()
            if not name or not industry:
                continue

            source = str(item.get("source", "")).strip() or fallback_source
            stage = str(item.get("stage", "")).strip() or "Growth-stage"
            if not any(token in stage.lower() for token in {"series a", "series b", "growth", "startup", "seed", "mature", "public"}):
                stage = "Growth-stage"

            candidates.append(
                CompanyTarget(
                    industry=industry,
                    name=name,
                    company_type=str(item.get("company_type", "")).strip() or "Startup operating company",
                    stage=stage,
                    focus=str(item.get("focus", "")).strip() or "Company focus not extracted.",
                    why_now=str(item.get("why_now", "")).strip()
                    or "Retrieved through Gemini grounded search with Google Search.",
                    region=str(item.get("region", "")).strip(),
                    hiring_signal=str(item.get("hiring_signal", "")).strip(),
                    source=_format_source_label(source) if source else "gemini_grounded_search",
                    international_environment=str(item.get("international_environment", "")).strip() or "medium",
                    orientation=str(item.get("orientation", "")).strip() or "balanced",
                    visa_support_likelihood=str(item.get("visa_support_likelihood", "")).strip() or "low-medium",
                )
            )

        if not candidates:
            return self._fallback_provider.search(query)
        return candidates[:8]


def get_company_search_provider() -> CompanySearchProvider:
    provider_name = os.getenv("COMPANY_SEARCH_PROVIDER", "local").strip().lower()
    if provider_name == "auto":
        provider_name = "gemini_grounded" if os.getenv("LLM_MODE", "disabled").strip().lower() != "disabled" else "local"
    if provider_name == "gemini_grounded":
        return GeminiGroundedCompanySearchProvider()
    if provider_name == "local":
        return LocalCompanySearchProvider()
    return LocalCompanySearchProvider()
