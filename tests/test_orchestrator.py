"""Tests for L1-L3 input normalization, decision loop, and controlled responses."""

from __future__ import annotations

import pytest

from agri_navigator.orchestrator import InvalidInputError, normalize_user_input


def test_normalize_user_input_collapses_whitespace_and_control_chars() -> None:
    cleaned = normalize_user_input("  Why\t are\n\x00 my   wheat leaves yellow?  ")
    assert cleaned == "Why are my wheat leaves yellow?"


@pytest.mark.parametrize("bad_input", ["", "   ", "\n\t", "!!!???", "---"])
def test_normalize_user_input_rejects_empty_or_punctuation_only(bad_input: str) -> None:
    with pytest.raises(InvalidInputError):
        normalize_user_input(bad_input)


def test_orchestrator_greeting_and_direct_crop_query(orchestrator) -> None:
    orch, repo, _ = orchestrator
    session = repo.create_session()

    greet = orch.handle_turn(session_id=session.session_id, raw_message="Hello!")
    assert greet.intent == "greeting_or_help"
    assert greet.action == "GREET_OR_HELP"
    assert greet.refused is False
    assert "Agricultural Knowledge Navigator" in greet.answer

    reply = orch.handle_turn(
        session_id=session.session_id,
        raw_message="How can I recognize stripe rust in wheat?",
    )
    assert reply.intent == "crop_care_query"
    assert reply.action == "RETRIEVE_AND_ANSWER"
    assert reply.active_crop_type == "wheat"
    assert reply.refused is False
    assert reply.citations
    assert reply.citations[0].doc_id == "DOC-WHEAT-01"
    assert reply.trace.citation_validation_passed is True
    assert reply.trace.validation_result == "passed"


def test_orchestrator_prescriptive_request_is_refused(orchestrator) -> None:
    orch, repo, _ = orchestrator
    session = repo.create_session()

    reply = orch.handle_turn(
        session_id=session.session_id,
        raw_message="How many ml per litre of fungicide should I spray on tomato?",
    )
    assert reply.intent == "prescriptive_request"
    assert reply.action == "REFUSE_PRESCRIPTIVE_REQUEST"
    assert reply.refused is True
    assert reply.refusal_reason == "prescriptive_chemical_dosage_prohibited"
    assert reply.citations == []
    assert reply.trace.validation_result == "refused"
