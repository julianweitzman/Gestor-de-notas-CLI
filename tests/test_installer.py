import shutil
import subprocess
import sys
from pathlib import Path

import pytest


pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Instalador de PowerShell para Windows")


@pytest.fixture
def installer(tmp_path):
    project = tmp_path / "proyecto con espacios"
    project.mkdir()
    script = project / "instalar.ps1"
    shutil.copyfile(Path(__file__).resolve().parents[1] / "instalar.ps1", script)

    def run(*args):
        return subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script), *args],
            cwd=tmp_path, capture_output=True, text=True, timeout=30,
        )

    return project, run


def test_uninstall_without_environment_preserves_data(installer):
    project, run = installer
    notes = project / "notas.sqlite3"
    notes.write_bytes(b"datos del usuario")
    result = run("-Accion", "Desinstalar")
    assert result.returncode == 0, result.stderr
    assert "No hay un entorno" in result.stdout
    assert notes.read_bytes() == b"datos del usuario"
    assert not (project / ".venv").exists()


def test_install_reports_missing_python(installer):
    project, run = installer
    result = run("-Python", str(project / "inexistente.exe"))
    assert result.returncode == 1
    assert "Error:" in result.stderr
    assert not (project / ".venv").exists()


@pytest.mark.parametrize("version_status, expected", [(1, "Python 3.11"), (0, "codigo 7")])
def test_install_stops_on_invalid_python_or_venv_failure(installer, version_status, expected):
    project, run = installer
    python = project / "python simulado.cmd"
    python.write_text(
        f'@echo off\nif "%~1"=="-c" exit /b {version_status}\nexit /b 7\n',
        encoding="ascii",
    )
    result = run("-Python", str(python))
    assert result.returncode == 1
    assert expected in result.stderr
    assert not (project / ".venv").exists()
