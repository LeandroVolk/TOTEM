#!/usr/bin/env python3
"""Coleta informacoes de video/SDL sem iniciar uma tela grafica."""

import ctypes
import ctypes.util
import glob
import grp
import os
import pwd
import stat
import subprocess
import sys


def titulo(nome):
    print(f"\n== {nome} ==")


def executar(comando):
    try:
        resultado = subprocess.run(
            comando,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as erro:
        return f"indisponivel: {erro}"
    return resultado.stdout.strip() or resultado.stderr.strip() or "(sem saida)"


def dono_e_permissoes(caminho):
    info = os.stat(caminho)
    modo = stat.filemode(info.st_mode)
    dono = pwd.getpwuid(info.st_uid).pw_name
    grupo = grp.getgrgid(info.st_gid).gr_name
    acesso = "leitura=" + str(os.access(caminho, os.R_OK)).lower()
    acesso += " escrita=" + str(os.access(caminho, os.W_OK)).lower()
    return f"{caminho}: {modo} {dono}:{grupo} {acesso}"


def drivers_sdl_do_sistema():
    nome_biblioteca = ctypes.util.find_library("SDL2-2.0")
    if not nome_biblioteca:
        nome_biblioteca = ctypes.util.find_library("SDL2")
    if not nome_biblioteca:
        return "SDL2 compartilhada nao encontrada pelo sistema."

    try:
        sdl = ctypes.CDLL(nome_biblioteca)
        sdl.SDL_GetNumVideoDrivers.restype = ctypes.c_int
        sdl.SDL_GetVideoDriver.argtypes = [ctypes.c_int]
        sdl.SDL_GetVideoDriver.restype = ctypes.c_char_p
        quantidade = sdl.SDL_GetNumVideoDrivers()
        drivers = [
            sdl.SDL_GetVideoDriver(indice).decode("utf-8")
            for indice in range(quantidade)
        ]
        return f"biblioteca={nome_biblioteca} drivers={', '.join(drivers)}"
    except OSError as erro:
        return f"nao foi possivel carregar {nome_biblioteca}: {erro}"


def relatar_pygame():
    titulo("Pygame e SDL usados pela .venv")
    try:
        import pygame
    except ImportError as erro:
        print(f"pygame indisponivel: {erro}")
        return

    print(f"python={sys.executable}")
    print(f"pygame={pygame.version.ver}")
    print(f"pygame_arquivo={pygame.__file__}")
    print(f"sdl_linkada={pygame.get_sdl_version()}")
    get_drivers = getattr(pygame.display, "get_drivers", None)
    if callable(get_drivers):
        print(f"pygame_display_get_drivers={get_drivers()}")
    else:
        print("pygame_display_get_drivers=ausente; usando SDL_GetNumVideoDrivers")
    print("pip_show:")
    print(executar([sys.executable, "-m", "pip", "show", "pygame"]))
    print("drivers_sdl_sistema:")
    print(drivers_sdl_do_sistema())


def relatar_ambiente():
    titulo("Variaveis de ambiente")
    chaves = sorted(chave for chave in os.environ if chave.startswith("SDL_"))
    chaves += ["DISPLAY", "WAYLAND_DISPLAY", "XDG_RUNTIME_DIR"]
    for chave in chaves:
        print(f"{chave}={os.environ.get(chave, '')}")


def relatar_dispositivos():
    titulo("Dispositivos de video")
    caminhos = sorted(glob.glob("/dev/dri/*") + glob.glob("/dev/fb*"))
    if not caminhos:
        print("nenhum dispositivo em /dev/dri/* ou /dev/fb*")
    for caminho in caminhos:
        print(dono_e_permissoes(caminho))

    print("sys_class_drm:")
    for caminho in sorted(glob.glob("/sys/class/drm/*")):
        print(caminho)


def relatar_kernel():
    titulo("Kernel e DRM")
    print(executar(["uname", "-a"]))
    modulos = executar(["lsmod"])
    linhas_drm = [linha for linha in modulos.splitlines() if "drm" in linha.lower()]
    print("\n".join(linhas_drm) or "nenhum modulo drm listado")
    print(f"id: {executar(['id'])}")


def main():
    print("Diagnostico de video do totem (somente leitura)")
    relatar_pygame()
    relatar_ambiente()
    relatar_dispositivos()
    relatar_kernel()


if __name__ == "__main__":
    main()
