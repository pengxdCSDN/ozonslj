from backend.app.application.identity import PasswordHasher


def test_password_hasher_round_trip_and_unique_salts() -> None:
    hasher = PasswordHasher()
    first = hasher.hash("a-strong-password")
    second = hasher.hash("a-strong-password")

    assert first != second
    assert hasher.verify("a-strong-password", first)
    assert not hasher.verify("wrong-password", first)


def test_password_hasher_rejects_malformed_hash() -> None:
    assert not PasswordHasher().verify("password", "not-a-password-hash")
