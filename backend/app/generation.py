"""
Grounded answer generation: assemble retrieved chunks + question into a
prompt and ask Gemini, constrained to answer only from the provided context.

If the main model is overloaded (503 "busy"), the call is retried and then
tried on a backup model, so a temporary spike does not break the chat.
"""
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from typing import List

from .config import settings
from .embeddings import get_client
from .retrieval import RetrievedChunk

SYSTEM_PROMPT = """You are DocuMind, an assistant that answers student questions \
using ONLY the academic document excerpts provided as context below.

Rules:
- Answer using only the information in the context. Do not use outside knowledge.
- If the context does not contain enough information to answer, say so clearly \
instead of guessing.
- Be concise and direct - students want the specific rule/number/date, not a \
summary of the whole document.
- Do not fabricate document names, sections, or page numbers.
"""

BACKUP_MODELS = ["gemini-3.8-flash"]   # tried if the main model keeps failing
REQUEST_TIMEOUT_SECONDS = 25
ROUNDS = 3

_executor = ThreadPoolExecutor(max_workers=2)


def _build_context(chunks: List[RetrievedChunk]) -> str:
    parts = []
    for i, c in enumerate(chunks, start=1):
        parts.append(
            f"[Source {i}: {c.document}, section \"{c.section}\", page {c.page}]\n{c.text}"
        )
    return "\n\n".join(parts)


def _is_temporary(message: str) -> bool:
    m = message.lower()
    return "503" in m or "unavailable" in m or "high demand" in m or "overloaded" in m


def _call_model(model: str, prompt: str):
    return get_client().models.generate_content(model=model, contents=prompt)


def _generate_with_fallback(prompt: str) -> str:
    models = [settings.generation_model] + [
        m for m in BACKUP_MODELS if m != settings.generation_model
    ]
    last_exc = None

    for round_no in range(1, ROUNDS + 1):
        for model in models:
            future = _executor.submit(_call_model, model, prompt)
            try:
                return future.result(timeout=REQUEST_TIMEOUT_SECONDS).text.strip()
            except FutureTimeout:
                last_exc = Exception(f"503 UNAVAILABLE: {model} did not respond in time")
            except Exception as exc:
                if not _is_temporary(str(exc)):
                    raise          # quota, bad model name, etc: do not hide it
                last_exc = exc
        if round_no < ROUNDS:
            time.sleep(2 * round_no)   # 2s, then 4s

    raise last_exc


def generate_answer(question: str, chunks: List[RetrievedChunk]) -> dict:
    """
    Generate a grounded answer. Returns a dict with the answer text and
    the list of sources actually available to the model (for citation
    display in the UI).
    """
    if not chunks:
        return {
            "answer": (
                "I couldn't find anything in the available documents that "
                "answers this question confidently. Try rephrasing, or this "
                "may not be covered in the indexed documents."
            ),
            "sources": [],
        }

    context = _build_context(chunks)
    prompt = f"{SYSTEM_PROMPT}\n\nContext:\n{context}\n\nQuestion: {question}\n\nAnswer:"

    answer = _generate_with_fallback(prompt)

    sources = [
        {
            "document": c.document,
            "section": c.section,
            "page": c.page,
            "similarity": c.similarity,
        }
        for c in chunks
    ]

    return {"answer": answer, "sources": sources}
