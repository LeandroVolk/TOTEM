import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def test_simulacao_headless_inicializa_sem_hardware(tmp_path):
    env = os.environ.copy()
    env["TOTEM_RUNTIME_DIR"] = str(tmp_path / "runtime")
    result = subprocess.run(
        [sys.executable, "totem.py", "--simulate", "--headless", "--script", "examples/simulation-full.txt"],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=15,
    )
    assert result.returncode == 0, result.stderr
    assert "Nenhuma camera sera aberta" in result.stdout


def test_interface_unica_expoe_comandos():
    result = subprocess.run(
        ["bash", "totem.sh", "--help"], cwd=ROOT, capture_output=True, text=True, timeout=5,
    )
    assert result.returncode == 0
    for command in ("install", "run", "stop", "restart", "status", "logs", "test", "doctor", "update", "backup", "restore"):
        assert command in result.stdout
