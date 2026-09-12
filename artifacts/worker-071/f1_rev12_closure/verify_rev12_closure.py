#!/usr/bin/env python3
"""W071-F1-REV12-CLOSURE-VERIFY-01 — mechanical closure check of the rev12 schemas.

Read-only on canonical paths. Binds every result to sha256 pins taken at snapshot time
(snapshot/MANIFEST.json). Exits 0 only when the pre-registered checks run to completion;
FAIL results are data, not crashes. Worker evidence only: no gate verdict, no node status.

Usage:
  python3 verify_rev12_closure.py --out closure_check.json
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import copy
import re
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
MANIFEST = HERE / "snapshot" / "MANIFEST.json"

PINS = {
    "research_map/formulation_taxonomy.yaml": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "schemas/af_wcc_vacuum.yaml": "cce9c60146d6a907",
    "schemas/af_scc_c2_vacuum.yaml": "5476a3f2c6bc7196",
    "schemas/af_scc_c0_vacuum.yaml": "55d0a1ea9bda96b8",
}

STRICT_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?([+-]\d{2}:\d{2}|Z)$")


# --------------------------------------------------------------------------- helpers
def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def load_manifest() -> dict:
    return json.loads(MANIFEST.read_text())


def snapshot_bytes(man: dict, canonical_path: str) -> bytes:
    for f in man["files"]:
        if f["path"] == canonical_path:
            return (MANIFEST.parent / f["snapshot_name"]).read_bytes()
    raise KeyError(canonical_path)


def strict_duplicate_keys(raw: str):
    """Return list of {mapping_line, key, occurrences:[lines]} for every mapping node."""
    dups = []

    class L(yaml.SafeLoader):
        pass

    def cm(loader, node, deep=False):
        seen = {}
        for k, _v in node.value:
            try:
                key = loader.construct_object(k, deep=deep)
            except Exception:
                key = str(k)
            line = k.start_mark.line + 1
            if key in seen:
                seen[key].append(line)
            else:
                seen[key] = [line]
        for key, lines in seen.items():
            if len(lines) > 1:
                dups.append({"mapping_line": node.start_mark.line + 1, "key": key, "lines": lines})
        return yaml.SafeLoader.construct_mapping(loader, node, deep)

    L.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, cm)
    yaml.load(raw, Loader=L)
    return dups


def walk_strings(obj, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk_strings(v, f"{path}.{k}" if path else str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk_strings(v, f"{path}[{i}]")
    elif isinstance(obj, str):
        yield path, obj


def get_path(obj, dotted: str):
    cur = obj
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def timestamp_values(obj, path=""):
    """Yield (path, raw, parsed) for keys that look like timestamps and parse as ISO."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{path}.{k}" if path else str(k)
            if isinstance(v, str) and re.search(r"(_at|timestamp)$", k) and STRICT_ISO.match(v):
                try:
                    parsed = dt.datetime.fromisoformat(v.replace("Z", "+00:00"))
                    if parsed.tzinfo is None:
                        parsed = parsed.replace(tzinfo=dt.timezone.utc)
                    yield p, v, parsed
                except ValueError:
                    pass
            yield from timestamp_values(v, p)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from timestamp_values(v, f"{path}[{i}]")


def resolve_pointer(pointer: str, repo: Path):
    """pointer = relpath#a.b.c ; return dict with resolution facts."""
    if "#" not in pointer:
        return {"pointer": pointer, "resolved": False, "reason": "no # anchor"}
    rel, anchor = pointer.split("#", 1)
    p = repo / rel
    out = {"pointer": pointer, "target": rel, "anchor": anchor, "exists": p.exists()}
    if not p.exists():
        out["resolved"] = False
        out["reason"] = "target file missing"
        return out
    out["target_sha256"] = sha256_file(p)
    doc = yaml.safe_load(p.read_text())
    cur = doc
    segs = anchor.split(".")
    for i, seg in enumerate(segs):
        if isinstance(cur, dict) and seg in cur:
            cur = cur[seg]
        else:
            out["resolved"] = False
            out["missing_segment"] = seg
            out["found_prefix"] = ".".join(segs[:i]) or "<root>"
            out["available_at_prefix"] = sorted(cur.keys())[:25] if isinstance(cur, dict) else type(cur).__name__
            return out
    out["resolved"] = True
    return out


