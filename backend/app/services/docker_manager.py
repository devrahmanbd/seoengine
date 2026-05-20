import shutil
import subprocess
import logging

logger = logging.getLogger(__name__)

ML_CONTAINER_NAME = "zenseo-ml"


def _docker_cmd(args: list[str]) -> tuple[str, str]:
    try:
        result = subprocess.run(
            ["docker"] + args,
            capture_output=True,
            text=True,
            timeout=15,
        )
        return result.stdout.strip(), result.stderr.strip()
    except FileNotFoundError:
        return "", "docker command not found"
    except subprocess.TimeoutExpired:
        return "", "command timed out"


def is_docker_available() -> bool:
    return shutil.which("docker") is not None


def get_container_status() -> dict:
    if not is_docker_available():
        return {"available": False, "error": "Docker not found on host"}

    try:
        stdout, stderr = _docker_cmd(["ps", "-a", "--filter", f"name={ML_CONTAINER_NAME}", "--format", "{{.ID}}|{{.Status}}|{{.State}}|{{.Ports}}|{{.Image}}"])
    except Exception as e:
        return {"available": False, "error": str(e)}

    if not stdout:
        return {
            "available": True,
            "container": None,
            "message": f"No container named '{ML_CONTAINER_NAME}' found",
        }

    parts = stdout.split("|")
    container_info = {
        "id": parts[0] if len(parts) > 0 else "",
        "status": parts[1] if len(parts) > 1 else "unknown",
        "state": parts[2] if len(parts) > 2 else "unknown",
        "ports": parts[3] if len(parts) > 3 else "",
        "image": parts[4] if len(parts) > 4 else "",
    }
    return {"available": True, "container": container_info}


def start_container() -> dict:
    if not is_docker_available():
        return {"success": False, "error": "Docker not found"}

    cfg = get_container_status()
    if cfg.get("container") and cfg["container"].get("state") == "running":
        return {"success": True, "message": "Container already running"}

    try:
        compose_dir = _find_compose_dir()
        if compose_dir:
            stdout, stderr = _docker_cmd(["compose", "-f", "docker-compose.yml", "up", "-d", "ml-service"])
            return {"success": True, "message": "Container started via Docker Compose"} if not stderr else {"success": False, "error": stderr}
        else:
            stdout, stderr = _docker_cmd(["start", ML_CONTAINER_NAME])
            return {"success": True, "message": "Container started"} if not stderr else {"success": False, "error": stderr}
    except Exception as e:
        return {"success": False, "error": str(e)}


def stop_container() -> dict:
    if not is_docker_available():
        return {"success": False, "error": "Docker not found"}

    cfg = get_container_status()
    if not cfg.get("container") or cfg["container"].get("state") != "running":
        return {"success": True, "message": "Container already stopped"}

    try:
        stdout, stderr = _docker_cmd(["stop", ML_CONTAINER_NAME])
        return {"success": True, "message": "Container stopped"} if not stderr else {"success": False, "error": stderr}
    except Exception as e:
        return {"success": False, "error": str(e)}


def restart_container() -> dict:
    if not is_docker_available():
        return {"success": False, "error": "Docker not found"}

    try:
        stdout, stderr = _docker_cmd(["restart", ML_CONTAINER_NAME])
        return {"success": True, "message": "Container restarted"} if not stderr else {"success": False, "error": stderr}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_container_logs(tail: int = 100) -> dict:
    if not is_docker_available():
        return {"available": False, "error": "Docker not found"}

    cfg = get_container_status()
    if not cfg.get("container"):
        return {"available": True, "logs": [], "message": "Container not created yet"}

    try:
        stdout, stderr = _docker_cmd(["logs", "--tail", str(tail), ML_CONTAINER_NAME])
        lines = stdout.split("\n") if stdout else []
        return {"available": True, "logs": lines, "error": stderr or ""}
    except Exception as e:
        return {"available": False, "error": str(e)}


def _find_compose_dir() -> str | None:
    import os
    candidates = [os.getcwd(), os.path.join(os.getcwd(), "..")]
    for d in candidates:
        if os.path.isfile(os.path.join(d, "docker-compose.yml")):
            return d
    return None
