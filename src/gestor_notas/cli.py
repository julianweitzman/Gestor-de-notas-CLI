from typing import Annotated
import httpx
import typer
from pydantic import ValidationError
from .models import NoteCreate
from .server import ServerError, api_client

app = typer.Typer(help="Creá y consultá tus notas locales.", no_args_is_help=True)


def request(method: str, path: str, **kwargs):
    try:
        with api_client() as client:
            response = client.request(method, path, **kwargs)
            if response.status_code == 404:
                raise ServerError("No existe una nota con ese ID.")
            if response.status_code == 422:
                raise ServerError("Los datos enviados no son válidos.")
            response.raise_for_status()
            return response.json()
    except (ServerError, httpx.HTTPError, ValueError) as exc:
        message = str(exc)
        if isinstance(exc, httpx.HTTPError):
            message = "No se pudo completar la solicitud a la API."
            if method == "POST":
                message += " La nota podría haberse guardado; consultá 'notas listar' antes de intentar nuevamente."
        typer.echo(f"Error: {message}", err=True)
        raise typer.Exit(1) from exc


def show_note(note: dict) -> None:
    typer.echo(f"ID: {note['id']}\nNombre: {note['nombre']}\nCreada: {note['creada_en']}\nTexto:\n{note['texto']}")


@app.command("crear", help="Crear una nota; se solicitan los campos omitidos.")
def create(
    nombre: Annotated[str | None, typer.Option(help="Nombre de la nota.")] = None,
    texto: Annotated[str | None, typer.Option(help="Contenido de la nota.")] = None,
):
    if nombre is None:
        nombre = typer.prompt("Nombre")
    if texto is None:
        texto = typer.prompt("Texto")
    try:
        data = NoteCreate(nombre=nombre, texto=texto)
    except ValidationError:
        typer.echo("Error: el nombre y el texto no pueden estar vacíos ni contener solo espacios.", err=True)
        raise typer.Exit(2)
    show_note(request("POST", "/notas", json=data.model_dump()))


@app.command("listar", help="Listar las notas desde la más reciente.")
def list_notes():
    notes = request("GET", "/notas")
    if not notes:
        typer.echo("No hay notas guardadas.")
        return
    typer.echo("ID\tNombre\tCreada (UTC)")
    for note in notes:
        name = note["nombre"].replace("\n", " ").replace("\r", " ").replace("\t", " ")
        typer.echo(f"{note['id']}\t{name}\t{note['creada_en']}")


@app.command("ver", help="Consultar una nota por su ID.")
def get_note(note_id: Annotated[int, typer.Argument(min=1, help="ID de la nota.")]):
    show_note(request("GET", f"/notas/{note_id}"))


@app.command("servidor", help="Mantener la API encendida; Ctrl+C para detenerla.")
def server():
    import uvicorn
    from .api import create_app
    from .config import HOST, PORT
    typer.echo(f"API disponible en http://{HOST}:{PORT}. Ctrl+C para detenerla.")
    uvicorn.run(create_app(), host=HOST, port=PORT)
