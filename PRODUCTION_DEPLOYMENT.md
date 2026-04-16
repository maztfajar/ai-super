# 🚀 PRODUCTION DEPLOYMENT GUIDE

## Comprehensive Checklist untuk Deploy ke Production

---

## ✅ PRE-DEPLOYMENT VALIDATION

### 1. Code Health Check
```bash
cd /home/ppidpengasih/Documents/ai-super

# ✅ Semua modules import tanpa error
python3 -c "
from backend.core.approval_system import approval_system
from backend.core.cost_tracking import cost_engine
from backend.core.audit_logging import audit_logger
from backend.core.enhanced_tools import enhanced_tool_executor
from backend.api.compliance import compliance_router
print('✅ All modules import successfully')
"

# ✅ Run full test suite
python3 test_improvements.py

# Expected output:
# ✅ ALL TESTS PASSED SUCCESSFULLY!
# 📋 SUMMARY OF IMPROVEMENTS:
#    1. ✅ Human Approval System
#    2. ✅ Cost Tracking System
#    3. ✅ Audit Logging System
#    4. ✅ Enhanced Tool Wrapper
# 🚀 Ready for production deployment!
```

### 2. Backend Startup Test
```bash
cd /home/ppidpengasih/Documents/ai-super/backend

# Kill any existing processes
pkill -f "uvicorn"

# Start backend fresh
python3 main.py

# In another terminal - health check
curl http://localhost:7860/api/health

# Expected:
# {
#   "status": "ok",
#   "components": {
#     "database": "ok",
#     "sumopod": "5 models online",
#     "cache": "ok"
#   }
# }
```

### 3. API Endpoints Validation
```bash
# Check all 13 compliance endpoints exist
curl -s http://localhost:7860/docs | grep -c "compliance"

# Should return >= 13

# Spot check key endpoints
curl http://localhost:7860/api/compliance/approvals/pending
curl http://localhost:7860/api/compliance/costs/budget
curl http://localhost:7860/api/compliance/audit/events?user_id=test
curl http://localhost:7860/api/compliance/dashboard/compliance-overview
```

---

## 🔧 DEPLOYMENT STEPS

### Step 1: Environment Setup

```bash
# 1a. Create production .env
cat > /home/ppidpengasih/Documents/ai-super/backend/.env.production << 'EOF'
# API Configuration
API_HOST=0.0.0.0
API_PORT=7860
DEBUG=false

# Database
DATABASE_URL=sqlite:///./data/production.db

# AI Endpoints
SUMOPOD_HOST=https://ai.sumopod.com/v1
OPENAI_API_KEY=${OPENAI_API_KEY}
ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}

# Compliance Settings
APPROVAL_TIMEOUT_SECONDS=300
DEFAULT_MONTHLY_BUDGET_USD=50.0
AUDIT_LOG_RETENTION_DAYS=90

# Redis (optional - for distributed approval queue)
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
ENABLE_CORS=true
CORS_ORIGINS=["https://yourdomain.com"]

# Telegram Alerts (optional)
TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
TELEGRAM_ADMIN_ID=${TELEGRAM_ADMIN_ID}
EOF

# 1b. Verify environment
source backend/.env.production
echo "✅ Environment variables loaded"
```

### Step 2: Database Preparation

```bash
# 2a. Backup existing database (if any)
if [ -f "backend/data/production.db" ]; then
    cp backend/data/production.db backend/data/production.db.backup.$(date +%Y%m%d)
    echo "✅ Database backed up"
fi

# 2b. Create/initialize database tables
python3 << 'PYEOF'
from backend.db.database import create_tables
create_tables()
print("✅ Database tables initialized")
PYEOF

# 2c. Run migrations (if any)
python3 << 'PYEOF'
from backend.db.models import User, CostBudget, ApprovalRequest
from backend.db.database import engine

# Create tables
Base.metadata.create_all(bind=engine)
print("✅ All database tables created")
PYEOF
```

### Step 3: Directory Structure

```bash
# 3a. Create required directories
mkdir -p /home/ppidpengasih/Documents/ai-super/backend/data/{
    audit_logs,      # For audit logging
    uploads,         # For file uploads
    logs,           # For application logs
    backups,        # For database backups
}
chmod -R 755 backend/data/

# 3b. Create log rotation
cat > /etc/logrotate.d/ai-orchestrator << 'EOF'
/home/ppidpengasih/Documents/ai-super/backend/data/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 ppidpengasih ppidpengasih
}
EOF
```

