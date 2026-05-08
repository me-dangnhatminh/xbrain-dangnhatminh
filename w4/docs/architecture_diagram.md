# W4 GeekBrain AI System - Architecture Diagram

## High-Level System Architecture

```mermaid
graph TB
    User[👤 User] -->|Query| API[🌐 API Layer<br/>FastAPI]
    API -->|Route Request| Orchestrator[🎯 Orchestrator<br/>Query Router & LLM Loop]
    
    Orchestrator -->|Retrieve Context| RAG[📚 RAG Pipeline<br/>Retrieve & Rank]
    Orchestrator -->|Execute Functions| Tools[🔧 Tool Layer<br/>7 Tools]
    Orchestrator -->|Load/Save State| Memory[💾 Memory Manager<br/>Conversation State]
    
    RAG -->|Read Documents| S3[☁️ AWS S3<br/>36 Markdown Files]
    RAG -->|Query Embeddings| BedrockKB[🤖 AWS Bedrock KB<br/>Knowledge Base Service]
    BedrockKB -->|Vector Search| OpenSearch[🔍 OpenSearch Serverless<br/>Vector Store]
    
    Tools -->|SQL Queries| DB[(🗄️ Database<br/>SQLite/PostgreSQL<br/>4 CSV Tables)]
    Tools -->|HTTP GET| MonAPI[📊 Monitoring API<br/>FastAPI Local Service]
    
    Memory -->|Read/Write| StateStore[(💿 Conversation State<br/>DynamoDB or Local)]
    
    Orchestrator -->|Generate Response| LLM[🧠 AWS Bedrock<br/>Claude Sonnet]
    LLM -->|Tool Calls| Orchestrator
    LLM -->|Final Answer| API
    API -->|Response| User
    
    style User fill:#e1f5ff,stroke:#0288d1,stroke-width:2px
    style LLM fill:#fff4e1,stroke:#f57c00,stroke-width:3px
    style BedrockKB fill:#e8f5e9,stroke:#388e3c,stroke-width:2px
    style OpenSearch fill:#e8f5e9,stroke:#388e3c,stroke-width:2px
    style S3 fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    style DB fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    style MonAPI fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    style StateStore fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    style Orchestrator fill:#e3f2fd,stroke:#1976d2,stroke-width:3px
```

## Component Descriptions

### Core Components

| Component | Technology | Responsibility |
|-----------|-----------|----------------|
| **User** | Web/CLI Interface | Submits queries and receives responses |
| **API Layer** | FastAPI | HTTP endpoint, request validation, error handling |
| **Orchestrator** | Python | Routes queries, manages LLM interaction loop, coordinates RAG/Tools/Memory |
| **RAG Pipeline** | Bedrock KB Retrieve API | Retrieves relevant document chunks from knowledge base |
| **Tool Layer** | Python Functions | Executes 7 tools: DB queries, metrics API, status checks, etc. |
| **Memory Manager** | Python + DynamoDB | Stores/retrieves conversation history for multi-turn context |
| **LLM** | AWS Bedrock (Claude Sonnet) | Generates responses, decides tool calls, resolves pronouns |

### Data Sources

| Data Source | Technology | Content |
|-------------|-----------|---------|
| **S3 Bucket** | AWS S3 | 36 markdown documents (company info, policies, postmortems) |
| **Bedrock Knowledge Base** | AWS Bedrock KB | RAG service with embedding generation and retrieval |
| **OpenSearch Serverless** | AWS OpenSearch | Vector store for document embeddings |
| **Database** | SQLite/PostgreSQL | 4 CSV tables: monthly_costs, incidents, sla_targets, daily_metrics |
| **Monitoring API** | FastAPI (Local) | Live system metrics: latency, error rate, request volume |
| **Conversation State** | DynamoDB or Local | Session history for multi-turn conversations |

## Data Flow by Level

### L1: Simple RAG
```mermaid
sequenceDiagram
    participant User
    participant API
    participant Orchestrator
    participant RAG
    participant BedrockKB
    participant LLM
    
    User->>API: Query
    API->>Orchestrator: Route query
    Orchestrator->>RAG: Retrieve context
    RAG->>BedrockKB: Search (top_k=5)
    BedrockKB-->>RAG: 5 chunks
    RAG-->>Orchestrator: Chunks + sources
    Orchestrator->>LLM: System prompt + chunks + query
    LLM-->>Orchestrator: Response with citations
    Orchestrator-->>API: Response
    API-->>User: Answer with sources
```

