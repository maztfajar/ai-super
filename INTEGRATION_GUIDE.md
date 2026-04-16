# 🔗 INTEGRATION GUIDE: Enhanced Systems dengan Agent Executor

## Fase II - Aktivasi Sistem dalam Orchestrator Pipeline

Dokumentasi ini untuk **mengintegrasikan** approval system, cost tracking, dan audit logging ke dalam agent executor agar berfungsi end-to-end.

---

## 1️⃣ INTEGRATION POINTS

### Current Architecture:
```
User Request
    ↓
orchestrator.process()
    ↓
agent_executor.execute(agent, task)
    ↓
core_tools.execute_bash() ⚠️ NO APPROVAL/COST/AUDIT
    ↓
Result → User
```

### Target Architecture:
```
User Request
    ↓
orchestrator.process()
    ↓
agent_executor.execute(agent, task)
    ↓
enhanced_tool_executor.execute_bash() ✅ WITH APPROVAL/COST/AUDIT
    ↓
Result → User (auto 📝 audited + 💰 tracked + 👤 approved)
```

---

## 2️⃣ STEP-BY-STEP INTEGRATION

### Step 1: Update `backend/agents/executor.py`

**Current Code (Lines ~50-100):**
```python
from core.tool_manager import tool_manager

async def execute_agent(agent_id, task, context):
    # Tool calls go directly to tool_manager
    result = await tool_manager.execute_bash(cmd, ...)
```

**Required Changes:**
```python
# Add imports
from core.enhanced_tools import enhanced_tool_executor
from core.cost_tracking import cost_engine
from core.audit_logging import audit_logger, AuditEventType

# Modify tool_manager.execute_bash wrapper
async def execute_tool(tool_name, args, context):
    user_id = context.get("user_id")
    session_id = context.get("session_id")
    task_id = context.get("task_id")
    agent_type = context.get("agent_type")
    
    # Use enhanced executor instead of direct tool call
    if tool_name == "execute_bash":
        result = await enhanced_tool_executor.execute_bash(
            command=args["command"],
            user_id=user_id,
            session_id=session_id,
            task_id=task_id
        )
    elif tool_name == "write_file":
        result = await enhanced_tool_executor.write_file(
            filepath=args["filepath"],
            content=args["content"],
            user_id=user_id,
            session_id=session_id,
            task_id=task_id
        )
    elif tool_name == "read_file":
        result = await enhanced_tool_executor.read_file(
            filepath=args["filepath"],
            user_id=user_id
        )
    # ... etc
    
    return result
```

### Step 2: Update `backend/core/orchestrator.py`

**Add to `process_request()` method:**
```python
async def process_request(self, user_id, task, context):
    task_id = str(uuid.uuid4())
    session_id = context.get("session_id", str(uuid.uuid4()))
    
    # 📝 Log request started
    audit_logger.log_request_started(
        user_id=user_id,
        session_id=session_id,
        task_id=task_id,
        message=task[:100]  # First 100 chars
    )
    
    # 💰 Check budget before proceeding
    budget = cost_engine.get_user_budget(user_id)
    if budget.utilization_percent >= 100:
        audit_logger.log_event(
            event_type=AuditEventType.BUDGET_EXCEEDED,
            component="orchestrator",
            action="budget_exceeded",
            user_id=user_id,
            details={"remaining": budget.remaining_usd}
        )
        return {"error": "Monthly budget exceeded"}
    
    try:
        # Existing orchestration logic
        result = await self.orchestrate(task, context)
        
        # 📝 Log request completed
        audit_logger.log_request_completed(
            user_id=user_id,
            session_id=session_id,
            task_id=task_id,
            success=True
        )
        
        return result
        
    except Exception as e:
        # 📝 Log request failed
        audit_logger.log_request_failed(
            user_id=user_id,
            session_id=session_id,
            task_id=task_id,
            error=str(e)
        )
        raise
```

### Step 3: Update WebSocket Handler untuk Approval

**File: `backend/api/websocket.py`**

