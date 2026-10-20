# judaicalink-mannheim

The platform of **mannheim.judaicalink.org**: the Mannheim place for showcases and demonstrators of the work on
JudaicaLink, and our current version of the knowledge graph. It is not a production service (that runs in Frankfurt)
and not a staging copy of it: showcases are meant to be quick to put up and to keep working without upkeep.
Decisions: [`docs/decisions/`](docs/decisions/) (the platform; decisions about the data are in judaicalink-data).

This repository holds only the central parts. **Every showcase has its own repository.**

```
internet ─▶ nginx (host, TLS) ─┬─ /                 static Hugo site (site/)          /data/mannheim/www/site
                               ├─ /<showcase>/      static showcase                   /data/mannheim/www/showcases/<path>
                               │                    or a showcase container           127.0.0.1:<port>
                               ├─ /sparql           Fuseki, read-only                 127.0.0.1:3030 (container)
                               ├─ /data/ /datasets/ /ontology/ /search/   apps/graph  127.0.0.1:8090 (container)
                               ├─ /dashboard/ /status.json   made by the jobs         /data/mannheim/www/generated
                               └─ /dumps/           the files of the loaded versions  /data/mannheim/store
Docker network "judaicalink": fuseki (/judaicalink, /internal), solr ◀── graph, showcase containers
```

| Path | What |
|---|---|
| `host/install.sh` | sets up a fresh Ubuntu VM (24.04 or 26.04 LTS): packages, Docker (storage on `/data/docker`), firewall, directories, TLS, nginx |
| `host/deploy.sh` | copies the site (built here) or a static showcase to the VM |
| `host/local-vm.yaml` | a local test VM (Lima on macOS) set up the same way |
| `host/nginx/` | the nginx site; `showcases.py` writes the showcase locations from the registry |
| `services/compose.yml` | the central services: `fuseki` (read-only; public service and an internal one without time limit), `fuseki-load` (only while loading), `solr` (cores owned by the applications), `graph` (the platform application) |
| `apps/graph/` | the platform application: views of every JudaicaLink IRI (`/data/`, `/datasets/`, `/ontology/`, HTML or RDF), the graph search (`/search/`), and its jobs (`jobs.py`: figures of the graph, search index, dashboard) |
| `services/fuseki/` | the Fuseki image (release jar, pinned by checksum), its configuration, the loader `load.py` |
| `services/load.sh` | builds a new database from the data index, checks it, switches the endpoint |
| `site/` | the Hugo site; `site/data/showcases.toml` is the registry of the showcases; `static/kit/1/` the shared look |

## Principles

- **Static first.** A showcase is static files if it can be: results computed ahead, data embedded. A showcase that
  accompanies a publication keeps a frozen copy of its results and names the data versions it used, so it still
  works when the endpoint has moved on to newer data.
- **Few services, all private.** Containers publish only on 127.0.0.1; nginx is the only public entry. Docker
  bypasses the firewall (ufw) for published ports, so `127.0.0.1:` in every `ports:` entry is a must.
- **Read-only.** No logins, no databases written by visitors. The public Fuseki service has no update, upload or
  admin endpoints; databases are built by a separate loader container and switched in.
- **Same technology as Frankfurt** where it fits (Fuseki, Solr, Python), so that something can be adopted there,
  without copying their setup.
- **Reproducible.** Everything on the VM comes from this repository, the showcase repositories, and the published
  data; nothing depends on what grows on the VM.

## Setting up the VM

```sh
sudo mkdir -p /data/mannheim/src && sudo chown $USER: /data/mannheim/src
git clone https://github.com/judaicalink/judaicalink-mannheim /data/mannheim/src/judaicalink-mannheim
cd /data/mannheim/src/judaicalink-mannheim
sudo DEPLOY_USER=$USER host/install.sh   # then log out and in again (groups docker, fuseki)
```

DNS for mannheim.judaicalink.org must point to the VM before `install.sh`, and port 80 must be open from the internet
(the certificate is requested there); until then `TLS=self-signed TLS_EXTRA=IP:<address>` (see the head of install.sh).

Size: 4 cores, 32 GB RAM (24 GB at least), 100 GB disk. The programs take about 10 GB (heaps in `services/.env`:
Fuseki 5–8 GB, Solr 3–4 GB); the rest is the file cache for what searches and pages read: the Fuseki database
(7.5 GB), the Compact Memory core (6.8 GB) and the graph core (0.3 GB), as of 2026-10. With 15 GB the first view of a
page can take seconds on a slow disk. After a boot, `mannheim-warm-cache.service` (install.sh) reads the database and the cores
once, so that they are in the cache (about a minute; `journalctl -u mannheim-warm-cache`).

## Data and services

```sh
cd services
./load.sh             # downloads into /data/mannheim/store, loads, checks, starts the endpoint, runs the jobs
docker compose ps
```

