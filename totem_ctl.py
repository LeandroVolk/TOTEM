#!/usr/bin/env python3
"""Operacao por SSH usando o mesmo IPC e controle restrito do Admin."""

import argparse
import subprocess
import sys

from ipc.control import request as ipc_request
from operations import ControleServico
from v2_config import ADMIN_HOST, ADMIN_PORT, ADMIN_SERVICE_NAME, CONTROL_SOCKET_PATH, KIOSK_SERVICE_NAME


def main():
    parser = argparse.ArgumentParser(prog="totem-ctl")
    parser.add_argument(
        "command",
        choices=(
            "status", "start", "stop", "restart", "reload-content",
            "logs-kiosk", "logs-admin", "camera-check", "admin-url",
        ),
    )
    args = parser.parse_args()
    if args.command in {"start", "stop", "restart"}:
        print(ControleServico().executar(args.command))
        return
    if args.command == "status":
        print(ipc_request(CONTROL_SOCKET_PATH, "status"))
        return
    if args.command == "reload-content":
        print(ipc_request(CONTROL_SOCKET_PATH, "reload_content"))
        return
    if args.command == "logs-kiosk":
        raise SystemExit(subprocess.run(["journalctl", "-u", KIOSK_SERVICE_NAME, "-n", "100"]).returncode)
    if args.command == "logs-admin":
        raise SystemExit(subprocess.run(["journalctl", "-u", ADMIN_SERVICE_NAME, "-n", "100"]).returncode)
    if args.command == "camera-check":
        raise SystemExit(subprocess.run([sys.executable, "diagnosticar_video.py"]).returncode)
    print(f"http://{ADMIN_HOST}:{ADMIN_PORT}")


if __name__ == "__main__":
    main()
