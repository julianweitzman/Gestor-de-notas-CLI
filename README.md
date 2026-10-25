# Gestor de notas

CLI con Typer, API con FastAPI y almacenamiento local SQLite. Requiere Python 3.11 o posterior.

## Instalación en PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[test]"
.\.venv\Scripts\notas --help
```

Con el entorno activado, los ejemplos se ejecutan directamente como `notas`:

```powershell
notas crear --nombre "Idea" --texto "Preparar el proyecto"
notas crear
notas crear --nombre "Pendiente"
notas listar
notas ver 1
```

Si omitís el nombre, la CLI lo pregunta. Si omitís `--texto`, abre un editor de terminal con varias líneas: Enter agrega una línea, las flechas permiten moverse y Retroceso/Supr borran caracteres. Podés volver a líneas anteriores y corregirlas. Ctrl+S o F2 envían el contenido; Ctrl+C o Ctrl+Q cancelan sin guardar. Los atajos aparecen en pantalla. `--texto` sigue disponible para automatizar y no abre el editor.

Nombre y texto no pueden estar vacíos ni contener solo espacios. Se permiten nombres repetidos. El ID es automático y la fecha de creación se guarda en UTC.

La CLI accede exclusivamente por HTTP a `127.0.0.1:8000`. Si la API no está encendida, la inicia sin abrir otra ventana y la cierra al terminar el comando, también ante errores. Si ya está encendida, la reutiliza y la deja funcionando. No se repiten automáticamente las creaciones ante errores de conexión.

Para mantener la API encendida, ejecutá en otra terminal:

```powershell
notas servidor
```

Detenela con Ctrl+C. Documentación HTTP: http://127.0.0.1:8000/docs mientras está encendida. No incluye autenticación y está pensada para uso local de una persona.

## Archivos locales

Se guardan `notas.sqlite3` y `servidor.log` en el directorio de datos del usuario obtenido con `platformdirs` para `gestor-notas` (en Windows, normalmente `%LOCALAPPDATA%\gestor-notas`). No dependen del directorio de trabajo. Podés elegir otra ubicación con `NOTAS_DATA_DIR`; iniciá servidor y CLI con la misma configuración. Para respaldar las notas, detené la API y copiá el archivo SQLite.

## API

- `POST /notas`: JSON con `nombre` y `texto`; devuelve la nota con estado 201.
- `GET /notas`: notas completas, desde la más reciente.
- `GET /notas/{id}`: nota completa, o 404 si no existe; IDs no positivos devuelven 422.
- `GET /health`: identidad de aplicación y versión de protocolo.

Cada nota devuelve `id`, `nombre`, `texto` y `creada_en`. No incluye edición, eliminación, búsqueda ni sincronización.

## Pruebas

```powershell
.\.venv\Scripts\python -m pytest
```

Las pruebas usan directorios temporales y no modifican las notas del usuario.
