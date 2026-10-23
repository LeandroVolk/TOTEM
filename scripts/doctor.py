#!/usr/bin/env python3
"""Diagnostico somente leitura do ambiente TOTEM."""

from __future__ import annotations

import argparse
import importlib.util
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from totem_app.settings import load_settings


class Report:
    def __init__(self):
        self.failures = 0

    def item(self, name, ok, detail, required=True):
        label = "OK" if ok else ("FALHA" if required else "AVISO")
        print(f"[{label:5}] {name}: {detail}")
        if not ok and required:
            self.failures += 1


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict-hardware", action="store_true")
    args = parser.parse_args(argv)
    settings = load_settings()
    report = Report()
    report.item("plataforma", sys.platform.startswith("linux"), f"{settings.platform}; {platform.platform()}")
    report.item("python", sys.version_info >= (3, 11), sys.version.split()[0])
    for command in ("git", "ffmpeg"):
        path = shutil.which(command)
        report.item(command, bool(path), path or "nao encontrado")
    for module in ("fastapi", "uvicorn", "jinja2"):
        available = importlib.util.find_spec(module) is not None
        report.item(f"python:{module}", available, "disponivel" if available else "ausente")
    for module in ("numpy", "pygame", "mediapipe"):
        available = importlib.util.find_spec(module) is not None
        report.item(
            f"python:{module}", available,
            "disponivel" if available else "ausente (simulacao headless continua funcional)",
            required=args.strict_hardware,
        )
    for model in (settings.pose_model_path, settings.hand_model_path):
        report.item(f"modelo:{model.name}", model.is_file(), str(model), required=args.strict_hardware)
    camera = Path(settings.camera_device)
    report.item("camera", camera.exists() and os.access(camera, os.R_OK), str(camera), required=args.strict_hardware)
    graphical = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY") or Path("/dev/dri").exists())
    report.item("video", graphical, "sessao desktop ou DRM detectado" if graphical else "sem sessao/DRM", required=args.strict_hardware)
    audio = Path("/dev/snd").exists() or shutil.which("pactl") or shutil.which("wpctl")
    report.item("audio", bool(audio), "dispositivo ou servidor detectado" if audio else "nao detectado", required=False)
    try:
        settings.runtime_dir.mkdir(parents=True, exist_ok=True)
        writable = os.access(settings.runtime_dir, os.W_OK)
    except OSError:
        writable = False
    report.item("dados", writable, str(settings.runtime_dir))
    service = shutil.which("systemctl")
    if service:
        result = subprocess.run(
            [service, "is-enabled", "totem-kiosk.service"],
            check=False, capture_output=True, text=True,
        )
        report.item("autostart", result.returncode == 0, (result.stdout or result.stderr).strip(), required=False)
    print(f"\nResultado: {report.failures} falha(s) obrigatoria(s).")
    return 1 if report.failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
