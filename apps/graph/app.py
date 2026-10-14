#!/usr/bin/env python3
"""The platform's application: views of JudaicaLink IRIs (/data/, /datasets/, /ontology/) and the graph search
(/search/). Standard library only; behind nginx, which adds the platform bar (SSI).

    JL_SPARQL=http://localhost:3030/internal/query JL_SOLR=http://localhost:8983/solr python3 app.py
"""

import json
import os
import sys
import traceback
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import search
import views
from common import esc, page

HOST = os.environ.get("JL_HOST", "0.0.0.0")
PORT = int(os.environ.get("JL_PORT", "8090"))
STATIC = Path(__file__).parent / "static"


class Handler(BaseHTTPRequestHandler):
    server_version = "judaicalink-graph"
    sys_version = ""

    def log_message(self, fmt, *args):
        sys.stderr.write("%s %s\n" % (self.address_string(), fmt % args))

    def send(self, r):
        body = r.body.encode("utf-8") if isinstance(r.body, str) else r.body
        self.send_response(r.status)
        self.send_header("Content-Type", r.ctype)
        self.send_header("Content-Length", str(len(body)))
        for k, v in r.headers.items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        url = urllib.parse.urlsplit(self.path)
        path = urllib.parse.unquote(url.path)
        qs = urllib.parse.parse_qs(url.query)
        accept = self.headers.get("Accept", "")
        try:
            self.send(route(path, qs, accept))
        except Exception:                                   # one broken view must not take the app down
            traceback.print_exc()
            self.send(views.Response(500, page("Error", "<h1>Something went wrong</h1><p>The error was logged.</p>")))


def route(path, qs, accept):
    if path.startswith("/data/") and len(path) > 6:
        return views.resource(path[1:], accept)            # data/<namespace>/<id>, as in http://data.judaicalink.org/
    if path in ("/datasets", "/datasets/"):
        return views.datasets_index()
    if path.startswith("/datasets/"):
        return views.dataset_page(path[len("/datasets/"):].strip("/"), accept)
    if path in ("/ontology", "/ontology/"):
        return views.ontology_index()
    if path.startswith("/ontology/"):
        return views.ontology_term(path[len("/ontology/"):].strip("/"), accept)
    if path in ("/search", "/data", "/data/"):
        return views.Response(301, "", headers={"Location": "/search/"})
    if path == "/search/":
        return views.Response(200, search.view(qs))
    if path == "/search/suggest":
        return views.Response(200, json.dumps(search.suggest(qs), ensure_ascii=False), "application/json; charset=utf-8",
                              {"Access-Control-Allow-Origin": "*"})
    if path.startswith("/search/static/"):
        f = (STATIC / path[len("/search/static/"):]).resolve()
        if f.is_file() and STATIC.resolve() in f.parents:
            ctype = {"css": "text/css", "js": "text/javascript"}.get(f.suffix[1:], "application/octet-stream")
            return views.Response(200, f.read_bytes(), ctype + "; charset=utf-8", {"Cache-Control": "max-age=3600"})
    return views.Response(404, page("Not found", f"<h1>Not found</h1><p><code>{esc(path)}</code></p>"))


if __name__ == "__main__":
    print(f"graph app on {HOST}:{PORT}", flush=True)
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
