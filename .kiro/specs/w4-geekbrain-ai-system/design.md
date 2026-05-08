# Design Document: W4 GeekBrain AI System

## Overview

### System Purpose

GeekBrain AI System là một hệ thống AI trả lời câu hỏi thông minh về GeekBrain — một fintech startup vận hành 6 production services. Hệ thống được thiết kế theo kiến trúc phân tầng với 4 cấp độ khả năng tăng dần:

- **L1 (Simple RAG)**: Retrieval-Augmented Generation cơ bản từ knowledge base
- **L2 (Multi-Source RAG)**: Tổng hợp thông tin từ nhiều documents và giải quyết conflicts
- **L3 (Tool-Augmented RAG)**: Tích hợp tools để truy vấn databases và live APIs
- **L4 (Memory-Enabled RAG)**: Xử lý multi-turn conversations với context awareness

### Key Design Principles

1. **Incremental Complexity**: Mỗi level xây dựng trên nền tảng level trước, không thể bỏ qua
2. **Data Source Separation**: Ba nguồn dữ liệu riêng biệt (Knowledge Base, Database, Monitoring API) phục vụ các mục đích khác nhau
3. **Managed Services First**: Ưu tiên AWS managed services (Bedrock KB, Bedrock Agents) để giảm complexity
4. **Graceful Degradation**: Xử lý lỗi một cách elegant, không crash khi một component fail
5. **Observable by Design**: Mọi bước xử lý đều có thể trace và debug

### Success Criteria

- L1-L3 hoạt động ổn định = 90% điểm (9/10)
- Response time đáp ứng targets (5s L1, 8s L2, 10s L3, 12s L4)
- Numerical accuracy 100% cho L3 queries
- Multi-turn conversation coherence cho L4



## Architecture

### High-Level System Architecture

```mermaid
graph TB
    User[User] -->|Query| API[API Layer]
    API -->|Route| Orchestrator[Orchestration Engine]
    
    Orchestrator -->|Retrieve| RAG[RAG Pipeline]
    Orchestrator -->|Execute| Tools[Tool Execution Layer]
    Orchestrator -->|Load/Save| Memory[Memory Manager]
    
    RAG -->|Read| S3[S3 Bucket<br/>36 MD Files]
    RAG -->|Query| BedrockKB[Bedrock Knowledge Base]
    BedrockKB -->|Vector Search| OpenSearch[OpenSearch Serverless<br/>Vector Store]
    
    Tools -->|SQL Query| DB[(Database<br/>SQLite/PostgreSQL)]
    Tools -->|HTTP GET| MonAPI[Monitoring API<br/>FastAPI Local]
    
    Memory -->|Read/Write| StateStore[(Conversation State<br/>DynamoDB/Local)]
    
    Orchestrator -->|Generate| LLM[Amazon Bedrock<br/>Claude Sonnet]
    LLM -->|Response| API
    API -->|Answer| User
    
    style User fill:#e1f5ff
    style LLM fill:#fff4e1
    style BedrockKB fill:#e8f5e9
    style OpenSearch fill:#e8f5e9
    style DB fill:#f3e5f5
    style MonAPI fill:#f3e5f5
    style StateStore fill:#fff3e0
```

### Component Responsibilities

| Component | Responsibility | Technology |
|-----------|---------------|------------|
| **API Layer** | Accept user queries, return responses, handle errors | FastAPI / Flask / Lambda |
| **Orchestration Engine** | Route queries to appropriate handlers (RAG/Tools/Memory), manage LLM interaction loop | Custom code / LangChain / Bedrock Agents |
| **RAG Pipeline** | Retrieve relevant chunks from knowledge base, rank by relevance | Bedrock KB Retrieve API |
| **Tool Execution Layer** | Execute tool functions, validate inputs, handle errors | Python functions / Lambda |
| **Memory Manager** | Store/retrieve conversation state, manage context window | DynamoDB / Local dict |
| **LLM** | Generate responses, decide tool calls, resolve pronouns | Claude Sonnet via Bedrock |
| **Knowledge Base** | Store and index documents | S3 + Bedrock KB + OpenSearch |
| **Database** | Store structured numerical data | SQLite / PostgreSQL |
| **Monitoring API** | Provide live system metrics | FastAPI script |



### Data Flow by Level

#### L1 Flow: Simple RAG
```
User Query → API → Orchestrator → RAG Pipeline
  ↓
Bedrock KB Retrieve (top-K=5 chunks)
  ↓
LLM (system prompt + chunks + query)
  ↓
Response with source citation → User
```

#### L2 Flow: Multi-Source RAG
```
User Query → API → Orchestrator → RAG Pipeline
  ↓
Bedrock KB Retrieve (top-K=10 chunks, multiple docs)
  ↓
LLM (enhanced prompt + chunks + conflict resolution rules)
  ↓
Response with synthesis + conflict explanation → User
```

#### L3 Flow: Tool-Augmented RAG
```
User Query → API → Orchestrator
  ↓
Parallel: RAG Pipeline + Tool Routing Decision
  ↓
LLM receives: chunks + tool definitions + query
  ↓
LLM generates: tool_use request
  ↓
Tool Execution Layer: execute function
  ↓
Tool results → LLM
  ↓
LLM generates: final response with data
  ↓
Response → User
```

#### L4 Flow: Memory-Enabled
```
User Query → API → Orchestrator
  ↓
Memory Manager: load last N turns
  ↓
Query Rewriting (optional): resolve pronouns
  ↓
RAG + Tools (as in L3) + conversation history
  ↓
LLM generates response with context awareness
  ↓
Memory Manager: save turn
  ↓
Response → User
```



### AWS Service Integration Architecture

```mermaid
graph LR
    subgraph "Data Layer"
        S3[S3 Bucket<br/>geekbrain-kb-*]
        DB[(RDS PostgreSQL<br/>or SQLite)]
    end
    
    subgraph "AI/ML Layer"
        BedrockKB[Bedrock Knowledge Base]
        OpenSearch[OpenSearch Serverless<br/>Vector Store]
        Bedrock[Amazon Bedrock<br/>Claude Sonnet]
        Embeddings[Titan Embeddings v2]
    end
    
    subgraph "Compute Layer"
        Lambda1[Lambda: DB Query Tool]
        Lambda2[Lambda: Metrics Tool]
        Lambda3[Lambda: Other Tools]
    end
    
    subgraph "State Management"
        DynamoDB[(DynamoDB<br/>Conversation State)]
    end
    
    subgraph "Orchestration"
        Agent[Bedrock Agent<br/>or Custom Code]
    end
    
    S3 -->|Data Source| BedrockKB
    BedrockKB -->|Embeddings| Embeddings
    BedrockKB -->|Store Vectors| OpenSearch
    BedrockKB -->|Retrieve| Agent
    
    Agent -->|Invoke Model| Bedrock
    Agent -->|Call Tools| Lambda1
    Agent -->|Call Tools| Lambda2
    Agent -->|Call Tools| Lambda3
    
    Lambda1 -->|Query| DB
    Lambda2 -->|HTTP| MonAPI[Monitoring API<br/>External]
    
    Agent -->|Read/Write| DynamoDB
    
    style S3 fill:#ff9800
    style BedrockKB fill:#4caf50
    style Bedrock fill:#2196f3
    style DynamoDB fill:#9c27b0
```

### IAM Roles and Permissions

**Bedrock KB Role**:
- `s3:GetObject` on knowledge base bucket
- `aoss:APIAccessAll` on OpenSearch Serverless collection
- `bedrock:InvokeModel` for embeddings

**Lambda Execution Role** (for tools):
- `rds:DescribeDBInstances` (if using RDS)
- `dynamodb:GetItem`, `dynamodb:PutItem` (for conversation state)
- `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents`

**Bedrock Agent Role** (if using Agents):
- `bedrock:InvokeModel` for Claude
- `bedrock:Retrieve` for KB access
- `lambda:InvokeFunction` for action groups
- `dynamodb:*` for session state



## Components and Interfaces

### 1. RAG Pipeline (L1-L2)

#### Purpose
Retrieve relevant information from 36 markdown documents stored in S3, indexed by Bedrock Knowledge Base.

#### Interface
```python
class RAGPipeline:
    def retrieve(self, query: str, top_k: int = 5) -> List[Chunk]:
        """
        Retrieve relevant chunks from knowledge base.
        
        Args:
            query: User's question
            top_k: Number of chunks to retrieve (5 for L1, 10 for L2)
            
        Returns:
            List of Chunk objects with text, source, and score
        """
        pass
    
    def retrieve_and_generate(self, query: str, top_k: int = 5) -> Response:
        """
        Retrieve chunks and generate response using LLM.
        
        Args:
            query: User's question
            top_k: Number of chunks to retrieve
            
        Returns:
            Response object with answer and source citations
        """
        pass
```

#### Implementation Details

**Setup Phase**:
1. Create S3 bucket with versioning and encryption enabled
2. Upload 36 markdown files to S3
3. Create Bedrock Knowledge Base:
   - Data source: S3 bucket
   - Embedding model: Amazon Titan Embeddings v2 (1024 dimensions)
   - Vector store: OpenSearch Serverless (auto-created)
   - Chunking strategy: Default (300 tokens, 20% overlap)
4. Trigger sync job and wait for completion

**Retrieval Phase**:
```python
import boto3

bedrock_agent = boto3.client('bedrock-agent-runtime')

def retrieve_chunks(query: str, kb_id: str, top_k: int = 5):
    response = bedrock_agent.retrieve(
        knowledgeBaseId=kb_id,
        retrievalQuery={'text': query},
        retrievalConfiguration={
            'vectorSearchConfiguration': {
                'numberOfResults': top_k
            }
        }
    )
    
    chunks = []
    for result in response['retrievalResults']:
        chunks.append({
            'text': result['content']['text'],
            'source': result['location']['s3Location']['uri'],
            'score': result['score']
        })
    
    return chunks
```

**L1 vs L2 Differences**:

| Aspect | L1 | L2 |
|--------|----|----|
| Top-K | 5 chunks | 10 chunks |
| System Prompt | Basic citation | Conflict resolution rules |
| Metadata Filtering | None | Check version, date, status |
| Response Format | Single source | Multi-source synthesis |



### 2. Tool System (L3)

#### Purpose
Enable LLM to query structured databases and live APIs for numerical data and current system state.

#### Tool Interface
```python
from typing import Dict, Any, List
from dataclasses import dataclass

@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: Dict[str, Any]
    
@dataclass
class ToolResult:
    success: bool
    data: Any
    error: str = None

class ToolExecutor:
    def execute(self, tool_name: str, parameters: Dict[str, Any]) -> ToolResult:
        """Execute a tool function with given parameters."""
        pass
    
    def get_tool_definitions(self) -> List[ToolDefinition]:
        """Return list of available tools for LLM."""
        pass
```

#### Tool Implementations

**1. Database Query Tool**

```python
import sqlite3
from typing import List, Dict

class DatabaseQueryTool:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.read_only_keywords = ['SELECT', 'WITH']
        self.forbidden_keywords = ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER']
    
    def execute_query(self, sql: str) -> ToolResult:
        """
        Execute read-only SQL query against database.
        
        Args:
            sql: SQL query string
            
        Returns:
            ToolResult with rows or error message
        """
        # Validate query is read-only
        sql_upper = sql.strip().upper()
        if not any(sql_upper.startswith(kw) for kw in self.read_only_keywords):
            return ToolResult(
                success=False,
                data=None,
                error="Only SELECT queries are allowed"
            )
        
        if any(kw in sql_upper for kw in self.forbidden_keywords):
            return ToolResult(
                success=False,
                data=None,
                error="Write operations are not permitted"
            )
        
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(sql)
            rows = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            return ToolResult(success=True, data=rows)
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                error=f"Query execution failed: {str(e)}"
            )
    
    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="query_database",
            description=(
                "Execute SQL query against structured database. "
                "Use for HISTORICAL data: monthly costs, incident history, "
                "SLA targets, daily metrics from Jan-Mar 2026. "
                "Returns rows as list of dictionaries."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "SQL SELECT query to execute"
                    }
                },
                "required": ["sql"]
            }
        )
```

