# 🔧 TECHNICAL REFERENCE GUIDE

## Quick API & System Reference

---

## 📍 QUICK START

### Test All Systems
```bash
cd /home/ppidpengasih/Documents/ai-super
source backend/venv/bin/activate
python3 test_improvements.py
# Expected: ✅ ALL TESTS PASSED SUCCESSFULLY!
```

### Start Backend
```bash
cd backend
python3 main.py
# Backend runs on http://0.0.0.0:7860
```

### View API Docs
```bash
# Open in browser: http://localhost:7860/docs
# Or: curl http://localhost:7860/openapi.json
```

---

## 🔌 API REFERENCE

### Authentication (All Endpoints)
```bash
# Most endpoints require user context from session
# Admin endpoints require role="admin"

# Example with auth header:
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:7860/api/compliance/approvals/pending
```

### 1️⃣ APPROVAL ENDPOINTS

#### Get Pending Approvals
```bash
GET /api/compliance/approvals/pending

# Response:
{
  "pending_requests": [
    {
      "id": "approval_xyz",
      "component": "execute_bash",
      "description": "Request to execute: rm -rf /tmp/cache",
      "risk_level": "HIGH",
      "created_at": 1713270920,
      "expires_at": 1713271220
    }
  ]
}
```

#### Get Approval Details
```bash
GET /api/compliance/approvals/{request_id}

# Example:
curl http://localhost:7860/api/compliance/approvals/approval_xyz

# Response:
{
  "id": "approval_xyz",
  "component": "execute_bash",
  "description": "Request to execute: rm -rf /tmp/cache",
  "risk_level": "HIGH",
  "status": "pending",
  "timeout_seconds": 300,
  "created_at": 1713270920
}
```

#### Approve Operation
```bash
POST /api/compliance/approvals/{request_id}/approve

# Example:
curl -X POST http://localhost:7860/api/compliance/approvals/approval_xyz/approve

# Response:
{
  "success": true,
  "message": "Approval granted",
  "request_id": "approval_xyz",
  "approved_at": 1713270935
}
```

#### Reject Operation
```bash
POST /api/compliance/approvals/{request_id}/reject
Content-Type: application/json

{
  "reason": "Too risky"
}

# Example:
curl -X POST http://localhost:7860/api/compliance/approvals/approval_xyz/reject \
  -H "Content-Type: application/json" \
  -d '{"reason": "Too risky"}'

# Response:
{
  "success": true,
  "message": "Operation rejected",
  "request_id": "approval_xyz"
}
```

#### Get Approval History
```bash
GET /api/compliance/approvals/history?limit=20&days=7

# Response:
{
  "total": 45,
  "history": [
    {
      "id": "approval_xyz",
      "status": "approved",
      "risk_level": "MEDIUM",
      "created_at": 1713270920,
      "resolved_at": 1713270935,
      "decision_time_seconds": 15
    }
  ]
}
```

---

### 2️⃣ COST TRACKING ENDPOINTS

#### Get Budget Status
```bash
GET /api/compliance/costs/budget

# Response:
{
  "user_id": "user_123",
  "monthly_limit_usd": 50.00,
  "monthly_used_usd": 12.45,
  "remaining_usd": 37.55,
  "utilization_percent": 24.9,
  "reset_date": "2024-05-01",
  "usage_by_model": {
    "gpt-4o": 10.20,
    "claude-3-sonnet": 2.25
  }
}
```

#### Set Budget (Admin Only)
```bash
POST /api/compliance/costs/budget
Content-Type: application/json

{
  "user_id": "user_123",
  "monthly_limit_usd": 100.0
}

# Example:
curl -X POST http://localhost:7860/api/compliance/costs/budget \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -d '{"monthly_limit_usd": 100.0}'

# Response:
{
  "success": true,
  "message": "Budget updated",
  "new_limit": 100.0,
  "effective_date": "2024-04-16"
}
```

#### Get Cost Statistics
```bash
GET /api/compliance/costs/stats?days=30

# Response:
{
  "user_id": "user_123",
  "period_days": 30,
  "total_cost_usd": 45.67,
  "daily_average": 1.52,
  "daily_breakdown": [
    {
      "date": "2024-04-16",
      "cost_usd": 2.45,
      "requests": 15,
      "tokens": 25000
    }
  ],
  "by_agent": {
    "coding": {
      "cost_usd": 35.20,
      "requests": 120
    },
    "writing": {
      "cost_usd": 10.47,
      "requests": 45
    }
  }
}
```