### Step 4: Process Management (Systemd)

```bash
# 4a. Create systemd service
sudo tee /etc/systemd/system/ai-orchestrator.service > /dev/null << 'EOF'
[Unit]
Description=AI Orchestrator Service
After=network.target

[Service]
Type=notify
User=ppidpengasih
WorkingDirectory=/home/ppidpengasih/Documents/ai-super

# Environment
EnvironmentFile=/home/ppidpengasih/Documents/ai-super/backend/.env.production

# Start command
ExecStart=/home/ppidpengasih/Documents/ai-super/backend/venv/bin/python3 \
    -m uvicorn main:app \
    --host 0.0.0.0 \
    --port 7860 \
    --workers 4 \
    --loop uvloop

# Restart policy
Restart=on-failure
RestartSec=10
StartLimitInterval=60
StartLimitBurst=3

# Resource limits
MemoryLimit=2G
CPUQuota=80%

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=ai-orchestrator

[Install]
WantedBy=multi-user.target
EOF

# 4b. Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable ai-orchestrator
sudo systemctl start ai-orchestrator

# 4c. Verify service
sudo systemctl status ai-orchestrator
```

### Step 5: Nginx Reverse Proxy

```bash
# 5a. Create nginx config
sudo tee /etc/nginx/sites-available/ai-orchestrator.conf > /dev/null << 'EOF'
upstream ai_orchestrator {
    server 127.0.0.1:7860;
}

server {
    listen 80;
    server_name api.yourdomain.com;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=100r/m;
    limit_req zone=api burst=200 nodelay;

    # SSL redirect
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    # SSL certificates
    ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;

    # Compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript;
    gzip_min_length 1000;

    location / {
        proxy_pass http://ai_orchestrator;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    location /ws {
        proxy_pass http://ai_orchestrator/ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }

    # Compliance dashboard
    location /api/compliance {
        proxy_pass http://ai_orchestrator/api/compliance;
        # Require authentication for sensitive endpoints
        auth_request /auth;
    }
}

server {
    listen 127.0.0.1:9000;
    server_name _;
    location /auth {
        # Internal auth endpoint
        access_log off;
    }
}
EOF

# 5b. Enable nginx config
sudo ln -sf /etc/nginx/sites-available/ai-orchestrator.conf /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### Step 6: Monitoring & Logging

```bash
# 6a. Setup centralized logging (optional - using ELK stack)
cat > /home/ppidpengasih/Documents/ai-super/backend/logging_config.yaml << 'EOF'
version: 1
disable_existing_loggers: false

formatters:
  standard:
    format: '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
  json:
    class: pythonjsonlogger.jsonlogger.JsonFormatter
    format: '%(asctime)s %(name)s %(levelname)s %(message)s'

handlers:
  console:
    class: logging.StreamHandler
    formatter: standard
    level: INFO

  file:
    class: logging.handlers.RotatingFileHandler
    filename: data/logs/app.log
    formatter: json
    level: DEBUG
    maxBytes: 10485760  # 10MB
    backupCount: 10

loggers:
  orchestrator:
    level: DEBUG
    handlers: [console, file]
  
  compliance:
    level: DEBUG
    handlers: [file]

root:
  level: DEBUG
  handlers: [console, file]
EOF

# 6b. Setup metrics collection
cat > /home/ppidpengasih/Documents/ai-super/backend/metrics_config.py << 'EOF'
from prometheus_client import Counter, Histogram, Gauge

# Approval metrics
approval_requests_total = Counter(
    'approval_requests_total',
    'Total approval requests',
    ['risk_level']
)
approval_latency = Histogram(
    'approval_latency_seconds',
    'Approval decision latency'
)

# Cost metrics
cost_total_usd = Gauge(
    'cost_total_usd',
    'Total cost in USD',
    ['user_id']
)
budget_utilization_percent = Gauge(
    'budget_utilization_percent',
    'Budget utilization percentage',
    ['user_id']
)

# Tool metrics
tool_execution_time = Histogram(
    'tool_execution_seconds',
    'Tool execution time',
    ['tool_name', 'status']
)
EOF
```

### Step 7: Backup & Recovery

```bash
# 7a. Create backup script
cat > /home/ppidpengasih/Documents/ai-super/scripts/backup-production.sh << 'EOF'
#!/bin/bash
set -e

BACKUP_DIR="/home/ppidpengasih/backups/ai-orchestrator"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

