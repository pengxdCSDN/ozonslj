from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ReadonlyToolDecision:
    tool: str
    allowed: bool
    parameters: dict[str, str]
    reason: str
    sql_allowed: bool


class ReadonlyToolGateway(Protocol):
    async def save_decision(
        self, *, workspace_id: str, decision: ReadonlyToolDecision
    ) -> ReadonlyToolDecision: ...

    async def list_decisions(
        self, *, workspace_id: str, limit: int
    ) -> list[ReadonlyToolDecision]: ...


ALLOWED_TOOLS = frozenset({
    "sales_summary", "stock_summary", "advertising_summary", "product_search"
})


def authorize_readonly_tool(tool: str, parameters: dict[str, object]) -> ReadonlyToolDecision:
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
