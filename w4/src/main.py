"""
FastAPI application for GeekBrain AI System.

This module provides the REST API endpoints for querying the AI system.
"""

import os
import time
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from rag_pipeline import RAGPipeline
from orchestrator import Orchestrator, QueryRequest as OrchestratorQueryRequest
from tools import ToolExecutor, DatabaseQueryTool, ServiceMetricsTool, ServiceStatusTool, ListServicesTool, IncidentHistoryTool, TeamInfoTool, CompareServicesTool
from memory import WindowMemory, DynamoDBMemory
from event_logger import event_logger

# Load environment variables from .env file
# Look for .env in multiple locations: current dir, parent dir, and root
env_paths = [
    Path(".env"),                    # w4/src/.env
    Path("../.env"),                 # w4/.env
    Path("../../.env"),              # root .env
]

for env_path in env_paths:
    if env_path.exists():
        load_dotenv(env_path)
        break
else:
    # If no .env found, just load from default location
    load_dotenv()


# Pydantic models for request/response
class QueryRequest(BaseModel):
    """Request model for query endpoint."""
    query: str = Field(..., min_length=1, description="User's question")
    top_k: Optional[int] = Field(None, ge=1, le=20, description="Number of chunks to retrieve (default: 5 for L1, 10 for L2)")
    level: Optional[str] = Field("L1", pattern="^(L1|L2|L3|L4)$", description="Query level: L1 (simple RAG), L2 (multi-source), L3 (tool-augmented), L4 (memory-enabled)")
    session_id: Optional[str] = Field(None, description="Session ID for L4 multi-turn conversations")


class QueryResponse(BaseModel):
    """Response model for query endpoint."""
    answer: str = Field(..., description="Generated answer")
    sources: list[str] = Field(..., description="Source documents cited")
    tools_used: list[str] = Field(default_factory=list, description="Tools used for L3 queries")
    processing_time: float = Field(..., description="Processing time in seconds")


# Initialize FastAPI app
app = FastAPI(
    title="GeekBrain AI System",
    description="AI-powered question answering system for GeekBrain fintech startup",
    version="1.0.0"
)

@app.on_event("startup")
async def startup_event():
    """Launch the observability dashboard (Bonus A) inside the same process."""
    import asyncio
    import uvicorn
    from dashboard import app as dashboard_app
    
    # Run dashboard on port 8002 in background
    config = uvicorn.Config(dashboard_app, host="0.0.0.0", port=8002, log_level="warning")
    server = uvicorn.Server(config)
    asyncio.create_task(server.serve())
    print("✅ Observability Dashboard auto-started on http://localhost:8002")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize RAG Pipeline
# Get configuration from environment variables
KNOWLEDGE_BASE_ID = os.getenv("BEDROCK_KB_ID")
MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-3-5-haiku-20241022-v1:0")
_DEFAULT_DB_PATH = str(Path(__file__).resolve().parent.parent / "geekbrain.db")
DB_PATH = os.getenv("DB_PATH", _DEFAULT_DB_PATH)
MONITORING_API_URL = os.getenv("MONITORING_API_URL", "http://localhost:8000")
DYNAMODB_TABLE = os.getenv("DYNAMODB_TABLE", "")
DYNAMODB_REGION = os.getenv("DYNAMODB_REGION") or os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION")

rag_pipeline = RAGPipeline(
    knowledge_base_id=KNOWLEDGE_BASE_ID,
    model_id=MODEL_ID
)

# Initialize Tool Executor for L3
tool_executor = None
orchestrator = None

