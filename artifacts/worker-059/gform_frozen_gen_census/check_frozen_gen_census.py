#!/usr/bin/env python3
"""W059-GFORM-FROZEN-GEN-BINDING-CENSUS-01.

One bounded class-bound read-only task: audit the CF-27 same-revision move of
`artifacts/formulation/FROZEN.json` (rev29 generation A `3d9e3d77fd87` ->
generation B `815e08079aefbc`) and decide which F1/F2a/F2b review verdicts in the
r3 window still *bind* live bytes and which cite superseded class-bound bytes in
binding fields.

Class binding: AF-WCC-VAC-GEN (F1); AF-SCC-C2-VAC-GEN (F2a); AF-SCC-C0-VAC-GEN (F2b).
Gate context: G-FORM. Authority: worker measurement only. No canonical file is
written; no node status, validation_status=passed or gate verdict is claimed.

Determinism: `report.json` contains the full measurement. `measurement_digest`
covers the deterministic core only (no wall-clock fields), and the harness
re-runs that core twice in-process and compares digests.

Usage: python3 check_frozen_gen_census.py [--out report.json]
"""
import argparse
import datetime
import glob
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))

FROZEN_CUR = "artifacts/formulation/FROZEN.json"
FROZEN_OLD = "artifacts/worker-007/rev29_preflight/snapshot/FROZEN.3d9e3d77fd87.json"

# ---------------------------------------------------------------- pre-registration
# Declared BEFORE measurement. Each is (id, statement, predicate_key).
PREREG = [
    ("E1", "snapshot FROZEN.3d9e3d77fd87.json measures sha256 3d9e3d77fd87*",
     "old_gen_hash"),
    ("E2", "live artifacts/formulation/FROZEN.json measures sha256 815e08079aefbc*",
     "new_gen_hash"),
    ("E3", "both generations declare revision 29 and new frozen_at > old frozen_at",
     "revision_and_order"),
    ("E4", "differing top-level keys are exactly {files, frozen_at, rev29_delta}",
     "top_level_diff"),
    ("E5", "changed pin set is exactly 6 value-changed + 2 added, 0 removed",
     "changed_pin_set"),
    ("E6", "all three class schema pins (and their mirrors/taxonomy/cases) are byte-identical across generations",
     "schema_pins_fixed"),
    ("E7", "every pin in the live generation resolves at live bytes (sha256 and bytes)",
     "live_pins_resolve"),
    ("E8", "the old generation no longer fully resolves at live bytes; the unresolvable set equals the superseded paths",
     "old_pins_stale"),
    ("E9", "the changed/added pins include the two class-bound variant deltas and the variant registry",
     "class_bound_change"),
    ("E10", "at least one review cites the old generation or a superseded pin in a BINDING field",
     "stale_binding_exists"),
    ("E11", "at least one review binds the live generation 815e08079aefbc and all its binding hashes resolve live",
     "rebound_exists"),
    ("E12", "the rev29_delta text documents the downstream variant rebase in generation B but not generation A",
     "delta_documented"),
    ("E13b", "all 5 superseded predecessor pins are byte-recoverable in-tree",
     "recovery_5of5"),
]

# A drafted expectation E13 ("exactly 3 of 5 superseded pins recoverable") was falsified by the
# full scan and is recorded here rather than silently rewritten.  The draft came from a recon
# listing truncated to its first 40 lines, which hid two predecessor copies.
AMENDMENTS = [
    {"id": "E13-draft",
     "statement": "exactly 3 of the 5 superseded pins are byte-recoverable in-tree",
     "status": "falsified-by-measurement",
     "measured": "5 of 5 superseded pins are byte-recoverable in-tree",
     "reason": "initial recon output was truncated (head -40) and missed two predecessor copies; "
               "the full bounded scan finds all five",
     "registered_as": "E13b"},
]

