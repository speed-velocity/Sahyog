from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from backend.app.models.demo import DemoRun
from backend.app.schemas.demo import Scenario
from backend.app.services.demo import create_demo_run


def test_demo_start_key_rejects_a_different_scenario() -> None:
    session = MagicMock()
    session.scalar.return_value = DemoRun(
        demo_run_id=uuid4(),
        subject_user_id=uuid4(),
        scenario=Scenario.NORMAL.value,
        status="RUNNING",
        current_generation=1,
        start_idempotency_key="same-key",
    )

    with pytest.raises(ValueError, match="different scenario"):
        create_demo_run(
            session,
            subject_user_id=uuid4(),
            scenario=Scenario.TRUE_ANOMALY,
            start_idempotency_key="same-key",
        )


def test_demo_start_key_replays_the_same_scenario() -> None:
    session = MagicMock()
    existing = DemoRun(
        demo_run_id=uuid4(),
        subject_user_id=uuid4(),
        scenario=Scenario.NORMAL.value,
        status="RUNNING",
        current_generation=1,
        start_idempotency_key="same-key",
    )
    session.scalar.return_value = existing

    result = create_demo_run(
        session,
        subject_user_id=existing.subject_user_id,
        scenario=Scenario.NORMAL,
        start_idempotency_key="same-key",
    )

    assert result is existing
    session.add.assert_not_called()
