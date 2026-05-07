# Implementation Plan: W4 GeekBrain AI System

## Overview

This implementation plan follows a 3-day roadmap (Tuesday → Friday) to build a 4-level AI question-answering system for GeekBrain fintech startup. The system integrates AWS Bedrock Knowledge Base (RAG), 7 tools for database/API queries, and conversation memory. Implementation progresses incrementally: L1 (Simple RAG) → L2 (Multi-Source) → L3 (Tool-Augmented) → L4 (Memory), with each level building on the previous foundation.

**Technology Stack**: Python 3.11+, AWS Bedrock (Claude Sonnet), Bedrock Knowledge Base, OpenSearch Serverless, S3, DynamoDB, FastAPI, SQLite/PostgreSQL

**Data Sources**: 36 markdown documents (Knowledge Base), 4 CSV files (Database), Monitoring API (live metrics)

## Tasks

### Phase 1: Data Exploration & Setup (Tuesday)

- [ ] 1. Read and analyze knowledge base documents
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
  
  - [ ]* 9.3 Write integration tests for L2
    - Test conflict resolution query returns v2 value (1000 req/min)
    - Test response mentions v1 was 500 req/min
    - Test multi-document synthesis query uses multiple sources
    - Test response time < 8 seconds
    - _Requirements: 3.7, 3.8, 11.2, 22.5_

- [ ] 10. Checkpoint - L2 functional
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
  
  - [ ]* 11.3 Write unit tests for Database Tool
    - Test successful query returns correct data
    - Test Q1 PaymentGW cost query returns exactly 16500
    - Test write operations are rejected
    - Test malformed SQL returns error
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
  
  - [ ]* 12.3 Write unit tests for Metrics Tool
    - Test successful metrics retrieval for PaymentGW
    - Test service not found returns error
    - Test timeout handling when API unavailable
    - Mock HTTP requests for faster tests
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
  
  - [ ]* 13.6 Write unit tests for additional tools
    - Test each tool independently
    - Test error handling for invalid inputs
    - Verify tool definitions are correctly formatted
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
  
  - [ ]* 14.4 Write integration tests for L3
    - Test query "What was PaymentGW's total cost in Q1 2026?" returns $16,500
    - Test query "What is PaymentGW's current p99 latency?" calls metrics tool
    - Test query "Is NotificationSvc meeting SLA?" calls both database and metrics tools
    - Test response time < 10 seconds
    - _Requirements: 4.8, 4.9, 4.10, 11.3, 13.1, 13.2, 13.3_

- [ ] 15. Checkpoint - L3 functional
  - Ensure all tests pass, ask the user if questions arise.

### Phase 5: L4 Implementation - Memory-Enabled RAG (Friday Morning)

- [ ] 16. Implement memory management
  - [ ] 16.1 Create MemoryManager base class in w4/src/memory.py
    - Define interface: save_turn(), get_history(), format_for_llm(), clear_session()
    - Define ConversationTurn dataclass with turn_id, timestamp, query, response, context_used
    - _Requirements: 8.1, 9.5_
  
  - [ ] 16.2 Implement WindowMemory strategy
    - Create WindowMemory class extending MemoryManager
    - Store all turns in memory dict: session_id → List[ConversationTurn]
    - Implement get_history() to return only last N turns (default 5)
    - Implement format_for_llm() to create context string
    - _Requirements: 9.2, 9.3, 9.7_
  
  - [ ] 16.3 Integrate memory with orchestrator
    - Modify process_query_with_tools() to accept session_id
    - Load conversation history before processing query
    - Include formatted history in LLM context
    - Save turn after generating response
    - _Requirements: 8.2, 9.8_
  
  - [ ]* 16.4 Write unit tests for memory
    - Test save_turn() and get_history()
    - Test window memory limits to last N turns
    - Test format_for_llm() creates proper context string
    - _Requirements: 22.7_

- [ ] 17. Implement pronoun resolution
  - [ ] 17.1 Update system prompt for L4
    - Add conversation context section
    - Add pronoun resolution instructions with examples
    - Add instruction to resolve "it", "its", "they", "that service"
    - _Requirements: 8.3, 8.4, 10.7_
  
  - [ ]* 17.2 Write integration tests for L4
    - Test 4-turn conversation with pronoun resolution
    - Turn 1: "Which service had highest cost in March 2026?" → "PaymentGW"
    - Turn 2: "Why did its costs spike?" → resolves "its" to PaymentGW
    - Turn 3: "Which team is responsible?" → returns "Team Platform"
    - Turn 4: "Is the postmortem review deadline overdue?" → maintains context
    - Test response time < 12 seconds
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

- [ ] 19. Checkpoint - L4 functional
  - Ensure all tests pass, ask the user if questions arise.

### Phase 6: Evidence Pack & Presentation (Friday)