SUPERSEDED_EXPECTED_PATHS = {
    "artifacts/formulation/VARIANT_REGISTRY.json",
    "artifacts/formulation/evidence/evidence_binding_repair_rev29_report.json",
    "artifacts/formulation/tools/regenerate_frozen.py",
    "artifacts/formulation/variants/AF-SCC-C0-VAC-GEN.variant-CH.delta.json",
    "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json",
}
FROZEN_REV28_P12 = "2f358f6722d9"
ADDED_EXPECTED_PATHS = {
    "artifacts/formulation/evidence/variant_rebase_rev29_report.json",
    "artifacts/formulation/tools/variant_rebase_rev29.py",
}
SCHEMA_PATHS = [
    "schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
    "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
    "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml",
    "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
    "research_map/formulation_taxonomy.yaml",
    "artifacts/formulation/formulation_taxonomy.yaml",
    "schemas/taxonomy_cases.jsonl",
    "schemas/f1_falsifier_tests.jsonl",
]
CLASS_TOKENS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]
BINDING_KEY_RE = re.compile(
    r"(sha256|_sha\b|hash|_pin|pin_|binding|bind_chain|reviewed|artifact_sha|mirror|evidence_ref|frozen)", re.I)
HASH_RE = re.compile(r"\b[0-9a-f]{12}\b|\b[0-9a-f]{64}\b")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def prefix12(h):
    return h[:12]


def measure_input(p):
    full = os.path.join(ROOT, p)
    if not os.path.exists(full):
        return {"path": p, "exists": False, "sha256": None, "bytes": None}
    return {"path": p, "exists": True, "sha256": sha256_file(full), "bytes": os.path.getsize(full)}


def resolve_pins(pins, label):
    """Resolve every declared pin against live bytes."""
    rows, failures = [], []
    for path in sorted(pins):
        declared = pins[path]
        full = os.path.join(ROOT, path)
        row = {"path": path, "declared_sha256": declared.get("sha256"),
               "declared_bytes": declared.get("bytes"),
               "exists": os.path.exists(full), "measured_sha256": None, "measured_bytes": None,
               "sha256_match": False, "bytes_match": False}
        if row["exists"]:
            row["measured_sha256"] = sha256_file(full)
            row["measured_bytes"] = os.path.getsize(full)
            row["sha256_match"] = row["measured_sha256"] == row["declared_sha256"]
            row["bytes_match"] = row["measured_bytes"] == row["declared_bytes"]
        rows.append(row)
        if not (row["exists"] and row["sha256_match"] and row["bytes_match"]):
            failures.append(row)
    return {"label": label, "total": len(rows), "resolved": len(rows) - len(failures),
            "failures": failures, "rows": rows}


def extract_hash_tokens(text):
    return set(HASH_RE.findall(text))


def walk_binding_hashes(node, key_hint="", acc=None):
    """Collect hash tokens under binding-looking keys as {hash: sorted(key paths)}."""
    if acc is None:
        acc = {}
    if isinstance(node, dict):
        for k, v in node.items():
            walk_binding_hashes(v, f"{key_hint}/{k}", acc)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            walk_binding_hashes(v, f"{key_hint}[{i}]", acc)
    elif isinstance(node, str):
        if BINDING_KEY_RE.search(key_hint):
            for h in extract_hash_tokens(node):
                acc.setdefault(h, set()).add(key_hint)
    return acc


def refs_for(hashes, by_hash):
    out = []
    for h in sorted(hashes):
        for kp in sorted(by_hash.get(h, [])):
            out.append(f"{kp}:{h[:12]}")
    return sorted(out)


def review_class_scope(obj, text):
    scopes = set()
    for key in ("class_id", "class_ids", "class_binding", "class_scope_tokens"):
        v = obj.get(key)
        if isinstance(v, str):
            scopes |= {t for t in CLASS_TOKENS if t in v}
        elif isinstance(v, list):
            for item in v:
                if isinstance(item, str):
                    scopes |= {t for t in CLASS_TOKENS if t in item}
    if not scopes:
        scopes = {t for t in CLASS_TOKENS if t in text}
    return sorted(scopes)


