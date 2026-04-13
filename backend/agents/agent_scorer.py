"""
Super Agent Orchestrator — Agent Scorer
Multi-criteria agent selection using dynamic scoring.
Score = (Capability Match × 0.4) + (Historical Performance × 0.3) +
        (Specialization × 0.2) + (Availability × 0.1)
"""
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import structlog

from core.model_manager import model_manager
from core.metrics import metrics_engine
from agents.agent_registry import agent_registry, AgentCapability
from core.dag_builder import SubTask

log = structlog.get_logger()


@dataclass
class AgentScore:
    """Score breakdown for a model/agent combination."""
    model_id: str
    agent_type: str
    capability_score: float = 0.0        # 0-1: how well the model matches required skills
    historical_score: float = 0.0        # 0-1: past performance on similar tasks
    specialization_score: float = 0.0    # 0-1: how specialized this agent is for this task
    availability_score: float = 0.0      # 0-1: current load/availability
    capability_map_score: float = 0.0    # 0-1: score from CapabilityMap discovery
    total_score: float = 0.0             # weighted combination
    reasoning: str = ""

    def compute_total(self,
                      w_capability: float = 0.35,
                      w_cap_map: float = 0.25,
                      w_historical: float = 0.22,
                      w_specialization: float = 0.13,
                      w_availability: float = 0.05) -> float:
        """Compute weighted total score."""
        self.total_score = (
            self.capability_score * w_capability +
            self.capability_map_score * w_cap_map +
            self.historical_score * w_historical +
            self.specialization_score * w_specialization +
            self.availability_score * w_availability
        )
        return self.total_score


# Track active model executions for availability scoring
_active_executions: Dict[str, int] = {}


