"""Agent 编排端口；为 LangChain/LangGraph 提供可选适配边界。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class AgentToolSpec:
    """受控工具声明；工具只能是参数化只读或进入审核的业务动作。"""

    name: str
    description: str
    input_schema: dict[str, str]
    read_only: bool = True


@dataclass(frozen=True, slots=True)
class AgentState:
    """跨节点传递的最小状态；不保存凭据、任意 SQL 或原始用户隐私。"""

    request_id: str
    user_id: str
    question: str
    intent: str | None = None
    messages: tuple[str, ...] = ()
    tool_results: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    metadata: tuple[tuple[str, str], ...] = ()


class AgentNode(Protocol):
    async def __call__(self, state: AgentState) -> AgentState: ...


class AgentGraphPort(Protocol):
    """可由 LangGraph StateGraph 适配实现的编排端口。"""

    async def invoke(self, state: AgentState) -> AgentState: ...


class SequentialAgentGraph:
    """确定性编排替身；生产环境可由 LangGraph 适配器替换。"""

    def __init__(self, nodes: tuple[AgentNode, ...] = ()) -> None:
        self._nodes = nodes

    async def invoke(self, state: AgentState) -> AgentState:
        current = state
        for node in self._nodes:
            current = await node(current)
        return current


def langchain_tool_specs(specs: tuple[AgentToolSpec, ...]) -> tuple[AgentToolSpec, ...]:
    """返回可转换为 LangChain StructuredTool 的声明，不在领域层导入 LangChain。"""

    if any(not spec.name.strip() or not spec.description.strip() for spec in specs):
        raise ValueError("Agent 工具名称和描述不能为空")
    if any(not spec.read_only for spec in specs):
        raise ValueError("外部写工具必须经过独立审核执行链，不能直接注册为 Agent 工具")
    return specs