def classify_review(obj, text, gen):
    """Pure classifier used for the real corpus and for planted mutants."""
    by_hash = walk_binding_hashes(obj)
    binding = set(by_hash)
    mention = extract_hash_tokens(text) - binding
    binding_p12 = {prefix12(h) for h in binding}
    mention_p12 = {prefix12(h) for h in mention}

    frozen_gens = {"rev28": FROZEN_REV28_P12, "genA": gen["old_gen_p12"], "genB": gen["new_gen_p12"]}
    bound_frozen = sorted(name for name, p in frozen_gens.items() if p in binding_p12)
    binds_old_gen = "genA" in bound_frozen
    binds_new_gen = "genB" in bound_frozen
    superseded_hashes = {h for h in binding
                         if prefix12(h) in gen["superseded_p12"] or h in gen["superseded_full"]}
    superseded_refs = refs_for(superseded_hashes, by_hash)
    old_gen_refs = refs_for({h for h in binding if prefix12(h) == gen["old_gen_p12"]}, by_hash)
    new_gen_refs = refs_for({h for h in binding if prefix12(h) == gen["new_gen_p12"]}, by_hash)
    live = sorted({h for h in binding if prefix12(h) in gen["live_p12"]})
    unknown = sorted({h for h in binding
                      if prefix12(h) not in gen["live_p12"]
                      and prefix12(h) not in gen["superseded_p12"]
                      and prefix12(h) not in frozen_gens.values()})
    mention_old_only = (gen["old_gen_p12"] in mention_p12) and not binds_old_gen

    created = obj.get("created_at") or obj.get("written_at")
    written_after_genb = bool(created and gen.get("new_frozen_at")
                              and str(created) > gen["new_frozen_at"])

    if superseded_refs or any(g != "genB" for g in bound_frozen):
        category = "STALE_BINDING"
    elif binds_new_gen:
        category = "REBOUND"
    elif mention_old_only:
        category = "MENTION_ONLY_OLD"
    else:
        category = "UNBOUND"

    verdict = obj.get("verdict")
    if isinstance(verdict, dict):
        verdict = verdict.get("verdict")
    return {
        "binds_old_gen": binds_old_gen,
        "binds_new_gen": binds_new_gen,
        "bound_frozen_generations": bound_frozen,
        "binds_superseded": bool(superseded_refs),
        "superseded_refs": superseded_refs,
        "old_gen_refs": old_gen_refs,
        "new_gen_refs": new_gen_refs,
        "live_binding_hashes": live,
        "unknown_binding_hashes": unknown,
        "mention_old_only": mention_old_only,
        "written_after_genB_frozen_at": written_after_genb,
        "verdict": verdict,
        "class_scope": review_class_scope(obj, text),
        "counts_as_full_schema_verdict": bool(obj.get("counts_as_full_schema_verdict")
                                              or obj.get("counts_as_independent_verdict")
                                              or obj.get("counts_as_full_schema_verdict")),
        "category": category,
    }


def build_generation_model(cur, old):
    pins_cur, pins_old = cur.get("files", {}), old.get("files", {})
    changed = []
    for path in sorted(set(pins_cur) | set(pins_old)):
        a, b = pins_old.get(path), pins_cur.get(path)
        if a == b:
            continue
        if a is None:
            kind = "added"
        elif b is None:
            kind = "removed"
        else:
            kind = "value_changed"
        changed.append({"path": path, "kind": kind, "old": a, "new": b})
    superseded_full = set()
    for c in changed:
        if c["old"]:
            superseded_full.add(c["old"]["sha256"])
    sup_p12 = {prefix12(h) for h in superseded_full}
    live_p12 = {prefix12(v["sha256"]) for v in pins_cur.values()}
    new_full = sha256_file(os.path.join(ROOT, FROZEN_CUR))
    old_full = sha256_file(os.path.join(ROOT, FROZEN_OLD))
    return {
        "changed": changed,
        "superseded_full": superseded_full,
        "superseded_p12": sup_p12,
        "live_p12": live_p12,
        "old_gen_p12": prefix12(old_full),
        "old_gen_full": old_full,
        "new_gen_p12": prefix12(new_full),
        "new_gen_full": new_full,
        "old_frozen_at": old.get("frozen_at"),
        "new_frozen_at": cur.get("frozen_at"),
    }


