import re
from dataclasses import dataclass


@dataclass
class ScoredDocument:
    """A document with its blended relevance score."""

    text: str
    semantic_score: float
    keyword_score: float
    final_score: float


def _tokenize(text: str) -> set[str]:
    """Lowercase tokenization, drop tokens shorter than 2 chars."""
    return {t for t in re.findall(r"[a-z0-9_]+", text.lower()) if len(t) >= 2}


def rerank(
    query: str,
    documents: list[str],
    distances: list[float],
    n_results: int = 5,
    semantic_weight: float = 0.7,
) -> list[ScoredDocument]:
    """Hybrid reranking: blend semantic distance with keyword overlap.

    Args:
        query: The user's search query.
        documents: Candidate documents from ChromaDB.
        distances: ChromaDB distances (lower = more similar, 0-2 range for cosine).
        n_results: How many top results to return.
        semantic_weight: Weight for semantic score (keyword gets 1 - this).
    """
    if not documents:
        return []

    query_tokens = _tokenize(query)
    if not query_tokens:
        query_tokens = {""}

    keyword_weight = 1.0 - semantic_weight
    scored: list[ScoredDocument] = []

    for doc, dist in zip(documents, distances):
        # Semantic: convert distance (0-2) to score (1-0)
        semantic_score = max(0.0, 1.0 - dist / 2.0)

        # Keyword: fraction of query tokens found in document
        doc_tokens = _tokenize(doc)
        matching = len(query_tokens & doc_tokens)
        keyword_score = matching / len(query_tokens)

        final = semantic_score * semantic_weight + keyword_score * keyword_weight

        scored.append(ScoredDocument(
            text=doc,
            semantic_score=semantic_score,
            keyword_score=keyword_score,
            final_score=final,
        ))

    scored.sort(key=lambda s: s.final_score, reverse=True)
    return scored[:n_results]
