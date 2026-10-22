"""
🔍 Stage 3 Agent: Quality Checker
Reviews generated code for completeness, quality, security.
"""

import json
from pathlib import Path
from typing import Any

from agents.base_agent import BaseAgent, AgentResult
from shared.llm_client import LLMClient


class QualityCheckerAgent(BaseAgent):
    """
    Reviews generated Next.js code against the PRD.
    Checks: completeness, syntax, security, UX, analytics, SEO.
    """

    def __init__(self, workspace_dir: str = "agents/stage3_build/quality_checker",
                 llm_client: LLMClient = None):
        super().__init__(
            agent_id="quality_checker",
            workspace_dir=workspace_dir,
            llm_client=llm_client,
        )

    async def execute(self, input_data: Any = None) -> AgentResult:
        """
        Input: { "prd": PRD dict, "product_dir": path, "files": list }
        Output: quality report with PASS/NEEDS_FIX/FAIL
        """
        if not input_data or not self.llm_client:
            return AgentResult(
                agent_id=self.agent_id, status="error",
                errors=["Missing input or LLM client"],
            )

        try:
            prd = input_data.get("prd", {})
            product_dir = Path(input_data.get("product_dir", ""))
            file_list = input_data.get("files", [])

            # Read all generated files
            file_contents = {}
            for filepath in file_list:
                full_path = product_dir / filepath
                if full_path.exists() and full_path.stat().st_size < 50000:
                    try:
                        file_contents[filepath] = full_path.read_text(encoding="utf-8")
                    except Exception:
                        file_contents[filepath] = "[UNREADABLE]"

            # LLM review
            report = await self._review_code(prd, file_contents)

            if not report:
                return AgentResult(
                    agent_id=self.agent_id, status="error",
                    errors=["LLM failed to generate quality report"],
                )

            # Save report
            report_file = product_dir / "quality_report.json"
            report_file.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

            return AgentResult(
                agent_id=self.agent_id,
                status="completed",
                output=report,
                metrics={
                    "verdict": report.get("verdict", "UNKNOWN"),
                    "score": report.get("score", 0),
                    "issues_count": len(report.get("issues", [])),
                    "blockers": len([i for i in report.get("issues", []) if i.get("severity") == "blocker"]),
                },
            )

        except Exception as e:
            return AgentResult(
                agent_id=self.agent_id, status="error",
                errors=[str(e)],
            )

    async def _review_code(self, prd: dict, files: dict[str, str]) -> dict:
        """LLM performs comprehensive code review"""
        system_prompt = self.build_system_prompt()

        # Build file digest (truncate very large files)
        file_digest = {}
        for path, content in files.items():
            if len(content) > 3000:
                file_digest[path] = content[:3000] + "\n... [truncated]"
            else:
                file_digest[path] = content

        overview = prd.get("product_overview", {})
        features = prd.get("feature_spec", [])

        user_prompt = f"""Review this generated Next.js application:

PRODUCT: {overview.get('display_name', '')}
PRD FEATURES: {json.dumps([f.get('feature_name', '') for f in features], default=str)}

GENERATED FILES ({len(file_digest)} total):
{json.dumps(file_digest, indent=2, default=str)}

REVIEW ALL 7 AREAS:
1. Completeness — Are all PRD features implemented?
2. Syntax — Any obvious errors?
3. Functionality — Do user flows work?
4. Security — Exposed keys? XSS? Injection?
5. UX — Loading states? Error handling? Mobile?
6. Analytics — PostHog events on all key actions?
7. SEO — Meta tags, title, description?

Return as JSON:
{{
  "verdict": "PASS | NEEDS_FIX | FAIL",
  "score": 0-100,
  "issues": [
    {{
      "severity": "blocker | major | minor",
      "file": "path",
      "description": "what's wrong",
      "fix_suggestion": "how to fix"
    }}
  ],
  "missing_features": [],
  "missing_files": [],
  "ready_for_review": true/false
}}"""

        try:
            return await self.llm_client.chat_json(
                system=system_prompt,
                user=user_prompt,
                temperature=0.2,
            )
        except Exception as e:
            print(f"   [Quality Checker error: {e}]")
            return None
