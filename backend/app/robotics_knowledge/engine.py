"""Knowledge engine — high-level query and retrieval interface."""

import logging
from dataclasses import dataclass
from typing import Optional
from .base import KnowledgeBase, KnowledgeEntry, KnowledgeDomain

logger = logging.getLogger(__name__)


@dataclass
class QueryResult:
    """Result from a knowledge query."""
    query: str
    entries: list[KnowledgeEntry]
    domain_filter: Optional[str]
    total_found: int
    suggestions: list[str]

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "total_found": self.total_found,
            "domain_filter": self.domain_filter,
            "entries": [
                {
                    "id": e.id,
                    "title": e.title,
                    "content": e.content,
                    "domain": e.domain,
                    "category": e.category,
                    "tags": e.tags,
                    "difficulty": e.difficulty.value,
                    "examples": e.examples,
                    "score": 0,
                }
                for e in self.entries
            ],
            "suggestions": self.suggestions,
        }


class KnowledgeEngine:
    """High-level interface for querying the robotics knowledge base."""

    def __init__(self, knowledge_base: KnowledgeBase):
        self.kb = knowledge_base
        self._query_history: list[str] = []

    def query(
        self,
        query: str,
        domain: str | None = None,
        limit: int = 10,
        min_score: float = 0.5,
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
            domain_filter=domain,
            total_found=len(entries),
            suggestions=suggestions,
        )

    def explain(self, topic: str, depth: str = "intermediate") -> str:
        result = self.query(topic, limit=5)
        if not result.entries:
            return f"No knowledge found for '{topic}'. Try rephrasing or checking available domains."

        output = []
        for entry in result.entries:
            output.append(f"## {entry.title}")
            output.append(f"**Domain:** {entry.domain} | **Category:** {entry.category}")
            output.append(f"**Difficulty:** {entry.difficulty.value}")
            output.append("")
            output.append(entry.content)

            if entry.examples:
                output.append("")
                output.append("### Examples:")
                for ex in entry.examples:
                    output.append(f"- {ex}")

            if entry.references:
                output.append("")
                output.append("### References:")
                for ref in entry.references:
                    output.append(f"- {ref}")

            output.append("")
            output.append("---")
            output.append("")

        return "\n".join(output)

    def troubleshoot(self, problem: str) -> str:
        result = self.query(problem, limit=10)
        if not result.entries:
            return f"No troubleshooting information found for '{problem}'."

        output = [f"# Troubleshooting: {problem}", ""]
        for entry in result.entries:
            if "troubleshoot" in entry.tags or "error" in entry.tags or "debug" in entry.tags:
                output.append(f"## {entry.title}")
                output.append(entry.content)
                if entry.examples:
                    output.append("")
                    output.append("**Solutions:**")
                    for ex in entry.examples:
                        output.append(f"- {ex}")
                output.append("")

        if len(output) == 2:
            output.append("Related knowledge that might help:")
            output.append("")
            for entry in result.entries[:5]:
                output.append(f"- **{entry.title}**: {entry.content[:200]}...")

        return "\n".join(output)

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
                "domain": entry.domain,
                "prerequisites": entry.prerequisites,
            })

        return path

    def get_domain_overview(self, domain_name: str) -> str:
        domain = self.kb.get_domain(domain_name)
        if not domain:
            available = ", ".join(self.kb.list_domains())
            return f"Domain '{domain_name}' not found. Available domains: {available}"

        output = [
            f"# {domain.name}",
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
                output.append(f"- **{entry.title}** [{entry.difficulty.value}]")
            if len(entries) > 5:
                output.append(f"- ... and {len(entries) - 5} more")
            output.append("")

        return "\n".join(output)

    def _generate_suggestions(self, query: str) -> list[str]:
        suggestions = []
        query_lower = query.lower()

        domain_keywords = {
            "python": ["python", "scripting", "programming"],
            "c++": ["c++", "cpp", "embedded"],
            "ros2": ["ros2", "ros", "robot operating system"],
            "plc": ["plc", "ladder logic", "industrial"],
            "hmi": ["hmi", "scada", "interface"],
            "sensors": ["sensor", "detection", "measurement"],
            "actuators": ["actuator", "motor", "movement"],
            "vision": ["vision", "opencv", "yolo", "camera"],
            "ai": ["ai", "ml", "machine learning", "neural"],
            "electronics": ["circuit", "voltage", "current", "electronics"],
        }

        for domain, keywords in domain_keywords.items():
            if any(kw in query_lower for kw in keywords):
                suggestions.append(f"Try searching in the '{domain}' domain")

        if not suggestions:
            suggestions.append("Try broader terms like 'robotics', 'programming', or 'sensors'")
            suggestions.append("Check available domains with: list_domains()")

        return suggestions

    def get_stats(self) -> dict:
        return self.kb.get_stats()
