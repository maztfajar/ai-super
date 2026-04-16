"""
Audit Logging System — Comprehensive logging untuk compliance & security.
Tracks semua agent decisions, operations, approvals.
"""
import json
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import structlog

log = structlog.get_logger()

# Path untuk audit logs
AUDIT_LOG_DIR = Path(__file__).parent.parent.parent / "data" / "audit_logs"


class AuditEventType(Enum):
    """Jenis audit events."""
    REQUEST_STARTED = "request_started"
    REQUEST_COMPLETED = "request_completed"
    REQUEST_FAILED = "request_failed"
    
    AGENT_ASSIGNED = "agent_assigned"
    AGENT_EXECUTED = "agent_executed"
    AGENT_FAILED = "agent_failed"
    
    TOOL_CALLED = "tool_called"
    TOOL_EXECUTED = "tool_executed"
    TOOL_FAILED = "tool_failed"
    
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_GRANTED = "approval_granted"
    APPROVAL_REJECTED = "approval_rejected"
    
    COST_ALERT = "cost_alert"
    BUDGET_EXCEEDED = "budget_exceeded"
    
    ERROR_RECOVERY = "error_recovery"
    CIRCUIT_BREAKER_OPENED = "circuit_breaker_opened"
    CIRCUIT_BREAKER_CLOSED = "circuit_breaker_closed"


@dataclass
class AuditEvent:
    """Single audit event."""
    event_type: AuditEventType
    timestamp: float = field(default_factory=time.time)
    user_id: str = ""
    session_id: str = ""
    task_id: str = ""
    
    # Event details
    component: str = ""  # orchestrator, agent_executor, tool, etc
    action: str = ""     # what happened
    
    # Additional context
    details: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    severity: str = "info"  # info | warning | error | critical
    
    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "event_type": self.event_type.value,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "task_id": self.task_id,
            "component": self.component,
            "action": self.action,
            "severity": self.severity,
            "details": self.details,
        }

    def to_json_line(self) -> str:
        """Format sebagai JSON line untuk logging."""
        return json.dumps(self.to_dict(), ensure_ascii=False)


