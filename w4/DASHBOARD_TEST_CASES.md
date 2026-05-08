# Dashboard Test Cases — Comprehensive Testing Guide

## 🎯 Test Objectives

Verify that the Chat & Observability Dashboard correctly:
1. Displays retrieved chunks with scores
2. Shows tool execution with parameters and results
3. Tracks LLM invocations
4. Displays memory loading for L4
5. Reports accurate processing times
6. Updates in real-time

---

## 📋 Test Cases by Level

### L1 — Simple RAG Tests

#### Test 1.1: Basic Team Information
**Query**: `Who is the Team Platform lead?`

**Expected Observability Events**:
- ✅ Query Received (L1)
- ✅ Retrieval Completed: 5 chunks from `team_platform.md`
- ✅ Response Generated: "Alex Chen"

**Verification Points**:
- [ ] Chunks show `team_platform.md` as source
- [ ] Relevance scores > 0.7
- [ ] Processing time < 5s
- [ ] Answer mentions "Alex Chen"

---

#### Test 1.2: Policy Information
**Query**: `What is the deployment freeze window?`

**Expected Observability Events**:
- ✅ Query Received (L1)
- ✅ Retrieval Completed: 5 chunks from `deployment_policy.md`
- ✅ Response Generated: "Friday 18:00 to Monday 08:00"

**Verification Points**:
- [ ] Chunks from `deployment_policy.md`
- [ ] Answer includes specific time window
- [ ] Processing time < 5s

---

#### Test 1.3: Technical Documentation
**Query**: `How do I configure the monitoring agent?`

**Expected Observability Events**:
- ✅ Query Received (L1)
- ✅ Retrieval Completed: 5 chunks from monitoring docs
- ✅ Response Generated: Configuration steps

**Verification Points**:
- [ ] Multiple relevant chunks retrieved
- [ ] Answer provides actionable steps
- [ ] Sources cited correctly

---

### L2 — Multi-Source RAG Tests

#### Test 2.1: Version Conflict Resolution
**Query**: `What is PaymentGW's API rate limit?`

**Expected Observability Events**:
- ✅ Query Received (L2)
- ✅ Retrieval Completed: 10 chunks (increased from L1)
- ✅ Response Generated: "1,000 req/min (v2 supersedes v1)"

**Verification Points**:
- [ ] Chunks from both `api_reference_v1.md` and `api_reference_v2.md`
- [ ] Answer mentions conflict: v1 (500) vs v2 (1000)
- [ ] Answer prefers v2 (newer version)
- [ ] Processing time < 8s

---

#### Test 2.2: Multi-Document Query
**Query**: `What are the SLA requirements for all services?`

**Expected Observability Events**:
- ✅ Query Received (L2)
- ✅ Retrieval Completed: 10 chunks from multiple SLA docs
- ✅ Response Generated: Aggregated SLA info

**Verification Points**:
- [ ] Chunks from multiple service documents
- [ ] Answer aggregates information correctly
- [ ] All services mentioned

---

#### Test 2.3: Conflicting Information
**Query**: `What is the incident response time SLA?`

**Expected Observability Events**:
- ✅ Query Received (L2)
- ✅ Retrieval Completed: 10 chunks
- ✅ Response Generated: Resolved conflict with explanation

**Verification Points**:
- [ ] System detects conflicting information
- [ ] Answer explains which source is authoritative
- [ ] Reasoning is transparent

---

### L3 — Tool-Augmented RAG Tests

#### Test 3.1: Historical Cost Query (Database Tool)
**Query**: `What was PaymentGW's total infrastructure cost in Q1 2026?`

**Expected Observability Events**:
- ✅ Query Received (L3)
- ✅ Tool Executed: `query_database`
  - Parameters: SQL query for Q1 2026 costs
  - Result: `[{"total": 16500.0}]`
- ✅ Response Generated: "$16,500"

**Verification Points**:
- [ ] Tool badge shows `query_database`
- [ ] SQL query visible in parameters
- [ ] Result shows exact value: 16500.0
- [ ] Answer: "$16,500" (exact match)
- [ ] Processing time < 10s

---

#### Test 3.2: Live Metrics Query (Monitoring API Tool)
**Query**: `What is PaymentGW's current p99 latency?`

**Expected Observability Events**:
- ✅ Query Received (L3)
- ✅ Tool Executed: `get_service_metrics`
  - Parameters: `{"service_name": "PaymentGW"}`
  - Result: `{"latency_p99_ms": 185, ...}`
