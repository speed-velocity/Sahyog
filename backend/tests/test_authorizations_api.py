from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from backend.app.api.authorizations import router
from backend.app.core.auth import require_active_principal
from backend.app.db.session import get_db
from backend.app.schemas.auth import AuthenticatedPrincipal, UserRole
from fastapi import FastAPI
from fastapi.testclient import TestClient


class FakeResults:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows


class FakeAuthorizationSession:
    def __init__(self, rows=()):
        self.rows = list(rows)
        self.statement = None

    def scalars(self, statement):
        self.statement = statement
        return FakeResults(self.rows)


@pytest.fixture
def authorization_client():
    caregiver_id = uuid4()
    subject_id = uuid4()
    granted_at = datetime(2026, 1, 1, tzinfo=UTC)
    active_grant = SimpleNamespace(
        subject_user_id=subject_id,
        granted_at=granted_at,
        revoked_at=None,
    )
    session = FakeAuthorizationSession([active_grant])
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[require_active_principal] = lambda: AuthenticatedPrincipal(
        user_id=caregiver_id,
        role=UserRole.CAREGIVER,
    )
    app.dependency_overrides[get_db] = lambda: session
    with TestClient(app) as client:
        yield client, caregiver_id, subject_id, session


def test_authorized_subjects_requires_bearer_authentication() -> None:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: FakeAuthorizationSession()
    with TestClient(app) as client:
        response = client.get("/api/v1/authorizations/me")
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_caregiver_receives_only_active_subject_grants(authorization_client) -> None:
    client, _caregiver_id, subject_id, session = authorization_client
    response = client.get(
        "/api/v1/authorizations/me",
        headers={"Authorization": "Bearer test-token"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "authorized_subjects": [
            {
                "subject_user_id": str(subject_id),
                "granted_at": "2026-01-01T00:00:00Z",
                "revoked_at": None,
            }
        ]
    }
    assert "caregiver_user_id" in str(session.statement)
    assert "revoked_at IS NULL" in str(session.statement)


def test_subject_role_is_forbidden_from_caregiver_discovery() -> None:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[require_active_principal] = lambda: AuthenticatedPrincipal(
        user_id=uuid4(),
        role=UserRole.SUBJECT,
    )
    app.dependency_overrides[get_db] = lambda: FakeAuthorizationSession()
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/authorizations/me",
            headers={"Authorization": "Bearer test-token"},
        )
    assert response.status_code == 403
    assert response.json()["detail"] == "Only caregivers may list authorized subjects"


def test_caregiver_without_active_grants_gets_empty_subject_list(
    authorization_client,
) -> None:
    client, _caregiver_id, _subject_id, session = authorization_client
    session.rows = []
    response = client.get(
        "/api/v1/authorizations/me",
        headers={"Authorization": "Bearer test-token"},
    )
    assert response.status_code == 200
    assert response.json() == {"authorized_subjects": []}
