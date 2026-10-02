"""Web search fallback with source validation for Vedic knowledge."""

from __future__ import annotations

import logging
import json
import hashlib
import urllib.parse
import urllib.request
import re
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
from pathlib import Path
from enum import Enum

from .base import KnowledgeEntry, DifficultyLevel

logger = logging.getLogger(__name__)


class SourceType(Enum):
    PRIMARY_TEXT = "primary_text"
    TRANSLATION = "translation"
    TRADITIONAL_COMMENTARY = "traditional_commentary"
    SCHOLARLY_REFERENCE = "scholarly_reference"
    HISTORICAL_REFERENCE = "historical_reference"
    SECONDARY_SOURCE = "secondary_source"
    SUMMARY = "summary"


class ValidationStatus(Enum):
    VALIDATED = "validated"
    PENDING = "pending"
    REJECTED = "rejected"
    DUPLICATE = "duplicate"
    UNCERTAIN = "uncertain"


@dataclass
class WebSource:
    url: str
    title: str
    content: str
    author: Optional[str] = None
    translator: Optional[str] = None
    commentator: Optional[str] = None
    publication: Optional[str] = None
    publication_date: Optional[str] = None
    source_type: SourceType = SourceType.SECONDARY_SOURCE
    language: str = "English"
    retrieved_at: str = field(default_factory=lambda: datetime.now().isoformat())
    content_hash: str = ""
    validation_status: ValidationStatus = ValidationStatus.PENDING
    validation_notes: str = ""
    domain: str = ""
    category: str = ""
    topics: list[str] = field(default_factory=list)
    concepts: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.content_hash:
            self.content_hash = hashlib.md5(self.content.encode()).hexdigest()[:16]


@dataclass
class SearchResult:
    query: str
    sources: list[WebSource]
    total_found: int
    search_engine: str
    searched_at: str = field(default_factory=lambda: datetime.now().isoformat())


REPUTABLE_DOMAINS = {
    "sacred-texts.com": {"type": SourceType.PRIMARY_TEXT, "trust": 0.9},
    "vedabase.io": {"type": SourceType.TRANSLATION, "trust": 0.95},
    "gita-society.com": {"type": SourceType.TRANSLATION, "trust": 0.85},
    "hinduism.co.za": {"type": SourceType.SECONDARY_SOURCE, "trust": 0.7},
    "kamakoti.org": {"type": SourceType.TRADITIONAL_COMMENTARY, "trust": 0.85},
    "advaita.org.in": {"type": SourceType.TRADITIONAL_COMMENTARY, "trust": 0.85},
    "srirangam.org": {"type": SourceType.TRADITIONAL_COMMENTARY, "trust": 0.8},
    "chinmayamission.com": {"type": SourceType.SCHOLARLY_REFERENCE, "trust": 0.85},
    "ramakrishnamath.org": {"type": SourceType.SCHOLARLY_REFERENCE, "trust": 0.85},
    "arishabda.in": {"type": SourceType.PRIMARY_TEXT, "trust": 0.9},
    "sanskritdocuments.org": {"type": SourceType.PRIMARY_TEXT, "trust": 0.95},
    "gretil.sub.uni-goettingen.de": {"type": SourceType.PRIMARY_TEXT, "trust": 0.95},
    "www.vedamu.org": {"type": SourceType.TRANSLATION, "trust": 0.85},
    "www.valmiki.iitk.ac.in": {"type": SourceType.PRIMARY_TEXT, "trust": 0.95},
    "www.mahabharata.org": {"type": SourceType.PRIMARY_TEXT, "trust": 0.85},
    "dsbcproject.org": {"type": SourceType.SCHOLARLY_REFERENCE, "trust": 0.8},
    "jstor.org": {"type": SourceType.SCHOLARLY_REFERENCE, "trust": 0.95},
    "academia.edu": {"type": SourceType.SCHOLARLY_REFERENCE, "trust": 0.7},
    "archive.org": {"type": SourceType.PRIMARY_TEXT, "trust": 0.85},
    "wisdomlib.org": {"type": SourceType.SECONDARY_SOURCE, "trust": 0.75},
    "exoticindia.com": {"type": SourceType.SECONDARY_SOURCE, "trust": 0.7},
}


UNRELIABLE_PATTERNS = [
    r"blogspot\.com", r"wordpress\.com", r"medium\.com",
    r"quora\.com", r"reddit\.com", r"yahoo\.com",
    r"answers\.com", r"wiki\.answers", r"pinterest\.com",
]


def extract_domain(url: str) -> str:
    try:
        parsed = urllib.parse.urlparse(url)
        return parsed.netloc.lower().replace("www.", "")
    except Exception:
        return ""


