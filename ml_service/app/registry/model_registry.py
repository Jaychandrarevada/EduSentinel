"""
Model registry -- versioned save/load of sklearn pipelines.

Local filesystem (dev): artifacts are stored as .pkl + registry.json
S3/MinIO (production):  upload artifacts after local save.

registry.json schema:
  {
    "production": "v20250101_120000",
    "models": [
      {
        "version":     "v20250101_120000",
        "model_name":  "xgboost",
        "path":        "/app/artifacts/model_v20250101_120000.pkl",
        "threshold":   0.43,
        "metrics":     {...},
        "feature_cols": [...],
        "created_at":  "2025-01-01T12:00:00Z"
      }
    ]
  }
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import joblib
import structlog

log = structlog.get_logger()

_REGISTRY_FILENAME = "registry.json"


class ModelRegistry:
    def __init__(self, artifact_dir: str = "./artifacts"):
        self._dir = Path(artifact_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._registry_path = self._dir / _REGISTRY_FILENAME
        self._registry: dict = self._load_registry()

    # ── Persistence ───────────────────────────────────────────────────────

    def _load_registry(self) -> dict:
        if self._registry_path.exists():
            return json.loads(self._registry_path.read_text())
        return {"production": None, "models": []}

    def _write_registry(self) -> None:
        self._registry_path.write_text(json.dumps(self._registry, indent=2, default=str))

    # ── Save ──────────────────────────────────────────────────────────────

    def save(
        self,
        pipeline,
        version: str,
        model_name: str,
        metrics: dict,
        feature_cols: list[str],
        threshold: float = 0.5,
        promote: bool = True,
    ) -> str:
        """
        Persist a fitted pipeline to disk and register it.

        Args:
            pipeline:     Fitted sklearn/imblearn Pipeline
            version:      Unique version string (e.g. "v20250101_120000")
            model_name:   Algorithm name (e.g. "xgboost")
            metrics:      Dict of evaluation metrics
            feature_cols: Ordered list of feature names used by the model
            threshold:    Optimal decision threshold from validation
            promote:      Set this version as the production model

        Returns:
            Artifact file path
        """
        pkl_path = self._dir / f"model_{version}.pkl"
        joblib.dump(pipeline, pkl_path, compress=3)

        entry = {
            "version":      version,
            "model_name":   model_name,
            "path":         str(pkl_path),
            "threshold":    threshold,
            "metrics":      metrics,
            "feature_cols": feature_cols,
            "created_at":   datetime.now(timezone.utc).isoformat(),
        }

        # Remove previous entry for this version if exists
        self._registry["models"] = [
            m for m in self._registry["models"] if m["version"] != version
        ]
        self._registry["models"].append(entry)

        if promote:
            self._registry["production"] = version

        self._write_registry()
        log.info(
            "registry.saved",
            version=version, model=model_name,
            path=str(pkl_path), promoted=promote,
            roc_auc=metrics.get("roc_auc"),
        )
        return str(pkl_path)

    # ── Load ──────────────────────────────────────────────────────────────

    def load_latest(self) -> Optional[tuple[object, dict]]:
        """
        Load the current production model.
        Returns (pipeline, metadata) or None if no model is registered.
        """
        version = self._registry.get("production")
        if not version:
            log.warning("registry.no_production_model")
            return None
        return self.load(version)

    def load(self, version: str) -> tuple[object, dict]:
        """Load a specific model version. Returns (pipeline, metadata)."""
        entry = next(
            (m for m in self._registry["models"] if m["version"] == version),
            None,
        )
        if not entry:
            raise FileNotFoundError(f"Model version '{version}' not found in registry")

        pkl_path = Path(entry["path"])
        if not pkl_path.exists():
            raise FileNotFoundError(f"Model artifact not found: {pkl_path}")

        pipeline = joblib.load(pkl_path)
        log.info("registry.loaded", version=version, model=entry["model_name"])
        return pipeline, entry

    # ── Query ─────────────────────────────────────────────────────────────

    def list_versions(self) -> list[dict]:
        """Return all registered model versions (metadata only, no pipeline)."""
        return sorted(
            self._registry["models"],
            key=lambda m: m["created_at"],
            reverse=True,
        )

    def get_production_version(self) -> Optional[str]:
        return self._registry.get("production")

    def get_metadata(self, version: str) -> Optional[dict]:
        return next(
            (m for m in self._registry["models"] if m["version"] == version),
            None,
        )

    def promote(self, version: str) -> None:
        """Promote a registered version to production."""
        if not self.get_metadata(version):
            raise ValueError(f"Version '{version}' not found")
        self._registry["production"] = version
        self._write_registry()
        log.info("registry.promoted", version=version)

    def rollback(self) -> Optional[str]:
        """Promote the second-newest version (undo last promotion)."""
        versions = self.list_versions()
        if len(versions) < 2:
            log.warning("registry.rollback.no_previous_version")
            return None
        prev_version = versions[1]["version"]
        self.promote(prev_version)
        log.info("registry.rollback.complete", version=prev_version)
        return prev_version

    def delete(self, version: str, delete_file: bool = False) -> None:
        """Remove a version from registry. Optionally delete the .pkl file."""
        if self._registry.get("production") == version:
            raise ValueError("Cannot delete the production version. Promote another first.")
        entry = self.get_metadata(version)
        if not entry:
            raise ValueError(f"Version '{version}' not found")
        if delete_file:
            Path(entry["path"]).unlink(missing_ok=True)
        self._registry["models"] = [
            m for m in self._registry["models"] if m["version"] != version
        ]
        self._write_registry()
        log.info("registry.deleted", version=version)