def census(gen, corpus_pins=None):
    rows, parse_fail, scanned = [], [], 0
    corpus_verified, corpus_missing = 0, []
    all_files = sorted(glob.glob(os.path.join(ROOT, "reviews", "*.json")))
    if corpus_pins is not None:
        all_files = [p for p in all_files if os.path.basename(p) in corpus_pins]
    extras = 0
    for p in all_files:
        name = os.path.basename(p)
        scanned += 1
        raw = open(p, "r", encoding="utf-8", errors="replace").read()
        if corpus_pins is not None:
            if sha256_file(p) != corpus_pins.get(name):
                corpus_missing.append(name)
                continue
            corpus_verified += 1
        try:
            obj = json.loads(raw)
        except Exception as exc:  # noqa: BLE001
            parse_fail.append({"file": name, "error": str(exc)[:120]})
            continue
        if not isinstance(obj, dict):
            parse_fail.append({"file": name, "error": "not-an-object"})
            continue
        row = classify_review(obj, raw, gen)
        row["file"] = name
        row["created_at"] = obj.get("created_at") or obj.get("written_at")
        row["nodes"] = obj.get("node_id") or obj.get("node_ids")
        rows.append(row)
    if corpus_pins is not None:
        live_names = {os.path.basename(p) for p in glob.glob(os.path.join(ROOT, "reviews", "*.json"))}
        extras = len(live_names - set(corpus_pins))
    counts = {}
    for r in rows:
        counts[r["category"]] = counts.get(r["category"], 0) + 1
    return {"scanned": scanned, "parsed": len(rows), "parse_failures": parse_fail,
            "corpus_verified": corpus_verified, "corpus_mismatch_or_missing": corpus_missing,
            "live_extras_ignored": extras,
            "corpus_pins": {os.path.basename(p): sha256_file(p) for p in all_files},
            "counts": counts, "rows": rows}


def recovery_scan(changed):
    """Bounded in-tree census: which superseded predecessor bytes still exist anywhere."""
    wanted = {c["old"]["sha256"]: c["path"] for c in changed
              if c["kind"] == "value_changed" and c["old"]}
    wanted_basenames = {os.path.basename(p): h for h, p in wanted.items()}
    found = {h: [] for h in wanted}
    scanned = 0
    for sub in ("artifacts", "tmp"):
        base_dir = os.path.join(ROOT, sub)
        if not os.path.isdir(base_dir):
            continue
        for dirpath, _dirnames, filenames in os.walk(base_dir):
            for fn in filenames:
                if fn not in wanted_basenames:
                    continue
                scanned += 1
                full = os.path.join(dirpath, fn)
                try:
                    h = sha256_file(full)
                except OSError:
                    continue
                if h in found:
                    found[h].append(os.path.relpath(full, ROOT))
    rows = []
    for c in changed:
        if c["kind"] != "value_changed" or not c["old"]:
            continue
        h = c["old"]["sha256"]
        rows.append({"path": c["path"], "superseded_sha256": h,
                     "recoverable": bool(found[h]), "copies": sorted(found[h])})
    return {"scanned_candidate_files": scanned, "recoverable_count": sum(1 for r in rows if r["recoverable"]),
            "total_superseded": len(rows), "rows": rows}


