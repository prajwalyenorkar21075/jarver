"""Corpus ingestion, validation, and versioning system."""

from __future__ import annotations

import logging
import json
import hashlib
import shutil
from dataclasses import dataclass, field, asdict
from typing import Optional
from datetime import datetime
from pathlib import Path
from enum import Enum
from collections import defaultdict

from .base import KnowledgeEntry, KnowledgeDomain, KnowledgeBase, DifficultyLevel
from .embeddings import EmbeddingEngine, ChunkMetadata, build_embeddings_from_kb, get_embedding_engine
from .concept_graph import ConceptGraph, get_concept_graph

logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    severity: ValidationSeverity
    code: str
    message: str
    entry_id: Optional[str] = None
    field: Optional[str] = None
    suggested_fix: Optional[str] = None


@dataclass
class CorpusValidationReport:
    total_documents: int = 0
    total_chunks: int = 0
    errors: list[ValidationIssue] = field(default_factory=list)
    warnings: list[ValidationIssue] = field(default_factory=list)
    info: list[ValidationIssue] = field(default_factory=list)
    duplicate_documents: list[str] = field(default_factory=list)
    duplicate_chunks: list[str] = field(default_factory=list)
    missing_metadata_fields: dict[str, int] = field(default_factory=dict)
    malformed_files: list[str] = field(default_factory=list)
    empty_documents: list[str] = field(default_factory=list)
    unsupported_formats: list[str] = field(default_factory=list)
    invalid_references: list[str] = field(default_factory=list)
    validated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    corpus_version: str = ""

    def add_issue(self, issue: ValidationIssue):
        if issue.severity == ValidationSeverity.ERROR:
            self.errors.append(issue)
        elif issue.severity == ValidationSeverity.WARNING:
            self.warnings.append(issue)
        else:
            self.info.append(issue)

    def has_errors(self) -> bool:
        return len(self.errors) > 0

    def summary(self) -> dict:
        return {
            "total_documents": self.total_documents,
            "total_chunks": self.total_chunks,
            "errors": len(self.errors),
            "warnings": len(self.warnings),
            "info": len(self.info),
            "duplicates": len(self.duplicate_documents) + len(self.duplicate_chunks),
            "has_errors": self.has_errors(),
            "validated_at": self.validated_at,
            "corpus_version": self.corpus_version,
        }


REQUIRED_METADATA_FIELDS = [
    "source",
    "source_type",
    "original_language",
    "translation_language",
]

OPTIONAL_METADATA_FIELDS = [
    "author",
    "translator",
    "commentator",
    "tradition",
    "chapter",
    "section",
    "verse",
    "topics",
    "concepts",
    "keywords",
    "historical_context",
    "interpretation_type",
    "source_url",
    "retrieved_at",
]

VALID_SOURCE_TYPES = {
    "primary_text",
    "translation",
    "traditional_commentary",
    "scholarly_reference",
    "historical_reference",
    "secondary_source",
    "summary",
}

SUPPORTED_FORMATS = {".json", ".txt", ".md"}


def validate_entry(entry: KnowledgeEntry, report: CorpusValidationReport):
    if not entry.id:
        report.add_issue(ValidationIssue(
            ValidationSeverity.ERROR, "MISSING_ID", "Entry has no ID", entry_id=entry.id, field="id"
        ))

    if not entry.title or not entry.title.strip():
        report.add_issue(ValidationIssue(
            ValidationSeverity.ERROR, "MISSING_TITLE", "Entry has no title", entry_id=entry.id, field="title"
        ))

    if not entry.content or not entry.content.strip():
        report.add_issue(ValidationIssue(
            ValidationSeverity.ERROR, "EMPTY_CONTENT", "Entry has no content", entry_id=entry.id, field="content"
        ))
        report.empty_documents.append(entry.id)
        return

    if not entry.domain:
        report.add_issue(ValidationIssue(
            ValidationSeverity.ERROR, "MISSING_DOMAIN", "Entry has no domain", entry_id=entry.id, field="domain"
        ))

    if not entry.category:
        report.add_issue(ValidationIssue(
            ValidationSeverity.ERROR, "MISSING_CATEGORY", "Entry has no category", entry_id=entry.id, field="category"
        ))

    for field_name in REQUIRED_METADATA_FIELDS:
        if field_name not in entry.metadata or not entry.metadata[field_name]:
            report.add_issue(ValidationIssue(
                ValidationSeverity.WARNING, "MISSING_METADATA", f"Missing required metadata: {field_name}",
                entry_id=entry.id, field=field_name
            ))
            report.missing_metadata_fields[field_name] = report.missing_metadata_fields.get(field_name, 0) + 1

    source_type = entry.metadata.get("source_type", "")
    if source_type and source_type not in VALID_SOURCE_TYPES:
        report.add_issue(ValidationIssue(
            ValidationSeverity.WARNING, "INVALID_SOURCE_TYPE", f"Invalid source_type: {source_type}",
            entry_id=entry.id, field="source_type", suggested_fix=f"Use one of: {', '.join(VALID_SOURCE_TYPES)}"
        ))

    if entry.metadata.get("source_url"):
        url = entry.metadata["source_url"]
        if not (url.startswith("http://") or url.startswith("https://")):
            report.add_issue(ValidationIssue(
                ValidationSeverity.WARNING, "INVALID_URL", f"Invalid source_url format: {url}",
                entry_id=entry.id, field="source_url"
            ))

    for ref in entry.references:
        if not ref or not ref.strip():
            report.add_issue(ValidationIssue(
                ValidationSeverity.WARNING, "EMPTY_REFERENCE", "Empty reference in entry",
                entry_id=entry.id, field="references"
            ))


