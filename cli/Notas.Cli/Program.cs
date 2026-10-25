using System.Text;
using System.CommandLine;
using Notas.Cli;

Console.InputEncoding = Encoding.UTF8;
Console.OutputEncoding = new UTF8Encoding(false);
using var interrupts = new CancellationTokenSource();
ConsoleCancelEventHandler cancel = (_, eventArgs) =>
{
    eventArgs.Cancel = true;
    interrupts.Cancel();
};
Console.CancelKeyPress += cancel;
await using var backend = new Backend();
using var http = new HttpClient(new SocketsHttpHandler { UseProxy = false, AllowAutoRedirect = false })
{
    BaseAddress = new Uri(Backend.BaseUrl), Timeout = TimeSpan.FromSeconds(5)
};
var application = new CliApplication(new NotesClient(http, backend.EnsureAsync),
    new TerminalInteraction(), backend.ServeAsync);
var parsed = application.Build().Parse(args.Length == 0 ? ["--help"] : args);
if (parsed.Errors.Count > 0)
{
    foreach (var error in parsed.Errors) Console.Error.WriteLine("Error: " + error.Message);
    return 2;
}
try
{
    return await parsed.InvokeAsync(new InvocationConfiguration
    {
        EnableDefaultExceptionHandler = false,
        ProcessTerminationTimeout = TimeSpan.FromSeconds(10)
    }, interrupts.Token);
}
catch (CliException ex)
{
    Console.Error.WriteLine("Error: " + ex.Message);
    return ex.ExitCode;
}
catch (OperationCanceledException)
{
    Console.WriteLine("Operación cancelada.");
    return 0;
}
catch (Exception ex) when (ex is IOException or UnauthorizedAccessException or System.ComponentModel.Win32Exception)
{
    Console.Error.WriteLine("Error: " + ex.Message);
    return 1;
}
finally
{
    Console.CancelKeyPress -= cancel;
}
