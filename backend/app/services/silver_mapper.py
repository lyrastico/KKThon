from __future__ import annotations

from typing import Any

from app.schemas.silver import SilverPayload


FIELD_LABELS: dict[str, str] = {
    "siren": "SIREN",
    "date_validite": "Date de validité",
    "raison_sociale": "Raison sociale",
    "code_verification": "Code de vérification",
}


MISSING_FIELD_SEVERITY: dict[str, str] = {
    "code_verification": "warning",
}


MISSING_FIELD_MESSAGES: dict[str, str] = {
    "code_verification": "Code de vérification absent",
}


EXTRACTION_SOURCE_PREFIX = "result.data"


def _to_json_compatible(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def build_analysis_run_data(payload: SilverPayload) -> dict[str, Any]:
    silver_output = payload.model_dump(mode="json")
    return {
        "document_id": payload.document_id,
        "document_file_id": payload.document_file_id,
        "model_name": payload.processing.model,
        "model_version": None,
        "status": "completed",
        "bronze_status": "completed",
        "silver_status": "completed",
        "bronze_output": None,
        "silver_output": silver_output,
        "error_message": None,
        "started_at": payload.processing.processed_at,
        "finished_at": payload.processing.processed_at,
    }


def build_findings_from_silver(payload: SilverPayload, analysis_run_id) -> list[dict[str, Any]]:
    result = payload.result
    data = result.data
    confidence = result.confidence_score
    findings: list[dict[str, Any]] = []

    if result.document_detected is not None:
        findings.append(
            {
                "analysis_run_id": analysis_run_id,
                "finding_type": "document_classification",
                "code": "document_detected",
                "label": "Type de document détecté",
                "severity": "info",
                "is_pass": True,
                "confidence": confidence,
                "message": f"Document détecté : {result.document_detected}",
                "extracted_value": result.document_detected,
                "details": {"source_path": "result.document_detected"},
            }
        )

    extracted_fields = {
        "siren": data.siren,
        "date_validite": data.date_validite,
        "raison_sociale": data.raison_sociale,
        "code_verification": data.code_verification,
    }
    extracted_fields.update(data.extractions)

    for field_name, raw_value in extracted_fields.items():
        value = _to_json_compatible(raw_value)
        label = FIELD_LABELS.get(field_name, field_name.replace("_", " ").title())
        is_pass = value is not None
        severity = "info" if is_pass else MISSING_FIELD_SEVERITY.get(field_name, "warning")
        message = (
            f"{label} extrait avec succès"
            if is_pass
            else MISSING_FIELD_MESSAGES.get(field_name, f"{label} absent")
        )

        findings.append(
            {
                "analysis_run_id": analysis_run_id,
                "finding_type": "field_extraction",
                "code": field_name,
                "label": label,
                "severity": severity,
                "is_pass": is_pass,
                "confidence": confidence,
                "message": message,
                "extracted_value": value,
                "details": {"source_path": f"{EXTRACTION_SOURCE_PREFIX}.{field_name}"},
            }
        )

    for check in result.checks:
        findings.append(
            {
                "analysis_run_id": analysis_run_id,
                "finding_type": check.get("finding_type", "validation_check"),
                "code": check.get("code", "unknown_check"),
                "label": check.get("label", check.get("code", "Check")),
                "severity": check.get("severity"),
                "is_pass": check.get("is_pass"),
                "confidence": check.get("confidence", confidence),
                "message": check.get("message"),
                "extracted_value": check.get("extracted_value"),
                "details": check.get("details", {}),
            }
        )

    return findings
