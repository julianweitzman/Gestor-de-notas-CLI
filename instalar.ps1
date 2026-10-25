[CmdletBinding()]
param(
    [ValidateSet('Instalar', 'Desinstalar')]
    [string]$Accion = 'Instalar',
    [string]$Python = 'python',
    [switch]$Pruebas,
    [switch]$NativeAot
)

$ErrorActionPreference = 'Stop'
$projectRoot = [System.IO.Path]::GetFullPath($PSScriptRoot)
$environmentPath = Join-Path $projectRoot '.venv'
$publishPath = Join-Path $projectRoot '.publish\windows'

function Invoke-Checked {
    param([string]$Executable, [string[]]$Arguments)
    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "El comando $Executable termino con codigo $LASTEXITCODE."
    }
}

function Remove-ProjectDirectory {
    param([string]$Target)
    if (-not (Test-Path -LiteralPath $Target)) { return }
    $resolvedTarget = (Resolve-Path -LiteralPath $Target).Path
    $expectedTarget = [System.IO.Path]::GetFullPath($Target)
    if ($resolvedTarget -ne $expectedTarget -or
        -not $resolvedTarget.StartsWith($projectRoot + '\', [System.StringComparison]::OrdinalIgnoreCase)) {
        throw 'La carpeta a eliminar debe permanecer dentro del proyecto.'
    }
    # No atravesar enlaces o junctions al eliminar un entorno.
    $links = @(Get-Item -LiteralPath $resolvedTarget) + @(Get-ChildItem -LiteralPath $resolvedTarget -Force -Recurse)
    if ($links | Where-Object { $_.Attributes -band [System.IO.FileAttributes]::ReparsePoint }) {
        throw 'No se elimina una carpeta que contiene enlaces o junctions.'
    }
    Remove-Item -LiteralPath $resolvedTarget -Recurse -Force
}

try {
    if ($Accion -eq 'Desinstalar') {
        if (-not (Test-Path -LiteralPath $environmentPath) -and -not (Test-Path -LiteralPath $publishPath)) {
            Write-Output 'No hay un entorno ni una CLI instalados en este proyecto.'
        } else {
            Remove-ProjectDirectory $publishPath
            Remove-ProjectDirectory $environmentPath
            Write-Output 'CLI y entorno desinstalados. Las notas y los registros se conservan.'
        }
        exit 0
    }

    & $Python -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)'
    if ($LASTEXITCODE -ne 0) { throw 'Se requiere Python 3.11 o posterior.' }
    if (-not (Test-Path -LiteralPath $environmentPath)) {
        Invoke-Checked $Python @('-m', 'venv', $environmentPath)
    }
    $backendPython = Join-Path $environmentPath 'Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $backendPython)) { throw 'El entorno no contiene Scripts\python.exe.' }
    $package = if ($Pruebas) { $projectRoot + '[test]' } else { $projectRoot }
    Invoke-Checked $backendPython @('-m', 'pip', 'install', '-e', $package)
    $sdkVersion = & dotnet --version
    if ($LASTEXITCODE -ne 0 -or [int]($sdkVersion.Split('.')[0]) -lt 10) {
        throw 'Se requiere el SDK de .NET 10 o posterior.'
    }
    $publishArguments = @('publish', (Join-Path $projectRoot 'cli\Notas.Cli'), '-c', 'Release',
        '-r', 'win-x64', '--self-contained', 'true', '-o', $publishPath, '-p:RestoreLockedMode=true')
    if ($NativeAot) { $publishArguments += '-p:PublishAot=true' }
    Invoke-Checked 'dotnet' $publishArguments
    [System.IO.File]::WriteAllText((Join-Path $publishPath 'backend-python.txt'), $backendPython,
        [System.Text.UTF8Encoding]::new($false))
    $env:PATH = $publishPath + ';' + $env:PATH
    Write-Output "CLI instalada: $publishPath\notas.exe"
    Write-Output 'En esta terminal podes usar notas. En otra terminal, usa la ruta completa o agrega la carpeta al PATH.'
} catch {
    [Console]::Error.WriteLine('Error: ' + $_.Exception.Message)
    exit 1
}
