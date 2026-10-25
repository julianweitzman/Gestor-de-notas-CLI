using System.Diagnostics;
using System.Net.Http.Json;
using System.Net;
using System.Net.Sockets;
using System.Text.Json;

namespace Notas.Cli;

public sealed class Backend(HttpClient? healthClient = null) : IAsyncDisposable
{
    public const string BaseUrl = "http://127.0.0.1:8000";
    private Process? process;
    private StreamWriter? log;
    private Task[] pumps = [];
    private bool ready;
    private readonly HttpClient probe = healthClient ?? new(new SocketsHttpHandler
    {
        UseProxy = false,
        AllowAutoRedirect = false,
        ConnectCallback = ConnectAsync
    }) { BaseAddress = new Uri(BaseUrl), Timeout = TimeSpan.FromSeconds(2) };

    public static string DataDirectory => Path.GetFullPath(
        Environment.GetEnvironmentVariable("NOTAS_DATA_DIR") is { Length: > 0 } value
            ? ExpandHome(value)
            : Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "gestor-notas"));

    public static string LogPath => Path.Combine(DataDirectory, "servidor.log");

    private static async ValueTask<Stream> ConnectAsync(SocketsHttpConnectionContext context, CancellationToken ct)
    {
        var socket = new Socket(SocketType.Stream, ProtocolType.Tcp) { NoDelay = true };
        using var timeout = CancellationTokenSource.CreateLinkedTokenSource(ct);
        timeout.CancelAfter(TimeSpan.FromMilliseconds(50));
        try
        {
            await socket.ConnectAsync(context.DnsEndPoint, timeout.Token);
            return new NetworkStream(socket, ownsSocket: true);
        }
        catch (OperationCanceledException) when (!ct.IsCancellationRequested)
        {
            socket.Dispose();
            // Distinguir el plazo de conexión del plazo de lectura de /health.
            throw new SocketException((int)SocketError.TimedOut);
        }
        catch
        {
            socket.Dispose();
            throw;
        }
    }

    private static string ExpandHome(string value) => value == "~" ?
        Environment.GetFolderPath(Environment.SpecialFolder.UserProfile) :
        value.StartsWith("~/") || value.StartsWith("~\\") ?
            Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), value[2..]) : value;

    public static string FindPython()
    {
        if (Environment.GetEnvironmentVariable("NOTAS_PYTHON") is { Length: > 0 } configured)
            return Path.GetFullPath(configured);
        var config = Path.Combine(AppContext.BaseDirectory, "backend-python.txt");
        if (File.Exists(config))
            return Path.GetFullPath(File.ReadAllText(config).Trim());
        for (var dir = new DirectoryInfo(AppContext.BaseDirectory); dir is not null; dir = dir.Parent)
        {
            if (!File.Exists(Path.Combine(dir.FullName, "pyproject.toml"))) continue;
            var python = Path.Combine(dir.FullName, ".venv", OperatingSystem.IsWindows() ? "Scripts/python.exe" : "bin/python");
            if (File.Exists(python)) return python;
        }
        throw new CliException("No se encontró Python del backend. Ejecutá instalar.ps1 o configurá NOTAS_PYTHON con su ruta absoluta.");
    }

    public Task<bool> IsHealthyAsync(CancellationToken ct) => ProbeHealthAsync(ct, retry: true);

    private async Task<bool> ProbeHealthAsync(CancellationToken ct, bool retry)
    {
        try
        {
            using var response = await probe.GetAsync("/health", ct);
            Health? identity;
            try { identity = await response.Content.ReadFromJsonAsync(NotesJson.Default.Health, ct); }
            catch (JsonException) { identity = null; }
            if (response.StatusCode != HttpStatusCode.OK || identity != new Health("gestor-notas", 1))
                throw new CliException("El puerto 8000 está ocupado por otro servicio o una versión incompatible.");
            return true;
        }
        catch (HttpRequestException ex) when (ex.InnerException is SocketException socket &&
            socket.SocketErrorCode is SocketError.ConnectionRefused or SocketError.TimedOut)
        {
            return false;
        }
        catch (HttpRequestException ex) when (retry &&
            (ex.HttpRequestError == HttpRequestError.ResponseEnded ||
             ex.InnerException is SocketException { SocketErrorCode: SocketError.ConnectionReset }))
        {
            // Una API que está cerrándose puede aceptar y cortar la conexión.
            // Repetir solo el sondeo GET; nunca una operación sobre las notas.
            await Task.Delay(100, ct);
            return await ProbeHealthAsync(ct, retry: false);
        }
        catch (Exception ex) when (ex is HttpRequestException || ex is OperationCanceledException && !ct.IsCancellationRequested)
        {
            throw new CliException("El servicio del puerto 8000 no responde correctamente.");
        }
    }

    public async Task EnsureAsync(CancellationToken ct)
    {
        if (ready) return;
        try
        {
            if (!await IsHealthyAsync(ct))
            {
                Start();
                var timer = Stopwatch.StartNew();
                while (true)
                {
                    if (process!.HasExited)
                        throw new CliException("La API terminó antes de estar disponible.");
                    if (await IsHealthyAsync(ct))
                    {
                        await Task.Delay(50, ct);
                        if (process.HasExited)
                            throw new CliException("La API no pudo conservar el puerto 8000.");
                        break;
                    }
                    if (timer.Elapsed > TimeSpan.FromSeconds(10))
                        throw new CliException("La API no estuvo disponible en el tiempo esperado.");
                    await Task.Delay(100, ct);
                }
            }
            ready = true;
        }
        catch (Exception ex) when (ex is CliException or IOException or System.ComponentModel.Win32Exception)
        {
            throw new CliException($"{ex.Message} Registro: {LogPath}. Para iniciarla manualmente, ejecutá 'notas servidor'.");
        }
    }

    private void Start()
    {
        var python = FindPython();
        Directory.CreateDirectory(DataDirectory);
        log = new StreamWriter(new FileStream(LogPath, FileMode.Append, FileAccess.Write, FileShare.ReadWrite))
        { AutoFlush = true };
        var start = new ProcessStartInfo(python)
        {
            UseShellExecute = false, CreateNoWindow = true,
            RedirectStandardInput = true, RedirectStandardOutput = true, RedirectStandardError = true
        };
        foreach (var arg in new[] { "-m", "uvicorn", "gestor_notas.api:create_app", "--factory", "--host", "127.0.0.1", "--port", "8000" })
            start.ArgumentList.Add(arg);
        start.Environment["NOTAS_DATA_DIR"] = DataDirectory;
        start.Environment["PYTHONIOENCODING"] = "utf-8";
        process = Process.Start(start) ?? throw new CliException("No se pudo iniciar la API.");
        process.StandardInput.Close();
        pumps = [CopyLogAsync(process.StandardOutput), CopyLogAsync(process.StandardError)];
    }

    private async Task CopyLogAsync(StreamReader reader)
    {
        while (await reader.ReadLineAsync() is { } line)
        {
            lock (log!) log.WriteLine(line);
        }
    }

    public async Task ServeAsync(CancellationToken ct)
    {
        if (await IsHealthyAsync(ct))
        {
            Console.WriteLine($"La API ya está disponible en {BaseUrl}. Se conserva el servidor existente.");
            return;
        }
        await EnsureAsync(ct);
        if (process is null)
        {
            Console.WriteLine($"La API ya está disponible en {BaseUrl}. Se conserva el servidor existente.");
            return;
        }
        Console.WriteLine($"API disponible en {BaseUrl}. Ctrl+C para detenerla.");
        await WaitForForegroundExitAsync(ct);
        if (process.ExitCode != 0)
            throw new CliException($"La API terminó con código {process.ExitCode}. Registro: {LogPath}.");
    }

    private async Task WaitForForegroundExitAsync(CancellationToken ct)
    {
        if (Console.IsInputRedirected)
        {
            await process!.WaitForExitAsync(ct);
            return;
        }
        // Las pseudoterminales pueden entregar Ctrl+C como carácter en lugar de
        // generar CancelKeyPress. Admitir ambas formas y restaurar la consola.
        var original = Console.TreatControlCAsInput;
        try
        {
            Console.TreatControlCAsInput = true;
            while (!process!.HasExited)
            {
                if (Console.KeyAvailable && Console.ReadKey(intercept: true).KeyChar == '\u0003')
                    throw new OperationCanceledException();
                await Task.Delay(50, ct);
            }
        }
        finally { Console.TreatControlCAsInput = original; }
    }

    public async ValueTask DisposeAsync()
    {
        try
        {
            if (process is not null)
            {
                if (!process.HasExited) process.Kill(entireProcessTree: true);
                await process.WaitForExitAsync();
                await Task.WhenAll(pumps);
            }
        }
        finally
        {
            log?.Dispose();
            process?.Dispose();
            probe.Dispose();
        }
    }
}
