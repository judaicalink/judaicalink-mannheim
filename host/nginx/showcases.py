#!/usr/bin/env python3
"""Write the nginx locations of the showcases from site/data/showcases.toml (one file per showcase).

A showcase with a `port` has a server (a container of its own repository, on 127.0.0.1:<port>), and its path is
passed on unchanged (the app is told its base path, e.g. /entities); one without is static, served from
/data/mannheim/www/showcases/<path>/. Files of showcases no longer in the registry are removed.

    sudo python3 host/nginx/showcases.py [--out /etc/nginx/mannheim-showcases] && sudo nginx -t && sudo systemctl reload nginx
"""

import argparse
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WWW = "/data/mannheim/www/showcases"
# paths of the platform itself (site sections, nginx locations)
RESERVED = {"sparql", "dumps", "showcases", "data", "datasets", "ontology", "kit", "about", "css", "js", "img", "fonts",
            "tags", "categories"}

STATIC = """location /{path}/ {{
    alias {www}/{path}/;
}}
"""
SERVER = """location /{path}/ {{
    proxy_pass http://127.0.0.1:{port};
    proxy_set_header Accept-Encoding "";     # nginx can include the platform bar (SSI) only into uncompressed HTML
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 130s;
}}
location = /{path} {{ return 301 /{path}/; }}
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--registry", type=Path, default=ROOT / "site" / "data" / "showcases.toml")
    ap.add_argument("--out", type=Path, default=Path("/etc/nginx/mannheim-showcases"))
    args = ap.parse_args()

    showcases = tomllib.loads(args.registry.read_text(encoding="utf-8")).get("showcase", [])
    paths, ports, errors = set(), set(), []
    for s in showcases:
        p = s.get("path", "")
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", p) or p in RESERVED or p in paths:
            errors.append(f"bad or duplicate path: {p!r}")
        if "port" in s and (s["port"] in ports or not 8100 <= s["port"] <= 8999):
            errors.append(f"{p}: port must be unique, 8100-8999")
        paths.add(p)
        ports.add(s.get("port"))
    if errors:
        sys.exit("\n".join(errors))

    args.out.mkdir(parents=True, exist_ok=True)
    keep = set()
    for s in showcases:
        f = args.out / f"{s['path']}.conf"
        tpl = SERVER if "port" in s else STATIC
        f.write_text(f"# {s['title']} (generated from showcases.toml)\n" +
                     tpl.format(path=s["path"], port=s.get("port"), www=WWW), encoding="utf-8")
        keep.add(f.name)
        print(f"{s['path']:<20} {'server :' + str(s['port']) if 'port' in s else 'static'}")
    for f in args.out.glob("*.conf"):
        if f.name not in keep:
            f.unlink()
            print(f"removed {f.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
