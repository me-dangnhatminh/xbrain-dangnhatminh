# Dashboard Demo Cheat Sheet 🚀

Quick reference for demonstrating the Chat & Observability Dashboard.

---

## 🎯 Demo Flow (10 minutes)

### 1. Introduction (1 min)
"This is the GeekBrain AI Chat & Observability Dashboard — an interactive interface that lets you chat with the AI while seeing exactly how it processes your queries in real-time."

**Show**:
- Left panel: Chat interface
- Right panel: Observability (empty state)
- Level selector: L1, L2, L3, L4

---

### 2. L1 Demo — Simple RAG (2 min)

**Say**: "Let's start with L1 — Simple RAG. I'll ask about team information."

**Type**: `Who is the Team Platform lead?`

**Point out**:
- ✅ Query Received event (blue)
- ✅ Retrieval Completed: **5 chunks** from `team_platform.md`
  - Show relevance scores (0.8-0.9)
  - Show text previews
- ✅ Response Generated: "Alex Chen" with processing time

**Key Message**: "The system retrieved 5 relevant chunks from the knowledge base and used them to generate an accurate answer with source citation."

---

### 3. L2 Demo — Conflict Resolution (2 min)

**Say**: "Now L2 — Multi-Source RAG with conflict resolution."

**Switch to L2**, then type: `What is PaymentGW's API rate limit?`

**Point out**:
- ✅ Retrieval Completed: **10 chunks** (more than L1)
- ✅ Chunks from both `api_reference_v1.md` and `api_reference_v2.md`
- ✅ Answer: "1,000 req/min (v2 supersedes v1 which had 500)"

**Key Message**: "The system found conflicting information — v1 said 500, v2 said 1000 — and correctly chose the newer version while explaining the conflict."

---

### 4. L3 Demo — Tool Augmentation (3 min)

**Say**: "L3 is where it gets interesting — the AI can use tools to query databases and APIs."

**Switch to L3**, then type: `What was PaymentGW's total infrastructure cost in Q1 2026?`

**Point out**:
- ✅ Tool Executed: `query_database` (orange badge)
  - Show SQL query in parameters
  - Show result: `[{"total": 16500.0}]`
- ✅ Answer: "$16,500" (exact match from database)

**Say**: "Notice there's no retrieval — the AI knew this required numerical data and went straight to the database tool."

---

**Type**: `What is PaymentGW's current p99 latency?`

**Point out**:
- ✅ Tool Executed: `get_service_metrics`
  - Parameters: `{"service_name": "PaymentGW"}`
  - Result: Live metrics from monitoring API
- ✅ Answer: "185ms"

**Key Message**: "The AI can distinguish between historical data (database) and live metrics (monitoring API) and use the appropriate tool."

---

**Type**: `Is NotificationSvc meeting its SLA targets?`

**Point out**:
- ✅ Tool Executed #1: `query_database` (get SLA targets)
- ✅ Tool Executed #2: `get_service_metrics` (get current metrics)
- ✅ Answer: "❌ NOT meeting SLA" with comparison

**Key Message**: "The AI orchestrated multiple tools — first getting the SLA targets from the database, then getting current metrics, and finally comparing them to determine SLA breach."

---

### 5. L4 Demo — Multi-Turn Memory (2 min)

**Say**: "Finally, L4 — Multi-turn conversations with memory. Watch how the AI maintains context across turns."

**Switch to L4**, note the session ID

**Turn 1**: `Service nào có chi phí cao nhất tháng 3/2026?`

**Point out**:
- ✅ Memory Loaded: 0 turns (new session)
- ✅ Tool Executed: `query_database`
- ✅ Answer: "PaymentGW với $7,500"

---

**Turn 2**: `Tại sao chi phí của nó tăng đột biến?`

**Point out**:
- ✅ Memory Loaded: **1 turn** (previous Q&A)
- ✅ System resolved "nó" → PaymentGW from context
- ✅ Retrieval from postmortem document
- ✅ Answer: Explanation of scaling incident

**Key Message**: "The AI understood 'nó' (it) refers to PaymentGW from the previous turn — no need to repeat context."

---

**Turn 3**: `Team nào chịu trách nhiệm?`

**Point out**:
- ✅ Memory Loaded: **2 turns**
- ✅ System knows we're still talking about PaymentGW
- ✅ Answer: "Team Platform, Alex Chen"

