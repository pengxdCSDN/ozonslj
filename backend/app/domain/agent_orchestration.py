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
    """说明 AgentNode 的职责、状态边界和对外协作关系。"""
    async def __call__(self, state: AgentState) -> AgentState:
        """实现特殊方法 __call__，遵循该类型的 Python 运行时约定。

Args:
    state: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""


class AgentGraphPort(Protocol):
    """可由 LangGraph StateGraph 适配实现的编排端口。"""

    async def invoke(self, state: AgentState) -> AgentState:
        """执行 invoke 的业务流程并返回该流程的结果。

Args:
    state: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""


class SequentialAgentGraph:
    """确定性编排替身；生产环境可由 LangGraph 适配器替换。"""

    def __init__(self, nodes: tuple[AgentNode, ...] = ()) -> None:
        """初始化对象依赖和运行时状态。

Args:
    nodes: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        self._nodes = nodes

    async def invoke(self, state: AgentState) -> AgentState:
        """执行 invoke 的业务流程并返回该流程的结果。

Args:
    state: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
        current = state
        for node in self._nodes:
            current = await node(current)
        return current


def langchain_tool_specs(specs: tuple[AgentToolSpec, ...]) -> tuple[AgentToolSpec, ...]:
    """返回可转换为 LangChain StructuredTool 的声明，不在领域层导入 LangChain。

Args:
    specs: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    ValueError: 业务约束或外部依赖失败时抛出。
"""

    if any(not spec.name.strip() or not spec.description.strip() for spec in specs):
        raise ValueError("Agent 工具名称和描述不能为空")
    if any(not spec.read_only for spec in specs):
        raise ValueError("外部写工具必须经过独立审核执行链，不能直接注册为 Agent 工具")
    return specs