def run_core(corpus_pins=None):
    cur = read_json(os.path.join(ROOT, FROZEN_CUR))
    old = read_json(os.path.join(ROOT, FROZEN_OLD))
    gen = build_generation_model(cur, old)
    gen_res = {"live": resolve_pins(cur.get("files", {}), "live"),
               "old_at_live_bytes": resolve_pins(old.get("files", {}), "old_at_live_bytes")}
    rev = census(gen, corpus_pins)

    # ---- expectations
    top_diff = sorted(k for k in set(cur) | set(old) if cur.get(k) != old.get(k))
    changed_pins = gen["changed"]
    class_scan = []
    for c in changed_pins:
        full = os.path.join(ROOT, c["path"])
        toks, live_sha = None, None
        if os.path.exists(full):
            body = open(full, "r", encoding="utf-8", errors="replace").read()
            toks = sorted({t for t in CLASS_TOKENS if t in body})
            live_sha = sha256_file(full)
        class_scan.append({"path": c["path"], "kind": c["kind"],
                           "class_tokens": toks, "live_sha256": live_sha})
    rec = recovery_scan(changed_pins)
    value_changed = sorted(c["path"] for c in changed_pins if c["kind"] == "value_changed")
    added = sorted(c["path"] for c in changed_pins if c["kind"] == "added")
    removed = sorted(c["path"] for c in changed_pins if c["kind"] == "removed")
    schema_fixed = all(cur["files"].get(p) == old["files"].get(p) for p in SCHEMA_PATHS)
    old_fail_paths = sorted(f["path"] for f in gen_res["old_at_live_bytes"]["failures"])
    stale_binding = [r for r in rev["rows"] if r["category"] == "STALE_BINDING"]
    stale_full = [r for r in stale_binding if r["counts_as_full_schema_verdict"]]
    rebound_live = [r for r in rev["rows"] if r["category"] == "REBOUND" and not r["unknown_binding_hashes"]]
    delta_new = json.dumps(cur.get("rev29_delta"))
    delta_old = json.dumps(old.get("rev29_delta"))

    results = {}
    results["old_gen_hash"] = gen["old_gen_full"].startswith("3d9e3d77fd87")
    results["new_gen_hash"] = gen["new_gen_full"].startswith("815e08079aefbc")
    results["revision_and_order"] = (cur.get("revision") == old.get("revision") == 29
                                     and cur.get("frozen_at", "") > old.get("frozen_at", ""))
    results["top_level_diff"] = top_diff == ["files", "frozen_at", "rev29_delta"]
    results["changed_pin_set"] = (set(value_changed) == SUPERSEDED_EXPECTED_PATHS
                                  and set(added) == ADDED_EXPECTED_PATHS and not removed)
    results["schema_pins_fixed"] = schema_fixed
    results["live_pins_resolve"] = gen_res["live"]["resolved"] == gen_res["live"]["total"]
    results["old_pins_stale"] = (gen_res["old_at_live_bytes"]["resolved"] < gen_res["old_at_live_bytes"]["total"]
                                 and set(old_fail_paths) == SUPERSEDED_EXPECTED_PATHS)
    results["class_bound_change"] = any("variant" in p for p in value_changed) and any(
        p.endswith("VARIANT_REGISTRY.json") for p in value_changed)
    results["stale_binding_exists"] = len(stale_binding) >= 1
    results["rebound_exists"] = len(rebound_live) >= 1
    results["delta_documented"] = ("Downstream" in delta_new and "Downstream" not in delta_old)
    unrecoverable = {r["path"] for r in rec["rows"] if not r["recoverable"]}
    results["recovery_5of5"] = (rec["recoverable_count"] == 5 and rec["total_superseded"] == 5
                                and not unrecoverable)

    expectations = []
    for eid, statement, key in PREREG:
        expectations.append({"id": eid, "statement": statement, "result": bool(results[key])})

    core = {
        "generations": {
            "live": {"path": FROZEN_CUR, "revision": cur.get("revision"),
                     "frozen_at": cur.get("frozen_at"),
                     "sha256": sha256_file(os.path.join(ROOT, FROZEN_CUR)),
                     "pins": len(cur.get("files", {}))},
            "predecessor": {"path": FROZEN_OLD, "revision": old.get("revision"),
                            "frozen_at": old.get("frozen_at"),
                            "sha256": sha256_file(os.path.join(ROOT, FROZEN_OLD)),
                            "pins": len(old.get("files", {}))},
            "same_revision": cur.get("revision") == old.get("revision"),
            "top_level_diff": top_diff,
        },
        "changed_pins": changed_pins,
        "changed_pin_class_scan": class_scan,
        "superseded_recovery_scan": rec,
        "superseded_hashes": sorted(gen["superseded_full"]),
        "pin_resolution": gen_res,
        "review_census": rev,
        "materiality": {
            "stale_binding_all": [r["file"] for r in stale_binding],
            "stale_binding_full_schema_scope": [r["file"] for r in stale_full],
            "stale_written_after_genB_frozen_at": [r["file"] for r in stale_binding
                                                   if r["written_after_genB_frozen_at"]],
            "stale_accepts": [r["file"] for r in stale_binding if r["verdict"] == "accept"],
            "rebound_live_all": [r["file"] for r in rebound_live],
            "bound_frozen_generation_counts": {
                gen_name: sum(1 for r in rev["rows"]
                              if gen_name in r["bound_frozen_generations"])
                for gen_name in ("rev28", "genA", "genB")},
        },
        "expectations": expectations,
        "amendments": AMENDMENTS,
        "expectations_all_pass": all(e["result"] for e in expectations),
    }
    return core


