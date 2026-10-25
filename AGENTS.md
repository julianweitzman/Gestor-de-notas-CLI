# Repository Guidelines

## Estructura y arquitectura

El backend requiere Python 3.11+ y vive en `src/gestor_notas/`: FastAPI, Pydantic, servicio y SQLite. La CLI está en `cli/Notas.Cli/`, requiere .NET 10 y usa System.CommandLine, Spectre.Console, HttpClient y Terminal.Gui. Los módulos Python de CLI se conservan como referencia para pruebas, sin registrar un comando instalable.

La CLI accede exclusivamente por HTTP a la API. No agregues consultas SQLite a los comandos. Cada comando reutiliza una sesión de servidor y solo cierra su proceso propio. Conservá los comandos, opciones, mensajes en español y escucha local.

## Instalación y desarrollo

Desde la raíz, en PowerShell:

```powershell
.\instalar.ps1 -Pruebas
.\.publish\windows\notas.exe --help
dotnet test cli/Notas.Cli.Tests
.\.venv\Scripts\python -m pytest -q --basetemp=.test-tmp-local
```

`instalar.ps1` instala el backend editable y publica la CLI Release con runtime incluido. C# requiere recompilar; Python requiere reiniciar la API. `servidor` mantiene la API hasta Ctrl+C. Documentación HTTP: `http://127.0.0.1:8000/docs`.

## Estilo y nombres

Usá cuatro espacios, nombres `snake_case` para módulos y funciones, `PascalCase` para clases y `UPPER_SNAKE_CASE` para constantes. Añadí anotaciones de tipos en interfaces nuevas. Mantené mensajes y documentación para usuarios en español. Utilizá consultas SQL parametrizadas y fechas UTC. No hay formateador ni linter configurados; seguí el estilo existente.

En C# usá las convenciones de .NET: tipos, métodos y propiedades en `PascalCase`; variables locales y campos privados en `camelCase`.

## Pruebas

Usá xUnit para la CLI C# y pytest para backend, integración y regresiones históricas. En Python usá archivos `test_*.py` con funciones `test_*`. Cubrí validación, contratos HTTP, persistencia, opciones y preguntas de la CLI, y cierre del servidor propio sin afectar servidores existentes. Utilizá `tmp_path`, `monkeypatch` y `NOTAS_DATA_DIR` para aislar datos. La prueba de integración necesita el comando instalado y omite su ejecución si el puerto 8000 tiene un servicio activo. No existe un umbral de cobertura configurado.

## Commits y pull requests

Siempre que modifiques código, al finalizar los cambios y ejecutar las verificaciones correspondientes, debés hacer un commit y un push al remoto. No esperes a que el usuario lo solicite por separado.

Escribí mensajes breves y descriptivos y agrupá cambios relacionados. Cada PR debe explicar el comportamiento resultante, indicar pruebas ejecutadas y vincular una incidencia cuando corresponda. Actualizá el README si cambian comandos o configuración.

## Datos y configuración

SQLite y los registros se guardan fuera del repositorio mediante `platformdirs`. Configurá `NOTAS_DATA_DIR` igual para servidor y CLI. No incluyas bases, registros, `.venv/`, `bin/`, `obj/` ni `.publish/` en commits. Conservá los lockfiles NuGet. Conservá la escucha local: la API no tiene autenticación.
