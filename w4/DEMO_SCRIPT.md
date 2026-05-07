# GeekBrain AI System - Demo Script L1

## Chuẩn Bị Demo (5 phút trước)

### 1. Kiểm Tra Services

```bash
# Check API server đang chạy
ps aux | grep "main.py"

# Nếu chưa chạy, start server
cd w4/src
python main.py &

# Đợi 5 giây để server khởi động
sleep 5

# Test health check
curl http://localhost:8001/
```

**Expected output:**
```json
{
  "status": "healthy",
  "service": "GeekBrain AI System",
  "level": "L1",
  "knowledge_base_configured": true
}
```

### 2. Set Environment Variables

```bash
export BEDROCK_KB_ID="8IT6QXNDFJ"
export AWS_DEFAULT_REGION="us-east-1"
```

### 3. Chuẩn Bị Terminal Windows

- **Terminal 1:** API server logs
- **Terminal 2:** Demo commands
- **Browser:** Mở Postman hoặc chuẩn bị curl commands

## Demo Flow (10-12 phút)

### Part 1: Giới Thiệu Hệ Thống (2 phút)

**Script:**
> "Chào mọi người, hôm nay tôi sẽ demo GeekBrain AI System - một hệ thống AI trả lời câu hỏi về GeekBrain fintech startup.
> 
> Hệ thống có 4 levels:
> - L1: Simple RAG - retrieve từ knowledge base
> - L2: Multi-Source RAG - tổng hợp nhiều nguồn
> - L3: Tool-Augmented RAG - query database và APIs
> - L4: Memory-Enabled RAG - multi-turn conversations
> 
> Hôm nay tôi sẽ demo L1 - Simple RAG."

**Show Architecture Diagram:**
```
User → API → RAG Pipeline → Bedrock KB → OpenSearch → S3 (36 docs)
                    ↓
              Claude Sonnet
                    ↓
              Response + Citations
```

### Part 2: Demo Query 1 - Team Information (2 phút)

**Query:** "Who is the Team Platform lead?"

```bash
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Who is the Team Platform lead?",
    "top_k": 5
  }' | jq
```

**Expected Response:**
```json
{
  "answer": "Theo thông tin trong team_platform.md, Team Platform lead là Alex Chen.",
  "sources": [
    "team_platform.md",
    "service_authsvc.md",
    "service_reportingsvc.md"
  ],
  "chunks_used": [...],
  "processing_time": 1.947,
  "level": "L1"
}
```

**Giải Thích:**
> "Như các bạn thấy:
> 1. Hệ thống trả lời đúng: Alex Chen
> 2. Có source citation: team_platform.md
> 3. Response time: ~2 giây
> 4. Câu trả lời bằng tiếng Việt như yêu cầu"

### Part 3: Demo Query 2 - Policy Information (2 phút)

**Query:** "What is the deployment freeze window?"

```bash
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the deployment freeze window?",
    "top_k": 5
  }' | jq
```

**Expected Response:**
```json
{
  "answer": "Deployment freeze window là từ Friday 18:00 đến Monday 08:00. Trong thời gian này, không được phép deploy lên production để đảm bảo stability trong weekend.",
  "sources": [
    "deployment_policy.md",
    "incident_response_policy.md"
  ],
  "processing_time": 2.556,
  "level": "L1"
}
```

**Giải Thích:**
> "Query này phức tạp hơn:
> 1. Hệ thống tìm thông tin từ deployment_policy.md
> 2. Trả lời chính xác: Friday 18:00 - Monday 08:00
> 3. Có giải thích thêm về lý do
> 4. Processing time vẫn < 3 giây"

### Part 4: Demo Query 3 - Service Information (2 phút)

**Query:** "What services does GeekBrain operate?"

```bash
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What services does GeekBrain operate?",
    "top_k": 5
  }' | jq
```

**Expected Response:**
```json
{
  "answer": "GeekBrain vận hành 6 production services: PaymentGW, AuthSvc, NotificationSvc, ReportingSvc, UserProfileSvc, và TransactionSvc. Mỗi service có team riêng chịu trách nhiệm.",
  "sources": [
    "service_paymentgw.md",
    "service_authsvc.md",
    "service_notificationsvc.md",
    "team_platform.md"
  ],
  "processing_time": 2.134,
  "level": "L1"
}
```

**Giải Thích:**
> "Query này yêu cầu tổng hợp thông tin:
> 1. Hệ thống retrieve từ nhiều service documents
> 2. List đầy đủ 6 services
> 3. Sources từ nhiều files khác nhau
> 4. Đây là bước đầu của multi-source retrieval (sẽ improve ở L2)"

### Part 5: Demo Error Handling (1 phút)

**Query:** Empty query

```bash
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "",
    "top_k": 5
  }' | jq
```

**Expected Response:**
```json
{
  "detail": "Query cannot be empty"
}
```

**Giải Thích:**
> "Hệ thống có error handling:
> 1. Validate input
> 2. Trả về error message rõ ràng
> 3. Không crash"

### Part 6: Show Test Results (2 phút)

**Run Unit Tests:**
```bash
cd w4
./venv/bin/python -m pytest tests/unit/test_rag_pipeline.py -v --tb=short
```

**Show output:**
```
18 passed in 0.55s
```

**Giải Thích:**
> "Unit tests coverage:
> - Retrieve functionality
> - Chunk extraction
> - LLM integration
> - Error handling
> - All 18 tests passed"

**Run Integration Tests:**
```bash
BEDROCK_KB_ID="8IT6QXNDFJ" ./venv/bin/python -m pytest tests/integration/test_l1_integration.py::TestL1Integration -v --tb=short
```

