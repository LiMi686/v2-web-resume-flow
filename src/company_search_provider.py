"""Company discovery providers for the career strategy system."""

from __future__ import annotations

import os
from typing import Protocol

try:
    from .schemas import CompanySearchQuery, CompanyTarget
except ImportError:
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
                    )
                )
        return candidates


def get_company_search_provider() -> CompanySearchProvider:
    provider_name = os.getenv("COMPANY_SEARCH_PROVIDER", "local").strip().lower()
    if provider_name == "local":
        return LocalCompanySearchProvider()
    return LocalCompanySearchProvider()
