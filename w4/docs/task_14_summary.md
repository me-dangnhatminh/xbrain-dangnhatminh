# Task 14: Tool Orchestration Implementation Summary

## Overview
Successfully implemented tool orchestration for L3 (Tool-Augmented RAG) queries in the GeekBrain AI System.

## Completed Subtasks

### 14.1 ✅ Create ToolOrchestrator class
**Location**: `w4/src/orchestrator.py`

**Implementation Details**:
- Created `ToolOrchestrator` class with initialization accepting:
  - `tool_executor`: ToolExecutor instance with registered tools
  - `model_id`: Bedrock model ID (default: Claude 3.5 Sonnet v2 via cross-region inference profile)
- Collects tool definitions from all registered tools via `_format_tool_definitions()`
- Implements `process_query_with_tools()` method as main entry point
- Supports optional RAG context and chunk tracking for source citations

**Key Features**:
- Automatic tool definition formatting for Claude API
- Context integration from RAG retrieval
- Source tracking from both RAG chunks and tool results
- Error handling for tool execution failures

### 14.2 ✅ Implement tool execution loop
**Location**: `w4/src/orchestrator.py` - `ToolOrchestrator.process_query_with_tools()`

**Implementation Details**:
1. **Send query + context + tool definitions to LLM**
   - Formats initial message with context and query
   - Includes all tool definitions in Claude format
   - Uses L3 system prompt with tool selection guidance

2. **Parse LLM response for tool_use requests**
   - Checks `stop_reason` for "tool_use" or "end_turn"
   - Extracts tool_use blocks from response content
   - Handles multiple content blocks (text + tool_use)

3. **Execute requested tool with provided parameters**
   - Calls `tool_executor.execute()` with tool name and parameters
   - Tracks tools used for response metadata
   - Handles tool execution errors gracefully

4. **Send tool results back to LLM**
   - Formats tool results as tool_result content blocks
   - Maintains conversation history with assistant and user messages
   - Includes tool_use_id for proper result matching

5. **Repeat until LLM generates final answer (max 5 iterations)**
   - Implements loop with `max_iterations = 5`
   - Stops on `stop_reason == "end_turn"`
   - Returns error if max iterations exceeded
   - Tracks iteration count in response metadata

**Error Handling**:
- Missing tool_use block: Returns error message
- Tool execution failure: Passes error to LLM for graceful handling
- Unexpected stop_reason: Returns error with details
- Max iterations exceeded: Returns error message
- LLM API exceptions: Catches and returns error

### 14.3 ✅ Update system prompt for L3
**Location**: `w4/src/orchestrator.py` - `ToolOrchestrator._get_l3_system_prompt()`

**Implementation Details**:

**Tool Selection Guidance**:
- `query_database`: For historical data (Jan-Mar 2026), costs, incidents, SLA targets
- `get_service_metrics`: For current live data, real-time latency, error rate, request volume
- `get_service_status`: For current operational status (healthy/degraded/down)
- `list_services`: For listing all services in the system
- `get_incident_history`: For past incidents of a service
- `get_team_info`: For team information (lead, members, responsibilities)
- `compare_services`: For comparing metrics between multiple services
- Knowledge base: For policies, architecture, team structure, documentation

**Numerical Value Preservation**:
- Instruction: "Giữ nguyên số chính xác từ kết quả tool - không làm tròn trừ khi được yêu cầu"
- Translation: "Preserve exact numbers from tool results - don't round unless asked"

**Source Citation**:
- Tool results: "[Nguồn: Database query]" or "[Nguồn: Monitoring API]"
- Documents: "[Nguồn: document_name.md]"

**Language**: Vietnamese (unless user asks in English)

## Integration with Orchestrator

Updated `Orchestrator` class to:
1. Initialize `ToolOrchestrator` when `tool_executor` is provided
2. Implement `_process_l3()` method that:
   - Retrieves context from RAG pipeline (optional, continues if fails)
   - Calls `ToolOrchestrator.process_query_with_tools()`
   - Returns `QueryResponse` with answer, sources, tools_used, and processing_time

Also implemented `_process_l1()` and `_process_l2()` for completeness:
- L1: Simple RAG with top_k=5
- L2: Multi-source RAG with top_k=10 and conflict resolution

## Testing

### Unit Tests
**Location**: `w4/tests/unit/test_tool_orchestrator.py`

**Test Coverage**:
1. ✅ `test_tool_orchestrator_initialization` - Verifies proper initialization
2. ✅ `test_format_tool_definitions` - Verifies tool definitions formatted correctly for Claude API
3. ✅ `test_system_prompt_contains_tool_guidance` - Verifies L3 prompt has tool selection guidance
4. ✅ `test_process_query_with_direct_answer` - Tests LLM answering directly without tools
5. ✅ `test_process_query_with_tool_use` - Tests full tool execution loop

**Results**: All 5 tests passed ✅

### Integration Tests
**Location**: `w4/tests/integration/test_l3_orchestration.py`

