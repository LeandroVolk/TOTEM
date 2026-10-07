#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${BASE_DIR}/.venv/bin/python"

if [[ ! -x "${PYTHON}" ]]; then
  echo "Ambiente virtual nao encontrado em ${BASE_DIR}/.venv" >&2
  exit 1
fi

exec "${PYTHON}" -m uvicorn admin.app:app \
  --host "${TOTEM_ADMIN_HOST:-127.0.0.1}" \
  --port "${TOTEM_ADMIN_PORT:-8787}"
