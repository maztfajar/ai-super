"""
Super Agent Orchestrator — Agent Registry
Defines agent types, their capabilities, and preferred models.
This replaces hardcoded agent logic with a structured registry.
"""
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
import structlog
import threading
import time as _time

log = structlog.get_logger()


@dataclass
class AgentCapability:
    """Defines what an agent type can do."""
    agent_type: str
    display_name: str
    description: str
    skills: List[str]                          # what this agent is good at
    preferred_models: List[str]                # ordered list of preferred model patterns
    tools_allowed: List[str] = field(default_factory=list)  # tool names this agent can use
    max_concurrent: int = 3                     # max parallel instances
    default_temperature: float = 0.7
    default_max_tokens: int = 4096
    system_prompt_addon: str = ""               # additional system prompt for this agent type


# ─── Agent Capability Registry ────────────────────────────────────────────────
AGENT_REGISTRY: Dict[str, AgentCapability] = {
    "reasoning": AgentCapability(
        agent_type="reasoning",
        display_name="🧠 Reasoning Agent",
        description="Complex logic, math, deep analysis, and strategic planning",
        skills=["logic", "math", "analysis", "planning", "strategy", "reasoning",
                "problem_solving", "critical_thinking"],
        preferred_models=["gpt-4o", "claude-3-5-sonnet", "claude-3-opus",
                           "gemini-1.5-pro", "seed-2-0-pro"],
        default_temperature=0.3,
        system_prompt_addon="Focus on logical reasoning. Show your thought process step by step. "
                            "Prioritize accuracy over speed.",
    ),
    "coding": AgentCapability(
        agent_type="coding",
        display_name="💻 Coding Agent",
        description="Software development, debugging, code review, and refactoring",
        skills=["python", "javascript", "typescript", "sql", "bash", "api",
                "debug", "refactor", "code_review", "testing"],
        preferred_models=["gpt-4o", "claude-3-5-sonnet", "seed-2-0-pro",
                           "gemini-1.5-pro"],
        tools_allowed=["execute_bash", "read_file", "write_file", "write_multiple_files"],
        default_temperature=0.2,
        default_max_tokens=8192,
        system_prompt_addon="Write clean, production-quality code. Include error handling. "
                            "Use type hints and docstrings.",
    ),
    "research": AgentCapability(
        agent_type="research",
        display_name="🔍 Research Agent",
        description="Information gathering, web search, data collection, and comparison",
        skills=["search", "gather", "compare", "summarize", "fact_check",
                "data_collection"],
        preferred_models=["gemini-1.5-pro", "gpt-4o", "claude-3-5-sonnet"],
        default_temperature=0.5,
        system_prompt_addon="Be thorough in your research. Cite sources when possible. "
                            "Present findings in a structured format.",
    ),
    "writing": AgentCapability(
        agent_type="writing",
        display_name="✍️ Writing Agent",
        description="Content creation, documentation, translation, and editing",
        skills=["writing", "editing", "translation", "documentation",
                "content_creation", "copywriting", "email"],
        preferred_models=["claude-3-5-sonnet", "gpt-4o", "gemini-1.5-pro"],
        default_temperature=0.7,
        system_prompt_addon="Write in clear, professional language. Match the requested tone and style. "
                            "Use proper formatting.",
    ),
    "system": AgentCapability(
        agent_type="system",
        display_name="🖥️ System Agent",
        description="VPS management, server admin, terminal commands, DevOps",
        skills=["bash", "linux", "docker", "nginx", "systemd", "networking",
                "monitoring", "deployment"],
        preferred_models=["gpt-4o", "claude-3-5-sonnet", "seed-2-0-pro"],
        tools_allowed=["execute_bash", "read_file", "write_file", "write_multiple_files"],
        default_temperature=0.2,
        system_prompt_addon="Prioritize safety. Always explain what a command does before executing. "
                            "Use sudo only when necessary.",
    ),
    "creative": AgentCapability(
        agent_type="creative",
        display_name="🎨 Creative Agent",
        description="Brainstorming, idea generation, design thinking, innovation",
        skills=["brainstorming", "ideation", "design", "creativity",
                "innovation", "storytelling"],
        preferred_models=["claude-3-5-sonnet", "gpt-4o", "gemini-1.5-pro"],
        default_temperature=0.9,
        system_prompt_addon="Think outside the box. Offer multiple creative options. "
                            "Encourage novel approaches.",
    ),
    "validation": AgentCapability(
        agent_type="validation",
        display_name="✅ Validation Agent",
        description="Quality assurance, testing, verification, fact-checking",
        skills=["testing", "verification", "qa", "fact_checking",
                "code_review", "proofreading"],
        preferred_models=["gpt-4o", "claude-3-5-sonnet", "gemini-1.5-pro"],
        default_temperature=0.1,
        system_prompt_addon="Be critical and thorough. Check for errors, inconsistencies, "
                            "and edge cases. Provide specific feedback.",
    ),
    "general": AgentCapability(
        agent_type="general",
        display_name="💬 General Agent",
        description="General conversation, FAQs, simple questions, greetings",
        skills=["conversation", "faq", "general_knowledge"],
        preferred_models=["gpt-4o-mini", "gemini-1.5-flash", "claude-3-haiku", "MiniMax-M2.7-highspeed"],
        default_temperature=0.7,
        system_prompt_addon="",
    ),
    "image_gen": AgentCapability(
        agent_type="image_gen",
        display_name="🖼️ Image Generation Agent",
        description="Generate images from text descriptions using vision/image models",
        skills=["image_gen", "vision", "creative", "design"],
        preferred_models=["mimo-v2-omni", "dall-e-3", "gpt-image-1", "flux"],
        default_temperature=0.7,
        default_max_tokens=1024,
        system_prompt_addon="You generate images. If the API supports it, use image generation. "
                            "Otherwise, provide a very detailed image description and suggest the user use an image gen tool.",
    ),
    "audio_gen": AgentCapability(
        agent_type="audio_gen",
        display_name="🔊 Audio/TTS Agent",
        description="Convert text to speech or generate audio using speech models",
        skills=["tts", "audio", "speech", "voice"],
        preferred_models=["minimax/speech-2.8-hd", "mimo-v2-omni"],
        default_temperature=0.5,
        default_max_tokens=512,
        system_prompt_addon="You are a Text-to-Speech assistant. Acknowledge the TTS request and confirm it will be processed.",
    ),
    "multimodal": AgentCapability(
        agent_type="multimodal",
        display_name="🌐 Multimodal Agent",
        description="Handle text, image, and audio inputs simultaneously",
        skills=["vision", "audio", "text", "analysis", "reasoning"],
        preferred_models=["mimo-v2-omni", "gpt-4o", "gemini-1.5-pro"],
        default_temperature=0.7,
        system_prompt_addon="You can process text, images, and audio. Handle multimodal inputs accurately.",
    ),
}


