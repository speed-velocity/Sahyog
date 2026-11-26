from backend.app.api.health import health


def test_health_endpoint() -> None:
    response = health()

    assert response.status == "ok"
    assert response.service == "sahyog-backend"
