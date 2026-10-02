"""HTTP request tool with SSRF protection."""

import logging
import httpx
from . import BaseTool, ToolSpec, ToolRegistry
from ..security.ssrf import ssrf_checker

logger = logging.getLogger(__name__)


@ToolRegistry.register("http_request")
class HTTPRequestTool(BaseTool):
    """Make HTTP requests with SSRF protection."""

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="http_request",
            description="Make HTTP GET/POST requests to external URLs. Includes SSRF protection — internal/private IPs are blocked.",
            parameters={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to request"},
                    "method": {"type": "string", "description": "HTTP method (GET, POST, PUT, DELETE)", "default": "GET"},
                    "headers": {"type": "object", "description": "Request headers"},
                    "body": {"type": "string", "description": "Request body for POST/PUT"},
                    "timeout": {"type": "integer", "description": "Timeout in seconds", "default": 30},
                },
                "required": ["url"]
            },
            category="web",
        )

    async def execute(self, url: str = "", method: str = "GET", headers: dict = None,
                      body: str = None, timeout: int = 30, **kwargs) -> dict:
        safe, reason = ssrf_checker.check(url)
        if not safe:
            return {"error": f"URL blocked by SSRF protection: {reason}"}

        timeout = min(timeout, 60)

        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                resp = await client.request(
                    method=method.upper(),
                    url=url,
                    headers=headers,
                    content=body,
                )

                content = resp.text[:10000]
                return {
                    "status_code": resp.status_code,
                    "content_type": resp.headers.get("content-type", ""),
                    "content": content,
                    "size": len(resp.content),
                }
        except httpx.TimeoutException:
            return {"error": f"Request timed out after {timeout}s"}
        except Exception as e:
            return {"error": str(e)}
