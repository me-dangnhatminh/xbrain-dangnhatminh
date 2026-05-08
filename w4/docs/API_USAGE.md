# GeekBrain AI System - API Usage Guide

## Starting the API Server

```bash
# Set environment variables
export BEDROCK_KB_ID="your-knowledge-base-id"
export BEDROCK_MODEL_ID="anthropic.claude-3-sonnet-20240229-v1:0"  # Optional, this is the default

# Run the server
cd w4/src
python main.py

# Or using uvicorn directly
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

The API will be available at `http://localhost:8001`

## API Endpoints

### Health Check

**GET /** or **GET /health**

Check if the service is running and configured properly.

```bash
curl http://localhost:8001/health
```

Response:
```json
{
  "status": "healthy",
  "knowledge_base_configured": true
}
```

### Query Endpoint (L1)

**POST /query**

Submit a question to the AI system and receive an answer with source citations.

**Request Body:**
```json
{
  "query": "Who is the Team Platform lead?",
  "top_k": 5
}
```

**Parameters:**
- `query` (required): User's question as a string
- `top_k` (optional): Number of chunks to retrieve (default: 5, range: 1-20)

**Response:**
```json
{
  "answer": "Theo team_platform.md, Team Platform lead là Alex Chen.",
  "sources": ["team_platform.md"],
  "processing_time": 2.345
}
```

**Response Fields:**
- `answer`: Generated answer in Vietnamese with source citations
- `sources`: List of source document filenames
- `processing_time`: Processing time in seconds

### Example Requests

**Using curl:**
```bash
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Who is the Team Platform lead?"
  }'
```

**Using Python requests:**
```python
import requests

response = requests.post(
    "http://localhost:8001/query",
    json={"query": "Who is the Team Platform lead?"}
)

result = response.json()
print(f"Answer: {result['answer']}")
print(f"Sources: {result['sources']}")
print(f"Processing time: {result['processing_time']}s")
```

**Using httpie:**
```bash
http POST http://localhost:8001/query query="Who is the Team Platform lead?"
```

## Error Handling

The API returns appropriate HTTP status codes and error messages:

### 400 Bad Request
Invalid request parameters (e.g., empty query string)

```json
{
  "detail": "Invalid request: query cannot be empty"
}
```

### 503 Service Unavailable
Knowledge Base or Bedrock service is unavailable

```json
{
  "detail": "Knowledge Base retrieval failed: ..."
}
```

### 500 Internal Server Error
Unexpected errors during processing

```json
{
  "detail": "Unexpected error: ..."
}
```

## Testing the Endpoint

### Test Query 1: Team Information
```bash
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Who is the Team Platform lead?"}'
```

Expected: Answer should mention "Alex Chen" with source citation from team_platform.md

### Test Query 2: Policy Information
```bash
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the deployment freeze window?"}'
```

Expected: Answer should mention "Friday 18:00 to Monday 08:00" with source citation

### Test Query 3: Not Found
```bash
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the weather today?"}'
```

Expected: Answer should state information is not available in knowledge base

## Interactive API Documentation

FastAPI provides automatic interactive API documentation:

- **Swagger UI**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc

These interfaces allow you to test the API directly from your browser.

## Performance Targets

- **L1 Response Time**: < 5 seconds
- **Concurrent Requests**: Supports multiple simultaneous queries
- **Timeout**: No explicit timeout (relies on Bedrock API timeouts)

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `BEDROCK_KB_ID` | Yes | None | Bedrock Knowledge Base ID |
| `BEDROCK_MODEL_ID` | No | `anthropic.claude-3-sonnet-20240229-v1:0` | Bedrock model ID for LLM |

### AWS Credentials

The application uses boto3, which requires AWS credentials to be configured:

1. **Environment variables**: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`
2. **AWS credentials file**: `~/.aws/credentials`
3. **IAM role** (if running on EC2/Lambda)

Required IAM permissions:
- `bedrock:InvokeModel`
- `bedrock:Retrieve` (for Knowledge Base access)

## Troubleshooting

### "Knowledge Base is not configured"
Set the `BEDROCK_KB_ID` environment variable before starting the server.

### "Knowledge Base retrieval failed"
- Check that the Knowledge Base ID is correct
- Verify AWS credentials have proper permissions
- Ensure the Knowledge Base sync is complete

### "Response generation failed"
- Check that the Bedrock model ID is correct
- Verify the model is available in your AWS region
- Check AWS service quotas for Bedrock

### Slow response times
- Check network latency to AWS services
- Consider using a faster model (e.g., Claude Haiku)
- Reduce `top_k` parameter to retrieve fewer chunks
