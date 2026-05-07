"""
Orchestration engine for GeekBrain AI System.

This module coordinates RAG pipeline, tools, and memory management.
"""

import json
import boto3
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from rag_pipeline import RAGPipeline, Response
from tools import ToolExecutor, ToolResult, ToolDefinition
from memory import MemoryManager, ConversationTurn
from datetime import datetime


@dataclass
class QueryRequest:
    """Represents a user query request."""
    query: str
    session_id: Optional[str] = None
    level: str = "L1"  # L1, L2, L3, or L4


@dataclass
class QueryResponse:
    """Represents the system's response to a query."""
    answer: str
    sources: list
    tools_used: list
    processing_time: float
    chunks_used: list = None  # Optional: for observability logging


class Orchestrator:
    """Main orchestration engine for routing and processing queries."""
    
    def __init__(
        self,
        rag_pipeline: RAGPipeline,
        tool_executor: Optional[ToolExecutor] = None,
        memory_manager: Optional[MemoryManager] = None,
        model_id: str = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
    ):
        """
        Initialize orchestrator.
        
        Args:
            rag_pipeline: RAG pipeline instance
            tool_executor: Tool executor instance (for L3+)
            memory_manager: Memory manager instance (for L4)
            model_id: Bedrock model ID for tool orchestration
        """
        self.rag_pipeline = rag_pipeline
        self.tool_executor = tool_executor
        self.memory_manager = memory_manager
        
        # Initialize ToolOrchestrator if tool_executor is provided
        if tool_executor:
            self.tool_orchestrator = ToolOrchestrator(tool_executor, model_id)
        else:
            self.tool_orchestrator = None
    
    def process_query(self, request: QueryRequest) -> QueryResponse:
        """
        Process a user query based on the level.
        
        Args:
            request: Query request with level and session info
            
        Returns:
            QueryResponse with answer and metadata
        """
        start_time = datetime.now()
        
        if request.level == "L1":
            response = self._process_l1(request)
        elif request.level == "L2":
            response = self._process_l2(request)
        elif request.level == "L3":
            response = self._process_l3(request)
        elif request.level == "L4":
            response = self._process_l4(request)
        else:
            raise ValueError(f"Unknown level: {request.level}")
        
        processing_time = (datetime.now() - start_time).total_seconds()
        response.processing_time = processing_time
        
        return response
    
    def _process_l1(self, request: QueryRequest) -> QueryResponse:
        """Process L1 query: Simple RAG."""
        # Use RAG pipeline for L1
        rag_response = self.rag_pipeline.retrieve_and_generate(
            query=request.query,
            top_k=5,
            level="L1"
        )
        
        return QueryResponse(
            answer=rag_response.answer,
            sources=rag_response.sources,
            tools_used=[],
            processing_time=0.0,  # Will be set by process_query
            chunks_used=rag_response.chunks_used if hasattr(rag_response, 'chunks_used') else None
        )
    
    def _process_l2(self, request: QueryRequest) -> QueryResponse:
        """Process L2 query: Multi-source RAG with conflict resolution."""
        # Use RAG pipeline for L2 with higher top_k
        rag_response = self.rag_pipeline.retrieve_and_generate(
            query=request.query,
            top_k=10,
            level="L2"
        )
        
        return QueryResponse(
            answer=rag_response.answer,
            sources=rag_response.sources,
            tools_used=[],
            processing_time=0.0,  # Will be set by process_query
            chunks_used=rag_response.chunks_used if hasattr(rag_response, 'chunks_used') else None
        )
    
    def _process_l3(self, request: QueryRequest) -> QueryResponse:
        """Process L3 query: Tool-augmented RAG."""
        if not self.tool_orchestrator:
            raise ValueError("ToolOrchestrator not initialized. Provide tool_executor to use L3.")
        
        # For L3, we can optionally retrieve context from RAG
        # But for numerical queries, we should minimize RAG context to avoid confusion
        chunks = []
        context = ""
        
        # Check if query is about numerical data (should use tools primarily)
        numerical_keywords = ['cost', 'chi phí', 'latency', 'metrics', 'total', 'bao nhiêu', 'how much', 'incidents', 'sla']
        is_numerical_query = any(keyword in request.query.lower() for keyword in numerical_keywords)
        
        if not is_numerical_query:
            # For non-numerical queries, retrieve RAG context
            try:
                chunks = self.rag_pipeline.retrieve(query=request.query, top_k=5)
                context = self.rag_pipeline._format_chunks_as_context(chunks)
            except Exception:
                # If RAG fails, continue without context
                pass
        else:
            # For numerical queries, provide minimal or no RAG context
            # This forces LLM to use tools instead of trying to answer from documents
            context = "Lưu ý: Câu hỏi này yêu cầu dữ liệu số liệu chính xác. Hãy sử dụng tools để truy vấn database hoặc monitoring API."
        
        # Use ToolOrchestrator to process query with tools
        result = self.tool_orchestrator.process_query_with_tools(
            query=request.query,
            context=context,
            rag_chunks=chunks
        )
        
        return QueryResponse(
            answer=result.get("answer", ""),
            sources=result.get("sources", []),
            tools_used=result.get("tools_used", []),
            processing_time=0.0,  # Will be set by process_query
            chunks_used=None  # L3 uses tools, not RAG retrieval
        )
    
    def _process_l4(self, request: QueryRequest) -> QueryResponse:
        """
        Process L4 query: Memory-enabled multi-turn conversation.

        Flow:
        1. Load conversation history from MemoryManager
        2. Format history as context string
        3. Retrieve optional RAG context
        4. Process with ToolOrchestrator (passing memory context)
        5. Save turn to MemoryManager
        """
        if not self.memory_manager:
            raise ValueError(
                "MemoryManager not initialized. Provide memory_manager to use L4."
            )
        if not self.tool_orchestrator:
            raise ValueError(
                "ToolOrchestrator not initialized. Provide tool_executor to use L4."
            )

        # Require session_id for L4
        session_id = request.session_id
        if not session_id:
            raise ValueError(
                "session_id is required for L4 multi-turn conversations. "
                "Please include session_id in the request."
            )

        # 1. Load conversation history
        history = self.memory_manager.get_history(session_id)
        memory_context = self.memory_manager.format_for_llm(history)

        # 2. Optionally retrieve RAG context
        chunks = []
        rag_context = ""
        numerical_keywords = [
            'cost', 'chi phí', 'latency', 'metrics', 'total',
            'bao nhiêu', 'how much', 'incidents', 'sla'
        ]
        is_numerical_query = any(
            kw in request.query.lower() for kw in numerical_keywords
        )
        if not is_numerical_query:
            try:
                chunks = self.rag_pipeline.retrieve(query=request.query, top_k=5)
                rag_context = self.rag_pipeline._format_chunks_as_context(chunks)
            except Exception:
                pass

        # 3. Build combined context: memory + optional RAG
        combined_context = ""
        if memory_context:
            combined_context += memory_context + "\n"
        if rag_context:
            combined_context += rag_context + "\n"
        if is_numerical_query and not rag_context:
            combined_context += (
                "Lưu ý: Câu hỏi này yêu cầu dữ liệu số liệu chính xác. "
                "Hãy sử dụng tools để truy vấn database hoặc monitoring API.\n"
            )

        # 4. Process with ToolOrchestrator using L4 system prompt
        result = self.tool_orchestrator.process_query_with_tools(
            query=request.query,
            context=combined_context,
            rag_chunks=chunks,
            level="L4"
        )

        answer = result.get("answer", "")

        # 5. Save turn to memory
        turn = ConversationTurn(
            turn_id=len(history) + 1,
            timestamp=datetime.now(),
            query=request.query,
            response=answer,
            context_used=result.get("sources", [])
        )
        self.memory_manager.save_turn(session_id, turn)

        return QueryResponse(
            answer=answer,
            sources=result.get("sources", []),
            tools_used=result.get("tools_used", []),
            processing_time=0.0,  # Will be set by process_query
            chunks_used=chunks if chunks else None  # Add chunks for observability
        )