**Key Message**: "The conversation flows naturally — the AI maintains full context without you having to repeat 'PaymentGW' every time."

---

## 🎨 Visual Highlights

### Event Colors
- 🔵 Blue = Query Received
- 🟢 Green = Retrieval Completed
- 🟠 Orange = Tool Executed
- 🟣 Purple = LLM Invoked
- 🔴 Red = Response Generated
- 🔷 Cyan = Memory Loaded (L4)

### Key UI Elements
- **Level badges**: Color-coded (L1=green, L2=blue, L3=orange, L4=purple)
- **Tool badges**: Orange with tool name
- **Processing time**: Red badge with milliseconds
- **Timeline**: Vertical line connecting events
- **Auto-scroll**: Both panels scroll to latest content

---

## 💡 Demo Tips

### Do's ✅
- **Start simple** (L1) and build up complexity
- **Point to the screen** when highlighting events
- **Pause** after each query to let events populate
- **Explain the "why"** — why did it use this tool? Why these chunks?
- **Show real-time updates** — watch events appear progressively

### Don'ts ❌
- Don't rush — let the observability panel populate
- Don't skip L1/L2 — they set the foundation
- Don't use queries that might fail (check beforehand)
- Don't forget to switch levels between demos
- Don't ignore the observability panel — it's the star!

---

## 🔥 Backup Queries (If Something Fails)

### L1 Backups
```
What is the deployment freeze window?
Who are the members of Team Platform?
What is the incident response process?
```

### L2 Backups
```
What are the monitoring requirements?
What is the backup retention policy?
```

### L3 Backups
```
List all monitored services
Show me PaymentGW's incident history
Compare PaymentGW and NotificationSvc latency
```

### L4 Backups
```
Turn 1: What is PaymentGW's error rate?
Turn 2: Is it above the SLA threshold?
Turn 3: What should we do about it?
```

---

## 🎯 Key Messages to Emphasize

1. **Transparency**: "You can see exactly what the AI is doing — no black box."

2. **Intelligence**: "The AI chooses the right tool for the job — database for historical data, API for live metrics."

3. **Context**: "Multi-turn conversations work naturally — the AI remembers what you're talking about."

4. **Performance**: "All of this happens in seconds — L1 in ~3s, L3 in ~6s, L4 in ~8s."

5. **Debugging**: "For developers, this is invaluable — you can debug exactly why the AI gave a certain answer."

---

## 🐛 Troubleshooting During Demo

### If retrieval shows 0 chunks
- **Cause**: Event logging issue or KB not synced
- **Fix**: Use L3 query instead (tools don't need retrieval)
- **Say**: "Let me show you the tool capabilities instead"

### If tool execution fails
- **Cause**: Monitoring API not running
- **Fix**: Switch to L1/L2 queries
- **Say**: "Let me demonstrate the RAG capabilities"

### If response is slow
- **Cause**: Cold start or network latency
- **Say**: "First query can be slower due to cold start — subsequent queries are faster"
- **Show**: Processing time in observability

### If memory doesn't work
- **Cause**: Session ID issue
- **Fix**: Click "New Session" and try again
- **Say**: "Let me start a fresh session"

---

## 📊 Expected Performance

| Level | Target | Typical | Max Acceptable |
|-------|--------|---------|----------------|
| L1    | <5s    | 2-3s    | 6s             |
| L2    | <8s    | 3-5s    | 9s             |
| L3    | <10s   | 5-8s    | 12s            |
| L4    | <12s   | 6-10s   | 15s            |

---

## 🎬 Opening Line

"Welcome to the GeekBrain AI Dashboard. What you're seeing is not just a chatbot — it's a fully transparent AI system where you can watch every step of the reasoning process in real-time. Let me show you how it works."

## 🎬 Closing Line

"As you can see, this dashboard provides complete visibility into the AI's decision-making process — from retrieval to tool selection to final answer generation. This transparency is crucial for debugging, validation, and building trust in AI systems. Thank you!"

---

## ⏱ Time Allocation

- Introduction: 1 min
- L1 Demo: 2 min
- L2 Demo: 2 min
- L3 Demo: 3 min (most impressive)
- L4 Demo: 2 min
- **Total: 10 minutes**

---

**Ready to demo?** Open http://localhost:8002 and follow this guide! 🚀
