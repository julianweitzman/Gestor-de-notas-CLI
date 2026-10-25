# Gestor de notas

CLI en C# (.NET 10), API con FastAPI (Python 3.11+) y almacenamiento local SQLite. La CLI usa System.CommandLine, Spectre.Console y Terminal.Gui; se comunica exclusivamente por HTTP con el backend.

## Instalación en Windows x64

Necesitás Python 3.11+, el SDK de .NET 10 y acceso a Internet para instalar y publicar. Desde PowerShell en la raíz del proyecto:

```powershell
.\instalar.ps1
.\.publish\windows\notas.exe --help
```

El instalador crea `.venv`, instala el backend en modo editable y publica la CLI Release con runtime incluido en `.publish\windows`. Para usar el ejecutable publicado no hace falta instalar .NET ni activar el entorno virtual. Python sigue siendo necesario para el backend. Conservá el repositorio y el entorno en su ubicación.

La carpeta publicada se agrega al PATH de la terminal actual. En otras terminales usí la ruta completa o agregá esa carpeta a tu PATH. Para elegir Python:

```powershell
.\instalar.ps1 -Python 'C:\ruta\python.exe'
```

Para instalar también las herramientas de prueba:

```powershell
.\instalar.ps1 -Pruebas
```

Para desinstalar la publicación y el entorno de este proyecto:

```powershell
.\instalar.ps1 -Accion Desinstalar
```

Cerrá primero los comandos y servidores iniciados desde esta instalación. La desinstalación conserva las notas y registros externos al repositorio.

### Actualización desde la CLI Python

El paquete Python ya no registra un comando `notas`: el instalador publica el ejecutable C#. Si tenías una instalación anterior en otro entorno o con pipx, desinstalala con la herramienta correspondiente o usí la ruta completa de la CLI nueva para evitar confundir ambos comandos. No hace falta migrar la base SQLite.

## Comandos

Los ejemplos suponen que `notas` está en el PATH; también podés usar `.\.publish\windows\notas.exe`.

```powershell
notas crear --nombre "Idea" --texto "Contenido"
notas crear
notas listar
notas ver 1
notas ver "Idea"
notas ver --nombre "123"
notas editar 1
notas editar "Idea" --texto "Contenido actualizado"
notas editar --buscar-nombre "123" --nombre "Nombre nuevo"
notas eliminar 1
notas eliminar 1 --forsar
notas servidor
```

- `crear`: pregunta el nombre cuando falta; sin `--texto` abre el editor multilínea.
- `listar`: muestra ID, nombre y fecha UTC en una tabla, desde la nota más reciente.
- `ver [referencia] [--nombre NOMBRE]`: interpreta referencias numéricas como IDs; el resto busca por nombre completo o parcial. `--nombre` permite buscar un nombre numérico. Sin referencia pregunta la búsqueda.
- `editar [referencia] [--buscar-nombre BUSQUEDA] [--nombre NUEVO] [--texto TEXTO]`: conserva los campos omitidos. Sin nuevo nombre ni texto abre el editor con el contenido actual.
- `eliminar ID`: pide confirmación negativa por defecto; acepta `s`, `sí` o `y`. `--forsar` conserva la opción existente y omite la confirmación.
- `servidor`: inicia la API y la mantiene hasta Ctrl+C. Si ya existe un servidor compatible, informa su dirección y lo deja funcionando.

Cada comando acepta `--help`. Los errores de argumentos o validación devuelven código 2; los errores HTTP o de servidor devuelven 1; el éxito y la cancelación voluntaria devuelven 0.

### Editor y selección

El editor Terminal.Gui permite escribir varias líneas, moverse con flechas y borrar con Retroceso/Supr. Ctrl+S o F2 aceptan el texto; Ctrl+C o Ctrl+Q cancelan sin guardar. Muestra los atajos y la posición del cursor. Conserva los caracteres Unicode y usa saltos de línea LF al aceptar.

Cuando una búsqueda encuentra varias notas, Spectre.Console permite elegir con flechas y Enter; Esc o Ctrl+C cancelan. El editor y el selector requieren entrada y salida de terminal interactivas. Para scripts usí `--texto` y referencias por ID. Si una búsqueda es ambigua con salida redirigida, el error incluye los IDs disponibles.

Nombre y texto no pueden estar vacíos ni contener solo espacios. Los nombres son únicos; se distinguen mayúsculas y espacios. La búsqueda parcial ignora mayúsculas y trata `%` y `_` como texto literal.

