import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("API_BASE_URL")
REPORTS_URL = f"{BASE_URL}/api/v1/conformity-reports"


class ConformityReportServiceError(Exception):
    pass


@dataclass
class ConformityReport:
    report_id: UUID
    client_id: UUID
    gold_content: dict[str, Any] | None
    silver_content: dict[str, Any] | None
    s3_gold_path: str | None
    processing_status: str
    created_at: str
    updated_at: str


def _headers(access_token: str) -> dict:
    return {"Authorization": f"Bearer {access_token}"}


def _error_detail(resp: requests.Response) -> str:
    try:
        return resp.json().get("detail", "Unexpected error")
    except Exception:
        return f"HTTP {resp.status_code}"


def create_report(access_token: str, client_id: str | UUID, dry_run: bool = False) -> ConformityReport:
    """Triggers Gold analysis generation for all done files of the client."""
    resp = requests.post(
        REPORTS_URL,
        headers=_headers(access_token),
        json={"client_id": str(client_id), "dry_run": dry_run},
        timeout=30,
    )
    if resp.status_code not in (200, 201):
        raise ConformityReportServiceError(_error_detail(resp))
    return ConformityReport(**resp.json())


def list_reports(access_token: str, client_id: str | UUID, skip: int = 0, limit: int = 100) -> list[ConformityReport]:
    resp = requests.get(
        REPORTS_URL,
        headers=_headers(access_token),
        params={"client_id": str(client_id), "skip": skip, "limit": limit},
        timeout=10,
    )
    if resp.status_code != 200:
        raise ConformityReportServiceError(_error_detail(resp))
    return [ConformityReport(**r) for r in resp.json()]


def get_report(access_token: str, report_id: str | UUID) -> ConformityReport:
    resp = requests.get(
        f"{REPORTS_URL}/{report_id}",
        headers=_headers(access_token),
        timeout=10,
    )
    if resp.status_code != 200:
        raise ConformityReportServiceError(_error_detail(resp))
    return ConformityReport(**resp.json())


def delete_report(access_token: str, report_id: str | UUID) -> None:
    resp = requests.delete(
        f"{REPORTS_URL}/{report_id}",
        headers=_headers(access_token),
        timeout=10,
    )
    if resp.status_code not in (200, 204):
        raise ConformityReportServiceError(_error_detail(resp))