try:
    print(f"📂 DB_PATH = {DB_PATH}")
    print(f"   exists={os.path.exists(DB_PATH)}, size={os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 'N/A'}")
    
    # Validate the database is not empty
    if os.path.exists(DB_PATH) and os.path.getsize(DB_PATH) == 0:
        print(f"⚠️  WARNING: Database file is empty (0 bytes)! Removing and looking for real one...")
        os.remove(DB_PATH)
    
    if not os.path.exists(DB_PATH) or os.path.getsize(DB_PATH) == 0:
        # Try to find the real database
        alt_paths = [
            str(Path(__file__).resolve().parent.parent / "geekbrain.db"),
            str(Path(__file__).resolve().parent / ".." / "geekbrain.db"),
        ]
        for alt in alt_paths:
            if os.path.exists(alt) and os.path.getsize(alt) > 0:
                DB_PATH = alt
                print(f"✅ Found valid database at: {DB_PATH} ({os.path.getsize(DB_PATH)} bytes)")
                break
    
    # Initialize tools
    db_tool = DatabaseQueryTool(db_path=DB_PATH)
    metrics_tool = ServiceMetricsTool(api_base_url=MONITORING_API_URL)
    status_tool = ServiceStatusTool(api_base_url=MONITORING_API_URL)
    list_services_tool = ListServicesTool(api_base_url=MONITORING_API_URL)
    incident_tool = IncidentHistoryTool(db_path=DB_PATH)
    team_info_tool = TeamInfoTool(rag_pipeline=rag_pipeline)
    compare_tool = CompareServicesTool(metrics_tool=metrics_tool)
    
    # Register all tools
    tool_executor = ToolExecutor()
    tool_executor.register_tool("query_database", db_tool)
    tool_executor.register_tool("get_service_metrics", metrics_tool)
    tool_executor.register_tool("get_service_status", status_tool)
    tool_executor.register_tool("list_services", list_services_tool)
    tool_executor.register_tool("get_incident_history", incident_tool)
    tool_executor.register_tool("get_team_info", team_info_tool)
    tool_executor.register_tool("compare_services", compare_tool)
    
    # Verify DB tool works at startup
    test_result = db_tool.execute_query("SELECT COUNT(*) as cnt FROM monthly_costs")
    print(f"   DB test query: {test_result}")
    
    # Initialize Orchestrator with RAG, tools, and memory (L4)
    # Use DynamoDB if configured, otherwise fall back to in-memory WindowMemory
    memory_manager = None
    if DYNAMODB_TABLE:
        try:
            memory_manager = DynamoDBMemory(
                table_name=DYNAMODB_TABLE,
                window_size=5,
                ttl_days=30,
                region_name=DYNAMODB_REGION,
            )
            print(f"✅ DynamoDBMemory initialized: table={DYNAMODB_TABLE}")
        except Exception as e:
            print(f"⚠️  DynamoDB not available ({e}), falling back to WindowMemory")
            memory_manager = WindowMemory(window_size=5)
    else:
        memory_manager = WindowMemory(window_size=5)
        print("ℹ️  Using in-memory WindowMemory (set DYNAMODB_TABLE to enable persistence)")

    orchestrator = Orchestrator(
        rag_pipeline=rag_pipeline,
        tool_executor=tool_executor,
        memory_manager=memory_manager,
        model_id=MODEL_ID
    )
    
    print("✅ Orchestrator initialized with 7 tools (L3) + WindowMemory (L4)")
    
except Exception as e:
    print(f"⚠️  Warning: Could not initialize tools for L3: {e}")
    print("   L3/L4 queries will not be available")
    # Continue without L3/L4 support


@app.get("/")
async def root():
    """Root endpoint - health check."""
    return {
        "service": "GeekBrain AI System",
        "status": "healthy",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "knowledge_base_configured": KNOWLEDGE_BASE_ID is not None
    }


