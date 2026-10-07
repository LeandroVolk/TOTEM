#!/usr/bin/env bash
set -euo pipefail

TTY_PATH="${DIALOGO_TTY:-/dev/tty1}"
USUARIO="${SUDO_USER:-${USER}}"

if [[ ! -e "${TTY_PATH}" ]]; then
  echo "Console nao encontrado: ${TTY_PATH}" >&2
  exit 1
fi

if ! command -v setfacl >/dev/null 2>&1; then
  echo "Instalando pacote acl para usar setfacl..."
  sudo apt update
  sudo apt install -y acl
fi

sudo setfacl -m "u:${USUARIO}:rw" "${TTY_PATH}"

echo "Permissao liberada para ${USUARIO} escrever em ${TTY_PATH}."
echo "Agora rode:"
echo "  ./run_totem.sh"
