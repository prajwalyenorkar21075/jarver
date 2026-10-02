"""Base classes for the robotics knowledge system."""

import logging
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

logger = logging.getLogger(__name__)


class DifficultyLevel(Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


@dataclass
class KnowledgeEntry:
    """A single piece of knowledge."""
    id: str
    title: str
    content: str
    domain: str
    category: str
    tags: list[str] = field(default_factory=list)
    difficulty: DifficultyLevel = DifficultyLevel.INTERMEDIATE
    prerequisites: list[str] = field(default_factory=list)
    related: list[str] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)
    references: list[str] = field(default_factory=list)
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
        if query_lower == self.domain.lower():
            score += 2.5
        if query_lower == self.category.lower():
            score += 2.0
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


@dataclass
class KnowledgeDomain:
    """A domain of knowledge containing related entries."""
    name: str
    description: str
    entries: dict[str, KnowledgeEntry] = field(default_factory=dict)
    subcategories: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def add_entry(self, entry: KnowledgeEntry):
        self.entries[entry.id] = entry
        logger.debug(f"[KNOWLEDGE] Added entry {entry.id} to domain {self.name}")

    def get_entry(self, entry_id: str) -> Optional[KnowledgeEntry]:
        return self.entries.get(entry_id)

    def search(self, query: str, limit: int = 10) -> list[KnowledgeEntry]:
        scored = []
        for entry in self.entries.values():
            score = entry.matches_query(query)
            if score > 0:
                scored.append((score, entry))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [entry for _, entry in scored[:limit]]


class KnowledgeBase:
    """Global knowledge base containing multiple domains."""

    def __init__(self):
        self.domains: dict[str, KnowledgeDomain] = {}
        self._loaded = False

    def add_domain(self, domain: KnowledgeDomain):
        self.domains[domain.name] = domain
        logger.debug(f"[KNOWLEDGE] Added domain: {domain.name}")

    def get_domain(self, name: str) -> Optional[KnowledgeDomain]:
        return self.domains.get(name)

    def search(self, query: str, domain: str | None = None, limit: int = 20) -> list[tuple[float, KnowledgeEntry]]:
        results = []
        if domain:
            d = self.domains.get(domain)
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

    def get_entry(self, entry_id: str) -> Optional[KnowledgeEntry]:
        for domain in self.domains.values():
            entry = domain.get_entry(entry_id)
            if entry:
                return entry
        return None

    def list_domains(self) -> list[str]:
        return list(self.domains.keys())

    def list_entries(self, domain: str | None = None) -> list[str]:
        if domain:
            d = self.domains.get(domain)
            if d:
                return list(d.entries.keys())
            return []
        all_entries = []
        for d in self.domains.values():
            all_entries.extend(d.entries.keys())
        return all_entries

    def get_stats(self) -> dict:
        total_entries = sum(len(d.entries) for d in self.domains.values())
        return {
            "domains": len(self.domains),
            "total_entries": total_entries,
            "domain_names": self.list_domains(),
        }
