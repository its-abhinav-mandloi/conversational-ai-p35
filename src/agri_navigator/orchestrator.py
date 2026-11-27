"""L1-L3 Orchestrator: input normalization, goal/action loop, state continuity, and tracing."""

from __future__ import annotations

import logging
import re
import time
import uuid

from agri_navigator.config import Settings
from agri_navigator.domain_data import (
    EDUCATIONAL_DISCLAIMER,
    SUPPORTED_CROPS,
    extract_supported_crop,
    extract_unsupported_crop,
    is_agricultural_query,
    is_general_soil_ipm_query,
    is_greeting_or_help,
    is_prescriptive_request,
)
from agri_navigator.grounded_answer import GroundedAnswerSynthesizer
from agri_navigator.repository import SQLiteRepository
from agri_navigator.retrieval import SemanticRetriever
from agri_navigator.schemas import (
    AllowedAction,
    AllowedIntent,
    ChatResponse,
    TurnTrace,
    utc_now_iso,
)

logger = logging.getLogger("agri_navigator.trace")


class InvalidInputError(ValueError):
    """Raised when normalized user input is empty, control-char-only, or malformed."""


def normalize_user_input(raw_message: str) -> str:
    """Normalize whitespace and control characters, rejecting empty/non-informative input."""
    cleaned = re.sub(r"[\x00-\x1f\x7f]+", " ", raw_message)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned or not re.search(r"[a-zA-Z0-9]", cleaned):
        raise InvalidInputError(
            "Input message must contain non-empty alphanumeric text after normalization."
        )
    if len(cleaned) > 1000:
        raise InvalidInputError("Input message exceeds the 1000-character limit.")
    return cleaned