- ✅ Response Generated: "185ms"

**Verification Points**:
- [ ] Tool badge shows `get_service_metrics`
- [ ] Service name in parameters
- [ ] Live metrics in result
- [ ] Answer matches result value
- [ ] Processing time < 10s

---

#### Test 3.3: Multi-Tool Query (Database + Monitoring)
**Query**: `Is NotificationSvc meeting its SLA targets?`

**Expected Observability Events**:
- ✅ Query Received (L3)
- ✅ Tool Executed #1: `query_database` (get SLA targets)
  - Result: `{"p99_target_ms": 2000, "error_rate_target": 0.05}`
- ✅ Tool Executed #2: `get_service_metrics` (get current metrics)
  - Result: `{"latency_p99_ms": 3200, "error_rate": 0.15}`
- ✅ Response Generated: "❌ NOT meeting SLA"

**Verification Points**:
- [ ] Two tool executions visible
- [ ] First tool gets targets from DB
- [ ] Second tool gets current metrics
- [ ] Answer compares and concludes breach
- [ ] Processing time < 10s

---

#### Test 3.4: Service Comparison
**Query**: `Compare latency between PaymentGW and NotificationSvc`

**Expected Observability Events**:
- ✅ Query Received (L3)
- ✅ Tool Executed: `compare_services`
  - Parameters: `{"service_names": ["PaymentGW", "NotificationSvc"]}`
- ✅ Response Generated: Comparison table

**Verification Points**:
- [ ] Tool shows both service names
- [ ] Result contains metrics for both
- [ ] Answer presents clear comparison

---

#### Test 3.5: Incident History
**Query**: `Show me recent incidents for PaymentGW`

**Expected Observability Events**:
- ✅ Query Received (L3)
- ✅ Tool Executed: `get_incident_history`
  - Parameters: `{"service_name": "PaymentGW", "limit": 10}`
- ✅ Response Generated: List of incidents

**Verification Points**:
- [ ] Tool parameters show service name
- [ ] Result lists incidents with dates
- [ ] Answer formats incidents clearly

---

#### Test 3.6: List All Services
**Query**: `What services are being monitored?`

**Expected Observability Events**:
- ✅ Query Received (L3)
- ✅ Tool Executed: `list_services`
- ✅ Response Generated: List of services

**Verification Points**:
- [ ] Tool executed without parameters
- [ ] Result shows all services
- [ ] Answer lists services clearly

---

#### Test 3.7: Team Information via RAG Tool
**Query**: `Who are the members of Team Platform?`

**Expected Observability Events**:
- ✅ Query Received (L3)
- ✅ Tool Executed: `get_team_info`
  - Parameters: `{"team_name": "Platform"}`
- ✅ Response Generated: Team member list

**Verification Points**:
- [ ] Tool uses RAG internally
- [ ] Result shows team members
- [ ] Answer includes names and roles

---

### L4 — Memory-Enabled Multi-Turn Tests

#### Test 4.1: Four-Turn Conversation (Vietnamese)
**Session ID**: `test-session-001`

**Turn 1**: `Service nào có chi phí cao nhất tháng 3/2026?`

**Expected Events**:
- ✅ Query Received (L4, session: test-session-001)
- ✅ Memory Loaded: 0 turns (new session)
- ✅ Tool Executed: `query_database`
- ✅ Response Generated: "PaymentGW với $7,500"

**Verification**:
- [ ] Session ID displayed
- [ ] Memory shows 0 turns (first query)
- [ ] Tool finds highest cost service

---

**Turn 2**: `Tại sao chi phí của nó tăng đột biến?`

**Expected Events**:
- ✅ Query Received (L4, session: test-session-001)
- ✅ Memory Loaded: 1 turn (previous Q&A)
- ✅ Retrieval Completed: Chunks from `postmortem_paymentgw.md`
- ✅ Response Generated: Explanation of cost spike

**Verification**:
- [ ] Memory shows 1 turn loaded
- [ ] System resolves "nó" → PaymentGW from context
- [ ] Answer explains scaling incident

---

**Turn 3**: `Team nào chịu trách nhiệm?`

**Expected Events**:
- ✅ Query Received (L4, session: test-session-001)
- ✅ Memory Loaded: 2 turns
- ✅ Tool Executed: `get_team_info` or RAG retrieval
- ✅ Response Generated: "Team Platform, Alex Chen"

