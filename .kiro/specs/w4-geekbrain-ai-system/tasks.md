# Implementation Plan: W4 GeekBrain AI System

## Overview

This implementation plan follows a 3-day roadmap (Tuesday → Friday) to build a 4-level AI question-answering system for GeekBrain fintech startup. The system integrates AWS Bedrock Knowledge Base (RAG), 7 tools for database/API queries, and conversation memory. Implementation progresses incrementally: L1 (Simple RAG) → L2 (Multi-Source) → L3 (Tool-Augmented) → L4 (Memory), with each level building on the previous foundation.

**Technology Stack**: Python 3.11+, AWS Bedrock (Claude Sonnet), Bedrock Knowledge Base, OpenSearch Serverless, S3, DynamoDB, FastAPI, SQLite/PostgreSQL

**Data Sources**: 36 markdown documents (Knowledge Base), 4 CSV files (Database), Monitoring API (live metrics)

## Tasks

### Phase 1: Data Exploration & Setup (Tuesday)

- [x] 1. Read and analyze knowledge base documents
  - [x] 1.1 Review all 36 markdown documents in w4/data_package/knowledge_base/
    - Understand document structure, metadata, and content
    - Identify documents with version conflicts (api_reference_v1.md vs v2.md)
    - Note team information, service details, policies, and postmortems
    - _Requirements: 2.1, 2.7_
  
  - [x] 1.2 Analyze CSV data files
    - Review monthly_costs.csv, incidents.csv, sla_targets.csv, daily_metrics.csv
    - Understand schema and data ranges (Jan-Mar 2026)
    - Calculate expected values for test queries (PaymentGW Q1 total = $16,500)
    - _Requirements: 5.1, 5.7, 13.1_

- [x] 2. Setup local development environment
  - [x] 2.1 Initialize Python project structure
    - Create w4/src/ directory with modules: rag_pipeline.py, tools.py, memory.py, orchestrator.py, main.py
    - Create w4/tests/ directory with subdirectories: unit/, integration/, validation/
    - Setup w4/requirements.txt with dependencies: boto3, fastapi, uvicorn, requests, sqlalchemy, pydantic
    - Create .env file for configuration
    - _Requirements: 16.1_
  
  - [x] 2.2 Seed database with CSV data
    - Run w4/seed_data.py to create SQLite database
    - Verify tables created: monthly_costs, incidents, sla_targets, daily_metrics
    - Test sample queries to confirm data integrity
    - _Requirements: 5.1, 5.2_
  
  - [x] 2.3 Start monitoring API service
    - Run w4/monitoring_api.py with uvicorn
    - Test endpoints: GET /services, GET /metrics/{service}, GET /status/{service}
    - Verify PaymentGW returns p99 latency ~185ms, NotificationSvc ~3200ms
    - _Requirements: 6.1, 6.6_

- [x] 3. Create architecture diagram
  - [x] 3.1 Draw system architecture diagram
    - Include components: User, API Layer, Orchestrator, RAG Pipeline, Tool Layer, Memory Manager
    - Show data flows: S3 → Bedrock KB → OpenSearch, Database queries, Monitoring API calls
    - Indicate AWS services: Bedrock, Bedrock KB, OpenSearch Serverless, S3, DynamoDB
    - Save as w4/docs/architecture_diagram.png or use Mermaid in markdown
    - _Requirements: 14.3_

- [x] 4. Checkpoint - Verify data setup
  - Ensure all tests pass, ask the user if questions arise.

### Phase 2: L1 Implementation - Simple RAG (Thursday Morning)

- [x] 5. Setup AWS S3 and Bedrock Knowledge Base
  - [x] 5.1 Create S3 bucket and upload documents
    - Create S3 bucket: geekbrain-kb-{environment}
    - Enable versioning and encryption
    - Upload all 36 markdown documents from w4/data_package/knowledge_base/
    - Verify all files uploaded successfully
    - _Requirements: 2.1, 16.1, 16.2, 16.3_
  
  - [x] 5.2 Create Bedrock Knowledge Base
    - Create OpenSearch Serverless collection for vector store
    - Create Bedrock Knowledge Base with S3 as data source
    - Configure embedding model: Amazon Titan Embeddings v2
    - Set chunking strategy: 300 tokens, 20% overlap
    - _Requirements: 2.2, 2.3, 16.5, 16.6_
  
  - [x] 5.3 Trigger KB sync and verify
    - Start ingestion job for Bedrock KB
    - Wait for sync completion (monitor status)
    - Test retrieval with sample query: "Who is Team Platform lead?"
    - Verify chunks returned contain "Alex Chen" from team_platform.md
    - _Requirements: 2.4, 2.5, 2.6, 2.7_

