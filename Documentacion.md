# Guía de uso y funcionamiento de la CLI

Este gestor permite crear, listar y consultar notas desde una terminal. Los datos se guardan localmente en SQLite y permanecen disponibles después de cerrar el programa o reiniciar la computadora.

## 1. Instalación

Necesitás Python 3.11 o posterior. Abrí PowerShell en la carpeta del proyecto y ejecutá:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e .
.\.venv\Scripts\notas --help
```

El primer comando crea un entorno virtual y el segundo instala el proyecto con sus dependencias. La opción `-e` permite que los cambios del código se reflejen sin reinstalarlo.

Los ejemplos siguientes usan la ruta del ejecutable para que no sea necesario activar el entorno virtual. Ejecutalos desde la raíz del proyecto. Si activás el entorno, podés reemplazar `.\.venv\Scripts\notas` por `notas`.

## 2. Crear una nota

### Pasar todos los datos en el comando

```powershell
.\.venv\Scripts\notas crear --nombre "Compras" --texto "Comprar pan y leche"
```

La CLI muestra la nota guardada. Ejemplo ilustrativo:

```text
ID: 1
Nombre: Compras
Creada: 2026-10-24T15:30:00Z
Texto:
Comprar pan y leche
```

El ID y la fecha reales se generan automáticamente. La fecha está en UTC, por lo que puede diferir de tu hora local.

### Ingresar los datos mediante preguntas

```powershell
.\.venv\Scripts\notas crear
```

La CLI solicita primero `Nombre` y después `Texto`. Escribí cada valor y presioná Enter.

También podés combinar ambas formas:

```powershell
.\.venv\Scripts\notas crear --nombre "Pendientes"
```

En ese caso, solo se solicita el texto que falta. También funciona si proporcionás únicamente `--texto`.

### Escribir texto con varias líneas

Las preguntas interactivas reciben una línea por campo. Para guardar varias líneas, pasá una cadena multilínea de PowerShell:

```powershell
$contenidoNota = @'
Primera tarea
Segunda tarea
Tercera tarea
'@
.\.venv\Scripts\notas crear --nombre "Tareas" --texto $contenidoNota
```

### Reglas de las notas

- Nombre y texto son obligatorios y no pueden estar vacíos ni contener solamente espacios.
- Se permiten nombres repetidos; el ID identifica cada nota.
- El texto conserva los saltos de línea.
- El ID es un entero positivo generado por SQLite y la fecha de creación la genera la API.

## 3. Listar las notas

```powershell
.\.venv\Scripts\notas listar
```

Muestra ID, nombre y fecha de creación, desde la nota más reciente. El listado no muestra el contenido completo. Si no hay notas, aparece:

```text
No hay notas guardadas.
```

## 4. Consultar una nota

Usá el ID obtenido al crear la nota o al listar las existentes:

```powershell
.\.venv\Scripts\notas ver 1
```

Muestra ID, nombre, fecha y texto completo. Reemplazá `1` por el ID que corresponda. Si no existe, se informa el error; el ID debe ser un entero mayor que cero.

## 5. Consultar la ayuda

```powershell
.\.venv\Scripts\notas --help
.\.venv\Scripts\notas crear --help
.\.venv\Scripts\notas ver --help
```

Cada comando acepta `--help` para consultar sus opciones o argumentos.

## 6. Cómo funciona internamente

El recorrido de una operación es el siguiente:

```text
Terminal → CLI (Typer) → HTTP (HTTPX) → API (FastAPI)
                                         ↓
                                  Servicio de notas
                                         ↓
                                  SQLite local
```

Typer interpreta los comandos y solicita los campos omitidos. Para crear una nota, la CLI valida los datos con Pydantic y envía nombre y texto a la API. La API vuelve a validar la entrada, genera la fecha UTC y utiliza el servicio y el repositorio para guardar la nota mediante una consulta SQL parametrizada. SQLite asigna el ID. La respuesta vuelve a la CLI, que la presenta en la terminal.

La CLI nunca consulta directamente la base de datos. La API atiende únicamente en `http://127.0.0.1:8000` y no requiere conexión a Internet para las operaciones de notas.