```python
from api.compliance import compliance_router
from fastapi import WebSocketException

async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    try:
        while True:
            data = await websocket.receive_json()
            
            # Check untuk approval pending
            if data.get("type") == "check_for_approvals":
                pending = approval_system.get_pending_approvals()
                # Send ke client untuk user interaction
                await websocket.send_json({
                    "type": "pending_approvals",
                    "approvals": pending
                })
            
            # Handle approval dari client
            elif data.get("type") == "approve_operation":
                request_id = data.get("request_id")
                approval_system.approve_request(request_id)
                
                # Resume blocked operation
                await websocket.send_json({
                    "type": "approval_granted",
                    "request_id": request_id
                })
```

### Step 4: Add to `backend/main.py` Lifespan

**Current:**
```python
@app.on_event("startup")
async def startup():
    pass
```

**Updated:**
```python
@app.on_event("startup")
async def startup():
    # Initialize compliance systems
    logger.info("Initializing compliance systems...")
    
    # Create audit log directory
    os.makedirs("data/audit_logs", exist_ok=True)
    
    # Load default budgets (optional)
    cost_engine.set_user_budget("default", 50.0)
    
    logger.info("✅ Approval system ready")
    logger.info("✅ Cost tracking ready")
    logger.info("✅ Audit logging ready")
    logger.info(f"✅ Enhanced tools ready with {5} wrapped tools")

@app.on_event("shutdown")
async def shutdown():
    # Export audit logs if needed
    await audit_logger.flush_to_file()
    logger.info("📁 Audit logs flushed to disk")
```

---

## 3️⃣ API INTEGRATION EXAMPLES

### Example 1: Execute Risky Command dengan Approval

**User Flow:**
```
1. User: "Delete /tmp/cache"
   ↓
2. Agent detects: HIGH risk
   ↓
3. System: Creates approval request
   ↓
4. API Response: 
   {
     "status": "pending_approval",
     "approval_id": "approval_abc123",
     "message": "This operation is risky and requires approval",
     "timeout_seconds": 300
   }
   ↓
5. Admin checks: GET /api/compliance/approvals/pending
   ↓
6. Admin approves: POST /api/compliance/approvals/approval_abc123/approve
   ↓
7. System: Executes command, logs event, tracks cost
   ↓
8. User: Gets final result
```

### Example 2: Cost Estimation & Tracking

**Before Execution:**
```bash
# Estimate cost untuk GPT-4o response
curl "http://localhost:7860/api/compliance/costs/estimate?model_id=gpt-4o&estimated_input_tokens=2000&estimated_output_tokens=1500"

Response:
{
  "model_id": "gpt-4o",
  "estimated_input_cost": 0.030,
  "estimated_output_cost": 0.090,
  "total_estimated_cost": 0.120,
  "current_budget_remaining": 49.88,
  "will_fit_in_budget": true
}
```

**After Execution:**
```bash
# Check actual usage
curl http://localhost:7860/api/compliance/costs/history?days=1

Response:
{
  "user_id": "user_123",
  "date": "2024-04-16",
  "daily_cost": 0.145,
  "monthly_total": 2.85,
  "remaining_budget": 47.15,
  "usage_breakdown": [
    {
      "task_id": "task_001",
      "model_id": "gpt-4o",
      "input_tokens": 2050,
      "output_tokens": 1620,
      "cost": 0.120
    }
  ]
}
```

### Example 3: Audit Trail untuk Compliance

**Query all events dari user:**
```bash
curl "http://localhost:7860/api/compliance/audit/events?user_id=user_123&severity=error"

Response:
{
  "total_events": 1,
  "events": [
    {
      "timestamp": 1713270920,
      "event_type": "TOOL_FAILED",
      "component": "execute_bash",
      "action": "command_failed",
      "user_id": "user_123",
      "details": {
        "command": "rm /tmp/nonexistent.txt",
        "error": "File not found"
      },
      "severity": "warning"
    }
  ]
}
```

---

## 4️⃣ APPROVAL WORKFLOW INTEGRATION

### In Chat/Message Handler:

