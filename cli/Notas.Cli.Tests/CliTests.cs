using System.CommandLine;
using System.Net;
using System.Text;
using System.Text.Json;
using Notas.Cli;

[assembly: CollectionBehavior(DisableTestParallelization = true)]

namespace Notas.Cli.Tests;

public sealed class CliTests
{
    private const string NoteJson = """{"id":1,"nombre":"Idea ñ","texto":"Uno\nDos 😊","creada_en":"2026-01-01T00:00:00Z"}""";

    private sealed class Handler(Func<HttpRequestMessage, HttpResponseMessage> respond) : HttpMessageHandler
    {
        public List<(string Method, string Path, string? Body)> Calls { get; } = [];
        protected override async Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken ct)
        {
            Calls.Add((request.Method.Method, request.RequestUri!.PathAndQuery,
                request.Content is null ? null : await request.Content.ReadAsStringAsync(ct)));
            return respond(request);
        }
    }

    private sealed class Interaction : IUserInteraction
    {
        public string Answer { get; set; } = "Idea ñ";
        public string? Edited { get; set; } = "Texto\n😊";
        public string? Initial { get; private set; }
        public bool Confirmed { get; set; }
        public bool CancelSelection { get; set; }
        public int EditCalls { get; private set; }
        public string Ask(string prompt) => Answer;
        public bool Confirm(string prompt) => Confirmed;
        public string? Edit(string initialText = "") { EditCalls++; Initial = initialText; return Edited; }
        public Note? Select(Note[] notes) => CancelSelection ? null : notes[^1];
    }

    private static HttpResponseMessage Json(string body, HttpStatusCode code = HttpStatusCode.OK) =>
        new(code) { Content = new StringContent(body, Encoding.UTF8, "application/json") };

    private static RootCommand App(Handler handler, Interaction ui)
    {
        var http = new HttpClient(handler) { BaseAddress = new Uri("http://test") };
        return new CliApplication(new NotesClient(http, _ => Task.CompletedTask), ui,
            _ => Task.CompletedTask).Build();
    }

    private static Task<int> Run(RootCommand app, params string[] args) =>
        app.Parse(args).InvokeAsync(new InvocationConfiguration { EnableDefaultExceptionHandler = false });

    [Fact]
    public async Task CreatePreservesUnicodeAndExplicitTextBypassesEditor()
    {
        var handler = new Handler(_ => Json(NoteJson, HttpStatusCode.Created));
        var ui = new Interaction();
        Assert.Equal(0, await Run(App(handler, ui), "crear", "--texto", "Uno\nDos 😊"));
        var call = Assert.Single(handler.Calls);
        using var json = JsonDocument.Parse(call.Body!);
        Assert.Equal("Idea ñ", json.RootElement.GetProperty("nombre").GetString());
        Assert.Equal("Uno\nDos 😊", json.RootElement.GetProperty("texto").GetString());
        Assert.Equal(0, ui.EditCalls);
    }

    [Fact]
    public async Task CancelledOrBlankCreationNeverSendsHttp()
    {
        var handler = new Handler(_ => throw new Exception("No debe enviar"));
        var ui = new Interaction { Edited = null };
        var app = App(handler, ui);
        Assert.Equal(0, await Run(app, "crear", "--nombre", "Idea"));
        ui.Edited = "\n  ";
        var error = await Assert.ThrowsAsync<CliException>(() => Run(app, "crear", "--nombre", "Idea"));
        Assert.Equal(2, error.ExitCode);
        Assert.Empty(handler.Calls);
    }

    [Fact]
    public async Task EditPrefillsEditorAndPreservesExistingName()
    {
        var handler = new Handler(_ => Json(NoteJson));
        var ui = new Interaction();
        await Run(App(handler, ui), "editar", "1");
        Assert.Equal("Uno\nDos 😊", ui.Initial);
        Assert.Equal(new[] { "GET", "PUT" }, handler.Calls.Select(c => c.Method));
        using var json = JsonDocument.Parse(handler.Calls[1].Body!);
        Assert.Equal("Idea ñ", json.RootElement.GetProperty("nombre").GetString());
        Assert.Equal(ui.Edited, json.RootElement.GetProperty("texto").GetString());
    }

    [Fact]
    public async Task CancellingEditDoesNotWrite()
    {
        var handler = new Handler(_ => Json(NoteJson));
        await Run(App(handler, new Interaction { Edited = null }), "editar", "1");
        Assert.Equal("GET", Assert.Single(handler.Calls).Method);
    }

    [Fact]
    public async Task NumericNamesAndAmbiguousSearchesUseSelection()
    {
        var handler = new Handler(_ => Json($"[{NoteJson},{NoteJson.Replace("\"id\":1", "\"id\":2")} ]"));
        var ui = new Interaction { CancelSelection = true };
        await Run(App(handler, ui), "ver", "--nombre", "123");
        Assert.Equal("/notas?nombre=123", Assert.Single(handler.Calls).Path);
    }

    [Theory]
    [InlineData("0")]
    [InlineData("-1")]
    [InlineData("999999999999999999999")]
    public async Task InvalidIdsFailBeforeHttp(string id)
    {
        var handler = new Handler(_ => throw new Exception("No debe enviar"));
        var error = await Assert.ThrowsAsync<CliException>(() => Run(App(handler, new Interaction()), "ver", "--", id));
        Assert.Equal(2, error.ExitCode);
        Assert.Empty(handler.Calls);
    }

    [Fact]
    public async Task ConflictingSearchInputsFailBeforeHttp()
    {
        var handler = new Handler(_ => throw new Exception("No debe enviar"));
        var error = await Assert.ThrowsAsync<CliException>(() =>
            Run(App(handler, new Interaction()), "ver", "1", "--nombre", "Idea"));
        Assert.Equal(2, error.ExitCode);
        Assert.Empty(handler.Calls);
    }

    [Theory]
    [InlineData(false, false, 1)]
    [InlineData(true, false, 2)]
    [InlineData(false, true, 1)]
    public async Task DeleteHonorsConfirmationAndForce(bool confirmed, bool force, int requests)
    {
        var handler = new Handler(r => r.Method == HttpMethod.Delete ?
            new(HttpStatusCode.NoContent) : Json(NoteJson));
        var args = force ? new[] { "eliminar", "1", "--forsar" } : ["eliminar", "1"];
        await Run(App(handler, new Interaction { Confirmed = confirmed }), args);
        Assert.Equal(requests, handler.Calls.Count);
        Assert.Equal(confirmed || force, handler.Calls.Any(c => c.Method == "DELETE"));
    }

    [Theory]
    [InlineData("crear", "guardado")]
    [InlineData("editar", "editado")]
    [InlineData("eliminar", "eliminado")]
    public async Task UncertainWritesAreNeverRetried(string command, string warning)
    {
        var handler = new Handler(r => r.Method == HttpMethod.Get ? Json(NoteJson) :
            throw new HttpRequestException("Conexión interrumpida"));
        var app = App(handler, new Interaction());
        var args = command switch
        {
            "crear" => new[] { "crear", "--nombre", "Idea", "--texto", "x" },
            "editar" => ["editar", "1", "--texto", "x"],
            _ => ["eliminar", "1", "--forsar"]
        };
        var error = await Assert.ThrowsAsync<CliException>(() => Run(app, args));
        Assert.Contains("podría haberse " + warning, error.Message);
        Assert.Single(handler.Calls, c => c.Method != "GET");
    }

    [Theory]
    [InlineData(404, "No existe")]
    [InlineData(409, "Ya existe")]
    [InlineData(422, "no son válidos")]
    public async Task ApiErrorsHaveSpanishMessages(int status, string message)
    {
        var handler = new Handler(_ => Json("{}", (HttpStatusCode)status));
        var error = await Assert.ThrowsAsync<CliException>(() => Run(App(handler, new Interaction()), "ver", "1"));
        Assert.Contains(message, error.Message);
    }

    [Theory]
    [InlineData("null")]
    [InlineData("{}")]
    [InlineData("HTML")]
    public async Task MalformedResponsesHaveReadableErrors(string json)
    {
        var handler = new Handler(_ => Json(json));
        var error = await Assert.ThrowsAsync<CliException>(() => Run(App(handler, new Interaction()), "ver", "1"));
        Assert.Contains("No se pudo completar", error.Message);
    }

    [Fact]
    public async Task SqliteIdsAreNotLimitedTo32Bits()
    {
        var handler = new Handler(_ => Json(NoteJson.Replace("\"id\":1", "\"id\":3000000000")));
        await Run(App(handler, new Interaction()), "ver", "3000000000");
        Assert.Equal("/notas/3000000000", Assert.Single(handler.Calls).Path);
    }

    [Theory]
    [InlineData("{}")]
    [InlineData("{\"app\":\"other\",\"protocol_version\":1}")]
    [InlineData("{\"app\":\"gestor-notas\",\"protocol_version\":2}")]
    [InlineData("HTML")]
    public async Task ForeignServicesAreRejected(string identity)
    {
        var handler = new Handler(_ => Json(identity));
        await using var backend = new Backend(new HttpClient(handler) { BaseAddress = new Uri("http://test") });
        var error = await Assert.ThrowsAsync<CliException>(() => backend.EnsureAsync(default));
        Assert.Contains("ocupado", error.Message);
        Assert.Single(handler.Calls);
    }

    [Fact]
    public async Task BackendChecksHealthOnlyOncePerSession()
    {
        var handler = new Handler(_ => Json("""{"app":"gestor-notas","protocol_version":1}"""));
        await using var backend = new Backend(new HttpClient(handler) { BaseAddress = new Uri("http://test") });
        await backend.EnsureAsync(default);
        await backend.EnsureAsync(default);
        Assert.Single(handler.Calls);
    }

    [Fact]
    public async Task InterruptedHealthProbeCanRecoverWithoutStartingAnotherServer()
    {
        var attempts = 0;
        var handler = new Handler(_ => ++attempts == 1
            ? throw new HttpRequestException(HttpRequestError.ResponseEnded, "Conexión cerrada")
            : Json("""{"app":"gestor-notas","protocol_version":1}"""));
        await using var backend = new Backend(new HttpClient(handler) { BaseAddress = new Uri("http://test") });
        await backend.EnsureAsync(default);
        Assert.Equal(2, handler.Calls.Count);
    }

    [Fact]
    public async Task BrokenHealthProbeHasBoundedRetries()
    {
        var handler = new Handler(_ => throw new HttpRequestException(HttpRequestError.ResponseEnded, "Conexión cerrada"));
        await using var backend = new Backend(new HttpClient(handler) { BaseAddress = new Uri("http://test") });
        var error = await Assert.ThrowsAsync<CliException>(() => backend.EnsureAsync(default));
        Assert.Contains("no responde correctamente", error.Message);
        Assert.Equal(2, handler.Calls.Count);
    }
}
