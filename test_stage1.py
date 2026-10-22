"""
🧪 Stage 1 Test Run v3 — Full Market Observation (All Issues Fixed)
Fixed: GitHub parsing, Reddit noise filtering, LLM evidence quality, resource warnings.
"""

import asyncio
import json
import os
import sys
import warnings
from datetime import datetime
from pathlib import Path

os.environ["PYTHONIOENCODING"] = "utf-8"
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
warnings.filterwarnings("ignore", category=ResourceWarning)

sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from shared.web_search import WebSearchTool

console = Console()

# Subreddits that contain relevant tech/tool discussions
RELEVANT_SUBREDDITS = {
    "sideproject", "webdev", "saas", "startups", "entrepreneur",
    "smallbusiness", "internetisbeautiful", "selfhosted", "nocode",
    "javascript", "python", "programming", "devops", "opensource",
    "indiehackers", "microsaas", "buildinpublic", "productivity",
}

# Keywords that indicate noise (non-tech viral posts from r/all)
NOISE_KEYWORDS = [
    "aitah", "aita", "wife", "husband", "boyfriend", "girlfriend",
    "marriage", "divorce", "trump", "biden", "election", "political",
    "meme", "nfl", "nba", "football", "soccer",
]


def is_relevant_signal(signal: dict) -> bool:
    """Filter out noise — only keep tech/tool-relevant signals"""
    title = (signal.get("title") or "").lower()
    sub = (signal.get("subreddit") or "").lower()
    source = signal.get("source", "")

    # Non-Reddit sources are always relevant
    if source in ("duckduckgo", "hackernews", "hackernews_frontpage", "github_trending"):
        return True

    # Reddit: check subreddit relevance
    if source in ("reddit", "reddit_hot"):
        # If from a known relevant sub, keep it
        if sub in RELEVANT_SUBREDDITS:
            return True
        # If from r/all, check for noise keywords
        for noise in NOISE_KEYWORDS:
            if noise in title:
                return False
        # Check for tool-related keywords in title
        tool_signals = ["tool", "built", "made", "launched", "free", "open source",
                        "alternative", "app", "site", "software", "project", "dev"]
        return any(kw in title for kw in tool_signals)

    return True


