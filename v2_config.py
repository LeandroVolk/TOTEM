"""Configuracao da plataforma V2 sem alterar os parametros da experiencia V1."""

import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
RUNTIME_DIR = Path(os.environ.get("TOTEM_RUNTIME_DIR", BASE_DIR / "runtime"))
DATABASE_PATH = Path(os.environ.get("TOTEM_DATABASE_PATH", RUNTIME_DIR / "totem.sqlite3"))
CONTENT_ROOT = Path(os.environ.get("TOTEM_CONTENT_ROOT", RUNTIME_DIR / "content"))
CONTROL_SOCKET_PATH = Path(
    os.environ.get("TOTEM_CONTROL_SOCKET", RUNTIME_DIR / "totem-control.sock")
)
ADMIN_HOST = os.environ.get("TOTEM_ADMIN_HOST", "127.0.0.1")
ADMIN_PORT = int(os.environ.get("TOTEM_ADMIN_PORT", "8787"))
ADMIN_TOKEN = os.environ.get("TOTEM_ADMIN_TOKEN", "")
KIOSK_SERVICE_NAME = os.environ.get("TOTEM_KIOSK_SERVICE", "totem-kiosk.service")
ADMIN_SERVICE_NAME = os.environ.get("TOTEM_ADMIN_SERVICE", "totem-admin.service")


def preparar_diretorios():
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    CONTENT_ROOT.mkdir(parents=True, exist_ok=True)
    (CONTENT_ROOT / "bundles").mkdir(exist_ok=True)
    (CONTENT_ROOT / "staging").mkdir(exist_ok=True)
