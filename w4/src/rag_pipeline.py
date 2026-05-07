"""
RAG Pipeline module for GeekBrain AI System.

This module handles retrieval-augmented generation using Amazon Bedrock Knowledge Base.
"""

import json
import boto3
from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class Chunk:
    """Represents a retrieved chunk from knowledge base."""
    text: str
    source: str
    score: float


@dataclass
class Response:
    """Represents a response from the AI system."""
    answer: str
    sources: List[str]
    chunks_used: List[Chunk]


class RAGPipeline:
    """Handles retrieval and generation for L1-L2 queries."""
    
    def __init__(self, knowledge_base_id: str = None, model_id: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"):
        """
        Initialize RAG pipeline.
        
        Args:
            knowledge_base_id: Bedrock Knowledge Base ID
            model_id: Bedrock model ID for LLM generation
        """
        self.knowledge_base_id = knowledge_base_id
        self.model_id = model_id
        
        # Initialize Bedrock clients
        self.bedrock_agent_runtime = boto3.client('bedrock-agent-runtime')
        self.bedrock_runtime = boto3.client('bedrock-runtime')
    
    def retrieve(self, query: str, top_k: int = 5) -> List[Chunk]:
        """
        Retrieve relevant chunks from knowledge base.
        
        Args:
            query: User's question
            top_k: Number of chunks to retrieve (5 for L1, 10 for L2)
            
        Returns:
            List of Chunk objects with text, source, and score
        """
        if not self.knowledge_base_id:
            raise ValueError("knowledge_base_id is required for retrieval")
        
        try:
            # Call Bedrock Knowledge Base retrieve API
            response = self.bedrock_agent_runtime.retrieve(
                knowledgeBaseId=self.knowledge_base_id,
                retrievalQuery={'text': query},
                retrievalConfiguration={
                    'vectorSearchConfiguration': {
                        'numberOfResults': top_k
                    }
                }
            )
            
            # Parse response and extract chunks
            chunks = []
            for result in response.get('retrievalResults', []):
                # Extract text content
                text = result.get('content', {}).get('text', '')
                
                # Extract source from S3 location
                location = result.get('location', {})
                s3_location = location.get('s3Location', {})
                source_uri = s3_location.get('uri', 'unknown')
                
                # Extract just the filename from S3 URI
                source = source_uri.split('/')[-1] if source_uri != 'unknown' else 'unknown'
                
                # Extract relevance score
                score = result.get('score', 0.0)
                
                chunks.append(Chunk(
                    text=text,
                    source=source,
                    score=score
                ))
            
            return chunks
            
        except Exception as e:
            raise RuntimeError(f"Failed to retrieve from Knowledge Base: {str(e)}")
    
    def retrieve_and_generate(self, query: str, top_k: int = 5) -> Response:
        """
        Retrieve chunks and generate response using LLM.
        
        Args:
            query: User's question
            top_k: Number of chunks to retrieve
            
        Returns:
            Response object with answer and source citations
        """
        # Step 1: Retrieve relevant chunks
        chunks = self.retrieve(query, top_k)
        
        if not chunks:
            return Response(
                answer="Xin lỗi, tôi không tìm thấy thông tin liên quan trong cơ sở tri thức.",
                sources=[],
                chunks_used=[]
            )
        
        # Step 2: Format chunks into context string with sources
        context = self._format_chunks_as_context(chunks)
        
        # Step 3: Construct system prompt for L1
        system_prompt = self._get_l1_system_prompt()
        
        # Step 4: Call Bedrock InvokeModel API with Claude Sonnet
        try:
            # Prepare the request body for Claude
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 2000,
                "temperature": 0.0,
                "system": system_prompt,
                "messages": [
                    {
                        "role": "user",
                        "content": f"{context}\n\nCâu hỏi: {query}"
                    }
                ]
            }
            
            # Invoke the model
            response = self.bedrock_runtime.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body)
            )
            
            # Parse response
            response_body = json.loads(response['body'].read())
            answer = response_body.get('content', [{}])[0].get('text', '')
            
            # Extract unique sources from chunks
            sources = list(set(chunk.source for chunk in chunks))
            
            return Response(
                answer=answer,
                sources=sources,
                chunks_used=chunks
            )
            
        except Exception as e:
            raise RuntimeError(f"Failed to generate response: {str(e)}")
    
    def _format_chunks_as_context(self, chunks: List[Chunk]) -> str:
        """
        Format retrieved chunks into context string for LLM.
        
        Args:
            chunks: List of retrieved chunks
            
        Returns:
            Formatted context string
        """
        context = "Thông tin từ cơ sở tri thức:\n\n"
        
        for i, chunk in enumerate(chunks, 1):
            context += f"[Nguồn {i}: {chunk.source}]\n"
            context += f"{chunk.text}\n\n"
        
        return context
    
    def _get_l1_system_prompt(self) -> str:
        """
        Get system prompt for L1 (Simple RAG).
        
        Returns:
            System prompt string
        """
        return """Bạn là trợ lý AI của GeekBrain, một fintech startup. Nhiệm vụ của bạn là trả lời câu hỏi dựa trên thông tin được cung cấp từ cơ sở tri thức.

Quy tắc quan trọng:
1. CHỈ sử dụng thông tin từ các nguồn được cung cấp để trả lời
2. BẮT BUỘC phải trích dẫn nguồn trong câu trả lời (ví dụ: "theo team_platform.md" hoặc "từ deployment_policy.md")
3. Trả lời bằng tiếng Việt
4. Nếu thông tin không có trong các nguồn được cung cấp, hãy nói rõ "Thông tin này không có trong cơ sở tri thức"
5. Trả lời ngắn gọn, chính xác và trực tiếp

Ví dụ câu trả lời tốt:
"Theo team_platform.md, Team Platform lead là Alex Chen."
"Từ deployment_policy.md, cửa sổ deployment freeze là từ thứ Sáu 18:00 đến thứ Hai 08:00."
"""
