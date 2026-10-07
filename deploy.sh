#!/usr/bin/env bash
set -euo pipefail

PI_USER="${PI_USER:-labeco}"
PI_HOST="${PI_HOST:-raspberrypi}"
PI_PATH="${PI_PATH:-/home/${PI_USER}/totem}"
SSH_PORT="${SSH_PORT:-22}"

DRY_RUN="--dry-run"

if [[ "${1:-}" == "--apply" ]]; then
  DRY_RUN=""
elif [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  cat <<EOF
Uso:
  ./deploy.sh              # mostra o que seria sincronizado
  ./deploy.sh --apply      # sincroniza para o Raspberry Pi

Variaveis opcionais:
  PI_USER=labeco
  PI_HOST=raspberrypi
  PI_PATH=/home/labeco/totem
  SSH_PORT=22

Exemplo:
  PI_HOST=10.163.4.35 ./deploy.sh --apply
EOF
  exit 0
elif [[ -n "${1:-}" ]]; then
  echo "Argumento desconhecido: $1" >&2
  echo "Use ./deploy.sh --help" >&2
  exit 2
fi

echo "Destino: ${PI_USER}@${PI_HOST}:${PI_PATH}"
if [[ -n "${DRY_RUN}" ]]; then
  echo "Modo: dry-run. Use ./deploy.sh --apply para sincronizar de verdade."
else
  echo "Modo: aplicando alteracoes."
  ssh -p "${SSH_PORT}" "${PI_USER}@${PI_HOST}" "mkdir -p '${PI_PATH}'"
fi

rsync -avz --delete ${DRY_RUN} \
  -e "ssh -p ${SSH_PORT}" \
  --exclude ".venv*/" \
  --exclude "Arte_e_Ciencia-port1.mp4" \
  --exclude "__pycache__/" \
  --exclude "*.pyc" \
  --exclude ".git/" \
  --exclude ".mypy_cache/" \
  --exclude ".pytest_cache/" \
  ./ "${PI_USER}@${PI_HOST}:${PI_PATH}/"
