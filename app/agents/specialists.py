"""
4 Specialist Agents – Logic + Prompts đầy đủ theo NCKH Chương 4.4
"""

from typing import List, Dict, Any
from loguru import logger
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from app.core.config import get_settings
from app.core.schemas import (
    AgentState,
    AgentName,
    AgentResult,
    Citation,
)
from app.tools.vector_search import search_vector
from app.tools.kg_query import query_cypher, get_related_articles

settings = get_settings()


def get_agent_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.primary_llm,
        temperature=0.0,
        api_key=settings.openai_api_key or None,
    )


# ============================================================
# Agent 1 – Legal Text Specialist
# ============================================================

LEGAL_TEXT_PROMPT = """Bạn là Legal Text Agent – chuyên gia tra cứu văn bản quy phạm pháp luật Việt Nam.

Nhiệm vụ:
- Trả lời chính xác nội dung Điều / Khoản / Điểm dựa trên ngữ cảnh được cung cấp.
- Luôn trích dẫn rõ: Tên văn bản + Số hiệu + Điều + Khoản (nếu có).
- Nếu ngữ cảnh không đủ → nói rõ "Không tìm thấy căn cứ trong kho dữ liệu hiện tại".
- Không bịa đặt điều luật.

### Câu hỏi:
{query}

### Ngữ cảnh truy xuất được:
{context}

Hãy trả lời ngắn gọn, chính xác, kèm căn cứ.
"""


async def run_legal_text_agent(state: AgentState) -> AgentState:
    logger.info(f"[{state.session_id}] LegalTextAgent running...")

    # TODO: thay bằng embedding thật + hybrid retrieval (bước E)
    # Hiện tại dùng stub context để flow chạy được
    context = (
        "Luật Doanh nghiệp 2020 – Điều 15:\n"
        "1. Tự do kinh doanh trong những ngành, nghề mà luật không cấm.\n"
        "2. Tự chủ kinh doanh và lựa chọn hình thức tổ chức kinh doanh..."
    )

    try:
        llm = get_agent_llm()
        prompt = ChatPromptTemplate.from_template(LEGAL_TEXT_PROMPT)
        chain = prompt | llm
        response = await chain.ainvoke({"query": state.query, "context": context})

        citations = [
            Citation(
                document_id="LUAT-DN-2020",
                document_title="Luật Doanh nghiệp 2020",
                article="15",
                clause="1",
                content_snippet="Tự do kinh doanh trong những ngành, nghề mà luật không cấm.",
                score=0.92,
            )
        ]

        result = AgentResult(
            agent_name=AgentName.LEGAL_TEXT,
            content=response.content,
            citations=citations,
            confidence=0.85,
        )
    except Exception as e:
        logger.exception("LegalTextAgent failed")
        result = AgentResult(
            agent_name=AgentName.LEGAL_TEXT,
            content=f"Lỗi khi xử lý Legal Text Agent: {str(e)}",
            citations=[],
            confidence=0.0,
        )
        state.error_messages.append(str(e))

    state.agent_results[AgentName.LEGAL_TEXT.value] = result
    return state


# ============================================================
# Agent 2 – Case / Precedent Specialist
# ============================================================

CASE_PROMPT = """Bạn là Case/Precedent Agent – chuyên gia tìm án lệ và tình huống pháp lý tương tự.

Nhiệm vụ:
- Xác định vấn đề pháp lý cốt lõi từ câu hỏi.
- Tìm và tóm tắt các án lệ / tình huống tương tự từ ngữ cảnh.
- So sánh điểm giống / khác với tình huống người dùng nêu.
- Nêu rõ nguồn án lệ (số án lệ, năm, Tòa án…).

### Câu hỏi:
{query}

### Ngữ cảnh án lệ truy xuất được:
{context}

Hãy trả lời có cấu trúc: Vấn đề pháp lý → Án lệ liên quan → Phân tích tương đồng.
"""


async def run_case_precedent_agent(state: AgentState) -> AgentState:
    logger.info(f"[{state.session_id}] CasePrecedentAgent running...")

    context = "[Chưa có dữ liệu án lệ trong demo – sẽ bổ sung ở bước ingest]"

    try:
        llm = get_agent_llm()
        prompt = ChatPromptTemplate.from_template(CASE_PROMPT)
        chain = prompt | llm
        response = await chain.ainvoke({"query": state.query, "context": context})

        result = AgentResult(
            agent_name=AgentName.CASE_PRECEDENT,
            content=response.content,
            citations=[],
            confidence=0.6,
        )
    except Exception as e:
        logger.exception("CasePrecedentAgent failed")
        result = AgentResult(
            agent_name=AgentName.CASE_PRECEDENT,
            content=f"Lỗi CasePrecedentAgent: {str(e)}",
            citations=[],
            confidence=0.0,
        )

    state.agent_results[AgentName.CASE_PRECEDENT.value] = result
    return state


