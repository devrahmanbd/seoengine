import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from app.api.v1.websites import router
from app.core.auth import get_current_admin
from app.core.database import get_db
from app.core.db_models import Website

app = FastAPI()

async def mock_get_current_admin():
    class MockAdmin:
        id = "admin_id"
    return MockAdmin()

app.dependency_overrides[get_current_admin] = mock_get_current_admin
app.include_router(router, prefix="/websites")

@pytest.fixture
def mock_db_session():
    mock = MagicMock()
    return mock

@pytest.fixture
def test_client(mock_db_session):
    app.dependency_overrides[get_db] = lambda: mock_db_session
    client = TestClient(app)
    return client

def test_list_websites_with_status_filter(test_client, mock_db_session):
    mock_query = MagicMock()
    mock_db_session.query.return_value = mock_query

    mock_filter_query = MagicMock()
    mock_query.filter.return_value = mock_filter_query

    mock_count_query = MagicMock()
    mock_filter_query.count.return_value = 1

    mock_limit_query = MagicMock()
    mock_filter_query.offset.return_value.limit.return_value.all.return_value = [
        Website(id="web1", status="connected")
    ]

    response = test_client.get("/websites?status=connected")
    assert response.status_code == 200

    mock_query.filter.assert_called_once()
    filter_args = mock_query.filter.call_args[0]

    # Check if we are filtering by Website.status
    assert str(filter_args[0].left) == "websites.status"

def test_list_websites_without_status_filter(test_client, mock_db_session):
    mock_query = MagicMock()
    mock_db_session.query.return_value = mock_query

    mock_query.count.return_value = 1
    mock_query.offset.return_value.limit.return_value.all.return_value = [
        Website(id="web1", status="connected")
    ]

    response = test_client.get("/websites")
    assert response.status_code == 200
    mock_query.filter.assert_not_called()

def test_list_websites_with_invalid_status_filter(test_client, mock_db_session):
    mock_query = MagicMock()
    mock_db_session.query.return_value = mock_query

    mock_filter_query = MagicMock()
    mock_query.filter.return_value = mock_filter_query
    mock_filter_query.count.return_value = 0
    mock_filter_query.offset.return_value.limit.return_value.all.return_value = []

    response = test_client.get("/websites?status=invalid_status")
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 0
