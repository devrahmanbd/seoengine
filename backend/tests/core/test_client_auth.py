import pytest
import hmac
import hashlib
from fastapi import FastAPI, APIRouter, Request
from fastapi.testclient import TestClient
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.client_auth import ClientOriginMiddleware
from app.core.config import settings

app = FastAPI()

app.add_middleware(ClientOriginMiddleware)

@app.get("/api/v1/protected")
def protected_route():
    return {"status": "ok"}

@app.get("/health")
def health_route():
    return {"status": "ok"}

@app.get("/api/admin/v1/some_admin_route")
def admin_route():
    return {"status": "ok"}

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

client = TestClient(app)

def test_health_route_allowed():
    response = client.get("/health")
    assert response.status_code == 200

def test_admin_route_allowed():
    response = client.get("/api/admin/v1/some_admin_route")
    assert response.status_code == 200

def test_protected_route_allowed_origin():
    response = client.get("/api/v1/protected", headers={"origin": "http://localhost:3000"})
    assert response.status_code == 200

def test_protected_route_forbidden_origin():
    with pytest.raises(Exception) as excinfo:
        client.get("/api/v1/protected", headers={"origin": "http://evil.com"})
    assert "Direct access denied. Use the ZenSEO admin panel." in str(excinfo.value)
    # The actual exception is an HTTPException raised by the middleware
    # Fastapi TestClient raises the exception directly when raised from BaseHTTPMiddleware

def test_protected_route_valid_signature(monkeypatch):
    monkeypatch.setattr(settings, "client_secret", "test_secret")

    timestamp = "1234567890"
    path = "/api/v1/protected"
    expected_signature = hmac.new(
        "test_secret".encode(),
        f"{path}:{timestamp}".encode(),
        hashlib.sha256,
    ).hexdigest()[:16]

    response = client.get(
        "/api/v1/protected",
        headers={
            "origin": "http://evil.com",
            "x-zenseo-timestamp": timestamp,
            "x-zenseo-signature": expected_signature
        }
    )
    assert response.status_code == 200

def test_protected_route_invalid_signature(monkeypatch):
    monkeypatch.setattr(settings, "client_secret", "test_secret")

    with pytest.raises(Exception) as excinfo:
        client.get(
            "/api/v1/protected",
            headers={
                "origin": "http://evil.com",
                "x-zenseo-timestamp": "1234567890",
                "x-zenseo-signature": "invalid_sig"
            }
        )
    assert "Direct access denied. Use the ZenSEO admin panel." in str(excinfo.value)
