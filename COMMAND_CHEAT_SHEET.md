# 🎯 COMMAND CHEAT SHEET

**Print ini dan simpan di meja untuk quick reference!**

---

## 🚀 STARTUP

```bash
# Start backend
cd /home/ppidpengasih/Documents/ai-super/backend
python3 main.py

# Test all systems
python3 test_improvements.py

# View API docs
open http://localhost:7860/docs

# Check health
curl http://localhost:7860/api/health
```

---

## 🔐 APPROVAL SYSTEM

### Check Pending Approvals
```bash
curl http://localhost:7860/api/compliance/approvals/pending
```

### Approve Operation
```bash
curl -X POST http://localhost:7860/api/compliance/approvals/{REQUEST_ID}/approve
```

### Reject Operation
```bash
curl -X POST http://localhost:7860/api/compliance/approvals/{REQUEST_ID}/reject \
  -H "Content-Type: application/json" \
  -d '{"reason": "Too risky"}'
```

### Get Approval History
```bash
curl http://localhost:7860/api/compliance/approvals/history
```

---

## 💰 COST TRACKING

### Check Budget
```bash
curl http://localhost:7860/api/compliance/costs/budget
```

### Set Monthly Budget
```bash
curl -X POST http://localhost:7860/api/compliance/costs/budget \
  -H "Content-Type: application/json" \
  -d '{"monthly_limit_usd": 50.0}'
```

### Cost Stats (Last 30 days)
```bash
curl "http://localhost:7860/api/compliance/costs/stats?days=30"
```

### Estimate Cost (Before Execute)
```bash
curl "http://localhost:7860/api/compliance/costs/estimate?model_id=gpt-4o&estimated_input_tokens=2000&estimated_output_tokens=1500"
```

### Cost History
```bash
curl "http://localhost:7860/api/compliance/costs/history?days=7&limit=50"
```

---

## 📋 AUDIT LOGGING

### Query Events
```bash
curl "http://localhost:7860/api/compliance/audit/events?user_id=user_123&severity=error"
```

### Activity Summary
```bash
curl "http://localhost:7860/api/compliance/audit/activity?user_id=user_123&days=7"
```

### Export as CSV
```bash
curl "http://localhost:7860/api/compliance/audit/export?format=csv" > audit.csv
```

### Export as JSON
```bash
curl "http://localhost:7860/api/compliance/audit/export?format=json" > audit.json
```

### Export as JSONL
```bash
curl "http://localhost:7860/api/compliance/audit/export?format=jsonl" > audit.jsonl
```

### View Real-time Logs
```bash
tail -f backend/data/audit_logs/audit-$(date +%Y-%m-%d).jsonl
```

---

## 📊 DASHBOARD

### Compliance Overview
```bash
curl http://localhost:7860/api/compliance/dashboard/compliance-overview
```

---

## 🧪 TESTING

### Full Test Suite
```bash
python3 test_improvements.py
```

### Individual Component Testing
```python
# Test Approval System
python3 << 'EOF'
from core.approval_system import approval_system
risk, reason = approval_system.detect_bash_risk("rm -rf /")
print(f"Risk: {risk.name}")
EOF

# Test Cost Tracking
python3 << 'EOF'
from core.cost_tracking import cost_engine
cost_engine.set_user_budget("test", 50.0)
print(cost_engine.get_user_budget("test").to_dict())
EOF

# Test Audit Logging
python3 << 'EOF'
from core.audit_logging import audit_logger, AuditEventType
audit_logger.log_event(
    event_type=AuditEventType.REQUEST_STARTED,
    component="test",
    action="test",
    user_id="test"
)
print("✅ Event logged")
EOF
```

---

## 🔍 DEBUGGING

### Check Pending Approvals (Real-time)
```bash
watch -n 5 'curl -s http://localhost:7860/api/compliance/approvals/pending | jq ".pending_requests | length"'
```

### Check Budget Utilization
```bash
curl -s http://localhost:7860/api/compliance/costs/budget | jq '.utilization_percent'
```

### Audit Trail for Forensics
```bash
curl "http://localhost:7860/api/compliance/audit/events?user_id=USER_ID" | jq '.events[] | .details.command'
```

### Find All High Risk Operations
```bash
curl "http://localhost:7860/api/compliance/approvals/history" | jq '.history[] | select(.risk_level=="HIGH")'
```

---

## 🆘 EMERGENCY

### Stop All Operations (Set Budget to $0)
```bash
curl -X POST http://localhost:7860/api/compliance/costs/budget \
  -H "Content-Type: application/json" \
  -d '{"monthly_limit_usd": 0}'
```

### Kill Backend
```bash
pkill -f "uvicorn"
```

### Check Backend Status
```bash
ps aux | grep uvicorn
```

### Restart Backend
```bash
cd /home/ppidpengasih/Documents/ai-super/backend
python3 main.py
```

### Restore from Backup
```bash
cp /home/ppidpengasih/backups/ai-orchestrator/db_*.db backend/data/production.db
```

---

## 📊 MONITORING QUERIES

### Daily Cost Report
```bash
curl "http://localhost:7860/api/compliance/costs/stats?days=1" | \
  jq '.daily_breakdown[0] | {date, cost_usd: .cost_usd, requests: .requests}'
```

### Weekly Activity
```bash
curl "http://localhost:7860/api/compliance/audit/activity?days=7" | \
  jq '.by_event_type'
```

