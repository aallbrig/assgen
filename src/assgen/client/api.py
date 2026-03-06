"""HTTP client wrapper for the assgen server API.

Thin synchronous wrapper around httpx that raises friendly errors.
"""
from __future__ import annotations

from typing import Any

import httpx

from assgen.config import load_client_config

DEFAULT_TIMEOUT = 30.0


class APIError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"HTTP {status_code}: {detail}")


class APIClient:
    def __init__(self, base_url: str, timeout: float = DEFAULT_TIMEOUT) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(base_url=self.base_url, timeout=timeout)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "APIClient":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    def health(self) -> dict[str, Any]:
        return self._get("/health")

    def is_healthy(self) -> bool:
        try:
            self.health()
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Jobs
    # ------------------------------------------------------------------

    def enqueue_job(
        self,
        job_type: str,
        params: dict[str, Any],
        priority: int = 0,
        tags: list[str] | None = None,
        model_id: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "job_type": job_type,
            "params": params,
            "priority": priority,
            "tags": tags or [],
        }
        if model_id:
            body["model_id"] = model_id
        return self._post("/jobs", body)

    def get_job(self, job_id: str) -> dict[str, Any]:
        return self._get(f"/jobs/{job_id}")

    def list_jobs(
        self,
        statuses: list[str] | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"limit": limit}
        if statuses:
            params["status"] = statuses
        return self._get("/jobs", params=params)

    def cancel_job(self, job_id: str) -> None:
        self._delete(f"/jobs/{job_id}")

    # ------------------------------------------------------------------
    # Models
    # ------------------------------------------------------------------

    def list_models(self) -> list[dict[str, Any]]:
        return self._get("/models")

    def get_model(self, model_id: str) -> dict[str, Any]:
        return self._get(f"/models/{model_id}")

    def install_models(self, model_ids: list[str] | None = None) -> dict[str, Any]:
        return self._post("/models/install", {"model_ids": model_ids})

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------

    def _get(self, path: str, params: dict | None = None) -> Any:
        r = self._client.get(path, params=params)
        return self._handle(r)

    def _post(self, path: str, body: dict) -> Any:
        r = self._client.post(path, json=body)
        return self._handle(r)

    def _delete(self, path: str) -> None:
        r = self._client.delete(path)
        self._handle(r)

    @staticmethod
    def _handle(response: httpx.Response) -> Any:
        if response.status_code in (200, 201, 202, 204):
            if response.status_code == 204 or not response.content:
                return None
            return response.json()
        try:
            detail = response.json().get("detail", response.text)
        except Exception:
            detail = response.text
        raise APIError(response.status_code, str(detail))


# ---------------------------------------------------------------------------
# Factory — builds a client pointing at the configured (or auto-started) server
# ---------------------------------------------------------------------------

def get_client() -> APIClient:
    """Return an APIClient connected to the configured or auto-started server."""
    from assgen.client.auto_server import get_or_start_server
    url = get_or_start_server()
    cfg = load_client_config()
    return APIClient(url, timeout=float(cfg.get("default_timeout", DEFAULT_TIMEOUT)))