**Example Queries**:
```sql
-- Total Q1 2026 cost for PaymentGW
SELECT SUM(total_cost) as total 
FROM monthly_costs 
WHERE service = 'PaymentGW' 
  AND month IN ('2026-01', '2026-02', '2026-03');
-- Expected: 16500

-- Highest cost service in March 2026
SELECT service, total_cost 
FROM monthly_costs 
WHERE month = '2026-03' 
ORDER BY total_cost DESC 
LIMIT 1;
-- Expected: PaymentGW, 7500

-- NotificationSvc SLA target
SELECT latency_p99_ms 
FROM sla_targets 
WHERE service = 'NotificationSvc';
-- Expected: 2000
```



**2. Service Metrics Tool**

```python
import requests
from typing import Dict

class ServiceMetricsTool:
    def __init__(self, api_base_url: str = "http://localhost:8000"):
        self.api_base_url = api_base_url
        self.timeout = 3  # seconds
    
    def get_metrics(self, service_name: str) -> ToolResult:
        """
        Get current live metrics for a service.
        
        Args:
            service_name: Name of service (e.g., 'PaymentGW')
            
        Returns:
            ToolResult with current metrics or error
        """
        try:
            response = requests.get(
                f"{self.api_base_url}/metrics/{service_name}",
                timeout=self.timeout
            )
            
            if response.status_code == 404:
                return ToolResult(
                    success=False,
                    data=None,
                    error=f"Service '{service_name}' not found"
                )
            
            response.raise_for_status()
            data = response.json()
            
            return ToolResult(success=True, data=data)
            
        except requests.Timeout:
            return ToolResult(
                success=False,
                data=None,
                error="Monitoring API timeout - service may be down"
            )
        except requests.RequestException as e:
            return ToolResult(
                success=False,
                data=None,
                error=f"Failed to fetch metrics: {str(e)}"
            )
    
    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="get_service_metrics",
            description=(
                "Get CURRENT live performance metrics for a service. "
                "Use for real-time data: current latency, error rate, "
                "request volume. Returns p50/p95/p99 latency in ms, "
                "error_rate as percentage, requests_per_min."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "service_name": {
                        "type": "string",
                        "description": "Name of the service (e.g., PaymentGW, NotificationSvc)"
                    }
                },
                "required": ["service_name"]
            }
        )
```

**Example API Responses**:
```json
// GET /metrics/PaymentGW
{
  "service": "PaymentGW",
  "timestamp": "2026-03-15T10:30:00Z",
  "latency_p50_ms": 45,
  "latency_p95_ms": 120,
  "latency_p99_ms": 185,
  "error_rate": 0.02,
  "requests_per_min": 1250
}

// GET /metrics/NotificationSvc
{
  "service": "NotificationSvc",
  "timestamp": "2026-03-15T10:30:00Z",
  "latency_p50_ms": 1200,
  "latency_p95_ms": 2800,
  "latency_p99_ms": 3200,
  "error_rate": 0.15,
  "requests_per_min": 450
}
```



**3. Additional Tools (5 more)**

```python
class ServiceStatusTool:
    """Get live status of a service (healthy, degraded, down)."""
    
    def get_status(self, service_name: str) -> ToolResult:
        try:
            response = requests.get(f"{self.api_base_url}/status/{service_name}")
            response.raise_for_status()
            return ToolResult(success=True, data=response.json())
        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e))
    
    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="get_service_status",
            description="Get current operational status of a service (healthy/degraded/down)",
            parameters={
                "type": "object",
                "properties": {
                    "service_name": {"type": "string"}
                },
                "required": ["service_name"]
            }
        )

class ListServicesTool:
    """List all services in the system."""
    
    def list_services(self) -> ToolResult:
        try:
            response = requests.get(f"{self.api_base_url}/services")
            response.raise_for_status()
            return ToolResult(success=True, data=response.json())
        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e))
    
    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="list_services",
            description="Get list of all services in the GeekBrain system",
            parameters={"type": "object", "properties": {}}
        )

class IncidentHistoryTool:
    """Query incident history from database."""
    
    def get_incidents(self, service_name: str = None) -> ToolResult:
        if service_name:
            sql = f"SELECT * FROM incidents WHERE service = '{service_name}' ORDER BY occurred_at DESC"
        else:
            sql = "SELECT * FROM incidents ORDER BY occurred_at DESC LIMIT 20"
        
        return self.db_tool.execute_query(sql)
    
    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="get_incident_history",
            description="Get past incidents for a service or all services",
            parameters={
                "type": "object",
                "properties": {
                    "service_name": {
                        "type": "string",
                        "description": "Optional: filter by service name"
                    }
                }
            }
        )

class TeamInfoTool:
    """Retrieve team information from knowledge base."""
    
    def get_team_info(self, team_name: str) -> ToolResult:
        # This would use RAG pipeline to search for team documents
        query = f"Information about {team_name} team"
        chunks = self.rag_pipeline.retrieve(query, top_k=3)
        return ToolResult(success=True, data=chunks)
    
    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="get_team_info",
            description="Get information about a team (lead, members, responsibilities)",
            parameters={
                "type": "object",
                "properties": {
                    "team_name": {"type": "string"}
                },
                "required": ["team_name"]
            }
        )

class CompareServicesTool:
    """Compare metrics between multiple services."""
    
    def compare_services(self, service_names: List[str], metric: str) -> ToolResult:
        results = {}
        for service in service_names:
            metrics = self.metrics_tool.get_metrics(service)
            if metrics.success:
                results[service] = metrics.data.get(metric)
        
        return ToolResult(success=True, data=results)
    
    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="compare_services",
            description="Compare a specific metric across multiple services",
            parameters={
                "type": "object",
                "properties": {
                    "service_names": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "metric": {
                        "type": "string",
                        "description": "Metric to compare (e.g., latency_p99_ms, error_rate)"
                    }
                },
                "required": ["service_names", "metric"]
            }
        )
```



#### Tool Orchestration Loop

```python
class ToolOrchestrator:
    def __init__(self, tools: List[Any], llm_client):
        self.tools = {tool.get_definition().name: tool for tool in tools}
        self.tool_definitions = [tool.get_definition() for tool in tools]
        self.llm_client = llm_client
    
    def process_query_with_tools(self, query: str, context: str = "") -> str:
        """
        Main orchestration loop for tool-augmented queries.
        
        Flow:
        1. Send query + context + tool definitions to LLM
        2. LLM decides: answer directly OR use tool
        3. If tool_use: execute tool, send result back to LLM
        4. Repeat until LLM generates final answer
        """
        messages = [
            {"role": "user", "content": f"{context}\n\nQuery: {query}"}
        ]
        
        max_iterations = 5
        for iteration in range(max_iterations):
            # Call LLM with tool definitions
            response = self.llm_client.invoke(
                messages=messages,
                tools=self.tool_definitions
            )
            
            # Check if LLM wants to use a tool
            if response.stop_reason == "tool_use":
                tool_use = response.content[-1]  # Last content block is tool_use
                tool_name = tool_use.name
                tool_input = tool_use.input
                
                # Execute tool
                tool = self.tools[tool_name]
                result = tool.execute(**tool_input)
                
                # Add tool result to conversation
                messages.append({
                    "role": "assistant",
                    "content": response.content
                })
                messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": tool_use.id,
                        "content": str(result.data) if result.success else result.error
                    }]
                })
                
            elif response.stop_reason == "end_turn":
                # LLM generated final answer
                return response.content[0].text
            
            else:
                # Unexpected stop reason
                return f"Error: Unexpected stop reason {response.stop_reason}"
        
        return "Error: Max tool iterations exceeded"
```

**Tool Call Example Flow**:

```
User: "What was PaymentGW's total cost in Q1 2026?"

→ LLM receives: query + tool definitions

→ LLM generates tool_use:
{
  "name": "query_database",
  "input": {
    "sql": "SELECT SUM(total_cost) FROM monthly_costs WHERE service='PaymentGW' AND month IN ('2026-01','2026-02','2026-03')"
  }
}

→ System executes tool → returns: [{"total": 16500}]

→ LLM receives tool result

→ LLM generates final answer:
"PaymentGW's total infrastructure cost in Q1 2026 was $16,500."
```



### 3. Memory System (L4)

#### Purpose
Maintain conversation context across multiple turns to enable follow-up questions with pronoun resolution.

#### Memory Interface
```python
from typing import List, Dict
from dataclasses import dataclass
from datetime import datetime

@dataclass
class ConversationTurn:
    turn_id: int
    timestamp: datetime
    query: str
    response: str
    context_used: List[str]  # Sources/tools used
    
class MemoryManager:
    def save_turn(self, session_id: str, turn: ConversationTurn) -> None:
        """Save a conversation turn to persistent storage."""
        pass
    
    def get_history(self, session_id: str, last_n: int = None) -> List[ConversationTurn]:
        """Retrieve conversation history for a session."""
        pass
    
    def format_for_llm(self, history: List[ConversationTurn]) -> str:
        """Format conversation history for LLM context."""
        pass
    
    def clear_session(self, session_id: str) -> None:
        """Clear conversation history for a session."""
        pass
```

#### Memory Strategies

**Strategy 1: Buffer Memory (Simplest)**
```python
class BufferMemory(MemoryManager):
    """Store all turns, send all to LLM."""
    
    def __init__(self):
        self.sessions = {}  # session_id -> List[ConversationTurn]
    
    def save_turn(self, session_id: str, turn: ConversationTurn):
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        self.sessions[session_id].append(turn)
    
    def get_history(self, session_id: str, last_n: int = None):
        history = self.sessions.get(session_id, [])
        if last_n:
            return history[-last_n:]
        return history
    
    def format_for_llm(self, history: List[ConversationTurn]) -> str:
        formatted = "Previous conversation:\n\n"
        for turn in history:
            formatted += f"User: {turn.query}\n"
            formatted += f"Assistant: {turn.response}\n\n"
        return formatted
```

**Pros**: Simple, preserves all context  
**Cons**: Context window grows unbounded, expensive for long conversations  
**Best for**: Demo with <10 turns

**Strategy 2: Window Memory (Recommended)**
```python
class WindowMemory(MemoryManager):
    """Store all turns, send only last N to LLM."""
    
    def __init__(self, window_size: int = 5):
        self.window_size = window_size
        self.sessions = {}
    
    def save_turn(self, session_id: str, turn: ConversationTurn):
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        self.sessions[session_id].append(turn)
    
    def get_history(self, session_id: str, last_n: int = None):
        history = self.sessions.get(session_id, [])
        n = last_n or self.window_size
        return history[-n:]
    
    def format_for_llm(self, history: List[ConversationTurn]) -> str:
        if not history:
            return ""
        
        formatted = f"Recent conversation (last {len(history)} turns):\n\n"
        for turn in history:
            formatted += f"User: {turn.query}\n"
            formatted += f"Assistant: {turn.response}\n\n"
        return formatted
```

**Pros**: Bounded context size, predictable cost  
**Cons**: Loses older context  
**Best for**: Production use with long conversations



**Strategy 3: Query Rewriting (Advanced)**
```python
class QueryRewritingMemory(MemoryManager):
    """Rewrite query to be self-contained before processing."""
    
    def __init__(self, llm_client):
        self.llm_client = llm_client
        self.sessions = {}
    
    def rewrite_query(self, session_id: str, query: str) -> str:
        """
        Rewrite query to resolve pronouns and implicit references.
        """
        history = self.get_history(session_id, last_n=3)
        if not history:
            return query  # No context, return as-is
        
        context = self.format_for_llm(history)
        
        rewrite_prompt = f"""Given this conversation history:

{context}

The user asks: "{query}"

Rewrite the user's question to be self-contained, replacing pronouns and implicit references with explicit entities from the conversation history.

Examples:
- "Why did its costs spike?" → "Why did PaymentGW's costs spike?"
- "Which team is responsible?" → "Which team is responsible for PaymentGW?"
- "Is the deadline overdue?" → "Is the PaymentGW postmortem review deadline overdue?"

Rewritten question:"""

        response = self.llm_client.invoke(rewrite_prompt)
        rewritten = response.strip()
        
        return rewritten
    
    def save_turn(self, session_id: str, turn: ConversationTurn):
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        self.sessions[session_id].append(turn)
    
    def get_history(self, session_id: str, last_n: int = None):
        history = self.sessions.get(session_id, [])
        if last_n:
            return history[-last_n:]
        return history
```

**Pros**: Each query becomes self-contained, better retrieval quality  
**Cons**: Extra LLM call per query, adds latency  
**Best for**: Complex multi-turn conversations with many entity references

#### DynamoDB Schema for Persistent Memory

