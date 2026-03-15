"""Unit tests for JWT and password hashing utilities."""
import pytest
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    create_refresh_token,
    decode_refresh_token,
)


def test_password_hash_is_not_plaintext():
    plain = "SecurePass1"
    hashed = hash_password(plain)
    assert hashed != plain
    assert len(hashed) > 20


def test_password_verify_correct():
    plain = "SecurePass1"
    assert verify_password(plain, hash_password(plain)) is True


def test_password_verify_wrong():
    assert verify_password("wrong", hash_password("SecurePass1")) is False


def test_access_token_round_trip():
    token = create_access_token(subject=42, extra_claims={"role": "ADMIN"})
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "42"
    assert payload["role"] == "ADMIN"
    assert payload["type"] == "access"


def test_access_token_invalid_returns_none():
    assert decode_access_token("not.a.valid.token") is None


def test_refresh_token_round_trip():
    token = create_refresh_token(subject=7)
    payload = decode_refresh_token(token)
    assert payload is not None
    assert payload["sub"] == "7"
    assert payload["type"] == "refresh"


def test_access_token_rejected_as_refresh():
    token = create_access_token(subject=1)
    assert decode_refresh_token(token) is None


def test_refresh_token_rejected_as_access():
    token = create_refresh_token(subject=1)
    assert decode_access_token(token) is None
