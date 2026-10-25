from contextlib import contextmanager
import sqlite3

from fastapi.testclient import TestClient
from prompt_toolkit.application import create_app_session
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput
from typer.testing import CliRunner

from gestor_notas import cli, selector
from gestor_notas.api import create_app
from gestor_notas.storage import Repository


def test_search_unicode_literal_and_unique_names(tmp_path):
    with TestClient(create_app(tmp_path / 'notes.db')) as client:
        for name in ['Reunión', 'Reunión semanal', '100%_lista', '123']:
            assert client.post('/notas', json={'nombre': name, 'texto': 'x'}).status_code == 201
        assert client.post('/notas', json={'nombre': 'Reunión', 'texto': 'otro'}).status_code == 409
        assert len(client.get('/notas', params={'nombre': 'REUNIÓN'}).json()) == 2
        assert [n['nombre'] for n in client.get('/notas', params={'nombre': '%_'}).json()] == ['100%_lista']
        assert client.get('/notas', params={'nombre': 'ausente'}).json() == []


def test_legacy_duplicates_are_preserved_and_migration_is_repeatable(tmp_path):
    path = tmp_path / 'old.db'
    with sqlite3.connect(path) as connection:
        connection.execute('CREATE TABLE notas (id INTEGER PRIMARY KEY, nombre TEXT NOT NULL, texto TEXT NOT NULL, creada_en TEXT NOT NULL)')
        for index, name in enumerate(['Idea', 'Idea', 'Idea (2)', 'Idea'], 1):
            connection.execute('INSERT INTO notas VALUES (?, ?, ?, ?)', (index, name, str(index), '2026-01-01'))
    repository = Repository(path)
    repository.initialize()
    repository.initialize()
    assert [repository.get(i)['nombre'] for i in range(1, 5)] == ['Idea', 'Idea (3)', 'Idea (2)', 'Idea (4)']
    assert [repository.get(i)['texto'] for i in range(1, 5)] == ['1', '2', '3', '4']


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
