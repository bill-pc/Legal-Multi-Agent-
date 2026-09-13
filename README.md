# Legal Multi-Agent Assistant

Hệ thống Trợ lý Pháp lý Thông minh dựa trên kiến trúc **Multi-Agent + Hybrid Knowledge Base (Vector + Knowledge Graph) + MCP + Agent Harness**.

Đề tài NCKH Eureka 2026 – Trường Đại học Công nghiệp TP. Hồ Chí Minh.

## Kiến trúc tổng thể

```
Client (React)
    ↓ HTTPS + SSE
API Gateway (FastAPI + JWT + SSE)
    ↓
Orchestrator / Router Agent (LangGraph)
    ├── Legal Text Agent
    ├── Case/Precedent Agent
    ├── Compliance Agent
    └── Procedure Agent
         ↓ MCP Tools
    Hybrid Knowledge Base
         ├── Qdrant (Vector – HNSW)
         ├── Neo4j (Knowledge Graph)
         └── Redis (Cache / Session)
    ↓
Retrieval & Fusion (BM25 + Dense + RRF + Cross-Encoder)
    ↓
Agent Harness (Bounded Loop + Guardrail Citation + Failover)
    ↓
Response Synthesis + Citations
```

## Yêu cầu hệ thống

- Docker & Docker Compose
- Python 3.11+
- OpenAI API key (hoặc Anthropic)

## Cài đặt nhanh

```bash
# 1. Clone / copy project
cd legal-multi-agent

# 2. Tạo môi trường
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Cài dependency
pip install -r requirements.txt

# 4. Copy env
cp .env.example .env
# Sửa OPENAI_API_KEY và các thông tin khác

# 5. Chạy infrastructure
docker compose up -d

# 6. Chạy API
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Truy cập:
- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/health
- Neo4j Browser: http://localhost:7474 (credentials configured in `.env`)
- Qdrant Dashboard: http://localhost:6333/dashboard

## Cấu trúc thư mục

```
legal-multi-agent/
├── app/
│   ├── api/          # FastAPI routes
│   ├── agents/       # Router + 4 Specialists + Graph
│   ├── tools/        # MCP-style tools (search_vector, query_cypher…)
│   ├── retrieval/    # Hybrid retrieval, RRF, Reranker
│   ├── harness/      # Guardrail, Loop control, Failover
│   └── core/         # config, schemas
├── data/
├── scripts/          # ingest scripts
├── frontend/
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## Roadmap triển khai

- [x] **A.** Cấu trúc + docker-compose + FastAPI skeleton
- [x] **B.** Router Agent (LangGraph) + Orchestrator + Aggregator
- [x] **C.** Schema Neo4j + Tool search_vector / query_cypher + Ingest script
- [x] **D.** 4 Specialist Agents + Prompts đầy đủ
- [ ] **E.** Hybrid Retrieval (BM25 + Dense + RRF + Cross-Encoder Rerank)
- [ ] **F.** Agent Harness (Bounded Loop + Guardrail Citation + Failover)
- [ ] **G.** Frontend React + SSE
- [ ] **H.** Evaluation pipeline (1.247 queries)

## Tài liệu liên quan

- Luận văn NCKH Eureka 2026
- Sơ đồ kiến trúc FLLU.png
- Dataset: Vietnamese Legal Documents Dataset (Hugging Face)
