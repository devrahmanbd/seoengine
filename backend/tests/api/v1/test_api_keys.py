import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from app.api.v1.api_keys import router
from app.core.auth import get_current_admin
from app.core.database import get_db

app = FastAPI()

async def mock_get_current_admin():
    class MockAdmin:
        id = "admin_id"
    return MockAdmin()

app.dependency_overrides[get_current_admin] = mock_get_current_admin
app.include_router(router, prefix="/api-keys")

@pytest.fixture
def mock_db_session():
    mock = MagicMock()
    return mock

@pytest.fixture
def test_client(mock_db_session):
    app.dependency_overrides[get_db] = lambda: mock_db_session
    client = TestClient(app)
    return client

def test_update_api_key_is_active_string_true(test_client, mock_db_session):
    mock_key = MagicMock()
    mock_key.id = "key123"
    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_key

    response = test_client.put("/api-keys/key123", json={"isActive": "true"})
    assert response.status_code == 200
    assert mock_key.is_active is True
    mock_db_session.commit.assert_called_once()

def test_update_api_key_is_active_string_false(test_client, mock_db_session):
    mock_key = MagicMock()
    mock_key.id = "key123"
    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_key

    response = test_client.put("/api-keys/key123", json={"isActive": "False"})
    assert response.status_code == 200
    assert mock_key.is_active is False
    mock_db_session.commit.assert_called_once()

def test_update_api_key_is_active_boolean(test_client, mock_db_session):
    mock_key = MagicMock()
    mock_key.id = "key123"
    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_key

    response = test_client.put("/api-keys/key123", json={"is_active": False})
    assert response.status_code == 200
    assert mock_key.is_active is False

def test_update_api_key_not_found(test_client, mock_db_session):
    mock_db_session.query.return_value.filter.return_value.first.return_value = None

    response = test_client.put("/api-keys/key123", json={"isActive": "false"})
    assert response.status_code == 404