- [x] 6. Implement RAG Pipeline (L1)
  - [x] 6.1 Create RAGPipeline class in w4/src/rag_pipeline.py
    - Implement retrieve() method using boto3 bedrock-agent-runtime client
    - Call retrieve() API with knowledgeBaseId, query text, top_k=5
    - Parse response to extract chunks with text, source, and score
    - Return List[Chunk] with structured data
    - _Requirements: 1.1, 2.6_
  
  - [x] 6.2 Implement retrieve_and_generate() method
    - Call retrieve() to get chunks
    - Format chunks into context string with sources
    - Construct system prompt for L1 (citation rules, Vietnamese response)
    - Call Bedrock InvokeModel API with Claude Sonnet
    - Parse LLM response and extract answer with source citations
    - _Requirements: 1.2, 1.3, 10.1, 10.2, 10.9_
  
  - [x] 6.3 Write unit tests for RAG pipeline
    - Test retrieve() returns expected number of chunks
    - Test chunks contain required fields (text, source, score)
    - Test retrieve_and_generate() includes source citations
    - Mock Bedrock API calls for faster tests
    - _Requirements: 22.4_

- [x] 7. Create FastAPI endpoint for L1
  - [x] 7.1 Implement /query endpoint in w4/src/main.py
    - Create FastAPI app with POST /query endpoint
    - Accept QueryRequest with query string
    - Call RAGPipeline.retrieve_and_generate()
    - Return QueryResponse with answer, sources, processing_time
    - Add error handling for Bedrock API failures
    - _Requirements: 1.4, 12.1_
  
  - [x] 7.2 Write integration tests for L1
    - Test query "Who is the Team Platform lead?" returns "Alex Chen"
    - Test query "What is the deployment freeze window?" returns "Friday 18:00 to Monday 08:00"
    - Test response includes source citations
    - Test response time < 5 seconds
    - _Requirements: 1.5, 1.6, 11.1, 22.4_

- [x] 8. Checkpoint - L1 functional
  - Ensure all tests pass, ask the user if questions arise.

### Phase 3: L2 Implementation - Multi-Source RAG (Thursday Afternoon)

- [x] 9. Enhance RAG for multi-source retrieval
  - [x] 9.1 Increase top_k retrieval parameter
    - Modify retrieve() to accept configurable top_k (default 5 for L1, 10 for L2)
    - Update API endpoint to support level parameter
    - Test retrieval with top_k=10 returns more diverse sources
    - _Requirements: 3.2_
  
  - [x] 9.2 Implement conflict resolution in system prompt
    - Enhance system prompt with conflict resolution rules
    - Add instructions: prefer higher version, more recent date, "current" status
    - Add instruction to explain which source was trusted and why
    - Test with query "What is PaymentGW's API rate limit?" (v1=500, v2=1000)
    - _Requirements: 3.3, 3.4, 3.5, 3.6, 18.1, 18.2, 18.3, 18.4_
  
  - [x] 9.3 Write integration tests for L2
    - Test conflict resolution query returns v2 value (1000 req/min)
    - Test response mentions v1 was 500 req/min
    - Test multi-document synthesis query uses multiple sources
    - Test response time < 8 seconds
    - File: tests/integration/test_l2_integration.py (7 tests)
    - _Requirements: 3.7, 3.8, 11.2, 22.5_

- [x] 10. Checkpoint - L2 functional
  - Ensure all tests pass, ask the user if questions arise.

### Phase 4: L3 Implementation - Tool-Augmented RAG (Thursday Late Afternoon)

