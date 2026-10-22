"""
🏭 Full Pipeline Run — Income Percentile Calculator
Stage 2 (PRD) → Stage 3 (Code) → I fix → Stage 4 (QA)
"""

import asyncio
import json
import os
import sys
import warnings
from pathlib import Path

os.environ["PYTHONIOENCODING"] = "utf-8"
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
warnings.filterwarnings("ignore", category=ResourceWarning)

sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console
from rich.panel import Panel
from rich import box

console = Console()

# The opportunity — manually curated from our market scan
OPPORTUNITY = {
    "rank": 1,
    "title": "Income Percentile Calculator",
    "tagline": "See where you stand — compare your income to your country and the world.",
    "pain_point": "People are curious about their financial standing but have no easy, free tool to visualize where their income falls relative to others in their country and globally. A Reddit post 'I built a site to see how poor I actually am compared to my country' got 599+ upvotes, proving massive demand.",
    "evidence": [
        {"signal": "I built a site to see how poor I actually am compared to my country [OC]",
         "source": "reddit", "engagement": 599},
        {"signal": "Killed by Google, visualized: 49 of 299 retired products clustered in just two specific years",
         "source": "reddit", "engagement": 770},
    ],
    "existing_alternatives": "Global Rich List exists but is outdated (2015 data). Most alternatives require signup or show ads. None offer per-country breakdowns with recent data.",
    "our_advantage": "Free, no signup, modern UI with interactive charts. Uses 2024 World Bank / OECD data. Client-side only — no income data ever sent to servers.",
    "mvp_features": [
        "Select country from dropdown, enter annual income",
        "See your percentile rank with animated bar chart",
        "Compare across countries (side-by-side)",
        "Share result image on social media",
    ],
    "tech_stack": "Next.js 14, Tailwind, Vercel, PostHog + Recharts for visualization",
    "build_days": 3,
    "data_collection": {
        "what": "Country selections, income ranges (bucketed, not exact), comparison patterns, share events",
        "how": "PostHog events on each interaction, all processing client-side",
        "value": "Anonymous income distribution data across countries — extremely valuable market research",
    },
    "scores": {"evidence_strength": 8, "market_gap": 8, "build_feasibility": 9, "data_value": 9, "virality": 9},
    "priority_score": 8.6,
}


async def run_pipeline():
    from shared.llm_client import LLMClient
    from agents.stage2_analyze.prd_generator.agent import PRDGeneratorAgent
    from agents.stage3_build.code_generator.agent import CodeGeneratorAgent

    console.print(Panel(
        "[bold cyan]Full Pipeline: Income Percentile Calculator[/bold cyan]\n"
        "Stage 2 (PRD) + Stage 3 (Code Gen)",
        box=box.DOUBLE
    ))

    llm = LLMClient(provider="openai", model="gpt-4o-mini", max_tokens=8000)

    # ===== Stage 2: PRD =====
    console.print("\n[bold yellow]Stage 2: Generating PRD...[/bold yellow]")
    prd_agent = PRDGeneratorAgent(llm_client=llm)
    prd_result = await prd_agent.execute(input_data=OPPORTUNITY)

    if prd_result.status != "completed":
        console.print(f"[red]PRD failed: {prd_result.errors}[/red]")
        return
    
    prd = prd_result.output
    overview = prd.get("product_overview", {})
    console.print(f"   PRD: [bold]{overview.get('display_name', '?')}[/bold]")
    console.print(f"   Features: {len(prd.get('feature_spec', []))}")
    console.print(f"   Pages: {len(prd.get('ui_spec', {}).get('pages', []))}")

    # ===== Stage 3: Code Gen =====
    console.print("\n[bold yellow]Stage 3: Generating Code...[/bold yellow]")
    code_agent = CodeGeneratorAgent(llm_client=llm, products_dir="products")
    code_result = await code_agent.execute(input_data=prd)

    if code_result.status != "completed":
        console.print(f"[red]Code gen failed: {code_result.errors}[/red]")
        return
    
    output = code_result.output
    console.print(f"   Product: {output['product_dir']}")
    console.print(f"   Files: {output['file_count']}")
    for f in sorted(output['files']):
        console.print(f"     {f}")
    
    console.print(f"\n[dim]Tokens: {llm.total_tokens_used}[/dim]")
    console.print(Panel(
        f"[bold green]Pipeline complete![/bold green]\n"
        f"Product: {output['product_dir']}\n"
        f"Next: I will manually fix the code to production quality.",
        box=box.DOUBLE
    ))


if __name__ == "__main__":
    from dotenv import load_dotenv
    env = Path("config/.env")
    if env.exists():
        load_dotenv(env)
    asyncio.run(run_pipeline())
