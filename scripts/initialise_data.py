"""Deterministic initialization script for SQLite database and Chroma vector index."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from agri_navigator.config import get_settings  # noqa: E402
from agri_navigator.repository import SQLiteRepository  # noqa: E402
from agri_navigator.retrieval import SemanticRetriever, create_embedder  # noqa: E402


def main() -> int:
    """Initialize SQLite schema and deterministically rebuild the Chroma vector index."""
    settings = get_settings()
    sqlite_path = settings.resolved_path(settings.sqlite_path)
    chroma_dir = settings.resolved_path(settings.chroma_dir)
    raw_docs_dir = settings.resolved_path(settings.raw_docs_dir)

    repository = SQLiteRepository(
        db_path=sqlite_path,
        max_history_turns=settings.max_history_turns,
    )
    embedder = create_embedder(
        backend=settings.embedding_backend,
        model_name=settings.embedding_model,
    )
    retriever = SemanticRetriever(
        chroma_dir=chroma_dir,
        raw_docs_dir=raw_docs_dir,
        embedder=embedder,
        top_k=settings.top_k,
        min_similarity=settings.min_similarity,
    )
    indexed_count = retriever.rebuild_index()

    summary = {
        "status": "initialized",
        "project": "P35 - Agricultural Knowledge Navigator",
        "sqlite_path": str(sqlite_path),
        "sqlite_ok": repository.health_check(),
        "chroma_dir": str(chroma_dir),
        "chroma_ok": retriever.health_check(),
        "embedding_backend": settings.embedding_backend,
        "embedding_model": settings.embedding_model,
        "indexed_chunks": indexed_count,
    }
    print(json.dumps(summary, indent=2))
    return 0 if indexed_count > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
