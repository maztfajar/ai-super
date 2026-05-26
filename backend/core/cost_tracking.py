"""
Cost Tracking Engine — Track AI usage costs dan token consumption.
Prevents unexpected bills dengan budget limits dan alerts.
"""
import time
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from enum import Enum
import structlog

log = structlog.get_logger()


# Pricing per 1K tokens — sesuai AI Core v2 pricing reference
# Sumber: AI ORCHESTRATOR CORE ENGINE v2.0 — Section PRICING REFERENCE v2
TOKEN_PRICING = {
    # [THE RUNNER] + [VISION_GATE] — gemini/gemini-2.5-flash
    "gemini/gemini-2.5-flash":       {"input": 0.00030, "output": 0.0025},
    "gemini-2.5-flash":              {"input": 0.00030, "output": 0.0025},  # alias

    # [THE THINKER] + [THE WRITER] primary — qwen3.6-plus
    "qwen3.6-plus":                  {"input": 0.00025, "output": 0.00150},

    # [BRAIN] + [ARCHITECT] — deepseek-v4-pro
    # *Promo 75% off s/d 31 Mei 2026. Normal: $1.74/$3.48 per 1M token
    "deepseek-v4-pro":               {"input": 0.00043, "output": 0.00087},

    # [THE WRITER] + [THE CREATIVE] fallback — claude-haiku-4-5
    "claude-haiku-4-5":              {"input": 0.00070, "output": 0.0035},

    # [THE EAR] — minimax/speech-2.8-hd (per-menit, bukan token)
    "minimax/speech-2.8-hd":         {"input": 0.0, "output": 0.0},   # billed per-minute

    # [EMERGENCY] last resort — gpt-5-mini
    "gpt-5-mini":                    {"input": 0.00025, "output": 0.0020},
}


import os
import json

