# L1 (Simple RAG) - Complete Implementation Guide

## Tổng Quan

L1 (Simple RAG - Retrieval-Augmented Generation) là cấp độ đầu tiên của hệ thống GeekBrain AI. Nó cho phép người dùng hỏi câu hỏi đơn giản về GeekBrain và nhận câu trả lời chính xác kèm nguồn trích dẫn.

### Kiến Trúc L1

```
User Query
    ↓
FastAPI Endpoint (/query)
    ↓
RAGPipeline.retrieve_and_generate()
    ↓
    ├─→ Bedrock KB Retrieve (lấy 5 chunks)
    │       ↓
    │   OpenSearch Vector Store
    │       ↓
    │   S3 (36 markdown files)
    │
    └─→ Claude Sonnet (LLM)
            ↓
        Response với source citations
            ↓
        Trả về User
```

## Các Thành Phần Đã Implement

### 1. Infrastructure (AWS)

**Terraform Setup** (`w4/terraform/`)
- ✅ S3 bucket: lưu trữ 36 markdown documents
- ✅ OpenSearch Serverless: vector store cho embeddings
- ✅ Bedrock Knowledge Base: RAG pipeline
- ✅ IAM roles: quyền truy cập các services

**Cấu hình:**
- Embedding model: Amazon Titan Embeddings v2
- Chunking: 300 tokens, 20% overlap
- Knowledge Base ID: `8IT6QXNDFJ`

### 2. RAG Pipeline (`w4/src/rag_pipeline.py`)

**Class: RAGPipeline**

Chức năng chính:
- `retrieve()`: Lấy relevant chunks từ Knowledge Base
- `retrieve_and_generate()`: Lấy chunks + gọi LLM để sinh câu trả lời

**Đặc điểm:**
- Top-K = 5 chunks cho L1
- Trích xuất filename từ S3 URI
- Sắp xếp chunks theo relevance score
- Format context cho LLM
- System prompt với citation rules

### 3. API Server (`w4/src/main.py`)

**FastAPI Application**

Endpoints:
- `GET /` - Health check
- `POST /query` - Query endpoint chính

**Request Format:**
```json
{
  "query": "Who is the Team Platform lead?",
  "top_k": 5
}
```

**Response Format:**
```json
{
  "answer": "Theo thông tin trong team_platform.md, Team Platform lead là Alex Chen.",
  "sources": ["team_platform.md", "service_authsvc.md"],
  "chunks_used": [...],
  "processing_time": 1.947,
  "level": "L1"
}
```

### 4. Data Models (`w4/src/rag_pipeline.py`)

**Dataclasses:**
- `Chunk`: Đại diện cho một đoạn text được retrieve
  - text: nội dung
  - source: tên file
  - score: relevance score (0-1)

- `Response`: Đại diện cho câu trả lời
  - answer: câu trả lời từ LLM
  - sources: list các file nguồn
  - chunks_used: list các chunks đã dùng
  - processing_time: thời gian xử lý

## Testing

### Unit Tests (18 tests - ALL PASSED ✅)

**File:** `w4/tests/unit/test_rag_pipeline.py`

**Test Coverage:**

1. **Retrieve Tests (8 tests)**
   - ✅ Trả về đúng số lượng chunks
   - ✅ Chunks có đầy đủ fields (text, source, score)
   - ✅ Extract filename từ S3 URI
   - ✅ Sắp xếp theo relevance score
   - ✅ Error handling (no KB ID, API error, empty results)
   - ✅ Gọi Bedrock API với đúng parameters

2. **Retrieve and Generate Tests (8 tests)**
   - ✅ Response có source citations
   - ✅ Trả về Response object đúng cấu trúc
   - ✅ Sử dụng retrieved chunks
   - ✅ Xử lý trường hợp không có chunks
   - ✅ Gọi LLM với context đúng format
   - ✅ Error handling khi LLM fail
   - ✅ Extract unique sources
   - ✅ Respect top_k parameter

3. **Helper Methods Tests (2 tests)**
   - ✅ Format chunks thành context string
   - ✅ Generate L1 system prompt

**Chạy Unit Tests:**
```bash
cd w4
./venv/bin/python -m pytest tests/unit/test_rag_pipeline.py -v
```

### Integration Tests (8/9 PASSED ✅)

**File:** `w4/tests/integration/test_l1_integration.py`

**Test Coverage:**

