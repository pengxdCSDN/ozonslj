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
    """定义项目对 LangChain 异步 Runnable 的最小依赖协议。"""

    async def ainvoke(self, input: dict[str, Any]) -> dict[str, Any]:
        """接收图状态并返回可映射回领域状态的结果。"""
        ...


class LangChainGraphAdapter:
    """把 LangChain Runnable 适配为项目内部的图执行端口。"""

    def __init__(self, runnable: LangChainRunnable) -> None:
        """保存第三方 Runnable；不在构造阶段加载模型或访问网络。"""
        self._runnable = runnable

    async def run(self, state: AgentState) -> AgentState:
        """将领域 AgentState 转换为 Runnable 输入，并映射执行结果。"""
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
        """延迟创建 Runnable 的领域图端口适配器。"""

        async def invoke(self, state: AgentState) -> AgentState:
            """按当前意图创建 Runnable 并执行一次领域状态转换。"""
            return await LangChainGraphAdapter(factory({"intent": state.intent})).run(state)

    return FactoryAdapter()
