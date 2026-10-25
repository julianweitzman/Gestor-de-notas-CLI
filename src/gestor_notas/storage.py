import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


class DuplicateNameError(ValueError):
    """Ya existe una nota con ese nombre."""


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
            # La migración conserva IDs y contenido, incluso si ya había duplicados.
            rows = connection.execute("SELECT id, nombre FROM notas ORDER BY id").fetchall()
            occupied = {row["nombre"] for row in rows}
            seen: set[str] = set()
            for row in rows:
                name = row["nombre"]
                if name in seen:
                    suffix = 2
                    candidate = f"{name} ({suffix})"
                    while candidate in occupied:
                        suffix += 1
                        candidate = f"{name} ({suffix})"
                    connection.execute("UPDATE notas SET nombre = ? WHERE id = ?", (candidate, row["id"]))
                    occupied.add(candidate)
                seen.add(name)
            connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS notas_nombre_unique ON notas(nombre)")

    def create(self, nombre: str, texto: str, creada_en: str) -> dict:
        with self.connection() as connection:
            try:
                cursor = connection.execute("INSERT INTO notas (nombre, texto, creada_en) VALUES (?, ?, ?)", (nombre, texto, creada_en))
            except sqlite3.IntegrityError as exc:
                if "notas.nombre" in str(exc):
                    raise DuplicateNameError("Ya existe una nota con ese nombre.") from exc
                raise
            row = connection.execute("SELECT * FROM notas WHERE id = ?", (cursor.lastrowid,)).fetchone()
            return dict(row)

    def list(self) -> list[dict]:
        with self.connection() as connection:
            return [dict(row) for row in connection.execute("SELECT * FROM notas ORDER BY creada_en DESC, id DESC")]

    def get(self, note_id: int) -> dict | None:
        with self.connection() as connection:
            row = connection.execute("SELECT * FROM notas WHERE id = ?", (note_id,)).fetchone()
            return dict(row) if row else None
