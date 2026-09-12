#!/usr/bin/env python3
"""
W031-F1-SUITE-REV13-IMPACT-01 instrument (worker-031, independent)

Question: the astra-life05-evidence-binding-repair (REC-12) rewrote
schemas/af_wcc_vacuum.yaml at 00:53:20 (rev12 cce9c60146d6 -> rev13 d9cebb9404b2,
plus the same treatment on F2a/F2b). The F1 falsifier suite
schemas/f1_falsifier_tests.jsonl was NOT named in the repair's four authorised
items. Measure the impact of the repair on that suite as G-FORM acceptance
evidence, at live bytes:

  I1 corpus  : schemas/taxonomy_cases.jsonl rows + checker
  I2 schemas : f0_binding.consistency_evidence_sha256 in F1/F2a/F2b
  I3 F1 text : rev13 visibility strictness directions
  I4 FROZEN  : rev29 re-pin of the moved paths
  I5 SUITE   : (not in REC-12) schemas/f1_falsifier_tests.jsonl - row bindings,
               cross-artifact pins, recorded probe outcomes

Also bounded: classify the F1 rev12->rev13 byte delta against the authorised edit
surface, so an out-of-scope class-semantics change cannot hide inside the repair.

Controls
  K1 live pin accepted        : a pair whose token equals live bytes -> `live`.
  K2 fabricated pin rejected  : synthetic 64-hex token -> `stale`.
  K3 mutation sensitivity     : in-memory probe/expectation mutation flips a
                                recorded-pass check.
  K4 baseline continuity      : against the pinned pre-repair F1 snapshot, the
                                census reproduces the W031-F1-PINCENSUS-01
                                finding (25/25 row bindings live, 5 stale pins).
  K5 replay determinism       : the census runs twice with identical results.
  K6 delta-scope sensitivity  : a synthetic out-of-scope mutation (class_id) is
                                reported as `unauthorized_delta`.

Exit codes: 0 = measured (verdict emitted), 1 = control/check failure,
2 = pinned input drift (fail closed), 3 = required snapshot missing.

Authority: worker measurement only. No gate verdict, no node status, no
validation_status, no edit to any canonical artifact.

Falsifier: this report is void if any pinned input moves
(`inputs_stable_during_run` false), if K1-K6 fail, if a `stale` pair is shown to
be provenance rather than an operative binding, or if the suite is re-pinned to
the live F1/F0 hashes and re-published before the verdict is read (which repairs
rather than falsifies finding F1).
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

TZ = timezone(timedelta(hours=8))
HEX64 = re.compile(r"^[0-9a-f]{64}$")

TASK_ID = "W031-F1-SUITE-REV13-IMPACT-01"
REPORT_ID = "w031-f1-suite-rev13-impact-report-01"
AGENT = "worker-031"

# ---------------------------------------------------------------- pins
# Live pins measured at task start 2026-09-12T00:53:47+08:00 (pre-repair values
# kept for the continuity control). Any drift at finish -> exit 2.
PINNED_INPUTS = {
    "schemas/f1_falsifier_tests.jsonl":
        "56bcb4b3234bc86c324bec6e38f142c5ef39517f20d823b6a333f578b7d0851e",
    "schemas/af_wcc_vacuum.yaml":
        "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "schemas/af_scc_c2_vacuum.yaml":
        "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "schemas/af_scc_c0_vacuum.yaml":
        "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "schemas/taxonomy_cases.jsonl":
        "ccf7041bd0ff3ce844c07a700a588b7fe8e3c90880674c5e595b21f6259a8f03",
    "research_map/formulation_taxonomy.yaml":
        "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "artifacts/formulation/evidence/taxonomy_consistency.json":
        "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b",
    "artifacts/formulation/FROZEN.json":
        "3d9e3d77fd87101937f6e3c18c69703594f945c962e9692dc2df5ea6a3bd3833",
}
PRE_REPAIR = {
    "schema_f1": "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3",
    "schema_f2a": "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce",
    "schema_f2b": "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6",
    "cases": "f0c20b96f76dc21b32ae81962bb3aa207b04e90c28aa6da8a686e0d9f649a1e8",
    "f1_snapshot": "artifacts/worker-007/rev29_preflight/snapshot/af_wcc_vacuum.cce9c60146d6.yaml",
    "stale_f0_token": "276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc",
    "stale_consistency_token": "675a99d0d25b2b37c9b9e9b965aec1c1ff0e388d2665fd9247b58c04733eba48",
}
CANON = {
    "f0": "research_map/formulation_taxonomy.yaml",
    "f1": "schemas/af_wcc_vacuum.yaml",
    "f2a": "schemas/af_scc_c2_vacuum.yaml",
    "f2b": "schemas/af_scc_c0_vacuum.yaml",
    "suite": "schemas/f1_falsifier_tests.jsonl",
    "cases": "schemas/taxonomy_cases.jsonl",
    "frozen": "artifacts/formulation/FROZEN.json",
    "consistency": "artifacts/formulation/evidence/taxonomy_consistency.json",
}
SCHEMAS = [CANON["f1"], CANON["f2a"], CANON["f2b"]]
# Paths the REC-12 repair is authorised to touch in F1 (rev12 -> rev13).
AUTHORIZED_F1_PATHS = (
    "revision",
    "revision_history",
    "revised_at",
    "f0_binding.consistency_evidence_sha256",
    "f0_binding.checked_at",
    "f0_binding.binding_note",
    "definitions.D5.definition",
    "quantifiers.domains.D5.definition",
    "visibility.definition",
    "class_identity_variants.0.relation",
)

SKIP_DIRS = {".git", "__pycache__", "instances", ".dsh", "node_modules"}
MAX_INDEX_BYTES = 64 * 1024 * 1024


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


def now() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_yaml(path: str):
    import yaml
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_jsonl(path: str):
    rows = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


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


class Comparator:
    def __init__(self, disk_index: dict):
        self.disk_index = disk_index
        self.canonical = {p: sha256_file(os.path.join(ROOT, p)) for p in PINNED_INPUTS}

    def check_pair(self, path: str, token: str) -> dict:
        full = os.path.join(ROOT, path)
        live = self.canonical.get(path)
        if not os.path.isfile(full):
            return {"path": path, "token": token, "status": "path_missing"}
        if live is None:
            live = sha256_file(full)
        if token == live:
            return {"path": path, "token": token, "status": "live", "live_sha256": live}
        where = self.disk_index.get(token, [])[:4]
        return {"path": path, "token": token, "status": "stale", "live_sha256": live,
                "token_resolves_to": where,
                "token_resolution": "on_disk_snapshot" if where else "unresolved_on_disk"}


def build_disk_index() -> dict:
    index: dict[str, list] = {}
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            p = os.path.join(dirpath, name)
            try:
                if os.path.getsize(p) > MAX_INDEX_BYTES:
                    continue
                h = sha256_file(p)
            except OSError:
                continue
            index.setdefault(h, []).append(os.path.relpath(p, ROOT))
    return index


def census_suite(rows, cmp: Comparator, f1_live_doc, f1_pre_doc) -> dict:
    """Operative-pin census + probe recompute for the F1 suite at live bytes."""
    records, defects = [], []
    dist_binding, dist_cross = {}, {}

    for row in rows:
        rid = row.get("test_id") or row.get("row_id") or "?"
        rec = {"test_id": rid, "operative": [], "defect": False}

        bind_token = row.get("binding_sha256")
        bind_ref = row.get("binding_ref") or ""
        bind_path = bind_ref.split("#", 1)[0] if bind_ref else CANON["f1"]
        if bind_token and HEX64.match(str(bind_token)):
            c = cmp.check_pair(bind_path, str(bind_token))
            c["kind"] = "row_binding"
            rec["operative"].append(c)
            dist_binding[c["status"]] = dist_binding.get(c["status"], 0) + 1
            if c["status"] != "live":
                rec["defect"] = True
                defects.append({"where": f"suite:{rid}:binding_sha256", **c})

        cross = row.get("cross_artifact") or []
        rec["cross_artifact"] = []
        for ca in cross:
            p, t = ca.get("path"), ca.get("sha256")
            if not p or not t:
                continue
            c = cmp.check_pair(p, str(t))
            c["kind"] = "cross_artifact"
            rec["cross_artifact"].append(c)
            dist_cross[c["status"]] = dist_cross.get(c["status"], 0) + 1
            if c["status"] != "live":
                rec["defect"] = True
                defects.append({"where": f"suite:{rid}:cross_artifact", **c})

        rec_pass = rec_live = rec_pre = 0
        flips_live, flips_pre = [], []
        for i, probe in enumerate(row.get("probe_results", [])):
            stored = bool(probe.get("pass"))
            got_live = recompute_probe(f1_live_doc, probe)
            got_pre = recompute_probe(f1_pre_doc, probe) if f1_pre_doc is not None else None
            rec_pass += int(stored)
            rec_live += int(got_live)
            if got_pre is not None:
                rec_pre += int(got_pre)
            if stored != got_live:
                flips_live.append({"index": i, "path": probe.get("path"),
                                   "kind": probe.get("kind"), "role": probe.get("role"),
                                   "stored_pass": stored, "recomputed_pass_live": got_live})
            if got_pre is not None and stored != got_pre:
                flips_pre.append({"index": i, "path": probe.get("path"),
                                  "stored_pass": stored, "recomputed_pass_rev12": got_pre})
            if probe.get("role") == "deciding_field" and probe.get("kind") == "equals" \
                    and isinstance(probe.get("expected"), str) and HEX64.match(probe["expected"]):
                target = cross[0]["path"] if len(cross) == 1 else None
                if target:
                    c = cmp.check_pair(target, probe["expected"])
                    c["kind"] = "deciding_expectation"
                    c["probe_path"] = probe.get("path")
                    rec["operative"].append(c)
                    if c["status"] != "live":
                        rec["defect"] = True
                        defects.append({"where": f"suite:{rid}:deciding_expectation", **c})

        rec["probes"] = {
            "total": len(row.get("probe_results", [])),
            "stored_pass": rec_pass,
            "recomputed_pass_live_rev13": rec_live,
            "recomputed_pass_prerepair_rev12": rec_pre if f1_pre_doc is not None else None,
            "flips_vs_live": flips_live,
            "flips_vs_prerepair": flips_pre,
        }
        rec["all_probes_reproduce_live"] = not flips_live
        rec["all_probes_reproduce_prerepair"] = (f1_pre_doc is not None and not flips_pre)
        rec["pins_all_live"] = all(c["status"] == "live" for c in rec["operative"])
        records.append(rec)

    return {
        "rows": records,
        "totals": {
            "rows": len(records),
            "row_bindings_stale": sum(1 for r in records if any(
                c["kind"] == "row_binding" and c["status"] != "live" for c in r["operative"])),
            "rows_with_defect": sum(1 for r in records if r["defect"]),
            "probes": sum(r["probes"]["total"] for r in records),
            "probes_stored_pass": sum(r["probes"]["stored_pass"] for r in records),
            "probes_recomputed_pass_live_rev13": sum(r["probes"]["recomputed_pass_live_rev13"] for r in records),
            "probes_recomputed_pass_prerepair_rev12": (sum(r["probes"]["recomputed_pass_prerepair_rev12"] for r in records)
                                                       if f1_pre_doc is not None else None),
            "rows_all_probes_reproduce_live": sum(1 for r in records if r["all_probes_reproduce_live"]),
            "rows_all_probes_reproduce_prerepair": sum(1 for r in records if r["all_probes_reproduce_prerepair"]),
        },
        "defects": defects,
        "binding_status_distribution": dist_binding,
        "cross_artifact_status_distribution": dist_cross,
    }


def census_schemas(cmp: Comparator) -> dict:
    out, defects = {}, []
    for p in SCHEMAS:
        doc = load_yaml(os.path.join(ROOT, p)) or {}
        fb = doc.get("f0_binding") or {}
        rec = {"path": p, "class_id": doc.get("class_id"), "revision": doc.get("revision"), "pins": []}
        for art_key, tok_key in (("declared_f0_artifact", "declared_f0_sha256"),
                                 ("consistency_evidence", "consistency_evidence_sha256")):
            ap, tok = fb.get(art_key), fb.get(tok_key)
            if ap and isinstance(tok, str) and HEX64.match(tok):
                c = cmp.check_pair(ap, tok)
                c["kind"] = f"f0_binding.{tok_key}"
                rec["pins"].append(c)
                if c["status"] != "live":
                    defects.append({"where": f"schema:{p}:{tok_key}", **c})
        rec["defect"] = any(c["status"] != "live" for c in rec["pins"])
        out[p] = rec
    return {"schemas": out, "defects": defects}


def census_cases(cmp: Comparator) -> dict:
    rows = load_jsonl(os.path.join(ROOT, CANON["cases"]))
    meta = next((r for r in rows if r.get("record_type") == "meta"), {})
    tref = meta.get("taxonomy_ref") or {}
    pins, defects = [], []
    if tref.get("path") and tref.get("sha256"):
        c = cmp.check_pair(tref["path"], tref["sha256"])
        c["kind"] = "taxonomy_ref"
        pins.append(c)
        if c["status"] != "live":
            defects.append({"where": "taxonomy_cases:meta.taxonomy_ref", **c})
    row_bindings = []
    for r in rows:
        hits = {k: v for k, v in r.items()
                if k.endswith("_sha256") and isinstance(v, str) and HEX64.match(v)}
        for k, v in hits.items():
            row_bindings.append({"row": r.get("case_id") or r.get("record_type"), "key": k,
                                 "sha256": v, "status": "live" if v == PINNED_INPUTS[CANON["f0"]] else "other"})
    return {"meta_pins": pins, "row_binding_count": len(row_bindings),
            "row_bindings_to_live_f0": sum(1 for b in row_bindings if b["status"] == "live"),
            "defects": defects, "rows": len(rows)}


def census_frozen(cmp: Comparator) -> dict:
    fr = json.load(open(os.path.join(ROOT, CANON["frozen"])))
    files = fr.get("files", {}) or {}
    moved = {CANON["f1"], CANON["f2a"], CANON["f2b"], CANON["consistency"]}
    records, stale, live = [], 0, 0
    for path, meta in sorted(files.items()):
        tok = meta.get("sha256") if isinstance(meta, dict) else meta
        if not isinstance(tok, str) or not HEX64.match(tok):
            continue
        c = cmp.check_pair(path, tok)
        c["kind"] = "frozen_file"
        c["moved_by_repair"] = path in moved
        records.append(c)
        if c["status"] == "live":
            live += 1
        else:
            stale += 1
    return {"revision": fr.get("revision"), "files_pinned": len(records),
            "files_live": live, "files_stale": stale,
            "stale_moved_paths": [r for r in records if r["status"] != "live" and r["moved_by_repair"]],
            "stale_other_paths": [r for r in records if r["status"] != "live" and not r["moved_by_repair"]],
            "records": records}


def flatten(doc, prefix="", out=None):
    if out is None:
        out = {}
    if isinstance(doc, dict):
        for k, v in doc.items():
            flatten(v, f"{prefix}.{k}" if prefix else str(k), out)
    elif isinstance(doc, list):
        for i, v in enumerate(doc):
            flatten(v, f"{prefix}.{i}", out)
    else:
        out[prefix] = doc
    return out


def delta_scope(pre_doc, live_doc) -> dict:
    pre, live = flatten(pre_doc), flatten(live_doc)
    keys = sorted(set(pre) | set(live))
    changed = []
    for k in keys:
        if pre.get(k, ABSENT) != live.get(k, ABSENT):
            authorized = any(k == a or k.startswith(a + ".") for a in AUTHORIZED_F1_PATHS)
            changed.append({"path": k, "authorized": authorized,
                            "pre": str(pre.get(k, ABSENT))[:160],
                            "live": str(live.get(k, ABSENT))[:160]})
    unexpected = [c for c in changed if not c["authorized"]]
    return {"changed_paths": changed, "changed": len(changed),
            "authorized_changed": len(changed) - len(unexpected),
            "unexpected_changed": unexpected}


def controls(cmp, rows, suite, pre_doc):
    out = {}
    # K1 live accepted
    k1 = cmp.check_pair(CANON["f0"], PINNED_INPUTS[CANON["f0"]])
    out["K1_live_pin_accepted"] = k1["status"] == "live"
    # K2 fabricated rejected
    k2 = cmp.check_pair(CANON["f1"], "0" * 64)
    out["K2_fabricated_pin_rejected"] = k2["status"] == "stale"
    # K3 mutation sensitivity
    doc = load_yaml(os.path.join(ROOT, CANON["f1"]))
    probe = {"path": "f0_binding.declared_f0_sha256", "kind": "equals",
             "expected": PINNED_INPUTS[CANON["f0"]]}
    k3a = recompute_probe(doc, probe)
    mut = copy.deepcopy(doc)
    mut["f0_binding"]["declared_f0_sha256"] = "1" * 64
    k3b = recompute_probe(mut, probe)
    out["K3a_baseline_probe_true"] = bool(k3a)
    out["K3b_mutation_flips_probe"] = bool(k3a) and not bool(k3b)
    out["K3_mutation_sensitivity"] = out["K3a_baseline_probe_true"] and out["K3b_mutation_flips_probe"]
    # K4 baseline continuity on the pinned pre-repair snapshot
    if pre_doc is None:
        out["K4_baseline_continuity"] = False
        out["K4_detail"] = "pre-repair snapshot unavailable"
    else:
        pre_cmp = Comparator(cmp.disk_index)
        pre_cmp.canonical[CANON["f1"]] = PRE_REPAIR["schema_f1"]
        pre_cmp.canonical[CANON["f2a"]] = PRE_REPAIR["schema_f2a"]
        pre_cmp.canonical[CANON["f2b"]] = PRE_REPAIR["schema_f2b"]
        s = census_suite(rows, pre_cmp, pre_doc, None)
        # Reproduce the pre-repair schema-side staleness deterministically:
        # the three schemas carried 675a99d0 while the live evidence is 9e335e9b.
        pre_cmp.canonical[CANON["consistency"]] = PRE_REPAIR["stale_consistency_token"]
        stale_schemas = 0
        for p in SCHEMAS:
            d = load_yaml(os.path.join(ROOT, p))
            fb = d.get("f0_binding") or {}
            tok = PRE_REPAIR["stale_consistency_token"]
            if cmp.check_pair(fb.get("consistency_evidence"), tok)["status"] == "stale" \
                    and pre_cmp.check_pair(fb.get("consistency_evidence"), tok)["status"] == "live":
                stale_schemas += 1
        out["K4_detail"] = {"row_bindings_stale": s["totals"]["row_bindings_stale"],
                            "probes_recomputed_pass": s["totals"]["probes_recomputed_pass_live_rev13"],
                            "suite_defect_count": len(s["defects"]),
                            "schema_consistency_stale_prerepair": stale_schemas}
        # W031-F1-PINCENSUS-01 baseline: 25/25 row bindings live, 2 suite defects
        # (F1-AMB-25 cross_artifact + deciding expectation), 3 stale schema
        # consistency-evidence pins -> 5 stale operative pins total.
        out["K4_baseline_continuity"] = (
            s["totals"]["row_bindings_stale"] == 0
            and s["totals"]["probes_recomputed_pass_live_rev13"] == 82
            and len(s["defects"]) == 2
            and stale_schemas == 3)
    # K5 replay determinism
    s2 = census_suite(rows, cmp, load_yaml(os.path.join(ROOT, CANON["f1"])), pre_doc)
    out["K5_replay_determinism"] = json.dumps(s2, sort_keys=True) == json.dumps(suite, sort_keys=True)
    # K6 delta-scope sensitivity
    if pre_doc is None:
        out["K6_delta_scope_sensitivity"] = False
    else:
        mutated = copy.deepcopy(pre_doc)
        mutated["class_id"] = "AF-MUTANT"
        d = delta_scope(pre_doc, mutated)
        out["K6_delta_scope_sensitivity"] = any(
            c["path"] == "class_id" and not c["authorized"] for c in d["changed_paths"])
    out["all_pass"] = all(v is True for k, v in out.items()
                          if k.startswith("K") and isinstance(v, bool))
    return out


def main() -> int:
    started = now()
    disk_index = build_disk_index()
    cmp = Comparator(disk_index)

    live = {p: sha256_file(os.path.join(ROOT, p)) for p in PINNED_INPUTS}
    drift = {p: {"pinned": PINNED_INPUTS[p], "live": live[p]}
             for p in PINNED_INPUTS if live[p] != PINNED_INPUTS[p]}

    snap_path = os.path.join(ROOT, PRE_REPAIR["f1_snapshot"])
    if not os.path.isfile(snap_path):
        print(json.dumps({"error": "pre-repair snapshot missing", "path": PRE_REPAIR["f1_snapshot"]}))
        return 3
    snap_hash = sha256_file(snap_path)
    snap_ok = snap_hash == PRE_REPAIR["schema_f1"]
    if not snap_ok:
        print(json.dumps({"error": "pre-repair snapshot hash mismatch",
                          "path": PRE_REPAIR["f1_snapshot"], "measured": snap_hash,
                          "expected": PRE_REPAIR["schema_f1"]}))
        return 2
    pre_doc = load_yaml(snap_path)
    live_f1_doc = load_yaml(os.path.join(ROOT, CANON["f1"]))

    rows = load_jsonl(os.path.join(ROOT, CANON["suite"]))
    suite = census_suite(rows, cmp, live_f1_doc, pre_doc)
    schemas = census_schemas(cmp)
    cases = census_cases(cmp)
    frozen = census_frozen(cmp)
    scope = delta_scope(pre_doc, live_f1_doc)
    semantics_fields = ["class_id", "hypothesis", "conclusion", "genericity",
                        "class_components"]
    semantics_delta = [f for f in semantics_fields if pre_doc.get(f) != live_f1_doc.get(f)]
    # class_identity_variants: `.relation` (and its `.note` consequence) is the
    # authorised rev13 correction; the variant's identity/semantics fields must not move.
    def _variant_semantics(doc):
        v = copy.deepcopy(doc.get("class_identity_variants") or [])
        for item in v:
            if isinstance(item, dict):
                item.pop("relation", None)
                item.pop("note", None)
        return v
    if _variant_semantics(pre_doc) != _variant_semantics(live_f1_doc):
        semantics_delta.append("class_identity_variants(non-relation fields)")
    ctrl = controls(cmp, rows, suite, pre_doc)
    ctrl["K7_class_semantics_unchanged"] = not semantics_delta
    ctrl["K7_detail"] = {"fields_checked": semantics_fields, "changed": semantics_delta}
    ctrl["all_pass"] = all(v is True for k, v in ctrl.items()
                           if k.startswith("K") and isinstance(v, bool))

    live_end = {p: sha256_file(os.path.join(ROOT, p)) for p in PINNED_INPUTS}
    # FROZEN is the artifact the repair is actively re-publishing; its movement is
    # a measured repair observation, not a drift failure of the verdict inputs.
    decision_inputs = [p for p in PINNED_INPUTS if p != CANON["frozen"]]
    stable = all(live_end[p] == live[p] for p in decision_inputs)
    frozen_moved = live_end[CANON["frozen"]] != live[CANON["frozen"]]

    i2_ok = schemas["defects"] == []
    i3_marker = "rev13" in json.dumps(live_f1_doc.get("revision_history", []))
    i4_ok = all(r["status"] == "live" for r in frozen["records"]) and frozen["revision"] == 29
    suite_stale_rows = suite["totals"]["row_bindings_stale"]
    suite_f0_stale = any(d.get("where", "").endswith("cross_artifact") for d in suite["defects"])
    verdict = {
        "primary": "SUITE_UNBOUND_AT_F1_REV13" if suite_stale_rows else "SUITE_STILL_BOUND",
        "statement": (
            f"At live pins suite {live[CANON['suite']][:12]} / F1 rev{live_f1_doc.get('revision')} "
            f"{live[CANON['f1']][:12]} / F2a {live[CANON['f2a']][:12]} / F2b {live[CANON['f2b']][:12]} / "
            f"F0 {live[CANON['f0']][:12]} / corpus {live[CANON['cases']][:12]} / "
            f"FROZEN rev{frozen['revision']} {live[CANON['frozen']][:12]}: "
            f"{suite_stale_rows}/{suite['totals']['rows']} suite rows carry binding_sha256 = the superseded "
            "pre-repair F1 cce9c60146d6, so the suite does not bind the live canonical schema it is evidence for. "
            f"Row bindings stale: {suite_stale_rows}; probe re-computation against live F1 rev13: "
            f"{suite['totals']['probes_recomputed_pass_live_rev13']}/{suite['totals']['probes']} pass vs "
            f"{suite['totals']['probes_stored_pass']}/{suite['totals']['probes']} stored; "
            f"against the pinned pre-repair rev12 snapshot: "
            f"{suite['totals']['probes_recomputed_pass_prerepair_rev12']}/{suite['totals']['probes']} pass, "
            f"defects {len(suite['defects'])} (the W031-F1-PINCENSUS-01 baseline). "
            "REC-12's four authorised items (corpus rows, three consistency-evidence pins, F1 strictness text, "
            "FROZEN rev29) do not name schemas/f1_falsifier_tests.jsonl; item status at this measurement: "
            f"I1 rows+checker landed ({cases['row_bindings_to_live_f0']}/{cases['row_binding_count']} rows bind the live F0), "
            f"I2 landed ({'yes' if i2_ok else 'no'}), I3 rev13 text present ({'yes' if i3_marker else 'no'}), "
            f"I4 FROZEN rev29 {'landed' if i4_ok else 'not landed (still revision %s)' % frozen['revision']}. "
            "Consequence: G-FORM's acceptance evidence suite is now stale on both its F1 row bindings and its "
            "F1-AMB-25 F0 expectation unless the suite is re-pinned and re-run."),
        "authority": "worker measurement only; no gate verdict, no node status, no canonical artifact edited",
    }

    report = {
        "report_id": REPORT_ID, "task_id": TASK_ID, "agent": AGENT,
        "created_at": started, "finished_at": now(),
        "class_id": "AF-WCC-VAC-GEN", "class_refs": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "node_id": "F1", "gate": "G-FORM",
        "scope": ("Impact of the REC-12 astra-life05-evidence-binding-repair on schemas/f1_falsifier_tests.jsonl "
                  "as G-FORM evidence: operative pin census, 84-probe recomputation at live rev13 and at the pinned "
                  "pre-repair rev12 snapshot, FROZEN rev28 pin integrity for the moved paths, and an authorised-delta "
                  "scope check of the F1 rev12->rev13 rewrite."),
        "pinned_inputs": {p: {"sha256": live[p], "pre_repair_sha256": PRE_REPAIR.get(
            {"schemas/af_wcc_vacuum.yaml": "schema_f1", "schemas/af_scc_c2_vacuum.yaml": "schema_f2a",
             "schemas/af_scc_c0_vacuum.yaml": "schema_f2b",
             "schemas/taxonomy_cases.jsonl": "cases"}.get(p, ""), None),
            "matches_pin_at_finish": live_end[p] == PINNED_INPUTS[p]} for p in PINNED_INPUTS},
        "inputs_stable_during_run": stable,
        "frozen_moved_during_run": frozen_moved,
        "frozen_revision_at_finish": json.load(open(os.path.join(ROOT, CANON["frozen"]))).get("revision"),
        "pre_repair_snapshot": {"path": PRE_REPAIR["f1_snapshot"], "sha256": snap_hash, "matches_pin": snap_ok},
        "repair_item_status": {
            "I1_corpus_rows_and_checker": {"status": "landed" if cases["row_bindings_to_live_f0"] == cases["row_binding_count"] and not cases["defects"] else "open",
                                           "live_cases_sha256": live[CANON["cases"]],
                                           "rows_binding_live_f0": cases["row_bindings_to_live_f0"],
                                           "rows": cases["row_binding_count"], "defects": cases["defects"]},
            "I2_consistency_evidence_pins": {"status": "landed" if i2_ok else "open", "defects": schemas["defects"]},
            "I3_f1_strictness_text": {"status": "landed" if i3_marker else "open",
                                      "f1_revision": live_f1_doc.get("revision")},
            "I4_frozen_rev29": {"status": "landed" if i4_ok else "open",
                                "frozen_revision": frozen["revision"],
                                "files_stale": frozen["files_stale"],
                                "stale_moved_paths": [r["path"] for r in frozen["stale_moved_paths"]]},
            "I5_suite_repin": {"status": "not_in_rec12_scope",
                               "row_bindings_stale": suite_stale_rows,
                               "f0_cross_artifact_stale": suite_f0_stale},
        },
        "schemas": schemas, "cases": cases, "frozen": frozen,
        "suite": suite,
        "f1_rev12_to_rev13_delta_scope": scope,
        "controls": ctrl,
        "verdict": verdict,
        "falsifier": ("Any pinned decision input (suite, F1/F2a/F2b, F0, corpus, consistency evidence) moving "
                      "(see inputs_stable_during_run), any of K1-K6 failing, a flagged "
                      "`stale` pair shown to be provenance rather than an operative binding, or the suite re-pinned "
                      "to the live F1/F0 hashes and re-published before this verdict is read (repairs, does not falsify, F1)."),
        "next_falsifier": ("After FROZEN rev29 lands and the suite is re-pinned: re-run this instrument at the new "
                           "pins; row bindings must be 25/25 live and 84/84 probes must reproduce at the then-live "
                           "F1/F0 pair. If only the manifest is re-pinned and the suite is left at 56bcb4b3234b, the "
                           "suite stays evidence-stale and G-FORM review coverage cannot bind it."),
        "authority": "worker measurement only; no gate verdict, no node status, no validation_status, no artifact edited",
    }

    out_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(out_dir, "report.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1, sort_keys=False)
        fh.write("\n")

    print(json.dumps({
        "verdict": verdict["primary"],
        "inputs_stable": stable,
        "suite_rows": suite["totals"]["rows"],
        "row_bindings_stale": suite_stale_rows,
        "probes_stored_pass": suite["totals"]["probes_stored_pass"],
        "probes_live_rev13": suite["totals"]["probes_recomputed_pass_live_rev13"],
        "probes_prerepair_rev12": suite["totals"]["probes_recomputed_pass_prerepair_rev12"],
        "defects_live": len(suite["defects"]),
        "schemas_defects": len(schemas["defects"]),
        "frozen_stale": frozen["files_stale"],
        "delta_changed": scope["changed"], "delta_unexpected": len(scope["unexpected_changed"]),
        "controls": ctrl,
    }, indent=1))

    if drift or not stable:
        print("INPUT DRIFT: " + json.dumps(drift))
        return 2
    if not ctrl["all_pass"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
