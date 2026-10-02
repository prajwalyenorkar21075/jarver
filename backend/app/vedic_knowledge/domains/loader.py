"""Load all Vedic knowledge domains from the existing indian_knowledge corpus."""

import logging
from ..base import (
    VedicKnowledgeBase,
    VedicKnowledgeDomain,
    VedicKnowledgeEntry,
    KnowledgeChunk,
    SourceMetadata,
    DifficultyLevel,
    SourceType,
    Language,
    VedicDomain,
)

logger = logging.getLogger(__name__)


def load_all_domains() -> VedicKnowledgeBase:
    """Load all Vedic knowledge domains from the existing indian_knowledge corpus."""
    kb = VedicKnowledgeBase(version="1.0.0")

    # Import the existing domain creators
    from app.indian_knowledge.domains.vedic_literature import create_vedic_literature_domain
    from app.indian_knowledge.domains.vedangas import create_vedangas_domain
    from app.indian_knowledge.domains.itihasa import create_itihasa_domain
    from app.indian_knowledge.domains.puranas import create_puranas_domain
    from app.indian_knowledge.domains.bhagavad_gita import create_bhagavad_gita_domain

    # Load each domain and convert to VedicKnowledgeDomain
    domains_to_load = [
        (VedicDomain.UPANISHADS, create_vedic_literature_domain),
        (VedicDomain.VEDANGAS, create_vedangas_domain),
        (VedicDomain.ITIHASA, create_itihasa_domain),
        (VedicDomain.PURANAS, create_puranas_domain),
        (VedicDomain.BHAGAVAD_GITA, create_bhagavad_gita_domain),
    ]

    for vedic_domain, creator in domains_to_load:
        old_domain = creator()
        new_domain = _convert_domain(vedic_domain, old_domain)
        kb.add_domain(new_domain)

    # Add Brahmanas and Aranyakas as separate domains (they're part of vedic_literature)
    _add_brahmanas_domain(kb)
    _add_aranyakas_domain(kb)

    logger.info(f"[VEDIC_DOMAINS] Loaded {len(kb.domains)} domains with {kb.stats['total_entries']} entries")
    return kb


def _convert_domain(vedic_domain: VedicDomain, old_domain) -> VedicKnowledgeDomain:
    """Convert old KnowledgeDomain to new VedicKnowledgeDomain."""
    new_domain = VedicKnowledgeDomain(
        name=vedic_domain,
        description=old_domain.description,
        subcategories=old_domain.subcategories,
        metadata=old_domain.metadata,
    )

    for old_entry in old_domain.entries.values():
        # Create source metadata
        source_metadata = SourceMetadata(
            title=old_entry.title,
            category=old_entry.category,
            subcategory=old_entry.category,  # Use category as subcategory for now
            source=_determine_source(old_entry),
            source_type=_determine_source_type(old_entry),
            tradition=old_domain.metadata.get("tradition", "Hindu"),
            original_language=old_domain.metadata.get("language", "Sanskrit"),
            translation_language="English",
            topics=old_entry.tags[:5] if old_entry.tags else [],
            concepts=_extract_concepts(old_entry),
            keywords=old_entry.tags,
            references=old_entry.references,
        )

        # Map difficulty
        difficulty = DifficultyLevel.INTERMEDIATE
        if old_entry.difficulty:
            try:
                difficulty = DifficultyLevel(old_entry.difficulty.value)
            except ValueError:
                pass

        # Create new entry
        new_entry = VedicKnowledgeEntry(
            id=old_entry.id,
            title=old_entry.title,
            content=old_entry.content,
            domain=vedic_domain,
            category=old_entry.category,
            subcategory=old_entry.category,
            source_metadata=source_metadata,
            tags=old_entry.tags,
            difficulty=difficulty,
            prerequisites=old_entry.prerequisites,
            related=old_entry.related,
            examples=old_entry.examples,
            references=old_entry.references,
        )

        # Create chunks from content
        new_entry.chunks = _create_chunks(new_entry)

        new_domain.add_entry(new_entry)

    return new_domain


