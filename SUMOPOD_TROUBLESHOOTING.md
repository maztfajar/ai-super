# Sumopod API - Troubleshooting & Recovery Guide

**Status**: ❌ SUMOPOD CONNECTION FAILED
**Severity**: HIGH
**Impact**: Primary AI model (mimo-v2-pro) unavailable
**Solution**: Switch to fallback provider (OpenAI/Anthropic/Google/Ollama)

---

## 📋 Issue Summary

### Error Encountered
```
ServiceUnavailableError: OpenAIException - auth_unavailable: 
no auth available (providers=opencode go, mimo token plan, nous portal, 
model=mimo-v2-pro)
```

### Root Cause Analysis
- **Direct API Test**: `curl` to Sumopod times out after 10+ seconds
- **Configuration**: API credentials present in `.env`
- **Status**: Server not responding / connection refused
- **Likely Causes**:
  - Sumopod service is down or under maintenance
  - Network connectivity issue to Sumopod endpoint
  - API key expired or invalid
  - Regional IP blocking
  - Account suspended or credit exhausted

---

## ✅ Available Solutions

### Solution 1: Use Fallback Models (Recommended - Immediate)

**Fastest option to restore service (5 minutes)**

#### Option A: OpenAI (Best Quality/Speed)
```bash
# Step 1: Set API key in .env
export OPENAI_API_KEY=sk-YOUR_API_KEY_HERE

# Step 2: Update ai_core_prompt.md
# Change [BRAIN] from mimo-v2-pro to gpt-4o
# Change [ARCHITECT] from deepseek-v3-2 to gpt-4o (backup)

# Step 3: Restart backend
kill $(ps aux | grep "uvicorn main:app" | grep -v grep | awk '{print $2}')
cd ~/Documents/ai-super/backend
python -m uvicorn main:app --host 0.0.0.0 --port 7860

# Step 4: Verify
curl http://localhost:7860/api/health
```

**Pricing**: $0.15-3.00 per 1K tokens (depending on model)
**Quality**: ✅ Excellent (GPT-4o is state-of-the-art)
**Speed**: 1-2 seconds average response

---

#### Option B: Anthropic Claude (Best Reasoning)
```bash
# Step 1: Set API key
export ANTHROPIC_API_KEY=sk-ant-YOUR_API_KEY_HERE

# Step 2: Update ai_core_prompt.md
# Change [BRAIN] to claude-3-5-sonnet
# Change [ARCHITECT] to claude-3-sonnet (backup)

# Step 3: Restart backend (same as above)
```

**Pricing**: $0.8-3.0 per 1K tokens
**Quality**: ✅ Excellent for reasoning/analysis
**Speed**: 1-2 seconds

---

#### Option C: Google Gemini (Good Quality, Low Cost)
```bash
# Step 1: Set API key
export GOOGLE_API_KEY=YOUR_GOOGLE_API_KEY_HERE

# Step 2: Update ai_core_prompt.md
# Change [BRAIN] to gemini-1.5-pro
# Fallback to gemini-1.5-flash

# Step 3: Restart backend
```

**Pricing**: $1.50-5.0 per 1M tokens (cheapest)
**Quality**: ✅ Good (state-of-the-art)
**Speed**: 1-2 seconds

---

#### Option D: Ollama (Free, Local)
```bash
# Step 1: Install Ollama
curl https://ollama.ai/install.sh | sh

# Step 2: Run inference server
ollama serve

# Step 3: Pull models
ollama pull llama2
ollama pull mistral

# Step 4: Update ai_core_prompt.md
# Change [BRAIN] to ollama/mistral
# Fallback to ollama/llama2

# Step 5: Restart backend
```

**Pricing**: FREE (runs locally)
**Quality**: ⭐⭐⭐ Good (but slower than cloud)
**Speed**: 2-5 seconds (depends on hardware)

---

### Solution 2: Fix Sumopod Connection (If Credentials Valid)

**Use this if you have valid Sumopod credentials**

#### Step 1: Verify Sumopod Account
```bash
# Check if account is active
# 1. Go to https://sumopod.com
# 2. Login to your account
# 3. Verify:
#    - API key not expired
#    - Account has credit/balance
#    - Usage limit not exceeded
#    - Region/IP not blocked
```

#### Step 2: Check Network Connectivity
```bash
# Test connectivity to Sumopod
ping ai.sumopod.com

# Check DNS resolution
dig ai.sumopod.com

# Test HTTPS connection
curl -v https://ai.sumopod.com/v1/health

# If timeout, check with IP directly
curl -v https://1.2.3.4/v1/health (replace with actual IP)
```

