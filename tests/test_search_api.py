import sqlite3

from fastapi.testclient import TestClient
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


