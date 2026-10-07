"""Reproducao fullscreen de video fora da sessao Pygame/KMS."""

from pathlib import Path
import shutil
import subprocess


class ReprodutorVideo:
    def __init__(self, caminho):
        self.caminho = Path(caminho)

    def reproduzir(self):
        if not self.caminho.is_file():
            print(f"[video] arquivo nao encontrado: {self.caminho}")
            return False
        if shutil.which("mpv") is None:
            print("[video] mpv nao esta instalado; reproducao ignorada.")
            return False

        print(f"[video] reproduzindo {self.caminho.name}")
        resultado = subprocess.run(
            [
                "mpv",
                "--fs",
                "--really-quiet",
                "--no-terminal",
                "--keep-open=no",
                "--",
                str(self.caminho),
            ],
            check=False,
        )
        if resultado.returncode != 0:
            print(f"[video] mpv terminou com codigo={resultado.returncode}")
            return False
        return True