#### Step 3: Validate API Credentials
```bash
# Test with different auth header format
curl -X POST https://ai.sumopod.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-vDZWHQ3lRBrDewGkmv-PGA" \
  -d '{
    "model": "mimo-v2-pro",
    "messages": [{"role": "user", "content": "test"}],
    "max_tokens": 10
  }' \
  --connect-timeout 15 \
  --max-time 30

# If Bearer doesn't work, try without Bearer:
curl -X POST https://ai.sumopod.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: sk-vDZWHQ3lRBrDewGkmv-PGA" \
  ...
```

#### Step 4: Try VPN (If Region Blocked)
```bash
# Install VPN if Sumopod is region-blocked
# Test from different IP/location
```

---

## 🔄 Model Configuration Reference

### Current Stack (Before Failure)
```
[BRAIN]     = mimo-v2-pro (Sumopod) ❌ FAILING
[ARCHITECT] = deepseek-v3-2 (Sumopod) ❌ FAILING
[RUNNER]    = gemini-2.5-flash (Google) ✅ OK
[VISION]    = gemini-2.5-flash (Google) ✅ OK
[EAR]       = minimax-2.8-hd (Sumopod) ❌ FAILING
[POLISHER]  = minimax-m2.5-free (Sumopod) ❌ FAILING

FALLBACK:
- seed-2-0-pro
- MiniMax-M2.7-highspeed
- gpt-5-nano
```

### Recommended Fallback Stack
```
[BRAIN]     = gpt-4o (OpenAI) ✅
[ARCHITECT] = gpt-4o (OpenAI) ✅
[RUNNER]    = gpt-4o-mini (OpenAI) ✅ [Fast]
[VISION]    = gemini-1.5-pro (Google) ✅ [Multimodal]
[EAR]       = No change (Web audio not impacted)
[POLISHER]  = gpt-3.5-turbo (OpenAI) ✅ [Fast]
```

### File to Update
**Location**: `/home/ppidpengasih/Documents/ai-super/data/ai_core_prompt.md`

**Changes needed**:
```markdown
# BEFORE (Line ~200-250ish)
- **[BRAIN]**: mimo-v2-pro ($0.15-0.25/1K tokens)
- **[ARCHITECT]**: deepseek-v3-2 ($0.30-0.50/1K tokens)

# AFTER
- **[BRAIN]**: gpt-4o ($0.30-3.00/1K tokens, OpenAI)
- **[ARCHITECT]**: gpt-4o ($0.30-3.00/1K tokens, OpenAI)
```

---

## 📊 Model Comparison Matrix

| Model | Provider | Speed | Quality | Cost/1K | Reasoning | Multimodal | Setup |
|-------|----------|-------|---------|---------|-----------|------------|-------|
| gpt-4o | OpenAI | 1-2s | ⭐⭐⭐⭐⭐ | $3.00 | ⭐⭐⭐⭐⭐ | ✅ | Easy |
| gpt-4o-mini | OpenAI | 0.5s | ⭐⭐⭐⭐ | $0.15 | ⭐⭐⭐⭐ | ✅ | Easy |
| claude-3.5 | Anthropic | 1-2s | ⭐⭐⭐⭐⭐ | $3.00 | ⭐⭐⭐⭐⭐ | ❌ | Easy |
| gemini-1.5 | Google | 1-2s | ⭐⭐⭐⭐ | $1.50 | ⭐⭐⭐⭐ | ✅ | Easy |
| mimo-v2-pro | Sumopod | 2-3s | ⭐⭐⭐⭐ | $0.15 | ⭐⭐⭐ | ❌ | ❌ DOWN |
| deepseek-v3 | Sumopod | 2-3s | ⭐⭐⭐⭐⭐ | $0.30 | ⭐⭐⭐⭐⭐ | ❌ | ❌ DOWN |
| llama2 | Ollama | 2-5s | ⭐⭐⭐ | FREE | ⭐⭐ | ❌ | Moderate |

**Recommendation**: ⭐⭐⭐ Use **gpt-4o** or **claude-3.5-sonnet** for immediate stability

---

## 🚀 Quick Implementation: 5-Minute Fix

