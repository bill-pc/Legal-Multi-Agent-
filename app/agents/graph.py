"""
LangGraph Multi-Agent Orchestration
-----------------------------------
Flow chính (theo sơ đồ + NCKH):

START
  → router
  → (conditional)
       ├─ OUT_OF_SCOPE / clarification → END
       └─ specialists (fan-out theo decision)
            → aggregator
            → harness (sẽ thêm ở bước F)
            → END
"""

from typing import Optional, Callable, List, Dict, Annotated, TypedDict
import operator
from loguru import logger

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

from app.core.schemas import AgentState, AgentName, IntentType
from app.agents.router import run_router, route_after_router
from app.agents.specialists import SPECIALIST_RUNNERS
from app.agents.aggregator import run_aggregator


# ---------- Helper nodes ----------

async def run_specialists(state: AgentState) -> AgentState:
    """
    Fan-out: chạy tuần tự (hoặc song song sau này) các specialist
    được Router chỉ định.
    """
    if not state.router_decision:
        return state

    agents_to_run = state.router_decision.agents
    logger.info(f"[{state.session_id}] Running specialists: {agents_to_run}")

    for agent_name in agents_to_run:
        runner = SPECIALIST_RUNNERS.get(agent_name)
        if runner:
            state = await runner(state)
        else:
            logger.warning(f"No runner for agent {agent_name}")

    return state


async def clarification_node(state: AgentState) -> AgentState:
    """Trả câu hỏi làm rõ cho người dùng."""
    q = (
        state.router_decision.clarification_question
        if state.router_decision
        else "Bạn có thể cung cấp thêm thông tin chi tiết hơn không?"
    )
    state.final_answer = q
    state.status = "NEED_CLARIFICATION"
    return state


# ---------- Build Graph ----------

def build_graph() -> StateGraph:
    workflow = StateGraph(AgentState)

    # Nodes
    workflow.add_node("router", run_router)
    workflow.add_node("specialists", run_specialists)
    workflow.add_node("aggregator", run_aggregator)
    workflow.add_node("clarification", clarification_node)

    # Entry
    workflow.set_entry_point("router")

    # Conditional edges after router
    workflow.add_conditional_edges(
        "router",
        route_after_router,
        {
            "specialists": "specialists",
            "clarification": "clarification",
            "end": END,
        },
    )

    # Specialists → Aggregator
    workflow.add_edge("specialists", "aggregator")

    # Aggregator → END (sau này sẽ chèn harness)
    workflow.add_edge("aggregator", END)
    workflow.add_edge("clarification", END)

    return workflow.compile()


# Compiled graph (singleton)
_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


# ---------- Public entry point ----------

async def run_multi_agent_graph(
    query: str,
    session_id: Optional[str] = None,
    history: Optional[List[Dict[str, str]]] = None,
    stream_callback: Optional[Callable] = None,
) -> AgentState:
    """
    Entry point được gọi từ FastAPI.
    """
    logger.info(f"[{session_id}] === Multi-Agent Graph START ===")
    logger.info(f"[{session_id}] Query: {query[:100]}...")

    initial_state = AgentState(
        query=query,
        session_id=session_id,
        history=history or [],
    )

    graph = get_graph()

    # LangGraph invoke (async)
    final_state_dict = await graph.ainvoke(initial_state)

    # LangGraph trả về dict → convert lại AgentState nếu cần
    if isinstance(final_state_dict, dict):
        final_state = AgentState(**final_state_dict)
    else:
        final_state = final_state_dict

    logger.info(
        f"[{session_id}] === Graph END === status={final_state.status}, "
        f"agents={list(final_state.agent_results.keys())}"
    )
    return final_state
