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
        if DIALOGO_SDL_DRIVER:
            drivers = [DIALOGO_SDL_DRIVER]
        elif os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"):
            # No Fedora desktop, deixe a SDL escolher Wayland/X11.
            drivers = [None]
        elif os.environ.get("SDL_VIDEODRIVER") == "dummy":
            drivers = ["dummy"]
        else:
            drivers = ["kmsdrm", "fbcon"]
        erros = []
        for driver in drivers:
            if driver:
                os.environ["SDL_VIDEODRIVER"] = driver
            else:
                os.environ.pop("SDL_VIDEODRIVER", None)
            try:
                pygame.display.init()
                pygame.font.init()
                fullscreen = os.environ.get("TOTEM_FULLSCREEN", "1") != "0"
                if fullscreen:
                    size = (0, 0)
                    flags = pygame.FULLSCREEN
                else:
                    size = (
                        int(os.environ.get("TOTEM_SCREEN_WIDTH", "1280")),
                        int(os.environ.get("TOTEM_SCREEN_HEIGHT", "720")),
                    )
                    flags = pygame.RESIZABLE
                self.superficie = pygame.display.set_mode(size, flags)
                pygame.display.set_caption(self.titulo)
                pygame.mouse.set_visible(not fullscreen)
                self.driver = pygame.display.get_driver()
                origem = "sistema" if "/usr/lib/python3/dist-packages" in pygame.__file__ else "venv"
                modo = "tela cheia" if fullscreen else f"janela {size[0]}x{size[1]}"
                print(f"[tela] pygame={origem} interface grafica em {modo} via {self.driver}")
                return True
            except pygame.error as erro:
                erros.append(f"{driver or 'auto'}: {erro}")
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
