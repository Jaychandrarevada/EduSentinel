"""Unit tests for the ModelRegistry."""
import json
import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.registry.model_registry import ModelRegistry


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_registry(tmp_path):
    """A ModelRegistry backed by a temporary directory."""
    return ModelRegistry(artifact_dir=str(tmp_path))


def _fake_pipeline():
    return MagicMock(name="FakePipeline")


SAMPLE_METRICS = {
    "accuracy": 0.85,
    "precision": 0.80,
    "recall": 0.87,
    "f1": 0.83,
    "roc_auc": 0.92,
}

SAMPLE_FEATURE_COLS = ["attendance_pct", "ia1_score", "combined_risk_score"]


# ---------------------------------------------------------------------------
# Save and load
# ---------------------------------------------------------------------------

class TestSaveAndLoad:
    def test_save_creates_registry_json(self, tmp_registry):
        with patch("app.registry.model_registry.joblib.dump"):
            tmp_registry.save(
                pipeline=_fake_pipeline(),
                version="v1",
                model_name="random_forest",
                metrics=SAMPLE_METRICS,
                feature_cols=SAMPLE_FEATURE_COLS,
                threshold=0.45,
            )
        assert tmp_registry._registry_path.exists()

    def test_save_writes_version_to_models(self, tmp_registry):
        with patch("app.registry.model_registry.joblib.dump"):
            tmp_registry.save(
                pipeline=_fake_pipeline(),
                version="v1",
                model_name="random_forest",
                metrics=SAMPLE_METRICS,
                feature_cols=SAMPLE_FEATURE_COLS,
                threshold=0.45,
            )
        meta = tmp_registry.get_metadata("v1")
        assert meta is not None
        assert meta["model_name"] == "random_forest"

    def test_save_sets_production_pointer(self, tmp_registry):
        with patch("app.registry.model_registry.joblib.dump"):
            tmp_registry.save(
                pipeline=_fake_pipeline(),
                version="v1",
                model_name="random_forest",
                metrics=SAMPLE_METRICS,
                feature_cols=SAMPLE_FEATURE_COLS,
                threshold=0.45,
                promote=True,
            )
        assert tmp_registry.get_production_version() == "v1"

    def test_save_no_promote_keeps_old_production(self, tmp_registry):
        with patch("app.registry.model_registry.joblib.dump"):
            tmp_registry.save(
                pipeline=_fake_pipeline(),
                version="v1",
                model_name="random_forest",
                metrics=SAMPLE_METRICS,
                feature_cols=SAMPLE_FEATURE_COLS,
                threshold=0.45,
                promote=True,
            )
            tmp_registry.save(
                pipeline=_fake_pipeline(),
                version="v2",
                model_name="xgboost",
                metrics=SAMPLE_METRICS,
                feature_cols=SAMPLE_FEATURE_COLS,
                threshold=0.48,
                promote=False,
            )
        assert tmp_registry.get_production_version() == "v1"

    def test_load_latest_returns_none_when_empty(self, tmp_registry):
        result = tmp_registry.load_latest()
        assert result is None

    def test_load_latest_returns_tuple(self, tmp_registry):
        fake_pipe = _fake_pipeline()
        with patch("app.registry.model_registry.joblib.dump"), \
             patch("app.registry.model_registry.joblib.load", return_value=fake_pipe):
            tmp_registry.save(
                pipeline=fake_pipe,
                version="v1",
                model_name="random_forest",
                metrics=SAMPLE_METRICS,
                feature_cols=SAMPLE_FEATURE_COLS,
                threshold=0.45,
            )
            result = tmp_registry.load_latest()
        assert result is not None
        pipeline, metadata = result
        assert metadata["version"] == "v1"

    def test_load_specific_version(self, tmp_registry):
        fake_pipe = _fake_pipeline()
        with patch("app.registry.model_registry.joblib.dump"), \
             patch("app.registry.model_registry.joblib.load", return_value=fake_pipe):
            tmp_registry.save(
                pipeline=fake_pipe, version="v1", model_name="rf",
                metrics=SAMPLE_METRICS, feature_cols=SAMPLE_FEATURE_COLS, threshold=0.45,
            )
            result = tmp_registry.load("v1")
        assert result is not None
        _, meta = result
        assert meta["version"] == "v1"

    def test_load_unknown_version_raises(self, tmp_registry):
        with pytest.raises(FileNotFoundError):
            tmp_registry.load("v999")


# ---------------------------------------------------------------------------
# Promote and rollback
# ---------------------------------------------------------------------------

class TestPromoteAndRollback:
    @pytest.fixture
    def registry_with_two_versions(self, tmp_registry):
        with patch("app.registry.model_registry.joblib.dump"):
            tmp_registry.save(
                pipeline=_fake_pipeline(), version="v1", model_name="rf",
                metrics=SAMPLE_METRICS, feature_cols=SAMPLE_FEATURE_COLS,
                threshold=0.45, promote=True,
            )
            tmp_registry.save(
                pipeline=_fake_pipeline(), version="v2", model_name="xgb",
                metrics=SAMPLE_METRICS, feature_cols=SAMPLE_FEATURE_COLS,
                threshold=0.48, promote=False,
            )
        return tmp_registry

    def test_promote_changes_production_pointer(self, registry_with_two_versions):
        registry_with_two_versions.promote("v2")
        assert registry_with_two_versions.get_production_version() == "v2"

    def test_promote_unknown_version_raises(self, registry_with_two_versions):
        with pytest.raises(ValueError, match="not found"):
            registry_with_two_versions.promote("v99")

    def test_rollback_restores_previous_version(self, registry_with_two_versions):
        # Start: production=v1. Promote v2.
        registry_with_two_versions.promote("v2")
        # Rollback should restore to v1
        registry_with_two_versions.rollback()
        assert registry_with_two_versions.get_production_version() == "v1"

    def test_rollback_with_single_version_returns_none(self, tmp_registry):
        with patch("app.registry.model_registry.joblib.dump"):
            tmp_registry.save(
                pipeline=_fake_pipeline(), version="v1", model_name="rf",
                metrics=SAMPLE_METRICS, feature_cols=SAMPLE_FEATURE_COLS,
                threshold=0.45,
            )
        # Only one version — rollback has nothing to fall back to
        result = tmp_registry.rollback()
        assert result is None


# ---------------------------------------------------------------------------
# List versions
# ---------------------------------------------------------------------------

class TestListVersions:
    def test_list_empty(self, tmp_registry):
        assert tmp_registry.list_versions() == []

    def test_list_after_save(self, tmp_registry):
        with patch("app.registry.model_registry.joblib.dump"):
            tmp_registry.save(
                pipeline=_fake_pipeline(), version="v1", model_name="rf",
                metrics=SAMPLE_METRICS, feature_cols=SAMPLE_FEATURE_COLS, threshold=0.45,
            )
            tmp_registry.save(
                pipeline=_fake_pipeline(), version="v2", model_name="xgb",
                metrics=SAMPLE_METRICS, feature_cols=SAMPLE_FEATURE_COLS, threshold=0.48,
            )
        version_metas = tmp_registry.list_versions()
        version_ids = [m["version"] for m in version_metas]
        assert "v1" in version_ids
        assert "v2" in version_ids
