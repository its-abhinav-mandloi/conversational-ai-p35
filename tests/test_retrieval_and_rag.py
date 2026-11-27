"""Tests for L6 semantic retrieval, chunking, thresholding, and L7-L8 citation validation."""

from __future__ import annotations

from agri_navigator.config import PROJECT_ROOT
from agri_navigator.grounded_answer import validate_citations
from agri_navigator.retrieval import RetrievedChunk, load_corpus_chunks


def test_deterministic_chunking_produces_stable_ids() -> None:
    chunks_first = load_corpus_chunks(PROJECT_ROOT / "data" / "raw")
    chunks_second = load_corpus_chunks(PROJECT_ROOT / "data" / "raw")
    assert len(chunks_first) == 24
    assert [c.chunk_id for c in chunks_first] == [c.chunk_id for c in chunks_second]
    assert "DOC-WHEAT-01#sec-1" in [c.chunk_id for c in chunks_first]
    assert "DOC-SOIL-01#sec-2" in [c.chunk_id for c in chunks_first]


def test_semantic_retrieval_returns_relevant_section_with_crop_filter(orchestrator) -> None:
    _, _, retriever = orchestrator
    accepted, candidates = retriever.search(
        "blossom end rot sunken dark patch on fruit",
        crop_filter="tomato",
    )
    assert candidates
    assert accepted
    assert accepted[0].chunk_id == "DOC-TOMATO-01#sec-2"
    assert accepted[0].similarity_score >= 0.32


def test_semantic_retrieval_score_threshold_rejects_unrelated_query(orchestrator) -> None:
    _, _, retriever = orchestrator
    accepted, candidates = retriever.search(
        "quantum entanglement superconductivity equations",
        crop_filter=None,
        min_similarity=0.35,
    )
    assert candidates
    assert accepted == []
    assert all(not c.accepted for c in candidates)


def test_citation_validator_rejects_missing_or_hallucinated_citations() -> None:
    allowed = [
        RetrievedChunk(
            chunk_id="DOC-RICE-01#sec-1",
            doc_id="DOC-RICE-01",
            title="Rice Paddy Management Educational Primer",
            crop_type="rice",
            section="Section 1: Water Management and Alternate Wetting and Drying",
            text="Alternate Wetting and Drying saves water.",
            similarity_score=0.71,
            accepted=True,
        )
    ]
    assert validate_citations("AWD reduces water use [DOC-RICE-01#sec-1].", allowed) is True
    assert validate_citations("AWD reduces water use without a citation.", allowed) is False
    assert (
        validate_citations("Invented claim [DOC-FAKE-99#sec-1] and [DOC-RICE-01#sec-1].", allowed)
        is False
    )
