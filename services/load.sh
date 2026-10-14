#!/usr/bin/env bash
# Build a new Fuseki database from the data index of judaicalink-data, check it, switch the endpoint to it, and run
# the jobs of the graph application (figures of the graph, search index, dashboard).
#   services/load.sh            (as the deploy user, on the VM)
# The new database is $DATA/fuseki/db-<date>; the previous one stays until it is removed by hand.
# Downloaded files stay in $DATA/store (served as /dumps), so a reload downloads only what is new.
set -euo pipefail
cd "$(dirname "$0")"
[ -f .env ] || cp .env.example .env
set -a; . ./.env; set +a

new=$DATA/fuseki/db-$(date +%F)
n=1; while [ -e "$new" ]; do n=$((n + 1)); new=$DATA/fuseki/db-$(date +%F)-$n; done
mkdir -p "$new" && chmod 2775 "$new"

wait_for() { for _ in $(seq 300); do curl -sf -o /dev/null "http://127.0.0.1:$1/\$/ping" && return 0; sleep 1; done; return 1; }

echo "== loading into $new"
docker compose build -q fuseki
FUSEKI_LOAD_DB=$new docker compose --profile load up -d fuseki-load
wait_for 3031
status=0
python3 fuseki/load.py --store "$DATA/store" --fuseki http://127.0.0.1:3031/judaicalink "$@" | tee "$new.log" || status=$?
FUSEKI_LOAD_DB=$new docker compose --profile load rm -sf fuseki-load
if [ $status != 0 ]; then
  echo "load failed or the check found differences (see $new.log); the endpoint is unchanged"
  exit 1
fi

echo "== switching the endpoint to $new"
sed -i "s#^FUSEKI_DB=.*#FUSEKI_DB=$new#" .env
export FUSEKI_DB=$new           # the value read from .env above would win over the file
docker compose up -d fuseki
wait_for 3030
curl -s http://127.0.0.1:3030/judaicalink/query -H 'Accept: text/csv' \
  --data-urlencode 'query=SELECT (COUNT(*) AS ?triples) { GRAPH ?g { ?s ?p ?o } }'
echo "previous databases:"; ls -d "$DATA"/fuseki/db-* | grep -vx "$new" || true

echo "== the jobs of the graph application: figures, search index, dashboard (apps/graph/jobs.py)"
docker compose up -d solr graph
docker compose run --rm -T graph python3 jobs.py all