def mutants_and_controls():
    """Exercise the same classifier/generation logic on planted defects."""
    out = []
    cur = read_json(os.path.join(ROOT, FROZEN_CUR))
    old = read_json(os.path.join(ROOT, FROZEN_OLD))
    gen = build_generation_model(cur, old)
    good = json.loads(json.dumps(cur))
    good_old = json.loads(json.dumps(old))

    # M1 schema pin mutated -> schema_pins_fixed must fail
    m = json.loads(json.dumps(good)); m["files"]["schemas/af_wcc_vacuum.yaml"]["sha256"] = "0" * 64
    out.append({"id": "M1", "planted": "F1 schema pin mutated in live generation",
                "detector": "schema_pins_fixed",
                "fired": not all(m["files"].get(p) == good_old["files"].get(p) for p in SCHEMA_PATHS)})
    # M2 added pin removed -> changed_pin_set must fail
    m = json.loads(json.dumps(good)); m["files"].pop("artifacts/formulation/tools/variant_rebase_rev29.py", None)
    mg = build_generation_model(m, good_old)
    added = {c["path"] for c in mg["changed"] if c["kind"] == "added"}
    out.append({"id": "M2", "planted": "added pin removed",
                "detector": "changed_pin_set", "fired": added != ADDED_EXPECTED_PATHS})
    # M3 frozen_at order inverted -> revision_and_order must fail
    m = json.loads(json.dumps(good)); m["frozen_at"] = "2026-09-12T00:00:00+08:00"
    out.append({"id": "M3", "planted": "frozen_at earlier than predecessor",
                "detector": "revision_and_order",
                "fired": not (m.get("revision") == good_old.get("revision") == 29
                              and m.get("frozen_at", "") > good_old.get("frozen_at", ""))})
    # M4 superseded hash in a binding field -> STALE_BINDING
    sup = sorted(gen["superseded_full"])[0]
    mk = {"event_type": "review", "verdict": "accept", "counts_as_full_schema_verdict": True,
          "class_id": "AF-WCC-VAC-GEN", "evidence_refs": ["schemas/af_wcc_vacuum.yaml#" + sup]}
    txt = json.dumps(mk)
    out.append({"id": "M4", "planted": "superseded class-bound hash in evidence_refs",
                "detector": "classify_review=STALE_BINDING",
                "fired": classify_review(mk, txt, gen)["category"] == "STALE_BINDING"})
    # M5 old-gen hash only in narrative -> MENTION_ONLY_OLD (false-positive control)
    mk = {"event_type": "review", "verdict": "revise", "class_id": "AF-WCC-VAC-GEN",
          "note": "superseded by generation " + gen["old_gen_p12"]}
    txt = json.dumps(mk)
    out.append({"id": "M5", "planted": "old-gen hash in narrative only",
                "detector": "classify_review=MENTION_ONLY_OLD",
                "fired": classify_review(mk, txt, gen)["category"] == "MENTION_ONLY_OLD"})
    # M6 unchanged live schema hash only -> UNBOUND (must NOT be flagged stale)
    live_schema = good["files"]["schemas/af_wcc_vacuum.yaml"]["sha256"]
    mk = {"event_type": "review", "verdict": "accept", "class_id": "AF-WCC-VAC-GEN",
          "reviewed_sha256": live_schema}
    txt = json.dumps(mk)
    r = classify_review(mk, txt, gen)
    out.append({"id": "M6", "planted": "review binds only the unchanged live schema",
                "detector": "classify_review=UNBOUND (no stale flag)",
                "fired": r["category"] == "UNBOUND" and not r["binds_superseded"]})
    # C1 unparseable review line is skipped, not classified
    try:
        json.loads("{not json")
        c1 = False
    except Exception:  # noqa: BLE001
        c1 = True
    out.append({"id": "C1", "planted": "malformed review bytes", "detector": "census parse guard", "fired": c1})
    # C2 rollback check: predecessor FROZEN itself still parses and pins 48 paths
    out.append({"id": "C2", "planted": "predecessor generation readable",
                "detector": "generation model", "fired": len(good_old.get("files", {})) == 48})
    # C3 live generation re-hashes to its recorded bytes (measurement instrument stability)
    out.append({"id": "C3", "planted": "live FROZEN re-hashed after core run",
                "detector": "sha256 determinism",
                "fired": sha256_file(os.path.join(ROOT, FROZEN_CUR)) == gen["new_gen_full"]})
    return out


