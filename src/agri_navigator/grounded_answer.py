"""L7-L8 Grounded RAG: evidence-only answer synthesis and citation verification."""

from __future__ import annotations

import re
from dataclasses import dataclass

import httpx

from agri_navigator.config import Settings
from agri_navigator.domain_data import EDUCATIONAL_DISCLAIMER
from agri_navigator.retrieval import RetrievedChunk
from agri_navigator.schemas import Citation


class ProviderUnavailableError(RuntimeError):
    """Raised when an optional external/local LLM provider is unconfigured or unreachable."""


@dataclass(frozen=True)
class GroundedAnswerResult:
    """Result of L7-L8 grounded generation and citation validation."""

    answer: str
    citations: list[Citation]
    citation_validation_passed: bool
    llm_mode_used: str
    warnings: list[str]
    error_class: str | None = None


_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "how",
        "in",
        "is",
        "it",
        "my",
        "of",
        "on",
        "or",
        "the",
        "this",
        "to",
        "what",
        "when",
        "where",
        "which",
        "why",
        "with",
    }
)


def _strip_chunk_prefix(chunk: RetrievedChunk) -> str:
    """Remove synthetic index header prefix from chunk text for clean sentence extraction."""
    marker = f"{chunk.section}:"
    if marker in chunk.text:
        return chunk.text.split(marker, 1)[1].strip()
    return chunk.text.strip()


def _select_relevant_sentences(query: str, body: str, max_sentences: int = 2) -> str:
    """Select the most query-relevant sentences deterministically from a retrieved chunk."""
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", body) if s.strip()]
    if not sentences:
        return body
    query_terms = {
        tok
        for tok in re.findall(r"[a-z0-9]+", query.lower())
        if tok not in _STOPWORDS and len(tok) > 2
    }
    if not query_terms:
        return " ".join(sentences[:max_sentences])

    scored: list[tuple[int, int, str]] = []
    for idx, sent in enumerate(sentences):
        sent_tokens = set(re.findall(r"[a-z0-9]+", sent.lower()))
        overlap = len(query_terms & sent_tokens)
        scored.append((overlap, -idx, sent))
    scored.sort(reverse=True)
    chosen = [item[2] for item in scored[:max_sentences]]
    # Restore original document sentence order for readability.
    ordered = [s for s in sentences if s in chosen]
    return " ".join(ordered)


def _build_citations(chunks: list[RetrievedChunk]) -> list[Citation]:
    """Build structured Citation objects from retrieved chunks."""
    citations: list[Citation] = []
    for chunk in chunks[:3]:
        body = _strip_chunk_prefix(chunk)
        excerpt = body[:220].rstrip() + ("..." if len(body) > 220 else "")
        citations.append(
            Citation(
                source_id=chunk.chunk_id,
                doc_id=chunk.doc_id,
                title=chunk.title,
                crop_type=chunk.crop_type,
                section=chunk.section,
                similarity_score=chunk.similarity_score,
                excerpt=excerpt,
            )
        )
    return citations


def validate_citations(answer_text: str, allowed_chunks: list[RetrievedChunk]) -> bool:
    """Verify every cited source in answer_text is allowed and >= 1 citation exists."""
    allowed_source_ids = {c.chunk_id for c in allowed_chunks}
    allowed_doc_ids = {c.doc_id for c in allowed_chunks}

    cited_tokens = re.findall(r"\[(DOC-[A-Z0-9-]+(?:#sec-\d+)?)\b", answer_text)
    if not cited_tokens:
        return False
    for token in cited_tokens:
        if token not in allowed_source_ids and token not in allowed_doc_ids:
            return False
    return True


def _compose_local_grounded_answer(
    query: str,
    crop_label: str | None,
    chunks: list[RetrievedChunk],
) -> tuple[str, list[Citation]]:
    """Compose a deterministic, citation-backed, non-prescriptive answer from retrieved chunks."""
    citations = _build_citations(chunks)
    top_chunks = chunks[:2]

    header_subject = (
        f"for **{crop_label}**"
        if crop_label and crop_label != "general"
        else "on general crop care"
    )
    lines = [f"Based on the permitted educational documents {header_subject}:", ""]

    for chunk in top_chunks:
        body = _strip_chunk_prefix(chunk)
        summary = _select_relevant_sentences(query, body, max_sentences=2)
        lines.append(f"- **[{chunk.chunk_id}] {chunk.section}:** {summary}")

    lines.append("")
    lines.append(f"*Note:* {EDUCATIONAL_DISCLAIMER}")
    return "\n".join(lines), citations


def _build_rag_prompt(query: str, crop_label: str | None, chunks: list[RetrievedChunk]) -> str:
    """Construct strict context-only prompt for optional OpenAI/Ollama providers."""
    context_blocks = []
    for chunk in chunks[:3]:
        body = _strip_chunk_prefix(chunk)
        context_blocks.append(f"[{chunk.chunk_id}] ({chunk.title} — {chunk.section}): {body}")
    context_text = "\n\n".join(context_blocks)
    crop_note = crop_label or "general"
    return (
        "You are an educational Agricultural Knowledge Navigator. Answer the user's question "
        "ONLY using the retrieved context excerpts below. Cite every factual claim inline using "
        "the exact bracketed ID such as [DOC-WHEAT-01#sec-2]. Do NOT give chemical dosages, "
        "brand recommendations, or prescriptive treatments. Keep the answer educational.\n\n"
        f"Crop context: {crop_note}\n"
        f"Question: {query}\n\n"
        f"Retrieved Context:\n{context_text}"
    )


