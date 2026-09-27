"""
Custom, section-aware chunking.

Naive fixed-length splitters cut text mid-sentence and mid-clause, which
hurts retrieval quality on structured documents like handbooks (where a
whole rule/paragraph should stay together). This chunker:

1. Splits on section headers (all-caps lines, numbered headings, or lines
   ending without punctuation followed by a blank line) to keep sections
   distinct where possible.
2. Within a section, splits on paragraph boundaries first.
3. Packs paragraphs into chunks up to `chunk_size` characters.
4. Adds `chunk_overlap` characters of trailing context from the previous
   chunk to the start of the next, so a fact split across a chunk boundary
   is still retrievable from either side.
"""
import re
from dataclasses import dataclass, field
from typing import List


@dataclass
class Chunk:
    text: str
    section: str
    page: int
    chunk_index: int
    metadata: dict = field(default_factory=dict)


# Matches likely section headers: short lines, all-caps or Title-Case,
# not ending in typical sentence punctuation.
_HEADER_RE = re.compile(
    r"^(?:[0-9]+(?:\.[0-9]+)*\.?\s+)?[A-Z][A-Za-z0-9 ,&/'()-]{2,80}$"
)


def _looks_like_header(line: str) -> bool:
    line = line.strip()
    if not line or len(line) > 90:
        return False
    if line.endswith((".", ",", ";", ":")):
        return False
    if _HEADER_RE.match(line):
        # Reject lines that are mostly lowercase (likely a normal sentence)
        letters = [c for c in line if c.isalpha()]
        if not letters:
            return False
        upper_ratio = sum(1 for c in letters if c.isupper()) / len(letters)
        return upper_ratio > 0.3 or line.isupper()
    return False


def split_into_sections(page_text: str) -> List[tuple]:
    """Split a page's text into (section_title, body_text) tuples."""
    lines = page_text.split("\n")
    sections = []
    current_title = "General"
    current_lines: List[str] = []

    for line in lines:
        if _looks_like_header(line):
            if current_lines:
                sections.append((current_title, "\n".join(current_lines).strip()))
            current_title = line.strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        sections.append((current_title, "\n".join(current_lines).strip()))

    return [(title, body) for title, body in sections if body.strip()]


def _split_paragraphs(text: str) -> List[str]:
    paras = re.split(r"\n\s*\n", text)
    return [p.strip() for p in paras if p.strip()]


def chunk_page(
    page_text: str,
    page_number: int,
    chunk_size: int = 800,
    chunk_overlap: int = 120,
) -> List[Chunk]:
    """Chunk a single page's text into section-aware, overlapping chunks."""
    chunks: List[Chunk] = []
    sections = split_into_sections(page_text)

    for title, body in sections:
        paragraphs = _split_paragraphs(body)
        current = ""

        for para in paragraphs:
            candidate = f"{current}\n\n{para}".strip() if current else para

            if len(candidate) <= chunk_size:
                current = candidate
                continue

            # Current chunk is full — flush it, start new chunk with overlap
            if current:
                chunks.append(
                    Chunk(
                        text=current,
                        section=title,
                        page=page_number,
                        chunk_index=len(chunks),
                    )
                )
                overlap_text = current[-chunk_overlap:] if chunk_overlap else ""
                current = f"{overlap_text}\n\n{para}".strip()
            else:
                # Single paragraph longer than chunk_size — hard split it
                for i in range(0, len(para), chunk_size - chunk_overlap):
                    piece = para[i:i + chunk_size]
                    chunks.append(
                        Chunk(
                            text=piece,
                            section=title,
                            page=page_number,
                            chunk_index=len(chunks),
                        )
                    )
                current = ""

        if current:
            chunks.append(
                Chunk(
                    text=current,
                    section=title,
                    page=page_number,
                    chunk_index=len(chunks),
                )
            )

    return chunks


def chunk_document(
    pages: List[str],
    chunk_size: int = 800,
    chunk_overlap: int = 120,
) -> List[Chunk]:
    """Chunk a full document given as a list of page texts (1-indexed pages)."""
    all_chunks: List[Chunk] = []
    for page_number, page_text in enumerate(pages, start=1):
        page_chunks = chunk_page(page_text, page_number, chunk_size, chunk_overlap)
        for c in page_chunks:
            c.chunk_index = len(all_chunks)
            all_chunks.append(c)
    return all_chunks
