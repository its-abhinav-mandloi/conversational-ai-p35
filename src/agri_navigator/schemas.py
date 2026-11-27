"""Typed Pydantic schemas for API requests, responses, citations, and turn traces."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

AllowedIntent = Literal[
    "crop_care_query",
    "crop_clarification_reply",
    "general_soil_ipm_query",
    "prescriptive_request",
    "greeting_or_help",
    "out_of_scope",
    "invalid_input",
]

AllowedAction = Literal[
    "CLARIFY_CROP",
    "RETRIEVE_AND_ANSWER",
    "REFUSE_INSUFFICIENT_EVIDENCE",
    "REFUSE_PRESCRIPTIVE_REQUEST",
    "GREET_OR_HELP",
    "REJECT_INVALID_INPUT",
]


def utc_now_iso() -> str:
    """Return current UTC timestamp in ISO-8601 format."""
    return datetime.now(timezone.utc).isoformat()


class SessionCreateResponse(BaseModel):
    """Response returned when creating a new conversation session."""

    session_id: str
    created_at: str
    active_crop_type: str | None = None
    pending_clarification: bool = False
    turn_count: int = 0


class MessageRecord(BaseModel):
    """Persisted message entry inside a session."""

    turn_number: int
    role: Literal["user", "assistant"]
    content: str
    created_at: str


class SessionDetailResponse(BaseModel):
    """Detailed view of a persisted session and bounded message history."""

    session_id: str
    created_at: str
    updated_at: str
    active_crop_type: str | None = None
    pending_clarification: bool = False
    pending_query: str | None = None
    turn_count: int
    messages: list[MessageRecord] = Field(default_factory=list)


class ChatRequest(BaseModel):
    """Incoming user turn payload."""

    session_id: str = Field(..., min_length=1, max_length=128)
    message: str = Field(..., max_length=2000)
    llm_mode_override: Literal["local-only", "openai", "ollama"] | None = None


class Citation(BaseModel):
    """Grounded source citation linked to a retrieved document chunk."""

    source_id: str
    doc_id: str
    title: str
    crop_type: str
    section: str
    similarity_score: float = Field(..., ge=0.0, le=1.0)
    excerpt: str


class RetrievalCandidate(BaseModel):
    """Candidate chunk scored during semantic retrieval."""

    source_id: str
    doc_id: str
    crop_type: str
    section: str
    score: float = Field(..., ge=0.0, le=1.0)
    accepted: bool


class TurnTrace(BaseModel):
    """Structured JSON trace emitted for every orchestrator turn."""

    trace_id: str
    session_id: str
    turn_number: int
    normalized_input: str
    intent: AllowedIntent
    selected_action: AllowedAction
    active_crop_before: str | None = None
    active_crop_after: str | None = None
    clarification_pending_before: bool = False
    clarification_pending_after: bool = False
    memory_reads: dict[str, Any] = Field(default_factory=dict)
    memory_writes: dict[str, Any] = Field(default_factory=dict)
    retrieval_query: str | None = None
    retrieval_crop_filter: str | None = None
    retrieval_candidates: list[RetrievalCandidate] = Field(default_factory=list)
    chosen_sources: list[str] = Field(default_factory=list)
    citation_validation_passed: bool = True
    validation_result: Literal["passed", "refused", "clarification_requested", "error"]
    llm_mode_requested: str = "local-only"
    llm_mode_used: str = "local-only"
    latency_ms: float = Field(..., ge=0.0)
    error_class: str | None = None
    timestamp: str = Field(default_factory=utc_now_iso)


class ChatResponse(BaseModel):
    """Controlled output returned to callers for each conversational turn."""

    session_id: str
    turn_number: int
    intent: AllowedIntent
    action: AllowedAction
    active_crop_type: str | None = None
    clarification_needed: bool = False
    answer: str
    educational_disclaimer: str
    citations: list[Citation] = Field(default_factory=list)
    confidence: float = Field(..., ge=0.0, le=1.0)
    refused: bool = False
    refusal_reason: str | None = None
    warnings: list[str] = Field(default_factory=list)
    trace: TurnTrace


class HealthResponse(BaseModel):
    """Service readiness and dependency status."""

    status: Literal["ok", "degraded"]
    project: str
    llm_mode: str
    embedding_backend: str
    embedding_model: str
    indexed_chunks: int
    sqlite_ok: bool
    chroma_ok: bool
    supported_crops: list[str]
