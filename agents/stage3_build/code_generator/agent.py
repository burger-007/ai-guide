"""
🔨 Stage 3 Agent: Code Generator
Takes a PRD and generates a complete, deployable Next.js project.
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from agents.base_agent import BaseAgent, AgentResult
from shared.llm_client import LLMClient


class CodeGeneratorAgent(BaseAgent):
    """
    Generates a complete Next.js project from a PRD.
    Output: a directory under products/<product-name>/ with all files.
    """

    def __init__(self, workspace_dir: str = "agents/stage3_build/code_generator",
                 llm_client: LLMClient = None,
                 products_dir: str = "products"):
        super().__init__(
            agent_id="code_generator",
            workspace_dir=workspace_dir,
            llm_client=llm_client,
        )
        self.products_dir = Path(products_dir)

    async def execute(self, input_data: Any = None) -> AgentResult:
        """
        Input: PRD dict (from Stage 2)
        Output: dict with product_dir, product_id, file_count
        """
        if not input_data or not self.llm_client:
            return AgentResult(
                agent_id=self.agent_id, status="error",
                errors=["Missing PRD or LLM client"],
            )

        try:
            prd = input_data
            if isinstance(input_data, dict) and "prd" in input_data:
                prd = input_data["prd"]

            overview = prd.get("product_overview", {})
            product_name = overview.get("product_name", "untitled")
            product_dir = self.products_dir / product_name

            print(f"   Generating code for: {product_name}")

            # Step 1: Generate project scaffold (config files)
            scaffold_files = self._generate_scaffold(prd, product_name)

            # Step 2: LLM generates the actual application code
            app_files = await self._generate_app_code(prd)

            # Step 3: Generate analytics integration
            analytics_files = self._generate_analytics(prd)

            # Step 4: Generate privacy policy
            privacy_file = await self._generate_privacy_page(prd)

            # Step 5: Generate README
            readme = self._generate_readme(prd, product_name)

            # Combine all files
            all_files = {**scaffold_files, **app_files, **analytics_files, **privacy_file, **readme}

            # Write to disk
            file_count = self._write_files(product_dir, all_files)

            print(f"   Written {file_count} files to {product_dir}")

            # Save to memory
            self.save_to_memory(
                key=f"build_{product_name}",
                value={"product_dir": str(product_dir), "files": list(all_files.keys())},
                memory_type="working",
            )

            return AgentResult(
                agent_id=self.agent_id,
                status="completed",
                output={
                    "product_id": product_name,
                    "product_dir": str(product_dir),
                    "file_count": file_count,
                    "files": list(all_files.keys()),
                },
                metrics={"files_generated": file_count, "product_name": product_name},
            )

        except Exception as e:
            import traceback
            traceback.print_exc()
            return AgentResult(
                agent_id=self.agent_id, status="error",
                errors=[str(e)],
            )

    def _generate_scaffold(self, prd: dict, product_name: str) -> dict[str, str]:
        """Generate config files that don't need LLM"""
        tech = prd.get("tech_architecture", {})
        libs = tech.get("key_libraries", [])

        # Build dependencies
        deps = {
            "next": "14.2.0",
            "react": "^18",
            "react-dom": "^18",
            "posthog-js": "^1.100.0",
        }
        for lib in libs:
            name = lib.get("name", lib) if isinstance(lib, dict) else str(lib)
            if name and name not in deps:
                deps[name] = "latest"

        dev_deps = {
            "typescript": "^5",
            "@types/node": "^20",
            "@types/react": "^18",
            "@types/react-dom": "^18",
            "tailwindcss": "^3.4",
            "postcss": "^8",
            "autoprefixer": "^10",
        }

        overview = prd.get("product_overview", {})

        return {
            "package.json": json.dumps({
                "name": product_name,
                "version": "0.1.0",
                "private": True,
                "scripts": {
                    "dev": "next dev",
                    "build": "next build",
                    "start": "next start",
                },
                "dependencies": deps,
                "devDependencies": dev_deps,
            }, indent=2),

            "next.config.js": "/** @type {import('next').NextConfig} */\nconst nextConfig = {}\nmodule.exports = nextConfig\n",

            "tsconfig.json": json.dumps({
                "compilerOptions": {
                    "target": "es5",
                    "lib": ["dom", "dom.iterable", "esnext"],
                    "allowJs": True,
                    "skipLibCheck": True,
                    "strict": True,
                    "noEmit": True,
                    "esModuleInterop": True,
                    "module": "esnext",
                    "moduleResolution": "bundler",
                    "resolveJsonModule": True,
                    "isolatedModules": True,
                    "jsx": "preserve",
                    "incremental": True,
                    "plugins": [{"name": "next"}],
                    "paths": {"@/*": ["./src/*"]},
                },
                "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
                "exclude": ["node_modules"],
            }, indent=2),

            "tailwind.config.ts": (
                "import type { Config } from 'tailwindcss'\n\n"
                "const config: Config = {\n"
                "  content: [\n"
                "    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',\n"
                "    './src/components/**/*.{js,ts,jsx,tsx,mdx}',\n"
                "    './src/app/**/*.{js,ts,jsx,tsx,mdx}',\n"
                "  ],\n"
                "  theme: { extend: {} },\n"
                "  plugins: [],\n"
                "}\n"
                "export default config\n"
            ),

            "postcss.config.js": (
                "module.exports = {\n"
                "  plugins: {\n"
                "    tailwindcss: {},\n"
                "    autoprefixer: {},\n"
                "  },\n"
                "}\n"
            ),

            ".env.local.example": (
                "# PostHog Analytics\n"
                "NEXT_PUBLIC_POSTHOG_KEY=phc_your_key_here\n"
                "NEXT_PUBLIC_POSTHOG_HOST=https://app.posthog.com\n"
            ),
        }

    async def _generate_app_code(self, prd: dict) -> dict[str, str]:
        """Use LLM to generate the main application code"""
        system_prompt = self.build_system_prompt()

        overview = prd.get("product_overview", {})
        features = prd.get("feature_spec", [])
        ui_spec = prd.get("ui_spec", {})
        data_plan = prd.get("data_collection_plan", {})

        user_prompt = f"""Generate the complete Next.js 14 application code for this product:

PRODUCT: {overview.get('display_name', '')}
TAGLINE: {overview.get('tagline', '')}
CORE PROBLEM: {overview.get('core_problem', '')}

FEATURES:
{json.dumps(features, indent=2, default=str)}

UI SPEC:
{json.dumps(ui_spec, indent=2, default=str)}

ANALYTICS EVENTS:
{json.dumps(data_plan.get('analytics_events', []), indent=2, default=str)}

Generate these files:
1. src/app/layout.tsx — Root layout with Inter font, meta tags, PostHog init
2. src/app/page.tsx — Main tool page with full functionality
3. src/app/globals.css — Tailwind imports + custom design tokens + animations
4. src/components/Header.tsx — Clean header with product name and nav
5. src/components/Footer.tsx — Footer with links (privacy, etc.)
6. src/components/[MainTool].tsx — The core tool component(s) for ALL P0 features
7. src/types/index.ts — TypeScript types

RULES:
- Return as a JSON object where keys are file paths and values are complete file contents
- Every file must be complete, working code — no TODOs or placeholders
- Use 'use client' only where needed (components with state/effects)
- Import analytics: import {{ trackEvent }} from '@/lib/analytics'
- Modern design: gradients, shadows, smooth transitions, dark mode support
- Responsive: works on mobile and desktop
- All text in English
- Include proper loading states and error handling"""

        try:
            result = await self.llm_client.chat_json(
                system=system_prompt,
                user=user_prompt,
                temperature=0.3,
            )

            if isinstance(result, dict):
                # Clean up file paths
                cleaned = {}
                for path, content in result.items():
                    # Normalize paths
                    clean_path = path.replace("\\", "/")
                    if not clean_path.startswith("src/"):
                        if clean_path.startswith("/"):
                            clean_path = clean_path[1:]
                    cleaned[clean_path] = content
                return cleaned

        except Exception as e:
            print(f"   [Code generation error: {e}]")

        return {}

    def _generate_analytics(self, prd: dict) -> dict[str, str]:
        """Generate PostHog analytics integration files"""
        events = prd.get("data_collection_plan", {}).get("analytics_events", [])

        event_helpers = ""
        for evt in events:
            if isinstance(evt, dict):
                name = evt.get("name", "event")
                props = evt.get("properties", [])
                props_type = ", ".join(f"{p}?: string | number" for p in props if isinstance(p, str))
                event_helpers += f"""
export function track{name.replace('_', ' ').title().replace(' ', '')}(props?: {{ {props_type} }}) {{
  trackEvent('{name}', props);
}}
"""

        analytics_code = f"""import posthog from 'posthog-js';

let initialized = false;

export function initAnalytics() {{
  if (typeof window !== 'undefined' && !initialized) {{
    const key = process.env.NEXT_PUBLIC_POSTHOG_KEY;
    if (key) {{
      posthog.init(key, {{
        api_host: process.env.NEXT_PUBLIC_POSTHOG_HOST || 'https://app.posthog.com',
        capture_pageview: true,
        capture_pageleave: true,
        autocapture: true,
      }});
      initialized = true;
    }}
  }}
}}

export function trackEvent(name: string, properties?: Record<string, any>) {{
  if (initialized) {{
    posthog.capture(name, {{
      ...properties,
      timestamp: new Date().toISOString(),
    }});
  }}
}}

export function identifyUser(userId: string, traits?: Record<string, any>) {{
  if (initialized) {{
    posthog.identify(userId, traits);
  }}
}}
{event_helpers}"""

        analytics_provider = """'use client';

import { useEffect } from 'react';
import { initAnalytics } from '@/lib/analytics';

export function AnalyticsProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    initAnalytics();
  }, []);
  return <>{children}</>;
}
"""

        return {
            "src/lib/analytics.ts": analytics_code,
            "src/components/Analytics.tsx": analytics_provider,
        }

    async def _generate_privacy_page(self, prd: dict) -> dict[str, str]:
        """Generate privacy policy page"""
        overview = prd.get("product_overview", {})
        data_plan = prd.get("data_collection_plan", {})
        events = data_plan.get("analytics_events", [])
        privacy_notes = data_plan.get("privacy_notes", [])

        event_descriptions = ""
        for evt in events:
            if isinstance(evt, dict):
                event_descriptions += f"- **{evt.get('name', '')}**: {evt.get('trigger', '')}\\n"

        product_name = overview.get("display_name", "This tool")
        today = datetime.now().strftime("%B %d, %Y")

        page_code = f"""export default function PrivacyPage() {{
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-3xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-8">Privacy Policy</h1>
        <div className="prose dark:prose-invert max-w-none space-y-6">
          <p className="text-gray-600 dark:text-gray-300">
            Last updated: {today}
          </p>

          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            1. Information We Collect
          </h2>
          <p className="text-gray-600 dark:text-gray-300">
            {product_name} collects anonymous usage data to improve the service.
            We do NOT collect personal information such as names, emails, or addresses
            unless you explicitly provide them.
          </p>

          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            2. Usage Analytics
          </h2>
          <p className="text-gray-600 dark:text-gray-300">
            We use PostHog (posthog.com) for anonymous product analytics.
            This helps us understand how the tool is used and how to improve it.
            Data collected includes: page views, feature usage patterns, and
            general interaction metrics. No personally identifiable information (PII)
            is collected through analytics.
          </p>

          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            3. Data Processing
          </h2>
          <p className="text-gray-600 dark:text-gray-300">
            All tool processing happens in your browser (client-side).
            Your input data is not sent to or stored on our servers unless
            specifically required for the tool&apos;s functionality.
          </p>

          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            4. Third-Party Services
          </h2>
          <ul className="list-disc pl-6 text-gray-600 dark:text-gray-300">
            <li>PostHog — Anonymous analytics</li>
            <li>Vercel — Hosting</li>
          </ul>

          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            5. Your Rights
          </h2>
          <p className="text-gray-600 dark:text-gray-300">
            You can opt out of analytics tracking by using a browser ad blocker
            or Do Not Track setting. You may request deletion of any data
            associated with your usage.
          </p>

          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            6. Contact
          </h2>
          <p className="text-gray-600 dark:text-gray-300">
            For privacy-related questions, please open an issue on our GitHub repository.
          </p>
        </div>
        <div className="mt-8">
          <a href="/" className="text-blue-600 dark:text-blue-400 hover:underline">
            &larr; Back to {product_name}
          </a>
        </div>
      </div>
    </div>
  );
}}
"""
        return {"src/app/privacy/page.tsx": page_code}

    def _generate_readme(self, prd: dict, product_name: str) -> dict[str, str]:
        """Generate README.md"""
        overview = prd.get("product_overview", {})
        tech = prd.get("tech_architecture", {})

        readme = f"""# {overview.get('display_name', product_name)}

> {overview.get('tagline', '')}

## What it does
{overview.get('core_problem', '')}

## Tech Stack
- **Framework**: {tech.get('framework', 'Next.js 14')}
- **Styling**: {tech.get('styling', 'Tailwind CSS')}
- **Analytics**: {tech.get('analytics', 'PostHog')}
- **Deployment**: {tech.get('deployment', 'Vercel')}

## Getting Started

```bash
# Install dependencies
npm install

# Set up environment (copy and fill in your PostHog key)
cp .env.local.example .env.local

# Run dev server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Deploy to Vercel

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new)

## Privacy
See [Privacy Policy](/privacy).
"""
        return {"README.md": readme}

    def _write_files(self, product_dir: Path, files: dict[str, str]) -> int:
        """Write all generated files to disk"""
        count = 0
        for filepath, content in files.items():
            full_path = product_dir / filepath
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")
            count += 1
        return count
