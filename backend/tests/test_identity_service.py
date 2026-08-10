import asyncio
from dataclasses import dataclass, field
from datetime import datetime

from backend.app.application.identity import IdentityService, PasswordHasher
from backend.app.domain.identity import AuthenticatedUser


@dataclass(slots=True)
class FakeIdentityGateway:
    identity: tuple[AuthenticatedUser, str] | None
    sessions: list[tuple[str, str, str, datetime]] = field(default_factory=list)
    revoked: list[str] = field(default_factory=list)

    async def find_login_identity(
        self,
        email: str,
        organization_id: str,
    ) -> tuple[AuthenticatedUser, str] | None:
        if self.identity is None:
            return None
        user, password_hash = self.identity
        if user.email != email or user.organization_id != organization_id:
            return None
        return user, password_hash

    async def create_session(
        self,
        user_id: str,
        organization_id: str,
        token_hash: str,
        expires_at: datetime,
    ) -> None:
        self.sessions.append((user_id, organization_id, token_hash, expires_at))

    async def find_user_by_session_hash(self, token_hash: str) -> AuthenticatedUser | None:
        if self.sessions and self.sessions[-1][2] == token_hash and self.identity:
            return self.identity[0]
        return None

    async def revoke_session(self, token_hash: str) -> None:
        self.revoked.append(token_hash)


def test_login_stores_only_token_hash_and_authenticates() -> None:
    hasher = PasswordHasher()
    user = AuthenticatedUser(
        id="user-1",
        email="owner@example.com",
        display_name="Owner",
        organization_id="org-1",
        organization_role="owner",
    )
    gateway = FakeIdentityGateway((user, hasher.hash("long-test-password")))
    service = IdentityService(gateway, password_hasher=hasher)

    result = asyncio.run(service.login(user.email, "long-test-password", "org-1"))

    assert result is not None
    assert result.token not in gateway.sessions[0]
    assert len(gateway.sessions[0][2]) == 64
    assert asyncio.run(service.authenticate(result.token)) == user


def test_wrong_password_or_organization_does_not_create_session() -> None:
    hasher = PasswordHasher()
    user = AuthenticatedUser(
        id="user-1",
        email="owner@example.com",
        display_name="Owner",
        organization_id="org-1",
        organization_role="owner",
    )
    gateway = FakeIdentityGateway((user, hasher.hash("long-test-password")))
    service = IdentityService(gateway, password_hasher=hasher)

    assert asyncio.run(service.login(user.email, "wrong-password", "org-1")) is None
    assert asyncio.run(service.login(user.email, "long-test-password", "org-2")) is None
    assert gateway.sessions == []
