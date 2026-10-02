"""Embeddings and vector search for the Indian Knowledge System."""

from __future__ import annotations

import logging
import json
import hashlib
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path

import numpy as np

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

from .base import KnowledgeEntry, KnowledgeDomain, KnowledgeBase

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingConfig:
    model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    device: str = "cpu"
    cache_folder: Optional[str] = None
    batch_size: int = 32
    normalize_embeddings: bool = True


@dataclass
class ChunkMetadata:
    entry_id: str
    chunk_index: int
    chunk_text: str
    domain: str
    category: str
    title: str
    source: str
    source_type: str
    author: Optional[str] = None
    translator: Optional[str] = None
    commentator: Optional[str] = None
    original_language: str = "Sanskrit"
    translation_language: str = "English"
    tradition: Optional[str] = None
    chapter: Optional[str] = None
    section: Optional[str] = None
    verse: Optional[str] = None
    topics: list[str] = field(default_factory=list)
    concepts: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    historical_context: Optional[str] = None
    interpretation_type: Optional[str] = None
    source_url: Optional[str] = None
    retrieved_at: Optional[str] = None
    embedding_hash: Optional[str] = None


class EmbeddingEngine:
    """Manages embeddings for semantic search across the knowledge base."""

    def __init__(self, config: EmbeddingConfig | None = None):
        self.config = config or EmbeddingConfig()
        self._model: Optional[SentenceTransformer] = None
        self._embeddings: dict[str, np.ndarray] = {}
        self._chunk_metadata: dict[str, ChunkMetadata] = {}
        self._initialized = False

    def initialize(self) -> bool:
        if self._initialized:
            return True

        if SentenceTransformer is None:
            logger.warning("[EMBEDDINGS] sentence-transformers not installed. Install with: pip install sentence-transformers")
            return False

        try:
            logger.info(f"[EMBEDDINGS] Loading model: {self.config.model_name}")
            self._model = SentenceTransformer(
                self.config.model_name,
                device=self.config.device,
                cache_folder=self.config.cache_folder,
            )
            self._initialized = True
            logger.info("[EMBEDDINGS] Model loaded successfully")
            return True
        except Exception as e:
            logger.error(f"[EMBEDDINGS] Failed to load model: {e}")
            return False

    def _get_model(self) -> Optional[SentenceTransformer]:
        if not self._initialized:
            self.initialize()
        return self._model

    def embed_text(self, text: str) -> Optional[np.ndarray]:
        model = self._get_model()
        if model is None:
            return None

        try:
            embedding = model.encode(
                text,
                batch_size=self.config.batch_size,
                normalize_embeddings=self.config.normalize_embeddings,
                show_progress_bar=False,
            )
            return embedding
        except Exception as e:
            logger.error(f"[EMBEDDINGS] Failed to embed text: {e}")
            return None

    def embed_texts(self, texts: list[str]) -> list[Optional[np.ndarray]]:
        model = self._get_model()
        if model is None:
            return [None] * len(texts)

        try:
            embeddings = model.encode(
                texts,
                batch_size=self.config.batch_size,
                normalize_embeddings=self.config.normalize_embeddings,
                show_progress_bar=False,
            )
            return list(embeddings)
        except Exception as e:
            logger.error(f"[EMBEDDINGS] Failed to embed texts: {e}")
            return [None] * len(texts)

    def add_chunk(self, chunk_id: str, text: str, metadata: ChunkMetadata) -> bool:
        embedding = self.embed_text(text)
        if embedding is None:
            return False

        self._embeddings[chunk_id] = embedding
        self._chunk_metadata[chunk_id] = metadata
        return True

    def add_chunks_batch(self, chunks: list[tuple[str, str, ChunkMetadata]]) -> int:
        if not chunks:
            return 0

        texts = [c[1] for c in chunks]
        embeddings = self.embed_texts(texts)

        added = 0
        for i, (chunk_id, text, metadata) in enumerate(chunks):
            if embeddings[i] is not None:
                self._embeddings[chunk_id] = embeddings[i]
                self._chunk_metadata[chunk_id] = metadata
                added += 1
        return added

    def search(self, query: str, top_k: int = 10, domain_filter: Optional[str] = None,
               category_filter: Optional[str] = None, min_score: float = 0.3) -> list[tuple[float, ChunkMetadata]]:
        query_embedding = self.embed_text(query)
        if query_embedding is None:
            return []

        results = []
        for chunk_id, embedding in self._embeddings.items():
            metadata = self._chunk_metadata.get(chunk_id)
            if not metadata:
                continue

            if domain_filter and metadata.domain != domain_filter:
                continue
            if category_filter and metadata.category != category_filter:
                continue

            score = float(np.dot(query_embedding, embedding))
            if score >= min_score:
                results.append((score, metadata))

        results.sort(key=lambda x: x[0], reverse=True)
        return results[:top_k]

    def search_by_concept(self, concepts: list[str], top_k: int = 10,
                          domain_filter: Optional[str] = None) -> list[tuple[float, ChunkMetadata]]:
        results = []
        for chunk_id, metadata in self._chunk_metadata.items():
            if domain_filter and metadata.domain != domain_filter:
                continue

            score = 0.0
            for concept in concepts:
                concept_lower = concept.lower()
                if concept_lower in [c.lower() for c in metadata.concepts]:
                    score += 2.0
                if concept_lower in [k.lower() for k in metadata.keywords]:
                    score += 1.5
                if concept_lower in [t.lower() for t in metadata.topics]:
                    score += 1.0
                if concept_lower in metadata.title.lower():
                    score += 2.5
                if concept_lower in metadata.chunk_text.lower():
                    score += 0.5

            if score > 0:
                results.append((score, metadata))

        results.sort(key=lambda x: x[0], reverse=True)
        return results[:top_k]

    def search_exact_source(self, source: str, top_k: int = 10) -> list[tuple[float, ChunkMetadata]]:
        results = []
        for chunk_id, metadata in self._chunk_metadata.items():
            if metadata.source == source:
                results.append((1.0, metadata))
        return results[:top_k]

    def get_chunk(self, chunk_id: str) -> Optional[ChunkMetadata]:
        return self._chunk_metadata.get(chunk_id)

    def get_stats(self) -> dict:
        domains = set()
        categories = set()
        sources = set()
        source_types = set()
        languages = set()

        for meta in self._chunk_metadata.values():
            domains.add(meta.domain)
            categories.add(meta.category)
            if meta.source:
                sources.add(meta.source)
            if meta.source_type:
                source_types.add(meta.source_type)
            if meta.translation_language:
                languages.add(meta.translation_language)

        return {
            "total_chunks": len(self._chunk_metadata),
            "domains": len(domains),
            "categories": len(categories),
            "unique_sources": len(sources),
            "source_types": list(source_types),
            "translation_languages": list(languages),
            "domain_list": list(domains),
            "category_list": list(categories),
        }

    def save_index(self, path: str | Path) -> bool:
        try:
            path = Path(path)
            path.parent.mkdir(parents=True, exist_ok=True)

            data = {
                "config": {
                    "model_name": self.config.model_name,
                    "device": self.config.device,
                },
                "embeddings": {k: v.tolist() for k, v in self._embeddings.items()},
                "metadata": {k: v.__dict__ for k, v in self._chunk_metadata.items()},
            }
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            logger.info(f"[EMBEDDINGS] Index saved to {path}")
            return True
        except Exception as e:
            logger.error(f"[EMBEDDINGS] Failed to save index: {e}")
            return False

    def load_index(self, path: str | Path) -> bool:
        try:
            path = Path(path)
            if not path.exists():
                logger.warning(f"[EMBEDDINGS] Index file not found: {path}")
                return False

            data = json.loads(path.read_text(encoding="utf-8"))

            self._embeddings = {k: np.array(v) for k, v in data.get("embeddings", {}).items()}

            for k, v in data.get("metadata", {}).items():
                self._chunk_metadata[k] = ChunkMetadata(**v)

            logger.info(f"[EMBEDDINGS] Index loaded from {path} ({len(self._chunk_metadata)} chunks)")
            return True
        except Exception as e:
            logger.error(f"[EMBEDDINGS] Failed to load index: {e}")
            return False


