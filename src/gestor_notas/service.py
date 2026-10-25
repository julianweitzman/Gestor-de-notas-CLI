from datetime import datetime, timezone
from .models import Note, NoteCreate
from .storage import Repository


class NoteService:
    def __init__(self, repository: Repository):
        self.repository = repository

    def create(self, data: NoteCreate) -> Note:
        return Note.model_validate(self.repository.create(data.nombre, data.texto, datetime.now(timezone.utc).isoformat()))

    def list(self, nombre: str | None = None) -> list[Note]:
        rows = self.repository.list()
        if nombre is not None:
            rows = [row for row in rows if nombre.casefold() in row["nombre"].casefold()]
        return [Note.model_validate(row) for row in rows]

    def get(self, note_id: int) -> Note | None:
        row = self.repository.get(note_id)
        return Note.model_validate(row) if row else None

    def delete(self, note_id: int) -> bool:
        return self.repository.delete(note_id)