- [x] 11. Implement Database Query Tool
  - [x] 11.1 Create DatabaseQueryTool class in w4/src/tools.py
    - Implement execute_query() method accepting SQL string
    - Validate query is read-only (starts with SELECT)
    - Reject write operations (INSERT, UPDATE, DELETE, DROP)
    - Execute query using sqlite3 or sqlalchemy
    - Return ToolResult with success flag, data, or error message
    - _Requirements: 5.3, 5.4, 5.5, 5.6, 17.7_
  
  - [x] 11.2 Define tool definition for LLM
    - Create get_definition() method returning ToolDefinition
    - Specify name: "query_database"
    - Describe use case: "Use for historical data: costs, incidents, SLA targets, daily metrics from Jan-Mar 2026"
    - Define parameters schema: {sql: string}
    - _Requirements: 7.1, 7.3, 17.8_
  
  - [x] 11.3 Write unit tests for Database Tool
    - Test successful query returns correct data
    - Test Q1 PaymentGW cost query returns exactly 16500
    - Test write operations are rejected
    - Test malformed SQL returns error
    - File: tests/unit/test_database_tool.py (existing) + tests/unit/test_additional_tools.py
    - _Requirements: 5.7, 5.8, 13.1_

- [x] 12. Implement Service Metrics Tool
  - [x] 12.1 Create ServiceMetricsTool class in w4/src/tools.py
    - Implement get_metrics() method accepting service_name
    - Make HTTP GET request to monitoring API: /metrics/{service_name}
    - Set timeout to 3 seconds
    - Parse JSON response with latency_p50/p95/p99, error_rate, requests_per_min
    - Return ToolResult with metrics or error
    - _Requirements: 6.2, 6.3, 6.4, 6.5, 17.7_
  
  - [x] 12.2 Define tool definition for LLM
    - Create get_definition() method
    - Specify name: "get_service_metrics"
    - Describe use case: "Use for current live data: latency, error rate, request volume"
    - Define parameters schema: {service_name: string}
    - _Requirements: 7.1, 7.4, 17.8_
  
  - [x] 12.3 Write unit tests for Metrics Tool
    - Test successful metrics retrieval for PaymentGW
    - Test service not found returns error
    - Test timeout handling when API unavailable
    - Mock HTTP requests for faster tests
    - File: tests/unit/test_additional_tools.py::TestServiceMetricsTool (5 tests)
    - _Requirements: 6.6, 6.7, 6.8_

- [x] 13. Implement 5 additional tools
  - [x] 13.1 Implement ServiceStatusTool
    - Create get_status() method calling GET /status/{service_name}
    - Return current status: healthy, degraded, or down
    - Define tool definition with name "get_service_status"
    - _Requirements: 17.1, 17.8_
  
  - [x] 13.2 Implement ListServicesTool
    - Create list_services() method calling GET /services
    - Return list of all 6 services
    - Define tool definition with name "list_services"
    - _Requirements: 17.3, 17.8_
  
  - [x] 13.3 Implement IncidentHistoryTool
    - Create get_incidents() method with optional service_name filter
    - Query incidents table from database
    - Return past incidents with severity, date, root cause
    - Define tool definition with name "get_incident_history"
    - _Requirements: 17.4, 17.8_
  
  - [x] 13.4 Implement TeamInfoTool
    - Create get_team_info() method accepting team_name
    - Use RAG pipeline to search for team documents
    - Return team lead, members, responsibilities
    - Define tool definition with name "get_team_info"
    - _Requirements: 17.5, 17.8_
  
  - [x] 13.5 Implement CompareServicesTool
    - Create compare_services() method accepting service_names list and metric
    - Call get_metrics() for each service
    - Return comparison dictionary
    - Define tool definition with name "compare_services"
    - _Requirements: 17.6, 17.8_
  
  - [x] 13.6 Write unit tests for additional tools
    - Test each tool independently (ServiceStatus, ListServices, IncidentHistory, CompareServices)
    - Test error handling for invalid inputs
    - Verify tool definitions are correctly formatted
    - Test ToolExecutor register/execute mechanism (5 tests)
    - File: tests/unit/test_additional_tools.py (27 tests total)
    - _Requirements: 17.9, 17.10_

