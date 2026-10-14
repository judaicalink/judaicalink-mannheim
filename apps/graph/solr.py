"""A small Solr client (standard library) for cores owned by one application.

A rebuild goes into a new, uniquely named core, made on the host with `solr create` (services/solr-core.sh), which gives
the core its own copy of the _default configset (a core made over CoreAdmin with configSet=_default would share and
change the configset of all such cores). Its fields are defined here with the Schema API (guessing of new fields
switched off); then it is swapped in under the name the application searches, so that searches never see a
half-built index (decision 0004).
"""

import json
import os
import urllib.parse
import urllib.request

BASE = os.environ.get("JL_SOLR", "http://localhost:8983/solr").rstrip("/")


def _req(path, data=None, params=None, timeout=300):
    url = f"{BASE}/{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params, doseq=True)
    body = None if data is None else json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def cores():
    return set(_req("admin/cores", params={"action": "STATUS", "wt": "json"})["status"])


def define(core, fields, copy_fields=(), field_types=()):
    """Define the fields of a new core (made by services/solr-core.sh)."""
    if core not in cores():
        raise SystemExit(f"Solr core {core} does not exist: make it with services/solr-core.sh first")
    _req(f"{core}/config", {"set-user-property": {"update.autoCreateFields": "false"}})
    existing = {f["name"] for f in _req(f"{core}/schema/fields")["fields"]}
    types = {t["name"] for t in _req(f"{core}/schema/fieldtypes")["fieldTypes"]}
    cmds = {}
    for t in field_types:
        cmds.setdefault("replace-field-type" if t["name"] in types else "add-field-type", []).append(t)
    for f in fields:
        cmds.setdefault("replace-field" if f["name"] in existing else "add-field", []).append(f)
    if copy_fields:
        cmds["add-copy-field"] = list(copy_fields)
    if cmds:
        _req(f"{core}/schema", cmds)


def add(core, docs, commit_within=60000):
    if docs:
        _req(f"{core}/update", docs, params={"commitWithin": commit_within})


def commit(core):
    _req(f"{core}/update", {"commit": {}}, timeout=3600)


def swap(core, new):
    """Make <new> the core <core>; the old one (now named <new>) is dropped with its directory."""
    if core in cores():
        _req("admin/cores", params={"action": "SWAP", "core": core, "other": new})
        _req("admin/cores", params={"action": "UNLOAD", "core": new, "deleteInstanceDir": "true"})
    else:
        _req("admin/cores", params={"action": "RENAME", "core": new, "other": core})


def select(core, params, timeout=60):
    p = dict(params)
    p.setdefault("wt", "json")
    data = urllib.parse.urlencode(p, doseq=True).encode()
    req = urllib.request.Request(f"{BASE}/{core}/select", data=data,
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)