def _call_openai(prompt: str, settings: Settings) -> str:
    """Invoke optional OpenAI Chat Completions endpoint when explicitly enabled and configured."""
    api_key = settings.openai_api_key.strip()
    if not api_key:
        raise ProviderUnavailableError("OpenAI mode requested, but OPENAI_API_KEY is missing.")

    url = f"{settings.openai_base_url.rstrip('/')}/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": settings.openai_model,
        "temperature": 0.1,
        "messages": [{"role": "user", "content": prompt}],
    }
    try:
        response = httpx.post(url, json=payload, headers=headers, timeout=15.0)
        response.raise_for_status()
        data = response.json()
        return str(data["choices"][0]["message"]["content"]).strip()
    except httpx.HTTPError as exc:
        raise ProviderUnavailableError(f"OpenAI request failed: {exc.__class__.__name__}") from exc
    except (KeyError, IndexError, ValueError) as exc:
        raise ProviderUnavailableError("OpenAI returned an unexpected response payload.") from exc


def _call_ollama(prompt: str, settings: Settings) -> str:
    """Invoke optional local Ollama generate endpoint when explicitly enabled and running."""
    url = f"{settings.ollama_base_url.rstrip('/')}/api/generate"
    payload = {"model": settings.ollama_model, "prompt": prompt, "stream": False}
    try:
        response = httpx.post(url, json=payload, timeout=15.0)
        response.raise_for_status()
        data = response.json()
        text = str(data.get("response", "")).strip()
        if not text:
            raise ProviderUnavailableError("Ollama returned an empty response.")
        return text
    except httpx.HTTPError as exc:
        raise ProviderUnavailableError(
            f"Ollama endpoint unavailable: {exc.__class__.__name__}"
        ) from exc


class GroundedAnswerSynthesizer:
    """Synthesizes grounded, cited educational answers and verifies citation integrity."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def synthesize(
        self,
        *,
        query: str,
        crop_label: str | None,
        chunks: list[RetrievedChunk],
        llm_mode_override: str | None = None,
    ) -> GroundedAnswerResult:
        """Produce a grounded answer solely from retrieved chunks and validate citations."""
        requested_mode = llm_mode_override or self.settings.llm_mode
        warnings: list[str] = []

        if not chunks:
            return GroundedAnswerResult(
                answer=(
                    "I could not find sufficient supporting evidence in the permitted crop-care "
                    "documents to answer that safely. Please ask about general crop care for "
                    "wheat, rice, tomato, maize, potato, or general soil and irrigation practices."
                ),
                citations=[],
                citation_validation_passed=True,
                llm_mode_used="local-only",
                warnings=warnings,
            )

        citations = _build_citations(chunks)

        if requested_mode in ("openai", "ollama"):
            prompt = _build_rag_prompt(query, crop_label, chunks)
            try:
                raw_answer = (
                    _call_openai(prompt, self.settings)
                    if requested_mode == "openai"
                    else _call_ollama(prompt, self.settings)
                )
                if validate_citations(raw_answer, chunks):
                    return GroundedAnswerResult(
                        answer=f"{raw_answer}\n\n*Note:* {EDUCATIONAL_DISCLAIMER}",
                        citations=citations,
                        citation_validation_passed=True,
                        llm_mode_used=requested_mode,
                        warnings=warnings,
                    )
                warnings.append(
                    f"Optional {requested_mode} output failed post-generation citation check; "
                    "reverted to deterministic local-only grounded response."
                )
                fallback_answer, _ = _compose_local_grounded_answer(query, crop_label, chunks)
                return GroundedAnswerResult(
                    answer=fallback_answer,
                    citations=citations,
                    citation_validation_passed=validate_citations(fallback_answer, chunks),
                    llm_mode_used="local-only",
                    warnings=warnings,
                    error_class="CitationValidationError",
                )
            except ProviderUnavailableError as exc:
                warnings.append(
                    f"Optional {requested_mode} provider unavailable ({exc}); "
                    "safely fell back to local-only grounded composition."
                )
                fallback_answer, _ = _compose_local_grounded_answer(query, crop_label, chunks)
                return GroundedAnswerResult(
                    answer=fallback_answer,
                    citations=citations,
                    citation_validation_passed=validate_citations(fallback_answer, chunks),
                    llm_mode_used="local-only",
                    warnings=warnings,
                    error_class="ProviderUnavailableError",
                )

        answer_text, citations = _compose_local_grounded_answer(query, crop_label, chunks)
        valid = validate_citations(answer_text, chunks)
        return GroundedAnswerResult(
            answer=answer_text,
            citations=citations,
            citation_validation_passed=valid,
            llm_mode_used="local-only",
            warnings=warnings,
        )
