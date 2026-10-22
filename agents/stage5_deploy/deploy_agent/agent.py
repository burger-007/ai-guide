"""
🚀 Stage 5 Agent: Deploy Agent
Handles build validation, GitHub push, Vercel deploy, and human review gate.
"""

import json
import subprocess
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from agents.base_agent import BaseAgent, AgentResult


class DeployAgent(BaseAgent):
    """
    Deployment pipeline:
    1. Validate build (npm run build)
    2. Create human review package
    3. Wait for approval
    4. Deploy to Vercel (when tokens are configured)
    """

    def __init__(self, workspace_dir: str = "agents/stage5_deploy/deploy_agent"):
        super().__init__(
            agent_id="deploy_agent",
            workspace_dir=workspace_dir,
        )

    async def execute(self, input_data: Any = None) -> AgentResult:
        """
        Input: {
            "product_dir": path to generated product,
            "product_id": product name,
            "prd": PRD dict,
            "quality_report": quality report dict,
            "security_report": security report dict (optional),
        }
        """
        if not input_data:
            return AgentResult(
                agent_id=self.agent_id, status="error",
                errors=["No input data provided"],
            )

        try:
            product_dir = Path(input_data.get("product_dir", ""))
            product_id = input_data.get("product_id", "unknown")
            prd = input_data.get("prd", {})
            quality_report = input_data.get("quality_report", {})
            security_report = input_data.get("security_report", {})

            if not product_dir.exists():
                return AgentResult(
                    agent_id=self.agent_id, status="error",
                    errors=[f"Product directory not found: {product_dir}"],
                )

            # Step 1: Validate package.json exists
            pkg = product_dir / "package.json"
            if not pkg.exists():
                return AgentResult(
                    agent_id=self.agent_id, status="error",
                    errors=["No package.json found"],
                )

            # Step 2: Check for leaked secrets
            secret_check = self._check_secrets(product_dir)
            if secret_check:
                return AgentResult(
                    agent_id=self.agent_id, status="error",
                    errors=[f"Leaked secrets found: {secret_check}"],
                )

            # Step 3: Try local build (if node_modules exist)
            build_result = await self._try_build(product_dir)

            # Step 4: Generate human review package 
            review = self._generate_review_package(
                product_id=product_id,
                product_dir=product_dir,
                prd=prd,
                quality_report=quality_report,
                security_report=security_report,
                build_result=build_result,
            )

            # Save review package
            review_dir = Path("data/reviews")
            review_dir.mkdir(parents=True, exist_ok=True)
            review_file = review_dir / f"review_{product_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            review_file.write_text(
                json.dumps(review, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8",
            )
            print(f"   Review package: {review_file}")

            return AgentResult(
                agent_id=self.agent_id,
                status="completed",
                output=review,
                metrics={
                    "product_id": product_id,
                    "build_status": build_result.get("status", "skipped"),
                    "secrets_clean": len(secret_check) == 0,
                    "review_file": str(review_file),
                },
            )

        except Exception as e:
            return AgentResult(
                agent_id=self.agent_id, status="error",
                errors=[str(e)],
            )

    def _check_secrets(self, product_dir: Path) -> list[str]:
        """Scan for leaked API keys or secrets in source files"""
        import re
        issues = []
        secret_patterns = [
            (r'sk-[a-zA-Z0-9]{20,}', "OpenAI API key"),
            (r'phc_[a-zA-Z0-9]{20,}', "PostHog API key"),
            (r'ghp_[a-zA-Z0-9]{20,}', "GitHub token"),
            (r'sk_live_[a-zA-Z0-9]{20,}', "Stripe live key"),
            (r'password\s*=\s*["\'][^"\']+["\']', "Hardcoded password"),
        ]

        for filepath in product_dir.rglob("*"):
            if filepath.is_file() and filepath.suffix in (".ts", ".tsx", ".js", ".jsx", ".json", ".env"):
                if "node_modules" in str(filepath) or ".next" in str(filepath):
                    continue
                try:
                    content = filepath.read_text(encoding="utf-8", errors="ignore")
                    for pattern, desc in secret_patterns:
                        if re.search(pattern, content):
                            rel = filepath.relative_to(product_dir)
                            issues.append(f"{desc} in {rel}")
                except Exception:
                    pass
        return issues

    async def _try_build(self, product_dir: Path) -> dict:
        """Attempt npm install + build if possible"""
        npm = shutil.which("npm")
        if not npm:
            return {"status": "skipped", "reason": "npm not found"}

        node_modules = product_dir / "node_modules"
        if not node_modules.exists():
            return {"status": "skipped", "reason": "node_modules not installed (run npm install first)"}

        try:
            result = subprocess.run(
                [npm, "run", "build"],
                cwd=str(product_dir),
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode == 0:
                return {"status": "success", "output": result.stdout[-500:]}
            else:
                return {"status": "failed", "error": result.stderr[-500:]}
        except subprocess.TimeoutExpired:
            return {"status": "timeout"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _generate_review_package(self, product_id: str, product_dir: Path,
                                  prd: dict, quality_report: dict,
                                  security_report: dict, build_result: dict) -> dict:
        """Create the human review package"""
        overview = prd.get("product_overview", {})
        data_plan = prd.get("data_collection_plan", {})

        # List all files
        files = []
        for f in sorted(product_dir.rglob("*")):
            if f.is_file() and "node_modules" not in str(f) and ".next" not in str(f):
                files.append(str(f.relative_to(product_dir)))

        return {
            "product_id": product_id,
            "product_name": overview.get("display_name", product_id),
            "tagline": overview.get("tagline", ""),
            "product_dir": str(product_dir),
            "preview_url": f"https://{product_id.lower()}.vercel.app",
            "prd_summary": {
                "core_problem": overview.get("core_problem", ""),
                "target_user": overview.get("target_user", ""),
                "success_metric": overview.get("success_metric", ""),
                "features_count": len(prd.get("feature_spec", [])),
                "tech_stack": prd.get("tech_architecture", {}).get("framework", "Next.js"),
            },
            "files": files,
            "file_count": len(files),
            "build_result": build_result,
            "quality_report": {
                "verdict": quality_report.get("verdict", "N/A"),
                "score": quality_report.get("score", 0),
                "issues": len(quality_report.get("issues", [])),
            },
            "security_report": {
                "verdict": security_report.get("verdict", "N/A"),
            },
            "analytics_events": [
                e.get("name", "") for e in data_plan.get("analytics_events", [])
                if isinstance(e, dict)
            ],
            "deploy_status": "pending_review",
            "review_actions": ["approve_deploy", "request_changes", "abort"],
            "created_at": datetime.now().isoformat(),
        }
