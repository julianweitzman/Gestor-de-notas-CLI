# CLI Python histórica

`gestor_notas_cli/` conserva la implementación anterior de la CLI con Typer, Rich y prompt_toolkit: comandos, editor, selector y gestión del servidor. La CLI principal está en `cli/Notas.Cli/` y se distribuye como `notas.exe`.

Este código se utiliza para pruebas de regresión y para comparar tiempos de arranque. No forma parte del paquete Python del backend ni registra el comando `notas`.

Para ejecutarlo desde la raíz del repositorio, con las dependencias de prueba instaladas:

```powershell
.\.venv\Scripts\python -m pip install -e ".[test]"
$env:PYTHONPATH = (Resolve-Path .\legacy).Path
.\.venv\Scripts\python -m gestor_notas_cli --help
```

Las pruebas configuran esta ruta automáticamente mediante `pyproject.toml`. El benchmark también la configura para el proceso de referencia:

```powershell
.\.venv\Scripts\python tools/benchmark_cli.py
```

La API, los modelos, la configuración y SQLite permanecen en `src/gestor_notas/`. La implementación histórica importa esos modelos y esa configuración; no duplica ni migra los datos.
