"""Resume scanning and schema mapping utilities."""

from __future__ import annotations

import json
import mimetypes
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from .llm_client import generate_json_strict, generate_multimodal_json_strict
    from .schemas import UserProfile
except ImportError:
    from llm_client import generate_json_strict, generate_multimodal_json_strict
    from schemas import UserProfile


SUPPORTED_IMAGE_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".bmp",
    ".gif",
    ".tif",
    ".tiff",
    ".webp",
    ".heic",
}
SUPPORTED_TEXT_SUFFIXES = {".txt", ".md", ".rst"}
SUPPORTED_WORD_SUFFIXES = {".doc", ".docx"}
SUPPORTED_PDF_SUFFIXES = {".pdf"}

BOOL_FIELDS = {"needs_visa_sponsorship", "has_work_authorization", "open_to_remote"}
PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass(slots=True)
class ResumeScanResult:
    profile: UserProfile
    source_path: Path
    extraction_mode: str
    missing_fields: list[str] = field(default_factory=list)
    confidence_notes: list[str] = field(default_factory=list)
    extracted_text: str = ""
    saved_profile_path: Path | None = None
    saved_text_path: Path | None = None


def _clean_string_list(value: Any, *, limit: int | None = None) -> list[str]:
    if not isinstance(value, list):
        return []
    cleaned = [str(item).strip() for item in value if str(item).strip()]
    if limit is not None:
        return cleaned[:limit]
    return cleaned


def _normalize_bool_or_none(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "yes", "y", "1"}:
            return True
        if normalized in {"false", "no", "n", "0"}:
            return False
    return None


def _resume_extraction_prompt(document_label: str, document_text: str) -> str:
    return f"""
You are extracting structured resume information for a career-planning system.

Source document: {document_label}

Resume text:
{document_text}

Return strict JSON with this shape:
{{
  "name": "full name",
  "target_role": "best-fit role inferred from the resume",
  "degree": "highest degree",
  "schools": ["school 1", "school 2"],
  "education_history": [
    {{
      "school": "school",
      "degree": "degree",
      "start_year": "YYYY",
      "end_year": "YYYY or Expected",
      "location": "city, country",
      "notes": "gpa or honors if present"
    }}
  ],
  "skills": ["skill 1", "skill 2"],
  "interests": [],
  "years_experience": 0,
  "preferred_regions": ["region if explicitly stated"],
  "needs_visa_sponsorship": null,
  "has_work_authorization": null,
  "open_to_remote": null,
  "constraints": ["constraint 1"],
  "experience_highlights": ["highlight 1", "highlight 2"],
  "internship_experiences": [
    {{
      "company": "company",
      "title": "title",
      "industry": "industry",
      "summary": "one-line summary",
      "skills_used": ["skill 1"],
      "impact_points": ["impact 1", "impact 2"]
    }}
  ],
  "project_experiences": [
    {{
      "name": "project",
      "role": "role",
      "summary": "one-line summary",
      "skills_used": ["skill 1"],
      "impact_points": ["impact 1", "impact 2"]
    }}
  ],
  "missing_fields": ["field name"],
  "confidence_notes": ["note 1"]
}}

Instructions:
- Use only information supported by the resume text.
- For missing string fields use "".
- For missing list fields use [].
- For missing boolean fields use null.
- Do not invent visa sponsorship, work authorization, or remote preference unless explicitly stated.
- Infer a realistic target_role from the resume when possible.
- Estimate years_experience from the timeline only when the resume provides enough date evidence; otherwise use 0.
- Keep skills concise and deduplicated.
- Treat work experience entries, internships, and major technical roles as internship_experiences for this schema.
- Treat academic, research, and portfolio work as project_experiences when they are clearly project-like.
- Only return valid JSON.
"""


