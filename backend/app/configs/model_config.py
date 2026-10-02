"""Model configuration loader — reads model TOML configs and provides capabilities."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

try:
    import tomllib
except ModuleNotFoundError:
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ModuleNotFoundError:
        tomllib = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

MODELS_DIR = Path(__file__).parent / "models"


@dataclass
class ModelCapabilities:
    text_generation: bool = True
    tool_use: bool = False
    function_calling: bool = False
    vision: bool = False
    audio_input: bool = False
    audio_output: bool = False
    streaming: bool = False
    structured_output: bool = False
    json_mode: bool = False
    system_prompt: bool = True
    multi_turn: bool = True
    code_execution: bool = False
    image_generation: bool = False
    embeddings: bool = False
    reasoning: bool = False
    extended_thinking: bool = False


@dataclass
class ModelLimits:
    context_window: int = 128_000
    max_output_tokens: int = 4_096
    max_tool_calls_per_turn: int = 32
    request_timeout_seconds: int = 60
    concurrent_requests: int = 50


@dataclass
class ModelParameters:
    default_temperature: float = 0.7
    default_top_p: float = 1.0
    default_frequency_penalty: float = 0.0
    default_presence_penalty: float = 0.0


@dataclass
class ModelConfig:
    id: str
    name: str
    provider: str
    type: str
    version: str
    description: str
    capabilities: ModelCapabilities
    limits: ModelLimits
    parameters: ModelParameters
    api_endpoint: str
    fallback_model: str = ""
    supports_responses_api: bool = False
    supports_streaming: bool = True


@dataclass
class ModelRegistry:
    models: dict[str, ModelConfig] = field(default_factory=dict)

    def get(self, model_id: str) -> Optional[ModelConfig]:
        return self.models.get(model_id)

    def list_models(self) -> list[dict]:
        result = []
        for m in self.models.values():
            result.append({
                "id": m.id,
                "name": m.name,
                "provider": m.provider,
                "type": m.type,
                "description": m.description,
                "context_window": m.limits.context_window,
                "max_output_tokens": m.limits.max_output_tokens,
                "capabilities": {
                    "text": m.capabilities.text_generation,
                    "tools": m.capabilities.tool_use,
                    "vision": m.capabilities.vision,
                    "streaming": m.capabilities.streaming,
                    "reasoning": m.capabilities.reasoning,
                    "json_mode": m.capabilities.json_mode,
                },
            })
        return result

    def get_fallback_chain(self, model_id: str) -> list[str]:
        model = self.models.get(model_id)
        if not model:
            return []
        chain = [model_id]
        visited = {model_id}
        current = model
        while current.fallback_model and current.fallback_model not in visited:
            visited.add(current.fallback_model)
            chain.append(current.fallback_model)
            next_model = self.models.get(current.fallback_model)
            if not next_model:
                break
            current = next_model
        return chain


def _load_model_config(path: Path) -> Optional[ModelConfig]:
    if tomllib is None:
        return None
    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
    except Exception as e:
        logger.warning(f"Failed to load model config {path.name}: {e}")
        return None

    model_data = data.get("model", {})
    caps_data = data.get("capabilities", {})
    limits_data = data.get("limits", {})
    params_data = data.get("parameters", {})
    api_data = data.get("api", {})

    capabilities = ModelCapabilities(
        text_generation=caps_data.get("text_generation", True),
        tool_use=caps_data.get("tool_use", False),
        function_calling=caps_data.get("function_calling", False),
        vision=caps_data.get("vision", False),
        audio_input=caps_data.get("audio_input", False),
        audio_output=caps_data.get("audio_output", False),
        streaming=caps_data.get("streaming", False),
        structured_output=caps_data.get("structured_output", False),
        json_mode=caps_data.get("json_mode", False),
        system_prompt=caps_data.get("system_prompt", True),
        multi_turn=caps_data.get("multi_turn", True),
        code_execution=caps_data.get("code_execution", False),
        image_generation=caps_data.get("image_generation", False),
        embeddings=caps_data.get("embeddings", False),
        reasoning=caps_data.get("reasoning", False),
        extended_thinking=caps_data.get("extended_thinking", False),
    )

    limits = ModelLimits(
        context_window=limits_data.get("context_window", 128_000),
        max_output_tokens=limits_data.get("max_output_tokens", 4_096),
        max_tool_calls_per_turn=limits_data.get("max_tool_calls_per_turn", 32),
        request_timeout_seconds=limits_data.get("request_timeout_seconds", 60),
        concurrent_requests=limits_data.get("concurrent_requests", 50),
    )

    parameters = ModelParameters(
        default_temperature=params_data.get("default_temperature", 0.7),
        default_top_p=params_data.get("default_top_p", 1.0),
        default_frequency_penalty=params_data.get("default_frequency_penalty", 0.0),
        default_presence_penalty=params_data.get("default_presence_penalty", 0.0),
    )

    return ModelConfig(
        id=model_data.get("id", path.stem),
        name=model_data.get("name", path.stem),
        provider=model_data.get("provider", "unknown"),
        type=model_data.get("type", "general"),
        version=model_data.get("version", "unknown"),
        description=model_data.get("description", ""),
        capabilities=capabilities,
        limits=limits,
        parameters=parameters,
        api_endpoint=api_data.get("endpoint", ""),
        fallback_model=api_data.get("fallback_model", ""),
        supports_responses_api=api_data.get("supports_responses_api", False),
        supports_streaming=caps_data.get("streaming", False),
    )


def load_model_registry() -> ModelRegistry:
    registry = ModelRegistry()
    if not MODELS_DIR.exists():
        logger.warning(f"Models config directory not found: {MODELS_DIR}")
        return registry

    for toml_file in sorted(MODELS_DIR.glob("*.toml")):
        config = _load_model_config(toml_file)
        if config:
            registry.models[config.id] = config
            logger.info(f"[MODEL CONFIG] Loaded: {config.name} ({config.provider})")

    logger.info(f"[MODEL CONFIG] Registry loaded: {len(registry.models)} models")
    return registry


_model_registry: Optional[ModelRegistry] = None


def get_model_registry() -> ModelRegistry:
    global _model_registry
    if _model_registry is None:
        _model_registry = load_model_registry()
    return _model_registry


def get_model_config(model_id: str) -> Optional[ModelConfig]:
    return get_model_registry().get(model_id)
