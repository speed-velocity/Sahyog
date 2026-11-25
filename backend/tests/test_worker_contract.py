import inspect

from backend.app.workers.timeout import process_expired_incidents


def test_timeout_worker_is_async_and_bounded_by_limit() -> None:
    assert inspect.iscoroutinefunction(process_expired_incidents)
    assert "limit" in inspect.signature(process_expired_incidents).parameters
