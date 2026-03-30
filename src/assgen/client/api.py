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
    def __init__(self, base_url: str, timeout: float = DEFAULT_TIMEOUT, api_key: str | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        headers: dict[str, str] = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        self._client = httpx.Client(base_url=self.base_url, timeout=timeout, headers=headers)

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

    def list_job_files(self, job_id: str) -> list[str]:
        """Return the list of output filenames for a completed job."""
        result = self._get(f"/jobs/{job_id}/files")
        return result if isinstance(result, list) else []

    def download_job_file(self, job_id: str, filename: str) -> bytes:
        """Download the raw bytes of a specific output file."""
        r = self._client.get(f"/jobs/{job_id}/files/{filename}")
        if r.status_code == 200:
            return r.content
        try:
            detail = r.json().get("detail", r.text)
        except Exception:
            detail = r.text
        raise APIError(r.status_code, str(detail))

    def stream_job_events(self, job_id: str, remaining_timeout: float | None = None):
        """Yield parsed SSE event dicts from GET /jobs/{id}/events.

        Each yielded dict has keys: ``progress`` (float), ``message`` (str),
        ``status`` (str).

        Raises :class:`APIError` if the server returns a non-200 response.
        The stream ends naturally when the server closes it (job terminal).
        """
        import json as _json

        stream_timeout = httpx.Timeout(
            connect=10.0,
            read=remaining_timeout or 3600.0,
            write=10.0,
            pool=10.0,
        )
        with self._client.stream(
            "GET",
            f"/jobs/{job_id}/events",
            timeout=stream_timeout,
        ) as response:
            if response.status_code != 200:
                response.read()
                try:
                    detail = response.json().get("detail", response.text)
                except Exception:
                    detail = response.text
                raise APIError(response.status_code, str(detail))

            for line in response.iter_lines():
                if line.startswith("data: "):
                    try:
                        yield _json.loads(line[6:])
                    except _json.JSONDecodeError:
                        pass
                elif line.startswith("event: error"):
                    pass  # next data line will have the error payload

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
    import os
    from assgen.client.auto_server import get_or_start_server
    url = get_or_start_server()
    cfg = load_client_config()
    api_key = os.environ.get("ASSGEN_API_KEY") or cfg.get("api_key")
    return APIClient(
        url,
        timeout=float(cfg.get("default_timeout", DEFAULT_TIMEOUT)),
        api_key=api_key,
    )