```python
# Table: geekbrain-conversations
# Partition Key: session_id (String)
# Sort Key: turn_id (Number)

{
    "session_id": "user123-20260315",
    "turn_id": 1,
    "timestamp": "2026-03-15T10:30:00Z",
    "query": "Which service had the highest cost in March 2026?",
    "response": "PaymentGW had the highest cost in March 2026 at $7,500.",
    "context_used": ["monthly_costs table"],
    "ttl": 1678896000  # Auto-delete after 30 days
}
```

```python
import boto3
from datetime import datetime, timedelta

class DynamoDBMemory(MemoryManager):
    def __init__(self, table_name: str):
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table(table_name)
    
    def save_turn(self, session_id: str, turn: ConversationTurn):
        ttl = int((datetime.now() + timedelta(days=30)).timestamp())
        
        self.table.put_item(Item={
            'session_id': session_id,
            'turn_id': turn.turn_id,
            'timestamp': turn.timestamp.isoformat(),
            'query': turn.query,
            'response': turn.response,
            'context_used': turn.context_used,
            'ttl': ttl
        })
    
    def get_history(self, session_id: str, last_n: int = None):
        response = self.table.query(
            KeyConditionExpression='session_id = :sid',
            ExpressionAttributeValues={':sid': session_id},
            ScanIndexForward=True  # Ascending order by turn_id
        )
        
        turns = [
            ConversationTurn(
                turn_id=item['turn_id'],
                timestamp=datetime.fromisoformat(item['timestamp']),
                query=item['query'],
                response=item['response'],
                context_used=item['context_used']
            )
            for item in response['Items']
        ]
        
        if last_n:
            return turns[-last_n:]
        return turns
```



## Data Models

### Knowledge Base Document Structure

**36 Markdown Files in S3**:
```
knowledge_base/
├── company/
│   ├── company_overview.md
│   ├── mission_values.md
│   └── org_structure.md
├── teams/
│   ├── team_platform.md
│   ├── team_commerce.md
│   ├── team_fintech.md
│   └── team_data.md
├── services/
│   ├── service_paymentgw.md
│   ├── service_ordersvc.md
│   ├── service_notificationsvc.md
│   ├── service_analyticsengine.md
│   ├── service_usermgmt.md
│   └── service_reportingapi.md
├── policies/
│   ├── deployment_policy.md
│   ├── incident_response_policy.md
│   ├── sla_policy.md
│   └── security_policy.md
├── architecture/
│   ├── system_architecture.md
│   ├── api_reference_v1.md (archived)
│   ├── api_reference_v2.md (current)
│   └── infrastructure_overview.md
├── postmortems/
│   ├── postmortem_2026_01_paymentgw.md
│   ├── postmortem_2026_02_notificationsvc.md
│   └── postmortem_2026_03_ordersvc.md
└── runbooks/
    ├── runbook_deployment.md
    ├── runbook_incident_response.md
    └── runbook_monitoring.md
```

**Document Metadata** (embedded in frontmatter):
```yaml
---
title: "PaymentGW Service Documentation"
version: "2.1"
status: "current"
last_updated: "2026-03-01"
team: "Platform"
tags: ["service", "payment", "api"]
---
```

**Conflict Example**:
- `api_reference_v1.md`: Rate limit = 500 req/min, status = "archived"
- `api_reference_v2.md`: Rate limit = 1000 req/min, status = "current"

System must detect version/status and prefer v2.



### Database Schema

**Table 1: monthly_costs**
```sql
CREATE TABLE monthly_costs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    service VARCHAR(50) NOT NULL,
    month VARCHAR(7) NOT NULL,  -- Format: YYYY-MM
    compute_cost DECIMAL(10,2),
    storage_cost DECIMAL(10,2),
    network_cost DECIMAL(10,2),
    total_cost DECIMAL(10,2) NOT NULL,
    UNIQUE(service, month)
);

-- Sample data
INSERT INTO monthly_costs VALUES
(1, 'PaymentGW', '2026-01', 2000.00, 500.00, 500.00, 3000.00),
(2, 'PaymentGW', '2026-02', 2500.00, 800.00, 700.00, 4000.00),
(3, 'PaymentGW', '2026-03', 4000.00, 2000.00, 1500.00, 7500.00),
(4, 'NotificationSvc', '2026-01', 800.00, 200.00, 100.00, 1100.00),
-- ... 36 rows total (6 services × 6 months)
```

**Table 2: incidents**
```sql
CREATE TABLE incidents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    service VARCHAR(50) NOT NULL,
    severity VARCHAR(10) NOT NULL,  -- P1, P2, P3
    occurred_at TIMESTAMP NOT NULL,
    resolved_at TIMESTAMP,
    duration_minutes INTEGER,
    root_cause TEXT,
    resolution TEXT,
    postmortem_link VARCHAR(200)
);

-- Sample data
INSERT INTO incidents VALUES
(1, 'PaymentGW', 'P1', '2026-01-15 14:30:00', '2026-01-15 16:45:00', 
 135, 'Database connection pool exhaustion', 
 'Increased pool size from 50 to 200', 
 'postmortem_2026_01_paymentgw.md'),
(2, 'NotificationSvc', 'P2', '2026-02-20 09:00:00', '2026-02-20 11:30:00',
 150, 'Message queue backlog', 
 'Scaled workers from 5 to 15',
 'postmortem_2026_02_notificationsvc.md');
-- ... ~20 incidents
```

**Table 3: sla_targets**
```sql
CREATE TABLE sla_targets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    service VARCHAR(50) NOT NULL UNIQUE,
    availability_percent DECIMAL(5,2),
    latency_p99_ms INTEGER,
    error_rate_max DECIMAL(5,4),
    uptime_hours_per_month INTEGER
);

-- Sample data
INSERT INTO sla_targets VALUES
(1, 'PaymentGW', 99.95, 200, 0.01, 719),
(2, 'NotificationSvc', 99.50, 2000, 0.05, 716),
(3, 'OrderSvc', 99.90, 500, 0.02, 718),
(4, 'AnalyticsEngine', 99.00, 5000, 0.10, 713),
(5, 'UserMgmt', 99.95, 300, 0.01, 719),
(6, 'ReportingAPI', 99.50, 3000, 0.05, 716);
```

**Table 4: daily_metrics**
```sql
CREATE TABLE daily_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    service VARCHAR(50) NOT NULL,
    date DATE NOT NULL,
    avg_latency_ms INTEGER,
    p99_latency_ms INTEGER,
    error_rate DECIMAL(5,4),
    total_requests INTEGER,
    UNIQUE(service, date)
);

-- Sample data (Jan-Mar 2026, 6 services × 90 days = 540 rows)
INSERT INTO daily_metrics VALUES
(1, 'PaymentGW', '2026-01-01', 45, 180, 0.015, 125000),
(2, 'PaymentGW', '2026-01-02', 48, 185, 0.018, 130000),
-- ...
```

**Seed Script Usage**:
```bash
cd data_package/scripts
uv sync
uv run python seed_data.py --db-type sqlite --db-path ../../geekbrain.db
# or
uv run python seed_data.py --db-type postgresql --db-url postgresql://user:pass@localhost/geekbrain
```



### Monitoring API Response Formats

**Endpoint: GET /services**
```json
{
  "services": [
    "PaymentGW",
    "OrderSvc",
    "NotificationSvc",
    "AnalyticsEngine",
    "UserMgmt",
    "ReportingAPI"
  ]
}
```

**Endpoint: GET /status/{service_name}**
```json
{
  "service": "NotificationSvc",
  "status": "degraded",
  "timestamp": "2026-03-15T10:30:00Z",
  "message": "High latency detected",
  "active_alerts": [
    {
      "severity": "warning",
      "message": "P99 latency exceeds SLA target"
    }
  ]
}
```

**Endpoint: GET /metrics/{service_name}**
```json
{
  "service": "PaymentGW",
  "timestamp": "2026-03-15T10:30:00Z",
  "latency_p50_ms": 45,
  "latency_p95_ms": 120,
  "latency_p99_ms": 185,
  "error_rate": 0.02,
  "requests_per_min": 1250
}
```

**Endpoint: GET /incidents**
```json
{
  "incidents": [
    {
      "service": "NotificationSvc",
      "severity": "P2",
      "occurred_at": "2026-03-14T15:30:00Z",
      "status": "investigating",
      "message": "Message queue backlog growing"
    }
  ]
}
```

**Endpoint: GET /incidents/{service_name}**
```json
{
  "service": "PaymentGW",
  "incidents": [
    {
      "severity": "P1",
      "occurred_at": "2026-01-15T14:30:00Z",
      "resolved_at": "2026-01-15T16:45:00Z",
      "duration_minutes": 135,
      "root_cause": "Database connection pool exhaustion"
    }
  ]
}
```

**Starting the API**:
```bash
cd data_package/scripts
uv sync
uv run uvicorn monitoring_api:app --host 0.0.0.0 --port 8000 --reload
```



### Conversation State Schema

**In-Memory (Python dict)**:
```python
conversation_state = {
    "session_id": "user123-20260315",
    "created_at": "2026-03-15T10:00:00Z",
    "last_updated": "2026-03-15T10:35:00Z",
    "turns": [
        {
            "turn_id": 1,
            "timestamp": "2026-03-15T10:30:00Z",
            "query": "Which service had the highest cost in March 2026?",
            "response": "PaymentGW had the highest cost in March 2026 at $7,500.",
            "tools_used": ["query_database"],
            "sources": ["monthly_costs table"]
        },
        {
            "turn_id": 2,
            "timestamp": "2026-03-15T10:32:00Z",
            "query": "Why did its costs spike?",
            "rewritten_query": "Why did PaymentGW's costs spike?",
            "response": "PaymentGW's costs spiked due to database connection pool exhaustion...",
            "tools_used": [],
            "sources": ["postmortem_2026_01_paymentgw.md"]
        }
    ],
    "entities": {
        "current_service": "PaymentGW",
        "current_team": "Platform",
        "current_month": "2026-03"
    }
}
```

**DynamoDB Item**:
```json
{
  "session_id": "user123-20260315",
  "turn_id": 1,
  "timestamp": "2026-03-15T10:30:00Z",
  "query": "Which service had the highest cost in March 2026?",
  "response": "PaymentGW had the highest cost in March 2026 at $7,500.",
  "tools_used": ["query_database"],
  "sources": ["monthly_costs table"],
  "entities": {
    "service": "PaymentGW",
    "month": "2026-03"
  },
  "ttl": 1678896000
}
```

### Tool Call/Response Format

**LLM Tool Use Request** (Claude format):
```json
{
  "role": "assistant",
  "content": [
    {
      "type": "text",
      "text": "I need to query the database to find the total cost."
    },
    {
      "type": "tool_use",
      "id": "toolu_01A2B3C4D5E6F7G8H9I0J1K2",
      "name": "query_database",
      "input": {
        "sql": "SELECT SUM(total_cost) FROM monthly_costs WHERE service='PaymentGW' AND month IN ('2026-01','2026-02','2026-03')"
      }
    }
  ]
}
```

**Tool Result Response**:
```json
{
  "role": "user",
  "content": [
    {
      "type": "tool_result",
      "tool_use_id": "toolu_01A2B3C4D5E6F7G8H9I0J1K2",
      "content": "[{\"total\": 16500}]"
    }
  ]
}
```

**Final LLM Response**:
```json
{
  "role": "assistant",
  "content": [
    {
      "type": "text",
      "text": "PaymentGW's total infrastructure cost in Q1 2026 was $16,500."
    }
  ],
  "stop_reason": "end_turn"
}
```



## System Prompt Engineering

### L1-L2 System Prompt (RAG Only)

```
You are an AI assistant for GeekBrain, a fintech startup. Your role is to answer questions about the company using the provided knowledge base documents.

INSTRUCTIONS:
1. Answer questions using ONLY the information in the provided context
2. ALWAYS cite the source document for your information
3. If the context doesn't contain the answer, say "I don't have that information in the knowledge base"
4. Be concise and direct

CITATION FORMAT:
- End your answer with: [Source: document_name.md]
- If using multiple sources, list all: [Sources: doc1.md, doc2.md]

CONFLICT RESOLUTION (L2):
When multiple documents provide different information:
1. Check for version numbers - prefer higher versions (v2 over v1)
2. Check for dates - prefer more recent dates
3. Check for status indicators - prefer "current" over "archived" or "superseded"
4. If you find conflicting information, explain which source you trust and why
5. Example: "The current rate limit is 1000 req/min (api_reference_v2.md, current). The previous version (v1, archived) specified 500 req/min."

RESPONSE LANGUAGE:
- Respond in Vietnamese unless the user asks in English
- Use clear, professional language
- Format numbers with appropriate units ($, ms, %, etc.)

Context documents:
{retrieved_chunks}

User question: {query}
```

