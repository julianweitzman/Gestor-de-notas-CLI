from datetime import datetime
from fastapi.testclient import TestClient
from gestor_notas.api import create_app


def test_persistence_and_contract(tmp_path):
    path = tmp_path / "nested" / "notes.sqlite3"
    with TestClient(create_app(path)) as client:
        assert client.get("/health").json() == {"app": "gestor-notas", "protocol_version": 1}
        assert client.get("/notas").json() == []
        payload = {"nombre": "Idea ñ", "texto": "Primera línea\nSegunda línea 😊"}
        response = client.post("/notas", json=payload)
        assert response.status_code == 201
        first = response.json()
        assert first["nombre"] == payload["nombre"]
        assert first["texto"] == payload["texto"]
        assert datetime.fromisoformat(first["creada_en"]).utcoffset().total_seconds() == 0
        assert client.post("/notas", json=payload).status_code == 409
        second = client.post("/notas", json={**payload, "nombre": "Otra"}).json()
        assert second["id"] != first["id"]
        assert [note["id"] for note in client.get("/notas").json()] == [second["id"], first["id"]]
        assert client.get(f"/notas/{first['id']}").json() == first
        assert client.get("/notas/999999").status_code == 404
        assert client.get("/notas/0").status_code == 422
    with TestClient(create_app(path)) as client:
        assert len(client.get("/notas").json()) == 2


def test_validation_and_sql_parameters(tmp_path):
    with TestClient(create_app(tmp_path / "notes.sqlite3")) as client:
        for payload in ({}, {"nombre": " ", "texto": "x"}, {"nombre": "x", "texto": "\n\t"}, {"nombre": 2, "texto": "x"}):
            assert client.post("/notas", json=payload).status_code == 422
        payload = {"nombre": "'); DROP TABLE notas;--", "texto": "'"}
        assert client.post("/notas", json=payload).status_code == 201
        assert client.get("/notas").json()[0]["nombre"] == payload["nombre"]


def test_delete_persistence_and_contract(tmp_path):
    path = tmp_path / "notes.sqlite3"
    payload = {"nombre": "Para eliminar", "texto": "Contenido"}
    with TestClient(create_app(path)) as client:
        note = client.post("/notas", json=payload).json()
        other = client.post("/notas", json={**payload, "nombre": "Conservar"}).json()
        response = client.delete(f"/notas/{note['id']}")
        assert response.status_code == 204
        assert response.content == b""
        assert client.get(f"/notas/{note['id']}").status_code == 404
        assert client.delete(f"/notas/{note['id']}").status_code == 404
        assert client.get("/notas").json() == [other]
        for invalid_id in ("0", "-1", "abc"):
            assert client.delete(f"/notas/{invalid_id}").status_code == 422
    with TestClient(create_app(path)) as client:
        assert client.get("/notas").json() == [other]
        assert client.post("/notas", json=payload).status_code == 201
