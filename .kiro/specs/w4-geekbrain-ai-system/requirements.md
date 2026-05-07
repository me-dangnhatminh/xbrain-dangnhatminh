# Requirements Document: W4 GeekBrain AI System

## Introduction

Hệ thống AI trả lời câu hỏi về GeekBrain — một fintech startup đang vận hành 6 production services. Hệ thống phải xử lý câu hỏi ở 4 cấp độ tăng dần: từ retrieval đơn giản (L1), tổng hợp nhiều nguồn (L2), sử dụng tools để truy vấn dữ liệu số liệu (L3), đến xử lý hội thoại nhiều turn với memory (L4).

Hệ thống tích hợp 3 nguồn dữ liệu:
- **Knowledge Base**: 36 markdown documents về company info, policies, postmortems (lưu trên S3, truy xuất qua Bedrock KB)
- **Database**: 4 CSV files (monthly_costs, incidents, sla_targets, daily_metrics) được seed vào SQLite/PostgreSQL
- **Monitoring API**: Python FastAPI script chạy local, trả về live system state

## Glossary

- **AI_System**: Hệ thống AI trả lời câu hỏi về GeekBrain
- **Knowledge_Base**: Tập hợp 36 markdown documents chứa thông tin về GeekBrain
- **Bedrock_KB**: Amazon Bedrock Knowledge Bases service thực hiện RAG pipeline
- **LLM**: Large Language Model (Claude via Amazon Bedrock) sinh câu trả lời
- **Retrieval**: Quá trình tìm kiếm và trích xuất relevant chunks từ Knowledge_Base
- **Tool**: Function có thể được gọi bởi LLM để lấy dữ liệu từ Database hoặc Monitoring_API
- **Database**: SQLite hoặc PostgreSQL chứa structured data từ 4 CSV files
- **Monitoring_API**: FastAPI service chạy local trả về live system metrics
- **Source_Citation**: Tên document gốc được trích dẫn trong câu trả lời
- **Conflict_Resolution**: Quá trình xác định thông tin đúng khi nhiều documents mâu thuẫn
- **Tool_Call**: LLM request để execute một Tool function
- **Conversation_State**: Context từ các turns trước trong multi-turn conversation
- **User**: Người dùng hỏi câu hỏi về GeekBrain
- **Query**: Câu hỏi từ User gửi đến AI_System
- **Response**: Câu trả lời từ AI_System trả về User
- **Chunk**: Đoạn text được trích xuất từ document trong quá trình Retrieval
- **Embedding**: Vector representation của text dùng cho semantic search
- **Vector_Store**: Database lưu trữ Embeddings (OpenSearch Serverless)
- **Top_K**: Số lượng Chunks được retrieve từ Vector_Store
- **System_Prompt**: Instructions cho LLM về cách xử lý Query và sinh Response
- **Multi_Turn_Conversation**: Chuỗi Query-Response liên tiếp có tham chiếu lẫn nhau
- **Pronoun_Resolution**: Quá trình xác định entity mà đại từ (it, its, they, that) tham chiếu đến

---

## Requirements

### Requirement 1: Simple RAG (L1)

**User Story:** Là một User, tôi muốn hỏi câu hỏi đơn giản về GeekBrain và nhận câu trả lời chính xác kèm source citation, để tôi có thể tin tưởng thông tin và verify nguồn gốc.

#### Acceptance Criteria

1. WHEN a User submits a Query requesting a single fact from one document, THE AI_System SHALL retrieve relevant Chunks from Knowledge_Base
2. WHEN relevant Chunks are retrieved, THE AI_System SHALL pass Chunks and Query to LLM
3. WHEN LLM generates a Response, THE AI_System SHALL include Source_Citation identifying the source document
4. THE AI_System SHALL return Response within 5 seconds for L1 queries
5. WHEN a Query asks "Who is the Team Platform lead?", THE AI_System SHALL return "Alex Chen" with Source_Citation "team_platform.md"
6. WHEN a Query asks "What is the deployment freeze window?", THE AI_System SHALL return "Friday 18:00 to Monday 08:00" with Source_Citation from deployment policy document
7. IF no relevant Chunks are found, THEN THE AI_System SHALL return a message stating information is not available in Knowledge_Base

