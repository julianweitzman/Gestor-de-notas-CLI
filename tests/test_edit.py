from contextlib import contextmanager
from unittest.mock import Mock, call

import httpx
import pytest
from typer.testing import CliRunner

from gestor_notas import cli
from gestor_notas.editor import EditorUnavailable


runner = CliRunner()
NOTE = {"id": 1, "nombre": "Idea", "texto": "Original\nSegunda línea", "creada_en": "2026-01-01T00:00:00Z"}


@pytest.mark.parametrize("options, changes", [
    (["--nombre", "Renombrada"], {"nombre": "Renombrada"}),
    (["--texto", "Nuevo\nTexto ñ"], {"texto": "Nuevo\nTexto ñ"}),
    (["--nombre", "Renombrada", "--texto", "Nuevo"], {"nombre": "Renombrada", "texto": "Nuevo"}),
])
def test_edit_options_preserve_other_fields(monkeypatch, options, changes):
    updated = {**NOTE, **changes}
    request = Mock(side_effect=[NOTE, updated])
    editor = Mock(side_effect=AssertionError("No debe abrir el editor"))
    monkeypatch.setattr(cli, "request", request)
    monkeypatch.setattr(cli, "edit_text", editor)
    result = runner.invoke(cli.app, ["editar", "1", *options])
    assert result.exit_code == 0, result.output
    assert updated["nombre"] in result.output
    assert updated["texto"] in result.output
    assert request.call_args_list == [call("GET", "/notas/1"), call(
        "PUT", "/notas/1", json={key: updated[key] for key in ("nombre", "texto")})]
    editor.assert_not_called()


def test_edit_prefills_editor(monkeypatch):
    request = Mock(side_effect=[NOTE, {**NOTE, "texto": "Editado"}])
    editor = Mock(return_value="Editado")
    monkeypatch.setattr(cli, "request", request)
    monkeypatch.setattr(cli, "edit_text", editor)
    result = runner.invoke(cli.app, ["editar", "1"])
    assert result.exit_code == 0, result.output
    editor.assert_called_once_with(NOTE["texto"])
    request.assert_called_with("PUT", "/notas/1", json={"nombre": "Idea", "texto": "Editado"})


@pytest.mark.parametrize("text, code", [(None, 0), ("", 2), (" \n", 2)])
def test_edit_cancel_and_invalid_editor_content_do_not_save(monkeypatch, text, code):
    request = Mock(return_value=NOTE)
    monkeypatch.setattr(cli, "request", request)
    monkeypatch.setattr(cli, "edit_text", Mock(return_value=text))
    result = runner.invoke(cli.app, ["editar", "1"])
    assert result.exit_code == code, result.output
    request.assert_called_once_with("GET", "/notas/1")
    if text is None:
        assert "cancelada" in result.output


def test_edit_editor_unavailable(monkeypatch):
    request = Mock(return_value=NOTE)
    monkeypatch.setattr(cli, "request", request)
    monkeypatch.setattr(cli, "edit_text", Mock(side_effect=EditorUnavailable("Usá --texto.")))
    result = runner.invoke(cli.app, ["editar", "1"])
    assert result.exit_code == 2
    assert "--texto" in result.output
    request.assert_called_once_with("GET", "/notas/1")


@pytest.mark.parametrize("options", [["--nombre", " "], ["--texto", ""]])
def test_edit_invalid_options_do_not_save(monkeypatch, options):
    request = Mock(return_value=NOTE)
    monkeypatch.setattr(cli, "request", request)
    result = runner.invoke(cli.app, ["editar", "1", *options])
    assert result.exit_code == 2
    request.assert_called_once_with("GET", "/notas/1")


def test_edit_invalid_id_does_not_request(monkeypatch):
    request = Mock()
    monkeypatch.setattr(cli, "request", request)
    for invalid_id in ("0", "-1"):
        assert runner.invoke(cli.app, ["editar", "--", invalid_id]).exit_code == 2
    request.assert_not_called()


