from datetime import timedelta

import jwt
import pytest

from backend.config import settings
from backend.security import (
    ALGORITHM,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)

# --- contraseñas ------------------------------------------------------------


def test_hash_is_not_the_password_and_verifies() -> None:
    hashed = hash_password("una-contraseña-larga")

    assert hashed != "una-contraseña-larga"
    assert "una-contraseña-larga" not in hashed
    assert verify_password("una-contraseña-larga", hashed) is True


def test_wrong_password_does_not_verify() -> None:
    assert verify_password("otra", hash_password("una-contraseña-larga")) is False


def test_same_password_gives_different_hashes_because_of_salt() -> None:
    assert hash_password("misma") != hash_password("misma")


def test_verify_without_hash_is_false() -> None:
    # Camino de "usuario inexistente": nunca debe validar.
    assert verify_password("lo-que-sea", None) is False


# --- tokens -----------------------------------------------------------------


def test_token_roundtrip() -> None:
    assert decode_access_token(create_access_token(42)) == 42


def test_expired_token_is_rejected() -> None:
    token = create_access_token(1, expires_in=timedelta(seconds=-1))

    assert decode_access_token(token) is None


def test_token_signed_with_another_secret_is_rejected() -> None:
    forged = jwt.encode({"sub": "1", "exp": 9999999999}, "otro-secreto" * 4, ALGORITHM)

    assert decode_access_token(forged) is None


def test_token_with_alg_none_is_rejected() -> None:
    unsigned = jwt.encode({"sub": "1", "exp": 9999999999}, None, algorithm="none")

    assert decode_access_token(unsigned) is None


@pytest.mark.parametrize(
    "payload",
    [
        {"exp": 9999999999},  # sin sub
        {"sub": "1"},  # sin exp: no caduca nunca
        {"sub": "abc", "exp": 9999999999},  # sub no numérico
    ],
)
def test_token_with_missing_or_invalid_claims_is_rejected(payload: dict) -> None:
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=ALGORITHM)

    assert decode_access_token(token) is None


@pytest.mark.parametrize("garbage", ["", "abc", "a.b.c", "Bearer xyz"])
def test_garbage_is_rejected(garbage: str) -> None:
    assert decode_access_token(garbage) is None


def test_token_does_not_contain_role_or_permissions() -> None:
    token = create_access_token(1)

    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])

    assert set(payload) == {"sub", "iat", "exp"}
