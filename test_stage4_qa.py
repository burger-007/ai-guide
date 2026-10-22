"""
🧪 Stage 4 Test — QA Agent
Run comprehensive QA on generated product.
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
from rich.table import Table
from rich import box

console = Console()


def find_latest_product() -> tuple[Path, dict]:
    """Find latest product dir and its PRD"""
    products_dir = Path("products")
    if not products_dir.exists():
        return None, {}

    # Find most recent product directory
    product_dirs = [d for d in products_dir.iterdir() if d.is_dir()]
    if not product_dirs:
        return None, {}

    latest = max(product_dirs, key=lambda d: d.stat().st_mtime)

    # Find matching PRD
    prd_dir = Path("data/prds")
    prd = {}
    if prd_dir.exists():
        prd_files = sorted(prd_dir.glob("*.json"), reverse=True)
        for f in prd_files:
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                name = data.get("product_overview", {}).get("product_name", "")
                if name.lower() in latest.name.lower() or latest.name.lower() in name.lower():
                    prd = data
                    break
            except Exception:
                pass
        if not prd and prd_files:
            prd = json.loads(prd_files[0].read_text(encoding="utf-8"))

    return latest, prd


async def test_stage4():
    """Run QA on the latest generated product"""
    from shared.llm_client import LLMClient
    from agents.stage4_qa.qa_agent.agent import QAAgent

    console.print(Panel(
        "[bold cyan]Stage 4: QA Agent (品管)[/bold cyan]\n"
        "Build verification + 8-area comprehensive check",
        box=box.DOUBLE
    ))

    product_dir, prd = find_latest_product()
    if not product_dir:
        console.print("[red]No product found. Run test_stage3.py first.[/red]")
        return

    overview = prd.get("product_overview", {})
    console.print(f"\n[bold green]Product: {overview.get('display_name', product_dir.name)}[/bold green]")
    console.print(f"[dim]Directory: {product_dir}[/dim]")

    # Setup
    llm = LLMClient(provider="openai", model="gpt-4o-mini", max_tokens=4000)
    qa = QAAgent(llm_client=llm)

    # List files
    files = [str(f.relative_to(product_dir)).replace("\\", "/")
             for f in product_dir.rglob("*")
             if f.is_file() and "node_modules" not in str(f) and ".next" not in str(f)]

    console.print(f"   Files to scan: {len(files)}")

    # Run QA
    console.print("\n[bold yellow]Running QA...[/bold yellow]")
    result = await qa.execute(input_data={
        "product_dir": str(product_dir),
        "product_id": product_dir.name,
        "prd": prd,
        "files": files,
    })

    if result.status != "completed":
        console.print(f"[red]QA failed: {result.errors}[/red]")
        return

    report = result.output
    verdict = report.get("verdict", "UNKNOWN")
    score = report.get("overall_score", 0)
    verdict_color = {"SHIP_IT": "green", "FIX_REQUIRED": "yellow", "REBUILD": "red"}.get(verdict, "white")

    # Header
    console.print(Panel(
        f"[bold {verdict_color}]{verdict}[/bold {verdict_color}] — "
        f"Overall Score: [bold]{score}/100[/bold]",
        title="QA Verdict",
        box=box.HEAVY,
    ))

    # Area scores table
    table = Table(title="QA Area Scores", box=box.ROUNDED)
    table.add_column("Area", style="bold")
    table.add_column("Score", justify="center")
    table.add_column("Verdict", justify="center")
    table.add_column("Weight", justify="center")
    table.add_column("Issues", justify="center")

    area_weights = {
        "build": "25%", "files": "5%", "prd_compliance": "20%",
        "security": "15%", "analytics": "10%", "seo": "10%",
        "ux": "10%", "code_quality": "5%",
    }
    area_icons = {
        "build": "Build", "files": "Files", "prd_compliance": "PRD",
        "security": "Security", "analytics": "Analytics", "seo": "SEO",
        "ux": "UX", "code_quality": "Code",
    }

    areas = report.get("areas", {})
    for area_key in ["build", "files", "prd_compliance", "security",
                     "analytics", "seo", "ux", "code_quality"]:
        area = areas.get(area_key, {})
        av = area.get("verdict", "?")
        ascore = area.get("score", 0)
        vc = {"PASS": "green", "PARTIAL": "yellow", "FAIL": "red"}.get(av, "white")
        issues_count = len(area.get("issues", []))
        table.add_row(
            area_icons.get(area_key, area_key),
            f"[{vc}]{ascore}[/{vc}]",
            f"[{vc}]{av}[/{vc}]",
            area_weights.get(area_key, "?"),
            str(issues_count) if issues_count > 0 else "[dim]-[/dim]",
        )

    console.print(table)

    # Blockers
    blockers = report.get("blockers", [])
    if blockers:
        console.print(f"\n[bold red]BLOCKERS ({len(blockers)}):[/bold red]")
        for b in blockers:
            console.print(f"  [red]X[/red] {b}")

    # Warnings
    warns = report.get("warnings", [])
    if warns:
        console.print(f"\n[bold yellow]WARNINGS ({len(warns)}):[/bold yellow]")
        for w in warns[:10]:
            console.print(f"  [yellow]![/yellow] {w}")

    # Suggestions
    suggestions = report.get("suggestions", [])
    if suggestions:
        console.print(f"\n[dim]Suggestions ({len(suggestions)}):[/dim]")
        for s in suggestions[:5]:
            console.print(f"  [dim]- {s}[/dim]")

    # Fix instructions
    fixes = report.get("fix_instructions", [])
    if fixes:
        console.print(f"\n[bold]Fix Instructions:[/bold]")
        for fix in fixes[:5]:
            f = fix.get("file", "?")
            desc = fix.get("description", fix.get("fix", ""))
            console.print(f"  [{f}] {desc}")

    console.print(f"\n[dim]Tokens used: {llm.total_tokens_used}[/dim]")


if __name__ == "__main__":
    from dotenv import load_dotenv
    env = Path("config/.env")
    if env.exists():
        load_dotenv(env)
    asyncio.run(test_stage4())
