# Quick Start — Chat & Observability Dashboard

## 🚀 Start in 3 Steps

### Step 1: Start Services

```bash
cd w4

# Option A: Auto-start script (recommended)
bash start_dashboard.sh

# Option B: Manual start
# Terminal 1: Monitoring API
python monitoring_api.py

# Terminal 2: Main API + Dashboard
cd src && python main.py
```

### Step 2: Open Dashboard

Open browser: **http://localhost:8002**

### Step 3: Start Chatting!

1. Select level (L1, L2, L3, or L4)
2. Type a question
3. Press Enter
4. Watch the magic happen! ✨

## 📊 What You'll See

### Left Panel: Chat Interface
- Your questions and AI responses
- Processing time and tools used
- Session management for L4

### Right Panel: Real-Time Observability
- 📥 Query received
- 📚 Retrieved chunks from knowledge base
- 🔧 Tools executed (L3)
- 🧠 LLM invocations
- 💾 Memory loaded (L4)
- ✅ Final response

## 🧪 Test Queries

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
```

### L4 — Multi-Turn Memory
```
Turn 1: Service nào có chi phí cao nhất tháng 3/2026?
Turn 2: Tại sao chi phí của nó tăng đột biến?
Turn 3: Team nào chịu trách nhiệm?
```

## 🛑 Stop Services

```bash
# Option A: Using stop script
bash stop_dashboard.sh

# Option B: Ctrl+C in each terminal
```

## 🔧 Troubleshooting

### Services won't start
```bash
# Check if ports are in use
lsof -i :8000
lsof -i :8001
lsof -i :8002

# Kill processes on those ports
kill -9 $(lsof -ti:8000,8001,8002)
```

### Dashboard not loading
- Check main API is running: `curl http://localhost:8001/health`
- Check dashboard: `curl http://localhost:8002`
- Check browser console for errors

### No observability events
- Events are logged automatically
- Try sending a query first
- Check event_logger is working

### L3 queries failing
- Ensure monitoring API is running on port 8000
- Check database exists: `ls -lh w4/geekbrain.db`
- Verify .env has correct paths

## 📝 Logs

```bash
# View logs
tail -f logs/main_api.log
tail -f logs/monitoring_api.log
```

## 🎯 Demo Tips

1. **Start with L1** to show basic RAG
2. **Move to L3** to demonstrate tool usage
3. **Finish with L4** to show memory/context
4. **Keep observability panel visible** during demo
5. **Highlight real-time updates** as query processes

## 🌟 Features Showcase

### For Trainers
- ✅ See exactly what chunks were retrieved
- ✅ Verify tool calls and parameters
- ✅ Track LLM reasoning process
- ✅ Measure performance metrics
- ✅ Understand system behavior

### For Developers
- ✅ Debug query processing
- ✅ Optimize retrieval quality
- ✅ Monitor tool execution
- ✅ Test different levels
- ✅ Validate responses

## 📚 More Info

See [DASHBOARD_README.md](DASHBOARD_README.md) for full documentation.

---

**Ready to go?** Open http://localhost:8002 and start chatting! 🚀
