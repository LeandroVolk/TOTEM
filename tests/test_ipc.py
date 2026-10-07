from ipc.control import ControlServer, request


class RuntimeFake:
    def status(self):
        return {"state": "ESPERA", "running": True}

    def recarregar_conteudo(self):
        return {"ok": True, "content": {"version": "0.1.0"}}


def test_status_e_reload_por_socket_unix(tmp_path):
    caminho = tmp_path / "control.sock"
    server = ControlServer(caminho, RuntimeFake())
    server.start()
    try:
        assert request(caminho, "status")["status"]["state"] == "ESPERA"
        assert request(caminho, "reload_content")["ok"]
    finally:
        server.stop()
