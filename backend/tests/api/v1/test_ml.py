import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from app.api.v1.ml import router
from app.core.auth import get_current_admin

app = FastAPI()

async def mock_get_current_admin():
    class MockAdmin:
        id = "admin_id"
    return MockAdmin()

app.dependency_overrides[get_current_admin] = mock_get_current_admin
app.include_router(router)

@pytest.fixture
def test_client():
    client = TestClient(app)
    return client

@pytest.fixture
def mock_ml_client(monkeypatch):
    mock = AsyncMock()
    mock.get_status.return_value = {"available": True, "train_step": 50}
    mock.toggle = AsyncMock()
    app.state.ml_client = mock
    return mock

def test_ml_status(test_client, mock_ml_client):
    response = test_client.get("/api/admin/v1/ml/status")
    assert response.status_code == 200
    assert response.json() == {"available": True, "train_step": 50}

def test_ml_toggle(test_client, mock_ml_client):
    response = test_client.post("/api/admin/v1/ml/toggle", json={"enabled": False})
    assert response.status_code == 200
    assert response.json() == {"enabled": False, "status": "ok"}
    mock_ml_client.toggle.assert_called_once_with(False)

def test_ml_status_no_client(test_client):
    if hasattr(app.state, "ml_client"):
        delattr(app.state, "ml_client")
    response = test_client.get("/api/admin/v1/ml/status")
    assert response.status_code == 503

@patch("app.api.v1.ml.is_docker_available", return_value=True, create=True)
@patch("app.api.v1.ml.get_container_status", return_value={"available": True, "container": {"id": "123"}}, create=True)
def test_container_status_docker_available(mock_get_status, mock_is_docker, test_client):
    with patch("app.services.docker_manager.is_docker_available", mock_is_docker):
        with patch("app.services.docker_manager.get_container_status", mock_get_status):
            response = test_client.get("/api/admin/v1/ml/container/status")
            assert response.status_code == 200
            assert response.json() == {"available": True, "container": {"id": "123"}}

@patch("app.api.v1.ml.is_docker_available", return_value=False, create=True)
def test_container_status_docker_unavailable(mock_is_docker, test_client):
    with patch("app.services.docker_manager.is_docker_available", mock_is_docker):
        response = test_client.get("/api/admin/v1/ml/container/status")
        assert response.status_code == 200
        assert response.json() == {"available": False, "error": "Docker not installed on host"}
