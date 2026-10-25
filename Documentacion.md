# Guía de uso y funcionamiento de la CLI

Este gestor permite crear, listar, consultar y eliminar notas desde una terminal. Los datos se guardan localmente en SQLite y permanecen disponibles después de cerrar el programa o reiniciar la computadora.

## 1. Instalación

Necesitás Python 3.11 o posterior y el SDK de .NET 10. Abrí PowerShell en la carpeta del proyecto y ejecutá:

```powershell
.\instalar.ps1
.\.publish\windows\notas.exe --help
```

El instalador prepara el entorno Python del backend y publica la CLI C# con runtime incluido. Los cambios Python se reflejan al reiniciar la API; los cambios C# requieren recompilar.

Los ejemplos siguientes usan la ruta del ejecutable para que no sea necesario activar el entorno virtual. Ejecutalos desde la raíz del proyecto. Si agregás `.publish\windows` al PATH, podés usar `notas`.

## 2. Crear una nota

### Pasar todos los datos en el comando

```powershell
.\.publish\windows\notas.exe crear --nombre "Compras" --texto "Comprar pan y leche"
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
.\.publish\windows\notas.exe crear
```

La CLI solicita `Nombre`. Escribilo y presioná Enter. Después abre un editor de texto en la terminal para escribir el contenido. Enter agrega una línea; para enviar el contenido completo usá Ctrl+S o F2.

También podés combinar ambas formas:

```powershell
.\.publish\windows\notas.exe crear --nombre "Pendientes"
```

En ese caso, abre directamente el editor de texto. Si proporcionás únicamente `--texto`, solo pregunta el nombre y no abre el editor.

### Escribir texto con varias líneas

No necesitás preparar una variable de PowerShell. Ejecutá:

```powershell
.\.publish\windows\notas.exe crear --nombre "Tareas"
```

El editor ocupa la terminal y muestra la posición del cursor y los atajos. Podés escribir directamente y volver a cualquier línea para corregirla.

| Tecla | Acción |
| --- | --- |
| Enter | Insertar una nueva línea en la posición del cursor. |
| Flechas | Mover el cursor, incluso a líneas anteriores. |
| Inicio / Fin | Ir al principio o al final de la línea. |
| Retroceso / Supr | Borrar antes o después del cursor; también permite unir líneas. |
| Ctrl+S o F2 | Enviar todo el contenido y salir del editor. |
| Ctrl+C o Ctrl+Q | Cancelar sin crear la nota. |

Podés pegar texto con varias líneas usando la opción de pegado de tu terminal. El contenido solo se envía después de confirmar; no hay guardado automático. Al salir se restaura la pantalla anterior y, si confirmaste, la CLI valida y crea la nota. Un contenido vacío o compuesto solo por espacios se rechaza sin guardarlo.

Si tu terminal intercepta Ctrl+S, usá F2. El editor necesita una terminal interactiva; para scripts o entrada redirigida, proporcioná `--nombre` y `--texto` explícitamente.

Como alternativa para automatizar, `--texto` sigue aceptando cadenas multilínea de PowerShell:

```powershell
$contenidoNota = @'
Primera tarea
Segunda tarea
Tercera tarea
'@
.\.publish\windows\notas.exe crear --nombre "Tareas" --texto $contenidoNota
```

### Reglas de las notas

- Nombre y texto son obligatorios y no pueden estar vacíos ni contener solamente espacios.
- Los nombres son únicos (se distinguen mayúsculas y espacios); el ID también identifica cada nota.
- El texto conserva los saltos de línea.
- El ID es un entero positivo generado por SQLite y la fecha de creación la genera la API.

## 3. Listar las notas

```powershell
.\.publish\windows\notas.exe listar
```

Muestra ID, nombre y fecha de creación, desde la nota más reciente. El listado no muestra el contenido completo. Si no hay notas, aparece:

```text
No hay notas guardadas.
```

## 4. Consultar una nota

Usá el ID obtenido al crear la nota o al listar las existentes:

```powershell
.\.publish\windows\notas.exe ver 1
```

Muestra ID, nombre, fecha y texto completo. Reemplazá `1` por el ID que corresponda. Si no existe, se informa el error; el ID debe ser un entero mayor que cero.

### Buscar por nombre y seleccionar

```powershell
notas ver "Compras"
notas ver "comp"
notas ver --nombre "123"
notas ver
```

La búsqueda encuentra nombres completos o parciales sin distinguir mayúsculas, incluidos caracteres Unicode. Sin argumento, pregunta qué nombre buscar. Una coincidencia se abre directamente; con varias, muestra una lista: usá las flechas arriba/abajo y Enter para abrir la seleccionada. Ctrl+C o Esc cierran la consulta. En scripts, usá el ID si hay varias coincidencias. `notas ver 1` sigue funcionando; `--nombre` permite buscar nombres numéricos.

