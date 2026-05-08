# GeekBrain AI System — W4 Project

Multi-level AI question-answering system for GeekBrain fintech startup, built with AWS Bedrock, RAG, and tool orchestration.

## 🎯 Overview

This system implements a 4-level AI Q&A platform:

- **L1**: Simple RAG from Knowledge Base
- **L2**: Multi-Source RAG with conflict resolution
- **L3**: Tool-Augmented RAG (database + monitoring API)
- **L4**: Memory-Enabled RAG (multi-turn conversations)

## ✨ Key Features

### Core Capabilities
- 📚 **RAG Pipeline**: AWS Bedrock Knowledge Base with 36 markdown documents
- 🔧 **7 Tools**: Database queries, service metrics, incident history, team info
- 💾 **Memory System**: WindowMemory for multi-turn conversations
- 🧠 **LLM**: Claude 3.5 Sonnet/Haiku via AWS Bedrock

### Bonus Features
- ✅ **Bonus A**: Chat & Observability Dashboard (real-time pipeline visualization)
- ✅ **Bonus B**: Investigation Agent (multi-step reasoning)
- ✅ **Bonus C**: Knowledge Base Sync automation

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd w4
pip install -r requirements.txt
```

### 2. Configure Environment

Create `.env` file in project root:

```bash
BEDROCK_KB_ID=your_kb_id
BEDROCK_MODEL_ID=us.anthropic.claude-3-5-haiku-20241022-v1:0
DB_PATH=w4/geekbrain.db
MONITORING_API_URL=http://localhost:8000
AWS_REGION=ap-southeast-1
```

### 3. Seed Database

```bash
python seed_data.py
```

### 4. Start Dashboard (Recommended)

```bash
bash start_dashboard.sh
```

This starts:
- Monitoring API (port 8000)
- Main API (port 8001)
- Dashboard (port 8002) — **auto-starts with main API**

### 5. Open Dashboard

**http://localhost:8002**

See [QUICKSTART_DASHBOARD.md](QUICKSTART_DASHBOARD.md) for detailed guide.

## 📊 Chat & Observability Dashboard

**NEW!** Interactive web dashboard with:

### 💬 Chat Interface
- Direct chat with AI system
- Level selection (L1/L2/L3/L4)
- Session management for L4
- Message history

### 🔍 Real-Time Observability
- Retrieved chunks with scores
- Tool execution with parameters
- LLM invocations
- Memory loading (L4)
- Processing time metrics

**See full documentation**: [DASHBOARD_README.md](DASHBOARD_README.md)

## 🏗️ Architecture

```
┌─────────────────┐         ┌──────────────────┐
│  Chat Panel     │         │  Observability   │
│  (Port 8002)    │◄────────┤  Panel           │
└────────┬────────┘         └──────────────────┘
         │
         │ POST /query
         ▼
┌─────────────────┐
│  Main API       │
│  (Port 8001)    │
│                 │
│  ┌───────────┐  │
│  │Orchestrator│ │
│  └─────┬─────┘  │
│        │        │
│  ┌─────▼─────┐  │
│  │RAG Pipeline│ │
│  └───────────┘  │
│                 │
│  ┌───────────┐  │
│  │7 Tools    │ │
│  └───────────┘  │
│                 │
│  ┌───────────┐  │
│  │Memory     │ │
│  └───────────┘  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  AWS Bedrock    │
│  - KB (RAG)     │
│  - Claude LLM   │
└─────────────────┘
```

## 📁 Project Structure

```
w4/
├── src/
│   ├── main.py              # FastAPI app + endpoints
│   ├── orchestrator.py      # Query routing & tool orchestration
│   ├── rag_pipeline.py      # Bedrock KB retrieval + generation
│   ├── tools.py             # 7 tools implementation
│   ├── memory.py            # WindowMemory + DynamoDB
│   ├── dashboard.py         # Chat & Observability UI
│   ├── event_logger.py      # Event tracking for observability
│   └── investigation.py     # Bonus B: Investigation agent
├── data_package/
│   └── knowledge_base/      # 36 markdown documents
├── tests/
│   ├── unit/                # Unit tests
│   └── integration/         # Integration tests
├── docs/
│   └── W4_evidence.md       # Evidence pack
├── geekbrain.db             # SQLite database
├── monitoring_api.py        # Mock monitoring API
├── seed_data.py             # Database seeding
├── start_dashboard.sh       # Start all services
├── stop_dashboard.sh        # Stop all services
└── test_dashboard.py        # Dashboard test script
```

## 🧪 Testing

### Run All Tests

```bash
pytest tests/ -v
```

### Test Dashboard

```bash
python test_dashboard.py
```

### Manual Testing

```bash
# L1 query
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Who is the Team Platform lead?", "level": "L1"}'