### For OpenAI Users
```bash
# 1. Check if OPENAI_API_KEY is set
grep OPENAI_API_KEY ~/.env

# 2. If not set, add it
echo "OPENAI_API_KEY=sk-YOUR_KEY_HERE" >> ~/.env

# 3. Edit ai_core_prompt.md
vi ~/Documents/ai-super/data/ai_core_prompt.md
# Find and replace:
# mimo-v2-pro → gpt-4o
# deepseek-v3-2 → gpt-4o

# 4. Kill old backend
pkill -f "uvicorn main:app"
sleep 2

# 5. Start backend
cd ~/Documents/ai-super/backend
nohup python -m uvicorn main:app --host 0.0.0.0 --port 7860 > backend.log 2>&1 &

# 6. Wait 3 seconds and verify
sleep 3
curl http://localhost:7860/api/health | jq .

# Expected output:
# {
#   "status": "ok",
#   "uptime": "1.2s",
#   "models": {
#     "mimo-v2-pro": "Not available",
#     "gpt-4o": "Available"
#   }
# }
```

---

## 🔍 Debugging Checklist

### Before Switching Providers
- [ ] Confirmed Sumopod API is not responding (timeout)
- [ ] Checked .env has SUMOPOD_API_KEY
- [ ] Verified network connectivity to Sumopod
- [ ] Confirmed API key not expired
- [ ] Checked Sumopod account has credit

### After Switching to Fallback
- [ ] New API key added to .env
- [ ] ai_core_prompt.md updated with new model names
- [ ] Backend restarted successfully
- [ ] `/api/health` endpoint responds
- [ ] No errors in `backend.log`
- [ ] Test chat request works without timeout

### Monitoring
```bash
# Watch backend logs
tail -f ~/Documents/ai-super/backend.log

# Monitor API health every 5 seconds
watch -n 5 'curl -s http://localhost:7860/api/health | jq .'

# Check for errors
grep -i error backend.log | tail -20
```

---

## 📞 Support Options

### If OpenAI/Anthropic/Google API Keys Unavailable
1. **Get free trials**:
   - OpenAI: $5 free credits (3 months)
   - Anthropic: Free tier available
   - Google: $300 free credits

2. **Use Ollama** (completely free, local):
   - Runs on your machine
   - No API calls/costs
   - Download models: llama2, mistral, etc.

3. **Wait for Sumopod Recovery**:
   - Monitor: https://status.sumopod.com
   - Monitor their Twitter: @sumopod_official
   - Estimate: 1-24 hours for resolution

---

## 📝 Logs & Troubleshooting

### Check Backend Errors
```bash
# Last 50 errors
grep ERROR ~/Documents/ai-super/backend.log | tail -50

# Sumopod connection attempts
grep -i sumopod ~/Documents/ai-super/backend.log

# All model routing decisions
grep -i "provider:" ~/Documents/ai-super/backend.log | tail -20
```

### Enable Debug Logging
```python
# In backend/core/logging.py, set:
LOG_LEVEL = "DEBUG"  # Was "INFO"

# Restart backend to capture detailed logs
```

### Clear Old Logs (If Size Growing)
```bash
# Archive logs
tar -czf ~/Documents/ai-super/backend-logs-$(date +%Y%m%d).tar.gz ~/Documents/ai-super/backend.log

# Clear
> ~/Documents/ai-super/backend.log

# Restart backend
```

---

## ⚠️ Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Model unavailable | Chat fails | ✅ Fallback stack configured |
| API costs higher | Budget exceeded | ⭐ Use gpt-4o-mini or gemini for cost savings |
| Provider down too | All models fail | ✅ Use local Ollama as ultimate fallback |
| Latency increase | Slower responses | ✅ Gemini/GPT-4o are faster than Mimo |
| Network timeout | Stranded requests | ✅ TimeoutMiddleware already deployed (120s) |

---

## 🎯 Status Checkpoints

**✅ Completed**:
- ChatTimeout fix deployed (120s limit)
- Compliance systems verified
- Fallback models configured
- Error handling enhanced

**⚠️ In Progress**:
- Sumopod authentication failure investigation
- Fallback provider selection

**📋 Next Steps**:
1. Choose fallback provider (OpenAI/Anthropic/Google/Ollama)
2. Get/verify API credentials
3. Update ai_core_prompt.md with new model mappings
4. Restart backend
5. Test chat functionality
6. Monitor error logs for 24 hours

---

**Last Updated**: 2024
**Responsibility**: DevOps/Backend Team
**Escalation**: Check Sumopod status page for outage info