def _resume_multimodal_prompt(document_label: str) -> str:
    return f"""
You are extracting structured resume information from a document image or binary file.

Source document: {document_label}

Read the attached resume carefully and return strict JSON with this shape:
{{
  "name": "full name",
  "target_role": "best-fit role inferred from the resume",
  "degree": "highest degree",
  "schools": ["school 1", "school 2"],
  "education_history": [
    {{
      "school": "school",
      "degree": "degree",
      "start_year": "YYYY",
      "end_year": "YYYY or Expected",
      "location": "city, country",
      "notes": "gpa or honors if present"
    }}
  ],
  "skills": ["skill 1", "skill 2"],
  "interests": [],
  "years_experience": 0,
  "preferred_regions": ["region if explicitly stated"],
  "needs_visa_sponsorship": null,
  "has_work_authorization": null,
  "open_to_remote": null,
  "constraints": ["constraint 1"],
  "experience_highlights": ["highlight 1", "highlight 2"],
  "internship_experiences": [
    {{
      "company": "company",
      "title": "title",
      "industry": "industry",
      "summary": "one-line summary",
      "skills_used": ["skill 1"],
      "impact_points": ["impact 1", "impact 2"]
    }}
  ],
  "project_experiences": [
    {{
      "name": "project",
      "role": "role",
      "summary": "one-line summary",
      "skills_used": ["skill 1"],
      "impact_points": ["impact 1", "impact 2"]
    }}
  ],
  "missing_fields": ["field name"],
  "confidence_notes": ["note 1"],
  "extracted_text": "plain text transcription of the resume"
}}

Instructions:
- Use only information that appears in the attached document.
- For missing string fields use "".
- For missing list fields use [].
- For missing boolean fields use null.
- Do not invent visa sponsorship, work authorization, or remote preference unless explicitly stated.
- Infer a realistic target_role from the resume when possible.
- Estimate years_experience from the timeline only when the resume provides enough date evidence; otherwise use 0.
- Keep extracted_text readable but concise; include the main resume content needed for debugging.
- Only return valid JSON.
"""


