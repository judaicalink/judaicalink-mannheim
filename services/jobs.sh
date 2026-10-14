#!/usr/bin/env bash
# The jobs of the graph application (apps/graph/jobs.py): figures, search index (in a new core), dashboard.
#   services/jobs.sh            all;   services/jobs.sh stats|index|dashboard   one of them
set -euo pipefail
cd "$(dirname "$0")"
what=${1:-all}
docker compose build -q graph       # the code is in the image: build it from this checkout
run() { docker compose run --rm -T graph python3 jobs.py "$@"; }
[[ $what == all || $what == stats ]] && run stats
if [[ $what == all || $what == index ]]; then run index "$(./solr-core.sh graph)"; fi
[[ $what == all || $what == dashboard ]] && run dashboard
true
