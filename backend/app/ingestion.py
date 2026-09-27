"""
Document ingestion: parse PDFs into per-page text, ready for chunking.
"""
from pathlib import Path
from typing import List

from pypdf import PdfReader

from .chunking import Chunk, chunk_document


def extract_pages(pdf_path: str) -> List[str]:
    """Extract text from every page of a PDF as a list of strings."""
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
    """
    Full ingestion pipeline for one PDF: extract text per page, then
    chunk section-aware. Attaches the source document name to each chunk's
    metadata (used later for citation).
    """
    doc_name = Path(pdf_path).stem
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
    """Ingest every PDF in a directory."""
    all_chunks: List[Chunk] = []
    for pdf_file in sorted(Path(directory).glob("*.pdf")):
        chunks = ingest_pdf(str(pdf_file), chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        all_chunks.extend(chunks)
    return all_chunks
