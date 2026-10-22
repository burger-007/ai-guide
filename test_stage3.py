"""
🧪 Stage 3 Test — Full Pipeline: Opportunity → PRD → Code → Quality Check
Uses existing Stage 2 PRD output to generate and verify a Next.js project.
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
from rich.tree import Tree
from rich import box

console = Console()


def find_latest_prd() -> dict:
    """Find the most recent PRD from Stage 2"""
    prd_dir = Path("data/prds")
    if not prd_dir.exists():
        return {}
    prd_files = sorted(prd_dir.glob("*.json"), reverse=True)
    if not prd_files:
        return {}
    latest = prd_files[0]
    console.print(f"[dim]Loading PRD from: {latest}[/dim]")
    return json.loads(latest.read_text(encoding="utf-8"))


async def generate_prd_fresh():
    """If no PRD exists yet, generate one from opportunities"""
    from shared.llm_client import LLMClient
    from agents.stage2_analyze.prd_generator.agent import PRDGeneratorAgent

    opps_dir = Path("data/test_runs")
    opp_files = sorted(opps_dir.glob("opportunities_*.json"), reverse=True)
    if not opp_files:
        console.print("[red]No opportunities found. Run test_stage1.py first.[/red]")
        return None

    opportunities = json.loads(opp_files[0].read_text(encoding="utf-8"))

    # Pick first opportunity (in real pipeline, pick first GO one)
    opp = opportunities[0]
    console.print(f"[bold]Generating PRD for: {opp.get('title')}[/bold]")

    llm = LLMClient(provider="openai", model="gpt-4o-mini", max_tokens=6000)
    prd_agent = PRDGeneratorAgent(llm_client=llm)
    result = await prd_agent.execute(input_data=opp)

    if result.status == "completed":
        return result.output
    return None


async def test_stage3():
    """Generate code from PRD and check quality"""
    from shared.llm_client import LLMClient
    from agents.stage3_build.code_generator.agent import CodeGeneratorAgent
    from agents.stage3_build.quality_checker.agent import QualityCheckerAgent

    console.print(Panel(
        "[bold cyan]Stage 3: Build — Code Generation + Quality Check[/bold cyan]",
        box=box.DOUBLE
    ))

    # Load or generate PRD
    prd = find_latest_prd()
    if not prd:
        console.print("[yellow]No PRD found. Generating one first...[/yellow]")
        prd = await generate_prd_fresh()
        if not prd:
            console.print("[red]Failed to generate PRD.[/red]")
            return

    overview = prd.get("product_overview", {})
    console.print(f"\n[bold green]Product: {overview.get('display_name', '?')}[/bold green]")
    console.print(f"[dim]{overview.get('tagline', '')}[/dim]")

    # Setup LLM (use gpt-4o-mini for code gen — fast and cheap)
    llm = LLMClient(provider="openai", model="gpt-4o-mini", max_tokens=8000)

    # ====== Phase 1: Generate Code ======
    console.print("\n[bold yellow]Phase 1: Generating Next.js project...[/bold yellow]")

    code_agent = CodeGeneratorAgent(llm_client=llm, products_dir="products")
    code_result = await code_agent.execute(input_data=prd)

    if code_result.status != "completed":
        console.print(f"[red]Code generation failed: {code_result.errors}[/red]")
        return

    output = code_result.output
    product_dir = output["product_dir"]
    file_list = output["files"]

    # Display file tree
    tree = Tree(f"[bold]{product_dir}[/bold]")
    for f in sorted(file_list):
        parts = f.split("/")
        current = tree
        for i, part in enumerate(parts):
            if i == len(parts) - 1:
                size = 0
                fp = Path(product_dir) / f
                if fp.exists():
                    size = fp.stat().st_size
                current.add(f"[cyan]{part}[/cyan] [dim]({size}b)[/dim]")
            else:
                # Find or create branch
                found = False
                for child in current.children:
                    if child.label and part in str(child.label):
                        current = child
                        found = True
                        break
                if not found:
                    current = current.add(f"[yellow]{part}/[/yellow]")

    console.print(tree)
    console.print(f"\n   {len(file_list)} files generated")

    # ====== Phase 2: Quality Check ======
    console.print("\n[bold yellow]Phase 2: Quality Check...[/bold yellow]")

    qa_agent = QualityCheckerAgent(llm_client=llm)
    qa_result = await qa_agent.execute(input_data={
        "prd": prd,
        "product_dir": product_dir,
        "files": file_list,
    })

    if qa_result.status != "completed":
        console.print(f"[red]Quality check failed: {qa_result.errors}[/red]")
        return

    report = qa_result.output
    verdict = report.get("verdict", "UNKNOWN")
    score = report.get("score", 0)
    verdict_color = {"PASS": "green", "NEEDS_FIX": "yellow", "FAIL": "red"}.get(verdict, "white")

    console.print(Panel(
        f"[bold {verdict_color}]{verdict}[/bold {verdict_color}] — Score: {score}/100\n\n"
        f"[bold]Issues:[/bold] {len(report.get('issues', []))}\n"
        f"[bold]Missing Features:[/bold] {len(report.get('missing_features', []))}\n"
        f"[bold]Missing Files:[/bold] {len(report.get('missing_files', []))}\n"
        f"[bold]Ready for Review:[/bold] {report.get('ready_for_review', False)}",
        title="Quality Report",
        box=box.HEAVY,
    ))

    for issue in report.get("issues", []):
        sev = issue.get("severity", "minor")
        sev_color = {"blocker": "red", "major": "yellow", "minor": "cyan"}.get(sev, "white")
        console.print(
            f"  [{sev_color}][{sev.upper()}][/{sev_color}] "
            f"{issue.get('file', '?')}: {issue.get('description', '')}"
        )
        if issue.get("fix_suggestion"):
            console.print(f"    -> {issue['fix_suggestion']}")

    if report.get("missing_features"):
        console.print("\n[bold]Missing Features:[/bold]")
        for f in report["missing_features"]:
            console.print(f"  ! {f}")

    console.print(f"\n[dim]Total tokens: {llm.total_tokens_used}[/dim]")

    # Summary
    console.print(Panel(
        f"Product: [bold]{overview.get('display_name', '?')}[/bold]\n"
        f"Directory: {product_dir}\n"
        f"Files: {len(file_list)}\n"
        f"Quality: [{verdict_color}]{verdict} ({score}/100)[/{verdict_color}]\n"
        f"Ready: {report.get('ready_for_review', False)}\n\n"
        f"Next: Run `cd {product_dir} && npm install && npm run dev`",
        title="Stage 3 Complete",
        box=box.DOUBLE,
    ))


if __name__ == "__main__":
    from dotenv import load_dotenv
    env = Path("config/.env")
    if env.exists():
        load_dotenv(env)
    asyncio.run(test_stage3())
