"""Integration tests for POST /api/v1/predictions/predict-risk."""
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient


VALID_PAYLOAD = {
    "attendance": 75.0,
    "internal_score": 68.0,
    "assignment_score": 70.0,
    "lms_activity": 40.0,
    "engagement_time": 12.0,
    "previous_gpa": 6.5,
}

ML_SERVICE_RESPONSE = {
    "student_id": 0,
    "risk_score": 0.82,
    "risk_label": "HIGH",
    "contributing_factors": [
        {"feature": "attendance_pct", "label": "Attendance", "impact": 0.3, "value": 75.0, "direction": "increases_risk"}
    ],
}


# ---------------------------------------------------------------------------
# Auth guard
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_predict_risk_requires_auth(client: AsyncClient):
    resp = await client.post("/api/v1/predictions/predict-risk", json=VALID_PAYLOAD)
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_predict_risk_high(client: AsyncClient, auth_headers: dict):
    with patch(
        "app.services.prediction_service.httpx.AsyncClient",
        return_value=_mock_ml_client(ML_SERVICE_RESPONSE),
    ):
        resp = await client.post(
            "/api/v1/predictions/predict-risk",
            json=VALID_PAYLOAD,
            headers=auth_headers,
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["risk_level"] == "High"
    assert data["probability"] == 0.82
    assert data["recommendation"] == "Faculty intervention recommended"


@pytest.mark.asyncio
async def test_predict_risk_medium(client: AsyncClient, auth_headers: dict):
    ml_resp = {**ML_SERVICE_RESPONSE, "risk_score": 0.45, "risk_label": "MEDIUM"}
    with patch(
        "app.services.prediction_service.httpx.AsyncClient",
        return_value=_mock_ml_client(ml_resp),
    ):
        resp = await client.post(
            "/api/v1/predictions/predict-risk",
            json=VALID_PAYLOAD,
            headers=auth_headers,
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["risk_level"] == "Medium"
    assert data["recommendation"] == "Monitor student progress closely"


@pytest.mark.asyncio
async def test_predict_risk_low(client: AsyncClient, auth_headers: dict):
    ml_resp = {**ML_SERVICE_RESPONSE, "risk_score": 0.12, "risk_label": "LOW"}
    with patch(
        "app.services.prediction_service.httpx.AsyncClient",
        return_value=_mock_ml_client(ml_resp),
    ):
        resp = await client.post(
            "/api/v1/predictions/predict-risk",
            json=VALID_PAYLOAD,
            headers=auth_headers,
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["risk_level"] == "Low"
    assert data["recommendation"] == "Student is performing well"


@pytest.mark.asyncio
async def test_predict_risk_response_schema(client: AsyncClient, auth_headers: dict):
    with patch(
        "app.services.prediction_service.httpx.AsyncClient",
        return_value=_mock_ml_client(ML_SERVICE_RESPONSE),
    ):
        resp = await client.post(
            "/api/v1/predictions/predict-risk",
            json=VALID_PAYLOAD,
            headers=auth_headers,
        )
    data = resp.json()
    assert "risk_level" in data
    assert "probability" in data
    assert "recommendation" in data
    assert isinstance(data["probability"], float)
    assert 0.0 <= data["probability"] <= 1.0


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_predict_risk_attendance_out_of_range(client: AsyncClient, auth_headers: dict):
    bad = {**VALID_PAYLOAD, "attendance": 110.0}
    resp = await client.post(
        "/api/v1/predictions/predict-risk", json=bad, headers=auth_headers
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_predict_risk_negative_gpa(client: AsyncClient, auth_headers: dict):
    bad = {**VALID_PAYLOAD, "previous_gpa": -1.0}
    resp = await client.post(
        "/api/v1/predictions/predict-risk", json=bad, headers=auth_headers
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_predict_risk_missing_field(client: AsyncClient, auth_headers: dict):
    incomplete = {k: v for k, v in VALID_PAYLOAD.items() if k != "internal_score"}
    resp = await client.post(
        "/api/v1/predictions/predict-risk", json=incomplete, headers=auth_headers
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# ML service unavailable
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_predict_risk_ml_service_down(client: AsyncClient, auth_headers: dict):
    import httpx
    with patch(
        "app.services.prediction_service.httpx.AsyncClient",
        return_value=_mock_ml_client_error(httpx.ConnectError("refused")),
    ):
        resp = await client.post(
            "/api/v1/predictions/predict-risk",
            json=VALID_PAYLOAD,
            headers=auth_headers,
        )
    assert resp.status_code == 503


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_ml_client(response_data: dict):
    """Return an async context manager that yields a mock httpx response."""
    mock_response = AsyncMock()
    mock_response.json.return_value = response_data
    mock_response.raise_for_status = AsyncMock()

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.post.return_value = mock_response
    return mock_client


def _mock_ml_client_error(exc: Exception):
    """Return an async context manager whose post() raises the given exception."""
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.post.side_effect = exc
    return mock_client
