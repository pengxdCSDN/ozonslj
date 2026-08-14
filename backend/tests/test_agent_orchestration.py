import pytest

from backend.app.domain.agent_orchestration import (
    AgentState,
    AgentToolSpec,
    SequentialAgentGraph,
    langchain_tool_specs,
)


@pytest.mark.asyncio
async def test_sequential_graph_passes_state_between_nodes() -> None:
    async def add_intent(state: AgentState) -> AgentState:
        return AgentState(
            request_id=state.request_id,
            user_id=state.user_id,
            question=state.question,
            intent="knowledge",
            messages=state.messages,
        )

    async def add_message(state: AgentState) -> AgentState:
        return AgentState(
            request_id=state.request_id, user_id=state.user_id, question=state.question,
            intent=state.intent, messages=(*state.messages, "done"),
        )

    result = await SequentialAgentGraph((add_intent, add_message)).invoke(
        AgentState("r1", "u1", "什么是切片？")
    )
    assert result.intent == "knowledge"
    assert result.messages == ("done",)


def test_tool_specs_reject_external_writes() -> None:
    with pytest.raises(ValueError, match="外部写工具"):
        langchain_tool_specs((AgentToolSpec("write", "写入", {}, read_only=False),))
