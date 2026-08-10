from dataclasses import dataclass
from typing import Literal, Protocol

PublishStatus = Literal["pending", "approved", "executed", "partial", "rejected"]


@dataclass(frozen=True, slots=True)
class PublishCommand:
    idempotency_key: str
    version: int
    status: PublishStatus
    requested_text: str
    readback_text: str | None
    matched: bool
    message: str


class ListingPublishGateway(Protocol):
    async def save_command(
        self, *, workspace_id: str, product_scope: str, command: PublishCommand
    ) -> PublishCommand: ...

    async def list_commands(
        self, *, workspace_id: str, product_scope: str, limit: int
    ) -> list[PublishCommand]: ...


def execute_controlled_publish(
    *,
    idempotency_key: str,
    version: int,
    status: PublishStatus,
    requested_text: str,
    readback_text: str | None = None,
) -> PublishCommand:
    if not idempotency_key.strip():
        raise ValueError("发布命令必须包含幂等键")
    if version < 1:
        raise ValueError("发布版本号必须从 1 开始")
    if not requested_text.strip():
        raise ValueError("发布内容不能为空")
    if status != "approved":
        return PublishCommand(
            idempotency_key, version, "rejected", requested_text, None, False,
            "版本尚未审核通过",
        )
    if readback_text is None:
        return PublishCommand(
            idempotency_key, version, "executed", requested_text, None, False,
            "已提交 Stub 写入，等待回读",
        )
    matched = readback_text == requested_text
    return PublishCommand(
        idempotency_key, version, "executed" if matched else "partial",
        requested_text, readback_text, matched,
        "回读与请求一致" if matched else "回读内容不一致，需要人工复核",
    )