def _determine_source(entry) -> str:
    """Determine the source text from entry metadata."""
    # Check references for source info
    for ref in entry.references:
        if any(keyword in ref.lower() for keyword in ["upanishad", "gita", "ramayana", "mahabharata", "purana", "vedanga", "brahmana", "aranyaka", "veda"]):
            return ref

    # Default based on domain/category
    source_map = {
        "upanishads": "Upanishads (Mukhya)",
        "brahmanas": "Brahmanas (Shatapatha, Aitareya, Taittiriya)",
        "aranyakas": "Aranyakas",
        "vedas": "Vedas (Samhitas)",
        "vedangas": "Vedangas (Shiksha, Kalpa, Vyakarana, Nirukta, Chandas, Jyotisha)",
        "ramayana": "Valmiki Ramayana",
        "mahabharata": "Vyasa Mahabharata",
        "puranas": "Puranas (18 Maha Puranas)",
        "bhagavad_gita": "Bhagavad Gita (Mahabharata Book 6)",
        "karma_yoga": "Bhagavad Gita Chapter 3",
        "jnana_yoga": "Bhagavad Gita Chapters 2, 7, 13-15",
        "bhakti_yoga": "Bhagavad Gita Chapters 9, 11, 12, 18",
        "dharma": "Bhagavad Gita Chapters 1, 3, 18",
    }

    return source_map.get(entry.category, "Indian Knowledge Tradition")


def _determine_source_type(entry) -> SourceType:
    """Determine source type from entry."""
    # Most entries in the existing corpus are summaries/secondary sources
    # In a real system, we'd have separate entries for primary texts, translations, commentaries
    category = entry.category.lower()

    if category in ["vedas", "upanishads", "brahmanas", "aranyakas"]:
        return SourceType.PRIMARY_TEXT
    elif "gita" in category or category in ["karma_yoga", "jnana_yoga", "bhakti_yoga"]:
        return SourceType.TRANSLATION
    elif category in ["ramayana", "mahabharata", "puranas"]:
        return SourceType.PRIMARY_TEXT
    elif category in ["shiksha", "kalpa", "vyakarana", "nirukta", "chandas", "jyotisha"]:
        return SourceType.TRADITIONAL_COMMENTARY

    return SourceType.SECONDARY_SOURCE


def _extract_concepts(entry) -> list[str]:
    """Extract concepts from entry tags and content."""
    concepts = set()

    # From tags
    concepts.update(entry.tags)

    # Common concept keywords
    concept_keywords = [
        "atman", "brahman", "dharma", "karma", "moksha", "yoga",
        "jnana", "bhakti", "maya", "avidya", "samsara", "punarjanma",
        "guru", "shishya", "shruti", "smriti", "vedanta", "samkhya",
        "prana", "kundalini", "chakra", "nadi", "om", "gayatri",
        "rishi", "deva", "asura", "avatar", "murti", "puja",
    ]

    content_lower = entry.content.lower()
    for keyword in concept_keywords:
        if keyword in content_lower:
            concepts.add(keyword)

    return list(concepts)[:10]  # Limit


def _create_chunks(entry: VedicKnowledgeEntry) -> list[KnowledgeChunk]:
    """Create knowledge chunks from entry content."""
    chunks = []
    content = entry.content

    # Split by paragraphs
    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]

    current_chunk = ""
    chunk_index = 0
    max_chunk_size = 1000

    for para in paragraphs:
        if len(current_chunk) + len(para) > max_chunk_size and current_chunk:
            chunk = KnowledgeChunk(
                id=f"{entry.id}_chunk_{chunk_index}",
                content=current_chunk.strip(),
                source_metadata=entry.source_metadata,
                language=Language.ENGLISH,
                chunk_index=chunk_index,
            )
            chunks.append(chunk)
            chunk_index += 1
            current_chunk = para
        else:
            if current_chunk:
                current_chunk += "\n\n" + para
            else:
                current_chunk = para

    if current_chunk.strip():
        chunk = KnowledgeChunk(
            id=f"{entry.id}_chunk_{chunk_index}",
            content=current_chunk.strip(),
            source_metadata=entry.source_metadata,
            language=Language.ENGLISH,
            chunk_index=chunk_index,
        )
        chunks.append(chunk)

    # Update total_chunks
    for chunk in chunks:
        chunk.total_chunks = len(chunks)

    return chunks


