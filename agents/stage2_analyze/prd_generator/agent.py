"""
📊 Stage 2 Agent: PRD Generator
Transforms market opportunities into complete, buildable PRDs.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from agents.base_agent import BaseAgent, AgentResult
from shared.llm_client import LLMClient


class PRDGeneratorAgent(BaseAgent):
    """
    Takes an opportunity from Stage 1 and produces a full PRD
    that a code-generation agent can build from directly.
    """

    def __init__(self, workspace_dir: str = "agents/stage2_analyze/prd_generator",
                 llm_client: LLMClient = None):
        super().__init__(
            agent_id="prd_generator",
            workspace_dir=workspace_dir,
            llm_client=llm_client,
        )

    async def execute(self, input_data: Any = None) -> AgentResult:
        """
        Input: opportunity dict from Stage 1
        Output: complete PRD as structured JSON
        """
        if not input_data:
            return AgentResult(
                agent_id=self.agent_id, status="error",
                errors=["No opportunity provided"],
            )

        if not self.llm_client:
            return AgentResult(
                agent_id=self.agent_id, status="error",
                errors=["No LLM client configured"],
            )

        try:
            opportunity = input_data
            if isinstance(input_data, dict) and "opportunity" in input_data:
                opportunity = input_data["opportunity"]

            # Generate PRD
            prd = await self._generate_prd(opportunity)

            if not prd:
                return AgentResult(
                    agent_id=self.agent_id, status="error",
                    errors=["LLM failed to generate PRD"],
                )

            # Save PRD to file
            prd_id = prd.get("product_overview", {}).get("product_name", "unknown")
            self._save_prd(prd_id, prd)

            # Save to memory
            self.save_to_memory(
                key=f"prd_{prd_id}",
                value=prd,
                memory_type="working",
            )

            return AgentResult(
                agent_id=self.agent_id,
                status="completed",
                output=prd,
                metrics={
                    "product_name": prd_id,
                    "user_stories": len(prd.get("user_stories", [])),
                    "p0_features": len([
                        f for f in prd.get("feature_spec", [])
                        if f.get("priority") == "P0"
                    ]),
                    "pages": len(prd.get("ui_spec", {}).get("pages", [])),
                },
            )

        except Exception as e:
            return AgentResult(
                agent_id=self.agent_id, status="error",
                errors=[str(e)],
            )

    async def _generate_prd(self, opportunity: dict) -> dict:
        """Use LLM to generate a complete PRD from an opportunity"""
        system_prompt = self.build_system_prompt()

        user_prompt = f"""Generate a complete PRD for this opportunity:

OPPORTUNITY:
{json.dumps(opportunity, indent=2, default=str)}

REQUIREMENTS:
1. Product name must be a real, memorable name (not just the category)
2. Exactly 3-5 user stories, each with priority P0/P1/P2
3. At least 3 P0 features with complete user flows
4. Tech stack: Next.js 14 App Router + Tailwind CSS + Vercel + PostHog
5. Every page and feature must have analytics events defined
6. UI must be modern, clean, responsive — think premium free tool
7. Include specific color palette and font choices
8. Maximum 3 pages for MVP (main tool + privacy + optional about)
9. ALL text in English

Return as a single JSON object with these keys:
- product_overview (product_name, display_name, tagline, target_user, core_problem, success_metric)
- user_stories (array of {{story, priority, acceptance_criteria}})
- feature_spec (array of features with user_flow, input, output, data_events)
- tech_architecture (framework, styling, deployment, analytics, database, key_libraries, api_routes)
- data_collection_plan (analytics_events array, privacy_notes)
- ui_spec (pages array with path/layout/components, design_tokens with colors/font/style)
- launch_checklist (array of items)

Be SPECIFIC. This PRD goes directly to a code-generation agent — no ambiguity allowed."""

        try:
            prd = await self.llm_client.chat_json(
                system=system_prompt,
                user=user_prompt,
                temperature=0.3,
            )
            return prd
        except Exception as e:
            print(f"   [PRD Generator error: {e}]")
            return None

    def _save_prd(self, prd_id: str, prd: dict):
        """Save PRD to disk"""
        prd_dir = Path("data/prds")
        prd_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{prd_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        prd_file = prd_dir / filename
        prd_file.write_text(
            json.dumps(prd, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        print(f"   PRD saved: {prd_file}")
