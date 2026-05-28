"""
DocHub AI Backend — FastAPI entrypoint.
"""

import logging
import time

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from src.auth import get_workspace_id, verify_token
from src.config import get_config
from src.logger import setup_logging
from src.rag_pipeline import RAGPipeline

# ── Bootstrap ──────────────────────────────────────────────────────────────────
setup_logging()
logger = logging.getLogger(__name__)
config = get_config()

# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="DocHub AI Backend",
    version=config.APP_VERSION,
    description="Multi-tenant RAG backend powered by AWS Bedrock",
)

# ── Rate limiting (per IP) ─────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS (kept as-is; tighten origin list before production) ───────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Bedrock pipeline singleton ─────────────────────────────────────────────────
pipeline = RAGPipeline(
    knowledge_base_id=config.BEDROCK_KB_ID,
    model_id=config.BEDROCK_MODEL_ID,
)


# ── Schemas ────────────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000, description="User question")
    # workspace_id is now extracted from the verified JWT — not accepted from client


# ── Endpoints ──────────────────────────────────────────────────────────────────
@app.get("/health")
def health_check():
    """Liveness probe — always returns 200 if the process is up."""
    return {"status": "ok", "version": config.APP_VERSION}


@app.post("/chat")
@limiter.limit("30/minute")
def chat_with_docs(
    request: Request,                          # required by slowapi
    body: ChatRequest,
    token_payload: dict = Depends(verify_token),  # 401 if no valid JWT
):
    """
    Query the knowledge base for the authenticated tenant.

    Requires:  Authorization: Bearer <cognito_token>
    workspace_id is extracted from the JWT (custom:workspace_id or sub).
    """
    workspace_id = get_workspace_id(token_payload)

    start = time.perf_counter()
    logger.info(
        "chat_request",
        extra={
            "workspace_id": workspace_id,
            "query_len": len(body.query),
            "jwt_sub": token_payload.get("sub"),
            "jwt_custom_workspace": token_payload.get("custom:workspace_id"),
        },
    )

    try:
        response = pipeline.retrieve_and_generate(
            query=body.query,
            workspace_id=workspace_id,
            top_k=5,
        )
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            "chat_response",
            extra={
                "workspace_id": workspace_id,
                "sources_count": len(response.sources),
                "latency_ms": latency_ms,
            },
        )
        return {"answer": response.answer, "sources": response.sources}

    except RuntimeError as exc:
        logger.error("chat_error", extra={"workspace_id": workspace_id}, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

    except Exception:
        logger.error("unexpected_error", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
