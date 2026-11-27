"""Transactional demo-run creation and reset."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.demo import DemoRun
from backend.app.schemas.demo import Scenario


def create_demo_run(
    session: Session,
    *,
    subject_user_id: UUID,
    scenario: Scenario,
    start_idempotency_key: str,
) -> DemoRun:
    existing = session.scalar(
        select(DemoRun).where(
            DemoRun.subject_user_id == subject_user_id,
            DemoRun.start_idempotency_key == start_idempotency_key,
        )
    )
    if existing is not None:
        if existing.scenario != scenario.value:
            raise ValueError(
                "start_idempotency_key was already used with a different scenario"
            )
        return existing
    now = datetime.now(UTC)
    run = DemoRun(
        demo_run_id=uuid4(),
        subject_user_id=subject_user_id,
        scenario=scenario.value,
        status="RUNNING",
        outcome=None,
        current_generation=1,
        start_idempotency_key=start_idempotency_key,
        started_at=now,
    )
    session.add(run)
    return run


def reset_demo_run(
    session: Session, *, demo_run_id: UUID, subject_user_id: UUID
) -> DemoRun:
    run = session.scalar(
        select(DemoRun)
        .where(
            DemoRun.demo_run_id == demo_run_id,
            DemoRun.subject_user_id == subject_user_id,
        )
        .with_for_update()
    )
    if run is None:
        raise ValueError("demo run was not found")
    run.current_generation += 1
    run.status = "RESET"
    run.reset_at = datetime.now(UTC)
    return run
