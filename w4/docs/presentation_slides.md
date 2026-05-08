# GeekBrain AI System — Presentation Slides

## Slide 1: Title

**GeekBrain AI System**
*4-Level AI Q&A Platform for Fintech Operations*

- Team: GeekBrain AI System Team
- LLM: Amazon Bedrock — Claude 3.5 Sonnet v2
- Framework: FastAPI + AWS Bedrock SDK (boto3)
- Repo: `w4/`

---

## Slide 2: Architecture Overview

```
    ┌──────────┐
    │  👤 User │
    └────┬─────┘
         │ POST /query
    ┌────▼─────────────────┐
    │  🌐 FastAPI API       │  main.py
    └────┬─────────────────┘
         │ route L1/L2/L3/L4
    ┌────▼─────────────────┐
    │  🎯 Orchestrator      │  orchestrator.py
    │  - Query Router       │
    │  - LLM Loop (max 5)  │
    └──┬───────┬────────┬──┘
       │       │        │
 ┌─────▼──┐ ┌─▼──────┐ ┌▼────────────┐
 │📚 RAG  │ │🔧 Tools│ │💾 Memory    │
 │Pipeline│ │(7 tools)│ │WindowMemory │
 └───┬────┘ └──┬──┬──┘ │(last 5 turns)│
     │         │  │    └──────────────┘
 ┌───▼────┐ ┌──▼──┐ ┌──▼──────────┐
 │☁️Bedrock│ │🗄️DB│ │📊Monitoring │
 │  KB     │ │SQLite│ │   API      │
 │36 docs  │ │4 CSV │ │(:8000)     │
 └────────┘ └─────┘ └─────────────┘
```

**3 Data Sources:**
| Source | Technology | Data Type |
|--------|-----------|-----------|
| Knowledge Base | Bedrock KB + OpenSearch | 36 markdown docs (qualitative) |
| Database | SQLite | 4 CSV tables (costs, incidents, SLA, metrics) |
| Monitoring API | FastAPI | Live service metrics |

---

## Slide 3: Query Levels

| Level | Capability | Response Target | Key Feature |
|-------|-----------|----------------|-------------|
| **L1** | Simple RAG | < 5s | Single document retrieval + citation |
| **L2** | Multi-Source RAG | < 8s | Conflict resolution (v1 vs v2) |
| **L3** | Tool-Augmented | < 10s | 7 tools: DB query, metrics, status |
| **L4** | Memory-Enabled | < 12s | Multi-turn + pronoun resolution |

---

## Slide 4: Demo — L1 Simple RAG

**Query:** "Who is the Team Platform lead?"

```json
POST /query {"query": "Who is the Team Platform lead?", "level": "L1"}

Response:
{
  "answer": "Team Platform lead là Alex Chen.",
  "sources": ["team_platform.md"],
  "processing_time": 2.3
}
```

✅ Correct answer with source citation
✅ Response time < 5s

---

## Slide 5: Demo — L3 Tool-Augmented RAG

**Query:** "What was PaymentGW's total cost in Q1 2026?"

```
→ LLM generates tool_use:
  query_database("SELECT SUM(total_cost) FROM monthly_costs 
                  WHERE service='PaymentGW' AND month IN ('2026-01','2026-02','2026-03')")
→ Database returns: [{"total": 16500.0}]
→ LLM generates answer:
  "Tổng chi phí PaymentGW trong Q1 2026 là $16,500."
```

✅ Exact numerical value from database tool
✅ SQL generated and executed by LLM
✅ Response time < 10s

---

## Slide 6: Demo — L4 Memory-Enabled (4-Turn Conversation)

| Turn | User Query | Pronoun Resolution | Expected Answer |
|------|-----------|-------------------|-----------------|
| 1 | "Service nào chi phí cao nhất tháng 3?" | — | PaymentGW, $7,500 |
| 2 | "Tại sao chi phí **của nó** tăng?" | **nó** = PaymentGW | Sự cố scaling RAM |
| 3 | "Team nào chịu trách nhiệm?" | context = PaymentGW | Team Platform, Alex Chen |
| 4 | "Deadline review đã qua chưa?" | context = postmortem | 2026-04-05, đã qua |

**Memory:** WindowMemory (last 5 turns) — bounded context, no overflow

---

## Slide 7: Key Decision — Custom Tool Orchestration

**Decision:** Implement custom tool loop instead of Bedrock Agents

**Rationale:**
- Full transparency: can inspect exact messages, tool calls, results
- Easier debugging: no Lambda function overhead
- Flexible error handling per tool type

**Lesson Learned:**
System prompt engineering is the #1 lever for L3 accuracy.
Without explicit rules like "NEVER answer numbers from documents",
Claude hallucinated plausible costs from document text.

---

## Slide 8: Test Results

```
Unit Tests:           81 passed ✅
├── test_rag_pipeline.py         18 tests
├── test_database_tool.py         8 tests  
├── test_tool_orchestrator.py     5 tests
├── test_memory.py               20 tests  ← NEW
└── test_additional_tools.py     27 tests  ← NEW

Integration Tests (Real AWS):
├── test_l1_integration.py        9 tests
├── test_l2_integration.py        7 tests
├── test_l3_integration.py       14 tests
└── test_l4_integration.py       11 tests  ← NEW
```

---

## Slide 9: Reflection

**Hardest Level:** L3 — not the code, but the prompt
- Without explicit tool selection rules, LLM answered cost questions from KB documents
- Fix: "Use query_database for HISTORICAL data, get_service_metrics for CURRENT data"

**What I'd Change:**
1. Start with prompt evaluation harness (test multiple phrasings)
2. Use DynamoDB from start (persistence across API restarts)
3. Add structured JSON logging from day 1

**Memory Strategy:**
| Strategy | Chosen? | Why |
|----------|---------|-----|
| Buffer | ❌ | Unbounded growth, context overflow risk |
| **Window (N=5)** | ✅ | Bounded, predictable, sufficient for demo |
| Query Rewriting | ❌ | Extra LLM call per turn, doubles latency |

---

## Slide 10: Q&A

**Likely Questions:**
- "Tại sao dùng Window Memory thay vì Query Rewriting?"
  → Extra LLM call per turn doubles latency; 5 turns is enough for demo
- "Cost per query?"
  → ~$0.003–0.015 (KB retrieve + Claude Sonnet inference)
- "Production readiness?"
  → Functional ✅, Tested ✅, Need: rate limiting, auth, monitoring