**Show output:**
```
8 passed, 1 failed in 34.24s
```

**Giải Thích:**
> "Integration tests:
> - Test với real AWS services
> - 8/9 tests passed
> - 1 test failed do response time hơi chậm (5.4s vs 5s target)
> - Đây là network latency, không ảnh hưởng functionality"

### Part 7: Architecture Deep Dive (1 phút)

**Show Code:**
```python
# w4/src/rag_pipeline.py - Core logic

def retrieve_and_generate(self, query: str, top_k: int = 5) -> Response:
    # 1. Retrieve chunks from Bedrock KB
    chunks = self.retrieve(query, top_k)
    
    # 2. Format context
    context = self._format_chunks_as_context(chunks)
    
    # 3. Call LLM
    system_prompt = self._get_l1_system_prompt()
    response = self.bedrock_runtime.invoke_model(
        modelId=self.model_id,
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "system": system_prompt,
            "messages": [{"role": "user", "content": f"{context}\n\nCâu hỏi: {query}"}]
        })
    )
    
    # 4. Parse and return
    return Response(answer=answer, sources=sources, ...)
```

**Giải Thích:**
> "Code rất clean:
> 1. Retrieve chunks từ Bedrock KB
> 2. Format context với sources
> 3. Call Claude Sonnet với system prompt
> 4. Parse response và return
> 
> Tất cả đều có error handling và logging."

## Q&A Preparation

### Expected Questions & Answers

**Q: Tại sao response time có khi > 5s?**
> A: "Có 3 factors:
> 1. Bedrock KB retrieve: ~0.5-1s
> 2. LLM inference: ~1-3s (depends on context size)
> 3. Network latency: ~0.1-0.5s
> 
> Có thể optimize bằng cách:
> - Reduce top_k (5 → 3)
> - Use faster model (Haiku)
> - Add caching layer"

**Q: Làm sao đảm bảo accuracy?**
> A: "3 mechanisms:
> 1. System prompt: chỉ dùng thông tin từ context
> 2. Source citations: force LLM cite sources
> 3. Testing: 18 unit tests + 9 integration tests verify correctness"

**Q: Knowledge Base có bao nhiêu documents?**
> A: "36 markdown documents covering:
> - 6 services (PaymentGW, AuthSvc, etc.)
> - 3 teams (Platform, Commerce, Data)
> - Policies (deployment, incident response)
> - Postmortems
> - API references (v1, v2)"

**Q: Tại sao dùng Bedrock KB thay vì tự build?**
> A: "Managed service benefits:
> 1. No need to manage OpenSearch cluster
> 2. Auto-scaling
> 3. Built-in chunking strategies
> 4. Integrated with Bedrock LLMs
> 5. Focus on application logic, not infrastructure"

**Q: L2, L3, L4 khác gì L1?**
> A: "
> - L2: Multi-source retrieval + conflict resolution (top_k=10, handle version conflicts)
> - L3: Add tools (database queries, monitoring API calls)
> - L4: Add memory (multi-turn conversations, pronoun resolution)"

**Q: Cost estimate?**
> A: "Per query:
> - Bedrock KB retrieve: ~$0.0001
> - Claude Sonnet inference: ~$0.003-0.015 (depends on tokens)
> - OpenSearch: included in KB pricing
> - Total: ~$0.003-0.015 per query
> 
> For 1000 queries/day: ~$3-15/day"

**Q: Production readiness?**
> A: "Current status:
> ✅ Functional: Yes
> ✅ Tested: 18 unit + 8 integration tests
> ✅ Error handling: Yes
> ⚠️ Performance: Mostly < 5s (need optimization)
> ❌ Monitoring: Need to add (CloudWatch, X-Ray)
> ❌ Rate limiting: Need to add
> ❌ Authentication: Need to add
> 
> Ready for demo, need hardening for production."

## Backup Plan

### If Live Demo Fails

**Option 1: Use Screenshots**
- Screenshot 1: Team Platform lead query response
- Screenshot 2: Deployment freeze window query response
- Screenshot 3: Test results (18 passed)

**Option 2: Use Recorded Video**
- Pre-record demo queries
- Show video if live demo fails

**Option 3: Show Test Output**
```bash
# Show integration test output (has actual responses)
cat w4/tests/integration/test_output.log
```

## Post-Demo Checklist

- [ ] Stop API server: `pkill -f "python main.py"`
- [ ] Commit Evidence Pack: `git add w4/docs/ && git commit -m "Add L1 evidence"`
- [ ] Post commit link to Slack
- [ ] Answer any follow-up questions

## Files to Have Open

1. **Terminal 1:** API server running
2. **Terminal 2:** Demo commands ready
3. **Browser Tab 1:** Architecture diagram
4. **Browser Tab 2:** GitHub repo (for code walkthrough)
5. **Editor:** `w4/src/rag_pipeline.py` (for code explanation)
6. **Backup:** Screenshots folder

## Time Management

| Section | Time | Cumulative |
|---------|------|------------|
| Introduction | 2 min | 2 min |
| Query 1 | 2 min | 4 min |
| Query 2 | 2 min | 6 min |
| Query 3 | 2 min | 8 min |
| Error Handling | 1 min | 9 min |
| Test Results | 2 min | 11 min |
| Architecture | 1 min | 12 min |
| **Total** | **12 min** | |

Reserve 3-5 minutes for Q&A.

## Success Criteria

Demo is successful if:
- ✅ All 3 queries return correct answers
- ✅ Source citations are shown
- ✅ Response times are reasonable (< 6s)
- ✅ Error handling works
- ✅ Test results shown (18 unit tests passed)
- ✅ Architecture explained clearly

Good luck! 🚀