def classify_source_type(url: str, content: str) -> tuple[SourceType, float]:
    domain = extract_domain(url)

    if domain in REPUTABLE_DOMAINS:
        return REPUTABLE_DOMAINS[domain]["type"], REPUTABLE_DOMAINS[domain]["trust"]

    for pattern in UNRELIABLE_PATTERNS:
        if re.search(pattern, domain):
            return SourceType.SECONDARY_SOURCE, 0.3

    content_lower = content.lower()
    if any(term in content_lower for term in ["original sanskrit", "devanagari", "iast transliteration", "verse by verse"]):
        return SourceType.PRIMARY_TEXT, 0.7
    if any(term in content_lower for term in ["translation by", "translated by", "commentary by", "bhashya"]):
        return SourceType.TRANSLATION, 0.65
    if any(term in content_lower for term in ["shankara", "ramanuja", "madhva", "sridhara", "jiva goswami"]):
        return SourceType.TRADITIONAL_COMMENTARY, 0.75
    if any(term in content_lower for term in ["journal", "doi:", "isbn", "university press", "academic"]):
        return SourceType.SCHOLARLY_REFERENCE, 0.7

    return SourceType.SECONDARY_SOURCE, 0.5


def validate_source(source: WebSource) -> WebSource:
    source_type, trust_score = classify_source_type(source.url, source.content)
    source.source_type = source_type

    if trust_score < 0.4:
        source.validation_status = ValidationStatus.REJECTED
        source.validation_notes = f"Low trust score ({trust_score:.2f}) for domain"
        return source

    if len(source.content) < 200:
        source.validation_status = ValidationStatus.UNCERTAIN
        source.validation_notes = "Content too short for reliable extraction"
        return source

    if source.source_type == SourceType.PRIMARY_TEXT:
        if not any(term in source.content.lower() for term in ["verse", "chapter", "śloka", "shloka", "sanskrit", "devanagari"]):
            source.validation_status = ValidationStatus.UNCERTAIN
            source.validation_notes = "Primary text claim but no verse/chapter markers found"
            return source

    if source.source_type == SourceType.TRANSLATION:
        if not source.translator and not any(term in source.content.lower() for term in ["translated by", "translation by"]):
            source.validation_status = ValidationStatus.UNCERTAIN
            source.validation_notes = "Translation claim but no translator identified"
            return source

    source.validation_status = ValidationStatus.VALIDATED
    source.validation_notes = f"Validated with trust score {trust_score:.2f}"
    return source


def check_duplicate(source: WebSource, existing_sources: list[WebSource]) -> bool:
    for existing in existing_sources:
        if existing.content_hash == source.content_hash:
            return True
        if source.url == existing.url:
            return True
    return False


async def search_web(query: str, max_results: int = 10) -> SearchResult:
    encoded = urllib.parse.quote(query)
    url = f"https://api.duckduckgo.com/?q={encoded}&format=json&no_html=1&skip_disambig=1"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "JARVIS-VedicKnowledge/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="ignore"))

        sources = []

        if data.get("AbstractText"):
            source = WebSource(
                url=data.get("AbstractURL", ""),
                title=data.get("Heading", "DuckDuckGo Instant Answer"),
                content=data.get("AbstractText", ""),
                source_type=SourceType.SECONDARY_SOURCE,
            )
            source = validate_source(source)
            if source.validation_status != ValidationStatus.REJECTED:
                sources.append(source)

        for topic in data.get("RelatedTopics", [])[:max_results]:
            if isinstance(topic, dict) and topic.get("Text"):
                source = WebSource(
                    url=topic.get("FirstURL", ""),
                    title=topic.get("Text", "")[:80],
                    content=topic.get("Text", ""),
                    source_type=SourceType.SECONDARY_SOURCE,
                )
                source = validate_source(source)
                if source.validation_status != ValidationStatus.REJECTED:
                    sources.append(source)

        if not sources:
            fallback_url = f"https://www.google.com/search?q={encoded}"
            sources.append(WebSource(
                url=fallback_url,
                title=f"Search Results for '{query}'",
                content=f"Web search initiated for '{query}'. Direct internet links available.",
                source_type=SourceType.SECONDARY_SOURCE,
                validation_status=ValidationStatus.PENDING,
                validation_notes="Fallback search link - requires manual verification",
            ))

        return SearchResult(query=query, sources=sources, total_found=len(sources), search_engine="duckduckgo")

    except Exception as e:
        logger.error(f"[WEB_SEARCH] Search failed: {e}")
        fallback_url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
        return SearchResult(
            query=query,
            sources=[WebSource(
                url=fallback_url,
                title=f"Search Error - Fallback",
                content=f"Search failed: {e}. Manual search: {fallback_url}",
                source_type=SourceType.SECONDARY_SOURCE,
                validation_status=ValidationStatus.REJECTED,
                validation_notes=str(e),
            )],
            total_found=0,
            search_engine="error",
        )


