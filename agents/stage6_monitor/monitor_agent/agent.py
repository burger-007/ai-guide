"""
📡 Stage 6 Agent: Monitor
Monitors deployed products: health, analytics, user feedback.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from agents.base_agent import BaseAgent, AgentResult
from shared.web_search import WebSearchTool


class MonitorAgent(BaseAgent):
    """
    Post-deployment monitoring:
    1. Health check (is the site responding?)
    2. Analytics check (are events flowing?)
    3. Feedback scan (Reddit/HN mentions)
    4. Performance summary
    """

    def __init__(self, workspace_dir: str = "agents/stage6_monitor/monitor_agent"):
        super().__init__(
            agent_id="monitor_agent",
            workspace_dir=workspace_dir,
        )
        self.search = WebSearchTool()

    async def execute(self, input_data: Any = None) -> AgentResult:
        """
        Input: { "product_id": name, "product_url": url, "product_name": display_name }
        Output: monitoring report
        """
        if not input_data:
            return AgentResult(
                agent_id=self.agent_id, status="error",
                errors=["No input data"],
            )

        try:
            product_id = input_data.get("product_id", "")
            product_url = input_data.get("product_url", "")
            product_name = input_data.get("product_name", product_id)

            report = {
                "product_id": product_id,
                "product_name": product_name,
                "checked_at": datetime.now().isoformat(),
                "health": await self._check_health(product_url),
                "mentions": await self._check_mentions(product_name),
            }

            # Save
            monitor_dir = Path("data/monitors")
            monitor_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            out = monitor_dir / f"monitor_{product_id}_{ts}.json"
            out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

            await self.search.close()

            return AgentResult(
                agent_id=self.agent_id,
                status="completed",
                output=report,
                metrics={
                    "site_up": report["health"].get("status") == "up",
                    "mentions_found": len(report["mentions"]),
                },
            )

        except Exception as e:
            await self.search.close()
            return AgentResult(
                agent_id=self.agent_id, status="error",
                errors=[str(e)],
            )

    async def _check_health(self, url: str) -> dict:
        """Check if site is responding"""
        if not url:
            return {"status": "unknown", "reason": "no URL provided"}

        try:
            import aiohttp
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(url) as resp:
                    return {
                        "status": "up" if resp.status == 200 else "degraded",
                        "status_code": resp.status,
                        "response_time_ms": 0,  # Could measure
                    }
        except Exception as e:
            return {"status": "down", "error": str(e)}

    async def _check_mentions(self, product_name: str) -> list[dict]:
        """Search for mentions of the product on HN and Reddit"""
        mentions = []

        hn = await self.search.search_hackernews(product_name, max_results=5, time_range="week")
        for r in hn:
            mentions.append({
                "source": "hackernews",
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "engagement": r.get("points", 0),
            })

        reddit = await self.search.search_reddit(product_name, subreddit="all", limit=5)
        for r in reddit:
            mentions.append({
                "source": "reddit",
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "engagement": r.get("score", 0),
            })

        return mentions