#### Estimate Cost (Before Execution)
```bash
GET /api/compliance/costs/estimate?model_id=gpt-4o&estimated_input_tokens=2000&estimated_output_tokens=1500

# Response:
{
  "model_id": "gpt-4o",
  "estimated_input_cost_usd": 0.030,
  "estimated_output_cost_usd": 0.090,
  "total_estimated_cost_usd": 0.120,
  "current_budget_remaining_usd": 37.55,
  "will_fit_in_budget": true,
  "warning": null
}
```

#### Get Cost History
```bash
GET /api/compliance/costs/history?limit=50&days=30

# Response:
{
  "total": 125,
  "history": [
    {
      "timestamp": 1713270920,
      "task_id": "task_001",
      "model_id": "gpt-4o",
      "input_tokens": 2050,
      "output_tokens": 1620,
      "cost_usd": 0.1425,
      "agent_type": "coding"
    }
  ]
}
```

---

### 3️⃣ AUDIT LOGGING ENDPOINTS

#### Get Events (Admin)
```bash
GET /api/compliance/audit/events?user_id=user_123&event_type=TOOL_CALLED&severity=error&limit=50

# Response:
{
  "total": 3,
  "events": [
    {
      "timestamp": 1713270920,
      "event_type": "TOOL_CALLED",
      "component": "execute_bash",
      "action": "command_executed",
      "user_id": "user_123",
      "severity": "error",
      "details": {
        "command": "rm /tmp/file.txt",
        "status": "failed",
        "error": "Permission denied"
      }
    }
  ]
}
```

#### Get Activity Summary
```bash
GET /api/compliance/audit/activity?user_id=user_123&days=7

# Response:
{
  "user_id": "user_123",
  "period_days": 7,
  "total_events": 234,
  "by_event_type": {
    "REQUEST_STARTED": 45,
    "AGENT_ASSIGNED": 45,
    "TOOL_CALLED": 120,
    "APPROVAL_REQUESTED": 8,
    "APPROVAL_GRANTED": 7,
    "COST_ALERT": 3
  },
  "by_severity": {
    "info": 200,
    "warning": 30,
    "error": 4
  }
}
```

#### Export Logs
```bash
GET /api/compliance/audit/export?format=json&days=30&user_id=user_123

# Formats: json, csv, jsonl
# Returns: file download

# Example: Export JSONL for last 30 days
curl "http://localhost:7860/api/compliance/audit/export?format=jsonl&days=30" \
  > audit_export.jsonl

# File format (JSONL - one JSON per line):
{"timestamp": 1713270920, "event_type": "request_started", "user_id": "user_123", ...}
{"timestamp": 1713270921, "event_type": "agent_assigned", "user_id": "user_123", ...}
```

#### Dashboard Overview
```bash
GET /api/compliance/dashboard/compliance-overview

# Response:
{
  "timestamp": 1713270920,
  "pending_approvals": 2,
  "critical_alerts": 1,
  "cost_status": {
    "total_users": 5,
    "over_budget": 1,
    "near_budget": 2
  },
  "audit_status": {
    "total_events_today": 1245,
    "errors_today": 3,
    "critical_events": 0
  },
  "top_risks": [
    {
      "risk_type": "HIGH_COST_USER",
      "user_id": "user_456",
      "usage_percent": 95.2
    }
  ]
}
```

---

## 💻 PYTHON USAGE

### Direct Usage (Python Code)

#### Approval System
```python
from core.approval_system import approval_system, RiskLevel

# Detect risk
risk_level, reason = approval_system.detect_bash_risk("rm -rf /")
print(risk_level)  # RiskLevel.HIGH
print(reason)      # "Detected risky command pattern..."

# Create approval request
request = approval_system.create_approval_request(
    user_id="user_123",
    component="execute_bash",
    description="rm -rf /tmp/cache",
    risk_level=RiskLevel.HIGH,
    timeout_seconds=300
)
print(request.id)  # "approval_xyz"

# Check approval
approval = approval_system.get_approval_request("approval_xyz")
print(approval.status)  # "pending"

# Approve
approval_system.approve_request("approval_xyz")
print(approval_system.get_approval_request("approval_xyz").status)  # "approved"

# Get all pending
pending = approval_system.get_pending_approvals()
print(len(pending))  # Number of pending requests
```

