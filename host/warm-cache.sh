#!/usr/bin/env bash
# Read the Fuseki database and the Solr cores once, so that they are in the file cache of the system: after a reboot
# the cache is empty, and the first views of pages would read from the disk (seconds instead of 0.1 s).
# Run at boot by mannheim-warm-cache.service (host/install.sh), with the lowest I/O priority; by hand:
#   sudo host/warm-cache.sh
# Skipped if the files do not fit into the available memory (they would only push each other out).
set -euo pipefail
REPO=$(cd "$(dirname "$0")/.." && pwd)
DATA=$(sed -n 's/^DATA=//p' "$REPO/services/.env" 2>/dev/null || true); DATA=${DATA:-/data/mannheim}
FUSEKI_DB=$(sed -n 's/^FUSEKI_DB=//p' "$REPO/services/.env" 2>/dev/null || true)

dirs=()
[ -n "$FUSEKI_DB" ] && [ -d "$FUSEKI_DB" ] && dirs+=("$FUSEKI_DB")
[ -d "$DATA/solr/data" ] && dirs+=("$DATA/solr/data")
[ ${#dirs[@]} -gt 0 ] || { echo "nothing to read"; exit 0; }

need=$(du -sk "${dirs[@]}" | awk '{s += $1} END {print s}')
avail=$(awk '/^MemAvailable:/ {print $2}' /proc/meminfo)
if [ "$need" -gt "$avail" ]; then
  echo "not read: $((need / 1048576)) GB of files, $((avail / 1048576)) GB memory available"
  exit 0
fi
start=$(date +%s)
find "${dirs[@]}" -type f -exec cat {} + > /dev/null
echo "read $((need / 1048576)) GB in $(( $(date +%s) - start )) s: ${dirs[*]}"
