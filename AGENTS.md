# Repository Guidelines

## Estructura y arquitectura

El backend requiere Python 3.11 o posterior y sigue activo en `src/gestor_notas/`: `api.py` implementa FastAPI; `models.py`, los modelos Pydantic; `service.py`, la lógica de notas; `storage.py`, SQLite; `server.py`, las utilidades de ciclo de vida del servidor; y `config.py`, las rutas y configuración. Solamente la CLI Python, el editor y el selector están archivados en `legacy/python/src/gestor_notas_cli/`, durante la migración de la CLI a C#.

La CLI accede exclusivamente por HTTP a la API. Conservá esta separación: no agregues consultas SQLite a los comandos. Las pruebas del backend están en `tests/`; las de la CLI, en `legacy/python/tests/`. El `pyproject.toml` raíz instala solamente el backend; el paquete archivado instala el comando `notas`. No hay recursos gráficos ni frontend.

## Instalación y desarrollo

Desde la raíz, en PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[test]"
.\.venv\Scripts\python -m uvicorn gestor_notas.api:create_app --factory --host 127.0.0.1 --port 8000
.\.venv\Scripts\python -m pytest -q
```

La instalación editable refleja los cambios del código. Uvicorn mantiene la API en primer plano hasta Ctrl+C. La documentación HTTP está en `http://127.0.0.1:8000/docs` mientras funciona. Para instalar y probar la CLI archivada, consultá `legacy/python/README.md`.

## Estilo y nombres

Usá cuatro espacios, nombres `snake_case` para módulos y funciones, `PascalCase` para clases y `UPPER_SNAKE_CASE` para constantes. Añadí anotaciones de tipos en interfaces nuevas. Mantené mensajes y documentación para usuarios en español. Utilizá consultas SQL parametrizadas y fechas UTC. No hay formateador ni linter configurados; seguí el estilo existente.

## Pruebas

Usá pytest y archivos `test_*.py` con funciones `test_*`. Cubrí validación, contratos HTTP, persistencia, opciones y preguntas de la CLI, y cierre del servidor propio sin afectar servidores existentes. Utilizá `tmp_path`, `monkeypatch` y `NOTAS_DATA_DIR` para aislar datos. La prueba de integración necesita el comando instalado y omite su ejecución si el puerto 8000 tiene un servicio activo. No existe un umbral de cobertura configurado.

## Commits y pull requests

Siempre que modifiques código, al finalizar los cambios y ejecutar las verificaciones correspondientes, debés hacer un commit y un push al remoto. No esperes a que el usuario lo solicite por separado.

El repositorio todavía no tiene commits; no hay una convención histórica. Escribí mensajes breves y descriptivos y agrupá cambios relacionados. Cada PR debe explicar el comportamiento resultante, indicar pruebas ejecutadas y vincular una incidencia cuando corresponda. Actualizá el README si cambian comandos o configuración.

## Datos y configuración

SQLite y los registros se guardan fuera del repositorio mediante `platformdirs`. Configurá `NOTAS_DATA_DIR` igual para servidor y CLI. No incluyas bases, registros ni `.venv/` en commits. Conservá la escucha local: la API no tiene autenticación.
