#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${TOTEM_VENV_DIR:-${PROJECT_DIR}/.venv}"
PID_FILE="${PROJECT_DIR}/.totem.pid"
LOCAL_LOG_DIR="${PROJECT_DIR}/logs"
LOCAL_DATA_DIR="${TOTEM_RUNTIME_DIR:-${PROJECT_DIR}/runtime}"
BACKUP_DIR="${TOTEM_BACKUP_DIR:-${PROJECT_DIR}/backups}"
SERVICE_USER="${TOTEM_SERVICE_USER:-${SUDO_USER:-${USER}}}"
OS_ID="unknown"
OS_VERSION="unknown"
ARCH="$(uname -m)"

if [[ -r /etc/os-release ]]; then
  source /etc/os-release
  OS_ID="${ID:-unknown}"
  OS_VERSION="${VERSION_ID:-unknown}"
fi

usage() {
  cat <<'EOF'
TOTEM - desenvolvimento, testes e producao

Uso: ./totem.sh <comando> [opcoes]

  install                 instala dependencias e, no Raspberry, os servicos
  run [--simulate]        executa em primeiro plano
  stop | restart | status controla o processo local ou os servicos
  logs                    acompanha os registros
  test                    executa todos os testes sem hardware
  doctor [--strict-hardware] diagnostica o ambiente
  update <tag>            atualiza uma instalacao para uma tag estavel
  backup [destino]        exporta configuracoes e dados
  restore <arquivo>       restaura um backup validado
EOF
}

is_raspberry_production() { [[ "${OS_ID}" == "debian" && "${ARCH}" == "aarch64" ]]; }
have_installed_service() { [[ -f /etc/systemd/system/totem-kiosk.service ]]; }

sudo_run() {
  if [[ "${EUID}" -eq 0 ]]; then "$@"; else sudo "$@"; fi
}

python_bin() {
  if [[ -x "${VENV_DIR}/bin/python" ]]; then printf '%s\n' "${VENV_DIR}/bin/python"; else printf '%s\n' "python3"; fi
}

install_system_packages() {
  if [[ "${TOTEM_SKIP_SYSTEM:-0}" == "1" ]]; then
    echo "[install] pacotes de sistema ignorados por TOTEM_SKIP_SYSTEM=1"
    return
  fi
  case "${OS_ID}:${ARCH}" in
    fedora:x86_64) sudo_run dnf install -y python3 python3-pip ffmpeg git ;;
    debian:aarch64)
      sudo_run apt-get update
      sudo_run apt-get install -y --no-install-recommends \
        python3 python3-venv python3-pip python3-pygame ffmpeg git \
        v4l-utils libgl1 libglib2.0-0 acl
      ;;
    *)
      echo "Plataforma sem instalacao automatica: ${OS_ID} ${OS_VERSION} ${ARCH}" >&2
      echo "Plataformas suportadas: Fedora x86_64 e Debian 13 ARM64." >&2
      return 2
      ;;
  esac
}

select_requirements() {
  case "${OS_ID}:${ARCH}" in
    fedora:x86_64) printf '%s\n' "${PROJECT_DIR}/requirements/fedora-x86_64.txt" ;;
    debian:aarch64) printf '%s\n' "${PROJECT_DIR}/requirements/debian-arm64.txt" ;;
    *) printf '%s\n' "${PROJECT_DIR}/requirements/dev.txt" ;;
  esac
}

create_venv() {
  if [[ ! -x "${VENV_DIR}/bin/python" ]]; then
    echo "[install] criando ambiente virtual em ${VENV_DIR}"
    if [[ "${OS_ID}" == "debian" ]]; then
      python3 -m venv --system-site-packages "${VENV_DIR}"
    else
      python3 -m venv "${VENV_DIR}"
    fi
  else
    echo "[install] preservando ambiente virtual existente"
  fi
  if [[ "${OS_ID}" == "debian" && -f "${VENV_DIR}/pyvenv.cfg" ]]; then
    sed -i 's/^include-system-site-packages = .*/include-system-site-packages = true/' "${VENV_DIR}/pyvenv.cfg"
  fi
  "${VENV_DIR}/bin/python" -m ensurepip --upgrade
  "${VENV_DIR}/bin/python" -m pip install --upgrade "pip==26.0.1"
  "${VENV_DIR}/bin/python" -m pip install -r "$(select_requirements)"
}

render_service() {
  local source="$1" target="$2" temporary
  temporary="$(mktemp)"
  sed "s|__USER__|${SERVICE_USER}|g; s|__PROJECT_DIR__|${PROJECT_DIR}|g" "${source}" >"${temporary}"
  sudo_run install -m 0644 "${temporary}" "${target}"
  rm -f "${temporary}"
}

