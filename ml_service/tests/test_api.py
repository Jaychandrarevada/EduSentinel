"""Integration tests for ML service FastAPI endpoints."""
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from main import app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Return value from predict_single (no student_id — the API adds it)
SAMPLE_PREDICTOR_RESULT = {
    "risk_score": 0.82,
    "risk_label": "HIGH",
    "contributing_factors": [
        {
            "feature": "attendance_pct",
            "label": "Attendance %",
            "impact": 0.35,
            "value": 52.0,
            "direction": "increases_risk",
        }
    ],
}

# Full StudentPrediction response (includes student_id added by API layer)
SAMPLE_PREDICTION = {"student_id": 1, **SAMPLE_PREDICTOR_RESULT}

SAMPLE_META = {
    "version": "v1",
    "model_name": "random_forest",
    "threshold": 0.42,
    "metrics": {"roc_auc": 0.91, "recall": 0.87, "precision": 0.78, "f1": 0.82, "accuracy": 0.85},
    "feature_cols": ["attendance_pct", "ia1_score"],
    "created_at": "2025-06-01T10:00:00+00:00",
}


def _make_client(pipeline=None, meta=None):
    """Build a TestClient with mocked app state."""
    client = TestClient(app, raise_server_exceptions=True)
    app.state.pipeline = pipeline or MagicMock()
    app.state.model_meta = meta or SAMPLE_META
    return client


# ---------------------------------------------------------------------------
# Health endpoints
# ---------------------------------------------------------------------------

class TestHealth:
    def test_liveness(self):
        client = _make_client()
        resp = client.get("/health/live")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_readiness_with_model(self):
        client = _make_client(pipeline=MagicMock(), meta=SAMPLE_META)
        resp = client.get("/health/ready")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ready"
        assert data["model_loaded"] is True

    def test_readiness_without_model(self):
        client = TestClient(app)
        app.state.pipeline = None
        app.state.model_meta = None
        resp = client.get("/health/ready")
        assert resp.status_code == 200
        assert resp.json()["status"] == "degraded"


# ---------------------------------------------------------------------------
# Predict / model-info
# ---------------------------------------------------------------------------

class TestModelInfo:
    def test_model_info_loaded(self):
        client = _make_client(pipeline=MagicMock(), meta=SAMPLE_META)
        resp = client.get("/predict/model-info")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "loaded"
        assert data["version"] == "v1"
        assert data["model_name"] == "random_forest"

    def test_model_info_no_model(self):
        client = TestClient(app)
        app.state.pipeline = None
        app.state.model_meta = None
        resp = client.get("/predict/model-info")
        assert resp.status_code == 200
        assert resp.json()["status"] == "no_model_loaded"


class TestSinglePredict:
    PAYLOAD = {
        "student_id": 1,
        "attendance_pct": 52.0,
        "ia1_score": 28.0,
        "ia2_score": 31.0,
        "ia3_score": 25.0,
        "assignment_avg_score": 40.0,
        "assignment_completion_rate": 0.55,
        "lms_login_frequency": 0.3,
        "lms_time_spent_hours": 1.5,
        "lms_content_views": 4.0,
        "previous_gpa": 3.8,
    }

    def test_single_predict_returns_200(self):
        client = _make_client(pipeline=MagicMock(), meta=SAMPLE_META)
        with patch("app.api.predict.predict_single", return_value=SAMPLE_PREDICTOR_RESULT):
            resp = client.post("/predict/single", json=self.PAYLOAD)
        assert resp.status_code == 200

    def test_single_predict_response_schema(self):
        client = _make_client(pipeline=MagicMock(), meta=SAMPLE_META)
        with patch("app.api.predict.predict_single", return_value=SAMPLE_PREDICTOR_RESULT):
            resp = client.post("/predict/single", json=self.PAYLOAD)
        data = resp.json()
        assert "student_id" in data
        assert "risk_score" in data
        assert "risk_label" in data
        assert "contributing_factors" in data

    def test_single_predict_503_without_model(self):
        client = TestClient(app)
        app.state.pipeline = None
        app.state.model_meta = None
        resp = client.post("/predict/single", json=self.PAYLOAD)
        assert resp.status_code == 503

    def test_single_predict_validation_error(self):
        client = _make_client(pipeline=MagicMock(), meta=SAMPLE_META)
        bad_payload = {**self.PAYLOAD, "attendance_pct": 150.0}  # > 100
        resp = client.post("/predict/single", json=bad_payload)
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Train endpoints
# ---------------------------------------------------------------------------

class TestTrainEndpoints:
    def test_trigger_training_returns_202(self):
        import app.api.train as train_module
        train_module._training_in_progress = False

        client = _make_client()
        with patch("app.api.train._run_and_reload"):
            resp = client.post("/train", json={"data_source": "synthetic"})
        assert resp.status_code == 202
        assert "started" in resp.json()["message"].lower()

    def test_trigger_training_conflicts_when_in_progress(self):
        import app.api.train as train_module
        train_module._training_in_progress = True

        client = _make_client()
        resp = client.post("/train", json={"data_source": "synthetic"})
        assert resp.status_code == 409
        # Reset for other tests
        train_module._training_in_progress = False

    def test_trigger_training_validates_csv_source(self):
        import app.api.train as train_module
        train_module._training_in_progress = False

        client = _make_client()
        # csv source without csv_path should return 422
        resp = client.post("/train", json={"data_source": "csv"})
        assert resp.status_code == 422

    def test_training_status_not_in_progress(self):
        import app.api.train as train_module
        train_module._training_in_progress = False

        client = _make_client()
        with patch.object(train_module.registry, "load_latest", return_value=(MagicMock(), SAMPLE_META)):
            resp = client.get("/train/status")
        assert resp.status_code == 200
        assert "no training in progress" in resp.json()["message"].lower()

    def test_training_status_in_progress(self):
        import app.api.train as train_module
        train_module._training_in_progress = True

        client = _make_client()
        resp = client.get("/train/status")
        assert resp.status_code == 200
        assert "in progress" in resp.json()["message"].lower()
        # Reset
        train_module._training_in_progress = False