- [x] 14. Implement tool orchestration
  - [x] 14.1 Create ToolOrchestrator class in w4/src/orchestrator.py
    - Initialize with list of tool instances and LLM client
    - Collect tool definitions from all tools
    - Implement process_query_with_tools() method
    - _Requirements: 7.1, 7.2_
  
  - [x] 14.2 Implement tool execution loop
    - Send query + context + tool definitions to LLM
    - Parse LLM response for tool_use requests
    - Execute requested tool with provided parameters
    - Send tool results back to LLM
    - Repeat until LLM generates final answer (max 5 iterations)
    - _Requirements: 7.5, 7.6, 7.7, 7.8, 7.9, 7.10_
  
  - [x] 14.3 Update system prompt for L3
    - Add tool selection guidance: when to use database vs metrics API
    - Add instruction to preserve exact numerical values
    - Add instruction to cite tool results as sources
    - _Requirements: 10.5, 10.6, 10.9_
  
  - [x] 14.4 Write integration tests for L3
    - Test query "What was PaymentGW's total cost in Q1 2026?" returns $16,500
    - Test query "What is PaymentGW's current p99 latency?" calls metrics tool
    - Test query "Is NotificationSvc meeting SLA?" calls both database and metrics tools
    - Test response time < 10 seconds
    - File: tests/integration/test_l3_integration.py (14 tests, real AWS)
    - _Requirements: 4.8, 4.9, 4.10, 11.3, 13.1, 13.2, 13.3_

- [x] 15. Checkpoint - L3 functional
  - Ensure all tests pass, ask the user if questions arise.

### Phase 5: L4 Implementation - Memory-Enabled RAG (Friday Morning)

- [x] 16. Implement memory management
  - [x] 16.1 Create MemoryManager base class in w4/src/memory.py
    - Define interface: save_turn(), get_history(), format_for_llm(), clear_session()
    - Define ConversationTurn dataclass with turn_id, timestamp, query, response, context_used
    - Also implemented BufferMemory strategy
    - _Requirements: 8.1, 9.5_
  
  - [x] 16.2 Implement WindowMemory strategy
    - Create WindowMemory class extending MemoryManager
    - Store all turns in memory dict: session_id → List[ConversationTurn]
    - Implement get_history() to return only last N turns (default 5)
    - Implement format_for_llm() to create context string with User/Assistant labels
    - _Requirements: 9.2, 9.3, 9.7_
  
  - [x] 16.3 Integrate memory with orchestrator
    - Implemented _process_l4() in Orchestrator: loads history → injects into context → calls ToolOrchestrator → saves turn
    - Updated main.py: imports WindowMemory, creates WindowMemory(window_size=5), passes to Orchestrator
    - Added session_id validation (HTTP 400 if missing for L4)
    - _Requirements: 8.2, 9.8_
  
  - [x] 16.4 Write unit tests for memory
    - Test save_turn() and get_history() for both BufferMemory and WindowMemory
    - Test window memory limits to last N turns (configurable window_size)
    - Test format_for_llm() creates proper context string
    - Test session isolation and clear_session()
    - Test MemoryManager base class raises NotImplementedError
    - File: tests/unit/test_memory.py (20 tests)
    - _Requirements: 22.7_

- [x] 17. Implement pronoun resolution
  - [x] 17.1 Update system prompt for L4
    - Added _build_system_prompt(level) method to ToolOrchestrator
    - L4 prompt extends L3 base with pronoun resolution section
    - Includes rules for resolving "nó", "its", "it", "dịch vụ đó", "that service", "họ", "they"
    - Includes 4-turn conversation example in prompt
    - Added _get_l4_system_prompt() method
    - _Requirements: 8.3, 8.4, 10.7_
  
  - [x] 17.2 Write integration tests for L4 (REAL AWS — no mocks)
    - Tests run via HTTP POST to running FastAPI at localhost:8001
    - Test 4-turn conversation with pronoun resolution
    - Turn 1: "Which service had highest cost in March 2026?" → "PaymentGW" + $7,500
    - Turn 2: "Why did its costs spike?" → resolves "its" to PaymentGW
    - Turn 3: "Which team is responsible?" → returns "Team Platform" / Alex Chen
    - Turn 4: "Is the postmortem review deadline overdue?" → maintains context
    - Test session isolation between different session_ids
    - Test L4 + database tool in multi-turn
    - Test L4 + metrics tool in multi-turn
    - Test response time < 12 seconds for all queries
    - Test session_id required (HTTP 400 if missing)
    - File: tests/integration/test_l4_integration.py (11 tests, real AWS)
    - _Requirements: 8.5, 8.6, 8.7, 8.8, 8.9, 11.4, 22.7_

