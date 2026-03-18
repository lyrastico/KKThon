from __future__ import annotations

from datetime import date
from typing import Any

from app.schemas.silver import SilverPayload


REQUIRED_FIELDS: dict[str, str] = {
    "siren": "SIREN",
    "date_validite": "Date de validité",
    "raison_sociale": "Raison sociale",
}

OPTIONAL_FIELDS: dict[str, str] = {
    "code_verification": "Code de vérification",
}


def _is_blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def run_document_compliance_checks(payload: SilverPayload) -> list[dict[str, Any]]:
    data = payload.result.data
    confidence = payload.result.confidence_score
    today = date.today()
    findings: list[dict[str, Any]] = []

    field_values = {
        "siren": data.siren,
        "date_validite": data.date_validite,
        "raison_sociale": data.raison_sociale,
        "code_verification": data.code_verification,
    }

    for field_name, label in REQUIRED_FIELDS.items():
        value = field_values[field_name]
        passed = not _is_blank(value)
        findings.append(
            {
                "finding_type": "compliance_check",
                "code": f"required_{field_name}",
                "label": f"Présence {label}",
                "severity": "info" if passed else "error",
                "is_pass": passed,
                "confidence": confidence,
                "message": f"{label} présent" if passed else f"{label} manquant",
                "extracted_value": value,
                "details": {"field": field_name, "rule": "required_field"},
            }
        )

    for field_name, label in OPTIONAL_FIELDS.items():
        value = field_values[field_name]
        passed = not _is_blank(value)
        findings.append(
            {
                "finding_type": "compliance_check",
                "code": f"optional_{field_name}",
                "label": f"Présence {label}",
                "severity": "info" if passed else "warning",
                "is_pass": passed,
                "confidence": confidence,
                "message": f"{label} présent" if passed else f"{label} absent",
                "extracted_value": value,
                "details": {"field": field_name, "rule": "optional_field"},
            }
        )

    siren = (data.siren or "").strip() if data.siren else ""
    siren_is_valid = siren.isdigit() and len(siren) == 9
    findings.append(
        {
            "finding_type": "compliance_check",
            "code": "siren_format",
            "label": "Format SIREN",
            "severity": "info" if siren_is_valid else "error",
            "is_pass": siren_is_valid,
            "confidence": confidence,
            "message": "Format SIREN valide" if siren_is_valid else "Le SIREN doit contenir 9 chiffres",
            "extracted_value": data.siren,
            "details": {"field": "siren", "rule": "digits_len_9"},
        }
    )

    date_validite = data.date_validite
    if date_validite is None:
        findings.append(
            {
                "finding_type": "compliance_check",
                "code": "date_validite_not_expired",
                "label": "Date de validité non expirée",
                "severity": "error",
                "is_pass": False,
                "confidence": confidence,
                "message": "Impossible de vérifier la validité sans date",
                "extracted_value": None,
                "details": {"field": "date_validite", "rule": "not_expired"},
            }
        )
    else:
        not_expired = date_validite >= today
        findings.append(
            {
                "finding_type": "compliance_check",
                "code": "date_validite_not_expired",
                "label": "Date de validité non expirée",
                "severity": "info" if not_expired else "error",
                "is_pass": not_expired,
                "confidence": confidence,
                "message": "Document encore valide" if not_expired else "Document expiré",
                "extracted_value": date_validite.isoformat(),
                "details": {"field": "date_validite", "rule": "not_expired", "today": today.isoformat()},
            }
        )

    document_detected = payload.result.document_detected
    type_detected = bool(document_detected)
    findings.append(
        {
            "finding_type": "compliance_check",
            "code": "document_detected",
            "label": "Type de document identifié",
            "severity": "info" if type_detected else "warning",
            "is_pass": type_detected,
            "confidence": confidence,
            "message": f"Type détecté : {document_detected}" if type_detected else "Type de document non détecté",
            "extracted_value": document_detected,
            "details": {"field": "document_detected", "rule": "detected"},
        }
    )

    return findings
