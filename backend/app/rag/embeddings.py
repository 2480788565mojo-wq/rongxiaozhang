from functools import lru_cache
from typing import Any

from app.config import get_settings


@lru_cache
def get_embedding_function() -> Any:
    # Import lazily: loading sentence-transformers also loads the local model,
    # which should only happen when the knowledge base is actually used.
    from chromadb.utils.embedding_functions import (
        SentenceTransformerEmbeddingFunction,
    )

    settings = get_settings()
    return SentenceTransformerEmbeddingFunction(
        model_name=settings.EMBEDDING_MODEL,
        device=settings.EMBEDDING_DEVICE,
        normalize_embeddings=True,
    )
