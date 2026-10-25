"""Selección interactiva de coincidencias por nombre."""

import sys

from prompt_toolkit.application import Application, get_app
from prompt_toolkit.key_binding import KeyBindings, KeyPressEvent
from prompt_toolkit.layout import HSplit, Layout
from prompt_toolkit.widgets import Dialog, Label, RadioList


class SelectionUnavailable(RuntimeError):
    """La selección requiere una terminal interactiva."""


class NoteList(RadioList):
    def _handle_enter(self) -> None:
        super()._handle_enter()
        get_app().exit(result=self.current_value)


def select_note(notes: list[dict]) -> dict | None:
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise SelectionUnavailable(
            "Hay varias coincidencias. Usá una terminal para seleccionar con flechas "
            "y Enter, o consultá con 'notas ver ID': "
            + ", ".join(f"{note['id']}: {note['nombre']!r}" for note in notes)
        )
    values = [
        (index, f"{' '.join(note['nombre'].split())} (ID: {note['id']})")
        for index, note in enumerate(notes)
    ]
    choices = NoteList(values)
    bindings = KeyBindings()

    @bindings.add('c-c', eager=True)
    @bindings.add('escape', eager=True)
    def cancel(event: KeyPressEvent) -> None:
        event.app.exit(result=None)

    dialog = Dialog(
        title="Seleccionar nota",
        body=HSplit([
            Label("Flechas: cambiar de nota | Enter: abrir | Esc o Ctrl+C: cancelar"),
            choices,
        ]),
    )
    application: Application[int | None] = Application(
        layout=Layout(dialog, focused_element=choices),
        key_bindings=bindings,
        full_screen=True,
    )
    try:
        index = application.run()
    except (EOFError, KeyboardInterrupt):
        return None
    return notes[index] if index is not None else None
