"""
Bedrock Knowledge Base retrieval helper for DocHub AI (W7).

Handles RAG retrieval with Tenant Isolation via metadata filtering.
"""

import json
import logging
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import List, Optional
from urllib.parse import urlparse

import boto3
from botocore.config import Config as BotocoreConfig

from src.config import get_config

logger = logging.getLogger(__name__)

# Discard chunks below this relevance threshold to reduce hallucination
MIN_RELEVANCE_SCORE: float = 0.40


@dataclass
class Chunk:
    """Represents a retrieved chunk from the knowledge base."""
    text: str
    source: str
    score: float


@dataclass
class Response:
    """Represents a generated response from retrieved knowledge."""
    answer: str
    sources: List[str]
    chunks_used: List[Chunk]


def _parse_source(uri: str) -> str:
    """Safely extract filename from an S3 URI or HTTPS URL."""
    try:
        return PurePosixPath(urlparse(uri).path).name or "unknown"
    except Exception:
        return "unknown"


def _is_anthropic_model(model_id: str) -> bool:
    return "anthropic" in model_id.lower()


class RAGPipeline:
    """Handles Bedrock Knowledge Base retrieval and grounded generation."""

    def __init__(
        self,
        knowledge_base_id: Optional[str] = None,
        model_id: str = "",
    ):
        self.knowledge_base_id = knowledge_base_id
        self.model_id = model_id

        _cfg = BotocoreConfig(
            retries={"max_attempts": 3, "mode": "adaptive"},
            read_timeout=30,
            connect_timeout=5,
        )
        config = get_config()
        self.bedrock_agent_runtime = boto3.client(
            "bedrock-agent-runtime", region_name=config.AWS_REGION, config=_cfg
        )
        self.bedrock_runtime = boto3.client(
            "bedrock-runtime", region_name=config.AWS_REGION, config=_cfg
        )

    # ── Public API ─────────────────────────────────────────────────────────────

    def retrieve(self, query: str, workspace_id: str, top_k: int = 5) -> List[Chunk]:
        """
        Retrieve relevant chunks from the knowledge base.

        Args:
            query: User question or search query
            workspace_id: Tenant ID for metadata filtering
            top_k: Number of chunks to request from Bedrock

        Returns:
            Filtered list of Chunk objects (score >= MIN_RELEVANCE_SCORE)
        """
        if not self.knowledge_base_id:
            raise ValueError("knowledge_base_id is required for retrieval")

        try:
            response = self.bedrock_agent_runtime.retrieve(
                knowledgeBaseId=self.knowledge_base_id,
                retrievalQuery={"text": query},
                retrievalConfiguration={
                    "vectorSearchConfiguration": {
                        "numberOfResults": top_k,
                        "filter": {
                            "equals": {"key": "workspace_id", "value": workspace_id}
                        },
                    }
                },
            )

            chunks = []
            for result in response.get("retrievalResults", []):
                score = result.get("score", 0.0)
                if score < MIN_RELEVANCE_SCORE:
                    logger.debug("Skipping low-score chunk (%.3f < %.2f)", score, MIN_RELEVANCE_SCORE)
                    continue
                text = result.get("content", {}).get("text", "")
                uri = result.get("location", {}).get("s3Location", {}).get("uri", "")
                chunks.append(Chunk(text=text, source=_parse_source(uri), score=score))

            logger.info(
                "retrieval_done",
                extra={"workspace_id": workspace_id, "chunks_returned": len(chunks), "top_k": top_k},
            )
            return chunks

        except Exception as exc:
            raise RuntimeError(f"Failed to retrieve from Knowledge Base: {exc}") from exc

    def retrieve_and_generate(self, query: str, workspace_id: str, top_k: int = 5, **_ignored) -> Response:
        """
        Retrieve chunks then synthesize a grounded answer via Bedrock LLM.
        """
        chunks = self.retrieve(query, workspace_id, top_k)

        if not chunks:
            return Response(
                answer="I could not find relevant information in the knowledge base for your query.",
                sources=[],
                chunks_used=[],
            )

        context = self._format_context(chunks)

        try:
            request_body = self._build_model_request(context, query)
            response = self.bedrock_runtime.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body),
            )
            response_body = json.loads(response["body"].read())
            answer = self._extract_answer(response_body)
            sources = sorted({c.source for c in chunks})
            return Response(answer=answer, sources=sources, chunks_used=chunks)

        except Exception as exc:
            raise RuntimeError(f"Failed to generate grounded response: {exc}") from exc

    # ── Private helpers ────────────────────────────────────────────────────────

    def _build_model_request(self, context: str, query: str) -> dict:
        """Build Bedrock invoke_model request body based on model provider."""
        if _is_anthropic_model(self.model_id):
            return {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 2000,
                "temperature": 0.0,
                "system": self._system_prompt(),
                "messages": [
                    {"role": "user", "content": f"{context}\n\nQuestion: {query}"}
                ],
            }
        # Generic fallback for Amazon Titan / other providers
        return {
            "inputText": f"{self._system_prompt()}\n\n{context}\n\nQuestion: {query}",
            "textGenerationConfig": {"maxTokenCount": 2000, "temperature": 0.0},
        }

    def _extract_answer(self, response_body: dict) -> str:
        """Extract answer text from Bedrock response regardless of model provider."""
        # Anthropic Claude
        if "content" in response_body:
            return response_body["content"][0].get("text", "")
        # Amazon Titan
        if "results" in response_body:
            return response_body["results"][0].get("outputText", "")
        return str(response_body)

    def _format_context(self, chunks: List[Chunk]) -> str:
        """Format retrieved chunks into numbered context block."""
        lines = ["Knowledge base excerpts:\n"]
        for i, chunk in enumerate(chunks, 1):
            lines.append(f"[Source {i}: {chunk.source}]\n{chunk.text}\n")
        return "\n".join(lines)

    def _system_prompt(self) -> str:
        return (
            "You are DocHub AI, a precise document assistant for a multi-tenant platform.\n\n"
            "STRICT RULES:\n"
            "1. Answer ONLY using information from the provided knowledge base excerpts.\n"
            "2. Cite every claim using the format [Source N: filename].\n"
            "3. If the answer is not in the excerpts, respond exactly: "
            '"The information is not available in the provided documents."\n'
            "4. Never invent statistics, dates, names, or facts.\n"
            "5. Be concise and factual."
        )