def chunk_entry(entry: KnowledgeEntry, max_chunk_size: int = 500, overlap: int = 50) -> list[tuple[str, str, ChunkMetadata]]:
    """Chunk a knowledge entry into smaller pieces for embedding."""
    content = entry.content
    if not content.strip():
        return []

    chunks = []
    start = 0
    chunk_index = 0

    while start < len(content):
        end = min(start + max_chunk_size, len(content))

        if end < len(content):
            last_period = content.rfind('.', start, end)
            last_newline = content.rfind('\n', start, end)
            break_point = max(last_period, last_newline)
            if break_point > start:
                end = break_point + 1

        chunk_text = content[start:end].strip()
        if chunk_text:
            chunk_id = f"{entry.id}_chunk_{chunk_index}"

            metadata = ChunkMetadata(
                entry_id=entry.id,
                chunk_index=chunk_index,
                chunk_text=chunk_text,
                domain=entry.domain,
                category=entry.category,
                title=entry.title,
                source=entry.metadata.get("source", ""),
                source_type=entry.metadata.get("source_type", ""),
                author=entry.metadata.get("author"),
                translator=entry.metadata.get("translator"),
                commentator=entry.metadata.get("commentator"),
                original_language=entry.metadata.get("original_language", "Sanskrit"),
                translation_language=entry.metadata.get("translation_language", "English"),
                tradition=entry.metadata.get("tradition"),
                chapter=entry.metadata.get("chapter"),
                section=entry.metadata.get("section"),
                verse=entry.metadata.get("verse"),
                topics=entry.metadata.get("topics", []),
                concepts=entry.metadata.get("concepts", []),
                keywords=entry.metadata.get("keywords", entry.tags),
                historical_context=entry.metadata.get("historical_context"),
                interpretation_type=entry.metadata.get("interpretation_type"),
                source_url=entry.metadata.get("source_url"),
                retrieved_at=entry.metadata.get("retrieved_at"),
                embedding_hash=hashlib.md5(chunk_text.encode()).hexdigest()[:16],
            )

            chunks.append((chunk_id, chunk_text, metadata))
            chunk_index += 1

        start = end - overlap
        if start >= len(content):
            break

    return chunks


def build_embeddings_from_kb(knowledge_base: KnowledgeBase, engine: EmbeddingEngine) -> int:
    """Build embeddings for all entries in a knowledge base."""
    total_chunks = 0

    for domain_name, domain in knowledge_base.domains.items():
        for entry in domain.entries.values():
            chunks = chunk_entry(entry)
            if chunks:
                added = engine.add_chunks_batch(chunks)
                total_chunks += added
                logger.debug(f"[EMBEDDINGS] Added {added} chunks for {entry.id}")

    logger.info(f"[EMBEDDINGS] Built index with {total_chunks} chunks from {len(knowledge_base.domains)} domains")
    return total_chunks


_embedding_engine: EmbeddingEngine | None = None


def get_embedding_engine(config: EmbeddingConfig | None = None) -> EmbeddingEngine:
    global _embedding_engine
    if _embedding_engine is None:
        _embedding_engine = EmbeddingEngine(config)
    return _embedding_engine