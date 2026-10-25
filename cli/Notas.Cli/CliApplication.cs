using System.CommandLine;
using System.Globalization;
using Spectre.Console;

namespace Notas.Cli;

public sealed class CliApplication(NotesClient client, IUserInteraction ui, Func<CancellationToken, Task> serve)
{
    public RootCommand Build()
    {
        var root = new RootCommand("Creá, consultá, editá y eliminá tus notas locales.");
        var name = new Option<string?>("--nombre") { Description = "Nombre de la nota." };
        var text = new Option<string?>("--texto") { Description = "Contenido; si se omite, abre el editor." };
        var create = new Command("crear", "Crear una nota.") { name, text };
        create.SetAction(async (parsed, ct) =>
        {
            var title = parsed.GetValue(name) ?? ui.Ask("Nombre:");
            var content = parsed.GetValue(text) ?? ui.Edit();
            if (content is null) { Console.WriteLine("Creación cancelada. No se guardó ninguna nota."); return; }
            Show(await client.CreateAsync(Validate(title, content), ct));
        });
        root.Subcommands.Add(create);

        var list = new Command("listar", "Listar las notas desde la más reciente.");
        list.SetAction(async (_, ct) =>
        {
            var notes = await client.ListAsync(null, ct);
            if (notes.Length == 0) { Console.WriteLine("No hay notas guardadas."); return; }
            var table = new Table().Border(TableBorder.Rounded).ShowRowSeparators();
            table.AddColumn(new TableColumn("ID").RightAligned().NoWrap());
            table.AddColumn("Nombre");
            table.AddColumn(new TableColumn("Creada (UTC)").NoWrap());
            foreach (var note in notes)
                table.AddRow(new Text(note.Id.ToString(CultureInfo.InvariantCulture)),
                    new Text(TerminalInteraction.SingleLine(note.Nombre)), new Text(FormatDate(note.CreadaEn)));
            AnsiConsole.Write(table);
        });
        root.Subcommands.Add(list);

        var reference = Reference();
        var searchName = new Option<string?>("--nombre") { Description = "Buscar por nombre, incluso si es numérico." };
        var view = new Command("ver", "Consultar una nota por ID o buscar por nombre.") { reference, searchName };
        view.SetAction(async (parsed, ct) =>
        {
            var note = await ResolveAsync(parsed.GetValue(reference), parsed.GetValue(searchName), ct);
            if (note is null) Console.WriteLine("Consulta cancelada.");
            else Show(note);
        });
        root.Subcommands.Add(view);

        var editReference = Reference();
        var newName = new Option<string?>("--nombre") { Description = "Nuevo nombre." };
        var newText = new Option<string?>("--texto") { Description = "Nuevo contenido." };
        var findName = new Option<string?>("--buscar-nombre") { Description = "Buscar por nombre, incluso si es numérico." };
        var edit = new Command("editar", "Editar por ID o nombre; sin opciones, abre el editor.")
            { editReference, newName, newText, findName };
        edit.SetAction(async (parsed, ct) =>
        {
            var note = await ResolveAsync(parsed.GetValue(editReference), parsed.GetValue(findName), ct);
            if (note is null) { CancelEdit(); return; }
            var title = parsed.GetValue(newName);
            var content = parsed.GetValue(newText);
            if (title is null && content is null)
            {
                content = ui.Edit(note.Texto);
                if (content is null) { CancelEdit(); return; }
            }
            Show(await client.UpdateAsync(note.Id, Validate(title ?? note.Nombre, content ?? note.Texto), ct));
        });
        root.Subcommands.Add(edit);

        var id = new Argument<long>("id") { Description = "ID de la nota que se eliminará." };
        var force = new Option<bool>("--forsar") { Description = "Eliminar sin pedir confirmación." };
        var delete = new Command("eliminar", "Eliminar permanentemente una nota por ID.") { id, force };
        delete.SetAction(async (parsed, ct) =>
        {
            var noteId = parsed.GetValue(id);
            if (noteId < 1) throw new CliException("El ID debe ser mayor que cero.", 2);
            if (!parsed.GetValue(force))
            {
                var note = await client.GetAsync(noteId, ct);
                if (!ui.Confirm($"¿Eliminar permanentemente la nota {noteId} ({note.Nombre})?"))
                { Console.WriteLine("Eliminación cancelada."); return; }
            }
            await client.DeleteAsync(noteId, ct);
            Console.WriteLine($"Nota {noteId} eliminada.");
        });
        root.Subcommands.Add(delete);

        var server = new Command("servidor", "Mantener la API encendida; Ctrl+C para detenerla.");
        server.SetAction(async (_, ct) => await serve(ct));
        root.Subcommands.Add(server);
        return root;
    }

    private async Task<Note?> ResolveAsync(string? reference, string? name, CancellationToken ct)
    {
        if (reference is not null && name is not null)
            throw new CliException("Usá una referencia o una opción de búsqueda por nombre, no ambas.", 2);
        if (name is null && reference is not null && IsNumericReference(reference))
        {
            if (!long.TryParse(reference, out var id) || id < 1)
                throw new CliException("El ID debe ser mayor que cero y estar dentro del rango admitido.", 2);
            return await client.GetAsync(id, ct);
        }
        var query = name ?? reference ?? ui.Ask("Nombre o parte del nombre:");
        if (string.IsNullOrWhiteSpace(query)) throw new CliException("La búsqueda no puede estar vacía.", 2);
        var notes = await client.ListAsync(query, ct);
        return notes.Length switch
        {
            0 => throw new CliException("No se encontraron notas con ese nombre."),
            1 => notes[0],
            _ => ui.Select(notes)
        };
    }

    private static bool IsNumericReference(string value)
    {
        var digits = value.AsSpan().TrimStart('-');
        return !digits.IsEmpty && digits.IndexOfAnyExceptInRange('0', '9') < 0;
    }

    private static Argument<string?> Reference() => new("referencia")
    { Arity = ArgumentArity.ZeroOrOne, Description = "ID o nombre completo o parcial de la nota." };

    private static NoteInput Validate(string name, string text)
    {
        if (string.IsNullOrWhiteSpace(name) || string.IsNullOrWhiteSpace(text))
            throw new CliException("El nombre y el texto no pueden estar vacíos ni contener solo espacios.", 2);
        return new NoteInput(name, text);
    }

    private static void CancelEdit() => Console.WriteLine("Edición cancelada. No se guardaron cambios.");
    private static string FormatDate(DateTimeOffset date) => date.UtcDateTime.ToString("yyyy-MM-ddTHH:mm:ss.ffffff'Z'", CultureInfo.InvariantCulture);
    private static void Show(Note note) => Console.WriteLine(
        $"ID: {note.Id}\nNombre: {note.Nombre}\nCreada: {FormatDate(note.CreadaEn)}\nTexto:\n{note.Texto}");
}
