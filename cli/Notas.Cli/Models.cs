using System.Text.Json.Serialization;

namespace Notas.Cli;

public sealed record Note(
    [property: JsonPropertyName("id")] long Id,
    [property: JsonPropertyName("nombre")] string Nombre,
    [property: JsonPropertyName("texto")] string Texto,
    [property: JsonPropertyName("creada_en")] DateTimeOffset CreadaEn);

public sealed record NoteInput(
    [property: JsonPropertyName("nombre")] string Nombre,
    [property: JsonPropertyName("texto")] string Texto);

public sealed record Health(
    [property: JsonPropertyName("app")] string App,
    [property: JsonPropertyName("protocol_version")] int ProtocolVersion);

[JsonSourceGenerationOptions(RespectNullableAnnotations = true, RespectRequiredConstructorParameters = true)]
[JsonSerializable(typeof(Note))]
[JsonSerializable(typeof(Note[]))]
[JsonSerializable(typeof(NoteInput))]
[JsonSerializable(typeof(Health))]
internal partial class NotesJson : JsonSerializerContext;

public sealed class CliException(string message, int exitCode = 1) : Exception(message)
{
    public int ExitCode { get; } = exitCode;
}
