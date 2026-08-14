"""LangChain/LangGraph 可选适配边界。

核心领域层不依赖第三方编排框架；部署环境安装对应包后，可通过本模块把领域
AgentGraphPort 接到 Runnable 或 StateGraph。未安装依赖时导入本模块仍然安全，
便于测试、迁移和小规格服务器上的降级运行。
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

from backend.app.domain.agent_orchestration import AgentGraphPort, AgentState


class LangChainRunnable(Protocol):
    async def ainvoke(self, input: dict[str, Any]) -> dict[str, Any]: ...


class LangChainGraphAdapter:
    """把 LangChain Runnable 适配为项目内部的图执行端口。"""

    def __init__(self, runnable: LangChainRunnable) -> None:
        self._runnable = runnable

    async def run(self, state: AgentState) -> AgentState:
        result = await self._runnable.ainvoke(
            {"messages": list(state.messages), "intent": state.intent, "question": state.question}
        )
        messages = tuple(str(item) for item in result.get("messages", state.messages))
        intent = result.get("intent", state.intent)
        return AgentState(
            request_id=state.request_id,
            user_id=state.user_id,
            question=state.question,
            intent=str(intent) if intent is not None else None,
            messages=messages,
            tool_results=state.tool_results,
            errors=state.errors,
            metadata=state.metadata,
        )


def build_langgraph_adapter(
    factory: Callable[[dict[str, Any]], LangChainRunnable],
) -> AgentGraphPort:
    """以工厂形式接入 LangGraph，避免在领域代码中硬编码 StateGraph。"""

    class FactoryAdapter:
        async def invoke(self, state: AgentState) -> AgentState:
            return await LangChainGraphAdapter(factory({"intent": state.intent})).run(state)

    return FactoryAdapter()
