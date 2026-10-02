"""Base classes for the Vedic Knowledge System — source-aware, multilingual, provenance-tracked."""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class DifficultyLevel(Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class SourceType(Enum):
    PRIMARY_TEXT = "primary_text"
    TRANSLATION = "translation"
    TRADITIONAL_COMMENTARY = "traditional_commentary"
    SCHOLARLY_REFERENCE = "scholarly_reference"
    HISTORICAL_REFERENCE = "historical_reference"
    SECONDARY_SOURCE = "secondary_source"
    SUMMARY = "summary"


class Language(Enum):
    ENGLISH = "en"
    HINDI = "hi"
    MARATHI = "mr"
    SANSKRIT = "sa"
    HINGLISH = "hinglish"
    MARATHI_ENGLISH = "mr-en"
    HINDI_ENGLISH = "hi-en"


class VedicDomain(Enum):
    UPANISHADS = "upanishads"
    BRAHMANAS = "brahmanas"
    ARANYAKAS = "aranyakas"
    VEDANGAS = "vedangas"
    ITIHASA = "itihasa"
    PURANAS = "puranas"
    BHAGAVAD_GITA = "bhagavad_gita"


@dataclass
class SourceMetadata:
    """Complete source metadata for provenance tracking."""
    title: str
    category: str
    subcategory: str
    source: str
    source_type: SourceType
    author: str = ""
    translator: str = ""
    commentator: str = ""
    original_language: str = ""
    translation_language: str = ""
    tradition: str = ""
    chapter: str = ""
    section: str = ""
    verse: str = ""
    topics: list[str] = field(default_factory=list)
    concepts: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    historical_context: str = ""
    interpretation_type: str = ""
    source_url: str = ""
    references: list[str] = field(default_factory=list)
    retrieved_at: str = field(default_factory=lambda: datetime.now().isoformat())
    document_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "category": self.category,
            "subcategory": self.subcategory,
            "source": self.source,
            "source_type": self.source_type.value,
            "author": self.author,
            "translator": self.translator,
            "commentator": self.commentator,
            "original_language": self.original_language,
            "translation_language": self.translation_language,
            "tradition": self.tradition,
            "chapter": self.chapter,
            "section": self.section,
            "verse": self.verse,
            "topics": self.topics,
            "concepts": self.concepts,
            "keywords": self.keywords,
            "historical_context": self.historical_context,
            "interpretation_type": self.interpretation_type,
            "source_url": self.source_url,
            "references": self.references,
            "retrieved_at": self.retrieved_at,
            "document_id": self.document_id,
        }


@dataclass
class KnowledgeChunk:
    """A chunk of knowledge with full source provenance."""
    id: str
    content: str
    source_metadata: SourceMetadata
    language: Language = Language.ENGLISH
    chunk_index: int = 0
    total_chunks: int = 1
    embedding: list[float] | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "content": self.content,
            "source_metadata": self.source_metadata.to_dict(),
            "language": self.language.value,
            "chunk_index": self.chunk_index,
            "total_chunks": self.total_chunks,
            "has_embedding": self.embedding is not None,
        }


@dataclass
class VedicKnowledgeEntry:
    """A complete knowledge entry with full provenance."""
    id: str
    title: str
    content: str
    domain: VedicDomain
    category: str
    subcategory: str
    source_metadata: SourceMetadata
    tags: list[str] = field(default_factory=list)
    difficulty: DifficultyLevel = DifficultyLevel.INTERMEDIATE
    prerequisites: list[str] = field(default_factory=list)
    related: list[str] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)
    references: list[str] = field(default_factory=list)
    chunks: list[KnowledgeChunk] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def matches_query(self, query: str) -> float:
        query_lower = query.lower()
        score = 0.0
        if query_lower in self.title.lower():
            score += 3.0
        if query_lower in self.content.lower():
            score += 1.0
        for tag in self.tags:
            if query_lower in tag.lower() or tag.lower() in query_lower:
                score += 2.0
        if query_lower == self.domain.value.lower():
            score += 2.5
        if query_lower == self.category.lower():
            score += 2.0
        for concept in self.source_metadata.concepts:
            if query_lower in concept.lower() or concept.lower() in query_lower:
                score += 1.5
        words = query_lower.split()
        for word in words:
            if len(word) < 3:
                continue
            if word in self.title.lower():
                score += 0.5
            if word in self.content.lower():
                score += 0.2
            for tag in self.tags:
                if word in tag.lower():
                    score += 0.3
        return score

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "domain": self.domain.value,
            "category": self.category,
            "subcategory": self.subcategory,
            "source_metadata": self.source_metadata.to_dict(),
            "tags": self.tags,
            "difficulty": self.difficulty.value,
            "prerequisites": self.prerequisites,
            "related": self.related,
            "examples": self.examples,
            "references": self.references,
            "chunk_count": len(self.chunks),
            "metadata": self.metadata,
        }


