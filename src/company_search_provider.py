"""Company discovery providers for the career strategy system."""

from __future__ import annotations

from urllib.parse import urlparse
from typing import Protocol

try:
    from .llm_client import generate_grounded_json_strict, generate_json_strict
    from .schemas import CompanySearchQuery, CompanyTarget
except ImportError:
    from llm_client import generate_grounded_json_strict, generate_json_strict
    from schemas import CompanySearchQuery, CompanyTarget


class CompanySearchProvider(Protocol):
    def search(self, query: CompanySearchQuery) -> list[CompanyTarget]:
        """Return candidate companies for the given search query."""


def _format_source_label(uri: str) -> str:
    parsed = urlparse(uri)
    return parsed.netloc or uri


class GeminiGroundedCompanySearchProvider:
    """Gemini grounded search provider for live company discovery."""

    def _prompt(self, query: CompanySearchQuery, *, grounded: bool) -> str:
        grounding_instruction = (
            "Only include companies supported by grounded search results."
            if grounded
            else "Use your model knowledge to propose realistic current companies, and avoid speculative or obviously mismatched names."
        )
        return f"""
You are discovering real companies for a layered career strategy system.

Search goal:
- Stay inside these industries: {query.industries}
- Prefer these regions: {query.preferred_regions or ['no strict region preference']}
- Target roles: {query.target_roles or ['analytics / data / AI roles']}
- Treat these company archetypes or stages as the user's stated preference order: {query.preferred_stages or ['Big Tech / platform', 'Series A-B startup', 'Late-stage growth', 'Established or mission-driven operator']}
- Needs visa sponsorship: {query.needs_visa_sponsorship}
- Open to remote: {query.open_to_remote}
- Prioritize companies where data work is strategically important
- Prefer at most 12 high-signal companies

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

Instructions:
- Results must be fully model-derived.
- {grounding_instruction}
- If no single archetype is mandated, intentionally return a stage-diverse candidate set so downstream analysis can compare big tech, startup, growth-stage, and established environments.
- Only return valid JSON.
"""

    def search(self, query: CompanySearchQuery) -> list[CompanyTarget]:
        grounding_used = True
        try:
            payload = generate_grounded_json_strict(
                self._prompt(query, grounded=True),
                profile="balanced",
            )
        except Exception:
            grounding_used = False
            payload = generate_json_strict(
                self._prompt(query, grounded=False),
                profile="balanced",
            )
        raw_companies = payload.get("companies")
        if not isinstance(raw_companies, list):
            raise ValueError("Grounded company search must return a companies list.")

        grounding = payload.get("_grounding", {})
        sources = grounding.get("sources") if isinstance(grounding, dict) else []
        fallback_source = ""
        if isinstance(sources, list) and sources:
            first_source = sources[0]
            if isinstance(first_source, dict):
                fallback_source = str(first_source.get("uri", "")).strip()

        candidates: list[CompanyTarget] = []
        seen_names: set[str] = set()
        for item in raw_companies:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "")).strip()
            industry = str(item.get("industry", "")).strip()
            if not name or not industry:
                continue

            key = name.lower()
            if key in seen_names:
                continue
            seen_names.add(key)

            source = str(item.get("source", "")).strip() or fallback_source
            if not source and not grounding_used:
                source = "llm_non_grounded"
            candidates.append(
                CompanyTarget(
                    industry=industry,
                    name=name,
                    company_type=str(item.get("company_type", "")).strip()
                    or "Strategic operating company",
                    stage=str(item.get("stage", "")).strip() or "Growth-stage",
                    focus=str(item.get("focus", "")).strip() or "Data-rich operating environment",
                    why_now=str(item.get("why_now", "")).strip()
                    or "This company sits inside the selected strategic industry.",
                    region=str(item.get("region", "")).strip(),
                    hiring_signal=str(item.get("hiring_signal", "")).strip(),
                    source=_format_source_label(source) if source else "gemini_grounded_search",
                    international_environment=str(item.get("international_environment", "")).strip()
                    or "medium",
                    orientation=str(item.get("orientation", "")).strip() or "balanced",
                    visa_support_likelihood=str(item.get("visa_support_likelihood", "")).strip()
                    or "low-medium",
                )
            )

        if not candidates:
            raise ValueError("Grounded company search returned no valid companies.")
        return candidates[:12]


def get_company_search_provider() -> CompanySearchProvider:
    return GeminiGroundedCompanySearchProvider()
