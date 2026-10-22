# Available Tools: Security Guardian

## Static Analysis Tools
- **Regex Scanner**: Built-in pattern matching for secrets, vulnerabilities, PII
- **LLM Deep Review**: Use LLM for logic-level security analysis (auth bypass, IDOR, etc.)

## External Tools (when configured)
- `npm audit`: Node.js dependency vulnerability check
- `pip audit`: Python dependency vulnerability check  
- `semgrep`: Advanced static analysis (optional, if installed)
- `trufflehog`: Deep secret scanning across git history (optional)

## Output Tools
- **Security Report Generator**: Structured JSON report with findings
- **Privacy Policy Generator**: Auto-generate privacy policy from data collection points
- **Remediation Suggester**: Provide fix suggestions (some auto-fixable)

## Integration Points
- **Stage 3 (Build)**: Called after code generation, before human review
- **Stage 4 (Deploy)**: Called before deployment, verdict shown in review
- **Stage 5 (Monitor)**: Periodic dependency audit on deployed products
