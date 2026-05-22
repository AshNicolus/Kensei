import hashlib
import secrets
from typing import Optional

from fastapi import Header, HTTPException, status

from backend.core.config import settings


def generate_api_key(prefix: str = "ks") -> str:
    return f"{prefix}_{secrets.token_urlsafe(24)}"


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def verify_api_key(provided: Optional[str], expected_hash: Optional[str]) -> bool:
    if not provided or not expected_hash:
        return False
    return secrets.compare_digest(hash_token(provided), expected_hash)


async def require_api_key(
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
) -> str:
    if settings.ENV == "development":
        return x_api_key or "dev"
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
        )
    return x_api_key
