"""
🛡️ Security Guardian Agent
Cross-cutting security gatekeeper for the entire pipeline.

Responsibilities:
- Code security review (Stage 3)
- Pre-deployment security scan (Stage 4)
- Runtime security monitoring (Stage 5)
- Secret leak detection (Always-on)
- Data privacy compliance enforcement
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from agents.base_agent import BaseAgent, AgentResult


# ============================================================
# Secret Detection Patterns
# ============================================================

SECRET_PATTERNS = {
    "aws_access_key": r"AKIA[0-9A-Z]{16}",
    "aws_secret_key": r"(?i)aws_secret_access_key\s*[=:]\s*['\"]?[A-Za-z0-9/+=]{40}",
    "github_token": r"gh[ps]_[A-Za-z0-9_]{36,}",
    "openai_api_key": r"sk-[A-Za-z0-9]{48,}",
    "anthropic_api_key": r"sk-ant-[A-Za-z0-9-_]{80,}",
    "generic_api_key": r"(?i)(api[_-]?key|apikey|api[_-]?secret)\s*[=:]\s*['\"][A-Za-z0-9]{16,}['\"]",
    "generic_secret": r"(?i)(secret|password|passwd|pwd|token)\s*[=:]\s*['\"][^'\"]{8,}['\"]",
    "private_key": r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----",
    "connection_string": r"(?i)(mongodb|postgres|mysql|redis):\/\/[^\s]+",
    "jwt_token": r"eyJ[A-Za-z0-9-_]+\.eyJ[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+",
    "supabase_key": r"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9\.[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+",
}

# ============================================================
# Vulnerability Patterns
# ============================================================

VULN_PATTERNS = {
    "eval_usage": {
        "pattern": r"\beval\s*\(",
        "severity": "CRITICAL",
        "category": "code_injection",
        "description": "eval() can execute arbitrary code",
        "remediation": "Replace eval() with JSON.parse() or a safe parser",
    },
    "innerhtml_xss": {
        "pattern": r"\.innerHTML\s*=",
        "severity": "HIGH",
        "category": "xss",
        "description": "innerHTML can lead to XSS attacks",
        "remediation": "Use textContent or a sanitization library like DOMPurify",
    },
    "dangerously_set_html": {
        "pattern": r"dangerouslySetInnerHTML",
        "severity": "HIGH",
        "category": "xss",
        "description": "dangerouslySetInnerHTML bypasses React XSS protection",
        "remediation": "Use DOMPurify to sanitize HTML before rendering",
    },
    "cors_wildcard": {
        "pattern": r"""(?i)(?:access-control-allow-origin|cors).*['"]\*['"]""",
        "severity": "HIGH",
        "category": "cors",
        "description": "Wildcard CORS allows any origin to access your API",
        "remediation": "Restrict to specific trusted domains",
    },
    "console_log": {
        "pattern": r"console\.(log|debug|warn|error)\(",
        "severity": "LOW",
        "category": "info_leak",
        "description": "Console statements may leak sensitive info in production",
        "remediation": "Remove or use a proper logging library",
    },
    "sql_concat": {
        "pattern": r"""(?i)(?:query|execute|sql)\s*\(\s*[`'"].*\$\{""",
        "severity": "CRITICAL",
        "category": "sqli",
        "description": "String interpolation in SQL query — SQL injection risk",
        "remediation": "Use parameterized queries or an ORM",
    },
    "hardcoded_localhost": {
        "pattern": r"(?:http://localhost|http://127\.0\.0\.1|http://0\.0\.0\.0)",
        "severity": "MEDIUM",
        "category": "config",
        "description": "Hardcoded localhost URL — will fail in production",
        "remediation": "Use environment variable for API base URL",
    },
    "no_rate_limit": {
        "pattern": r"(?i)export\s+(?:async\s+)?function\s+(?:GET|POST|PUT|DELETE|PATCH)\s*\(",
        "severity": "MEDIUM",
        "category": "rate_limit",
        "description": "API route handler without visible rate limiting",
        "remediation": "Add rate limiting middleware (e.g., upstash/ratelimit)",
    },
}

# ============================================================
# PII Detection in Analytics
# ============================================================

PII_PATTERNS = {
    "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
    "phone": r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
    "ip_address": r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
    "credit_card": r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",
    "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
}