def load_pricing_overrides():
    """Load pricing overrides from data/pricing_overrides.json if exists, else create default."""
    overrides_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
    overrides_path = os.path.join(overrides_dir, "pricing_overrides.json")
    
    default_overrides = {
        "sumopod/qwen3.6-flash": {"input": 0.00013, "output": 0.00075},
        "sumopod/qwen3.6-plus": {"input": 0.00025, "output": 0.00150},
        "sumopod/claude-haiku-4-5": {"input": 0.00070, "output": 0.00350},
        "sumopod/claude-opus-4-6": {"input": 0.00500, "output": 0.02500},
        "sumopod/claude-opus-4-7": {"input": 0.00500, "output": 0.02500},
        "sumopod/claude-sonnet-4-6": {"input": 0.00300, "output": 0.01500},
        "sumopod/deepseek-v3-2": {"input": 0.00028, "output": 0.00042},
        "sumopod/glm-4-7": {"input": 0.00060, "output": 0.00220},
        "sumopod/seed-2-0-code": {"input": 0.00050, "output": 0.00300},
        "sumopod/seed-2-0-lite": {"input": 0.00025, "output": 0.00200},
        "sumopod/seed-2-0-mini": {"input": 0.00010, "output": 0.00040},
        "sumopod/seed-2-0-pro": {"input": 0.00050, "output": 0.00300},
        "sumopod/deepseek-v4-flash": {"input": 0.00014, "output": 0.00028},
        "sumopod/deepseek-v4-pro": {"input": 0.00043, "output": 0.00087},
        "sumopod/gemini/gemini-2.5-flash": {"input": 0.00030, "output": 0.00250},
        "sumopod/gemini/gemini-2.5-flash-lite": {"input": 0.00010, "output": 0.00040},
        "sumopod/gemini/gemini-2.5-pro": {"input": 0.00125, "output": 0.01000},
        "sumopod/gemini/gemini-3-flash-preview": {"input": 0.00050, "output": 0.00300},
        "sumopod/gemini/gemini-3.1-flash-lite-preview": {"input": 0.00025, "output": 0.00150},
        "sumopod/gemini/gemini-3.1-pro-preview": {"input": 0.00200, "output": 0.01200},
        "sumopod/gemini/gemini-2.0-flash": {"input": 0.00010, "output": 0.00040},
        "sumopod/gemini/gemini-2.0-flash-lite": {"input": 0.00007, "output": 0.00030},
        "sumopod/mimo-v2-flash": {"input": 0.00010, "output": 0.00030},
        "sumopod/mimo-v2-omni": {"input": 0.00012, "output": 0.00060},
        "sumopod/mimo-v2-pro": {"input": 0.00030, "output": 0.00090},
        "sumopod/mimo-v2.5": {"input": 0.00012, "output": 0.00060},
        "sumopod/mimo-v2.5-pro": {"input": 0.00030, "output": 0.00090},
        "sumopod/MiniMax-M2.7-highspeed": {"input": 0.00002, "output": 0.00006},
        "sumopod/kimi-k2.6": {"input": 0.00008, "output": 0.00035},
        "sumopod/gpt-4.1": {"input": 0.00200, "output": 0.00800},
        "sumopod/gpt-4.1-mini": {"input": 0.00040, "output": 0.00160},
        "sumopod/gpt-4.1-nano": {"input": 0.00010, "output": 0.00040},
        "sumopod/gpt-4o": {"input": 0.00250, "output": 0.01000},
        "sumopod/gpt-4o-mini": {"input": 0.00015, "output": 0.00060},
        "sumopod/gpt-5": {"input": 0.00125, "output": 0.01000},
        "sumopod/gpt-5-mini": {"input": 0.00025, "output": 0.00200},
        "sumopod/gpt-5-nano": {"input": 0.00005, "output": 0.00040},
        "sumopod/gpt-5.1": {"input": 0.00125, "output": 0.01000},
        "sumopod/gpt-5.1-codex": {"input": 0.00125, "output": 0.01000},
        "sumopod/gpt-5.1-codex-mini": {"input": 0.00025, "output": 0.00200},
        "sumopod/gpt-5.2": {"input": 0.00175, "output": 0.01400},
        "sumopod/gpt-5.2-codex": {"input": 0.00175, "output": 0.01400},
        "sumopod/gpt-5.3-codex": {"input": 0.00175, "output": 0.01400},
        "sumopod/gpt-5.4": {"input": 0.00250, "output": 0.01500},
        "sumopod/gpt-5.4-mini": {"input": 0.00075, "output": 0.00450},
        "sumopod/gpt-5.4-nano": {"input": 0.00020, "output": 0.00125},
        "sumopod/text-embedding-3-large": {"input": 0.00013, "output": 0.00000},
        "sumopod/text-embedding-3-small": {"input": 0.00002, "output": 0.00000},
        "sumopod/gemma-4-31b-it": {"input": 0.00012, "output": 0.00037},
        "sumopod/qwen3.6-27b": {"input": 0.00032, "output": 0.00320},
        "sumopod/glm-5": {"input": 0.00010, "output": 0.00032},
        "sumopod/glm-5-turbo": {"input": 0.00010, "output": 0.00032},
        "sumopod/glm-5.1": {"input": 0.00010, "output": 0.00032},
    }
    
    if not os.path.exists(overrides_dir):
        try:
            os.makedirs(overrides_dir, exist_ok=True)
        except Exception:
            pass
            
    if os.path.exists(overrides_path):
        try:
            with open(overrides_path, "r") as f:
                custom_data = json.load(f)
                if isinstance(custom_data, dict):
                    # Validate and merge
                    for k, v in custom_data.items():
                        if isinstance(v, dict) and "input" in v and "output" in v:
                            TOKEN_PRICING[k] = {
                                "input": float(v["input"]),
                                "output": float(v["output"])
                            }
                    log.info(f"Loaded {len(custom_data)} pricing overrides from {overrides_path}")
                    return
        except Exception as e:
            log.warning("Failed to load pricing_overrides.json", error=str(e))
            
    # Create default file if it doesn't exist or failed to load
    try:
        with open(overrides_path, "w") as f:
            json.dump(default_overrides, f, indent=2)
        log.info(f"Created default pricing overrides at {overrides_path}")
    except Exception as e:
        log.warning("Failed to save default pricing_overrides.json", error=str(e))
        
    # Apply default overrides to TOKEN_PRICING
    for k, v in default_overrides.items():
        TOKEN_PRICING[k] = v

