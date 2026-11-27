"""L6 Semantic Retrieval: deterministic chunking, local embeddings, and Chroma indexing."""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import chromadb
from chromadb.config import Settings as ChromaSettings

from agri_navigator.schemas import RetrievalCandidate


@dataclass(frozen=True)
class DocumentChunk:
    """Deterministic section chunk extracted from a permitted markdown document."""

    chunk_id: str
    doc_id: str
    title: str
    crop_type: str
    section: str
    license_note: str
    source_file: str
    text: str


@dataclass(frozen=True)
class RetrievedChunk:
    """Scored retrieval hit returned by semantic search."""

    chunk_id: str
    doc_id: str
    title: str
    crop_type: str
    section: str
    text: str
    similarity_score: float
    accepted: bool


class TextEmbedder(Protocol):
    """Protocol for deterministic dense vector embedders."""

    backend_name: str

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Encode a list of strings into L2-normalized dense vectors."""


class SentenceTransformerEmbedder:
    """Local HuggingFace sentence-transformers embedder (runs offline once cached)."""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> None:
        from sentence_transformers import SentenceTransformer

        self.backend_name = "sentence-transformers"
        self.model_name = model_name
        try:
            self._model = SentenceTransformer(model_name, local_files_only=True)
        except Exception:
            # First-run fallback when cache is not yet populated and network is available.
            self._model = SentenceTransformer(model_name)

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = self._model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return [vec.tolist() for vec in vectors]


class HashedNgramEmbedder:
    """Deterministic zero-network fallback embedder using hashed word/char n-grams."""

    def __init__(self, dim: int = 384) -> None:
        self.backend_name = "hashed-local"
        self.dim = dim

    def _encode_one(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        tokens = re.findall(r"[a-z0-9]+", text.lower())
        features: list[str] = list(tokens)
        for token in tokens:
            if len(token) >= 4:
                features.extend(token[i : i + 3] for i in range(len(token) - 2))
        for i in range(len(tokens) - 1):
            features.append(f"{tokens[i]}_{tokens[i + 1]}")
        for feat in features:
            digest = hashlib.blake2b(feat.encode("utf-8"), digest_size=8).digest()
            bucket = int.from_bytes(digest[:4], "little") % self.dim
            sign = 1.0 if (digest[4] & 1) == 0 else -1.0
            vec[bucket] += sign
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._encode_one(t) for t in texts]


def create_embedder(backend: str, model_name: str) -> TextEmbedder:
    """Instantiate configured local embedder."""
    if backend == "hashed-local":
        return HashedNgramEmbedder()
    return SentenceTransformerEmbedder(model_name=model_name)


def parse_markdown_document(file_path: Path) -> list[DocumentChunk]:
    """Deterministically parse a frontmatter markdown document into section chunks."""
    raw = file_path.read_text(encoding="utf-8").strip()
    frontmatter: dict[str, str] = {}
    body = raw

    if raw.startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) == 3:
            fm_block, body = parts[1], parts[2].strip()
            for line in fm_block.strip().splitlines():
                if ":" in line:
                    key, val = line.split(":", 1)
                    frontmatter[key.strip().lower()] = val.strip()

    doc_id = frontmatter.get("doc_id", file_path.stem.upper())
    title = frontmatter.get("title", file_path.stem.replace("_", " ").title())
    crop_type = frontmatter.get("crop_type", "general").lower()
    license_note = frontmatter.get("license", "Permitted educational reference")

    section_pattern = re.compile(r"^##\s+(.+)$", re.MULTILINE)
    matches = list(section_pattern.finditer(body))
    chunks: list[DocumentChunk] = []

    if not matches:
        clean_text = re.sub(r"\s+", " ", body).strip()
        if clean_text:
            chunks.append(
                DocumentChunk(
                    chunk_id=f"{doc_id}#sec-1",
                    doc_id=doc_id,
                    title=title,
                    crop_type=crop_type,
                    section="Overview",
                    license_note=license_note,
                    source_file=file_path.name,
                    text=f"{title} ({crop_type}) — {clean_text}",
                )
            )
        return chunks

    for idx, match in enumerate(matches, start=1):
        heading = match.group(1).strip()
        start = match.end()
        end = matches[idx].start() if idx < len(matches) else len(body)
        section_body = re.sub(r"\s+", " ", body[start:end]).strip()
        if not section_body:
            continue
        # Embed-friendly enriched text includes title and section heading for semantic recall.
        enriched_text = f"{title} | Crop: {crop_type} | {heading}: {section_body}"
        chunks.append(
            DocumentChunk(
                chunk_id=f"{doc_id}#sec-{idx}",
                doc_id=doc_id,
                title=title,
                crop_type=crop_type,
                section=heading,
                license_note=license_note,
                source_file=file_path.name,
                text=enriched_text,
            )
        )
    return chunks


def load_corpus_chunks(raw_docs_dir: Path) -> list[DocumentChunk]:
    """Load and deterministically chunk all markdown documents in raw_docs_dir."""
    if not raw_docs_dir.exists():
        return []
    chunks: list[DocumentChunk] = []
    for path in sorted(raw_docs_dir.glob("*.md")):
        chunks.extend(parse_markdown_document(path))
    return chunks


class SemanticRetriever:
    """Chroma-backed semantic retriever with stable IDs, crop filters, and score threshold."""

    COLLECTION_NAME = "crop_care_docs"

    def __init__(
        self,
        *,
        chroma_dir: Path,
        raw_docs_dir: Path,
        embedder: TextEmbedder,
        top_k: int = 4,
        min_similarity: float = 0.32,
    ) -> None:
        self.chroma_dir = chroma_dir
        self.raw_docs_dir = raw_docs_dir
        self.embedder = embedder
        self.top_k = top_k
        self.min_similarity = min_similarity
        self.chroma_dir.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=str(self.chroma_dir),
            settings=ChromaSettings(anonymized_telemetry=False),
        )

    def _get_or_create_collection(self):
        return self._client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    def rebuild_index(self) -> int:
        """Deterministically rebuild the Chroma vector index from raw documents."""
        chunks = load_corpus_chunks(self.raw_docs_dir)
        try:
            self._client.delete_collection(name=self.COLLECTION_NAME)
        except Exception:
            pass
        collection = self._get_or_create_collection()
        if not chunks:
            return 0

        ids = [c.chunk_id for c in chunks]
        documents = [c.text for c in chunks]
        metadatas = [
            {
                "doc_id": c.doc_id,
                "title": c.title,
                "crop_type": c.crop_type,
                "section": c.section,
                "license_note": c.license_note,
                "source_file": c.source_file,
            }
            for c in chunks
        ]
        embeddings = self.embedder.embed(documents)
        collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )
        return len(chunks)

    def ensure_indexed(self) -> int:
        """Build the index automatically if empty; otherwise return current chunk count."""
        collection = self._get_or_create_collection()
        count = collection.count()
        if count == 0:
            return self.rebuild_index()
        return count

    def count(self) -> int:
        """Return number of indexed chunks in Chroma."""
        try:
            return self._get_or_create_collection().count()
        except Exception:
            return 0

    def health_check(self) -> bool:
        """Verify Chroma persistent collection is readable."""
        try:
            _ = self._get_or_create_collection().count()
            return True
        except Exception:
            return False

    def search(
        self,
        query: str,
        *,
        crop_filter: str | None = None,
        top_k: int | None = None,
        min_similarity: float | None = None,
    ) -> tuple[list[RetrievedChunk], list[RetrievalCandidate]]:
        """Run semantic top-k retrieval with optional crop filtering and score thresholding."""
        collection = self._get_or_create_collection()
        total = collection.count()
        if total == 0:
            return [], []

        k = min(top_k or self.top_k, total)
        threshold = self.min_similarity if min_similarity is None else min_similarity
        query_embedding = self.embedder.embed([query])[0]

        where_clause = None
        if crop_filter and crop_filter != "general":
            where_clause = {"crop_type": {"$in": [crop_filter, "general"]}}
        elif crop_filter == "general":
            where_clause = {"crop_type": "general"}

        result = collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            where=where_clause,
            include=["documents", "metadatas", "distances"],
        )

        ids = (result.get("ids") or [[]])[0]
        docs = (result.get("documents") or [[]])[0]
        metas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]

        accepted_chunks: list[RetrievedChunk] = []
        candidates: list[RetrievalCandidate] = []

        for chunk_id, doc_text, meta, dist in zip(ids, docs, metas, distances):
            # Chroma cosine distance = 1 - cosine_similarity; clamp cleanly to [0, 1].
            similarity = max(0.0, min(1.0, round(1.0 - float(dist), 4)))
            is_accepted = similarity >= threshold
            # Prefer crop-specific hits if general hits are barely relevant when crop_filter set.
            candidate = RetrievalCandidate(
                source_id=chunk_id,
                doc_id=str(meta["doc_id"]),
                crop_type=str(meta["crop_type"]),
                section=str(meta["section"]),
                score=similarity,
                accepted=is_accepted,
            )
            candidates.append(candidate)
            if is_accepted:
                accepted_chunks.append(
                    RetrievedChunk(
                        chunk_id=chunk_id,
                        doc_id=str(meta["doc_id"]),
                        title=str(meta["title"]),
                        crop_type=str(meta["crop_type"]),
                        section=str(meta["section"]),
                        text=str(doc_text),
                        similarity_score=similarity,
                        accepted=True,
                    )
                )

        # Sort deterministically by descending similarity score, then source_id.
        accepted_chunks.sort(key=lambda c: (-c.similarity_score, c.chunk_id))
        return accepted_chunks, candidates
