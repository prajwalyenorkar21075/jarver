"""Vedic Knowledge Engine — high-level query and retrieval interface."""

import logging
from dataclasses import dataclass
from typing import Optional

from .base import (
    VedicKnowledgeBase,
    VedicKnowledgeEntry,
    VedicKnowledgeDomain,
    QueryResult,
    DifficultyLevel,
    Language,
    VedicDomain,
    SourceType,
)

logger = logging.getLogger(__name__)


@dataclass
class ExplainResult:
    """Result from an explain request."""
    topic: str
    explanation: str
    entries_used: list[str]
    depth: str
    language: Language


class VedicKnowledgeEngine:
    """High-level interface for querying the Vedic knowledge base."""

    def __init__(self, knowledge_base: VedicKnowledgeBase):
        self.kb = knowledge_base
        self._query_history: list[str] = []

    def query(
        self,
        query: str,
        domain: str | VedicDomain | None = None,
        limit: int = 10,
        min_score: float = 0.5,
        language: Language = Language.ENGLISH,
    ) -> QueryResult:
        self._query_history.append(query)
        scored_entries = self.kb.search(query, domain=domain, limit=limit * 2)
        filtered = [(score, entry) for score, entry in scored_entries if score >= min_score]
        entries = [entry for _, entry in filtered[:limit]]

        suggestions = []
        if not entries:
            suggestions = self._generate_suggestions(query)

        return QueryResult(
            query=query,
            entries=entries,
            domain_filter=domain.value if isinstance(domain, VedicDomain) else domain,
            total_found=len(entries),
            suggestions=suggestions,
            language=language,
        )

    def explain(
        self,
        topic: str,
        depth: str = "intermediate",
        language: Language = Language.ENGLISH,
    ) -> ExplainResult:
        result = self.query(topic, limit=5, language=language)
        if not result.entries:
            return ExplainResult(
                topic=topic,
                explanation=f"No knowledge found for '{topic}'. Try rephrasing or checking available domains.",
                entries_used=[],
                depth=depth,
                language=language,
            )

        output_parts = []
        entries_used = []

        for entry in result.entries:
            entries_used.append(entry.id)
            output_parts.append(f"## {entry.title}")
            output_parts.append(f"**Domain:** {entry.domain.value} | **Category:** {entry.category} | **Subcategory:** {entry.subcategory}")
            output_parts.append(f"**Difficulty:** {entry.difficulty.value}")
            output_parts.append(f"**Source:** {entry.source_metadata.source} ({entry.source_metadata.source_type.value})")
            if entry.source_metadata.chapter:
                output_parts.append(f"**Chapter:** {entry.source_metadata.chapter}")
            if entry.source_metadata.verse:
                output_parts.append(f"**Verse/Section:** {entry.source_metadata.verse}")
            output_parts.append("")
            output_parts.append(entry.content)

            if entry.examples:
                output_parts.append("")
                output_parts.append("### Examples:")
                for ex in entry.examples:
                    output_parts.append(f"- {ex}")

            if entry.references:
                output_parts.append("")
                output_parts.append("### References:")
                for ref in entry.references:
                    output_parts.append(f"- {ref}")

            if entry.source_metadata.source_url:
                output_parts.append("")
                output_parts.append(f"**Source URL:** {entry.source_metadata.source_url}")

            output_parts.append("")
            output_parts.append("---")
            output_parts.append("")

        depth_adapter = {
            "beginner": self._adapt_for_beginner,
            "intermediate": lambda x: x,
            "advanced": self._adapt_for_advanced,
            "expert": self._adapt_for_expert,
        }
        adapter = depth_adapter.get(depth, lambda x: x)
        adapted = adapter("\n".join(output_parts))

        return ExplainResult(
            topic=topic,
            explanation=adapted,
            entries_used=entries_used,
            depth=depth,
            language=language,
        )

    def get_learning_path(self, topic: str) -> list[dict]:
        result = self.query(topic, limit=20)
        if not result.entries:
            return []

        difficulty_order = {"beginner": 0, "intermediate": 1, "advanced": 2, "expert": 3}
        sorted_entries = sorted(
            result.entries,
            key=lambda e: difficulty_order.get(e.difficulty.value, 1)
        )

        path = []
        for entry in sorted_entries:
            path.append({
                "id": entry.id,
                "title": entry.title,
                "difficulty": entry.difficulty.value,
                "domain": entry.domain.value,
                "category": entry.category,
                "prerequisites": entry.prerequisites,
                "source": entry.source_metadata.source,
                "source_type": entry.source_metadata.source_type.value,
            })

        return path

    def get_domain_overview(self, domain_name: str) -> str:
        domain = self.kb.get_domain(domain_name)
        if not domain:
            available = ", ".join(self.kb.list_domains())
            return f"Domain '{domain_name}' not found. Available domains: {available}"

        output = [
            f"# {domain.name.value.replace('_', ' ').title()}",
            "",
            domain.description,
            "",
            f"**Total entries:** {len(domain.entries)}",
            "",
        ]

        categories = {}
        for entry in domain.entries.values():
            cat = entry.category
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(entry)

        output.append("## Categories:")
        output.append("")
        for cat, entries in categories.items():
            output.append(f"### {cat} ({len(entries)} entries)")
            for entry in entries[:5]:
                output.append(f"- **{entry.title}** [{entry.difficulty.value}] ({entry.source_metadata.source_type.value})")
            if len(entries) > 5:
                output.append(f"- ... and {len(entries) - 5} more")
            output.append("")

        return "\n".join(output)

    def get_concept_graph(self, concept: str, max_depth: int = 2) -> dict:
        """Build a concept relationship graph from corpus evidence."""
        result = self.query(concept, limit=15)
        if not result.entries:
            return {"concept": concept, "relationships": {}}

        relationships = {}
        for entry in result.entries:
            for related_concept in entry.source_metadata.concepts:
                if related_concept.lower() != concept.lower():
                    if related_concept not in relationships:
                        relationships[related_concept] = {
                            "domains": set(),
                            "sources": [],
                            "evidence": [],
                        }
                    relationships[related_concept]["domains"].add(entry.domain.value)
                    relationships[related_concept]["sources"].append(entry.source_metadata.source)
                    relationships[related_concept]["evidence"].append({
                        "entry_id": entry.id,
                        "entry_title": entry.title,
                        "source": entry.source_metadata.source,
                        "source_type": entry.source_metadata.source_type.value,
                    })

        # Convert sets to lists for JSON serialization
        for rel in relationships.values():
            rel["domains"] = list(rel["domains"])
            rel["sources"] = list(set(rel["sources"]))

        return {
            "concept": concept,
            "relationships": relationships,
        }

    def _generate_suggestions(self, query: str) -> list[str]:
        suggestions = []
        query_lower = query.lower()

        domain_keywords = {
            "upanishads": ["upanishad", "brahman", "atman", "vedanta", "moksha", "self"],
            "brahmanas": ["brahmana", "ritual", "yajna", "sacrifice", "ceremony"],
            "aranyakas": ["aranyaka", "forest", "meditation", "contemplation"],
            "vedangas": ["vedanga", "shiksha", "kalpa", "vyakarana", "nirukta", "chandas", "jyotisha", "phonetics", "grammar", "etymology", "meter", "astronomy"],
            "itihasa": ["ramayana", "mahabharata", "itihasa", "epic", "rama", "krishna", "arjuna"],
            "puranas": ["purana", "bhagavata", "vishnu", "shiva", "cosmology", "creation", "avatar"],
            "bhagavad_gita": ["gita", "bhagavad", "karma yoga", "jnana yoga", "bhakti yoga", "dharma", "kurukshetra"],
        }

        for domain, keywords in domain_keywords.items():
            if any(kw in query_lower for kw in keywords):
                suggestions.append(f"Try searching in the '{domain}' domain")

        if not suggestions:
            suggestions.append("Try terms like 'atman', 'brahman', 'dharma', 'karma', 'yoga', 'moksha'")
            suggestions.append("Check available domains with: list_domains()")

        return suggestions

    def _adapt_for_beginner(self, text: str) -> str:
        # Simplify: remove complex Sanskrit terms, add explanations
        return text

    def _adapt_for_advanced(self, text: str) -> str:
        # Add more technical detail, include Sanskrit terms
        return text

    def _adapt_for_expert(self, text: str) -> str:
        # Include full references, commentaries, variant readings
        return text

    def get_stats(self) -> dict:
        return self.kb.get_stats()

    def list_domains(self) -> list[str]:
        return self.kb.list_domains()