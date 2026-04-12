"""
Super Agent Orchestrator — Request Preprocessor & Parser
Replaces the simple keyword-matching smart_router with intelligent preprocessing.
Handles: intent classification, constraint extraction, complexity assessment,
entity recognition, and success criteria generation.
"""
import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
import structlog

from core.model_manager import model_manager

log = structlog.get_logger()


@dataclass
class TaskSpecification:
    """Structured output from the request preprocessor."""
    # Core
    original_message: str = ""
    intents: List[str] = field(default_factory=list)         # multi-label: coding, analysis, writing, research, etc
    primary_intent: str = "general"                          # main intent
    complexity_score: float = 0.0                            # 0.0-1.0 (0=trivial, 1=extremely complex)
    is_simple: bool = True                                   # True = skip orchestration
    requires_multi_agent: bool = False                       # True = needs decomposition

    # Constraints
    quality_priority: str = "balanced"                       # speed | balanced | quality
    max_cost_preference: str = "normal"                      # cheap | normal | expensive_ok
    urgency: str = "normal"                                  # immediate | normal | can_wait

    # Entities extracted
    entities: Dict[str, List[str]] = field(default_factory=dict)  # files, urls, models, etc
    mentioned_models: List[str] = field(default_factory=list)

    # Success Criteria
    success_criteria: List[str] = field(default_factory=list)

    # Metadata
    user_id: str = ""
    session_id: str = ""
    preprocessing_time_ms: int = 0
    raw_classification: Optional[Dict] = None

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


PREPROCESSOR_PROMPT = """You are the AI Orchestrator Request Preprocessor.
Analyze the user's request comprehensively and extract structured information.

You MUST output ONLY valid JSON in exactly this format:
{
    "intents": ["coding", "analysis"],
    "primary_intent": "coding",
    "complexity_score": 0.7,
    "requires_multi_agent": true,
    "quality_priority": "balanced",
    "urgency": "normal",
    "entities": {
        "languages": ["python"],
        "files": [],
        "urls": [],
        "tools": ["bash"]
    },
    "success_criteria": ["Working Python script that...", "Output formatted as..."],
    "reasoning": "This is a complex coding task because..."
}

Intent categories (can be MULTIPLE):
- coding: writing, debugging, refactoring code
- analysis: data analysis, reasoning, math, logic
- research: information gathering, web search, comparison
- writing: content creation, documentation, translation
- system: VPS management, terminal commands, server admin
- file_operation: file CRUD on local filesystem
- creative: brainstorming, design, ideation
- planning: strategy, scheduling, project management
- general: casual chat, greetings, simple questions

Complexity scoring guide:
- 0.0-0.2: trivial (greetings, yes/no questions)
- 0.2-0.4: simple (factual lookups, short translations)
- 0.4-0.6: moderate (writing tasks, single coding tasks)
- 0.6-0.8: complex (multi-step coding, deep analysis)
- 0.8-1.0: very complex (full project, multi-domain work)

requires_multi_agent = true ONLY IF:
- Complexity > 0.6 AND multiple intents
- Task explicitly requires different perspectives
- Task has multiple independent sub-deliverables

quality_priority options:
- speed: user wants fast response (use cheaper/faster models)
- balanced: normal balance (default)
- quality: user wants best possible answer (use premium models, ensemble)

urgency options:
- immediate: user is waiting, time-sensitive
- normal: standard request
- can_wait: batch processing, background task
"""


# Fast heuristic patterns to skip LLM classification entirely
LIGHT_PATTERNS = {
    "greetings": ["halo", "hai", "hi", "hello", "hey", "selamat pagi", "selamat siang",
                   "selamat sore", "selamat malam", "good morning", "good evening"],
    "acknowledgments": ["ok", "oke", "sip", "siap", "ya", "tidak", "terima kasih",
                         "makasih", "thanks", "thank you", "baik", "noted"],
    "tests": ["test", "tes", "ping", "p"],
}

COMPLEX_TRIGGERS = [
    "buat", "bikin", "install", "setup", "deploy", "analisa", "analyze",
    "bandingkan", "compare", "kode", "code", "sistem", "system", "vps",
    "server", "file", "tulis", "write", "riset", "research", "rencana",
    "plan", "desain", "design", "debug", "fix", "perbaiki", "optimasi",
    "optimize", "migrasi", "migrate", "refactor", "arsitektur", "architecture",
]


