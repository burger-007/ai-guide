"""
🚀 Gateway — Pipeline Orchestrator
Central control plane that routes tasks through the 5-stage pipeline.
"""

import asyncio
import json
import yaml
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class PipelineStage(Enum):
    OBSERVE = "observe"
    ANALYZE = "analyze"
    BUILD = "build"
    DEPLOY = "deploy"
    MONITOR = "monitor"


class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    WAITING_HUMAN = "waiting_human"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class PipelineTask:
    """A task flowing through the pipeline"""
    id: str
    stage: PipelineStage
    status: TaskStatus = TaskStatus.PENDING
    input_data: Any = None
    output_data: Any = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = ""
    agent_results: list = field(default_factory=list)
    human_review_notes: str = ""


@dataclass
class Opportunity:
    """A market opportunity discovered by Stage 1"""
    id: str
    title: str
    pain_point: str
    evidence: list = field(default_factory=list)
    market_size: str = "unknown"
    competition_level: str = "unknown"
    technical_feasibility: str = "unknown"
    priority_score: float = 0.0
    recommended_solution: str = ""
    source_agent: str = ""
    discovered_at: str = field(default_factory=lambda: datetime.now().isoformat())


class Orchestrator:
    """
    Pipeline Orchestrator — manages the 5-stage flow.
    
    Flow: Observe → Analyze → Build → [HUMAN REVIEW] → Deploy → Monitor
                                         ↑ stops here until approved
    """
    
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config = self._load_config(config_path)
        self.tasks: dict[str, PipelineTask] = {}
        self.opportunities: list[Opportunity] = []
        self.agents: dict[str, Any] = {}
        self.data_dir = Path("data")
        self.data_dir.mkdir(exist_ok=True)
        
        # Task persistence
        self.tasks_file = self.data_dir / "pipeline_tasks.json"
        self.opps_file = self.data_dir / "opportunities.json"
        self._load_state()
    
    def _load_config(self, path: str) -> dict:
        config_path = Path(path)
        if config_path.exists():
            return yaml.safe_load(config_path.read_text(encoding="utf-8"))
        return {}
    
    def _load_state(self):
        """Load persisted state from disk"""
        if self.tasks_file.exists():
            try:
                data = json.loads(self.tasks_file.read_text(encoding="utf-8"))
                # Reconstruct tasks (simplified)
            except (json.JSONDecodeError, OSError):
                pass
    
    def _save_state(self):
        """Persist state to disk"""
        # Save opportunities
        opps_data = []
        for opp in self.opportunities:
            opps_data.append({
                "id": opp.id,
                "title": opp.title,
                "pain_point": opp.pain_point,
                "priority_score": opp.priority_score,
                "recommended_solution": opp.recommended_solution,
                "discovered_at": opp.discovered_at,
            })
        self.opps_file.write_text(
            json.dumps(opps_data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    
    # ========== Stage Execution ==========
    
    async def run_stage(self, stage: PipelineStage, input_data: Any = None) -> list:
        """Run all agents in a given stage"""
        stage_config = self.config.get("stages", {}).get(stage.value, {})
        agent_ids = stage_config.get("agents", [])
        
        results = []
        for agent_id in agent_ids:
            agent = self.agents.get(agent_id)
            if agent:
                result = await agent.run(input_data)
                results.append(result)
        
        return results
    
    async def run_observe(self):
        """Stage 1: Observe market trends and find opportunities"""
        print("🔭 Stage 1: Observing market trends...")
        results = await self.run_stage(PipelineStage.OBSERVE)
        
        # Extract opportunities from results
        for result in results:
            if result.status == "completed" and result.output:
                if isinstance(result.output, list):
                    for opp_data in result.output:
                        opp = Opportunity(**opp_data)
                        self.opportunities.append(opp)
                        print(f"  💡 Found: {opp.title} (score: {opp.priority_score})")
        
        self._save_state()
        return results
    
    async def run_analyze(self, opportunity: Opportunity):
        """Stage 2: Analyze opportunity and generate PRD"""
        print(f"📊 Stage 2: Analyzing '{opportunity.title}'...")
        results = await self.run_stage(PipelineStage.ANALYZE, input_data={
            "opportunity": opportunity.__dict__,
        })
        return results
    
    async def run_build(self, prd: dict):
        """Stage 3: Build the product based on PRD"""
        print(f"🔨 Stage 3: Building product...")
        results = await self.run_stage(PipelineStage.BUILD, input_data=prd)
        return results
    
    async def request_human_review(self, task: PipelineTask) -> bool:
        """
        ⭐ HUMAN GATE — pauses pipeline and waits for approval.
        Returns True if approved, False if rejected.
        """
        task.status = TaskStatus.WAITING_HUMAN
        
        print("\n" + "=" * 60)
        print("👁️  HUMAN REVIEW REQUIRED")
        print("=" * 60)
        print(f"Task: {task.id}")
        print(f"Stage: {task.stage.value}")
        print(f"Product ready for deployment.")
        print("\nPlease review the generated product in the products/ directory.")
        print("=" * 60)
        
        # Save task state so it persists across restarts
        self._save_task(task)
        
        # In production, this would wait for an API call or CLI input
        # For now, it writes a review file that the user edits
        review_file = self.data_dir / f"review_{task.id}.json"
        review_file.write_text(json.dumps({
            "task_id": task.id,
            "status": "waiting",
            "instructions": "Change status to 'approved' or 'rejected'",
            "notes": "",
        }, indent=2), encoding="utf-8")
        
        print(f"\n📝 Edit this file to approve/reject: {review_file}")
        return False  # Will be checked by monitor loop
    
    async def run_deploy(self, build_output: dict):
        """Stage 4: Deploy to Vercel (after human approval)"""
        print(f"🚀 Stage 4: Deploying product...")
        results = await self.run_stage(PipelineStage.DEPLOY, input_data=build_output)
        return results
    
    async def run_monitor(self):
        """Stage 5: Monitor deployed products"""
        print(f"🔧 Stage 5: Monitoring products...")
        results = await self.run_stage(PipelineStage.MONITOR)
        return results
    
    # ========== Security Gate ==========
    
    async def run_security_scan(self, build_output: dict) -> dict:
        """
        🛡️ Security scan — MANDATORY before any deployment.
        Returns the security report. If verdict is BLOCK, pipeline stops.
        """
        security_agent = self.agents.get("security_guardian")
        if not security_agent:
            print("⚠️  Security Guardian not registered. Skipping scan (NOT RECOMMENDED).")
            return {"verdict": "WARN", "summary": "Security agent not configured"}
        
        print("🛡️  Running security scan...")
        product_dir = build_output.get("product_dir", "")
        result = await security_agent.run({
            "product_dir": product_dir,
            "product_id": build_output.get("product_id", "unknown"),
            "scan_type": "pre_deployment",
        })
        
        if result.status == "completed" and result.output:
            report = result.output
            verdict = report.get("verdict", "PASS")
            
            if verdict == "PASS":
                print("   ✅ Security scan PASSED")
            elif verdict == "WARN":
                print(f"   ⚠️  Security scan: {report.get('total_findings', 0)} issue(s) found")
            else:
                print(f"   🚫 Security scan BLOCKED: {report.get('summary', '')}")
            
            return report
        
        return {"verdict": "WARN", "summary": "Security scan returned no results"}
    
    # ========== Full Pipeline ==========
    
    async def run_full_pipeline(self, opportunity: Optional[Opportunity] = None):
        """
        Run the complete pipeline for an opportunity.
        Stops at human review gate if configured.
        """
        # Stage 1: Observe (if no opportunity provided)
        if opportunity is None:
            await self.run_observe()
            if not self.opportunities:
                print("❌ No opportunities found. Will try again later.")
                return
            # Pick highest priority
            opportunity = max(self.opportunities, key=lambda o: o.priority_score)
        
        # Stage 2: Analyze
        analysis_results = await self.run_analyze(opportunity)
        prd = self._extract_prd(analysis_results)
        
        # Stage 3: Build
        build_results = await self.run_build(prd)
        build_output = self._extract_build_output(build_results)
        
        # 🛡️ SECURITY SCAN (mandatory, before human review)
        security_report = await self.run_security_scan(build_output)
        if security_report and security_report.get("verdict") == "BLOCK":
            print("\n🚫 SECURITY SCAN BLOCKED DEPLOYMENT")
            print(f"   {security_report.get('summary', 'Critical issues found')}")
            print("   Fix the issues and re-run the pipeline.")
            task = PipelineTask(
                id=f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                stage=PipelineStage.BUILD,
                status=TaskStatus.FAILED,
                input_data=build_output,
                output_data=security_report,
            )
            self.tasks[task.id] = task
            self._save_task(task)
            return task
        
        # ⭐ HUMAN REVIEW GATE (only reached if security scan passes)
        if self.config.get("pipeline", {}).get("human_review", True):
            task = PipelineTask(
                id=f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                stage=PipelineStage.DEPLOY,
                input_data={
                    "build": build_output,
                    "security_report": security_report,  # Show to human reviewer
                },
            )
            self.tasks[task.id] = task
            await self.request_human_review(task)
            print("\n⏸️  Pipeline paused. Waiting for human review...")
            return task
        
        # Stage 4: Deploy (auto if no review needed)
        await self.run_deploy(build_output)
        
        return None
    
    def approve_task(self, task_id: str, notes: str = ""):
        """Resume pipeline after human approval"""
        task = self.tasks.get(task_id)
        if task and task.status == TaskStatus.WAITING_HUMAN:
            task.status = TaskStatus.APPROVED
            task.human_review_notes = notes
            print(f"✅ Task {task_id} approved! Resuming deployment...")
            # Trigger deployment
            asyncio.create_task(self.run_deploy(task.input_data))
    
    def reject_task(self, task_id: str, notes: str = ""):
        """Reject a task — product will not be deployed"""
        task = self.tasks.get(task_id)
        if task:
            task.status = TaskStatus.REJECTED
            task.human_review_notes = notes
            print(f"❌ Task {task_id} rejected. Reason: {notes}")
    
    # ========== Helpers ==========
    
    def _extract_prd(self, results: list) -> dict:
        for r in results:
            if r.status == "completed" and r.output:
                return r.output
        return {}
    
    def _extract_build_output(self, results: list) -> dict:
        for r in results:
            if r.status == "completed" and r.output:
                return r.output
        return {}
    
    def _save_task(self, task: PipelineTask):
        tasks_dir = self.data_dir / "tasks"
        tasks_dir.mkdir(exist_ok=True)
        task_file = tasks_dir / f"{task.id}.json"
        task_file.write_text(json.dumps({
            "id": task.id,
            "stage": task.stage.value,
            "status": task.status.value,
            "created_at": task.created_at,
        }, indent=2), encoding="utf-8")
    
    def register_agent(self, agent_id: str, agent):
        """Register an agent with the orchestrator"""
        self.agents[agent_id] = agent
    
    def get_status(self) -> dict:
        """Get current pipeline status"""
        return {
            "opportunities_found": len(self.opportunities),
            "active_tasks": len([t for t in self.tasks.values() 
                               if t.status in (TaskStatus.IN_PROGRESS, TaskStatus.WAITING_HUMAN)]),
            "pending_review": len([t for t in self.tasks.values()
                                 if t.status == TaskStatus.WAITING_HUMAN]),
            "completed": len([t for t in self.tasks.values()
                            if t.status == TaskStatus.COMPLETED]),
        }