**Test Coverage**:
1. ✅ `test_l3_orchestrator_with_mocked_components` - Tests L3 orchestration with RAG and tools
2. ✅ `test_tool_orchestrator_respects_max_iterations` - Verifies max_iterations is set correctly
3. ✅ `test_l3_processing_without_tool_executor_raises_error` - Tests error handling

**Results**: All 3 tests passed ✅

## Requirements Validation

### Requirement 7.1 ✅
"THE Developer SHALL define Tool descriptions in format LLM can understand"
- Implemented in `_format_tool_definitions()` with Claude API format

### Requirement 7.2 ✅
"THE Tool description SHALL specify Tool name, parameters, return type, and when to use"
- All tool definitions include name, description, and input_schema
- System prompt provides "when to use" guidance for each tool

### Requirement 7.5 ✅
"WHEN LLM receives a Query, THE LLM SHALL determine whether to retrieve from Knowledge_Base, invoke Tool, or both"
- System prompt provides clear guidance on tool selection
- RAG context is provided alongside tool definitions

### Requirement 7.6 ✅
"WHEN LLM generates Tool_Call, THE AI_System SHALL parse Tool_Call request"
- Implemented in tool execution loop with proper parsing of tool_use blocks

### Requirement 7.7 ✅
"THE AI_System SHALL execute requested Tool with provided parameters"
- Calls `tool_executor.execute()` with extracted parameters

### Requirement 7.8 ✅
"WHEN Tool execution completes, THE AI_System SHALL send Tool results back to LLM"
- Formats tool results as tool_result content blocks
- Maintains conversation history properly

### Requirement 7.9 ✅
"THE LLM SHALL generate final Response incorporating Tool results"
- Loop continues until LLM returns stop_reason == "end_turn"

### Requirement 7.10 ✅
"THE AI_System SHALL support multiple Tool_Calls in sequence for complex queries"
- Loop supports up to 5 iterations for sequential tool calls

### Requirement 10.5 ✅
"THE System_Prompt SHALL provide clear guidance on when to use Database Query Tool vs Service Metrics Tool"
- Detailed guidance in L3 system prompt with examples

### Requirement 10.6 ✅
"THE System_Prompt SHALL instruct LLM to use Tools for numerical data and live metrics"
- Explicit instruction: "Với câu hỏi về số liệu, BẮT BUỘC phải sử dụng tools"

### Requirement 10.9 ✅
"THE System_Prompt SHALL specify Response format and language (Vietnamese)"
- Language specified: "NGÔN NGỮ TRẢ LỜI: Tiếng Việt"
- Citation format specified for both tools and documents

## Architecture

```
User Query (L3)
    ↓
Orchestrator._process_l3()
    ↓
RAGPipeline.retrieve() [optional context]
    ↓
ToolOrchestrator.process_query_with_tools()
    ↓
┌─────────────────────────────────────┐
│  Tool Execution Loop (max 5 iter)  │
│                                     │
│  1. LLM receives:                   │
│     - Query                         │
│     - RAG context                   │
│     - Tool definitions              │
│     - System prompt                 │
│                                     │
│  2. LLM decides:                    │
│     - Answer directly? → Return     │
│     - Use tool? → Continue          │
│                                     │
│  3. Execute tool:                   │
│     - Parse tool_use block          │
│     - Call tool_executor.execute()  │
│     - Track tools_used              │
│                                     │
│  4. Send result to LLM:             │
│     - Format as tool_result         │
│     - Add to conversation history   │
│                                     │
│  5. Repeat or return final answer   │
└─────────────────────────────────────┘
    ↓
QueryResponse(answer, sources, tools_used, processing_time)
```

## Key Design Decisions

1. **Separate ToolOrchestrator class**: Keeps tool orchestration logic separate from main Orchestrator for better modularity and testability

2. **Max 5 iterations**: Prevents infinite loops while allowing complex multi-tool queries

3. **Optional RAG context**: L3 can work with or without RAG context, making it flexible for pure tool queries

4. **Graceful error handling**: Tool failures are passed to LLM for intelligent handling rather than crashing

5. **Source tracking**: Tracks both RAG sources and tool sources for comprehensive citation

6. **Vietnamese-first prompts**: System prompts in Vietnamese align with user language preference

## Files Modified

1. `w4/src/orchestrator.py` - Added ToolOrchestrator class and updated Orchestrator
2. `w4/tests/unit/test_tool_orchestrator.py` - New unit tests
3. `w4/tests/integration/test_l3_orchestration.py` - New integration tests
4. `w4/docs/task_14_summary.md` - This summary document

## Next Steps

Task 14 is complete. The system is now ready for:
- Task 14.4 (optional): Write integration tests for L3 with real queries
- Task 15: Checkpoint - L3 functional verification
- Task 16+: L4 implementation with memory

## Notes

- All tests pass successfully
- No diagnostics or errors in implementation
- Ready for integration with main API endpoint
- System prompt can be further tuned based on real-world testing
