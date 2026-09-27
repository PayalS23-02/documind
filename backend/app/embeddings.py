"""
Embedding generation using Google's gemini-embedding-001 model.
"""
from typing import List

from google import genai
from google.genai import types

from .config import settings

_client = None


def get_client() -> genai.Client:
    global _client
    if _client is None:
        if not settings.gemini_api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Add it to your .env file "
                "(see .env.example)."
            )
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


def embed_texts(texts: List[str], task_type: str = "RETRIEVAL_DOCUMENT") -> List[List[float]]:
    """
    Embed a batch of texts.
    task_type: "RETRIEVAL_DOCUMENT" for chunks being stored,
               "RETRIEVAL_QUERY" for the user's question at query time.
    """
    client = get_client()
    result = client.models.embed_content(
        model=settings.embedding_model,
        contents=texts,
        config=types.EmbedContentConfig(task_type=task_type),
    )
    return [e.values for e in result.embeddings]


def embed_query(query: str) -> List[float]:
    return embed_texts([query], task_type="RETRIEVAL_QUERY")[0]
