"""Corpus ingestion system for Vedic Knowledge."""

import logging
import hashlib
import json
import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..base import (
    VedicKnowledgeBase,
    VedicKnowledgeDomain,
    VedicKnowledgeEntry,
    KnowledgeChunk,
    SourceMetadata,
    SourceType,
    DifficultyLevel,
    Language,
    VedicDomain,
)
from ..validation.validator import CorpusValidator, get_source_validator

logger = logging.getLogger(__name__)


@dataclass
class IngestionConfig:
    """Configuration for ingestion."""
    chunk_size: int = 1000
    chunk_overlap: int = 200
    min_chunk_size: int = 100
    max_chunk_size: int = 2000
    deduplicate: bool = True
    validate_metadata: bool = True
    generate_embeddings: bool = False
    supported_formats: list[str] = field(default_factory=lambda: [".json", ".txt", ".md"])


@dataclass
class IngestionResult:
    """Result of ingestion operation."""
    files_processed: int = 0
    entries_added: int = 0
    chunks_created: int = 0
    duplicates_skipped: int = 0
    errors: list[dict] = field(default_factory=list)
    validation_report: str = ""


class DocumentIngester:
    """Ingest documents into the Vedic knowledge base."""

    def __init__(self, knowledge_base: VedicKnowledgeBase, config: IngestionConfig | None = None):
        self.kb = knowledge_base
        self.config = config or IngestionConfig()
        self._validator = get_source_validator()
        self._corpus_validator = CorpusValidator(knowledge_base)
        self._existing_hashes: set[str] = set()
        self._load_existing_hashes()

    def _load_existing_hashes(self):
        """Load hashes of existing documents for deduplication."""
        for domain in self.kb.domains.values():
            for entry in domain.entries.values():
                content_hash = hashlib.md5(entry.content.encode()).hexdigest()
                self._existing_hashes.add(content_hash)
                for chunk in entry.chunks:
                    chunk_hash = hashlib.md5(chunk.content.encode()).hexdigest()
                    self._existing_hashes.add(chunk_hash)

    def ingest_directory(self, path: str | Path) -> IngestionResult:
        """Ingest all supported files from a directory."""
        path = Path(path)
        if not path.exists():
            return IngestionResult(errors=[{"path": str(path), "error": "Directory not found"}])

        result = IngestionResult()

        for file_path in path.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in self.config.supported_formats:
                try:
                    file_result = self.ingest_file(file_path)
                    result.files_processed += 1
                    result.entries_added += file_result.entries_added
                    result.chunks_created += file_result.chunks_created
                    result.duplicates_skipped += file_result.duplicates_skipped
                    result.errors.extend(file_result.errors)
                except Exception as e:
                    logger.error(f"[INGESTION] Error processing {file_path}: {e}")
                    result.errors.append({"path": str(file_path), "error": str(e)})

        # Run validation after ingestion
        if result.entries_added > 0:
            validation = self._corpus_validator.validate_all()
            result.validation_report = self._corpus_validator.generate_report()

        return result

    def ingest_file(self, file_path: Path) -> IngestionResult:
        """Ingest a single file."""
        result = IngestionResult()

        try:
            if file_path.suffix.lower() == ".json":
                file_result = self._ingest_json(file_path)
            elif file_path.suffix.lower() in [".txt", ".md"]:
                file_result = self._ingest_text(file_path)
            else:
                result.errors.append({"path": str(file_path), "error": f"Unsupported format: {file_path.suffix}"})
                return result

            result.files_processed = 1
            result.entries_added = file_result.entries_added
            result.chunks_created = file_result.chunks_created
            result.duplicates_skipped = file_result.duplicates_skipped
            result.errors = file_result.errors

        except Exception as e:
            logger.error(f"[INGESTION] Error ingesting {file_path}: {e}")
            result.errors.append({"path": str(file_path), "error": str(e)})

        return result

    def _ingest_json(self, file_path: Path) -> IngestionResult:
        """Ingest a JSON file with knowledge entries."""
        result = IngestionResult()

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Handle different JSON structures
        entries_data = data if isinstance(data, list) else data.get("entries", [])

        for entry_data in entries_data:
            try:
                entry = self._create_entry_from_dict(entry_data)
                if entry:
                    add_result = self._add_entry(entry)
                    result.entries_added += add_result[0]
                    result.chunks_created += add_result[1]
                    result.duplicates_skipped += add_result[2]
            except Exception as e:
                result.errors.append({"entry": entry_data.get("id", "unknown"), "error": str(e)})

        return result

    def _ingest_text(self, file_path: Path) -> IngestionResult:
        """Ingest a plain text or markdown file."""
        result = IngestionResult()

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Create a basic entry from the file
        # In production, this would parse structured content
        entry_data = {
            "id": file_path.stem,
            "title": file_path.stem.replace("_", " ").title(),
            "content": content,
            "domain": "vedic_literature",
            "category": "general",
            "subcategory": "ingested",
            "source_metadata": {
                "title": file_path.name,
                "source": str(file_path),
                "source_type": "secondary_source",
                "category": "general",
                "subcategory": "ingested",
            },
        }

        try:
            entry = self._create_entry_from_dict(entry_data)
            if entry:
                add_result = self._add_entry(entry)
                result.entries_added = add_result[0]
                result.chunks_created = add_result[1]
                result.duplicates_skipped = add_result[2]
        except Exception as e:
            result.errors.append({"path": str(file_path), "error": str(e)})

        return result

    def _create_entry_from_dict(self, data: dict) -> Optional[VedicKnowledgeEntry]:
        """Create a VedicKnowledgeEntry from a dictionary."""
        # Required fields
        entry_id = data.get("id", hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()[:12])
        title = data.get("title", "Untitled")
        content = data.get("content", "")

        if not content:
            return None

        # Domain
        domain_str = data.get("domain", "vedic_literature")
        try:
            domain = VedicDomain(domain_str)
        except ValueError:
            domain = VedicDomain.VEDIC_LITERATURE

        # Source metadata
        meta_data = data.get("source_metadata", {})
        source_metadata = SourceMetadata(
            title=meta_data.get("title", title),
            category=meta_data.get("category", data.get("category", "general")),
            subcategory=meta_data.get("subcategory", data.get("subcategory", "general")),
            source=meta_data.get("source", data.get("source", "unknown")),
            source_type=SourceType(meta_data.get("source_type", "secondary_source")),
            author=meta_data.get("author", ""),
            translator=meta_data.get("translator", ""),
            commentator=meta_data.get("commentator", ""),
            original_language=meta_data.get("original_language", ""),
            translation_language=meta_data.get("translation_language", ""),
            tradition=meta_data.get("tradition", ""),
            chapter=meta_data.get("chapter", ""),
            section=meta_data.get("section", ""),
            verse=meta_data.get("verse", ""),
            topics=meta_data.get("topics", data.get("topics", [])),
            concepts=meta_data.get("concepts", data.get("concepts", [])),
            keywords=meta_data.get("keywords", data.get("keywords", [])),
            historical_context=meta_data.get("historical_context", ""),
            interpretation_type=meta_data.get("interpretation_type", ""),
            source_url=meta_data.get("source_url", ""),
        )

        # Validate metadata
        if self.config.validate_metadata:
            validation = self._validator.validate_metadata(source_metadata)
            if not validation.is_valid:
                logger.warning(f"[INGESTION] Metadata validation failed for {entry_id}: {validation.issues}")

        # Create entry
        entry = VedicKnowledgeEntry(
            id=entry_id,
            title=title,
            content=content,
            domain=domain,
            category=source_metadata.category,
            subcategory=source_metadata.subcategory,
            source_metadata=source_metadata,
            tags=data.get("tags", []),
            difficulty=DifficultyLevel(data.get("difficulty", "intermediate")),
            prerequisites=data.get("prerequisites", []),
            related=data.get("related", []),
            examples=data.get("examples", []),
            references=data.get("references", []),
            metadata=data.get("metadata", {}),
        )

        # Create chunks
        chunks = self._chunk_content(entry)
        entry.chunks = chunks

        return entry

    def _chunk_content(self, entry: VedicKnowledgeEntry) -> list[KnowledgeChunk]:
        """Split content into chunks."""
        chunks = []
        content = entry.content

        # Simple chunking by paragraphs first
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]

        current_chunk = ""
        chunk_index = 0

        for para in paragraphs:
            # If adding this paragraph would exceed max size, save current chunk
            if len(current_chunk) + len(para) > self.config.max_chunk_size and current_chunk:
                chunk = self._create_chunk(entry, current_chunk.strip(), chunk_index)
                chunks.append(chunk)
                chunk_index += 1
                current_chunk = para
            else:
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para

        # Add final chunk
        if current_chunk and len(current_chunk) >= self.config.min_chunk_size:
            chunk = self._create_chunk(entry, current_chunk.strip(), chunk_index)
            chunks.append(chunk)

        # If no chunks created (content too small), create single chunk
        if not chunks and content.strip():
            chunks.append(self._create_chunk(entry, content.strip(), 0))

        # Update total_chunks in each chunk
        for chunk in chunks:
            chunk.total_chunks = len(chunks)

        return chunks

    def _create_chunk(self, entry: VedicKnowledgeEntry, content: str, index: int) -> KnowledgeChunk:
        """Create a knowledge chunk."""
        chunk_id = f"{entry.id}_chunk_{index}"
        return KnowledgeChunk(
            id=chunk_id,
            content=content,
            source_metadata=entry.source_metadata,
            language=Language.ENGLISH,
            chunk_index=index,
            total_chunks=1,  # Will be updated
        )

    def _add_entry(self, entry: VedicKnowledgeEntry) -> tuple[int, int, int]:
        """Add entry to knowledge base with deduplication."""
        # Check content hash for deduplication
        content_hash = hashlib.md5(entry.content.encode()).hexdigest()
        if self.config.deduplicate and content_hash in self._existing_hashes:
            logger.info(f"[INGESTION] Skipping duplicate entry: {entry.id}")
            return (0, 0, 1)

        # Get or create domain
        domain = self.kb.get_domain(entry.domain)
        if not domain:
            domain = VedicKnowledgeDomain(
                name=entry.domain,
                description=f"{entry.domain.value.replace('_', ' ').title()} domain",
            )
            self.kb.add_domain(domain)

        # Add entry
        domain.add_entry(entry)

        # Update hashes
        self._existing_hashes.add(content_hash)
        for chunk in entry.chunks:
            chunk_hash = hashlib.md5(chunk.content.encode()).hexdigest()
            self._existing_hashes.add(chunk_hash)

        logger.info(f"[INGESTION] Added entry: {entry.id} with {len(entry.chunks)} chunks")
        return (1, len(entry.chunks), 0)

    def add_web_source(
        self,
        url: str,
        title: str,
        content: str,
        source_type: SourceType,
        domain: VedicDomain,
        category: str,
        subcategory: str,
        metadata: dict | None = None,
    ) -> IngestionResult:
        """Add a validated web source to the corpus."""
        result = IngestionResult()

        metadata = metadata or {}
        entry_id = hashlib.md5(url.encode()).hexdigest()[:12]

        source_metadata = SourceMetadata(
            title=title,
            category=category,
            subcategory=subcategory,
            source=url,
            source_type=source_type,
            source_url=url,
            author=metadata.get("author", ""),
            translator=metadata.get("translator", ""),
            commentator=metadata.get("commentator", ""),
            original_language=metadata.get("original_language", ""),
            translation_language=metadata.get("translation_language", ""),
            tradition=metadata.get("tradition", ""),
            chapter=metadata.get("chapter", ""),
            section=metadata.get("section", ""),
            verse=metadata.get("verse", ""),
            topics=metadata.get("topics", []),
            concepts=metadata.get("concepts", []),
            keywords=metadata.get("keywords", []),
            historical_context=metadata.get("historical_context", ""),
            interpretation_type=metadata.get("interpretation_type", ""),
            document_id=entry_id,
        )

        entry = VedicKnowledgeEntry(
            id=entry_id,
            title=title,
            content=content,
            domain=domain,
            category=category,
            subcategory=subcategory,
            source_metadata=source_metadata,
            tags=metadata.get("tags", []),
            difficulty=DifficultyLevel(metadata.get("difficulty", "intermediate")),
        )

        entry.chunks = self._chunk_content(entry)
        add_result = self._add_entry(entry)

        result.entries_added = add_result[0]
        result.chunks_created = add_result[1]
        result.duplicates_skipped = add_result[2]

        return result


