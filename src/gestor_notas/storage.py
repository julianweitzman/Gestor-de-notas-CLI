import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


class Repository:
    def __init__(self, path: Path):
        self.path = path

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=5)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as connection:
            connection.execute("CREATE TABLE IF NOT EXISTS notas (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL, texto TEXT NOT NULL, creada_en TEXT NOT NULL)")

    def create(self, nombre: str, texto: str, creada_en: str) -> dict:
        with self.connection() as connection:
            cursor = connection.execute("INSERT INTO notas (nombre, texto, creada_en) VALUES (?, ?, ?)", (nombre, texto, creada_en))
            row = connection.execute("SELECT * FROM notas WHERE id = ?", (cursor.lastrowid,)).fetchone()
            return dict(row)

    def list(self) -> list[dict]:
        with self.connection() as connection:
            return [dict(row) for row in connection.execute("SELECT * FROM notas ORDER BY creada_en DESC, id DESC")]

    def get(self, note_id: int) -> dict | None:
        with self.connection() as connection:
            row = connection.execute("SELECT * FROM notas WHERE id = ?", (note_id,)).fetchone()
            return dict(row) if row else None
