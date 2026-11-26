from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from backend.app.models.auth import AuthIdentity
from backend.app.schemas.auth import UserRole
from backend.app.services.authorization import (
    AuthorizationServiceError,
    grant_caregiver_access,
)


def test_subject_cannot_authorize_themselves() -> None:
    user_id = uuid4()

    with pytest.raises(AuthorizationServiceError, match="cannot authorize"):
        grant_caregiver_access(
            MagicMock(), subject_user_id=user_id, caregiver_user_id=user_id
        )


def test_only_active_caregiver_can_be_granted_access() -> None:
    session = MagicMock()
    caregiver_id = uuid4()
    session.get.return_value = AuthIdentity(
        user_id=caregiver_id,
        login_identifier="caregiver",
        password_hash="hash",
        role=UserRole.CAREGIVER.value,
        disabled=False,
        created_at=None,
        updated_at=None,
    )
    session.scalar.return_value = None

    authorization = grant_caregiver_access(
        session,
        subject_user_id=uuid4(),
        caregiver_user_id=caregiver_id,
    )

    assert authorization.caregiver_user_id == caregiver_id
    session.add.assert_called_once()
