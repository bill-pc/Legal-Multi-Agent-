"""
Script ingest dữ liệu pháp luật vào Qdrant.
Hỗ trợ:
- Ingest từ file JSON/JSONL local
- Ingest mẫu demo (khi chưa có dataset đầy đủ)

Chạy:
    python -m scripts.ingest_qdrant --mode demo
    python -m scripts.ingest_qdrant --mode file --path data/processed/chunks.jsonl
"""

import argparse
import json
import uuid
from pathlib import Path
from typing import List, Dict, Any

from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Distance,
    VectorParams,
    PointStruct,
)
from loguru import logger

# Để chạy độc lập, tạm hard-code (sau này dùng settings)
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
COLLECTION = "vietnamese_legal_chunks"
EMBEDDING_DIM = 1536


def get_client() -> QdrantClient:
    return QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)


def ensure_collection(client: QdrantClient):
    collections = [c.name for c in client.get_collections().collections]
    if COLLECTION not in collections:
        logger.info(f"Creating collection `{COLLECTION}`...")
        client.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(
                size=EMBEDDING_DIM,
                distance=Distance.COSINE,
            ),
        )
        logger.info("Collection created.")
    else:
        logger.info(f"Collection `{COLLECTION}` already exists.")


def create_demo_points() -> List[PointStruct]:
    """
    Tạo vài điểm demo (vector giả) để test flow.
    Trong thực tế sẽ dùng embedding model thật.
    """
    import random

    demos = [
        {
            "document_id": "LUAT-DN-2020",
            "document_title": "Luật Doanh nghiệp 2020",
            "article": "15",
            "clause": "1",
            "content": "Doanh nghiệp có quyền tự do kinh doanh trong những ngành, nghề mà luật không cấm.",
            "type": "Luật",
            "status": "Còn hiệu lực",
        },
        {
            "document_id": "LUAT-DN-2020",
            "document_title": "Luật Doanh nghiệp 2020",
            "article": "15",
            "clause": "2",
            "content": "Doanh nghiệp có quyền tự chủ kinh doanh và lựa chọn hình thức tổ chức kinh doanh, chủ động lựa chọn ngành, nghề, địa bàn, hình thức kinh doanh...",
            "type": "Luật",
            "status": "Còn hiệu lực",
        },
        {
            "document_id": "LUAT-LD-2019",
            "document_title": "Bộ luật Lao động 2019",
            "article": "5",
            "clause": "1",
            "content": "Người lao động có quyền làm việc, tự do lựa chọn việc làm, nghề nghiệp, học nghề, nâng cao trình độ nghề nghiệp...",
            "type": "Bộ luật",
            "status": "Còn hiệu lực",
        },
    ]

    points = []
    for item in demos:
        # Vector giả (random) – thay bằng embedding thật sau
        vector = [random.uniform(-1, 1) for _ in range(EMBEDDING_DIM)]
        points.append(
            PointStruct(
                id=str(uuid.uuid4()),
                vector=vector,
                payload=item,
            )
        )
    return points


def ingest_from_jsonl(client: QdrantClient, path: str, batch_size: int = 64):
    """
    Ingest từ file JSONL.
    Mỗi dòng là object có keys: content, metadata..., và "vector" (list[float])
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)

    batch: List[PointStruct] = []
    total = 0

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            vector = obj.pop("vector", None)
            if vector is None:
                logger.warning("Skipping record without vector")
                continue

            point = PointStruct(
                id=obj.get("id") or str(uuid.uuid4()),
                vector=vector,
                payload=obj,
            )
            batch.append(point)

            if len(batch) >= batch_size:
                client.upsert(collection_name=COLLECTION, points=batch)
                total += len(batch)
                logger.info(f"Upserted {total} points...")
                batch = []

    if batch:
        client.upsert(collection_name=COLLECTION, points=batch)
        total += len(batch)

    logger.info(f"Finished. Total points upserted: {total}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["demo", "file"], default="demo")
    parser.add_argument("--path", type=str, default="")
    args = parser.parse_args()

    client = get_client()
    ensure_collection(client)

    if args.mode == "demo":
        points = create_demo_points()
        client.upsert(collection_name=COLLECTION, points=points)
        logger.info(f"Demo: upserted {len(points)} points.")
    else:
        if not args.path:
            raise ValueError("--path is required when mode=file")
        ingest_from_jsonl(client, args.path)


if __name__ == "__main__":
    main()
