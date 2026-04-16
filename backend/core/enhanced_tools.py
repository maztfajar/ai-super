"""
Enhanced Tool Wrapper — Tool execution dengan approval, cost tracking, audit logging.
"""
import time
from typing import Any, Optional
import structlog
from core.approval_system import approval_system, RiskLevel
from core.cost_tracking import cost_engine
from core.audit_logging import audit_logger, AuditEventType
from agents.tools import core_tools

log = structlog.get_logger()


class EnhancedToolExecutor:
    """
    Wraps tool execution dengan:
    - Risk assessment
    - Human approval untuk risky operations
    - Cost tracking
    - Audit logging
    """
    
    async def execute_bash(
        self,
        command: str,
        user_id: str,
        session_id: str,
        task_id: str,
        require_approval: bool = True,
    ) -> dict:
        """
        Execute bash command dengan safety checks.
        
        Returns:
        {
            "status": "success" | "pending_approval" | "approved_via_api" | "error",
            "output": "...",
            "approval_request_id": "...",  (if pending)
            "error": "...",
        }
        """
        
        # Assess risk
        risk_level, reason = approval_system.detect_bash_risk(command)
        
        # Log tool call
        audit_logger.log_tool_called(
            user_id=user_id,
            session_id=session_id,
            task_id=task_id,
            tool_name="execute_bash",
            tool_args={"command": command},
            risk_level=risk_level.value,
            risk_reason=reason,
        )
        
        # Check if approval needed
        if require_approval and risk_level != RiskLevel.LOW:
            approval_request = approval_system.create_approval_request(
                operation_type="execute_bash",
                operation_detail=command,
                risk_level=risk_level,
                reason=reason,
                timeout_seconds=300 if risk_level == RiskLevel.HIGH else 600,
            )
            
            audit_logger.log_approval_requested(
                user_id=user_id,
                request_id=approval_request.request_id,
                operation_type="execute_bash",
                operation_detail=command[:100],
                risk_level=risk_level.value,
                reason=reason,
            )
            
            return {
                "status": "pending_approval",
                "approval_request_id": approval_request.request_id,
                "message": f"Risky operation requires approval. Request ID: {approval_request.request_id}",
            }
        
        # Execute tool
        try:
            result = await core_tools.execute_bash(command)
            
            audit_logger.log_event(
                event_type=AuditEventType.TOOL_EXECUTED,
                component="tool_executor",
                action="execute_bash_success",
                user_id=user_id,
                session_id=session_id,
                task_id=task_id,
                details={
                    "command": command[:100],
                    "output_length": len(result),
                },
                severity="info",
            )
            
            return {
                "status": "success",
                "output": result,
            }
        
        except Exception as e:
            error_msg = str(e)
            
            audit_logger.log_event(
                event_type=AuditEventType.TOOL_FAILED,
                component="tool_executor",
                action="execute_bash_failed",
                user_id=user_id,
                session_id=session_id,
                task_id=task_id,
                details={
                    "command": command[:100],
                    "error": error_msg[:200],
                },
                severity="error",
            )
            
            return {
                "status": "error",
                "error": error_msg,
            }

    async def write_file(
        self,
        path: str,
        content: str,
        user_id: str,
        session_id: str,
        task_id: str,
        require_approval: bool = True,
    ) -> dict:
        """
        Write file dengan safety checks untuk protected paths.
        
        Returns:
        {
            "status": "success" | "pending_approval" | "error",
            "approval_request_id": "...",  (if pending)
            "message": "...",
        }
        """
        
        # Assess risk
        risk_level, reason = approval_system.detect_file_risk(path, "write")
        
        # Log tool call
        audit_logger.log_tool_called(
            user_id=user_id,
            session_id=session_id,
            task_id=task_id,
            tool_name="write_file",
            tool_args={"path": path, "content": f"{len(content)} bytes"},
            risk_level=risk_level.value,
            risk_reason=reason,
        )
        
        # Check if approval needed
        if require_approval and risk_level != RiskLevel.LOW:
            approval_request = approval_system.create_approval_request(
                operation_type="write_file",
                operation_detail=f"{path} ({len(content)} bytes)",
                risk_level=risk_level,
                reason=reason,
                timeout_seconds=300 if risk_level == RiskLevel.HIGH else 600,
            )
            
            audit_logger.log_approval_requested(
                user_id=user_id,
                request_id=approval_request.request_id,
                operation_type="write_file",
                operation_detail=path,
                risk_level=risk_level.value,
                reason=reason,
            )
            
            return {
                "status": "pending_approval",
                "approval_request_id": approval_request.request_id,
                "message": f"Cannot write to protected path. Request ID: {approval_request.request_id}",
            }
        
        # Execute tool
        try:
            result = await core_tools.write_file(path, content)
            
            audit_logger.log_event(
                event_type=AuditEventType.TOOL_EXECUTED,
                component="tool_executor",
                action="write_file_success",
                user_id=user_id,
                session_id=session_id,
                task_id=task_id,
                details={
                    "path": path,
                    "size_bytes": len(content),
                },
                severity="info",
            )
            
            return {
                "status": "success",
                "message": result,
            }
        
        except Exception as e:
            error_msg = str(e)
            
            audit_logger.log_event(
                event_type=AuditEventType.TOOL_FAILED,
                component="tool_executor",
                action="write_file_failed",
                user_id=user_id,
                session_id=session_id,
                task_id=task_id,
                details={
                    "path": path,
                    "error": error_msg[:200],
                },
                severity="error",
            )
            
            return {
                "status": "error",
                "error": error_msg,
            }

    async def read_file(
        self,
        path: str,
        user_id: str,
        session_id: str,
        task_id: str,
    ) -> dict:
        """Read file (no approval needed untuk read operations)."""
        
        try:
            result = await core_tools.read_file(path)
            
            audit_logger.log_event(
                event_type=AuditEventType.TOOL_EXECUTED,
                component="tool_executor",
                action="read_file_success",
                user_id=user_id,
                session_id=session_id,
                task_id=task_id,
                details={"path": path, "size_bytes": len(result)},
            )
            
            return {
                "status": "success",
                "output": result,
            }
        
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    async def ask_model(
        self,
        model_id: str,
        prompt: str,
        user_id: str,
        session_id: str,
        task_id: str,
    ) -> dict:
        """Ask another model (dengan cost tracking)."""
        
        # Estimate cost (rough estimate: ~50:50 input:output ratio)
        estimated_input = len(prompt.split()) * 1.3  # rough approximation
        estimated_output = estimated_input * 0.5
        
        cost_engine.add_token_usage(
            task_id=task_id,
            model_id=model_id,
            input_tokens=int(estimated_input),
            output_tokens=int(estimated_output),
        )
        
        try:
            result = await core_tools.ask_model(model_id, prompt)
            
            audit_logger.log_event(
                event_type=AuditEventType.TOOL_EXECUTED,
                component="tool_executor",
                action="ask_model_success",
                user_id=user_id,
                session_id=session_id,
                task_id=task_id,
                details={
                    "model_id": model_id,
                    "prompt_length": len(prompt),
                },
            )
            
            return {
                "status": "success",
                "output": result,
            }
        
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    async def web_search(
        self,
        query: str,
        user_id: str,
        session_id: str,
        task_id: str,
    ) -> dict:
        """Web search."""
        
        try:
            from agents.tools.web_search import web_search
            result = await web_search(query)
            
            audit_logger.log_event(
                event_type=AuditEventType.TOOL_EXECUTED,
                component="tool_executor",
                action="web_search_success",
                user_id=user_id,
                session_id=session_id,
                task_id=task_id,
                details={
                    "query": query,
                    "results_count": len(result) if result else 0,
                },
            )
            
            return {
                "status": "success",
                "output": result,
            }
        
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }


# Global singleton
enhanced_tool_executor = EnhancedToolExecutor()
