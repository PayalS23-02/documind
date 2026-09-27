"""
Central configuration for DocuMind.
All values are loaded from environment variables / .env file.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Gemini
    gemini_api_key: str = ""
    embedding_model: str = "gemini-embedding-001"
    generation_model: str = "gemini-2.5-flash"

    # Chunking
    chunk_size: int = 800          # characters per chunk (approx)
    chunk_overlap: int = 120       # overlap between consecutive chunks

    # Retrieval
    top_k: int = 5
    similarity_threshold: float = 0.55   # cosine similarity, 0-1; below this we say "not found"

    # ChromaDB
    chroma_persist_dir: str = "./chroma_db"
    chroma_collection_name: str = "documind_docs"


settings = Settings()
