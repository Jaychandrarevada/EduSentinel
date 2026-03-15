"""Integration tests for /students endpoints."""
import pytest
from httpx import AsyncClient

STUDENT_PAYLOAD = {
    "roll_no": "CS2021001",
    "full_name": "Alice Johnson",
    "email": "alice@test.edu",
    "department": "Computer Science",
    "semester": 5,
    "batch_year": 2021,
}


@pytest.mark.asyncio
async def test_create_student(client: AsyncClient, auth_headers: dict):
    resp = await client.post("/api/v1/students", json=STUDENT_PAYLOAD, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["roll_no"] == "CS2021001"
    assert data["id"] is not None


@pytest.mark.asyncio
async def test_create_duplicate_student(client: AsyncClient, auth_headers: dict):
    await client.post("/api/v1/students", json=STUDENT_PAYLOAD, headers=auth_headers)
    resp = await client.post("/api/v1/students", json=STUDENT_PAYLOAD, headers=auth_headers)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_get_student(client: AsyncClient, auth_headers: dict):
    create = await client.post("/api/v1/students", json={
        **STUDENT_PAYLOAD,
        "roll_no": "CS2021002",
        "email": "bob@test.edu",
    }, headers=auth_headers)
    student_id = create.json()["id"]

    resp = await client.get(f"/api/v1/students/{student_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == student_id


@pytest.mark.asyncio
async def test_get_nonexistent_student(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/students/99999", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_students_paginated(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/students?page=1&size=10", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert "pages" in data


@pytest.mark.asyncio
async def test_update_student(client: AsyncClient, auth_headers: dict):
    create = await client.post("/api/v1/students", json={
        **STUDENT_PAYLOAD,
        "roll_no": "CS2021003",
        "email": "carol@test.edu",
    }, headers=auth_headers)
    sid = create.json()["id"]

    resp = await client.put(
        f"/api/v1/students/{sid}",
        json={"full_name": "Carol Updated"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["full_name"] == "Carol Updated"
