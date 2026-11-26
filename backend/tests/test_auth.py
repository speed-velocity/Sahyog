from uuid import uuid4

from backend.app.api.auth import register
from backend.app.core import auth
from backend.app.core.config import get_settings
from backend.app.schemas.auth import RegisterRequest, UserRole


class _RegistrationSession:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def scalar(self, _statement):
        return None

    def add(self, value) -> None:
        self.calls.append(type(value).__name__)

    def flush(self) -> None:
        self.calls.append("flush")

    def commit(self) -> None:
        self.calls.append("commit")


def test_password_hash_round_trip() -> None:
    password = "a-strong-demo-password"
    hashed = auth.hash_password(password)

    assert hashed != password
    assert auth.verify_password(password, hashed)
    assert not auth.verify_password("wrong-password", hashed)


def test_jwt_contains_backend_subject_and_role(monkeypatch) -> None:
    monkeypatch.setenv("SAHYOG_AUTH_SECRET_KEY", "x" * 64)
    get_settings.cache_clear()
    user_id = uuid4()

    token = auth.create_access_token(user_id=user_id, role=UserRole.CAREGIVER)
    principal = auth.get_current_principal(token=token)

    assert principal.user_id == user_id
    assert principal.role is UserRole.CAREGIVER
    get_settings.cache_clear()


def test_registration_flushes_user_before_identity() -> None:
    session = _RegistrationSession()
    response = register(
        RegisterRequest(
            login_identifier="subject@example.test",
            password="a-strong-demo-password",
            role=UserRole.SUBJECT,
        ),
        session,
    )

    assert response.role is UserRole.SUBJECT
    assert session.calls == ["User", "flush", "AuthIdentity", "commit"]
