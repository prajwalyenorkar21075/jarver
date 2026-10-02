"""Concept graph for cross-domain knowledge retrieval."""

from __future__ import annotations

import logging
import json
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path
from collections import defaultdict

from .base import KnowledgeEntry, KnowledgeBase

logger = logging.getLogger(__name__)


@dataclass
class ConceptNode:
    name: str
    canonical_name: str
    aliases: list[str] = field(default_factory=list)
    domains: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    related_concepts: dict[str, float] = field(default_factory=dict)
    entry_ids: list[str] = field(default_factory=list)
    source_evidence: dict[str, list[str]] = field(default_factory=dict)
    definition: Optional[str] = None
    languages: dict[str, str] = field(default_factory=dict)

    def add_alias(self, alias: str):
        if alias and alias not in self.aliases:
            self.aliases.append(alias)

    def add_related(self, concept: str, weight: float = 1.0):
        if concept != self.canonical_name:
            self.related_concepts[concept] = self.related_concepts.get(concept, 0.0) + weight

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "canonical_name": self.canonical_name,
            "aliases": self.aliases,
            "domains": self.domains,
            "categories": self.categories,
            "related_concepts": self.related_concepts,
            "entry_ids": self.entry_ids,
            "source_evidence": self.source_evidence,
            "definition": self.definition,
            "languages": self.languages,
        }


