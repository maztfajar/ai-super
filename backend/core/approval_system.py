"""
Human Approval System — Request risky operations untuk user confirmation.
Detects dangerous commands (sudo, rm -rf, etc) dan require explicit approval.
"""
import re
import time
from typing import Optional, List, Dict
from dataclasses import dataclass, field
from enum import Enum
import structlog

log = structlog.get_logger()


class RiskLevel(Enum):
    LOW = "low"           # No approval needed
    MEDIUM = "medium"     # Warning & log
    HIGH = "high"         # Require approval
    CRITICAL = "critical" # Require approval + disable auto-retry


# Risky patterns yang perlu approval
RISKY_COMMAND_PATTERNS = [
    r"^sudo\s+",                    # Any sudo command
    r"rm\s+-rf\s+/",               # rm -rf /
    r"dd\s+if=",                   # dd disk operations
    r"mkfs",                        # Format filesystem
    r"systemctl\s+stop",           # Stop system service
    r"systemctl\s+restart",        # Restart system service
    r"iptables",                   # Firewall rules
    r"chown\s+.*:\d+",            # Change ownership to root
    r"chmod\s+[0-9]{3}\s+/etc",   # Change /etc permissions
    r">(>)?\s*/dev/sda",          # Write to disk directly
    r"killall\s+",                 # Kill processes
    r"pkill\s+",                   # Pattern kill
]

# Warning patterns (medium risk)
WARNING_COMMAND_PATTERNS = [
    r"rm\s+",                      # Remove files
    r"truncate\s+",                # Truncate files
    r"reboot",                     # Reboot system
    r"shutdown",                   # Shutdown system
    r"docker\s+rm",                # Remove docker containers
    r"docker\s+rmi",               # Remove docker images
]

# Risky file operations
RISKY_FILE_PATHS = [
    "/etc/",
    "/sys/",
    "/dev/",
    "/proc/",
    "/root/",
    "/.ssh/",
]


@dataclass
class ApprovalRequest:
    """Request untuk user approval."""
    request_id: str
    operation_type: str              # "execute_bash" | "write_file" | "delete_file"
    operation_detail: str             # Command atau path
    risk_level: RiskLevel
    reason: str                       # Kenapa dianggap risky
    required_by: float                # Unix timestamp deadline
    created_at: float = field(default_factory=time.time)
    status: str = "pending"           # pending | approved | rejected | expired
    approved_by: Optional[str] = None
    approved_at: Optional[float] = None
    rejection_reason: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "operation_type": self.operation_type,
            "operation_detail": self.operation_detail,
            "risk_level": self.risk_level.value,
            "reason": self.reason,
            "status": self.status,
            "created_at": self.created_at,
            "required_by": self.required_by,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at,
            "rejection_reason": self.rejection_reason,
        }

    def is_expired(self) -> bool:
        """Check if approval request sudah expired."""
        return time.time() > self.required_by


