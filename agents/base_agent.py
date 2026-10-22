"""
🏭 Software Factory Pipeline — Base Agent
OpenClaw-inspired File-first Agentic Loop

Every agent has:
  - SOUL.md   → Who it is (personality, values)
  - AGENTS.md → What it does (rules, constraints)  
  - TOOLS.md  → What tools it can use
  - MEMORY.md → What it remembers
"""

import json
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class AgentStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    WAITING_HUMAN = "waiting_human"
    ERROR = "error"
    COMPLETED = "completed"


@dataclass
class AgentContext:
    """Assembled context for each agent run (OpenClaw Stage 3: Context Assembly)"""
    soul: str = ""          # From SOUL.md
    agents: str = ""        # From AGENTS.md
    tools: str = ""         # From TOOLS.md
    memory: str = ""        # From MEMORY.md
    session_history: list = field(default_factory=list)
    shared_memory: dict = field(default_factory=dict)


@dataclass
class AgentResult:
    """Standardized output from every agent run"""
    agent_id: str
    status: str
    output: Any = None
    artifacts: list = field(default_factory=list)   # Files created
    metrics: dict = field(default_factory=dict)      # Performance metrics
    errors: list = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    duration_ms: int = 0
    tokens_used: int = 0


class BaseAgent(ABC):
    """
    Base Agent — implements the 7-stage Agentic Loop from OpenClaw:
    
    1. Input Normalization
    2. Routing & Session Serialization
    3. Context Assembly (SOUL + AGENTS + TOOLS + MEMORY)
    4. Model Inference
    5. ReAct Loop (Reason → Act → Observe)
    6. On-Demand Skill Loading
    7. Memory & Persistence
    """
    
    def __init__(self, agent_id: str, workspace_dir: str, llm_client=None):
        self.agent_id = agent_id
        self.workspace_dir = Path(workspace_dir)
        self.llm_client = llm_client
        self.status = AgentStatus.IDLE
        self.context = AgentContext()
        self.skills: dict[str, Any] = {}
        
        # Ensure workspace exists
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        (self.workspace_dir / "skills").mkdir(exist_ok=True)
        (self.workspace_dir / "memory").mkdir(exist_ok=True)
    
    # ========== Stage 3: Context Assembly ==========
    
    def _load_bootstrap_file(self, filename: str) -> str:
        """Load a markdown bootstrap file from the agent's workspace"""
        filepath = self.workspace_dir / filename
        if filepath.exists():
            return filepath.read_text(encoding="utf-8")
        return ""
    
    def assemble_context(self, input_data: Any = None) -> AgentContext:
        """
        Assemble the full context for this run.
        Reads SOUL.md, AGENTS.md, TOOLS.md, MEMORY.md
        """
        self.context = AgentContext(
            soul=self._load_bootstrap_file("SOUL.md"),
            agents=self._load_bootstrap_file("AGENTS.md"),
            tools=self._load_bootstrap_file("TOOLS.md"),
            memory=self._load_bootstrap_file("MEMORY.md"),
        )
        
        # Load shared memory if available
        shared_mem_path = self.workspace_dir.parent.parent / "shared" / "memory" / "shared_state.json"
        if shared_mem_path.exists():
            try:
                self.context.shared_memory = json.loads(
                    shared_mem_path.read_text(encoding="utf-8")
                )
            except (json.JSONDecodeError, OSError):
                pass
        
        return self.context
    
    def build_system_prompt(self) -> str:
        """Build the system prompt from assembled context"""
        parts = []
        
        if self.context.soul:
            parts.append(f"# Identity\n{self.context.soul}")
        if self.context.agents:
            parts.append(f"# Instructions\n{self.context.agents}")
        if self.context.tools:
            parts.append(f"# Available Tools\n{self.context.tools}")
        if self.context.memory:
            parts.append(f"# Memory\n{self.context.memory}")
        
        return "\n\n---\n\n".join(parts)
    
    # ========== Stage 5: ReAct Loop ==========
    
    @abstractmethod
    async def execute(self, input_data: Any = None) -> AgentResult:
        """
        Core execution logic — subclasses implement this.
        Should follow the ReAct pattern: Reason → Act → Observe
        """
        pass
    
    # ========== Stage 6: Skill Loading ==========
    
    def load_skill(self, skill_name: str):
        """Dynamically load a skill from the skills directory"""
        skill_dir = self.workspace_dir / "skills" / skill_name
        skill_file = skill_dir / "SKILL.md"
        if skill_file.exists():
            self.skills[skill_name] = skill_file.read_text(encoding="utf-8")
            return True
        return False
    
    # ========== Stage 7: Memory & Persistence ==========
    
    def save_to_memory(self, key: str, value: Any, memory_type: str = "working"):
        """Save data to agent's memory"""
        mem_dir = self.workspace_dir / "memory" / memory_type
        mem_dir.mkdir(parents=True, exist_ok=True)
        
        mem_file = mem_dir / f"{key}.json"
        data = {
            "key": key,
            "value": value,
            "timestamp": datetime.now().isoformat(),
            "agent_id": self.agent_id,
        }
        mem_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    
    def load_from_memory(self, key: str, memory_type: str = "working") -> Optional[Any]:
        """Load data from agent's memory"""
        mem_file = self.workspace_dir / "memory" / memory_type / f"{key}.json"
        if mem_file.exists():
            try:
                data = json.loads(mem_file.read_text(encoding="utf-8"))
                return data.get("value")
            except (json.JSONDecodeError, OSError):
                return None
        return None
    
    # ========== Full Run (All 7 Stages) ==========
    
    async def run(self, input_data: Any = None) -> AgentResult:
        """
        Execute the complete 7-stage agentic loop:
        1. Normalize input
        2. (Handled by Gateway)
        3. Assemble context
        4-5. Model inference + ReAct loop (in execute())
        6. Load skills on demand (in execute())
        7. Persist memory
        """
        start_time = time.time()
        self.status = AgentStatus.RUNNING
        
        try:
            # Stage 1: Normalize input
            normalized_input = self._normalize_input(input_data)
            
            # Stage 3: Context Assembly
            self.assemble_context(normalized_input)
            
            # Stage 4-6: Execute (subclass implements)
            result = await self.execute(normalized_input)
            
            # Stage 7: Persist
            self._persist_run_record(result)
            
            self.status = AgentStatus.COMPLETED
            result.duration_ms = int((time.time() - start_time) * 1000)
            return result
            
        except Exception as e:
            self.status = AgentStatus.ERROR
            return AgentResult(
                agent_id=self.agent_id,
                status="error",
                errors=[str(e)],
                duration_ms=int((time.time() - start_time) * 1000),
            )
    
    def _normalize_input(self, input_data: Any) -> Any:
        """Stage 1: Normalize input into standard format"""
        if input_data is None:
            return {}
        if isinstance(input_data, str):
            return {"message": input_data}
        return input_data
    
    def _persist_run_record(self, result: AgentResult):
        """Stage 7: Save run record for reflection"""
        records_dir = self.workspace_dir / "memory" / "run_records"
        records_dir.mkdir(parents=True, exist_ok=True)
        
        record_file = records_dir / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        record_file.write_text(
            json.dumps(asdict(result), ensure_ascii=False, default=str, indent=2),
            encoding="utf-8"
        )