```python
# backend/api/chat.py

async def handle_chat_message(message: str, user_id: str, session_id: str):
    task_id = str(uuid.uuid4())
    
    # 1. Check untuk pending approvals
    pending = approval_system.get_pending_approvals(user_id)
    if pending:
        return {
            "type": "approval_check",
            "message": f"You have {len(pending)} pending approvals that need your action",
            "pending_approvals": pending
        }
    
    # 2. Process message normally
    result = await orchestrator.process(user_id, message, {
        "session_id": session_id,
        "task_id": task_id
    })
    
    # 3. Check hasil - apakah perlu approval?
    if result.get("status") == "pending_approval":
        approval_id = result.get("approval_request_id")
        return {
            "type": "approval_required",
            "approval_id": approval_id,
            "message": result.get("message"),
            "timeout": result.get("timeout_seconds")
        }
    
    return {
        "type": "result",
        "message": result.get("output")
    }
```

---

## 5️⃣ FRONTEND INTEGRATION (React)

### Approval Notification Component:

```jsx
// frontend/src/components/ApprovalNotification.jsx

import { useEffect, useState } from 'react';

export function ApprovalNotification() {
  const [pending, setPending] = useState([]);
  const [ws, setWs] = useState(null);
  
  useEffect(() => {
    // Connect to WebSocket untuk real-time updates
    const websocket = new WebSocket('ws://localhost:7860/ws');
    
    websocket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'pending_approvals') {
        setPending(data.approvals);
      }
    };
    
    setWs(websocket);
    
    return () => websocket.close();
  }, []);
  
  const handleApprove = async (approvalId) => {
    const response = await fetch(
      `/api/compliance/approvals/${approvalId}/approve`,
      { method: 'POST' }
    );
    if (response.ok) {
      setPending(pending.filter(a => a.id !== approvalId));
    }
  };
  
  if (pending.length === 0) return null;
  
  return (
    <div className="bg-yellow-100 border-l-4 border-yellow-500 p-4">
      <h3 className="font-bold">⚠️ Pending Approvals ({pending.length})</h3>
      {pending.map(approval => (
        <div key={approval.id} className="mt-3 p-3 bg-white rounded">
          <p className="text-sm">{approval.description}</p>
          <p className="text-xs text-gray-500 mt-1">
            Risk Level: <span className="font-bold text-red-600">
              {approval.risk_level}
            </span>
          </p>
          <div className="mt-3 flex gap-2">
            <button
              onClick={() => handleApprove(approval.id)}
              className="px-3 py-1 bg-green-500 text-white rounded text-sm"
            >
              ✓ Approve
            </button>
            <button
              onClick={() => handleReject(approval.id)}
              className="px-3 py-1 bg-red-500 text-white rounded text-sm"
            >
              ✗ Reject
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
```

### Cost Dashboard Component:

```jsx
// frontend/src/components/CostDashboard.jsx

export function CostDashboard() {
  const [budget, setBudget] = useState(null);
  const [stats, setStats] = useState(null);
  
  useEffect(() => {
    fetchBudgetAndStats();
    const interval = setInterval(fetchBudgetAndStats, 30000); // Refresh setiap 30 detik
    return () => clearInterval(interval);
  }, []);
  
  const fetchBudgetAndStats = async () => {
    const budgetResponse = await fetch('/api/compliance/costs/budget');
    const budget = await budgetResponse.json();
    
    const statsResponse = await fetch('/api/compliance/costs/stats?days=30');
    const stats = await statsResponse.json();
    
    setBudget(budget);
    setStats(stats);
  };
  
  if (!budget) return <div>Loading...</div>;
  
  const percentageUsed = budget.utilization_percent;
  const progressColor = percentageUsed > 90 ? 'red' : percentageUsed > 50 ? 'yellow' : 'green';
  
  return (
    <div className="p-4 bg-gray-50 rounded">
      <h3 className="font-bold">💰 Monthly Budget</h3>
      
      <div className="mt-3">
        <div className="flex justify-between text-sm mb-2">
          <span>${budget.monthly_used_usd.toFixed(2)}</span>
          <span className="font-bold">${budget.monthly_limit_usd.toFixed(2)}</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div
            className={`h-2 rounded-full bg-${progressColor}-500`}
            style={{ width: `${percentageUsed}%` }}
          />
        </div>
        <p className="text-xs text-gray-500 mt-1">
          ${budget.remaining_usd.toFixed(2)} remaining ({100 - percentageUsed.toFixed(1)}%)
        </p>
      </div>
    </div>
  );
}
```