---

### Requirement 2: Knowledge Base Setup

**User Story:** Là một Developer, tôi muốn setup Knowledge_Base với 36 markdown documents, để AI_System có thể retrieve thông tin chính xác.

#### Acceptance Criteria

1. THE Developer SHALL upload all 36 markdown documents to S3 bucket
2. THE Developer SHALL create Bedrock_KB pointing to S3 bucket as data source
3. THE Developer SHALL configure Bedrock_KB with an embedding model
4. WHEN Bedrock_KB sync is triggered, THE Bedrock_KB SHALL process all documents and generate Embeddings
5. WHEN sync completes, THE Bedrock_KB SHALL store Embeddings in Vector_Store
6. THE Developer SHALL verify Retrieval by testing with sample queries
7. WHEN a test Query "Team Platform lead" is submitted, THE Bedrock_KB SHALL return Chunks containing "Alex Chen" from team_platform.md

---

### Requirement 3: Multi-Source Retrieval (L2)

**User Story:** Là một User, tôi muốn hỏi câu hỏi phức tạp yêu cầu thông tin từ nhiều documents hoặc có conflicting information, để nhận câu trả lời tổng hợp chính xác.

#### Acceptance Criteria

1. WHEN a Query requires information from multiple documents, THE AI_System SHALL retrieve Chunks from all relevant documents
2. THE AI_System SHALL increase Top_K to retrieve 8-10 Chunks instead of 3-5
3. WHEN multiple Chunks contain conflicting information, THE AI_System SHALL apply Conflict_Resolution logic
4. THE System_Prompt SHALL instruct LLM to prefer most recent version when documents conflict
5. WHEN documents contain version indicators or dates, THE LLM SHALL check metadata to determine currency
6. WHEN a Query asks "What is PaymentGW's API rate limit?", THE AI_System SHALL identify v1 document (500 req/min) and v2 document (1000 req/min) and return v2 as current
7. WHEN a Query asks "Can Team Commerce deploy on Friday night?", THE AI_System SHALL synthesize information from deployment_policy.md and incident_response_policy.md and team information
8. WHEN Conflict_Resolution is applied, THE Response SHALL explain which source was trusted and why

---

### Requirement 4: Tool-Augmented RAG (L3)

**User Story:** Là một User, tôi muốn hỏi câu hỏi về số liệu hoặc live system state không có trong documents, để nhận câu trả lời chính xác dựa trên real data.

#### Acceptance Criteria

1. THE AI_System SHALL support Tool_Call mechanism for LLM to invoke external functions
2. THE AI_System SHALL implement Database Query Tool accepting SQL query string as parameter
3. THE AI_System SHALL implement Service Metrics Tool accepting service name as parameter
4. WHEN LLM determines a Query requires numerical data, THE LLM SHALL generate appropriate Tool_Call
5. WHEN a Tool_Call is generated, THE AI_System SHALL execute the Tool function and return results to LLM
6. WHEN Tool execution fails, THE AI_System SHALL return error message to LLM
7. THE LLM SHALL incorporate Tool results into Response generation
8. WHEN a Query asks "What was PaymentGW's total infrastructure cost in Q1 2026?", THE AI_System SHALL invoke Database Query Tool and return exactly $16,500
9. WHEN a Query asks "What is PaymentGW's current p99 latency?", THE AI_System SHALL invoke Service Metrics Tool and return current value from Monitoring_API
10. WHEN a Query asks "Is NotificationSvc meeting its SLA targets?", THE AI_System SHALL invoke both Service Metrics Tool and Database Query Tool to compare current metrics against SLA targets

---

### Requirement 5: Database Tool Implementation

**User Story:** Là một Developer, tôi muốn implement Database Query Tool, để LLM có thể truy vấn structured data từ CSV files.

