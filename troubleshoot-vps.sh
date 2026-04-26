#!/bin/bash
# AI ORCHESTRATOR — VPS Troubleshooting Script
# Run this on VPS to diagnose and fix dashboard loading issues

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; NC='\033[0m'; BOLD='\033[1m'

echo -e "${BOLD}🔍 AI ORCHESTRATOR — VPS Troubleshooting${NC}"
echo "========================================"

# 1. Check if backend is running
echo -e "\n${BOLD}1. Checking Backend Status${NC}"
if pgrep -f "uvicorn main:app" > /dev/null; then
    echo -e "${GREEN}✅ Backend is running${NC}"
    BACKEND_RUNNING=true
else
    echo -e "${RED}❌ Backend is NOT running${NC}"
    BACKEND_RUNNING=false
fi

# 2. Check backend health
echo -e "\n${BOLD}2. Testing Backend Health${NC}"
if curl -s --max-time 5 http://localhost:7860/api/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Backend health endpoint responds${NC}"
    HEALTH_OK=true
else
    echo -e "${RED}❌ Backend health endpoint failed${NC}"
    HEALTH_OK=false
fi

# 3. Check dashboard API
echo -e "\n${BOLD}3. Testing Dashboard API${NC}"
DASHBOARD_RESPONSE=$(curl -s --max-time 10 http://localhost:7860/api/monitoring/dashboard 2>/dev/null)
if [ $? -eq 0 ] && [ -n "$DASHBOARD_RESPONSE" ]; then
    echo -e "${GREEN}✅ Dashboard API responds${NC}"
    DASHBOARD_OK=true
else
    echo -e "${RED}❌ Dashboard API failed${NC}"
    DASHBOARD_OK=false
fi

# 4. Check frontend files
echo -e "\n${BOLD}4. Checking Frontend Files${NC}"
if [ -d "$DIR/frontend/dist" ] && [ -f "$DIR/frontend/dist/index.html" ]; then
    echo -e "${GREEN}✅ Frontend dist exists${NC}"
    FRONTEND_EXISTS=true
else
    echo -e "${RED}❌ Frontend dist missing${NC}"
    FRONTEND_EXISTS=false
fi

# 5. Check database
echo -e "\n${BOLD}5. Checking Database${NC}"
if [ -f "$DIR/backend/data/ai-orchestrator.db" ]; then
    echo -e "${GREEN}✅ Database file exists${NC}"
    DB_EXISTS=true
else
    echo -e "${RED}❌ Database file missing${NC}"
    DB_EXISTS=false
fi

# 6. Check logs for errors
echo -e "\n${BOLD}6. Checking Recent Logs${NC}"
if [ -d "$DIR/backend/data/logs" ]; then
    RECENT_ERRORS=$(find "$DIR/backend/data/logs" -name "*.log" -mtime -1 -exec grep -l "ERROR\|Failed\|Exception" {} \; 2>/dev/null | wc -l)
    if [ "$RECENT_ERRORS" -gt 0 ]; then
        echo -e "${YELLOW}⚠️  Found $RECENT_ERRORS log files with errors in last 24h${NC}"
        LOG_ERRORS=true
    else
        echo -e "${GREEN}✅ No recent error logs${NC}"
        LOG_ERRORS=false
    fi
else
    echo -e "${YELLOW}⚠️  No logs directory${NC}"
fi

# 7. Check database schema
echo -e "\n${BOLD}7. Checking Database Schema${NC}"
if [ -f "$DIR/backend/data/ai-orchestrator.db" ]; then
    # Check if thinking_process column exists
    if python3 -c "
import sqlite3
conn = sqlite3.connect('$DIR/backend/data/ai-orchestrator.db')
cursor = conn.cursor()
cursor.execute('PRAGMA table_info(messages)')
columns = [row[1] for row in cursor.fetchall()]
conn.close()
print('thinking_process' in columns)
" 2>/dev/null | grep -q "True"; then
        echo -e "${GREEN}✅ Database schema is up to date${NC}"
        SCHEMA_OK=true
    else
        echo -e "${RED}❌ Database schema needs migration${NC}"
        SCHEMA_OK=false
    fi
else
    echo -e "${YELLOW}⚠️  Database file not found${NC}"
    SCHEMA_OK=false
fi

echo -e "\n${BOLD}📋 TROUBLESHOOTING SUMMARY${NC}"
echo "=========================="
echo "Backend Running: $([ "$BACKEND_RUNNING" = true ] && echo "${GREEN}YES${NC}" || echo "${RED}NO${NC}")"
echo "Health Endpoint: $([ "$HEALTH_OK" = true ] && echo "${GREEN}OK${NC}" || echo "${RED}FAIL${NC}")"
echo "Dashboard API: $([ "$DASHBOARD_OK" = true ] && echo "${GREEN}OK${NC}" || echo "${RED}FAIL${NC}")"
echo "Frontend Built: $([ "$FRONTEND_EXISTS" = true ] && echo "${GREEN}YES${NC}" || echo "${RED}NO${NC}")"
echo "Database Exists: $([ "$DB_EXISTS" = true ] && echo "${GREEN}YES${NC}" || echo "${RED}NO${NC}")"
echo "Schema Updated: $([ "$SCHEMA_OK" = true ] && echo "${GREEN}YES${NC}" || echo "${RED}NO${NC}")"
echo "Recent Errors: $([ "$LOG_ERRORS" = true ] && echo "${YELLOW}YES${NC}" || echo "${GREEN}NO${NC}")"

# Auto-fix suggestions
echo -e "\n${BOLD}🔧 AUTO-FIX SUGGESTIONS${NC}"
echo "========================"

FIXES_APPLIED=false

# Fix 1: Restart backend if not running
if [ "$BACKEND_RUNNING" = false ]; then
    echo -e "\n${YELLOW}Fix 1: Starting backend...${NC}"
    cd "$DIR"
    bash scripts/stop.sh 2>/dev/null
    sleep 2
    bash scripts/start.sh &
    sleep 5
    if pgrep -f "uvicorn main:app" > /dev/null; then
        echo -e "${GREEN}✅ Backend started successfully${NC}"
        FIXES_APPLIED=true
    else
        echo -e "${RED}❌ Failed to start backend${NC}"
    fi
fi

# Fix 3: Run database migration if schema outdated
if [ "$SCHEMA_OK" = false ] && [ "$DB_EXISTS" = true ]; then
    echo -e "\n${YELLOW}Fix 3: Running database migration...${NC}"
    cd "$DIR"
    python3 migrate_thinking_process.py
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Database migration completed${NC}"
        FIXES_APPLIED=true
        SCHEMA_OK=true
    else
        echo -e "${RED}❌ Database migration failed${NC}"
    fi
fi

# Fix 3: Test again after fixes
if [ "$FIXES_APPLIED" = true ]; then
    echo -e "\n${BOLD}🔄 Testing after fixes...${NC}"
    sleep 3

    # Test health
    if curl -s --max-time 5 http://localhost:7860/api/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Health endpoint OK${NC}"
    else
        echo -e "${RED}❌ Health endpoint still failing${NC}"
    fi

    # Test dashboard
    if curl -s --max-time 10 http://localhost:7860/api/monitoring/dashboard > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Dashboard API OK${NC}"
    else
        echo -e "${RED}❌ Dashboard API still failing${NC}"
    fi
fi

echo -e "\n${BOLD}🎯 FINAL STATUS${NC}"
echo "==============="
if curl -s --max-time 5 http://localhost:7860/api/health > /dev/null 2>&1 && \
   curl -s --max-time 10 http://localhost:7860/api/monitoring/dashboard > /dev/null 2>&1; then
    echo -e "${GREEN}✅ ALL SYSTEMS OPERATIONAL${NC}"
    echo -e "${GREEN}🌐 Dashboard should now load at: http://localhost:7860${NC}"
else
    echo -e "${RED}❌ ISSUES STILL EXIST${NC}"
    echo -e "${YELLOW}Manual intervention required. Check logs in backend/data/logs/${NC}"
fi

echo -e "\n${BOLD}📞 Support${NC}"
echo "If issues persist, check:"
echo "1. Backend logs: tail -f backend/data/logs/*.log"
echo "2. Browser console for frontend errors"
echo "3. Network tab for failed API calls"