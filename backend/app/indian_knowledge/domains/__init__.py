"""Domain loaders — creates and populates all Indian knowledge domains."""

import logging
from ..base import KnowledgeBase
from .vedic_literature import create_vedic_literature_domain
from .vedangas import create_vedangas_domain
from .itihasa import create_itihasa_domain
from .puranas import create_puranas_domain
from .bhagavad_gita import create_bhagavad_gita_domain

logger = logging.getLogger(__name__)


def load_all_domains() -> KnowledgeBase:
    """Create and populate the knowledge base with all Indian knowledge domains."""
    kb = KnowledgeBase()

    domain_creators = [
        ("vedic_literature", create_vedic_literature_domain),
        ("vedangas", create_vedangas_domain),
        ("itihasa", create_itihasa_domain),
        ("puranas", create_puranas_domain),
        ("bhagavad_gita", create_bhagavad_gita_domain),
    ]

    for name, creator in domain_creators:
        try:
            domain = creator()
            kb.add_domain(domain)
            logger.debug(f"[KNOWLEDGE] Loaded domain: {name} ({len(domain.entries)} entries)")
        except Exception as e:
            logger.error(f"[KNOWLEDGE] Failed to load domain {name}: {e}", exc_info=True)

    stats = kb.get_stats()
    logger.info(f"[KNOWLEDGE] Indian knowledge base loaded: {stats['domains']} domains, {stats['total_entries']} entries")
    return kb
