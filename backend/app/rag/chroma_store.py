from functools import lru_cache
from typing import Any

from app.config import get_settings
from app.rag.embeddings import get_embedding_function


@lru_cache
def get_chroma_client() -> Any:
    import chromadb
    from chromadb.config import Settings as ChromaSettings

    settings = get_settings()
    return chromadb.PersistentClient(
        path=settings.CHROMA_PERSIST_DIR,
        settings=ChromaSettings(anonymized_telemetry=False),
    )


@lru_cache
def get_finance_collection() -> Any:
    return get_chroma_client().get_or_create_collection(
        name="finance_tips",
        embedding_function=get_embedding_function(),
        metadata={"hnsw:space": "cosine"},
    )
