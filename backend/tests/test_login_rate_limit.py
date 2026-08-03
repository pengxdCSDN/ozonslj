from backend.app.infrastructure.login_rate_limit import RedisLoginRateLimiter


def test_login_rate_limit_key_does_not_contain_email_or_client_address() -> None:
    key = RedisLoginRateLimiter._key("Admin@Example.com", "192.0.2.10")

    assert key.startswith("auth:login:")
    assert "admin" not in key
    assert "example" not in key
    assert "192.0.2.10" not in key
    assert len(key.removeprefix("auth:login:")) == 64