### L3 System Prompt (With Tools)

```
You are an AI assistant for GeekBrain, a fintech startup. You can answer questions using:
1. Knowledge base documents (for policies, architecture, team info)
2. Database queries (for historical costs, incidents, SLA targets, daily metrics)
3. Monitoring API (for current live system status and metrics)

TOOL SELECTION GUIDE:
- Use query_database for:
  * Historical data (Jan-Mar 2026)
  * Exact costs, incident records, SLA targets
  * Questions like "What was X's cost in Q1?" or "How many incidents did Y have?"

- Use get_service_metrics for:
  * Current live data (right now)
  * Real-time latency, error rate, request volume
  * Questions like "What is X's current latency?" or "Is Y healthy right now?"

- Use knowledge base retrieval for:
  * Company policies, team structure, architecture
  * Postmortem details, runbooks, documentation
  * Questions like "Who leads Team X?" or "What is the deployment policy?"

IMPORTANT:
- For numerical questions, ALWAYS use tools - never guess or estimate
- Preserve exact numbers from tool results - don't round unless asked
- If a tool fails, explain the error and suggest alternatives
- You can use multiple tools in sequence if needed

CITATION:
- Cite tool results: [Source: Database query] or [Source: Monitoring API]
- Cite documents: [Source: document_name.md]

RESPONSE LANGUAGE: Vietnamese (unless user asks in English)

Available tools:
{tool_definitions}

User question: {query}
```



### L4 System Prompt (With Memory)

```
You are an AI assistant for GeekBrain, a fintech startup. You maintain context across a multi-turn conversation.

CONVERSATION CONTEXT:
You have access to the previous conversation turns. Use this context to:
1. Resolve pronouns (it, its, they, that, this)
2. Understand implicit references
3. Maintain topic continuity

PRONOUN RESOLUTION EXAMPLES:
- User: "Which service had highest cost?" → You: "PaymentGW at $7,500"
- User: "Why did its costs spike?" → Resolve "its" = PaymentGW
- User: "Which team is responsible?" → Resolve context = PaymentGW team
- User: "Is the deadline overdue?" → Resolve context = PaymentGW postmortem deadline

RESOLUTION STRATEGY:
1. Check the last 2-3 turns for entity mentions (service names, team names, dates)
2. If a pronoun appears, map it to the most recently mentioned relevant entity
3. If ambiguous, ask for clarification: "Which service do you mean?"

TOOLS AND KNOWLEDGE BASE:
- Use the same tool selection rules as L3
- After resolving pronouns, process the query normally

CONVERSATION HISTORY:
{conversation_history}

Current question: {query}
```

### Prompt Templates by Use Case

**Conflict Resolution Prompt**:
```
You retrieved these chunks about API rate limits:

Chunk 1 (api_reference_v1.md, archived):
"Rate limit: 500 requests per minute"

Chunk 2 (api_reference_v2.md, current):
"Rate limit: 1000 requests per minute"

Apply conflict resolution:
1. v2 > v1 (version number)
2. "current" > "archived" (status)
→ Answer: 1000 req/min, mention v1 was 500
```

**Tool Selection Prompt**:
```
User asks: "What was PaymentGW's total cost in Q1 2026?"

Analysis:
- "total cost" → numerical data
- "Q1 2026" → historical period (Jan-Mar)
- Not asking for "current" or "right now"

Decision: Use query_database tool
SQL: SELECT SUM(total_cost) FROM monthly_costs 
     WHERE service='PaymentGW' 
     AND month IN ('2026-01','2026-02','2026-03')
```

**Pronoun Resolution Prompt**:
```
Conversation history:
Turn 1: "Which service had highest cost in March?" → "PaymentGW at $7,500"
Turn 2: "Why did its costs spike?"

Resolve "its":
- Last mentioned service: PaymentGW
- "its" refers to: PaymentGW
- Rewritten query: "Why did PaymentGW's costs spike?"

Now process: Search knowledge base for PaymentGW cost spike reasons
```



## Error Handling

### Error Categories and Strategies

#### 1. Knowledge Base Errors

**Error**: Bedrock KB unavailable or sync in progress
```python
try:
    chunks = bedrock_agent.retrieve(...)
except ClientError as e:
    if e.response['Error']['Code'] == 'ResourceNotFoundException':
        return {
            "error": "Knowledge base not found. Please check configuration.",
            "suggestion": "Verify KB ID and ensure sync is complete"
        }
    elif e.response['Error']['Code'] == 'ThrottlingException':
        return {
            "error": "Too many requests to knowledge base",
            "suggestion": "Please try again in a moment"
        }
```

**Graceful Degradation**: If KB fails, system can still answer tool-based questions

#### 2. Database Errors

**Error**: Database connection failed
```python
try:
    result = db_tool.execute_query(sql)
except sqlite3.OperationalError as e:
    return ToolResult(
        success=False,
        data=None,
        error=f"Database unavailable: {str(e)}. Historical data queries cannot be processed."
    )
```

**Error**: Malformed SQL query
```python
if not sql.strip().upper().startswith('SELECT'):
    return ToolResult(
        success=False,
        data=None,
        error="Only SELECT queries are allowed. Please reformulate your query."
    )
```

**Graceful Degradation**: LLM receives error message and can:
- Suggest alternative data sources (knowledge base, monitoring API)
- Ask user to rephrase question
- Provide partial answer from available sources

#### 3. Monitoring API Errors

**Error**: API not running
```python
try:
    response = requests.get(url, timeout=3)
except requests.ConnectionError:
    return ToolResult(
        success=False,
        data=None,
        error="Monitoring API is not running. Cannot fetch live metrics. Please start the API with: uvicorn monitoring_api:app --port 8000"
    )
```

**Error**: Timeout
```python
except requests.Timeout:
    return ToolResult(
        success=False,
        data=None,
        error="Monitoring API timeout. The service may be experiencing issues."
    )
```

**Graceful Degradation**: 
- Use historical data from database as fallback
- Inform user that live data is unavailable

#### 4. LLM Errors

**Error**: Context window exceeded
```python
def truncate_context(chunks, max_tokens=8000):
    """Truncate chunks if total tokens exceed limit."""
    total_tokens = sum(estimate_tokens(c['text']) for c in chunks)
    
    if total_tokens > max_tokens:
        # Keep highest scoring chunks
        chunks = sorted(chunks, key=lambda x: x['score'], reverse=True)
        truncated = []
        current_tokens = 0
        
        for chunk in chunks:
            chunk_tokens = estimate_tokens(chunk['text'])
            if current_tokens + chunk_tokens <= max_tokens:
                truncated.append(chunk)
                current_tokens += chunk_tokens
            else:
                break
        
        return truncated
    
    return chunks
```

**Error**: Tool call parsing failed
```python
try:
    tool_use = response.content[-1]
    tool_name = tool_use.name
    tool_input = tool_use.input
except (AttributeError, KeyError, IndexError) as e:
    return {
        "error": "Failed to parse tool call from LLM",
        "details": str(e),
        "suggestion": "This is a system error. Please try rephrasing your question."
    }
```



#### 5. Memory Errors

**Error**: Session not found
```python
def get_history(self, session_id: str):
    if session_id not in self.sessions:
        # Initialize new session instead of error
        self.sessions[session_id] = []
        return []
    return self.sessions[session_id]
```

**Error**: DynamoDB unavailable (L4)
```python
try:
    self.table.put_item(Item=item)
except ClientError as e:
    # Log error but don't fail the request
    logger.error(f"Failed to save conversation turn: {e}")
    # Continue without persistent memory
    # Use in-memory fallback
```

### Error Response Format

**Standard Error Response**:
```json
{
  "success": false,
  "error": {
    "type": "DatabaseConnectionError",
    "message": "Unable to connect to database",
    "details": "sqlite3.OperationalError: unable to open database file",
    "suggestion": "Please ensure the database file exists and is accessible"
  },
  "partial_result": null
}
```

**Error with Partial Result**:
```json
{
  "success": true,
  "warning": "Monitoring API unavailable, using historical data only",
  "result": {
    "answer": "Based on historical data from March 2026, PaymentGW's average p99 latency was 185ms. Current live metrics are unavailable.",
    "sources": ["daily_metrics table"],
    "limitations": ["Live metrics unavailable"]
  }
}
```

### Timeout Configuration

```python
TIMEOUTS = {
    "bedrock_retrieve": 10,      # seconds
    "bedrock_invoke": 30,        # seconds
    "database_query": 5,         # seconds
    "monitoring_api": 3,         # seconds
    "total_request": 15          # seconds (L1-L2)
                                 # 20 seconds (L3-L4)
}
```

### Retry Strategy

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10)
)
def call_bedrock_with_retry(client, **kwargs):
    """Retry Bedrock calls with exponential backoff."""
    return client.invoke_model(**kwargs)
```

**Retry Policy**:
- Bedrock API calls: 3 attempts, exponential backoff
- Database queries: 2 attempts, 1s delay
- Monitoring API: 1 attempt only (fail fast for live data)



## Testing Strategy

### Unit Testing

**Test Coverage by Component**:

```python
# tests/test_rag_pipeline.py
def test_retrieve_chunks():
    """Test retrieval returns expected number of chunks."""
    pipeline = RAGPipeline(kb_id="test-kb")
    chunks = pipeline.retrieve("Who leads Team Platform?", top_k=5)
    assert len(chunks) == 5
    assert all('text' in c and 'source' in c for c in chunks)

def test_retrieve_with_conflict():
    """Test conflict resolution prefers current version."""
    chunks = pipeline.retrieve("API rate limit", top_k=10)
    # Should retrieve both v1 and v2 docs
    sources = [c['source'] for c in chunks]
    assert any('v2' in s for s in sources)

# tests/test_database_tool.py
def test_database_query_success():
    """Test successful database query."""
    tool = DatabaseQueryTool("test.db")
    result = tool.execute_query(
        "SELECT SUM(total_cost) FROM monthly_costs WHERE service='PaymentGW'"
    )
    assert result.success == True
    assert result.data[0]['sum'] == 16500

def test_database_query_rejects_write():
    """Test write operations are rejected."""
    tool = DatabaseQueryTool("test.db")
    result = tool.execute_query("DELETE FROM monthly_costs")
    assert result.success == False
    assert "not allowed" in result.error.lower()

def test_database_query_malformed_sql():
    """Test malformed SQL returns error."""
    tool = DatabaseQueryTool("test.db")
    result = tool.execute_query("SELCT * FORM monthly_costs")
    assert result.success == False

# tests/test_monitoring_tool.py
def test_get_metrics_success(mock_api):
    """Test successful metrics retrieval."""
    tool = ServiceMetricsTool("http://localhost:8000")
    result = tool.get_metrics("PaymentGW")
    assert result.success == True
    assert 'latency_p99_ms' in result.data

def test_get_metrics_service_not_found(mock_api):
    """Test handling of unknown service."""
    tool = ServiceMetricsTool("http://localhost:8000")
    result = tool.get_metrics("UnknownService")
    assert result.success == False
    assert "not found" in result.error.lower()

def test_get_metrics_timeout():
    """Test timeout handling."""
    tool = ServiceMetricsTool("http://localhost:9999")  # Not running
    result = tool.get_metrics("PaymentGW")
    assert result.success == False
    assert "timeout" in result.error.lower()

# tests/test_memory.py
def test_save_and_retrieve_turn():
    """Test conversation turn persistence."""
    memory = BufferMemory()
    turn = ConversationTurn(
        turn_id=1,
        timestamp=datetime.now(),
        query="Test query",
        response="Test response",
        context_used=[]
    )
    memory.save_turn("session1", turn)
    history = memory.get_history("session1")
    assert len(history) == 1
    assert history[0].query == "Test query"

def test_window_memory_limits_turns():
    """Test window memory returns only last N turns."""
    memory = WindowMemory(window_size=3)
    for i in range(5):
        turn = ConversationTurn(turn_id=i, ...)
        memory.save_turn("session1", turn)
    
    history = memory.get_history("session1")
    assert len(history) == 3
    assert history[0].turn_id == 2  # Last 3: 2, 3, 4
