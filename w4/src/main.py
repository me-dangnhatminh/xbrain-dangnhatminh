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
    level: Optional[str] = Field("L1", pattern="^(L1|L2)$", description="Query level: L1 (simple RAG) or L2 (multi-source with conflict resolution)")


class QueryResponse(BaseModel):
    """Response model for query endpoint."""
    answer: str = Field(..., description="Generated answer")
    sources: list[str] = Field(..., description="Source documents cited")
    processing_time: float = Field(..., description="Processing time in seconds")


# Initialize FastAPI app
app = FastAPI(
    title="GeekBrain AI System",
    description="AI-powered question answering system for GeekBrain fintech startup",
    version="1.0.0"
)

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

rag_pipeline = RAGPipeline(
    knowledge_base_id=KNOWLEDGE_BASE_ID,
    model_id=MODEL_ID
)


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
    Query endpoint for L1 (Simple RAG) and L2 (Multi-Source RAG).
    
    Accepts a user query and returns an AI-generated answer with source citations.
    
    Args:
        request: QueryRequest with query string, optional top_k parameter, and optional level parameter
        
    Returns:
        QueryResponse with answer, sources, and processing time
        
    Raises:
        HTTPException: If query processing fails
    """
    start_time = time.time()
    
    try:
        # Validate that knowledge base is configured
        if not KNOWLEDGE_BASE_ID:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Knowledge Base is not configured. Please set BEDROCK_KB_ID environment variable."
            )
        
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
        
        # Return response
        return QueryResponse(
            answer=response.answer,
            sources=response.sources,
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


if __name__ == "__main__":
    import uvicorn
    
    # Run the application
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=True
    )
