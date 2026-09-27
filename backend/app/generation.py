"""
Grounded answer generation: assemble retrieved chunks + question into a
prompt and call gemini-2.5-flash, constrained to answer only from the
provided context.
"""
from typing import List

from google.genai import types

from .config import settings
from .embeddings import get_client
from .retrieval import RetrievedChunk

SYSTEM_PROMPT = """You are DocuMind, an assistant that answers student questions \
using ONLY the academic document excerpts provided as context below.

Rules:
- Answer using only the information in the context. Do not use outside knowledge.
- If the context does not contain enough information to answer, say so clearly \
instead of guessing.
- Be concise and direct — students want the specific rule/number/date, not a \
summary of the whole document.
- Do not fabricate document names, sections, or page numbers.
"""


def _build_context(chunks: List[RetrievedChunk]) -> str:
    parts = []
    for i, c in enumerate(chunks, start=1):
        parts.append(
            f"[Source {i}: {c.document}, section \"{c.section}\", page {c.page}]\n{c.text}"
        )
    return "\n\n".join(parts)


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

    client = get_client()
    response = client.models.generate_content(
        model=settings.generation_model,
        contents=prompt,
    )

    sources = [
        {
            "document": c.document,
            "section": c.section,
            "page": c.page,
            "similarity": c.similarity,
        }
        for c in chunks
    ]

    return {"answer": response.text.strip(), "sources": sources}
