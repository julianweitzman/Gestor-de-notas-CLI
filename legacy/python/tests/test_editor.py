import io

import pytest
from prompt_toolkit.application import create_app_session
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput

from gestor_notas_cli import editor


class Terminal(io.StringIO):
    def isatty(self) -> bool:
        return True


@pytest.fixture
def terminal(monkeypatch):
    with create_pipe_input() as pipe:
        with create_app_session(input=pipe, output=DummyOutput()):
            def run_editor(keys, initial_text="", *, title="Texto de la nota"):
                pipe.send_text(keys)
                # pytest restaura la captura entre setup y la llamada al test.
                with monkeypatch.context() as terminal_patch:
                    terminal_patch.setattr(editor.sys, "stdin", Terminal())
                    terminal_patch.setattr(editor.sys, "stdout", Terminal())
                    return editor.edit_text(initial_text, title=title)
            yield run_editor


def test_multiline_unicode_is_preserved(terminal):
    assert terminal("Título ñ\r\rTexto 😊\r\x13") == "Título ñ\n\nTexto 😊\n"


def test_move_edit_previous_lines_and_submit(terminal):
    keys = (
        "uno\rdos"  # Escribir dos líneas.
        "\x1b[A\x1b[H"  # Subir e ir al inicio.
        "!\x1b[C\x7f\x1b[3~"  # Insertar, mover, retroceder y suprimir.
        "\x1b[F\rnueva"  # Fin y nueva línea en medio del texto.
        "\x1b[B\x1b[F\rfin\x13"  # Bajar, fin, nueva línea y enviar.
    )
    assert terminal(keys) == "!o\nnueva\ndos\nfin"


def test_backspace_can_join_lines(terminal):
    assert terminal("uno\rdos\x1b[H\x7f\x13") == "unodos"


def test_prefilled_text_can_be_edited_and_f2_submits(terminal):
    assert terminal("Nueva \x1b[B\x1b[F!\x1bOQ", "Primera\nSegunda", title="Editar nota") == "Nueva Primera\nSegunda!"


def test_bracketed_paste_preserves_multiple_lines(terminal):
    assert terminal("\x1b[200~Uno\nDos\nTres\x1b[201~\x13") == "Uno\nDos\nTres"


@pytest.mark.parametrize("cancel_key", ["\x03", "\x11"])
def test_cancel_does_not_return_partial_text(terminal, cancel_key):
    assert terminal("Sin guardar\rSegunda línea" + cancel_key, "Original") is None


def test_empty_submission_is_different_from_cancellation(terminal):
    assert terminal("\x13") == ""


def test_noninteractive_input_has_actionable_error(monkeypatch):
    monkeypatch.setattr(editor.sys, "stdin", io.StringIO("texto"))
    with pytest.raises(editor.EditorUnavailable, match="--texto"):
        editor.edit_text()