def validate_knowledge_base(kb: KnowledgeBase) -> CorpusValidationReport:
    report = CorpusValidationReport()
    seen_ids = set()
    seen_content_hashes = set()

    for domain_name, domain in kb.domains.items():
        for entry in domain.entries.values():
            report.total_documents += 1

            if entry.id in seen_ids:
                report.duplicate_documents.append(entry.id)
                report.add_issue(ValidationIssue(
                    ValidationSeverity.ERROR, "DUPLICATE_ID", f"Duplicate entry ID: {entry.id}",
                    entry_id=entry.id, field="id"
                ))
            seen_ids.add(entry.id)

            content_hash = hashlib.md5(entry.content.encode()).hexdigest()
            if content_hash in seen_content_hashes:
                report.duplicate_chunks.append(entry.id)
                report.add_issue(ValidationIssue(
                    ValidationSeverity.WARNING, "DUPLICATE_CONTENT", f"Duplicate content detected: {entry.id}",
                    entry_id=entry.id, field="content"
                ))
            seen_content_hashes.add(content_hash)

            validate_entry(entry, report)

    report.corpus_version = get_corpus_version(kb)
    return report


def get_corpus_version(kb: KnowledgeBase) -> str:
    total_chars = sum(len(e.content) for d in kb.domains.values() for e in d.entries.values())
    total_entries = sum(len(d.entries) for d in kb.domains.values())
    hash_input = f"{total_entries}:{total_chars}:{sorted(kb.domains.keys())}"
    return hashlib.md5(hash_input.encode()).hexdigest()[:12]


@dataclass
class CorpusVersion:
    version: str
    timestamp: str
    documents_added: int = 0
    documents_updated: int = 0
    documents_removed: int = 0
    sources_changed: list[str] = field(default_factory=list)
    description: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


