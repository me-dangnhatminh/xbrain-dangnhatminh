# Hướng Dẫn Test Hệ Thống GeekBrain AI

## 📊 Tổng Quan Tiến Độ

### ✅ Đã Hoàn Thành (L1, L2, L3)

#### Phase 1: Setup & Data ✅
- ✅ Phân tích 36 markdown documents và 4 CSV files
- ✅ Setup Python project structure (src/, tests/, docs/)
- ✅ Seed database SQLite với dữ liệu từ CSV
- ✅ Chạy Monitoring API (FastAPI) trên port 8000
- ✅ Tạo architecture diagram

#### Phase 2: L1 - Simple RAG ✅
- ✅ Upload documents lên S3
- ✅ Tạo Bedrock Knowledge Base với OpenSearch Serverless
- ✅ Implement RAGPipeline class (retrieve, retrieve_and_generate)
- ✅ Tạo FastAPI endpoint `/query`
- ✅ Unit tests và integration tests cho L1

#### Phase 3: L2 - Multi-Source RAG ✅
- ✅ Tăng top_k từ 5 lên 10 chunks
- ✅ Implement conflict resolution trong system prompt
- ✅ Test với queries có conflicting information

#### Phase 4: L3 - Tool-Augmented RAG ✅
- ✅ Implement 7 tools:
  - DatabaseQueryTool (query historical data)
  - ServiceMetricsTool (get live metrics)
  - ServiceStatusTool (get service status)
  - ListServicesTool (list all services)
  - IncidentHistoryTool (get incident history)
  - TeamInfoTool (get team info from RAG)
  - CompareServicesTool (compare metrics)
- ✅ Implement ToolOrchestrator với tool execution loop
- ✅ System prompt cho L3 với tool selection guidance

### ⏳ Chưa Hoàn Thành (L4)

#### Phase 5: L4 - Memory-Enabled RAG ⏳
- ⏳ Implement MemoryManager base class
- ⏳ Implement WindowMemory strategy
- ⏳ Integrate memory với orchestrator
- ⏳ Pronoun resolution trong multi-turn conversations

---

## 🚀 Cách Test Hệ Thống

### 1️⃣ Khởi Động Services

#### Bước 1: Activate Virtual Environment
```bash
cd w4
source venv/bin/activate  # Linux/Mac
# hoặc
venv\Scripts\activate  # Windows
```

#### Bước 2: Khởi Động Monitoring API
```bash
# Terminal 1
cd w4
python monitoring_api.py
```

Kiểm tra API đang chạy:
```bash
curl http://localhost:8000/services
```

#### Bước 3: Khởi Động Main API
```bash
# Terminal 2
cd w4/src
uvicorn main:app --reload --port 8001
```

API sẽ chạy tại: `http://localhost:8001`

---

### 2️⃣ Test L1 - Simple RAG

**Mục đích**: Test retrieval từ Knowledge Base với source citation

#### Test Query 1: Team Information
```bash
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Who is the Team Platform lead?",
    "level": "L1"
  }'
```

**Kết quả mong đợi**:
- Answer: "Alex Chen"
- Sources: ["team_platform.md"]
- Processing time: < 5 seconds

#### Test Query 2: Policy Information
```bash
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the deployment freeze window?",
    "level": "L1"
  }'
```

**Kết quả mong đợi**:
- Answer: "Friday 18:00 to Monday 08:00"
- Sources: [deployment policy document]

#### Test bằng Python:
```python
import requests

response = requests.post(
    "http://localhost:8001/query",
    json={
        "query": "Who is the Team Platform lead?",
        "level": "L1"
    }
)

print(response.json())
```

---

### 3️⃣ Test L2 - Multi-Source RAG

**Mục đích**: Test conflict resolution và multi-document synthesis

#### Test Query 1: Conflict Resolution
```bash
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is PaymentGW API rate limit?",
    "level": "L2"
  }'
```

**Kết quả mong đợi**:
- Answer: "1000 req/min" (từ v2)
- Explanation: Mentions v1 was 500 req/min, v2 is current
- Sources: ["api_reference_v1.md", "api_reference_v2.md"]
- Processing time: < 8 seconds

