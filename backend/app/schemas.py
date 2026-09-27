from typing import List, Optional

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)
    top_k: Optional[int] = None


class SourceInfo(BaseModel):
    document: str
    section: str
    page: int
    similarity: float


class QueryResponse(BaseModel):
    answer: str
    sources: List[SourceInfo]


class IngestResponse(BaseModel):
    documents_ingested: int
    chunks_stored: int


class HealthResponse(BaseModel):
    status: str
    collection_count: int
