"""
Retrieval: query ChromaDB and filter out low-confidence matches so the
model isn't fed irrelevant context (which is a common cause of
hallucinated or off-topic answers in naive RAG setups).
"""
from dataclasses import dataclass
from typing import List

from .config import settings
from .vectorstore import query_similar


@dataclass
class RetrievedChunk:
    text: str
    document: str
    section: str
    page: int
    similarity: float  # 0-1, higher is more similar


def _distance_to_similarity(distance: float) -> float:
    """
    Chroma with cosine space returns cosine *distance* (0 = identical,
    2 = opposite). Convert to a 0-1 similarity score.
    """
    return max(0.0, 1.0 - (distance / 2.0))


def retrieve(query: str, top_k: int = None, threshold: float = None) -> List[RetrievedChunk]:
    """
    Retrieve the top_k most relevant chunks for a query, filtering out
    anything below the similarity threshold.
    """
    top_k = top_k or settings.top_k
    threshold = threshold if threshold is not None else settings.similarity_threshold

    raw = query_similar(query, top_k=top_k)

    documents = raw["documents"][0] if raw["documents"] else []
    metadatas = raw["metadatas"][0] if raw["metadatas"] else []
    distances = raw["distances"][0] if raw["distances"] else []

    results: List[RetrievedChunk] = []
    for text, meta, distance in zip(documents, metadatas, distances):
        similarity = _distance_to_similarity(distance)
        if similarity < threshold:
            continue
        results.append(
            RetrievedChunk(
                text=text,
                document=meta.get("document", "unknown"),
                section=meta.get("section", "unknown"),
                page=meta.get("page", 0),
                similarity=round(similarity, 4),
            )
        )

    return results
