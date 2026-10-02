import urllib.parse
import urllib.request
import json
import re
from typing import Any, Dict

from .skill_base import BaseSkill, SkillTool


class WebResearchSkill(BaseSkill):
    id = "web_researcher"
    display_name = "Live Web Intelligence & Doc Fetcher"
    description = "Query online technical documentation, APIs, and search results."
    icon = "globe-alt"

    def _setup_tools(self):
        self.tools.append(
            SkillTool(
                name="web_search",
                description="Search the web for up-to-date documentation, API syntax, or technical questions.",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query keywords"},
                    },
                    "required": ["query"],
                },
                handler=self.tool_web_search,
            )
        )
        self.tools.append(
            SkillTool(
                name="fetch_webpage",
                description="Fetch the text content of a documentation or webpage URL.",
                parameters={
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "HTTP or HTTPS URL to fetch"},
                    },
                    "required": ["url"],
                },
                handler=self.tool_fetch_webpage,
            )
        )

    def tool_web_search(self, query: str) -> Dict[str, Any]:
        """Perform search using DuckDuckGo Instant Answers or HTML query."""
        try:
            encoded = urllib.parse.quote(query)
            url = f"https://api.duckduckgo.com/?q={encoded}&format=json&no_html=1&skip_disambig=1"
            req = urllib.request.Request(url, headers={"User-Agent": "JarvisCodingAssistant/2.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8", errors="ignore"))

            results = []
            if data.get("AbstractText"):
                results.append({
                    "title": data.get("Heading", "Instant Answer"),
                    "snippet": data.get("AbstractText"),
                    "url": data.get("AbstractURL", ""),
                })

            for topic in data.get("RelatedTopics", [])[:5]:
                if isinstance(topic, dict) and topic.get("Text"):
                    results.append({
                        "title": topic.get("Text")[:60] + "...",
                        "snippet": topic.get("Text"),
                        "url": topic.get("FirstURL", ""),
                    })

            if not results:
                results.append({
                    "title": f"Search Results for '{query}'",
                    "snippet": f"Web search initiated for '{query}'. Direct internet links available.",
                    "url": f"https://www.google.com/search?q={encoded}",
                })

            return {"query": query, "results": results}
        except Exception as e:
            return {
                "query": query,
                "error": str(e),
                "fallback_url": f"https://www.google.com/search?q={urllib.parse.quote(query)}",
            }

    def tool_fetch_webpage(self, url: str) -> Dict[str, Any]:
        try:
            if not url.startswith("http://") and not url.startswith("https://"):
                url = "https://" + url
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Jarvis/2.0"})
            with urllib.request.urlopen(req, timeout=12) as resp:
                html = resp.read().decode("utf-8", errors="ignore")

            # Extract basic text content by stripping HTML tags
            text = re.sub(r"<script[^>]*>[\s\S]*?</script>", "", html, flags=re.IGNORECASE)
            text = re.sub(r"<style[^>]*>[\s\S]*?</style>", "", text, flags=re.IGNORECASE)
            text = re.sub(r"<[^>]+>", " ", text)
            clean_text = " ".join(text.split())

            return {
                "url": url,
                "length": len(clean_text),
                "content": clean_text[:4000] + ("\n... [truncated]" if len(clean_text) > 4000 else ""),
            }
        except Exception as e:
            return {"url": url, "error": str(e)}