class ApprovalSystem:
    """
    Manages risky operation approvals.
    Pengguna harus confirm sebelum dangerous operations jalan.
    """

    def __init__(self):
        # Store pending approvals: request_id -> ApprovalRequest
        self._pending: Dict[str, ApprovalRequest] = {}
        self._history: List[ApprovalRequest] = []
        self._max_history = 1000

    def detect_bash_risk(self, command: str) -> tuple[RiskLevel, str]:
        """Detect risk level dari bash command."""
        
        # Strip whitespace
        cmd = command.strip()
        
        # Check critical patterns
        for pattern in RISKY_COMMAND_PATTERNS:
            if re.search(pattern, cmd, re.IGNORECASE):
                reason = f"Detected risky command pattern: {pattern}"
                return RiskLevel.HIGH, reason
        
        # Check warning patterns
        for pattern in WARNING_COMMAND_PATTERNS:
            if re.search(pattern, cmd, re.IGNORECASE):
                reason = f"Detected potentially risky pattern: {pattern}"
                return RiskLevel.MEDIUM, reason
        
        return RiskLevel.LOW, ""

    def detect_file_risk(self, path: str, operation: str = "write") -> tuple[RiskLevel, str]:
        """Detect risk level dari file operation."""
        
        path_lower = path.lower()
        
        # Check if path is in risky locations
        for risky_prefix in RISKY_FILE_PATHS:
            if path_lower.startswith(risky_prefix):
                reason = f"Writing to protected system path: {risky_prefix}"
                return RiskLevel.HIGH, reason
        
        # Check for attempt to overwrite critical files
        critical_files = ["/etc/passwd", "/etc/shadow", "/etc/sudoers", "/.bashrc", "/.bash_profile"]
        if path_lower in critical_files:
            reason = f"Attempting to modify critical file: {path}"
            return RiskLevel.CRITICAL, reason
        
        return RiskLevel.LOW, ""

    def create_approval_request(
        self,
        operation_type: str,
        operation_detail: str,
        risk_level: RiskLevel,
        reason: str,
        timeout_seconds: int = 300  # 5 minutes default
    ) -> ApprovalRequest:
        """Create approval request untuk risky operation."""
        
        import uuid
        request_id = f"approval_{uuid.uuid4().hex[:12]}"
        required_by = time.time() + timeout_seconds
        
        request = ApprovalRequest(
            request_id=request_id,
            operation_type=operation_type,
            operation_detail=operation_detail,
            risk_level=risk_level,
            reason=reason,
            required_by=required_by,
        )
        
        self._pending[request_id] = request
        
        log.warning(
            "Approval request created",
            request_id=request_id,
            operation=operation_type,
            risk_level=risk_level.value,
            reason=reason
        )
        
        return request

    def approve_request(self, request_id: str, user_id: str) -> bool:
        """User approve risky operation."""
        
        if request_id not in self._pending:
            log.warning("Approval request not found", request_id=request_id)
            return False
        
        request = self._pending[request_id]
        
        if request.is_expired():
            request.status = "expired"
            log.warning("Approval request expired", request_id=request_id)
            return False
        
        request.status = "approved"
        request.approved_by = user_id
        request.approved_at = time.time()
        
        # Move to history
        del self._pending[request_id]
        self._history.append(request)
        if len(self._history) > self._max_history:
            self._history.pop(0)
        
        log.info(
            "Approval granted",
            request_id=request_id,
            approved_by=user_id,
            operation=request.operation_type
        )
        
        return True

    def reject_request(self, request_id: str, user_id: str, reason: str = "") -> bool:
        """User reject risky operation."""
        
        if request_id not in self._pending:
            log.warning("Approval request not found", request_id=request_id)
            return False
        
        request = self._pending[request_id]
        request.status = "rejected"
        request.approved_by = user_id
        request.rejection_reason = reason
        request.approved_at = time.time()
        
        # Move to history
        del self._pending[request_id]
        self._history.append(request)
        if len(self._history) > self._max_history:
            self._history.pop(0)
        
        log.warning(
            "Approval rejected",
            request_id=request_id,
            rejected_by=user_id,
            operation=request.operation_type,
            reason=reason
        )
        
        return True

    def is_approved(self, request_id: str) -> bool:
        """Check if request sudah approved."""
        if request_id not in self._pending:
            return False
        
        request = self._pending[request_id]
        if request.is_expired():
            request.status = "expired"
            return False
        
        return True  # Not approved yet, wait for user

    def get_pending_requests(self) -> List[Dict]:
        """Get all pending approval requests."""
        # Clean up expired
        expired_ids = [rid for rid, req in self._pending.items() if req.is_expired()]
        for rid in expired_ids:
            self._pending[rid].status = "expired"
            self._history.append(self._pending[rid])
            del self._pending[rid]
        
        return [req.to_dict() for req in self._pending.values()]

    def get_request(self, request_id: str) -> Optional[Dict]:
        """Get specific approval request."""
        in_pending = self._pending.get(request_id)
        if in_pending:
            if in_pending.is_expired():
                in_pending.status = "expired"
            return in_pending.to_dict()
        
        # Check history
        for req in self._history:
            if req.request_id == request_id:
                return req.to_dict()
        
        return None

    def get_history(self, limit: int = 100) -> List[Dict]:
        """Get approval history."""
        return [req.to_dict() for req in self._history[-limit:]]


# Global singleton
approval_system = ApprovalSystem()
