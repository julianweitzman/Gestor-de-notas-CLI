from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException, Path as PathParameter, Response
from .config import APP_ID, PROTOCOL_VERSION, database_path
from .models import Note, NoteCreate
from .service import NoteService
from .storage import DuplicateNameError, Repository


def create_app(db_path: Path | None = None) -> FastAPI:
    repository = Repository(db_path if db_path is not None else database_path())
    service = NoteService(repository)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        repository.initialize()
        yield

    application = FastAPI(title="Gestor de notas", lifespan=lifespan)

    @application.get("/health")
    def health():
        return {"app": APP_ID, "protocol_version": PROTOCOL_VERSION}

    @application.post("/notas", response_model=Note, status_code=201)
    def create_note(data: NoteCreate):
        try:
            return service.create(data)
        except DuplicateNameError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @application.get("/notas", response_model=list[Note])
    def list_notes(nombre: str | None = None):
        return service.list(nombre)

    @application.get("/notas/{note_id}", response_model=Note)
    def get_note(note_id: int = PathParameter(gt=0)):
        note = service.get(note_id)
        if note is None:
            raise HTTPException(status_code=404, detail="No existe una nota con ese ID.")
        return note

    @application.put("/notas/{note_id}", response_model=Note)
    def update_note(data: NoteCreate, note_id: int = PathParameter(gt=0)):
        try:
            note = service.update(note_id, data)
        except DuplicateNameError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        if note is None:
            raise HTTPException(status_code=404, detail="No existe una nota con ese ID.")
        return note

    @application.delete("/notas/{note_id}", status_code=204)
    def delete_note(note_id: int = PathParameter(gt=0)) -> Response:
        if not service.delete(note_id):
            raise HTTPException(status_code=404, detail="No existe una nota con ese ID.")
        return Response(status_code=204)

    return application
