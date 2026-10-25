import os
from pathlib import Path
from platformdirs import user_data_path

HOST = "127.0.0.1"
PORT = 8000
BASE_URL = f"http://{HOST}:{PORT}"
APP_ID = "gestor-notas"
PROTOCOL_VERSION = 1


def data_dir() -> Path:
    override = os.environ.get("NOTAS_DATA_DIR")
    return Path(override).expanduser().resolve() if override else user_data_path(APP_ID, appauthor=False)


def database_path() -> Path:
    return data_dir() / "notas.sqlite3"


def log_path() -> Path:
    return data_dir() / "servidor.log"
