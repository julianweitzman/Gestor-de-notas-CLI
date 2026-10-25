from datetime import datetime
from pydantic import BaseModel, field_validator


class NoteCreate(BaseModel):
    nombre: str
    texto: str

    @field_validator("nombre", "texto")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("El campo no puede estar vacío ni contener solo espacios.")
        return value


class Note(NoteCreate):
    id: int
    creada_en: datetime