@app.post("/query", response_model=QueryResponse, status_code=status.HTTP_200_OK)
async def query_endpoint(request: QueryRequest):
    """
    Query endpoint for L1-L4 queries.
    
    - L1: Simple RAG from Knowledge Base
    - L2: Multi-Source RAG with conflict resolution
    - L3: Tool-Augmented RAG (database + monitoring API)
    - L4: Memory-Enabled RAG (multi-turn conversations)
    
    Args:
        request: QueryRequest with query string, level, and optional parameters
        
    Returns:
        QueryResponse with answer, sources, tools_used, and processing time
        
    Raises:
        HTTPException: If query processing fails
    """
    start_time = time.time()
    query_id = event_logger.new_query_id()
    event_logger.log_query_received(query_id, request.query, request.level or "L1", request.session_id)
    
    try:
        # Validate that knowledge base is configured
        if not KNOWLEDGE_BASE_ID:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Knowledge Base is not configured. Please set BEDROCK_KB_ID environment variable."
            )
        
        # Check if L3/L4 is requested but orchestrator is not available
        if request.level in ["L3", "L4"] and orchestrator is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"{request.level} is not available. Tools or memory not initialized."
            )
        
        # Validate session_id for L4
        if request.level == "L4" and not request.session_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="session_id is required for L4 multi-turn conversations."
            )
        
        # Route to appropriate handler based on level
        if request.level in ["L3", "L4"]:
            # Use Orchestrator for L3 and L4
            orchestrator_request = OrchestratorQueryRequest(
                query=request.query,
                session_id=request.session_id,
                level=request.level
            )
            
            response = orchestrator.process_query(orchestrator_request)
            
            processing_time = round(response.processing_time, 3)
            
            # Log retrieval chunks if available (L4 RAG queries)
            if response.chunks_used:
                event_logger.log_retrieval(query_id, [
                    {"text": c.text, "source": c.source, "score": c.score}
                    for c in response.chunks_used
                ])
            
            # Log tool executions (if any)
            for tool_name in response.tools_used:
                event_logger.log_tool_call(
                    query_id, 
                    tool_name, 
                    {"note": "Tool was executed by orchestrator"},
                    "Success",
                    True
                )
            
            # Log memory loading for L4
            if request.level == "L4" and request.session_id:
                # Estimate memory turns from response (orchestrator doesn't expose this)
                event_logger.log_memory_loaded(query_id, request.session_id, 0)
            
            event_logger.log_response_generated(
                query_id, response.answer, response.processing_time, response.tools_used
            )
            
            return QueryResponse(
                answer=response.answer,
                sources=response.sources,
                tools_used=response.tools_used,
                processing_time=processing_time
            )
        
        else:
            # Use RAG Pipeline directly for L1 and L2
            # Determine top_k based on level if not explicitly provided
            top_k = request.top_k
            if top_k is None:
                # Default: 5 for L1, 10 for L2
                top_k = 10 if request.level == "L2" else 5
            
            # Call RAG pipeline to retrieve and generate response
            response = rag_pipeline.retrieve_and_generate(
                query=request.query,
                top_k=top_k,
                level=request.level
            )
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Log retrieval chunks
            event_logger.log_retrieval(query_id, [
                {"text": c.text, "source": c.source, "score": c.score}
                for c in response.chunks_used
            ])
            event_logger.log_response_generated(
                query_id, response.answer, processing_time, []
            )
            
            # Return response
            return QueryResponse(
                answer=response.answer,
                sources=response.sources,
                tools_used=[],
                processing_time=round(processing_time, 3)
            )
        
    except ValueError as e:
        # Handle validation errors
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid request: {str(e)}"
        )
        
    except RuntimeError as e:
        # Handle Bedrock API failures
        error_message = str(e)
        
        # Check for specific error types
        if "retrieve" in error_message.lower():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Knowledge Base retrieval failed: {error_message}"
            )
        elif "generate" in error_message.lower():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Response generation failed: {error_message}"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Query processing failed: {error_message}"
            )
        
    except Exception as e:
        # Handle unexpected errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}"
        )


# ── Bonus B: Investigation Endpoint ─────────────────────────────
investigation_agent = None
try:
    from investigation import InvestigationAgent
    if orchestrator:
        investigation_agent = InvestigationAgent(orchestrator)
        print("✅ InvestigationAgent initialized (Bonus B)")
except Exception as e:
    print(f"⚠️  InvestigationAgent not available: {e}")


class InvestigationRequest(BaseModel):
    """Request model for investigation endpoint."""
    query: str = Field(..., min_length=1, description="Investigation question")
    service_name: Optional[str] = Field(None, description="Service to investigate (auto-detected if omitted)")


@app.post("/investigate")
async def investigate_endpoint(request: InvestigationRequest):
    """
    Investigation endpoint (Bonus B) — multi-step agent reasoning.

    Runs plan-gather-analyze-report workflow and returns structured report.
    """
    if investigation_agent is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Investigation agent not available"
        )

    try:
        report = investigation_agent.investigate(
            query=request.query,
            service_name=request.service_name
        )
        return {
            "service": report.service_name,
            "report_markdown": report.to_markdown(),
            "issues_count": len(report.issues_found),
            "recommendations_count": len(report.recommendations),
            "reasoning_steps": len(report.reasoning_steps),
            "total_time_ms": round(report.total_time_ms, 1),
            "issues": report.issues_found,
            "recommendations": report.recommendations,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Investigation failed: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    
    # Run the application
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=True
    )
