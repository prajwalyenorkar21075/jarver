"""Composer bridges — convert a Recipe into EvalSuiteConfig or OperatorManifest.

These are pure-function transformations that let the unified Recipe format
drive both the eval framework and the operator system without those systems
needing to know about recipes directly.

Ported from OpenJarvis and adapted for JARVIS backend.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from .loader import Recipe


def recipe_to_eval_suite(
    recipe: "Recipe",
    benchmarks: Optional[List[str]] = None,
    max_samples: Optional[int] = None,
    judge_model: Optional[str] = None,
) -> dict:
    """Build an eval suite config dict from a recipe.

    The recipe's model / engine become the single ``models`` entry.
    The recipe's ``eval_benchmarks`` (or the *benchmarks* override) become
    ``benchmarks`` entries.  Agent type and tools are inherited so the
    eval runner constructs the right backend automatically.

    Args:
        recipe: Source recipe.
        benchmarks: Override benchmark list (defaults to ``recipe.eval_benchmarks``).
        max_samples: Override per-benchmark sample cap.
        judge_model: Override LLM judge model.

    Raises:
        ValueError: If no model or benchmarks can be resolved.

    Returns:
        A dict representing the eval suite configuration.  When the
        ``openjarvis.evals.core.types`` module is available the return
        value is upgraded to a proper ``EvalSuiteConfig`` dataclass.
    """
    bench_names = benchmarks or list(recipe.eval_benchmarks)
    if not bench_names:
        bench_names = list(recipe.eval_suites)
    if not bench_names:
        raise ValueError(
            f"Recipe '{recipe.name}' has no benchmarks defined and none were "
            "provided.  Set [eval] benchmarks in the TOML or pass benchmarks=."
        )

    model_name = recipe.model
    if not model_name:
        raise ValueError(
            f"Recipe '{recipe.name}' has no model defined.  "
            "Set [intelligence] model in the TOML."
        )

    has_agent = recipe.agent_type is not None
    backend = recipe.eval_backend or ("jarvis-agent" if has_agent else "jarvis-direct")

    model_cfg = {
        "name": model_name,
        "engine": recipe.engine_key,
        "provider": recipe.provider,
        "temperature": recipe.temperature,
    }

    bench_cfgs: list[dict] = []
    for bname in bench_names:
        bench_cfgs.append(
            {
                "name": bname,
                "backend": backend,
                "max_samples": max_samples or recipe.eval_max_samples,
                "agent": recipe.agent_type if has_agent else None,
                "tools": list(recipe.tools) if has_agent else [],
                "judge_model": judge_model or recipe.eval_judge_model,
            }
        )

    suite = {
        "meta": {
            "name": f"{recipe.name}-eval",
            "description": f"Auto-generated eval suite from recipe '{recipe.name}'",
        },
        "defaults": {
            "temperature": recipe.temperature or 0.0,
            "max_tokens": 2048,
        },
        "judge": {
            "model": judge_model or recipe.eval_judge_model or "gpt-5-mini-2025-08-07",
        },
        "run": {},
        "models": [model_cfg],
        "benchmarks": bench_cfgs,
    }

    # Attempt to upgrade to typed dataclass if available
    try:
        from openjarvis.evals.core.types import (
            BenchmarkConfig,
            DefaultsConfig,
            EvalSuiteConfig,
            ExecutionConfig,
            JudgeConfig,
            MetaConfig,
            ModelConfig,
        )

        return EvalSuiteConfig(
            meta=MetaConfig(**suite["meta"]),
            defaults=DefaultsConfig(**suite["defaults"]),
            judge=JudgeConfig(**suite["judge"]),
            run=ExecutionConfig(**suite["run"]),
            models=[ModelConfig(**m) for m in suite["models"]],
            benchmarks=[BenchmarkConfig(**b) for b in bench_cfgs],
        )
    except ImportError:
        return suite


def recipe_to_operator(recipe: "Recipe") -> dict:
    """Build an operator manifest dict from a recipe.

    Maps the recipe's agent, schedule, and channel fields into the
    operator manifest format used by ``OperatorManager``.

    Raises:
        ValueError: If schedule information is missing.

    Returns:
        A dict representing the operator manifest.  When the
        ``openjarvis.operators.types`` module is available the return
        value is upgraded to a proper ``OperatorManifest`` dataclass.
    """
    if not recipe.schedule_type:
        raise ValueError(
            f"Recipe '{recipe.name}' has no [schedule] section.  "
            "Operator recipes must define schedule_type and schedule_value."
        )

    prompt = recipe.system_prompt or ""
    prompt_path = recipe.system_prompt_path or ""

    manifest = {
        "id": recipe.name,
        "name": recipe.name,
        "version": recipe.version,
        "description": recipe.description,
        "tools": list(recipe.tools),
        "system_prompt": prompt,
        "system_prompt_path": prompt_path,
        "max_turns": recipe.max_turns or 20,
        "temperature": recipe.temperature or 0.3,
        "schedule_type": recipe.schedule_type,
        "schedule_value": recipe.schedule_value or "300",
        "required_capabilities": list(recipe.required_capabilities),
    }

    # Attempt to upgrade to typed dataclass if available
    try:
        from openjarvis.operators.types import OperatorManifest

        return OperatorManifest(**manifest)
    except ImportError:
        return manifest


__all__ = ["recipe_to_eval_suite", "recipe_to_operator"]
