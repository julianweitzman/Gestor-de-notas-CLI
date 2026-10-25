using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using System.Text.Json.Serialization.Metadata;

namespace Notas.Cli;

public sealed class NotesClient(HttpClient http, Func<CancellationToken, Task> ensureServer)
{
    public Task<Note[]> ListAsync(string? name, CancellationToken ct) =>
        SendAsync(HttpMethod.Get, "/notas" + (name is null ? "" : "?nombre=" + Uri.EscapeDataString(name)),
            null, NotesJson.Default.NoteArray, ct);

    public Task<Note> GetAsync(long id, CancellationToken ct) =>
        SendAsync(HttpMethod.Get, $"/notas/{id}", null, NotesJson.Default.Note, ct);

    public Task<Note> CreateAsync(NoteInput input, CancellationToken ct) =>
        SendAsync(HttpMethod.Post, "/notas", input, NotesJson.Default.Note, ct);

    public Task<Note> UpdateAsync(long id, NoteInput input, CancellationToken ct) =>
        SendAsync(HttpMethod.Put, $"/notas/{id}", input, NotesJson.Default.Note, ct);

    public async Task DeleteAsync(long id, CancellationToken ct) =>
        await SendAsync(HttpMethod.Delete, $"/notas/{id}", null, NotesJson.Default.Note, ct);

    private async Task<T> SendAsync<T>(HttpMethod method, string path, NoteInput? input,
        JsonTypeInfo<T> type, CancellationToken ct)
    {
        await ensureServer(ct);
        using var request = new HttpRequestMessage(method, path);
        if (input is not null)
            request.Content = JsonContent.Create(input, NotesJson.Default.NoteInput);
        try
        {
            using var response = await http.SendAsync(request, ct);
            switch (response.StatusCode)
            {
                case HttpStatusCode.NotFound:
                    throw new CliException("No existe una nota con ese ID.");
                case HttpStatusCode.Conflict:
                    throw new CliException("Ya existe una nota con ese nombre. Elegí otro nombre.");
                case HttpStatusCode.UnprocessableEntity:
                    throw new CliException("Los datos enviados no son válidos.");
                case HttpStatusCode.NoContent:
                    if (method != HttpMethod.Delete) throw new JsonException("Respuesta vacía.");
                    return default!;
            }
            response.EnsureSuccessStatusCode();
            return await response.Content.ReadFromJsonAsync(type, ct)
                ?? throw new JsonException("Respuesta vacía.");
        }
        catch (Exception ex) when (ex is HttpRequestException or JsonException ||
            ex is OperationCanceledException && !ct.IsCancellationRequested)
        {
            var warning = method.Method switch
            {
                "POST" => " La nota podría haberse guardado; consultá 'notas listar' antes de intentar nuevamente.",
                "PUT" => " La nota podría haberse editado; consultá 'notas ver' antes de intentar nuevamente.",
                "DELETE" => " La nota podría haberse eliminado; consultá 'notas listar' para verificarlo.",
                _ => ""
            };
            throw new CliException("No se pudo completar la solicitud a la API." + warning);
        }
    }
}
