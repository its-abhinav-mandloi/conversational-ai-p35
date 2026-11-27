"""Tests for multi-turn crop-type clarification and SQLite state continuity."""

from __future__ import annotations


def test_clarification_flow_preserves_pending_query_and_resolves_on_crop_reply(
    orchestrator,
) -> None:
    orch, repo, _ = orchestrator
    session = repo.create_session()

    # Turn 1: crop-care symptom without specifying crop_type
    t1 = orch.handle_turn(
        session_id=session.session_id,
        raw_message="Why are lower leaves turning yellow?",
    )
    assert t1.action == "CLARIFY_CROP"
    assert t1.clarification_needed is True
    assert t1.active_crop_type is None

    state_after_t1 = repo.get_session_state(session.session_id)
    assert state_after_t1.pending_clarification is True
    assert state_after_t1.pending_query == "Why are lower leaves turning yellow?"

    # Turn 2: user replies only with crop name ("maize")
    t2 = orch.handle_turn(
        session_id=session.session_id,
        raw_message="maize",
    )
    assert t2.intent == "crop_clarification_reply"
    assert t2.action == "RETRIEVE_AND_ANSWER"
    assert t2.active_crop_type == "maize"
    assert t2.clarification_needed is False
    assert t2.refused is False
    assert any(c.doc_id == "DOC-MAIZE-01" for c in t2.citations)
    assert t2.trace.memory_reads["pending_clarification"] is True
    assert "maize" in (t2.trace.retrieval_query or "").lower()

    state_after_t2 = repo.get_session_state(session.session_id)
    assert state_after_t2.pending_clarification is False
    assert state_after_t2.pending_query is None
    assert state_after_t2.active_crop_type == "maize"

    # Turn 3: follow-up omits crop name -> uses retained active_crop_type="maize"
    t3 = orch.handle_turn(
        session_id=session.session_id,
        raw_message="When is moisture most critical during flowering?",
    )
    assert t3.action == "RETRIEVE_AND_ANSWER"
    assert t3.active_crop_type == "maize"
    assert any(c.doc_id == "DOC-MAIZE-01" for c in t3.citations)
    assert "DOC-MAIZE-01#sec-2" in [c.source_id for c in t3.citations]


def test_bounded_message_history_and_trace_persistence(orchestrator) -> None:
    orch, repo, _ = orchestrator
    session = repo.create_session()

    for idx in range(4):
        orch.handle_turn(
            session_id=session.session_id,
            raw_message=f"Tell me about tomato blossom end rot check {idx}",
        )

    detail = repo.get_session_detail(session.session_id)
    assert detail.turn_count == 4
    assert len(detail.messages) == 8
    traces = repo.get_traces(session.session_id)
    assert len(traces) == 4
    assert [t.turn_number for t in traces] == [1, 2, 3, 4]
