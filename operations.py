"""Operacoes de servico explicitamente permitidas para Admin e CLI."""

from __future__ import annotations

import subprocess

from v2_config import KIOSK_SERVICE_NAME


class ControleServico:
    ACOES = frozenset({"start", "stop", "restart"})

    def __init__(self, helper="/usr/local/sbin/totem-kiosk-control", runner=subprocess.run):
        self.helper = helper
        self.runner = runner

    def executar(self, acao):
        if acao not in self.ACOES:
            raise ValueError("Acao de servico nao permitida.")
        resultado = self.runner(
            ["sudo", "-n", self.helper, acao],
            text=True,
            capture_output=True,
            timeout=15,
        )
        if resultado.returncode != 0:
            detalhe = (resultado.stderr or resultado.stdout or "falha no helper").strip()
            raise RuntimeError(detalhe)
        return {"action": acao, "ok": True}

    def status(self):
        resultado = self.runner(
            ["systemctl", "is-active", KIOSK_SERVICE_NAME],
            text=True,
            capture_output=True,
            timeout=5,
        )
        return (resultado.stdout or "unknown").strip()
