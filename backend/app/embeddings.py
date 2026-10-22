"""
Embedding generation using Google's gemini-embedding-001 model.

Calls are wrapped with a timeout and retries so a stalled or rate-limited
request fails with a clear message instead of hanging forever.
"""
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from typing import List

from google import genai
from google.genai import types

from .config import settings

_client = None
_executor = ThreadPoolExecutor(max_workers=2)

REQUEST_TIMEOUT_SECONDS = 30
MAX_ATTEMPTS = 3


class EmbeddingError(Exception):
    """Raised when embeddings cannot be generated after retries."""


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


def _is_quota_error(message: str) -> bool:
    m = message.lower()
    return "429" in m or "resource_exhausted" in m or "quota" in m


def _call_embed(texts: List[str], task_type: str):
    client = get_client()
    return client.models.embed_content(
        model=settings.embedding_model,
        contents=texts,
        config=types.EmbedContentConfig(task_type=task_type),
    )


def embed_texts(texts: List[str], task_type: str = "RETRIEVAL_DOCUMENT") -> List[List[float]]:
    """
    Embed a batch of texts. Retries on temporary failures and raises
    EmbeddingError with a readable message if it still cannot succeed.
    task_type: "RETRIEVAL_DOCUMENT" for chunks being stored,
               "RETRIEVAL_QUERY" for the user's question at query time.
    """
    last_error = "unknown error"

    for attempt in range(1, MAX_ATTEMPTS + 1):
        future = _executor.submit(_call_embed, texts, task_type)
        try:
            result = future.result(timeout=REQUEST_TIMEOUT_SECONDS)
            return [e.values for e in result.embeddings]
        except FutureTimeout:
            last_error = (
                f"Gemini did not respond within {REQUEST_TIMEOUT_SECONDS} seconds "
                "(check your internet connection or try again shortly)."
            )
        except Exception as exc:
            last_error = str(exc)
            if _is_quota_error(last_error):
                last_error = (
                    "Gemini API rate limit or daily quota reached. "
                    "Wait a few minutes (or until the quota resets) and try again."
                )

        if attempt < MAX_ATTEMPTS:
            time.sleep(2 ** attempt)  # 2s, then 4s

    raise EmbeddingError(last_error)


def embed_query(query: str) -> List[float]:
    return embed_texts([query], task_type="RETRIEVAL_QUERY")[0]