**Verification**:
- [ ] Memory shows 2 turns loaded
- [ ] System maintains PaymentGW context
- [ ] Answer identifies responsible team

---

**Turn 4**: `Deadline review postmortem đã qua chưa?`

**Expected Events**:
- ✅ Query Received (L4, session: test-session-001)
- ✅ Memory Loaded: 3 turns
- ✅ Retrieval Completed: Postmortem deadline info
- ✅ Response Generated: Date comparison

**Verification**:
- [ ] Memory shows 3 turns loaded
- [ ] System knows which postmortem (PaymentGW)
- [ ] Answer compares deadline with current date
- [ ] Processing time < 12s

---

#### Test 4.2: New Session Reset
**Action**: Click "🔄 New Session" button

**Expected**:
- [ ] New session ID generated
- [ ] Chat history cleared
- [ ] Observability panel reset
- [ ] Next query starts fresh (0 turns in memory)

---

#### Test 4.3: Pronoun Resolution
**Session ID**: `test-session-002`

**Turn 1**: `What is PaymentGW's current error rate?`
**Turn 2**: `Is it above the SLA threshold?`

**Expected Events (Turn 2)**:
- ✅ Memory Loaded: 1 turn
- ✅ System resolves "it" → PaymentGW error rate
- ✅ Tool Executed: Compare with SLA

**Verification**:
- [ ] Pronoun "it" correctly resolved
- [ ] Answer references PaymentGW specifically

---

#### Test 4.4: Context Switching
**Session ID**: `test-session-003`

**Turn 1**: `What is PaymentGW's cost?`
**Turn 2**: `What about NotificationSvc?`
**Turn 3**: `Compare them`

**Expected Events (Turn 3)**:
- ✅ Memory Loaded: 2 turns
- ✅ System knows "them" = PaymentGW + NotificationSvc
- ✅ Tool Executed: `compare_services`

**Verification**:
- [ ] Context maintained across turns
- [ ] Comparison includes both services

---

#### Test 4.5: Window Memory Limit (5 turns)
**Session ID**: `test-session-004`

**Turns 1-6**: Ask 6 different questions

**Expected Events (Turn 6)**:
- ✅ Memory Loaded: 5 turns (window size limit)
- ✅ Turn 1 is dropped (oldest)
- ✅ Turns 2-6 are in context

**Verification**:
- [ ] Memory shows max 5 turns
- [ ] Oldest turn not accessible
- [ ] Recent context maintained

---

## 🔍 Observability Verification Checklist

For each test, verify these observability features:

### Event Timeline
- [ ] Events appear in chronological order
- [ ] Each event has timestamp
- [ ] Event types color-coded correctly
- [ ] Timeline connector line visible

### Retrieved Chunks Display
- [ ] Source file names shown
- [ ] Relevance scores displayed (0.0-1.0)
- [ ] Text preview truncated appropriately
- [ ] Multiple chunks visible for L2

### Tool Execution Display
- [ ] Tool name badge visible
- [ ] Parameters formatted as JSON
- [ ] Result preview shown (truncated if long)
- [ ] Success/failure indicator (✅/❌)

### LLM Invocation Display
- [ ] Model ID shown (Claude 3.5 Sonnet/Haiku)
- [ ] Prompt length displayed
- [ ] Response preview visible

### Memory Loading Display (L4 only)
- [ ] Session ID shown
- [ ] Number of turns loaded
- [ ] Event appears before other processing

### Response Generated Display
- [ ] Final answer text shown
- [ ] Processing time in milliseconds
- [ ] Tools used listed (if any)
- [ ] Level badge displayed

---

## ⚡ Performance Tests

### Test P1: L1 Response Time
**Query**: Any L1 query
**Target**: < 5 seconds
**Measure**: Processing time in "Response Generated" event

---

### Test P2: L2 Response Time
**Query**: Any L2 query
**Target**: < 8 seconds
**Measure**: Processing time in "Response Generated" event

---

### Test P3: L3 Response Time
**Query**: Single tool query
**Target**: < 10 seconds
**Measure**: Processing time in "Response Generated" event

---

### Test P4: L3 Multi-Tool Response Time
**Query**: Query requiring 2+ tools
**Target**: < 10 seconds
**Measure**: Processing time in "Response Generated" event

---

