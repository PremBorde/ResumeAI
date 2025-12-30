from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import uuid4


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def sha256_text(text: str) -> str:
    return sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class LocalStorage:
    base_data_dir: Path
    base_embeddings_dir: Path

    @property
    def uploads_dir(self) -> Path:
        return self.base_data_dir / "uploads"

    @property
    def resumes_dir(self) -> Path:
        return self.base_data_dir / "resumes"

    @property
    def analyses_dir(self) -> Path:
        return self.base_data_dir / "analyses"

    @property
    def embedding_cache_dir(self) -> Path:
        return self.base_embeddings_dir / "cache"

    def init_dirs(self) -> None:
        for d in [
            self.base_data_dir,
            self.base_embeddings_dir,
            self.uploads_dir,
            self.resumes_dir,
            self.analyses_dir,
            self.embedding_cache_dir,
        ]:
            ensure_dir(d)

    def new_id(self, prefix: str) -> str:
        return f"{prefix}_{uuid4().hex}"

    def save_upload(self, filename: str, raw_bytes: bytes) -> Path:
        self.init_dirs()
        safe_name = os.path.basename(filename)
        target = self.uploads_dir / f"{uuid4().hex}_{safe_name}"
        target.write_bytes(raw_bytes)
        return target

    def save_resume_record(self, resume_id: str, record: dict[str, Any]) -> None:
        self.init_dirs()
        (self.resumes_dir / f"{resume_id}.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

    def load_resume_record(self, resume_id: str) -> dict[str, Any]:
        path = self.resumes_dir / f"{resume_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"Unknown resume_id: {resume_id}")
        return json.loads(path.read_text(encoding="utf-8"))

    def save_analysis_record(self, analysis_id: str, record: dict[str, Any]) -> None:
        self.init_dirs()
        (self.analyses_dir / f"{analysis_id}.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

    def load_analysis_record(self, analysis_id: str) -> dict[str, Any]:
        path = self.analyses_dir / f"{analysis_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"Unknown analysis_id: {analysis_id}")
        return json.loads(path.read_text(encoding="utf-8"))

    def embedding_cache_path(self, cache_key: str) -> Path:
        self.init_dirs()
        return self.embedding_cache_dir / f"{cache_key}.npy"


