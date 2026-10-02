"""Proactive Agent - Runs on a schedule to autonomously handle routine tasks.

Ported from OpenJARVIS (Stanford Hazy Research).
Collects data, classifies items, proposes actions with tiered permissions.
"""

import logging
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ActionTier(Enum):
    TRIVIAL = "trivial"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ProactiveAgent:
    def __init__(self):
        self._approval_store: dict[str, bool] = {}
        self._scheduled_tasks: list[dict] = []

    async def run_proactive_check(self, data_sources: dict[str, Any] | None = None, llm_call=None) -> dict[str, Any]:
        collected = data_sources or {}
        items = []

        for source_name, source_data in collected.items():
            if isinstance(source_data, list):
                for item in source_data:
                    items.append({"source": source_name, "data": item})
            elif source_data:
                items.append({"source": source_name, "data": source_data})

        actions = []
        for item in items:
            action = await self._classify_and_propose(item, llm_call)
            if action:
                actions.append(action)

        auto_approved = []
        pending_approval = []

        for action in actions:
            if self._should_auto_approve(action):
                auto_approved.append(action)
                self._approval_store[action["key"]] = True
            else:
                pending_approval.append(action)

        return {
            "timestamp": datetime.now().isoformat(),
            "items_processed": len(items),
            "actions_proposed": len(actions),
            "auto_approved": auto_approved,
            "pending_approval": pending_approval,
        }

    async def _classify_and_propose(self, item: dict, llm_call) -> dict[str, Any] | None:
        source = item.get("source", "unknown")
        data = item.get("data", {})

        action = {
            "key": f"{source}:{hash(str(data))}",
            "source": source,
            "description": f"Process item from {source}",
            "tier": ActionTier.LOW.value,
            "data": data,
        }

        if llm_call:
            messages = [
                {
                    "role": "system",
                    "content": "Classify this item and propose an action. Respond with JSON: {\"description\": \"...\", \"tier\": \"trivial|low|medium|high\", \"action\": \"...\"}",
                },
                {"role": "user", "content": f"Source: {source}\nData: {str(data)[:500]}"},
            ]
            try:
                response = await llm_call(messages)
                content = response.get("content", "")
                import json
                parsed = json.loads(content)
                action.update(parsed)
            except Exception as e:
                logger.debug(f"LLM classification failed: {e}")

        return action

    def _should_auto_approve(self, action: dict) -> bool:
        tier = action.get("tier", "low")
        key = action.get("key", "")

        if key in self._approval_store and self._approval_store[key]:
            return True

        return tier in (ActionTier.TRIVIAL.value, ActionTier.LOW.value)

    def register_scheduled_task(self, name: str, cron_expr: str, handler) -> None:
        self._scheduled_tasks.append({
            "name": name,
            "cron": cron_expr,
            "handler": handler,
        })

    @property
    def scheduled_tasks(self) -> list[dict]:
        return self._scheduled_tasks