class AgriNavigatorOrchestrator:
    """Explicit goal/action dialogue orchestrator for P35 Agricultural Knowledge Navigator."""

    def __init__(
        self,
        *,
        settings: Settings,
        repository: SQLiteRepository,
        retriever: SemanticRetriever,
        synthesizer: GroundedAnswerSynthesizer,
    ) -> None:
        self.settings = settings
        self.repository = repository
        self.retriever = retriever
        self.synthesizer = synthesizer

    def handle_turn(
        self,
        *,
        session_id: str,
        raw_message: str,
        llm_mode_override: str | None = None,
    ) -> ChatResponse:
        """Execute one conversational turn with state read/update, retrieval, RAG, and tracing."""
        started = time.perf_counter()
        normalized = normalize_user_input(raw_message)

        # 1. Read persisted conversation state from SQLite.
        state = self.repository.get_session_state(session_id)
        recent_history = self.repository.get_recent_messages(session_id)
        next_turn = state.turn_count + 1
        requested_llm = llm_mode_override or self.settings.llm_mode

        memory_reads = {
            "active_crop_type": state.active_crop_type,
            "pending_clarification": state.pending_clarification,
            "pending_query": state.pending_query,
            "history_messages_loaded": len(recent_history),
        }

        explicit_crop = extract_supported_crop(normalized)
        unsupported_crop = extract_unsupported_crop(normalized)
        general_topic = is_general_soil_ipm_query(normalized)

        # 2. Explicit Goal / Action Decision Loop.
        intent: AllowedIntent
        action: AllowedAction
        effective_query: str | None = None
        crop_filter: str | None = None
        new_active_crop = state.active_crop_type
        new_pending_clarification = False
        new_pending_query: str | None = None

        if is_prescriptive_request(normalized):
            intent = "prescriptive_request"
            action = "REFUSE_PRESCRIPTIVE_REQUEST"
            new_pending_clarification = False
            new_pending_query = None

        elif is_greeting_or_help(normalized) and not state.pending_clarification:
            intent = "greeting_or_help"
            action = "GREET_OR_HELP"

        elif state.pending_clarification and explicit_crop and not unsupported_crop:
            # Continuity resolution: combine previously saved pending_query with clarified crop.
            intent = "crop_clarification_reply"
            action = "RETRIEVE_AND_ANSWER"
            new_active_crop = explicit_crop
            crop_filter = explicit_crop
            base_query = state.pending_query or normalized
            effective_query = (
                base_query
                if explicit_crop in base_query.lower()
                else f"{explicit_crop}: {base_query}"
            )
            new_pending_clarification = False
            new_pending_query = None

        elif state.pending_clarification and unsupported_crop:
            intent = "out_of_scope"
            action = "REFUSE_INSUFFICIENT_EVIDENCE"
            new_pending_clarification = False
            new_pending_query = None

        elif unsupported_crop:
            intent = "out_of_scope"
            action = "REFUSE_INSUFFICIENT_EVIDENCE"

        elif explicit_crop:
            intent = "crop_care_query"
            action = "RETRIEVE_AND_ANSWER"
            new_active_crop = explicit_crop
            crop_filter = explicit_crop
            effective_query = normalized

        elif general_topic:
            intent = "general_soil_ipm_query"
            action = "RETRIEVE_AND_ANSWER"
            crop_filter = "general"
            effective_query = normalized

        elif is_agricultural_query(normalized):
            if state.active_crop_type:
                # Follow-up question inherits the active crop from conversation state.
                intent = "crop_care_query"
                action = "RETRIEVE_AND_ANSWER"
                crop_filter = state.active_crop_type
                effective_query = f"{state.active_crop_type}: {normalized}"
            else:
                # Missing crop_type slot -> ask clarification & persist pending_query.
                intent = "crop_care_query"
                action = "CLARIFY_CROP"
                new_pending_clarification = True
                new_pending_query = normalized

        else:
            intent = "out_of_scope"
            action = "REFUSE_INSUFFICIENT_EVIDENCE"

        # 3. Execute selected action.
        retrieval_candidates = []
        chosen_sources: list[str] = []
        citations = []
        warnings: list[str] = []
        refused = False
        refusal_reason: str | None = None
        clarification_needed = False
        citation_validation_passed = True
        validation_result: str = "passed"
        llm_mode_used = "local-only"
        error_class: str | None = None
        confidence = 0.0
        answer = ""

        if action == "GREET_OR_HELP":
            supported_list = ", ".join(SUPPORTED_CROPS)
            answer = (
                "Hello! I am the **Agricultural Knowledge Navigator (P35)**. I provide cited, "
                "non-prescriptive educational crop-care information from vetted reference guides "
                f"covering **{supported_list}**, plus general soil and IPM practices.\n\n"
                "Ask a crop-care question (for example, *'What causes yellowing lower leaves "
                "in wheat?'* or *'How do I tell early blight from late blight in tomatoes?'*)."
            )
            confidence = 1.0
            validation_result = "passed"

        elif action == "CLARIFY_CROP":
            supported_list = ", ".join(SUPPORTED_CROPS)
            answer = (
                "To retrieve accurate crop-care educational guidance, could you please clarify "
                f"**which crop type** you are asking about?\n\n"
                f"Currently supported crops in the educational corpus: **{supported_list}** "
                "(or ask a general soil/irrigation/IPM question)."
            )
            clarification_needed = True
            confidence = 0.85
            validation_result = "clarification_requested"

        elif action == "REFUSE_PRESCRIPTIVE_REQUEST":
            refused = True
            refusal_reason = "prescriptive_chemical_dosage_prohibited"
            validation_result = "refused"
            confidence = 1.0
            answer = (
                "I cannot prescribe chemical dosages, mixing ratios, spray schedules, or specific "
                "pesticide/fungicide products. This assistant provides educational crop-care "
                "information only.\n\n"
                "For safe, localized treatment recommendations, please consult a certified "
                "agricultural extension officer or plant health clinic."
            )

        elif action == "RETRIEVE_AND_ANSWER":
            accepted_chunks, retrieval_candidates = self.retriever.search(
                effective_query or normalized,
                crop_filter=crop_filter,
            )
            if crop_filter and crop_filter != "general":
                accepted_chunks.sort(
                    key=lambda c: (c.crop_type == crop_filter, c.similarity_score),
                    reverse=True,
                )

            if not accepted_chunks:
                action = "REFUSE_INSUFFICIENT_EVIDENCE"
                refused = True
                refusal_reason = "insufficient_retrieval_evidence"
                validation_result = "refused"
                error_class = "NoRetrievalEvidenceError"
                confidence = 0.0
                supported_list = ", ".join(SUPPORTED_CROPS)
                answer = (
                    "I could not find sufficiently relevant evidence in the permitted crop-care "
                    "documents to answer your question reliably (all candidates fell below the "
                    f"similarity threshold of {self.settings.min_similarity:.2f}).\n\n"
                    f"Try asking about **{supported_list}** crop care, or general soil pH, "
                    "mulching, irrigation, and IPM principles."
                )
            else:
                rag_result = self.synthesizer.synthesize(
                    query=effective_query or normalized,
                    crop_label=crop_filter,
                    chunks=accepted_chunks,
                    llm_mode_override=llm_mode_override,
                )
                answer = rag_result.answer
                citations = rag_result.citations
                citation_validation_passed = rag_result.citation_validation_passed
                llm_mode_used = rag_result.llm_mode_used
                warnings = rag_result.warnings
                error_class = rag_result.error_class
                chosen_sources = [c.source_id for c in citations]
                confidence = round(max(c.similarity_score for c in accepted_chunks), 4)
                validation_result = "passed" if citation_validation_passed else "refused"

        else:  # REFUSE_INSUFFICIENT_EVIDENCE (out_of_scope / unsupported crop)
            refused = True
            supported_list = ", ".join(SUPPORTED_CROPS)
            if unsupported_crop:
                refusal_reason = f"unsupported_crop:{unsupported_crop}"
                answer = (
                    f"I do not have permitted crop-care educational documents indexed for "
                    f"**{unsupported_crop}**.\n\n"
                    f"Currently supported crops are **{supported_list}**, along with general soil "
                    "health, irrigation, and IPM fundamentals."
                )
            else:
                refusal_reason = "out_of_scope_or_unindexed_topic"
                answer = (
                    "Your request falls outside the permitted crop-care educational documents. "
                    f"I can answer non-prescriptive questions about **{supported_list}** crop care "
                    "or general soil, irrigation, and IPM concepts."
                )
            validation_result = "refused"
            error_class = "OutOfScopeOrUnsupportedTopic"
            confidence = 0.0

        latency_ms = round((time.perf_counter() - started) * 1000.0, 2)

        memory_writes = {
            "active_crop_type": new_active_crop,
            "pending_clarification": new_pending_clarification,
            "pending_query": new_pending_query,
        }

        trace = TurnTrace(
            trace_id=f"tr-{uuid.uuid4().hex[:12]}",
            session_id=session_id,
            turn_number=next_turn,
            normalized_input=normalized,
            intent=intent,
            selected_action=action,
            active_crop_before=state.active_crop_type,
            active_crop_after=new_active_crop,
            clarification_pending_before=state.pending_clarification,
            clarification_pending_after=new_pending_clarification,
            memory_reads=memory_reads,
            memory_writes=memory_writes,
            retrieval_query=effective_query,
            retrieval_crop_filter=crop_filter,
            retrieval_candidates=retrieval_candidates,
            chosen_sources=chosen_sources,
            citation_validation_passed=citation_validation_passed,
            validation_result=validation_result,  # type: ignore[arg-type]
            llm_mode_requested=requested_llm,
            llm_mode_used=llm_mode_used,
            latency_ms=latency_ms,
            error_class=error_class,
            timestamp=utc_now_iso(),
        )

        # 4. Persist updated conversation state, messages, and trace atomically.
        self.repository.record_turn(
            session_id=session_id,
            turn_number=next_turn,
            user_message=normalized,
            assistant_message=answer,
            active_crop_type=new_active_crop,
            pending_clarification=new_pending_clarification,
            pending_query=new_pending_query,
            trace=trace,
        )

        # Emit structured JSON log line (contains zero secrets).
        logger.info(trace.model_dump_json())

        return ChatResponse(
            session_id=session_id,
            turn_number=next_turn,
            intent=intent,
            action=action,
            active_crop_type=new_active_crop,
            clarification_needed=clarification_needed,
            answer=answer,
            educational_disclaimer=EDUCATIONAL_DISCLAIMER,
            citations=citations,
            confidence=confidence,
            refused=refused,
            refusal_reason=refusal_reason,
            warnings=warnings,
            trace=trace,
        )