#### Acceptance Criteria

1. THE Developer SHALL run seed script to load 4 CSV files into Database
2. THE Database SHALL contain tables: monthly_costs, incidents, sla_targets, daily_metrics
3. THE Database Query Tool SHALL accept SQL query string as input parameter
4. THE Database Query Tool SHALL execute read-only SQL queries against Database
5. THE Database Query Tool SHALL return query results as structured data
6. THE Database Query Tool SHALL reject write operations (INSERT, UPDATE, DELETE)
7. WHEN Database Query Tool receives "SELECT SUM(total_cost) FROM monthly_costs WHERE service='PaymentGW' AND month IN ('2026-01','2026-02','2026-03')", THE Tool SHALL return 16500
8. IF SQL query is malformed, THEN THE Database Query Tool SHALL return descriptive error message

---

### Requirement 6: Monitoring API Tool Implementation

**User Story:** Là một Developer, tôi muốn implement Service Metrics Tool, để LLM có thể lấy live system state từ Monitoring_API.

#### Acceptance Criteria

1. THE Developer SHALL start Monitoring_API service on localhost port 8000
2. THE Service Metrics Tool SHALL accept service name as input parameter
3. WHEN Service Metrics Tool is invoked, THE Tool SHALL make HTTP GET request to Monitoring_API endpoint
4. THE Service Metrics Tool SHALL parse JSON response from Monitoring_API
5. THE Service Metrics Tool SHALL return current latency, error rate, and request volume
6. WHEN Service Metrics Tool receives "PaymentGW", THE Tool SHALL call GET /metrics/PaymentGW and return current p99 latency approximately 185ms
7. IF Monitoring_API is not running, THEN THE Service Metrics Tool SHALL return error message indicating API unavailable
8. IF service name is invalid, THEN THE Service Metrics Tool SHALL return error message from Monitoring_API

---

### Requirement 7: Tool Registration and Orchestration

**User Story:** Là một Developer, tôi muốn register Tools với LLM và implement orchestration loop, để LLM có thể quyết định khi nào gọi Tool nào.

#### Acceptance Criteria

1. THE Developer SHALL define Tool descriptions in format LLM can understand
2. THE Tool description SHALL specify Tool name, parameters, return type, and when to use
3. THE Database Query Tool description SHALL state "Use for historical data: costs, incidents, SLA targets, daily metrics"
4. THE Service Metrics Tool description SHALL state "Use for current live data: latency, error rate, request volume"
5. WHEN LLM receives a Query, THE LLM SHALL determine whether to retrieve from Knowledge_Base, invoke Tool, or both
6. WHEN LLM generates Tool_Call, THE AI_System SHALL parse Tool_Call request
7. THE AI_System SHALL execute requested Tool with provided parameters
8. WHEN Tool execution completes, THE AI_System SHALL send Tool results back to LLM
9. THE LLM SHALL generate final Response incorporating Tool results
10. THE AI_System SHALL support multiple Tool_Calls in sequence for complex queries

---

### Requirement 8: Multi-Turn Conversation with Memory (L4)

**User Story:** Là một User, tôi muốn tiến hành hội thoại nhiều turn với AI_System, trong đó các câu hỏi follow-up tham chiếu đến turns trước, để tôi không phải lặp lại context.

#### Acceptance Criteria

1. THE AI_System SHALL maintain Conversation_State across multiple turns
2. WHEN a new Query is received, THE AI_System SHALL include relevant Conversation_State in context sent to LLM
3. THE AI_System SHALL implement Pronoun_Resolution to map pronouns to entities from previous turns
4. WHEN a Query contains "it", "its", "they", "that service", "their team", THE LLM SHALL resolve references using Conversation_State
5. THE AI_System SHALL handle conversations of at least 4 turns
6. WHEN Turn 1 asks "Which service had the highest cost in March 2026?", THE AI_System SHALL return "PaymentGW at $7,500"
7. WHEN Turn 2 asks "Why did its costs spike?", THE AI_System SHALL resolve "its" to PaymentGW and retrieve relevant postmortem
8. WHEN Turn 3 asks "Which team is responsible?", THE AI_System SHALL resolve context to PaymentGW and return "Team Platform, led by Alex Chen"
9. WHEN Turn 4 asks "Is the postmortem review deadline overdue?", THE AI_System SHALL maintain context about PaymentGW postmortem and check deadline
10. THE AI_System SHALL limit Conversation_State size to prevent context window overflow