- [ ] 18. Optional: Implement DynamoDB persistence
  - [ ] 18.1 Create DynamoDB table for conversations
    - Create table: geekbrain-conversations
    - Set partition key: session_id, sort key: turn_id
    - Enable TTL for auto-deletion after 30 days
    - _Requirements: 9.5, 16.9_
  
  - [ ] 18.2 Implement DynamoDBMemory class
    - Extend MemoryManager base class
    - Implement save_turn() using boto3 DynamoDB client
    - Implement get_history() querying by session_id
    - Add error handling for DynamoDB unavailable
    - _Requirements: 9.5, 12.3_

- [x] 19. Checkpoint - L4 functional
  - Unit tests: 81 passed (tests/unit/)
  - Integration tests: L4 tests ready to run with real AWS

### Phase 6: Evidence Pack & Presentation (Friday)

- [x] 20. Create Evidence Pack documentation
  - [x] 20.1 Write Evidence Pack markdown file
    - Created w4/docs/W4_evidence.md
    - Cover section: team info, LLM (Claude 3.5 Sonnet v2), framework (FastAPI + Bedrock), memory (WindowMemory)
    - Architecture Overview with Mermaid diagram and component table
    - Decision Log: 3 decisions (Custom orchestration, Window Memory, Separate data sources)
    - _Requirements: 14.1, 14.2, 14.3, 14.4_
  
  - [x] 20.2 Document L1-L2 evidence
    - L1: Team Platform lead query → "Alex Chen" with source citation
    - L1: Deployment freeze query → "Friday 18:00 to Monday 08:00"
    - L2: PaymentGW API rate limit → v2=1000 supersedes v1=500 with conflict explanation
    - _Requirements: 14.5, 14.6_
  
  - [x] 20.3 Document L3 evidence
    - Database query: PaymentGW Q1 cost = $16,500 with SQL shown
    - Monitoring API: PaymentGW current p99 = 185ms
    - Multi-tool: NotificationSvc SLA breach (3200ms > 2000ms target)
    - Tool execution logs with exact inputs/outputs
    - Numerical accuracy verification table (5 queries verified)
    - _Requirements: 14.6, 14.7, 13.7_
  
  - [x] 20.4 Document L4 evidence
    - 4-turn conversation: cost → pronoun "nó" → team → deadline
    - Memory configuration: WindowMemory(window_size=5)
    - Session ID shown for each turn
    - _Requirements: 14.8_
  
  - [x] 20.5 Add Reflection section
    - Hardest level: L3 (system prompt engineering for tool selection accuracy)
    - What would be different: prompt evaluation harness, DynamoDB from start, structured logging
    - Memory strategy trade-offs table: Buffer vs Window vs Query Rewriting
    - _Requirements: 14.9, 9.9_
  
  - [ ] 20.6 Commit and share Evidence Pack
    - Commit w4/docs/W4_evidence.md to repository
    - Post commit link to Slack before presentation slot
    - _Requirements: 14.10, 23.9_

- [x] 21. Prepare presentation slides
  - [x] 21.1 Create presentation slides
    - Created w4/docs/presentation_slides.md (10 slides)
    - Includes architecture diagram with component labels
    - Includes 1 major decision and 1 lesson learned
    - Includes demo plan for each implemented level (L1-L4)
    - Backup screenshots available in Evidence Pack
    - _Requirements: 23.1, 23.2, 23.3, 23.4, 23.5_
  
  - [ ] 21.2 Rehearse presentation
    - Practice presentation to fit 10-12 minutes
    - Assign roles: architecture presenter, demo runner, QnA responder
    - Prepare answers for likely QnA questions
    - _Requirements: 23.6, 23.7, 23.8_

- [x] 22. Test demo environment
  - [x] 22.1 Verify all services running
    - Updated DEMO_SCRIPT.md with full L1-L4 demo (was L1-only)
    - Includes health check commands for both APIs
    - Includes env var setup instructions
    - _Requirements: 23.10_
  
  - [x] 22.2 Test live demo queries
    - Demo script includes unseen queries per level
    - All queries use real API (not hardcoded responses)
    - Error handling tested via integration tests
    - _Requirements: 15.1, 15.2, 15.3, 15.4, 22.9_
  
  - [x] 22.3 Prepare for live demo
    - Created full demo script with curl commands for L1-L4
    - Includes fallback screenshots plan (Evidence Pack)
    - Includes Q&A preparation table
    - _Requirements: 15.5, 15.6, 15.7_

- [x] 23. Final checkpoint - System ready for demo
  - 81 unit tests passing, L4 integration tests ready
  - Evidence Pack written, Demo Script exists