### L2: Multi-Source RAG
```mermaid
sequenceDiagram
    participant User
    participant API
    participant Orchestrator
    participant RAG
    participant BedrockKB
    participant LLM
    
    User->>API: Complex query
    API->>Orchestrator: Route query
    Orchestrator->>RAG: Retrieve context (top_k=10)
    RAG->>BedrockKB: Search multiple docs
    BedrockKB-->>RAG: 10 chunks (multiple sources)
    RAG-->>Orchestrator: Chunks with metadata
    Orchestrator->>LLM: Enhanced prompt + conflict rules + chunks
    LLM-->>Orchestrator: Synthesized response + conflict explanation
    Orchestrator-->>API: Response
    API-->>User: Answer with source synthesis
```

### L3: Tool-Augmented RAG
```mermaid
sequenceDiagram
    participant User
    participant Orchestrator
    participant RAG
    participant Tools
    participant DB
    participant MonAPI
    participant LLM
    
    User->>Orchestrator: Query requiring data
    Orchestrator->>RAG: Retrieve context
    RAG-->>Orchestrator: Chunks
    Orchestrator->>LLM: Chunks + tool definitions + query
    LLM-->>Orchestrator: tool_use request
    Orchestrator->>Tools: Execute tool
    alt Database Query
        Tools->>DB: SQL query
        DB-->>Tools: Results
    else Metrics Query
        Tools->>MonAPI: HTTP GET
        MonAPI-->>Tools: Live metrics
    end
    Tools-->>Orchestrator: Tool results
    Orchestrator->>LLM: Tool results
    LLM-->>Orchestrator: Final response with data
    Orchestrator-->>User: Answer with exact numbers
```

### L4: Memory-Enabled RAG
```mermaid
sequenceDiagram
    participant User
    participant Orchestrator
    participant Memory
    participant RAG
    participant Tools
    participant LLM
    
    User->>Orchestrator: Follow-up query (with pronouns)
    Orchestrator->>Memory: Load conversation history
    Memory-->>Orchestrator: Last N turns
    Orchestrator->>RAG: Retrieve context
    RAG-->>Orchestrator: Chunks
    Orchestrator->>Tools: Execute tools (if needed)
    Tools-->>Orchestrator: Results
    Orchestrator->>LLM: History + chunks + tools + query
    LLM-->>Orchestrator: Response (pronouns resolved)
    Orchestrator->>Memory: Save turn
    Memory-->>Orchestrator: Saved
    Orchestrator-->>User: Contextual answer
```

## AWS Service Integration

```mermaid
graph LR
    subgraph "Data Layer"
        S3[AWS S3<br/>Knowledge Base Docs]
        DB[(Database<br/>Structured Data)]
    end
    
    subgraph "AI/ML Services"
        BedrockKB[AWS Bedrock<br/>Knowledge Base]
        OpenSearch[OpenSearch<br/>Serverless]
        Bedrock[AWS Bedrock<br/>Claude Sonnet]
        Embeddings[Titan Embeddings<br/>v2]
    end
    
    subgraph "Compute"
        Lambda1[Lambda<br/>DB Query Tool]
        Lambda2[Lambda<br/>Metrics Tool]
        Lambda3[Lambda<br/>Other Tools]
    end
    
    subgraph "State Management"
        DynamoDB[(DynamoDB<br/>Conversations)]
    end
    
    subgraph "Orchestration"
        Agent[Bedrock Agent<br/>or Custom Code]
    end
    
    S3 -->|Data Source| BedrockKB
    BedrockKB -->|Generate| Embeddings
    BedrockKB -->|Store Vectors| OpenSearch
    BedrockKB -->|Retrieve| Agent
    
    Agent -->|Invoke Model| Bedrock
    Agent -->|Call| Lambda1
    Agent -->|Call| Lambda2
    Agent -->|Call| Lambda3
    
    Lambda1 -->|Query| DB
    Lambda2 -->|HTTP| MonAPI[Monitoring API]
    
    Agent -->|Read/Write| DynamoDB
    
    style S3 fill:#ff9800,stroke:#e65100,stroke-width:2px
    style BedrockKB fill:#4caf50,stroke:#2e7d32,stroke-width:2px
    style Bedrock fill:#2196f3,stroke:#1565c0,stroke-width:3px
    style DynamoDB fill:#9c27b0,stroke:#6a1b9a,stroke-width:2px
    style Agent fill:#00bcd4,stroke:#0097a7,stroke-width:3px
```

## Tool Architecture