---

### Requirement 9: Memory Strategy Implementation

**User Story:** Là một Developer, tôi muốn implement memory strategy cho L4, để AI_System có thể maintain context hiệu quả mà không làm ngập context window.

#### Acceptance Criteria

1. THE Developer SHALL choose one memory strategy: Buffer, Window, or Query Rewriting
2. WHERE Buffer strategy is chosen, THE AI_System SHALL store all turns and send all to LLM
3. WHERE Window strategy is chosen, THE AI_System SHALL store all turns but only send last 5 turns to LLM
4. WHERE Query Rewriting strategy is chosen, THE AI_System SHALL rewrite Query to be self-contained before processing
5. THE AI_System SHALL store Conversation_State in persistent storage (DynamoDB, local file, or in-memory dict)
6. WHEN Conversation_State exceeds context window limit, THE AI_System SHALL apply truncation or summarization
7. THE AI_System SHALL associate Conversation_State with session identifier
8. WHEN a new session starts, THE AI_System SHALL initialize empty Conversation_State
9. THE Developer SHALL document chosen memory strategy and trade-offs in Evidence Pack

---

### Requirement 10: System Prompt Engineering

**User Story:** Là một Developer, tôi muốn craft effective System_Prompt, để LLM xử lý queries đúng cách ở mọi level.

#### Acceptance Criteria

1. THE System_Prompt SHALL instruct LLM to answer using only provided context
2. THE System_Prompt SHALL instruct LLM to cite source documents for L1-L2 queries
3. THE System_Prompt SHALL instruct LLM to prefer most recent version when documents conflict
4. THE System_Prompt SHALL instruct LLM to explain conflicts when detected
5. THE System_Prompt SHALL provide clear guidance on when to use Database Query Tool vs Service Metrics Tool
6. THE System_Prompt SHALL instruct LLM to use Tools for numerical data and live metrics
7. WHERE L4 is implemented, THE System_Prompt SHALL instruct LLM to resolve pronouns using conversation history
8. THE System_Prompt SHALL instruct LLM to state when information is not available
9. THE System_Prompt SHALL specify Response format and language (Vietnamese)
10. THE Developer SHALL iterate on System_Prompt based on test results

---

### Requirement 11: Response Time and Performance

**User Story:** Là một User, tôi muốn nhận Response nhanh chóng, để trải nghiệm hỏi đáp mượt mà.

#### Acceptance Criteria

1. THE AI_System SHALL return Response within 5 seconds for L1 queries (retrieval only)
2. THE AI_System SHALL return Response within 8 seconds for L2 queries (multi-source retrieval)
3. THE AI_System SHALL return Response within 10 seconds for L3 queries (with Tool_Calls)
4. THE AI_System SHALL return Response within 12 seconds for L4 queries (with memory)
5. WHEN Monitoring_API is unavailable, THE AI_System SHALL timeout Tool_Call after 3 seconds
6. WHEN Database query takes longer than 5 seconds, THE AI_System SHALL return timeout error
7. THE AI_System SHALL log response time for each Query
8. WHEN response time exceeds threshold, THE AI_System SHALL log warning for performance investigation

---

### Requirement 12: Error Handling and Graceful Degradation

**User Story:** Là một User, tôi muốn nhận error messages rõ ràng khi hệ thống gặp vấn đề, để tôi biết cách điều chỉnh Query.

#### Acceptance Criteria