class ToolOrchestrator:
    """
    Tool orchestration class for L3 queries.
    
    Manages tool execution loop with LLM:
    1. Send query + context + tool definitions to LLM
    2. Check if LLM wants to use a tool (stop_reason == "tool_use")
    3. Execute the requested tool with provided parameters
    4. Send tool results back to LLM
    5. Repeat until LLM generates final answer (max 5 iterations)
    """
    
    def __init__(
        self,
        tool_executor: ToolExecutor,
        model_id: str = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
    ):
        """
        Initialize ToolOrchestrator.
        
        Args:
            tool_executor: ToolExecutor instance with registered tools
            model_id: Bedrock model ID for LLM (default: Claude 3.5 Sonnet v2 via cross-region inference profile)
        """
        self.tool_executor = tool_executor
        self.model_id = model_id
        self.bedrock_runtime = boto3.client('bedrock-runtime')
        self.max_iterations = 5
    
    def process_query_with_tools(
        self,
        query: str,
        context: str = "",
        rag_chunks: Optional[List[Any]] = None,
        level: str = "L3"
    ) -> Dict[str, Any]:
        """
        Main orchestration loop for tool-augmented queries.
        
        Flow:
        1. Send query + context + tool definitions to LLM
        2. LLM decides: answer directly OR use tool
        3. If tool_use: execute tool, send result back to LLM
        4. Repeat until LLM generates final answer (max 5 iterations)
        
        Args:
            query: User's question
            context: Additional context (e.g., from RAG retrieval)
            rag_chunks: Optional list of RAG chunks for source tracking
            
        Returns:
            Dict with answer, tools_used, sources, and metadata
        """
        # Get tool definitions for LLM
        tool_definitions = self._format_tool_definitions()
        
        # Build initial message with context
        initial_content = context if context else ""
        if initial_content:
            initial_content += "\n\n"
        initial_content += f"Câu hỏi: {query}"
        
        messages = [
            {
                "role": "user",
                "content": initial_content
            }
        ]
        
        # Track tools used and sources
        tools_used = []
        sources = []
        
        # Add RAG sources if provided
        if rag_chunks:
            sources.extend([chunk.source for chunk in rag_chunks])
        
        # Tool execution loop
        for iteration in range(self.max_iterations):
            try:
                # Choose system prompt based on level
                if level == "L4":
                    system_prompt = self._get_l4_system_prompt()
                else:
                    system_prompt = self._get_l3_system_prompt()

                # Call LLM with tool definitions
                request_body = {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 4000,
                    "temperature": 0.0,
                    "system": system_prompt,
                    "messages": messages,
                    "tools": tool_definitions
                }
                
                response = self.bedrock_runtime.invoke_model(
                    modelId=self.model_id,
                    body=json.dumps(request_body)
                )
                
                response_body = json.loads(response['body'].read())
                stop_reason = response_body.get('stop_reason')
                content = response_body.get('content', [])
                
                # Check if LLM wants to use a tool
                if stop_reason == "tool_use":
                    # Find tool_use block in content
                    tool_use_block = None
                    text_blocks = []
                    
                    for block in content:
                        if block.get('type') == 'tool_use':
                            tool_use_block = block
                        elif block.get('type') == 'text':
                            text_blocks.append(block)
                    
                    if not tool_use_block:
                        # No tool_use block found, treat as error
                        return {
                            "answer": "Lỗi: LLM yêu cầu sử dụng tool nhưng không cung cấp thông tin tool.",
                            "tools_used": tools_used,
                            "sources": sources,
                            "error": "Missing tool_use block"
                        }
                    
                    # Extract tool information
                    tool_name = tool_use_block.get('name')
                    tool_input = tool_use_block.get('input', {})
                    tool_use_id = tool_use_block.get('id')
                    
                    # Execute tool
                    tool_result = self.tool_executor.execute(tool_name, tool_input)
                    tools_used.append(tool_name)
                    
                    # Add tool result as source
                    if tool_result.success:
                        sources.append(f"{tool_name} tool")
                    
                    # Add assistant message with tool_use to conversation
                    messages.append({
                        "role": "assistant",
                        "content": content
                    })
                    
                    # Add tool result to conversation
                    tool_result_content = str(tool_result.data) if tool_result.success else f"Error: {tool_result.error}"
                    
                    messages.append({
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": tool_use_id,
                                "content": tool_result_content
                            }
                        ]
                    })
                    
                elif stop_reason == "end_turn":
                    # LLM generated final answer
                    answer_text = ""
                    for block in content:
                        if block.get('type') == 'text':
                            answer_text += block.get('text', '')
                    
                    return {
                        "answer": answer_text,
                        "tools_used": tools_used,
                        "sources": list(set(sources)),  # Remove duplicates
                        "iterations": iteration + 1
                    }
                
                else:
                    # Unexpected stop reason
                    return {
                        "answer": f"Lỗi: Stop reason không mong đợi: {stop_reason}",
                        "tools_used": tools_used,
                        "sources": sources,
                        "error": f"Unexpected stop_reason: {stop_reason}"
                    }
                    
            except Exception as e:
                return {
                    "answer": f"Lỗi khi xử lý với LLM: {str(e)}",
                    "tools_used": tools_used,
                    "sources": sources,
                    "error": str(e)
                }
        
        # Max iterations exceeded
        return {
            "answer": "Lỗi: Đã vượt quá số lần lặp tối đa (5) khi sử dụng tools.",
            "tools_used": tools_used,
            "sources": sources,
            "error": "Max iterations exceeded"
        }
    
    def _format_tool_definitions(self) -> List[Dict[str, Any]]:
        """
        Format tool definitions for Claude API.
        
        Returns:
            List of tool definitions in Claude format
        """
        tool_defs = self.tool_executor.get_tool_definitions()
        
        formatted_tools = []
        for tool_def in tool_defs:
            formatted_tools.append({
                "name": tool_def.name,
                "description": tool_def.description,
                "input_schema": tool_def.parameters
            })
        
        return formatted_tools
    
    def _get_l3_system_prompt(self) -> str:
        """
        Get system prompt for L3 with tool selection guidance.

        Returns:
            System prompt string
        """
        return self._build_system_prompt(level="L3", conversation_context="")

    def _get_l4_system_prompt(self, conversation_context: str = "") -> str:
        """
        Get system prompt for L4 with memory + pronoun resolution instructions.

        Args:
            conversation_context: Formatted conversation history string

        Returns:
            System prompt string for L4
        """
        return self._build_system_prompt(level="L4", conversation_context=conversation_context)

    def _build_system_prompt(self, level: str = "L3", conversation_context: str = "") -> str:
        """
        Build system prompt for L3 or L4.

        Args:
            level: "L3" or "L4"
            conversation_context: Formatted memory string (L4 only)

        Returns:
            System prompt string
        """
        base = """Bạn là trợ lý AI của GeekBrain, một fintech startup. 

⚠️ QUY TẮC QUAN TRỌNG NHẤT - ĐỌC KỸ:
1. Với MỌI câu hỏi về SỐ LIỆU (chi phí, cost, latency, metrics, incidents count, etc.), bạn BẮT BUỘC phải sử dụng tools
2. KHÔNG BAO GIỜ trả lời số liệu dựa trên knowledge base documents - documents chỉ chứa thông tin định tính
3. Nếu câu hỏi có từ khóa: "cost", "chi phí", "total", "how much", "bao nhiêu", "latency", "metrics", "incidents" → PHẢI dùng tool
4. Knowledge base CHỈ dùng cho: policies, team info, architecture, postmortems (không có số liệu)

CÔNG CỤ CÓ SẴN:

🔧 query_database - CHO DỮ LIỆU LỊCH SỬ (Jan-Mar 2026):
   - Chi phí theo tháng (monthly_costs table)
   - Incident history (incidents table)
   - SLA targets (sla_targets table)
   - Daily metrics (daily_metrics table)
   
   Ví dụ SQL:
   - Tổng chi phí Q1: SELECT SUM(total_cost) FROM monthly_costs WHERE service='PaymentGW' AND month IN ('2026-01','2026-02','2026-03')
   - Chi phí tháng 3: SELECT total_cost FROM monthly_costs WHERE service='PaymentGW' AND month='2026-03'
   - SLA target: SELECT latency_p99_ms FROM sla_targets WHERE service='NotificationSvc'

🔧 get_service_metrics - CHO DỮ LIỆU THỜI GIAN THỰC:
   - Current latency (p50, p95, p99)
   - Current error rate
   - Current request volume
   
🔧 get_service_status - Trạng thái service (healthy/degraded/down)

🔧 list_services - Danh sách tất cả services

🔧 get_incident_history - Lịch sử incidents

🔧 get_team_info - Thông tin team từ knowledge base

🔧 compare_services - So sánh metrics giữa services

CÁCH XỬ LÝ CÂU HỎI:

Bước 1: Phân tích câu hỏi
- Có yêu cầu số liệu? → Dùng tool (database hoặc metrics API)
- Chỉ hỏi thông tin định tính? → Dùng knowledge base context

Bước 2: Chọn tool phù hợp
- Dữ liệu lịch sử (Q1, tháng 3, Jan-Mar) → query_database
- Dữ liệu hiện tại (current, now, đang) → get_service_metrics
- So sánh với SLA → Cần cả 2 tools

Bước 3: Trả lời
- Giữ NGUYÊN số chính xác từ tool (không làm tròn)
- Trích dẫn nguồn: [Nguồn: Database query] hoặc [Nguồn: Monitoring API]

VÍ DỤ:

❌ SAI:
Q: "Chi phí PaymentGW Q1 2026 là bao nhiêu?"
A: "Theo document, chi phí đang tăng..." (KHÔNG được trả lời như vậy!)

✅ ĐÚNG:
Q: "Chi phí PaymentGW Q1 2026 là bao nhiêu?"
→ Dùng query_database với SQL: SELECT SUM(total_cost) FROM monthly_costs WHERE service='PaymentGW' AND month IN ('2026-01','2026-02','2026-03')
→ Nhận kết quả: 16500
A: "Tổng chi phí của PaymentGW trong Q1 2026 là $16,500. [Nguồn: Database query]"

NGÔN NGỮ: Tiếng Việt (trừ khi user hỏi bằng tiếng Anh)
"""

        # L4 extension: pronoun resolution
        if level == "L4":
            base += """

---
🧠 CHẾ ĐỘ L4 - MULTI-TURN CONVERSATION VỚI MEMORY:

Bạn đang xử lý hội thoại nhiều lượt. Lịch sử cuộc trò chuyện được cung cấp ở đầu context.

QUY TẮC GIẢI QUYẾT ĐẠI TỪ (Pronoun Resolution):
- Khi user dùng "nó", "its", "it", "dịch vụ đó", "that service" → xác định entity từ lịch sử hội thoại
- Khi user dùng "họ", "they", "their team", "team đó" → xác định team từ context trước
- Khi user hỏi follow-up không đề cập tên rõ ràng → suy luận từ lịch sử cuộc trò chuyện
- Nếu không thể xác định entity → hỏi lại user để làm rõ

VÍ DỤ PRONOUN RESOLUTION:

Turn 1: "Service nào có chi phí cao nhất tháng 3/2026?" → "PaymentGW ($7,500)"
Turn 2: "Tại sao chi phí của nó tăng đột biến?" 
  → "nó" = PaymentGW (từ turn 1)
  → Tìm postmortem của PaymentGW trong knowledge base
  → Trả lời dựa trên thông tin postmortem

Turn 3: "Team nào chịu trách nhiệm?"
  → Context = PaymentGW
  → Trả lời: "Team Platform, do Alex Chen lãnh đạo"

Turn 4: "Deadline review postmortem đã qua chưa?"
  → Context = PaymentGW postmortem
  → Kiểm tra deadline từ document

Bây giờ hãy xử lý câu hỏi với đầy đủ context từ lịch sử hội thoại!
"""

        return base