def _extract_pdf_text(path: Path) -> str:
    if shutil.which("swift") is None:
        return ""

    swift_source = f"""
import Foundation
import PDFKit

let url = URL(fileURLWithPath: {json.dumps(str(path))})
guard let doc = PDFDocument(url: url) else {{
    fputs("Unable to open PDF.\\n", stderr)
    exit(1)
}}

for index in 0..<doc.pageCount {{
    if let page = doc.page(at: index), let text = page.string {{
        print(text)
    }}
}}
"""
    env = {
        **os.environ,
        "SWIFT_MODULECACHE_PATH": "/tmp/swift-module-cache",
        "CLANG_MODULE_CACHE_PATH": "/tmp/swift-clang-module-cache",
    }
    result = subprocess.run(
        ["swift", "-e", swift_source],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def _extract_word_text(path: Path) -> str:
    if shutil.which("textutil") is None:
        raise RuntimeError(
            "Word scanning requires macOS textutil in the current environment."
        )
    result = subprocess.run(
        ["textutil", "-convert", "txt", "-stdout", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"Failed to extract text from {path.name}.")
    return result.stdout.strip()


def _extract_text(path: Path) -> tuple[str, str]:
    suffix = path.suffix.lower()
    if suffix in SUPPORTED_TEXT_SUFFIXES:
        return path.read_text(encoding="utf-8"), "plain_text"
    if suffix in SUPPORTED_WORD_SUFFIXES:
        return _extract_word_text(path), "word_text"
    if suffix in SUPPORTED_PDF_SUFFIXES:
        extracted = _extract_pdf_text(path)
        return extracted, "pdf_text"
    return "", "multimodal"


def _guess_mime_type(path: Path) -> str:
    suffix_map = {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".doc": "application/msword",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".bmp": "image/bmp",
        ".gif": "image/gif",
        ".tif": "image/tiff",
        ".tiff": "image/tiff",
        ".webp": "image/webp",
        ".heic": "image/heic",
    }
    guessed = suffix_map.get(path.suffix.lower())
    if guessed:
        return guessed
    mime_type, _ = mimetypes.guess_type(path.name)
    return mime_type or "application/octet-stream"


def _extract_payload_from_binary(path: Path) -> dict[str, Any]:
    from google.genai import types

    return generate_multimodal_json_strict(
        _resume_multimodal_prompt(path.name),
        parts=[
            types.Part.from_bytes(
                data=path.read_bytes(),
                mime_type=_guess_mime_type(path),
            )
        ],
        profile="stable",
    )


def _extract_payload_from_text(path: Path, extracted_text: str) -> dict[str, Any]:
    return generate_json_strict(
        _resume_extraction_prompt(path.name, extracted_text),
        profile="stable",
    )


def _payload_to_profile(payload: dict[str, Any]) -> UserProfile:
    profile_data: dict[str, Any] = {
        "name": str(payload.get("name", "")).strip(),
        "target_role": str(payload.get("target_role", "")).strip(),
        "degree": str(payload.get("degree", "")).strip(),
        "schools": _clean_string_list(payload.get("schools")),
        "education_history": payload.get("education_history")
        if isinstance(payload.get("education_history"), list)
        else [],
        "skills": _clean_string_list(payload.get("skills")),
        "interests": _clean_string_list(payload.get("interests")),
        "years_experience": payload.get("years_experience", 0),
        "preferred_regions": _clean_string_list(payload.get("preferred_regions")),
        "constraints": _clean_string_list(payload.get("constraints"), limit=8),
        "experience_highlights": _clean_string_list(
            payload.get("experience_highlights"),
            limit=8,
        ),
        "internship_experiences": payload.get("internship_experiences")
        if isinstance(payload.get("internship_experiences"), list)
        else [],
        "project_experiences": payload.get("project_experiences")
        if isinstance(payload.get("project_experiences"), list)
        else [],
        "target_companies": [],
        "company_preferences": {},
    }

    for field_name in BOOL_FIELDS:
        normalized_value = _normalize_bool_or_none(payload.get(field_name))
        if normalized_value is not None:
            profile_data[field_name] = normalized_value

    return UserProfile.from_dict(profile_data)


def _derive_missing_fields(payload: dict[str, Any], profile: UserProfile) -> list[str]:
    missing_fields = _clean_string_list(payload.get("missing_fields"), limit=20)
    missing_lookup = {item.lower() for item in missing_fields}

    def add_missing(field_name: str) -> None:
        normalized = field_name.lower()
        if normalized not in missing_lookup:
            missing_lookup.add(normalized)
            missing_fields.append(field_name)

    if not profile.name:
        add_missing("name")
    if not profile.degree:
        add_missing("degree")
    if not profile.schools:
        add_missing("schools")
    if not profile.skills:
        add_missing("skills")
    if not profile.education_history:
        add_missing("education_history")
    if not profile.internship_experiences:
        add_missing("internship_experiences")

    for field_name in sorted(BOOL_FIELDS):
        if _normalize_bool_or_none(payload.get(field_name)) is None:
            add_missing(field_name)

    return missing_fields


def _save_scan_artifacts(
    result: ResumeScanResult,
    output_root: Path | None = None,
) -> ResumeScanResult:
    if output_root is None:
        configured_root = os.getenv("CAREER_OUTPUT_ROOT", "").strip()
        if configured_root:
            output_root = Path(configured_root).expanduser()
            if not output_root.is_absolute():
                output_root = PROJECT_ROOT / output_root
            output_root = output_root / "scanned_profiles"
        else:
            output_root = PROJECT_ROOT / "outputs" / "scanned_profiles"

    output_root.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    stem = result.source_path.stem.replace(" ", "_")
    profile_path = output_root / f"{stem}_{timestamp}.json"
    profile_path.write_text(
        json.dumps(result.profile.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    result.saved_profile_path = profile_path

    if result.extracted_text.strip():
        text_path = output_root / f"{stem}_{timestamp}.txt"
        text_path.write_text(result.extracted_text, encoding="utf-8")
        result.saved_text_path = text_path

    return result


def scan_resume_to_profile(path: str | Path) -> ResumeScanResult:
    source_path = Path(path).expanduser().resolve()
    if not source_path.exists():
        raise FileNotFoundError(f"Resume file not found: {source_path}")

    extracted_text, extraction_mode = _extract_text(source_path)
    payload: dict[str, Any]

    if extracted_text.strip():
        payload = _extract_payload_from_text(source_path, extracted_text)
        extraction_mode = f"{extraction_mode}+llm"
        if source_path.suffix.lower() in SUPPORTED_PDF_SUFFIXES and len(extracted_text.strip()) < 300:
            payload = _extract_payload_from_binary(source_path)
            extraction_mode = "pdf_multimodal"
            extracted_text = str(payload.get("extracted_text", "")).strip()
    else:
        payload = _extract_payload_from_binary(source_path)
        extraction_mode = "multimodal"
        extracted_text = str(payload.get("extracted_text", "")).strip()

    result = ResumeScanResult(
        profile=_payload_to_profile(payload),
        source_path=source_path,
        extraction_mode=extraction_mode,
        confidence_notes=_clean_string_list(payload.get("confidence_notes"), limit=12),
        extracted_text=extracted_text,
    )
    result.missing_fields = _derive_missing_fields(payload, result.profile)
    return _save_scan_artifacts(result)
