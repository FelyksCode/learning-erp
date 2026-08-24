import jwt
import pytest
from sqlalchemy import select

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.models import User, UserRole

pytestmark = pytest.mark.unit


def test_password_survives_hash_and_verify_roundtrip():
    stored = hash_password("s3cret!")

    assert stored != "s3cret!"
    assert verify_password("s3cret!", stored) is True
    assert verify_password("wrong", stored) is False


def test_same_password_hashes_differently_each_time():
    assert hash_password("same") != hash_password("same")


def test_token_carries_user_identity():
    user = User(id=42, username="amy", role=UserRole.STAFF)

    claims = decode_access_token(create_access_token(user))

    assert claims["sub"] == "42"
    assert claims["username"] == "amy"
    assert claims["role"] == "staff"


def test_tampered_token_is_rejected():
    user = User(id=1, username="amy", role=UserRole.ADMIN)
    token = create_access_token(user) + "tampered"

    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(token)


def test_passwords_never_stored_in_plain_text(db_session):
    db_session.add(User(username="plaincheck", password_hash=hash_password("hunter22")))
    db_session.commit()

    row = db_session.scalar(select(User.password_hash).where(User.username == "plaincheck"))

    assert "hunter22" not in row
