"""
🔍 Stage 4 Agent: QA Agent (品管)
Full quality assurance — builds, scans, verifies every PRD requirement.
"""

import json
import os
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from agents.base_agent import BaseAgent, AgentResult
from shared.llm_client import LLMClient


# Patterns that indicate placeholder / unfinished code
PLACEHOLDER_PATTERNS = [
    r'\bTODO\b', r'\bFIXME\b', r'\bHACK\b',
    r'placeholder', r'lorem ipsum',
    r'YOUR_.*_KEY', r'YOUR_.*_TOKEN',
    r'sk-[a-zA-Z0-9]{20,}',       # OpenAI key
    r'phc_[a-zA-Z0-9]{20,}',      # PostHog key
    r'ghp_[a-zA-Z0-9]{20,}',      # GitHub token
]

# Security anti-patterns
SECURITY_PATTERNS = [
    (r'dangerouslySetInnerHTML', "XSS risk: dangerouslySetInnerHTML"),
    (r'\beval\s*\(', "Security: eval() usage"),
    (r'new\s+Function\s*\(', "Security: new Function() usage"),
    (r'document\.write\s*\(', "Security: document.write()"),
]

# Required SEO elements (regex to match in layout/page files)
SEO_CHECKS = {
    "title_tag": r'title\s*[:=]',
    "meta_description": r'description\s*[:=]',
    "viewport": r'viewport',
    "og_title": r'og:title|openGraph',
}

# Weights for each QA area
AREA_WEIGHTS = {
    "build": 0.25,
    "files": 0.05,
    "prd_compliance": 0.20,
    "security": 0.15,
    "analytics": 0.10,
    "seo": 0.10,
    "ux": 0.10,
    "code_quality": 0.05,
}


