"""Domain loaders — creates and populates all knowledge domains."""

import logging
from ..base import KnowledgeBase
from .python_robotics import create_python_domain
from .cpp_robotics import create_cpp_domain
from .ros2 import create_ros2_domain
from .plc import create_plc_domain
from .hmi_scada import create_hmi_scada_domain
from .sensors import create_sensors_domain
from .actuators import create_actuators_domain
from .electronics import create_electronics_domain
from .computer_vision import create_vision_domain
from .ai_ml import create_ai_ml_domain
from .industrial_robots import create_industrial_robots_domain
from .automation import create_automation_domain

logger = logging.getLogger(__name__)


def load_all_domains() -> KnowledgeBase:
    """Create and populate the knowledge base with all robotics domains."""
    kb = KnowledgeBase()

    domain_creators = [
        ("python", create_python_domain),
        ("cpp", create_cpp_domain),
        ("ros2", create_ros2_domain),
        ("plc", create_plc_domain),
        ("hmi_scada", create_hmi_scada_domain),
        ("sensors", create_sensors_domain),
        ("actuators", create_actuators_domain),
        ("electronics", create_electronics_domain),
        ("computer_vision", create_vision_domain),
        ("ai_ml", create_ai_ml_domain),
        ("industrial_robots", create_industrial_robots_domain),
        ("automation", create_automation_domain),
    ]

    for name, creator in domain_creators:
        try:
            domain = creator()
            kb.add_domain(domain)
            logger.debug(f"[KNOWLEDGE] Loaded domain: {name} ({len(domain.entries)} entries)")
        except Exception as e:
            logger.error(f"[KNOWLEDGE] Failed to load domain {name}: {e}", exc_info=True)

    stats = kb.get_stats()
    logger.info(f"[KNOWLEDGE] Knowledge base loaded: {stats['domains']} domains, {stats['total_entries']} entries")
    return kb
