"""Pruebas del ejecutable publicado: HTTP real, aislamiento y ciclo de vida."""

import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest


@pytest.fixture
def invoke(tmp_path):
    root = Path(__file__).resolve().parents[1]
    executable = Path(os.environ.get("NOTAS_CLI", root / ".publish/windows/notas.exe"))
    assert executable.exists(), "Publicá la CLI C# antes de ejecutar pytest."

    def run(*args, input=None, python=None):
        env = {**os.environ, "NOTAS_DATA_DIR": str(tmp_path),
               "NOTAS_PYTHON": str(python or sys.executable), "PYTHONIOENCODING": "utf-8"}
        return subprocess.run([str(executable), *args], input=input, capture_output=True,
                              encoding="utf-8", env=env, timeout=25)

    return run


@pytest.fixture
def free_port():
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", 8000)) == 0:
            pytest.skip("El puerto 8000 tiene un servicio activo")


@pytest.fixture
def fake_api(free_port):
    calls = []
    state = {"health": {"app": "gestor-notas", "protocol_version": 1}, "status": 200, "health_delay": 0}
    note = {"id": 1, "nombre": "Nota [ñ]", "texto": "Uno\nDos 😊", "creada_en": "2026-01-01T00:00:00Z"}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            calls.append(("GET", self.path))
            if self.path == "/health":
                time.sleep(state["health_delay"])
                payload, status = state["health"], 200
            elif self.path.startswith("/notas?"):
                payload, status = [note, {**note, "id": 2}], state["status"]
            else:
                payload, status = note, state["status"]
            self.respond(payload, status)

        def do_PUT(self):
            calls.append(("PUT", self.path))
            if self.headers.get("Transfer-Encoding") == "chunked":
                chunks = []
                while size := int(self.rfile.readline().strip(), 16):
                    chunks.append(self.rfile.read(size))
                    self.rfile.read(2)
                self.rfile.readline()
                body = json.loads(b"".join(chunks))
            else:
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            self.respond({**note, **body}, state["status"])

        def respond(self, payload, status):
            body = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            try:
                self.wfile.write(body)
            except ConnectionError:
                pass  # La CLI puede haber agotado su plazo de respuesta.

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 8000), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield state, calls
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_help_and_invalid_input_do_not_start_backend(invoke, tmp_path):
    assert invoke("--help", python=tmp_path / "missing.exe").returncode == 0
    assert invoke("eliminar", "0").returncode == 2
    assert invoke("eliminar", "abc").returncode == 2
    assert invoke("ver", " ").returncode == 2
    assert invoke("ver", "1", "--nombre", "Idea").returncode == 2
    assert invoke("crear", "--nombre", " ", "--texto", "contenido").returncode == 2
    assert not (tmp_path / "servidor.log").exists()


def test_editor_requires_terminal_without_sending_http(invoke, tmp_path):
    result = invoke("crear", "--nombre", "Idea")
    assert result.returncode == 2
    assert "--texto" in result.stderr
    assert not (tmp_path / "servidor.log").exists()


def test_edit_reuses_one_session_and_existing_server(invoke, fake_api, tmp_path):
    state, calls = fake_api
    result = invoke("editar", "1", "--texto", "Actualización ñ 😊", python=tmp_path / "missing.exe")
    assert result.returncode == 0, result.stderr
    assert "Actualización ñ 😊" in result.stdout
    assert calls == [("GET", "/health"), ("GET", "/notas/1"), ("PUT", "/notas/1")]
    # Una segunda invocación aún puede utilizar el servidor ajeno.
    assert invoke("ver", "1").returncode == 0
    assert not (tmp_path / "servidor.log").exists()


def test_slow_healthy_server_is_reused_without_spawning(invoke, fake_api, tmp_path):
    state, calls = fake_api
    state["health_delay"] = 0.75
    result = invoke("ver", "1", python=tmp_path / "missing.exe")
    assert result.returncode == 0, result.stderr
    assert calls == [("GET", "/health"), ("GET", "/notas/1")]
    assert not (tmp_path / "servidor.log").exists()


def test_unresponsive_service_does_not_spawn_or_receive_note_requests(invoke, fake_api, tmp_path):
    state, calls = fake_api
    state["health_delay"] = 2.5
    result = invoke("ver", "1")
    assert result.returncode == 1
    assert "no responde correctamente" in result.stderr
    assert calls == [("GET", "/health")]
    assert not (tmp_path / "servidor.log").exists()


@pytest.mark.parametrize("health", [{}, {"app": "otra", "protocol_version": 1},
                                    {"app": "gestor-notas", "protocol_version": 2}])
def test_foreign_server_is_not_modified(invoke, fake_api, health):
    state, calls = fake_api
    state["health"] = health
    result = invoke("listar")
    assert result.returncode == 1
    assert "ocupado" in result.stderr
    assert calls == [("GET", "/health")]


def test_ambiguous_search_requires_terminal_and_lists_ids(invoke, fake_api):
    result = invoke("ver", "Nota")
    assert result.returncode == 2
    assert "varias coincidencias" in result.stderr
    assert "1:" in result.stderr and "2:" in result.stderr


def test_missing_python_has_actionable_error(invoke, free_port, tmp_path):
    result = invoke("listar", python=tmp_path / "missing.exe")
    assert result.returncode == 1
    assert "Registro:" in result.stderr
    assert "notas servidor" in result.stderr


def test_failed_backend_does_not_leave_server_running(invoke, free_port, tmp_path):
    # El intérprete existe, pero no puede importar el backend.
    environment = tmp_path / "python sin backend"
    subprocess.run([sys.executable, "-m", "venv", "--without-pip", str(environment)], check=True)
    result = invoke("listar", python=environment / "Scripts/python.exe")
    assert result.returncode == 1
    assert "terminó antes de estar disponible" in result.stderr
    with socket.socket() as probe:
        assert probe.connect_ex(("127.0.0.1", 8000)) != 0


def test_real_delete_confirmation_and_force(invoke, free_port):
    assert invoke("crear", "--nombre", "Idea ñ", "--texto", "Uno\nDos 😊").returncode == 0
    assert "cancelada" in invoke("eliminar", "1", input="\n").stdout
    assert invoke("ver", "1").returncode == 0
    assert "eliminada" in invoke("eliminar", "1", input="s\n").stdout
    assert invoke("ver", "1").returncode == 1
    assert invoke("crear", "--nombre", "Otra", "--texto", "x").returncode == 0
    assert invoke("eliminar", "2", "--forsar").returncode == 0


def test_server_command_leaves_existing_server_running(invoke, fake_api):
    result = invoke("servidor")
    assert result.returncode == 0
    assert "servidor existente" in result.stdout
    assert invoke("ver", "1").returncode == 0