def _add_brahmanas_domain(kb: VedicKnowledgeBase):
    """Add Brahmanas as a separate domain."""
    from app.indian_knowledge.domains.vedic_literature import create_vedic_literature_domain

    old_domain = create_vedic_literature_domain()

    new_domain = VedicKnowledgeDomain(
        name=VedicDomain.BRAHMANAS,
        description="The Brahmanas — ritual texts explaining Vedic ceremonies, yajnas, and sacrificial procedures. They provide detailed instructions for priests and explain the cosmic significance of rituals.",
        subcategories=["brahmanas", "rituals", "yajna", "sacrifice", "ceremonies"],
        metadata={"tradition": "Hindu", "language": "Sanskrit", "period": "900-700 BCE"},
    )

    for old_entry in old_domain.entries.values():
        if old_entry.category == "brahmanas":
            source_metadata = SourceMetadata(
                title=old_entry.title,
                category=old_entry.category,
                subcategory=old_entry.category,
                source=_determine_source(old_entry),
                source_type=SourceType.PRIMARY_TEXT,
                tradition="Hindu",
                original_language="Sanskrit",
                translation_language="English",
                topics=old_entry.tags[:5],
                concepts=_extract_concepts(old_entry),
                keywords=old_entry.tags,
                references=old_entry.references,
            )

            new_entry = VedicKnowledgeEntry(
                id=old_entry.id,
                title=old_entry.title,
                content=old_entry.content,
                domain=VedicDomain.BRAHMANAS,
                category=old_entry.category,
                subcategory=old_entry.category,
                source_metadata=source_metadata,
                tags=old_entry.tags,
                difficulty=DifficultyLevel(old_entry.difficulty.value) if old_entry.difficulty else DifficultyLevel.INTERMEDIATE,
                prerequisites=old_entry.prerequisites,
                related=old_entry.related,
                examples=old_entry.examples,
                references=old_entry.references,
            )

            new_entry.chunks = _create_chunks(new_entry)
            new_domain.add_entry(new_entry)

    if new_domain.entries:
        kb.add_domain(new_domain)


def _add_aranyakas_domain(kb: VedicKnowledgeBase):
    """Add Aranyakas as a separate domain."""
    from app.indian_knowledge.domains.vedic_literature import create_vedic_literature_domain

    old_domain = create_vedic_literature_domain()

    new_domain = VedicKnowledgeDomain(
        name=VedicDomain.ARANYAKAS,
        description="The Aranyakas — forest texts bridging Vedic rituals and Upanishadic philosophy. Composed for hermits practicing meditation in the forest, they reinterpret external rituals as internal spiritual practices.",
        subcategories=["aranyakas", "forest texts", "meditation", "contemplation", "spiritual study"],
        metadata={"tradition": "Hindu", "language": "Sanskrit", "period": "800-600 BCE"},
    )

    for old_entry in old_domain.entries.values():
        if old_entry.category == "aranyakas":
            source_metadata = SourceMetadata(
                title=old_entry.title,
                category=old_entry.category,
                subcategory=old_entry.category,
                source=_determine_source(old_entry),
                source_type=SourceType.PRIMARY_TEXT,
                tradition="Hindu",
                original_language="Sanskrit",
                translation_language="English",
                topics=old_entry.tags[:5],
                concepts=_extract_concepts(old_entry),
                keywords=old_entry.tags,
                references=old_entry.references,
            )

            new_entry = VedicKnowledgeEntry(
                id=old_entry.id,
                title=old_entry.title,
                content=old_entry.content,
                domain=VedicDomain.ARANYAKAS,
                category=old_entry.category,
                subcategory=old_entry.category,
                source_metadata=source_metadata,
                tags=old_entry.tags,
                difficulty=DifficultyLevel(old_entry.difficulty.value) if old_entry.difficulty else DifficultyLevel.INTERMEDIATE,
                prerequisites=old_entry.prerequisites,
                related=old_entry.related,
                examples=old_entry.examples,
                references=old_entry.references,
            )

            new_entry.chunks = _create_chunks(new_entry)
            new_domain.add_entry(new_entry)

    if new_domain.entries:
        kb.add_domain(new_domain)