# Instructions: PRD Generator

## Mission
Transform market opportunities into complete, actionable PRDs that a code-generation agent can immediately build from.

## Input
An opportunity object from Stage 1 containing:
- title, tagline, pain_point
- evidence (signals from multiple sources)
- existing_alternatives, our_advantage
- mvp_features, tech_stack, build_days
- data_collection details
- scores and priority_score

## PRD Structure

### 1. Product Overview
```yaml
product_name: "kebab-case-name"
display_name: "Human Readable Name"
tagline: "One-line value proposition"
target_user: "Who is the primary user persona"
core_problem: "The specific problem being solved"
success_metric: "How we measure if this product works"
```

### 2. User Stories (exactly 3-5)
```
As a [user type], I want to [action], so that [benefit].
```
- Prioritize: P0 (must-have for launch), P1 (add in week 2), P2 (future)
- Every P0 story must be completable in one user session

### 3. Feature Specification
For each P0 feature:
```yaml
feature_name: "Short name"
description: "What it does"
user_flow:
  1. "Step 1"
  2. "Step 2"
  3. "Step 3"
input: "What the user provides"
output: "What the user gets back"
data_events:
  - event_name: "feature_used"
    properties: ["input_type", "output_format", "duration_ms"]
```

### 4. User Psychology & Trust Design ⭐ (CRITICAL)
**Think deeply about what the USER needs to see, feel, and believe.**

```yaml
trust_signals:
  # What makes users believe this tool is legitimate?
  - type: "data_source_attribution"
    detail: "Show where the data comes from (e.g., 'Source: World Bank 2024')"
    placement: "Near results AND in footer"
  - type: "methodology_transparency"
    detail: "Brief explanation of HOW the calculation works"
    placement: "Expandable section below results"
  - type: "social_proof"
    detail: "Show usage count, or 'used by X people today'"
    placement: "Near CTA button"

shareability_design:
  # WHY would a user share this? What emotion drives sharing?
  emotional_hook: "What specific feeling does the result trigger?"
  share_format: "What does the shared content look like?"
  share_text_template: "Pre-written text that makes sharing frictionless"
  visual_share: "Can the result be shared as an image/card?"
  platforms: ["Twitter/X", "WhatsApp", "Copy Link"]
  
first_impression:
  # User decides to stay or leave in 3 seconds. What do they see?
  above_fold: "What is visible without scrolling?"
  value_proposition_clarity: "Can a user understand what this does in 1 sentence?"
  time_to_first_result: "How fast can a user get their first result? (target: <10 seconds)"
  
emotional_design:
  # What emotions does each screen trigger?
  landing: "Curiosity ('Where do I stand?')"
  input: "Ease ('Just pick a country and type a number')"
  result: "Surprise/validation ('Wow, I'm in the top X%!')"
  share: "Pride/humor ('Look where I rank!')"

credibility_elements:
  # What makes this look professional, not sketchy?
  - "Clean, minimal design (not cluttered)"
  - "Real data with citations, not random numbers"
  - "No ads, no popups, no signup walls"
  - "HTTPS, privacy-first messaging"
  - "Data never leaves the browser (stated clearly)"

readability_rules:
  # CRITICAL: Every label, axis, dropdown must be human-readable
  - "Country names must be FULL NAMES with flag emojis, never abbreviations"
  - "Numbers must be formatted with commas (50,000 not 50000)"
  - "Currency amounts must have $ prefix"
  - "Percentages must have % suffix"
  - "Chart axes must have clear labels"
  - "All text in plain English, no jargon"
```

### 5. Tech Architecture
```yaml
framework: "Next.js 14 (App Router)"
styling: "Tailwind CSS"
deployment: "Vercel"
analytics: "PostHog"
database: "None (client-side) | Supabase (if needed)"
key_libraries:
  - name: "library-name"
    purpose: "Why we need it"
api_routes:
  - path: "/api/endpoint"
    method: "POST"
    purpose: "What it does"
```

### 6. Data Collection Plan
```yaml
analytics_events:
  - name: "page_view"
    trigger: "User lands on page"
    properties: ["referrer", "utm_source"]
  - name: "tool_used" 
    trigger: "User completes main action"
    properties: ["input_type", "output_format", "processing_time"]
  - name: "tool_shared"
    trigger: "User clicks share button"
    properties: ["share_platform"]

privacy_notes:
  - "No PII collected"
  - "All processing client-side when possible"
  - "Privacy policy page auto-generated"
```

### 7. UI/UX Specification
```yaml
pages:
  - path: "/"
    layout: "Hero + main tool interface"
    components: ["Header", "ToolForm", "ResultPreview", "Footer"]
  - path: "/privacy"
    layout: "Static text"

design_tokens:
  primary_color: "#hex"
  background: "#hex"
  font: "Inter"
  style: "Modern, clean, dark/light toggle"

responsive: true
accessibility: "WCAG 2.1 AA"

# UX Psychology Requirements
ux_psychology:
  - "Above-the-fold must contain: headline + 1 input + 1 button"
  - "Result must appear WITHOUT page reload (client-side)"
  - "Result must trigger an emotional response (big number, color-coded)"
  - "Share button must appear IMMEDIATELY after result"
  - "Data source must be visible to build trust"
  - "All labels must be human-readable (full country names, formatted numbers)"
  - "Empty states must guide the user ('Enter your income to see where you stand')"
  - "Error messages must be helpful, not technical"
```

### 7. Launch Checklist
- [ ] Core feature works
- [ ] PostHog tracking installed
- [ ] Privacy policy page
- [ ] Meta tags (title, description, og:image)
- [ ] Mobile responsive
- [ ] Error handling
- [ ] Loading states
- [ ] Share button

## Output Format
Return the complete PRD as a JSON object with all 7 sections.

## Constraints
- PRD must be specific enough that a code-gen agent can build it WITHOUT asking questions
- Every page must have analytics events defined
- Zero external auth required for MVP (no login)
- Client-side processing preferred (reduces server costs)
- Maximum 3 pages for MVP
- ALL text in English