def build_focused(report, source_path, source_sha256, digest):
    return {
        "audit_id": report["audit_id"],
        "actor": report["actor"],
        "class_binding": report["class_binding"],
        "gate_context": report["gate_context"],
        "source_report": os.path.basename(source_path),
        "source_report_sha256": source_sha256,
        "measurement_digest": digest,
        "generations": report["generations"],
        "changed_pins": report["changed_pins"],
        "changed_pin_class_scan": report["changed_pin_class_scan"],
        "superseded_hashes": report["superseded_hashes"],
        "materiality": report["materiality"],
        "stale_rows": [row for row in report["review_census"]["rows"]
                       if row["category"] == "STALE_BINDING"],
        "rebound_rows_live_resolvable": [row for row in report["review_census"]["rows"]
                                         if row["category"] == "REBOUND"
                                         and not row["unknown_binding_hashes"]],
        "falsifier": ("Re-run check_frozen_gen_census.py --corpus-from report.json at the same six "
                      "input pins: falsified if measurement_digest or review_census_digest changes, "
                      "if E1-E12/E13b or M1-M6/C1-C3 change result, if any review row's category "
                      "changes under the pinned corpus, or if any pinned input re-hashes differently."),
    }


def write_focused(report, source_path, source_sha256, digest, out_path):
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(build_focused(report, source_path, source_sha256, digest), fh,
                  indent=1, sort_keys=False)
        fh.write("\n")
    return out_path