`load.sh` builds a new database `/data/mannheim/fuseki/db-<date>` in the `fuseki-load` container (over HTTP; the
bulk loader of Fuseki 6.2.0 wraps integers beyond 64 bits), applies the corrections, compares every graph with
the `void:triples` of its `-meta`, and only then points `FUSEKI_DB` in `services/.env` to it and restarts `fuseki`.
Then it compacts the database (each upload leaves old copies of the changed blocks behind: 14 GB instead of 7.5 GB;
about 20 minutes on the VM) and compares the triple count again; it skips the compaction when the files have numbers of 19 or more digits,
because `tdb2.tdbcompact` 6.2.0 wraps integers beyond 64 bits like the bulk loader.
If anything fails, the endpoint stays as it was. Old databases are removed by hand
(`sudo rm -rf /data/mannheim/fuseki/db-…`, they belong to the container user).

What is loaded is derived from `catalog/dataindex.json` of judaicalink-data: the stable version of every dataset that
is not replaced, one named graph per dataset, its `-meta` in `<graph>/meta`. Run it again after new versions are
published. Heap: `FUSEKI_HEAP` in `.env` (default 8g).
The showcases are not updated by the reload: run their own steps afterwards (Compact Memory: `bin/index.sh` and the
dashboard job; Library of Haskala: build with the new `ep` and deploy; see their READMEs).

Queries over the whole graph take seconds on Fuseki (counting classes about 13 s, a substring search over all
labels about 25 s; measured in the workspace, `endpoints/`). Showcases compute such numbers ahead; text search
belongs in Solr.

## The site

Built here and copied, like web.judaicalink.org: `host/deploy.sh <ssh-host> site`.

## Local test VM

A VM on the Mac, set up exactly like the real one (Lima, Ubuntu Server 26.04 LTS, self-signed certificate):

```sh
brew install lima
limactl start --name=mannheim host/local-vm.yaml          # mounts this repository read-only
limactl shell mannheim -- bash -c 'sudo mkdir -p /data/mannheim/src && sudo chown $USER: /data/mannheim/src &&
  rsync -a --exclude services/.env $PWD/ /data/mannheim/src/judaicalink-mannheim/ &&
  cd /data/mannheim/src/judaicalink-mannheim && sudo TLS=self-signed host/install.sh'
limactl shell mannheim -- sudo -iu $USER /data/mannheim/src/judaicalink-mannheim/services/load.sh
host/deploy.sh lima-mannheim site
```

Then https://localhost (accept the certificate). `limactl stop mannheim` / `limactl delete mannheim`.

On Linux (Lima from the release tarball, QEMU from the distribution, e.g. `qemu-base` on Arch), the same file with
QEMU, the path of the checkout and host ports a user may open; the other steps are the same:

```sh
limactl start --name=mannheim --set '.vmType="qemu" | .memory="20GiB"
  | .mounts[0].location="~/judaicalink/judaicalink-mannheim"
  | .portForwards[0].hostPort=8080 | .portForwards[1].hostPort=8443' host/local-vm.yaml
```

Then https://localhost:8443 on that machine (from another one: `ssh -L 8443:localhost:8443 <host>`).

## The platform bar and the kit

nginx puts the platform bar into every HTML page that contains the line
`<!--# include virtual="/kit/1/header.html" -->` (server-side includes, SSI): no JavaScript, no delay, and search
engines see the links. The bar is built by Hugo from `site/layouts/partials/header.html` and the registry, so a new
showcase appears in every bar with the next site build. Outside the platform the line is an HTML comment.
`/kit/1/jl.css` is the common look (colours, type, components) for showcases that want it. Kit 1 only gets
compatible changes; a breaking change becomes `/kit/2/`.

## Showcases

A showcase is its own repository. It is entered in `site/data/showcases.toml` (path, title, description; `port`
if it has a server; optionally repository and publication), then on the VM:
`sudo python3 host/nginx/showcases.py && sudo nginx -t && sudo systemctl reload nginx`, and the site is rebuilt.

Every showcase page has the platform bar right after `<body>`, and no margin on `body`:

```html
<body>
<!--# include virtual="/kit/1/header.html" -->
```

**Static showcase:** its repository builds a directory with an `index.html`, which is copied to
`/data/mannheim/www/showcases/<path>/` with `host/deploy.sh <ssh-host> <path> <directory>`.

Links inside must be relative (or start with `/<path>/`). If it queries the endpoint from the browser, it uses
`https://mannheim.judaicalink.org/sparql` (CORS is allowed).

**Showcase with a server:** its repository has a `Dockerfile` and a `compose.yml` like this, and is cloned to
`/data/mannheim/src/<repository>` and started there with `docker compose up -d --build`:

```yaml
services:
  app:
    build: .
    restart: unless-stopped
    environment:
      JL_SPARQL: http://fuseki:3030/judaicalink/query   # the endpoint inside the network
      JL_BASE: /entities                                # its path; nginx passes the full path on
    ports:
      - "127.0.0.1:8101:8101"                           # the port of the registry; never without 127.0.0.1
    networks: [judaicalink]
    read_only: true
networks:
  judaicalink:
    external: true
```

A showcase with a server must escape what visitors type before putting it into a page (as any web application
should): nginx would otherwise treat a typed `<!--# … -->` as an instruction.

A showcase may expect: the endpoint (and later Solr) under these names, its path, and nothing else of the server.
It must not write anywhere but its own volumes, and it pins what it depends on (base image, packages), so that it
still builds years later.
