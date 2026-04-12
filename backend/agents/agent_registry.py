"""
Super Agent Orchestrator — Agent Registry
Defines agent types, their capabilities, and preferred models.
This replaces hardcoded agent logic with a structured registry.
"""
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
import structlog

from core.model_manager import model_manager

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
        tools_allowed=["execute_bash", "read_file", "write_file"],
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
        tools_allowed=["execute_bash", "read_file", "write_file"],
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
        preferred_models=["gpt-4o-mini", "gemini-1.5-flash", "claude-3-haiku"],
        default_temperature=0.7,
        system_prompt_addon="",
    ),
}


class AgentRegistryManager:
    """
    Manages the agent registry and provides lookup/matching functionality.
    """

    def __init__(self):
        self.registry = AGENT_REGISTRY

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
        Priority: user preference > agent preferred list > any available.
        """
        # User explicitly chose a model
        if user_preferred and user_preferred in model_manager.available_models:
            return user_preferred

        agent = self.registry.get(agent_type)
        if not agent:
            return model_manager.get_default_model()

        # Try preferred models in order
        available = set(model_manager.available_models.keys())
        for preferred in agent.preferred_models:
            # Pattern match (e.g., "gpt-4o" matches "gpt-4o" or "sumopod/gpt-4o")
            for model_id in available:
                if preferred in model_id:
                    return model_id

        # Fallback to any available model
        return model_manager.get_default_model()

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