```



### Integration Testing

**End-to-End Test Suite**:

```python
# tests/integration/test_l1_simple_rag.py
def test_l1_single_fact_retrieval():
    """Test L1: Single fact with source citation."""
    system = GeekBrainAI(level="L1")
    
    response = system.query("Who is the Team Platform lead?")
    
    assert "Alex Chen" in response.answer
    assert "team_platform.md" in response.sources
    assert response.processing_time < 5.0  # L1 target: 5s

def test_l1_deployment_policy():
    """Test L1: Deployment freeze window."""
    system = GeekBrainAI(level="L1")
    
    response = system.query("What is the deployment freeze window?")
    
    assert "Friday 18:00" in response.answer
    assert "Monday 08:00" in response.answer
    assert "deployment_policy.md" in response.sources

# tests/integration/test_l2_multi_source.py
def test_l2_conflict_resolution():
    """Test L2: Resolve API rate limit conflict."""
    system = GeekBrainAI(level="L2")
    
    response = system.query("What is PaymentGW's API rate limit?")
    
    assert "1000" in response.answer  # v2 value
    assert response.processing_time < 8.0  # L2 target: 8s
    # Should mention v1 was 500
    assert "500" in response.answer or "v1" in response.answer.lower()

def test_l2_multi_document_synthesis():
    """Test L2: Synthesize from multiple documents."""
    system = GeekBrainAI(level="L2")
    
    response = system.query(
        "Can Team Commerce deploy on Friday night? What approvals do they need?"
    )
    
    assert len(response.sources) >= 2  # Multiple docs
    assert "deployment_policy.md" in response.sources
    assert response.processing_time < 8.0

# tests/integration/test_l3_tools.py
def test_l3_database_query_q1_cost():
    """Test L3: Query Q1 2026 total cost."""
    system = GeekBrainAI(level="L3")
    
    response = system.query("What was PaymentGW's total infrastructure cost in Q1 2026?")
    
    assert "16500" in response.answer or "16,500" in response.answer
    assert response.tools_used == ["query_database"]
    assert response.processing_time < 10.0  # L3 target: 10s

def test_l3_monitoring_api_current_latency():
    """Test L3: Get current live metrics."""
    system = GeekBrainAI(level="L3")
    
    response = system.query("What is PaymentGW's current p99 latency?")
    
    assert "ms" in response.answer.lower()
    assert response.tools_used == ["get_service_metrics"]
    assert response.processing_time < 10.0

def test_l3_combined_tools_sla_check():
    """Test L3: Use both database and API."""
    system = GeekBrainAI(level="L3")
    
    response = system.query("Is NotificationSvc meeting its SLA targets?")
    
    # Should call both tools
    assert "query_database" in response.tools_used  # For SLA target
    assert "get_service_metrics" in response.tools_used  # For current metrics
    # Should compare 3200ms (current) vs 2000ms (target)
    assert "not meeting" in response.answer.lower() or "exceeds" in response.answer.lower()

# tests/integration/test_l4_memory.py
def test_l4_multi_turn_conversation():
    """Test L4: Multi-turn with pronoun resolution."""
    system = GeekBrainAI(level="L4")
    session_id = "test-session-1"
    
    # Turn 1
    r1 = system.query("Which service had the highest cost in March 2026?", session_id)
    assert "PaymentGW" in r1.answer
    
    # Turn 2 - pronoun "its"
    r2 = system.query("Why did its costs spike?", session_id)
    assert "PaymentGW" in r2.context_used  # Should resolve "its" to PaymentGW
    
    # Turn 3 - implicit reference
    r3 = system.query("Which team is responsible?", session_id)
    assert "Platform" in r3.answer or "Alex Chen" in r3.answer
    
    # Turn 4 - continued context
    r4 = system.query("Is the postmortem review deadline overdue?", session_id)
    assert r4.processing_time < 12.0  # L4 target: 12s
```



### Numerical Accuracy Validation

**Critical Test Cases for L3**:

```python
# tests/validation/test_numerical_accuracy.py

EXPECTED_VALUES = {
    "paymentgw_q1_2026_total": 16500,
    "paymentgw_march_2026": 7500,
    "notificationsvc_sla_latency": 2000,
    "paymentgw_jan_2026": 3000,
    "paymentgw_feb_2026": 4000,
}

def test_all_numerical_queries():
    """Validate exact numerical accuracy for all L3 queries."""
    system = GeekBrainAI(level="L3")
    
    test_cases = [
        {
            "query": "What was PaymentGW's total infrastructure cost in Q1 2026?",
            "expected": 16500,
            "tolerance": 0  # Must be exact
        },
        {
            "query": "Which service had the highest cost in March 2026?",
            "expected_service": "PaymentGW",
            "expected_cost": 7500
        },
        {
            "query": "What is NotificationSvc's SLA target for p99 latency?",
            "expected": 2000,
            "unit": "ms"
        }
    ]
    
    for case in test_cases:
        response = system.query(case["query"])
        extracted_number = extract_number(response.answer)
        
        assert extracted_number == case["expected"], \
            f"Expected {case['expected']}, got {extracted_number} for query: {case['query']}"

def extract_number(text: str) -> float:
    """Extract numerical value from response text."""
    import re
    # Remove commas, extract number
    numbers = re.findall(r'[\d,]+\.?\d*', text)
    if numbers:
        return float(numbers[0].replace(',', ''))
    return None
```

### Performance Testing

```python
# tests/performance/test_response_times.py

def test_l1_response_time():
    """Verify L1 meets 5s target."""
    system = GeekBrainAI(level="L1")
    
    queries = [
        "Who is the Team Platform lead?",
        "What is the deployment freeze window?",
        "What authentication method does PaymentGW use?"
    ]
    
    for query in queries:
        start = time.time()
        response = system.query(query)
        elapsed = time.time() - start
        
        assert elapsed < 5.0, f"L1 query took {elapsed}s, target is 5s"

def test_l3_response_time_with_tools():
    """Verify L3 meets 10s target."""
    system = GeekBrainAI(level="L3")
    
    queries = [
        "What was PaymentGW's total cost in Q1 2026?",
        "What is PaymentGW's current p99 latency?",
        "Is NotificationSvc meeting its SLA targets?"
    ]
    
    for query in queries:
        start = time.time()
        response = system.query(query)
        elapsed = time.time() - start
        
        assert elapsed < 10.0, f"L3 query took {elapsed}s, target is 10s"

def test_concurrent_requests():
    """Test system handles concurrent requests."""
    import concurrent.futures
    
    system = GeekBrainAI(level="L3")
    queries = ["Query 1", "Query 2", "Query 3", "Query 4", "Query 5"]
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(system.query, q) for q in queries]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
    
    assert len(results) == 5
    assert all(r.success for r in results)
```



## Observability (Bonus A)

### Dashboard Architecture

```mermaid
graph LR
    Query[User Query] --> API[API Layer]
    API --> Logger[Event Logger]
    Logger --> Store[(Event Store<br/>In-Memory/Redis)]
    
    API --> Orchestrator[Orchestrator]
    Orchestrator --> Logger
    
    Store --> Dashboard[Web Dashboard<br/>FastAPI + WebSocket]
    Dashboard --> Browser[Browser UI]
    
    style Dashboard fill:#4caf50
    style Browser fill:#2196f3
```

### Event Logging

```python
from dataclasses import dataclass
from typing import List, Dict, Any
from datetime import datetime
import json

@dataclass
class ProcessingEvent:
    event_id: str
    timestamp: datetime
    event_type: str  # query_received, retrieval_started, tool_called, llm_invoked, response_generated
    data: Dict[str, Any]

class EventLogger:
    def __init__(self):
        self.events = {}  # query_id -> List[ProcessingEvent]
    
    def log_query_received(self, query_id: str, query: str):
        event = ProcessingEvent(
            event_id=f"{query_id}-001",
            timestamp=datetime.now(),
            event_type="query_received",
            data={"query": query}
        )
        self._add_event(query_id, event)
    
    def log_retrieval(self, query_id: str, chunks: List[Dict]):
        event = ProcessingEvent(
            event_id=f"{query_id}-002",
            timestamp=datetime.now(),
            event_type="retrieval_completed",
            data={
                "num_chunks": len(chunks),
                "chunks": [
                    {
                        "text": c['text'][:200] + "...",
                        "source": c['source'],
                        "score": c['score']
                    }
                    for c in chunks
                ]
            }
        )
        self._add_event(query_id, event)
    
    def log_tool_call(self, query_id: str, tool_name: str, parameters: Dict, result: Any):
        event = ProcessingEvent(
            event_id=f"{query_id}-003",
            timestamp=datetime.now(),
            event_type="tool_executed",
            data={
                "tool_name": tool_name,
                "parameters": parameters,
                "result": str(result)[:500]  # Truncate long results
            }
        )
        self._add_event(query_id, event)
    
    def log_llm_invocation(self, query_id: str, prompt: str, response: str):
        event = ProcessingEvent(
            event_id=f"{query_id}-004",
            timestamp=datetime.now(),
            event_type="llm_invoked",
            data={
                "prompt_length": len(prompt),
                "prompt_preview": prompt[:500] + "...",
                "response": response
            }
        )
        self._add_event(query_id, event)
    
    def log_response_generated(self, query_id: str, response: str, processing_time: float):
        event = ProcessingEvent(
            event_id=f"{query_id}-005",
            timestamp=datetime.now(),
            event_type="response_generated",
            data={
                "response": response,
                "processing_time_ms": processing_time * 1000
            }
        )
        self._add_event(query_id, event)
    
    def _add_event(self, query_id: str, event: ProcessingEvent):
        if query_id not in self.events:
            self.events[query_id] = []
        self.events[query_id].append(event)
    
    def get_events(self, query_id: str) -> List[ProcessingEvent]:
        return self.events.get(query_id, [])
```



### Dashboard Implementation

```python
# dashboard/app.py
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
import json

app = FastAPI()
event_logger = EventLogger()  # Shared instance

