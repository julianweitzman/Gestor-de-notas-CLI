from typing import Annotated
import httpx
import typer
from pydantic import ValidationError
from rich.console import Console
from rich.table import Table
from rich.text import Text
from .models import NoteCreate
from .server import ServerError, api_client

app = typer.Typer(help="Creá, consultá, editá y eliminá tus notas locales.", no_args_is_help=True)


def edit_text(initial_text: str = "") -> str | None:
    from .editor import edit_text as run_editor

    return run_editor(initial_text)


def select_note(notes: list[dict]) -> dict | None:
    from .selector import select_note as run_selector

    return run_selector(notes)


def request(method: str, path: str, **kwargs):
    try:
        with api_client() as client:
            response = client.request(method, path, **kwargs)
            if response.status_code == 404:
                raise ServerError("No existe una nota con ese ID.")
            if response.status_code == 409:
                raise ServerError("Ya existe una nota con ese nombre. Elegí otro nombre.")
            if response.status_code == 422:
                raise ServerError("Los datos enviados no son válidos.")
            response.raise_for_status()
            if response.status_code == 204:
                return None
            return response.json()
    except (ServerError, httpx.HTTPError, ValueError) as exc:
        message = str(exc)
        if isinstance(exc, httpx.HTTPError):
            message = "No se pudo completar la solicitud a la API."
            if method == "POST":
                message += " La nota podría haberse guardado; consultá 'notas listar' antes de intentar nuevamente."
            elif method == "DELETE":
                message += " La nota podría haberse eliminado; consultá 'notas listar' para verificarlo."
            elif method == "PUT":
                message += " La nota podría haberse editado; consultá 'notas ver' antes de intentar nuevamente."
        typer.echo(f"Error: {message}", err=True)
        raise typer.Exit(1) from exc


def show_note(note: dict) -> None:
    typer.echo(f"ID: {note['id']}\nNombre: {note['nombre']}\nCreada: {note['creada_en']}\nTexto:\n{note['texto']}")


@app.command("crear", help="Crear una nota; si falta el texto, abre un editor multilínea.")
def create(
    nombre: Annotated[str | None, typer.Option(help="Nombre de la nota.")] = None,
    texto: Annotated[str | None, typer.Option(help="Contenido; si se omite, abre el editor.")] = None,
):
    if nombre is None:
        nombre = typer.prompt("Nombre")
    if texto is None:
        from .editor import EditorUnavailable

        try:
            texto = edit_text()
        except EditorUnavailable as exc:
            typer.echo(f"Error: {exc}", err=True)
            raise typer.Exit(2) from exc
        if texto is None:
            typer.echo("Creación cancelada. No se guardó ninguna nota.")
            raise typer.Exit(0)
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
    table = Table(show_lines=True)
    table.add_column("ID", justify="right", no_wrap=True)
    table.add_column("Nombre", overflow="fold")
    table.add_column("Creada (UTC)", no_wrap=True)
    for note in notes:
        name = note["nombre"].replace("\n", " ").replace("\r", " ").replace("\t", " ")
        table.add_row(str(note["id"]), Text(name), Text(note["creada_en"]))
    Console().print(table)


@app.command("ver", help="Consultar una nota por ID o buscar por nombre completo o parcial.")
def get_note(
    referencia: Annotated[str | None, typer.Argument(help="ID o nombre de la nota.")] = None,
    nombre: Annotated[str | None, typer.Option(help="Buscar por nombre, incluso si es numérico.")] = None,
):
    if referencia is not None and nombre is not None:
        raise typer.BadParameter("Usá una referencia o --nombre, no ambos.")
    if nombre is None and referencia is not None and referencia.isascii() and referencia.isdigit():
        if int(referencia) < 1:
            raise typer.BadParameter("El ID debe ser mayor que cero.")
        show_note(request("GET", f"/notas/{int(referencia)}"))
        return
    query = nombre if nombre is not None else referencia
    if query is None:
        query = typer.prompt("Nombre o parte del nombre")
    if not query.strip():
        raise typer.BadParameter("La búsqueda no puede estar vacía.")
    notes = request("GET", "/notas", params={"nombre": query})
    if not notes:
        typer.echo("No se encontraron notas con ese nombre.")
        raise typer.Exit(1)
    if len(notes) == 1:
        show_note(notes[0])
        return
    from .selector import SelectionUnavailable

    try:
        selected = select_note(notes)
    except SelectionUnavailable as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(2) from exc
    if selected is None:
        typer.echo("Consulta cancelada.")
        return
    show_note(selected)


@app.command("editar", help="Editar una nota por ID; sin opciones, abre el editor con el texto actual.")
def update_note(
    note_id: Annotated[int, typer.Argument(min=1, help="ID de la nota que se editará.")],
    nombre: Annotated[str | None, typer.Option(help="Nuevo nombre; si se omite, conserva el actual.")] = None,
    texto: Annotated[str | None, typer.Option(help="Nuevo contenido de la nota.")] = None,
) -> None:
    note = request("GET", f"/notas/{note_id}")
    if nombre is None and texto is None:
        from .editor import EditorUnavailable

        try:
            texto = edit_text(note["texto"])
        except EditorUnavailable as exc:
            typer.echo(f"Error: {exc}", err=True)
            raise typer.Exit(2) from exc
        if texto is None:
            typer.echo("Edición cancelada. No se guardaron cambios.")
            return
    try:
        data = NoteCreate(
            nombre=nombre if nombre is not None else note["nombre"],
            texto=texto if texto is not None else note["texto"],
        )
    except ValidationError:
        typer.echo("Error: el nombre y el texto no pueden estar vacíos ni contener solo espacios.", err=True)
        raise typer.Exit(2)
    show_note(request("PUT", f"/notas/{note_id}", json=data.model_dump()))


@app.command("eliminar", help="Eliminar permanentemente una nota por ID.")
def delete_note(
    note_id: Annotated[int, typer.Argument(min=1, help="ID de la nota que se eliminará.")],
    forsar: Annotated[bool, typer.Option("--forsar", help="Eliminar sin pedir confirmación.")] = False,
) -> None:
    if not forsar:
        note = request("GET", f"/notas/{note_id}")
        if not typer.confirm(f"¿Eliminar permanentemente la nota {note_id} ({note['nombre']})?", default=False):
            typer.echo("Eliminación cancelada.")
            return
    request("DELETE", f"/notas/{note_id}")
    typer.echo(f"Nota {note_id} eliminada.")


@app.command("servidor", help="Mantener la API encendida; Ctrl+C para detenerla.")
def server():
    import uvicorn
    from .api import create_app
    from .config import HOST, PORT
    typer.echo(f"API disponible en http://{HOST}:{PORT}. Ctrl+C para detenerla.")
    uvicorn.run(create_app(), host=HOST, port=PORT)
