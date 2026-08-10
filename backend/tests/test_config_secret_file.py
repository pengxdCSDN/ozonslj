from pathlib import Path

from backend.app.config import Settings


def test_settings_builds_database_url_from_compose_secret(tmp_path: Path) -> None:
    password_file = tmp_path / "postgres_password"
    password_file.write_text("secret@value\n", encoding="utf-8")

    settings = Settings(
        app_env="production",
        postgres_host="postgres",
        postgres_password_file=password_file,
        redis_url="redis://redis:6379/0",
    )

    assert str(settings.database_url) == (
        "postgresql://ozonslj:secret%40value@postgres:5432/ozonslj"
    )
