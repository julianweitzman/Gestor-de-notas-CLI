"""Editor de texto reutilizable, independiente de notas, HTTP y almacenamiento."""

import sys

from prompt_toolkit import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.enums import EditingMode
from prompt_toolkit.filters import has_focus, vi_navigation_mode
from prompt_toolkit.key_binding import KeyBindings, KeyPressEvent
from prompt_toolkit.key_binding.vi_state import InputMode
from prompt_toolkit.layout import HSplit, Layout
from prompt_toolkit.layout.containers import ConditionalContainer
from prompt_toolkit.widgets import Label, TextArea


class EditorUnavailable(RuntimeError):
    """No hay una terminal interactiva donde mostrar el editor."""


def edit_text(initial_text: str = "", *, title: str = "Texto de la nota", vim: bool = False) -> str | None:
    """Editar texto y devolverlo con Ctrl+S/F2; devolver None al cancelar.

    ``initial_text`` permite reutilizar el editor con contenido existente.
    ``vim`` habilita modos normal/inserción y comandos :wq, :q y :q!.
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
    command = TextArea(height=1, multiline=False, prompt=":")
    message = ""

    def execute_command(buffer: Buffer) -> bool:
        nonlocal message
        value = buffer.text.strip()
        if value == "wq":
            application.exit(result=area.text)
        elif value == "q!" or (value == "q" and area.text == initial_text):
            application.exit(result=None)
        elif value == "q":
            message = "Hay cambios sin guardar. Usá :wq para guardar o :q! para cancelar."
        else:
            message = "Comando desconocido. Usá :wq, :q o :q!."
        application.layout.focus(area)
        application.vi_state.input_mode = InputMode.NAVIGATION
        return False

    command.accept_handler = execute_command

    @bindings.add(":", filter=vi_navigation_mode & has_focus(area), eager=True)
    def open_command(event: KeyPressEvent) -> None:
        nonlocal message
        message = ""
        command.text = ""
        event.app.layout.focus(command)
        event.app.vi_state.input_mode = InputMode.INSERT

    @bindings.add("escape", filter=has_focus(command), eager=True)
    def close_command(event: KeyPressEvent) -> None:
        event.app.layout.focus(area)
        event.app.vi_state.input_mode = InputMode.NAVIGATION

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
        modes = {InputMode.NAVIGATION: "NORMAL", InputMode.INSERT: "INSERCIÓN",
                 InputMode.REPLACE: "REEMPLAZO", InputMode.REPLACE_SINGLE: "REEMPLAZO"}
        return (
            (f"Vim: {modes.get(application.vi_state.input_mode, 'VISUAL')} | " if vim else "")
            + f"Línea {document.cursor_position_row + 1}, "
            f"columna {document.cursor_position_col + 1}"
        )

    layout = HSplit([
        Label(title),
        area,
        Label("i: insertar | Esc: modo normal | h/j/k/l: mover | :wq: guardar | :q!: cancelar"
              if vim else "Enter: nueva línea | Flechas: mover | Retroceso/Supr: borrar"),
        Label("Ctrl+S o F2: enviar | Ctrl+C o Ctrl+Q: cancelar"),
        ConditionalContainer(command, filter=has_focus(command)),
        Label(lambda: message),
        Label(position),
    ])
    application: Application[str | None] = Application(
        layout=Layout(layout, focused_element=area),
        key_bindings=bindings,
        editing_mode=EditingMode.VI if vim else EditingMode.EMACS,
        full_screen=True,
    )

    def initialize_mode() -> None:
        if vim:
            application.vi_state.input_mode = InputMode.NAVIGATION

    try:
        return application.run(pre_run=initialize_mode)
    except (EOFError, KeyboardInterrupt):
        return None