# ============================================================
# Agent 3 – Compliance Specialist
# ============================================================

COMPLIANCE_PROMPT = """Bạn là Compliance Agent – chuyên gia kiểm tra điều kiện và tính tuân thủ pháp luật.

Nhiệm vụ:
- Liệt kê các điều kiện pháp lý liên quan từ ngữ cảnh.
- Đối chiếu với thông tin người dùng cung cấp.
- Kết luận rõ ràng từng điều kiện: Đáp ứng / Không đáp ứng / Thiếu thông tin.
- Luôn kèm căn cứ pháp lý.

### Câu hỏi / Tình huống của người dùng:
{query}

### Quy định truy xuất được:
{context}

Hãy trả lời dạng bảng hoặc danh sách rõ ràng.
"""


async def run_compliance_agent(state: AgentState) -> AgentState:
    logger.info(f"[{state.session_id}] ComplianceAgent running...")

    context = (
        "Theo Luật Doanh nghiệp 2020, điều kiện thành lập doanh nghiệp bao gồm: "
        "có ngành nghề không bị cấm, có trụ sở, có vốn điều lệ tối thiểu theo quy định..."
    )

    try:
        llm = get_agent_llm()
        prompt = ChatPromptTemplate.from_template(COMPLIANCE_PROMPT)
        chain = prompt | llm
        response = await chain.ainvoke({"query": state.query, "context": context})

        result = AgentResult(
            agent_name=AgentName.COMPLIANCE,
            content=response.content,
            citations=[],
            confidence=0.75,
        )
    except Exception as e:
        logger.exception("ComplianceAgent failed")
        result = AgentResult(
            agent_name=AgentName.COMPLIANCE,
            content=f"Lỗi ComplianceAgent: {str(e)}",
            citations=[],
            confidence=0.0,
        )

    state.agent_results[AgentName.COMPLIANCE.value] = result
    return state


# ============================================================
# Agent 4 – Procedure Specialist
# ============================================================

PROCEDURE_PROMPT = """Bạn là Procedure Agent – chuyên gia hướng dẫn thủ tục hành chính / pháp lý.

Nhiệm vụ:
- Xác định đúng thủ tục người dùng hỏi.
- Liệt kê đầy đủ: thành phần hồ sơ, cơ quan tiếp nhận, trình tự các bước, thời hạn giải quyết, kết quả.
- Nêu rõ căn cứ pháp lý của thủ tục.
- Nếu thiếu thông tin → hỏi thêm hoặc nêu điều kiện tiên quyết.

### Câu hỏi:
{query}

### Thông tin thủ tục truy xuất được:
{context}

Hãy trả lời theo cấu trúc:
1. Tên thủ tục
2. Căn cứ pháp lý
3. Thành phần hồ sơ
4. Cơ quan thực hiện
5. Trình tự các bước
6. Thời hạn
7. Kết quả
"""


async def run_procedure_agent(state: AgentState) -> AgentState:
    logger.info(f"[{state.session_id}] ProcedureAgent running...")

    context = (
        "Thủ tục đăng ký thành lập doanh nghiệp theo Luật Doanh nghiệp 2020 và "
        "Nghị định hướng dẫn: hồ sơ gồm giấy đề nghị, điều lệ, danh sách thành viên..."
    )

    try:
        llm = get_agent_llm()
        prompt = ChatPromptTemplate.from_template(PROCEDURE_PROMPT)
        chain = prompt | llm
        response = await chain.ainvoke({"query": state.query, "context": context})

        result = AgentResult(
            agent_name=AgentName.PROCEDURE,
            content=response.content,
            citations=[],
            confidence=0.8,
        )
    except Exception as e:
        logger.exception("ProcedureAgent failed")
        result = AgentResult(
            agent_name=AgentName.PROCEDURE,
            content=f"Lỗi ProcedureAgent: {str(e)}",
            citations=[],
            confidence=0.0,
        )

    state.agent_results[AgentName.PROCEDURE.value] = result
    return state


# ---------- Mapping ----------
SPECIALIST_RUNNERS = {
    AgentName.LEGAL_TEXT: run_legal_text_agent,
    AgentName.CASE_PRECEDENT: run_case_precedent_agent,
    AgentName.COMPLIANCE: run_compliance_agent,
    AgentName.PROCEDURE: run_procedure_agent,
}
