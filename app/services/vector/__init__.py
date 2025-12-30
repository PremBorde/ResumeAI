"""Vector storage (FAISS where available, numpy fallback on Windows)."""

from app.services.vector.faiss_store import VectorStore, VectorStoreError, l2_normalize

__all__ = ["VectorStore", "VectorStoreError", "l2_normalize"]