class CorpusManager:
    """Manage the Vedic knowledge corpus."""

    def __init__(self, knowledge_base: VedicKnowledgeBase):
        self.kb = knowledge_base
        self._ingester = DocumentIngester(knowledge_base)
        self._corpus_validator = CorpusValidator(knowledge_base)

    def ingest(self, path: str | Path) -> IngestionResult:
        """Ingest a file or directory."""
        path = Path(path)
        if path.is_dir():
            return self._ingester.ingest_directory(path)
        else:
            return self._ingester.ingest_file(path)

    def add_web_source(self, *args, **kwargs) -> IngestionResult:
        """Add a validated web source."""
        return self._ingester.add_web_source(*args, **kwargs)

    def validate(self) -> dict:
        """Validate the corpus."""
        return self._corpus_validator.validate_all()

    def generate_report(self) -> str:
        """Generate validation report."""
        return self._corpus_validator.generate_report()

    def get_stats(self) -> dict:
        """Get corpus statistics."""
        return self.kb.get_stats()

    def export_domain(self, domain_name: str, output_path: Path) -> bool:
        """Export a domain to JSON."""
        domain = self.kb.get_domain(domain_name)
        if not domain:
            return False

        data = {
            "domain": domain_name,
            "version": self.kb.version,
            "exported_at": datetime.now().isoformat(),
            "entries": [entry.to_dict() for entry in domain.entries.values()],
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return True

    def list_versions(self) -> list[dict]:
        """List corpus versions (placeholder for versioning system)."""
        return [{
            "version": self.kb.version,
            "date": self.kb.last_updated,
            "stats": self.kb.get_stats(),
        }]


# Convenience function
async def ingest_corpus(path: str | Path, knowledge_base: VedicKnowledgeBase) -> IngestionResult:
    """Convenience function to ingest a corpus."""
    manager = CorpusManager(knowledge_base)
    return manager.ingest(path)