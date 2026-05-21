import pytest
from unittest.mock import patch, MagicMock
from app.services.docker_manager import (
    get_container_status,
    start_container,
    stop_container,
    restart_container,
    get_container_logs,
    is_docker_available,
    _find_compose_dir,
)

@pytest.fixture
def mock_docker_available():
    with patch("app.services.docker_manager.is_docker_available", return_value=True) as mock:
        yield mock

@pytest.fixture
def mock_subprocess_run():
    with patch("subprocess.run") as mock:
        yield mock

def test_get_container_status_success(mock_docker_available, mock_subprocess_run):
    mock_run_result = MagicMock()
    mock_run_result.stdout = "12345|running|running|8000/tcp|test-image\n"
    mock_run_result.stderr = ""
    mock_run_result.returncode = 0
    mock_subprocess_run.return_value = mock_run_result

    status = get_container_status()
    assert status["available"] is True
    assert status["container"]["id"] == "12345"
    assert status["container"]["status"] == "running"
    assert status["container"]["state"] == "running"

def test_get_container_status_not_found(mock_docker_available, mock_subprocess_run):
    mock_run_result = MagicMock()
    mock_run_result.stdout = ""
    mock_run_result.stderr = ""
    mock_run_result.returncode = 0
    mock_subprocess_run.return_value = mock_run_result

    status = get_container_status()
    assert status["available"] is True
    assert status["container"] is None

def test_start_container_compose(mock_docker_available, mock_subprocess_run):
    with patch("app.services.docker_manager.get_container_status", return_value={"available": True, "container": {"state": "exited"}}):
        with patch("app.services.docker_manager._find_compose_dir", return_value="/fake/dir"):
            mock_run_result = MagicMock()
            mock_run_result.stdout = "Started"
            mock_run_result.stderr = "Warning: some warning"
            mock_run_result.returncode = 0
            mock_subprocess_run.return_value = mock_run_result

            res = start_container()
            assert res["success"] is True

def test_start_container_compose_failure(mock_docker_available, mock_subprocess_run):
    with patch("app.services.docker_manager.get_container_status", return_value={"available": True, "container": {"state": "exited"}}):
        with patch("app.services.docker_manager._find_compose_dir", return_value="/fake/dir"):
            mock_run_result = MagicMock()
            mock_run_result.stdout = ""
            mock_run_result.stderr = "Error occurred"
            mock_run_result.returncode = 1
            mock_subprocess_run.return_value = mock_run_result

            res = start_container()
            assert res["success"] is False
            assert res["error"] == "Error occurred"

def test_stop_container(mock_docker_available, mock_subprocess_run):
    with patch("app.services.docker_manager.get_container_status", return_value={"available": True, "container": {"state": "running"}}):
        mock_run_result = MagicMock()
        mock_run_result.stdout = "Stopped"
        mock_run_result.stderr = ""
        mock_run_result.returncode = 0
        mock_subprocess_run.return_value = mock_run_result

        res = stop_container()
        assert res["success"] is True

def test_restart_container(mock_docker_available, mock_subprocess_run):
    mock_run_result = MagicMock()
    mock_run_result.stdout = "Restarted"
    mock_run_result.stderr = ""
    mock_run_result.returncode = 0
    mock_subprocess_run.return_value = mock_run_result

    res = restart_container()
    assert res["success"] is True

def test_get_container_logs(mock_docker_available, mock_subprocess_run):
    with patch("app.services.docker_manager.get_container_status", return_value={"available": True, "container": {"state": "running"}}):
        mock_run_result = MagicMock()
        mock_run_result.stdout = "log line 1\nlog line 2"
        mock_run_result.stderr = ""
        mock_run_result.returncode = 0
        mock_subprocess_run.return_value = mock_run_result

        res = get_container_logs()
        assert res["available"] is True
        assert len(res["logs"]) == 2
        assert res["logs"][0] == "log line 1"

def test_find_compose_dir_env_var(monkeypatch):
    monkeypatch.setenv("DOCKER_COMPOSE_PATH", "/tmp/docker-compose.yml")
    with patch("os.path.isfile", return_value=True):
        res = _find_compose_dir()
        assert res == "/tmp"

def test_find_compose_dir_warning():
    with patch("os.path.isfile", return_value=False):
        res = _find_compose_dir()
        assert res is None
