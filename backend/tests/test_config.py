import pytest
from pydantic import ValidationError

from backend.app.config import Settings


def test_test_mode_requires_postgresql_but_allows_redis_to_be_omitted() -> None:
    settings = Settings(
        app_env="test",
        database_url="postgresql://app:secret@postgres:5432/ozonslj",
        redis_url=None,
    )

    assert settings.database_url is not None
    assert settings.redis_url is None


def test_all_modes_reject_missing_postgresql() -> None:
    with pytest.raises(ValidationError, match="DATABASE_URL"):
        Settings(app_env="test", database_url=None, redis_url=None)


@pytest.mark.parametrize("missing_name", ["DATABASE_URL", "REDIS_URL"])
def test_production_requires_postgresql_and_redis(missing_name: str) -> None:
    values: dict[str, str] = {
        "app_env": "production",
        "database_url": "postgresql://app:secret@postgres:5432/ozonslj",
        "redis_url": "redis://redis:6379/0",
    }
    values.pop(missing_name.lower())

    with pytest.raises(ValidationError, match=missing_name):
        Settings(**values)


def test_production_accepts_explicit_cloud_dependencies() -> None:
    settings = Settings(
        app_env="production",
        database_url="postgresql://app:secret@postgres:5432/ozonslj",
        redis_url="redis://redis:6379/0",
    )

    assert settings.database_url is not None
    assert settings.redis_url is not None


def test_scheduler_role_does_not_require_model_credentials() -> None:
    settings = Settings(
        app_env="production",
        service_role="scheduler",
        database_url="postgresql://app:secret@postgres:5432/ozonslj",
        redis_url="redis://redis:6379/0",
    )

    assert settings.service_role == "scheduler"