class AgentScorer:
    """
    Scores and selects the best model/agent combination for each subtask.
    Implements the dynamic scoring algorithm from Section 3.2 of the plan.
    """

    def score_model(self, model_id: str, subtask: SubTask,
                     agent_cap: AgentCapability) -> AgentScore:
        """
        Score a specific model for a specific subtask.
        """
        score = AgentScore(model_id=model_id, agent_type=agent_cap.agent_type)

        # 1. Capability Match from registry (0.35)
        score.capability_score = self._compute_capability(model_id, subtask, agent_cap)

        # 2. Capability Map Score from discovery engine (0.25)
        score.capability_map_score = self._compute_capability_map_score(
            model_id, agent_cap, subtask
        )

        # 3. Historical Performance (0.22)
        score.historical_score = metrics_engine.get_model_score(
            model_id, subtask.task_type
        )

        # 4. Specialization (0.13)
        score.specialization_score = self._compute_specialization(model_id, agent_cap)

        # 5. Availability (0.05)
        score.availability_score = self._compute_availability(model_id, agent_cap)

        score.compute_total()

        score.reasoning = (
            f"cap={score.capability_score:.2f} "
            f"cap_map={score.capability_map_score:.2f} "
            f"hist={score.historical_score:.2f} "
            f"spec={score.specialization_score:.2f} "
            f"avail={score.availability_score:.2f} "
            f"-> total={score.total_score:.3f}"
        )

        return score

    def select_best_model(self, subtask: SubTask,
                           quality_priority: str = "balanced") -> Tuple[str, str, AgentScore]:
        """
        Select the best model and agent type for a subtask.
        Returns (model_id, agent_type, score).
        """
        # Determine the best agent type for this subtask
        agent_type = agent_registry.find_best_agent_type(
            subtask.task_type, subtask.required_skills
        )
        agent_cap = agent_registry.get_agent(agent_type)
        if not agent_cap:
            agent_cap = agent_registry.get_agent("general")
            agent_type = "general"

        # Score all available models
        candidates: List[AgentScore] = []
        for model_id in model_manager.available_models:
            score = self.score_model(model_id, subtask, agent_cap)
            candidates.append(score)

        if not candidates:
            default = model_manager.get_default_model()
            return default, agent_type, AgentScore(model_id=default, agent_type=agent_type)

        # Apply quality priority modifiers
        if quality_priority == "speed":
            # Boost cheaper/faster models
            for c in candidates:
                if any(fast in c.model_id for fast in ["mini", "flash", "haiku", "small"]):
                    c.total_score *= 1.3
        elif quality_priority == "quality":
            # Boost premium models
            for c in candidates:
                if any(prem in c.model_id for prem in ["gpt-4o", "claude-3-5-sonnet",
                                                        "claude-3-opus", "pro"]):
                    c.total_score *= 1.3

        # Sort by total score
        candidates.sort(key=lambda c: c.total_score, reverse=True)
        best = candidates[0]

        log.debug("Agent scored",
                  task=subtask.id,
                  type=agent_type,
                  model=best.model_id,
                  score=f"{best.total_score:.3f}",
                  reasoning=best.reasoning)

        return best.model_id, agent_type, best

    def assign_all(self, subtasks: List[SubTask],
                    quality_priority: str = "balanced") -> List[SubTask]:
        """
        Assign the best model and agent type to ALL subtasks.
        Considers load balancing across assignments.
        """
        for st in subtasks:
            model_id, agent_type, score = self.select_best_model(st, quality_priority)
            st.assigned_model = model_id
            st.assigned_agent = agent_type
            # Track active executions for future availability scoring
            _active_executions[model_id] = _active_executions.get(model_id, 0) + 1

        return subtasks

    def release_model(self, model_id: str):
        """Mark a model as no longer actively executing (for availability scoring)."""
        if model_id in _active_executions:
            _active_executions[model_id] = max(0, _active_executions[model_id] - 1)

    # ─── Scoring Sub-functions ────────────────────────────────

    def _compute_capability(self, model_id: str, subtask: SubTask,
                             agent_cap: AgentCapability) -> float:
        """
        How well does this model match the required capabilities?
        Based on: is the model in the agent's preferred list + skill overlap.
        """
        # Check if model is in preferred list
        position_score = 0.0
        for idx, preferred in enumerate(agent_cap.preferred_models):
            if preferred in model_id:
                # Higher score for earlier positions in preferred list
                position_score = 1.0 - (idx * 0.15)
                break

        # Skill overlap
        if subtask.required_skills:
            agent_skills = set(s.lower() for s in agent_cap.skills)
            req_skills = set(s.lower() for s in subtask.required_skills)
            if req_skills:
                overlap = len(agent_skills & req_skills) / len(req_skills)
            else:
                overlap = 0.5
        else:
            overlap = 0.5

        return min(1.0, (position_score * 0.6 + overlap * 0.4))

    def _compute_specialization(self, model_id: str,
                                  agent_cap: AgentCapability) -> float:
        """
        How specialized is the agent for this type of task?
        Specialized agents score higher than general ones.
        """
        if agent_cap.agent_type == "general":
            return 0.3  # general agents get lower specialization score

        # Check if model is the top preferred for this agent
        if agent_cap.preferred_models:
            if any(agent_cap.preferred_models[0] in model_id for _ in [1]):
                return 1.0  # top preferred model for this specialized agent
            if any(p in model_id for p in agent_cap.preferred_models[:3]):
                return 0.7

        return 0.5

    def _compute_availability(self, model_id: str,
                                agent_cap: AgentCapability) -> float:
        """
        Current availability of the model.
        Models with fewer active executions score higher.
        """
        active = _active_executions.get(model_id, 0)
        max_concurrent = agent_cap.max_concurrent

        if active >= max_concurrent:
            return 0.1  # nearly saturated
        elif active == 0:
            return 1.0  # fully available
        else:
            return 1.0 - (active / max_concurrent) * 0.8

    def _compute_capability_map_score(self, model_id: str,
                                       agent_cap: AgentCapability,
                                       subtask: SubTask) -> float:
        """
        Score based on discovered capability tags from CapabilityMapEngine.
        Returns 1.0 if model has all required caps, 0.0 if incompatible.
        """
        try:
            from core.capability_map import capability_map
            model_caps = capability_map.get_capabilities(model_id)
            if not model_caps:
                return 0.5  # unknown model, neutral score

            # Map agent type to required capability tags
            AGENT_TO_CAPS = {
                "image_gen":   {"image_gen"},
                "audio_gen":   {"tts", "audio"},
                "multimodal":  {"vision"},
                "vision":      {"vision"},
                "coding":      {"coding"},
                "reasoning":   {"reasoning"},
                "analysis":    {"analysis", "reasoning"},
                "writing":     {"writing", "text"},
                "research":    {"text"},
                "system":      {"text"},
                "creative":    {"text", "writing"},
                "general":     {"text"},
            }

            required = AGENT_TO_CAPS.get(agent_cap.agent_type, {"text"})

            # Hard block: if required cap is not available at all, score is 0
            if agent_cap.agent_type in ("image_gen", "audio_gen"):
                if not (required & model_caps):
                    return 0.0  # Hard block — this model cannot do this task

            overlap = len(required & model_caps)
            if not required:
                return 0.5
            return min(1.0, overlap / len(required))

        except Exception:
            return 0.5  # neutral fallback if capability_map unavailable


agent_scorer = AgentScorer()
