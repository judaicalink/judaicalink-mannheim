"""A small Solr client (standard library) for cores owned by one application.

A core is made from the _default configset over the CoreAdmin API, its fields are defined with the Schema API
(guessing of new fields switched off), and a rebuild goes into <core>_new, which is then swapped in, so that searches
never see a half-built index.
"""

import json
import os
import time
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


def create(core, fields, copy_fields=(), field_types=()):
    """Create the core (dropping an old one of that name) with these fields:
    fields: [{'name': …, 'type': …, 'multiValued': …, 'stored': …, 'indexed': …, 'docValues': …}]."""
    if core in cores():
        _req("admin/cores", params={"action": "UNLOAD", "core": core, "deleteInstanceDir": "true"})
    # a directory of its own: after a SWAP or RENAME, core names and directory names no longer match
    _req("admin/cores", params={"action": "CREATE", "name": core, "configSet": "_default",
                                "instanceDir": f"{core}-{time.strftime('%Y%m%d%H%M%S')}"})
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
    """Make <new> the core <core> (the old content ends up in <new>, which is then dropped)."""
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
