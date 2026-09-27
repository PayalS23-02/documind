"""
ChromaDB vector store: stores chunk embeddings + metadata (document,
section, page) together, so retrieval returns everything citation needs
in a single call — no separate metadata lookup.
"""
from typing import List

import chromadb

from .chunking import Chunk
from .config import settings
from .embeddings import embed_texts, embed_query

_client = None
_collection = None


def get_collection():
    global _client, _collection
    if _collection is None:
        _client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
        _collection = _client.get_or_create_collection(
            name=settings.chroma_collection_name,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def add_chunks(chunks: List[Chunk], batch_size: int = 50) -> int:
    """Embed and store a list of chunks in ChromaDB. Returns count stored."""
    collection = get_collection()
    total = 0

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        texts = [c.text for c in batch]
        embeddings = embed_texts(texts, task_type="RETRIEVAL_DOCUMENT")

        ids = [f"{c.metadata.get('document', 'doc')}_p{c.page}_c{c.chunk_index}" for c in batch]
        metadatas = [
            {
                "document": c.metadata.get("document", "unknown"),
                "section": c.section,
                "page": c.page,
                "chunk_index": c.chunk_index,
            }
            for c in batch
        ]

        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )
        total += len(batch)

    return total


def query_similar(query: str, top_k: int = 5) -> dict:
    """Embed the query and return the top_k most similar chunks with metadata."""
    collection = get_collection()
    query_embedding = embed_query(query)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )
    return results


def reset_collection():
    """Delete and recreate the collection (useful for re-ingesting from scratch)."""
    global _client, _collection
    if _client is None:
        _client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
    try:
        _client.delete_collection(settings.chroma_collection_name)
    except Exception:
        pass
    _collection = None
    return get_collection()
