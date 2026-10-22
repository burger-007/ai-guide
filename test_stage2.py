"""
🧪 Stage 2 Test — PRD Generation + Feasibility Check
Takes the top opportunity from Stage 1 test output and generates a PRD.
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
from rich.panel import Panel
from rich.syntax import Syntax
from rich import box

console = Console()


def find_latest_opportunities() -> list:
    """Find the most recent opportunities file from Stage 1"""
    test_dir = Path("data/test_runs")
    if not test_dir.exists():
        return []
    
    opp_files = sorted(test_dir.glob("opportunities_*.json"), reverse=True)
    if not opp_files:
        return []
    
    latest = opp_files[0]
    console.print(f"[dim]Loading opportunities from: {latest}[/dim]")
    return json.loads(latest.read_text(encoding="utf-8"))


async def test_stage2():
    """Run PRD generation on top opportunity"""
    from shared.llm_client import LLMClient
    from agents.stage2_analyze.prd_generator.agent import PRDGeneratorAgent
    from agents.stage2_analyze.feasibility_checker.agent import FeasibilityCheckerAgent

    console.print(Panel(
        "[bold cyan]Stage 2: Analyze — PRD Generation + Feasibility Check[/bold cyan]",
        box=box.DOUBLE
    ))

    # Load Stage 1 output
    opportunities = find_latest_opportunities()
    if not opportunities:
        console.print("[red]No opportunities found. Run test_stage1.py first.[/red]")
        return

    # Show available opportunities
    console.print("\n[bold]Available Opportunities from Stage 1:[/bold]")
    for i, opp in enumerate(opportunities):
        score = opp.get("priority_score", "?")
        console.print(f"  {i+1}. [{score}] {opp.get('title', 'Untitled')}")

    # Pick the top one
    top = opportunities[0]
    console.print(f"\n[bold green]Selected: {top.get('title')}[/bold green]")

    # Setup LLM
    llm = LLMClient(provider="openai", model="gpt-4o-mini", max_tokens=6000)

    # ====== Phase 1: Generate PRD ======
    console.print("\n[bold yellow]Phase 1: Generating PRD...[/bold yellow]")
    
    prd_agent = PRDGeneratorAgent(llm_client=llm)
    prd_result = await prd_agent.execute(input_data=top)

    if prd_result.status != "completed":
        console.print(f"[red]PRD generation failed: {prd_result.errors}[/red]")
        return

    prd = prd_result.output
    overview = prd.get("product_overview", {})

    console.print(Panel(
        f"[bold white]{overview.get('display_name', 'Product')}[/bold white]\n"
        f"[italic]{overview.get('tagline', '')}[/italic]\n\n"
        f"[bold]Product Name:[/bold] {overview.get('product_name', '')}\n"
        f"[bold]Target User:[/bold] {overview.get('target_user', '')}\n"
        f"[bold]Core Problem:[/bold] {overview.get('core_problem', '')}\n"
        f"[bold]Success Metric:[/bold] {overview.get('success_metric', '')}\n\n"
        f"[bold]User Stories:[/bold] {len(prd.get('user_stories', []))}\n"
        f"[bold]Features:[/bold] {len(prd.get('feature_spec', []))}\n"
        f"[bold]Pages:[/bold] {len(prd.get('ui_spec', {}).get('pages', []))}\n"
        f"[bold]Analytics Events:[/bold] {len(prd.get('data_collection_plan', {}).get('analytics_events', []))}",
        title="Generated PRD",
        box=box.HEAVY,
    ))

    # Show user stories
    console.print("\n[bold]User Stories:[/bold]")
    for story in prd.get("user_stories", []):
        priority = story.get("priority", "?")
        color = {"P0": "red", "P1": "yellow", "P2": "dim"}.get(priority, "white")
        console.print(f"  [{color}][{priority}][/{color}] {story.get('story', '')}")

    # Show features
    console.print("\n[bold]P0 Features:[/bold]")
    for feat in prd.get("feature_spec", []):
        if feat.get("priority", "P0") == "P0":
            console.print(f"  - {feat.get('feature_name', '')}: {feat.get('description', '')[:60]}")

    # Show tech stack
    tech = prd.get("tech_architecture", {})
    console.print(f"\n[bold]Tech:[/bold] {tech.get('framework', '?')} + {tech.get('styling', '?')} → {tech.get('deployment', '?')}")
    for lib in tech.get("key_libraries", []):
        if isinstance(lib, dict):
            console.print(f"  + {lib.get('name', '')}: {lib.get('purpose', '')}")
        else:
            console.print(f"  + {lib}")

    # Show design tokens
    ui = prd.get("ui_spec", {})
    tokens = ui.get("design_tokens", {})
    if tokens:
        console.print(f"\n[bold]Design:[/bold] {tokens.get('primary_color', '?')} | Font: {tokens.get('font', '?')} | {tokens.get('style', '?')}")

    # ====== Phase 2: Feasibility Check ======
    console.print("\n[bold yellow]Phase 2: Feasibility Check...[/bold yellow]")

    feasibility_agent = FeasibilityCheckerAgent(llm_client=llm)
    feas_result = await feasibility_agent.execute(input_data=prd)

    if feas_result.status != "completed":
        console.print(f"[red]Feasibility check failed: {feas_result.errors}[/red]")
        return

    report = feas_result.output

    # Normalize — LLM may return different JSON structures
    verdict = report.get("verdict") or report.get("final_verdict", "UNKNOWN")
    confidence = report.get("confidence", "N/A")
    total_hours = (
        report.get("total_estimated_hours")
        or report.get("time_estimate", {}).get("total_hours", "?")
    )
    build_days = report.get("revised_build_days", "?")
    go_no_go = report.get("go_no_go") or report.get("reason", "N/A")
    issues = report.get("feasibility_issues", [])

    verdict_color = {"GO": "green", "REVISE": "yellow", "ABORT": "red"}.get(verdict, "white")

    # Build details summary from alternative format
    details_lines = []
    for section_key in ["technical_feasibility", "time_estimate", "competitor_check",
                        "data_collection_sanity", "deployment_cost"]:
        section = report.get(section_key, {})
        if isinstance(section, dict) and section.get("details"):
            result_str = section.get("result", "")
            result_color = "green" if result_str == "YES" else "red"
            label = section_key.replace("_", " ").title()
            details_lines.append(
                f"  [{result_color}][{result_str}][/{result_color}] "
                f"[bold]{label}:[/bold] {section['details'][:80]}"
            )

    console.print(Panel(
        f"[bold {verdict_color}]VERDICT: {verdict}[/bold {verdict_color}]\n"
        f"[bold]Confidence:[/bold] {confidence}\n"
        f"[bold]Estimated Hours:[/bold] {total_hours}\n"
        f"[bold]Build Days:[/bold] {build_days}\n",
        title="Feasibility Report",
        box=box.HEAVY,
    ))

    # Show structured issues (expected format)
    if issues:
        console.print(f"[bold]Issues ({len(issues)}):[/bold]")
        for issue in issues:
            sev = issue.get("severity", "info")
            sev_color = {"critical": "red", "warning": "yellow", "info": "cyan"}.get(sev, "white")
            console.print(
                f"  [{sev_color}][{sev.upper()}][/{sev_color}] "
                f"{issue.get('area', '?')}: {issue.get('description', '')}"
            )
            if issue.get("recommendation"):
                console.print(f"    -> {issue['recommendation']}")

    # Show details from alternative format
    if details_lines:
        console.print("\n[bold]Assessment Details:[/bold]")
        for line in details_lines:
            console.print(line)

    # Scope recommendations
    scope = report.get("scope_recommendations", {})
    if scope.get("cut_features"):
        console.print("\n[bold red]Cut Features:[/bold red]")
        for f in scope["cut_features"]:
            console.print(f"  x {f}")
    if scope.get("must_keep"):
        console.print("[bold green]Must Keep:[/bold green]")
        for f in scope["must_keep"]:
            console.print(f"  v {f}")

    # Cost estimate
    cost = report.get("cost_estimate", {})
    deploy = report.get("deployment_cost", {})
    if cost:
        console.print(f"\n[bold]Cost Estimate:[/bold]")
        for tier, amount in cost.items():
            console.print(f"  {tier}: {amount}")
    elif deploy and isinstance(deploy, dict):
        console.print(f"\n[bold]Deployment:[/bold] {deploy.get('details', '')[:80]}")

    console.print(f"\n[bold]Go/No-Go:[/bold] {go_no_go}")
    console.print(f"\n[dim]Total tokens: {llm.total_tokens_used}[/dim]")


if __name__ == "__main__":
    from dotenv import load_dotenv
    env = Path("config/.env")
    if env.exists():
        load_dotenv(env)
    asyncio.run(test_stage2())