#### Test Query 2: Multi-Document Synthesis
```bash
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Can Team Commerce deploy on Friday night?",
    "level": "L2"
  }'
```

**Kết quả mong đợi**:
- Synthesizes info from deployment_policy.md và team info
- Answer: No (deployment freeze window)

---

### 4️⃣ Test L3 - Tool-Augmented RAG

**Mục đích**: Test tool execution với database queries và monitoring API

#### Test Query 1: Database Query (Historical Data)
```bash
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What was PaymentGW total cost in Q1 2026?",
    "level": "L3"
  }'
```

**Kết quả mong đợi**:
- Answer: "$16,500" (EXACT value, không làm tròn)
- Tools used: ["query_database"]
- Sources: ["query_database tool"]
- Processing time: < 10 seconds

#### Test Query 2: Monitoring API (Live Data)
```bash
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is PaymentGW current p99 latency?",
    "level": "L3"
  }'
```

**Kết quả mong đợi**:
- Answer: "~185ms" (from live API)
- Tools used: ["get_service_metrics"]
- Sources: ["get_service_metrics tool"]

#### Test Query 3: Combined (Database + Monitoring API)
```bash
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Is NotificationSvc meeting its SLA targets?",
    "level": "L3"
  }'
```

**Kết quả mong đợi**:
- Calls both tools:
  1. `query_database` để lấy SLA target (2000ms p99)
  2. `get_service_metrics` để lấy current p99 (~3200ms)
- Answer: "No, NotificationSvc is NOT meeting SLA" (3200ms > 2000ms)
- Tools used: ["query_database", "get_service_metrics"]

#### Test Query 4: Service Status
```bash
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the current status of all services?",
    "level": "L3"
  }'
```

**Kết quả mong đợi**:
- Tools used: ["list_services", "get_service_status"]
- Lists all 6 services with their status

#### Test Query 5: Team Info (RAG Tool)
```bash
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Who are the members of Team Platform?",
    "level": "L3"
  }'
```

**Kết quả mong đợi**:
- Tools used: ["get_team_info"]
- Answer includes team lead and members

---

### 5️⃣ Test L4 - Memory-Enabled RAG (Chưa implement)

**Mục đích**: Test multi-turn conversation với pronoun resolution

#### Test Conversation (4 turns):

**Turn 1:**
```bash
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Which service had highest cost in March 2026?",
    "level": "L4",
    "session_id": "test-session-1"
  }'
```
Expected: "PaymentGW at $7,500"

**Turn 2:**
```bash
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Why did its costs spike?",
    "level": "L4",
    "session_id": "test-session-1"
  }'
```
Expected: Resolves "its" to PaymentGW, retrieves postmortem

**Turn 3:**
```bash
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Which team is responsible?",
    "level": "L4",
    "session_id": "test-session-1"
  }'
```
Expected: "Team Platform, led by Alex Chen"

**Turn 4:**
```bash
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Is the postmortem review deadline overdue?",
    "level": "L4",
    "session_id": "test-session-1"
  }'
```
Expected: Maintains context about PaymentGW postmortem

---

## 🧪 Chạy Unit Tests

```bash
cd w4

# Chạy tất cả tests
pytest

# Chạy tests cho một module cụ thể
pytest tests/unit/test_rag_pipeline.py -v
pytest tests/unit/test_tools.py -v
pytest tests/unit/test_tool_orchestrator.py -v

# Chạy integration tests
pytest tests/integration/ -v

# Chạy với coverage
pytest --cov=src --cov-report=html
```

---

## 📝 Test Script Python

Tạo file `test_queries.py`:

