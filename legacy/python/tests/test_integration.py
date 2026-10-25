import os
import socket
import subprocess
import sys
import time
from pathlib import Path
import pytest
from gestor_notas.server import api_client


def test_real_cli_and_automatic_server(tmp_path, monkeypatch):
    # No interferir con servicios del usuario que ya ocupen el puerto fijo.
    with socket.socket() as probe:
        probe.settimeout(0.5)
        if probe.connect_ex(("127.0.0.1", 8000)) == 0:
            pytest.skip("El puerto 8000 tiene un servicio activo")
    monkeypatch.setenv("NOTAS_DATA_DIR", str(tmp_path))
    executable = Path(sys.executable).parent / ("notas.exe" if sys.platform == "win32" else "notas")
    def invoke(*args):
        return subprocess.run([str(executable), *args], capture_output=True, text=True, encoding="utf-8", env={**os.environ, "PYTHONIOENCODING": "utf-8"}, timeout=25)
    created = invoke("crear", "--nombre", "Persistencia ñ", "--texto", "Contenido")
    assert created.returncode == 0, created.stdout + created.stderr
    assert "ID: 1" in created.stdout
    fetched = invoke("ver", "1")
    assert fetched.returncode == 0, fetched.stdout + fetched.stderr
    assert "Persistencia ñ" in fetched.stdout
    edited = invoke("editar", "persistencia", "--nombre", "Revisada ñ", "--texto", "Nuevo\nContenido")
    assert edited.returncode == 0, edited.stdout + edited.stderr
    fetched = invoke("ver", "1")
    assert fetched.returncode == 0, fetched.stdout + fetched.stderr
    assert "Revisada ñ" in fetched.stdout
    assert "Nuevo\nContenido" in fetched.stdout
    assert (tmp_path / "notas.sqlite3").exists()
    with api_client() as client:
        assert client.get("/health").status_code == 200
        listed = invoke("listar")
        assert listed.returncode == 0, listed.stdout + listed.stderr
        edited = invoke("editar", "1", "--texto", "Servidor existente")
        assert edited.returncode == 0, edited.stdout + edited.stderr
        assert client.get("/notas/1").json()["texto"] == "Servidor existente"
        # La CLI debe dejar funcionando el servidor que ya existía.
        assert client.get("/health").status_code == 200
    # TIME_WAIT puede impedir bind aunque ya no exista un servidor.
    deadline = time.monotonic() + 5
    while True:
        with socket.socket() as probe:
            probe.settimeout(0.5)
            if probe.connect_ex(("127.0.0.1", 8000)) != 0:
                break
        assert time.monotonic() < deadline, "El servidor sigue aceptando conexiones"
        time.sleep(0.1)
