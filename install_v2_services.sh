#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_USER="${SUDO_USER:-$USER}"
TEMPORARY="$(mktemp)"
trap 'rm -f "${TEMPORARY}"' EXIT

if [[ ! -x "${PROJECT_DIR}/.venv/bin/python" ]]; then
  echo "Ambiente virtual nao encontrado em ${PROJECT_DIR}/.venv" >&2
  exit 1
fi

for unit in totem-kiosk.service totem-admin.service; do
  sed "s|__USER__|${SERVICE_USER}|g; s|__PROJECT_DIR__|${PROJECT_DIR}|g" \
    "${PROJECT_DIR}/systemd/${unit}" >"${TEMPORARY}"
  sudo install -m 644 "${TEMPORARY}" "/etc/systemd/system/${unit}"
done

sudo install -m 755 "${PROJECT_DIR}/systemd/totem-kiosk-control" /usr/local/sbin/totem-kiosk-control
sed "s|__USER__|${SERVICE_USER}|g" "${PROJECT_DIR}/systemd/totem-kiosk-control.sudoers" | \
  sudo tee /etc/sudoers.d/totem-kiosk-control >/dev/null
sudo chmod 440 /etc/sudoers.d/totem-kiosk-control
sudo visudo -cf /etc/sudoers.d/totem-kiosk-control

if [[ ! -f /etc/totem-labeco/admin.env ]]; then
  sudo install -d -m 755 /etc/totem-labeco
  sudo install -m 600 "${PROJECT_DIR}/systemd/admin.env.example" /etc/totem-labeco/admin.env
fi

sudo systemctl daemon-reload
sudo systemctl enable totem-kiosk.service totem-admin.service
echo "Servicos instalados. Use sudo systemctl start totem-kiosk.service totem-admin.service"
