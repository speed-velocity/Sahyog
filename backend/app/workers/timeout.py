"""Bounded verification-timeout worker orchestration."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from backend.app.core.clock import utc_now
from backend.app.schemas.incidents import NotificationResultStatus
from backend.app.services.incident_service import (
    IncidentServiceError,
    begin_timeout_escalation,
    complete_escalation,
    find_expired_pending_incidents,
)
from backend.app.services.notifier import EscalationNotifier, NotificationResult

SessionFactory = Callable[[], Session]
logger = logging.getLogger(__name__)


async def run_timeout_worker(
    session_factory: SessionFactory,
    notifier: EscalationNotifier,
    stop_event: asyncio.Event,
    *,
    interval_seconds: float = 1.0,
    batch_limit: int = 50,
) -> None:
    """Run bounded timeout batches until application shutdown."""

    interval = max(0.1, interval_seconds)
    limit = max(1, min(batch_limit, 100))
    while not stop_event.is_set():
        try:
            await process_expired_incidents(
                session_factory,
                notifier,
                limit=limit,
            )
        except Exception:
            logger.exception("timeout worker cycle failed")
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
        except TimeoutError:
            continue


async def process_expired_incidents(
    session_factory: SessionFactory,
    notifier: EscalationNotifier,
    *,
    now: datetime | None = None,
    limit: int = 100,
) -> int:
    """Process one bounded timeout batch; callers schedule subsequent cycles.

    Database intent is committed before the notifier is called. External I/O is
    therefore never performed while a database transaction or row lock is held.
    """

    current_time = now or utc_now()
    read_session = session_factory()
    try:
        incident_ids = find_expired_pending_incidents(
            read_session, now=current_time, limit=limit
        )
    finally:
        read_session.close()

    processed = 0
    for incident_id in incident_ids:
        attempt_id, idempotency_key = _start_attempt(
            session_factory, incident_id, current_time
        )
        if attempt_id is None or idempotency_key is None:
            continue

        try:
            result = await notifier.send_escalation_notification(
                incident_id=incident_id,
                escalation_attempt_id=attempt_id,
                trigger_reason="VERIFICATION_TIMEOUT",
                idempotency_key=idempotency_key,
                context={"incident_id": str(incident_id)},
            )
        except Exception as exc:  # noqa: BLE001 - worker must record provider failure
            result = NotificationResult(
                status=NotificationResultStatus.FAILED,
                provider_reference=None,
                failure_reason=str(exc)[:500],
                completed_at=utc_now(),
            )

        _complete_attempt(session_factory, incident_id, attempt_id, result)
        processed += 1
    return processed


def _start_attempt(
    session_factory: SessionFactory, incident_id: UUID, now: datetime
) -> tuple[UUID | None, str | None]:
    session = session_factory()
    try:
        with session.begin():
            key = f"verification-timeout:{incident_id}"
            try:
                attempt = begin_timeout_escalation(
                    session,
                    incident_id=incident_id,
                    idempotency_key=key,
                    now=now,
                )
            except IncidentServiceError:
                return None, None
            return attempt.escalation_attempt_id, attempt.idempotency_key
    finally:
        session.close()


def _complete_attempt(
    session_factory: SessionFactory,
    incident_id: UUID,
    attempt_id: UUID,
    result: NotificationResult,
) -> None:
    session = session_factory()
    try:
        with session.begin():
            complete_escalation(
                session,
                incident_id=incident_id,
                escalation_attempt_id=attempt_id,
                result=result.status,
                completed_at=result.completed_at,
            )
    finally:
        session.close()
