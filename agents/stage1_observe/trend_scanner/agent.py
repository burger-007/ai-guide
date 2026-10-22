"""
🔭 Stage 1 Agent: Trend Scanner
Scans HN, GitHub, Reddit for emerging tech trends.
"""

import json
from datetime import datetime
from typing import Any

from agents.base_agent import BaseAgent, AgentResult
from shared.web_search import WebSearchTool
from shared.llm_client import LLMClient


# Keywords that signal buildable opportunities
TREND_QUERIES = [
    "new developer tool",
    "AI tool launch 2026",
    "free alternative to",
    "open source tool",
    "API just launched",
    "no-code tool",
    "productivity tool",
    "built in a weekend",
    "Show HN",
]

# Subreddits to monitor for tool trends
TREND_SUBREDDITS = [
    "webdev", "SideProject", "SaaS", "startups",
    "Entrepreneur", "InternetIsBeautiful", "coolgithubprojects",
]


class TrendScannerAgent(BaseAgent):
    """
    Scans HN front page, GitHub trending, Reddit for rising tech trends.
    Identifies opportunities to build tools that ride emerging waves.
    """

    def __init__(self, workspace_dir: str = "agents/stage1_observe/trend_scanner",
                 llm_client: LLMClient = None):
        super().__init__(
            agent_id="trend_scanner",
            workspace_dir=workspace_dir,
            llm_client=llm_client,
        )
        self.search = WebSearchTool()

    async def execute(self, input_data: Any = None) -> AgentResult:
        """
        Flow: gather signals → LLM analysis → score trends → rank
        """
        try:
            # 1. Gather signals from all sources concurrently
            signals = await self._gather_signals()

            if not signals:
                return AgentResult(
                    agent_id=self.agent_id,
                    status="completed",
                    output=[],
                    metrics={"signals_found": 0, "trends_identified": 0},
                )

            # 2. LLM: identify and cluster trends from raw signals
            trends = await self._identify_trends(signals)

            # 3. Score and rank
            ranked = sorted(trends, key=lambda t: t.get("trend_score", 0), reverse=True)

            # 4. Save scan results
            self.save_to_memory(
                key=f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                value={"signals_count": len(signals), "trends": ranked},
                memory_type="working",
            )

            await self.search.close()

            return AgentResult(
                agent_id=self.agent_id,
                status="completed",
                output=ranked,
                metrics={
                    "signals_found": len(signals),
                    "trends_identified": len(ranked),
                    "top_trend_score": ranked[0]["trend_score"] if ranked else 0,
                },
            )

        except Exception as e:
            await self.search.close()
            return AgentResult(
                agent_id=self.agent_id,
                status="error",
                errors=[str(e)],
            )

    async def _gather_signals(self) -> list[dict]:
        """Gather signals from HN, GitHub, Reddit in parallel"""
        import asyncio

        tasks = [
            self._scan_hackernews(),
            self._scan_github_trending(),
            self._scan_reddit_trends(),
            self._scan_web_trends(),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        signals = []
        for result in results:
            if isinstance(result, list):
                signals.extend(result)

        return signals

    async def _scan_hackernews(self) -> list[dict]:
        """Scan HN front page + search for tool launches"""
        signals = []

        # Front page
        front_page = await self.search.get_hn_front_page(limit=30)
        for item in front_page:
            if item.get("points", 0) > 50:
                signals.append({
                    "source": "hackernews",
                    "type": "front_page",
                    "title": item["title"],
                    "url": item.get("url", ""),
                    "engagement": item.get("points", 0),
                    "comments": item.get("comments", 0),
                    "timestamp": datetime.now().isoformat(),
                })

        # Search for specific patterns
        for query in ["Show HN", "Launch HN", "new tool"]:
            results = await self.search.search_hackernews(query, max_results=5)
            for r in results:
                if r.get("points", 0) > 20:
                    signals.append({
                        "source": "hackernews",
                        "type": "search",
                        "query": query,
                        "title": r["title"],
                        "url": r.get("url", ""),
                        "engagement": r.get("points", 0),
                        "comments": r.get("comments", 0),
                        "timestamp": r.get("created_at", ""),
                    })

        return signals

    async def _scan_github_trending(self) -> list[dict]:
        """Scan GitHub trending repos"""
        signals = []

        for lang in ["", "python", "typescript", "javascript"]:
            trending = await self.search.get_github_trending(language=lang, since="weekly")
            for repo in trending:
                signals.append({
                    "source": "github",
                    "type": "trending",
                    "title": repo.get("repo", ""),
                    "url": repo.get("url", ""),
                    "description": repo.get("description", ""),
                    "stars_today": repo.get("stars_today", 0),
                    "language": lang or "all",
                    "timestamp": datetime.now().isoformat(),
                })

        return signals

    async def _scan_reddit_trends(self) -> list[dict]:
        """Scan Reddit for trending tools and pain points"""
        signals = []

        for subreddit in TREND_SUBREDDITS[:4]:  # Rate limit awareness
            for query in ["free tool", "just launched", "built this"]:
                results = await self.search.search_reddit(
                    query=query, subreddit=subreddit, limit=5
                )
                for r in results:
                    if r.get("score", 0) > 10:
                        signals.append({
                            "source": "reddit",
                            "type": "search",
                            "subreddit": r.get("subreddit", subreddit),
                            "title": r["title"],
                            "url": r.get("url", ""),
                            "engagement": r.get("score", 0),
                            "comments": r.get("comments", 0),
                            "snippet": r.get("selftext", "")[:300],
                            "timestamp": datetime.now().isoformat(),
                        })

        return signals

    async def _scan_web_trends(self) -> list[dict]:
        """General web search for trending tools"""
        signals = []

        for query in TREND_QUERIES[:3]:  # Limit to avoid rate limiting
            results = await self.search.search_ddg(query, max_results=5)
            for r in results:
                signals.append({
                    "source": "web",
                    "type": "search",
                    "query": query,
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "snippet": r.get("snippet", ""),
                    "timestamp": datetime.now().isoformat(),
                })

        return signals

    async def _identify_trends(self, signals: list[dict]) -> list[dict]:
        """Use LLM to cluster signals into trends and score them"""
        if not self.llm_client:
            return []

        system_prompt = self.build_system_prompt()

        # Limit signals to avoid token overflow
        top_signals = sorted(
            signals,
            key=lambda s: s.get("engagement", 0),
            reverse=True
        )[:40]

        user_prompt = f"""
Analyze these {len(top_signals)} signals gathered from HN, GitHub, Reddit, and web searches.

SIGNALS:
{json.dumps(top_signals, indent=2, default=str)}

YOUR TASK:
1. Cluster related signals into TRENDS (group by theme)
2. For each trend, assess:
   - growth_velocity: low/medium/high/explosive
   - opportunity_window: how long until saturated
   - suggested_tools: what free web tools could ride this trend
   - trend_score: 1-10 based on your scoring matrix
3. Only include trends scoring ≥ 6.0
4. Maximum 10 trends

Return as a JSON array of trend objects matching your output format.
"""

        try:
            trends = await self.llm_client.chat_json(
                system=system_prompt,
                user=user_prompt,
            )
            if isinstance(trends, dict) and "trends" in trends:
                return trends["trends"]
            if isinstance(trends, list):
                return trends
        except (json.JSONDecodeError, Exception) as e:
            # Fallback: return raw signals as ungrouped trends
            return []

        return []
