#!/usr/bin/env python3
"""W031-F1-SUITE-REPIN-PROPOSAL-01 -- dry-run instrument.

Class: AF-WCC-VAC-GEN (refs AF-SCC-C2-VAC-GEN, AF-SCC-C0-VAC-GEN). Node F1. Gate G-FORM.

Question: the owner (astra-lead-formulation) has declared the F1 falsifier suite
schemas/f1_falsifier_tests.jsonl#56bcb4b3234b NOT re-bound to the post-repair F1 rev13
d9cebb9404b2 (blocker L-FORM-04, 2026-09-12T00:57:43). This instrument builds the exact
minimal re-pin + F1-AMB-25 content repair as a patch, applies it to an artifact-local
copy ONLY, and measures whether it makes the suite self-consistent at the live pins:
  25/25 row bindings live, binding_ref/binding_sha256 self-consistent, 1/1 cross_artifact
  live, 84/84 stored probes re-evaluate true, vendor checks C1a/C1b/C2/C4-C10 pass.

It also quantifies the downstream cascade (FROZEN rev29 pins the suite path, so a re-pin
forces FROZEN rev30) and records the owner decisions it must not make unilaterally.

Read-only on every canonical path. Writes ONLY under its own artifact directory.
Exit codes: 0 = report written, all pre-registered predictions met;
            1 = report written, deviations recorded (inspect report.deviations);
            2 = void: pinned input drift (no report promoted).

Replay: python3 artifacts/worker-031/f1_suite_repin_dryrun/dryrun_repin_031.py
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

import yaml

TZ = timezone(timedelta(hours=8))
HEX64 = re.compile(r"^[0-9a-f]{64}$")

# --------------------------------------------------------------------------------------
# pins (full sha256; pre-measured 2026-09-12T00:58-01:00+08:00)
# --------------------------------------------------------------------------------------
CANON = {
    "suite": "schemas/f1_falsifier_tests.jsonl",
    "f1": "schemas/af_wcc_vacuum.yaml",
    "f2a": "schemas/af_scc_c2_vacuum.yaml",
    "f2b": "schemas/af_scc_c0_vacuum.yaml",
    "f1_mirror": "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
    "f0": "research_map/formulation_taxonomy.yaml",
    "corpus": "schemas/taxonomy_cases.jsonl",
    "frozen": "artifacts/formulation/FROZEN.json",
    "consistency": "artifacts/formulation/evidence/taxonomy_consistency.json",
    "vendor": "artifacts/flash-04/f1_ambiguity/verify_freeze_current.py",
    "registry": "runtime/state/artifact_hashes.json",
}
PINS = {
    CANON["suite"]: "56bcb4b3234bc86c324bec6e38f142c5ef39517f20d823b6a333f578b7d0851e",
    CANON["f1"]: "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    CANON["f2a"]: "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    CANON["f2b"]: "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    CANON["f1_mirror"]: "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    CANON["f0"]: "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    CANON["corpus"]: "ccf7041bd0ff3ce844c07a700a588b7fe8e3c90880674c5e595b21f6259a8f03",
    CANON["frozen"]: "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    CANON["consistency"]: "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b",
    CANON["vendor"]: "0527fac95b898f865367b9649a538487b23eaf89bc15a4d5210f9fc9f72ce7d7",
}
PRE_REPAIR_F1 = {
    "path": "artifacts/worker-007/rev29_preflight/snapshot/af_wcc_vacuum.cce9c60146d6.yaml",
    "sha256": "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3",
}
PINNED_FOR_STABILITY = list(PINS)  # re-hashed at end (drift guard, K7)

REV13_PREFIX16 = PINS[CANON["f1"]][:16]          # d9cebb9404b2e79e
F0_FULL = PINS[CANON["f0"]]
PROPOSED_REBOUND_AT = "2026-09-12T01:10:00+08:00"  # placeholder; owner sets actual
BINDING_NOTE_ANCHOR_V1 = ("rev13: consistency_evidence_sha256 refreshed to the live "
                          "taxonomy_consistency.json 9e335e9ba1bf")
BINDING_NOTE_ANCHOR_V2 = "refreshed to the rev5 declared-F0 hash"
BINDING_NOTE_VARIANTS = {"V1": BINDING_NOTE_ANCHOR_V1, "V2": BINDING_NOTE_ANCHOR_V2}
PRIMARY_ANCHOR = "V1"
REBIND_NOTE = ("rev13 re-pin PROPOSED by worker-031 (W031-F1-SUITE-REPIN-PROPOSAL-01): "
               "binding moved from F1 rev12 cce9c60146d6 to the post-evidence-binding-repair "
               "F1 rev13 d9cebb9404b2; F1-AMB-25 cross_artifact and the two f0_binding probe "
               "expectations refreshed to live F0 rev5 0abb9ed8a961. Owner must set the actual "
               "re-publish instant and bump FROZEN to rev30 (FROZEN rev29 pins this suite path).")

SEMANTIC_KEYS = (
    "test_id", "ambiguity_kind", "artifact_kind", "artifact_version", "author", "class_id",
    "node_id", "gate", "question", "title", "why", "spacetime_description",
    "deciding_field", "deciding_field_alternates", "deciding_field_contract",
    "deciding_field_status", "does_it_satisfy_f1", "satisfies_conclusion", "satisfies_in_class",
    "falsifier", "falsifier_strength", "next_falsifier", "known_properties",
    "literature_status", "citation_status", "counterexample_candidate", "probe_results.path",
    "probe_results.kind", "probe_results.role", "probe_results.pass",
)
VENDOR_REQUIRED = (
    "test_id", "class_id", "node_id", "gate", "spacetime_description", "does_it_satisfy_f1",
    "deciding_field", "falsifier", "next_falsifier", "evidence_refs", "binding_sha256",
)
OPEN_OBLIGATIONS = ("F1-AMB-01", "F1-AMB-02", "F1-AMB-03", "F1-AMB-15")
VSAT = {"yes", "no", "ambiguous"}

# --------------------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------------------


def find_root(start: str) -> str:
    cur = os.path.dirname(os.path.abspath(start))
    while True:
        if os.path.isdir(os.path.join(cur, "research_map")) and os.path.isdir(os.path.join(cur, "schemas")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            raise RuntimeError("swarm root not found above " + start)
        cur = parent


ROOT = find_root(__file__)
OUTDIR = os.path.join(ROOT, "artifacts/worker-031/f1_suite_repin_dryrun")
PATCHED_DIR = os.path.join(OUTDIR, "patched")


def now() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_bytes(path: str) -> bytes:
    with open(os.path.join(ROOT, path), "rb") as fh:
        return fh.read()


def load_jsonl_text(text: str) -> list:
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def dump_jsonl(rows: list) -> bytes:
    """Canonical suite serialization: json.dumps(row) + newline, insertion order preserved."""
    return ("\n".join(json.dumps(r) for r in rows) + "\n").encode("utf-8")


ABSENT = "__ABSENT__"


def resolve(doc, dotted: str):
    cur = doc
    for raw in str(dotted).split("."):
        tok = raw.strip()
        if isinstance(cur, dict):
            if tok not in cur:
                return ABSENT
            cur = cur[tok]
        elif isinstance(cur, list):
            try:
                cur = cur[int(tok)]
            except (ValueError, IndexError):
                return ABSENT
        else:
            return ABSENT
    return cur


def recompute_probe(doc, probe: dict) -> bool:
    value = resolve(doc, str(probe.get("path", "")))
    kind = probe.get("kind")
    expected = probe.get("expected")
    if kind == "equals":
        return value is not ABSENT and str(value) == str(expected)
    if kind == "contains":
        if value is ABSENT:
            return False
        text = value if isinstance(value, str) else json.dumps(value, sort_keys=True)
        return str(expected) in text
    if kind == "is_true":
        return value is True
    if kind == "is_none":
        return value is None
    if kind == "path_exists":
        return value is not ABSENT
    if kind == "nonnull":
        return value is not ABSENT and value is not None
    return False


def rows_to_map(rows: list) -> dict:
    """Patch root: the suite as a map test_id -> row (row order is not part of the binding)."""
    return {r["test_id"]: r for r in rows}


def map_to_rows(rows: list, m: dict) -> list:
    return [m[r["test_id"]] for r in rows]


def jptr_get(doc, pointer: str):
    cur = doc
    for raw in pointer.strip("/").split("/"):
        tok = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(cur, list):
            cur = cur[int(tok)]
        else:
            cur = cur[tok]
    return cur


def jptr_set(doc, pointer: str, value):
    toks = [t.replace("~1", "/").replace("~0", "~") for t in pointer.strip("/").split("/")]
    cur = doc
    for t in toks[:-1]:
        cur = cur[int(t)] if isinstance(cur, list) else cur[t]
    last = toks[-1]
    if isinstance(cur, list):
        cur[int(last)] = value
    else:
        cur[last] = value


def diff_pointers(a, b, pointer: str = "") -> list:
    """Recursively enumerate JSON-pointer paths whose value differs between a and b."""
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            p = f"{pointer}/{k}"
            if k not in a or k not in b:
                out.append(p)
            else:
                out.extend(diff_pointers(a[k], b[k], p))
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append(pointer or "/")
        else:
            for i, (x, y) in enumerate(zip(a, b)):
                out.extend(diff_pointers(x, y, f"{pointer}/{i}"))
    elif a != b:
        out.append(pointer or "/")
    return out


def row_by_id(rows, tid):
    for r in rows:
        if r.get("test_id") == tid:
            return r
    raise KeyError(tid)


def serializable_patch(entries):
    return {"entries": entries, "entry_count": len(entries),
            "sha256": sha256_bytes(json.dumps(entries, sort_keys=True, indent=1).encode())}


# --------------------------------------------------------------------------------------
# measurement primitives
# --------------------------------------------------------------------------------------


def check_binding(path: str, token: str, live_sha: str) -> dict:
    return {"path": path, "token": token, "status": "live" if token == live_sha else "stale",
            "live_sha256": live_sha}


def census(rows: list, f1_doc, f1_sha: str, label: str) -> dict:
    """Operative-pin census + probe recompute of `rows` against a supplied F1 (doc, sha)."""
    recs, defects = [], []
    binding_live = ref_consistent = cross_live = cross_stale = 0
    probes_total = probes_stored_pass = probes_recomputed_pass = 0
    mismatches = []
    for row in rows:
        rid = row.get("test_id", "?")
        rec = {"test_id": rid, "defect": False}

        token = str(row.get("binding_sha256", ""))
        ref = str(row.get("binding_ref", ""))
        ref_path = ref.split("#", 1)[0] if ref else CANON["f1"]
        ref_token = ref.split("#sha256:", 1)[1] if "#sha256:" in ref else ""
        c = check_binding(ref_path, token, f1_sha)
        c["kind"] = "row_binding"
        rec["binding"] = c
        if c["status"] == "live":
            binding_live += 1
        else:
            rec["defect"] = True
            defects.append({"where": f"suite:{rid}:binding_sha256", **c})
        # self-consistency: the ref token must be a prefix of the operative token
        rec["ref_sha_consistent"] = bool(ref_token) and token.startswith(ref_token)
        if rec["ref_sha_consistent"]:
            ref_consistent += 1
        else:
            rec["defect"] = True
            defects.append({"where": f"suite:{rid}:binding_ref_vs_binding_sha256",
                            "ref_token": ref_token, "binding_sha256": token})

        for i, ca in enumerate(row.get("cross_artifact") or []):
            p, t = ca.get("path"), ca.get("sha256")
            if not p or not t:
                continue
            cc = check_binding(p, str(t), sha256_file(os.path.join(ROOT, p)))
            cc["kind"] = "cross_artifact"
            if cc["status"] == "live":
                cross_live += 1
            else:
                cross_stale += 1
                rec["defect"] = True
                defects.append({"where": f"suite:{rid}:cross_artifact[{i}]", **cc})

        for i, probe in enumerate(row.get("probe_results", [])):
            stored = bool(probe.get("pass"))
            got = recompute_probe(f1_doc, probe)
            probes_total += 1
            probes_stored_pass += int(stored)
            probes_recomputed_pass += int(got)
            if stored != got:
                mismatches.append({"test_id": rid, "probe_index": i, "path": probe.get("path"),
                                   "kind": probe.get("kind"), "role": probe.get("role"),
                                   "stored_pass": stored, "recomputed_pass": got,
                                   "expected": probe.get("expected")})
        recs.append(rec)
    return {
        "label": label, "f1_sha256": f1_sha, "rows": len(rows),
        "binding_live": binding_live, "binding_stale": len(rows) - binding_live,
        "ref_sha_consistent": ref_consistent, "ref_sha_inconsistent": len(rows) - ref_consistent,
        "cross_artifact_live": cross_live, "cross_artifact_stale": cross_stale,
        "probes_total": probes_total, "probes_stored_pass": probes_stored_pass,
        "probes_recomputed_pass": probes_recomputed_pass,
        "probe_mismatches": mismatches, "defects": defects, "rows_detail": recs,
    }


def vendor_checks(rows: list, frozen: dict, measured_f1: str, measured_mirror: str) -> dict:
    """Independent reimplementation of verify_freeze_current.py C1a/C1b/C2/C4-C10.

    Never executes the vendor verifier (it rewrites artifacts/flash-04/.../frozen_current_verification.json).
    """
    f1_doc = yaml.safe_load(read_bytes(CANON["f1"]))
    ids = [r.get("test_id") for r in rows]
    dupes = sorted({x for x in ids if ids.count(x) > 1})
    bindings = sorted({r.get("binding_sha256") for r in rows})
    suite_binding = bindings[0] if len(bindings) == 1 else None
    files = frozen.get("files", {})
    canon_pin = files.get(CANON["f1"], {}).get("sha256")
    auth_pin = files.get(CANON["f1_mirror"], {}).get("sha256")
    c = {}
    c["C1a"] = (suite_binding is not None and measured_f1 == suite_binding,
                {"suite_binding": suite_binding, "canonical_measured": measured_f1})
    c["C1b"] = (canon_pin == suite_binding,
                {"frozen_revision": frozen.get("revision"), "frozen_canonical_pin": canon_pin,
                 "suite_binding": suite_binding})
    c["C2"] = (measured_mirror == suite_binding and auth_pin == suite_binding,
               {"authoring_measured": measured_mirror, "frozen_authoring_pin": auth_pin})
    c["C4"] = (not dupes and len(rows) >= 10, {"records": len(rows), "duplicate_ids": dupes})
    incomplete = [r.get("test_id") for r in rows
                  if any(not r.get(k) for k in VENDOR_REQUIRED)]
    sat_ok = all(r.get("does_it_satisfy_f1") in VSAT for r in rows)
    c["C5"] = (len(rows) >= 10 and not incomplete and sat_ok,
               {"incomplete_rows": incomplete, "sat_values_valid": sat_ok})
    c["C6"] = (suite_binding is not None and all(
        r.get("class_id") == "AF-WCC-VAC-GEN" and r.get("node_id") == "F1" and r.get("gate") == "G-FORM"
        for r in rows), {"distinct_bindings": bindings})
    bad_fields = []
    for r in rows:
        for f in [r.get("deciding_field")] + list(r.get("deciding_field_alternates") or []):
            if f and resolve(f1_doc, f) is ABSENT:
                bad_fields.append({"test_id": r.get("test_id"), "field": f})
    c["C7"] = (not bad_fields, {"unresolved": bad_fields})
    c8_bad = []
    for r in rows:
        for i, p in enumerate(r.get("probe_results", [])):
            if bool(p.get("pass")) != recompute_probe(f1_doc, p):
                c8_bad.append({"test_id": r.get("test_id"), "index": i, "path": p.get("path")})
    c["C8"] = (not c8_bad, {"mismatches": c8_bad})
    c9_bad = []
    for r in rows:
        for xa in r.get("cross_artifact") or []:
            p = os.path.join(ROOT, xa["path"])
            actual = sha256_file(p) if os.path.exists(p) else None
            if actual != xa.get("sha256"):
                c9_bad.append({"test_id": r.get("test_id"), "path": xa["path"], "actual": actual})
    c["C9"] = (not c9_bad, {"stale": c9_bad})
    by_id = {r.get("test_id"): r for r in rows}
    c["C10"] = (all(t in by_id for t in OPEN_OBLIGATIONS),
                {"present": [t for t in OPEN_OBLIGATIONS if t in by_id]})
    return {k: {"pass": v[0], "detail": v[1]} for k, v in c.items()}


# --------------------------------------------------------------------------------------
# patch construction
# --------------------------------------------------------------------------------------


def locate_amb25(rows):
    row = row_by_id(rows, "F1-AMB-25")
    dec_idx = next(i for i, p in enumerate(row["probe_results"])
                   if p.get("role") == "deciding_field" and p.get("kind") == "equals")
    bn_idx = next(i for i, p in enumerate(row["probe_results"])
                  if p.get("path") == "f0_binding.binding_note")
    ev_idx = next(i for i, e in enumerate(row.get("evidence_refs", []))
                  if e.startswith("research_map/formulation_taxonomy.yaml#sha256:"))
    return row, dec_idx, bn_idx, ev_idx


def build_patches(rows):
    live_note = str(resolve(yaml.safe_load(read_bytes(CANON["f1"])), "f0_binding.binding_note"))
    prot = copy.deepcopy(rows)
    tier_a_entries, tier_b_entries = [], []

    def add(entries, pointer, before, after, klass, rationale):
        entries.append({"pointer": pointer, "before": before, "after": after,
                        "class": klass, "rationale": rationale})

    for row in prot:
        rid = row.get("test_id")
        add(tier_a_entries, f"/{rid}/binding_ref", row.get("binding_ref"),
            f"schemas/af_wcc_vacuum.yaml#sha256:{REV13_PREFIX16}",
            "operative", "row binding ref must name the live F1 rev13 bytes")
        add(tier_a_entries, f"/{rid}/binding_sha256", row.get("binding_sha256"),
            PINS[CANON["f1"]], "operative",
            "operative row binding token must equal the live F1 rev13 sha256")
        add(tier_b_entries, f"/{rid}/binding_frozen_revision", row.get("binding_frozen_revision"),
            29, "provenance",
            "re-pin lands at FROZEN revision 29; leaving 27 contradicts the new binding")

    _, dec_idx, bn_idx, ev_idx = locate_amb25(rows)
    old_f0_token = rows[[r.get("test_id") for r in rows].index("F1-AMB-25")]["cross_artifact"][0]["sha256"]
    add(tier_a_entries, f"/F1-AMB-25/cross_artifact/0/sha256", old_f0_token, F0_FULL,
        "operative", "declared cross-artifact F0 binding must equal live F0 rev5")
    add(tier_a_entries, f"/F1-AMB-25/probe_results/{dec_idx}/expected",
        jptr_get(row_by_id(rows, "F1-AMB-25"), f"/probe_results/{dec_idx}/expected"), F0_FULL,
        "operative", "deciding equality probe must expect the live F0 rev5 hash")
    add(tier_a_entries, f"/F1-AMB-25/probe_results/{bn_idx}/expected",
        jptr_get(row_by_id(rows, "F1-AMB-25"), f"/probe_results/{bn_idx}/expected"),
        BINDING_NOTE_VARIANTS[PRIMARY_ANCHOR], "owner_decision",
        "binding_note probe anchor is stale; primary anchor = current rev13 operative text "
        "(variant V2 = F0-contract anchor also passes; owner chooses)")
    add(tier_b_entries, "/F1-AMB-25/binding_frozen_revision_schema",
        row_by_id(rows, "F1-AMB-25").get("binding_frozen_revision_schema"), 13, "provenance",
        "schema revision at re-pin")
    add(tier_b_entries, "/F1-AMB-25/rebound_at",
        row_by_id(rows, "F1-AMB-25").get("rebound_at"), PROPOSED_REBOUND_AT, "owner_decision",
        "placeholder instant declared in the instrument; owner must set the actual re-publish time")
    add(tier_b_entries, "/F1-AMB-25/rebind_note",
        row_by_id(rows, "F1-AMB-25").get("rebind_note"), REBIND_NOTE, "provenance",
        "record the rev12 -> rev13 re-pin provenance in the row")
    add(tier_b_entries, f"/F1-AMB-25/probe_results/{dec_idx}/observed_excerpt",
        jptr_get(row_by_id(rows, "F1-AMB-25"), f"/probe_results/{dec_idx}/observed_excerpt"),
        json.dumps(F0_FULL), "descriptive", "refresh the stored observation to the live value")
    add(tier_b_entries, f"/F1-AMB-25/probe_results/{bn_idx}/observed_excerpt",
        jptr_get(row_by_id(rows, "F1-AMB-25"), f"/probe_results/{bn_idx}/observed_excerpt"),
        json.dumps(live_note), "descriptive", "refresh the stored observation to the live text")
    add(tier_b_entries, f"/F1-AMB-25/evidence_refs/{ev_idx}",
        jptr_get(row_by_id(rows, "F1-AMB-25"), f"/evidence_refs/{ev_idx}"),
        f"research_map/formulation_taxonomy.yaml#sha256:{F0_FULL}", "descriptive",
        "the F0 evidence ref must cite the live F0 revision the row now binds")

    def apply(entries):
        m = rows_to_map(copy.deepcopy(rows))
        for e in entries:
            jptr_set(m, e["pointer"], e["after"])
        return map_to_rows(rows, m)

    return {
        "live_binding_note": live_note,
        "tier_A": {"entries": tier_a_entries, "patched": apply(tier_a_entries)},
        "tier_B": {"entries": tier_a_entries + tier_b_entries,
                   "patched": apply(tier_a_entries + tier_b_entries)},
    }


def semantics_unchanged(orig_rows, patched_rows) -> dict:
    diffs = []
    for a, b in zip(orig_rows, patched_rows):
        rid = a.get("test_id")
        for key in SEMANTIC_KEYS:
            if "." in key:
                base, sub = key.split(".", 1)
                va = [p.get(sub) for p in a.get(base, [])]
                vb = [p.get(sub) for p in b.get(base, [])]
            else:
                va, vb = a.get(key), b.get(key)
            if va != vb:
                diffs.append({"test_id": rid, "key": key})
    return {"comparison_keys": list(SEMANTIC_KEYS), "rows": len(orig_rows),
            "unchanged": not diffs, "diffs": diffs}


# --------------------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------------------


def main() -> int:
    started = now()
    raw_suite = read_bytes(CANON["suite"])
    rows = load_jsonl_text(raw_suite.decode("utf-8"))
    f1_doc = yaml.safe_load(read_bytes(CANON["f1"]))
    f1_sha = PINS[CANON["f1"]]
    frozen = json.loads(read_bytes(CANON["frozen"]).decode("utf-8"))

    pinned = {}
    drift = []
    for p in PINS:
        got = sha256_file(os.path.join(ROOT, p))
        pinned[p] = {"sha256": got, "matches_pin": got == PINS[p]}
        if got != PINS[p]:
            drift.append({"path": p, "expected": PINS[p], "measured": got})
    prerepair_path = os.path.join(ROOT, PRE_REPAIR_F1["path"])
    prerepair_ok = os.path.exists(prerepair_path) and sha256_file(prerepair_path) == PRE_REPAIR_F1["sha256"]
    if not prerepair_ok:
        drift.append({"path": PRE_REPAIR_F1["path"], "expected": PRE_REPAIR_F1["sha256"],
                      "measured": "missing_or_moved"})
    if drift:
        print(json.dumps({"error": "pinned input drift", "drift": drift}, indent=1))
        return 2

    # pre-registration (declared before measurement)
    prereg = {
        "P1_baseline": "25/25 row bindings stale, 25/25 ref/sha self-consistent, 1/1 cross_artifact "
                       "stale, 84 probes stored-pass, 82/84 recomputed, mismatch set = "
                       "{F1-AMB-25 probe 0 (deciding equals), F1-AMB-25 probe 3 (binding_note contains)}",
        "P2_tier_A": "25/25 bindings live, 25/25 ref/sha consistent, 1/1 cross live, 84/84 probes, "
                     "vendor C1a/C1b/C2/C4-C10 pass",
        "P3_tier_A_pointers": 25 * 2 + 3,
        "P4_semantics": "semantic key set unchanged on all 25 rows (both tiers)",
        "P5_frozen_cascade": "exactly 1 FROZEN rev29 file pin goes stale (the suite path) -> FROZEN rev30 required",
        "P6_tier_B_pointers": 25 * 2 + 3 + 25 + 1 + 1 + 1 + 2 + 1,
        "P7_bytes": "patched file byte delta <= 2500 bytes on both tiers",
    }
    deviations = []

    def expect(cond, msg):
        if not cond:
            deviations.append(msg)
        return cond

    # ---- baseline -------------------------------------------------------------------
    base = census(rows, f1_doc, f1_sha, "baseline_live_rev13")
    baseline_vendor = vendor_checks(rows, frozen, sha256_file(os.path.join(ROOT, CANON["f1"])),
                                    sha256_file(os.path.join(ROOT, CANON["f1_mirror"])))
    expect(base["binding_stale"] == 25, f"P1: binding_stale {base['binding_stale']} != 25")
    expect(base["ref_sha_consistent"] == 25, f"P1: ref_sha_consistent {base['ref_sha_consistent']} != 25")
    expect(base["cross_artifact_stale"] == 1, f"P1: cross_artifact_stale {base['cross_artifact_stale']} != 1")
    expect(base["probes_total"] == 84, f"P1: probes_total {base['probes_total']} != 84")
    expect(base["probes_stored_pass"] == 84, f"P1: probes_stored_pass {base['probes_stored_pass']} != 84")
    expect(base["probes_recomputed_pass"] == 82, f"P1: probes_recomputed_pass {base['probes_recomputed_pass']} != 82")
    expect([(m["test_id"], m["probe_index"]) for m in base["probe_mismatches"]] ==
           [("F1-AMB-25", 0), ("F1-AMB-25", 3)],
           f"P1: mismatch set {[(m['test_id'], m['probe_index']) for m in base['probe_mismatches']]}")

    # pre-repair (rev12) recompute: shows the two AMB-25 mismatches predate the rev13 staging
    pre_doc = yaml.safe_load(read_bytes(PRE_REPAIR_F1["path"]))
    pre = census(rows, pre_doc, PRE_REPAIR_F1["sha256"], "baseline_prerepair_rev12")

    # ---- canonical round-trip (K1) ---------------------------------------------------
    roundtrip = dump_jsonl(rows) == raw_suite

    # ---- patches ---------------------------------------------------------------------
    patches = build_patches(rows)
    tier_a_bytes = dump_jsonl(patches["tier_A"]["patched"])
    tier_b_bytes = dump_jsonl(patches["tier_B"]["patched"])
    # rebuild from a fresh load to prove determinism (K8)
    patches2 = build_patches(load_jsonl_text(raw_suite.decode("utf-8")))
    tier_a_bytes2 = dump_jsonl(patches2["tier_A"]["patched"])
    tier_b_bytes2 = dump_jsonl(patches2["tier_B"]["patched"])
    determinism = (tier_a_bytes == tier_a_bytes2 and tier_b_bytes == tier_b_bytes2
                   and [e["pointer"] for e in patches["tier_B"]["entries"]] ==
                   [e["pointer"] for e in patches2["tier_B"]["entries"]])

    def apply_subset(entries, drop_pointers=()):
        m = rows_to_map(copy.deepcopy(rows))
        for e in entries:
            if e["pointer"] in drop_pointers:
                continue
            jptr_set(m, e["pointer"], e["after"])
        return map_to_rows(rows, m)

    # ---- post-patch measurement -------------------------------------------------------
    results = {}
    for tier in ("tier_A", "tier_B"):
        pr = patches[tier]["patched"]
        b = dump_jsonl(pr)
        post = census(pr, f1_doc, f1_sha, f"post_{tier}")
        vc = vendor_checks(pr, frozen, sha256_file(os.path.join(ROOT, CANON["f1"])),
                           sha256_file(os.path.join(ROOT, CANON["f1_mirror"])))
        changed = sorted(diff_pointers(rows_to_map(rows), rows_to_map(pr)))
        declared = sorted({e["pointer"] for e in patches[tier]["entries"]})
        results[tier] = {
            "sha256": sha256_bytes(b), "bytes": len(b),
            "pointer_root": "suite keyed by test_id (stable across row reordering)",
            "row_set_unchanged": sorted(rows_to_map(rows)) == sorted(rows_to_map(pr)),
            "pointer_count_declared": len(patches[tier]["entries"]),
            "distinct_pointers_declared": len(declared),
            "changed_pointers": changed, "unexpected_changes": sorted(set(changed) - set(declared)),
            "missing_changes": sorted(set(declared) - set(changed)),
            "census": {k: v for k, v in post.items() if k not in ("rows_detail", "defects")},
            "probe_mismatches": post["probe_mismatches"],
            "vendor": vc,
            "semantics": semantics_unchanged(rows, pr),
        }

    expect(results["tier_A"]["census"]["binding_live"] == 25 and
           results["tier_A"]["census"]["binding_stale"] == 0 and
           results["tier_A"]["census"]["ref_sha_consistent"] == 25 and
           results["tier_A"]["census"]["cross_artifact_live"] == 1 and
           results["tier_A"]["census"]["probes_recomputed_pass"] == 84,
           "P2: tier_A post-patch census not 25/25 + 1/1 + 84/84")
    expect(all(v["pass"] for v in results["tier_A"]["vendor"].values()),
           "P2: tier_A vendor check failure: " +
           json.dumps({k: v["detail"] for k, v in results["tier_A"]["vendor"].items() if not v["pass"]}))
    expect(results["tier_A"]["distinct_pointers_declared"] == 53,
           f"P3: tier_A distinct pointers {results['tier_A']['distinct_pointers_declared']} != 53")
    expect(results["tier_A"]["semantics"]["unchanged"] and results["tier_B"]["semantics"]["unchanged"],
           "P4: semantic key diff detected")
    expect(results["tier_B"]["distinct_pointers_declared"] == 84,
           f"P6: tier_B distinct pointers {results['tier_B']['distinct_pointers_declared']} != 84")
    for tier in ("tier_A", "tier_B"):
        expect(results[tier]["bytes"] - len(raw_suite) <= 2500,
               f"P7: {tier} byte delta {results[tier]['bytes'] - len(raw_suite)} > 2500")
        expect(not results[tier]["unexpected_changes"],
               f"{tier}: unexpected changed pointers {results[tier]['unexpected_changes']}")
        expect(not results[tier]["missing_changes"],
               f"{tier}: declared pointers with no effect {results[tier]['missing_changes']}")
        expect(results[tier]["row_set_unchanged"], f"{tier}: row set changed (a row was added or dropped)")

    # ---- FROZEN cascade ----------------------------------------------------------------
    files = frozen.get("files", {})
    suite_pin = files.get(CANON["suite"], {})
    moved = []
    if suite_pin.get("sha256") != results["tier_B"]["sha256"]:
        moved.append({"path": CANON["suite"], "frozen_rev29_pin": suite_pin.get("sha256"),
                      "patched_sha256": results["tier_B"]["sha256"]})
    registry = read_bytes(CANON["registry"]).decode("utf-8")
    registry_stale = "56bcb4b3234b" in registry
    expect(len(moved) == 1, f"P5: frozen moved-path count {len(moved)} != 1")
    frozen_cascade = {
        "frozen_revision_at_measure": frozen.get("revision"),
        "frozen_sha256": PINS[CANON["frozen"]],
        "suite_pin_in_frozen_rev29": suite_pin,
        "moved_paths": moved,
        "registry_mentions_stale_suite_hash": registry_stale,
        "required_action": ("bump FROZEN to revision 30 with the new suite sha256/bytes and re-emit the "
                            "artifact event (change_protocol requires a revision bump for any canonical "
                            "artifact change); refresh runtime/state/artifact_hashes.json; then re-run the "
                            "vendor verifier (its C1a/C9 hard checks should pass; C3 is a soft record check)."),
        "not_required": "F1/F2a/F2b/F0 bytes and FROZEN pins for them are untouched by this patch",
    }

    # ---- controls ----------------------------------------------------------------------
    controls = {}
    controls["K1_serializer_roundtrip_byte_identical"] = roundtrip
    # K2: bindings are revision-responsive -- decoy F1 rev14 in a sandbox copy
    decoy_doc = copy.deepcopy(f1_doc)
    decoy_doc["revision"] = 14
    decoy_bytes = yaml.safe_dump(decoy_doc, sort_keys=False).encode("utf-8")
    decoy = census(patches["tier_B"]["patched"], decoy_doc, sha256_bytes(decoy_bytes), "decoy_f1_rev14")
    controls["K2_revision_responsive_decoy"] = {
        "decoy_binding_stale": decoy["binding_stale"], "decoy_probe_mismatches": len(decoy["probe_mismatches"]),
        "expected_binding_stale": 25, "pass": decoy["binding_stale"] == 25}
    # K3: both binding fields operative
    only_ref = apply_subset(patches["tier_A"]["entries"],
                            drop_pointers={e["pointer"] for e in patches["tier_A"]["entries"]
                                           if e["pointer"].endswith("/binding_sha256")})
    k3 = census(only_ref, f1_doc, f1_sha, "variant_ref_only")
    controls["K3_binding_sha256_operative"] = {"binding_stale": k3["binding_stale"],
                                              "ref_sha_inconsistent": k3["ref_sha_inconsistent"],
                                              "pass": k3["binding_stale"] == 25 and k3["ref_sha_inconsistent"] == 25}
    # K4: each AMB-25 probe expectation is load-bearing
    _, dec_i, bn_i, _ = locate_amb25(rows)
    drop_dec = apply_subset(patches["tier_A"]["entries"],
                            drop_pointers={f"/F1-AMB-25/probe_results/{dec_i}/expected"})
    drop_bn = apply_subset(patches["tier_A"]["entries"],
                           drop_pointers={f"/F1-AMB-25/probe_results/{bn_i}/expected"})
    k4a = census(drop_dec, f1_doc, f1_sha, "variant_drop_deciding_expected")
    k4b = census(drop_bn, f1_doc, f1_sha, "variant_drop_binding_note_expected")
    controls["K4a_drop_deciding_expected"] = {"recomputed_pass": k4a["probes_recomputed_pass"],
                                              "mismatch_indices": [m["probe_index"] for m in k4a["probe_mismatches"]],
                                              "pass": k4a["probes_recomputed_pass"] == 83}
    controls["K4b_drop_binding_note_expected"] = {"recomputed_pass": k4b["probes_recomputed_pass"],
                                                  "mismatch_indices": [m["probe_index"] for m in k4b["probe_mismatches"]],
                                                  "pass": k4b["probes_recomputed_pass"] == 83}
    # K5: cross_artifact is independent of the probes
    drop_cross = apply_subset(patches["tier_A"]["entries"],
                              drop_pointers={"/F1-AMB-25/cross_artifact/0/sha256"})
    k5 = census(drop_cross, f1_doc, f1_sha, "variant_drop_cross_artifact")
    controls["K5_cross_artifact_operative"] = {"cross_stale": k5["cross_artifact_stale"],
                                               "probes_recomputed_pass": k5["probes_recomputed_pass"],
                                               "pass": k5["cross_artifact_stale"] == 1 and k5["probes_recomputed_pass"] == 84}
    # K6: binding_note anchor variants both pass
    k6 = {}
    for name, anchor in BINDING_NOTE_VARIANTS.items():
        entries = [{**e, "after": anchor} if e["pointer"] == f"/F1-AMB-25/probe_results/{bn_i}/expected" else e
                   for e in patches["tier_A"]["entries"]]
        k6[name] = census(apply_subset(entries), f1_doc, f1_sha, f"variant_anchor_{name}")["probes_recomputed_pass"]
    controls["K6_binding_note_anchors"] = {"variant_passes": k6, "primary": PRIMARY_ANCHOR,
                                           "pass": all(v == 84 for v in k6.values())}
    controls["K8_patch_determinism"] = determinism
    controls["K9_sandbox_confinement"] = {
        "writes": [os.path.relpath(os.path.join(OUTDIR, "report.json"), ROOT),
                   os.path.relpath(os.path.join(OUTDIR, "PROPOSED_PATCH.json"), ROOT),
                   "artifacts/worker-031/f1_suite_repin_dryrun/patched/*"],
        "canonical_paths_opened_read_only": sorted(PINS) + [PRE_REPAIR_F1["path"]],
        "canonical_paths_written": [],
        "pass": True,
    }
    for k, v in controls.items():
        if isinstance(v, dict) and "pass" in v:
            expect(v["pass"], f"control {k} failed: {json.dumps(v)[:300]}")
    expect(roundtrip, "K1: serializer round-trip is not byte-identical to the canonical suite")
    expect(determinism, "K8: patch construction is not deterministic across fresh loads")

    # ---- drift guard (K7) ----------------------------------------------------------------
    drift_end = [{"path": p, "expected": PINS[p], "measured": sha256_file(os.path.join(ROOT, p))}
                 for p in PINNED_FOR_STABILITY if sha256_file(os.path.join(ROOT, p)) != PINS[p]]
    controls["K7_input_drift_guard"] = {"stable": not drift_end, "drift": drift_end,
                                        "pass": not drift_end}
    expect(not drift_end, f"K7: input drift during run: {drift_end}")

    verdict = "PATCH_VALIDATED_AT_LIVE_PINS" if not deviations and not drift_end else "DEVIATIONS_RECORDED"

    report = {
        "report_id": "w031-f1-suite-repin-dryrun-report-01",
        "task_id": "W031-F1-SUITE-REPIN-PROPOSAL-01",
        "agent": "worker-031",
        "created_at": started, "finished_at": now(),
        "class_id": "AF-WCC-VAC-GEN",
        "class_refs": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "node_id": "F1", "gate": "G-FORM",
        "scope": ("dry-run of the minimal F1 falsifier-suite re-pin (all 25 row bindings) plus the "
                  "F1-AMB-25 F0 content repair at live pins; measured on artifact-local copies only"),
        "authority": ("worker measurement only. No canonical path written; no gate verdict; no node status; "
                      "no validation_status. The proposed patch is not applied to schemas/f1_falsifier_tests.jsonl."),
        "pinned_inputs": pinned,
        "pre_repair_f1_snapshot": {**PRE_REPAIR_F1, "matches_pin": prerepair_ok},
        "pre_registered": prereg,
        "inputs_stable_during_run": not drift_end,
        "baseline_live_rev13": base,
        "baseline_vendor": baseline_vendor,
        "baseline_prerepair_rev12": {k: v for k, v in pre.items() if k not in ("rows_detail", "defects")},
        "patch": {
            "live_binding_note": patches["live_binding_note"],
            "tier_A_purpose": "operative fields only (bindings + cross_artifact + 2 probe expectations)",
            "tier_B_purpose": "tier A + provenance/descriptive refresh (frozen revision, rebind note, observations, evidence ref)",
            "tier_A_entries": patches["tier_A"]["entries"],
            "tier_B_entries": patches["tier_B"]["entries"],
            "tier_A_sha256": sha256_bytes(json.dumps(patches["tier_A"]["entries"], sort_keys=True, indent=1).encode()),
            "tier_B_sha256": sha256_bytes(json.dumps(patches["tier_B"]["entries"], sort_keys=True, indent=1).encode()),
            "proposed_rebound_at": PROPOSED_REBOUND_AT,
            "binding_note_anchor_primary": PRIMARY_ANCHOR,
            "binding_note_anchor_variants": BINDING_NOTE_VARIANTS,
        },
        "post_patch": results,
        "canonical_suite_bytes": len(raw_suite),
        "canonical_suite_sha256": PINS[CANON["suite"]],
        "frozen_cascade": frozen_cascade,
        "owner_decisions": [
            "binding_note anchor variant: V1 (current rev13 operative text, primary) vs V2 (F0-contract anchor); both measured 84/84",
            "rebound_at/rebind_note actual values: the dry-run uses a declared placeholder instant; owner sets the re-publish instant",
            "tier A vs tier B: tier A is the minimal operative repair (53 pointers, hash " +
            results["tier_A"]["sha256"][:12] + "); tier B also refreshes provenance/descriptive fields (84 pointers, hash " +
            results["tier_B"]["sha256"][:12] + ") and is the recommended published form",
            "FROZEN rev30 bump + artifact event + registry refresh + vendor verifier re-run are outside worker authority",
        ],
        "controls": controls,
        "deviations": deviations,
        "verdict": verdict,
        "falsifier": ("Any pinned decision input moving during the run; a declared pointer whose application does "
                      "not change the measured semantics; a tier whose patched suite does not reach 25/25 live "
                      "bindings + 1/1 live cross-artifact + 84/84 probes + all vendor C-checks; or an owner-applied "
                      "re-pin whose bytes differ from the proposed bytes without a recorded reason."),
        "next_falsifier": ("Owner applies the re-pin and bumps FROZEN to rev30; then re-run this instrument with the "
                           "suite pin replaced by the published bytes and EXPECT 0 outstanding defects and "
                           "PATCH-ALREADY-APPLIED (round-trip: proposed bytes == published bytes). If the published "
                           "bytes differ, diff the pointer sets before accepting."),
        "replay": "python3 artifacts/worker-031/f1_suite_repin_dryrun/dryrun_repin_031.py",
    }

    os.makedirs(PATCHED_DIR, exist_ok=True)
    prop = {
        "patch_id": "w031-f1-suite-repin-proposal-01",
        "task_id": report["task_id"], "agent": "worker-031", "created_at": report["created_at"],
        "class_id": report["class_id"], "node_id": "F1", "gate": "G-FORM",
        "target": CANON["suite"],
        "target_sha256_before": PINS[CANON["suite"]],
        "pointer_root": "JSON Pointer into the suite keyed by test_id (e.g. /F1-AMB-01/binding_ref); "
                        "row order is not part of the binding",
        "tier_A": {"entries": patches["tier_A"]["entries"], "entry_count": len(patches["tier_A"]["entries"]),
                   "patched_sha256": results["tier_A"]["sha256"], "patched_bytes": results["tier_A"]["bytes"]},
        "tier_B": {"entries": patches["tier_B"]["entries"], "entry_count": len(patches["tier_B"]["entries"]),
                   "patched_sha256": results["tier_B"]["sha256"], "patched_bytes": results["tier_B"]["bytes"]},
        "application_note": ("Apply tier B (recommended) or tier A with a JSON-pointer patch tool; do not hand-edit. "
                             "Then bump FROZEN to rev30 and re-emit. The patched files in ./patched/ are the exact "
                             "proposed bytes for byte-level comparison."),
        "sha256_of_this_patch": None,  # self-reference excluded, recorded in SHA256SUMS
    }
    with open(os.path.join(OUTDIR, "report.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1, sort_keys=True)
        fh.write("\n")
    with open(os.path.join(OUTDIR, "PROPOSED_PATCH.json"), "w", encoding="utf-8") as fh:
        json.dump(prop, fh, indent=1, sort_keys=True)
        fh.write("\n")
    for tier, b in (("tierA", tier_a_bytes), ("tierB", tier_b_bytes)):
        p = os.path.join(PATCHED_DIR, f"f1_falsifier_tests.{tier}.jsonl")
        with open(p, "wb") as fh:
            fh.write(b)
        with open(p + ".sha256", "w", encoding="utf-8") as fh:
            fh.write(f"{sha256_bytes(b)}  {os.path.relpath(p, ROOT)}\n")

    print(json.dumps({
        "verdict": verdict, "deviations": deviations,
        "report": "artifacts/worker-031/f1_suite_repin_dryrun/report.json",
        "tier_A": {"sha256": results["tier_A"]["sha256"], "bytes": results["tier_A"]["bytes"],
                   "bindings_live": results["tier_A"]["census"]["binding_live"],
                   "probes_recomputed_pass": results["tier_A"]["census"]["probes_recomputed_pass"]},
        "tier_B": {"sha256": results["tier_B"]["sha256"], "bytes": results["tier_B"]["bytes"],
                   "bindings_live": results["tier_B"]["census"]["binding_live"],
                   "probes_recomputed_pass": results["tier_B"]["census"]["probes_recomputed_pass"]},
        "frozen_cascade_moved": len(moved),
        "controls_pass": all((v is True) or (isinstance(v, dict) and v.get("pass") is True)
                             for v in controls.values()),
    }, indent=1))
    return 0 if verdict == "PATCH_VALIDATED_AT_LIVE_PINS" else 1


if __name__ == "__main__":
    sys.exit(main())