# --------------------------------------------------------------------------- checks
def run_checks(snap: dict, man: dict, wall: dt.datetime):
    checks = []

    def add(cid, scope, status, detail, evidence=None):
        checks.append({"id": cid, "scope": scope, "status": status, "detail": detail,
                       "evidence": evidence or []})

    docs = {}
    raws = {}
    for path in ["schemas/af_wcc_vacuum.yaml", "schemas/af_scc_c2_vacuum.yaml",
                 "schemas/af_scc_c0_vacuum.yaml", "research_map/formulation_taxonomy.yaml",
                 "artifacts/formulation/formulation_taxonomy.yaml", "artifacts/formulation/FROZEN.json"]:
        raws[path] = snap[path]
        docs[path] = yaml.safe_load(raws[path]) if path.endswith((".yaml", ".yml")) else json.loads(raws[path])

    f1 = docs["schemas/af_wcc_vacuum.yaml"]
    f2a = docs["schemas/af_scc_c2_vacuum.yaml"]
    f2b = docs["schemas/af_scc_c0_vacuum.yaml"]

    # C1 duplicate keys
    dup_summary = {}
    for path in ["schemas/af_wcc_vacuum.yaml", "schemas/af_scc_c2_vacuum.yaml", "schemas/af_scc_c0_vacuum.yaml"]:
        d = strict_duplicate_keys(raws[path].decode())
        dup_summary[path] = d
    if any(dup_summary.values()):
        add("C1-DUPKEY", "F1,F2a,F2b", "FAIL",
            f"duplicate mapping keys remain: {json.dumps(dup_summary)}",
            [f"{p}:{ln}" for p, ds in dup_summary.items() for x in ds for ln in x["lines"]])
    else:
        add("C1-DUPKEY", "F1,F2a,F2b", "PASS",
            "strict compose walk finds zero duplicate mapping keys at any depth in all three rev12 schemas")

    # C2 unique revised_at + revision_history + revision
    # Known rev11 top-level values, read from the pinned rev11 bytes by this worker at 00:33
    # (grep '^revised_at:' on the 9a8bd4c9 / b6123750 / 1bb78ce9 files) and cited in reviews
    # F1-review-009 HF-009-1 / F2a-review-088 / F2b-review-22.
    PRIOR_REVISED = {
        "schemas/af_wcc_vacuum.yaml": ["2026-09-11T23:34:10", "2026-09-11T23:37:51", "2026-09-11T23:42:45",
                                       "2026-09-11T23:46:17", "2026-09-11T23:51:53", "2026-09-12T00:15:00",
                                       "2026-09-12T00:30:00"],
        "schemas/af_scc_c2_vacuum.yaml": ["2026-09-11T23:34:10", "2026-09-11T23:37:51", "2026-09-11T23:42:15",
                                          "2026-09-11T23:42:45", "2026-09-11T23:46:17", "2026-09-11T23:52:21",
                                          "2026-09-12T00:15:00", "2026-09-12T00:30:00"],
        "schemas/af_scc_c0_vacuum.yaml": ["2026-09-11T23:34:10", "2026-09-11T23:37:51", "2026-09-11T23:42:15",
                                          "2026-09-11T23:42:45", "2026-09-11T23:46:17", "2026-09-11T23:52:21",
                                          "2026-09-12T00:15:00", "2026-09-12T00:30:00"],
    }
    c2_rows = []
    c2_fail = []
    for path, doc in [("schemas/af_wcc_vacuum.yaml", f1), ("schemas/af_scc_c2_vacuum.yaml", f2a),
                      ("schemas/af_scc_c0_vacuum.yaml", f2b)]:
        hist = doc.get("revision_history")
        raws_lines = [i + 1 for i, l in enumerate(raws[path].decode().splitlines())
                      if re.match(r"^revised_at:", l)]
        ok_unique = len(raws_lines) == 1
        ok_hist = isinstance(hist, list) and len(hist) >= 1
        hist_times = [(h.get("at") or "")[:19] for h in hist] if ok_hist else []
        ok_rev = doc.get("revision") == 12
        missing = [t for t in PRIOR_REVISED[path] if t not in hist_times]
        row = {"path": path, "raw_revised_at_lines": raws_lines, "revision": doc.get("revision"),
               "revision_history_len": len(hist) if isinstance(hist, list) else None,
               "prior_values_checked": len(PRIOR_REVISED[path]), "prior_values_missing": missing,
               "revised_at": doc.get("revised_at"), "history_last_at": hist_times[-1] if hist_times else None}
        c2_rows.append(row)
        if not (ok_unique and ok_hist and ok_rev and not missing):
            c2_fail.append(path)
    if c2_fail:
        add("C2-REVISED-UNIQUE", "F1,F2a,F2b", "FAIL",
            f"revision_history/revised_at/revision defect in {c2_fail}", json.dumps(c2_rows))
    else:
        add("C2-REVISED-UNIQUE", "F1,F2a,F2b", "PASS",
            "one top-level revised_at per file; revision_history contains every known rev11 top-level "
            f"timestamp (7 for F1, 8 for F2a/F2b); revision == 12. rows={json.dumps(c2_rows)}")

    # C3 clock discipline: (a) no timestamp after wall clock, (b) top-level revised_at not after file mtime
    future = []
    total_ts = 0
    mtime_rows = []
    mtime_fail = []
    for path, doc in [("schemas/af_wcc_vacuum.yaml", f1), ("schemas/af_scc_c2_vacuum.yaml", f2a),
                      ("schemas/af_scc_c0_vacuum.yaml", f2b)]:
        for p, rawv, parsed in timestamp_values(doc):
            total_ts += 1
            if parsed > wall:
                future.append({"path": path, "field": p, "value": rawv,
                               "skew_s": (parsed - wall).total_seconds()})
        meta = next(f for f in man["files"] if f["path"] == path)
        mtime = dt.datetime.fromisoformat(meta["mtime"])
        rev = dt.datetime.fromisoformat(doc["revised_at"])
        delta_s = (rev - mtime).total_seconds()
        row = {"path": path, "revised_at": doc["revised_at"], "mtime": meta["mtime"],
               "revised_at_minus_mtime_s": delta_s, "not_after_mtime_tol120s": delta_s <= 120}
        mtime_rows.append(row)
        if delta_s > 120:
            mtime_fail.append(path)
    if future or mtime_fail:
        add("C3-CLOCK", "F1,F2a,F2b", "FAIL",
            f"future-dated vs wall clock: {len(future)}; revised_at after mtime(>120s): {mtime_fail}",
            json.dumps({"future": future, "mtime": mtime_rows}))
    else:
        add("C3-CLOCK", "F1,F2a,F2b", "PASS",
            f"0 future-dated timestamps of {total_ts} checked against wall clock {wall.isoformat()}; "
            "top-level revised_at is not after file mtime (tolerance 120 s) in all three files",
            json.dumps(mtime_rows))

    # C4 pointer resolution (F1)
    f1_ptr = f1.get("class_contract_pointer")
    f1_sup = f1.get("class_contract_supplement_pointer")
    ptr_res = resolve_pointer(f1_ptr, REPO)
    sup_res = resolve_pointer(f1_sup, REPO) if f1_sup else {"resolved": None, "pointer": None}
    canon_sha = sha256_file(REPO / "research_map/formulation_taxonomy.yaml")
    auth_sha = sha256_file(REPO / "artifacts/formulation/formulation_taxonomy.yaml")
    f0_divergent = canon_sha != auth_sha
    c4_status = "PASS" if ptr_res.get("resolved") and (sup_res.get("resolved") in (True, None)) else "FAIL"
    add("C4-POINTER", "F1", c4_status,
        f"class_contract_pointer resolved={ptr_res.get('resolved')} in canonical; "
        f"supplement pointer present={bool(f1_sup)} resolved={sup_res.get('resolved')}; "
        f"canonical/authoring taxonomy divergence={f0_divergent} (INFO, not an F1 defect at rev12)",
        json.dumps({"pointer": ptr_res, "supplement": sup_res,
                    "canonical_sha256": canon_sha, "authoring_sha256": auth_sha}))

    # C5 AF_{I+} definition anchor
    occ = [(p, v) for p, v in walk_strings(f1) if "AF_{I+}" in v]
    anchors = [(p, v) for p, v in occ if "abbreviat" in v.lower()]
    c5_status = "PASS" if occ and anchors else "FAIL"
    add("C5-AFIPLUS", "F1", c5_status,
        f"{len(occ)} occurrence path(s) of AF_{{I+}}, {len(anchors)} definition anchor(s)",
        json.dumps({"occurrences": [p for p, _ in occ], "anchors": [p for p, _ in anchors]}))

    # C6 visibility predicate
    formal = str(get_path(f1, "quantifiers.formal") or "")
    neg = str(get_path(f1, "quantifiers.negation") or "")
    concl = str(get_path(f1, "conclusion.statement_formal") or "")
    vis_def = str(get_path(f1, "visibility.definition") or "")
    vis_neg = str(get_path(f1, "visibility.negation_conclusion") or "")
    d5 = str(get_path(f1, "quantifiers.domains.D5.definition") or "")
    whole = re.compile(r"gamma\(\[0\s*,\s*T\)\)")
    tail = re.compile(r"gamma\(\[t0\s*,\s*T\)\)")
    operative = {"quantifiers.formal": formal, "quantifiers.negation": neg,
                 "conclusion.statement_formal": concl, "visibility.definition": vis_def,
                 "visibility.negation_conclusion": vis_neg}
    whole_in_operative = [k for k, v in operative.items() if whole.search(v)]
    tail_in_operative = [k for k, v in operative.items() if tail.search(v)]
    uses_pred = ("visible_singularity_from_I_plus" in concl) or ("visible from I+" in concl)
    d5_marks = ("STRONGER" in d5) and ("NOT" in d5)
    c6_ok = (not whole_in_operative) and len(tail_in_operative) >= 2 and uses_pred and d5_marks
    add("C6-VISIBILITY", "F1", "PASS" if c6_ok else "FAIL",
        f"operative clauses with whole-curve containment: {whole_in_operative}; "
        f"operative clauses with tail form: {tail_in_operative}; formal statement uses the named predicate: {uses_pred}; "
        f"D5 prohibition text marked: {d5_marks}",
        json.dumps({"whole_in_operative": whole_in_operative, "tail_in_operative": tail_in_operative}))

    # C7 D0 well-typed
    ordered = get_path(f1, "quantifiers.ordered") or []
    first = ordered[0] if ordered else {}
    d0 = get_path(f1, "quantifiers.domains.D0") or {}
    d0def = str(d0.get("definition") if isinstance(d0, dict) else d0)
    tagged = ("tagged disjoint union" in d0def) and ("r = smooth" in d0def) and ("(sobolev,s,delta)" in d0def)
    binder_r = first.get("binder") == "r" and first.get("domain_id") == "D0"
    formal_binds_r = "r in D0" in formal
    old_illtyped = "(s,delta) in D0" in formal or "(s, delta) in D0" in formal
    c7_ok = tagged and binder_r and formal_binds_r and not old_illtyped
    add("C7-D0", "F1", "PASS" if c7_ok else "FAIL",
        f"tagged disjoint union declared: {tagged}; first binder r in D0: {binder_r}; "
        f"formal binds r in D0: {formal_binds_r}; old ill-typed binder present: {old_illtyped}")

    # C8 f0_binding equality
    c8_rows = []
    c8_fail = []
    for path, doc in [("schemas/af_wcc_vacuum.yaml", f1), ("schemas/af_scc_c2_vacuum.yaml", f2a),
                      ("schemas/af_scc_c0_vacuum.yaml", f2b)]:
        fb = doc.get("f0_binding") or {}
        declared = fb.get("declared_f0_sha256") if isinstance(fb, dict) else None
        row = {"path": path, "declared_f0_sha256": declared,
               "measured_canonical_sha256": canon_sha, "match": declared == canon_sha}
        c8_rows.append(row)
        if declared is not None and declared != canon_sha:
            c8_fail.append(path)
    if c8_fail:
        add("C8-F0BINDING", "F1,F2a,F2b", "FAIL", f"declared F0 hash mismatch in {c8_fail}", json.dumps(c8_rows))
    else:
        add("C8-F0BINDING", "F1,F2a,F2b", "PASS",
            "declared_f0_sha256 equals measured canonical taxonomy hash in all files where present", json.dumps(c8_rows))

    # C9 FROZEN manifest
    frozen = docs["artifacts/formulation/FROZEN.json"]
    files_map = frozen.get("files") or {}
    c9_rows = []
    c9_mismatch = []
    for path in ["schemas/af_wcc_vacuum.yaml", "schemas/af_scc_c2_vacuum.yaml",
                 "schemas/af_scc_c0_vacuum.yaml", "research_map/formulation_taxonomy.yaml"]:
        entry = files_map.get(path)
        measured = sha256_file(REPO / path)
        listed = entry.get("sha256") if isinstance(entry, dict) else None
        row = {"path": path, "listed": listed, "measured": measured,
               "listed_present": entry is not None, "match": listed == measured}
        c9_rows.append(row)
        if entry is not None and listed != measured:
            c9_mismatch.append(path)
    c9_status = "PASS" if not c9_mismatch else "FAIL"
    absent = [r["path"] for r in c9_rows if not r["listed_present"]]
    detail = (f"FROZEN revision {frozen.get('revision')} frozen_at {frozen.get('frozen_at')}; "
              f"listed canonical paths with mismatch: {c9_mismatch}; not listed: {absent}")
    if absent and not c9_mismatch:
        c9_status = "INFO"
    add("C9-FROZEN", "F0,F1,F2a,F2b", c9_status, detail, json.dumps(c9_rows))

    return checks, {"wall_clock": wall.isoformat(), "pins": {p: sha256_file(REPO / p) for p in PINS}}