install_services() {
  echo "[install] configurando producao para ${SERVICE_USER}"
  sudo_run install -d -m 0755 /etc/totem /var/lib/totem /var/log/totem
  sudo_run chown "${SERVICE_USER}:${SERVICE_USER}" /var/lib/totem /var/log/totem
  [[ -f /etc/totem/totem.toml ]] || sudo_run install -m 0644 "${PROJECT_DIR}/config/default.toml" /etc/totem/totem.toml
  [[ -f /etc/totem/totem.env ]] || sudo_run install -m 0644 "${PROJECT_DIR}/systemd/totem.env.example" /etc/totem/totem.env
  [[ -f /etc/totem/admin.env ]] || sudo_run install -m 0600 "${PROJECT_DIR}/systemd/admin.env.example" /etc/totem/admin.env
  render_service "${PROJECT_DIR}/systemd/totem-kiosk.service" /etc/systemd/system/totem-kiosk.service
  render_service "${PROJECT_DIR}/systemd/totem-admin.service" /etc/systemd/system/totem-admin.service
  sudo_run install -m 0755 "${PROJECT_DIR}/systemd/totem-kiosk-control" /usr/local/sbin/totem-kiosk-control
  local sudoers_tmp
  sudoers_tmp="$(mktemp)"
  sed "s|__USER__|${SERVICE_USER}|g" "${PROJECT_DIR}/systemd/totem-kiosk-control.sudoers" >"${sudoers_tmp}"
  sudo_run install -m 0440 "${sudoers_tmp}" /etc/sudoers.d/totem-kiosk-control
  rm -f "${sudoers_tmp}"
  sudo_run visudo -cf /etc/sudoers.d/totem-kiosk-control
  sudo_run systemctl daemon-reload
  sudo_run systemctl enable totem-kiosk.service totem-admin.service
}

cmd_install() {
  echo "[install] sistema=${OS_ID} versao=${OS_VERSION} arquitetura=${ARCH}"
  install_system_packages
  create_venv
  mkdir -p "${LOCAL_DATA_DIR}" "${LOCAL_LOG_DIR}" "${BACKUP_DIR}"
  chmod +x "${PROJECT_DIR}/totem.py" "${PROJECT_DIR}/run_totem.sh" "${PROJECT_DIR}/run_admin.sh" "${PROJECT_DIR}/scripts/doctor.py"
  if is_raspberry_production; then install_services; fi
  echo "[install] validando instalacao"
  "$(python_bin)" "${PROJECT_DIR}/scripts/doctor.py"
  echo "[install] concluido. Use ./totem.sh test e ./totem.sh run --simulate"
}

cmd_run() {
  if have_installed_service && is_raspberry_production && [[ "${1:-}" != "--simulate" ]]; then
    sudo_run systemctl start totem-kiosk.service totem-admin.service
    return
  fi
  local args=()
  if [[ "${1:-}" == "--simulate" ]]; then args+=(--simulate); shift; fi
  exec "$(python_bin)" "${PROJECT_DIR}/totem.py" "${args[@]}" "$@"
}

cmd_stop() {
  if have_installed_service && is_raspberry_production; then
    sudo_run systemctl stop totem-kiosk.service totem-admin.service
  elif [[ -f "${PID_FILE}" ]]; then
    local pid
    pid="$(<"${PID_FILE}")"
    if [[ "${pid}" =~ ^[0-9]+$ ]] && kill -0 "${pid}" 2>/dev/null; then kill -TERM "${pid}"; fi
    rm -f "${PID_FILE}"
  else
    echo "Nenhum processo local gerenciado pelo TOTEM foi encontrado."
  fi
}

cmd_restart() {
  if have_installed_service && is_raspberry_production; then
    sudo_run systemctl restart totem-kiosk.service totem-admin.service
  else
    cmd_stop
    echo "No desenvolvimento, use './totem.sh run' para manter os logs no terminal."
  fi
}

cmd_status() {
  echo "TOTEM plataforma=${OS_ID}-${ARCH} python=$("$(python_bin)" --version 2>&1)"
  if have_installed_service && is_raspberry_production; then
    systemctl --no-pager --full status totem-kiosk.service totem-admin.service || true
  elif [[ -f "${PID_FILE}" ]] && kill -0 "$(<"${PID_FILE}")" 2>/dev/null; then
    echo "processo local ativo pid=$(<"${PID_FILE}")"
  else
    echo "processo local inativo"
  fi
}

cmd_logs() {
  if have_installed_service && is_raspberry_production; then
    exec journalctl -u totem-kiosk.service -u totem-admin.service -f
  fi
  mkdir -p "${LOCAL_LOG_DIR}"
  touch "${LOCAL_LOG_DIR}/totem.log"
  exec tail -n 100 -f "${LOCAL_LOG_DIR}/totem.log"
}

cmd_test() {
  export SDL_VIDEODRIVER="${SDL_VIDEODRIVER:-dummy}"
  export TOTEM_HEADLESS=1
  exec "$(python_bin)" -m pytest -q "$@"
}

