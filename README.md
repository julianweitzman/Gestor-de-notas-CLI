# Gestor de notas

El backend sigue en Python 3.11 o posterior: FastAPI, modelos Pydantic y persistencia SQLite. La CLI está migrando a C#; solamente la CLI Python anterior está archivada en `legacy/python/`.

## Backend Python

Desde la raíz, en PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[test]"
.\.venv\Scripts\python -m uvicorn gestor_notas.api:create_app --factory --host 127.0.0.1 --port 8000
```

La API permanece en primer plano hasta Ctrl+C. Documentación HTTP: http://127.0.0.1:8000/docs. La escucha es local y no incluye autenticación. La instalación del backend no instala el comando `notas` ni las dependencias de la CLI.

## Estructura

- `src/gestor_notas/`: API, modelos, lógica, almacenamiento, configuración y utilidades de ciclo de vida del servidor.
- `tests/`: pruebas del backend, persistencia y servidor.
- `legacy/python/`: CLI Python, editor, selector y pruebas de la CLI, conservados como referencia para C#.

La CLI se comunica con el backend exclusivamente por HTTP. El contrato HTTP y los datos del backend se conservan.

## Archivos locales

Se guardan `notas.sqlite3` y `servidor.log` en el directorio de datos del usuario obtenido con `platformdirs` para `gestor-notas` (en Windows, normalmente `%LOCALAPPDATA%\gestor-notas`). No dependen del directorio de trabajo. Podés elegir otra ubicación con `NOTAS_DATA_DIR`; iniciá servidor y CLI con la misma configuración. Para respaldar las notas, detené la API y copiá el archivo SQLite.

## API

- `POST /notas`: JSON con `nombre` y `texto`; devuelve la nota con estado 201, o 409 si el nombre ya existe.
- `GET /notas`: notas completas, desde la más reciente; `?nombre=texto` filtra por nombre completo o parcial sin distinguir mayúsculas.
- `GET /notas/{id}`: nota completa, o 404 si no existe; IDs no positivos devuelven 422.
- `PUT /notas/{id}`: reemplaza `nombre` y `texto` (ambos obligatorios) y devuelve la nota con estado 200; 404 si no existe, 409 si el nombre ya está ocupado y 422 para datos inválidos.
- `DELETE /notas/{id}`: elimina permanentemente la nota y devuelve 204 sin contenido; 404 si no existe y 422 para IDs no positivos.
- `GET /health`: identidad de aplicación y versión de protocolo.

Cada nota devuelve `id`, `nombre`, `texto` y `creada_en`. No incluye sincronización.

## Pruebas del backend

```powershell
.\.venv\Scripts\python -m pytest -q
```

Las pruebas usan directorios temporales y no modifican las notas del usuario.

## CLI Python archivada

La [documentación anterior](legacy/python/README.md) y la [guía de uso](legacy/python/Documentacion.md) se conservan para la migración. La nueva CLI C# todavía no está incluida en esta rama.
