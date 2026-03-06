"""HuggingFace model manager.

Responsible for:
- Resolving which model to use for a given job type (catalog lookup)
- Downloading models from the Hub into the local cache
- Tracking installed models in the SQLite database
- Reporting model status (configured / downloading / installed)
"""
from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from assgen.catalog import get_model_for_job, load_catalog
from assgen.config import get_models_cache_dir
from assgen.db import upsert_model

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Device detection
# ---------------------------------------------------------------------------

def detect_device(preference: str = "auto") -> str:
    if preference != "auto":
        return preference
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda"
        if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
            return "mps"
    except ImportError:
        pass
    return "cpu"


# ---------------------------------------------------------------------------
# Model manager
# ---------------------------------------------------------------------------

class ModelManager:
    def __init__(
        self,
        conn: sqlite3.Connection,
        device: str = "auto",
        server_cfg: dict | None = None,
    ) -> None:
        self.conn = conn
        self.device = detect_device(device)
        self._cache_dir = get_models_cache_dir()
        self._server_cfg: dict = server_cfg or {}
        logger.info("ModelManager initialised", extra={"device": self.device})

    # ------------------------------------------------------------------
    # Download / install
    # ------------------------------------------------------------------

    def ensure_model(self, model_id: str) -> Path:
        """Download model if not already cached; return local path.

        Raises ``ValueError`` if the model_id is not on the server allow_list.
        """
        if model_id is None:
            raise ValueError("model_id is None — job type may not require a model")

        # Enforce allow-list before any I/O
        from assgen.server.validation import check_allow_list
        check_allow_list(model_id, self._server_cfg)

        cache_path = self._cache_dir / _safe_name(model_id)

        if cache_path.exists() and any(cache_path.iterdir()):
            logger.info("Model already cached", extra={"model_id": model_id})
            return cache_path

        logger.info(
            "Downloading model from HuggingFace Hub",
            extra={"model_id": model_id, "cache_dir": str(cache_path)},
        )
        try:
            from huggingface_hub import snapshot_download
            snapshot_download(
                repo_id=model_id,
                local_dir=str(cache_path),
                local_dir_use_symlinks=False,
                ignore_patterns=["*.msgpack", "*.h5", "flax_*"],
            )
        except Exception as exc:
            logger.error("Model download failed", extra={"model_id": model_id, "error": str(exc)})
            raise

        now = datetime.now(timezone.utc).isoformat()
        size = _dir_size(cache_path)
        upsert_model(
            self.conn,
            model_id=model_id,
            local_path=str(cache_path),
            installed_at=now,
            size_bytes=size,
        )
        logger.info(
            "Model downloaded successfully",
            extra={"model_id": model_id, "size_bytes": size},
        )
        return cache_path

    def ensure_for_job_type(self, job_type: str) -> tuple[str | None, Path | None]:
        """Resolve catalog entry for job_type and ensure the model is cached.

        Returns (model_id, local_path) — both None if no model is needed.
        """
        entry = get_model_for_job(job_type)
        if not entry:
            raise ValueError(f"No catalog entry for job type: {job_type!r}")
        model_id = entry.get("model_id")
        if not model_id:
            return None, None  # e.g., format-conversion tasks
        path = self.ensure_model(model_id)
        return model_id, path

    # ------------------------------------------------------------------
    # Status / listing
    # ------------------------------------------------------------------

    def list_status(self) -> list[dict[str, Any]]:
        """Return status of every model in the catalog."""
        catalog = load_catalog()
        seen: dict[str, dict[str, Any]] = {}
        for job_type, entry in catalog.items():
            mid = entry.get("model_id") or "(none)"
            if mid not in seen:
                row = self.conn.execute(
                    "SELECT * FROM models WHERE model_id = ?", (mid,)
                ).fetchone()
                installed = bool(row and row["local_path"] and Path(row["local_path"]).exists())
                seen[mid] = {
                    "model_id": mid,
                    "name": entry.get("name", mid),
                    "installed": installed,
                    "local_path": row["local_path"] if row else None,
                    "installed_at": row["installed_at"] if row else None,
                    "last_used_at": row["last_used_at"] if row else None,
                    "size_bytes": row["size_bytes"] if row else None,
                    "job_types": [],
                }
            seen[mid]["job_types"].append(job_type)
        return list(seen.values())

    def install_all(self) -> None:
        """Download every model referenced in the catalog."""
        for mid in set(
            e["model_id"]
            for e in load_catalog().values()
            if e.get("model_id")
        ):
            try:
                self.ensure_model(mid)
            except Exception as exc:
                logger.error("Failed to install model", extra={"model_id": mid, "error": str(exc)})


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _safe_name(model_id: str) -> str:
    """Convert 'org/repo' to 'org--repo' for use as a directory name."""
    return model_id.replace("/", "--")


def _dir_size(path: Path) -> int:
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
