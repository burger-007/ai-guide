"""
📊 Stage 2 Agent: Feasibility Checker
Validates PRDs before they reach the build stage.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from agents.base_agent import BaseAgent, AgentResult
from shared.web_search import WebSearchTool
from shared.llm_client import LLMClient


class FeasibilityCheckerAgent(BaseAgent):
    """
    Reviews PRDs and catches showstoppers:
    1. Technical feasibility
    2. Time estimate validation  
    3. Competitor quick-check (web search)
    4. Data collection sanity
    5. Deployment cost estimate
    """

    def __init__(self, workspace_dir: str = "agents/stage2_analyze/feasibility_checker",
                 llm_client: LLMClient = None):
        super().__init__(
            agent_id="feasibility_checker",
            workspace_dir=workspace_dir,
            llm_client=llm_client,
        )
        self.search = WebSearchTool()

    async def execute(self, input_data: Any = None) -> AgentResult:
        """
        Input: PRD dict from prd_generator
        Output: feasibility report with GO/REVISE/ABORT verdict
        """
        if not input_data:
            return AgentResult(
                agent_id=self.agent_id, status="error",
                errors=["No PRD provided"],
            )

        if not self.llm_client:
            return AgentResult(
                agent_id=self.agent_id, status="error",
                errors=["No LLM client configured"],
            )

        try:
            prd = input_data
            if isinstance(input_data, dict) and "prd" in input_data:
                prd = input_data["prd"]

            # 1. Competition check (web search — real data)
            product_name = prd.get("product_overview", {}).get("display_name", "")
            tagline = prd.get("product_overview", {}).get("tagline", "")
            competitor_data = await self._check_competitors(product_name, tagline)

            # 2. LLM: full feasibility analysis
            report = await self._analyze_feasibility(prd, competitor_data)

            if not report:
                return AgentResult(
                    agent_id=self.agent_id, status="error",
                    errors=["LLM failed to generate feasibility report"],
                )

            # 3. Save report
            self._save_report(product_name, report)

            await self.search.close()

            # Save to memory
            self.save_to_memory(
                key=f"feasibility_{product_name}",
                value=report,
                memory_type="working",
            )

            return AgentResult(
                agent_id=self.agent_id,
                status="completed",
                output=report,
                metrics={
                    "verdict": report.get("verdict", "UNKNOWN"),
                    "confidence": report.get("confidence", 0),
                    "estimated_hours": report.get("total_estimated_hours", 0),
                    "issues_found": len(report.get("feasibility_issues", [])),
                    "critical_issues": len([
                        i for i in report.get("feasibility_issues", [])
                        if i.get("severity") == "critical"
                    ]),
                },
            )

        except Exception as e:
            await self.search.close()
            return AgentResult(
                agent_id=self.agent_id, status="error",
                errors=[str(e)],
            )

    async def _check_competitors(self, product_name: str, tagline: str) -> list[dict]:
        """Search for existing competitors via web search"""
        queries = [
            f"{product_name} free tool",
            f"free {tagline}",
            f"{product_name} alternative",
        ]

        all_results = []
        for q in queries[:2]:
            results = await self.search.search_ddg(q, max_results=5)
            all_results.extend(results)

            # Also check HN
            hn_results = await self.search.search_hackernews(q, max_results=3)
            all_results.extend(hn_results)

        return all_results

    async def _analyze_feasibility(self, prd: dict, competitor_data: list) -> dict:
        """LLM performs comprehensive feasibility analysis"""
        system_prompt = self.build_system_prompt()

        user_prompt = f"""Analyze this PRD for feasibility:

PRD:
{json.dumps(prd, indent=2, default=str)}

COMPETITOR SEARCH RESULTS (from real web search):
{json.dumps(competitor_data[:10], indent=2, default=str)}

PERFORM ALL 5 CHECKS:
1. Technical Feasibility — Can every feature be built with the tech stack?
2. Time Estimate — Break down each P0 feature into hours. Total must be <= 40 hours.
3. Competitor Check — Based on the search results, does a good free alternative exist?
4. Data Collection Sanity — Are the analytics events useful and privacy-safe?
5. Deployment Cost — Will it run on Vercel free tier at 1K/10K/100K users?

DECISION RULES:
- Any CRITICAL issue → verdict = REVISE or ABORT
- Total hours > 50 → REVISE (cut scope)
- Strong free competitor → ABORT
- Cost > $50/month at 10K users → REVISE
- Otherwise → GO

Return as JSON matching the output format in your instructions.
Be honest and specific — vague "it should be fine" is not acceptable."""

        try:
            return await self.llm_client.chat_json(
                system=system_prompt,
                user=user_prompt,
                temperature=0.2,
            )
        except Exception as e:
            print(f"   [Feasibility Checker error: {e}]")
            return None

    def _save_report(self, product_name: str, report: dict):
        """Save feasibility report to disk"""
        report_dir = Path("data/feasibility")
        report_dir.mkdir(parents=True, exist_ok=True)

        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in product_name.lower())
        filename = f"{safe_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_file = report_dir / filename
        report_file.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        print(f"   Feasibility report saved: {report_file}")