1. ✅ **API Health Check** - Verify API running và KB configured
2. ✅ **Team Platform Lead Query** - Test query trả về "Alex Chen"
3. ✅ **Deployment Freeze Window Query** - Test query về deployment policy
4. ✅ **Source Citations** - Verify responses có source citations
5. ⚠️ **Response Time** - 2/3 queries < 5s (1 query: 5.4s)
6. ✅ **Multiple Queries Consistency** - Same query → consistent results
7. ✅ **Error Handling Empty Query** - Graceful error handling
8. ✅ **Error Handling Invalid Parameters** - Validate input
9. ✅ **Vietnamese Response** - Responses in Vietnamese

**Chạy Integration Tests:**
```bash
cd w4
export BEDROCK_KB_ID="8IT6QXNDFJ"
./venv/bin/python -m pytest tests/integration/test_l1_integration.py -v
```

## Demo Script

### Chuẩn Bị

1. **Start API Server:**
```bash
cd w4/src
python main.py
```

Server sẽ chạy tại: `http://localhost:8001`

2. **Set Environment Variables:**
```bash
export BEDROCK_KB_ID="8IT6QXNDFJ"
export AWS_DEFAULT_REGION="us-east-1"
```

### Demo Queries

#### Query 1: Team Information
```bash
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Who is the Team Platform lead?",
    "top_k": 5
  }'
```

**Expected Response:**
```json
{
  "answer": "Theo thông tin trong team_platform.md, Team Platform lead là Alex Chen.",
  "sources": ["team_platform.md", ...],
  "processing_time": 1.9
}
```

#### Query 2: Policy Information
```bash
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the deployment freeze window?",
    "top_k": 5
  }'
```

**Expected Response:**
```json
{
  "answer": "Deployment freeze window là từ Friday 18:00 đến Monday 08:00...",
  "sources": ["deployment_policy.md", ...],
  "processing_time": 2.5
}
```

#### Query 3: Service Information
```bash
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What services does GeekBrain operate?",
    "top_k": 5
  }'
```

### Demo với Python

```python
import requests

API_URL = "http://localhost:8001/query"

def ask_question(query):
    response = requests.post(API_URL, json={"query": query, "top_k": 5})
    data = response.json()
    
    print(f"\nQuery: {query}")
    print(f"Answer: {data['answer']}")
    print(f"Sources: {', '.join(data['sources'])}")
    print(f"Processing time: {data['processing_time']:.2f}s")
    return data

# Demo queries
ask_question("Who is the Team Platform lead?")
ask_question("What is the deployment freeze window?")
ask_question("What services does GeekBrain operate?")
```

## Giải Thích Chi Tiết

### Luồng Xử Lý Query

1. **User gửi query** → FastAPI endpoint `/query`

2. **API validate input:**
   - Check query không empty
   - Check top_k hợp lệ (1-20)

3. **RAGPipeline.retrieve_and_generate():**
   
   a. **Retrieve Phase:**
   - Gọi Bedrock Agent Runtime `retrieve()` API
   - Parameters:
     - `knowledgeBaseId`: "8IT6QXNDFJ"
     - `retrievalQuery`: {"text": query}
     - `numberOfResults`: 5
   - Bedrock KB:
     - Convert query → embedding (Titan v2)
     - Search OpenSearch vector store
     - Trả về top 5 relevant chunks
   
   b. **Format Context:**
   - Extract text, source, score từ mỗi chunk
   - Format thành context string:
     ```
     Thông tin từ Knowledge Base:
     
     [Nguồn: team_platform.md]
     Team Platform is responsible for...
     
     [Nguồn: deployment_policy.md]
     Deployment freeze window is...
     ```
   
   c. **Generate Response:**
   - Tạo system prompt với citation rules
   - Gọi Bedrock Runtime `invoke_model()` API
   - Model: Claude Sonnet 3.5
   - Messages:
     - System: "Bạn là AI assistant... phải cite sources..."
     - User: context + query
   - LLM sinh câu trả lời với citations
   
   d. **Parse Response:**
   - Extract answer text
   - Extract unique sources
   - Calculate processing time
   - Return Response object

4. **API trả về JSON** cho user

### System Prompt Strategy

```python
def _get_l1_system_prompt(self) -> str:
    return """Bạn là AI assistant trả lời câu hỏi về GeekBrain.

QUAN TRỌNG - Citation Rules:
1. CHỈ sử dụng thông tin từ context được cung cấp
2. PHẢI cite nguồn bằng cách mention tên file (vd: "theo team_platform.md")
3. NẾU không tìm thấy thông tin → nói rõ "không có trong knowledge base"

Format câu trả lời:
- Ngắn gọn, rõ ràng
- Tiếng Việt
- Có source citation
"""
```

