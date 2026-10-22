"""
DocuMind FastAPI backend.

Endpoints:
  POST /ingest   - upload PDF(s), chunk + embed + store in ChromaDB
  POST /query    - ask a question, get a grounded, cited answer
  GET  /health   - basic health/status check
"""
import logging
import shutil
import tempfile
from pathlib import Path
from typing import List

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .embeddings import EmbeddingError
from .generation import generate_answer
from .ingestion import ingest_pdf
from .retrieval import retrieve
from .schemas import HealthResponse, IngestResponse, QueryRequest, QueryResponse, SourceInfo
from .vectorstore import add_chunks, get_collection

logger = logging.getLogger("documind")

app = FastAPI(title="DocuMind API", version="1.0.0")


def _friendly_model_error(exc: Exception) -> str:
    """Turn a raw Gemini error into a short message the chat UI can show."""
    msg = str(exc)
    low = msg.lower()
    if "429" in low or "resource_exhausted" in low or "quota" in low:
        return (
            "Gemini API rate limit or daily quota reached. "
            "Wait a few minutes (or until the quota resets) and try again."
        )
    if "503" in low or "unavailable" in low or "high demand" in low:
        return "The Gemini model is busy right now. Please try again in a minute."
    if "404" in low or "not found" in low:
        return (
            "The configured Gemini model was not found. "
            "Check GENERATION_MODEL in your .env file."
        )
    return f"The AI model returned an error: {msg[:200]}"

# Allow the React dev server to call this API directly.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
def health():
    try:
        count = get_collection().count()
    except Exception:
        count = 0
    return HealthResponse(status="ok", collection_count=count)


@app.post("/ingest", response_model=IngestResponse)
async def ingest(files: List[UploadFile] = File(...)):
    """Upload one or more PDF files to ingest into the knowledge base."""
    total_chunks = 0

    with tempfile.TemporaryDirectory() as tmp_dir:
        for upload in files:
            if not upload.filename.lower().endswith(".pdf"):
                raise HTTPException(400, f"Only PDF files are supported: {upload.filename}")

            tmp_path = Path(tmp_dir) / upload.filename
            with open(tmp_path, "wb") as f:
                shutil.copyfileobj(upload.file, f)

            chunks = ingest_pdf(
                str(tmp_path),
                chunk_size=settings.chunk_size,
                chunk_overlap=settings.chunk_overlap,
            )
            if chunks:
                try:
                    total_chunks += add_chunks(chunks)
                except EmbeddingError as exc:
                    # Return a readable message to the UI instead of hanging
                    raise HTTPException(status_code=502, detail=str(exc))

    return IngestResponse(documents_ingested=len(files), chunks_stored=total_chunks)


@app.post("/query", response_model=QueryResponse)
def query(request: QueryRequest):
    """Ask a natural-language question and get a grounded, cited answer."""
    try:
        chunks = retrieve(request.question, top_k=request.top_k)
        result = generate_answer(request.question, chunks)
    except EmbeddingError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:
        # Without this, an unexpected error becomes a bare 500 with no CORS
        # header and the browser only shows "Failed to fetch".
        logger.exception("Query failed")
        raise HTTPException(status_code=502, detail=_friendly_model_error(exc))

    return QueryResponse(
        answer=result["answer"],
        sources=[SourceInfo(**s) for s in result["sources"]],
    )