class SecurityGuardianAgent(BaseAgent):
    """
    Cross-cutting security agent that reviews all generated code.
    Must pass before any deployment.
    """

    def __init__(self, workspace_dir: str = "agents/security_guardian",
                 llm_client=None):
        super().__init__(
            agent_id="security_guardian",
            workspace_dir=workspace_dir,
            llm_client=llm_client,
        )

    async def execute(self, input_data: Any = None) -> AgentResult:
        """
        Runs a full security scan on the provided code directory.
        input_data should contain: {"product_dir": "path/to/product"}
        """
        if not input_data or "product_dir" not in input_data:
            return AgentResult(
                agent_id=self.agent_id,
                status="error",
                errors=["Missing product_dir in input"],
            )

        product_dir = Path(input_data["product_dir"])
        if not product_dir.exists():
            return AgentResult(
                agent_id=self.agent_id,
                status="error",
                errors=[f"Product directory not found: {product_dir}"],
            )

        findings = []

        # 1. Secret Scan
        secret_findings = self._scan_secrets(product_dir)
        findings.extend(secret_findings)

        # 2. Vulnerability Scan
        vuln_findings = self._scan_vulnerabilities(product_dir)
        findings.extend(vuln_findings)

        # 3. Privacy Compliance Check
        privacy_result = self._check_privacy_compliance(product_dir)

        # 4. PII in Analytics Check
        pii_findings = self._check_pii_in_analytics(product_dir)
        findings.extend(pii_findings)

        # 5. LLM Deep Review (if available and findings are ambiguous)
        if self.llm_client and findings:
            llm_review = await self._llm_deep_review(product_dir, findings)
            if llm_review:
                findings.extend(llm_review)

        # Determine verdict
        verdict = self._determine_verdict(findings)

        # Build report
        report = {
            "product_id": input_data.get("product_id", "unknown"),
            "scan_type": input_data.get("scan_type", "pre_deployment"),
            "timestamp": datetime.now().isoformat(),
            "verdict": verdict,
            "total_findings": len(findings),
            "findings": findings,
            "privacy_compliance": privacy_result,
            "summary": self._build_summary(findings, verdict),
        }

        # Save report
        self.save_to_memory(
            key=f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            value=report,
            memory_type="working",
        )

        return AgentResult(
            agent_id=self.agent_id,
            status="completed",
            output=report,
            metrics={
                "files_scanned": self._count_files(product_dir),
                "findings_critical": len([f for f in findings if f["severity"] == "CRITICAL"]),
                "findings_high": len([f for f in findings if f["severity"] == "HIGH"]),
                "findings_medium": len([f for f in findings if f["severity"] == "MEDIUM"]),
                "findings_low": len([f for f in findings if f["severity"] == "LOW"]),
                "verdict": verdict,
            },
        )

    # ========================================================
    # Scan Engines
    # ========================================================

    def _scan_secrets(self, product_dir: Path) -> list[dict]:
        """Scan all files for hardcoded secrets"""
        findings = []
        for filepath in self._iter_code_files(product_dir):
            content = filepath.read_text(encoding="utf-8", errors="ignore")
            for secret_name, pattern in SECRET_PATTERNS.items():
                for match in re.finditer(pattern, content):
                    # Skip if inside .env.example or comments
                    line_num = content[:match.start()].count("\n") + 1
                    line_content = content.split("\n")[line_num - 1].strip()

                    if self._is_example_or_comment(filepath, line_content):
                        continue

                    findings.append({
                        "severity": "CRITICAL",
                        "category": "hardcoded_secret",
                        "subcategory": secret_name,
                        "file": str(filepath.relative_to(product_dir)),
                        "line": line_num,
                        "description": f"Potential {secret_name} found in source code",
                        "remediation": "Move to .env file and use environment variable",
                        "auto_fixable": True,
                    })
        return findings

    def _scan_vulnerabilities(self, product_dir: Path) -> list[dict]:
        """Scan for common vulnerability patterns"""
        findings = []
        for filepath in self._iter_code_files(product_dir):
            content = filepath.read_text(encoding="utf-8", errors="ignore")
            for vuln_name, vuln_config in VULN_PATTERNS.items():
                for match in re.finditer(vuln_config["pattern"], content):
                    line_num = content[:match.start()].count("\n") + 1
                    findings.append({
                        "severity": vuln_config["severity"],
                        "category": vuln_config["category"],
                        "file": str(filepath.relative_to(product_dir)),
                        "line": line_num,
                        "description": vuln_config["description"],
                        "remediation": vuln_config["remediation"],
                        "auto_fixable": False,
                    })
        return findings

    def _check_privacy_compliance(self, product_dir: Path) -> dict:
        """Check if product has required privacy elements"""
        has_privacy_policy = False
        has_cookie_consent = False
        has_data_disclosure = False

        for filepath in self._iter_code_files(product_dir):
            content = filepath.read_text(encoding="utf-8", errors="ignore").lower()
            fname = filepath.name.lower()

            if "privacy" in fname or "/privacy" in content:
                has_privacy_policy = True
            if "cookie" in content and "consent" in content:
                has_cookie_consent = True
            if "we collect" in content or "data collection" in content:
                has_data_disclosure = True

        return {
            "has_privacy_policy": has_privacy_policy,
            "has_cookie_consent": has_cookie_consent,
            "data_collection_disclosed": has_data_disclosure,
            "compliant": has_privacy_policy,  # Minimum requirement
        }

    def _check_pii_in_analytics(self, product_dir: Path) -> list[dict]:
        """Check that analytics events don't contain PII"""
        findings = []
        for filepath in self._iter_code_files(product_dir):
            content = filepath.read_text(encoding="utf-8", errors="ignore")
            # Only check files that contain analytics calls
            if "posthog" not in content.lower() and "analytics" not in content.lower():
                continue

            for pii_name, pattern in PII_PATTERNS.items():
                for match in re.finditer(pattern, content):
                    line_num = content[:match.start()].count("\n") + 1
                    findings.append({
                        "severity": "HIGH",
                        "category": "privacy",
                        "subcategory": f"pii_{pii_name}",
                        "file": str(filepath.relative_to(product_dir)),
                        "line": line_num,
                        "description": f"Possible {pii_name} found in analytics code",
                        "remediation": f"Remove or hash {pii_name} before sending to analytics",
                        "auto_fixable": False,
                    })
        return findings

    async def _llm_deep_review(self, product_dir: Path, existing_findings: list) -> list[dict]:
        """Use LLM for deeper security analysis on suspicious files"""
        flagged_files = set(f["file"] for f in existing_findings)
        if not flagged_files:
            return []

        # Read flagged file contents (limit to prevent token overuse)
        file_contents = {}
        for rel_path in list(flagged_files)[:5]:  # Max 5 files
            full_path = product_dir / rel_path
            if full_path.exists():
                content = full_path.read_text(encoding="utf-8", errors="ignore")
                if len(content) < 10000:  # Skip very large files
                    file_contents[rel_path] = content

        if not file_contents:
            return []

        system_prompt = self.build_system_prompt()
        user_prompt = f"""
Review these files for security vulnerabilities that regex patterns might miss.
Focus on: logic flaws, auth bypass, insecure data handling, IDOR, CSRF.

Files:
{json.dumps(file_contents, indent=2)}

Existing findings (already detected):
{json.dumps(existing_findings[:10], indent=2)}

Return ONLY NEW findings not already in the existing list, as a JSON array.
Each finding: {{"severity", "category", "file", "line", "description", "remediation"}}
Return [] if no new issues found.
"""
        try:
            response = await self.llm_client.chat(system=system_prompt, user=user_prompt)
            return json.loads(response)
        except (json.JSONDecodeError, Exception):
            return []

    # ========================================================
    # Privacy Policy Generator
    # ========================================================

    def generate_privacy_policy(self, product_name: str, data_points: list[str]) -> str:
        """Auto-generate a basic privacy policy for a product"""
        data_list = "\n".join(f"- {dp}" for dp in data_points)
        return f"""# Privacy Policy — {product_name}

**Last Updated:** {datetime.now().strftime('%Y-%m-%d')}

## What Data We Collect
{data_list}

## How We Use Your Data
- To improve the product experience
- To fix bugs and performance issues
- To understand which features are most useful

## What We Do NOT Collect
- Personal identification information (names, emails)
- Payment or financial information
- Location data beyond country level

## Analytics
We use privacy-respecting analytics to understand product usage.
All data is anonymized and aggregated. No individual tracking.

## Your Rights
- You can opt out of analytics tracking at any time
- You can request deletion of any data associated with your session
- Contact: [Contact information]

## Data Retention
Usage data is retained for 90 days, then automatically deleted.
"""

    # ========================================================
    # Helpers
    # ========================================================

    def _iter_code_files(self, directory: Path):
        """Iterate over relevant code files"""
        code_extensions = {
            ".ts", ".tsx", ".js", ".jsx", ".py", ".json",
            ".yaml", ".yml", ".toml", ".env", ".md",
            ".html", ".css", ".sql"
        }
        skip_dirs = {"node_modules", ".next", "dist", ".git", "__pycache__", ".vercel"}

        for filepath in directory.rglob("*"):
            if filepath.is_file() and filepath.suffix in code_extensions:
                if not any(skip in filepath.parts for skip in skip_dirs):
                    yield filepath

    def _is_example_or_comment(self, filepath: Path, line: str) -> bool:
        """Check if a line is in an example file or is a comment"""
        if ".example" in filepath.name or "example" in filepath.stem:
            return True
        if line.startswith("//") or line.startswith("#") or line.startswith("*"):
            return True
        return False

    def _determine_verdict(self, findings: list[dict]) -> str:
        """Determine the overall security verdict"""
        severities = [f["severity"] for f in findings]
        if "CRITICAL" in severities:
            return "BLOCK"
        if "HIGH" in severities:
            return "BLOCK"
        if "MEDIUM" in severities:
            return "WARN"
        return "PASS"

    def _build_summary(self, findings: list, verdict: str) -> str:
        """Build human-readable summary"""
        if verdict == "PASS":
            return "✅ Security scan passed. No significant issues found."
        elif verdict == "WARN":
            return f"⚠️ {len(findings)} issue(s) found. Review recommended before deployment."
        else:
            critical = len([f for f in findings if f["severity"] == "CRITICAL"])
            high = len([f for f in findings if f["severity"] == "HIGH"])
            return (
                f"🚫 DEPLOYMENT BLOCKED — {critical} critical, {high} high severity issues. "
                f"Fix all CRITICAL and HIGH issues before re-scanning."
            )

    def _count_files(self, directory: Path) -> int:
        return sum(1 for _ in self._iter_code_files(directory))
