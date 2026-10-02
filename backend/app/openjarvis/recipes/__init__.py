"""Recipe system — composable primitive configurations.

Ported from OpenJarvis (Stanford Hazy Research / Scaling Intelligence Lab).
Adapted for JARVIS backend integration.
"""

from .composer import (
    recipe_to_eval_suite,
    recipe_to_operator,
)
from .loader import (
    Recipe,
    discover_recipes,
    load_recipe,
    resolve_recipe,
)

__all__ = [
    "Recipe",
    "discover_recipes",
    "load_recipe",
    "recipe_to_eval_suite",
    "recipe_to_operator",
    "resolve_recipe",
]