async def fetch_and_validate(url: str) -> WebSource:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) JARVIS/1.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            html = resp.read().decode("utf-8", errors="ignore")

        text = re.sub(r"<script[^>]*>[\s\S]*?</script>", "", html, flags=re.IGNORECASE)
        text = re.sub(r"<style[^>]*>[\s\S]*?</style>", "", text, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        clean_text = " ".join(text.split())

        title_match = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
        title = title_match.group(1) if title_match else url

        source = WebSource(
            url=url,
            title=title,
            content=clean_text[:8000],
        )

        return validate_source(source)

    except Exception as e:
        logger.error(f"[WEB_SEARCH] Fetch failed for {url}: {e}")
        return WebSource(
            url=url,
            title="Fetch Error",
            content=f"Failed to fetch: {e}",
            validation_status=ValidationStatus.REJECTED,
            validation_notes=str(e),
        )


def extract_knowledge_entry(source: WebSource, domain: str, category: str) -> Optional[KnowledgeEntry]:
    if source.validation_status != ValidationStatus.VALIDATED:
        return None

    entry_id = f"web_{domain}_{category}_{source.content_hash}"

    metadata = {
        "source": source.title,
        "source_type": source.source_type.value,
        "author": source.author,
        "translator": source.translator,
        "commentator": source.commentator,
        "original_language": "Sanskrit" if source.source_type == SourceType.PRIMARY_TEXT else "English",
        "translation_language": source.language,
        "source_url": source.url,
        "retrieved_at": source.retrieved_at,
        "topics": source.topics,
        "concepts": source.concepts,
        "historical_context": source.publication_date,
        "interpretation_type": source.source_type.value,
    }

    entry = KnowledgeEntry(
        id=entry_id,
        title=source.title,
        content=source.content[:5000],
        domain=domain,
        category=category,
        tags=source.topics + source.concepts,
        difficulty=DifficultyLevel.INTERMEDIATE,
        references=[source.url],
        metadata=metadata,
    )

    return entry


class WebIngestionPipeline:
    def __init__(self, corpus_path: str | Path):
        self.corpus_path = Path(corpus_path)
        self.corpus_path.mkdir(parents=True, exist_ok=True)
        self.validated_sources: list[WebSource] = []
        self.rejected_sources: list[WebSource] = []

    def load_existing_sources(self) -> list[WebSource]:
        sources_file = self.corpus_path / "sources" / "web_sources.json"
        if sources_file.exists():
            try:
                data = json.loads(sources_file.read_text(encoding="utf-8"))
                self.validated_sources = [WebSource(**s) for s in data.get("validated", [])]
                self.rejected_sources = [WebSource(**s) for s in data.get("rejected", [])]
                logger.info(f"[WEB_INGESTION] Loaded {len(self.validated_sources)} validated sources")
            except Exception as e:
                logger.error(f"[WEB_INGESTION] Failed to load sources: {e}")
        return self.validated_sources

    def save_sources(self):
        sources_file = self.corpus_path / "sources" / "web_sources.json"
        sources_file.parent.mkdir(parents=True, exist_ok=True)

        def serialize_source(s: WebSource) -> dict:
            d = s.__dict__.copy()
            d["source_type"] = s.source_type.value if hasattr(s.source_type, 'value') else str(s.source_type)
            d["validation_status"] = s.validation_status.value if hasattr(s.validation_status, 'value') else str(s.validation_status)
            return d

        data = {
            "validated": [serialize_source(s) for s in self.validated_sources],
            "rejected": [serialize_source(s) for s in self.rejected_sources],
            "updated_at": datetime.now().isoformat(),
        }
        sources_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    async def search_and_ingest(self, query: str, domain: str, category: str, max_results: int = 5) -> list[KnowledgeEntry]:
        self.load_existing_sources()

        search_result = await search_web(query, max_results)
        new_entries = []

        for source in search_result.sources:
            if source.validation_status != ValidationStatus.VALIDATED:
                self.rejected_sources.append(source)
                continue

            if check_duplicate(source, self.validated_sources):
                source.validation_status = ValidationStatus.DUPLICATE
                source.validation_notes = "Duplicate content detected"
                self.rejected_sources.append(source)
                continue

            if source.url:
                detailed_source = await fetch_and_validate(source.url)
                if detailed_source.validation_status == ValidationStatus.VALIDATED:
                    source = detailed_source
                else:
                    self.rejected_sources.append(detailed_source)
                    continue

            source.domain = domain
            source.category = category
            self.validated_sources.append(source)

            entry = extract_knowledge_entry(source, domain, category)
            if entry:
                new_entries.append(entry)

        self.save_sources()
        return new_entries

    def get_ingestion_report(self) -> dict:
        return {
            "total_validated": len(self.validated_sources),
            "total_rejected": len(self.rejected_sources),
            "by_type": {
                t.value: sum(1 for s in self.validated_sources if s.source_type == t)
                for t in SourceType
            },
            "by_status": {
                s.value: sum(1 for src in self.validated_sources + self.rejected_sources if src.validation_status == s)
                for s in ValidationStatus
            },
        }