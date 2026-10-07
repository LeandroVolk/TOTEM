"""Protocolo JSON por linha, pequeno e deliberadamente restrito."""

from __future__ import annotations

import json
import os
from pathlib import Path
import socket
from threading import Event, Thread


class ControlServer:
    def __init__(self, socket_path: Path, runtime):
        self.socket_path = Path(socket_path)
        self.runtime = runtime
        self._stop = Event()
        self._thread = None
        self._socket = None

    def start(self):
        self.socket_path.parent.mkdir(parents=True, exist_ok=True)
        if self.socket_path.exists() or self.socket_path.is_symlink():
            self.socket_path.unlink()
        self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._socket.bind(str(self.socket_path))
        os.chmod(self.socket_path, 0o660)
        self._socket.listen(4)
        self._socket.settimeout(0.5)
        self._thread = Thread(target=self._serve, name="totem-control", daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1)
        if self._socket:
            self._socket.close()
        self.socket_path.unlink(missing_ok=True)

    def _serve(self):
        while not self._stop.is_set():
            try:
                conexao, _ = self._socket.accept()
            except TimeoutError:
                continue
            except OSError:
                return
            with conexao:
                try:
                    linha = conexao.makefile("rb").readline(32_768)
                    resposta = self._responder(json.loads(linha))
                except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as erro:
                    resposta = {"ok": False, "error": f"invalid_request: {erro}"}
                conexao.sendall((json.dumps(resposta) + "\n").encode("utf-8"))

    def _responder(self, request):
        comando = request.get("command")
        if comando == "status":
            return {"ok": True, "status": self.runtime.status()}
        if comando == "reload_content":
            return self.runtime.recarregar_conteudo()
        return {"ok": False, "error": "unsupported_command"}


def request(socket_path: Path, command: str, timeout=1.0):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as conexao:
        conexao.settimeout(timeout)
        conexao.connect(str(socket_path))
        conexao.sendall((json.dumps({"command": command}) + "\n").encode("utf-8"))
        resposta = conexao.makefile("rb").readline(32_768)
    return json.loads(resposta)
