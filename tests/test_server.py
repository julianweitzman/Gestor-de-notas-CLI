from unittest.mock import Mock
import httpx
import pytest
from gestor_notas import server


def test_health_rejects_other_services():
    for response in (httpx.Response(200, json={"app": "other"}), httpx.Response(404), httpx.Response(200, text="HTML")):
        with httpx.Client(base_url="http://test", transport=httpx.MockTransport(lambda request: response)) as client:
            with pytest.raises(server.ServerError, match="ocupado"):
                server.healthy(client)


def test_reuses_existing_server(monkeypatch):
    monkeypatch.setattr(server, "healthy", lambda client: True)
    spawn = Mock()
    monkeypatch.setattr(server.subprocess, "Popen", spawn)
    with server.api_client() as client:
        assert isinstance(client, httpx.Client)
    spawn.assert_not_called()


@pytest.mark.parametrize("failure", [None, RuntimeError, KeyboardInterrupt])
def test_stops_only_own_process(tmp_path, monkeypatch, failure):
    monkeypatch.setenv("NOTAS_DATA_DIR", str(tmp_path))
    checks = iter([False, True])
    monkeypatch.setattr(server, "healthy", lambda client: next(checks))
    process = Mock()
    process.poll.return_value = None
    monkeypatch.setattr(server.subprocess, "Popen", Mock(return_value=process))
    def run():
        with server.api_client():
            if failure:
                raise failure()
    if failure:
        with pytest.raises(failure):
            run()
    else:
        run()
    process.terminate.assert_called_once()
    process.wait.assert_called_once_with(timeout=5)


def test_startup_timeout_and_exit(tmp_path, monkeypatch):
    monkeypatch.setenv("NOTAS_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(server, "healthy", lambda client: False)
    process = Mock()
    process.poll.return_value = None
    monkeypatch.setattr(server.subprocess, "Popen", Mock(return_value=process))
    with pytest.raises(server.ServerError, match="tiempo esperado"):
        with server.api_client(startup_timeout=0):
            pytest.fail("No debe estar disponible")
    process.terminate.assert_called_once()
    process.poll.return_value = 1
    with pytest.raises(server.ServerError, match="terminó"):
        with server.api_client():
            pytest.fail("No debe estar disponible")


def test_forces_stop_after_timeout():
    process = Mock()
    process.poll.return_value = None
    process.wait.side_effect = [server.subprocess.TimeoutExpired("uvicorn", 5), 0]
    server.stop_process(process)
    process.kill.assert_called_once()


def test_connect_timeout_means_no_server():
    def handle(request):
        raise httpx.ConnectTimeout("timeout", request=request)
    with httpx.Client(base_url="http://test", transport=httpx.MockTransport(handle)) as client:
        assert server.healthy(client) is False


def test_foreign_server_does_not_spawn_or_stop_process(monkeypatch):
    def reject(client):
        raise server.ServerError("Puerto ocupado")
    monkeypatch.setattr(server, "healthy", reject)
    spawn = Mock()
    monkeypatch.setattr(server.subprocess, "Popen", spawn)
    with pytest.raises(server.ServerError, match="Puerto ocupado"):
        with server.api_client():
            pytest.fail("No debe conectarse")
    spawn.assert_not_called()
