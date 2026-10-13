#!/usr/bin/env bash
# Copy the site or a static showcase to the VM (rsync over ssh; the files of the VM are replaced).
#   host/deploy.sh <ssh-host> site                       build the Hugo site here and copy it
#   host/deploy.sh <ssh-host> <path> <directory>         a static showcase: <directory> becomes /<path>/
# The local test VM (host/local-vm.yaml) is the ssh host lima-mannheim.
set -euo pipefail
REPO=$(cd "$(dirname "$0")/.." && pwd)
host=${1:?ssh host}; what=${2:?site or a showcase path}

ssh_cmd=ssh
lima_cfg=~/.lima/${host#lima-}/ssh.config
[[ $host == lima-* && -f $lima_cfg ]] && ssh_cmd="ssh -F $lima_cfg"

if [ "$what" = site ]; then
  out=$(mktemp -d) && chmod 755 "$out"     # mktemp makes it 700, and rsync would copy that to the web root
  trap 'rm -rf "$out"' EXIT
  hugo --source "$REPO/site" -d "$out" --quiet
  src=$out/; dest=/data/mannheim/www/site/
else
  dir=${3:?the directory of the showcase}
  [ -f "$dir/index.html" ] || { echo "$dir has no index.html"; exit 1; }
  grep -q "^path = \"$what\"" "$REPO/site/data/showcases.toml" || { echo "$what is not in site/data/showcases.toml"; exit 1; }
  src=${dir%/}/; dest=/data/mannheim/www/showcases/$what/
fi
rsync -a --delete -e "$ssh_cmd" "$src" "$host:$dest"
echo "copied to $host:$dest"