class CorpusManager:
    def __init__(self, corpus_root: str | Path):
        self.corpus_root = Path(corpus_root)
        self.corpus_root.mkdir(parents=True, exist_ok=True)

        self.kb = KnowledgeBase()
        self.embedding_engine = get_embedding_engine()
        self.concept_graph = get_concept_graph()
        self.version_history: list[CorpusVersion] = []
        self.current_version: Optional[CorpusVersion] = None

        self._load_version_history()

    def _load_version_history(self):
        version_file = self.corpus_root / "metadata" / "versions.json"
        if version_file.exists():
            try:
                data = json.loads(version_file.read_text(encoding="utf-8"))
                self.version_history = [CorpusVersion(**v) for v in data.get("versions", [])]
                if self.version_history:
                    self.current_version = self.version_history[-1]
                logger.info(f"[CORPUS] Loaded {len(self.version_history)} versions")
            except Exception as e:
                logger.error(f"[CORPUS] Failed to load version history: {e}")

    def _save_version_history(self):
        version_file = self.corpus_root / "metadata" / "versions.json"
        version_file.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "versions": [v.to_dict() for v in self.version_history],
            "current_version": self.current_version.to_dict() if self.current_version else None,
        }
        version_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def load_corpus(self, rebuild_embeddings: bool = True, rebuild_graph: bool = True) -> CorpusValidationReport:
        self.kb = KnowledgeBase()
        self._load_domains_from_files()

        report = validate_knowledge_base(self.kb)

        if rebuild_embeddings and not report.has_errors():
            logger.info("[CORPUS] Building embeddings...")
            build_embeddings_from_kb(self.kb, self.embedding_engine)

        if rebuild_graph and not report.has_errors():
            logger.info("[CORPUS] Building concept graph...")
            self.concept_graph.build_from_knowledge_base(self.kb)

        self.current_version = CorpusVersion(
            version=get_corpus_version(self.kb),
            timestamp=datetime.now().isoformat(),
            documents_added=report.total_documents,
            description="Corpus loaded and validated",
        )
        self.version_history.append(self.current_version)
        self._save_version_history()

        logger.info(f"[CORPUS] Loaded {report.total_documents} documents, {len(self.kb.domains)} domains")
        return report

    def _load_domains_from_files(self):
        domain_dirs = {
            "vedic_literature": ["upanishads", "brahmanas", "aranyakas", "vedas"],
            "vedangas": ["shiksha", "kalpa", "vyakarana", "nirukta", "chandas", "jyotisha"],
            "itihasa": ["ramayana", "mahabharata"],
            "puranas": ["mahapuranas", "cosmology", "creation", "avatars", "devotion"],
            "bhagavad_gita": ["chapters", "karma_yoga", "jnana_yoga", "bhakti_yoga", "dharma"],
        }

        for domain_name, subcategories in domain_dirs.items():
            domain = KnowledgeDomain(
                name=domain_name,
                description=f"{domain_name.replace('_', ' ').title()} knowledge domain",
                subcategories=subcategories,
            )

            # Check both the expected domain directory and the actual file locations
            domain_path = self.corpus_root / domain_name
            if not domain_path.exists():
                # Fallback: check if files are directly under subcategory directories
                for subcat in subcategories:
                    subcat_path = self.corpus_root / subcat
                    if subcat_path.exists():
                        for file_path in subcat_path.rglob("*.json"):
                            try:
                                self._load_entries_from_file(file_path, domain)
                            except Exception as e:
                                logger.error(f"[CORPUS] Failed to load {file_path}: {e}")
            else:
                for file_path in domain_path.rglob("*.json"):
                    try:
                        self._load_entries_from_file(file_path, domain)
                    except Exception as e:
                        logger.error(f"[CORPUS] Failed to load {file_path}: {e}")

            if domain.entries:
                self.kb.add_domain(domain)

    def _load_entries_from_file(self, file_path: Path, domain: KnowledgeDomain):
        data = json.loads(file_path.read_text(encoding="utf-8"))

        if isinstance(data, list):
            entries_data = data
        elif isinstance(data, dict) and "entries" in data:
            entries_data = data["entries"]
        else:
            entries_data = [data]

        for entry_data in entries_data:
            if not all(k in entry_data for k in ["id", "title", "content", "domain", "category"]):
                logger.warning(f"[CORPUS] Skipping invalid entry in {file_path}")
                continue

            entry = KnowledgeEntry(
                id=entry_data["id"],
                title=entry_data["title"],
                content=entry_data["content"],
                domain=entry_data["domain"],
                category=entry_data["category"],
                tags=entry_data.get("tags", []),
                difficulty=DifficultyLevel(entry_data.get("difficulty", "intermediate")),
                prerequisites=entry_data.get("prerequisites", []),
                related=entry_data.get("related", []),
                examples=entry_data.get("examples", []),
                references=entry_data.get("references", []),
                metadata=entry_data.get("metadata", {}),
            )
            domain.add_entry(entry)

    def add_document(self, entry: KnowledgeEntry, source_file: Optional[str] = None) -> bool:
        domain = self.kb.get_domain(entry.domain)
        if not domain:
            logger.error(f"[CORPUS] Domain not found: {entry.domain}")
            return False

        existing = domain.get_entry(entry.id)
        is_update = existing is not None

        if is_update:
            logger.info(f"[CORPUS] Updating document: {entry.id}")
        else:
            logger.info(f"[CORPUS] Adding document: {entry.id}")

        domain.add_entry(entry)

        chunks = self._chunk_and_embed(entry)
        logger.debug(f"[CORPUS] Added {len(chunks)} chunks to embeddings")

        self.concept_graph.build_from_knowledge_base(self.kb)

        self._create_version_entry(1 if not is_update else 0, 1 if is_update else 0, 0, source_file)

        return True

    def _chunk_and_embed(self, entry: KnowledgeEntry) -> list:
        from .embeddings import chunk_entry
        chunks = chunk_entry(entry)
        if chunks:
            self.embedding_engine.add_chunks_batch(chunks)
        return chunks

    def remove_document(self, entry_id: str) -> bool:
        for domain in self.kb.domains.values():
            if entry_id in domain.entries:
                del domain.entries[entry_id]
                logger.info(f"[CORPUS] Removed document: {entry_id}")
                self._create_version_entry(0, 0, 1, entry_id)
                return True
        return False

    def _create_version_entry(self, added: int, updated: int, removed: int, source: str):
        if self.current_version:
            self.current_version.documents_added += added
            self.current_version.documents_updated += updated
            self.current_version.documents_removed += removed
            if source:
                self.current_version.sources_changed.append(source)
        else:
            self.current_version = CorpusVersion(
                version=get_corpus_version(self.kb),
                timestamp=datetime.now().isoformat(),
                documents_added=added,
                documents_updated=updated,
                documents_removed=removed,
                sources_changed=[source] if source else [],
            )
            self.version_history.append(self.current_version)

        self._save_version_history()

    def save_embeddings(self, path: Optional[str | Path] = None) -> bool:
        if path is None:
            path = self.corpus_root / "index" / "embeddings.json"
        return self.embedding_engine.save_index(path)

    def load_embeddings(self, path: Optional[str | Path] = None) -> bool:
        if path is None:
            path = self.corpus_root / "index" / "embeddings.json"
        return self.embedding_engine.load_index(path)

    def save_concept_graph(self, path: Optional[str | Path] = None) -> bool:
        if path is None:
            path = self.corpus_root / "index" / "concept_graph.json"
        return self.concept_graph.export_graph(path)

    def load_concept_graph(self, path: Optional[str | Path] = None) -> bool:
        if path is None:
            path = self.corpus_root / "index" / "concept_graph.json"
        return self.concept_graph.import_graph(path)

    def validate_corpus(self) -> CorpusValidationReport:
        return validate_knowledge_base(self.kb)

    def get_corpus_stats(self) -> dict:
        kb_stats = self.kb.get_stats()
        embed_stats = self.embedding_engine.get_stats()
        graph_stats = self.concept_graph.get_stats()

        return {
            "knowledge_base": kb_stats,
            "embeddings": embed_stats,
            "concept_graph": graph_stats,
            "versions": len(self.version_history),
            "current_version": self.current_version.to_dict() if self.current_version else None,
        }

    def export_corpus(self, output_path: str | Path) -> bool:
        try:
            output_path = Path(output_path)
            output_path.mkdir(parents=True, exist_ok=True)

            for domain_name, domain in self.kb.domains.items():
                domain_file = output_path / f"{domain_name}.json"
                entries_data = [self._entry_to_dict(e) for e in domain.entries.values()]
                domain_file.write_text(json.dumps(entries_data, ensure_ascii=False, indent=2), encoding="utf-8")

            self.save_embeddings(output_path / "embeddings.json")
            self.save_concept_graph(output_path / "concept_graph.json")

            logger.info(f"[CORPUS] Exported corpus to {output_path}")
            return True
        except Exception as e:
            logger.error(f"[CORPUS] Export failed: {e}")
            return False

    def _entry_to_dict(self, entry: KnowledgeEntry) -> dict:
        return {
            "id": entry.id,
            "title": entry.title,
            "content": entry.content,
            "domain": entry.domain,
            "category": entry.category,
            "tags": entry.tags,
            "difficulty": entry.difficulty.value,
            "prerequisites": entry.prerequisites,
            "related": entry.related,
            "examples": entry.examples,
            "references": entry.references,
            "metadata": entry.metadata,
        }


_corpus_manager: CorpusManager | None = None


def get_corpus_manager(corpus_root: Optional[str | Path] = None) -> CorpusManager:
    global _corpus_manager
    if _corpus_manager is None:
        if corpus_root is None:
            # Go up 5 levels from corpus_manager.py to reach workspace root, then knowledge/vedic
            corpus_root = Path(__file__).parent.parent.parent.parent.parent / "knowledge" / "vedic"
        _corpus_manager = CorpusManager(corpus_root)
    return _corpus_manager