# Backup database
sqlite3 backend/data/production.db ".backup $BACKUP_DIR/db_$DATE.db"

# Backup audit logs
tar -czf "$BACKUP_DIR/audit_logs_$DATE.tar.gz" backend/data/audit_logs/

# Backup configuration
tar -czf "$BACKUP_DIR/config_$DATE.tar.gz" backend/.env.production

# Cleanup old backups (keep 30 days)
find "$BACKUP_DIR" -mtime +30 -delete

echo "✅ Backup completed: $BACKUP_DIR"
EOF

chmod +x scripts/backup-production.sh

# 7b. Setup cron job untuk daily backup
crontab -e
# Add: 0 2 * * * /home/ppidpengasih/Documents/ai-super/scripts/backup-production.sh
```

---

## 📊 MONITORING & OBSERVABILITY

### Prometheus Metrics Endpoint
```bash
# View metrics
curl http://localhost:7860/metrics

# Expected metrics:
# approval_requests_total{risk_level="HIGH"} 5
# cost_total_usd{user_id="user_123"} 10.25
# tool_execution_seconds_bucket{tool_name="execute_bash", status="success"} 100
```

### Grafana Dashboard Setup
```bash
# 1. Install Grafana (if not already)
sudo apt-get install grafana-server

# 2. Create dashboard JSON (save as dashboard.json)
# Import into Grafana via: Dashboards → Import JSON

