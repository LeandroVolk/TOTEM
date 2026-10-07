"""Sessao grafica compartilhada entre as cenas do totem."""

import os
import sys
from pathlib import Path

from config import DIALOGO_SDL_DRIVER, DIALOGO_TITULO


class TelaPygame:
    def __init__(self, titulo=DIALOGO_TITULO):
        self.titulo = titulo
        self.pygame = None
        self.superficie = None
        self.driver = None
        self.erro = None

    @property
    def disponivel(self):
        return self.superficie is not None

    def abrir(self):
        if self.disponivel:
            return True
        if self.erro is not None:
            return False

        os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
        try:
            pygame = self._importar_pygame()
        except ImportError as erro:
            self.erro = str(erro)
            return False

        self.pygame = pygame
        drivers = [DIALOGO_SDL_DRIVER] if DIALOGO_SDL_DRIVER else ["kmsdrm", "fbcon"]
        erros = []
        for driver in drivers:
            os.environ["SDL_VIDEODRIVER"] = driver
            try:
                pygame.display.init()
                pygame.font.init()
                self.superficie = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                pygame.display.set_caption(self.titulo)
                pygame.mouse.set_visible(False)
                self.driver = driver
                origem = "sistema" if "/usr/lib/python3/dist-packages" in pygame.__file__ else "venv"
                print(f"[tela] pygame={origem} interface grafica em tela cheia via {driver}")
                return True
            except pygame.error as erro:
                erros.append(f"{driver}: {erro}")
                pygame.quit()

        self.pygame = None
        self.erro = "; ".join(erros)
        return False

    @staticmethod
    def _importar_pygame():
        caminho_sistema = Path(
            os.environ.get("PYGAME_SYSTEM_SITE_PACKAGES", "/usr/lib/python3/dist-packages")
        )
        adicionado = caminho_sistema.is_dir()
        if adicionado:
            sys.path.insert(0, str(caminho_sistema))
        try:
            import pygame
        finally:
            if adicionado:
                sys.path.pop(0)
        return pygame

    def processar_eventos(self):
        if self.disponivel:
            self.pygame.event.pump()

    def fechar(self):
        if self.disponivel:
            self.superficie.fill((0, 0, 0))
            self.pygame.display.flip()
            self.pygame.quit()
        self.pygame = None
        self.superficie = None
        self.driver = None