#### Cost Tracking
```python
from core.cost_tracking import cost_engine

# Set budget
cost_engine.set_user_budget("user_123", monthly_limit_usd=50.0)

# Add token usage
cost_engine.add_token_usage(
    task_id="task_001",
    model_id="gpt-4o",
    input_tokens=2000,
    output_tokens=1500
)

# Get budget status
budget = cost_engine.get_user_budget("user_123")
print(budget.monthly_used_usd)  # 0.1425
print(budget.remaining_usd)     # 49.86
print(budget.utilization_percent)  # 0.285

# Estimate cost
estimated_cost = cost_engine.estimate_cost(
    model_id="gpt-4o",
    estimated_input_tokens=1000,
    estimated_output_tokens=500
)
print(estimated_cost)  # 0.06
```

#### Audit Logging
```python
from core.audit_logging import audit_logger, AuditEventType

# Log event
audit_logger.log_event(
    event_type=AuditEventType.REQUEST_STARTED,
    component="orchestrator",
    action="request_received",
    user_id="user_123",
    details={"message": "Process request"}
)

# Log request lifecycle
audit_logger.log_request_started("user_123", "session_abc", "task_001", "My request")
audit_logger.log_agent_assigned("user_123", "session_abc", "task_001", "coding", "gpt-4o", 0.92)
audit_logger.log_tool_called("user_123", "task_001", "execute_bash", {"command": "ls"})

# Query events
events = audit_logger.query_events(user_id="user_123", severity="error")
for event in events:
    print(event.event_type, event.details)

# Get activity summary
summary = audit_logger.get_user_activity_summary("user_123")
print(summary)  # Dict with event counts
```

#### Enhanced Tools
```python
import asyncio
from core.enhanced_tools import enhanced_tool_executor

async def main():
    # Execute bash with approval
    result = await enhanced_tool_executor.execute_bash(
        command="rm /tmp/file.txt",
        user_id="user_123",
        session_id="session_abc",
        task_id="task_001"
    )
    
    if result["status"] == "pending_approval":
        print(f"Waiting for approval: {result['approval_request_id']}")
    else:
        print(f"Result: {result['output']}")

asyncio.run(main())
```

---

## 🗄️ DATABASE SCHEMA

### approval_requests Table
```sql
CREATE TABLE approval_requests (
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
```

