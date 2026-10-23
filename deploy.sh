#!/usr/bin/env bash
set -euo pipefail

cat >&2 <<'EOF'
O deploy cotidiano por rsync/SSH foi descontinuado.

Desenvolva e teste no Fedora, publique uma tag estavel no GitHub e use no
Raspberry: ./totem.sh install ou ./totem.sh update vX.Y.Z.

O script original permanece recuperavel na tag pre-reorganizacao-2026-10-23.
EOF
exit 2
