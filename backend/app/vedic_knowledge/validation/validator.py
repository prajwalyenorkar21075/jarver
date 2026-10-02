"""Source validation for Vedic Knowledge System."""

import hashlib
import logging
import re
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlparse

from ..base import SourceType, SourceMetadata

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of source validation."""
    is_valid: bool
    status: str
    confidence: float
    source_type: Optional[SourceType] = None
    metadata: dict = field(default_factory=dict)
    details: dict = field(default_factory=dict)
    issues: list[str] = field(default_factory=list)


TRUSTED_DOMAINS = {
    # Primary text repositories
    "sacred-texts.com": {"type": SourceType.PRIMARY_TEXT, "trust": 0.95},
    "gretil.sub.uni-goettingen.de": {"type": SourceType.PRIMARY_TEXT, "trust": 0.95},
    "sanskritdocuments.org": {"type": SourceType.PRIMARY_TEXT, "trust": 0.9},
    "vedicheritage.gov.in": {"type": SourceType.PRIMARY_TEXT, "trust": 0.95},
    "indianculture.gov.in": {"type": SourceType.PRIMARY_TEXT, "trust": 0.9},
    "www.vedamu.org": {"type": SourceType.PRIMARY_TEXT, "trust": 0.85},
    "www.vedic-heritage.in": {"type": SourceType.PRIMARY_TEXT, "trust": 0.85},

    # Academic / scholarly
    "journal.indianphilosophy.org": {"type": SourceType.SCHOLARLY_REFERENCE, "trust": 0.9},
    "www.jstor.org": {"type": SourceType.SCHOLARLY_REFERENCE, "trust": 0.95},
    "www.academia.edu": {"type": SourceType.SCHOLARLY_REFERENCE, "trust": 0.7},
    "philpapers.org": {"type": SourceType.SCHOLARLY_REFERENCE, "trust": 0.9},
    "doi.org": {"type": SourceType.SCHOLARLY_REFERENCE, "trust": 0.95},

    # Traditional commentaries
    "www.advaita-vedanta.org": {"type": SourceType.TRADITIONAL_COMMENTARY, "trust": 0.9},
    "www.sringeri.net": {"type": SourceType.TRADITIONAL_COMMENTARY, "trust": 0.9},
    "www.chinmayamission.com": {"type": SourceType.TRADITIONAL_COMMENTARY, "trust": 0.85},
    "www.ramakrishnamath.org": {"type": SourceType.TRADITIONAL_COMMENTARY, "trust": 0.85},
    "www.vedanta.org": {"type": SourceType.TRADITIONAL_COMMENTARY, "trust": 0.85},

    # Translations
    "www.gitasupersite.iitk.ac.in": {"type": SourceType.TRANSLATION, "trust": 0.95},
    "www.bhagavad-gita.org": {"type": SourceType.TRANSLATION, "trust": 0.85},
    "www.vedabase.io": {"type": SourceType.TRANSLATION, "trust": 0.9},
    "www.holy-bhagavad-gita.org": {"type": SourceType.TRANSLATION, "trust": 0.8},
    "www.valmiki.iitk.ac.in": {"type": SourceType.TRANSLATION, "trust": 0.9},

    # Encyclopedias / reference
    "www.britannica.com": {"type": SourceType.SCHOLARLY_REFERENCE, "trust": 0.9},
    "www.worldhistory.org": {"type": SourceType.SCHOLARLY_REFERENCE, "trust": 0.85},
    "plato.stanford.edu": {"type": SourceType.SCHOLARLY_REFERENCE, "trust": 0.95},
    "iep.utm.edu": {"type": SourceType.SCHOLARLY_REFERENCE, "trust": 0.95},
}


UNTRUSTED_PATTERNS = [
    r"blogspot\.com",
    r"wordpress\.com",
    r"medium\.com",
    r"quora\.com",
    r"reddit\.com",
    r"yahoo\.com",
    r"answers\.com",
    r"brainly\.com",
    r"studymode\.com",
    r"coursehero\.com",
    r"chegg\.com",
]


SUSPICIOUS_PATTERNS = [
    r"clickbank",
    r"affiliate",
    r"buy now",
    r"discount",
    r"limited time",
    r"secret knowledge",
    r"ancient secret",
    r"hidden truth",
]


class SourceValidator:
    """Validate web sources for Vedic knowledge."""

    def __init__(self):
        self._cache: dict[str, ValidationResult] = {}

    async def validate_source(self, url: str) -> ValidationResult:
        """Validate a source URL."""
        if url in self._cache:
            return self._cache[url]

        result = ValidationResult(
            is_valid=False,
            status="unchecked",
            confidence=0.0,
        )

        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()

            # Check for untrusted patterns
            for pattern in UNTRUSTED_PATTERNS:
                if re.search(pattern, domain):
                    result.status = "untrusted_domain"
                    result.issues.append(f"Domain matches untrusted pattern: {pattern}")
                    result.confidence = 0.1
                    self._cache[url] = result
                    return result

            # Check trusted domains
            trusted_info = None
            for trusted_domain, info in TRUSTED_DOMAINS.items():
                if trusted_domain in domain:
                    trusted_info = info
                    break

            if trusted_info:
                result.is_valid = True
                result.status = "trusted"
                result.confidence = trusted_info["trust"]
                result.source_type = trusted_info["type"]
                result.details["matched_domain"] = trusted_domain
            else:
                # Unknown domain - apply heuristics
                result = await self._heuristic_validation(url, domain, result)

        except Exception as e:
            logger.error(f"[VALIDATOR] Validation error for {url}: {e}")
            result.status = "error"
            result.issues.append(f"Validation error: {e}")
            result.confidence = 0.0

        self._cache[url] = result
        return result

    async def _heuristic_validation(
        self,
        url: str,
        domain: str,
        result: ValidationResult,
    ) -> ValidationResult:
        """Apply heuristic validation for unknown domains."""

        # Check for suspicious patterns
        for pattern in SUSPICIOUS_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                result.issues.append(f"Suspicious pattern in URL: {pattern}")
                result.confidence = max(0.0, result.confidence - 0.3)

        # Check domain structure
        if domain.count(".") > 3:
            result.issues.append("Excessive subdomains")
            result.confidence = max(0.0, result.confidence - 0.1)

        # Check for academic TLDs
        if domain.endswith((".edu", ".ac.in", ".gov.in", ".org")):
            result.confidence = min(1.0, result.confidence + 0.2)
            result.details["academic_tld"] = True

        # In production, would fetch and analyze content here
        # For now, set baseline for unknown domains
        if result.confidence == 0.0:
            result.confidence = 0.3
            result.status = "unknown"
            result.issues.append("Unknown domain - no content verification")

        result.is_valid = result.confidence >= 0.4
        if result.is_valid:
            result.status = "heuristic_pass"

        return result

    def validate_metadata(self, metadata: SourceMetadata) -> ValidationResult:
        """Validate source metadata for completeness."""
        result = ValidationResult(
            is_valid=True,
            status="valid",
            confidence=1.0,
        )

        required_fields = ["title", "source", "source_type", "category", "subcategory"]
        for field_name in required_fields:
            value = getattr(metadata, field_name, None)
            if not value:
                result.is_valid = False
                result.status = "incomplete_metadata"
                result.issues.append(f"Missing required field: {field_name}")
                result.confidence -= 0.15

        # Validate source_type
        if metadata.source_type and not isinstance(metadata.source_type, SourceType):
            result.issues.append("Invalid source_type")
            result.confidence -= 0.1

        # Check for duplicate detection info
        if not metadata.document_id:
            result.issues.append("Missing document_id for deduplication")
            result.confidence -= 0.05

        result.confidence = max(0.0, min(1.0, result.confidence))
        return result

    def check_duplicate(self, metadata: SourceMetadata, existing_metadata: list[SourceMetadata]) -> bool:
        """Check if metadata represents a duplicate of existing sources."""
        for existing in existing_metadata:
            # Same URL
            if metadata.source_url and metadata.source_url == existing.source_url:
                return True

            # Same title and source
            if (metadata.title == existing.title and
                metadata.source == existing.source):
                return True

            # Same verse/chapter from same source
            if (metadata.chapter and metadata.verse and
                metadata.chapter == existing.chapter and
                metadata.verse == existing.verse and
                metadata.source == existing.source):
                return True

        return False


class CorpusValidator:
    """Validate entire corpus for consistency and quality."""

    def __init__(self, knowledge_base):
        self.kb = knowledge_base
        self._source_validator = SourceValidator()

    def validate_all(self) -> dict:
        """Run full corpus validation."""
        issues = {
            "missing_metadata": [],
            "missing_source": [],
            "malformed_entries": [],
            "duplicate_documents": [],
            "duplicate_chunks": [],
            "empty_documents": [],
            "broken_references": [],
            "unsupported_formats": [],
            "invalid_metadata": [],
        }

        all_metadata = []

        for domain_name, domain in self.kb.domains.items():
            for entry_id, entry in domain.entries.items():
                # Check entry structure
                if not entry.title or not entry.content:
                    issues["empty_documents"].append({
                        "entry_id": entry_id,
                        "domain": domain_name,
                        "issue": "Empty title or content",
                    })

                # Check metadata
                meta_validation = self._source_validator.validate_metadata(entry.source_metadata)
                if not meta_validation.is_valid:
                    issues["invalid_metadata"].append({
                        "entry_id": entry_id,
                        "domain": domain_name,
                        "issues": meta_validation.issues,
                    })

                # Check source
                if not entry.source_metadata.source:
                    issues["missing_source"].append({
                        "entry_id": entry_id,
                        "domain": domain_name,
                    })

                # Check for duplicates
                if self._source_validator.check_duplicate(entry.source_metadata, all_metadata):
                    issues["duplicate_documents"].append({
                        "entry_id": entry_id,
                        "domain": domain_name,
                        "title": entry.title,
                    })

                all_metadata.append(entry.source_metadata)

                # Check chunks
                chunk_hashes = set()
                for chunk in entry.chunks:
                    chunk_hash = hashlib.md5(chunk.content.encode()).hexdigest()[:16]
                    if chunk_hash in chunk_hashes:
                        issues["duplicate_chunks"].append({
                            "entry_id": entry_id,
                            "chunk_id": chunk.id,
                        })
                    chunk_hashes.add(chunk_hash)

                    if not chunk.content.strip():
                        issues["malformed_entries"].append({
                            "entry_id": entry_id,
                            "chunk_id": chunk.id,
                            "issue": "Empty chunk content",
                        })

        return {
            "total_issues": sum(len(v) for v in issues.values()),
            "issues": issues,
            "health_score": self._calculate_health_score(issues),
        }

    def _calculate_health_score(self, issues: dict) -> float:
        """Calculate corpus health score (0-100)."""
        total_entries = sum(len(d.entries) for d in self.kb.domains.values())
        if total_entries == 0:
            return 0.0

        # Weight different issue types
        weights = {
            "missing_metadata": 2,
            "missing_source": 3,
            "malformed_entries": 5,
            "duplicate_documents": 4,
            "duplicate_chunks": 3,
            "empty_documents": 5,
            "broken_references": 2,
            "unsupported_formats": 1,
            "invalid_metadata": 3,
        }

        penalty = sum(len(issues[k]) * w for k, w in weights.items())
        max_penalty = total_entries * 10  # Rough maximum
        score = max(0.0, 100.0 - (penalty / max_penalty * 100))
        return round(score, 1)

    def generate_report(self) -> str:
        """Generate human-readable validation report."""
        validation = self.validate_all()

        lines = [
            "=" * 60,
            "VEDIC KNOWLEDGE CORPUS VALIDATION REPORT",
            "=" * 60,
            f"Health Score: {validation['health_score']}/100",
            f"Total Issues: {validation['total_issues']}",
            "",
        ]

        for category, items in validation["issues"].items():
            if items:
                lines.append(f"## {category.replace('_', ' ').title()} ({len(items)})")
                for item in items[:10]:  # Show first 10
                    lines.append(f"  - {item}")
                if len(items) > 10:
                    lines.append(f"  ... and {len(items) - 10} more")
                lines.append("")

        lines.append("=" * 60)
        return "\n".join(lines)


# Singleton
_validator: SourceValidator | None = None


def get_source_validator() -> SourceValidator:
    global _validator
    if _validator is None:
        _validator = SourceValidator()
    return _validator