### cost_records Table
```sql
CREATE TABLE cost_records (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    task_id TEXT,
    model_id TEXT,
    input_tokens INTEGER,
    output_tokens INTEGER,
    cost_usd REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### cost_budgets Table
```sql
CREATE TABLE cost_budgets (
    user_id TEXT PRIMARY KEY,
    monthly_limit_usd REAL DEFAULT 10.0,
    current_month_cost REAL DEFAULT 0.0,
    last_reset_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### File System Storage

**Audit Logs:**
```
backend/data/audit_logs/
├── audit-2024-04-16.jsonl  (Today's events)
├── audit-2024-04-15.jsonl  (Yesterday's events)
└── ...                     (Previous days)
```

**Backups:**
```
backend/data/backups/
├── db_20240416_120000.db   (Database backup)
├── audit_logs_20240416.tar.gz  (Audit logs archive)
└── ...
```

---

## ⚙️ CONFIGURATION

### Default Settings (Hardcoded)
```python
# backend/core/approval_system.py
APPROVAL_TIMEOUT = 300  # 5 minutes for HIGH risk
APPROVAL_TIMEOUT_CRITICAL = 600  # 10 minutes for CRITICAL

# backend/core/cost_tracking.py
DEFAULT_MONTHLY_BUDGET = 10.0  # USD
BUDGET_ALERT_THRESHOLDS = [50, 80, 90, 100]  # percent

# backend/core/audit_logging.py
AUDIT_LOG_DIR = "./data/audit_logs"
MAX_MEMORY_EVENTS = 5000
```

### Environment Variables (Optional)
```bash
# .env file
COMPLIANCE_ENABLED=true
APPROVAL_TIMEOUT_SECONDS=300
DEFAULT_MONTHLY_BUDGET_USD=50.0
AUDIT_LOG_RETENTION_DAYS=90
TELEGRAM_BOT_TOKEN=xxx (for alerts)
TELEGRAM_ADMIN_ID=xxx (for alerts)
```

---

## 🔍 DEBUGGING

### Check Approval Request
```bash
# Check if request exists
curl http://localhost:7860/api/compliance/approvals/pending | jq '.pending_requests[] | select(.id=="approval_xyz")'

# Check audit logs for it
tail -f backend/data/audit_logs/audit-$(date +%Y-%m-%d).jsonl | grep "approval_xyz"
```

### Troubleshoot Cost Issues
```bash
# Check budget remaining
curl http://localhost:7860/api/compliance/costs/budget | jq '.remaining_usd'

# Check if over budget
curl http://localhost:7860/api/compliance/costs/budget | jq '.utilization_percent'

# If over 100%, check what caused it
curl "http://localhost:7860/api/compliance/costs/history?days=1" | jq '.history[] | .cost_usd' | paste -sd+ | bc
```

### Audit Trail Investigation
```bash
# Find all operations from a user
curl "http://localhost:7860/api/compliance/audit/events?user_id=user_123" | jq '.'

# Find specific event type
curl "http://localhost:7860/api/compliance/audit/events?event_type=TOOL_CALLED" | jq '.events[] | .details.command'

# Get activity summary for forensics
curl "http://localhost:7860/api/compliance/audit/activity?user_id=user_123&days=7" | jq '.by_severity'
```

### Monitor Risky Operations
```bash
# Check pending approvals in real-time
watch -n 5 'curl -s http://localhost:7860/api/compliance/approvals/pending | jq ".pending_requests | length"'

# Or tail audit logs
tail -f backend/data/audit_logs/audit-$(date +%Y-%m-%d).jsonl | grep "APPROVAL_REQUESTED"
```

---

## 🧪 COMMON TEST COMMANDS

### Test All Systems
```bash
python3 test_improvements.py
```

### Test Individual Component
```python
# Test just approval
python3 << 'EOF'
from core.approval_system import approval_system
risk, reason = approval_system.detect_bash_risk("sudo rm -rf /")
print(f"Risk: {risk.name}, Reason: {reason}")
EOF

# Test just cost tracking
python3 << 'EOF'
from core.cost_tracking import cost_engine
cost_engine.set_user_budget("test", 50.0)
print(cost_engine.get_user_budget("test").to_dict())
EOF
```

---

## 📊 MONITORING QUERIES

### Daily Report
```bash
# Cost usage today
curl "http://localhost:7860/api/compliance/costs/stats?days=1" | jq '.daily_breakdown[0]'

# Approvals today
curl "http://localhost:7860/api/compliance/approvals/history?days=1" | jq '.history | length'

# Errors today
curl "http://localhost:7860/api/compliance/audit/events?severity=error" | jq '.events | length'
```

### Weekly Report
```bash
# Cost trend
curl "http://localhost:7860/api/compliance/costs/stats?days=7" | jq '.daily_breakdown[] | {date:.date, cost:.cost_usd}'

# High risk approvals
curl "http://localhost:7860/api/compliance/approvals/history?days=7&risk_level=CRITICAL" | jq '.history | length'
```

### Monthly Report
```bash
# Total spend
curl "http://localhost:7860/api/compliance/costs/stats?days=30" | jq '.total_cost_usd'

# Export for compliance
curl "http://localhost:7860/api/compliance/audit/export?format=csv&days=30" > audit_report.csv
```

---

## 🆘 EMERGENCY PROCEDURES

### Emergency: Stop All Operations
```bash
# Set budget to $0
curl -X POST http://localhost:7860/api/compliance/costs/budget \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -d '{"monthly_limit_usd": 0}'

# Check it took effect
curl http://localhost:7860/api/compliance/costs/budget | jq '.monthly_limit_usd'
```

### Emergency: Restart Services
```bash
# Kill backend
pkill -f "uvicorn"

# Restart
cd backend
python3 main.py
```

### Emergency: Recover from Backup
```bash
# Restore database from most recent backup
cp data/production.db.backup.* data/production.db

# Restart backend
pkill -f "uvicorn"
python3 main.py
```

---

## 📞 QUICK REFERENCE

| Task | Command |
|------|---------|
| Start backend | `python3 backend/main.py` |
| View API docs | `http://localhost:7860/docs` |
| Check health | `curl http://localhost:7860/api/health` |
| See pending approvals | `curl http://localhost:7860/api/compliance/approvals/pending` |
| Check budget | `curl http://localhost:7860/api/compliance/costs/budget` |
| Export audit log | `curl "...export?format=csv" > audit.csv` |
| Run tests | `python3 test_improvements.py` |
| Check logs | `tail -f backend/data/audit_logs/audit-*.jsonl` |
| Stop backend | `pkill -f "uvicorn"` |

---

**Use this guide as your reference while working with the compliance systems!**
