import subprocess
import sys
import time
from contextlib import contextmanager
from typing import Iterator
import httpx
from .config import APP_ID, BASE_URL, HOST, PORT, PROTOCOL_VERSION, log_path


class ServerError(RuntimeError):
    pass


def healthy(client: httpx.Client) -> bool:
    try:
        response = client.get("/health", timeout=0.5)
    except (httpx.ConnectError, httpx.ConnectTimeout):
        return False
    except httpx.HTTPError as exc:
        raise ServerError("El servicio del puerto 8000 no responde correctamente.") from exc
    try:
        identity = response.json()
    except ValueError:
        identity = None
    if response.status_code != 200 or identity != {"app": APP_ID, "protocol_version": PROTOCOL_VERSION}:
        raise ServerError("El puerto 8000 está ocupado por otro servicio o una versión incompatible.")
    return True


def stop_process(process: subprocess.Popen) -> None:
    if process.poll() is None:
        process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


@contextmanager
def api_client(startup_timeout: float = 10) -> Iterator[httpx.Client]:
    process = None
    with httpx.Client(base_url=BASE_URL, timeout=5, trust_env=False) as client:
        try:
            if not healthy(client):
                path = log_path()
                path.parent.mkdir(parents=True, exist_ok=True)
                flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                with path.open("ab") as log:
                    process = subprocess.Popen(
                        [sys.executable, "-m", "uvicorn", "gestor_notas.api:create_app", "--factory", "--host", HOST, "--port", str(PORT)],
                        stdin=subprocess.DEVNULL, stdout=log, stderr=log, creationflags=flags,
                    )
                deadline = time.monotonic() + startup_timeout
                while True:
                    if process.poll() is not None:
                        raise ServerError("La API terminó antes de estar disponible.")
                    if healthy(client):
                        if process.poll() is not None:
                            raise ServerError("La API no pudo conservar el puerto 8000.")
                        break
                    if time.monotonic() >= deadline:
                        raise ServerError("La API no estuvo disponible en el tiempo esperado.")
                    time.sleep(0.1)
            yield client
        except (ServerError, OSError) as exc:
            raise ServerError(f"{exc} Registro: {log_path()}. Para iniciarla manualmente, ejecutá 'notas servidor' en otra terminal.") from exc
        finally:
            if process is not None:
                stop_process(process)

