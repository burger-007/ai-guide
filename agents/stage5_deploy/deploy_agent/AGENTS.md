# Instructions: Deploy Agent

## Mission
Take a quality-checked product and deploy it to Vercel via GitHub.

## Flow
1. Validate build passes locally (`npm run build`)
2. Initialize or update GitHub repo
3. Push code to GitHub
4. Trigger Vercel deployment
5. Verify deployment URL responds
6. Generate human review package

## Pre-Deploy Checklist
```yaml
build_passes: true          # npm run build succeeds
env_vars_documented: true   # .env.local.example exists
security_scan_passed: true  # No critical issues
quality_score: ">= 70"     # Quality checker passed
no_leaked_secrets: true     # No API keys in source
```

## Human Review Package
Generate `data/review_<product_id>.json`:
```json
{
  "product_id": "product-name",
  "product_name": "Display Name",
  "tagline": "One-line description",
  "preview_url": "https://product-name.vercel.app",
  "github_url": "https://github.com/org/product-name",
  "prd_summary": {
    "core_feature": "What it does",
    "user_stories_count": 5,
    "tech_stack": "Next.js + Tailwind + Vercel"
  },
  "quality_report": { "score": 85, "verdict": "PASS" },
  "security_report": { "verdict": "PASS" },
  "analytics_events": ["list of tracked events"],
  "deploy_status": "preview | production",
  "review_actions": ["approve_deploy", "request_changes", "abort"],
  "created_at": "ISO timestamp"
}
```

## After Human Approval
- Promote preview → production
- Verify production URL
- Confirm analytics are receiving data
- Report final status
