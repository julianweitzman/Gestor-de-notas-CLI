[CmdletBinding()]
param(
    [ValidateSet('Instalar', 'Desinstalar')]
    [string]$Accion = 'Instalar',
    [string]$Python
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = $PSScriptRoot
$VenvPath = Join-Path $ProjectRoot '.venv'
$VenvPython = Join-Path $VenvPath 'Scripts\python.exe'
$Notas = Join-Path $VenvPath 'Scripts\notas.exe'

function Invoke-Checked {
    param([string]$Executable, [string[]]$Arguments)

    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "El comando '$Executable $($Arguments -join ' ')' fallo (codigo $LASTEXITCODE)."
    }
}

try {
    if ($Accion -eq 'Desinstalar') {
        if (-not (Test-Path -LiteralPath $VenvPython -PathType Leaf)) {
            Write-Host 'No hay un entorno .venv instalado por este proyecto.'
            exit 0
        }
        Invoke-Checked -Executable $VenvPython -Arguments @(
            '-m', 'pip', 'uninstall', '--yes', 'gestor-de-tarjetas'
        )
        Write-Host 'CLI desinstalada de .venv. Se conservan tus notas, el entorno y sus dependencias.'
        exit 0
    }

    $VersionCheck = 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)'
    if (-not (Test-Path -LiteralPath $VenvPython -PathType Leaf)) {
        $PythonArguments = @()
        if ($Python) {
            $PythonCommand = $Python
        } elseif (Get-Command py -ErrorAction SilentlyContinue) {
            $PythonCommand = 'py'
            $PythonArguments = @('-3')
        } elseif (Get-Command python -ErrorAction SilentlyContinue) {
            $PythonCommand = 'python'
        } else {
            throw 'No se encontro Python. Instala Python 3.11 o posterior y vuelve a ejecutar este script.'
        }
        & $PythonCommand @PythonArguments -c $VersionCheck
        if ($LASTEXITCODE -ne 0) {
            throw 'Se requiere Python 3.11 o posterior. Podes elegirlo con -Python C:\ruta\python.exe.'
        }
        Invoke-Checked -Executable $PythonCommand -Arguments ($PythonArguments + @('-m', 'venv', $VenvPath))
    }

    & $VenvPython -c $VersionCheck
    if ($LASTEXITCODE -ne 0) {
        throw 'El entorno .venv requiere Python 3.11 o posterior. Revisa su instalacion de Python.'
    }
    Invoke-Checked -Executable $VenvPython -Arguments @(
        '-m', 'pip', 'install', '--editable', $ProjectRoot
    )
    Invoke-Checked -Executable $Notas -Arguments @('--help')
    Write-Host ''
    Write-Host 'CLI instalada. Para usarla sin activar el entorno:'
    Write-Host ('  & "{0}" listar' -f $Notas)
    Write-Host 'Para habilitar el comando notas en esta terminal:'
    Write-Host ('  & "{0}"' -f (Join-Path $VenvPath 'Scripts\Activate.ps1'))
    Write-Host 'Si PowerShell bloquea la activacion: Set-ExecutionPolicy -Scope Process Bypass'
} catch {
    [Console]::Error.WriteLine("Error: $($_.Exception.Message)")
    exit 1
}
