import hashlib
import hmac
import logging
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.config import settings

logger = logging.getLogger(__name__)

ALLOWED_ORIGINS = frozenset({
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
})


class ClientOriginMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method

        if method == "OPTIONS":
            return await call_next(request)

        if path.startswith("/api/admin/v1/auth/login"):
            return await call_next(request)

        if path.startswith("/api/admin/v1"):
            return await call_next(request)

        if path in ("/", "/health"):
            return await call_next(request)

        origin = request.headers.get("origin", "")
        referer = request.headers.get("referer", "")

        if origin not in ALLOWED_ORIGINS and not any(r in referer for r in ALLOWED_ORIGINS):
            signature = request.headers.get("x-zenseo-signature", "")
            if not signature or not _verify_signature(request, signature):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Direct access denied. Use the ZenSEO admin panel.",
                )

        return await call_next(request)


def _verify_signature(request: Request, signature: str) -> bool:
    secret = settings.client_secret
    if not secret:
        return False
    timestamp = request.headers.get("x-zenseo-timestamp", "")
    path = request.url.path
    expected = hmac.new(
        secret.encode(),
        f"{path}:{timestamp}".encode(),
        hashlib.sha256,
    ).hexdigest()[:16]
    return hmac.compare_digest(expected, signature)