def test_edit_by_name_prompt_numeric_and_selection(monkeypatch):
    other = {**NOTE, "id": 2, "nombre": "Idea semanal"}
    for args, query, notes, selected in [
        (["idea"], "idea", [NOTE], NOTE),
        ([], "idea", [NOTE], NOTE),
        (["--buscar-nombre", "123"], "123", [{**NOTE, "nombre": "123"}], {**NOTE, "nombre": "123"}),
        (["idea"], "idea", [NOTE, other], other),
    ]:
        request = Mock(side_effect=[notes, {**selected, "texto": "Nuevo"}])
        monkeypatch.setattr(cli, "request", request)
        monkeypatch.setattr(cli, "select_note", Mock(return_value=selected))
        result = runner.invoke(cli.app, ["editar", *args, "--texto", "Nuevo"], input="idea\n")
        assert result.exit_code == 0, result.output
        assert request.call_args_list == [
            call("GET", "/notas", params={"nombre": query}),
            call("PUT", f"/notas/{selected['id']}", json={"nombre": selected["nombre"], "texto": "Nuevo"}),
        ]


def test_edit_name_cancel_missing_and_selection_unavailable(monkeypatch):
    from gestor_notas.selector import SelectionUnavailable

    for notes, selection, code, message in [
        ([], Mock(), 1, "No se encontraron"),
        ([NOTE, NOTE], Mock(return_value=None), 0, "cancelada"),
        ([NOTE, NOTE], Mock(side_effect=SelectionUnavailable("Usá un ID.")), 2, "Usá un ID"),
    ]:
        request = Mock(return_value=notes)
        monkeypatch.setattr(cli, "request", request)
        monkeypatch.setattr(cli, "select_note", selection)
        result = runner.invoke(cli.app, ["editar", "idea", "--texto", "Nuevo"])
        assert result.exit_code == code, result.output
        assert message in result.output
        request.assert_called_once_with("GET", "/notas", params={"nombre": "idea"})


def test_edit_by_name_opens_original_editor(monkeypatch):
    request = Mock(side_effect=[[NOTE], {**NOTE, "texto": "Editado"}])
    editor = Mock(return_value="Editado")
    monkeypatch.setattr(cli, "request", request)
    monkeypatch.setattr(cli, "edit_text", editor)
    result = runner.invoke(cli.app, ["editar", "idea"])
    assert result.exit_code == 0, result.output
    editor.assert_called_once_with(NOTE["texto"])
    request.assert_called_with("PUT", "/notas/1", json={"nombre": "Idea", "texto": "Editado"})


@pytest.mark.parametrize("args", [
    ["idea", "--buscar-nombre", "otra"],
    [" "],
])
def test_edit_conflicting_or_blank_arguments(monkeypatch, args):
    request = Mock()
    monkeypatch.setattr(cli, "request", request)
    result = runner.invoke(cli.app, ["editar", *args])
    assert result.exit_code == 2, result.output
    request.assert_not_called()


@pytest.mark.parametrize("status, message", [(404, "No existe una nota"), (409, "Ya existe una nota"), (422, "no son válidos"), (None, "podría haberse editado")])
def test_edit_http_errors_and_uncertain_update_not_retried(monkeypatch, status, message):
    calls = []

    def handle(request):
        calls.append(request.method)
        if request.method == "GET":
            return httpx.Response(404 if status == 404 else 200, json=NOTE)
        if status is None:
            raise httpx.ReadTimeout("timeout", request=request)
        return httpx.Response(status)

    @contextmanager
    def fake_client():
        with httpx.Client(base_url="http://test", transport=httpx.MockTransport(handle)) as client:
            yield client

    monkeypatch.setattr(cli, "api_client", fake_client)
    result = runner.invoke(cli.app, ["editar", "1", "--texto", "Nuevo"])
    assert result.exit_code == 1
    assert message in result.output
    assert calls == (["GET"] if status == 404 else ["GET", "PUT"])