### Inicio automático del servidor

Antes de operar, la CLI consulta `/health` para comprobar la identidad y la versión del servicio:

1. Si la API ya está encendida y es compatible, la reutiliza y la deja funcionando.
2. Si no está disponible, inicia Uvicorn con el mismo intérprete Python, sin abrir otra ventana en Windows.
3. Espera hasta 10 segundos a que el servidor esté disponible y ejecuta la operación.
4. Al terminar, incluso ante un error o una interrupción normal con Ctrl+C, cierra únicamente el proceso que inició para ese comando.

Cerrar la API no elimina las notas: ya están guardadas en el archivo SQLite.

### Mantener la API encendida

Para evitar iniciar un servidor en cada operación, ejecutá en una terminal:

```powershell
.\.venv\Scripts\notas servidor
```

Dejá esa terminal abierta y usá los comandos de notas en otra. Detené el servidor con Ctrl+C en la primera terminal. Mientras esté encendido, podés abrir `http://127.0.0.1:8000/docs` para consultar y probar los endpoints.

| Método | Ruta | Función |
| --- | --- | --- |
| `POST` | `/notas` | Crear una nota con `nombre` y `texto`; devuelve estado 201. |
| `GET` | `/notas` | Obtener las notas completas, desde la más reciente. |
| `GET` | `/notas/{note_id}` | Consultar una nota; devuelve 404 si no existe. |
| `GET` | `/health` | Consultar la identidad y la versión del protocolo. |

## 7. Dónde se guardan los datos

El proyecto utiliza `platformdirs` para elegir el directorio de datos del usuario. En Windows normalmente es:

```text
%LOCALAPPDATA%\gestor-notas
```

Los archivos son:

- `notas.sqlite3`: base de datos con las notas.
- `servidor.log`: salida y errores de los servidores iniciados automáticamente. El servidor manual muestra su salida en la terminal.

Podés consultar las rutas que utiliza tu instalación:

```powershell
.\.venv\Scripts\python -c "from gestor_notas.config import database_path, log_path; print(database_path()); print(log_path())"
```

Para elegir otra carpeta, configurá una ruta absoluta antes de ejecutar los comandos:

```powershell
$env:NOTAS_DATA_DIR = "C:\MisNotas"
.\.venv\Scripts\notas listar
```

Si mantenés la API encendida manualmente, configurá la misma variable en ambas terminales y reiniciá el servidor para cambiar su ubicación. La base utilizada siempre es la que abrió el servidor. Cambiar esta variable no mueve las notas anteriores: selecciona otra ubicación de almacenamiento.

Para realizar un respaldo, detené el servidor y copiá `notas.sqlite3`. Para restaurarlo, con el servidor detenido, colocá la copia en el directorio de datos elegido.

## 8. Problemas frecuentes

| Problema | Qué hacer |
| --- | --- |
| No se encuentra `notas`. | Usá `.\.venv\Scripts\notas` desde la raíz del proyecto y comprobá que realizaste la instalación. |
| Nombre o texto vacío. | Ingresá contenido que no sea solamente espacios. |
| No existe una nota con ese ID. | Ejecutá `listar` y verificá el ID. |
| Puerto 8000 ocupado o versión incompatible. | Revisá qué servicio está usando el puerto; la CLI no lo detiene. El puerto no tiene una opción de configuración en esta versión. |
| La API no inicia o tarda demasiado. | Consultá la ruta del registro indicada en el error y ejecutá `servidor` manualmente para ver su salida. |
| Falló la conexión durante una creación. | Consultá `listar` antes de repetirla: la nota podría haberse guardado aunque no llegara la respuesta. La CLI no reintenta esa creación automáticamente. |
| No aparecen notas guardadas anteriormente. | Verificá `NOTAS_DATA_DIR` y la ubicación usada por el servidor que está encendido. |

## 9. Alcance actual

La aplicación está pensada para uso local de una persona. Permite crear, listar y consultar notas; todavía no incluye edición, eliminación, búsqueda ni sincronización. La API no tiene autenticación y escucha en la dirección local `127.0.0.1`.