```mermaid
graph TB
    Orchestrator[Orchestrator] -->|Registers| ToolRegistry[Tool Registry]
    
    ToolRegistry --> Tool1[Database Query Tool]
    ToolRegistry --> Tool2[Service Metrics Tool]
    ToolRegistry --> Tool3[Service Status Tool]
    ToolRegistry --> Tool4[List Services Tool]
    ToolRegistry --> Tool5[Incident History Tool]
    ToolRegistry --> Tool6[Team Info Tool]
    ToolRegistry --> Tool7[Compare Services Tool]
    
    Tool1 -->|SQL| DB[(Database)]
    Tool2 -->|HTTP GET| MonAPI[Monitoring API]
    Tool3 -->|HTTP GET| MonAPI
    Tool4 -->|HTTP GET| MonAPI
    Tool5 -->|SQL| DB
    Tool6 -->|RAG Query| BedrockKB[Bedrock KB]
    Tool7 -->|HTTP GET| MonAPI
    
    style ToolRegistry fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    style Tool1 fill:#fff3e0,stroke:#f57c00
    style Tool2 fill:#fff3e0,stroke:#f57c00
    style Tool3 fill:#fff3e0,stroke:#f57c00
    style Tool4 fill:#fff3e0,stroke:#f57c00
    style Tool5 fill:#fff3e0,stroke:#f57c00
    style Tool6 fill:#fff3e0,stroke:#f57c00
    style Tool7 fill:#fff3e0,stroke:#f57c00
```

## Memory Strategy Options

```mermaid
graph LR
    subgraph "Strategy 1: Buffer Memory"
        B1[Store All Turns] --> B2[Send All to LLM]
        B2 --> B3[Simple but Unbounded]
    end
    
    subgraph "Strategy 2: Window Memory"
        W1[Store All Turns] --> W2[Send Last N to LLM]
        W2 --> W3[Bounded Context]
    end
    
    subgraph "Strategy 3: Query Rewriting"
        Q1[Store All Turns] --> Q2[Rewrite Query]
        Q2 --> Q3[Self-Contained Query]
        Q3 --> Q4[Process Normally]
    end
    
    style W2 fill:#4caf50,stroke:#2e7d32,stroke-width:3px
```

## Deployment Architecture

```mermaid
graph TB
    subgraph "Client Layer"
        WebUI[Web Interface]
        CLI[CLI Tool]
    end
    
    subgraph "API Gateway"
        APIGW[AWS API Gateway<br/>or ALB]
    end
    
    subgraph "Application Layer"
        Lambda[AWS Lambda<br/>or ECS Container]
    end
    
    subgraph "AWS Managed Services"
        Bedrock[Bedrock]
        BedrockKB[Bedrock KB]
        OpenSearch[OpenSearch]
        S3[S3]
        DynamoDB[DynamoDB]
        RDS[RDS PostgreSQL]
    end
    
    subgraph "Monitoring"
        CloudWatch[CloudWatch Logs]
        XRay[X-Ray Tracing]
    end
    
    WebUI --> APIGW
    CLI --> APIGW
    APIGW --> Lambda
    
    Lambda --> Bedrock
    Lambda --> BedrockKB
    Lambda --> DynamoDB
    Lambda --> RDS
    
    BedrockKB --> OpenSearch
    BedrockKB --> S3
    
    Lambda --> CloudWatch
    Lambda --> XRay
    
    style Lambda fill:#ff9800,stroke:#e65100,stroke-width:2px
    style Bedrock fill:#2196f3,stroke:#1565c0,stroke-width:2px
    style BedrockKB fill:#4caf50,stroke:#2e7d32,stroke-width:2px
```

## Key Design Decisions

### 1. Managed Services First
- **Decision**: Use AWS Bedrock KB instead of building custom RAG pipeline
- **Rationale**: Reduces complexity, faster development, production-ready infrastructure
- **Trade-off**: Less control over chunking and retrieval algorithms

### 2. Tool Orchestration Pattern
- **Decision**: Implement custom orchestration loop with tool definitions
- **Rationale**: Full control over tool execution, easier debugging, flexible error handling
- **Alternative**: Bedrock Agents (more managed but less transparent)

### 3. Window Memory Strategy
- **Decision**: Store all turns but send only last 5 to LLM
- **Rationale**: Bounded context size, predictable costs, sufficient for demo
- **Trade-off**: Loses older context beyond window

### 4. Separate Data Sources
- **Decision**: Keep Knowledge Base (S3), Database (RDS/SQLite), and Monitoring API separate
- **Rationale**: Each serves different query types, clear separation of concerns
- **Trade-off**: More components to manage

### 5. Python Implementation
- **Decision**: Use Python with boto3 for all components
- **Rationale**: Best AWS SDK support, rich ecosystem, team familiarity
- **Alternative**: TypeScript/Node.js (less mature Bedrock support)
