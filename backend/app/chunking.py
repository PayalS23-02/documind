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


# Table handling. PDF extraction spreads each table row over several lines,
# e.g. "3 CSA3007 DEEP LEARNING Lecture and" / "Tutorial ,practical" /
# "hours only" / "1.0 2 1 1 0 4.0". We glue those back into one line so the
# course code, title and credits always stay together in the same chunk.
_ROW_START_RE = re.compile(r"^\d{1,3}\s+[A-Z]{2,4}\d{3,4}\b")
_ROW_END_RE = re.compile(r"\d\.\d\s+\d+\s+\d+\s+\d+\s+\d+\s+\d\.\d\s*$")
_TABLE_HEADER_START_RE = re.compile(r"^sl\.?\s*no\b", re.IGNORECASE)
_NOISE_RE = re.compile(r"^\s*Report On\b", re.IGNORECASE)


def _join_table_rows(text: str) -> str:
    """Re-join multi-line table rows and column headers into single lines."""
    out: List[str] = []
    row = None   # table row being assembled
    hdr = None   # column-header line being assembled

    for line in text.split("\n"):
        s = line.strip()
        if not s:
            if row is None and hdr is None:
                out.append("")
            continue
        if _NOISE_RE.match(s):          # page footer such as "Report On : ..."
            continue

        if hdr is not None:
            hdr += " " + s
            if s.endswith("Credits"):
                out.append("Columns: " + hdr.replace(" Ver sio n ", " Version "))
                hdr = None
            continue

        if row is not None:
            if _ROW_START_RE.match(s):  # previous row never finished; keep it
                out.append(row)
                row = None
            else:
                row += " " + s
                if _ROW_END_RE.search(row):
                    out.append(row)
                    row = None
                continue

        if _TABLE_HEADER_START_RE.match(s):
            hdr = s
            if s.endswith("Credits"):
                out.append("Columns: " + hdr)
                hdr = None
            continue

        if _ROW_START_RE.match(s):
            if _ROW_END_RE.search(s):
                out.append(s)
            else:
                row = s
            continue

        out.append(line)

    if row:
        out.append(row)
    if hdr:
        out.append(hdr)
    return "\n".join(out)


def _looks_like_header(line: str) -> bool:
    line = line.strip()
    if not line or len(line) > 90:
        return False
    # Table rows and column headings are data, never section titles.
    if _ROW_START_RE.match(line) or _TABLE_HEADER_START_RE.match(line) or line.startswith("Columns:"):
        return False
    if line.endswith((".", ",", ";", ":")):
        return False
    if _HEADER_RE.match(line):
        letters = [c for c in line if c.isalpha()]
        if not letters:
            return False
        upper_ratio = sum(1 for c in letters if c.isupper()) / len(letters)
        if upper_ratio > 0.3 or line.isupper():
            return True
        # Title Case check: most words start with a capital letter, e.g.
        # "Programme Core", "University Elective - Open Electives". This
        # catches table/section headers that ALL-CAPS detection misses.
        words = [w for w in re.split(r"[\s\-]+", line) if w and w.isalpha()]
        if len(words) >= 2:
            capitalized = sum(1 for w in words if w[0].isupper())
            if capitalized / len(words) >= 0.8:
                return True
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
    default_cols: str = "",
) -> List[Chunk]:
    """Chunk a single page's text into section-aware, overlapping chunks."""
    chunks: List[Chunk] = []
    sections = split_into_sections(_join_table_rows(page_text))

    for title, body in sections:
        # If the section starts with table column labels, keep them aside and
        # attach them to every chunk so numbers like "1.0 2 1 1 0 4.0" are
        # never shown without their column names.
        col_header = ""
        first, _, rest = body.partition("\n")
        if first.startswith("Columns:"):
            col_header, body = first, rest.strip()
            if not body:
                continue
        elif default_cols and _ROW_START_RE.match(body.lstrip()):
            # Table continued from the previous page: reuse its column labels.
            col_header = default_cols

        section_start = len(chunks)
        paragraphs = _split_paragraphs(body)
        current = ""

        for para in paragraphs:
            candidate = f"{current}\n\n{para}".strip() if current else para

            if len(candidate) <= chunk_size:
                current = candidate
                continue

            # Current chunk is full - flush it, start new chunk with overlap
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
                # Single paragraph longer than chunk_size. This happens
                # with table-like content that has no blank lines between
                # rows (a whole table becomes one "paragraph"). Splitting
                # by raw character count here would cut a row in half -
                # instead, split on line boundaries and pack whole lines,
                # so no table row (or sentence, for prose) is ever broken
                # mid-way through.
                lines = para.split("\n")
                line_chunk = ""
                for line in lines:
                    candidate_line = f"{line_chunk}\n{line}".strip() if line_chunk else line

                    if len(candidate_line) <= chunk_size:
                        line_chunk = candidate_line
                        continue

                    if line_chunk:
                        chunks.append(
                            Chunk(
                                text=line_chunk,
                                section=title,
                                page=page_number,
                                chunk_index=len(chunks),
                            )
                        )
                        overlap_text = line_chunk[-chunk_overlap:] if chunk_overlap else ""
                        line_chunk = f"{overlap_text}\n{line}".strip()
                    else:
                        # A single line itself exceeds chunk_size (rare -
                        # e.g. an extremely long unbroken sentence). Only
                        # here do we fall back to a raw character split,
                        # since there's no smaller natural boundary left.
                        for i in range(0, len(line), chunk_size - chunk_overlap):
                            piece = line[i:i + chunk_size]
                            chunks.append(
                                Chunk(
                                    text=piece,
                                    section=title,
                                    page=page_number,
                                    chunk_index=len(chunks),
                                )
                            )
                        line_chunk = ""

                if line_chunk:
                    chunks.append(
                        Chunk(
                            text=line_chunk,
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

        # Put the section name and column labels into the chunk text itself,
        # so both the search and the model see what each chunk is about.
        for c in chunks[section_start:]:
            prefix = [] if title == "General" else [title]
            if col_header:
                prefix.append(col_header)
            c.text = "\n".join(prefix + [c.text])

    return chunks


def chunk_document(
    pages: List[str],
    chunk_size: int = 800,
    chunk_overlap: int = 120,
) -> List[Chunk]:
    """Chunk a full document given as a list of page texts (1-indexed pages)."""
    all_chunks: List[Chunk] = []
    last_cols = ""
    for page_number, page_text in enumerate(pages, start=1):
        page_chunks = chunk_page(
            page_text, page_number, chunk_size, chunk_overlap, default_cols=last_cols
        )
        for line in _join_table_rows(page_text).split("\n"):
            if line.startswith("Columns:"):
                last_cols = line
        for c in page_chunks:
            c.chunk_index = len(all_chunks)
            all_chunks.append(c)
    return all_chunks
