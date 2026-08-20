"""说明本模块的职责、边界和主要协作对象。"""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ReadonlyToolDecision:
    """说明 ReadonlyToolDecision 的职责、状态边界和对外协作关系。"""
    tool: str
    allowed: bool
    parameters: dict[str, str]
    reason: str
    sql_allowed: bool


class ReadonlyToolGateway(Protocol):
    """说明 ReadonlyToolGateway 的职责、状态边界和对外协作关系。"""
    async def save_decision(
        self, *, workspace_id: str, decision: ReadonlyToolDecision
    ) -> ReadonlyToolDecision:
        """执行 save_decision 的业务流程并返回该流程的结果。"""

    async def list_decisions(
        self, *, workspace_id: str, limit: int
    ) -> list[ReadonlyToolDecision]:
        """执行 list_decisions 的业务流程并返回该流程的结果。"""


ALLOWED_TOOLS = frozenset({
    "sales_summary", "stock_summary", "advertising_summary", "product_search"
})


def authorize_readonly_tool(tool: str, parameters: dict[str, object]) -> ReadonlyToolDecision:
    """执行 authorize_readonly_tool 的业务流程并返回该流程的结果。"""
    normalized = tool.strip().lower()
    if normalized not in ALLOWED_TOOLS:
        return ReadonlyToolDecision(normalized, False, {}, "工具不在只读白名单中", False)
    if any(key.lower() in {"sql", "query", "statement", "write"} for key in parameters):
        return ReadonlyToolDecision(normalized, False, {}, "只读工具不接受 SQL 或写入参数", False)
    workspace_id = parameters.get("workspace_id")
    if not isinstance(workspace_id, str) or not workspace_id.strip():
        return ReadonlyToolDecision(normalized, False, {}, "只读工具必须带有工作区上下文", False)
    safe_parameters = {
        key: str(value) for key, value in parameters.items()
        if key in {"workspace_id", "offer_id", "window"}
    }
    return ReadonlyToolDecision(
        normalized, True, safe_parameters, "仅允许调用参数化业务查询", False
    )