`GET /notas?nombre=texto` filtra por nombre; sin filtro sigue listando todas las notas. Crear un nombre repetido devuelve HTTP 409 y un mensaje en la CLI. SQLite garantiza la unicidad incluso ante creaciones simultáneas.

Al abrir una base anterior, los nombres repetidos se migran automáticamente: se conserva el nombre de la nota con menor ID y se agrega ` (2)`, ` (3)`, etc. a las siguientes, evitando nombres ya existentes. No se eliminan notas ni se cambian sus IDs, textos o fechas. Esta migración ocurre una sola vez; si mantenés el servidor encendido, reinicialo para aplicar la actualización.

## 5. Eliminar una nota

Buscá el ID con `listar` y ejecutá:

```powershell
.\.publish\windows\notas.exe eliminar 1
```

La CLI muestra el ID y el nombre de la nota y pide confirmación. Respondé `y` para eliminarla o presioná Enter para cancelar: la respuesta predeterminada es no. Al confirmar, muestra `Nota 1 eliminada.`. La eliminación es permanente y solo afecta a ese ID; después podés volver a crear una nota con el mismo nombre.

Para eliminar sin pedir confirmación, por ejemplo desde un script:

```powershell
.\.publish\windows\notas.exe eliminar 1 --forsar
```

La opción se escribe `--forsar`. El ID es obligatorio y debe ser un entero positivo; este comando no busca por nombre. Si la nota no existe, informa el error y termina con código 1. Un argumento inválido termina con código 2; una eliminación correcta o una cancelación mediante la pregunta termina con código 0.

Si falla la conexión, consultá `listar` antes de repetir la operación: la nota podría haberse eliminado aunque no llegara la respuesta. La CLI no reintenta automáticamente la eliminación. Si tenías `notas servidor` abierto antes de actualizar el código, reinicialo para cargar el nuevo endpoint.

## 6. Consultar la ayuda

```powershell
.\.publish\windows\notas.exe --help
.\.publish\windows\notas.exe crear --help
.\.publish\windows\notas.exe ver --help
.\.publish\windows\notas.exe eliminar --help
```

Cada comando acepta `--help` para consultar sus opciones o argumentos.

## 7. Cómo funciona internamente

El recorrido de una operación es el siguiente:

```text
Terminal → CLI (C#) → HTTP (HttpClient) → API (FastAPI)
                                         ↓
                                  Servicio de notas
                                         ↓
                                  SQLite local
```

System.CommandLine interpreta los comandos. Spectre.Console presenta tablas, preguntas y selección. Terminal.Gui implementa el editor, que devuelve el texto al confirmar o una cancelación. No accede a HTTP ni a SQLite. `editar` reutiliza el editor con el contenido actual.

Después de confirmar, la CLI valida que nombre y texto no estén vacíos y envía nombre y texto a la API. La API vuelve a validar la entrada, genera la fecha UTC y utiliza el servicio y el repositorio para guardar la nota mediante una consulta SQL parametrizada. SQLite asigna el ID. La respuesta vuelve a la CLI, que la presenta en la terminal. Cancelar el editor no inicia la API ni envía una solicitud de creación.

La CLI nunca consulta directamente la base de datos. La API atiende únicamente en `http://127.0.0.1:8000` y no requiere conexión a Internet para las operaciones de notas.

Para eliminar, la CLI consulta primero la nota por HTTP para mostrar su nombre y pedir confirmación; con `--forsar` omite esa consulta y la pregunta. Después envía `DELETE /notas/{note_id}`. El servicio delega en el repositorio, que ejecuta una consulta SQL parametrizada. La API devuelve 204 sin contenido si eliminó la nota, 404 si no existía y 422 si el ID no es válido.

### Inicio automático del servidor

Antes de operar, la CLI consulta `/health` para comprobar la identidad y la versión del servicio:

1. Si la API ya está encendida y es compatible, la reutiliza y la deja funcionando.
2. Si no está disponible, inicia Uvicorn con el Python del backend instalado, sin abrir otra ventana en Windows.
3. Espera hasta 10 segundos a que el servidor esté disponible y ejecuta la operación.
4. Al terminar, incluso ante un error o una interrupción normal con Ctrl+C, cierra únicamente el proceso que inició para ese comando.

Cerrar la API no elimina las notas: ya están guardadas en el archivo SQLite.

### Mantener la API encendida

Para evitar iniciar un servidor en cada operación, ejecutá en una terminal:

```powershell
.\.publish\windows\notas.exe servidor
```