@dataclass
class VedicKnowledgeDomain:
    """A domain of Vedic knowledge containing related entries."""
    name: VedicDomain
    description: str
    entries: dict[str, VedicKnowledgeEntry] = field(default_factory=dict)
    subcategories: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def add_entry(self, entry: VedicKnowledgeEntry):
        self.entries[entry.id] = entry
        logger.debug(f"[VEDIC] Added entry {entry.id} to domain {self.name.value}")

    def get_entry(self, entry_id: str) -> Optional[VedicKnowledgeEntry]:
        return self.entries.get(entry_id)

    def search(self, query: str, limit: int = 10) -> list[VedicKnowledgeEntry]:
        scored = []
        for entry in self.entries.values():
            score = entry.matches_query(query)
            if score > 0:
                scored.append((score, entry))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [entry for _, entry in scored[:limit]]

    def list_entries(self) -> list[str]:
        return list(self.entries.keys())


@dataclass
class VedicKnowledgeBase:
    """Global Vedic knowledge base containing multiple domains."""
    domains: dict[str, VedicKnowledgeDomain] = field(default_factory=dict)
    version: str = "1.0.0"
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())
    stats: dict = field(default_factory=dict)

    def add_domain(self, domain: VedicKnowledgeDomain):
        self.domains[domain.name.value] = domain
        logger.debug(f"[VEDIC] Added domain: {domain.name.value}")
        self._update_stats()

    def get_domain(self, name: str | VedicDomain) -> Optional[VedicKnowledgeDomain]:
        key = name.value if isinstance(name, VedicDomain) else name
        return self.domains.get(key)

    def search(self, query: str, domain: str | VedicDomain | None = None, limit: int = 20) -> list[tuple[float, VedicKnowledgeEntry]]:
        results = []
        if domain:
            d = self.get_domain(domain)
            if d:
                for entry in d.search(query, limit):
                    score = entry.matches_query(query)
                    results.append((score, entry))
        else:
            for d in self.domains.values():
                for entry in d.search(query, limit):
                    score = entry.matches_query(query)
                    results.append((score, entry))
        results.sort(key=lambda x: x[0], reverse=True)
        return results[:limit]

    def get_entry(self, entry_id: str) -> Optional[VedicKnowledgeEntry]:
        for domain in self.domains.values():
            entry = domain.get_entry(entry_id)
            if entry:
                return entry
        return None

    def list_domains(self) -> list[str]:
        return list(self.domains.keys())

    def list_entries(self, domain: str | VedicDomain | None = None) -> list[str]:
        if domain:
            d = self.get_domain(domain)
            if d:
                return d.list_entries()
            return []
        all_entries = []
        for d in self.domains.values():
            all_entries.extend(d.list_entries())
        return all_entries

    def _update_stats(self):
        total_entries = sum(len(d.entries) for d in self.domains.values())
        total_chunks = sum(
            len(e.chunks)
            for d in self.domains.values()
            for e in d.entries.values()
        )
        self.stats = {
            "domains": len(self.domains),
            "total_entries": total_entries,
            "total_chunks": total_chunks,
            "domain_names": self.list_domains(),
            "version": self.version,
            "last_updated": self.last_updated,
        }

    def get_stats(self) -> dict:
        return self.stats


@dataclass
class QueryResult:
    """Result from a Vedic knowledge query."""
    query: str
    entries: list[VedicKnowledgeEntry]
    domain_filter: Optional[str]
    total_found: int
    suggestions: list[str]
    language: Language = Language.ENGLISH
    response_depth: str = "intermediate"

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "total_found": self.total_found,
            "domain_filter": self.domain_filter,
            "language": self.language.value,
            "response_depth": self.response_depth,
            "entries": [e.to_dict() for e in self.entries],
            "suggestions": self.suggestions,
        }


@dataclass
class WebSearchResult:
    """Result from web search with validation metadata."""
    query: str
    url: str
    title: str
    snippet: str
    source_type: SourceType
    validation_status: str
    confidence: float
    retrieved_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "url": self.url,
            "title": self.title,
            "snippet": self.snippet,
            "source_type": self.source_type.value,
            "validation_status": self.validation_status,
            "confidence": self.confidence,
            "retrieved_at": self.retrieved_at,
        }


@dataclass
class ExplainResult:
    """Result from an explain request."""
    topic: str
    explanation: str
    entries_used: list[str]
    depth: str
    language: Language