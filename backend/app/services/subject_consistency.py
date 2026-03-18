from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.analysis_finding import AnalysisFindingRepository
from app.repositories.analysis_run import AnalysisRunRepository
from app.repositories.document import DocumentRepository
from app.repositories.subject_consistency_run import SubjectConsistencyRunRepository
from app.repositories.subject_finding import SubjectFindingRepository


class SubjectConsistencyService:
    def __init__(
        self,
        document_repo: DocumentRepository,
        analysis_run_repo: AnalysisRunRepository,
        analysis_finding_repo: AnalysisFindingRepository,
        subject_consistency_run_repo: SubjectConsistencyRunRepository,
        subject_finding_repo: SubjectFindingRepository,
    ):
        self.document_repo = document_repo
        self.analysis_run_repo = analysis_run_repo
        self.analysis_finding_repo = analysis_finding_repo
        self.subject_consistency_run_repo = subject_consistency_run_repo
        self.subject_finding_repo = subject_finding_repo

    async def execute(self, db: AsyncSession, subject_id: UUID) -> dict[str, Any]:
        documents = await self.document_repo.list_by_subject(db, subject_id)
        analysis_runs = []
        for document in documents:
            runs = await self.analysis_run_repo.list_by_document(db, document.id, limit=1)
            if runs:
                analysis_runs.append(runs[0])

        run = await self.subject_consistency_run_repo.create(
            db,
            {
                "subject_id": subject_id,
                "status": "completed" if analysis_runs else "completed_with_issues",
                "input_analysis_run_ids": [str(item.id) for item in analysis_runs],
                "gold_output": None,
                "error_message": None,
            },
        )

        findings = await self._build_subject_findings(db, run.id, analysis_runs)
        gold_output = {
            "documents_count": len(documents),
            "analysis_runs_count": len(analysis_runs),
            "metrics": self._compute_subject_metrics(findings),
        }
        await self.subject_consistency_run_repo.update(db, run, {"gold_output": gold_output})

        return {
            "subject_consistency_run_id": run.id,
            "findings_created": len(findings),
            "gold_output": gold_output,
        }

    async def _build_subject_findings(self, db: AsyncSession, subject_consistency_run_id: UUID, analysis_runs: list[Any]) -> list[dict[str, Any]]:
        extracted_values_by_code: dict[str, list[dict[str, Any]]] = defaultdict(list)

        for analysis_run in analysis_runs:
            findings = await self.analysis_finding_repo.list_by_analysis_run(db, analysis_run.id, limit=500)
            for finding in findings:
                if finding.finding_type != "field_extraction":
                    continue
                if finding.extracted_value in (None, "", {}):
                    continue
                extracted_values_by_code[finding.code].append(
                    {
                        "analysis_run_id": analysis_run.id,
                        "value": finding.extracted_value,
                        "confidence": self._to_float(finding.confidence),
                    }
                )

        subject_findings: list[dict[str, Any]] = []
        required_codes = {
            "siren": "SIREN",
            "raison_sociale": "Raison sociale",
        }

        for code, label in required_codes.items():
            values = extracted_values_by_code.get(code, [])
            if not values:
                subject_findings.append(
                    {
                        "subject_consistency_run_id": subject_consistency_run_id,
                        "code": f"missing_{code}",
                        "label": f"Présence {label} dossier",
                        "severity": "error",
                        "is_pass": False,
                        "confidence": None,
                        "message": f"Aucune valeur disponible pour {label}",
                        "details": {"field": code, "rule": "required_across_subject"},
                    }
                )
                continue

            normalized = {self._normalize_value(item["value"]) for item in values}
            is_consistent = len(normalized) == 1
            subject_findings.append(
                {
                    "subject_consistency_run_id": subject_consistency_run_id,
                    "code": f"consistent_{code}",
                    "label": f"Cohérence {label}",
                    "severity": "info" if is_consistent else "error",
                    "is_pass": is_consistent,
                    "confidence": self._avg_confidence(values),
                    "message": f"{label} cohérent entre documents" if is_consistent else f"{label} incohérent entre documents",
                    "details": {"field": code, "values": values, "distinct_values": sorted(normalized)},
                }
            )

        for finding in subject_findings:
            await self.subject_finding_repo.create(db, finding)
        return subject_findings

    def _compute_subject_metrics(self, findings: list[dict[str, Any]]) -> dict[str, Any]:
        total = len(findings)
        passed = sum(1 for item in findings if item.get("is_pass") is True)
        failed = sum(1 for item in findings if item.get("is_pass") is False)
        return {
            "total_findings": total,
            "passed_findings": passed,
            "failed_findings": failed,
            "consistency_rate": round(passed / total, 4) if total else 0.0,
        }

    def _normalize_value(self, value: Any) -> str:
        return str(value).strip().lower()

    def _avg_confidence(self, values: list[dict[str, Any]]) -> float | None:
        confidences = [value["confidence"] for value in values if value.get("confidence") is not None]
        if not confidences:
            return None
        return round(sum(confidences) / len(confidences), 4)

    def _to_float(self, value: Any) -> float | None:
        if value is None:
            return None
        if isinstance(value, Decimal):
            return float(value)
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
