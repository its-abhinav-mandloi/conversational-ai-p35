"""Negative and edge-case tests: invalid input, unknown session, no-hit retrieval, LLM fallback."""

from __future__ import annotations

from agri_navigator.config import PROJECT_ROOT, Settings
from agri_navigator.grounded_answer import GroundedAnswerSynthesizer
from agri_navigator.orchestrator import AgriNavigatorOrchestrator
from agri_navigator.repository import SQLiteRepository
from agri_navigator.retrieval import SemanticRetriever


def test_api_rejects_empty_input_and_unknown_session(api_client) -> None:
    session_id = api_client.post("/sessions").json()["session_id"]

    empty_resp = api_client.post("/chat", json={"session_id": session_id, "message": "   "})
    assert empty_resp.status_code == 400

    punct_resp = api_client.post("/chat", json={"session_id": session_id, "message": "???"})
    assert punct_resp.status_code == 400

    unknown_chat = api_client.post(
        "/chat",
        json={"session_id": "sess-unknown-123", "message": "Tell me about wheat rust"},
    )
    assert unknown_chat.status_code == 404

    unknown_get = api_client.get("/sessions/sess-unknown-123")
    assert unknown_get.status_code == 404


def test_insufficient_retrieval_evidence_triggers_refusal(
    tmp_path,
    shared_embedder,
) -> None:
    # High min_similarity simulates zero retrieval hits passing threshold for a vague crop query.
    strict_settings = Settings(
        llm_mode="local-only",
        chroma_dir=tmp_path / "chroma_strict",
        sqlite_path=tmp_path / "strict.db",
        raw_docs_dir=PROJECT_ROOT / "data" / "raw",
        top_k=4,
        min_similarity=0.98,
    )
    repo = SQLiteRepository(strict_settings.sqlite_path)
    retriever = SemanticRetriever(
        chroma_dir=strict_settings.chroma_dir,
        raw_docs_dir=strict_settings.raw_docs_dir,
        embedder=shared_embedder,
        top_k=4,
        min_similarity=0.98,
    )
    retriever.rebuild_index()
    orch = AgriNavigatorOrchestrator(
        settings=strict_settings,
        repository=repo,
        retriever=retriever,
        synthesizer=GroundedAnswerSynthesizer(strict_settings),
    )
    session = repo.create_session()
    resp = orch.handle_turn(
        session_id=session.session_id,
        raw_message="Tell me about wheat spaceflight hydroponics in orbit",
    )
    assert resp.action == "REFUSE_INSUFFICIENT_EVIDENCE"
    assert resp.refused is True
    assert resp.refusal_reason == "insufficient_retrieval_evidence"
    assert resp.citations == []
    assert resp.trace.error_class == "NoRetrievalEvidenceError"


def test_unavailable_optional_llm_falls_back_safely(api_client) -> None:
    session_id = api_client.post("/sessions").json()["session_id"]

    resp = api_client.post(
        "/chat",
        json={
            "session_id": session_id,
            "message": "Why is earthing up done in potato?",
            "llm_mode_override": "openai",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["refused"] is False
    assert body["citations"]
    assert body["trace"]["llm_mode_requested"] == "openai"
    assert body["trace"]["llm_mode_used"] == "local-only"
    assert body["trace"]["error_class"] == "ProviderUnavailableError"
    assert any("unavailable" in w.lower() for w in body["warnings"])


def test_out_of_scope_and_unsupported_crop_refusals(api_client) -> None:
    session_id = api_client.post("/sessions").json()["session_id"]

    unsupported = api_client.post(
        "/chat",
        json={"session_id": session_id, "message": "How do I prune mango trees?"},
    )
    assert unsupported.status_code == 200
    u_body = unsupported.json()
    assert u_body["refused"] is True
    assert u_body["refusal_reason"] == "unsupported_crop:mango"
    assert u_body["citations"] == []

    offtopic = api_client.post(
        "/chat",
        json={"session_id": session_id, "message": "Write a SQL query to drop tables."},
    )
    assert offtopic.status_code == 200
    o_body = offtopic.json()
    assert o_body["refused"] is True
    assert o_body["action"] == "REFUSE_INSUFFICIENT_EVIDENCE"
    assert o_body["citations"] == []