1. WHEN Knowledge_Base is unavailable, THE AI_System SHALL return error message stating retrieval service is down
2. WHEN Database connection fails, THE AI_System SHALL inform LLM that Database Tool is unavailable
3. WHEN Monitoring_API is not running, THE AI_System SHALL inform LLM that live metrics are unavailable
4. WHEN LLM generates malformed Tool_Call, THE AI_System SHALL return error message to LLM with correction guidance
5. WHEN Tool execution raises exception, THE AI_System SHALL catch exception and return error details to LLM
6. THE LLM SHALL incorporate error information into Response and suggest alternatives
7. WHEN Bedrock_KB sync is in progress, THE AI_System SHALL return message stating Knowledge_Base is updating
8. IF Query is empty or malformed, THEN THE AI_System SHALL return validation error message

---

### Requirement 13: Numerical Accuracy for L3

**User Story:** Là một Trainer, tôi muốn verify rằng AI_System trả về số liệu chính xác từ Database và Monitoring_API, để chấm điểm L3 đúng.

#### Acceptance Criteria

1. WHEN Query asks "What was PaymentGW's total cost in Q1 2026?", THE AI_System SHALL return exactly $16,500
2. WHEN Query asks "Which service had highest cost in March 2026?", THE AI_System SHALL return "PaymentGW" with cost $7,500
3. WHEN Query asks "What is NotificationSvc's SLA target for p99 latency?", THE AI_System SHALL return exactly 2000ms
4. WHEN Query asks current metrics, THE AI_System SHALL return values from Monitoring_API without modification
5. THE AI_System SHALL not round or approximate numerical values unless explicitly requested
6. WHEN Tool returns numerical data, THE LLM SHALL preserve exact values in Response
7. THE Developer SHALL verify numerical accuracy with at least 5 test queries before demo

---

### Requirement 14: Evidence Pack Documentation

**User Story:** Là một Developer, tôi muốn document hệ thống trong Evidence Pack, để Trainer có thể verify implementation sau presentation.

#### Acceptance Criteria

1. THE Developer SHALL create file docs/W4_evidence.md in repository
2. THE Evidence Pack SHALL include Cover section with team info, LLM used, framework used, and repo link
3. THE Evidence Pack SHALL include Architecture Overview with system diagram and component descriptions
4. THE Evidence Pack SHALL include Decision Log with 3 major decisions and lessons learned
5. THE Evidence Pack SHALL include Per-Level Evidence with screenshots and logs for L1-L4
6. FOR EACH level, THE Evidence Pack SHALL include screenshot of correct Response and proof of system processing
7. THE L3 Evidence SHALL include log showing Tool_Call invocation and real data returned
8. WHERE L4 is implemented, THE Evidence Pack SHALL include screenshot of 3-4 turn conversation
9. THE Evidence Pack SHALL include Reflection section with hardest level and what would be done differently
10. THE Developer SHALL commit Evidence Pack and post commit link to Slack before presentation slot

---

### Requirement 15: Live Demo Capability

**User Story:** Là một Trainer, tôi muốn test AI_System với câu hỏi chưa từng thấy trong demo, để verify hệ thống không hardcode responses.

#### Acceptance Criteria

1. THE AI_System SHALL accept arbitrary Query input during demo
2. THE AI_System SHALL not contain hardcoded responses for specific queries
3. WHEN Trainer asks a Query not in test set, THE AI_System SHALL process Query through full pipeline
4. THE AI_System SHALL handle at least 1 unseen Query per level during demo
5. WHEN live demo fails for a level, THE Developer SHALL present screenshot from Evidence Pack as backup
6. THE AI_System SHALL display processing steps or logs during demo (if observability dashboard exists)
7. THE AI_System SHALL complete Query processing within timeout limits during demo
8. IF AI_System returns incorrect Response during demo, THE Developer SHALL explain root cause

---

### Requirement 16: AWS Service Integration

**User Story:** Là một Developer, tôi muốn integrate AWS services đúng cách, để hệ thống chạy trên cloud infrastructure.

