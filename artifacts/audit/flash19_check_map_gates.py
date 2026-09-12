#!/usr/bin/env python3
"""T19-01 (deepseek-flash-19): artifact-provenance and dependency-gate control.

STATUS: proposed breadth artifact, UNVERIFIED pending lead review. This script
does not complete any research-map node and makes no mathematical claim.

Why this exists
---------------
`research_map/validate_map.py` checks only that a node marked `done` *has* an
`artifact` string. It never checks that the path exists, that a sha256-carrying
artifact event exists, or that validation evidence is present. A map can
therefore read VALID while every declared artifact is absent. This is the
control for that gap. Integration into the shared validator is deliberately
NOT done here; it is routed to lead-audit as a finding.

Checks
------
C0  hard(done)/warn(active,queued)  node declares an artifact path
C0b hard                            artifact path is absolute or escapes the root
C1  hard(done)/warn(active,queued)  declared artifact exists (file, or dir with
                                    real content at any depth)
C2  hard                            done node has validation_status=passed (or
                                    validated=true) AND recorded evidence_refs
C3  hard(done)/warn(active,queued)  file artifact: an artifact event sha256
                                    matches the file; a *mismatch* is hard at
                                    any status (contradicted ledger entry).
                                    Directory artifact: a passed artifact event
                                    exists (dir hashes need a manifest)
C4  hard                            active/queued node depends on a done node
                                    that fails C0-C3
C4b info                            node depends on a node that is not done yet
C5  warn                            node lacks machine-readable class_ids
C6  hard                            duplicate node id (first occurrence wins)
C7  hard                            dependency cycle
C8  warn                            malformed map field (string depends_on,
                                    unknown status) coerced and recorded

Severities: hard => verdict fail; warn/info => recorded, no fail.

Exit codes: 0 = verdict pass, 1 = verdict fail, 2 = checker error (malformed or
unreadable input; the report, if written, carries verdict "error").

Event discovery: every path passed via --events, plus research_map/events.jsonl
and comms/outbox/ when they exist. Reads .jsonl (one object per line) and .json
(one object or a list). Artifact paths in events are normalised the same way as
map paths, so "./schemas/x.yaml", "schemas/x.yaml" and "schemas//x.yaml" match.

Self-test:
    python3 artifacts/audit/flash19_check_map_gates.py --selftest
Live run:
    python3 artifacts/audit/flash19_check_map_gates.py \
        --map research_map/research_map.json \
        --json-out artifacts/audit/flash19_map_gate_report.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

JUNK = {".DS_Store"}
VALID_STATUSES = {"queued", "active", "blocked", "done", "rejected", "killed"}


class CheckerError(Exception):
    pass


def is_junk(name: str) -> bool:
    return name in JUNK or name.startswith("._")


def real_content(p: Path) -> bool:
    """True if p (dir) contains any non-junk file at any depth."""
    try:
        entries = list(p.iterdir())
    except OSError:
        return False
    for c in entries:
        if is_junk(c.name):
            continue
        if c.is_dir():
            if real_content(c):
                return True
        else:
            return True
    return False


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def norm_rel(root: Path, raw) -> tuple[str | None, str | None]:
    """Canonical root-relative posix path, or (None, reason) if invalid."""
    if not isinstance(raw, str) or not raw.strip():
        return None, "not a non-empty string"
    p = Path(raw)
    if p.is_absolute():
        return None, "absolute path not allowed"
    rr = root.resolve()
    try:
        rq = (root / p).resolve()
    except OSError as exc:
        return None, f"unresolvable: {exc}"
    if rq != rr and rr not in rq.parents:
        return None, "escapes repo root"
    return rq.relative_to(rr).as_posix(), None


def load_events(paths: list[Path]) -> tuple[list[dict], list[str]]:
    events: list[dict] = []
    errors: list[str] = []
    for p in paths:
        if not p.exists():
            errors.append(f"event source does not exist: {p}")
            continue
        files = ([c for c in sorted(p.iterdir()) if c.is_file() and c.suffix in {".jsonl", ".json"}]
                 if p.is_dir() else [p])
        for f in files:
            try:
                raw = f.read_text()
            except (OSError, UnicodeDecodeError) as exc:
                errors.append(f"unreadable event file {f}: {exc}")
                continue
            if f.suffix == ".jsonl":
                for i, line in enumerate(raw.splitlines(), 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError as exc:
                        errors.append(f"{f}:{i}: malformed JSON ({exc.msg})")
                        continue
                    if isinstance(obj, dict):
                        events.append(obj)
                    else:
                        errors.append(f"{f}:{i}: event is not an object")
            else:
                try:
                    obj = json.loads(raw)
                except json.JSONDecodeError as exc:
                    errors.append(f"{f}: malformed JSON ({exc.msg})")
                    continue
                if isinstance(obj, list):
                    for j, item in enumerate(obj):
                        if isinstance(item, dict):
                            events.append(item)
                        else:
                            errors.append(f"{f}[{j}]: event is not an object")
                elif isinstance(obj, dict):
                    events.append(obj)
                else:
                    errors.append(f"{f}: event is not an object")
    return events, errors


def check_map(m: dict, root: Path, events: list[dict], now: str,
              map_path: str, checker_errors: list[str] | None = None) -> dict:
    if not isinstance(m, dict):
        raise CheckerError("map root is not a JSON object")
    findings: list[dict] = []
    nodes: dict[str, tuple[str, dict]] = {}
    mk = m.get("_sha256", "unknown")

    def add(check, severity, node_id, group_id, message, evidence, falsifier,
            class_ids=None):
        findings.append({
            "check": check, "severity": severity, "node_id": node_id,
            "group_id": group_id, "class_ids": class_ids or [],
            "message": message, "evidence_refs": evidence,
            "next_falsifier": falsifier,
        })

    # ---- index nodes, detect duplicate ids and malformed fields ----------
    for g in m.get("groups", []):
        gid = g.get("id", "?")
        for n in g.get("nodes", []):
            nid = n.get("id")
            if not isinstance(nid, str) or not nid:
                add("C8", "warn", "<missing>", gid,
                    "node without a string id skipped", [f"{map_path}#groups/{gid}"],
                    "give the node an id; a nameless node cannot be gated")
                continue
            if nid in nodes:
                add("C6", "hard", nid, gid,
                    f"duplicate node id (first occurrence in group "
                    f"'{nodes[nid][0]}' wins; this occurrence ignored)",
                    [f"{map_path}#groups/{gid}/nodes/{nid}"],
                    "make node ids unique; silently shadowed nodes are ungateable")
                continue
            nodes[nid] = (gid, n)
            st = n.get("status")
            if st not in VALID_STATUSES:
                add("C8", "warn", nid, gid, f"unknown status {st!r}",
                    [f"{map_path}#groups/{gid}/nodes/{nid}"],
                    "use one of " + ", ".join(sorted(VALID_STATUSES)))
            deps = n.get("depends_on", [])
            if isinstance(deps, str):
                add("C8", "warn", nid, gid,
                    f"depends_on is a string ({deps!r}); coerced to one dependency",
                    [f"{map_path}#groups/{gid}/nodes/{nid}"],
                    "use a JSON list even for a single dependency")
            elif not isinstance(deps, list):
                add("C8", "warn", nid, gid, "depends_on is not a list; ignored",
                    [f"{map_path}#groups/{gid}/nodes/{nid}"],
                    "use a JSON list of node ids")

    # ---- index artifact events by canonical path -------------------------
    art_events: dict[str, list[dict]] = {}
    for e in events:
        if e.get("event_type") != "artifact" or not e.get("path"):
            continue
        rel, err = norm_rel(root, e["path"])
        key = rel if rel else f"<invalid>:{e['path']}"
        art_events.setdefault(key, []).append(e)

    def has_evidence(n: dict) -> bool:
        ev = n.get("evidence_refs")
        if isinstance(ev, list) and any(isinstance(x, str) and x.strip() for x in ev):
            return True
        art = n.get("artifact")
        if isinstance(art, str):
            rel, err = norm_rel(root, art)
            if rel and any(e.get("validation_status") == "passed"
                           for e in art_events.get(rel, [])):
                return True
        return False

    def artifact_gate(nid: str, gid: str, n: dict) -> bool:
        """True only if the declared artifact is present and provenance-backed.
        Hard findings only for status=done; active/queued absence is expected
        and recorded as warn so it does not inflate the hard count."""
        status = n.get("status")
        sev = "hard" if status == "done" else "warn"
        art = n.get("artifact")
        if art is None:
            add("C0", sev, nid, gid, "node declares no artifact path",
                [f"{map_path}#groups/{gid}/nodes/{nid}"],
                "add an artifact path and commit it with a sha256 artifact event")
            return False
        rel, err = norm_rel(root, art)
        if err:
            add("C0b", "hard", nid, gid,
                f"invalid artifact path {art!r}: {err}",
                [f"{map_path}#groups/{gid}/nodes/{nid}"],
                "use a root-relative path inside the repo; escapes and absolute "
                "paths cannot be provenance-checked")
            return False
        ap = root / rel
        ev = f"{map_path}#artifact:{rel}"
        if not ap.exists():
            msg = f"declared artifact '{rel}' does not exist"
            if status != "done":
                msg += f" (status={status}; expected while the node is incomplete)"
            add("C1", sev, nid, gid, msg, [ev],
                f"commit '{rel}' and re-run; the finding clears iff it exists")
            return False
        if ap.is_dir():
            if not real_content(ap):
                add("C1", sev, nid, gid,
                    f"declared artifact '{rel}' is an empty directory",
                    [ev], f"commit at least one real file under '{rel}'")
                return False
            passed = [e for e in art_events.get(rel, [])
                      if e.get("validation_status") == "passed"]
            if not passed:
                add("C3", sev, nid, gid,
                    f"directory artifact '{rel}' has no passed artifact event",
                    [ev], f"emit an artifact event for '{rel}' (validation_status="
                          f"passed); without it the directory is unbacked")
                return False
            if any(e.get("sha256") for e in passed):
                add("C3b", "warn", nid, gid,
                    f"directory artifact '{rel}' carries a sha256 that cannot be "
                    f"verified without a manifest",
                    [ev], "publish a manifest file and hash that instead")
            return True
        evs = [e for e in art_events.get(rel, []) if e.get("sha256")]
        if not evs:
            add("C3", sev, nid, gid,
                f"file artifact '{rel}' has no sha256-carrying artifact event",
                [ev], f"emit an artifact event for '{rel}' with its sha256")
            return False
        actual = sha256_file(ap)
        if not any(str(e.get("sha256", "")).lower() == actual for e in evs):
            # A contradicted event is an integrity failure at any status: the
            # ledger claims a hash the file does not have. Absence of an event
            # is status-dependent (C3 above); contradiction is always hard.
            add("C3", "hard", nid, gid,
                f"sha256 mismatch for '{rel}' (file {actual[:16]}...); "
                f"the artifact ledger is stale or wrong",
                [ev] + [f"event:{e.get('event_id', '?')}" for e in evs],
                f"re-hash '{rel}' and emit a matching artifact event; until then "
                f"the recorded provenance is contradicted")
            return False
        return True

    # ---- per-node checks -------------------------------------------------
    for nid, (gid, n) in nodes.items():
        status = n.get("status")
        artifact_gate(nid, gid, n)
        if status == "done":
            if n.get("validation_status") != "passed" and not n.get("validated"):
                add("C2", "hard", nid, gid,
                    "status=done but validation_status is not passed",
                    [f"{map_path}#groups/{gid}/nodes/{nid}"],
                    "record validation_status=passed with evidence, or demote the node")
            if not has_evidence(n):
                add("C2", "hard", nid, gid,
                    "status=done with no non-empty evidence_refs and no passed "
                    "artifact event",
                    [f"{map_path}#groups/{gid}/nodes/{nid}"],
                    "attach evidence_refs (artifact hash + validation command/output) "
                    "or demote the node")
        if not (n.get("class_ids") or n.get("class_id")):
            add("C5", "warn", nid, gid,
                "no machine-readable class_ids; class binding and leakage are not "
                "reviewable",
                [f"{map_path}#groups/{gid}/nodes/{nid}"],
                "lead adds class_ids from the frozen taxonomy")

    # ---- duplicate deps / unknown deps / dependency gate -----------------
    hard_checks = {"C0b", "C1", "C2", "C3", "C6", "C7"}
    gated = {nid: not any(f["node_id"] == nid and f["check"] in hard_checks
                          for f in findings) for nid in nodes}
    for nid, (gid, n) in nodes.items():
        deps = n.get("depends_on", [])
        if isinstance(deps, str):
            deps = [deps]
        if not isinstance(deps, list):
            deps = []
        seen = set()
        for dep in deps:
            if not isinstance(dep, str):
                add("C8", "warn", nid, gid, f"non-string dependency {dep!r} ignored",
                    [f"{map_path}#groups/{gid}/nodes/{nid}"],
                    "use node-id strings")
                continue
            if dep in seen:
                add("C8", "warn", nid, gid, f"duplicate dependency '{dep}'",
                    [f"{map_path}#groups/{gid}/nodes/{nid}"], "deduplicate depends_on")
                continue
            seen.add(dep)
            if dep not in nodes:
                add("C4", "hard", nid, gid, f"depends on unknown node '{dep}'",
                    [f"{map_path}#groups/{gid}/nodes/{nid}"],
                    "fix the dependency id or add the missing node")
                continue
            dep_n = nodes[dep][1]
            if n.get("status") in {"active", "queued"}:
                if dep_n.get("status") == "done" and not gated[dep]:
                    add("C4", "hard", nid, gid,
                        f"depends on '{dep}', marked done but failing its artifact gate",
                        [f"{map_path}#groups/{gid}/nodes/{nid}",
                         f"{map_path}#groups/{nodes[dep][0]}/nodes/{dep}"],
                        f"fix '{dep}' gate findings (C0-C3); '{nid}' may only start "
                        f"on a gated dependency")
                elif dep_n.get("status") != "done":
                    add("C4b", "info", nid, gid,
                        f"dependency '{dep}' is '{dep_n.get('status')}', node "
                        f"correctly not started",
                        [f"{map_path}#groups/{gid}/nodes/{nid}"],
                        f"re-run when '{dep}' reaches done with a passing gate")

    # ---- cycles ----------------------------------------------------------
    adj: dict[str, list[str]] = {nid: [] for nid in nodes}
    for nid, (gid, n) in nodes.items():
        deps = n.get("depends_on", [])
        if isinstance(deps, str):
            deps = [deps]
        for dep in (deps if isinstance(deps, list) else []):
            if isinstance(dep, str) and dep in nodes:
                adj[dep].append(nid)
    color: dict[str, int] = {}

    def dfs(x: str) -> None:
        color[x] = 1
        for y in adj.get(x, []):
            if color.get(y) == 1:
                add("C7", "hard", y, nodes[y][0],
                    f"dependency cycle involving '{x}' and '{y}'",
                    [f"{map_path}#groups/{nodes[y][0]}/nodes/{y}"],
                    "break the cycle; a cyclic map cannot be scheduled")
            elif color.get(y, 0) == 0:
                dfs(y)
        color[x] = 2

    for nid in nodes:
        if color.get(nid, 0) == 0:
            dfs(nid)

    for e in checker_errors or []:
        add("X", "warn", "<input>", "?", f"checker input warning: {e}", [],
            "fix the event source; malformed input can hide provenance")

    counts = {"hard": 0, "warn": 0, "info": 0}
    for f in findings:
        counts[f["severity"]] += 1
    verdict = "error" if checker_errors else ("fail" if counts["hard"] else "pass")
    return {
        "report_id": f"flash19-map-gate-{now}",
        "generated_at": now,
        "worker": "deepseek-flash-19",
        "task": "T19-01",
        "checker_version": "v3",
        "status": "unverified",
        "map_path": map_path,
        "map_sha256": mk,
        "checker": "artifacts/audit/flash19_check_map_gates.py",
        "checks_run": ["C0", "C0b", "C1", "C2", "C3", "C3b", "C4", "C4b",
                       "C5", "C6", "C7", "C8", "X"],
        "counts": counts,
        "verdict": verdict,
        "findings": findings,
        "limitations": [
            "existence/provenance only; does not validate scientific content",
            "directory artifacts require a passed event but their content is not "
            "hashed (needs a manifest file)",
            "evidence_refs are checked for presence, not resolved content",
            "runs on a snapshot: map_sha256 pins the map JSON but artifact "
            "existence is evaluated against the filesystem at run time",
            "class_ids are still absent from the live map, so C5 records the gap "
            "rather than checking leakage",
        ],
    }


# --------------------------------------------------------------------------
# self-test
# --------------------------------------------------------------------------
def _emit(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=2) if isinstance(obj, dict)
                    else "\n".join(json.dumps(x) for x in obj) + "\n")


def _fixture(tmp: Path, doc: str, mode: str) -> tuple[Path, Path]:
    root = tmp / doc
    (root / "research_map").mkdir(parents=True)
    (root / "out").mkdir()
    x = root / "schemas" / "x.yaml"
    x.parent.mkdir(parents=True)
    x.write_text("class_id: TEST-CLASS\n")
    child = root / "schemas" / "child.yaml"
    child.write_text("class_id: TEST-CLASS\n")
    outside = root.parent / "outside.txt"
    outside.write_text("outside\n")
    d = root / "reviews"
    d.mkdir()
    (d / "r1.md").write_text("review\n")

    f0 = {"id": "F0", "status": "done", "validation_status": "passed",
          "artifact": "schemas/x.yaml", "evidence_refs": ["run:selftest"],
          "class_ids": ["TEST-CLASS"], "depends_on": []}
    f1 = {"id": "F1", "status": "queued", "artifact": "schemas/child.yaml",
          "class_ids": ["TEST-CLASS"], "depends_on": ["F0"]}
    nodes = [f0, f1]
    groups = [{"id": "formulation", "nodes": nodes}]
    event_path = "schemas/x.yaml"

    if mode == "neg_dep":
        x.unlink()
    elif mode == "neg_hash":
        pass
    elif mode == "neg_hash_active":
        f0["status"] = "active"
        del f0["validation_status"]
    elif mode == "neg_escape":
        f0["artifact"] = "../outside.txt"
        f0["evidence_refs"] = ["run:selftest"]
    elif mode == "neg_dup":
        x.unlink()
        nodes.append({"id": "F0", "status": "done", "validation_status": "passed",
                      "artifact": "schemas/x.yaml", "evidence_refs": ["run:ok"],
                      "class_ids": ["TEST-CLASS"], "depends_on": []})
    elif mode == "neg_dir_unbacked":
        f0["artifact"] = "reviews/"
        event_path = "reviews/"
    elif mode == "neg_cycle":
        f0.update(status="active", validation_status=None)
        del f0["validation_status"]
        f1.update(status="active", artifact="schemas/child.yaml")
        f1["depends_on"] = ["F0"]
        f0["depends_on"] = ["F1"]
    elif mode == "pos_alias":
        event_path = "./schemas//x.yaml"
    elif mode == "warn_active_missing":
        f1["status"] = "active"
        f1["artifact"] = "schemas/nope.yaml"

    _emit(root / "research_map" / "research_map.json",
          {"schema_version": "0.1", "groups": groups})

    def ev(eid, node, path, sha, status="passed"):
        return {"event_id": eid, "event_type": "artifact",
                "created_at": "2026-09-11T00:00:00+00:00", "actor": "selftest",
                "node_id": node, "artifact_type": "yaml", "path": path,
                "sha256": sha, "validation_status": status}

    hx = hashlib.sha256(x.read_bytes()).hexdigest() if x.exists() else "0" * 64
    hc = hashlib.sha256(child.read_bytes()).hexdigest()
    if mode in {"neg_hash", "neg_hash_active"}:
        hx = "0" * 64
    if mode in {"pos", "pos_json", "pos_alias"}:
        events = [ev("e1", "F0", event_path, hx), ev("e2", "F1", "schemas/child.yaml", hc)]
    elif mode == "warn_active_missing":
        events = [ev("e1", "F0", event_path, hx)]
    elif mode == "neg_dir_unbacked":
        events = []
    else:
        events = [ev("e1", "F0", event_path, hx)]
    if mode == "pos_json":
        (root / "out" / "ev.json").write_text(json.dumps(events, indent=2) + "\n")
    else:
        _emit(root / "out" / "ev.jsonl", events)
    return root, root / "out"


def selftest() -> int:
    cases = [
        # name, doc, mode, want_fail, required (check,node,severity), forbidden
        ("neg dep: done dep missing artifact -> C1 hard + C4 hard",
         "neg_dep", "neg_dep", True, [("C1", "F0", "hard"), ("C4", "F1", "hard")], []),
        ("neg hash: sha mismatch -> C3 hard",
         "neg_hash", "neg_hash", True, [("C3", "F0", "hard")], []),
        ("neg hash active: contradicted event is hard even when not done",
         "neg_hash_active", "neg_hash_active", True, [("C3", "F0", "hard")], []),
        ("neg escape: ../outside.txt -> C0b hard",
         "neg_escape", "neg_escape", True, [("C0b", "F0", "hard")], []),
        ("neg dup: duplicate id -> C6 hard",
         "neg_dup", "neg_dup", True, [("C6", "F0", "hard")], []),
        ("neg dir unbacked: non-empty dir, no event -> C3 hard",
         "neg_dir_unbacked", "neg_dir_unbacked", True, [("C3", "F0", "hard")], []),
        ("neg cycle: A<->B -> C7 hard",
         "neg_cycle", "neg_cycle", True, [("C7", "*", "hard")], []),
        ("pos: all gated -> 0 hard", "pos", "pos", False, [], []),
        ("pos json: list-of-events .json ingested -> 0 hard",
         "pos_json", "pos_json", False, [], []),
        ("pos alias: './schemas//x.yaml' matches 'schemas/x.yaml' -> 0 hard",
         "pos_alias", "pos_alias", False, [], []),
        ("warn-active-missing: active node missing artifact -> 0 hard, C1 warn",
         "warn_active", "warn_active_missing", False, [("C1", "F1", "warn")],
         [("C1", "F1", "hard")]),
    ]
    failures = []
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        for name, doc, mode, want_fail, required, forbidden in cases:
            root, out = _fixture(tmp, doc, mode)
            mp = root / "research_map" / "research_map.json"
            m = json.loads(mp.read_text())
            events, errs = load_events([out])
            if errs:
                print(f"[FAIL] {name}: fixture event errors {errs}")
                failures.append(name)
                continue
            rep = check_map(m, root, events, "selftest",
                            "research_map/research_map.json")
            ok = (rep["verdict"] == "fail") == want_fail
            for check, node, sev in required:
                hit = any(f["check"] == check and f["severity"] == sev
                          and (node == "*" or f["node_id"] == node)
                          for f in rep["findings"])
                ok = ok and hit
                if not hit:
                    print(f"        missing required {check}/{node}/{sev}")
            for check, node, sev in forbidden:
                hit = any(f["check"] == check and f["severity"] == sev
                          and f["node_id"] == node for f in rep["findings"])
                ok = ok and not hit
                if hit:
                    print(f"        forbidden {check}/{node}/{sev} present")
            print(f"[{'PASS' if ok else 'FAIL'}] {name}: "
                  f"verdict={rep['verdict']} counts={rep['counts']}")
            if not ok:
                failures.append(name)
    print("selftest:", "PASS" if not failures else f"FAIL {failures}")
    return 0 if not failures else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[2]))
    ap.add_argument("--map", default="research_map/research_map.json")
    ap.add_argument("--events", nargs="*", default=None)
    ap.add_argument("--json-out")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    try:
        root = Path(a.root).resolve()
        mp = Path(a.map)
        if not mp.is_absolute():
            mp = root / mp
        if not mp.exists():
            raise CheckerError(f"map not found: {mp}")
        raw = mp.read_bytes()
        m = json.loads(raw)
        if not isinstance(m, dict):
            raise CheckerError("map root is not a JSON object")
        m["_sha256"] = hashlib.sha256(raw).hexdigest()
        ev_paths = [Path(p) if Path(p).is_absolute() else root / p for p in a.events] \
            if a.events is not None else []
        for d in ("comms/outbox", "research_map/events.jsonl"):
            p = root / d
            if p.exists() and p not in ev_paths:
                ev_paths.append(p)
        events, errs = load_events(ev_paths)
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        rep = check_map(m, root, events, now, a.map, checker_errors=errs)
        text = json.dumps(rep, indent=2)
        if a.json_out:
            op = Path(a.json_out)
            if not op.is_absolute():
                op = root / op
            op.parent.mkdir(parents=True, exist_ok=True)
            op.write_text(text + "\n")
            print(f"report -> {op}")
        else:
            print(text)
        print(f"verdict={rep['verdict']} hard={rep['counts']['hard']} "
              f"warn={rep['counts']['warn']} info={rep['counts']['info']} "
              f"map_sha256={m['_sha256'][:16]}...")
        return {"pass": 0, "fail": 1, "error": 2}[rep["verdict"]]
    except CheckerError as exc:
        print(f"checker error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # no traceback leaking as verdict=fail
        print(f"checker error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