class AgentRegistryManager:
    """
    Manages the agent registry and provides lookup/matching functionality.
    Tracks real-time active agents for monitoring dashboard.
    """

    def __init__(self):
        self.registry = AGENT_REGISTRY
        # Real-time active agent tracking: {agent_type: {task_id: start_timestamp}}
        self._active_agents: Dict[str, Dict[str, float]] = {}
        self._lock = threading.Lock()
        # Lazy import to avoid circular imports
        self._model_manager = None

    @property
    def model_manager(self):
        if self._model_manager is None:
            from core.model_manager import model_manager as mm
            self._model_manager = mm
        return self._model_manager

    # ─── Real-time Status Tracking ──────────────────────────────────────────

    def mark_busy(self, agent_type: str, task_id: str) -> None:
        """Mark an agent type as actively working on a task."""
        with self._lock:
            if agent_type not in self._active_agents:
                self._active_agents[agent_type] = {}
            self._active_agents[agent_type][task_id] = _time.time()

    def mark_idle(self, agent_type: str, task_id: str) -> None:
        """Mark an agent task as finished."""
        with self._lock:
            if agent_type in self._active_agents:
                self._active_agents[agent_type].pop(task_id, None)
                if not self._active_agents[agent_type]:
                    del self._active_agents[agent_type]

    def get_active_agents(self) -> List[str]:
        """Return list of agent types currently working."""
        # Clean up stale entries (> 5 minutes old)
        now = _time.time()
        with self._lock:
            stale_agents = []
            for agent_type, tasks in self._active_agents.items():
                stale_tasks = [tid for tid, ts in tasks.items() if now - ts > 300]
                for tid in stale_tasks:
                    tasks.pop(tid)
                if not tasks:
                    stale_agents.append(agent_type)
            for agent_type in stale_agents:
                del self._active_agents[agent_type]
            return list(self._active_agents.keys())

    def get_agent(self, agent_type: str) -> Optional[AgentCapability]:
        """Get agent capability by type."""
        return self.registry.get(agent_type)

    def get_all_agents(self) -> Dict[str, AgentCapability]:
        """Get all registered agents."""
        return self.registry

    def find_agents_for_skill(self, skill: str) -> List[AgentCapability]:
        """Find all agents that have a particular skill."""
        return [
            agent for agent in self.registry.values()
            if skill.lower() in [s.lower() for s in agent.skills]
        ]

    def find_best_agent_type(self, task_type: str, required_skills: List[str] = None) -> str:
        """
        Find the best agent type for a given task type and required skills.
        Returns the agent_type string.
        """
        # Direct match
        if task_type in self.registry:
            return task_type

        # Skill-based matching
        if required_skills:
            best_match = None
            best_score = 0
            for agent_type, agent in self.registry.items():
                agent_skills = set(s.lower() for s in agent.skills)
                req_skills = set(s.lower() for s in required_skills)
                overlap = len(agent_skills & req_skills)
                if overlap > best_score:
                    best_score = overlap
                    best_match = agent_type
            if best_match:
                return best_match

        return "general"

    def resolve_model_for_agent(self, agent_type: str,
                                 user_preferred: Optional[str] = None) -> str:
        """
        Resolve the actual model ID to use for a given agent type.
        Priority: user preference > capability map > agent preferred list > any available.
        """
        mm = self.model_manager

        # User explicitly chose a model
        if user_preferred and user_preferred in mm.available_models:
            return user_preferred

        agent = self.registry.get(agent_type)
        if not agent:
            return mm.get_default_model()

        # Try capability map first for specialized agents
        try:
            from core.capability_map import capability_map
            if agent_type in ("image_gen", "audio_gen", "multimodal"):
                capability_tag = {
                    "image_gen": "image_gen",
                    "audio_gen": "tts",
                    "multimodal": "vision",
                }.get(agent_type, "text")
                best = capability_map.find_best_model({capability_tag})
                if best and best in mm.available_models:
                    return best
        except Exception:
            pass

        # Try preferred models in order
        available = set(mm.available_models.keys())
        for preferred in agent.preferred_models:
            # Pattern match (e.g., "gpt-4o" matches "gpt-4o" or "sumopod/gpt-4o")
            for model_id in available:
                if preferred in model_id:
                    return model_id

        # Fallback to any available model
        return mm.get_default_model()

    def get_agent_system_prompt(self, agent_type: str, base_prompt: str = "") -> str:
        """Build a complete system prompt for an agent, combining base + agent-specific."""
        agent = self.registry.get(agent_type)
        if not agent:
            return base_prompt

        addon = agent.system_prompt_addon
        if addon and base_prompt:
            return f"{base_prompt}\n\n[Agent Role: {agent.display_name}] {addon}"
        elif addon:
            return addon
        return base_prompt

    def list_for_api(self) -> List[Dict]:
        """Return registry data suitable for API response."""
        return [
            {
                "type": agent.agent_type,
                "name": agent.display_name,
                "description": agent.description,
                "skills": agent.skills,
                "tools": agent.tools_allowed,
            }
            for agent in self.registry.values()
        ]


agent_registry = AgentRegistryManager()
