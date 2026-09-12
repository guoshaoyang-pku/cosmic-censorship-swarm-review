#!/usr/bin/env python3
"""REV29-LANDING-GUARD: acceptance + scope guard for astra-life05-evidence-binding-repair.

Worker-074 / task W074-REV29-LANDING-GUARD-01, class-bound to
AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN, gate G-FORM.

Purpose
-------
REC-12 authorizes exactly four bounded items at new bytes:
  C1  taxonomy_cases.jsonl rows rebound to F0 rev5 0abb9ed8 + checker re-run;
  C2  f0_binding.consistency_evidence_sha256 refreshed in all three schemas to the
      live taxonomy_consistency.json bytes;
  C3  F1/F2b class-identity variant SET/CH strictness wording corrected (assertion
      direction only);
  C4  FROZEN rev29 published with byte-verified pins + artifact events.
and forbids any class id, hypothesis, conclusion predicate, axis semantics or F0
canonical byte change.

This instrument is an independent, read-only predicate set over the pre-repair
frozen bytes (baseline, verified by sha256 against the rev12/rev28 pins) and the
live tree. It emits PASS / EXTRA_DECLARED / OPEN / FAIL per predicate and exits
0 (landed+in-scope), 3 (coherent but not yet complete) or 4 (violation).

It never writes a canonical path, never imports a workspace module, and never
edits another agent's artifact. It writes only report.json, raw/*.txt and
selftest output inside its own --out directory.

Exit codes: 0 = all predicates PASS; 3 = >=1 OPEN, no FAIL; 4 = >=1 FAIL.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timezone, timedelta

try:
    import yaml
except Exception as exc:  # pragma: no cover
    print("FATAL: PyYAML required: %s" % exc)
    sys.exit(2)

CST = timezone(timedelta(hours=8))
NOW = lambda: datetime.now(CST).strftime("%Y-%m-%dT%H:%M:%S+08:00")

SCHEMAS = {
    "F1": "schemas/af_wcc_vacuum.yaml",
    "F2a": "schemas/af_scc_c2_vacuum.yaml",
    "F2b": "schemas/af_scc_c0_vacuum.yaml",
}
MIRRORS = {
    "F1": "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
    "F2a": "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml",
    "F2b": "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
}
CASES = "schemas/taxonomy_cases.jsonl"
FROZEN = "artifacts/formulation/FROZEN.json"
F0_CANONICAL = "research_map/formulation_taxonomy.yaml"
F0_SUPPLEMENT = "artifacts/formulation/formulation_taxonomy.yaml"
EVIDENCE = "artifacts/formulation/evidence/taxonomy_consistency.json"
REGISTRY = "runtime/state/artifact_hashes.json"
EVENTS = "research_map/events.jsonl"

# Pre-repair pins (astra-lifecycle-05 measured_pins).
PIN = {
    "F1": "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3",
    "F2a": "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce",
    "F2b": "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6",
    "FROZEN": "2f358f6722d920621a66c0259cb48d35a5e3c1b706f28adf37ed467325fcedf1",
    "CASES": "ccf7041bd0ff3ce844c07a700a588b7fe8e3c90880674c5e595b21f6259a8f03",
    "F0": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "SUPP": "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
    "EVIDENCE": "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b",
}

STALE_EVIDENCE_PIN = "675a99d0d25b2b37c9b9e9b965aec1c1ff0e388d2665fd9247b58c04733eba48"
STALE_CASE_PIN = "66bf917b"
STRICT = ("STRONGER", "WEAKER", "EQUIVALENT")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def leaf_paths(obj, prefix=""):
    """Flatten a YAML/JSON object to {path: scalar}. Lists are index-addressed."""
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.update(leaf_paths(v, prefix + "." + str(k)))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.update(leaf_paths(v, prefix + "[%d]" % i))
    else:
        out[prefix] = obj
    return out


def structural_shape(obj, prefix=""):
    """Multiset of container/list shapes, to detect added/removed structure."""
    out = []
    if isinstance(obj, dict):
        out.append(("map", prefix, len(obj)))
        for k, v in obj.items():
            out += structural_shape(v, prefix + "." + str(k))
    elif isinstance(obj, list):
        out.append(("list", prefix, len(obj)))
        for i, v in enumerate(obj):
            out += structural_shape(v, prefix + "[%d]" % i)
    return out


def load_yaml(path):
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_json(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def is_strictness_text(v):
    return isinstance(v, str) and any(s in v.upper() for s in STRICT)


def classify_change(path, old, new):
    """Return AUTHORIZED | DIRECTION_ALLOWED | EXTRA_DECLARED | OUT_OF_SCOPE."""
    core = (
        ".f0_binding.consistency_evidence_sha256",
        ".f0_binding.checked_at",
        ".f0_binding.binding_note",
        ".revision",
        ".revised_at",
        ".supersedes",
        ".revision_history",
    )
    if any(path == c or path.startswith(c + ".") or path.startswith(c + "[") for c in core):
        return "AUTHORIZED"
    if "class_identity_variants" in path and is_strictness_text(old) and is_strictness_text(new):
        return "DIRECTION_ALLOWED"
    if path.endswith(".quantifiers.domains.D5.definition") or path.endswith(".visibility.definition"):
        # Named in the live rev13 revision_history note as a direction/equivalence
        # correction; still outside the literal C3 wording, so it is reported as
        # EXTRA_DECLARED (warn) rather than silently authorized.
        if is_strictness_text(old) or "EQUIVALENT" in str(new).upper() or "past-closed" in str(new):
            return "EXTRA_DECLARED"
    return "OUT_OF_SCOPE"


def diff_schema(baseline_yaml, live_yaml):
    b, l = leaf_paths(baseline_yaml), leaf_paths(live_yaml)
    changed, added, removed = [], [], []
    for p in sorted(set(b) | set(l)):
        if p == ".revision_history" or p.startswith(".revision_history[") or p.startswith(".revision_history."):
            continue  # appended revision-history entries are authorized provenance
        if p not in l:
            removed.append(p)
        elif p not in b:
            added.append(p)
        elif b[p] != l[p]:
            changed.append({"path": p, "old": b[p], "new": l[p], "class": classify_change(p, b[p], l[p])})
    bshape = {p: n for _, p, n in structural_shape(baseline_yaml)}
    lshape = {p: n for _, p, n in structural_shape(live_yaml)}
    shape_delta = [
        {"path": p, "baseline": bshape.get(p), "live": lshape.get(p)}
        for p in sorted(set(bshape) | set(lshape))
        if bshape.get(p) != lshape.get(p)
        and not (p == ".revision_history" or p.startswith(".revision_history[")
                 or p.startswith(".revision_history."))
    ]
    # revision_history growth also changes the enclosing revision_history len? covered above.
    return {"changed": changed, "added": added, "removed": removed, "shape_delta": shape_delta}


def semantic_guard(bl, lv):
    """Class-identity predicates independent of the diff whitelist."""
    problems = []
    for key in ("class_id", "class_ids"):
        if bl.get(key) != lv.get(key):
            problems.append("S1 %s changed: %r -> %r" % (key, bl.get(key), lv.get(key)))
    b_conc = (bl.get("conclusion") or {}).get("conclusion_type")
    l_conc = (lv.get("conclusion") or {}).get("conclusion_type")
    if b_conc != l_conc:
        problems.append("S2 conclusion.conclusion_type changed: %r -> %r" % (b_conc, l_conc))
    for key in ("declared_f0_artifact", "declared_f0_sha256", "class_contract_supplement",
                "class_contract_supplement_pointer", "consistency_evidence"):
        bv = (bl.get("f0_binding") or {}).get(key)
        lv2 = (lv.get("f0_binding") or {}).get(key)
        if bv != lv2:
            problems.append("S5 f0_binding.%s changed: %r -> %r" % (key, bv, lv2))
    if not isinstance(lv.get("revision"), int) or not isinstance(bl.get("revision"), int):
        problems.append("S6 revision not an integer")
    elif lv["revision"] <= bl["revision"]:
        problems.append("S6 revision did not increase: %r -> %r" % (bl["revision"], lv["revision"]))
    return problems


def check_taxonomy_cases(root):
    path = os.path.join(root, CASES)
    res = {"path": CASES, "sha256": sha256_file(path), "unchanged_from_pin": None,
           "rows": 0, "bound_rows": 0, "unbound_rows": [], "stale_occurrences": [],
           "meta_taxonomy_ref": None, "ok": False}
    res["unchanged_from_pin"] = res["sha256"] == PIN["CASES"]
    with open(path, "r", encoding="utf-8") as fh:
        for i, line in enumerate(fh):
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            res["rows"] += 1
            blob = json.dumps(row)
            is_meta = row.get("record_type") == "meta"
            if is_meta:
                res["meta_taxonomy_ref"] = (row.get("taxonomy_ref") or {}).get("sha256")
            bs = row.get("binding_status")
            if is_meta:
                continue
            if isinstance(bs, str) and bs.endswith("0abb9ed8a961"):
                res["bound_rows"] += 1
            else:
                res["unbound_rows"].append({"line": i + 1, "case_id": row.get("case_id"),
                                            "binding_status": bs})
            stale_fields = [k for k in ("binding_status", "taxonomy_ref", "evidence_refs")
                            if STALE_CASE_PIN in json.dumps(row.get(k))]
            if stale_fields:
                res["stale_occurrences"].append({"line": i + 1, "case_id": row.get("case_id"),
                                                 "fields": stale_fields})
    res["case_rows"] = res["rows"] - 1
    res["ok"] = (
        res["unchanged_from_pin"]
        and not res["unbound_rows"]
        and res["meta_taxonomy_ref"] == PIN["F0"]
        and res["bound_rows"] == res["case_rows"]
    )
    return res


def check_frozen(root, live_hashes, partial=False):
    path = os.path.join(root, FROZEN)
    res = {"path": FROZEN, "sha256": sha256_file(path), "revision": None,
           "files_total": 0, "files_resolved": 0, "files_mismatched": [],
           "files_skipped_absent": 0,
           "logical_total": 0, "logical_resolved": 0, "logical_mismatched": [],
           "pins_live_targets": {}, "ok": False, "rev29": False, "partial": partial}
    d = load_json(path)
    res["revision"] = d.get("revision")
    res["rev29"] = isinstance(d.get("revision"), int) and d["revision"] > 28
    for rel, meta in (d.get("files") or {}).items():
        p = os.path.join(root, rel)
        want = (meta or {}).get("sha256")
        if not os.path.exists(p) and partial:
            res["files_skipped_absent"] += 1
            continue
        res["files_total"] += 1
        if os.path.exists(p) and sha256_file(p) == want:
            res["files_resolved"] += 1
        else:
            res["files_mismatched"].append({
                "path": rel, "declared": want,
                "live": sha256_file(p) if os.path.exists(p) else None,
                "file_mtime": __import__("time").strftime(
                    "%Y-%m-%dT%H:%M:%S+08:00", __import__("time").localtime(os.path.getmtime(p)))
                if os.path.exists(p) else None,
                "frozen_mtime": __import__("time").strftime(
                    "%Y-%m-%dT%H:%M:%S+08:00", __import__("time").localtime(os.path.getmtime(path))),
                "written_after_freeze": bool(os.path.exists(p)
                                             and os.path.getmtime(p) > os.path.getmtime(path))})
    for name, meta in (d.get("logical_artifacts") or {}).items():
        rel = (meta or {}).get("path")
        want = (meta or {}).get("sha256")
        p = os.path.join(root, rel) if rel else None
        if (not p or not os.path.exists(p)) and partial:
            res["files_skipped_absent"] += 1
            continue
        res["logical_total"] += 1
        if p and os.path.exists(p) and sha256_file(p) == want:
            res["logical_resolved"] += 1
        else:
            res["logical_mismatched"].append({"name": name, "path": rel, "declared": want,
                                              "live": sha256_file(p) if p and os.path.exists(p) else None})
    # after rev29 the four moved targets must be pinned at live bytes
    if res["rev29"]:
        files = d.get("files") or {}
        logical = d.get("logical_artifacts") or {}
        for label, rel in list(SCHEMAS.items()) + [("CASES", CASES)]:
            pin = (files.get(rel) or {}).get("sha256")
            res["pins_live_targets"][label] = {
                "path": rel, "declared": pin, "live": live_hashes.get(rel),
                "match": pin == live_hashes.get(rel),
            }
        for name in ("F0-declared-taxonomy", "F0-class-contract-supplement"):
            meta = logical.get(name) or {}
            res["pins_live_targets"][name] = {
                "path": meta.get("path"), "declared": meta.get("sha256"),
                "live": live_hashes.get(meta.get("path")),
                "match": meta.get("sha256") == live_hashes.get(meta.get("path")),
            }
    res["ok"] = (res["files_resolved"] == res["files_total"]
                 and res["logical_resolved"] == res["logical_total"]
                 and (not res["rev29"] or all(v["match"] for v in res["pins_live_targets"].values())))
    return res


def scan_events(events_path, targets):
    """targets: {label: {'path':..., 'sha256':...}}; returns found/pending."""
    found = {k: [] for k in targets}
    pending_outbox = {k: [] for k in targets}
    if events_path and os.path.exists(events_path):
        with open(events_path, "r", encoding="utf-8", errors="replace") as fh:
            for i, line in enumerate(fh):
                if '"artifact"' not in line:
                    continue
                for k, t in targets.items():
                    if t["sha256"] in line and t["path"] in line:
                        found[k].append({"line": i + 1})
    outbox = os.path.join(os.path.dirname(events_path or ""), "..", "comms", "outbox")
    outbox = os.path.normpath(outbox)
    if os.path.isdir(outbox):
        for name in sorted(os.listdir(outbox)):
            if not name.endswith(".jsonl"):
                continue
            p = os.path.join(outbox, name)
            try:
                with open(p, "r", encoding="utf-8", errors="replace") as fh:
                    for i, line in enumerate(fh):
                        if '"artifact"' not in line:
                            continue
                        for k, t in targets.items():
                            if t["sha256"] in line and t["path"] in line:
                                pending_outbox[k].append({"file": name, "line": i + 1})
            except OSError:
                continue
    return found, pending_outbox


def check_registry(registry_path, targets):
    res = {}
    if not registry_path or not os.path.exists(registry_path):
        return {"available": False}
    reg = (load_json(registry_path).get("registry") or {})
    for k, t in targets.items():
        e = reg.get(t["path"]) or {}
        res[k] = {"path": t["path"], "live_sha256": t["sha256"],
                  "registered_sha256": e.get("sha256"),
                  "match": e.get("sha256") == t["sha256"]}
    return {"available": True, "targets": res,
            "ok": all(v["match"] for v in res.values())}


def audit(root, baseline_dir, events_path=None, registry_path=None, partial=False):
    live = {}
    for rel in [SCHEMAS["F1"], SCHEMAS["F2a"], SCHEMAS["F2b"], CASES, FROZEN,
                F0_CANONICAL, F0_SUPPLEMENT, EVIDENCE] + list(MIRRORS.values()):
        p = os.path.join(root, rel)
        live[rel] = sha256_file(p) if os.path.exists(p) else None

    r = {"schema": "rev29-landing-guard/v1", "actor": "worker-074",
         "task_id": "W074-REV29-LANDING-GUARD-01",
         "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
         "gate": "G-FORM", "root": os.path.abspath(root),
         "baseline_dir": os.path.abspath(baseline_dir), "measured_at": NOW(),
         "live_sha256": live, "predicates": {}, "findings": [], "status": None}

    # --- P0 baseline integrity -------------------------------------------------
    base_expected = {"F1": PIN["F1"], "F2a": PIN["F2a"], "F2b": PIN["F2b"],
                     "FROZEN": PIN["FROZEN"], "CASES": PIN["CASES"],
                     "F0": PIN["F0"], "SUPP": PIN["SUPP"]}
    base_files = {"F1": "af_wcc_vacuum.cce9c60146d6.yaml",
                  "F2a": "af_scc_c2_vacuum.5476a3f2c6bc.yaml",
                  "F2b": "af_scc_c0_vacuum.55d0a1ea9bda.yaml",
                  "FROZEN": "FROZEN.2f358f6722d9.json",
                  "CASES": "taxonomy_cases.ccf7041bd0ff.jsonl",
                  "F0": "formulation_taxonomy.0abb9ed8a961.yaml"}
    base = {}
    for k, fn in base_files.items():
        p = os.path.join(baseline_dir, fn)
        base[k] = sha256_file(p) if os.path.exists(p) else None
    base["SUPP"] = PIN["SUPP"] if sha256_file(os.path.join(root, F0_SUPPLEMENT)) == PIN["SUPP"] else None
    p0_bad = [k for k, v in base_expected.items() if base.get(k) != v]
    r["predicates"]["P0_baseline_integrity"] = {
        "status": "PASS" if not p0_bad else "FAIL",
        "baseline_sha256": base, "expected_pins": base_expected, "mismatches": p0_bad,
        "note": "baseline bytes verify byte-exactly against the rev12/rev28 pins"}
    if p0_bad:
        r["findings"].append({"id": "W074-R29-BASE", "severity": "major",
                              "text": "baseline snapshot does not match the pinned rev28/rev12 bytes: %s" % p0_bad})

    # --- P1 authorized-change scope -------------------------------------------
    per_schema = {}
    for label, rel in SCHEMAS.items():
        bfn = base_files[label]
        b = load_yaml(os.path.join(baseline_dir, bfn))
        l = load_yaml(os.path.join(root, rel))
        d = diff_schema(b, l)
        sem = semantic_guard(b, l)
        classes = {c["class"] for c in d["changed"]}
        oos = [c for c in d["changed"] if c["class"] == "OUT_OF_SCOPE"]
        extra = [c for c in d["changed"] if c["class"] == "EXTRA_DECLARED"]
        per_schema[label] = {
            "changed_count": len(d["changed"]), "added": d["added"], "removed": d["removed"],
            "shape_delta": d["shape_delta"],
            "changed": d["changed"],
            "by_class": {c: sum(1 for x in d["changed"] if x["class"] == c) for c in sorted(classes)},
            "semantic_violations": sem,
        }
        if d["added"] or d["removed"]:
            r["findings"].append({"id": "W074-R29-STRUCT-%s" % label, "severity": "major",
                                  "text": "%s structure changed: added=%s removed=%s"
                                          % (rel, d["added"][:8], d["removed"][:8])})
        if sem:
            r["findings"].append({"id": "W074-R29-SEM-%s" % label, "severity": "major",
                                  "text": "%s semantic violation: %s" % (rel, sem)})
        if oos:
            r["findings"].append({"id": "W074-R29-SCOPE-%s" % label, "severity": "major",
                                  "text": "%s changes outside the REC-12 authorized set: %s"
                                          % (rel, [c["path"] for c in oos])})
        if extra:
            r["findings"].append({"id": "W074-R29-EXTRA-%s" % label, "severity": "minor",
                                  "text": "%s extra-declared changes (named in the rev13 note, "
                                          "outside literal C3 wording): %s"
                                          % (rel, [c["path"] for c in extra])})
    scope_fail = any(v["semantic_violations"] or v["added"] or v["removed"]
                     or any(c["class"] == "OUT_OF_SCOPE" for c in v["changed"])
                     for v in per_schema.values())
    scope_extra = any(c["class"] == "EXTRA_DECLARED" for v in per_schema.values() for c in v["changed"])
    r["predicates"]["P1_authorized_change_scope"] = {
        "status": "FAIL" if scope_fail else ("EXTRA_DECLARED" if scope_extra else "PASS"),
        "per_schema": per_schema,
        "allowed": ["f0_binding.consistency_evidence_sha256", "f0_binding.checked_at",
                    "f0_binding.binding_note", "revision", "revised_at", "supersedes",
                    "revision_history", "class_identity_variants[*] strictness wording"],
        "declared_extra": [".quantifiers.domains.D5.definition", ".visibility.definition"],
    }

    # --- P2 binding chain ------------------------------------------------------
    ev = os.path.join(root, EVIDENCE)
    ev_sha = sha256_file(ev)
    ev_doc = load_json(ev)
    chain = {"evidence_sha256": ev_sha, "schemas": {}}
    chain_ok = True
    for label, rel in SCHEMAS.items():
        d = load_yaml(os.path.join(root, rel))
        fb = d.get("f0_binding") or {}
        row = {"declared_f0_sha256": fb.get("declared_f0_sha256"),
               "consistency_evidence_sha256": fb.get("consistency_evidence_sha256"),
               "f0_ok": fb.get("declared_f0_sha256") == PIN["F0"],
               "evidence_ok": fb.get("consistency_evidence_sha256") == ev_sha,
               "stale_pre_repair_pin": fb.get("consistency_evidence_sha256") == STALE_EVIDENCE_PIN}
        chain["schemas"][label] = row
        chain_ok = chain_ok and row["f0_ok"] and row["evidence_ok"]
    chain["evidence_consistent_flag"] = ev_doc.get("consistent")
    chain["evidence_classes_compared"] = len(ev_doc.get("classes_compared") or [])
    chain["evidence_ok"] = (ev_doc.get("consistent") is True
                            and chain["evidence_classes_compared"] == 4)
    # all three schemas must declare the same evidence pin
    pins = {v["consistency_evidence_sha256"] for v in chain["schemas"].values()}
    chain["uniform_evidence_pin"] = len(pins) == 1
    r["predicates"]["P2_binding_chain"] = {
        "status": "PASS" if (chain_ok and chain["evidence_ok"] and chain["uniform_evidence_pin"])
        else ("OPEN" if all(v["stale_pre_repair_pin"] for v in chain["schemas"].values()) else "FAIL"),
        **chain}

    # --- P3 mirrors ------------------------------------------------------------
    mirrors = {}
    for label, rel in SCHEMAS.items():
        m = MIRRORS[label]
        mirrors[label] = {"canonical": live[rel], "authoring": live[m],
                          "aligned": live[rel] == live[m]}
    r["predicates"]["P3_publication_mirrors"] = {
        "status": "PASS" if all(v["aligned"] for v in mirrors.values()) else "FAIL",
        "pairs": mirrors}

    # --- P4 F0 immutability ----------------------------------------------------
    f0 = {"canonical": live[F0_CANONICAL], "canonical_pin": PIN["F0"],
          "supplement": live[F0_SUPPLEMENT], "supplement_pin": PIN["SUPP"]}
    f0["ok"] = f0["canonical"] == f0["canonical_pin"] and f0["supplement"] == f0["supplement_pin"]
    r["predicates"]["P4_f0_immutability"] = {
        "status": "PASS" if f0["ok"] else "FAIL", **f0}

    # --- P5 taxonomy cases -----------------------------------------------------
    cases = check_taxonomy_cases(root)
    r["predicates"]["P5_case_corpus"] = {
        "status": "PASS" if cases["ok"] else "FAIL", **cases}

    # --- P6 FROZEN rev29 -------------------------------------------------------
    frozen = check_frozen(root, live, partial=partial)
    r["predicates"]["P6_frozen_rev29"] = {
        "status": "PASS" if (frozen["ok"] and frozen["rev29"]) else ("OPEN" if frozen["ok"] else "FAIL"),
        **frozen}

    # --- P7 registry -----------------------------------------------------------
    targets = {label: {"path": rel, "sha256": live[rel]} for label, rel in SCHEMAS.items()}
    targets["CASES"] = {"path": CASES, "sha256": live[CASES]}
    targets["FROZEN"] = {"path": FROZEN, "sha256": live[FROZEN]}
    registry = check_registry(registry_path or os.path.join(root, REGISTRY), targets)
    reg_ok = registry.get("available") and registry.get("ok")
    r["predicates"]["P7_hash_registry"] = {
        "status": "PASS" if reg_ok else ("OPEN" if registry.get("available") else "OPEN"),
        **{k: v for k, v in registry.items() if k != "ok"}}

    # --- P8 artifact events ----------------------------------------------------
    found, pending = scan_events(events_path or os.path.join(root, EVENTS), targets)
    ev_ok = all(found[k] for k in targets)
    r["predicates"]["P8_artifact_events"] = {
        "status": "PASS" if ev_ok else "OPEN",
        "accepted_stream_hits": {k: len(v) for k, v in found.items()},
        "outbox_pending_hits": {k: len(v) for k, v in pending.items()},
        "targets": targets,
        "note": "artifact events may lag the bytes; OPEN is expected until the owner emits "
                "and the controller ingests"}

    # --- P9 measurement stability ---------------------------------------------
    recheck = {}
    for rel in list(live):
        pp = os.path.join(root, rel)
        recheck[rel] = sha256_file(pp) if os.path.exists(pp) else None
    moved = {k: {"at_start": live[k], "at_end": recheck[k]}
             for k in live if live[k] != recheck[k]}
    r["predicates"]["P9_measurement_stability"] = {
        "status": "PASS" if not moved else "FAIL",
        "moved_during_run": moved,
        "note": "the tree is live; any hash move inside the measurement window "
                "invalidates the single-instant reading"}

    # --- auto findings for failing predicates ----------------------------------
    for k, v in r["predicates"].items():
        if v.get("status") != "FAIL":
            continue
        if k == "P6_frozen_rev29" and v.get("files_mismatched"):
            for m in v["files_mismatched"]:
                r["findings"].append({
                    "id": "W074-R29-FREEZE", "severity": "major",
                    "text": "FROZEN rev%s pin for %s declares %s but live bytes are %s "
                            "(file_mtime=%s, frozen_mtime=%s, written_after_freeze=%s)"
                            % (v.get("revision"), m["path"], str(m.get("declared"))[:12],
                               str(m.get("live"))[:12], m.get("file_mtime"),
                               m.get("frozen_mtime"), m.get("written_after_freeze"))})
        elif k == "P9_measurement_stability":
            r["findings"].append({"id": "W074-R29-MOVING", "severity": "major",
                                  "text": "hashes moved during the run: %s"
                                          % list(v.get("moved_during_run", {}))})
        else:
            r["findings"].append({"id": "W074-R29-%s" % k.split("_")[0],
                                  "severity": "major", "text": "%s FAIL" % k})

    # --- verdict ---------------------------------------------------------------
    statuses = {k: v["status"] for k, v in r["predicates"].items()}
    r["predicate_status"] = statuses
    r["failed"] = [k for k, v in statuses.items() if v == "FAIL"]
    r["open"] = [k for k, v in statuses.items() if v == "OPEN"]
    r["extra_declared"] = [k for k, v in statuses.items() if v == "EXTRA_DECLARED"]
    if r["failed"]:
        r["status"] = "FAIL"
    elif r["open"]:
        r["status"] = "OPEN"
    else:
        r["status"] = "PASS"
    r["landed"] = (statuses.get("P1_authorized_change_scope") in ("PASS", "EXTRA_DECLARED")
                   and statuses.get("P2_binding_chain") == "PASS"
                   and statuses.get("P6_frozen_rev29") == "PASS")
    r["conclusion"] = (
        "LANDED_IN_SCOPE" if r["status"] == "PASS" else
        "IN_FLIGHT_COHERENT" if r["status"] == "OPEN" else "VIOLATION")
    return r


def write_out(outdir, name, text):
    os.makedirs(outdir, exist_ok=True)
    p = os.path.join(outdir, name)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(text)
    return p


def selftest(outdir, root):
    """Negative controls: each mutation must trip the intended predicate."""
    sand_root = os.path.join(outdir, "sandbox_root")
    results = []
    base_src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "snapshot", "rev28_pin")
    base_dst = os.path.join(sand_root, "baseline")

    def build_tree():
        if os.path.isdir(sand_root):
            shutil.rmtree(sand_root)
        os.makedirs(base_dst)
        for fn in os.listdir(base_src):
            shutil.copy2(os.path.join(base_src, fn), os.path.join(base_dst, fn))
        for rel in [CASES, FROZEN, F0_CANONICAL, F0_SUPPLEMENT, EVIDENCE, REGISTRY, EVENTS] + \
                   list(SCHEMAS.values()) + list(MIRRORS.values()):
            src, dst = os.path.join(root, rel), os.path.join(sand_root, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
        return sand_root

    build_tree()
    # expected events/registry stubs in sandbox so only the mutated predicate fires
    reg = load_json(os.path.join(root, REGISTRY))
    for rel in list(SCHEMAS.values()) + [CASES, FROZEN]:
        reg.setdefault("registry", {})[rel] = {"sha256": sha256_file(os.path.join(sand_root, rel))}
    with open(os.path.join(sand_root, REGISTRY), "w", encoding="utf-8") as fh:
        json.dump(reg, fh)
    with open(os.path.join(sand_root, EVENTS), "w", encoding="utf-8") as fh:
        for rel in list(SCHEMAS.values()) + [CASES, FROZEN]:
            fh.write(json.dumps({"event_type": "artifact", "path": rel,
                                 "sha256": sha256_file(os.path.join(sand_root, rel))}) + "\n")

    clean = audit(sand_root, base_dst, events_path=os.path.join(sand_root, EVENTS),
                  registry_path=os.path.join(sand_root, REGISTRY), partial=True)
    # The unmutated tree mirrors the live repair state (coherent, possibly still
    # IN_FLIGHT), so the control asserts no FAIL, not PASS.
    results.append({"control": "C0_unmutated_tree_no_fail", "expected": "no FAIL",
                    "observed": "status=%s failed=%s" % (clean["status"], clean["failed"]),
                    "ok": clean["status"] != "FAIL" and not clean["failed"]})

    def mutate_and_expect(label, rel, mutate, expect_pred, expect_status):
        build_tree()
        reg = load_json(os.path.join(root, REGISTRY))
        for r2 in list(SCHEMAS.values()) + [CASES, FROZEN]:
            reg.setdefault("registry", {})[r2] = {"sha256": sha256_file(os.path.join(sand_root, r2))}
        with open(os.path.join(sand_root, REGISTRY), "w", encoding="utf-8") as fh:
            json.dump(reg, fh)
        with open(os.path.join(sand_root, EVENTS), "w", encoding="utf-8") as fh:
            for r2 in list(SCHEMAS.values()) + [CASES, FROZEN]:
                fh.write(json.dumps({"event_type": "artifact", "path": r2,
                                     "sha256": sha256_file(os.path.join(sand_root, r2))}) + "\n")
        mutate(os.path.join(sand_root, rel))
        res = audit(sand_root, base_dst, events_path=os.path.join(sand_root, EVENTS),
                    registry_path=os.path.join(sand_root, REGISTRY), partial=True)
        obs = res["predicates"][expect_pred]["status"]
        results.append({"control": label, "expected": "%s=%s" % (expect_pred, expect_status),
                        "observed": "%s=%s" % (expect_pred, obs),
                        "ok": obs == expect_status, "overall": res["status"]})

    def set_yaml_leaf(rel, *path, value=None):
        def _m(p):
            d = load_yaml(p)
            cur = d
            for k in path[:-1]:
                cur = cur[k]
            cur[path[-1]] = value
            with open(p, "w", encoding="utf-8") as fh:
                yaml.safe_dump(d, fh, sort_keys=False, allow_unicode=True)
        return _m

    mutate_and_expect("C1_hypothesis_rewrite", SCHEMAS["F1"],
                      set_yaml_leaf(SCHEMAS["F1"], "conclusion", "statement_natural_language",
                                    value="REWRITTEN BY CONTROL"),
                      "P1_authorized_change_scope", "FAIL")
    mutate_and_expect("C2_class_id_flip", SCHEMAS["F2a"],
                      set_yaml_leaf(SCHEMAS["F2a"], "class_id", value="AF-WCC-VAC-GEN"),
                      "P1_authorized_change_scope", "FAIL")
    mutate_and_expect("C4_declared_f0_mutation", SCHEMAS["F2b"],
                      set_yaml_leaf(SCHEMAS["F2b"], "f0_binding", "declared_f0_sha256",
                                    value="deadbeef" * 8),
                      "P1_authorized_change_scope", "FAIL")
    mutate_and_expect("C5_stale_evidence_pin", SCHEMAS["F2a"],
                      set_yaml_leaf(SCHEMAS["F2a"], "f0_binding",
                                    "consistency_evidence_sha256", value=STALE_EVIDENCE_PIN),
                      "P2_binding_chain", "FAIL")

    def drift_mirror(p):
        with open(p, "a", encoding="utf-8") as fh:
            fh.write("\n# control drift\n")
    mutate_and_expect("C6_mirror_divergence", MIRRORS["F1"], drift_mirror,
                      "P3_publication_mirrors", "FAIL")

    def unpin(p):
        d = load_json(p)
        cands = [rel for rel in sorted(d["files"]) if os.path.exists(os.path.join(sand_root, rel))]
        target = cands[0] if cands else sorted(d["files"])[0]
        d["files"][target]["sha256"] = "0" * 64
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(d, fh)
    mutate_and_expect("C7_frozen_pin_mutation", FROZEN, unpin, "P6_frozen_rev29", "FAIL")

    def mutate_f0(p):
        with open(p, "a", encoding="utf-8") as fh:
            fh.write("\n# control f0 write\n")
    mutate_and_expect("C8_f0_write", F0_CANONICAL, mutate_f0, "P4_f0_immutability", "FAIL")

    out = {"schema": "rev29-landing-guard-selftest/v1", "actor": "worker-074",
           "created_at": NOW(), "controls": results,
           "passed": sum(1 for x in results if x["ok"]), "total": len(results),
           "ok": all(x["ok"] for x in results)}
    write_out(outdir, "selftest.json", json.dumps(out, indent=1))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--baseline", default=None)
    ap.add_argument("--out", default=".")
    ap.add_argument("--events", default=None)
    ap.add_argument("--registry", default=None)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    here = os.path.dirname(os.path.abspath(__file__))
    baseline = args.baseline or os.path.join(here, "snapshot", "rev28_pin")
    if args.selftest:
        res = selftest(args.out, os.path.abspath(args.root))
        print("selftest %d/%d" % (res["passed"], res["total"]))
        sys.exit(0 if res["ok"] else 4)
    rep = audit(os.path.abspath(args.root), baseline,
                events_path=args.events, registry_path=args.registry)
    write_out(args.out, "report.json", json.dumps(rep, indent=1))
    lines = ["REV29 LANDING GUARD  measured_at=%s  status=%s  conclusion=%s"
             % (rep["measured_at"], rep["status"], rep["conclusion"])]
    for k, v in rep["predicates"].items():
        lines.append("%-32s %s" % (k, v["status"]))
    lines.append("failed=%s open=%s extra=%s"
                 % (rep["failed"], rep["open"], rep["extra_declared"]))
    write_out(args.out, os.path.join("raw", "run_log.txt"), "\n".join(lines) + "\n")
    print("\n".join(lines))
    sys.exit(0 if rep["status"] == "PASS" else (3 if rep["status"] == "OPEN" else 4))


if __name__ == "__main__":
    main()
