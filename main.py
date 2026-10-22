"""
🏭 Software Factory Pipeline — Entry Point
"""

import asyncio
import argparse
from pathlib import Path

from gateway.orchestrator import Orchestrator


def print_banner():
    print(r"""
    ╔═══════════════════════════════════════════╗
    ║  🏭 Software Factory Pipeline v0.1        ║
    ║                                           ║
    ║  Observe → Analyze → Build → Deploy       ║
    ║            ↑                    |          ║
    ║            └── Self-Optimize ───┘          ║
    ╚═══════════════════════════════════════════╝
    """)


async def cmd_observe(orchestrator: Orchestrator):
    """Run Stage 1: Observe market trends"""
    print("🔭 Starting market observation...")
    results = await orchestrator.run_observe()
    
    status = orchestrator.get_status()
    print(f"\n📊 Results: {status['opportunities_found']} opportunities found")


async def cmd_pipeline(orchestrator: Orchestrator):
    """Run the full pipeline"""
    print("🚀 Starting full pipeline...")
    task = await orchestrator.run_full_pipeline()
    
    if task:
        print(f"\n📋 Task {task.id} is waiting for your review.")
        print(f"   Edit: data/review_{task.id}.json")


async def cmd_approve(orchestrator: Orchestrator, task_id: str):
    """Approve a task for deployment"""
    orchestrator.approve_task(task_id)


async def cmd_reject(orchestrator: Orchestrator, task_id: str, reason: str = ""):
    """Reject a task"""
    orchestrator.reject_task(task_id, notes=reason)


async def cmd_status(orchestrator: Orchestrator):
    """Show pipeline status"""
    status = orchestrator.get_status()
    print("📊 Pipeline Status:")
    for key, value in status.items():
        print(f"   {key}: {value}")


def main():
    print_banner()
    
    parser = argparse.ArgumentParser(description="Software Factory Pipeline")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Commands
    subparsers.add_parser("observe", help="Run market observation (Stage 1)")
    subparsers.add_parser("pipeline", help="Run full pipeline")
    subparsers.add_parser("status", help="Show pipeline status")
    
    approve_parser = subparsers.add_parser("approve", help="Approve a task")
    approve_parser.add_argument("task_id", help="Task ID to approve")
    
    reject_parser = subparsers.add_parser("reject", help="Reject a task")
    reject_parser.add_argument("task_id", help="Task ID to reject")
    reject_parser.add_argument("--reason", default="", help="Rejection reason")
    
    args = parser.parse_args()
    
    # Initialize
    orchestrator = Orchestrator(config_path="config/config.yaml")
    
    if args.command == "observe":
        asyncio.run(cmd_observe(orchestrator))
    elif args.command == "pipeline":
        asyncio.run(cmd_pipeline(orchestrator))
    elif args.command == "approve":
        asyncio.run(cmd_approve(orchestrator, args.task_id))
    elif args.command == "reject":
        asyncio.run(cmd_reject(orchestrator, args.task_id, args.reason))
    elif args.command == "status":
        asyncio.run(cmd_status(orchestrator))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