class QAAgent(BaseAgent):
    """
    Comprehensive QA: build → scan → verify → score → verdict.
    """

    def __init__(self, workspace_dir: str = "agents/stage4_qa/qa_agent",
                 llm_client: LLMClient = None):
        super().__init__(
            agent_id="qa_agent",
            workspace_dir=workspace_dir,
            llm_client=llm_client,
        )

    async def execute(self, input_data: Any = None) -> AgentResult:
        if not input_data:
            return AgentResult(agent_id=self.agent_id, status="error",
                               errors=["No input data"])

        try:
            product_dir = Path(input_data.get("product_dir", ""))
            product_id = input_data.get("product_id", "unknown")
            prd = input_data.get("prd", {})

            if not product_dir.exists():
                return AgentResult(agent_id=self.agent_id, status="error",
                                   errors=[f"Product dir not found: {product_dir}"])

            # Read all source files
            source_files = self._read_source_files(product_dir)

            print(f"   QA scanning {len(source_files)} files in {product_dir}")

            # Run all 8 checks
            areas = {}
            areas["build"] = await self._check_build(product_dir)
            areas["files"] = self._check_files(product_dir, source_files, prd)
            areas["security"] = self._check_security(source_files)
            areas["analytics"] = self._check_analytics(source_files, prd)
            areas["seo"] = self._check_seo(source_files)
            areas["ux"] = self._check_ux(source_files)
            areas["code_quality"] = self._check_code_quality(source_files)

            # PRD compliance needs LLM
            areas["prd_compliance"] = await self._check_prd_compliance(source_files, prd)

            # Calculate overall score
            overall_score = sum(
                areas[area]["score"] * AREA_WEIGHTS.get(area, 0)
                for area in areas
            )
            overall_score = round(overall_score, 1)

            # Determine verdict
            if areas["build"]["score"] == 0:
                verdict = "REBUILD"
            elif overall_score >= 75:
                verdict = "SHIP_IT"
            elif overall_score >= 50:
                verdict = "FIX_REQUIRED"
            else:
                verdict = "REBUILD"

            # Collect all issues
            blockers = []
            warnings = []
            suggestions = []
            fix_instructions = []

            for area_name, area_data in areas.items():
                for issue in area_data.get("issues", []):
                    sev = issue.get("severity", "warning")
                    if sev == "blocker":
                        blockers.append(issue.get("description", ""))
                    elif sev == "warning":
                        warnings.append(issue.get("description", ""))
                    else:
                        suggestions.append(issue.get("description", ""))

                    if issue.get("fix"):
                        fix_instructions.append(issue)

            report = {
                "verdict": verdict,
                "overall_score": overall_score,
                "areas": areas,
                "blockers": blockers,
                "warnings": warnings,
                "suggestions": suggestions,
                "fix_instructions": fix_instructions[:10],  # Limit
                "checked_at": datetime.now().isoformat(),
            }

            # Save report
            qa_dir = Path("data/qa_reports")
            qa_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = qa_dir / f"qa_{product_id}_{ts}.json"
            report_file.write_text(
                json.dumps(report, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8",
            )

            # Also save in product dir
            (product_dir / "qa_report.json").write_text(
                json.dumps(report, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8",
            )

            return AgentResult(
                agent_id=self.agent_id,
                status="completed",
                output=report,
                metrics={
                    "verdict": verdict,
                    "overall_score": overall_score,
                    "blockers": len(blockers),
                    "warnings": len(warnings),
                    "files_scanned": len(source_files),
                },
            )

        except Exception as e:
            import traceback
            traceback.print_exc()
            return AgentResult(agent_id=self.agent_id, status="error",
                               errors=[str(e)])

    # ===================== Helpers =====================

    def _read_source_files(self, product_dir: Path) -> dict[str, str]:
        """Read all source files (skip node_modules, .next, etc.)"""
        files = {}
        skip_dirs = {"node_modules", ".next", ".git", "__pycache__"}
        for filepath in product_dir.rglob("*"):
            if filepath.is_file():
                # Skip big directories
                if any(sd in filepath.parts for sd in skip_dirs):
                    continue
                # Skip binary files
                if filepath.suffix in (".png", ".jpg", ".ico", ".woff", ".woff2"):
                    continue
                try:
                    rel = str(filepath.relative_to(product_dir)).replace("\\", "/")
                    content = filepath.read_text(encoding="utf-8", errors="replace")
                    files[rel] = content
                except Exception:
                    pass
        return files

    # ===================== Check 1: Build =====================

    async def _check_build(self, product_dir: Path) -> dict:
        """Try npm install + build"""
        npm = shutil.which("npm")
        pkg = product_dir / "package.json"

        if not pkg.exists():
            return {"score": 0, "verdict": "FAIL",
                    "details": "No package.json found", "issues": [
                        {"severity": "blocker", "description": "Missing package.json"}
                    ]}

        if not npm:
            return {"score": 50, "verdict": "PARTIAL",
                    "details": "npm not found, cannot verify build", "issues": [
                        {"severity": "warning", "description": "npm not in PATH, build not verified"}
                    ]}

        issues = []
        node_modules = product_dir / "node_modules"

        # Windows encoding fix
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        sub_kwargs = {
            "cwd": str(product_dir),
            "capture_output": True,
            "timeout": 120,
            "env": env,
            "encoding": "utf-8",
            "errors": "replace",
        }

        # Try install if not already done
        if not node_modules.exists():
            try:
                print("   Running npm install...")
                result = subprocess.run(
                    [npm, "install", "--legacy-peer-deps"], **sub_kwargs,
                )
                if result.returncode != 0:
                    err = (result.stderr or "")[-200:]
                    issues.append({
                        "severity": "blocker",
                        "description": f"npm install failed: {err}",
                    })
                    return {"score": 0, "verdict": "FAIL",
                            "details": "npm install failed", "issues": issues}
            except subprocess.TimeoutExpired:
                issues.append({"severity": "warning",
                               "description": "npm install timed out (120s)"})
                return {"score": 30, "verdict": "FAIL",
                        "details": "install timeout", "issues": issues}
            except Exception as e:
                issues.append({"severity": "warning",
                               "description": f"npm install error: {e}"})
                return {"score": 30, "verdict": "PARTIAL",
                        "details": str(e), "issues": issues}

        # Try build
        try:
            print("   Running npm run build...")
            result = subprocess.run(
                [npm, "run", "build"], **sub_kwargs,
            )
            if result.returncode == 0:
                return {"score": 100, "verdict": "PASS",
                        "details": "Build succeeded", "issues": []}
            else:
                error_msg = ((result.stderr or "") + (result.stdout or ""))[-300:]
                issues.append({
                    "severity": "blocker",
                    "description": f"Build failed: {error_msg}",
                })
                return {"score": 0, "verdict": "FAIL",
                        "details": "npm run build failed", "issues": issues}

        except subprocess.TimeoutExpired:
            issues.append({"severity": "warning",
                           "description": "Build timed out (120s)"})
            return {"score": 30, "verdict": "PARTIAL",
                    "details": "build timeout", "issues": issues}
        except Exception as e:
            issues.append({"severity": "warning",
                           "description": f"Build error: {e}"})
            return {"score": 30, "verdict": "PARTIAL",
                    "details": str(e), "issues": issues}

    # ===================== Check 2: Files =====================

    def _check_files(self, product_dir: Path, files: dict, prd: dict) -> dict:
        """Check file completeness"""
        issues = []
        score = 100

        # Required files
        required = [
            "package.json", "tsconfig.json", "next.config.js",
            "src/app/layout.tsx", "src/app/page.tsx",
        ]
        for req in required:
            if req not in files:
                issues.append({
                    "severity": "blocker",
                    "description": f"Missing required file: {req}",
                })
                score -= 15

        # Empty files
        for path, content in files.items():
            if len(content.strip()) == 0:
                issues.append({
                    "severity": "warning",
                    "description": f"Empty file: {path}",
                })
                score -= 5

        # Placeholder content
        for path, content in files.items():
            for pattern in PLACEHOLDER_PATTERNS:
                if re.search(pattern, content, re.IGNORECASE):
                    issues.append({
                        "severity": "warning",
                        "description": f"Placeholder/unfinished content in {path}: {pattern}",
                        "file": path,
                    })
                    score -= 3
                    break  # One per file

        verdict = "PASS" if score >= 80 else ("PARTIAL" if score >= 40 else "FAIL")
        return {"score": max(0, score), "verdict": verdict,
                "details": f"{len(files)} files checked", "issues": issues}

    # ===================== Check 3: Security =====================

    def _check_security(self, files: dict) -> dict:
        """Scan for security anti-patterns and leaked secrets"""
        issues = []
        score = 100

        for path, content in files.items():
            # Skip config examples
            if "example" in path.lower() or path.endswith(".md"):
                continue

            # Security anti-patterns
            for pattern, desc in SECURITY_PATTERNS:
                matches = re.findall(pattern, content)
                if matches:
                    issues.append({
                        "severity": "blocker",
                        "description": f"{desc} in {path}",
                        "file": path,
                    })
                    score -= 25

            # Leaked secrets — API keys
            secret_patterns = [
                (r'sk-[a-zA-Z0-9]{20,}', "OpenAI API key"),
                (r'phc_[a-zA-Z0-9]{20,}', "PostHog API key"),
                (r'ghp_[a-zA-Z0-9]{20,}', "GitHub token"),
                (r'sk_live_[a-zA-Z0-9]{20,}', "Stripe live key"),
            ]
            for pat, desc in secret_patterns:
                if re.search(pat, content):
                    issues.append({
                        "severity": "blocker",
                        "description": f"🔴 LEAKED {desc} in {path}",
                        "file": path,
                    })
                    score -= 30

            # Leaked credentials — work account
            credential_patterns = [
                (r'fanmercilessworker', "Work account email"),
                (r'SuperWorker', "Work account password"),
                (r'WORK_ACCOUNT_EMAIL\s*[=:]\s*\S+', "Hardcoded work email"),
                (r'WORK_ACCOUNT_PASSWORD\s*[=:]\s*\S+', "Hardcoded work password"),
            ]
            for pat, desc in credential_patterns:
                if re.search(pat, content):
                    issues.append({
                        "severity": "blocker",
                        "description": f"🔴 CRITICAL: {desc} leaked in {path}",
                        "file": path,
                    })
                    score -= 50  # Max severity

        # Check .env.local.example exists
        if ".env.local.example" not in files and ".env.example" not in files:
            issues.append({
                "severity": "warning",
                "description": "No .env.local.example file — env vars undocumented",
            })
            score -= 5

        verdict = "PASS" if score >= 80 else ("PARTIAL" if score >= 40 else "FAIL")
        return {"score": max(0, score), "verdict": verdict,
                "details": f"Scanned {len(files)} files", "issues": issues}

    # ===================== Check 4: Analytics =====================

    def _check_analytics(self, files: dict, prd: dict) -> dict:
        """Verify PostHog analytics integration"""
        issues = []
        score = 0

        all_content = " ".join(files.values())

        # PostHog init
        if "posthog" in all_content.lower():
            score += 30
        else:
            issues.append({"severity": "blocker",
                           "description": "No PostHog integration found"})

        # posthog.init or initAnalytics
        if re.search(r'posthog\.init|initAnalytics|initPostHog', all_content):
            score += 20
        else:
            issues.append({"severity": "warning",
                           "description": "PostHog initialization not found"})

        # Custom events
        event_matches = re.findall(r'trackEvent|posthog\.capture|track[A-Z]\w+', all_content)
        if len(event_matches) >= 3:
            score += 30
        elif len(event_matches) >= 1:
            score += 15
            issues.append({"severity": "warning",
                           "description": f"Only {len(event_matches)} analytics events (expected ≥3)"})
        else:
            issues.append({"severity": "warning",
                           "description": "No custom analytics events found"})

        # Page view tracking
        if "capture_pageview" in all_content or "pageview" in all_content.lower():
            score += 20
        else:
            issues.append({"severity": "info",
                           "description": "No explicit pageview tracking"})
            score += 10  # PostHog auto-captures by default

        verdict = "PASS" if score >= 80 else ("PARTIAL" if score >= 40 else "FAIL")
        return {"score": min(100, score), "verdict": verdict,
                "details": f"{len(event_matches)} event calls found", "issues": issues}

    # ===================== Check 5: SEO =====================

    def _check_seo(self, files: dict) -> dict:
        """Check SEO meta tags"""
        issues = []
        score = 0

        # Find layout and page files
        layout_files = {p: c for p, c in files.items()
                        if "layout" in p.lower() or "page" in p.lower()}
        all_layout = " ".join(layout_files.values())

        for tag, pattern in SEO_CHECKS.items():
            if re.search(pattern, all_layout, re.IGNORECASE):
                score += 25
            else:
                issues.append({
                    "severity": "warning",
                    "description": f"Missing SEO element: {tag}",
                })

        verdict = "PASS" if score >= 80 else ("PARTIAL" if score >= 40 else "FAIL")
        return {"score": min(100, score), "verdict": verdict,
                "details": f"Checked {len(layout_files)} layout/page files", "issues": issues}

    # ===================== Check 6: UX =====================

    def _check_ux(self, files: dict) -> dict:
        """Check UX quality indicators"""
        issues = []
        score = 0

        tsx_files = {p: c for p, c in files.items()
                     if p.endswith(".tsx") or p.endswith(".jsx")}
        all_tsx = " ".join(tsx_files.values())

        # Loading states
        if re.search(r'loading|isLoading|spinner|skeleton|Loading', all_tsx):
            score += 20
        else:
            issues.append({"severity": "warning",
                           "description": "No loading states detected"})

        # Error handling
        if re.search(r'error|isError|Error|catch|try', all_tsx):
            score += 20
        else:
            issues.append({"severity": "warning",
                           "description": "No error handling in components"})

        # Responsive design
        css_files = {p: c for p, c in files.items()
                     if p.endswith(".css") or p.endswith(".tsx")}
        all_css = " ".join(css_files.values())

        if re.search(r'sm:|md:|lg:|@media|responsive|mobile', all_css, re.IGNORECASE):
            score += 20
        else:
            issues.append({"severity": "warning",
                           "description": "No responsive design indicators found"})

        # Hover / transitions
        if re.search(r'hover:|transition|transform|animate', all_css):
            score += 15
        else:
            issues.append({"severity": "info",
                           "description": "No hover effects or animations"})

        # Consistent spacing
        if re.search(r'p-\d|px-\d|py-\d|gap-\d|space-', all_css):
            score += 10
        else:
            issues.append({"severity": "info",
                           "description": "Limited use of spacing utilities"})

        # ===== User Psychology Checks (new) =====

        # Trust: data source citation
        if re.search(r'source|data from|world bank|oecd|citation|methodology', all_tsx, re.IGNORECASE):
            score += 5
        else:
            issues.append({"severity": "warning",
                           "description": "UX Psychology: No data source citation — users won't trust results"})

        # Share functionality
        if re.search(r'share|navigator\.share|twitter|clipboard|copy', all_tsx, re.IGNORECASE):
            score += 5
        else:
            issues.append({"severity": "warning",
                           "description": "UX Psychology: No share functionality — limits virality"})

        # Empty/error state guidance
        if re.search(r'empty|no results|enter|try|get started', all_tsx, re.IGNORECASE):
            score += 5
        else:
            issues.append({"severity": "info",
                           "description": "UX Psychology: No empty state guidance for users"})

        verdict = "PASS" if score >= 80 else ("PARTIAL" if score >= 40 else "FAIL")
        return {"score": min(100, score), "verdict": verdict,
                "details": f"Checked {len(tsx_files)} component files", "issues": issues}

    # ===================== Check 7: Code Quality =====================

    def _check_code_quality(self, files: dict) -> dict:
        """Check code quality indicators"""
        issues = []
        score = 100

        ts_files = {p: c for p, c in files.items()
                    if p.endswith(".ts") or p.endswith(".tsx")}

        for path, content in ts_files.items():
            lines = content.split("\n")

            # File too long
            if len(lines) > 200:
                issues.append({"severity": "info",
                               "description": f"{path}: {len(lines)} lines (>200)",
                               "file": path})
                score -= 3

            # `any` type usage
            any_count = len(re.findall(r':\s*any\b', content))
            if any_count > 0:
                issues.append({"severity": "warning",
                               "description": f"{path}: {any_count}x 'any' type",
                               "file": path})
                score -= 3 * any_count

            # console.log (ok in dev, not in prod)
            log_count = len(re.findall(r'console\.log\(', content))
            if log_count > 2:
                issues.append({"severity": "info",
                               "description": f"{path}: {log_count}x console.log",
                               "file": path})
                score -= 2

        verdict = "PASS" if score >= 80 else ("PARTIAL" if score >= 40 else "FAIL")
        return {"score": max(0, score), "verdict": verdict,
                "details": f"Checked {len(ts_files)} TS/TSX files", "issues": issues}

    # ===================== Check 8: PRD Compliance (LLM) =====================

    async def _check_prd_compliance(self, files: dict, prd: dict) -> dict:
        """Use LLM to verify PRD features are actually implemented"""
        if not self.llm_client:
            return {"score": 50, "verdict": "PARTIAL",
                    "details": "No LLM — cannot verify PRD compliance", "issues": []}

        features = prd.get("feature_spec", [])
        user_stories = prd.get("user_stories", [])
        overview = prd.get("product_overview", {})

        if not features and not user_stories:
            return {"score": 50, "verdict": "PARTIAL",
                    "details": "No features in PRD to check", "issues": []}

        # Get key source files (skip configs)
        key_files = {p: c[:2000] for p, c in files.items()
                     if p.endswith((".tsx", ".ts")) and "node_modules" not in p}

        system_prompt = self.build_system_prompt()
        user_prompt = f"""Verify PRD compliance for "{overview.get('display_name', 'Product')}":

PRD USER STORIES:
{json.dumps(user_stories, indent=2, default=str)}

PRD FEATURES:
{json.dumps(features, indent=2, default=str)}

GENERATED CODE FILES:
{json.dumps(key_files, indent=2, default=str)}

For each P0 feature/story, verify:
1. Is the feature actually IMPLEMENTED (not just UI, but LOGIC)?
2. Is input validation present?
3. Does the output match what PRD describes?

Return JSON:
{{
  "score": 0-100,
  "feature_status": {{
    "feature_name": "IMPLEMENTED | PARTIAL | MISSING"
  }},
  "issues": [
    {{
      "severity": "blocker | warning | info",
      "description": "what's wrong",
      "file": "path if applicable",
      "fix": "suggested fix"
    }}
  ]
}}"""

        try:
            result = await self.llm_client.chat_json(
                system=system_prompt, user=user_prompt, temperature=0.1,
            )
            score = result.get("score", 50)
            issues_raw = result.get("issues", [])
            verdict = "PASS" if score >= 80 else ("PARTIAL" if score >= 40 else "FAIL")
            return {
                "score": score,
                "verdict": verdict,
                "details": json.dumps(result.get("feature_status", {})),
                "issues": issues_raw,
            }
        except Exception as e:
            return {"score": 50, "verdict": "PARTIAL",
                    "details": f"LLM error: {e}", "issues": []}