### Test P5: L4 Response Time
**Query**: Any L4 query with memory
**Target**: < 12 seconds
**Measure**: Processing time in "Response Generated" event

---

## 🎨 UI/UX Tests

### Test U1: Real-Time Updates
**Action**: Send a query
**Expected**: Events appear progressively, not all at once
**Verification**: Watch timeline populate in real-time

---

### Test U2: Auto-Scroll
**Action**: Send a query with many events
**Expected**: 
- Chat panel scrolls to latest message
- Observability panel scrolls to latest event

---

### Test U3: Level Switching
**Action**: Switch between L1/L2/L3/L4 buttons
**Expected**:
- Active button highlighted
- Session info shows/hides for L4
- Next query uses selected level

---

### Test U4: Session Management
**Action**: Click "New Session" button
**Expected**:
- New session ID generated
- Chat cleared
- Observability reset

---

### Test U5: Keyboard Shortcuts
**Action**: Press Enter in input field
**Expected**: Message sent (same as clicking Send button)

**Action**: Press Shift+Enter in input field
**Expected**: New line added (message not sent)

---

### Test U6: Long Messages
**Action**: Send very long query (500+ chars)
**Expected**:
- Input field expands
- Message displays fully in chat
- Observability shows full query

---

### Test U7: Error Handling
**Action**: Stop monitoring API, send L3 query
**Expected**:
- Error message in chat
- Tool execution shows failure
- User-friendly error explanation

---

## 🐛 Edge Case Tests

### Test E1: Empty Query
**Action**: Send empty message
**Expected**: Send button disabled or validation error

---

### Test E2: Very Long Query
**Query**: 1000+ character question
**Expected**: System handles gracefully, no truncation errors

---

### Test E3: Special Characters
**Query**: `What is "PaymentGW's" cost? (Q1 2026)`
**Expected**: Query processed correctly, special chars escaped

---

### Test E4: Multiple Rapid Queries
**Action**: Send 3 queries quickly
**Expected**: 
- Queries queued properly
- Each gets unique query_id
- Observability shows all queries

---

### Test E5: Network Timeout
**Action**: Simulate slow network
**Expected**: Loading indicator, timeout handling

---

### Test E6: Invalid Session ID
**Action**: Manually set invalid session_id
**Expected**: System creates new session or handles gracefully

---

## 📊 Test Execution Checklist

### Pre-Test Setup
- [ ] All services running (ports 8000, 8001, 8002)
- [ ] Database seeded with test data
- [ ] Knowledge Base synced with latest docs
- [ ] Browser cache cleared

### During Testing
- [ ] Record screenshots for each test
- [ ] Note actual processing times
- [ ] Document any unexpected behavior
- [ ] Check browser console for errors

### Post-Test Validation
- [ ] All L1 tests passed
- [ ] All L2 tests passed
- [ ] All L3 tests passed
- [ ] All L4 tests passed
- [ ] Performance targets met
- [ ] UI/UX tests passed
- [ ] Edge cases handled

---

## 🎯 Success Criteria

**Dashboard is production-ready if**:
- ✅ All L1-L4 functional tests pass
- ✅ All performance targets met
- ✅ Real-time updates work smoothly
- ✅ No console errors during normal operation
- ✅ Error handling is user-friendly
- ✅ UI is responsive and intuitive
- ✅ Observability provides clear insights

---

## 📝 Test Report Template

```markdown
# Dashboard Test Report

**Date**: YYYY-MM-DD
**Tester**: [Name]
**Environment**: Local / Staging / Production

## Summary
- Total Tests: X
- Passed: Y
- Failed: Z
- Success Rate: Y/X %

## L1 Tests: [X/Y passed]
- Test 1.1: ✅/❌ [Notes]
- Test 1.2: ✅/❌ [Notes]
...

## L2 Tests: [X/Y passed]
...

## L3 Tests: [X/Y passed]
...

## L4 Tests: [X/Y passed]
...

## Performance Results
| Level | Target | Actual | Status |
|-------|--------|--------|--------|
| L1    | <5s    | Xs     | ✅/❌   |
| L2    | <8s    | Xs     | ✅/❌   |
| L3    | <10s   | Xs     | ✅/❌   |
| L4    | <12s   | Xs     | ✅/❌   |

## Issues Found
1. [Issue description]
2. [Issue description]

## Recommendations
1. [Recommendation]
2. [Recommendation]
```

---

**Ready to test?** Start with L1 tests and work your way up! 🚀