## Servidor y datos

La CLI accede a `http://127.0.0.1:8000`. Antes de la primera solicitud de cada comando verifica `/health`: exige aplicación `gestor-notas` y protocolo 1. Si hace falta, inicia Uvicorn sin ventana, espera hasta 10 segundos y cierra su proceso al finalizar, incluso ante errores o Ctrl+C. Reutiliza una sola sesión para todas las solicitudes del comando. Nunca detiene un servidor existente.

Para evitar el costo de iniciar Python con cada comando, mantené `notas servidor` abierto en otra terminal. La documentación HTTP está en `http://127.0.0.1:8000/docs`. La API solo escucha en la dirección local y no tiene autenticación.

Los datos se guardan en `%LOCALAPPDATA%\gestor-notas`: `notas.sqlite3` y `servidor.log`. También el servidor en primer plano registra su salida en ese archivo. Para seleccionar otra ubicación:

```powershell
$env:NOTAS_DATA_DIR = 'C:\Mis notas'
notas listar
```

Configurá esa variable antes de iniciar el servidor. Cambiarla en una CLI no cambia la base de un servidor que ya está funcionando. Para respaldar o restaurar, detené la API y copiá el archivo SQLite.

El instalador guarda la ruta del intérprete en `backend-python.txt`, junto al ejecutable. `NOTAS_PYTHON` permite reemplazarla por una ruta absoluta. En desarrollo también se reconoce `.venv` en la raíz del proyecto. La CLI nunca consulta SQLite directamente ni reintenta escrituras: ante una respuesta incierta, consultá las notas antes de repetir la operación.

## Contrato HTTP conservado

| Operación | Endpoint | Resultado |
|---|---|---|
| Salud | `GET /health` | Identidad y protocolo |
| Crear | `POST /notas` | 201 con la nota |
| Listar/buscar | `GET /notas?nombre=texto` | Lista de notas completas |
| Consultar | `GET /notas/{id}` | Nota o 404 |
| Editar | `PUT /notas/{id}` | Reemplaza nombre y texto; 200 con la nota |
| Eliminar | `DELETE /notas/{id}` | 204 sin contenido |

Las notas tienen `id`, `nombre`, `texto` y `creada_en`. Crear y editar reciben `nombre` y `texto`. Un nombre repetido devuelve 409; datos inválidos devuelven 422.

## Desarrollo y pruebas

```powershell
.\instalar.ps1 -Pruebas
dotnet test cli/Notas.Cli.Tests
.\.venv\Scripts\python -m pytest -q --basetemp=.test-tmp-local
```

Las pruebas Python incluyen los contratos HTTP, persistencia y el ejecutable C# publicado. `NOTAS_CLI` permite probar otra publicación. Las pruebas que necesitan el puerto 8000 se omiten si está ocupado. Las pruebas históricas de la CLI Python se conservan como referencia de comportamiento; sus dependencias solo se instalan con `[test]`, y esa CLI ya no se distribuye como comando.

Para iterar sin publicar:

```powershell
dotnet run --project cli/Notas.Cli -- listar
```

Los cambios del backend editable se reflejan al reiniciar la API; los de C# requieren recompilar. Las versiones NuGet se fijan en `packages.lock.json`.

### Native AOT

La publicación predeterminada es convencional, con runtime incluido. Se comprobó que Native AOT compila, pero Terminal.Gui 1.19 emite advertencias de trimming y AOT: no se lo adopta como publicación predeterminada sin validar el editor completo. Para experimentar necesitás las herramientas C++ de Visual Studio:

```powershell
.\instalar.ps1 -NativeAot
```

Esa opción reemplaza la publicación normal. Para volver, ejecutá el instalador sin `-NativeAot`.

Para comparar arranques con la referencia Python instalada mediante `[test]`:

```powershell
.\.venv\Scripts\python tools/benchmark_cli.py
```

El informe distingue ayuda y listado con API encendida y apagada, y usa datos temporales.

Medianas de cinco ejecuciones en Windows x64, Python 3.13 y .NET 10 (25/10/2026), sin otras compilaciones simultáneas:

| Operación | CLI Python | CLI C# |
|---|---:|---:|
| Ayuda | 1703 ms | 308 ms |
| Listar con API encendida | 1647 ms | 450 ms |
| Listar iniciando y cerrando la API | 3762 ms | 2769 ms |

Estos tiempos dependen del equipo. Mantener la API encendida evita el costo de iniciar el backend Python.
