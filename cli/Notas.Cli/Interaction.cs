using Spectre.Console;
using Spectre.Console.Rendering;
using Terminal.Gui;
using GuiApplication = Terminal.Gui.Application;

namespace Notas.Cli;

public interface IUserInteraction
{
    string Ask(string prompt);
    bool Confirm(string prompt);
    string? Edit(string initialText = "");
    Note? Select(Note[] notes);
}

public sealed class TerminalInteraction : IUserInteraction
{
    public string Ask(string prompt)
    {
        if (!Console.IsInputRedirected && !Console.IsOutputRedirected)
            return AnsiConsole.Ask<string>(Markup.Escape(prompt));
        Console.Write(prompt + " ");
        return Console.ReadLine() ?? throw new CliException("No se recibió una respuesta.", 2);
    }

    public bool Confirm(string prompt)
    {
        var answer = Ask(prompt + " [s/N]").Trim().ToLowerInvariant();
        return answer is "s" or "si" or "sí" or "y" or "yes";
    }

    public string? Edit(string initialText = "")
    {
        RequireTerminal("El editor necesita una terminal interactiva. Proporcioná --texto para automatizar.");
        return TextEditor.Edit(initialText);
    }

    public Note? Select(Note[] notes)
    {
        RequireTerminal("Hay varias coincidencias. Usá una terminal para seleccionar con flechas y Enter, " +
            "o consultá con 'notas ver ID': " + string.Join(", ", notes.Select(n => $"{n.Id}: {n.Nombre}")));
        try
        {
            return new SelectionPrompt<Note>()
                .Title("Seleccionar nota (Esc o Ctrl+C: cancelar)")
                .UseConverter(n => Markup.Escape($"{SingleLine(n.Nombre)} (ID: {n.Id})"))
                .AddChoices(notes)
                .Show(new CancellableConsole(AnsiConsole.Console));
        }
        catch (OperationCanceledException) { return null; }
    }

    public static string SingleLine(string text) =>
        text.Replace('\r', ' ').Replace('\n', ' ').Replace('\t', ' ');

    private static void RequireTerminal(string message)
    {
        if (Console.IsInputRedirected || Console.IsOutputRedirected)
            throw new CliException(message, 2);
    }

    // Spectre.Console 0.54 no tiene cancelación con Esc en SelectionPrompt.
    private sealed class CancellableConsole(IAnsiConsole inner) : IAnsiConsole
    {
        public Profile Profile => inner.Profile;
        public IAnsiConsoleCursor Cursor => inner.Cursor;
        public IAnsiConsoleInput Input { get; } = new CancellableInput(inner.Input);
        public IExclusivityMode ExclusivityMode => inner.ExclusivityMode;
        public RenderPipeline Pipeline => inner.Pipeline;
        public void Clear(bool home) => inner.Clear(home);
        public void Write(IRenderable renderable) => inner.Write(renderable);
    }

    private sealed class CancellableInput(IAnsiConsoleInput inner) : IAnsiConsoleInput
    {
        public bool IsKeyAvailable() => inner.IsKeyAvailable();
        public ConsoleKeyInfo? ReadKey(bool intercept) => Check(inner.ReadKey(intercept));
        public async Task<ConsoleKeyInfo?> ReadKeyAsync(bool intercept, CancellationToken cancellationToken) =>
            Check(await inner.ReadKeyAsync(intercept, cancellationToken));

        private static ConsoleKeyInfo? Check(ConsoleKeyInfo? key)
        {
            if (key?.Key == ConsoleKey.Escape ||
                key?.Key == ConsoleKey.C && key?.Modifiers.HasFlag(ConsoleModifiers.Control) == true)
                throw new OperationCanceledException();
            return key;
        }
    }
}

public static class TextEditor
{
    public static string? Edit(string initialText)
    {
        string? result = null;
        GuiApplication.UseSystemConsole = true;
        GuiApplication.Init();
        try
        {
            using var window = new Window("Texto de la nota") { Width = Dim.Fill(), Height = Dim.Fill() };
            var editor = new TextView
            {
                X = 0, Y = 0, Width = Dim.Fill(), Height = Dim.Fill(3),
                Text = initialText, WordWrap = true
            };
            var help = new Label("Enter: nueva línea | Flechas: mover | Retroceso/Supr: borrar\n" +
                "Ctrl+S o F2: enviar | Ctrl+C o Ctrl+Q: cancelar")
            { X = 0, Y = Pos.AnchorEnd(3), Width = Dim.Fill(), Height = 2 };
            var position = new Label("Línea 1, columna 1")
                { X = 0, Y = Pos.AnchorEnd(1), Width = Dim.Fill(), Height = 1 };
            editor.UnwrappedCursorPosition += point =>
                position.Text = $"Línea {point.Y + 1}, columna {point.X + 1}";
            window.Add(editor, help, position);
            var controller = new EditorController(editor, () => GuiApplication.RequestStop());
            GuiApplication.RootKeyEvent = controller.Handle;
            editor.SetFocus();
            GuiApplication.Run(window);
            result = controller.Result;
            return result;
        }
        finally
        {
            GuiApplication.RootKeyEvent = null;
            GuiApplication.Shutdown();
        }
    }
}

internal sealed class EditorController(TextView editor, Action stop)
{
    private char? highSurrogate;
    public string? Result { get; private set; }

    public bool Handle(KeyEvent key)
    {
        if (key.Key is (Key.CtrlMask | Key.S) or Key.F2)
        {
            Result = (editor.Text.ToString() ?? "").Replace("\r\n", "\n");
            stop();
            return true;
        }
        if (key.Key is (Key.CtrlMask | Key.C) or (Key.CtrlMask | Key.Q))
        {
            stop();
            return true;
        }
        // El driver de consola entrega los emoji como dos eventos UTF-16.
        // TextView necesita recibir el par completo para no crear un Rune inválido.
        var code = (uint)(key.Key & Key.CharMask);
        if (code is >= 0xD800 and <= 0xDBFF)
        {
            highSurrogate = (char)code;
            return true;
        }
        if (code is >= 0xDC00 and <= 0xDFFF)
        {
            if (highSurrogate is { } high)
                editor.ProcessKey(new KeyEvent((Key)char.ConvertToUtf32(high, (char)code), new KeyModifiers()));
            highSurrogate = null;
            return true;
        }
        highSurrogate = null;
        return false;
    }
}
