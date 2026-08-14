from typing import Any
from unittest.mock import AsyncMock

import pytest

from backend.app.infrastructure.postgres.model_providers import PostgresModelProviderGateway


class FakeConnection:
    def __init__(self) -> None:
        self.execute = AsyncMock()

    async def __aenter__(self) -> "FakeConnection":
        return self

    async def __aexit__(self, *_args: Any) -> None:
        return None

    def transaction(self) -> "FakeConnection":
        return self


class FakePool:
    def __init__(self) -> None:
        self.connection_obj = FakeConnection()

    def connection(self) -> FakeConnection:
        return self.connection_obj


@pytest.mark.asyncio
async def test_provider_gateway_never_selects_api_key() -> None:
    pool = FakePool()
    gateway = PostgresModelProviderGateway(pool)  # type: ignore[arg-type]
    await gateway.create_provider(
        provider_id="p1", organization_id="o1", name="DeepSeek",
        adapter_type="deepseek", model="chat", api_key="secret", priority=1,
    )
    statement = pool.connection_obj.execute.await_args.args[0]
    assert "INSERT INTO rag_model_providers" in statement
    assert "SELECT api_key" not in statement
