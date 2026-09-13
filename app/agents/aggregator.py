"""
Aggregator / Synthesizer (Agent 4 trong sơ đồ gốc – Procedure Agent Aggregator)
Kết hợp kết quả từ các Specialist → câu trả lời cuối + citations.
"""

from loguru import logger
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from app.core.config import get_settings
from app.core.schemas import AgentState, Citation

settings = get_settings()

AGGREGATOR_PROMPT = """Bạn là Aggregator Agent của hệ thống Trợ lý Pháp lý.

Nhiệm vụ: Tổng hợp các kết quả từ các Agent chuyên môn thành một câu trả lời hoàn chỉnh, rõ ràng, có căn cứ pháp lý.

### Yêu cầu:
- Trả lời bằng tiếng Việt, văn phong trang trọng, dễ hiểu.
- Luôn kèm căn cứ (Điều, Khoản, văn bản…) nếu có.
- Nếu các agent đưa thông tin mâu thuẫn → nêu rõ và ưu tiên văn bản có hiệu lực cao hơn / mới hơn.
- Không bịa đặt thông tin.
- Kết thúc bằng phần "Căn cứ pháp lý" liệt kê các nguồn.

### Câu hỏi gốc:
{query}

### Kết quả từ các Agent:
{agent_outputs}

Hãy viết câu trả lời cuối cùng.
"""


async def run_aggregator(state: AgentState) -> AgentState:
    logger.info(f"[{state.session_id}] Aggregator running...")

    if not state.agent_results:
        state.final_answer = "Không có kết quả từ các agent chuyên môn."
        state.status = "FAIL"
        return state

    # Ghép output các agent
    outputs = []
    all_citations: list[Citation] = []
    for name, result in state.agent_results.items():
        outputs.append(f"### {name}\n{result.content}")
        all_citations.extend(result.citations)

    agent_outputs_str = "\n\n".join(outputs)

    # Nếu chỉ có 1 agent → có thể bỏ qua LLM tổng hợp để tiết kiệm
    if len(state.agent_results) == 1:
        only = next(iter(state.agent_results.values()))
        state.final_answer = only.content
        state.final_citations = only.citations
        state.status = "PASS"
        return state

    # Nhiều agent → gọi LLM tổng hợp
    try:
        llm = ChatOpenAI(
            model=settings.primary_llm,
            temperature=0.1,
            api_key=settings.openai_api_key or None,
        )
        prompt = ChatPromptTemplate.from_template(AGGREGATOR_PROMPT)
        chain = prompt | llm
        response = await chain.ainvoke(
            {
                "query": state.query,
                "agent_outputs": agent_outputs_str,
            }
        )
        state.final_answer = response.content
        state.final_citations = all_citations
        state.status = "PASS"
    except Exception as e:
        logger.exception("Aggregator failed")
        # Fallback: nối các câu trả lời
        state.final_answer = "\n\n---\n\n".join(
            [r.content for r in state.agent_results.values()]
        )
        state.final_citations = all_citations
        state.status = "PARTIAL"
        state.error_messages.append(f"Aggregator error: {str(e)}")

    return state
