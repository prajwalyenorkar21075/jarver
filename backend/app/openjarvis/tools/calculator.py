"""AST-based safe calculator tool."""

import ast
import math
import operator
import logging
from . import BaseTool, ToolSpec, ToolRegistry

logger = logging.getLogger(__name__)

_SAFE_BINOPS = {
    ast.Add: operator.add, ast.Sub: operator.sub,
    ast.Mult: operator.mul, ast.Div: operator.truediv,
    ast.Pow: operator.pow, ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv,
}

_SAFE_UNARYOPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}

_SAFE_FUNCTIONS = {
    "sqrt": math.sqrt, "log": math.log, "ln": math.log,
    "log10": math.log10, "log2": math.log2,
    "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "asin": math.asin, "acos": math.acos, "atan": math.atan,
    "abs": abs, "ceil": math.ceil, "floor": math.floor,
    "round": round, "min": min, "max": max,
    "pi": math.pi, "e": math.e,
}


def _safe_eval(node):
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError(f"Unsupported constant: {node.value}")
    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _SAFE_BINOPS:
            raise ValueError(f"Unsupported operator: {op_type.__name__}")
        left = _safe_eval(node.left)
        right = _safe_eval(node.right)
        if op_type == ast.Div and right == 0:
            return float("inf")
        if op_type == ast.FloorDiv and right == 0:
            return float("inf")
        return _SAFE_BINOPS[op_type](left, right)
    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _SAFE_UNARYOPS:
            raise ValueError(f"Unsupported unary op: {op_type.__name__}")
        return _SAFE_UNARYOPS[op_type](_safe_eval(node.operand))
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise ValueError("Only simple function calls allowed")
        func_name = node.func.id
        if func_name not in _SAFE_FUNCTIONS:
            raise ValueError(f"Unknown function: {func_name}")
        func = _SAFE_FUNCTIONS[func_name]
        if isinstance(func, (int, float)):
            return func
        args = [_safe_eval(a) for a in node.args]
        return func(*args)
    if isinstance(node, ast.Name):
        if node.id in _SAFE_FUNCTIONS:
            val = _SAFE_FUNCTIONS[node.id]
            if isinstance(val, (int, float)):
                return val
            raise ValueError(f"{node.id} is a function, not a constant")
        raise ValueError(f"Unknown name: {node.id}")
    raise ValueError(f"Unsupported expression: {type(node).__name__}")


@ToolRegistry.register("calculator")
class CalculatorTool(BaseTool):
    """Safe mathematical expression evaluator."""

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="calculator",
            description="Evaluate mathematical expressions safely. Supports +, -, *, /, ^, sqrt, log, sin, cos, tan, pi, e, etc.",
            parameters={
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Math expression to evaluate, e.g. '2^10 + sqrt(144)'"
                    }
                },
                "required": ["expression"]
            },
            category="utility",
        )

    async def execute(self, expression: str = "", **kwargs) -> dict:
        try:
            expr = expression.replace("^", "**")
            tree = ast.parse(expr, mode="eval")
            result = _safe_eval(tree)
            return {"result": result, "expression": expression}
        except ZeroDivisionError:
            return {"result": float("inf"), "expression": expression, "warning": "Division by zero"}
        except Exception as e:
            return {"error": str(e), "expression": expression}
