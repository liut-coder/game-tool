#!/usr/bin/env python3
from __future__ import annotations

import json
import mimetypes
import os
import secrets
import shutil
import subprocess
import threading
import time
import urllib.parse
from http import HTTPStatus
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
TOKEN_FILE = DATA_DIR / "admin_token"

DOCKER_DIR = Path(os.environ.get("GAME_TOOL_DOCKER_DIR", "/root/wd6zn-docker"))
ENV_FILE = DOCKER_DIR / ".env"
ENV_EXAMPLE = DOCKER_DIR / ".env.example"
DEFAULT_SERVER_SOURCE = Path("/root/wd6zn_extracted")
DEFAULT_APK = Path("/root/tiandao_zip_extracted/天道.apk")

ALLOWED_ENV_KEYS = [
    "PUBLIC_IP",
    "SOURCE_ROOT",
    "MYSQL_ROOT_PASSWORD",
    "MYSQL_PORT",
    "IMPORT_DB",
    "FORCE_IMPORT_DB",
    "REMOVE_BACKDOORS",
    "START_GAME",
    "START_ZONE2",
    "COMPOSE",
]

TASKS: dict[str, dict] = {}
TASK_LOCK = threading.Lock()


def ensure_dirs() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    UPLOAD_DIR.mkdir(exist_ok=True)


def get_token() -> str:
    ensure_dirs()
    if TOKEN_FILE.exists():
        return TOKEN_FILE.read_text().strip()
    token = secrets.token_urlsafe(24)
    TOKEN_FILE.write_text(token)
    TOKEN_FILE.chmod(0o600)
    return token