#### Acceptance Criteria

1. THE Developer SHALL upload Knowledge_Base documents to S3 bucket
2. THE S3 bucket SHALL have versioning enabled
3. THE S3 bucket SHALL have encryption at rest enabled
4. THE Developer SHALL create Bedrock_KB with S3 as data source
5. THE Bedrock_KB SHALL use OpenSearch Serverless as Vector_Store
6. THE Developer SHALL configure Bedrock_KB with embedding model (Amazon Titan Embeddings v2 or equivalent)
7. THE Developer SHALL select foundation model for LLM (Claude Sonnet or Haiku via Bedrock)
8. WHERE Bedrock Agents is used, THE Developer SHALL create Action Groups with Lambda functions for Tools
9. WHERE DynamoDB is used for L4, THE Developer SHALL create table with session_id as partition key
10. THE Developer SHALL configure IAM roles with least privilege for all AWS service access

---

### Requirement 17: Tool Function Completeness

**User Story:** Là một Developer, tôi muốn implement đầy đủ 7 tools theo spec, để AI_System có thể trả lời mọi loại câu hỏi L3.

#### Acceptance Criteria

1. THE AI_System SHALL implement Service Status Tool returning live status of a service
2. THE AI_System SHALL implement Service Metrics Tool returning current performance metrics
3. THE AI_System SHALL implement List Services Tool returning all services in system
4. THE AI_System SHALL implement Incident History Tool returning past incidents of a service
5. THE AI_System SHALL implement Team Info Tool returning details about a team
6. THE AI_System SHALL implement Compare Services Tool comparing metrics between services
7. THE AI_System SHALL implement Database Query Tool for structured data queries
8. EACH Tool SHALL have clear description of parameters, return type, and use case
9. EACH Tool SHALL handle errors gracefully and return descriptive error messages
10. THE Developer SHALL test each Tool independently before integration with LLM

---

### Requirement 18: Conflict Resolution Logic

**User Story:** Là một Developer, tôi muốn implement robust Conflict_Resolution logic, để AI_System xử lý đúng khi documents mâu thuẫn.

#### Acceptance Criteria

1. THE System_Prompt SHALL define conflict resolution rules for LLM
2. WHEN documents have version numbers, THE LLM SHALL prefer higher version
3. WHEN documents have dates, THE LLM SHALL prefer more recent date
4. WHEN documents have status (archived, superseded, current), THE LLM SHALL prefer current
5. WHEN conflict cannot be resolved by metadata, THE LLM SHALL state both values and explain uncertainty
6. THE Response SHALL explicitly mention when conflict was detected and resolved
7. WHEN Query asks "What is PaymentGW's API rate limit?", THE AI_System SHALL retrieve both v1 (500) and v2 (1000) documents
8. THE LLM SHALL identify v2 as current based on version number or date
9. THE Response SHALL state "The current rate limit is 1000 req/min (v2). Previous version (v1) specified 500 req/min."
10. THE Developer SHALL test conflict resolution with at least 3 conflicting document pairs

---

### Requirement 19: Observability and Debugging (Bonus A)

**User Story:** Là một Developer, tôi muốn xem nội bộ pipeline khi xử lý Query, để debug issues và demonstrate system behavior.

#### Acceptance Criteria

1. WHERE Observability Dashboard is implemented, THE Dashboard SHALL display retrieved Chunks for each Query
2. THE Dashboard SHALL display which Tools were called and with what parameters
3. THE Dashboard SHALL display Tool execution results
4. THE Dashboard SHALL display LLM input (context + Query + Tool results)
5. THE Dashboard SHALL display LLM output (Response)
6. THE Dashboard SHALL display processing time for each step
7. THE Dashboard SHALL update in real-time as Query is processed
8. THE Dashboard SHALL be accessible during demo presentation
9. THE Developer SHALL include Dashboard screenshots in Evidence Pack
10. THE Dashboard SHALL help Trainer understand system reasoning process

---

