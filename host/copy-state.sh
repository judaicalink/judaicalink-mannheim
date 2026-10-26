#!/usr/bin/env bash
# Copy the state of this platform VM to another one (decision 0009): the Fuseki database the endpoint uses, the Solr
# home (all cores), the generated pages (figures, dashboard, status.json), the store (/dumps) and the data of the
# showcases (/data/mannheim/showcases). Run it on the VM that has the finished state (the test VM on bee, after
# services/load.sh, the showcase jobs and the checks), as the deploy user, with ssh access to the target (an agent
# forwarded into the VM: ssh -A bee, then ssh -A into the VM; no key is stored there):
#   host/copy-state.sh <ssh-target> [--dry-run]       e.g. host/copy-state.sh eckert@141.19.143.18
# Both VMs must have the same commit of this repository and of the showcase repositories (checked). Static showcases
# and the site are copied by host/deploy.sh, not here. On the target, Solr, the graph application and the showcase
# containers are stopped while their files are replaced; the endpoint is switched to the copied database, and the
# copy is accepted when the target counts the same triples.
set -euo pipefail
REPO=$(cd "$(dirname "$0")/.." && pwd)
target=${1:?ssh target, e.g. eckert@141.19.143.18}
dry=${2:-}
[ -z "$dry" ] || [ "$dry" = --dry-run ] || { echo "unknown option $dry"; exit 1; }
cd "$REPO/services"
set -a; . ./.env; set +a
DATA=${DATA:-/data/mannheim}
db=${FUSEKI_DB:?FUSEKI_DB is not set in services/.env}
SSH="ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=$HOME/.ssh/known_hosts"
remote() { $SSH "$target" "$@"; }
# rsync as root on both sides (the files belong to container users); the agent of the deploy user goes along (sudo
# env: sudo-rs of Ubuntu 26.04 ignores sudo -E). DELETE=--delete mirrors the source (the default); the store is only
# added to, so that /dumps keeps the files of earlier versions.
copy() {
  sudo env SSH_AUTH_SOCK="${SSH_AUTH_SOCK:?no ssh agent: connect with ssh -A}" \
    rsync -aHS ${DELETE---delete} --info=stats1 ${dry:+--dry-run} -e "$SSH" --rsync-path="sudo rsync" "$@"
}
# a directory whose files keep the owner the target directory has (user ids differ between the VMs)
copy_owned() {
  local src=$1 dst=$2 owner
  owner=$(remote "stat -c %u:%g $dst 2>/dev/null || stat -c %u:%g $(dirname "$dst")")
  copy --no-owner --no-group "$src/" "$target:$dst/"
  [ -n "$dry" ] || remote "sudo chown -R $owner $dst"
}
count() { curl -sf "http://127.0.0.1:3030/judaicalink/query" -H 'Accept: text/csv' \
  --data-urlencode 'query=SELECT (COUNT(*) AS ?triples) { GRAPH ?g { ?s ?p ?o } }' | tail -1 | tr -d '\r'; }
showcases=()
for s in "$DATA"/src/*/compose.yml; do
  d=$(basename "$(dirname "$s")"); [ "$d" = judaicalink-mannheim ] || showcases+=("$d")
done

echo "== checking: the same commits on both VMs, the database"
for r in judaicalink-mannheim "${showcases[@]}"; do
  a=$(git -C "$DATA/src/$r" rev-parse HEAD); b=$(remote "git -C $DATA/src/$r rev-parse HEAD 2>/dev/null" || true)
  [ "$a" = "$b" ] || { echo "$r differs: here $a, there ${b:-missing}"; exit 1; }
done
[ -d "$db" ] || { echo "no database $db"; exit 1; }
triples=$(count)
echo "database $db: $triples triples"

# the database on the target: the name of this one, unless that is the database the target's endpoint uses (never
# written while it serves): then the next free name, -2, -3 …, as load.sh names them
active=$(remote "grep -oP '^FUSEKI_DB=\K.*' $DATA/src/judaicalink-mannheim/services/.env" || true)
dest=$db; n=1
while [ "$dest" = "$active" ]; do n=$((n + 1)); dest=$db-$n; done
echo "on the target: $dest (its endpoint uses ${active:-none})"

echo "== the store (added to), the database, the generated pages"
DELETE= copy_owned "$DATA/store" "$DATA/store"
copy_owned "$db" "$dest"          # rsync makes the directory; a dry run changes nothing on the target
[ -f "$db.log" ] && copy --no-owner --no-group "$db.log" "$target:$dest.log"
copy_owned "$DATA/www/generated" "$DATA/www/generated"
if [ -n "$dry" ]; then
  echo "dry run: Solr and the showcase data are copied with the services stopped, not compared here"; exit 0
fi

echo "== Solr and the showcase data, with the services stopped on the target"
remote "cd $DATA/src/judaicalink-mannheim/services && docker compose stop solr graph"
for d in "${showcases[@]}"; do remote "cd $DATA/src/$d && docker compose stop"; done
copy --numeric-ids "$DATA/solr/" "$target:$DATA/solr/"          # owned by the Solr container user, the same id
for d in "$DATA"/showcases/*/; do copy_owned "${d%/}" "$DATA/showcases/$(basename "$d")"; done

echo "== switching the target to $dest, starting the services"
remote "cd $DATA/src/judaicalink-mannheim/services && sed -i 's#^FUSEKI_DB=.*#FUSEKI_DB=$dest#' .env &&
  FUSEKI_DB=$dest docker compose up -d fuseki solr graph"
for d in "${showcases[@]}"; do remote "cd $DATA/src/$d && docker compose up -d"; done
there=""
for _ in $(seq 120); do
  there=$(remote "curl -sf http://127.0.0.1:3030/judaicalink/query -H 'Accept: text/csv' \
    --data-urlencode 'query=SELECT (COUNT(*) AS ?triples) { GRAPH ?g { ?s ?p ?o } }' | tail -1 | tr -d '\r'" || true)
  [ -n "$there" ] && break; sleep 5
done
echo "target: ${there:-no answer} triples (here $triples)"
[ "$there" = "$triples" ] || { echo "the counts differ: check the target before anything else"; exit 1; }
echo "previous databases on the target (remove by hand):"; remote "ls -d $DATA/fuseki/db-* | grep -v '\.log$' | grep -vx $dest" || true