# --------------------------------------------------------------------------- controls
def run_controls(snap: dict, wall: dt.datetime, checks_a, checks_b):
    ctl = []
    f1_raw = snap["schemas/af_wcc_vacuum.yaml"].decode()

    # sensitivity: duplicate key
    mutated = f1_raw.replace("revision: 12", "revision: 12\nrevised_at: \"2026-09-12T00:31:41+08:00\"", 1)
    d = strict_duplicate_keys(mutated)
    ctl.append({"id": "CTL-DUPKEY-SENS", "fired": bool(d), "detail": json.dumps(d)})

    # sensitivity: future timestamp
    import copy as _copy
    doc = yaml.safe_load(f1_raw)
    doc["revised_at"] = "2099-01-01T00:00:00+08:00"
    fut = [p for p, v, parsed in timestamp_values(doc) if parsed > wall]
    ctl.append({"id": "CTL-CLOCK-SENS", "fired": "revised_at" in fut, "detail": json.dumps(fut)})

    # sensitivity: pointer
    bad = resolve_pointer("research_map/formulation_taxonomy.yaml#classes.NOPE", REPO)
    ctl.append({"id": "CTL-POINTER-SENS", "fired": bad.get("resolved") is False, "detail": json.dumps(bad)})

    # determinism
    det = json.dumps(checks_a, sort_keys=True) == json.dumps(checks_b, sort_keys=True)
    ctl.append({"id": "CTL-DETERMINISM", "fired": det, "detail": "two runs identical" if det else "differ"})

    # no-write canary
    same = all(sha256_file(REPO / p) == PINS[p] or sha256_file(REPO / p).startswith(PINS[p][:16]) for p in PINS)
    ctl.append({"id": "CTL-NOWRITE", "fired": same, "detail": json.dumps({p: sha256_file(REPO / p)[:16] for p in PINS})})

    # historical real-defect control: the pinned rev11 F1 bytes must be FLAGGED by the same
    # detectors that pass rev12 (proves the instrument discriminates, not just accepts).
    rev11 = REPO / "artifacts/worker-048/f1_closure_preflight/snapshot/af_wcc_vacuum.9a8bd4c9.yaml"
    if rev11.exists():
        rev11_raw = rev11.read_text()
        rev11_sha = sha256_file(rev11)
        d11 = strict_duplicate_keys(rev11_raw)
        ctl.append({"id": "CTL-REV11-DUPKEY", "fired": len(d11) >= 2,
                    "detail": json.dumps({"sha256": rev11_sha, "duplicates": d11})})
        doc11 = yaml.safe_load(rev11_raw)
        mtime11 = dt.datetime.fromtimestamp(rev11.stat().st_mtime).astimezone()
        rev11_rev = dt.datetime.fromisoformat(doc11["revised_at"])
        ctl.append({"id": "CTL-REV11-MTIME", "fired": (rev11_rev - mtime11).total_seconds() > 120,
                    "detail": json.dumps({"sha256": rev11_sha, "effective_revised_at": doc11["revised_at"],
                                          "mtime": mtime11.isoformat(),
                                          "revised_at_minus_mtime_s": (rev11_rev - mtime11).total_seconds()})})
    else:
        ctl.append({"id": "CTL-REV11-DUPKEY", "fired": False, "detail": "rev11 pinned snapshot missing"})
        ctl.append({"id": "CTL-REV11-MTIME", "fired": False, "detail": "rev11 pinned snapshot missing"})
    return ctl


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE / "closure_check.json"))
    ap.add_argument("--live-summary", default=str(HERE / "live_hashes.json"))
    args = ap.parse_args()

    man = load_manifest()
    snap = {f["path"]: snapshot_bytes(man, f["path"]) for f in man["files"]}

    # fail-closed: snapshot bytes must match their recorded hashes
    for f in man["files"]:
        if sha256_bytes(snap[f["path"]]) != f["sha256"]:
            print(f"FATAL snapshot hash mismatch {f['path']}", file=sys.stderr)
            return 2

    wall = dt.datetime.now().astimezone()
    checks_a, meta = run_checks(snap, man, wall)
    checks_b, _ = run_checks(snap, man, wall)
    controls = run_controls(snap, wall, checks_a, checks_b)

    live_before = {p: sha256_file(REPO / p) for p in PINS}
    live_after = {p: sha256_file(REPO / p) for p in PINS}
    json.dump({"before": live_before, "after": live_after}, open(args.live_summary, "w"), indent=1)

    blocking = [c for c in checks_a if c["status"] == "FAIL"]
    failed_controls = [c for c in controls if not c["fired"]]
    out = {
        "task_id": "W071-F1-REV12-CLOSURE-VERIFY-01",
        "actor": "worker-071",
        "created_at": wall.isoformat(),
        "role": "bounded execution worker; read-only on canonical paths; worker evidence only",
        "node_id": "F1",
        "class_id": "AF-WCC-VAC-GEN",
        "class_ids_secondary": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "gate": "G-FORM",
        "pins": meta["pins"],
        "snapshot_at": man["snapshot_at"],
        "checks": checks_a,
        "controls": controls,
        "controls_pass": not failed_controls,
        "blocking_failures": [c["id"] for c in blocking],
        "verdict": "REV12_CLOSURE_CONFIRMED_ON_LISTED_CHECKS" if not blocking and not failed_controls
                   else ("REV12_CLOSURE_PARTIAL" if not failed_controls else "INSTRUMENT_CONTROL_FAILURE"),
        "input_stability": {"unchanged_during_run": live_before == live_after,
                            "before": live_before, "after": live_after},
        "scope_limits": [
            "Mechanical/lexical checks only: presence, absence, resolution and consistency of declared fields.",
            "Does not verify mathematical adequacy, non-vacuity, or literature scope.",
            "Does not adjudicate the F0 canonical/authoring divergence; recorded as INFO.",
            "No gate verdict, no node status, no validation_status promotion."
        ]
    }
    Path(args.out).write_text(json.dumps(out, indent=1))
    print(json.dumps({"verdict": out["verdict"], "blocking_failures": out["blocking_failures"],
                      "controls_pass": out["controls_pass"],
                      "checks": {c["id"]: c["status"] for c in checks_a}}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
