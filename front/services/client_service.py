import os
import requests
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

BASE_URL = os.getenv("API_BASE_URL")
AUTH_URL = f"{BASE_URL}/api/v1/clients"

class ClientServiceError(Exception):
    pass


@dataclass
class Client:
    client_id: UUID
    user_id: UUID
    client_name: str
    created_at: str
    updated_at: str


def _headers(access_token: str) -> dict:
    return {"Authorization": f"Bearer {access_token}"}

def _error_detail(resp) -> str:
    try:
        return resp.json().get("detail", "Unexpected error")
    except Exception:
        return f"HTTP {resp.status_code}"

def list_clients(access_token: str, skip: int = 0, limit: int = 100) -> list[Client]:
    resp = requests.get(
        f"{AUTH_URL}",
        headers=_headers(access_token),
        params={"skip": skip, "limit": limit},
        timeout=10,
    )
    if resp.status_code != 200:
        raise ClientServiceError(_error_detail(resp))
    return [Client(**c) for c in resp.json()]


def create_client(access_token: str, client_name: str) -> Client:
    resp = requests.post(
        f"{AUTH_URL}",
        headers=_headers(access_token),
        json={"client_name": client_name},
        timeout=10,
    )
    if resp.status_code != 201:
        raise ClientServiceError(resp.json().get("detail", "Failed to create client"))
    return Client(**resp.json())


def delete_client(access_token: str, client_id: str) -> None:
    resp = requests.delete(
        f"{AUTH_URL}/{client_id}",
        headers=_headers(access_token),
        timeout=10,
    )
    if resp.status_code not in (200, 204):
        raise ClientServiceError(resp.json().get("detail", "Failed to delete client"))