# Run on startup to load custom/default pricing overrides
load_pricing_overrides()


def get_pricing(model_id: str) -> dict:
    """Helper to resolve pricing for a model_id, stripping provider prefixes and using robust fallbacks."""
    if not model_id:
        return {"input": 0.00030, "output": 0.0020}  # default fallback

    # Strip provider prefixes
    clean_id = model_id
    for prefix in ("sumopod/", "ollama/", "openai/", "anthropic/", "google/", "custom/"):
        if clean_id.startswith(prefix):
            clean_id = clean_id[len(prefix):]
            break

    # Exact match in TOKEN_PRICING
    if clean_id in TOKEN_PRICING:
        return TOKEN_PRICING[clean_id]
    if model_id in TOKEN_PRICING:
        return TOKEN_PRICING[model_id]

    # Partial match/substring
    for key, price in TOKEN_PRICING.items():
        if key in clean_id or clean_id in key:
            return price

    # General keywords-based fallback
    model_lower = clean_id.lower()
    if "flash" in model_lower:
        return TOKEN_PRICING["gemini-2.5-flash"]
    if "deepseek" in model_lower or "reasoning" in model_lower or "pro" in model_lower:
        return TOKEN_PRICING["deepseek-v4-pro"]
    if "mini" in model_lower or "haiku" in model_lower:
        return TOKEN_PRICING["gpt-5-mini"]

    # Final fallback
    return {"input": 0.00030, "output": 0.0020}


@dataclass
class TokenUsage:
    """Token usage per request."""
    request_id: str
    model_id: str
    input_tokens: int = 0
    output_tokens: int = 0
    
    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens
    
    @property
    def input_cost(self) -> float:
        """Calculate input cost in USD."""
        pricing = get_pricing(self.model_id)
        return (self.input_tokens / 1000) * pricing["input"]
    
    @property
    def output_cost(self) -> float:
        """Calculate output cost in USD."""
        pricing = get_pricing(self.model_id)
        return (self.output_tokens / 1000) * pricing["output"]
    
    @property
    def total_cost(self) -> float:
        """Total cost for this usage."""
        return self.input_cost + self.output_cost
    
    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "model_id": self.model_id,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "input_cost_usd": round(self.input_cost, 6),
            "output_cost_usd": round(self.output_cost, 6),
            "total_cost_usd": round(self.total_cost, 6),
        }


@dataclass
class CostRecord:
    """Record satu execution dengan cost breakdown."""
    task_id: str
    user_id: str
    session_id: str
    timestamp: float = field(default_factory=time.time)
    
    # Task details
    task_type: str = ""
    agent_type: str = ""
    
    # Token tracking
    token_usages: List[TokenUsage] = field(default_factory=list)
    
    # Execution time
    execution_time_ms: int = 0
    
    # Status
    success: bool = True
    error_message: Optional[str] = None
    
    @property
    def total_cost_usd(self) -> float:
        """Sum of all token costs."""
        return sum(usage.total_cost for usage in self.token_usages)
    
    @property
    def total_tokens(self) -> int:
        """Sum of all tokens."""
        return sum(usage.total_tokens for usage in self.token_usages)
    
    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "task_type": self.task_type,
            "agent_type": self.agent_type,
            "total_tokens": self.total_tokens,
            "total_cost_usd": round(self.total_cost_usd, 6),
            "execution_time_ms": self.execution_time_ms,
            "success": self.success,
            "token_breakdown": [u.to_dict() for u in self.token_usages],
        }


