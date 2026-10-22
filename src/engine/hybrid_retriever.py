"""Hybrid temporal retrieval combining fulltext and vector search with RRF."""
from ..graph.connection import get_neo4j_driver
from .embedder import DeterministicEmbedder
from .models import ArticleNode


def reciprocal_rank_fusion(
    fulltext_ranks: list[str],
    vector_ranks: list[str],
    k: int = 60,
) -> list[tuple[str, float]]:
    """Compute Reciprocal Rank Fusion (RRF) scores across rankings."""
    scores: dict[str, float] = {}
    for rank_list in (fulltext_ranks, vector_ranks):
        seen: set[str] = set()
        for idx, doc_id in enumerate(rank_list, start=1):
            if doc_id not in seen:
                seen.add(doc_id)
                scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + idx)
    return sorted(scores.items(), key=lambda item: item[1], reverse=True)


def _format_lucene_query(query: str) -> str:
    """Format user query into high-precision Lucene query with phrase and AND matching."""
    clean_kw = "".join(
        c if c not in r'+-&|!(){}[]^"~*?:\/' else " " for c in query
    ).strip()
    words = clean_kw.split()
    if not words:
        return ""
    if len(words) == 1:
        return words[0]

    exact_phrase = f'"{clean_kw}"'
    bigrams = [f'"{words[i]} {words[i+1]}"' for i in range(len(words) - 1)]
    and_query = " AND ".join(words)
    if bigrams:
        return f'{exact_phrase}^4 OR {" OR ".join(f"{bg}^2" for bg in bigrams[:6])} OR ({and_query})'
    return f'{exact_phrase}^4 OR ({and_query})'


def _search_fulltext(
    session, query: str, as_of_date: str, limit: int = 30
) -> list[str]:
    """Search candidate article IDs using Lucene fulltext index with fallback."""
    formatted_kw = _format_lucene_query(query)
    if formatted_kw:
        try:
            cypher_lucene = """
            CALL db.index.fulltext.queryNodes('article_content_fulltext', $kw) YIELD node, score
            OPTIONAL MATCH (parent:Article)-[:CONTAINS]->(node:Clause)
            WITH coalesce(parent, node) AS art, score
            WHERE 'Article' IN labels(art)
              AND art.valid_from <= date($as_of_date)
              AND art.valid_to >= date($as_of_date)
            RETURN art.id AS id, max(score) AS score
            ORDER BY score DESC
            LIMIT $limit
            """
            rows = session.run(
                cypher_lucene, kw=formatted_kw, as_of_date=as_of_date, limit=limit
            ).data()
            if rows:
                return [r["id"] for r in rows if r.get("id")]
        except Exception:
            pass

    cypher_fallback = """
    MATCH (art:Article)
    WHERE art.valid_from <= date($as_of_date)
      AND art.valid_to >= date($as_of_date)
      AND toLower(art.content) CONTAINS toLower($kw)
    RETURN art.id AS id
    LIMIT $limit
    """
    rows = session.run(
        cypher_fallback, kw=query, as_of_date=as_of_date, limit=limit
    ).data()
    return [r["id"] for r in rows if r.get("id")]


def _search_vector(
    session, vec: list[float], as_of_date: str, top_k: int = 30
) -> list[str]:
    """Search candidate article IDs using vector index with temporal filter."""
    try:
        cypher_vector = """
        CALL db.index.vector.queryNodes('article_embedding', $top_k, $vec) YIELD node, score
        WHERE node.valid_from <= date($as_of_date)
          AND node.valid_to >= date($as_of_date)
        RETURN node.id AS id, score
        ORDER BY score DESC
        """
        rows = session.run(
            cypher_vector, top_k=top_k, vec=vec, as_of_date=as_of_date
        ).data()
        return [r["id"] for r in rows if r.get("id")]
    except Exception:
        return []


def _enrich_articles(
    session, candidate_ids: list[str], as_of_date: str
) -> list[ArticleNode]:
    """Fetch article details and 1-hop relations valid as of specified date."""
    if not candidate_ids:
        return []

    cypher_enrich = """
    MATCH (doc:Document)-[:CONTAINS]->(art:Article)
    WHERE art.id IN $ids
    OPTIONAL MATCH (amender:Article)-[:AMENDS]->(art)
      WHERE amender.valid_from <= date($as_of_date)
    OPTIONAL MATCH (art)-[:CONTAINS]->(:Clause)-[:CITES]->(cited:Article)
      WHERE cited.valid_from <= date($as_of_date)
        AND cited.valid_to >= date($as_of_date)
    RETURN art.id AS id, doc.id AS doc_id, art.code AS code,
           art.title AS title, art.content AS content,
           toString(art.valid_from) AS valid_from,
           toString(art.valid_to) AS valid_to,
           collect(DISTINCT amender.id) + collect(DISTINCT cited.id) AS related_ids
    """
    rows = session.run(
        cypher_enrich, ids=candidate_ids, as_of_date=as_of_date
    ).data()
    nodes: dict[str, ArticleNode] = {}
    for r in rows:
        related = sorted({x for x in r.pop("related_ids") if x})
        node = ArticleNode(**r, status="ACTIVE", related_ids=related)
        nodes[node.id] = node
    return [nodes[cid] for cid in candidate_ids if cid in nodes]


def query_hybrid_temporal(
    query: str,
    as_of_date: str,
    top_k: int = 15,
    embedder=None,
) -> list[ArticleNode]:
    """Execute hybrid search combining fulltext and vector retrieval."""
    # ponytail: default DeterministicEmbedder, upgrade to bge-m3 service in production
    active_embedder = embedder or DeterministicEmbedder(dimension=1024)
    query_vec = active_embedder.embed_text(query)

    driver = get_neo4j_driver()
    with driver.session() as session:
        ft_ranks = _search_fulltext(session, query, as_of_date, limit=30)
        vec_ranks = _search_vector(session, query_vec, as_of_date, top_k=30)
        fused = reciprocal_rank_fusion(ft_ranks, vec_ranks, k=60)
        candidate_ids = [doc_id for doc_id, _ in fused[:top_k]]
        return _enrich_articles(session, candidate_ids, as_of_date)
