import tomllib
from pathlib import Path


def test_backend_project_metadata_and_dependency_groups() -> None:
    project_file = Path(__file__).parents[1] / "pyproject.toml"
    config = tomllib.loads(project_file.read_text(encoding="utf-8"))

    project = config["project"]
    assert project["name"] == "sahyog-backend"
    assert project["version"] == "0.1.0"
    assert project["requires-python"] == ">=3.12,<3.13"

    runtime_dependencies = set(project["dependencies"])
    assert any(dep.startswith("SQLAlchemy>=") for dep in runtime_dependencies)
    assert any(dep.startswith("psycopg[binary]>=") for dep in runtime_dependencies)
    assert not any(dep.startswith("psycopg2") for dep in runtime_dependencies)

    groups = config["dependency-groups"]
    assert any(dep.startswith("alembic>=") for dep in groups["migrations"])
    assert any(dep.startswith("pytest>=") for dep in groups["dev"])
    assert any(dep.startswith("ruff>=") for dep in groups["dev"])

    assert config["tool"]["uv"]["package"] is False
