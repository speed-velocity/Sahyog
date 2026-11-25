import pytest
from conftest import validate_test_database_url
from sqlalchemy.engine import URL


def test_accepts_sahyog_test_psycopg_url() -> None:
    url = validate_test_database_url(
        "postgresql+psycopg://sahyog_migrator:placeholder@localhost:5432/sahyog_test"
    )

    assert isinstance(url, URL)
    assert url.drivername == "postgresql+psycopg"
    assert url.username == "sahyog_migrator"
    assert url.database == "sahyog_test"


def test_rejects_development_database_without_echoing_credentials() -> None:
    raw_url = (
        "postgresql+psycopg://sahyog_migrator:placeholder@localhost:5432/sahyog_dev"
    )

    with pytest.raises(ValueError, match="sahyog_test only"):
        validate_test_database_url(raw_url)


def test_rejects_other_database_names() -> None:
    with pytest.raises(ValueError, match="sahyog_test only"):
        validate_test_database_url(
            "postgresql+psycopg://sahyog_migrator:placeholder@localhost:5432/other"
        )


def test_rejects_wrong_database_user() -> None:
    with pytest.raises(ValueError, match="sahyog_migrator"):
        validate_test_database_url(
            "postgresql+psycopg://sahyog_app:placeholder@localhost:5432/sahyog_test"
        )


def test_rejects_non_postgresql_url() -> None:
    with pytest.raises(ValueError, match="PostgreSQL with Psycopg 3"):
        validate_test_database_url("sqlite:///sahyog_test.db")


def test_rejects_missing_url() -> None:
    with pytest.raises(ValueError, match="SAHYOG_TEST_DATABASE_URL is required"):
        validate_test_database_url(None)


@pytest.mark.parametrize(
    "raw_url",
    [
        "postgresql+psycopg://sahyog_migrator:synthetic-password-marker@localhost:5432/sahyog_dev",
        "postgresql+psycopg://sahyog_migrator:synthetic-password-marker@localhost:5432/other",
        "postgresql+psycopg://sahyog_app:synthetic-password-marker@localhost:5432/sahyog_test",
        "sqlite:///sahyog_test.db?password=synthetic-password-marker",
        "postgresql+psycopg://sahyog_migrator:synthetic-password-marker@localhost:5432/[invalid",
    ],
)
def test_validation_errors_do_not_echo_credentials(raw_url: str) -> None:
    secret_marker = "synthetic-password-marker"

    with pytest.raises(ValueError) as error:
        validate_test_database_url(raw_url)

    assert secret_marker not in str(error.value)
    assert raw_url not in str(error.value)