### Requirement 20: Agent Reasoning (Bonus B)

**User Story:** Là một User, tôi muốn hỏi câu hỏi điều tra mở yêu cầu multi-step reasoning, để nhận structured report với visible reasoning steps.

#### Acceptance Criteria

1. WHERE Agent Reasoning is implemented, THE AI_System SHALL handle investigation queries
2. WHEN Query asks "Is NotificationSvc in a healthy state?", THE AI_System SHALL plan investigation approach
3. THE AI_System SHALL gather data from multiple sources (Knowledge_Base, Database, Monitoring_API)
4. THE AI_System SHALL analyze gathered data and identify issues
5. THE Response SHALL include structured report with sections: Current Status, Historical Performance, Issues Found, Recommendations
6. THE Response SHALL display reasoning steps showing how conclusion was reached
7. EACH reasoning step SHALL cite data source used
8. THE AI_System SHALL flag items needing attention with severity level
9. THE Developer SHALL include investigation query example in Evidence Pack
10. THE investigation Response SHALL be more comprehensive than simple fact retrieval

---

### Requirement 21: Knowledge Base Sync (Bonus C)

**User Story:** Là một Developer, tôi muốn re-sync Bedrock_KB khi documents thay đổi, để Knowledge_Base không trở nên lỗi thời.

#### Acceptance Criteria

1. WHERE KB Sync is implemented, THE Developer SHALL create mechanism to trigger Bedrock_KB sync
2. WHEN documents are updated in S3, THE sync mechanism SHALL detect changes
3. THE sync mechanism SHALL call Bedrock StartIngestionJob API
4. THE sync mechanism SHALL wait for ingestion job to complete
5. THE sync mechanism SHALL log sync status and any errors
6. WHERE S3 event trigger is used, THE Developer SHALL configure S3 bucket notification to Lambda
7. WHERE manual sync is used, THE Developer SHALL provide script or notebook to trigger sync
8. THE Developer SHALL test sync by updating a document and verifying new content is retrievable
9. THE Developer SHALL document sync mechanism in Evidence Pack
10. THE sync mechanism SHALL handle concurrent sync requests gracefully

---

### Requirement 22: Testing and Validation

**User Story:** Là một Developer, tôi muốn test hệ thống thoroughly trước demo, để tự tin về độ chính xác và stability.

#### Acceptance Criteria

1. THE Developer SHALL create test suite with at least 3 queries per level
2. THE test suite SHALL include queries from project announcement examples
3. THE test suite SHALL include at least 2 unseen queries per level
4. THE Developer SHALL verify L1 queries return correct facts with source citations
5. THE Developer SHALL verify L2 queries correctly resolve conflicts
6. THE Developer SHALL verify L3 queries return exact numerical values
7. THE Developer SHALL verify L4 conversation maintains context across 4 turns
8. THE Developer SHALL test error cases (API down, DB unavailable, malformed query)
9. THE Developer SHALL measure and log response times for all test queries
10. THE Developer SHALL fix any failing tests before demo day

---

### Requirement 23: Presentation Preparation

**User Story:** Là một Team, chúng tôi muốn chuẩn bị presentation slides và demo script, để thuyết trình mượt mà trong 10-12 phút.

#### Acceptance Criteria

1. THE Team SHALL create presentation slides derived from Evidence Pack
2. THE slides SHALL include Architecture diagram with component labels
3. THE slides SHALL include 1 major decision and 1 lesson learned
4. THE slides SHALL include demo plan for each implemented level
5. THE Team SHALL prepare backup screenshots for each level in case live demo fails
6. THE Team SHALL rehearse presentation to ensure timing fits 10-12 minutes
7. THE Team SHALL assign roles: who presents architecture, who runs demo, who answers QnA
8. THE Team SHALL prepare answers for likely QnA questions about system design
9. THE Team SHALL post Evidence Pack commit link to Slack before presentation slot
10. THE Team SHALL test demo environment (API running, DB seeded, system accessible) before presentation

---