def parse_env(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    if not path.exists():
        return result
    for raw in path.read_text(errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key.strip()] = value.strip().strip('"').strip("'")
    return result


def load_config() -> dict[str, str]:
    if not ENV_FILE.exists() and ENV_EXAMPLE.exists():
        shutil.copy2(ENV_EXAMPLE, ENV_FILE)
    config = parse_env(ENV_EXAMPLE)
    config.update(parse_env(ENV_FILE))
    config.setdefault("SOURCE_ROOT", str(DEFAULT_SERVER_SOURCE))
    config.setdefault("COMPOSE", "docker compose")
    return {key: config.get(key, "") for key in ALLOWED_ENV_KEYS}


def write_config(values: dict[str, str]) -> dict[str, str]:
    current = load_config()
    for key in ALLOWED_ENV_KEYS:
        if key in values:
            current[key] = str(values[key]).strip()

    current["MYSQL_PORT"] = current.get("MYSQL_PORT") or "3306"
    for key in ["IMPORT_DB", "FORCE_IMPORT_DB", "REMOVE_BACKDOORS", "START_GAME", "START_ZONE2"]:
        current[key] = "1" if str(current.get(key, "0")).lower() in {"1", "true", "yes", "on"} else "0"
    current["COMPOSE"] = current.get("COMPOSE") or "docker compose"

    lines = [
        "# Managed by game-tool. Edit here or from the web panel.",
        f"PUBLIC_IP={current['PUBLIC_IP']}",
        f"SOURCE_ROOT={current['SOURCE_ROOT']}",
        f"MYSQL_ROOT_PASSWORD={current['MYSQL_ROOT_PASSWORD']}",
        f"MYSQL_PORT={current['MYSQL_PORT']}",
        f"IMPORT_DB={current['IMPORT_DB']}",
        f"FORCE_IMPORT_DB={current['FORCE_IMPORT_DB']}",
        f"REMOVE_BACKDOORS={current['REMOVE_BACKDOORS']}",
        f"START_GAME={current['START_GAME']}",
        f"START_ZONE2={current['START_ZONE2']}",
        f"COMPOSE={current['COMPOSE']}",
        "",
    ]
    ENV_FILE.write_text("\n".join(lines))
    return current


def path_summary(path: Path) -> dict:
    exists = path.exists()
    info = {"path": str(path), "exists": exists}
    if exists and path.is_file():
        info["size"] = path.stat().st_size
        info["mtime"] = int(path.stat().st_mtime)
    elif exists and path.is_dir():
        info["mtime"] = int(path.stat().st_mtime)
    return info


def run_quick(command: list[str], cwd: Path | None = None, timeout: int = 12) -> dict:
    try:
        proc = subprocess.run(command, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
        return {"ok": proc.returncode == 0, "code": proc.returncode, "output": proc.stdout[-6000:]}
    except Exception as exc:
        return {"ok": False, "code": -1, "output": str(exc)}


def compose_command(config: dict[str, str], *args: str) -> list[str]:
    compose = config.get("COMPOSE") or "docker compose"
    return compose.split() + list(args)


def task_env() -> dict[str, str]:
    env = os.environ.copy()
    env.update(load_config())
    return env


def append_task(task_id: str, line: str) -> None:
    with TASK_LOCK:
        task = TASKS.get(task_id)
        if not task:
            return
        task["log"].append(line)
        if len(task["log"]) > 1200:
            task["log"] = task["log"][-1200:]


def start_task(name: str, command: list[str], cwd: Path = DOCKER_DIR) -> dict:
    task_id = f"{int(time.time())}-{secrets.token_hex(4)}"
    task = {
        "id": task_id,
        "name": name,
        "command": " ".join(command),
        "cwd": str(cwd),
        "status": "running",
        "code": None,
        "started_at": int(time.time()),
        "finished_at": None,
        "log": [],
    }
    with TASK_LOCK:
        TASKS[task_id] = task

    def worker() -> None:
        append_task(task_id, f"$ cd {cwd}")
        append_task(task_id, f"$ {' '.join(command)}")
        try:
            proc = subprocess.Popen(
                command,
                cwd=cwd,
                env=task_env(),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1,
            )
            assert proc.stdout is not None
            for line in proc.stdout:
                append_task(task_id, line.rstrip("\n"))
            code = proc.wait()
            with TASK_LOCK:
                TASKS[task_id]["status"] = "done" if code == 0 else "failed"
                TASKS[task_id]["code"] = code
                TASKS[task_id]["finished_at"] = int(time.time())
        except Exception as exc:
            append_task(task_id, f"[ERROR] {exc}")
            with TASK_LOCK:
                TASKS[task_id]["status"] = "failed"
                TASKS[task_id]["code"] = -1
                TASKS[task_id]["finished_at"] = int(time.time())

    threading.Thread(target=worker, daemon=True).start()
    return task


def task_snapshot() -> list[dict]:
    with TASK_LOCK:
        return sorted(TASKS.values(), key=lambda item: item["started_at"], reverse=True)[:20]


def status_payload() -> dict:
    config = load_config()
    docker = run_quick(["docker", "--version"])
    compose = run_quick(compose_command(config, "ps"), cwd=DOCKER_DIR) if DOCKER_DIR.exists() else {"ok": False, "output": "docker dir missing"}
    return {
        "dockerDir": str(DOCKER_DIR),
        "config": config,
        "paths": {
            "serverArchive": path_summary(Path("/root/手工端.7z")),
            "serverExtracted": path_summary(Path(config.get("SOURCE_ROOT") or DEFAULT_SERVER_SOURCE)),
            "tiandaoZip": path_summary(Path("/root/天道.zip")),
            "apk": path_summary(DEFAULT_APK),
            "dockerPackage": path_summary(Path("/root/wd6zn-docker.tar.gz")),
            "dockerData": path_summary(DOCKER_DIR / "data/rootfs"),
        },
        "tools": {
            "docker": docker,
            "composePs": compose,
            "apktool": {"ok": bool(shutil.which("apktool")), "output": shutil.which("apktool") or ""},
            "apksigner": {"ok": bool(shutil.which("apksigner")), "output": shutil.which("apksigner") or ""},
            "zipalign": {"ok": bool(shutil.which("zipalign")), "output": shutil.which("zipalign") or ""},
        },
        "tasks": task_snapshot(),
    }


def json_response(handler: SimpleHTTPRequestHandler, data: object, code: int = 200) -> None:
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def error_response(handler: SimpleHTTPRequestHandler, message: str, code: int = 400) -> None:
    json_response(handler, {"ok": False, "error": message}, code)


class Handler(SimpleHTTPRequestHandler):
    server_version = "GameTool/0.1"

    def translate_path(self, path: str) -> str:
        parsed = urllib.parse.urlparse(path)
        rel = parsed.path.lstrip("/") or "index.html"
        return str(STATIC_DIR / rel)

    def log_message(self, fmt: str, *args) -> None:
        print(f"[{self.log_date_time_string()}] {fmt % args}")

    def authenticated(self) -> bool:
        token = get_token()
        header = self.headers.get("Authorization", "")
        parsed = urllib.parse.urlparse(self.path)
        query_token = urllib.parse.parse_qs(parsed.query).get("token", [""])[0]
        return header == f"Bearer {token}" or query_token == token

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        data = self.rfile.read(length)
        return json.loads(data.decode("utf-8"))

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path.startswith("/api/"):
            if not self.authenticated():
                return error_response(self, "unauthorized", HTTPStatus.UNAUTHORIZED)
            if parsed.path == "/api/status":
                return json_response(self, {"ok": True, **status_payload()})
            if parsed.path == "/api/tasks":
                return json_response(self, {"ok": True, "tasks": task_snapshot()})
            return error_response(self, "unknown api", HTTPStatus.NOT_FOUND)
        return super().do_GET()

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if not parsed.path.startswith("/api/"):
            return error_response(self, "unknown endpoint", HTTPStatus.NOT_FOUND)
        if not self.authenticated():
            return error_response(self, "unauthorized", HTTPStatus.UNAUTHORIZED)
        try:
            payload = self.read_json()
        except Exception as exc:
            return error_response(self, f"invalid json: {exc}")

        if parsed.path == "/api/config":
            config = write_config(payload)
            return json_response(self, {"ok": True, "config": config})

        if parsed.path == "/api/task":
            action = str(payload.get("action", ""))
            config = load_config()
            source_root = config.get("SOURCE_ROOT") or str(DEFAULT_SERVER_SOURCE)
            actions: dict[str, tuple[str, list[str]]] = {
                "prepare": ("准备服务端文件", ["./scripts/prepare_payload.sh", source_root]),
                "rewrite": ("重写 IP/数据库配置", ["python3", "./scripts/rewrite_config.py", "./data/rootfs"]),
                "deploy": ("一键部署 Docker", ["./deploy.sh"]),
                "up": ("启动服务", compose_command(config, "up", "-d", "--build", "web", "game")),
                "start_game": ("启动游戏进程", compose_command(config, "up", "-d", "game")),
                "down": ("停止服务", compose_command(config, "down")),
                "restart_web": ("重启 Web", compose_command(config, "restart", "web")),
                "apk_scan": ("扫描天道 APK 配置", ["python3", str(BASE_DIR / "scripts/scan_apk.py")]),
            }
            if action not in actions:
                return error_response(self, "unknown action")
            name, command = actions[action]
            task = start_task(name, command)
            return json_response(self, {"ok": True, "task": task})

        return error_response(self, "unknown api", HTTPStatus.NOT_FOUND)


def main() -> int:
    ensure_dirs()
    token = get_token()
    if not ENV_FILE.exists() and ENV_EXAMPLE.exists():
        shutil.copy2(ENV_EXAMPLE, ENV_FILE)
    host = os.environ.get("GAME_TOOL_HOST", "0.0.0.0")
    port = int(os.environ.get("GAME_TOOL_PORT", "8088"))
    mimetypes.add_type("application/javascript", ".js")
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"Game tool running: http://127.0.0.1:{port}/?token={token}")
    print(f"Bind address: {host}:{port}")
    httpd.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