@dataclass
class CostBudget:
    """User cost budget."""
    user_id: str
    monthly_limit_usd: float
    monthly_used_usd: float = 0.0
    month_start: float = field(default_factory=lambda: time.time())
    alerts_sent: List[str] = field(default_factory=list)  # Alert thresholds sent (e.g., "50%", "90%")
    
    def is_exceeded(self) -> bool:
        """Check if budget exceeded."""
        return self.monthly_used_usd > self.monthly_limit_usd
    
    def utilization_percent(self) -> float:
        """What % of budget used."""
        if self.monthly_limit_usd == 0:
            return 0.0
        return (self.monthly_used_usd / self.monthly_limit_usd) * 100
    
    def remaining_usd(self) -> float:
        """How much budget remaining."""
        return max(0.0, self.monthly_limit_usd - self.monthly_used_usd)
    
    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "monthly_limit_usd": round(self.monthly_limit_usd, 2),
            "monthly_used_usd": round(self.monthly_used_usd, 2),
            "remaining_usd": round(self.remaining_usd(), 2),
            "utilization_percent": round(self.utilization_percent(), 2),
            "alerts_sent": self.alerts_sent,
        }


class CostTrackingEngine:
    """
    Tracks & manages AI usage costs.
    Prevents runaway costs dengan budgets & alerts.
    """
    
    def __init__(self):
        # Cost records: task_id -> CostRecord
        self._records: Dict[str, CostRecord] = {}
        
        # User budgets: user_id -> CostBudget
        self._budgets: Dict[str, CostBudget] = {}
        
        # History for reporting
        self._history: List[CostRecord] = []
        self._max_history = 5000

    def create_cost_record(
        self,
        task_id: str,
        user_id: str,
        session_id: str,
        task_type: str = "",
        agent_type: str = "",
    ) -> CostRecord:
        """Create new cost record untuk task."""
        record = CostRecord(
            task_id=task_id,
            user_id=user_id,
            session_id=session_id,
            task_type=task_type,
            agent_type=agent_type,
        )
        self._records[task_id] = record
        return record

    def add_token_usage(
        self,
        task_id: str,
        model_id: str,
        input_tokens: int,
        output_tokens: int,
    ) -> Optional[TokenUsage]:
        """Add token usage ke cost record."""
        if task_id not in self._records:
            log.warning("Cost record not found", task_id=task_id)
            return None
        
        usage = TokenUsage(
            request_id=task_id,
            model_id=model_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
        
        self._records[task_id].token_usages.append(usage)
        
        # Check budget
        record = self._records[task_id]
        self._check_budget(record.user_id, record.total_cost_usd)
        
        log.info(
            "Token usage recorded",
            task_id=task_id,
            model=model_id,
            tokens=usage.total_tokens,
            cost_usd=round(usage.total_cost, 6),
        )
        
        return usage

    def finalize_record(
        self,
        task_id: str,
        execution_time_ms: int,
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> Optional[CostRecord]:
        """Finalize cost record setelah task selesai."""
        if task_id not in self._records:
            return None
        
        record = self._records[task_id]
        record.execution_time_ms = execution_time_ms
        record.success = success
        record.error_message = error_message
        
        # Move to history
        del self._records[task_id]
        self._history.append(record)
        if len(self._history) > self._max_history:
            self._history.pop(0)
        
        log.info(
            "Cost record finalized",
            task_id=task_id,
            total_cost_usd=round(record.total_cost_usd, 6),
            tokens=record.total_tokens,
            time_ms=execution_time_ms,
        )
        
        return record

    def set_user_budget(self, user_id: str, monthly_limit_usd: float):
        """Set monthly budget untuk user."""
        self._budgets[user_id] = CostBudget(
            user_id=user_id,
            monthly_limit_usd=monthly_limit_usd,
        )
        log.info("User budget set", user_id=user_id, limit_usd=monthly_limit_usd)

    def get_user_budget(self, user_id: str) -> Optional[CostBudget]:
        """Get user budget."""
        if user_id not in self._budgets:
            # Default: $10/month
            self.set_user_budget(user_id, 10.0)
        
        return self._budgets[user_id]

    def _check_budget(self, user_id: str, added_cost: float):
        """Check if user exceeded budget."""
        budget = self.get_user_budget(user_id)
        if not budget:
            return
        
        budget.monthly_used_usd += added_cost
        utilization = budget.utilization_percent()
        
        # Send alerts at threshold
        thresholds = [50, 80, 90, 100]
        for threshold in thresholds:
            if utilization >= threshold and str(threshold) not in budget.alerts_sent:
                budget.alerts_sent.append(str(threshold))
                log.warning(
                    "Budget alert",
                    user_id=user_id,
                    utilization_percent=utilization,
                    used_usd=round(budget.monthly_used_usd, 2),
                    limit_usd=budget.monthly_limit_usd,
                )
        
        if budget.is_exceeded():
            log.error(
                "Budget exceeded!",
                user_id=user_id,
                used_usd=round(budget.monthly_used_usd, 2),
                limit_usd=budget.monthly_limit_usd,
            )

    def get_user_stats(self, user_id: str, days: int = 30) -> dict:
        """Get cost stats untuk user dalam N hari terakhir."""
        cutoff_time = time.time() - (days * 86400)
        
        relevant_records = [
            r for r in self._history
            if r.user_id == user_id and r.timestamp >= cutoff_time
        ]
        
        total_cost = sum(r.total_cost_usd for r in relevant_records)
        total_tokens = sum(r.total_tokens for r in relevant_records)
        successful = sum(1 for r in relevant_records if r.success)
        failed = len(relevant_records) - successful
        
        # Group by agent
        agent_stats = {}
        for record in relevant_records:
            agent = record.agent_type or "unknown"
            if agent not in agent_stats:
                agent_stats[agent] = {"cost": 0.0, "tokens": 0, "count": 0}
            agent_stats[agent]["cost"] += record.total_cost_usd
            agent_stats[agent]["tokens"] += record.total_tokens
            agent_stats[agent]["count"] += 1
        
        return {
            "user_id": user_id,
            "period_days": days,
            "total_cost_usd": round(total_cost, 2),
            "total_tokens": total_tokens,
            "total_requests": len(relevant_records),
            "successful_requests": successful,
            "failed_requests": failed,
            "avg_cost_per_request": round(total_cost / len(relevant_records), 4) if relevant_records else 0.0,
            "agent_breakdown": {
                agent: {
                    "cost_usd": round(stats["cost"], 2),
                    "tokens": stats["tokens"],
                    "requests": stats["count"],
                    "avg_cost": round(stats["cost"] / stats["count"], 4),
                }
                for agent, stats in agent_stats.items()
            },
            "budget": self.get_user_budget(user_id).to_dict(),
        }

    def estimate_cost(self, model_id: str, estimated_input_tokens: int, estimated_output_tokens: int) -> float:
        """Estimate cost untuk request sebelum execute."""
        if model_id not in TOKEN_PRICING:
            return 0.0
        
        pricing = TOKEN_PRICING[model_id]
        input_cost = (estimated_input_tokens / 1000) * pricing["input"]
        output_cost = (estimated_output_tokens / 1000) * pricing["output"]
        
        return input_cost + output_cost

    def get_history(self, user_id: Optional[str] = None, limit: int = 100) -> List[dict]:
        """Get cost history."""
        records = self._history
        if user_id:
            records = [r for r in records if r.user_id == user_id]
        
        return [r.to_dict() for r in records[-limit:]]


# Global singleton
cost_engine = CostTrackingEngine()
