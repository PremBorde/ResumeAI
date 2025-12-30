from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np


class VectorStoreError(RuntimeError):
    pass


def l2_normalize(vec: np.ndarray) -> np.ndarray:
    v = vec.astype(np.float32)
    n = np.linalg.norm(v)
    if n == 0:
        return v
    return v / n


@dataclass
class VectorStore:
    """
    Vector store abstraction.

    - Uses FAISS if installed (typical on Linux).
    - Falls back to a numpy matrix search on Windows (still production-usable for small/medium scale).
    """

    dir_path: Path
    dim: int

    def __post_init__(self) -> None:
        self.dir_path.mkdir(parents=True, exist_ok=True)
        self._meta_path = self.dir_path / "meta.json"
        self._vecs_path = self.dir_path / "vectors.npy"

        self._ids: list[str] = []
        self._vecs: np.ndarray | None = None

        self._faiss = None
        self._index = None
        try:
            import faiss  # type: ignore

            self._faiss = faiss
        except Exception:
            self._faiss = None

        self._load()

    def _load(self) -> None:
        if self._meta_path.exists():
            meta = json.loads(self._meta_path.read_text(encoding="utf-8"))
            self._ids = list(meta.get("ids", []))
        if self._vecs_path.exists():
            self._vecs = np.load(str(self._vecs_path)).astype(np.float32)

        if self._faiss is not None and self._vecs is not None and len(self._ids) > 0:
            idx = self._faiss.IndexFlatIP(self.dim)
            idx.add(self._vecs)
            self._index = idx

    def _persist(self) -> None:
        self._meta_path.write_text(json.dumps({"ids": self._ids}, indent=2), encoding="utf-8")
        if self._vecs is not None:
            np.save(str(self._vecs_path), self._vecs)

    def add(self, item_id: str, vec: np.ndarray) -> None:
        v = l2_normalize(vec).reshape(1, -1)
        if v.shape[1] != self.dim:
            raise VectorStoreError(f"Vector dim mismatch: expected {self.dim}, got {v.shape[1]}")

        if item_id in self._ids:
            # overwrite by rebuilding (keeps logic simple and deterministic)
            idx = self._ids.index(item_id)
            if self._vecs is None:
                raise VectorStoreError("Internal error: ids exist but vectors missing.")
            self._vecs[idx] = v[0]
        else:
            self._ids.append(item_id)
            if self._vecs is None:
                self._vecs = v
            else:
                self._vecs = np.vstack([self._vecs, v])

        if self._faiss is not None:
            idx = self._faiss.IndexFlatIP(self.dim)
            idx.add(self._vecs)
            self._index = idx

        self._persist()

    def search(self, query_vec: np.ndarray, top_k: int = 5) -> list[dict[str, Any]]:
        if self._vecs is None or len(self._ids) == 0:
            return []

        q = l2_normalize(query_vec).reshape(1, -1)
        if q.shape[1] != self.dim:
            raise VectorStoreError(f"Vector dim mismatch: expected {self.dim}, got {q.shape[1]}")

        if self._index is not None:
            scores, idxs = self._index.search(q, top_k)
            results: list[dict[str, Any]] = []
            for score, i in zip(scores[0].tolist(), idxs[0].tolist()):
                if i < 0:
                    continue
                results.append({"id": self._ids[i], "score": float(score)})
            return results

        # numpy fallback: inner product on normalized vectors == cosine similarity
        sims = (self._vecs @ q[0]).astype(np.float32)
        top = np.argsort(-sims)[:top_k]
        return [{"id": self._ids[i], "score": float(sims[i])} for i in top.tolist()]






