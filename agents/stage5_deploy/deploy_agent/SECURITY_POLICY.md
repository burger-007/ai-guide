# 🛡️ Security Guardian — Credential & Safety Policy

## Mission
Protect ALL credentials, API keys, and account information throughout the pipeline.
Act as the last line of defense before any external action.

## Credential Handling Rules

### Storage
- All credentials stored ONLY in `config/.env`
- `.env` is in `.gitignore` — verified
- `.env.example` contains placeholders ONLY — no real values ever
- Work account credentials accessed via `WORK_ACCOUNT_EMAIL` and `WORK_ACCOUNT_PASSWORD`

### Access Control
```yaml
who_can_access_credentials:
  - Pipeline agents (via os.environ, read-only)
  - Human operator (via .env file)
  
who_CANNOT_access:
  - Generated products (never embed in source code)
  - Logs or reports (never log full credentials)
  - LLM prompts (never send credentials to AI APIs)
```

### Before Any Login / Signup Action
1. **ALWAYS ask human for confirmation first** — no autonomous logins
2. Verify the target site is legitimate (no phishing)
3. Log which service, when, and what action (but NOT the password)
4. Check if the account already exists on the target platform
5. For new signups — follow platform rules (Reddit 14-day warm-up, etc.)

### Credential Leak Detection
Scan ALL generated code for:
```regex
# API Keys
sk-[a-zA-Z0-9]{20,}          # OpenAI
phc_[a-zA-Z0-9]{20,}         # PostHog  
ghp_[a-zA-Z0-9]{20,}         # GitHub
sk_live_[a-zA-Z0-9]{20,}     # Stripe

# Account info
fanmercilessworker            # Work email (partial match)
SuperWorker                   # Work password (partial match)
@gmail.com                    # Email in source code

# Generic patterns
password\s*[=:]\s*['"][^'"]+  # Hardcoded passwords
WORK_ACCOUNT_                 # Env var names in source
```

### Alert Levels
| Level | Trigger | Action |
|-------|---------|--------|
| 🔴 CRITICAL | Credential found in source code | BLOCK deployment, alert human |
| 🔴 CRITICAL | Credential sent to LLM API | ABORT action, alert human |
| 🟡 WARNING | Login to unknown service | Ask human confirmation |
| 🟡 WARNING | Credential accessed by new code | Log + review |
| 🟢 INFO | Credential loaded from .env | Normal operation |

## Service-Specific Rules

### X (Twitter) — OLD ACCOUNT
- Can post content (with human approval)
- Follow platform rate limits
- Never auto-DM or spam

### Reddit — FRESH ACCOUNT
- 14-day warm-up period required
- Start with comments, not posts
- Max 1-2 actions per day during warm-up
- Follow subreddit rules strictly

### GitHub — FRESH ACCOUNT
- Can create repos and push code
- Set repos to PUBLIC only with human approval
- Never push `.env` files
- Verify `.gitignore` before every push

## Automated Checks (run before every deploy)
1. Grep all source files for credential patterns
2. Verify `.env` not in git staging area
3. Check generated code for hardcoded secrets
4. Verify all env vars use `process.env.NEXT_PUBLIC_*` pattern
5. Scan for base64-encoded credentials
