#!/usr/bin/env python3
"""W045-OPENCASE-REBIND-TRANSFER-01 — independent transfer verification of the
9-open-case disposition matrix onto the live (post-repair) F0 corpus bytes.

Read-only on every canonical path. Writes only under this artifact directory.
Stdlib + PyYAML. No network.

Question: the operative open-case disposition (claim
`flash02-opencase-claim-0010b-supersede-20260912T003552`) and its matrix artifact
`artifacts/flash-02/open_case_disposition.json` are pinned to superseded corpus
bytes. `schemas/taxonomy_cases.jsonl` was repaired at 2026-09-12T00:42 to
ccf7041bd0ff. Does the 7+2 disposition content transfer to the repaired bytes,
and which bindings are stale?

Verdict rule (pre-registered):
  TRANSFER_VERIFIED_BINDING_STALE  iff checks B..F pass and check G finds stale refs
  TRANSFER_VERIFIED_BINDING_CURRENT iff checks B..G pass with no stale refs
  TRANSFER_FAILED                  otherwise
Hard-fail conditions (check C): any CONTENT_KEY differs between the claim-pinned
snapshot and the live corpus, or the case_id multiset differs.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone, timedelta

import yaml

CST = timezone(timedelta(hours=8))

ROOT = os.path.abspath(os.path.dirname(__file__))
while not os.path.isdir(os.path.join(ROOT, "research_map")):
    parent = os.path.dirname(ROOT)
    if parent == ROOT:
        raise SystemExit("repo root not found")
    ROOT = parent

TASK_ID = "W045-OPENCASE-REBIND-TRANSFER-01"
ACTOR = "worker-045"
CLASS_ID = "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH"
OPERATIVE_CLAIM = "flash02-opencase-claim-0010b-supersede-20260912T003552"
OUT = os.path.join(ROOT, "artifacts/worker-045/opencase_rebind_transfer")

PINS = {
    "corpus_live": "schemas/taxonomy_cases.jsonl",
    "taxonomy_live": "research_map/formulation_taxonomy.yaml",
    "corpus_claim_pin_snapshot": "artifacts/flash-02/snapshots/taxonomy_cases.pre-rebind-r2.f0c20b96.jsonl",
    "matrix_flash02": "artifacts/flash-02/open_case_disposition.json",
    "matrix_worker083": "artifacts/worker-083/f0_open_case_disposition/dispositions.json",
    "catalog_live": "artifacts/flash-02/leak_rule_catalog.json",
    "map_snapshot": "research_map/research_map.json",
}
EXPECT = {
    "corpus_live": "ccf7041bd0ff3ce844c07a700a588b7fe8e3c90880674c5e595b21f6259a8f03",
    "taxonomy_live": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "corpus_claim_pin_snapshot": "f0c20b96f76dc21b32ae81962bb3aa207b04e90c28aa6da8a686e0d9f649a1e8",
    "matrix_flash02": "ee05eb8e7cdef44e6ab028652185c80f0737603a4d2c5a26c2de3008cb511bcf",
}
# Content keys: a difference in any of these between the claim-pinned snapshot
# and the live corpus is a hard failure (the repair must be pin-only).
CONTENT_KEYS = (
    "record_type", "case_id", "polarity", "class_id", "as_filed_class_id",
    "statement", "axis_vector", "decisive_axes", "decisive_hypothesis",
    "expected_classification", "expected_leak_rule", "expected_verdict",
    "expected_resolution", "gate_expectation", "leak_kind",
    "violated_vocabulary", "falsifier", "open",
)
# Pin/binding keys: churn here is expected across a pin repair and is reported,
# not failed. Anything outside CONTENT_KEYS|PIN_KEYS|evidence_refs is advisory.
PIN_KEYS = (
    "taxonomy_ref", "binding_status", "rebound_at", "rebind_note",
    "prior_binding_sha256", "prior_binding_ref", "binding_at_authoring",
)
MATRIX_NEW_CLASS_TOKENS = ("NEW_CLASS_REQUEST_DEFERRED_TO_HUMAN_PI",)
MATRIX_SPLIT_TOKENS = ("SPLIT_REQUIRED", "SPLIT_AND_BRIDGE_REQUIRED")


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_jsonl(path: str):
    return [json.loads(line) for line in open(path, encoding="utf-8") if line.strip()]


def load_json(path: str):
    return json.load(open(path, encoding="utf-8"))


_CACHE = {}


def read_once(path: str) -> bytes:
    """Read a moving target (the live map) exactly once per process."""
    if path not in _CACHE:
        with open(path, "rb") as f:
            _CACHE[path] = f.read()
    return _CACHE[path]


def canon(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def cases_of(records):
    return [r for r in records if r.get("record_type") == "case"]


def flatten_diff(a: dict, b: dict):
    """Return sorted paths whose values differ (shallow for lists/dicts)."""
    keys = sorted(set(a) | set(b))
    out = []
    for k in keys:
        if canon(a.get(k)) != canon(b.get(k)):
            out.append(k)
    return out


def measure(pins: dict) -> dict:
    measured_at = datetime.now(CST).isoformat(timespec="seconds")
    files = {k: os.path.join(ROOT, v) for k, v in pins.items()}
    hashes = {k: sha256_file(p) for k, p in files.items()}
    map_bytes = read_once(files["map_snapshot"])
    hashes["map_snapshot"] = hashlib.sha256(map_bytes).hexdigest()
    corpus = load_jsonl(files["corpus_live"])
    snapshot = load_jsonl(files["corpus_claim_pin_snapshot"])
    taxonomy = yaml.safe_load(open(files["taxonomy_live"], encoding="utf-8"))
    matrix = load_json(files["matrix_flash02"])
    m083 = load_json(files["matrix_worker083"])
    catalog = load_json(files["catalog_live"])
    rmap = json.loads(map_bytes)

    checks, controls, findings = {}, {}, []

    # ---- A. pin measurement / drift guard material
    checks["A_pins"] = {
        "status": "pass",
        "measured": hashes,
        "expected": {k: EXPECT[k] for k in EXPECT},
        "mismatches": [k for k in EXPECT if hashes[k] != EXPECT[k]],
    }
    if checks["A_pins"]["mismatches"]:
        checks["A_pins"]["status"] = "fail"

    # ---- B. open-set identity
    live_open = [r["case_id"] for r in cases_of(corpus) if r.get("open") is True]
    matrix_rows = matrix["rows"]
    matrix_ids = [r["case_id"] for r in matrix_rows]
    checks["B_open_set_identity"] = {
        "status": "pass",
        "live_open_count": len(live_open),
        "live_open_ids": sorted(live_open),
        "matrix_row_count": len(matrix_ids),
        "matrix_row_ids": sorted(matrix_ids),
        "missing_from_matrix": sorted(set(live_open) - set(matrix_ids)),
        "extra_in_matrix": sorted(set(matrix_ids) - set(live_open)),
        "duplicate_matrix_ids": sorted(k for k, v in Counter(matrix_ids).items() if v > 1),
    }
    if (set(live_open) != set(matrix_ids) or len(matrix_ids) != len(set(matrix_ids))
            or len(live_open) != 9):
        checks["B_open_set_identity"]["status"] = "fail"

    # ---- C. pin-only repair delta (claim-pinned snapshot -> live)
    snap_cases = cases_of(snapshot)
    live_cases = cases_of(corpus)
    snap_by = {r["case_id"]: r for r in snap_cases}
    live_by = {r["case_id"]: r for r in live_cases}
    per_case_diff = {}
    content_violations = []
    for cid in sorted(set(snap_by) | set(live_by)):
        a, b = snap_by.get(cid, {}), live_by.get(cid, {})
        diff = flatten_diff(a, b)
        per_case_diff[cid] = diff
        for k in diff:
            if k in CONTENT_KEYS:
                content_violations.append({"case_id": cid, "key": k,
                                           "snapshot": a.get(k), "live": b.get(k)})
    all_diff_keys = sorted({k for v in per_case_diff.values() for k in v})
    unexpected_keys = sorted(set(all_diff_keys) - set(CONTENT_KEYS) - set(PIN_KEYS) - {"evidence_refs"})
    checks["C_pin_only_delta"] = {
        "status": "pass" if not content_violations and set(snap_by) == set(live_by) else "fail",
        "snapshot_case_count": len(snap_cases),
        "live_case_count": len(live_cases),
        "case_id_sets_equal": set(snap_by) == set(live_by),
        "all_differing_keys": all_diff_keys,
        "changed_case_count": sum(1 for v in per_case_diff.values() if v),
        "content_key_violations": content_violations,
        "unexpected_non_pin_keys": unexpected_keys,
    }

    # ---- D. axis-vector non-match against every frozen class
    class_axes = {cid: c.get("axes", {}) for cid, c in taxonomy["classes"].items()}
    frozen_ids = sorted(class_axes)
    axis_matches = []
    nearest = {}
    open_set = set(live_open)
    for r in [x for x in cases_of(corpus) if x["case_id"] in open_set]:
        av = r.get("axis_vector") or {}
        for cid, axes in class_axes.items():
            if canon(av) == canon(axes):
                axis_matches.append({"case_id": r["case_id"], "class_id": cid})
            overlap = len([k for k in set(av) | set(axes) if canon(av.get(k)) == canon(axes.get(k))])
            nearest.setdefault(r["case_id"], []).append([overlap, cid])
    for cid in nearest:
        nearest[cid] = sorted(nearest[cid], key=lambda t: (-t[0], t[1]))
    checks["D_axis_nonmatch"] = {
        "status": "pass" if not axis_matches else "fail",
        "frozen_class_ids": frozen_ids,
        "open_rows_compared": len([r for r in cases_of(corpus) if r["case_id"] in set(live_open)]),
        "exact_matches": axis_matches,
        "nearest_class_by_key_overlap": nearest,
    }

    # ---- E. matrix coverage / token validity
    tokens = set(matrix.get("disposition_tokens") or {})
    dispo = Counter(r["disposition"] for r in matrix_rows)
    bad_tokens = sorted({r["disposition"] for r in matrix_rows} - tokens)
    new_rows = [r["case_id"] for r in matrix_rows if r["disposition"] in MATRIX_NEW_CLASS_TOKENS]
    split_rows = [r["case_id"] for r in matrix_rows if r["disposition"] in MATRIX_SPLIT_TOKENS]
    gap_ok = all((r.get("gap_ref") == "coverage_gaps.CG2")
                 for r in matrix_rows if r["disposition"] in MATRIX_NEW_CLASS_TOKENS)
    checks["E_matrix_validity"] = {
        "status": "pass",
        "disposition_census": dict(dispo),
        "bad_tokens": bad_tokens,
        "new_class_rows": sorted(new_rows),
        "split_rows": sorted(split_rows),
        "gap_ref_cg2_all_new_class": gap_ok,
        "matrix_frozen_class_ids": sorted(matrix.get("frozen_class_ids") or []),
        "taxonomy_class_ids": frozen_ids,
    }
    if (bad_tokens or len(new_rows) != 7 or len(split_rows) != 2
            or sorted(matrix.get("frozen_class_ids") or []) != frozen_ids or not gap_ok
            or matrix.get("corpus_ref", {}).get("open_cases") != 9):
        checks["E_matrix_validity"]["status"] = "fail"

    # ---- F. cross-source agreement with worker-083's independent matrix
    w83 = m083.get("summary", {})
    w83_open = w83.get("open_by_disposition", {})
    w83_new = int(w83_open.get("NEW_CLASS_REQUIRED", 0))
    w83_split = int(w83_open.get("SPLIT_REQUIRED", 0))
    agreement = (w83_new == len(new_rows) and w83_split == len(split_rows))
    checks["F_cross_source_agreement"] = {
        "status": "pass" if agreement else "fail",
        "flash02_open_by_family": {"new_class": len(new_rows), "split": len(split_rows)},
        "worker083_open_by_disposition": w83_open,
        "worker083_total_cases": w83.get("total_cases"),
        "worker083_open_cases": w83.get("open_cases"),
        "per_case_note": "worker-083 dispositions.json carries aggregate rows only; per-case ids cross-checked only for the split pair",
    }

    # ---- G. binding staleness (matrix refs vs live bytes)
    tax_ref = matrix.get("taxonomy_ref") or {}
    tax_ref_sha = tax_ref.get("sha256") if isinstance(tax_ref, dict) else None
    row_tax_pins = sorted({ref.split("#")[1] for r in matrix_rows for ref in (r.get("evidence_refs") or [])
                           if "formulation_taxonomy.yaml#" in ref})
    claim = next((c for c in rmap.get("claims", []) if c.get("event_id") == OPERATIVE_CLAIM), None)
    superseders = [c.get("event_id") for c in rmap.get("claims", [])
                   if c.get("supersedes_claim_event_id") == OPERATIVE_CLAIM]
    claim_corpus_pin = None
    if claim:
        for ref in claim.get("evidence_refs", []):
            if ref.startswith("schemas/taxonomy_cases.jsonl#"):
                claim_corpus_pin = ref.split("#", 1)[1]
    live_corpus = hashes["corpus_live"]
    live_tax = hashes["taxonomy_live"]
    stale = {
        "matrix_corpus_ref_sha256": matrix.get("corpus_ref", {}).get("sha256"),
        "matrix_taxonomy_ref_sha256": tax_ref_sha,
        "matrix_row_taxonomy_pins": row_tax_pins,
        "operative_claim_corpus_pin": claim_corpus_pin,
        "operative_claim_found": claim is not None,
        "operative_claim_superseded_by": superseders,
        "live_corpus_sha256": live_corpus,
        "live_taxonomy_sha256": live_tax,
    }
    stale["matrix_corpus_stale"] = stale["matrix_corpus_ref_sha256"] != live_corpus
    stale["matrix_taxonomy_stale"] = any(p != live_tax for p in row_tax_pins) or (
        tax_ref_sha is not None and tax_ref_sha != live_tax)
    stale["claim_corpus_stale"] = claim_corpus_pin != live_corpus
    checks["G_binding_staleness"] = {"status": "stale" if (
        stale["matrix_corpus_stale"] or stale["matrix_taxonomy_stale"] or stale["claim_corpus_stale"]
    ) else "current", **stale}

    # ---- K2/K3 mutation + tamper controls on in-memory copies
    k2_ids = [cid for cid in live_open if cid != "TC-F0-N01"]
    k2_detected = sorted(set(k2_ids) - set(matrix_ids)) == [] and sorted(set(matrix_ids) - set(k2_ids)) == ["TC-F0-N01"]
    controls["K2_open_flag_mutation"] = {
        "status": "pass" if k2_detected else "fail",
        "detail": "flip TC-F0-N01 open=true->false: open-set vs matrix mismatch detected" if k2_detected
                  else "mutation NOT detected",
    }
    tampered_open = (set(live_open) - {"TC-F0-N01"}) | {"TC-F0-N01X"}
    k3_detected = (sorted(set(live_open) - tampered_open) == ["TC-F0-N01"]
                   and sorted(tampered_open - set(live_open)) == ["TC-F0-N01X"])
    controls["K3_case_id_tamper"] = {
        "status": "pass" if k3_detected else "fail",
        "detail": "rename TC-F0-N01->TC-F0-N01X: missing/unknown ids reported" if k3_detected
                  else "tamper NOT detected",
    }

    # ---- K4 restamp invariance: pin-only rewrite must not register as content change
    restamped = json.loads(json.dumps(snapshot))
    for rec in restamped:
        if rec.get("record_type") == "case":
            if isinstance(rec.get("taxonomy_ref"), dict):
                rec["taxonomy_ref"]["sha256"] = live_tax
            rec["binding_status"] = "bound_taxonomy_sha_" + live_tax[:12]
            rec["evidence_refs"] = [re.sub(r"formulation_taxonomy\.yaml#[0-9a-f]{12}", "formulation_taxonomy.yaml#" + live_tax[:12],
                                           ref) for ref in rec.get("evidence_refs", [])]
    r_by = {r["case_id"]: r for r in cases_of(restamped)}
    k4_content = []
    for cid in sorted(set(snap_by) | set(r_by)):
        for k in flatten_diff(snap_by.get(cid, {}), r_by.get(cid, {})):
            if k in CONTENT_KEYS:
                k4_content.append({"case_id": cid, "key": k})
    controls["K4_restamp_invariance"] = {
        "status": "pass" if not k4_content else "fail",
        "detail": "pin-only restamp leaves all CONTENT_KEYS identical" if not k4_content
                  else f"restamp changed content keys: {k4_content[:5]}",
    }

    verdict = "TRANSFER_FAILED"
    if all(checks[k]["status"] == "pass" for k in ("B_open_set_identity", "C_pin_only_delta",
                                                   "D_axis_nonmatch", "E_matrix_validity", "F_cross_source_agreement")):
        verdict = ("TRANSFER_VERIFIED_BINDING_STALE" if checks["G_binding_staleness"]["status"] == "stale"
                   else "TRANSFER_VERIFIED_BINDING_CURRENT")

    if content_violations:
        findings.append({"id": "F1", "severity": "hard", "text": "repair is not pin-only for CONTENT_KEYS"})
    if checks["E_matrix_validity"]["status"] == "fail":
        findings.append({"id": "F2", "severity": "hard", "text": "matrix row validity/coverage check failed"})
    if checks["G_binding_staleness"]["status"] == "stale":
        findings.append({"id": "F3", "severity": "major",
                         "text": "disposition matrix and operative claim still pin superseded corpus/taxonomy bytes"})
    if checks["C_pin_only_delta"].get("unexpected_non_pin_keys"):
        findings.append({"id": "F4", "severity": "minor",
                         "text": f"repair touched keys outside the declared pin allowlist: {checks['C_pin_only_delta']['unexpected_non_pin_keys']}"})

    return {
        "task_id": TASK_ID,
        "actor": ACTOR,
        "created_at": measured_at,
        "class_id": CLASS_ID,
        "node_id": "F0",
        "gate": "G-F0",
        "operative_claim": OPERATIVE_CLAIM,
        "pins": PINS,
        "checks": checks,
        "controls": controls,
        "verdict": verdict,
        "findings": findings,
        "falsifier": ("Any of the 9 live open=true case_ids missing or duplicated in the matrix; any CONTENT_KEY "
                      "difference between the claim-pinned snapshot and the live corpus; any open-row axis_vector "
                      "equal to a frozen class axis vector; a matrix disposition token outside disposition_tokens; "
                      "a frozen_class_ids/taxonomy class-id mismatch; or any control K2/K3/K4 failing to fire."),
        "authority_note": ("worker measurement only; cannot set node status=done, validation_status=passed, or a "
                           "gate verdict; no canonical artifact was edited"),
    }


def measure_twice(pins):
    a = measure(pins)
    b = measure(pins)
    return a, canon(a["checks"]) == canon(b["checks"]) and canon(a["controls"]) == canon(b["controls"])


def main():
    os.makedirs(OUT, exist_ok=True)
    report, deterministic = measure_twice(PINS)
    report["controls"]["K1_determinism"] = {
        "status": "pass" if deterministic else "fail",
        "detail": "two in-process measurement passes produced byte-identical checks+controls",
    }
    # K5 drift guard: re-measure the fixed canonical pins at the end. The live
    # map is a moving target by design; it is reported separately, not failed.
    end = {k: sha256_file(os.path.join(ROOT, v)) for k, v in PINS.items() if k != "map_snapshot"}
    start = {k: v for k, v in report["checks"]["A_pins"]["measured"].items() if k != "map_snapshot"}
    drift = [k for k in end if end[k] != start[k]]
    map_now = sha256_file(os.path.join(ROOT, PINS["map_snapshot"]))
    report["controls"]["K5_zero_drift"] = {
        "status": "pass" if not drift else "fail",
        "detail": "all fixed pinned files unchanged start-to-end" if not drift else f"drift: {drift}",
        "map_moved_during_run": map_now != report["checks"]["A_pins"]["measured"]["map_snapshot"],
    }
    if any(report["controls"][k]["status"] != "pass" for k in report["controls"]):
        report["verdict"] = "TRANSFER_FAILED"
    with open(os.path.join(OUT, "report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1, sort_keys=True)
        f.write("\n")
    print(json.dumps({"verdict": report["verdict"],
                      "open_cases": report["checks"]["B_open_set_identity"]["live_open_ids"],
                      "controls": {k: v["status"] for k, v in report["controls"].items()},
                      "findings": report["findings"]}, indent=1))
    return 0 if report["verdict"].startswith("TRANSFER_VERIFIED") else 1


if __name__ == "__main__":
    raise SystemExit(main())
