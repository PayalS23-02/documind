"""
Quick CLI to test the pipeline without spinning up FastAPI/React.

Usage:
    python cli.py ingest sample_docs/sample_handbook.pdf
    python cli.py ask "What's the minimum attendance for a backlog course?"
"""
import sys

from app.config import settings
from app.generation import generate_answer
from app.ingestion import ingest_pdf
from app.retrieval import retrieve
from app.vectorstore import add_chunks


def cmd_ingest(pdf_path: str):
    chunks = ingest_pdf(pdf_path, chunk_size=settings.chunk_size, chunk_overlap=settings.chunk_overlap)
    print(f"Parsed {len(chunks)} chunks from {pdf_path}")
    stored = add_chunks(chunks)
    print(f"Stored {stored} chunks in ChromaDB at {settings.chroma_persist_dir}")


def cmd_ask(question: str):
    chunks = retrieve(question)
    print(f"Retrieved {len(chunks)} chunks above similarity threshold {settings.similarity_threshold}")
    for c in chunks:
        print(f"  - [{c.document} | {c.section} | p.{c.page}] similarity={c.similarity}")
    print()

    result = generate_answer(question, chunks)
    print("ANSWER:")
    print(result["answer"])
    print()
    print("SOURCES:")
    for s in result["sources"]:
        print(f"  - {s['document']}, section \"{s['section']}\", page {s['page']} (similarity {s['similarity']})")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    command, arg = sys.argv[1], sys.argv[2]

    if command == "ingest":
        cmd_ingest(arg)
    elif command == "ask":
        cmd_ask(arg)
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)