class RequestPreprocessor:
    """
    Intelligent request preprocessing pipeline.
    Replaces the keyword-based smart_router.
    """

    async def process(
        self,
        message: str,
        user_id: str = "",
        session_id: str = "",
        user_model_choice: Optional[str] = None,
    ) -> TaskSpecification:
        """
        Full preprocessing pipeline:
        1. Fast heuristic check (skip LLM for trivial messages)
        2. LLM-based deep analysis
        3. Post-processing & enrichment
        """
        start = time.time()
        spec = TaskSpecification(
            original_message=message,
            user_id=user_id,
            session_id=session_id,
        )

        # If user explicitly selected a model (not orchestrator), treat as simple
        if user_model_choice and "orchestrator" not in user_model_choice.lower():
            spec.is_simple = True
            spec.primary_intent = "general"
            spec.mentioned_models = [user_model_choice]
            spec.preprocessing_time_ms = int((time.time() - start) * 1000)
            return spec

        # Step 1: Fast heuristic check
        if self._is_trivial(message):
            spec.is_simple = True
            spec.primary_intent = "general"
            spec.complexity_score = 0.1
            spec.preprocessing_time_ms = int((time.time() - start) * 1000)
            log.debug("Preprocessor: trivial message detected", msg=message[:50])
            return spec

        # Step 2: LLM-based classification — with 6s timeout to prevent hangs
        try:
            import asyncio as _asyncio
            classification = await _asyncio.wait_for(
                self._classify_with_llm(message), timeout=6.0
            )
            spec.intents = classification.get("intents", ["general"])
            spec.primary_intent = classification.get("primary_intent", "general")
            spec.complexity_score = min(1.0, max(0.0, classification.get("complexity_score", 0.3)))
            spec.requires_multi_agent = classification.get("requires_multi_agent", False)
            spec.quality_priority = classification.get("quality_priority", "balanced")
            spec.urgency = classification.get("urgency", "normal")
            spec.entities = classification.get("entities", {})
            spec.success_criteria = classification.get("success_criteria", [])
            spec.raw_classification = classification

            # Determine if simple (skip orchestration overhead)
            spec.is_simple = spec.complexity_score < 0.4 and not spec.requires_multi_agent

        except _asyncio.TimeoutError:
            log.warning("Preprocessor LLM classification timed out (>6s), using fallback")
            spec = self._fallback_classify(message, spec)
        except Exception as e:
            log.warning("Preprocessor LLM classification failed, using fallback", error=str(e)[:100])
            spec = self._fallback_classify(message, spec)

        # Step 3: Post-processing
        spec = self._enrich(spec)

        spec.preprocessing_time_ms = int((time.time() - start) * 1000)
        log.info("Preprocessor complete",
                 intent=spec.primary_intent,
                 complexity=spec.complexity_score,
                 simple=spec.is_simple,
                 multi_agent=spec.requires_multi_agent,
                 time_ms=spec.preprocessing_time_ms)

        return spec

    def _is_trivial(self, message: str) -> bool:
        """Fast check: is this a trivial/light message that needs no analysis?"""
        msg = message.lower().strip()

        # Very short messages
        if len(msg) < 15:
            # Check against light patterns
            import string
            words = msg.translate(str.maketrans('', '', string.punctuation)).split()
            if not words:
                return True
            first_word = words[0]
            for category, patterns in LIGHT_PATTERNS.items():
                if first_word in patterns or msg in patterns:
                    return True

        # Short message with no complex triggers — raised 50→120 to avoid unnecessary LLM calls
        if len(msg) < 120 and not any(t in msg for t in COMPLEX_TRIGGERS):
            return True

        return False

    async def _classify_with_llm(self, message: str) -> Dict:
        """Use a fast LLM to classify the request."""
        fast_model = self._get_fast_model()
        messages = [
            {"role": "system", "content": PREPROCESSOR_PROMPT},
            {"role": "user", "content": f"User Request:\n{message}"},
        ]

        result_str = await model_manager.chat_completion(
            model=fast_model,
            messages=messages,
            temperature=0.1,
            max_tokens=500,
        )

        # Extract JSON
        if "```json" in result_str:
            result_str = result_str.split("```json")[1].split("```")[0].strip()
        elif "```" in result_str:
            result_str = result_str.split("```")[1].split("```")[0].strip()

        return json.loads(result_str)

    def _fallback_classify(self, message: str, spec: TaskSpecification) -> TaskSpecification:
        """Keyword-based fallback if LLM classification fails."""
        msg = message.lower()

        # Detect intents by keywords
        intent_keywords = {
            "coding": ["code", "kode", "python", "javascript", "debug", "class", "function",
                        "script", "api", "sql", "program", "bug", "error", "coding"],
            "analysis": ["analyze", "analisa", "compare", "bandingkan", "data", "statistik",
                          "insight", "logic", "math", "reason"],
            "research": ["cari", "search", "riset", "research", "info", "temukan", "find"],
            "writing": ["tulis", "write", "essay", "artikel", "report", "laporan", "email",
                         "translate", "terjemah"],
            "system": ["install", "sudo", "terminal", "server", "vps", "restart", "deploy",
                        "nginx", "systemctl", "docker"],
            "file_operation": ["file", "baca", "read", "edit", "hapus", "delete", "folder"],
            "creative": ["desain", "design", "gambar", "ide", "brainstorm", "kreatif"],
            "planning": ["rencana", "plan", "jadwal", "schedule", "strategy", "roadmap"],
        }

        detected_intents = []
        for intent, keywords in intent_keywords.items():
            if any(kw in msg for kw in keywords):
                detected_intents.append(intent)

        spec.intents = detected_intents or ["general"]
        spec.primary_intent = detected_intents[0] if detected_intents else "general"

        # Rough complexity estimate
        if len(message) > 300 or len(detected_intents) > 2:
            spec.complexity_score = 0.7
            spec.requires_multi_agent = True
        elif len(message) > 100 or len(detected_intents) > 1:
            spec.complexity_score = 0.5
        else:
            spec.complexity_score = 0.3

        spec.is_simple = spec.complexity_score < 0.4

        return spec

    def _enrich(self, spec: TaskSpecification) -> TaskSpecification:
        """Post-processing: enrich the specification with derived info."""
        # Set cost preference based on complexity
        if spec.complexity_score > 0.7:
            spec.max_cost_preference = "expensive_ok"
        elif spec.complexity_score < 0.3:
            spec.max_cost_preference = "cheap"

        # If system/file operation, enforce confirmation
        if spec.primary_intent in ("system", "file_operation"):
            spec.urgency = "immediate"  # user is watching

        return spec

    def _get_fast_model(self) -> str:
        """Pick the fastest available model for classification."""
        priorities = ["gpt-4o-mini", "claude-3-haiku", "gemini-1.5-flash",
                       "gemini-2.0-flash", "llama3.1"]
        for p in priorities:
            for k in model_manager.available_models.keys():
                if p in k:
                    return k
        return model_manager.get_default_model()


request_preprocessor = RequestPreprocessor()