class AuditLogger:
    """
    Comprehensive audit logging untuk compliance.
    All events logged ke file + in-memory untuk querying.
    """
    
    def __init__(self):
        AUDIT_LOG_DIR.mkdir(parents=True, exist_ok=True)
        self._events: List[AuditEvent] = []
        self._max_memory_events = 5000
        
        # Daily log files
        self._current_log_date = None
        self._current_log_file = None

    def _get_log_file(self, timestamp: float) -> Path:
        """Get log file path untuk date dari timestamp."""
        from datetime import datetime
        date_str = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")
        return AUDIT_LOG_DIR / f"audit-{date_str}.jsonl"

    def log_event(
        self,
        event_type: AuditEventType,
        component: str,
        action: str,
        user_id: str = "",
        session_id: str = "",
        task_id: str = "",
        details: Optional[Dict[str, Any]] = None,
        severity: str = "info",
    ) -> AuditEvent:
        """Log single audit event."""
        
        event = AuditEvent(
            event_type=event_type,
            user_id=user_id,
            session_id=session_id,
            task_id=task_id,
            component=component,
            action=action,
            details=details or {},
            severity=severity,
        )
        
        # Store in memory
        self._events.append(event)
        if len(self._events) > self._max_memory_events:
            self._events.pop(0)
        
        # Write to file
        try:
            log_file = self._get_log_file(event.timestamp)
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(event.to_json_line() + "\n")
        except Exception as e:
            log.error("Failed to write audit log", error=str(e))
        
        return event

    def log_request_started(
        self,
        user_id: str,
        session_id: str,
        task_id: str,
        message: str,
        **details
    ):
        """Log request start."""
        self.log_event(
            event_type=AuditEventType.REQUEST_STARTED,
            component="orchestrator",
            action="request_received",
            user_id=user_id,
            session_id=session_id,
            task_id=task_id,
            details={
                "message_preview": message[:100],
                **details,
            },
            severity="info",
        )

    def log_agent_assigned(
        self,
        user_id: str,
        session_id: str,
        task_id: str,
        agent_type: str,
        model_id: str,
        score: float,
        **details
    ):
        """Log agent assignment."""
        self.log_event(
            event_type=AuditEventType.AGENT_ASSIGNED,
            component="agent_scorer",
            action="agent_selected",
            user_id=user_id,
            session_id=session_id,
            task_id=task_id,
            details={
                "agent_type": agent_type,
                "model_id": model_id,
                "selection_score": round(score, 3),
                **details,
            },
            severity="info",
        )

    def log_tool_called(
        self,
        user_id: str,
        session_id: str,
        task_id: str,
        tool_name: str,
        tool_args: Dict[str, Any],
        **details
    ):
        """Log tool invocation."""
        # Sanitize sensitive args (passwords, keys, etc)
        sanitized_args = self._sanitize_args(tool_args)
        
        self.log_event(
            event_type=AuditEventType.TOOL_CALLED,
            component="agent_executor",
            action="tool_invoked",
            user_id=user_id,
            session_id=session_id,
            task_id=task_id,
            details={
                "tool_name": tool_name,
                "tool_args": sanitized_args,
                **details,
            },
            severity="info",
        )

    def log_approval_requested(
        self,
        user_id: str,
        request_id: str,
        operation_type: str,
        operation_detail: str,
        risk_level: str,
        reason: str,
    ):
        """Log approval request."""
        self.log_event(
            event_type=AuditEventType.APPROVAL_REQUESTED,
            component="approval_system",
            action="approval_needed",
            user_id=user_id,
            details={
                "request_id": request_id,
                "operation_type": operation_type,
                "operation_detail": operation_detail[:200],
                "risk_level": risk_level,
                "reason": reason,
            },
            severity="warning",
        )

    def log_approval_granted(
        self,
        user_id: str,
        request_id: str,
        approved_by: str,
    ):
        """Log approval granting."""
        self.log_event(
            event_type=AuditEventType.APPROVAL_GRANTED,
            component="approval_system",
            action="approval_granted",
            user_id=user_id,
            details={
                "request_id": request_id,
                "approved_by": approved_by,
            },
            severity="info",
        )

    def log_cost_alert(
        self,
        user_id: str,
        threshold_percent: int,
        current_usage_usd: float,
        budget_limit_usd: float,
    ):
        """Log cost alert."""
        self.log_event(
            event_type=AuditEventType.COST_ALERT,
            component="cost_engine",
            action="budget_threshold_reached",
            user_id=user_id,
            details={
                "threshold_percent": threshold_percent,
                "current_usage_usd": round(current_usage_usd, 2),
                "budget_limit_usd": round(budget_limit_usd, 2),
            },
            severity="warning",
        )

    def log_error_recovery(
        self,
        user_id: str,
        session_id: str,
        task_id: str,
        strategy: str,
        model_used: str,
        success: bool,
        error: Optional[str] = None,
    ):
        """Log error recovery attempt."""
        self.log_event(
            event_type=AuditEventType.ERROR_RECOVERY,
            component="error_recovery",
            action="recovery_attempted",
            user_id=user_id,
            session_id=session_id,
            task_id=task_id,
            details={
                "strategy": strategy,
                "model_used": model_used,
                "success": success,
                "original_error": error[:100] if error else None,
            },
            severity="warning",
        )

    def log_request_completed(
        self,
        user_id: str,
        session_id: str,
        task_id: str,
        execution_time_ms: int,
        total_cost_usd: float,
        success: bool,
        **details
    ):
        """Log request completion."""
        self.log_event(
            event_type=AuditEventType.REQUEST_COMPLETED,
            component="orchestrator",
            action="request_finished",
            user_id=user_id,
            session_id=session_id,
            task_id=task_id,
            details={
                "execution_time_ms": execution_time_ms,
                "total_cost_usd": round(total_cost_usd, 6),
                "success": success,
                **details,
            },
            severity="info",
        )

    def _sanitize_args(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Remove sensitive info from args."""
        sanitized = {}
        sensitive_keys = {"password", "api_key", "secret", "token", "auth"}
        
        for key, value in args.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_args(value)
            elif isinstance(value, str) and len(value) > 500:
                # Truncate long strings
                sanitized[key] = value[:500] + "..."
            else:
                sanitized[key] = value
        
        return sanitized

    def query_events(
        self,
        user_id: Optional[str] = None,
        event_type: Optional[AuditEventType] = None,
        session_id: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 100,
    ) -> List[dict]:
        """Query audit events dengan filter."""
        
        results = self._events
        
        if user_id:
            results = [e for e in results if e.user_id == user_id]
        if event_type:
            results = [e for e in results if e.event_type == event_type]
        if session_id:
            results = [e for e in results if e.session_id == session_id]
        if severity:
            results = [e for e in results if e.severity == severity]
        
        # Sort by timestamp descending, return latest
        results.sort(key=lambda e: e.timestamp, reverse=True)
        return [e.to_dict() for e in results[:limit]]

    def get_user_activity_summary(self, user_id: str, days: int = 7) -> dict:
        """Get summary aktivitas user dalam N hari."""
        cutoff_time = time.time() - (days * 86400)
        
        user_events = [
            e for e in self._events
            if e.user_id == user_id and e.timestamp >= cutoff_time
        ]
        
        # Count by event type
        event_counts = {}
        for event in user_events:
            event_type = event.event_type.value
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
        
        # Count by severity
        severity_counts = {}
        for event in user_events:
            severity_counts[event.severity] = severity_counts.get(event.severity, 0) + 1
        
        return {
            "user_id": user_id,
            "period_days": days,
            "total_events": len(user_events),
            "event_types": event_counts,
            "severity_breakdown": severity_counts,
            "latest_events": [e.to_dict() for e in user_events[-10:]],
        }


# Global singleton
audit_logger = AuditLogger()