cmd_doctor() { exec "$(python_bin)" "${PROJECT_DIR}/scripts/doctor.py" "$@"; }

cmd_backup() {
  local destination="${1:-${BACKUP_DIR}/totem-backup-$(date +%Y%m%d-%H%M%S).tar.gz}"
  mkdir -p "$(dirname "${destination}")"
  local staging
  staging="$(mktemp -d)"
  trap 'rm -rf "${staging}"' RETURN
  mkdir -p "${staging}/config" "${staging}/data"
  if is_raspberry_production && [[ -d /etc/totem ]]; then
    sudo_run cp -a /etc/totem/. "${staging}/config/"
    sudo_run cp -a /var/lib/totem/. "${staging}/data/"
    sudo_run chown -R "${USER}:${USER}" "${staging}"
  else
    [[ -f "${PROJECT_DIR}/config/local.toml" ]] && cp -a "${PROJECT_DIR}/config/local.toml" "${staging}/config/"
    [[ -d "${LOCAL_DATA_DIR}" ]] && cp -a "${LOCAL_DATA_DIR}/." "${staging}/data/"
  fi
  find "${staging}" -type s -delete
  printf 'format=1\ncreated_at=%s\ngit_commit=%s\n' \
    "$(date --iso-8601=seconds)" "$(git -C "${PROJECT_DIR}" rev-parse HEAD 2>/dev/null || echo unknown)" >"${staging}/manifest.txt"
  tar -C "${staging}" -czf "${destination}" manifest.txt config data
  echo "Backup criado: ${destination}"
}

cmd_restore() {
  local archive="${1:-}"
  [[ -n "${archive}" && -f "${archive}" ]] || { echo "Use: ./totem.sh restore <backup.tar.gz>" >&2; return 2; }
  if tar -tzf "${archive}" | grep -Eq '(^/|(^|/)\.\.(/|$))'; then echo "Backup recusado: caminho inseguro." >&2; return 2; fi
  tar -tzf "${archive}" | grep -qx 'manifest.txt' || { echo "Backup sem manifesto." >&2; return 2; }
  local staging
  staging="$(mktemp -d)"
  trap 'rm -rf "${staging}"' RETURN
  tar -xzf "${archive}" -C "${staging}"
  if is_raspberry_production; then
    cmd_backup "${BACKUP_DIR}/antes-da-restauracao-$(date +%Y%m%d-%H%M%S).tar.gz"
    sudo_run systemctl stop totem-kiosk.service totem-admin.service || true
    sudo_run cp -a "${staging}/config/." /etc/totem/
    sudo_run cp -a "${staging}/data/." /var/lib/totem/
    sudo_run chown -R "${SERVICE_USER}:${SERVICE_USER}" /var/lib/totem
  else
    mkdir -p "${LOCAL_DATA_DIR}"
    cp -a "${staging}/data/." "${LOCAL_DATA_DIR}/"
    [[ -f "${staging}/config/local.toml" ]] && cp -a "${staging}/config/local.toml" "${PROJECT_DIR}/config/local.toml"
  fi
  echo "Backup restaurado: ${archive}"
}

cmd_update() {
  local version="${1:-}"
  [[ "${version}" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "Informe uma tag estavel no formato vX.Y.Z." >&2; return 2; }
  [[ -d "${PROJECT_DIR}/.git" ]] || { echo "Atualizacao requer clone Git." >&2; return 2; }
  [[ -z "$(git -C "${PROJECT_DIR}" status --porcelain)" ]] || { echo "Atualizacao recusada: existem alteracoes locais no codigo." >&2; return 2; }
  git -C "${PROJECT_DIR}" fetch --tags origin
  git -C "${PROJECT_DIR}" rev-parse -q --verify "refs/tags/${version}" >/dev/null || { echo "Tag nao encontrada: ${version}" >&2; return 2; }
  cmd_backup
  if have_installed_service && is_raspberry_production; then sudo_run systemctl stop totem-kiosk.service totem-admin.service; fi
  git -C "${PROJECT_DIR}" switch --detach "${version}"
  create_venv
  if is_raspberry_production; then
    install_services
    sudo_run systemctl restart totem-kiosk.service totem-admin.service
  fi
  echo "TOTEM atualizado para ${version}."
}

command="${1:-help}"
shift || true
case "${command}" in
  install) cmd_install "$@" ;;
  run) cmd_run "$@" ;;
  stop) cmd_stop "$@" ;;
  restart) cmd_restart "$@" ;;
  status) cmd_status "$@" ;;
  logs) cmd_logs "$@" ;;
  test) cmd_test "$@" ;;
  doctor) cmd_doctor "$@" ;;
  update) cmd_update "$@" ;;
  backup) cmd_backup "$@" ;;
  restore) cmd_restore "$@" ;;
  help|-h|--help) usage ;;
  *) echo "Comando desconhecido: ${command}" >&2; usage >&2; exit 2 ;;
esac
