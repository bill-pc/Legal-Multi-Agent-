from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.core.config import get_settings
from app.api.chat import router as chat_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.app_name}")
    # TODO: init Qdrant / Neo4j / Redis connections here
    yield
    logger.info("Shutting down...")


app = FastAPI(
    title=settings.app_name,
    description="Hệ thống Trợ lý Pháp lý Thông minh – Multi-Agent + Hybrid Knowledge Base (NCKH Eureka 2026)",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": "0.1.0",
    }


@app.get("/")
async def root():
    return {
        "message": "Legal Multi-Agent Assistant API",
        "docs": "/docs",
        "health": "/health",
    }