async def test_full_observation():
    """Full Stage 1 observation with all fixes applied"""
    search = WebSearchTool()

    console.print(Panel(
        "[bold cyan]Stage 1: Market Observation v3 (All Fixes)[/bold cyan]\n"
        "DuckDuckGo + Hacker News + Reddit + GitHub Trending",
        box=box.DOUBLE
    ))

    all_signals = []

    # ====== 1. DuckDuckGo ======
    console.print("\n[bold yellow]1/4  DuckDuckGo[/bold yellow]")
    ddg_queries = [
        "free alternative to expensive SaaS",
        "simple developer tool I wish existed",
        "best free open source tools 2026",
        "productivity tool side project launch",
        "no good free tool for small business",
    ]
    for q in ddg_queries:
        results = await search.search_ddg(q, max_results=8)
        status = f"[green]{len(results)}[/green]" if results else "[red]0[/red]"
        console.print(f"   {status} '{q}'")
        all_signals.extend(results)

    # ====== 2. Hacker News ======
    console.print("\n[bold yellow]2/4  Hacker News[/bold yellow]")

    front = await search.get_hn_front_page(limit=20)
    console.print(f"   [green]{len(front)}[/green] front page stories")
    all_signals.extend(front)

    hn_queries = [
        ("Show HN", 15, "month"),
        ("free tool", 10, "week"),
        ("open source alternative", 10, "month"),
        ("I built", 10, "week"),
        ("developer productivity", 8, "month"),
    ]
    for query, limit, time in hn_queries:
        results = await search.search_hackernews(query, max_results=limit, time_range=time)
        high = len([r for r in results if r.get("points", 0) > 50])
        console.print(f"   [green]{len(results)}[/green] '{query}' ({high} high-engagement)")
        all_signals.extend(results)

    # ====== 3. Reddit — targeted subs only (no r/all noise) ======
    console.print("\n[bold yellow]3/4  Reddit (targeted subs)[/bold yellow]")

    # Search specific subreddits with relevant queries
    reddit_searches = [
        ("SideProject", "launched free tool"),
        ("SideProject", "I built"),
        ("webdev", "need tool for"),
        ("webdev", "wish there was"),
        ("SaaS", "free alternative"),
        ("SaaS", "too expensive"),
        ("Entrepreneur", "tool I built this week"),
        ("selfhosted", "looking for free"),
        ("InternetIsBeautiful", "free tool"),
        ("opensource", "new project"),
    ]
    for sub, query in reddit_searches:
        results = await search.search_reddit(
            query=query, subreddit=sub,
            sort="relevance", time_filter="month", limit=8
        )
        hot = len([r for r in results if r.get("score", 0) > 15])
        console.print(f"   [green]{len(results)}[/green] r/{sub} '{query}' ({hot} hot)")
        all_signals.extend(results)

    # Hot posts from tool-focused subs
    for sub in ["SideProject", "InternetIsBeautiful", "webdev", "selfhosted"]:
        results = await search.get_reddit_hot(sub, limit=10)
        console.print(f"   [green]{len(results)}[/green] r/{sub} /hot")
        all_signals.extend(results)

    # ====== 4. GitHub Trending ======
    console.print("\n[bold yellow]4/4  GitHub Trending[/bold yellow]")
    for lang in ["", "typescript", "python"]:
        trending = await search.get_github_trending(language=lang, since="weekly")
        label = lang or "all"
        console.print(f"   [green]{len(trending)}[/green] {label}")
        for r in trending[:3]:
            stars = r.get("stars_today", 0)
            desc = r.get("description", "")[:50]
            console.print(f"      {r['repo']} ({stars} stars today) {desc}")
        all_signals.extend(trending)

    await search.close()

    # ====== Filter noise + deduplicate ======
    filtered = [s for s in all_signals if is_relevant_signal(s)]
    console.print(f"\n[dim]Filtered: {len(all_signals)} raw -> {len(filtered)} relevant (removed {len(all_signals)-len(filtered)} noise)[/dim]")

    seen = set()
    unique = []
    for s in filtered:
        key = (s.get("title", s.get("repo", "")).lower().strip()[:60], s.get("source", ""))
        if key[0] and key not in seen:
            seen.add(key)
            unique.append(s)

    # ====== Summary ======
    console.print()
    src_counts = {}
    for s in unique:
        src = s.get("source", "unknown")
        src_counts[src] = src_counts.get(src, 0) + 1

    table = Table(title="Signal Summary", box=box.ROUNDED)
    table.add_column("Source", style="cyan")
    table.add_column("Count", style="green", justify="right")
    for src, cnt in sorted(src_counts.items(), key=lambda x: x[1], reverse=True):
        table.add_row(src, str(cnt))
    table.add_row("[bold]TOTAL[/bold]", f"[bold]{len(unique)}[/bold]")
    console.print(table)

    # Top signals
    scored = [s for s in unique if (s.get("points", 0) or s.get("score", 0) or s.get("stars_today", 0) or 0) > 5]
    scored.sort(key=lambda s: s.get("points", 0) or s.get("score", 0) or s.get("stars_today", 0) or 0, reverse=True)

    top_table = Table(title="Top 20 Relevant Signals", box=box.SIMPLE_HEAVY)
    top_table.add_column("Eng", style="bold cyan", width=7, justify="right")
    top_table.add_column("Src", style="yellow", width=10)
    top_table.add_column("Title / Repo", style="white")
    for s in scored[:20]:
        pts = s.get("points", 0) or s.get("score", 0) or s.get("stars_today", 0) or 0
        top_table.add_row(
            str(pts),
            s.get("source", "?")[:10],
            (s.get("title") or s.get("repo", ""))[:65],
        )
    console.print(top_table)

    # Save
    out_dir = Path("data/test_runs")
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    Path(out_dir / f"signals_{ts}.json").write_text(
        json.dumps(unique, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    console.print(f"\n   Saved {len(unique)} signals -> data/test_runs/signals_{ts}.json")

    # ====== LLM Analysis ======
    if not os.getenv("OPENAI_API_KEY"):
        console.print("\n[yellow]No OPENAI_API_KEY. Skipping LLM.[/yellow]")
        return
    console.print(f"\n[bold green]Running LLM deep analysis...[/bold green]")
    await run_llm_analysis(unique, ts)


async def run_llm_analysis(signals: list, timestamp: str):
    """Deep LLM analysis with strict evidence requirements"""
    from shared.llm_client import LLMClient
    llm = LLMClient(provider="openai", model="gpt-4o-mini", max_tokens=6000)

    # Build diverse digest — top by engagement, balanced across sources
    digest = []
    source_budgets = {
        "hackernews": 12, "hackernews_frontpage": 8, "reddit": 10,
        "reddit_hot": 6, "duckduckgo": 10, "github_trending": 8
    }
    source_used = {}
    scored = sorted(signals, key=lambda s: s.get("points", 0) or s.get("score", 0) or s.get("stars_today", 0) or 0, reverse=True)

    for s in scored:
        src = s.get("source", "other")
        if source_used.get(src, 0) >= source_budgets.get(src, 5):
            continue
        digest.append({
            "source": src,
            "title": (s.get("title") or s.get("repo", ""))[:120],
            "snippet": (s.get("snippet") or s.get("selftext") or s.get("description", ""))[:250],
            "engagement": s.get("points", 0) or s.get("score", 0) or s.get("stars_today", 0) or 0,
            "url": s.get("url", ""),
            "subreddit": s.get("subreddit", ""),
        })
        source_used[src] = source_used.get(src, 0) + 1
        if len(digest) >= 50:
            break

    system_prompt = """You are an elite market analyst for an autonomous software factory.
Your factory builds FREE web tools, deploys them, and collects usage data as its primary asset.

ANALYSIS RULES (STRICT):
1. CROSS-REFERENCE: Each opportunity MUST be supported by signals from AT LEAST 2 different sources (e.g., Reddit + HN, or DDG + Reddit). Single-source opportunities are REJECTED.
2. VERIFY GAPS: For each opportunity, explicitly check if a free, good-quality tool already exists. If yes, explain exactly why ours would be better.
3. ACTIONABLE SPECIFICS: Don't say "a tool for X". Say "A Next.js web app that lets users [specific action] by [specific mechanism]".
4. DATA MOAT: Explain exactly WHAT data the tool collects and WHY that data has value for future products.
5. SCORING: Be honest. Don't inflate scores. A true 9/10 means multiple strong signals + clear gap + easy to build.
6. WEB APP ONLY: Must be deployable on Vercel as a Next.js app. No native apps, no browser extensions.
7. ENGLISH ONLY: All output in English.
8. REAL-WORLD FEASIBILITY: Only suggest tools that a single developer can build and ship in 3-5 days.

OUTPUT REQUIREMENTS:
- Return exactly 5 opportunities ranked by priority_score
- Each must have evidence from multiple sources
- Each must have specific, concrete MVP features (not vague)
- Tech stack must always be: Next.js + Tailwind + Vercel + (PostHog for analytics)"""

    user_prompt = f"""MARKET SIGNALS ({len(digest)} from today's scan across HN, Reddit, DDG, GitHub):

{json.dumps(digest, indent=2)}

TASK: Find the 5 best opportunities for free web tools. Remember:
- Need evidence from 2+ sources for each opportunity
- Must verify no excellent free alternative already exists
- Must explain the data collection value specifically

Return JSON array:
[{{
  "rank": 1,
  "title": "Product Name",
  "tagline": "One-line value prop",
  "pain_point": "Detailed problem with specific evidence citations",
  "evidence": [
    {{"signal": "exact signal title", "source": "hackernews/reddit/duckduckgo/github", "engagement": 150, "relevance": "why this supports the opportunity"}}
  ],
  "existing_alternatives": "Name specific tools + their shortcomings",
  "our_advantage": "Why a free version wins",
  "mvp_features": ["Specific feature 1", "Specific feature 2", "Specific feature 3"],
  "tech_stack": "Next.js, Tailwind, Vercel, PostHog + specific libs",
  "build_days": 4,
  "data_collection": {{
    "what": "Exactly what data is collected",
    "how": "How it's collected (events, forms, usage patterns)",
    "value": "Why this data is valuable for future products"
  }},
  "scores": {{
    "evidence_strength": 8,
    "market_gap": 7,
    "build_feasibility": 9,
    "data_value": 8,
    "virality": 6
  }},
  "priority_score": 7.8
}}]"""

    try:
        result = await llm.chat_json(system=system_prompt, user=user_prompt, temperature=0.3)

        if isinstance(result, dict):
            result = result.get("opportunities", result.get("tools", [result]))
        if not isinstance(result, list):
            result = [result]

        # Display
        console.print()
        for opp in result:
            scores = opp.get("scores", {})
            evidence_lines = []
            for e in opp.get("evidence", []):
                if isinstance(e, dict):
                    evidence_lines.append(f"  [{e.get('source','?')}] {e.get('signal','')[:60]} (eng: {e.get('engagement','?')})")
                else:
                    evidence_lines.append(f"  - {e}")

            dc = opp.get("data_collection", {})
            if isinstance(dc, str):
                data_text = dc
            else:
                data_text = f"Collect: {dc.get('what','?')} | Value: {dc.get('value','?')}"

            panel_text = (
                f"[bold white]{opp.get('title', '')}[/bold white]\n"
                f"[italic]{opp.get('tagline', '')}[/italic]\n\n"
                f"[bold]Pain Point:[/bold] {opp.get('pain_point', '')}\n\n"
                f"[bold]Evidence ({len(opp.get('evidence', []))} signals):[/bold]\n" +
                "\n".join(evidence_lines) +
                f"\n\n[bold]Existing Alternatives:[/bold] {opp.get('existing_alternatives', 'N/A')}\n"
                f"[bold]Our Advantage:[/bold] {opp.get('our_advantage', '')}\n\n"
                f"[bold]MVP Features:[/bold]\n" +
                "\n".join(f"  - {f}" for f in opp.get("mvp_features", [])) +
                f"\n\n[bold]Data Value:[/bold] {data_text}\n"
                f"[bold]Build:[/bold] {opp.get('build_days', '?')} days | {opp.get('tech_stack', 'Next.js')}\n\n"
                f"[cyan]evidence={scores.get('evidence_strength','?')} "
                f"gap={scores.get('market_gap','?')} "
                f"feasibility={scores.get('build_feasibility','?')} "
                f"data={scores.get('data_value','?')} "
                f"viral={scores.get('virality','?')}[/cyan]"
            )
            console.print(Panel(
                panel_text,
                title=f"#{opp.get('rank','?')}  Score: [bold cyan]{opp.get('priority_score', '?')}[/bold cyan] /10",
                box=box.HEAVY,
            ))

        console.print(f"\n[dim]Tokens: {llm.total_tokens_used} | Model: gpt-4o-mini[/dim]")

        out = Path("data/test_runs") / f"opportunities_{timestamp}.json"
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        console.print(f"   Saved -> {out}")

    except Exception as e:
        console.print(f"[red]LLM error: {e}[/red]")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    from dotenv import load_dotenv
    env = Path("config/.env")
    if env.exists():
        load_dotenv(env)
    asyncio.run(test_full_observation())
