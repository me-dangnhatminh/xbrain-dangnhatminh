"""
JWT Authentication for DocHub AI.
Verifies AWS Cognito tokens and extracts workspace identity.
"""

import logging
import time

import httpx
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from src.config import get_config

logger = logging.getLogger(__name__)
_bearer = HTTPBearer()

# ── JWKS in-memory cache ───────────────────────────────────────────────────────
_jwks_cache: dict = {"keys": [], "fetched_at": 0.0}
_JWKS_TTL_SECONDS = 3600  # refresh every hour


def _get_jwks() -> list:
    """Fetch Cognito JWKS with in-memory TTL cache."""
    config = get_config()
    now = time.monotonic()

    if now - _jwks_cache["fetched_at"] < _JWKS_TTL_SECONDS and _jwks_cache["keys"]:
        return _jwks_cache["keys"]

    jwks_url = (
        f"https://cognito-idp.{config.AWS_REGION}.amazonaws.com"
        f"/{config.COGNITO_USER_POOL_ID}/.well-known/jwks.json"
    )
    try:
        resp = httpx.get(jwks_url, timeout=10)
        resp.raise_for_status()
        keys = resp.json().get("keys", [])
        _jwks_cache["keys"] = keys
        _jwks_cache["fetched_at"] = now
        logger.info("Refreshed Cognito JWKS (%d keys)", len(keys))
        return keys
    except Exception as exc:
        logger.error("Failed to fetch JWKS: %s", exc)
        if _jwks_cache["keys"]:
            logger.warning("Using stale JWKS cache as fallback")
            return _jwks_cache["keys"]
        raise HTTPException(status_code=503, detail="Authentication service unavailable")


def verify_token(
    credentials: HTTPAuthorizationCredentials = Security(_bearer),
) -> dict:
    """
    FastAPI dependency — verifies a Cognito Bearer JWT.

    Returns:
        Decoded token payload dict.
    Raises:
        HTTPException 401 on invalid/expired token.
    """
    config = get_config()
    token = credentials.credentials

    try:
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")

        keys = _get_jwks()
        rsa_key = next(
            (
                {"kty": k["kty"], "kid": k["kid"], "use": k["use"], "n": k["n"], "e": k["e"]}
                for k in keys
                if k["kid"] == kid
            ),
            None,
        )

        if not rsa_key:
            raise HTTPException(status_code=401, detail="Token signing key not recognized")

        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            options={"verify_aud": False},  # Cognito access tokens omit 'aud'
        )

        # For access tokens: validate client_id claim
        token_client = payload.get("client_id") or payload.get("aud")
        if token_client and token_client != config.COGNITO_CLIENT_ID:
            raise HTTPException(status_code=401, detail="Token audience mismatch")

        return payload

    except HTTPException:
        raise
    except JWTError as exc:
        logger.warning("JWT verification failed: %s", exc)
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    except Exception as exc:
        logger.error("Unexpected auth error: %s", exc, exc_info=True)
        raise HTTPException(status_code=401, detail="Authentication failed")


def get_user_id(payload: dict) -> str:
    """
    Extract user_id (sub) from verified JWT payload.
    Raises HTTPException 401 if not present.
    """
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="User identity not found in token claims.",
        )
    return user_id
