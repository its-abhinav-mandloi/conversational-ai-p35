"""Shared pytest fixtures for isolated SQLite and Chroma test runs."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from agri_navigator.api import create_app
from agri_navigator.config import PROJECT_ROOT, Settings
from agri_navigator.grounded_answer import GroundedAnswerSynthesizer
from agri_navigator.orchestrator import AgriNavigatorOrchestrator
from agri_navigator.repository import SQLiteRepository
from agri_navigator.retrieval import SemanticRetriever, SentenceTransformerEmbedder


@pytest.fixture(scope="session")
def shared_embedder() -> SentenceTransformerEmbedder:
    """Load the local SentenceTransformer model once per pytest session."""
    return SentenceTransformerEmbedder("sentence-transformers/all-MiniLM-L6-v2")


@pytest.fixture()
def test_settings(tmp_path: Path) -> Settings:
    """Create isolated per-test settings pointing to temporary SQLite and Chroma dirs."""
    return Settings(
        llm_mode="local-only",
        openai_api_key="",
        embedding_backend="sentence-transformers",
        embedding_model="sentence-transformers/all-MiniLM-L6-v2",
        chroma_dir=tmp_path / "chroma_db",
        sqlite_path=tmp_path / "agri_test.db",
        raw_docs_dir=PROJECT_ROOT / "data" / "raw",
        top_k=4,
        min_similarity=0.32,
        max_history_turns=6,
    )


@pytest.fixture()
def orchestrator(
    test_settings: Settings,
    shared_embedder: SentenceTransformerEmbedder,
) -> tuple[AgriNavigatorOrchestrator, SQLiteRepository, SemanticRetriever]:
    """Build an isolated orchestrator stack backed by real Chroma + SQLite."""
    repo = SQLiteRepository(
        db_path=test_settings.sqlite_path,
        max_history_turns=test_settings.max_history_turns,
    )
    retriever = SemanticRetriever(
        chroma_dir=test_settings.chroma_dir,
        raw_docs_dir=test_settings.raw_docs_dir,
        embedder=shared_embedder,
        top_k=test_settings.top_k,
        min_similarity=test_settings.min_similarity,
    )
    retriever.rebuild_index()
    synthesizer = GroundedAnswerSynthesizer(test_settings)
    orch = AgriNavigatorOrchestrator(
        settings=test_settings,
        repository=repo,
        retriever=retriever,
        synthesizer=synthesizer,
    )
    return orch, repo, retriever


@pytest.fixture()
def api_client(test_settings: Settings) -> TestClient:
    """FastAPI TestClient backed by isolated temporary storage."""
    app = create_app(test_settings)
    return TestClient(app)
