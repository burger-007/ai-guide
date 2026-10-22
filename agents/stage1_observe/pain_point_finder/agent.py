"""
🔭 Stage 1 Agent: Pain Point Finder
Scans online communities for recurring user frustrations.
"""

import json
from datetime import datetime
from typing import Any

from agents.base_agent import BaseAgent, AgentResult
from shared.web_search import WebSearchTool
from shared.llm_client import LLMClient

# Keywords that indicate real pain points
PAIN_KEYWORDS = [
    "I wish there was",
    "looking for a tool",
    "any free alternative",
    "hate paying for",
    "frustrated with",
    "does anyone know",
    "need help with",
    "too expensive",
    "too complicated",
    "anyone built",
    "simple tool for",
]

WATCH_SUBREDDITS = [
    "SideProject", "webdev", "startups", "SaaS",
    "Entrepreneur", "smallbusiness", "InternetIsBeautiful",
    "selfhosted", "nocode",
]


class PainPointFinderAgent(BaseAgent):
    """
    Scans Reddit, HN, web for recurring pain points
    that can be solved with a free web tool.
    """

    def __init__(self, workspace_dir: str = "agents/stage1_observe/pain_point_finder",
                 llm_client: LLMClient = None):
        super().__init__(
            agent_id="pain_point_finder",
            workspace_dir=workspace_dir,
            llm_client=llm_client,
        )
        self.search = WebSearchTool()

    async def execute(self, input_data: Any = None) -> AgentResult:
        """
        Main flow: search communities → extract pain points → score → rank
        """
        try:
            # 1. Gather raw data from multiple sources
            raw_data = await self._gather_community_data()

            if not raw_data:
                return AgentResult(
                    agent_id=self.agent_id,
                    status="completed",
                    output=[],
                    metrics={"sources_scanned": 0, "opportunities_found": 0},
                )

            # 2. LLM: analyze and extract opportunities
            opportunities = await self._analyze_with_llm(raw_data)

            # 3. Score and rank
            ranked = self._rank_opportunities(opportunities)

            # 4. Save to memory
            self.save_to_memory(
                key=f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                value=ranked,
                memory_type="working",
            )

            await self.search.close()

            return AgentResult(
                agent_id=self.agent_id,
                status="completed",
                output=ranked,
                metrics={
                    "sources_scanned": len(raw_data),
                    "opportunities_found": len(ranked),
                    "top_score": ranked[0]["priority_score"] if ranked else 0,
                },
            )

        except Exception as e:
            await self.search.close()
            return AgentResult(
                agent_id=self.agent_id,
                status="error",
                errors=[str(e)],
            )

    async def _gather_community_data(self) -> list[dict]:
        """Gather posts from Reddit, HN, and web search"""
        import asyncio

        tasks = []

        # Reddit: search each subreddit with pain keywords
        for subreddit in WATCH_SUBREDDITS[:4]:  # Rate limit
            for keyword in PAIN_KEYWORDS[:3]:
                tasks.append(
                    self.search.search_reddit(
                        query=keyword, subreddit=subreddit, limit=5
                    )
                )

        # HN: search for pain point patterns
        for keyword in ["looking for", "alternative to", "frustrated"]:
            tasks.append(
                self.search.search_hackernews(keyword, max_results=5)
            )

        # Web: general search
        for keyword in PAIN_KEYWORDS[:2]:
            tasks.append(
                self.search.search_ddg(f"{keyword} tool 2026", max_results=5)
            )

        results = await asyncio.gather(*tasks, return_exceptions=True)

        posts = []
        for result in results:
            if isinstance(result, list):
                for item in result:
                    # Filter: only keep items with some engagement
                    engagement = (
                        item.get("score", 0)
                        or item.get("points", 0)
                        or item.get("engagement", 0)
                    )
                    if engagement > 5 or item.get("source") == "web":
                        posts.append(item)

        # Deduplicate by title
        seen_titles = set()
        unique_posts = []
        for post in posts:
            title = post.get("title", "").lower().strip()
            if title and title not in seen_titles:
                seen_titles.add(title)
                unique_posts.append(post)

        return unique_posts

    async def _analyze_with_llm(self, raw_data: list[dict]) -> list[dict]:
        """Use LLM to extract and structure opportunities from raw data"""
        if not self.llm_client:
            return []

        system_prompt = self.build_system_prompt()

        # Take top posts by engagement
        top_posts = sorted(
            raw_data,
            key=lambda x: x.get("score", 0) or x.get("points", 0) or x.get("engagement", 0),
            reverse=True
        )[:30]

        user_prompt = f"""
Analyze the following {len(top_posts)} community posts from Reddit, Hacker News, and web searches.

POSTS:
{json.dumps(top_posts, indent=2, default=str)}

YOUR TASK:
1. Identify recurring PAIN POINTS — problems mentioned by multiple users
2. For each pain point, check if it meets ALL qualification criteria:
   - Multiple evidence (≥2 independent mentions)
   - Solvable with a web app
   - No dominant free solution exists
   - Buildable in <1 week
   - Data collection potential
3. Score each opportunity using the scoring formula in your instructions
4. Only include opportunities scoring ≥ 6.0

Return a JSON array of opportunity objects with these fields:
- id: unique identifier
- title: one-line description
- pain_point: detailed problem statement
- evidence: array of supporting posts (title, url, source, engagement)
- market_size_estimate: small/medium/large
- competition_level: none/low/medium/high (1-10 where 10=none, 1=high)
- technical_feasibility: low/medium/high (1-10)
- data_collection_potential: 1-10
- priority_score: calculated composite score
- recommended_solution: what to build

Maximum 10 opportunities.
"""

        try:
            result = await self.llm_client.chat_json(
                system=system_prompt,
                user=user_prompt,
            )
            if isinstance(result, list):
                return result
            if isinstance(result, dict) and "opportunities" in result:
                return result["opportunities"]
        except Exception:
            pass

        return []

    def _rank_opportunities(self, opportunities: list[dict]) -> list[dict]:
        """Sort opportunities by priority score"""
        return sorted(
            opportunities,
            key=lambda x: x.get("priority_score", 0),
            reverse=True
        )
