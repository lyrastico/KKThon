from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.analysis_finding import AnalysisFindingRepository
from app.repositories.analysis_run import AnalysisRunRepository
from app.repositories.document import DocumentRepository
from app.schemas.silver import SilverIngestResponse, SilverPayload
from app.services.document_compliance import run_document_compliance_checks
from app.services.metrics_extractor import compute_analysis_metrics
from app.services.silver_mapper import build_analysis_run_data, build_findings_from_silver


class DocumentAnalyzerService:
    def __init__(
        self,
        analysis_run_repo: AnalysisRunRepository,
        analysis_finding_repo: AnalysisFindingRepository,
        document_repo: DocumentRepository,
    ):
        self.analysis_run_repo = analysis_run_repo
        self.analysis_finding_repo = analysis_finding_repo
        self.document_repo = document_repo

    async def ingest_silver_payload(self, db: AsyncSession, payload: SilverPayload) -> SilverIngestResponse:
        analysis_run_data = build_analysis_run_data(payload)
        extraction_findings = build_findings_from_silver(payload, analysis_run_id=None)
        compliance_findings = run_document_compliance_checks(payload)
        all_findings = extraction_findings + compliance_findings
        metrics = compute_analysis_metrics(all_findings)

        silver_output = dict(analysis_run_data.get("silver_output") or {})
        silver_output["metrics"] = metrics
        analysis_run_data["silver_output"] = silver_output
        analysis_run_data["status"] = "completed" if metrics["failed_findings"] == 0 else "completed_with_issues"

        analysis_run = await self.analysis_run_repo.create(db, analysis_run_data)

        findings_created = 0
        for finding in all_findings:
            finding_payload: dict[str, Any] = dict(finding)
            finding_payload["analysis_run_id"] = analysis_run.id
            await self.analysis_finding_repo.create(db, finding_payload)
            findings_created += 1

        document = await self.document_repo.get(db, payload.document_id)
        if document is not None:
            compliance_status = "compliant" if metrics["failed_findings"] == 0 else "non_compliant"
            await self.document_repo.update(
                db,
                document,
                {
                    "latest_analysis_run_id": analysis_run.id,
                    "compliance_status": compliance_status,
                    "status": "analyzed",
                },
            )

        return SilverIngestResponse(
            analysis_run_id=analysis_run.id,
            findings_created=findings_created,
        )
