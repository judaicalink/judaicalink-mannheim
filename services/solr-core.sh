#!/usr/bin/env bash
# Make a new Solr core with its own copy of the _default configset (decision 0004) and print its name.
#   services/solr-core.sh <prefix>      e.g. graph -> graph_20261014T081500
set -euo pipefail
cd "$(dirname "$0")"
name=${1:?prefix}_$(date +%Y%m%dT%H%M%S)
docker compose exec -T solr solr create -c "$name" -d _default >/dev/null
echo "$name"
