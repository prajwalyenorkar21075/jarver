"""Unified CAD Command Executor implementing the complete pipeline:
INPUT -> INTENT PARSER -> CAD COMMAND PLAN -> CAD CONTEXT -> VALIDATION -> REAL CAD FUNCTION -> GEOMETRY ENGINE -> MODEL STATE -> VIEWPORT/UI UPDATE -> VERIFICATION -> RESULT.
"""
import logging
import time
from typing import Optional, Dict, Any

from app.cad_engine.core.document import get_active_document
from app.cad_engine.commands.parser import get_intent_parser, CADPlan
from app.cad_engine.commands.context import get_cad_context, CADContext
from app.cad_engine.commands.registry import get_function_registry
from app.cad_engine.features.modeling import CADModelingOperations

logger = logging.getLogger("jarvis.cad.executor")


class CADCommandExecutor:
    """Executes natural language & structured CAD commands against the real CAD engine."""

    def __init__(self):
        self.parser = get_intent_parser()
        self.registry = get_function_registry()
        self.context = get_cad_context()

    def execute(self, text: str, context_overrides: Optional[dict] = None) -> dict:
        """
        Main pipeline entry point.
        """
        t0 = time.time()
        doc = get_active_document()

        # Update context from client if provided
        if context_overrides:
            self.context.update_from_dict(context_overrides)

        # Stage 1: INTENT PARSER -> CAD COMMAND PLAN
        plan: Optional[CADPlan] = self.parser.parse(text)
        if not plan:
            return {
                "success": False,
                "recognized": False,
                "message": f"I did not recognize a valid CAD operation in: '{text}'.",
                "spoken_reply": "I did not recognize that CAD command, sir.",
                "duration_ms": round((time.time() - t0) * 1000, 1),
            }

        # Handle viewport-only actions (Fit view, section view)
        if plan.is_viewport_only:
            return {
                "success": True,
                "recognized": True,
                "action": plan.action,
                "viewport_action": plan.action.lower(),
                "message": plan.spoken_summary,
                "spoken_reply": plan.spoken_summary,
                "context": self.context.to_dict(),
                "duration_ms": round((time.time() - t0) * 1000, 1),
            }

        # Stage 2: RESOLVE TARGET & AMBIGUITY (CURRENT CAD CONTEXT)
        target_id = None
        params = dict(plan.parameters)

        if plan.requires_target:
            target_res = self.context.resolve_target(plan.target_query, doc)
            if target_res.is_ambiguous:
                return {
                    "success": False,
                    "recognized": True,
                    "ambiguous": True,
                    "action": plan.action,
                    "candidates": target_res.candidates,
                    "message": target_res.error_msg,
                    "spoken_reply": target_res.error_msg,
                    "duration_ms": round((time.time() - t0) * 1000, 1),
                }
            if not target_res.feature_id:
                return {
                    "success": False,
                    "recognized": True,
                    "message": target_res.error_msg or "No target object could be identified.",
                    "spoken_reply": target_res.error_msg or "Please select an object in the CAD viewport first, sir.",
                    "duration_ms": round((time.time() - t0) * 1000, 1),
                }
            target_id = target_res.feature_id
            params["feature_id"] = target_id

        # Stage 3: FUNCTION REGISTRY LOOKUP
        cad_fn = self.registry.get(plan.action)
        if not cad_fn:
            return {
                "success": False,
                "recognized": True,
                "message": f"CAD capability '{plan.action}' is not registered in the system registry.",
                "spoken_reply": f"The CAD operation {plan.action} is currently unavailable, sir.",
                "duration_ms": round((time.time() - t0) * 1000, 1),
            }

        # Stage 4: VALIDATION
        if cad_fn.validator:
            v_res = cad_fn.validator(params, self.context, doc)
            if isinstance(v_res, tuple):
                is_valid, validation_err = v_res
            else:
                is_valid, validation_err = bool(v_res), None

            if not is_valid:
                return {
                    "success": False,
                    "recognized": True,
                    "validation_failed": True,
                    "message": f"Validation error: {validation_err or 'Invalid parameters'}",
                    "spoken_reply": f"Cannot execute that command, sir. {validation_err or 'Invalid parameters'}",
                    "duration_ms": round((time.time() - t0) * 1000, 1),
                }

        # Stage 5: REAL CAD FUNCTION EXECUTION (GEOMETRY ENGINE)
        try:
            result = cad_fn.handler(params, self.context, doc)
        except Exception as e:
            logger.error(f"[CAD EXECUTOR] Execution error in {plan.action}: {e}", exc_info=True)
            return {
                "success": False,
                "recognized": True,
                "execution_error": True,
                "message": f"CAD engine execution failed: {str(e)}",
                "spoken_reply": f"The CAD engine encountered an error while executing {plan.action}, sir.",
                "duration_ms": round((time.time() - t0) * 1000, 1),
            }

        # Stage 6: VERIFICATION
        if cad_fn.verifier:
            v_res = cad_fn.verifier(params, result, doc)
            if isinstance(v_res, tuple):
                verified, verify_err = v_res
            else:
                verified, verify_err = bool(v_res), None

            if not verified:
                return {
                    "success": False,
                    "recognized": True,
                    "verification_failed": True,
                    "message": f"Post-execution verification failed: {verify_err or 'Verification failed'}",
                    "spoken_reply": "The command executed but the resulting geometry could not be verified in the document, sir.",
                    "duration_ms": round((time.time() - t0) * 1000, 1),
                }

        # Stage 7: UPDATE CONTEXT & PREPARE RESULT
        affected_id = None
        if hasattr(result, "id"):
            affected_id = result.id
            self.context.record_created(result.id, getattr(result, "name", "Feature"))
        elif target_id:
            affected_id = target_id
            self.context.selected_feature_id = target_id

        # Fetch fresh meshes for real-time viewport update
        document_meshes = CADModelingOperations.get_all_document_meshes(tolerance=0.1)

        duration_ms = round((time.time() - t0) * 1000, 1)
        spoken = plan.spoken_summary or f"{plan.action.replace('_', ' ').capitalize()} complete, sir."
        if isinstance(result, dict) and "bounding_box" in result:
            bb = result["bounding_box"]
            spoken = f"The bounding box is {bb['width']:g} by {bb['height']:g} by {bb['depth']:g} millimeters, sir."

        payload = {
            "success": True,
            "recognized": True,
            "action": plan.action,
            "feature_id": affected_id,
            "parameters": params,
            "result": result if not hasattr(result, "id") else None,
            "message": f"Successfully executed {plan.action} ({duration_ms}ms).",
            "spoken_reply": spoken,
            "context": self.context.to_dict(),
            "meshes": document_meshes.get("meshes", []),
            "sketches": document_meshes.get("sketches", []),
            "duration_ms": duration_ms,
        }
        if isinstance(result, dict):
            for k, v in result.items():
                if k not in payload:
                    payload[k] = v
        return payload


_global_executor = CADCommandExecutor()


def get_command_executor() -> CADCommandExecutor:
    return _global_executor