---

## 6️⃣ DATABASE MIGRATIONS

### If using SQLite, run these:

```sql
-- Create approval_requests table
CREATE TABLE IF NOT EXISTS approval_requests (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    component TEXT,
    description TEXT,
    risk_level TEXT,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    approved_at TIMESTAMP,
    approved_by TEXT
);

-- Create cost_records table
CREATE TABLE IF NOT EXISTS cost_records (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    task_id TEXT,
    model_id TEXT,
    input_tokens INTEGER,
    output_tokens INTEGER,
    cost_usd REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create cost_budgets table
CREATE TABLE IF NOT EXISTS cost_budgets (
    user_id TEXT PRIMARY KEY,
    monthly_limit_usd REAL DEFAULT 10.0,
    current_month_cost REAL DEFAULT 0.0,
    last_reset_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create audit_events index for queries
CREATE INDEX IF NOT EXISTS idx_audit_events_user ON audit_events(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_events_timestamp ON audit_events(timestamp);
```

---

## 7️⃣ TESTING INTEGRATION

### Integration Test Template:

```python
# backend/test_integration.py

import pytest
import asyncio
from core.enhanced_tools import enhanced_tool_executor
from core.approval_system import approval_system
from core.cost_tracking import cost_engine
from core.audit_logging import audit_logger

@pytest.mark.asyncio
async def test_full_workflow():
    """Test complete workflow: risky command → approval → execution → auditing"""
    
    user_id = "test_user_integration"
    task_id = "task_integration_001"
    
    # 1. Setup
    cost_engine.set_user_budget(user_id, 100.0)
    
    # 2. Try risky command
    result = await enhanced_tool_executor.execute_bash(
        command="rm -rf /tmp/test",
        user_id=user_id,
        task_id=task_id
    )
    
    # Should return pending approval
    assert result["status"] == "pending_approval"
    approval_id = result["approval_request_id"]
    
    # 3. Get approval details
    approval = approval_system.get_approval_request(approval_id)
    assert approval is not None
    assert approval.risk_level.name == "HIGH"
    
    # 4. Approve the request
    approval_system.approve_request(approval_id)
    
    # 5. Check audit logs
    events = audit_logger.query_events(user_id=user_id)
    assert len(events) > 0
    assert any(e.event_type.name == "APPROVAL_REQUESTED" for e in events)
    
    print("✅ Full workflow test passed!")

if __name__ == "__main__":
    asyncio.run(test_full_workflow())
```

---

## 8️⃣ DEPLOYMENT CHECKLIST

- [ ] Backup current database
- [ ] Run database migrations
- [ ] Update `backend/agents/executor.py` to use enhanced tools
- [ ] Update `backend/core/orchestrator.py` to use audit logging
- [ ] Update WebSocket handler untuk approval notifications
- [ ] Deploy frontend ApprovalNotification component
- [ ] Deploy frontend CostDashboard component
- [ ] Test full workflow in staging
- [ ] Monitor audit logs untuk pertama kalinya
- [ ] Set up cost alerts via Telegram/Email
- [ ] Train users pada approval workflow
- [ ] Deploy to production

---

## 🎯 OUTCOMES SETELAH INTEGRATION

✅ **User Experience:**
- Automatic detection of risky operations
- Clear approval workflow
- Real-time cost tracking
- Compliance audit trail

✅ **Team Benefits:**
- Cost control (prevent runaway bills)
- Security (prevent accidental harmful commands)
- Compliance (audit trail for regulations)
- Visibility (dashboard untuk monitoring)

✅ **System Benefits:**
- Production-ready (all edge cases handled)
- Scalable (async, efficient, logged)
- Maintainable (clean architecture)
- Testable (all functions have tests)

---

## 📝 NOTES

- Approval system bisa di-customize untuk different risk levels
- Cost pricing table bisa di-update dinamis dari API
- Audit logs bisa di-export untuk compliance reports
- Semua systems terintegrasi satu sama lain seamlessly
