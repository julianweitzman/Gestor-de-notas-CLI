from contextlib import contextmanager

from fastapi.testclient import TestClient
from prompt_toolkit.application import create_app_session
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput
from typer.testing import CliRunner

from gestor_notas_cli import cli, selector
from gestor_notas.api import create_app


def test_cli_search_and_conflict(tmp_path, monkeypatch):
    with TestClient(create_app(tmp_path / 'notes.db')) as client:
        @contextmanager
        def api_client():
            yield client
        monkeypatch.setattr(cli, 'api_client', api_client)
        runner = CliRunner()
        for name in ['Idea', 'Idea semanal', '123']:
            assert runner.invoke(cli.app, ['crear', '--nombre', name, '--texto', 'contenido']).exit_code == 0
        assert runner.invoke(cli.app, ['crear', '--nombre', 'Idea', '--texto', 'x']).exit_code == 1
        monkeypatch.setattr(cli, 'select_note', lambda notes: notes[0])
        result = runner.invoke(cli.app, ['ver', 'idea'])
        assert result.exit_code == 0
        assert 'Nombre: Idea semanal' in result.output
        assert 'Nombre: 123' in runner.invoke(cli.app, ['ver', '--nombre', '123']).output
        assert 'Nombre: Idea' in runner.invoke(cli.app, ['ver', '1']).output
        assert runner.invoke(cli.app, ['ver', 'ausente']).exit_code == 1
        assert runner.invoke(cli.app, ['ver', ' ']).exit_code == 2
        assert runner.invoke(cli.app, ['ver', '0']).exit_code == 2
        assert runner.invoke(cli.app, ['ver'], input='123\n').exit_code == 0
        monkeypatch.setattr(cli, 'select_note', lambda notes: None)
        assert 'cancelada' in runner.invoke(cli.app, ['ver', 'idea']).output


def test_selector_arrow_enter_and_cancel(monkeypatch):
    monkeypatch.setattr(selector.sys.stdin, 'isatty', lambda: True)
    monkeypatch.setattr(selector.sys.stdout, 'isatty', lambda: True)
    notes = [{'id': 1, 'nombre': 'Primera'}, {'id': 2, 'nombre': 'Segunda'}]
    for keys, expected in [('\x1b[B\r', notes[1]), ('\r', notes[0]), ('\x03', None)]:
        with create_pipe_input() as pipe:
            with create_app_session(input=pipe, output=DummyOutput()):
                pipe.send_text(keys)
                assert selector.select_note(notes) == expected