```python
import requests
import json
from typing import Dict, Any

API_URL = "http://localhost:8001/query"

def test_query(query: str, level: str, session_id: str = None) -> Dict[str, Any]:
    """Send a test query to the API."""
    payload = {
        "query": query,
        "level": level
    }
    if session_id:
        payload["session_id"] = session_id
    
    response = requests.post(API_URL, json=payload)
    result = response.json()
    
    print(f"\n{'='*60}")
    print(f"Query: {query}")
    print(f"Level: {level}")
    print(f"{'='*60}")
    print(f"Answer: {result.get('answer', 'N/A')}")
    print(f"Sources: {result.get('sources', [])}")
    print(f"Tools Used: {result.get('tools_used', [])}")
    print(f"Processing Time: {result.get('processing_time', 0):.2f}s")
    print(f"{'='*60}\n")
    
    return result

# Test L1
print("🔵 Testing L1 - Simple RAG")
test_query("Who is the Team Platform lead?", "L1")
test_query("What is the deployment freeze window?", "L1")

# Test L2
print("🟢 Testing L2 - Multi-Source RAG")
test_query("What is PaymentGW API rate limit?", "L2")

# Test L3
print("🟡 Testing L3 - Tool-Augmented RAG")
test_query("What was PaymentGW total cost in Q1 2026?", "L3")
test_query("What is PaymentGW current p99 latency?", "L3")
test_query("Is NotificationSvc meeting its SLA targets?", "L3")

# Test L4 (when implemented)
# print("🔴 Testing L4 - Memory-Enabled RAG")
# session = "test-session-1"
# test_query("Which service had highest cost in March 2026?", "L4", session)
# test_query("Why did its costs spike?", "L4", session)
# test_query("Which team is responsible?", "L4", session)
```

Chạy:
```bash
python test_queries.py
```

---

## 🔍 Debug & Troubleshooting

### Kiểm tra Monitoring API
```bash
# List all services
curl http://localhost:8000/services

# Get metrics for a service
curl http://localhost:8000/metrics/PaymentGW

# Get status for a service
curl http://localhost:8000/status/PaymentGW
```

### Kiểm tra Database
```bash
cd w4
sqlite3 geekbrain.db

# Check tables
.tables

# Query data
SELECT * FROM monthly_costs WHERE service='PaymentGW';
SELECT * FROM sla_targets;
SELECT * FROM incidents LIMIT 5;
```

### Kiểm tra Bedrock KB
```python
import boto3

bedrock_agent = boto3.client('bedrock-agent-runtime')

# Test retrieval
response = bedrock_agent.retrieve(
    knowledgeBaseId='YOUR_KB_ID',
    retrievalQuery={'text': 'Team Platform lead'}
)

print(response['retrievalResults'])
```

### Common Issues

**Issue 1: API không chạy**
- Check port 8001 có bị chiếm không: `lsof -i :8001`
- Check logs trong terminal

**Issue 2: Monitoring API timeout**
- Verify monitoring_api.py đang chạy trên port 8000
- Check `curl http://localhost:8000/services`

**Issue 3: Database query fails**
- Verify geekbrain.db exists: `ls -la w4/geekbrain.db`
- Re-seed database: `python w4/seed_data.py`

**Issue 4: Bedrock KB không trả về results**
- Check KB sync status trong AWS Console
- Verify S3 bucket có documents
- Re-trigger sync: `cd w4/terraform && ./trigger_kb_sync.sh`

---

## 📊 Expected Test Results Summary

| Level | Query Type | Expected Time | Tools Used | Status |
|-------|-----------|---------------|------------|--------|
| L1 | Simple fact | < 5s | None | ✅ Ready |
| L2 | Conflict resolution | < 8s | None | ✅ Ready |
| L3 | Database query | < 10s | query_database | ✅ Ready |
| L3 | Live metrics | < 10s | get_service_metrics | ✅ Ready |
| L3 | Combined | < 10s | Multiple tools | ✅ Ready |
| L4 | Multi-turn | < 12s | Memory + tools | ⏳ Not implemented |

---

## 🎯 Next Steps

1. **Test L1-L3 thoroughly** với các queries khác nhau
2. **Measure response times** để verify performance targets
3. **Test error cases**: API down, invalid queries, etc.
4. **Implement L4** (Memory-Enabled RAG)
5. **Create Evidence Pack** với screenshots và logs
6. **Prepare demo script** cho presentation

---

## 📚 Tài Liệu Tham Khảo

- `w4/docs/API_USAGE.md` - API documentation
- `w4/docs/L1_COMPLETE_GUIDE.md` - L1 implementation guide
- `w4/docs/task_14_summary.md` - L3 tool orchestration details
- `w4/DEMO_SCRIPT.md` - Demo script template
- `w4/tests/TESTING.md` - Testing documentation
