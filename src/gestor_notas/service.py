from datetime import datetime, timezone
from .models import Note, NoteCreate
from .storage import Repository


class NoteService:
    def __init__(self, repository: Repository):
        self.repository = repository

    def create(self, data: NoteCreate) -> Note:
        return Note.model_validate(self.repository.create(data.nombre, data.texto, datetime.now(timezone.utc).isoformat()))

    def list(self) -> list[Note]:
        return [Note.model_validate(row) for row in self.repository.list()]

    def get(self, note_id: int) -> Note | None:
        row = self.repository.get(note_id)
        return Note.model_validate(row) if row else None
