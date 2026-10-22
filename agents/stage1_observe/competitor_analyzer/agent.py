"""
🔭 Stage 1 Agent: Competitor Analyzer
Analyzes existing tools to find gaps and weaknesses we can exploit.
"""

import json
from datetime import datetime
from typing import Any

from agents.base_agent import BaseAgent, AgentResult
from shared.web_search import WebSearchTool
from shared.llm_client import LLMClient


class CompetitorAnalyzerAgent(BaseAgent):
    """
    Finds and analyzes existing tools in a given market.
    Identifies pricing gaps, UX weaknesses, and unmet features.
    """

    def __init__(self, workspace_dir: str = "agents/stage1_observe/competitor_analyzer",
                 llm_client: LLMClient = None):
        super().__init__(
            agent_id="competitor_analyzer",
            workspace_dir=workspace_dir,
            llm_client=llm_client,
        )
        self.search = WebSearchTool()

    async def execute(self, input_data: Any = None) -> AgentResult:
        """
        Input: a market/need description (from trend_scanner or pain_point_finder)
        Output: competitive analysis with gap identification
        """
        try:
            # Determine what market to analyze
            market_query = self._extract_market_query(input_data)

            if not market_query:
                # If no specific market, scan for general opportunities
                market_query = await self._discover_hot_markets()

            # 1. Find competitors
            competitor_data = await self._find_competitors(market_query)

            # 2. Find user complaints
            complaints = await self._find_user_complaints(market_query, competitor_data)

            # 3. LLM: deep analysis
            analysis = await self._analyze_with_llm(market_query, competitor_data, complaints)

            # 4. Save
            self.save_to_memory(
                key=f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                value=analysis,
                memory_type="working",
            )

            await self.search.close()

            return AgentResult(
                agent_id=self.agent_id,
                status="completed",
                output=analysis,
                metrics={
                    "market_analyzed": market_query,
                    "competitors_found": len(competitor_data),
                    "complaints_collected": len(complaints),
                    "confidence": analysis.get("recommendation", {}).get("confidence", 0) if analysis else 0,
                },
            )

        except Exception as e:
            await self.search.close()
            return AgentResult(
                agent_id=self.agent_id,
                status="error",
                errors=[str(e)],
            )

    def _extract_market_query(self, input_data: Any) -> str:
        """Extract market/need from input"""
        if not input_data:
            return ""
        if isinstance(input_data, str):
            return input_data
        if isinstance(input_data, dict):
            return (
                input_data.get("market", "")
                or input_data.get("pain_point", "")
                or input_data.get("title", "")
                or input_data.get("recommended_solution", "")
            )
        return ""

    async def _discover_hot_markets(self) -> str:
        """If no market specified, find one from trending signals"""
        # Search for "alternative to" patterns — these indicate unmet needs
        results = await self.search.search_ddg(
            "free alternative to popular SaaS tool 2026",
            max_results=5
        )
        if results:
            return results[0].get("title", "productivity tools")
        return "developer productivity tools"

    async def _find_competitors(self, market_query: str) -> list[dict]:
        """Find existing tools in this market"""
        search_queries = [
            f"best {market_query} tools 2026",
            f"{market_query} software alternatives",
            f"top free {market_query} tools",
        ]

        all_results = []
        for query in search_queries:
            results = await self.search.search_ddg(query, max_results=5)
            all_results.extend(results)

        # Also check Reddit
        reddit_results = await self.search.search_reddit(
            query=f"{market_query} tool recommendation",
            subreddit="all",
            limit=5
        )
        all_results.extend(reddit_results)

        return all_results

    async def _find_user_complaints(self, market_query: str,
                                     competitors: list[dict]) -> list[dict]:
        """Search for user complaints about existing tools"""
        complaints = []

        # Search for complaints
        complaint_queries = [
            f"{market_query} tool frustrating",
            f"{market_query} tool too expensive",
            f"hate {market_query} tool",
            f"{market_query} free alternative",
        ]

        for query in complaint_queries[:2]:  # Rate limit
            results = await self.search.search_reddit(
                query=query, subreddit="all", limit=5
            )
            for r in results:
                if r.get("score", 0) > 5:
                    complaints.append({
                        "source": "reddit",
                        "title": r.get("title", ""),
                        "text": r.get("selftext", "")[:500],
                        "score": r.get("score", 0),
                        "url": r.get("url", ""),
                    })

            # Also web search
            web_results = await self.search.search_ddg(query, max_results=3)
            for r in web_results:
                complaints.append({
                    "source": "web",
                    "title": r.get("title", ""),
                    "text": r.get("snippet", ""),
                    "url": r.get("url", ""),
                })

        return complaints

    async def _analyze_with_llm(self, market_query: str,
                                  competitor_data: list[dict],
                                  complaints: list[dict]) -> dict:
        """LLM deep analysis of the competitive landscape"""
        if not self.llm_client:
            return {"error": "No LLM client configured"}

        system_prompt = self.build_system_prompt()

        user_prompt = f"""
Analyze the competitive landscape for: "{market_query}"

## Competitor Search Results
{json.dumps(competitor_data[:15], indent=2, default=str)}

## User Complaints Found
{json.dumps(complaints[:15], indent=2, default=str)}

## YOUR TASK
1. Identify the top 3-5 actual competitor products from the search results
2. For each, assess: pricing, strengths, weaknesses, user complaints
3. Find the GAP — what's missing from all of them?
4. Recommend what FREE tool we should build to fill that gap
5. Explain the data collection angle (what data this tool naturally generates)

Return as a JSON object matching your output format.
Focus on actionable, buildable opportunities.
"""

        try:
            return await self.llm_client.chat_json(
                system=system_prompt,
                user=user_prompt,
            )
        except Exception:
            return {"error": "LLM analysis failed", "market": market_query}
