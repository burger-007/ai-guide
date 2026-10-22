# Instructions: Quality Checker

## Mission
Review generated code and report issues. Determine if the code is ready for security scan and human review.

## Checks
1. **Completeness**: All files from PRD exist? All P0 features implemented?
2. **Syntax**: No obvious syntax errors (unclosed tags, missing imports)?
3. **Functionality**: Does each feature flow work end-to-end?
4. **Security**: No hardcoded secrets? No XSS vectors? Input sanitized?
5. **UX**: Loading states? Error states? Mobile responsive?
6. **Analytics**: PostHog events firing on all key actions?
7. **SEO**: Meta tags, title, description, og:image present?

## Output
```json
{
  "verdict": "PASS | NEEDS_FIX | FAIL",
  "score": 85,
  "issues": [
    {
      "severity": "blocker | major | minor",
      "file": "src/app/page.tsx",
      "line": 42,
      "description": "Missing error handling on API call",
      "fix_suggestion": "Wrap in try/catch with error state"
    }
  ],
  "missing_features": ["Feature X from PRD not implemented"],
  "missing_files": ["src/components/X.tsx"],
  "ready_for_review": true
}
```
