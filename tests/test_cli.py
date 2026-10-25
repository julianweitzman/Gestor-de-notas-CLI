from contextlib import contextmanager
import httpx
from typer.testing import CliRunner
from gestor_notas import cli

runner = CliRunner()


def test_cli_options_prompts_and_missing_note(monkeypatch):
    notes = []
    def handle(request):
        import json
        if request.method == "POST":
            note = {**json.loads(request.content), "id": len(notes) + 1, "creada_en": "2026-01-01T00:00:00Z"}
            notes.append(note)
            return httpx.Response(201, json=note)
        if request.url.path == "/notas":
            return httpx.Response(200, json=list(reversed(notes)))
        return httpx.Response(404, json={"detail": "No existe"})
    @contextmanager
    def fake_client():
        with httpx.Client(base_url="http://test", transport=httpx.MockTransport(handle)) as client:
            yield client
    monkeypatch.setattr(cli, "api_client", fake_client)
    assert "No hay notas" in runner.invoke(cli.app, ["listar"]).output
    result = runner.invoke(cli.app, ["crear", "--nombre", "Idea", "--texto", "Texto"])
    assert result.exit_code == 0, result.output
    assert "ID: 1" in result.output
    assert runner.invoke(cli.app, ["crear"], input="Otra\nContenido\n").exit_code == 0
    assert runner.invoke(cli.app, ["crear", "--nombre", "Tercera"], input="Texto\n").exit_code == 0
    assert "Idea" in runner.invoke(cli.app, ["listar"]).output
    assert runner.invoke(cli.app, ["ver", "999"]).exit_code == 1
    assert runner.invoke(cli.app, ["crear", "--nombre", " ", "--texto", "x"]).exit_code == 2
    assert len(notes) == 3


def test_uncertain_creation_is_not_retried(monkeypatch):
    calls = []
    def handle(request):
        calls.append(request)
        raise httpx.ReadTimeout("timeout", request=request)
    @contextmanager
    def fake_client():
        with httpx.Client(base_url="http://test", transport=httpx.MockTransport(handle)) as client:
            yield client
    monkeypatch.setattr(cli, "api_client", fake_client)
    result = runner.invoke(cli.app, ["crear", "--nombre", "Idea", "--texto", "Texto"])
    assert result.exit_code == 1
    assert "podría haberse guardado" in result.output
    assert len(calls) == 1
