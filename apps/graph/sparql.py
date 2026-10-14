"""A small SPARQL client (standard library): SELECT as rows of terms, CONSTRUCT as N-Triples, streaming TSV."""

import csv
import io
import json
import os
import urllib.parse
import urllib.request

ENDPOINT = os.environ.get("JL_SPARQL", "http://localhost:3030/internal/query")
AGENT = "judaicalink-mannheim graph (https://mannheim.judaicalink.org/)"


def _post(query, accept, timeout):
    data = urllib.parse.urlencode({"query": query}).encode()
    req = urllib.request.Request(ENDPOINT, data=data, headers={
        "Accept": accept, "Content-Type": "application/x-www-form-urlencoded", "User-Agent": AGENT})
    return urllib.request.urlopen(req, timeout=timeout)


class Term(dict):
    """A result term: {'type': 'uri'|'literal'|'bnode', 'value': …, 'xml:lang'?, 'datatype'?}."""

    @property
    def value(self):
        return self["value"]

    @property
    def is_iri(self):
        return self["type"] == "uri"

    @property
    def lang(self):
        return self.get("xml:lang", "")

    @property
    def datatype(self):
        return self.get("datatype", "")

    def n3(self):
        if self.is_iri:
            return f"<{self.value}>"
        if self["type"] == "bnode":
            return f"_:{self.value}"
        v = self.value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r")
        if self.lang:
            return f'"{v}"@{self.lang}'
        if self.datatype:
            return f'"{v}"^^<{self.datatype}>'
        return f'"{v}"'


def select(query, timeout=120):
    """Rows as dicts of variable -> Term (unbound variables are missing)."""
    with _post(query, "application/sparql-results+json", timeout) as r:
        res = json.load(r)
    return [{k: Term(v) for k, v in b.items()} for b in res["results"]["bindings"]]


def ask(query, timeout=60):
    with _post(query, "application/sparql-results+json", timeout) as r:
        return json.load(r).get("boolean", False)


def construct(query, accept="application/n-triples", timeout=120):
    with _post(query, accept, timeout) as r:
        return r.read()


def select_tsv(query, timeout=36000):
    """Stream a large SELECT as tuples of plain values (IRIs without <>, literals as their text, language and
    datatype dropped): for the jobs that read much of the graph."""
    with _post(query, "text/csv", timeout) as r:
        reader = csv.reader(io.TextIOWrapper(r, encoding="utf-8", newline=""))
        next(reader, None)
        yield from reader
