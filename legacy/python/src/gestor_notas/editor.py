"""Editor de texto reutilizable, independiente de notas, HTTP y almacenamiento."""

import sys

from prompt_toolkit import Application
from prompt_toolkit.enums import EditingMode
from prompt_toolkit.key_binding import KeyBindings, KeyPressEvent
from prompt_toolkit.layout import HSplit, Layout
from prompt_toolkit.widgets import Label, TextArea


class EditorUnavailable(RuntimeError):
    """No hay una terminal interactiva donde mostrar el editor."""


def edit_text(initial_text: str = "", *, title: str = "Texto de la nota") -> str | None:
    """Editar texto y devolverlo con Ctrl+S/F2; devolver None al cancelar.

    ``initial_text`` permite reutilizar el editor con contenido existente.
    No guarda datos: el llamador decide cómo validar y utilizar el resultado.
    Las cadenas vacías se distinguen de una cancelación.
    """
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise EditorUnavailable(
            "El editor necesita una terminal interactiva. "
            "Ejecutá el comando en una terminal o proporcioná --texto."
        )

    area = TextArea(
        text=initial_text,
        multiline=True,
        line_numbers=True,
        scrollbar=True,
        wrap_lines=True,
    )
    bindings = KeyBindings()

    @bindings.add("c-s", eager=True)
    @bindings.add("f2", eager=True)
    def submit(event: KeyPressEvent) -> None:
        event.app.exit(result=area.text)

    @bindings.add("c-c", eager=True)
    @bindings.add("c-q", eager=True)
    def cancel(event: KeyPressEvent) -> None:
        event.app.exit(result=None)

    def position() -> str:
        document = area.document
        return (
            f"Línea {document.cursor_position_row + 1}, "
            f"columna {document.cursor_position_col + 1}"
        )

    layout = HSplit([
        Label(title),
        area,
        Label("Enter: nueva línea | Flechas: mover | Retroceso/Supr: borrar"),
        Label("Ctrl+S o F2: enviar | Ctrl+C o Ctrl+Q: cancelar"),
        Label(position),
    ])
    application: Application[str | None] = Application(
        layout=Layout(layout, focused_element=area),
        key_bindings=bindings,
        editing_mode=EditingMode.EMACS,
        full_screen=True,
    )
    try:
        return application.run()
    except (EOFError, KeyboardInterrupt):
        return None