### High Cost Users
```bash
curl "http://localhost:7860/api/compliance/costs/stats?days=30" | \
  jq '.by_user | sort_by(.cost) | reverse | .[0:5]'
```

### Recent Errors
```bash
curl "http://localhost:7860/api/compliance/audit/events?severity=error" | \
  jq '.events | .[0:10] | reverse'
```

---

## 💾 BACKUP & MAINTENANCE

### Backup Database
```bash
cp backend/data/production.db backend/data/production.db.backup.$(date +%Y%m%d_%H%M%S)
```

### Archive Audit Logs
```bash
tar -czf bg/audit_logs_$(date +%Y%m%d).tar.gz backend/data/audit_logs/*.jsonl
```

### Clear Old Audit Logs (Keep 30 days)
```bash
find backend/data/audit_logs -name "*.jsonl" -mtime +30 -delete
```

### Check Disk Usage
```bash
du -sh backend/data/*
```

---

## 🔧 CONFIGURATION

### Check Environment
```bash
cat backend/.env | grep -E "API_|DATABASE_|SUMOPOD_|BUDGET"
```

### Update Environment Variable
```bash
# Edit .env file
nano backend/.env

# Then restart backend
pkill -f uvicorn
python3 backend/main.py
```

---

## 📖 DOCUMENTATION LINKS

| Task | Document |
|------|----------|
| Overview | DELIVERY_SUMMARY.md |
| Features | IMPROVEMENTS_DOCUMENTATION.md |
| Integration | INTEGRATION_GUIDE.md |
| Deployment | PRODUCTION_DEPLOYMENT.md |
| API Ref | TECHNICAL_REFERENCE.md |
| Navigation | README_DOCUMENTATION.md |

---

## 🎯 COMMON WORKFLOWS

### Workflow 1: Verify System Health
```bash
# Check backend running
curl http://localhost:7860/api/health

# Check approvals working
curl http://localhost:7860/api/compliance/approvals/pending

# Check cost tracking working
curl http://localhost:7860/api/compliance/costs/budget

# Check audit logging working
curl http://localhost:7860/api/compliance/audit/events?limit=1

echo "✅ All systems OK!"
```

### Workflow 2: Approve Risky Operation
```bash
# 1. See pending
curl http://localhost:7860/api/compliance/approvals/pending | jq '.'
REQUEST_ID="approval_xyz"

# 2. Review details
curl http://localhost:7860/api/compliance/approvals/$REQUEST_ID | jq '.description'

# 3. Approve it
curl -X POST http://localhost:7860/api/compliance/approvals/$REQUEST_ID/approve

# 4. Verify approved
curl http://localhost:7860/api/compliance/approvals/$REQUEST_ID | jq '.status'
```

### Workflow 3: Generate Compliance Report
```bash
# Export all activities
curl "http://localhost:7860/api/compliance/audit/export?format=csv&days=30" \
  > compliance_report_$(date +%Y%m%d).csv

# Get summary stats
curl "http://localhost:7860/api/compliance/audit/activity?days=30" | \
  jq '.by_event_type' > activity_summary.json

echo "✅ Reports generated!"
```

### Workflow 4: Investigate Cost Spike
```bash
# 1. Check current budget
curl http://localhost:7860/api/compliance/costs/budget | jq '.utilization_percent'

# 2. Check history
curl "http://localhost:7860/api/compliance/costs/history?days=1" | jq '.'

# 3. Identify high cost requests
curl "http://localhost:7860/api/compliance/costs/history?days=1" | \
  jq '.history | sort_by(.cost_usd) | reverse | .[0:5]'

# 4. Check corresponding audit logs
USER_ID="identified_user"
curl "http://localhost:7860/api/compliance/audit/events?user_id=$USER_ID&severity=error" | \
  jq '.events[] | {timestamp, action, details}'
```

---

## 🚨 QUICK STATUS CHECK

```bash
#!/bin/bash
echo "🔍 System Status Check..."

echo "Backend running?"
curl -s http://localhost:7860/api/health > /dev/null && echo "✅ Backend OK" || echo "❌ Backend DOWN"

echo "Pending approvals?"
PENDING=$(curl -s http://localhost:7860/api/compliance/approvals/pending | jq '.pending_requests | length')
echo "📋 Pending: $PENDING"

echo "Budget status?"
BUDGET=$(curl -s http://localhost:7860/api/compliance/costs/budget | jq '.utilization_percent')
echo "💰 Budget used: $BUDGET%"

echo "Recent errors?"
ERRORS=$(curl -s "http://localhost:7860/api/compliance/audit/events?severity=error" | jq '.events | length')
echo "⚠️ Errors: $ERRORS"

echo ""
echo "✅ Status check complete!"
```

Save sebagai `check_status.sh` dan jalankan:
```bash
bash check_status.sh
```

---

## 📌 PIN THIS!

**Most Used Commands:**
1. `curl http://localhost:7860/api/compliance/approvals/pending`
2. `curl http://localhost:7860/api/compliance/costs/budget`
3. `curl http://localhost:7860/api/compliance/audit/events?limit=5`
4. `python3 test_improvements.py`
5. `tail -f backend/data/audit_logs/audit-$(date +%Y-%m-%d).jsonl`

---

**Created:** 2024-04-16
**Status:** ✅ READY TO USE
