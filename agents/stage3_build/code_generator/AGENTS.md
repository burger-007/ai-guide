# Instructions: Code Generator

## Mission
Generate a complete, deployable Next.js 14 web application from a PRD.

## Input
A PRD containing: product_overview, user_stories, feature_spec, tech_architecture, data_collection_plan, ui_spec, launch_checklist.

## Output
A complete project directory with all files needed to run `npm run dev` and deploy to Vercel.

## Project Structure (Standard)
```
products/<product-name>/
├── package.json
├── next.config.js
├── tsconfig.json
├── tailwind.config.ts
├── postcss.config.js
├── .env.local.example
├── public/
│   └── favicon.ico
├── src/
│   ├── app/
│   │   ├── layout.tsx          # Root layout with PostHog + fonts
│   │   ├── page.tsx            # Main tool page
│   │   ├── privacy/
│   │   │   └── page.tsx        # Privacy policy (auto-generated)
│   │   ├── globals.css         # Tailwind imports + custom tokens
│   │   └── api/                # API routes if needed
│   │       └── ...
│   ├── components/
│   │   ├── Header.tsx
│   │   ├── Footer.tsx
│   │   ├── [ToolComponents].tsx
│   │   └── Analytics.tsx       # PostHog wrapper
│   ├── lib/
│   │   ├── analytics.ts        # PostHog event helpers
│   │   └── utils.ts            # Shared utilities
│   └── types/
│       └── index.ts            # TypeScript types
└── README.md
```

## Code Standards

### 1. Package.json
```json
{
  "name": "<product-name>",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start"
  },
  "dependencies": {
    "next": "14.2.0",
    "react": "^18",
    "react-dom": "^18",
    "posthog-js": "^1.100.0"
  },
  "devDependencies": {
    "typescript": "^5",
    "@types/node": "^20",
    "@types/react": "^18",
    "tailwindcss": "^3.4",
    "postcss": "^8",
    "autoprefixer": "^10"
  }
}
```

### 2. Layout (Required Elements)
Every app MUST include:
- Inter font from Google Fonts
- PostHog analytics initialization
- Dark/light color scheme
- Meta tags (title, description, og:image)
- Responsive viewport

### 3. Component Pattern
```tsx
'use client'; // Only if interactive

import { useState } from 'react';
import { trackEvent } from '@/lib/analytics';

interface Props {
  // Typed props
}

export function ComponentName({ }: Props) {
  // State
  // Handlers (with analytics tracking)
  // Render with loading/error/success states
}
```

### 4. Analytics Integration
```typescript
// src/lib/analytics.ts
import posthog from 'posthog-js';

export function initAnalytics() {
  if (typeof window !== 'undefined' && process.env.NEXT_PUBLIC_POSTHOG_KEY) {
    posthog.init(process.env.NEXT_PUBLIC_POSTHOG_KEY, {
      api_host: process.env.NEXT_PUBLIC_POSTHOG_HOST || 'https://app.posthog.com',
      capture_pageview: true,
      capture_pageleave: true,
    });
  }
}

export function trackEvent(name: string, properties?: Record<string, any>) {
  posthog.capture(name, properties);
}
```

### 5. Privacy Policy Page
Auto-generate based on data_collection_plan. MUST include:
- What data is collected
- How it's used
- Third-party services (PostHog)
- Contact information placeholder
- Last updated date

### 6. Design Requirements
- Modern, premium feel (not generic Bootstrap look)
- Smooth animations (transform, opacity transitions)
- Hover effects on interactive elements
- Proper spacing (consistent padding/margin scale)
- Mobile-first responsive
- Dark mode support (prefers-color-scheme)

## File Generation Rules
1. Generate ALL files needed to run. No placeholders.
2. Every component must be functional — not stubbed.
3. Include proper error boundaries.
4. Include loading states for async operations.
5. All text in English.
6. No hardcoded API keys — use environment variables.
7. Generate a README.md with setup instructions.

## Constraints
- Maximum 15 files for MVP
- No external database for MVP (use localStorage or client-side state)
- No authentication for MVP
- Must work with `npx create-next-app` defaults
- Must deploy to Vercel with zero config
