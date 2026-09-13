import json
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from sse_starlette.sse import EventSourceResponse
from loguru import logger

from app.core.schemas import ChatRequest, ChatResponse, AgentState
from app.api.deps import get_current_user
from app.agents.graph import run_multi_agent_graph  # will implement in B

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("", response_model=ChatResponse)
async def chat_sync(
    request: ChatRequest,
    user: dict | None = Depends(get_current_user),
):
    """
    Synchronous chat endpoint (for testing / non-streaming clients).
    """
    session_id = request.session_id or str(uuid.uuid4())
    logger.info(f"[{session_id}] Query: {request.query[:80]}...")

    try:
        state = await run_multi_agent_graph(
            query=request.query,
            session_id=session_id,
            history=request.history or [],
        )
        return ChatResponse(
            answer=state.final_answer or "Không thể tạo câu trả lời.",
            citations=state.final_citations,
            agents_used=list(state.agent_results.keys()),
            intent=state.router_decision.intents if state.router_decision else [],
            session_id=session_id,
            status=state.status,
            metadata=state.metadata,
        )
    except Exception as e:
        logger.exception(f"[{session_id}] Error in chat_sync")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    user: dict | None = Depends(get_current_user),
):
    """
    SSE streaming endpoint – matches the architecture diagram (SSE Real-time Stream).
    """
    session_id = request.session_id or str(uuid.uuid4())

    async def event_generator() -> AsyncGenerator[dict, None]:
        try:
            # Stage 1: Router thinking
            yield {
                "event": "status",
                "data": json.dumps({"stage": "routing", "message": "Đang phân tích ý định..."}),
            }

            state = await run_multi_agent_graph(
                query=request.query,
                session_id=session_id,
                history=request.history or [],
                stream_callback=None,  # can be extended later
            )

            # Stage 2: Final answer
            yield {
                "event": "answer",
                "data": json.dumps(
                    {
                        "answer": state.final_answer,
                        "citations": [c.model_dump() for c in state.final_citations],
                        "agents_used": [a.value if hasattr(a, "value") else str(a) for a in state.agent_results.keys()],
                        "intent": [i.value for i in (state.router_decision.intents if state.router_decision else [])],
                        "status": state.status,
                        "session_id": session_id,
                    },
                    ensure_ascii=False,
                ),
            }

            yield {"event": "done", "data": "{}"}

        except Exception as e:
            logger.exception(f"[{session_id}] Stream error")
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)}, ensure_ascii=False),
            }

    return EventSourceResponse(event_generator())