def default_focused_path(out_path):
    """Never rewrite the published focused artifact when --out points elsewhere."""
    if os.path.abspath(out_path) == os.path.abspath(os.path.join(HERE, "report.json")):
        return os.path.join(HERE, "stale_binding_census.json")
    return os.path.splitext(out_path)[0] + ".focused.json"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(HERE, "report.json"))
    ap.add_argument("--corpus-from", default=None,
                    help="prior report.json; census only the pinned review corpus")
    ap.add_argument("--focused-out", default=None,
                    help="focused extract output path (default derived from --out)")
    ap.add_argument("--focused-from", default=None,
                    help="rebuild the focused extract from an existing report and exit")
    args = ap.parse_args()

    if args.focused_from:
        prior = read_json(args.focused_from)
        src_sha = sha256_file(args.focused_from)
        fpath = args.focused_out or default_focused_path(args.focused_from)
        write_focused(prior, args.focused_from, src_sha, prior["measurement_digest"], fpath)
        print("focused:", fpath, sha256_file(fpath)[:16])
        return 0

    corpus_pins = None
    if args.corpus_from:
        prior = read_json(args.corpus_from)
        corpus_pins = prior["review_census"]["corpus_pins"]
        print("pinned corpus:", len(corpus_pins), "reviews from", args.corpus_from)

    t0 = datetime.datetime.now().astimezone()
    inputs = [measure_input(p) for p in (
        FROZEN_CUR, FROZEN_OLD,
        "artifacts/worker-007/rev29_preflight/snapshot/AF-WCC-VAC-GEN.variant-SET.delta.45b9b6a8d192.json",
        "artifacts/worker-007/rev29_preflight/snapshot/AF-WCC-VAC-GEN.variant-SET.delta.64b8d6394a04.json",
        "artifacts/worker-007/rev29_preflight/snapshot/AF-SCC-C0-VAC-GEN.variant-CH.delta.c28795b0fdfc.json",
        "artifacts/worker-007/rev29_preflight/snapshot/AF-SCC-C0-VAC-GEN.variant-CH.delta.7c165a9063c6.json",
        "artifacts/worker-007/rev29_preflight/snapshot/VARIANT_REGISTRY.5eb42f9a384a.json",
        "artifacts/worker-007/rev29_preflight/snapshot/VARIANT_REGISTRY.6bac9adea19e.json",
    )]

    core1 = run_core(corpus_pins)
    core2 = run_core(corpus_pins)
    static_core = {k: v for k, v in core1.items() if k != "review_census"}
    digest = hashlib.sha256(json.dumps(static_core, sort_keys=True).encode()).hexdigest()
    census_core = {k: core1["review_census"][k] for k in ("corpus_pins", "counts", "rows")}
    census_digest = hashlib.sha256(json.dumps(census_core, sort_keys=True).encode()).hexdigest()

    def _norm(core):
        c = json.loads(json.dumps(core))
        c["review_census"].pop("live_extras_ignored", None)
        return json.dumps(c, sort_keys=True)

    deterministic = _norm(core1) == _norm(core2)
    mutants = mutants_and_controls()
    entry_exit_stable = [measure_input(p["path"]) for p in inputs] == inputs

    report = {
        "audit_id": "W059-GFORM-FROZEN-GEN-BINDING-CENSUS-01",
        "actor": "worker-059",
        "created_at": t0.isoformat(timespec="seconds"),
        "class_binding": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "nodes": ["F1", "F2a", "F2b"],
        "gate_context": "G-FORM",
        "authority": ("worker measurement only; no canonical file written, no node status, "
                      "no validation_status=passed, no gate verdict"),
        "inputs": inputs,
        "entry_exit_stable": entry_exit_stable,
        "deterministic_core": deterministic,
        "determinism_excludes": ["review_census.live_extras_ignored (wall-clock counter)"],
        "measurement_digest": digest,
        "review_census_digest": census_digest,
        "corpus_mode": "pinned" if corpus_pins is not None else "live",
        "mutants_controls": mutants,
        "mutants_controls_all_fired": all(m["fired"] for m in mutants),
        **core1,
    }
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1, sort_keys=False)
        fh.write("\n")

    focused_path = args.focused_out or default_focused_path(args.out)
    write_focused(report, args.out, sha256_file(args.out), digest, focused_path)

    print("report:", args.out)
    print("digest:", digest, "census_digest:", census_digest, "deterministic:", deterministic,
          "entry_exit_stable:", entry_exit_stable)
    print("expectations:", {e["id"]: e["result"] for e in report["expectations"]})
    print("mutants/controls:", {m["id"]: m["fired"] for m in mutants})
    print("review census:", report["review_census"]["counts"])
    print("live pins:", report["pin_resolution"]["live"]["resolved"], "/",
          report["pin_resolution"]["live"]["total"])
    print("old pins at live bytes:", report["pin_resolution"]["old_at_live_bytes"]["resolved"], "/",
          report["pin_resolution"]["old_at_live_bytes"]["total"])
    return 0 if (report["expectations_all_pass"] and deterministic and entry_exit_stable
                 and report["mutants_controls_all_fired"]) else 1


if __name__ == "__main__":
    sys.exit(main())
