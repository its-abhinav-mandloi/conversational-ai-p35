"""FastAPI application and dependency wiring for P35 Agricultural Knowledge Navigator."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, status

from agri_navigator.config import Settings, get_settings
from agri_navigator.domain_data import SUPPORTED_CROPS
from agri_navigator.grounded_answer import GroundedAnswerSynthesizer
from agri_navigator.orchestrator import AgriNavigatorOrchestrator, InvalidInputError
from agri_navigator.repository import SessionNotFoundError, SQLiteRepository
from agri_navigator.retrieval import SemanticRetriever, create_embedder
from agri_navigator.schemas import (
    ChatRequest,
    ChatResponse,
    HealthResponse,
    SessionCreateResponse,
    SessionDetailResponse,
    TurnTrace,
)


class AppContainer:
    """Holds initialized repository, retriever, synthesizer, and orchestrator instances."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        logging.basicConfig(
            level=getattr(logging, self.settings.log_level.upper(), logging.INFO),
            format="%(message)s",
        )
        sqlite_path = self.settings.resolved_path(self.settings.sqlite_path)
        chroma_dir = self.settings.resolved_path(self.settings.chroma_dir)
        raw_docs_dir = self.settings.resolved_path(self.settings.raw_docs_dir)

        self.repository = SQLiteRepository(
            db_path=sqlite_path,
            max_history_turns=self.settings.max_history_turns,
        )
        self.embedder = create_embedder(
            backend=self.settings.embedding_backend,
            model_name=self.settings.embedding_model,
        )
        self.retriever = SemanticRetriever(
            chroma_dir=chroma_dir,
            raw_docs_dir=raw_docs_dir,
            embedder=self.embedder,
            top_k=self.settings.top_k,
            min_similarity=self.settings.min_similarity,
        )
        self.retriever.ensure_indexed()
        self.synthesizer = GroundedAnswerSynthesizer(self.settings)
        self.orchestrator = AgriNavigatorOrchestrator(
            settings=self.settings,
            repository=self.repository,
            retriever=self.retriever,
            synthesizer=self.synthesizer,
        )


def create_app(settings: Settings | None = None) -> FastAPI:
    """Application factory enabling isolated test or production configurations."""
    effective_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        if not hasattr(application.state, "container"):
            application.state.container = AppContainer(effective_settings)
        yield

    application = FastAPI(
        title="Agricultural Knowledge Navigator (P35)",
        description=(
            "Conversational AI Assignment 1 Phase I — Group 92. "
            "L1-L3 controlled dialogue with L6 Chroma semantic retrieval and L7-L8 grounded RAG."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )
    # Initialize eagerly as well so TestClient without context manager or direct usage works.
    application.state.container = AppContainer(effective_settings)

    def get_container(request: Request) -> AppContainer:
        return request.app.state.container

    @application.get("/health", response_model=HealthResponse, tags=["system"])
    def health(container: AppContainer = Depends(get_container)) -> HealthResponse:
        sqlite_ok = container.repository.health_check()
        chroma_ok = container.retriever.health_check()
        chunks = container.retriever.count()
        overall = "ok" if (sqlite_ok and chroma_ok and chunks > 0) else "degraded"
        return HealthResponse(
            status=overall,
            project="P35 - Agricultural Knowledge Navigator",
            llm_mode=container.settings.llm_mode,
            embedding_backend=container.settings.embedding_backend,
            embedding_model=container.settings.embedding_model,
            indexed_chunks=chunks,
            sqlite_ok=sqlite_ok,
            chroma_ok=chroma_ok,
            supported_crops=list(SUPPORTED_CROPS),
        )

    @application.post(
        "/sessions",
        response_model=SessionCreateResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["sessions"],
    )
    def create_session(container: AppContainer = Depends(get_container)) -> SessionCreateResponse:
        return container.repository.create_session()

    @application.get(
        "/sessions/{session_id}",
        response_model=SessionDetailResponse,
        tags=["sessions"],
    )
    def get_session(
        session_id: str,
        container: AppContainer = Depends(get_container),
    ) -> SessionDetailResponse:
        try:
            return container.repository.get_session_detail(session_id)
        except SessionNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
            ) from exc

    @application.get(
        "/sessions/{session_id}/traces",
        response_model=list[TurnTrace],
        tags=["sessions"],
    )
    def get_session_traces(
        session_id: str,
        container: AppContainer = Depends(get_container),
    ) -> list[TurnTrace]:
        try:
            return container.repository.get_traces(session_id)
        except SessionNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
            ) from exc

    @application.post("/chat", response_model=ChatResponse, tags=["chat"])
    def chat(
        payload: ChatRequest,
        container: AppContainer = Depends(get_container),
    ) -> ChatResponse:
        try:
            return container.orchestrator.handle_turn(
                session_id=payload.session_id,
                raw_message=payload.message,
                llm_mode_override=payload.llm_mode_override,
            )
        except InvalidInputError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc
        except SessionNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
            ) from exc

    return application


app = create_app()
