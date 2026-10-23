#!/usr/bin/env bash
set -euo pipefail

echo "Este comando foi incorporado ao instalador unico do TOTEM." >&2
echo "Executando: ./totem.sh install" >&2
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/totem.sh" install
