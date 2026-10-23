#!/usr/bin/env python3
"""Ponto de entrada unico do TOTEM (hardware ou simulacao explicita)."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from totem_app.application import run
from totem_app.settings import load_settings


def parse_args(argv=None):
    parser = argparse.ArgumentParser(prog="totem", description="TOTEM interativo")
    parser.add_argument("--simulate", action="store_true", help="ativa entrada simulada")
    parser.add_argument("--headless", action="store_true", help="nao abre interface grafica")
    parser.add_argument("--script", type=Path, help="executa comandos de simulacao de um arquivo")
    parser.add_argument("--config", type=Path, help="arquivo TOML de configuracao")
    parser.add_argument("--windowed", action="store_true", help="abre janela no desktop local")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    mode = "simulation" if args.simulate or args.script else None
    settings = load_settings(
        args.config,
        mode=mode,
        headless=True if args.headless else None,
        fullscreen=False if args.windowed else None,
    )
    os.environ["TOTEM_FULLSCREEN"] = "1" if settings.fullscreen else "0"
    if settings.screen_width:
        os.environ["TOTEM_SCREEN_WIDTH"] = str(settings.screen_width)
    if settings.screen_height:
        os.environ["TOTEM_SCREEN_HEIGHT"] = str(settings.screen_height)
    script = args.script.read_text(encoding="utf-8").splitlines() if args.script else None
    return run(settings, script=script)


if __name__ == "__main__":
    raise SystemExit(main())