@app.get("/")
async def get_dashboard():
    """Serve dashboard HTML."""
    return HTMLResponse(content=DASHBOARD_HTML)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time event streaming."""
    await websocket.accept()
    
    while True:
        # Wait for query_id from client
        data = await websocket.receive_text()
        query_id = json.loads(data)['query_id']
        
        # Stream events as they occur
        while True:
            events = event_logger.get_events(query_id)
            await websocket.send_json({
                "query_id": query_id,
                "events": [
                    {
                        "timestamp": e.timestamp.isoformat(),
                        "type": e.event_type,
                        "data": e.data
                    }
                    for e in events
                ]
            })
            
            # Check if processing complete
            if events and events[-1].event_type == "response_generated":
                break
            
            await asyncio.sleep(0.5)  # Poll every 500ms

@app.get("/api/queries")
async def list_queries():
    """List all processed queries."""
    return {
        "queries": [
            {
                "query_id": qid,
                "first_event": events[0].timestamp.isoformat(),
                "num_events": len(events)
            }
            for qid, events in event_logger.events.items()
        ]
    }

@app.get("/api/query/{query_id}")
async def get_query_details(query_id: str):
    """Get detailed events for a query."""
    events = event_logger.get_events(query_id)
    return {
        "query_id": query_id,
        "events": [
            {
                "event_id": e.event_id,
                "timestamp": e.timestamp.isoformat(),
                "type": e.event_type,
                "data": e.data
            }
            for e in events
        ]
    }
```

### Dashboard UI (HTML + JavaScript)

```html
<!-- dashboard/templates/index.html -->
<!DOCTYPE html>
<html>
<head>
    <title>GeekBrain AI - Observability Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .event { 
            background: white; 
            padding: 15px; 
            margin: 10px 0; 
            border-radius: 5px;
            border-left: 4px solid #2196f3;
        }
        .event.retrieval { border-left-color: #4caf50; }
        .event.tool { border-left-color: #ff9800; }
        .event.llm { border-left-color: #9c27b0; }
        .event.response { border-left-color: #f44336; }
        .timestamp { color: #666; font-size: 0.9em; }
        .chunk { 
            background: #f9f9f9; 
            padding: 10px; 
            margin: 5px 0; 
            border-radius: 3px;
            font-size: 0.9em;
        }
        .tool-call {
            background: #fff3e0;
            padding: 10px;
            border-radius: 3px;
            font-family: monospace;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>GeekBrain AI - Processing Pipeline</h1>
        <div id="events"></div>
    </div>
    
    <script>
        const ws = new WebSocket('ws://localhost:8001/ws');
        const eventsDiv = document.getElementById('events');
        
        ws.onopen = () => {
            // Send query_id to start streaming
            const queryId = new URLSearchParams(window.location.search).get('query_id');
            ws.send(JSON.stringify({query_id: queryId}));
        };
        
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            eventsDiv.innerHTML = '';  // Clear
            
            data.events.forEach(e => {
                const eventDiv = document.createElement('div');
                eventDiv.className = `event ${e.type.split('_')[0]}`;
                
                let content = `
                    <div class="timestamp">${e.timestamp}</div>
                    <h3>${formatEventType(e.type)}</h3>
                `;
                
                if (e.type === 'query_received') {
                    content += `<p><strong>Query:</strong> ${e.data.query}</p>`;
                }
                else if (e.type === 'retrieval_completed') {
                    content += `<p><strong>Retrieved ${e.data.num_chunks} chunks:</strong></p>`;
                    e.data.chunks.forEach(c => {
                        content += `
                            <div class="chunk">
                                <strong>Source:</strong> ${c.source} (score: ${c.score.toFixed(3)})<br>
                                ${c.text}
                            </div>
                        `;
                    });
                }
                else if (e.type === 'tool_executed') {
                    content += `
                        <div class="tool-call">
                            <strong>Tool:</strong> ${e.data.tool_name}<br>
                            <strong>Parameters:</strong> ${JSON.stringify(e.data.parameters, null, 2)}<br>
                            <strong>Result:</strong> ${e.data.result}
                        </div>
                    `;
                }
                else if (e.type === 'llm_invoked') {
                    content += `
                        <p><strong>Prompt length:</strong> ${e.data.prompt_length} chars</p>
                        <p><strong>Response:</strong> ${e.data.response}</p>
                    `;
                }
                else if (e.type === 'response_generated') {
                    content += `
                        <p><strong>Final Response:</strong> ${e.data.response}</p>
                        <p><strong>Processing Time:</strong> ${e.data.processing_time_ms.toFixed(0)}ms</p>
                    `;
                }
                
                eventDiv.innerHTML = content;
                eventsDiv.appendChild(eventDiv);
            });
        };
        
        function formatEventType(type) {
            return type.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
        }
    </script>
</body>
</html>
```

**Dashboard Features**:
- Real-time event streaming via WebSocket
- Color-coded event types (retrieval, tool, LLM, response)
- Retrieved chunks with sources and scores
- Tool calls with parameters and results
- LLM input/output
- Processing time breakdown



## Performance Considerations

### Response Time Targets

| Level | Target | Breakdown |
|-------|--------|-----------|
| L1 | 5s | Retrieval (1s) + LLM (3s) + Overhead (1s) |
| L2 | 8s | Retrieval (2s) + LLM (5s) + Overhead (1s) |
| L3 | 10s | Retrieval (1s) + Tool (2s) + LLM (6s) + Overhead (1s) |
| L4 | 12s | Memory (1s) + Retrieval (1s) + Tool (2s) + LLM (7s) + Overhead (1s) |

### Optimization Strategies

#### 1. Caching

**Retrieval Cache**:
```python
from functools import lru_cache
import hashlib

class CachedRAGPipeline:
    def __init__(self, kb_id: str, cache_size: int = 100):
        self.kb_id = kb_id
        self.cache = {}
    
    def retrieve(self, query: str, top_k: int = 5):
        # Create cache key from query + top_k
        cache_key = hashlib.md5(f"{query}:{top_k}".encode()).hexdigest()
        
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # Actual retrieval
        chunks = self._retrieve_from_bedrock(query, top_k)
        
        # Cache result
        self.cache[cache_key] = chunks
        
        # LRU eviction if cache too large
        if len(self.cache) > 100:
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
        
        return chunks
```

**Database Query Cache**:
```python
class CachedDatabaseTool:
    def __init__(self, db_path: str, cache_ttl: int = 300):
        self.db_path = db_path
        self.cache = {}
        self.cache_ttl = cache_ttl
    
    def execute_query(self, sql: str):
        cache_key = hashlib.md5(sql.encode()).hexdigest()
        
        if cache_key in self.cache:
            cached_result, cached_time = self.cache[cache_key]
            if time.time() - cached_time < self.cache_ttl:
                return cached_result
        
        # Execute query
        result = self._execute_sql(sql)
        
        # Cache result
        self.cache[cache_key] = (result, time.time())
        
        return result
```

**When to Cache**:
- ✅ Retrieval results (queries rarely change)
- ✅ Database queries (historical data is immutable)
- ❌ Monitoring API calls (live data changes constantly)
- ❌ LLM responses (non-deterministic with temperature > 0)



#### 2. Parallel Execution

**Parallel Retrieval + Tool Routing**:
```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

async def process_query_parallel(query: str):
    """Execute retrieval and tool routing in parallel."""
    
    async def retrieve_async():
        return await asyncio.to_thread(rag_pipeline.retrieve, query)
    
    async def analyze_query_async():
        return await asyncio.to_thread(query_analyzer.needs_tools, query)
    
    # Run both in parallel
    chunks, needs_tools = await asyncio.gather(
        retrieve_async(),
        analyze_query_async()
    )
    
    return chunks, needs_tools
```

**Parallel Tool Calls**:
```python
async def execute_multiple_tools(tool_calls: List[Dict]):
    """Execute multiple independent tool calls in parallel."""
    
    async def execute_tool_async(tool_call):
        tool_name = tool_call['name']
        parameters = tool_call['parameters']
        return await asyncio.to_thread(
            tools[tool_name].execute,
            **parameters
        )
    
    results = await asyncio.gather(*[
        execute_tool_async(tc) for tc in tool_calls
    ])
    
    return results
```

**Savings**:
- Sequential: Retrieval (1s) + Tool (2s) = 3s
- Parallel: max(Retrieval, Tool) = 2s
- **33% faster**

#### 3. Batch Processing

**Batch Embedding for Knowledge Base Sync**:
```python
def sync_knowledge_base_optimized(documents: List[str], batch_size: int = 10):
    """Sync documents in batches instead of one-by-one."""
    
    for i in range(0, len(documents), batch_size):
        batch = documents[i:i+batch_size]
        
        # Upload batch to S3
        upload_batch_to_s3(batch)
        
        # Trigger single sync job for batch
        bedrock_kb.start_ingestion_job(
            knowledgeBaseId=kb_id,
            dataSourceId=data_source_id
        )
        
        # Wait for completion
        wait_for_sync_completion()
```

**Savings**: 36 documents × 10s each = 360s sequential → 4 batches × 30s = 120s batched

#### 4. Connection Pooling

**Database Connection Pool**:
```python
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    'postgresql://user:pass@localhost/geekbrain',
    poolclass=QueuePool,
    pool_size=10,          # Keep 10 connections open
    max_overflow=20,       # Allow 20 more if needed
    pool_pre_ping=True,    # Verify connection before use
    pool_recycle=3600      # Recycle connections after 1 hour
)

class DatabaseToolWithPool:
    def __init__(self, engine):
        self.engine = engine
    
    def execute_query(self, sql: str):
        # Reuse connection from pool
        with self.engine.connect() as conn:
            result = conn.execute(sql)
            return result.fetchall()
```

**HTTP Connection Pool for Monitoring API**:
```python
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

session = requests.Session()
retry = Retry(total=3, backoff_factor=0.3)
adapter = HTTPAdapter(
    max_retries=retry,
    pool_connections=10,
    pool_maxsize=20
)
session.mount('http://', adapter)

class ServiceMetricsToolWithPool:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = session
    
    def get_metrics(self, service_name: str):
        response = self.session.get(f"{self.base_url}/metrics/{service_name}")
        return response.json()
```



#### 5. LLM Optimization

**Model Selection**:
| Model | Speed | Cost | Quality | Use Case |
|-------|-------|------|---------|----------|
| Claude Haiku | Fast (1-2s) | Low | Good | L1-L2 simple queries |
| Claude Sonnet | Medium (3-5s) | Medium | Excellent | L3-L4 complex queries |
| Claude Opus | Slow (8-12s) | High | Best | Investigation queries (Bonus B) |

**Streaming Responses**:
```python
def invoke_llm_streaming(prompt: str):
    """Stream LLM response for better perceived performance."""
    
    response = bedrock_runtime.invoke_model_with_response_stream(
        modelId='anthropic.claude-3-sonnet-20240229-v1:0',
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 2000,
            "stream": True
        })
    )
    
    for event in response['body']:
        chunk = json.loads(event['chunk']['bytes'])
        if chunk['type'] == 'content_block_delta':
            yield chunk['delta']['text']
```

**Temperature Tuning**:
```python
# L1-L2: Factual retrieval → temperature = 0 (deterministic)
# L3: Tool use + facts → temperature = 0.1 (mostly deterministic)
# L4: Conversation → temperature = 0.3 (slight creativity for natural flow)
# Bonus B: Investigation → temperature = 0.5 (more creative reasoning)
```

#### 6. Context Window Management

**Chunk Truncation Strategy**:
```python
def truncate_chunks_intelligently(chunks: List[Dict], max_tokens: int = 6000):
    """
    Keep highest-scoring chunks that fit in context window.
    """
    # Sort by relevance score
    sorted_chunks = sorted(chunks, key=lambda x: x['score'], reverse=True)
    
    selected = []
    total_tokens = 0
    
    for chunk in sorted_chunks:
        chunk_tokens = estimate_tokens(chunk['text'])
        
        if total_tokens + chunk_tokens <= max_tokens:
            selected.append(chunk)
            total_tokens += chunk_tokens
        else:
            break
    
    return selected

def estimate_tokens(text: str) -> int:
    """Rough estimate: 1 token ≈ 4 characters."""
    return len(text) // 4
```

**Conversation History Compression**:
```python
def compress_conversation_history(turns: List[ConversationTurn]) -> str:
    """
    Compress old turns to summaries, keep recent turns full.
    """
    if len(turns) <= 3:
        return format_full_history(turns)
    
    # Keep last 3 turns full
    recent = turns[-3:]
    old = turns[:-3]
    
    # Summarize old turns
    summary = f"Earlier in conversation ({len(old)} turns):\n"
    for turn in old:
        summary += f"- User asked about {extract_topic(turn.query)}\n"
    
    # Full recent turns
    recent_text = format_full_history(recent)
    
    return summary + "\n" + recent_text
```



### Concurrent Request Handling

**FastAPI with Async Handlers**:
```python
from fastapi import FastAPI, BackgroundTasks
import asyncio

app = FastAPI()

@app.post("/query")
async def handle_query(request: QueryRequest):
    """Handle query asynchronously."""
    
    query_id = generate_query_id()
    
    # Process in background
    asyncio.create_task(process_query_async(query_id, request.query))
    
    return {"query_id": query_id, "status": "processing"}

@app.get("/query/{query_id}")
async def get_query_result(query_id: str):
    """Poll for query result."""
    
    result = await get_result_from_cache(query_id)
    
    if result:
        return {"status": "complete", "result": result}
    else:
        return {"status": "processing"}

async def process_query_async(query_id: str, query: str):
    """Process query asynchronously."""
    
    try:
        result = await orchestrator.process(query)
        await save_result_to_cache(query_id, result)
    except Exception as e:
        await save_error_to_cache(query_id, str(e))
```

**Load Testing Results** (Expected):
```
Concurrent Users: 10
Average Response Time: 6.2s (L1-L2), 11.5s (L3)
95th Percentile: 8.1s (L1-L2), 14.2s (L3)
Throughput: ~8 queries/minute
Error Rate: <1%
```

### Resource Limits

**AWS Service Quotas**:
| Service | Quota | Impact |
|---------|-------|--------|
| Bedrock KB Retrieve | 10 TPS | Bottleneck for >10 concurrent users |
| Bedrock InvokeModel | 20 TPS | Sufficient for demo |
| Lambda Concurrent Executions | 1000 | More than enough |
| DynamoDB Read/Write | 25 RCU/WCU | Sufficient for L4 |

**Mitigation**:
- Request quota increase for Bedrock KB if needed
- Implement request queuing for >10 concurrent users
- Use exponential backoff for throttling errors



## Deployment Strategy

### Local Development Setup

**Prerequisites**:
```bash
# Python 3.11+
python --version

# AWS CLI configured
aws configure
aws sts get-caller-identity

# UV for dependency management
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Step 1: Clone and Setup**:
```bash
git clone <repo-url>
cd geekbrain-ai-system

# Create virtual environment
uv venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install dependencies
uv pip install -r requirements.txt
```

**Step 2: Setup Data Layer**:
```bash
# Seed database
cd data_package/scripts
uv sync
uv run python seed_data.py --db-type sqlite --db-path ../../geekbrain.db

# Start monitoring API
uv run uvicorn monitoring_api:app --host 0.0.0.0 --port 8000 --reload
```

**Step 3: Setup AWS Resources**:
```bash
# Create S3 bucket
aws s3 mb s3://geekbrain-kb-dev-$(whoami)

# Upload knowledge base
aws s3 sync ../knowledge_base/ s3://geekbrain-kb-dev-$(whoami)/

# Create Bedrock KB (via console or Terraform)
# Note: KB ID will be needed for .env
```

**Step 4: Configure Environment**:
```bash
# .env file
cat > .env << EOF
AWS_REGION=us-east-1
BEDROCK_KB_ID=<your-kb-id>
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
DATABASE_PATH=./geekbrain.db
MONITORING_API_URL=http://localhost:8000
LOG_LEVEL=INFO
EOF
```

**Step 5: Run System**:
```bash
# Start main API
python -m src.main

# Or with hot reload
uvicorn src.main:app --reload --port 8080
```

**Step 6: Test**:
```bash
# Test L1
curl -X POST http://localhost:8080/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Who is the Team Platform lead?"}'

# Test L3
curl -X POST http://localhost:8080/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What was PaymentGW total cost in Q1 2026?"}'
```



### Cloud Deployment Options

#### Option 1: Lambda + API Gateway (Serverless)

**Architecture**:
```
API Gateway → Lambda (Orchestrator) → Bedrock KB + Bedrock + DynamoDB
                ↓
            Lambda (Tools) → RDS/Monitoring API
```

**Pros**:
- No server management
- Auto-scaling
- Pay per request

**Cons**:
- Cold start latency (2-5s)
- 15min timeout limit
- Complex for L4 with long conversations

**Terraform**:
```hcl
# terraform/lambda.tf
resource "aws_lambda_function" "orchestrator" {
  filename         = "orchestrator.zip"
  function_name    = "geekbrain-orchestrator"
  role            = aws_iam_role.lambda_exec.arn
  handler         = "main.handler"
  runtime         = "python3.11"
  timeout         = 60
  memory_size     = 1024
  
  environment {
    variables = {
      BEDROCK_KB_ID = aws_bedrockagent_knowledge_base.main.id
      BEDROCK_MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"
      DYNAMODB_TABLE = aws_dynamodb_table.conversations.name
    }
  }
}

resource "aws_apigatewayv2_api" "main" {
  name          = "geekbrain-api"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_integration" "lambda" {
  api_id           = aws_apigatewayv2_api.main.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.orchestrator.invoke_arn
}
```

#### Option 2: ECS Fargate (Containerized)

**Architecture**:
```
ALB → ECS Fargate (FastAPI) → Bedrock KB + Bedrock + DynamoDB
                ↓
            RDS/Monitoring API
```

**Pros**:
- No cold starts
- Long-running connections
- Better for L4 conversations
- Full control over runtime

**Cons**:
- More expensive (always running)
- Need to manage container images

**Dockerfile**:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY .env .

EXPOSE 8080

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

**Terraform**:
```hcl
# terraform/ecs.tf
resource "aws_ecs_cluster" "main" {
  name = "geekbrain-cluster"
}

resource "aws_ecs_task_definition" "app" {
  family                   = "geekbrain-app"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "512"
  memory                   = "1024"
  
  container_definitions = jsonencode([{
    name  = "geekbrain"
    image = "${aws_ecr_repository.app.repository_url}:latest"
    portMappings = [{
      containerPort = 8080
      protocol      = "tcp"
    }]
    environment = [
      {name = "BEDROCK_KB_ID", value = aws_bedrockagent_knowledge_base.main.id},
      {name = "BEDROCK_MODEL_ID", value = "anthropic.claude-3-sonnet-20240229-v1:0"}
    ]
  }])
}

resource "aws_ecs_service" "app" {
  name            = "geekbrain-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.app.arn
  desired_count   = 2
  launch_type     = "FARGATE"
  
  load_balancer {
    target_group_arn = aws_lb_target_group.app.arn
    container_name   = "geekbrain"
    container_port   = 8080
  }
}
```



#### Option 3: EC2 (Simple, Recommended for Demo)

**Architecture**:
```
EC2 (FastAPI + SQLite) → Bedrock KB + Bedrock
```

**Pros**:
- Simplest deployment
- Full control
- Can run monitoring API on same instance
- Good for demo/prototype

**Cons**:
- Manual scaling
- Need to manage instance

**Setup Script**:
```bash
#!/bin/bash
# deploy.sh

# Launch EC2 instance
aws ec2 run-instances \
  --image-id ami-0c55b159cbfafe1f0 \
  --instance-type t3.medium \
  --key-name my-key \
  --security-group-ids sg-xxx \
  --iam-instance-profile Name=GeekBrainEC2Role \
  --user-data file://user-data.sh

# user-data.sh
#!/bin/bash
yum update -y
yum install -y python3.11 git

# Clone repo
cd /home/ec2-user
git clone <repo-url>
cd geekbrain-ai-system

# Setup
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Seed database
cd data_package/scripts
python seed_data.py --db-type sqlite --db-path ../../geekbrain.db

# Start monitoring API in background
nohup uvicorn monitoring_api:app --host 0.0.0.0 --port 8000 &

# Start main API
cd ../..
nohup uvicorn src.main:app --host 0.0.0.0 --port 8080 &
```

### Infrastructure as Code (Terraform)

**Complete Terraform Setup**:
```hcl
# terraform/main.tf
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# S3 Bucket for Knowledge Base
resource "aws_s3_bucket" "knowledge_base" {
  bucket = "geekbrain-kb-${var.environment}"
  
  tags = {
    Name        = "GeekBrain Knowledge Base"
    Environment = var.environment
  }
}

resource "aws_s3_bucket_versioning" "knowledge_base" {
  bucket = aws_s3_bucket.knowledge_base.id
  
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "knowledge_base" {
  bucket = aws_s3_bucket.knowledge_base.id
  
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# OpenSearch Serverless Collection for Vector Store
resource "aws_opensearchserverless_collection" "vectors" {
  name = "geekbrain-vectors"
  type = "VECTORSEARCH"
  
  tags = {
    Name = "GeekBrain Vector Store"
  }
}

# Bedrock Knowledge Base
resource "aws_bedrockagent_knowledge_base" "main" {
  name     = "geekbrain-kb"
  role_arn = aws_iam_role.bedrock_kb.arn
  
  knowledge_base_configuration {
    type = "VECTOR"
    vector_knowledge_base_configuration {
      embedding_model_arn = "arn:aws:bedrock:${var.aws_region}::foundation-model/amazon.titan-embed-text-v2:0"
    }
  }
  
  storage_configuration {
    type = "OPENSEARCH_SERVERLESS"
    opensearch_serverless_configuration {
      collection_arn    = aws_opensearchserverless_collection.vectors.arn
      vector_index_name = "geekbrain-index"
      field_mapping {
        vector_field   = "embedding"
        text_field     = "text"
        metadata_field = "metadata"
      }
    }
  }
}

# Bedrock KB Data Source
resource "aws_bedrockagent_data_source" "s3" {
  knowledge_base_id = aws_bedrockagent_knowledge_base.main.id
  name              = "s3-documents"
  
  data_source_configuration {
    type = "S3"
    s3_configuration {
      bucket_arn = aws_s3_bucket.knowledge_base.arn
    }
  }
}

# DynamoDB Table for Conversation State
resource "aws_dynamodb_table" "conversations" {
  name           = "geekbrain-conversations"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "session_id"
  range_key      = "turn_id"
  
  attribute {
    name = "session_id"
    type = "S"
  }
  
  attribute {
    name = "turn_id"
    type = "N"
  }
  
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }
  
  tags = {
    Name = "GeekBrain Conversations"
  }
}

# RDS PostgreSQL (Optional, for production)
resource "aws_db_instance" "main" {
  identifier        = "geekbrain-db"
  engine            = "postgres"
  engine_version    = "15.4"
  instance_class    = "db.t3.micro"
  allocated_storage = 20
  
  db_name  = "geekbrain"
  username = var.db_username
  password = var.db_password
  
  skip_final_snapshot = true
  
  tags = {
    Name = "GeekBrain Database"
  }
}

# IAM Roles
resource "aws_iam_role" "bedrock_kb" {
  name = "GeekBrainBedrockKBRole"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "bedrock.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy" "bedrock_kb_s3" {
  role = aws_iam_role.bedrock_kb.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.knowledge_base.arn,
          "${aws_s3_bucket.knowledge_base.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "aoss:APIAccessAll"
        ]
        Resource = aws_opensearchserverless_collection.vectors.arn
      },
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel"
        ]
        Resource = "arn:aws:bedrock:${var.aws_region}::foundation-model/amazon.titan-embed-text-v2:0"
      }
    ]
  })
}

# Outputs
output "knowledge_base_id" {
  value = aws_bedrockagent_knowledge_base.main.id
}

output "s3_bucket_name" {
  value = aws_s3_bucket.knowledge_base.bucket
}

output "dynamodb_table_name" {
  value = aws_dynamodb_table.conversations.name
}
```

**Variables**:
```hcl
# terraform/variables.tf
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}

variable "db_username" {
  description = "Database username"
  type        = string
  sensitive   = true
}

variable "db_password" {
  description = "Database password"
  type        = string
  sensitive   = true
}
```

**Deploy**:
```bash
cd terraform
terraform init
terraform plan
terraform apply
```



### Environment Configuration

**Development (.env.dev)**:
```bash
AWS_REGION=us-east-1
BEDROCK_KB_ID=<dev-kb-id>
BEDROCK_MODEL_ID=anthropic.claude-3-haiku-20240307-v1:0  # Faster/cheaper for dev
DATABASE_PATH=./geekbrain.db
DATABASE_TYPE=sqlite
MONITORING_API_URL=http://localhost:8000
LOG_LEVEL=DEBUG
CACHE_ENABLED=false
OBSERVABILITY_ENABLED=true
```

**Production (.env.prod)**:
```bash
AWS_REGION=us-east-1
BEDROCK_KB_ID=<prod-kb-id>
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
DATABASE_URL=postgresql://user:pass@geekbrain-db.xxx.rds.amazonaws.com:5432/geekbrain
DATABASE_TYPE=postgresql
MONITORING_API_URL=https://monitoring.geekbrain.internal
LOG_LEVEL=INFO
CACHE_ENABLED=true
CACHE_TTL=300
OBSERVABILITY_ENABLED=false
DYNAMODB_TABLE=geekbrain-conversations-prod
```

**Configuration Loader**:
```python
# src/config.py
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    aws_region: str = "us-east-1"
    bedrock_kb_id: str
    bedrock_model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0"
    
    database_type: str = "sqlite"
    database_path: Optional[str] = None
    database_url: Optional[str] = None
    
    monitoring_api_url: str = "http://localhost:8000"
    
    log_level: str = "INFO"
    cache_enabled: bool = False
    cache_ttl: int = 300
    
    observability_enabled: bool = False
    
    dynamodb_table: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
```



## Implementation Roadmap

### Day 1 (Tuesday): Data Exploration & Architecture

**Morning (2 hours)**:
- [ ] Read all 36 knowledge base documents
- [ ] Identify conflicting documents (API reference v1 vs v2)
- [ ] Map which information is in docs vs database vs API

**Afternoon (3 hours)**:
- [ ] Run monitoring API locally, test all endpoints
- [ ] Seed database with CSV files
- [ ] Run test SQL queries to verify data
- [ ] Sketch system architecture diagram
- [ ] Team alignment on approach (Bedrock Agents vs custom orchestration)

**Deliverable**: Architecture diagram + data mapping document

### Day 2 (Thursday): Build L1 → L2 → L3

**Morning Session (08:30-10:00): GenAI in Practice Lecture**

**Afternoon Session 1 (13:00-14:30): L1 Implementation**
- [ ] Create S3 bucket, upload documents
- [ ] Create Bedrock Knowledge Base
- [ ] Configure embedding model (Titan v2)
- [ ] Trigger sync, wait for completion
- [ ] Test retrieval with sample queries
- [ ] Implement basic orchestrator with LLM call
- [ ] Test: "Who is Team Platform lead?" → "Alex Chen"
- [ ] **Checkpoint: L1 working**

**Afternoon Session 2 (14:30-16:00): L2 Implementation**
- [ ] Increase retrieval top-K to 10
- [ ] Enhance system prompt with conflict resolution rules
- [ ] Test: "What is API rate limit?" → Should resolve v1 vs v2
- [ ] Test multi-document synthesis query
- [ ] **Checkpoint: L2 working**

**Afternoon Session 3 (16:00-17:00): L3 Start**
- [ ] Implement Database Query Tool
- [ ] Implement Service Metrics Tool
- [ ] Register tools with LLM
- [ ] Test first tool call: "PaymentGW Q1 cost?"
- [ ] **Checkpoint: First tool call successful**

### Day 3 (Friday): Polish L3, Add L4, Evidence Pack

**Morning (08:00-10:00): Complete L3**
- [ ] Implement remaining 5 tools
- [ ] Test all L3 queries with numerical validation
- [ ] Verify exact values: $16,500, $7,500, 2000ms
- [ ] Test error handling (API down, DB unavailable)
- [ ] **Checkpoint: L3 stable with 100% numerical accuracy**

**Mid-Morning (10:00-12:00): L4 + Evidence Pack**
- [ ] Choose memory strategy (Window recommended)
- [ ] Implement conversation state storage
- [ ] Test 4-turn conversation with pronoun resolution
- [ ] Write Evidence Pack markdown
- [ ] Take screenshots for each level
- [ ] Capture tool call logs for L3 evidence
- [ ] **Checkpoint: Evidence Pack committed**

**Afternoon (14:00-18:00): Presentations**

### Bonus Work (If Time Permits)

**Bonus A: Observability Dashboard** (2-3 hours)
- Implement event logger
- Create FastAPI dashboard with WebSocket
- Build HTML/JS frontend
- Test real-time event streaming

**Bonus B: Agent Reasoning** (3-4 hours)
- Implement investigation query handler
- Create structured report format
- Test with "Is NotificationSvc healthy?" query

**Bonus C: KB Sync** (1-2 hours)
- Create Lambda function for S3 event trigger
- Implement StartIngestionJob call
- Test by updating a document



## Risk Mitigation

### Technical Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Bedrock KB sync fails | High - L1/L2 broken | Medium | Test sync early Tuesday, have retry logic |
| Tool calls return wrong data | High - L3 fails | Medium | Validate with test queries, check exact numbers |
| Context window overflow | Medium - L4 degraded | High | Implement truncation, use Window memory |
| Monitoring API not running during demo | High - L3 fails | Low | Start API in background, add health check |
| Database not seeded | High - L3 fails | Low | Seed on Tuesday, verify with queries |
| Cold start latency | Medium - Demo slow | Medium | Warm up system before demo slot |
| Bedrock throttling | Medium - Demo fails | Low | Request quota increase, implement retry |

### Mitigation Strategies

**1. Early Validation**:
```python
# validation/check_setup.py
def validate_setup():
    """Run before demo to ensure everything is ready."""
    
    checks = []
    
    # Check 1: Bedrock KB accessible
    try:
        response = bedrock_agent.retrieve(
            knowledgeBaseId=settings.bedrock_kb_id,
            retrievalQuery={'text': 'test'}
        )
        checks.append(("Bedrock KB", "✓ OK"))
    except Exception as e:
        checks.append(("Bedrock KB", f"✗ FAIL: {e}"))
    
    # Check 2: Database accessible
    try:
        result = db_tool.execute_query("SELECT COUNT(*) FROM monthly_costs")
        if result.data[0]['count'] == 36:
            checks.append(("Database", "✓ OK (36 rows)"))
        else:
            checks.append(("Database", f"✗ FAIL: Expected 36 rows, got {result.data[0]['count']}"))
    except Exception as e:
        checks.append(("Database", f"✗ FAIL: {e}"))
    
    # Check 3: Monitoring API accessible
    try:
        response = requests.get(f"{settings.monitoring_api_url}/services", timeout=3)
        if response.status_code == 200:
            checks.append(("Monitoring API", "✓ OK"))
        else:
            checks.append(("Monitoring API", f"✗ FAIL: Status {response.status_code}"))
    except Exception as e:
        checks.append(("Monitoring API", f"✗ FAIL: {e}"))
    
    # Check 4: Test L1 query
    try:
        response = system.query("Who is Team Platform lead?")
        if "Alex Chen" in response.answer:
            checks.append(("L1 Query", "✓ OK"))
        else:
            checks.append(("L1 Query", f"✗ FAIL: Wrong answer"))
    except Exception as e:
        checks.append(("L1 Query", f"✗ FAIL: {e}"))
    
    # Check 5: Test L3 query
    try:
        response = system.query("What was PaymentGW total cost in Q1 2026?")
        if "16500" in response.answer or "16,500" in response.answer:
            checks.append(("L3 Query", "✓ OK"))
        else:
            checks.append(("L3 Query", f"✗ FAIL: Wrong number"))
    except Exception as e:
        checks.append(("L3 Query", f"✗ FAIL: {e}"))
    
    # Print results
    print("\n=== System Validation ===\n")
    for check, result in checks:
        print(f"{check:20s} {result}")
    
    # Overall status
    failures = [c for c in checks if "✗" in c[1]]
    if failures:
        print(f"\n⚠️  {len(failures)} checks failed. Fix before demo.")
        return False
    else:
        print("\n✅ All checks passed. System ready for demo.")
        return True

if __name__ == "__main__":
    validate_setup()
```

**2. Backup Plan**:
- If live demo fails, use screenshots from Evidence Pack
- If Monitoring API down, use database historical data only
- If Bedrock KB unavailable, explain architecture with diagrams

**3. Pre-Demo Checklist**:
```markdown
## 30 Minutes Before Demo

- [ ] Run validation script: `python validation/check_setup.py`
- [ ] Start monitoring API: `uvicorn monitoring_api:app --port 8000`
- [ ] Start main system: `uvicorn src.main:app --port 8080`
- [ ] Test one query per level (L1, L2, L3, L4)
- [ ] Open Evidence Pack in browser
- [ ] Open dashboard (if Bonus A implemented)
- [ ] Charge laptop, connect to power
- [ ] Test screen sharing
- [ ] Have backup screenshots ready
```



## Appendix

### A. Example Queries by Level

**L1 Queries** (Simple fact retrieval):
```
1. "Who is the Team Platform lead?"
   Expected: "Alex Chen" [Source: team_platform.md]

2. "What is the deployment freeze window?"
   Expected: "Friday 18:00 to Monday 08:00" [Source: deployment_policy.md]

3. "What authentication method does PaymentGW use?"
   Expected: "API key + HMAC-SHA256" [Source: service_paymentgw.md]
```

**L2 Queries** (Multi-source + conflict resolution):
```
1. "What is PaymentGW's API rate limit?"
   Expected: "1000 req/min (v2, current). Previous version (v1) was 500 req/min."
   Sources: api_reference_v1.md, api_reference_v2.md

2. "Can Team Commerce deploy on Friday night? What approvals do they need?"
   Expected: Synthesis from deployment_policy.md + team_commerce.md
   Should mention: freeze window, emergency approval process

3. "What were the main causes of incidents in Q1 2026?"
   Expected: Synthesis from multiple postmortem documents
   Sources: postmortem_2026_01_paymentgw.md, postmortem_2026_02_notificationsvc.md
```

**L3 Queries** (Tool-augmented):
```
1. "What was PaymentGW's total infrastructure cost in Q1 2026?"
   Expected: "$16,500"
   Tool: query_database
   SQL: SELECT SUM(total_cost) FROM monthly_costs WHERE service='PaymentGW' AND month IN ('2026-01','2026-02','2026-03')

2. "Which service had the highest cost in March 2026?"
   Expected: "PaymentGW at $7,500"
   Tool: query_database

3. "What is PaymentGW's current p99 latency?"
   Expected: "~185ms" (from live API)
   Tool: get_service_metrics

4. "Is NotificationSvc meeting its SLA targets?"
   Expected: "No, current p99 latency is 3200ms, exceeding target of 2000ms"
   Tools: query_database (for target) + get_service_metrics (for current)

5. "Compare the error rates of PaymentGW and NotificationSvc"
   Expected: "PaymentGW: 0.02%, NotificationSvc: 0.15%"
   Tool: compare_services or multiple get_service_metrics calls
```

**L4 Queries** (Multi-turn conversation):
```
Turn 1: "Which service had the highest cost in March 2026?"
Expected: "PaymentGW at $7,500"

Turn 2: "Why did its costs spike?"
Expected: Should resolve "its" → PaymentGW, retrieve postmortem
Answer: "Database connection pool exhaustion led to increased compute costs..."

Turn 3: "Which team is responsible?"
Expected: Should maintain context about PaymentGW
Answer: "Team Platform, led by Alex Chen"

Turn 4: "Is the postmortem review deadline overdue?"
Expected: Should know we're talking about PaymentGW postmortem
Answer: Check deadline from postmortem document
```

### B. Database Schema Reference

**Quick Reference Queries**:
```sql
-- Total cost for a service in a period
SELECT SUM(total_cost) 
FROM monthly_costs 
WHERE service = ? AND month BETWEEN ? AND ?;

-- Service with highest cost in a month
SELECT service, total_cost 
FROM monthly_costs 
WHERE month = ? 
ORDER BY total_cost DESC 
LIMIT 1;

-- SLA target for a service
SELECT * 
FROM sla_targets 
WHERE service = ?;

-- Incidents for a service
SELECT * 
FROM incidents 
WHERE service = ? 
ORDER BY occurred_at DESC;

-- Average daily metrics for a service in a period
SELECT AVG(avg_latency_ms), AVG(error_rate) 
FROM daily_metrics 
WHERE service = ? AND date BETWEEN ? AND ?;
```

### C. Monitoring API Endpoints Reference

```
GET /services
→ List all services

GET /status/{service_name}
→ Current status (healthy/degraded/down)

GET /metrics/{service_name}
→ Current performance metrics

GET /incidents
→ Active incidents across all services

GET /incidents/{service_name}
→ Incidents for specific service
```

### D. Bedrock Model Comparison

| Model | Speed | Cost/1K tokens | Context Window | Best For |
|-------|-------|----------------|----------------|----------|
| Claude 3 Haiku | Fast (1-2s) | $0.00025 / $0.00125 | 200K | L1-L2 dev/testing |
| Claude 3 Sonnet | Medium (3-5s) | $0.003 / $0.015 | 200K | L1-L4 production |
| Claude 3 Opus | Slow (8-12s) | $0.015 / $0.075 | 200K | Bonus B investigation |

*Prices: Input / Output per 1K tokens*

### E. Useful AWS CLI Commands

```bash
# List Bedrock models
aws bedrock list-foundation-models --region us-east-1

# Test Bedrock KB retrieval
aws bedrock-agent-runtime retrieve \
  --knowledge-base-id <kb-id> \
  --retrieval-query text="test query" \
  --region us-east-1

# Check KB sync status
aws bedrock-agent get-knowledge-base \
  --knowledge-base-id <kb-id> \
  --region us-east-1

# Start KB ingestion
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id <kb-id> \
  --data-source-id <ds-id> \
  --region us-east-1

# Query DynamoDB
aws dynamodb query \
  --table-name geekbrain-conversations \
  --key-condition-expression "session_id = :sid" \
  --expression-attribute-values '{":sid":{"S":"session123"}}'
```

### F. Troubleshooting Guide

**Problem: Bedrock KB returns no results**
- Check sync status: `aws bedrock-agent get-knowledge-base --knowledge-base-id <id>`
- Verify documents uploaded to S3: `aws s3 ls s3://bucket-name/`
- Test with simple query: "test"
- Check embedding model is correct

**Problem: Tool calls fail**
- Verify database seeded: `sqlite3 geekbrain.db "SELECT COUNT(*) FROM monthly_costs;"`
- Check monitoring API running: `curl http://localhost:8000/services`
- Review tool definitions sent to LLM
- Check LLM response for tool_use format

**Problem: Wrong numerical values in L3**
- Verify database data: Run SQL queries manually
- Check tool result parsing
- Ensure LLM preserves exact numbers (temperature=0)
- Review system prompt instructions

**Problem: L4 loses context**
- Check conversation history is being saved
- Verify history is included in LLM prompt
- Review pronoun resolution logic
- Check context window not exceeded

**Problem: Slow response times**
- Enable caching for retrieval and DB queries
- Use Claude Haiku for faster responses
- Implement parallel execution
- Check network latency to AWS services

