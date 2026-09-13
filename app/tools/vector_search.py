"""
Vector MCP tool – search_vector
"""

from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.http.models import Filter, FieldCondition, MatchValue
from loguru import logger

from app.core.config import get_settings

settings = get_settings()


def get_qdrant_client() -> QdrantClient:
    return QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)


async def search_vector(
    query_vector: List[float],
    top_k: int = 8,
    filters: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Tìm kiếm vector trên Qdrant.
    Trả về list các payload + score.
    """
    client = get_qdrant_client()
    collection = settings.qdrant_collection

    qdrant_filter = None
    if filters:
        conditions = []
        for key, value in filters.items():
            conditions.append(
                FieldCondition(key=key, match=MatchValue(value=value))
            )
        if conditions:
            qdrant_filter = Filter(must=conditions)

    try:
        hits = client.search(
            collection_name=collection,
            query_vector=query_vector,
            limit=top_k,
            query_filter=qdrant_filter,
            with_payload=True,
        )
        results = []
        for hit in hits:
            results.append(
                {
                    "id": str(hit.id),
                    "score": hit.score,
                    "payload": hit.payload or {},
                }
            )
        return results
    except Exception as e:
        logger.error(f"Qdrant search error: {e}")
        return []