class ConceptGraph:
    """Graph of concepts extracted from the knowledge corpus with evidence-based relationships."""

    def __init__(self):
        self._concepts: dict[str, ConceptNode] = {}
        self._alias_index: dict[str, str] = {}
        self._domain_concepts: dict[str, set[str]] = defaultdict(set)
        self._category_concepts: dict[str, set[str]] = defaultdict(set)
        self._built = False

    def build_from_knowledge_base(self, kb: KnowledgeBase, min_cooccurrence: int = 2) -> int:
        self._concepts.clear()
        self._alias_index.clear()
        self._domain_concepts.clear()
        self._category_concepts.clear()

        concept_entries: dict[str, list[str]] = defaultdict(list)
        concept_domains: dict[str, set[str]] = defaultdict(set)
        concept_categories: dict[str, set[str]] = defaultdict(set)

        for domain_name, domain in kb.domains.items():
            for entry in domain.entries.values():
                concepts = entry.metadata.get("concepts", [])
                topics = entry.metadata.get("topics", [])
                keywords = entry.metadata.get("keywords", entry.tags)

                all_concepts = list(set(concepts + topics + keywords))

                for concept in all_concepts:
                    if not concept or len(concept) < 2:
                        continue
                    canonical = self._normalize_concept(concept)
                    concept_entries[canonical].append(entry.id)
                    concept_domains[canonical].add(domain_name)
                    concept_categories[canonical].add(entry.category)

        for canonical, entry_ids in concept_entries.items():
            if len(entry_ids) < 1:
                continue

            node = ConceptNode(
                name=canonical,
                canonical_name=canonical,
                domains=list(concept_domains.get(canonical, [])),
                categories=list(concept_categories.get(canonical, [])),
                entry_ids=entry_ids,
            )

            for alias in self._get_aliases_for_concept(canonical, kb):
                node.add_alias(alias)
                self._alias_index[alias.lower()] = canonical

            self._concepts[canonical] = node
            for domain in node.domains:
                self._domain_concepts[domain].add(canonical)
            for category in node.categories:
                self._category_concepts[category].add(canonical)

        self._build_relationships(kb, min_cooccurrence)
        self._built = True
        logger.info(f"[CONCEPT_GRAPH] Built graph with {len(self._concepts)} concepts")
        return len(self._concepts)

    def _normalize_concept(self, concept: str) -> str:
        return concept.strip().lower().replace(" ", "_").replace("-", "_")

    def _get_aliases_for_concept(self, canonical: str, kb: KnowledgeBase) -> list[str]:
        aliases = set()
        for domain in kb.domains.values():
            for entry in domain.entries.values():
                concepts = entry.metadata.get("concepts", [])
                topics = entry.metadata.get("topics", [])
                keywords = entry.metadata.get("keywords", entry.tags)
                all_terms = concepts + topics + keywords

                for term in all_terms:
                    if self._normalize_concept(term) == canonical:
                        aliases.add(term)
                        if entry.metadata.get("translation_language"):
                            lang = entry.metadata.get("translation_language")
                            if lang not in self._concepts.get(canonical, ConceptNode("", "")).languages:
                                pass

        return list(aliases)

    def _build_relationships(self, kb: KnowledgeBase, min_cooccurrence: int):
        concept_cooccurrence: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

        for domain in kb.domains.values():
            for entry in domain.entries.values():
                concepts = entry.metadata.get("concepts", [])
                topics = entry.metadata.get("topics", [])
                keywords = entry.metadata.get("keywords", entry.tags)
                all_concepts = list(set(c.lower() for c in concepts + topics + keywords if c.strip()))

                for i, c1 in enumerate(all_concepts):
                    norm1 = self._normalize_concept(c1)
                    if norm1 not in self._concepts:
                        continue
                    for c2 in all_concepts[i+1:]:
                        norm2 = self._normalize_concept(c2)
                        if norm2 not in self._concepts:
                            continue
                        concept_cooccurrence[norm1][norm2] += 1
                        concept_cooccurrence[norm2][norm1] += 1

        for c1, related in concept_cooccurrence.items():
            for c2, count in related.items():
                if count >= min_cooccurrence:
                    node1 = self._concepts.get(c1)
                    node2 = self._concepts.get(c2)
                    if node1 and node2:
                        weight = count / max(len(node1.entry_ids), len(node2.entry_ids))
                        node1.add_related(c2, weight)
                        node2.add_related(c1, weight)

                        self._add_source_evidence(node1, c2, kb)
                        self._add_source_evidence(node2, c1, kb)

    def _add_source_evidence(self, node: ConceptNode, related_concept: str, kb: KnowledgeBase):
        for entry_id in node.entry_ids:
            entry = kb.get_entry(entry_id)
            if not entry:
                continue
            related_entry_ids = self._concepts.get(related_concept, ConceptNode("", "")).entry_ids
            if entry_id in related_entry_ids:
                source = entry.metadata.get("source", "unknown")
                if source not in node.source_evidence:
                    node.source_evidence[source] = []
                if related_concept not in node.source_evidence[source]:
                    node.source_evidence[source].append(related_concept)

    def get_concept(self, name: str) -> Optional[ConceptNode]:
        normalized = self._normalize_concept(name)
        if normalized in self._concepts:
            return self._concepts[normalized]
        alias_canonical = self._alias_index.get(normalized)
        if alias_canonical and alias_canonical in self._concepts:
            return self._concepts[alias_canonical]
        return None

    def get_related_concepts(self, concept: str, limit: int = 10, min_weight: float = 0.1) -> list[tuple[str, float]]:
        node = self.get_concept(concept)
        if not node:
            return []

        related = [(c, w) for c, w in node.related_concepts.items() if w >= min_weight]
        related.sort(key=lambda x: x[1], reverse=True)
        return related[:limit]

    def get_concepts_by_domain(self, domain: str) -> list[ConceptNode]:
        concept_names = self._domain_concepts.get(domain, set())
        return [self._concepts[c] for c in concept_names if c in self._concepts]

    def get_concepts_by_category(self, category: str) -> list[ConceptNode]:
        concept_names = self._category_concepts.get(category, set())
        return [self._concepts[c] for c in concept_names if c in self._concepts]

    def find_concepts(self, query: str, limit: int = 10) -> list[ConceptNode]:
        query_lower = query.lower().strip()
        results = []

        for canonical, node in self._concepts.items():
            score = 0.0
            if query_lower == canonical:
                score = 10.0
            elif query_lower in canonical:
                score = 5.0
            elif any(query_lower in alias.lower() for alias in node.aliases):
                score = 4.0
            elif any(query_lower in alias.lower() for alias in node.languages.values()):
                score = 3.5

            if score > 0:
                results.append((score, node))

        results.sort(key=lambda x: x[0], reverse=True)
        return [node for _, node in results[:limit]]

    def get_cross_domain_concepts(self, concept: str) -> dict[str, list[str]]:
        node = self.get_concept(concept)
        if not node:
            return {}

        result = defaultdict(list)
        for related_name, weight in node.related_concepts.items():
            related_node = self._concepts.get(related_name)
            if related_node:
                for domain in related_node.domains:
                    if domain not in node.domains:
                        result[domain].append(related_name)
        return dict(result)

    def get_stats(self) -> dict:
        return {
            "total_concepts": len(self._concepts),
            "total_aliases": len(self._alias_index),
            "domains_covered": len(self._domain_concepts),
            "categories_covered": len(self._category_concepts),
            "total_relationships": sum(len(n.related_concepts) for n in self._concepts.values()),
        }

    def export_graph(self, path: str | Path) -> bool:
        try:
            path = Path(path)
            path.parent.mkdir(parents=True, exist_ok=True)

            data = {
                "concepts": {k: v.to_dict() for k, v in self._concepts.items()},
                "alias_index": self._alias_index,
                "domain_concepts": {k: list(v) for k, v in self._domain_concepts.items()},
                "category_concepts": {k: list(v) for k, v in self._category_concepts.items()},
            }
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            logger.info(f"[CONCEPT_GRAPH] Graph exported to {path}")
            return True
        except Exception as e:
            logger.error(f"[CONCEPT_GRAPH] Failed to export graph: {e}")
            return False

    def import_graph(self, path: str | Path) -> bool:
        try:
            path = Path(path)
            if not path.exists():
                return False

            data = json.loads(path.read_text(encoding="utf-8"))

            self._concepts = {k: ConceptNode(**v) for k, v in data.get("concepts", {}).items()}
            self._alias_index = data.get("alias_index", {})
            self._domain_concepts = {k: set(v) for k, v in data.get("domain_concepts", {}).items()}
            self._category_concepts = {k: set(v) for k, v in data.get("category_concepts", {}).items()}
            self._built = True

            logger.info(f"[CONCEPT_GRAPH] Graph imported from {path} ({len(self._concepts)} concepts)")
            return True
        except Exception as e:
            logger.error(f"[CONCEPT_GRAPH] Failed to import graph: {e}")
            return False


_concept_graph: ConceptGraph | None = None


def get_concept_graph() -> ConceptGraph:
    global _concept_graph
    if _concept_graph is None:
        _concept_graph = ConceptGraph()
    return _concept_graph