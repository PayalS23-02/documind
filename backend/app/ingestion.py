"""
Document ingestion: parse PDFs into per-page text, ready for chunking.
"""
import re
from pathlib import Path
from typing import List

from pypdf import PdfReader

from .chunking import Chunk, chunk_document

_PII_PATTERNS = [
    r"\d{2}[A-Z]{2,5}\d{4,7}",
    r"\d{4}-\d{2}-\d{2}",
    r"\d{2}-\d{2}-\d{2}",
    r"(?<![A-Za-z])Student(?![A-Za-z])",
]


def sanitize_document_name(raw_name: str) -> str:
    name = raw_name
    for pattern in _PII_PATTERNS:
        name = re.sub(pattern, "", name, flags=re.IGNORECASE)
    name = re.sub(r"[_\-]{2,}", "_", name)
    name = name.strip("_- ")
    name = re.sub(r"\s{2,}", " ", name)
    return name or raw_name


def extract_pages(pdf_path: str) -> List[str]:
    reader = PdfReader(pdf_path)
    pages = []
    for page in reader.pages:
        text = page.extract_text() or ""
        pages.append(text)
    return pages


def ingest_pdf(
    pdf_path: str,
    chunk_size: int = 800,
    chunk_overlap: int = 120,
) -> List[Chunk]:
    doc_name = sanitize_document_name(Path(pdf_path).stem)
    pages = extract_pages(pdf_path)
    chunks = chunk_document(pages, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    for c in chunks:
        c.metadata["document"] = doc_name
        c.metadata["source_path"] = pdf_path
    return chunks


def ingest_directory(
    directory: str,
    chunk_size: int = 800,
    chunk_overlap: int = 120,
) -> List[Chunk]:
    all_chunks: List[Chunk] = []
    for pdf_file in sorted(Path(directory).glob("*.pdf")):
        chunks = ingest_pdf(str(pdf_file), chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        all_chunks.extend(chunks)
    return all_chunks