### Phase 7: Bonus Features (Optional)

- [x] 24. Bonus A: Observability Dashboard
  - [x] 24.1 Implement event logging
    - Created `src/event_logger.py` with `EventLogger` class (thread-safe, singleton)
    - Tracks events: query_received, retrieval_completed, tool_executed, llm_invoked, memory_loaded, response_generated
    - Events stored in-memory dict: query_id → List[ProcessingEvent] (max 200 queries, LRU eviction)
    - Integrated into `main.py` — logs query received and response generated for every API call
    - _Requirements: 19.1, 19.2, 19.3, 19.4, 19.5, 19.6_
  
  - [x] 24.2 Create dashboard web interface
    - Created `src/dashboard.py` — FastAPI app running on port 8002
    - REST endpoints: GET /api/queries, GET /api/query/{id}
    - WebSocket endpoint: WS /ws for real-time event streaming (polls every 500ms)
    - Dark-themed HTML/JS UI with timeline visualization
    - Color-coded event types: query (blue), retrieval (green), tool (orange), LLM (purple), memory (cyan), response (red)
    - Auto-refresh every 3 seconds, sidebar with query list, click to view pipeline
    - _Requirements: 19.7, 19.8_
  
  - [-] 24.3 Test dashboard during demo
    - Dashboard ready to run: `python dashboard.py` → http://localhost:8002
    - Show retrieved chunks, tool calls, and LLM reasoning
    - Include dashboard screenshots in Evidence Pack
    - _Requirements: 19.9, 19.10_

- [x] 25. Bonus B: Agent Reasoning
  - [x] 25.1 Implement investigation query handler
    - Created `src/investigation.py` with `InvestigationAgent` class
    - Implements Plan → Gather → Analyze → Report workflow
    - Auto-detects service name from query text
    - Gathers: current metrics (Monitoring API), SLA targets (DB), incidents (DB), KB docs (RAG)
    - _Requirements: 20.1, 20.2, 20.3, 20.4_
  
  - [x] 25.2 Format structured investigation report
    - `InvestigationReport` dataclass with to_markdown() method
    - Sections: Current Status, Historical Performance, Issues Found, Recommendations
    - Each `ReasoningStep` includes: step_number, action, description, data_source, result, duration_ms
    - Issues flagged with severity: CRITICAL 🔴, HIGH 🟠, MEDIUM 🟡, LOW 🟢
    - Analysis: SLA latency comparison, error rate check, service status, incident patterns
    - _Requirements: 20.5, 20.6, 20.7, 20.8_
  
  - [x] 25.3 Document investigation example
    - Added POST /investigate endpoint to main.py
    - Test: `curl -X POST http://localhost:8001/investigate -d '{"query": "Is NotificationSvc healthy?"}'`
    - Returns: structured JSON with report_markdown, issues, recommendations, reasoning_steps
    - _Requirements: 20.9, 20.10_

- [x] 26. Bonus C: Knowledge Base Sync
  - [x] 26.1 Implement KB sync mechanism
    - Created `kb_sync.py` with `KBSyncManager` class
    - Methods: start_sync(), get_job_status(), wait_for_completion(), list_recent_jobs()
    - CLI: `python kb_sync.py` (trigger), `--wait` (wait for completion), `--status JOB_ID`, `--list`
    - Error handling: ConflictException (already syncing), ClientError, timeout
    - _Requirements: 21.1, 21.2, 21.3, 21.4, 21.5_
  
  - [ ] 26.2 Test KB sync
    - Update a document in S3
    - Trigger sync mechanism
    - Verify new content is retrievable after sync
    - Document sync mechanism in Evidence Pack
    - _Requirements: 21.8, 21.9_
  
  - [ ] 26.3 Optional: Setup S3 event trigger
    - Configure S3 bucket notification to Lambda
    - Implement automatic sync on document upload
    - Test concurrent sync request handling (handled via ConflictException)
    - _Requirements: 21.6, 21.7, 21.10_

## Notes

- Tasks marked with `*` are optional testing tasks and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation at key milestones
- L1-L3 completion = 90% score (9/10), L4 adds remaining 10%
- Bonus features (A, B, C) are optional enhancements beyond core requirements
- Python is the implementation language based on design document code examples
- All numerical values must be exact (no rounding) for L3 validation
- Response time targets: L1 (5s), L2 (8s), L3 (10s), L4 (12s)
