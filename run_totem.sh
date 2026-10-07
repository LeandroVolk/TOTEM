#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -n "${VIRTUAL_ENV:-}" && -x "${VIRTUAL_ENV}/bin/python" ]]; then
  PYTHON="${VIRTUAL_ENV}/bin/python"
else
  PYTHON="${BASE_DIR}/.venv/bin/python"
fi

echo "[run] Python: ${PYTHON}"
PYGAME_SYSTEM_SITE_PACKAGES="${PYGAME_SYSTEM_SITE_PACKAGES:-/usr/lib/python3/dist-packages}"
if [[ -d "${PYGAME_SYSTEM_SITE_PACKAGES}" ]]; then
  PYGAME_PRECHECK_PATH="${PYGAME_SYSTEM_SITE_PACKAGES}${PYTHONPATH:+:${PYTHONPATH}}"
else
  PYGAME_PRECHECK_PATH="${PYTHONPATH:-}"
fi

if [[ ! -x "${PYTHON}" ]]; then
  cat >&2 <<EOF
Ambiente virtual nao encontrado em:
  ${BASE_DIR}/.venv

No Raspberry, crie ou ative o ambiente antes de executar:
  cd ${BASE_DIR}
  python -m venv .venv
  source .venv/bin/activate
  pip install --no-cache-dir numpy mediapipe
  sudo apt install --no-install-recommends python3-pygame
EOF
  exit 1
fi

if ! PYGAME_HIDE_SUPPORT_PROMPT=1 PYTHONPATH="${PYGAME_PRECHECK_PATH}" "${PYTHON}" - <<'PY'
import mediapipe
import numpy
import pygame
PY
then
  cat >&2 <<EOF
Dependencias Python ausentes no ambiente virtual.

No Raspberry, rode:
  cd ${BASE_DIR}
  source .venv/bin/activate
  pip install --no-cache-dir numpy mediapipe
  sudo apt install --no-install-recommends python3-pygame
EOF
  exit 1
fi

exec "${PYTHON}" "${BASE_DIR}/totem.py"
