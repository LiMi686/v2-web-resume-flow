"""Local web interface for staged resume scanning and career pipeline runs."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from flask import Flask, render_template, request, send_file
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

try:
    from .application_assets_engine import run_application_assets
    from .growth_engine import run_growth_plan
    from .industry_engine import run_industry_selection
    from .job_targeting_engine import run_job_targeting
    from .llm_client import llm_status, refresh_llm_environment
    from .policy_engine import run_policy_analysis
    from .resume_scan import ResumeScanResult, scan_resume_to_profile
    from .role_engine import run_role_path
    from .company_engine import run_company_strategy
    from .schemas import UserProfile, create_initial_state
except ImportError:
    from application_assets_engine import run_application_assets
    from growth_engine import run_growth_plan
    from industry_engine import run_industry_selection
    from job_targeting_engine import run_job_targeting
    from llm_client import llm_status, refresh_llm_environment
    from policy_engine import run_policy_analysis
    from resume_scan import ResumeScanResult, scan_resume_to_profile
    from role_engine import run_role_path
    from company_engine import run_company_strategy
    from schemas import UserProfile, create_initial_state


PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_ROOT = PROJECT_ROOT / "src" / "templates"
OUTPUT_ROOT = PROJECT_ROOT / "outputs"
UPLOAD_ROOT = OUTPUT_ROOT / "uploaded_resumes"
WEB_RUN_ROOT = OUTPUT_ROOT / "web_runs"
WEB_SESSION_ROOT = OUTPUT_ROOT / "web_sessions"
ALLOWED_SUFFIXES = {
    ".pdf",
    ".doc",
    ".docx",
    ".png",
    ".jpg",
    ".jpeg",
    ".bmp",
    ".gif",
    ".tif",
    ".tiff",
    ".webp",
    ".heic",
    ".txt",
    ".md",
}
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
WORKFLOW_STAGE_RANK = {
    "scanned": 0,
    "policy_complete": 1,
    "industry_complete": 2,
    "preferences_complete": 3,
    "company_complete": 4,
    "role_complete": 5,
    "job_complete": 6,
    "job_skipped": 6,
    "growth_complete": 7,
    "complete": 8,
}
RESULT_VIEW_ORDER = [
    "scan",
    "policy",
    "industry",
    "preferences",
    "company",
    "role",
    "job",
    "growth",
    "final",
]
RESULT_VIEW_LABELS = {
    "scan": "Scanned Profile",
    "policy": "Policy / Region",
    "industry": "Industry",
    "preferences": "Company Preference",
    "company": "Company Strategy",
    "role": "Role Path",
    "job": "Job Alignment",
    "growth": "Growth Plan",
    "final": "Full Results",
}

app = Flask(__name__, template_folder=str(TEMPLATE_ROOT))
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _allowed_upload(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_SUFFIXES


def _save_uploaded_file(file_storage: FileStorage) -> Path:
    filename = secure_filename(file_storage.filename or "")
    if not filename:
        raise ValueError("Please choose a resume file before submitting.")
    if not _allowed_upload(filename):
        raise ValueError(
            "Unsupported file type. Please upload a PDF, Word document, image, or plain text resume."
        )

    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    destination = UPLOAD_ROOT / f"{_timestamp()}_{filename}"
    file_storage.save(destination)
    return destination


def _save_state_snapshot(state_dict: dict, source_stem: str) -> Path:
    WEB_RUN_ROOT.mkdir(parents=True, exist_ok=True)
    output_path = WEB_RUN_ROOT / f"{source_stem}_{_timestamp()}_career_state.json"
    output_path.write_text(
        json.dumps(state_dict, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return output_path


def _resolve_output_relative(relative_path: str) -> Path:
    target = (OUTPUT_ROOT / relative_path).resolve()
    if OUTPUT_ROOT.resolve() not in target.parents and target != OUTPUT_ROOT.resolve():
        raise FileNotFoundError("Invalid output path.")
    return target


def _to_output_relative(path: Path | None) -> str | None:
    if path is None:
        return None
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(OUTPUT_ROOT.resolve())
    except ValueError:
        return None
    return relative.as_posix()


def _resolve_if_present(relative_path: str | None) -> Path | None:
    if not relative_path:
        return None
    try:
        return _resolve_output_relative(relative_path)
    except FileNotFoundError:
        return None


@app.route("/outputs/<path:relative_path>")
def serve_output_file(relative_path: str):
    target = _resolve_output_relative(relative_path)
    return send_file(target, as_attachment=False)


def _split_csv_values(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def _split_lines(raw: str) -> list[str]:
    return [item.strip() for item in raw.splitlines() if item.strip()]


def _as_float(raw: str, default: float = 0.0) -> float:
    try:
        return float(raw.strip())
    except (AttributeError, ValueError):
        return default


def _form_text(form, key: str, default: str = "") -> str:
    if key in form:
        return (form.get(key) or "").strip()
    return default.strip()


def _form_csv(form, key: str, default: list[str]) -> list[str]:
    if key in form:
        return _split_csv_values(form.get(key) or "")
    return list(default)


def _form_lines(form, key: str, default: list[str]) -> list[str]:
    if key in form:
        return _split_lines(form.get(key) or "")
    return list(default)


def _apply_profile_form(form, base_profile: UserProfile) -> UserProfile:
    profile_data = base_profile.to_dict()
    profile_data["name"] = _form_text(form, "name", base_profile.name)
    profile_data["target_role"] = _form_text(form, "target_role", base_profile.target_role)
    profile_data["degree"] = _form_text(form, "degree", base_profile.degree)
    profile_data["schools"] = _form_csv(form, "schools", base_profile.schools)
    profile_data["skills"] = _form_csv(form, "skills", base_profile.skills)
    profile_data["preferred_regions"] = _form_csv(
        form,
        "preferred_regions",
        base_profile.preferred_regions,
    )
    profile_data["years_experience"] = (
        _as_float(form.get("years_experience"), default=base_profile.years_experience)
        if "years_experience" in form
        else base_profile.years_experience
    )
    profile_data["needs_visa_sponsorship"] = (
        form.get("needs_visa_sponsorship") == "on"
        if "needs_visa_sponsorship" in form
        else base_profile.needs_visa_sponsorship
    )
    profile_data["has_work_authorization"] = (
        form.get("has_work_authorization") == "on"
        if "has_work_authorization" in form
        else base_profile.has_work_authorization
    )
    profile_data["open_to_remote"] = (
        form.get("open_to_remote") == "on"
        if "open_to_remote" in form
        else base_profile.open_to_remote
    )
    profile_data["constraints"] = _form_lines(form, "constraints", base_profile.constraints)
    profile_data["experience_highlights"] = _form_lines(
        form,
        "experience_highlights",
        base_profile.experience_highlights,
    )

    company_preferences = dict(profile_data.get("company_preferences") or {})
    if "preferred_environments" in form:
        company_preferences["preferred_environments"] = form.getlist("preferred_environments")
    company_preferences["risk_tolerance"] = _form_text(
        form,
        "risk_tolerance",
        company_preferences.get("risk_tolerance", ""),
    )
    company_preferences["stability_priority"] = _form_text(
        form,
        "stability_priority",
        company_preferences.get("stability_priority", ""),
    )
    company_preferences["work_style_preference"] = _form_text(
        form,
        "work_style_preference",
        company_preferences.get("work_style_preference", ""),
    )
    company_preferences["brand_vs_growth_preference"] = _form_text(
        form,
        "brand_vs_growth_preference",
        company_preferences.get("brand_vs_growth_preference", ""),
    )
    company_preferences["notes"] = _form_lines(
        form,
        "company_notes",
        company_preferences.get("notes", []),
    )
    profile_data["company_preferences"] = company_preferences

    return UserProfile.from_dict(profile_data)


def _to_plain_data(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict):
        return {key: _to_plain_data(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_plain_data(item) for item in value]
    return value


def _to_namespace(value: Any) -> Any:
    if isinstance(value, dict):
        return SimpleNamespace(**{key: _to_namespace(item) for key, item in value.items()})
    if isinstance(value, list):
        return [_to_namespace(item) for item in value]
    return value


def _workflow_source_stem(workflow_payload: dict[str, Any]) -> str:
    scan = workflow_payload.get("scan") or {}
    source_path = str(scan.get("source_path", "")).strip()
    if source_path:
        return Path(source_path).stem or "career_workflow"

    saved_profile_relative = str(scan.get("saved_profile_relative", "")).strip()
    if saved_profile_relative:
        return Path(saved_profile_relative).stem or "career_workflow"

    return "career_workflow"


def _build_scan_context(scan_result: ResumeScanResult) -> dict[str, Any]:
    return {
        "source_path": str(scan_result.source_path),
        "extraction_mode": scan_result.extraction_mode,
        "missing_fields": list(scan_result.missing_fields),
        "confidence_notes": list(scan_result.confidence_notes),
        "saved_profile_relative": _to_output_relative(scan_result.saved_profile_path),
        "saved_text_relative": _to_output_relative(scan_result.saved_text_path),
    }


def _scan_result_from_workflow(workflow_payload: dict[str, Any]) -> ResumeScanResult:
    state_dict = workflow_payload.get("state") or {}
    scan = workflow_payload.get("scan") or {}
    profile = UserProfile.from_dict(state_dict.get("user_profile") or {})
    source_path = Path(str(scan.get("source_path") or "uploaded_resume"))
    return ResumeScanResult(
        profile=profile,
        source_path=source_path,
        extraction_mode=str(scan.get("extraction_mode") or "saved_scan_profile"),
        missing_fields=list(scan.get("missing_fields") or []),
        confidence_notes=list(scan.get("confidence_notes") or []),
        saved_profile_path=_resolve_if_present(scan.get("saved_profile_relative")),
        saved_text_path=_resolve_if_present(scan.get("saved_text_relative")),
    )


def _create_workflow_payload(scan_result: ResumeScanResult) -> dict[str, Any]:
    return {
        "stage": "scanned",
        "scan": _build_scan_context(scan_result),
        "state": create_initial_state(scan_result.profile).to_dict(),
        "state_output_relative": None,
        "updated_at": _timestamp(),
    }


def _save_workflow_payload(
    workflow_payload: dict[str, Any],
    source_stem: str,
    *,
    relative_path: str | None = None,
) -> Path:
    WEB_SESSION_ROOT.mkdir(parents=True, exist_ok=True)
    if relative_path:
        target = _resolve_output_relative(relative_path)
        if WEB_SESSION_ROOT.resolve() not in target.parents and target.parent != WEB_SESSION_ROOT.resolve():
            raise FileNotFoundError("Invalid workflow path.")
    else:
        target = WEB_SESSION_ROOT / f"{source_stem}_{_timestamp()}_workflow.json"
    target.write_text(
        json.dumps(workflow_payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return target


def _load_workflow_payload(relative_path: str) -> dict[str, Any]:
    target = _resolve_output_relative(relative_path)
    payload = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Invalid workflow payload.")
    payload.setdefault("stage", "scanned")
    payload.setdefault("state", create_initial_state(UserProfile()).to_dict())
    return payload


def _load_workflow_from_request(form) -> tuple[dict[str, Any], str]:
    relative_path = (form.get("workflow_path") or "").strip()
    if not relative_path:
        raise ValueError("Please scan a resume before continuing.")
    return _load_workflow_payload(relative_path), relative_path


def _persist_state_snapshot(workflow_payload: dict[str, Any]) -> None:
    state_path = _save_state_snapshot(
        workflow_payload.get("state") or {},
        _workflow_source_stem(workflow_payload),
    )
    workflow_payload["state_output_relative"] = _to_output_relative(state_path)
    workflow_payload["updated_at"] = _timestamp()


def _available_result_views(
    scan_result: ResumeScanResult | None,
    state_dict: dict[str, Any] | None,
    workflow_stage: str,
) -> list[str]:
    state_dict = state_dict or {}
    available: list[str] = []

    if scan_result is not None:
        available.append("scan")
    if state_dict.get("policy_result"):
        available.append("policy")
    if state_dict.get("industry_result"):
        available.append("industry")
    if WORKFLOW_STAGE_RANK.get(workflow_stage, -1) >= WORKFLOW_STAGE_RANK["preferences_complete"]:
        available.append("preferences")
    if state_dict.get("company_result"):
        available.append("company")
    if state_dict.get("role_result"):
        available.append("role")
    if state_dict.get("job_targeting_result"):
        available.append("job")
    if state_dict.get("growth_result"):
        available.append("growth")

    has_final = workflow_stage == "complete" or (
        workflow_stage == "growth_complete" and not state_dict.get("job_targeting_result")
    )
    if has_final:
        available.append("final")

    deduped: list[str] = []
    seen: set[str] = set()
    for item in available:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped


def _latest_result_view(
    scan_result: ResumeScanResult | None,
    state_dict: dict[str, Any] | None,
    workflow_stage: str,
) -> str:
    available = _available_result_views(scan_result, state_dict, workflow_stage)
    if not available:
        return ""
    if workflow_stage == "complete":
        return "final"
    if workflow_stage == "growth_complete":
        if state_dict and state_dict.get("job_targeting_result"):
            return "growth"
        return "final"

    stage_to_view = {
        "scanned": "scan",
        "policy_complete": "policy",
        "industry_complete": "industry",
        "preferences_complete": "preferences",
        "company_complete": "company",
        "role_complete": "role",
        "job_complete": "job",
        "job_skipped": "role",
    }
    candidate = stage_to_view.get(workflow_stage, available[-1])
    return candidate if candidate in available else available[-1]


def _normalize_result_view(
    requested_view: str,
    available_views: list[str],
    latest_view: str,
) -> str:
    if requested_view in available_views:
        return requested_view
    if latest_view in available_views:
        return latest_view
    return available_views[-1] if available_views else ""


def _previous_result_view(current_view: str, available_views: list[str]) -> str | None:
    if current_view not in available_views:
        return None
    current_index = available_views.index(current_view)
    if current_index <= 0:
        return None
    return available_views[current_index - 1]


def _build_final_summary(state_dict: dict[str, Any] | None) -> dict[str, Any]:
    state_dict = state_dict or {}
    summary_points: list[str] = []

    policy_result = state_dict.get("policy_result") or {}
    if policy_result:
        regions = ", ".join((policy_result.get("recommended_regions") or [])[:2])
        visa_risk = str(policy_result.get("visa_risk") or "").strip()
        mobility_strategy = str(policy_result.get("mobility_strategy") or "").strip()
        if visa_risk or regions:
            summary_points.append(
                f"Policy picture: visa risk is {visa_risk or 'not specified'}, with strongest regional focus on {regions or 'the recommended markets'}."
            )
        elif mobility_strategy:
            summary_points.append(f"Policy picture: {mobility_strategy}")

    industry_result = state_dict.get("industry_result") or {}
    top_industries = industry_result.get("top_industries") or []
    if top_industries:
        top_names = ", ".join(
            str(item.get("name", "")).strip() for item in top_industries[:2] if str(item.get("name", "")).strip()
        )
        if top_names:
            summary_points.append(f"Best-fit industries: {top_names}.")

    company_result = state_dict.get("company_result") or {}
    company_path = str(company_result.get("primary_company_path") or "").strip()
    if company_path:
        summary_points.append(f"Best company path right now: {company_path}.")

    role_result = state_dict.get("role_result") or {}
    recommended_paths = role_result.get("recommended_paths") or []
    if recommended_paths:
        lead_role = str((recommended_paths[0] or {}).get("role_title") or "").strip()
        if lead_role:
            summary_points.append(f"Lead role direction: {lead_role}.")

    job_result = state_dict.get("job_targeting_result") or {}
    if job_result:
        job_title = str(job_result.get("job_title") or "").strip()
        match_confidence = str(job_result.get("match_confidence") or "").strip()
        if job_title or match_confidence:
            summary_points.append(
                f"Job alignment: {job_title or 'Target role'} is currently a {match_confidence or 'pending'}-confidence match."
            )

    growth_result = state_dict.get("growth_result") or {}
    priority_gaps = growth_result.get("priority_gaps") or []
    if priority_gaps:
        summary_points.append(f"Most important gap to close next: {priority_gaps[0]}.")

    headline = "The full career strategy is now assembled."
    if company_path and recommended_paths:
        lead_role = str((recommended_paths[0] or {}).get("role_title") or "").strip()
        headline = (
            f"The strongest near-term path is {lead_role or 'the recommended role path'} "
            f"inside a {company_path}."
        )

    return {
        "headline": headline,
        "points": summary_points[:6],
    }


def _profile_from_workflow(workflow_payload: dict[str, Any]) -> UserProfile:
    state_dict = workflow_payload.get("state") or {}
    return UserProfile.from_dict(state_dict.get("user_profile") or {})


def _state_namespace(workflow_payload: dict[str, Any], key: str) -> Any:
    state_dict = workflow_payload.get("state") or {}
    value = state_dict.get(key)
    if value is None:
        return None
    return _to_namespace(value)


def _run_policy_step(workflow_payload: dict[str, Any], form) -> None:
    updated_profile = _apply_profile_form(form, _profile_from_workflow(workflow_payload))
    workflow_payload["state"] = create_initial_state(updated_profile).to_dict()
    workflow_payload["state"]["policy_result"] = _to_plain_data(run_policy_analysis(updated_profile))
    workflow_payload["stage"] = "policy_complete"


def _run_industry_step(workflow_payload: dict[str, Any]) -> None:
    profile = _profile_from_workflow(workflow_payload)
    policy_result = _state_namespace(workflow_payload, "policy_result")
    workflow_payload["state"]["industry_result"] = _to_plain_data(
        run_industry_selection(profile, policy_result)
    )
    workflow_payload["stage"] = "industry_complete"


def _save_preferences_step(workflow_payload: dict[str, Any], form) -> None:
    updated_profile = _apply_profile_form(form, _profile_from_workflow(workflow_payload))
    workflow_payload["state"]["user_profile"] = updated_profile.to_dict()
    workflow_payload["stage"] = "preferences_complete"


def _run_company_step(workflow_payload: dict[str, Any]) -> None:
    profile = _profile_from_workflow(workflow_payload)
    policy_result = _state_namespace(workflow_payload, "policy_result")
    industry_result = _state_namespace(workflow_payload, "industry_result")
    workflow_payload["state"]["company_result"] = _to_plain_data(
        run_company_strategy(profile, policy_result, industry_result)
    )
    workflow_payload["stage"] = "company_complete"


def _run_role_step(workflow_payload: dict[str, Any]) -> None:
    profile = _profile_from_workflow(workflow_payload)
    policy_result = _state_namespace(workflow_payload, "policy_result")
    industry_result = _state_namespace(workflow_payload, "industry_result")
    company_result = _state_namespace(workflow_payload, "company_result")
    workflow_payload["state"]["role_result"] = _to_plain_data(
        run_role_path(profile, policy_result, industry_result, company_result)
    )
    workflow_payload["stage"] = "role_complete"


def _run_job_targeting_step(workflow_payload: dict[str, Any], form) -> None:
    job_description = _form_text(form, "job_description")
    if not job_description:
        raise ValueError("Please paste a target job description before running Job Alignment.")

    profile = _profile_from_workflow(workflow_payload)
    policy_result = _state_namespace(workflow_payload, "policy_result")
    industry_result = _state_namespace(workflow_payload, "industry_result")
    company_result = _state_namespace(workflow_payload, "company_result")
    role_result = _state_namespace(workflow_payload, "role_result")
    workflow_payload["state"]["job_description"] = job_description
    workflow_payload["state"]["job_targeting_result"] = _to_plain_data(
        run_job_targeting(
            profile,
            policy_result,
            industry_result,
            company_result,
            role_result,
            job_description,
        )
    )
    workflow_payload["stage"] = "job_complete"


def _skip_job_targeting_step(workflow_payload: dict[str, Any]) -> None:
    workflow_payload["state"]["job_description"] = ""
    workflow_payload["state"]["job_targeting_result"] = None
    workflow_payload["state"]["application_assets_result"] = None
    workflow_payload["stage"] = "job_skipped"


def _run_growth_step(workflow_payload: dict[str, Any]) -> None:
    profile = _profile_from_workflow(workflow_payload)
    policy_result = _state_namespace(workflow_payload, "policy_result")
    industry_result = _state_namespace(workflow_payload, "industry_result")
    company_result = _state_namespace(workflow_payload, "company_result")
    role_result = _state_namespace(workflow_payload, "role_result")
    job_result = _state_namespace(workflow_payload, "job_targeting_result")
    job_description = str((workflow_payload.get("state") or {}).get("job_description") or "")
    workflow_payload["state"]["growth_result"] = _to_plain_data(
        run_growth_plan(
            profile,
            policy_result,
            industry_result,
            company_result,
            role_result,
            job_result,
            job_description,
        )
    )
    workflow_payload["stage"] = "growth_complete"


def _run_application_assets_step(workflow_payload: dict[str, Any]) -> None:
    profile = _profile_from_workflow(workflow_payload)
    company_result = _state_namespace(workflow_payload, "company_result")
    role_result = _state_namespace(workflow_payload, "role_result")
    job_result = _state_namespace(workflow_payload, "job_targeting_result")
    growth_result = _state_namespace(workflow_payload, "growth_result")
    if job_result is None:
        raise ValueError("Application Assets require a completed Job Alignment step.")
    workflow_payload["state"]["application_assets_result"] = _to_plain_data(
        run_application_assets(
            profile,
            company_result,
            role_result,
            job_result,
            growth_result,
        )
    )
    workflow_payload["stage"] = "complete"


@app.route("/", methods=["GET", "POST"])
def index():
    refresh_llm_environment()
    status = llm_status()
    error_message = ""
    status_message = ""
    action = "scan_resume"
    workflow_path_relative: str | None = None
    workflow_payload: dict[str, Any] | None = None
    scan_result: ResumeScanResult | None = None
    state_dict: dict[str, Any] | None = None
    workflow_stage = "new"
    current_result_view = ""

    if request.method == "POST":
        action = (request.form.get("action") or "scan_resume").strip()
        try:
            if not status["available"]:
                raise RuntimeError(
                    "Gemini is not ready. Add a valid GEMINI_API_KEY and required dependencies first."
                )

            if action == "scan_resume":
                uploaded_file = request.files.get("resume_file")
                if uploaded_file is None or not uploaded_file.filename:
                    raise ValueError("Please upload a resume file.")
                saved_upload = _save_uploaded_file(uploaded_file)
                scan_result = scan_resume_to_profile(saved_upload)
                workflow_payload = _create_workflow_payload(scan_result)
                workflow_path = _save_workflow_payload(
                    workflow_payload,
                    _workflow_source_stem(workflow_payload),
                )
                workflow_path_relative = _to_output_relative(workflow_path)
                status_message = (
                    "Resume scanned. Review the extracted profile, then decide when to start Policy Analysis."
                )
                current_result_view = "scan"
            else:
                workflow_payload, workflow_path_relative = _load_workflow_from_request(request.form)

                if action == "view_stage":
                    current_result_view = (request.form.get("target_view") or "").strip()
                    status_message = "Showing a previous step result."
                elif action == "view_latest":
                    status_message = "Showing the latest available result."
                elif action == "run_policy":
                    _run_policy_step(workflow_payload, request.form)
                    status_message = "Policy / Region is ready. Continue to Industry when you want the next layer."
                    current_result_view = "policy"
                elif action == "run_industry":
                    _run_industry_step(workflow_payload)
                    status_message = "Industry prioritization is ready. Next up is Company Preference."
                    current_result_view = "industry"
                elif action == "save_preferences":
                    _save_preferences_step(workflow_payload, request.form)
                    status_message = (
                        "Company preferences saved. Review the summary, then continue to Company Strategy."
                    )
                    current_result_view = "preferences"
                elif action == "run_company":
                    _run_company_step(workflow_payload)
                    status_message = "Company Strategy is ready. Continue to Role Path when you are ready."
                    current_result_view = "company"
                elif action == "run_role":
                    _run_role_step(workflow_payload)
                    status_message = "Role Path is ready. Choose whether to add a target job description next."
                    current_result_view = "role"
                elif action == "run_job_targeting":
                    _run_job_targeting_step(workflow_payload, request.form)
                    status_message = "Job Alignment is ready. You can now continue to Growth Plan."
                    current_result_view = "job"
                elif action == "skip_job_targeting":
                    _skip_job_targeting_step(workflow_payload)
                    status_message = "Job Alignment was skipped. You can continue directly to Growth Plan."
                    current_result_view = "role"
                elif action == "run_growth":
                    _run_growth_step(workflow_payload)
                    if (workflow_payload.get("state") or {}).get("job_targeting_result"):
                        status_message = (
                            "Growth Plan is ready. You can continue to Application Assets if you want the final candidate materials."
                        )
                        current_result_view = "growth"
                    else:
                        status_message = "Growth Plan is ready."
                        current_result_view = "final"
                elif action == "run_application_assets":
                    _run_application_assets_step(workflow_payload)
                    status_message = "Application Assets are ready. The staged workflow is complete."
                    current_result_view = "final"
                elif action == "stay_stage":
                    status_message = "Progress is saved. Stay on this stage and continue whenever you want."
                else:
                    raise ValueError("Unsupported action.")

                if workflow_payload is not None and action != "scan_resume":
                    if action not in {"stay_stage", "view_stage", "view_latest"}:
                        _persist_state_snapshot(workflow_payload)
                    workflow_path = _save_workflow_payload(
                        workflow_payload,
                        _workflow_source_stem(workflow_payload),
                        relative_path=workflow_path_relative,
                    )
                    workflow_path_relative = _to_output_relative(workflow_path)

            if workflow_payload is not None:
                scan_result = _scan_result_from_workflow(workflow_payload)
                state_dict = workflow_payload.get("state") or {}
                workflow_stage = str(workflow_payload.get("stage") or "scanned")
        except Exception as exc:
            error_message = str(exc)
            if workflow_payload is not None:
                scan_result = _scan_result_from_workflow(workflow_payload)
                state_dict = workflow_payload.get("state") or {}
                workflow_stage = str(workflow_payload.get("stage") or "scanned")

    if workflow_payload is None and scan_result is not None:
        state_dict = create_initial_state(scan_result.profile).to_dict()
        workflow_stage = "scanned"
        current_result_view = "scan"

    profile_dict = None
    job_description = ""
    state_output_relative = None
    if state_dict:
        profile_dict = (state_dict or {}).get("user_profile")
        job_description = str((state_dict or {}).get("job_description") or "")
    if workflow_payload:
        state_output_relative = workflow_payload.get("state_output_relative")

    available_result_views = _available_result_views(scan_result, state_dict, workflow_stage)
    latest_result_view = _latest_result_view(scan_result, state_dict, workflow_stage)
    current_result_view = _normalize_result_view(
        current_result_view,
        available_result_views,
        latest_result_view,
    )
    previous_result_view = _previous_result_view(current_result_view, available_result_views)
    final_summary = _build_final_summary(state_dict) if current_result_view == "final" else None

    return render_template(
        "upload.html",
        llm_status=status,
        error_message=error_message,
        status_message=status_message,
        action=action,
        scan_result=scan_result,
        scan_output_relative=_to_output_relative(scan_result.saved_profile_path) if scan_result else None,
        scan_text_relative=_to_output_relative(scan_result.saved_text_path) if scan_result else None,
        profile_dict=profile_dict,
        state_dict=state_dict,
        state_output_relative=state_output_relative,
        workflow_path=workflow_path_relative,
        workflow_stage=workflow_stage,
        workflow_stage_rank=WORKFLOW_STAGE_RANK.get(workflow_stage, -1),
        current_result_view=current_result_view,
        current_result_label=RESULT_VIEW_LABELS.get(current_result_view, ""),
        latest_result_view=latest_result_view,
        latest_result_label=RESULT_VIEW_LABELS.get(latest_result_view, ""),
        previous_result_view=previous_result_view,
        previous_result_label=RESULT_VIEW_LABELS.get(previous_result_view or "", ""),
        available_result_views=available_result_views,
        final_summary=final_summary,
        company_environment_options=COMPANY_ENVIRONMENT_OPTIONS,
        risk_tolerance_options=RISK_TOLERANCE_OPTIONS,
        stability_priority_options=STABILITY_PRIORITY_OPTIONS,
        work_style_options=WORK_STYLE_OPTIONS,
        brand_vs_growth_options=BRAND_VS_GROWTH_OPTIONS,
        job_description=job_description,
    )


def main() -> None:
    host = os.getenv("CAREER_WEB_HOST", "127.0.0.1")
    port = int(os.getenv("CAREER_WEB_PORT", "5000"))
    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    main()
