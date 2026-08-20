"""说明本模块的职责、边界和主要协作对象。"""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ManualApproval:
    """说明 ManualApproval 的职责、状态边界和对外协作关系。"""
    approval_id: str
    workspace_id: str
    command_type: str
    payload: dict[str, object]
    status: str
    reviewer: str | None
    idempotency_key: str


class ManualApprovalGateway(Protocol):
    """说明 ManualApprovalGateway 的职责、状态边界和对外协作关系。"""
    async def create(
        self, *, workspace_id: str, command_type: str, payload: dict[str, object],
        idempotency_key: str,
    ) -> ManualApproval:
        """执行 create 的业务流程并返回该流程的结果。"""

    async def approve(self, *, approval_id: str, reviewer: str) -> ManualApproval | None:
        """执行 approve 的业务流程并返回该流程的结果。"""

    async def list_pending(
        self, *, workspace_id: str, limit: int
    ) -> list[ManualApproval]:
        """执行 list_pending 的业务流程并返回该流程的结果。"""


def validate_approval_request(
    *, command_type: str, payload: dict[str, object], idempotency_key: str
) -> None:
    """校验人工审批请求，不允许把凭据或密码带入审批/审计数据。"""
    normalized_command = command_type.strip()
    normalized_key = idempotency_key.strip()
    if not normalized_command or not payload or not normalized_key:
        raise ValueError("审批请求必须包含命令类型、变更内容和幂等键")
    if len(normalized_key) < 8 or len(normalized_key) > 120:
        raise ValueError("幂等键长度必须在 8 到 120 个字符之间")
    sensitive_keys = {"api_key", "access_token", "refresh_token", "password"}
    if any(str(key).lower() in sensitive_keys for key in payload):
        raise ValueError("审批请求不得包含凭据或密码")
