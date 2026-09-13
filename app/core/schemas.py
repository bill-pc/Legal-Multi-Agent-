from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class IntentType(str, Enum):
    LEGAL_TEXT = "LEGAL_TEXT"
    PRECEDENT = "PRECEDENT"
    COMPLIANCE = "COMPLIANCE"
    PROCEDURE = "PROCEDURE"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    MULTI = "MULTI"  # multiple intents


class AgentName(str, Enum):
    LEGAL_TEXT = "LegalTextAgent"
    CASE_PRECEDENT = "CasePrecedentAgent"
    COMPLIANCE = "ComplianceAgent"
    PROCEDURE = "ProcedureAgent"
    AGGREGATOR = "AggregatorAgent"


# ---------- Request / Response ----------

class ChatRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=2000)
    session_id: Optional[str] = None
    history: Optional[List[Dict[str, str]]] = None


class Citation(BaseModel):
    document_id: Optional[str] = None
    document_title: Optional[str] = None
    article: Optional[str] = None
    clause: Optional[str] = None
    point: Optional[str] = None
    content_snippet: Optional[str] = None
    source_url: Optional[str] = None
    score: Optional[float] = None


class AgentResult(BaseModel):
    agent_name: AgentName
    content: str
    citations: List[Citation] = []
    raw_context: Optional[List[Dict[str, Any]]] = None
    confidence: float = 0.0


class ChatResponse(BaseModel):
    answer: str
    citations: List[Citation] = []
    agents_used: List[AgentName] = []
    intent: List[IntentType] = []
    session_id: Optional[str] = None
    status: str = "PASS"  # PASS | FAIL | PARTIAL
    metadata: Dict[str, Any] = {}


# ---------- Router internal ----------

class RouterDecision(BaseModel):
    intents: List[IntentType]
    agents: List[AgentName]
    confidence: float = 0.0
    reasoning: str = ""
    enriched_query: Optional[str] = None
    needs_clarification: bool = False
    clarification_question: Optional[str] = None


# ---------- State for LangGraph ----------

class AgentState(BaseModel):
    """State shared across the multi-agent graph."""
    query: str
    session_id: Optional[str] = None
    history: List[Dict[str, str]] = []

    # Router output
    router_decision: Optional[RouterDecision] = None

    # Results from specialist agents
    agent_results: Dict[str, AgentResult] = {}

    # Aggregated
    final_answer: Optional[str] = None
    final_citations: List[Citation] = []
    status: str = "PENDING"  # PENDING | PASS | FAIL | OUT_OF_SCOPE

    # Harness control
    loop_count: int = 0
    error_messages: List[str] = []
    metadata: Dict[str, Any] = {}

    class Config:
        arbitrary_types_allowed = True
