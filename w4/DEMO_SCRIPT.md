# GeekBrain AI System — Full Demo Script (L1–L4)

## Chuẩn Bị Demo (5 phút trước)

### 1. Kiểm Tra và Khởi Động Services

```bash
# Terminal 1: Start Monitoring API (port 8000)
cd w4
source venv/bin/activate
python monitoring_api.py &

# Terminal 2: Start Main API (port 8001)
cd w4/src
source ../venv/bin/activate
python main.py &

# Đợi 5 giây để cả 2 servers khởi động
sleep 5
```

### 2. Verify Tất Cả Services Running

```bash
# Health check — Main API
curl -s http://localhost:8001/health | jq

# Expected:
# { "status": "healthy", "knowledge_base_configured": true }

# Health check — Monitoring API
curl -s http://localhost:8000/services | jq

# Expected: ["PaymentGW", "NotificationSvc", ...]
```

### 3. Set Environment Variables (nếu chưa set)

```bash
export BEDROCK_KB_ID="8IT6QXNDFJ"
export AWS_DEFAULT_REGION="us-east-1"
```

---

## Demo Flow (10–12 phút)

### Part 1: Giới Thiệu Hệ Thống (1 phút)

> "Hôm nay tôi sẽ demo GeekBrain AI System — hệ thống AI Q&A có 4 levels:
> - L1: Simple RAG — truy vấn Knowledge Base
> - L2: Multi-Source RAG — xử lý xung đột tài liệu
> - L3: Tool-Augmented — query database & monitoring API
> - L4: Memory-Enabled — hội thoại nhiều lượt, giải quyết đại từ"

---

### Part 2: Demo L1 — Simple RAG (2 phút)

**Query 1:** Team information

```bash
curl -s -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Who is the Team Platform lead?", "level": "L1"}' | jq
```

> ✅ Expected: "Alex Chen" với source citation `team_platform.md`
> ✅ Response time: < 5 giây

**Query 2:** Policy information

```bash
curl -s -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the deployment freeze window?", "level": "L1"}' | jq
```

> ✅ Expected: "Friday 18:00 đến Monday 08:00" từ `deployment_policy.md`

---

### Part 3: Demo L2 — Conflict Resolution (2 phút)

**Query:** Version conflict

```bash
curl -s -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is PaymentGW'\''s API rate limit?", "level": "L2"}' | jq
```

> ✅ Expected: **1,000 req/min** (v2), ghi chú v1 là 500 req/min đã bị supersede
> "Hệ thống phát hiện xung đột giữa api_reference_v1.md (500) và v2.md (1000), ưu tiên phiên bản mới hơn."

---

### Part 4: Demo L3 — Tool-Augmented RAG (3 phút)

**Query 1:** Historical database query (exact numbers)

```bash
curl -s -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What was PaymentGW'\''s total infrastructure cost in Q1 2026?", "level": "L3"}' | jq
```

> ✅ Expected: **$16,500** (chính xác từ database tool)
> ✅ `tools_used: ["query_database"]`
> "Lưu ý: con số $16,500 lấy TRỰC TIẾP từ database bằng SQL query, không phải từ documents."

**Query 2:** Live monitoring API

```bash
curl -s -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is PaymentGW'\''s current p99 latency?", "level": "L3"}' | jq
```

> ✅ Expected: ~185ms (real-time từ monitoring API)
> ✅ `tools_used: ["get_service_metrics"]`

**Query 3:** Multi-tool (database + API)

```bash
curl -s -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Is NotificationSvc meeting its SLA targets?", "level": "L3"}' | jq
```

> ✅ Expected: ❌ Not meeting SLA — current p99 3200ms > target 2000ms
> ✅ `tools_used: ["query_database", "get_service_metrics"]`
> "Hệ thống dùng CẢ HAI tools: database cho SLA target, monitoring API cho current metrics, rồi so sánh."

---

### Part 5: Demo L4 — Memory-Enabled Multi-Turn (3 phút)

> "Đây là phần quan trọng nhất — hội thoại 4 lượt với pronoun resolution."

**Turn 1:** Establish entity

```bash
curl -s -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Service nào có chi phí cao nhất tháng 3/2026?",
    "level": "L4",
    "session_id": "demo-session-001"
  }' | jq
```

> ✅ Expected: "PaymentGW với $7,500"

**Turn 2:** Pronoun "nó" → PaymentGW

```bash
curl -s -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Tại sao chi phí của nó tăng đột biến?",
    "level": "L4",
    "session_id": "demo-session-001"
  }' | jq
```

> ✅ Expected: Giải thích liên quan đến PaymentGW (postmortem, scaling event)
> "Hệ thống resolve 'nó' = PaymentGW từ Turn 1."

**Turn 3:** Implicit entity

```bash
curl -s -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Team nào chịu trách nhiệm?",
    "level": "L4",
    "session_id": "demo-session-001"
  }' | jq
```

> ✅ Expected: "Team Platform, do Alex Chen lãnh đạo"

**Turn 4:** Full context chain

```bash
curl -s -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Deadline review postmortem đã qua chưa?",
    "level": "L4",
    "session_id": "demo-session-001"
  }' | jq
```

> ✅ Expected: Trả lời về deadline postmortem PaymentGW

> "Qua 4 turns, hệ thống duy trì context liên tục: PaymentGW → chi phí → team → postmortem. Tất cả đều dùng cùng session_id."

---

### Part 6: Show Test Results (1 phút)

```bash
# Unit tests (không cần AWS)
cd w4
source venv/bin/activate
python -m pytest tests/unit/ -v --tb=short | tail -5
# → 81 passed ✅
```

> "81 unit tests pass, bao gồm tests cho memory, tools, và RAG pipeline."

---

## Q&A Preparation

| Câu Hỏi | Trả Lời |
|----------|---------|
| Tại sao dùng Window Memory? | Bounded context (5 turns), không overflow, đủ cho demo 4-turn. Query Rewriting cần thêm 1 LLM call mỗi turn → gấp đôi latency. |
| Cost per query? | ~$0.003–0.015 (KB retrieve + Claude Sonnet inference). 1000 queries/day ≈ $3–15/day. |
| Sao response time L3 lâu hơn L1? | L3 có thêm tool execution loop: LLM quyết định tool → execute → gửi kết quả lại LLM → generate. Mỗi iteration ~2-3s. |
| Pronoun resolution hoạt động sao? | Không dùng NLP riêng — inject conversation history vào system prompt, Claude tự resolve "nó"/"its" dựa trên context. |
| Production readiness? | ✅ Functional, ✅ Tested. Cần thêm: rate limiting, authentication, CloudWatch monitoring, DynamoDB for persistent sessions. |

---

## Fallback Plan

Nếu live demo fail:
1. **Backup screenshots** trong Evidence Pack (`docs/W4_evidence.md`)
2. **Show test output**: `python -m pytest tests/integration/ -v -s`
3. **Show architecture diagram**: `docs/architecture_diagram.md`

---

## Checklist Sau Demo

- [ ] Stop servers: `pkill -f "python main.py" && pkill -f "python monitoring_api.py"`
- [ ] Commit: `git add w4/ && git commit -m "W4 GeekBrain AI System - L1 to L4 complete"`
- [ ] Post commit link to Slack