# 3. Configure Prometheus datasource
# Data Sources → Add Prometheus → URL: http://localhost:9090
```

### ELK Stack Logging (optional)
```bash
# Forward logs to Elasticsearch/Kibana
cat > /etc/filebeat/filebeat.yml << 'EOF'
filebeat.inputs:
- type: log
  enabled: true
  paths:
    - /home/ppidpengasih/Documents/ai-super/backend/data/logs/*.log
    - /home/ppidpengasih/Documents/ai-super/backend/data/audit_logs/*.jsonl

output.elasticsearch:
  hosts: ["localhost:9200"]
  index: "ai-orchestrator-%{+yyyy.MM.dd}"
EOF

systemctl restart filebeat
```

---

## 🔐 SECURITY HARDENING

### 1. API Authentication
```python
# In backend/api/auth.py, ensure all endpoints require:

from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthCredentials

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthCredentials = Depends(security)):
    token = credentials.credentials
    # Verify JWT token
    # If invalid, raise 401 Unauthorized
    return user
```

### 2. Rate Limiting
```python
# Install slowapi
# pip install slowapi

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/api/compliance/approvals/{request_id}/approve")
@limiter.limit("10/minute")
async def approve_operation(request_id: str):
    # Endpoint limited to 10 requests per minute
    pass
```

### 3. Input Validation
```python
# Use Pydantic models for all inputs

from pydantic import BaseModel, Field

class ApprovalResponse(BaseModel):
    request_id: str = Field(..., max_length=50)
    decision: str = Field(..., regex="^(approve|reject)$")
    reason: str = Field("", max_length=500)
```

### 4. Data Encryption
```bash
# Encrypt sensitive fields in database

# Install cryptography
pip install cryptography

# Usage in models
from sqlalchemy_utils import EncryptedType
from cryptography.fernet import Fernet

secret_key = Fernet.generate_key()

class User(Base):
    __tablename__ = "users"
    api_key = Column(EncryptedType(String, secret_key))
```

---

## 🧪 POST-DEPLOYMENT TESTING

### Smoke Tests
```bash
#!/bin/bash

echo "🔍 Running smoke tests..."

# Test 1: API Health
curl -f http://localhost:7860/api/health || exit 1
echo "✅ API health check passed"

# Test 2: Approvals endpoint
curl -f http://localhost:7860/api/compliance/approvals/pending || exit 1
echo "✅ Approvals endpoint accessible"

# Test 3: Cost tracking
curl -f http://localhost:7860/api/compliance/costs/budget || exit 1
echo "✅ Cost endpoint accessible"

# Test 4: Audit logging
curl -f http://localhost:7860/api/compliance/audit/events || exit 1
echo "✅ Audit endpoint accessible"

# Test 5: Load test
ab -n 100 -c 10 http://localhost:7860/api/health
echo "✅ Load test completed"

echo "🎉 All smoke tests passed!"
```

### Performance Baseline
```bash
# Record baseline metrics
curl http://localhost:7860/metrics | grep -E "requests_total|execution_seconds" > baseline.txt

# Compare after changes
curl http://localhost:7860/metrics | grep -E "requests_total|execution_seconds" > current.txt
diff baseline.txt current.txt
```

---

## 🚨 INCIDENT RESPONSE PLAYBOOK

### If Approval Queue Gets Stuck
```bash
# 1. Check for stuck approvals
curl http://localhost:7860/api/compliance/approvals/pending

# 2. Force expire old requests (must be admin)
curl -X POST http://localhost:7860/api/compliance/approvals/cleanup \
  -H "Content-Type: application/json" \
  -d '{"max_age_hours": 1}'

# 3. Check audit logs for details
tail -f backend/data/audit_logs/audit-$(date +%Y-%m-%d).jsonl
```

### If Cost Tracking Shows Spikes
```bash
# 1. Check cost history
curl "http://localhost:7860/api/compliance/costs/history?days=1"

# 2. Identify problematic agents
curl "http://localhost:7860/api/compliance/costs/stats?days=1" | jq '.breakdown'

# 3. Review audit logs untuk detail
curl "http://localhost:7860/api/compliance/audit/events?severity=warning"

# 4. Set emergency budget to $0 (pause operations)
curl -X POST http://localhost:7860/api/compliance/costs/budget \
  -H "Content-Type: application/json" \
  -d '{"monthly_limit_usd": 0}'
```

### If Audit Logs Disk Full
```bash
# 1. Check disk usage
du -sh backend/data/audit_logs/

# 2. Archive old logs
tar -czf backup/audit_logs_archive_$(date +%Y%m%d).tar.gz \
    backend/data/audit_logs/*-[01][0-9].jsonl

# 3. Delete archived logs
rm backend/data/audit_logs/*-[01][0-9].jsonl

# 4. Verify disk space freed
df -h backend/data/
```

---

## ✅ FINAL PRE-PRODUCTION CHECKLIST

- [ ] All 4 compliance systems tested and working
- [ ] Database backed up
- [ ] Environment variables configured
- [ ] Systemd service created and enabled
- [ ] Nginx reverse proxy configured with SSL
- [ ] Monitoring and logging setup
- [ ] Backup scripts configured with cron
- [ ] Security hardened (auth, rate limiting, SSL)
- [ ] Smoke tests passing
- [ ] Performance baseline recorded
- [ ] Incident response playbook documented
- [ ] Admin training completed
- [ ] Cost alerts configured
- [ ] Approval notification system tested
- [ ] Audit log export working

---

## 📈 POST-DEPLOYMENT MONITORING

### Daily Checks
1. Check systemd status: `sudo systemctl status ai-orchestrator`
2. Review error logs: `tail -f backend/data/logs/app.log`
3. Monitor cost usage: `curl http://localhost:7860/api/compliance/costs/stats`
4. Check pending approvals: `curl http://localhost:7860/api/compliance/approvals/pending`

### Weekly Reviews
1. Analyze audit logs for pattern
2. Review cost trends
3. Check approval acceptance rate
4. Verify backup integrity

### Monthly Review
1. Cost analysis and forecasting
2. Approval risk assessment
3. System performance metrics
4. Security audit

---

## 🎯 ROLLBACK PROCEDURE

Jika ada masalah serius:

```bash
# 1. Stop current service
sudo systemctl stop ai-orchestrator

# 2. Restore from backup
cp /home/ppidpengasih/backups/ai-orchestrator/db_YYYYMMDD_HHMMSS.db \
   backend/data/production.db

# 3. Restore configuration
tar -xzf /home/ppidpengasih/backups/ai-orchestrator/config_YYYYMMDD_HHMMSS.tar.gz

# 4. Start service with previous version
git revert <commit_hash>
sudo systemctl start ai-orchestrator

# 5. Verify
curl http://localhost:7860/api/health
```

---

## 📞 SUPPORT & ESCALATION

**Critical Issues:**
- API down → Page on-call engineer
- Budget exceeded → Alert to finance team
- Approval queue stuck → Engineering team
- Audit log failure → Compliance team

**Contact Matrix:**
```
Infrastructure:  ops-team@company.com
Security:        security@company.com
Finance:         finance@company.com
Compliance:      compliance@company.com
```

---

🚀 **Ready for Production!**

Semua 4 systems (Approval, Cost Tracking, Audit, Enhanced Tools) sudah production-ready dan dapat di-deploy dengan confidence.
