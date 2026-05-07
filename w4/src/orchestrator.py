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
            processing_time=0.0  # Will be set by process_query
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
            processing_time=0.0  # Will be set by process_query
        )
    
    def _process_l3(self, request: QueryRequest) -> QueryResponse:
        """Process L3 query: Tool-augmented RAG."""
        if not self.tool_orchestrator:
            raise ValueError("ToolOrchestrator not initialized. Provide tool_executor to use L3.")
        
        # First, retrieve context from RAG (optional but helpful)
        try:
            chunks = self.rag_pipeline.retrieve(query=request.query, top_k=5)
            context = self.rag_pipeline._format_chunks_as_context(chunks)
        except Exception:
            # If RAG fails, continue without context
            chunks = []
            context = ""
        
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
            processing_time=0.0  # Will be set by process_query
        )
    
    def _process_l4(self, request: QueryRequest) -> QueryResponse:
        """Process L4 query: Memory-enabled multi-turn conversation."""
        # TODO: Implement L4 processing with memory
        raise NotImplementedError("L4 processing not yet implemented")


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
        rag_chunks: Optional[List[Any]] = None
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
                # Call LLM with tool definitions
                request_body = {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 4000,
                    "temperature": 0.0,
                    "system": self._get_l3_system_prompt(),
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
        return """Bạn là trợ lý AI của GeekBrain, một fintech startup. Bạn có thể trả lời câu hỏi bằng cách sử dụng:
1. Thông tin từ cơ sở tri thức (knowledge base documents) - cho policies, architecture, team info
2. Database queries - cho dữ liệu lịch sử (historical costs, incidents, SLA targets, daily metrics)
3. Monitoring API - cho trạng thái hệ thống hiện tại và metrics thời gian thực

HƯỚNG DẪN CHỌN TOOL:
- Sử dụng query_database cho:
  * Dữ liệu lịch sử (Jan-Mar 2026)
  * Chi phí chính xác, incident records, SLA targets
  * Câu hỏi như "Chi phí của X trong Q1 là bao nhiêu?" hoặc "Y có bao nhiêu incidents?"

- Sử dụng get_service_metrics cho:
  * Dữ liệu thời gian thực (hiện tại)
  * Latency, error rate, request volume đang diễn ra
  * Câu hỏi như "Latency hiện tại của X là bao nhiêu?" hoặc "Y có healthy không?"

- Sử dụng get_service_status cho:
  * Trạng thái hoạt động hiện tại của service (healthy/degraded/down)

- Sử dụng list_services cho:
  * Danh sách tất cả services trong hệ thống

- Sử dụng get_incident_history cho:
  * Lịch sử incidents của một service cụ thể

- Sử dụng get_team_info cho:
  * Thông tin về team (lead, members, responsibilities)

- Sử dụng compare_services cho:
  * So sánh metrics giữa nhiều services

- Sử dụng thông tin từ knowledge base (đã được cung cấp trong context) cho:
  * Company policies, team structure, architecture
  * Postmortem details, runbooks, documentation
  * Câu hỏi như "Ai là lead của Team X?" hoặc "Deployment policy là gì?"

QUY TẮC QUAN TRỌNG:
- Với câu hỏi về số liệu, BẮT BUỘC phải sử dụng tools - không được đoán hoặc ước lượng
- Giữ nguyên số chính xác từ kết quả tool - không làm tròn trừ khi được yêu cầu
- Nếu tool thất bại, giải thích lỗi và đề xuất phương án thay thế
- Có thể sử dụng nhiều tools liên tiếp nếu cần

TRÍCH DẪN NGUỒN:
- Trích dẫn kết quả tool: [Nguồn: Database query] hoặc [Nguồn: Monitoring API]
- Trích dẫn documents: [Nguồn: document_name.md]

NGÔN NGỮ TRẢ LỜI: Tiếng Việt (trừ khi user hỏi bằng tiếng Anh)

Hãy phân tích câu hỏi cẩn thận và quyết định tool nào phù hợp nhất để trả lời chính xác.
"""
