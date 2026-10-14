#!/usr/bin/env bash
# Local test VM only: copy this checkout into the VM, as a git clone would on the real VM (host/local-vm.yaml).
set -euo pipefail
REPO=$(cd "$(dirname "$0")/.." && pwd)
limactl shell mannheim -- rsync -a --delete --exclude .git --exclude services/.env --exclude site/public \
  "$REPO/" /data/mannheim/src/judaicalink-mannheim/
echo "synced $REPO to the VM"
