"""Comparar la CLI C# publicada con la implementación Python de referencia."""

import argparse
import json
import os
from pathlib import Path
import socket
import statistics
import subprocess
import sys
import tempfile
import time
from urllib.error import URLError
from urllib.request import ProxyHandler, build_opener


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cli", type=Path, default=root / ".publish/windows/notas.exe")
    parser.add_argument("--repeticiones", type=int, default=5)
    args = parser.parse_args()
    if args.repeticiones < 1 or not args.cli.is_file():
        parser.error("Indicá un ejecutable existente y al menos una repetición.")
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", 8000)) == 0:
            parser.error("El puerto 8000 está ocupado. El benchmark necesita iniciar su propio servidor.")
    commands = {
        "Python": [sys.executable, "-m", "gestor_notas_cli"],
        "C#": [str(args.cli.resolve())],
    }
    with tempfile.TemporaryDirectory(prefix="notas-benchmark-") as directory:
        env = {**os.environ, "NOTAS_DATA_DIR": directory, "NOTAS_PYTHON": sys.executable,
               "PYTHONIOENCODING": "utf-8",
               "PYTHONPATH": str(root / "legacy") + os.pathsep + os.environ.get("PYTHONPATH", "")}

        def measure(command, arguments):
            samples = []
            for _ in range(args.repeticiones):
                start = time.perf_counter()
                result = subprocess.run(command + arguments, stdout=subprocess.DEVNULL,
                                        stderr=subprocess.PIPE, env=env, timeout=30)
                if result.returncode:
                    raise RuntimeError(result.stderr.decode("utf-8", errors="replace"))
                samples.append((time.perf_counter() - start) * 1000)
            return round(statistics.median(samples), 1)

        results = {label: {"ayuda_ms": measure(command, ["--help"]),
                           "listar_api_apagada_ms": measure(command, ["listar"])}
                   for label, command in commands.items()}
        process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "gestor_notas.api:create_app", "--factory",
             "--host", "127.0.0.1", "--port", "8000"],
            env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
        try:
            deadline = time.monotonic() + 10
            opener = build_opener(ProxyHandler({}))
            while True:
                if process.poll() is not None:
                    raise RuntimeError("El backend del benchmark terminó antes de estar disponible.")
                try:
                    with opener.open("http://127.0.0.1:8000/health", timeout=0.5) as response:
                        if json.load(response) != {"app": "gestor-notas", "protocol_version": 1}:
                            raise RuntimeError("El puerto fue ocupado por otro servicio.")
                    break
                except (URLError, TimeoutError):
                    if time.monotonic() >= deadline:
                        raise RuntimeError("La API no inició en 10 segundos.")
                    time.sleep(0.1)
            for label, command in commands.items():
                results[label]["listar_api_encendida_ms"] = measure(command, ["listar"])
        finally:
            if process.poll() is None:
                process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        print(json.dumps({"repeticiones": args.repeticiones, "medianas": results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
