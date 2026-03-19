import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("API_BASE_URL")
FILES_URL = f"{BASE_URL}/api/v1/files"


class FileServiceError(Exception):
    pass


@dataclass
class FileRecord:
    file_id: UUID
    client_id: UUID
    original_filename: str
    s3_raw_path: str
    s3_silver_path: str | None
    silver_content: dict[str, Any] | None
    file_format: str | None
    type: str | None
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


def list_files(access_token: str, client_id: str | UUID, skip: int = 0, limit: int = 100) -> list[FileRecord]:
    resp = requests.get(
        FILES_URL,
        headers=_headers(access_token),
        params={"client_id": str(client_id), "skip": skip, "limit": limit},
        timeout=10,
    )
    if resp.status_code != 200:
        raise FileServiceError(_error_detail(resp))
    return [FileRecord(**f) for f in resp.json()]


def upload_file(access_token: str, client_id: str | UUID, file_bytes: bytes, filename: str, content_type: str) -> FileRecord:
    resp = requests.post(
        f"{FILES_URL}/upload",
        headers=_headers(access_token),
        data={"client_id": str(client_id)},
        files={"file": (filename, file_bytes, content_type)},
        timeout=30,
    )
    if resp.status_code not in (200, 201):
        raise FileServiceError(_error_detail(resp))
    return FileRecord(**resp.json())


def get_file(access_token: str, file_id: str | UUID) -> FileRecord:
    """Fetch a single file record by ID."""
    resp = requests.get(
        f"{FILES_URL}/{file_id}",
        headers=_headers(access_token),
        timeout=10,
    )
    if resp.status_code != 200:
        raise FileServiceError(_error_detail(resp))
    return FileRecord(**resp.json())


def delete_file(access_token: str, file_id: str | UUID) -> None:
    resp = requests.delete(
        f"{FILES_URL}/{file_id}",
        headers=_headers(access_token),
        timeout=10,
    )
    if resp.status_code not in (200, 204):
        raise FileServiceError(_error_detail(resp))