- [ ] 20. Create Evidence Pack documentation
  - [ ] 20.1 Write Evidence Pack markdown file
    - Create w4/docs/W4_evidence.md
    - Add Cover section: team info, LLM used (Claude Sonnet), framework (FastAPI + Bedrock), repo link
    - Add Architecture Overview with system diagram and component descriptions
    - Add Decision Log with 3 major decisions and lessons learned
    - _Requirements: 14.1, 14.2, 14.3, 14.4_
  
  - [ ] 20.2 Document L1-L2 evidence
    - Take screenshots of L1 query with correct response and source citation
    - Take screenshots of L2 conflict resolution query
    - Include logs showing retrieval process
    - _Requirements: 14.5, 14.6_
  
  - [ ] 20.3 Document L3 evidence
    - Take screenshots of database query with exact numerical result
    - Take screenshots of monitoring API query with live metrics
    - Include logs showing tool_call invocation and results
    - Verify numerical accuracy for all test queries
    - _Requirements: 14.6, 14.7, 13.7_
  
  - [ ] 20.4 Document L4 evidence
    - Take screenshots of 3-4 turn conversation with pronoun resolution
    - Show conversation state being maintained
    - Include logs showing memory loading/saving
    - _Requirements: 14.8_
  
  - [ ] 20.5 Add Reflection section
    - Document hardest level and why
    - Describe what would be done differently
    - Document chosen memory strategy and trade-offs
    - _Requirements: 14.9, 9.9_
  
  - [ ] 20.6 Commit and share Evidence Pack
    - Commit w4/docs/W4_evidence.md to repository
    - Post commit link to Slack before presentation slot
    - _Requirements: 14.10, 23.9_

- [ ] 21. Prepare presentation slides
  - [ ] 21.1 Create presentation slides
    - Derive slides from Evidence Pack content
    - Include architecture diagram with component labels
    - Include 1 major decision and 1 lesson learned
    - Include demo plan for each implemented level (L1-L4)
    - Prepare backup screenshots for each level
    - _Requirements: 23.1, 23.2, 23.3, 23.4, 23.5_
  
  - [ ] 21.2 Rehearse presentation
    - Practice presentation to fit 10-12 minutes
    - Assign roles: architecture presenter, demo runner, QnA responder
    - Prepare answers for likely QnA questions
    - _Requirements: 23.6, 23.7, 23.8_

- [ ] 22. Test demo environment
  - [ ] 22.1 Verify all services running
    - Confirm monitoring API is running on port 8000
    - Confirm database is seeded with correct data
    - Confirm Bedrock KB sync is complete
    - Confirm main API is accessible
    - _Requirements: 23.10_
  
  - [ ] 22.2 Test live demo queries
    - Test at least 1 unseen query per level
    - Verify system handles arbitrary queries (not hardcoded)
    - Test error handling scenarios
    - Measure and log response times
    - _Requirements: 15.1, 15.2, 15.3, 15.4, 22.9_
  
  - [ ] 22.3 Prepare for live demo
    - Create demo script with example queries
    - Prepare fallback screenshots if live demo fails
    - Test observability dashboard if implemented
    - _Requirements: 15.5, 15.6, 15.7_

- [ ] 23. Final checkpoint - System ready for demo
  - Ensure all tests pass, ask the user if questions arise.

### Phase 7: Bonus Features (Optional)

- [ ] 24. Bonus A: Observability Dashboard
  - [ ] 24.1 Implement event logging
    - Create EventLogger class to track processing events
    - Log events: query_received, retrieval_completed, tool_executed, llm_invoked, response_generated
    - Store events in memory dict: query_id → List[ProcessingEvent]
    - _Requirements: 19.1, 19.2, 19.3, 19.4, 19.5, 19.6_
  
  - [ ] 24.2 Create dashboard web interface
    - Create FastAPI app for dashboard on separate port
    - Implement WebSocket endpoint for real-time event streaming
    - Create HTML/JavaScript UI to display events
    - Color-code event types: retrieval (green), tool (orange), LLM (purple), response (red)
    - _Requirements: 19.7, 19.8_
  
  - [ ] 24.3 Test dashboard during demo
    - Display dashboard during presentation
    - Show retrieved chunks, tool calls, and LLM reasoning
    - Include dashboard screenshots in Evidence Pack
    - _Requirements: 19.9, 19.10_

- [ ] 25. Bonus B: Agent Reasoning
  - [ ] 25.1 Implement investigation query handler
    - Create investigation prompt template for multi-step reasoning
    - Implement plan-gather-analyze-report workflow
    - Test with query "Is NotificationSvc in a healthy state?"
    - _Requirements: 20.1, 20.2, 20.3, 20.4_
  
  - [ ] 25.2 Format structured investigation report
    - Create report sections: Current Status, Historical Performance, Issues Found, Recommendations
    - Display reasoning steps with data source citations
    - Flag items needing attention with severity levels
    - _Requirements: 20.5, 20.6, 20.7, 20.8_
  
  - [ ] 25.3 Document investigation example
    - Include investigation query example in Evidence Pack
    - Show comprehensive report output
    - _Requirements: 20.9, 20.10_

- [ ] 26. Bonus C: Knowledge Base Sync
  - [ ] 26.1 Implement KB sync mechanism
    - Create script or Lambda to trigger Bedrock StartIngestionJob API
    - Implement sync status monitoring
    - Add error handling and logging
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
    - Test concurrent sync request handling
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