# L3 query
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What was PaymentGW cost in Q1 2026?", "level": "L3"}'

# L4 query
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Service nào có chi phí cao nhất?", "level": "L4", "session_id": "test-123"}'
```

## 📚 Documentation

- [QUICKSTART_DASHBOARD.md](QUICKSTART_DASHBOARD.md) — Quick start guide for dashboard
- [DASHBOARD_README.md](DASHBOARD_README.md) — Full dashboard documentation
- [DEMO_SCRIPT.md](DEMO_SCRIPT.md) — Demo presentation script
- [TESTING_GUIDE.md](TESTING_GUIDE.md) — Testing guide
- [docs/W4_evidence.md](docs/W4_evidence.md) — Evidence pack

## 🎯 Demo Queries

### L1 — Simple RAG
```
Who is the Team Platform lead?
What is the deployment freeze window?
```

### L2 — Multi-Source
```
What is PaymentGW's API rate limit?
```

### L3 — Tool-Augmented
```
What was PaymentGW's total infrastructure cost in Q1 2026?
What is PaymentGW's current p99 latency?
Is NotificationSvc meeting its SLA targets?
```

### L4 — Multi-Turn Memory
```
Turn 1: Service nào có chi phí cao nhất tháng 3/2026?
Turn 2: Tại sao chi phí của nó tăng đột biến?
Turn 3: Team nào chịu trách nhiệm?
Turn 4: Deadline review postmortem đã qua chưa?
```

## 🏆 Bonus Features

### ✅ Bonus A — Observability Dashboard
Interactive web dashboard with chat interface and real-time pipeline visualization.

**Access**: http://localhost:8002

### ✅ Bonus B — Investigation Agent
Multi-step reasoning agent for complex investigations.

```bash
curl -X POST http://localhost:8001/investigate \
  -H "Content-Type: application/json" \
  -d '{"query": "Why is NotificationSvc failing?"}'
```

### ✅ Bonus C — Knowledge Base Sync
Automated sync of documents to Bedrock KB.

```bash
python kb_sync.py
```

## 🛠️ Troubleshooting

### Services won't start
```bash
# Check ports
lsof -i :8000,8001,8002

# Kill processes
bash stop_dashboard.sh
```

### Dashboard not loading
- Check main API: `curl http://localhost:8001/health`
- Check dashboard: `curl http://localhost:8002`
- View logs: `tail -f logs/main_api.log`

### L3 queries failing
- Start monitoring API: `python monitoring_api.py`
- Check database: `ls -lh geekbrain.db`
- Verify .env configuration

### No observability events
- Events are logged automatically
- Send a query first
- Check event_logger is imported

## 📊 Performance Targets

| Level | Target | Achieved |
|-------|--------|----------|
| L1 | < 5s | ~2-3s ✅ |
| L2 | < 8s | ~3-5s ✅ |
| L3 | < 10s | ~5-8s ✅ |
| L4 | < 12s | ~6-10s ✅ |

## 🔧 Tech Stack

- **Framework**: FastAPI
- **LLM**: AWS Bedrock (Claude 3.5 Sonnet/Haiku)
- **RAG**: Bedrock Knowledge Base + OpenSearch Serverless
- **Database**: SQLite (local), DynamoDB (memory persistence)
- **Tools**: Custom Python functions
- **Frontend**: Pure HTML/CSS/JavaScript (no build step)

## 📝 License

Internal project for GeekBrain fintech startup.

---

**Ready to start?** Run `bash start_dashboard.sh` and open http://localhost:8002 🚀