### Error Handling

**Các trường hợp được xử lý:**

1. **Empty Query:**
   ```python
   if not query or query.strip() == "":
       raise HTTPException(400, "Query cannot be empty")
   ```

2. **Invalid top_k:**
   ```python
   if top_k < 1 or top_k > 20:
       raise HTTPException(400, "top_k must be between 1 and 20")
   ```

3. **Bedrock API Error:**
   ```python
   try:
       response = bedrock_agent.retrieve(...)
   except Exception as e:
       raise RuntimeError(f"Bedrock retrieve failed: {e}")
   ```

4. **No Chunks Found:**
   ```python
   if len(chunks) == 0:
       return Response(
           answer="Không tìm thấy thông tin trong knowledge base.",
           sources=[],
           chunks_used=[],
           processing_time=elapsed
       )
   ```

## Performance Metrics

### Actual Performance (từ tests)

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Response Time | < 5s | 1.8s - 5.4s | ⚠️ Mostly OK |
| Accuracy | 100% | 100% | ✅ |
| Source Citations | Always | Always | ✅ |
| Error Handling | Graceful | Graceful | ✅ |

### Response Time Breakdown

```
Total Time: ~2-5 seconds
├─ Bedrock KB Retrieve: ~0.5-1s
├─ LLM Inference: ~1-3s
└─ API Overhead: ~0.1-0.5s
```

## Troubleshooting

### Issue: "Knowledge Base is not configured"

**Solution:**
```bash
export BEDROCK_KB_ID="8IT6QXNDFJ"
```

### Issue: "Connection refused"

**Solution:** Start API server
```bash
cd w4/src
python main.py
```

### Issue: Response time > 5s

**Possible causes:**
- Network latency
- Bedrock service load
- Large context size

**Solutions:**
- Reduce top_k (5 → 3)
- Use faster model (Haiku instead of Sonnet)
- Add caching layer

### Issue: Wrong answer

**Debug steps:**
1. Check chunks retrieved:
   ```python
   chunks = rag_pipeline.retrieve(query, top_k=5)
   for chunk in chunks:
       print(f"Source: {chunk.source}, Score: {chunk.score}")
       print(f"Text: {chunk.text[:200]}...")
   ```

2. Check if document exists in KB:
   ```bash
   aws s3 ls s3://geekbrain-kb-*/
   ```

3. Check KB sync status:
   ```bash
   cd w4/terraform
   bash trigger_kb_sync.sh
   ```

## Next Steps

L1 đã hoàn thành với 8/9 integration tests passed. Sẵn sàng cho:

1. **L2 (Multi-Source RAG):**
   - Tăng top_k lên 10
   - Implement conflict resolution
   - Handle multiple document synthesis

2. **L3 (Tool-Augmented RAG):**
   - Add database query tool
   - Add monitoring API tool
   - Implement tool orchestration

3. **L4 (Memory-Enabled RAG):**
   - Add conversation memory
   - Implement pronoun resolution
   - Multi-turn conversation support

## Files Summary

```
w4/
├── src/
│   ├── rag_pipeline.py      # Core RAG logic (✅ Complete)
│   ├── main.py              # FastAPI server (✅ Complete)
│   ├── tools.py             # Tool implementations (for L3)
│   ├── memory.py            # Memory management (for L4)
│   └── orchestrator.py      # Tool orchestration (for L3)
│
├── tests/
│   ├── unit/
│   │   └── test_rag_pipeline.py  # 18 tests (✅ All passed)
│   └── integration/
│       └── test_l1_integration.py # 9 tests (✅ 8 passed)
│
├── terraform/
│   ├── main.tf              # Infrastructure (✅ Deployed)
│   └── outputs.tf           # KB ID and other outputs
│
└── docs/
    ├── L1_COMPLETE_GUIDE.md # This file
    └── architecture_diagram.md
```

## Kết Luận

L1 (Simple RAG) đã được implement thành công với:
- ✅ Infrastructure hoàn chỉnh (S3, Bedrock KB, OpenSearch)
- ✅ RAG pipeline hoạt động chính xác
- ✅ API server stable
- ✅ 18/18 unit tests passed
- ✅ 8/9 integration tests passed
- ⚠️ 1 test có response time hơi chậm (5.4s vs 5s target)

Hệ thống sẵn sàng cho demo và có thể tiến hành implement L2.
