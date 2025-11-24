# 🧪 Testing Guide: ADK-Aligned Architecture

This guide shows you how to test your new ADK-aligned framework using multiple methods.

---

## 📋 **Prerequisites**

1. ✅ Docker and Docker Compose installed
2. ✅ `.env` file with `GOOGLE_API_KEY` set
3. ✅ Phase 2 completed (ADK Runner integration)

---

## 🚀 **Method 1: Quick Test Script** (Recommended First)

Run the automated test script to verify everything works:

```bash
# Install dependencies (if not already done)
pip install -r requirements.txt

# Run tests
python test_adk_runner.py
```

**What it tests:**
- ✅ Agent loading with ADKAgentAdapter
- ✅ Streaming execution via MultiTenantRunner
- ✅ Session persistence (memory across messages)
- ✅ Multi-tenancy isolation (tenant A cannot access tenant B's data)
- ✅ Health checks

**Expected output:**
```
🧪 ADK RUNNER INTEGRATION TESTS
============================================================
TEST 1: Agent Loading
✅ Loaded 1 agent adapters:
   - template_simple_agent: A friendly workshop assistant

TEST 2: Streaming Execution
✅ Streaming completed
✅ TEST 2 PASSED: Received 15 chunks, 234 chars

TEST 3: Session Persistence
✅ TEST 3 PASSED: Agent remembered the name 'Alice'!

TEST 4: Multi-Tenancy Isolation
✅ TEST 4 PASSED: Multi-tenancy isolation working!

TEST 5: Health Checks
✅ HEALTHY - template_simple_agent

✅ ALL TESTS PASSED!
```

---

## 🌐 **Method 2: ADK Web Interface** (Visual Testing)

ADK Web provides a visual interface to interact with your agents.

### **Step 1: Start Services**

```bash
# Start backend + Redis + ADK Web
docker compose --profile dev up -d

# Check logs
docker compose logs -f adk-web
docker compose logs -f api
```

### **Step 2: Access ADK Web**

Open your browser to:
```
http://localhost:3002
```

### **Step 3: Test Your Agent**

1. **Select Agent**: Choose `template_simple_agent` from the dropdown
2. **Start Conversation**: Type a message like "Hello, what can you do?"
3. **Test Tools**: Try asking:
   - "What is the current time?"
   - "Tell me about the company"
   - "What's on the workshop roadmap?"

### **Step 4: Verify ADK Runner Integration**

Check the backend logs to see ADK Runner in action:

```bash
docker compose logs -f api | grep -i "runner\|adapter\|session"
```

You should see logs like:
```
INFO - MultiTenantRunner initialized for 'template_simple_agent'
INFO - ADKAgentAdapter created for agent 'template_simple_agent'
INFO - Executing agent 'template_simple_agent' for tenant=default
```

---

## 🔌 **Method 3: FastAPI Endpoints** (API Testing)

Test via the FastAPI backend using curl or the Swagger UI.

### **Option A: Swagger UI** (Interactive)

1. Open: http://localhost:8000/docs
2. Navigate to `/api/agents/stream` endpoint
3. Click "Try it out"
4. Enter test data:
   ```json
   {
     "message": "Hello, what can you help me with?",
     "session_id": "test123",
     "tenant_id": "acme-corp",
     "agent_name": "template_simple_agent"
   }
   ```
5. Click "Execute"

### **Option B: curl** (Command Line)

```bash
# Test 1: Simple message
curl -X POST http://localhost:8000/api/agents/stream \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello, what can you do?",
    "session_id": "session123",
    "tenant_id": "acme-corp",
    "agent_name": "template_simple_agent"
  }'

# Test 2: Session persistence (message 1)
curl -X POST http://localhost:8000/api/agents/stream \
  -H "Content-Type: application/json" \
  -d '{
    "message": "My name is Bob. Remember this.",
    "session_id": "persist_test",
    "tenant_id": "acme-corp",
    "agent_name": "template_simple_agent"
  }'

# Test 3: Session persistence (message 2 - should remember Bob)
curl -X POST http://localhost:8000/api/agents/stream \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is my name?",
    "session_id": "persist_test",
    "tenant_id": "acme-corp",
    "agent_name": "template_simple_agent"
  }'

# Test 4: Multi-tenancy (Tenant A)
curl -X POST http://localhost:8000/api/agents/stream \
  -d '{
    "message": "My secret is ALPHA",
    "session_id": "s1",
    "tenant_id": "tenant-a",
    "agent_name": "template_simple_agent"
  }'

# Test 5: Multi-tenancy (Tenant B - should NOT see ALPHA)
curl -X POST http://localhost:8000/api/agents/stream \
  -d '{
    "message": "What is my secret?",
    "session_id": "s1",
    "tenant_id": "tenant-b",
    "agent_name": "template_simple_agent"
  }'
```

---

## 🔍 **Method 4: WebSocket Testing** (Real-time Streaming)

Test the WebSocket endpoint for real-time streaming.

### **Using wscat:**

```bash
# Install wscat
npm install -g wscat

# Connect to WebSocket
wscat -c "ws://localhost:8000/ws/chat?session_id=test123&agent_name=template_simple_agent&tenant_id=acme"

# Send message (after connected)
{"message": "Hello, what can you do?"}

# You should see streaming chunks in real-time
```

### **Using Python:**

```python
import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://localhost:8000/ws/chat?session_id=test123&agent_name=template_simple_agent&tenant_id=acme"
    
    async with websockets.connect(uri) as websocket:
        # Send message
        await websocket.send(json.dumps({
            "message": "Hello, what can you do?"
        }))
        
        # Receive streaming chunks
        async for message in websocket:
            data = json.loads(message)
            print(data)
            
            if data.get("type") == "complete":
                break

asyncio.run(test_websocket())
```

---

## 📊 **Verification Checklist**

After testing, verify these key features:

### **✅ ADK Runner Integration**
- [ ] Agents load with ADKAgentAdapter
- [ ] MultiTenantRunner executes successfully
- [ ] Streaming works via ADK Runner
- [ ] No errors in logs

### **✅ Session Persistence**
- [ ] Agent remembers information across messages
- [ ] Session state persists in Redis
- [ ] Can retrieve session history

### **✅ Multi-Tenancy**
- [ ] Different tenants have isolated sessions
- [ ] Tenant A cannot access Tenant B's data
- [ ] Session IDs are scoped by tenant

### **✅ Tools & Features**
- [ ] Agent tools work (get_current_time, get_company_info, etc.)
- [ ] Streaming responses work
- [ ] Error handling works
- [ ] Health checks return correct status

---

## 🐛 **Troubleshooting**

### **Issue: "Agent not found"**
```bash
# Check loaded agents
docker compose exec api python -c "
from agents.manager import AgentManager
import asyncio
async def check():
    m = AgentManager()
    await m.initialize()
    print('Loaded agents:', list(m.adapters.keys()))
asyncio.run(check())
"
```

### **Issue: "Session not persisting"**
```bash
# Check Redis connection
docker compose exec redis redis-cli KEYS "session:*"

# Check session data
docker compose exec redis redis-cli GET "session:acme-corp:test123"
```

### **Issue: "ADK Runner errors"**
```bash
# Check detailed logs
docker compose logs -f api | grep -i "error\|exception\|traceback"

# Restart services
docker compose down
docker compose --profile dev up -d
```

### **Issue: "ADK Web not loading"**
```bash
# Check ADK Web logs
docker compose logs adk-web

# Verify port is accessible
curl http://localhost:3002

# Rebuild if needed
docker compose build adk-web
docker compose --profile dev up -d adk-web
```

---

## 📈 **Performance Testing**

Test with multiple concurrent requests:

```bash
# Install Apache Bench
# macOS: brew install httpd
# Ubuntu: sudo apt-get install apache2-utils

# Run 100 requests with 10 concurrent
ab -n 100 -c 10 -p test_payload.json -T application/json \
  http://localhost:8000/api/agents/stream

# Create test_payload.json:
echo '{
  "message": "Hello",
  "session_id": "perf_test",
  "tenant_id": "test",
  "agent_name": "template_simple_agent"
}' > test_payload.json
```

---

## 🎯 **Next Steps After Testing**

Once all tests pass:

1. ✅ **Phase 3: Security** - Add API keys, rate limiting
2. ✅ **Phase 4: Vertex AI Memory** - Long-term memory across sessions
3. ✅ **Phase 5: Monitoring** - Prometheus metrics, Cloud Trace
4. ✅ **Production Deployment** - Deploy to GCP (Cloud Run or Vertex AI Agent Engine)

---

## 📚 **Additional Resources**

- [ADK Documentation](https://google.github.io/adk-docs/)
- [ADK Web GitHub](https://github.com/google/adk-web)
- [FastAPI WebSocket Docs](https://fastapi.tiangolo.com/advanced/websockets/)
- [Redis Session Testing](https://redis.io/commands/)

---

**Happy Testing! 🚀**

