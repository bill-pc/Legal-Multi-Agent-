"""
Knowledge Graph MCP tool – query_cypher
"""

from typing import List, Dict, Any, Optional
from neo4j import GraphDatabase
from loguru import logger

from app.core.config import get_settings

settings = get_settings()


def get_neo4j_driver():
    return GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )


async def query_cypher(
    cypher: str,
    parameters: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Thực thi Cypher query trên Neo4j.
    """
    driver = get_neo4j_driver()
    try:
        with driver.session() as session:
            result = session.run(cypher, parameters or {})
            return [record.data() for record in result]
    except Exception as e:
        logger.error(f"Neo4j query error: {e}")
        return []
    finally:
        driver.close()


# ---------- Helper queries thường dùng ----------

async def get_related_articles(article_id: str) -> List[Dict[str, Any]]:
    cypher = """
    MATCH (a:Article {id: $article_id})-[r:CITES|GUIDES|AMENDED_BY|REPLACES]-(related)
    RETURN a.title AS source_title,
           type(r) AS relation,
           labels(related) AS related_labels,
           related.id AS related_id,
           related.title AS related_title
    LIMIT 20
    """
    return await query_cypher(cypher, {"article_id": article_id})


async def get_article_content(article_id: str) -> Optional[Dict[str, Any]]:
    cypher = """
    MATCH (a:Article {id: $article_id})
    OPTIONAL MATCH (a)-[:HAS_CLAUSE]->(c:Clause)
    OPTIONAL MATCH (c)-[:HAS_POINT]->(p:Point)
    RETURN a.id AS id,
           a.number AS number,
           a.title AS title,
           a.content AS content,
           collect(DISTINCT {
               clause_number: c.number,
               clause_content: c.content,
               points: collect(DISTINCT {point: p.letter, content: p.content})
           }) AS clauses
    """
    results = await query_cypher(cypher, {"article_id": article_id})
    return results[0] if results else None