Dejá esa terminal abierta y usá los comandos de notas en otra. Detené el servidor con Ctrl+C en la primera terminal. Mientras esté encendido, podés abrir `http://127.0.0.1:8000/docs` para consultar y probar los endpoints.

| Método | Ruta | Función |
| --- | --- | --- |
| `POST` | `/notas` | Crear una nota con `nombre` y `texto`; devuelve estado 201, o 409 si el nombre ya existe. |
| `GET` | `/notas` | Obtener las notas completas, desde la más reciente; `?nombre=texto` filtra por nombre sin distinguir mayúsculas. |
| `GET` | `/notas/{note_id}` | Consultar una nota; devuelve 404 si no existe. |
| `DELETE` | `/notas/{note_id}` | Eliminar una nota; devuelve 204 sin contenido, 404 si no existe o 422 si el ID no es un entero positivo. |
| `GET` | `/health` | Consultar la identidad y la versión del protocolo. |

## 8. Dónde se guardan los datos

El proyecto utiliza `platformdirs` para elegir el directorio de datos del usuario. En Windows normalmente es:

```text
%LOCALAPPDATA%\gestor-notas
```

Los archivos son:

- `notas.sqlite3`: base de datos con las notas.
- `servidor.log`: salida y errores de los servidores iniciados automáticamente. El servidor manual también registra su salida en ese archivo.

Podés consultar las rutas que utiliza tu instalación:

```powershell
.\.venv\Scripts\python -c "from gestor_notas.config import database_path, log_path; print(database_path()); print(log_path())"
```

Para elegir otra carpeta, configurá una ruta absoluta antes de ejecutar los comandos:

```powershell
$env:NOTAS_DATA_DIR = "C:\MisNotas"
.\.publish\windows\notas.exe listar
```

Si mantenés la API encendida manualmente, configurá la misma variable en ambas terminales y reiniciá el servidor para cambiar su ubicación. La base utilizada siempre es la que abrió el servidor. Cambiar esta variable no mueve las notas anteriores: selecciona otra ubicación de almacenamiento.

Para realizar un respaldo, detené el servidor y copiá `notas.sqlite3`. Para restaurarlo, con el servidor detenido, colocá la copia en el directorio de datos elegido.

## 9. Problemas frecuentes

| Problema | Qué hacer |
| --- | --- |
| No se encuentra `notas`. | Usá `.\.publish\windows\notas.exe` desde la raíz del proyecto y comprobá que realizaste la instalación. |
| Nombre o texto vacío. | Ingresá contenido que no sea solamente espacios. |
| El editor necesita una terminal interactiva. | Ejecutá el comando directamente en una terminal o pasá `--nombre` y `--texto` para automatizar. |
| Ctrl+S no envía el texto. | Usá F2; algunas terminales reservan Ctrl+S. |
| No existe una nota con ese ID. | Ejecutá `listar` y verificá el ID. |
| Puerto 8000 ocupado o versión incompatible. | Revisá qué servicio está usando el puerto; la CLI no lo detiene. El puerto no tiene una opción de configuración en esta versión. |
| La API no inicia o tarda demasiado. | Consultá la ruta del registro indicada en el error y ejecutá `servidor` y consultá `servidor.log`. |
| Falló la conexión durante una creación. | Consultá `listar` antes de repetirla: la nota podría haberse guardado aunque no llegara la respuesta. La CLI no reintenta esa creación automáticamente. |
| Falló la conexión durante una eliminación. | Consultá `listar` para verificar si la nota todavía existe antes de repetirla. La CLI no reintenta esa eliminación automáticamente. |
| No aparecen notas guardadas anteriormente. | Verificá `NOTAS_DATA_DIR` y la ubicación usada por el servidor que está encendido. |

## 10. Alcance actual

La aplicación está pensada para uso local de una persona. Permite crear, listar, consultar y eliminar notas; todavía no incluye edición ni sincronización. La API no tiene autenticación y escucha en la dirección local `127.0.0.1`.


## 11. Ejecutar las pruebas

Instalá las dependencias de prueba y ejecutá pytest desde la raíz:

```powershell
.\instalar.ps1 -Pruebas
dotnet test cli/Notas.Cli.Tests
.\.venv\Scripts\python -m pytest -q -p no:cacheprovider --basetemp=.test-tmp-local
```

Esta variante crea las bases de prueba dentro del proyecto y evita depender de los permisos de la carpeta temporal del sistema. No modifica las notas personales. Reservá `.test-tmp-local` exclusivamente para pytest: su contenido se elimina al reutilizarla. Las carpetas `.test-tmp-*` no se incluyen en Git.

La configuración de NOTAS_PYTHON, la actualización desde Python y la publicación Native AOT se describen en [README.md](README.md).
