"""
Router / Orchestrator Agent
---------------------------
Theo NCKH Chương 4.3 + sơ đồ kiến trúc.

Vai trò:
- Phân tích câu hỏi pháp lý
- Phân loại Intent (LEGAL_TEXT / PRECEDENT / COMPLIANCE / PROCEDURE / OUT_OF_SCOPE)
- Quyết định gọi 1 hoặc nhiều Specialist Agent
- Có thể làm giàu query + kiểm tra cần clarification
"""

from typing import List
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from loguru import logger

from app.core.config import get_settings
from app.core.schemas import (
    IntentType,
    AgentName,
    RouterDecision,
    AgentState,
)

settings = get_settings()

# ---------- Prompt ----------

ROUTER_SYSTEM_PROMPT = """Bạn là Router Agent (Orchestrator) của hệ thống Trợ lý Pháp lý Thông minh Việt Nam.

Nhiệm vụ của bạn:
1. Phân tích câu hỏi pháp lý của người dùng.
2. Xác định (các) Intent chính.
3. Quyết định Agent nào cần được gọi.
4. Nếu câu hỏi mơ hồ hoặc thiếu thông tin quan trọng → yêu cầu làm rõ.
5. Nếu câu hỏi hoàn toàn ngoài phạm vi pháp luật → đánh dấu OUT_OF_SCOPE.

### Các Intent được hỗ trợ:
- LEGAL_TEXT: Tìm nội dung văn bản quy phạm pháp luật (Luật, Nghị định, Thông tư, Điều, Khoản, Điểm…)
- PRECEDENT: Tìm án lệ hoặc tình huống pháp lý tương tự
- COMPLIANCE: Kiểm tra điều kiện, yêu cầu pháp lý, có đáp ứng quy định hay không
- PROCEDURE: Thủ tục hành chính / pháp lý, hồ sơ, cơ quan, trình tự, thời hạn
- OUT_OF_SCOPE: Không liên quan đến pháp luật Việt Nam hoặc nằm ngoài phạm vi hệ thống

### Quy tắc quyết định Agent:
- LEGAL_TEXT → LegalTextAgent
- PRECEDENT → CasePrecedentAgent
- COMPLIANCE → ComplianceAgent
- PROCEDURE → ProcedureAgent
- Có thể gọi NHIỀU agent cùng lúc nếu câu hỏi chứa nhiều yêu cầu.
- OUT_OF_SCOPE → không gọi agent chuyên môn.

### Ví dụ:
Câu hỏi: "Điều 15 Luật Doanh nghiệp quy định gì?"
→ intents: [LEGAL_TEXT], agents: [LegalTextAgent]

Câu hỏi: "Tôi có đủ điều kiện thành lập công ty TNHH không và cần chuẩn bị hồ sơ gì?"
→ intents: [COMPLIANCE, PROCEDURE], agents: [ComplianceAgent, ProcedureAgent]

Câu hỏi: "Thời tiết hôm nay thế nào?"
→ intents: [OUT_OF_SCOPE], agents: []

Hãy trả lời đúng format JSON theo schema được cung cấp.
"""

ROUTER_HUMAN_TEMPLATE = """Câu hỏi của người dùng:
{query}

Lịch sử hội thoại (nếu có):
{history}

Hãy phân tích và đưa ra quyết định routing.
"""


def get_router_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.primary_llm,
        temperature=0.0,
        api_key=settings.openai_api_key or None,
    )


async def run_router(state: AgentState) -> AgentState:
    """
    Node LangGraph: Router Agent.
    Input: state.query, state.history
    Output: cập nhật state.router_decision
    """
    logger.info(f"[{state.session_id}] Router Agent đang phân tích...")

    parser = PydanticOutputParser(pydantic_object=RouterDecision)

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", ROUTER_SYSTEM_PROMPT + "\n\n{format_instructions}"),
            ("human", ROUTER_HUMAN_TEMPLATE),
        ]
    ).partial(format_instructions=parser.get_format_instructions())

    llm = get_router_llm()
    chain = prompt | llm | parser

    history_str = "\n".join(
        [f"{m.get('role', 'user')}: {m.get('content', '')}" for m in state.history[-6:]]
    ) or "Không có"

    try:
        decision: RouterDecision = await chain.ainvoke(
            {
                "query": state.query,
                "history": history_str,
            }
        )
        logger.info(
            f"[{state.session_id}] Router decision → intents={decision.intents}, "
            f"agents={decision.agents}, confidence={decision.confidence:.2f}"
        )
        state.router_decision = decision

        # Early exit for OUT_OF_SCOPE
        if IntentType.OUT_OF_SCOPE in decision.intents and not decision.agents:
            state.status = "OUT_OF_SCOPE"
            state.final_answer = (
                "Xin lỗi, câu hỏi của bạn nằm ngoài phạm vi hỗ trợ của hệ thống "
                "Trợ lý Pháp lý (chỉ hỗ trợ văn bản quy phạm pháp luật Việt Nam)."
            )

    except Exception as e:
        logger.exception(f"[{state.session_id}] Router failed")
        # Fallback an toàn
        state.router_decision = RouterDecision(
            intents=[IntentType.LEGAL_TEXT],
            agents=[AgentName.LEGAL_TEXT],
            confidence=0.3,
            reasoning=f"Fallback do lỗi router: {str(e)}",
        )
        state.error_messages.append(f"Router error: {str(e)}")

    return state


def route_after_router(state: AgentState) -> str:
    """
    Conditional edge sau Router.
    Trả về tên node tiếp theo.
    """
    if state.status == "OUT_OF_SCOPE":
        return "end"

    if not state.router_decision or not state.router_decision.agents:
        return "end"

    # Nếu cần clarification
    if state.router_decision.needs_clarification:
        return "clarification"

    # Gọi các specialist (sẽ fan-out trong graph)
    return "specialists"
