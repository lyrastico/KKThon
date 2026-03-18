from __future__ import annotations

from decimal import Decimal
from typing import Any


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def compute_analysis_metrics(findings: list[dict[str, Any]]) -> dict[str, Any]:
    if not findings:
        return {
            "total_findings": 0,
            "passed_findings": 0,
            "failed_findings": 0,
            "completion_rate": 0.0,
            "confidence_avg": None,
            "severity_counts": {},
            "finding_type_counts": {},
        }

    total = len(findings)
    passed = sum(1 for finding in findings if finding.get("is_pass") is True)
    failed = sum(1 for finding in findings if finding.get("is_pass") is False)

    confidences = [
        confidence
        for confidence in (_to_float(finding.get("confidence")) for finding in findings)
        if confidence is not None
    ]

    severity_counts: dict[str, int] = {}
    finding_type_counts: dict[str, int] = {}
    for finding in findings:
        severity = finding.get("severity") or "unknown"
        severity_counts[severity] = severity_counts.get(severity, 0) + 1

        finding_type = finding.get("finding_type") or "unknown"
        finding_type_counts[finding_type] = finding_type_counts.get(finding_type, 0) + 1

    return {
        "total_findings": total,
        "passed_findings": passed,
        "failed_findings": failed,
        "completion_rate": round(passed / total, 4) if total else 0.0,
        "confidence_avg": round(sum(confidences) / len(confidences), 4) if confidences else None,
        "severity_counts": severity_counts,
        "finding_type_counts": finding_type_counts,
    }
