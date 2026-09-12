#!/usr/bin/env python3
"""W012-GNUM-C4-REGISTRY-VERIFY-01 — read-only verification of PROTOCOL rule 2 (C4) registration.

Owner: worker-012 (bounded execution worker). Class AF-WCC-SCALAR-SPH, node N0, gate G-NUM.

What it does (no writes anywhere):
  1. Pins runtime/state/artifact_hashes.json and research_map/audit_evidence.py pre/post.
  2. Extracts the registry scan roots from the pinned audit_evidence.py source.
  3. Classifies the union of the lead-audit B-N0-R2-1 six paths, the lifecycle-08 closure
     residual_unregistered four paths, and the N0 chain paths.
  4. Reconciles the two counts, emits the controller remediation set and in-memory controls.
  5. Checks the numerics lock guard and determinism.

Usage: python3 verify_c4_registry.py            # writes report.json next to this file
       python3 verify_c4_registry.py --stdout   # print only, no file write
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

CST = timezone(timedelta(hours=8))
ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent

REGISTRY_PATH = "runtime/state/artifact_hashes.json"
AUDIT_EVIDENCE_PATH = "research_map/audit_evidence.py"
REV3_PATH = "numerics/results/flat_wave_convergence_rev3.json"
CLOSURE_PATH = "numerics/protocol/lifecycle08_stoprule_closure_verify.json"
LEAD_AUDIT_VERDICT_PATH = "reviews/N0-review-final-verify.json"
TAXONOMY_PATH = "research_map/formulation_taxonomy.yaml"

# Pins declared in PRE_REGISTRATION.md; every one is re-measured, never trusted.
DECLARED = {
    REV3_PATH: "da7c360719950f7ef6be2624391dee464f8c818a0be74ec44f0f8c70d2b28ac3",
    CLOSURE_PATH: "88ec0bf298cbc4de6ae2a6d3038961d404f1c43a64cbaa92f29b6ad6cce77f75",
    LEAD_AUDIT_VERDICT_PATH: "18a0c0d0e77f0b0a",
    "numerics/CONVERGENCE_PROTOCOL.md": "1e6cdf04d7a2431373092b657095bab4edeea9fb32f1d3c8981c50b2156a7274",
    "numerics/gates.py": "fcd1d70991b6eade4aa993dc49b6103e338f68320aabb955d97da5a8f55d996e",
    "numerics/results/flat_wave_convergence.json": "e9e124227c4d29323f8bf9d4071a21da4484c1fdfdb67d4237dad8b8fe14bd2e",
    "numerics/protocol/n0_fixed_dt_certification.json": "1677822ceb9c81e8f6e48dee8360ab13edc35623c51f4be68bd6589a5fe79920",
    "numerics/tests/flat_wave_replication.py": "8ade1cdc163ea420790b9fdfdab41157b4f3d4219d6a0bcf827baafe69a6f422",
    "artifacts/worker-046/n0_fixed_dt_independent/verification.json": "814452111bc8912bb21f8e0a353fe78096640d299e469578462b755592ea9a61",
    "artifacts/worker-057/n0_fixeddt_verify/report.json": "b906445878f3130dd710595a362883e29be87f11cb8d8edbdbc79539147b3b04",
    "artifacts/worker-081/n0_c8_adjudication_rev2/adjudication.json": "65ae766d9e4c205762cff35fb822915d4b00bd4502a0326455bed84e7b3169d6",
    TAXONOMY_PATH: "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json_pinned(rel: str):
    p = ROOT / rel
    before = sha256(p)
    obj = json.loads(p.read_text())
    after = sha256(p)
    return obj, {"sha256": before, "before": before, "after": after, "stable": before == after,
                 "bytes": p.stat().st_size}


def extract_registry_roots(source: str):
    """Pull the scan-root tuple and the rubric path out of the pinned source text."""
    roots = []
    m = re.search(r"for\s+d\s+in\s*\(([^)]*)\)", source)
    if m:
        roots = re.findall(r"[\"']([^\"']+)[\"']", m.group(1))
    rubric = None
    m2 = re.search(r"rubric\s*=\s*ROOT\s*/\s*[\"']([^\"']+)[\"']", source)
    if m2:
        rubric = m2.group(1)
    return roots, rubric


def under_root(rel: str, roots) -> bool:
    return any(rel == r or rel.startswith(r.rstrip("/") + "/") for r in roots)


def classify(rel: str, registry: dict, hashes: dict, roots) -> dict:
    p = ROOT / rel
    if not p.is_file():
        return {"class": "missing-file", "measured_sha256": None, "bytes": None,
                "registered_sha256": (registry.get(rel) or {}).get("sha256"),
                "under_registry_root": under_root(rel, roots)}
    h = sha256(p)
    bytes_ = p.stat().st_size
    reg = registry.get(rel)
    base = {"measured_sha256": h, "bytes": bytes_,
            "registered_sha256": (reg or {}).get("sha256"),
            "under_registry_root": under_root(rel, roots)}
    if reg is not None:
        base["class"] = "registered-match" if reg.get("sha256") == h else "registered-mismatch"
        return base
    decl = hashes.get(rel)
    if isinstance(decl, dict) and decl.get("sha256") == h:
        base["class"] = "declared-only"
        return base
    base["class"] = "unregistered-in-root" if base["under_registry_root"] else "unregistered-structural"
    return base


def comparison_is_live(rel: str, registry: dict, roots) -> bool:
    """C2 helper: corrupting the registry hash for a registered path must flip match->mismatch."""
    good = classify(rel, registry, {}, roots)["class"]
    bad_reg = dict(registry)
    bad_reg[rel] = dict(registry[rel])
    bad_reg[rel]["sha256"] = "0" * 64
    bad = classify(rel, bad_reg, {}, roots)["class"]
    return good == "registered-match" and bad == "registered-mismatch"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stdout", action="store_true", help="print report, do not write report.json")
    args = ap.parse_args()

    registry_obj, registry_pin = load_json_pinned(REGISTRY_PATH)
    registry = registry_obj.get("registry", {})
    hashes = registry_obj.get("hashes", {})
    checked_at = registry_obj.get("checked_at")

    ae_src = (ROOT / AUDIT_EVIDENCE_PATH).read_text()
    ae_before = sha256(ROOT / AUDIT_EVIDENCE_PATH)
    roots, rubric = extract_registry_roots(ae_src)
    ae_after = sha256(ROOT / AUDIT_EVIDENCE_PATH)

    rev3, rev3_pin = load_json_pinned(REV3_PATH)
    closure, closure_pin = load_json_pinned(CLOSURE_PATH)
    lead, lead_pin = load_json_pinned(LEAD_AUDIT_VERDICT_PATH)

    lead_six = list(((lead.get("blocking_items") or [{}])[0]).get("finding", "") and
                    re.findall(r"[A-Za-z0-9_./-]+\.(?:json|md|py|yaml)", str((lead.get("blocking_items") or [{}])[0].get("finding", ""))))
    # B-N0-R2-1 enumerates the six paths inside a parenthetical; de-duplicate preserving order.
    lead_six = list(dict.fromkeys(lead_six))
    lead_six = [p for p in lead_six if p not in {"artifact_hashes.json", REGISTRY_PATH}]
    closure_four = list(closure.get("registration", {}).get("residual_unregistered", []))
    rev3_six = [p for p, v in (rev3.get("registration_state", {}).get("registry_generated_paths", {}) or {}).items()
                if v.get("registered") is False]

    chain = list(DECLARED.keys())
    union = list(dict.fromkeys(chain + lead_six + closure_four + rev3_six))

    cls = {p: classify(p, registry, hashes, roots) for p in union}
    cls2 = {p: classify(p, registry, hashes, roots) for p in union}

    # P3 reconciliation
    lead_six_now = {p: cls.get(p, {}).get("class") for p in lead_six}
    closure_four_now = {p: cls.get(p, {}).get("class") for p in closure_four}
    live_residual = sorted(p for p, v in cls.items()
                           if v["class"] in {"unregistered-in-root", "unregistered-structural",
                                             "registered-mismatch", "missing-file"})
    declared_only = sorted(p for p, v in cls.items() if v["class"] == "declared-only")
    # PROTOCOL rule 2 says "a sha256 in runtime/state/artifact_hashes.json". The file has two
    # sections; a path can satisfy the sentence in `hashes` while absent from `registry`.
    rule2_readings = {
        "registry_only": sorted(live_residual + declared_only),
        "registry_union_hashes": list(live_residual),
        "note": ("registry-only reading reproduces the closure's 4-path residual; the "
                 "registry-union-hashes reading leaves 3. research_map/formulation_taxonomy.yaml "
                 "is present in `hashes` with a matching measured sha256 but absent from `registry`."),
    }

    # P4 remediation
    remediation = [{"path": p, "measured_sha256": cls[p]["measured_sha256"], "bytes": cls[p]["bytes"],
                    "class": cls[p]["class"], "under_registry_root": cls[p]["under_registry_root"],
                    "minimal_action": (
                        "register measured sha256 in runtime/state/artifact_hashes.json"
                        if cls[p]["class"] == "unregistered-in-root" else
                        "extend audit_evidence.py registry roots to cover this path (or register explicitly)"
                        if cls[p]["class"] == "unregistered-structural" else
                        "resolve hash mismatch before any completion claim"
                        if cls[p]["class"] == "registered-mismatch" else
                        "restore file or retract the reference")}
                   for p in live_residual]

    # P5 controls (all in memory)
    plant = "artifacts/worker-012/n0_c4_registry_verify/__planted_nonexistent__.json"
    c1 = classify(plant, registry, hashes, roots)["class"] == "missing-file"
    some_registered = next((p for p in chain if cls[p]["class"] == "registered-match"), None)
    c2 = comparison_is_live(some_registered, registry, roots) if some_registered else False
    # C3: prune a real in-root file out of the registry and require unregistered-in-root
    in_root = next((p for p in chain if under_root(p, roots) and (ROOT / p).is_file()), None)
    pruned = {k: v for k, v in registry.items() if k != in_root}
    c3 = classify(in_root, pruned, {}, roots)["class"] == "unregistered-in-root" if in_root else False
    c4 = cls.get(TAXONOMY_PATH, {}).get("class") == "declared-only"
    c5 = (roots == ["schemas", "ledger", "numerics", "reviews", "evaluation",
                    "artifacts/numerics", "runtime/state/controller_verification"]
          and rubric == "evaluation_rubric.yaml")
    controls = {"C1_planted_missing": c1, "C2_corrupted_hash_detected": c2,
                "C3_pruned_in_root_unregistered": c3, "C4_taxonomy_declared_only": c4,
                "C5_roots_and_rubric": c5, "C3_subject": in_root, "C2_subject": some_registered}

    # P6 lock guard
    solver = (ROOT / "numerics/spherical_solver").exists()
    n1_paths = [p for p in union if re.search(r"(^|/)N1([^0-9]|$)|spherical_solver", p)]
    try:
        live_map = json.loads((ROOT / "research_map/research_map.json").read_text())
        lock_state = (live_map.get("numerics_lock") or {}).get("state")
    except Exception as e:  # pragma: no cover
        lock_state = f"unreadable: {e}"
    lock_ok = (not solver) and (not n1_paths) and lock_state == "locked"

    # P7 determinism
    deterministic = cls == cls2

    mismatches = [p for p, v in cls.items() if v["class"] == "registered-mismatch"]
    missing = [p for p, v in cls.items() if v["class"] == "missing-file"]
    controls_ok = all(v for k, v in controls.items() if k.startswith("C"))
    pins_ok = (registry_pin["stable"] and ae_before == ae_after
               and all(p["stable"] for p in (rev3_pin, closure_pin, lead_pin)))
    verdict = ("RESIDUAL_RECONCILED_STRUCTURAL" if (controls_ok and pins_ok and deterministic
                                                    and not mismatches and not missing and lock_ok)
               else "REVISE")

    report = {
        "schema": "worker-012/n0-c4-registry-verify/v1",
        "task_id": "W012-GNUM-C4-REGISTRY-VERIFY-01",
        "worker": "worker-012",
        "role": "bounded execution worker (no gate authority, no node transition)",
        "class_id": "AF-WCC-SCALAR-SPH",
        "node_id": "N0",
        "gate": "G-NUM",
        "generated_at": datetime.now(CST).isoformat(timespec="seconds"),
        "method": ("read-only; registry and all sources pinned pre/post; roots extracted from "
                   "the pinned audit_evidence.py source; no canonical file, map, registry or "
                   "detector written"),
        "registry_checked_at": checked_at,
        "pins": {REGISTRY_PATH: registry_pin, AUDIT_EVIDENCE_PATH: {"sha256": ae_before,
                                                                   "before": ae_before,
                                                                   "after": ae_after,
                                                                   "stable": ae_before == ae_after},
                 REV3_PATH: rev3_pin, CLOSURE_PATH: closure_pin, LEAD_AUDIT_VERDICT_PATH: lead_pin},
        "declared_pins_match_disk": {p: bool((cls.get(p, {}).get("measured_sha256") or "").startswith(h))
                                     for p, h in DECLARED.items()},
        "registry_root_mechanism": {"source": AUDIT_EVIDENCE_PATH, "roots": roots,
                                    "rubric": rubric,
                                    "note": ("paths outside these roots are structurally unreachable "
                                             "by the registry snapshot, whatever the controller does")},
        "source_lists": {"lead_audit_b_n0_r2_1_six": lead_six,
                         "closure_residual_unregistered_four": closure_four,
                         "rev3_declared_unregistered_six": rev3_six},
        "classifications": cls,
        "reconciliation": {"lead_audit_six_at_live_registry": lead_six_now,
                           "closure_four_at_live_registry": closure_four_now,
                           "live_residual": live_residual,
                           "declared_only_not_in_registry": declared_only,
                           "rule2_readings": rule2_readings,
                           "lead_audit_gap_now_closed": all(v == "registered-match" for v in lead_six_now.values()),
                           "closure_residual_reproduced_registry_only": all(
                               v != "registered-match" for v in closure_four_now.values()),
                           "rev3_declared_gap_now_closed": all(
                               cls.get(p, {}).get("class") == "registered-match" for p in rev3_six)},
        "remediation": remediation,
        "controls": controls,
        "lock_guard": {"numerics_lock_state": lock_state,
                       "spherical_solver_present": solver,
                       "n1_artifacts_in_evidence": n1_paths,
                       "passes": lock_ok},
        "determinism": {"identical_across_two_in_process_runs": deterministic},
        "counts": {"classified": len(cls), "registered_match": sum(v["class"] == "registered-match" for v in cls.values()),
                   "declared_only": sum(v["class"] == "declared-only" for v in cls.values()),
                   "unregistered_in_root": sum(v["class"] == "unregistered-in-root" for v in cls.values()),
                   "unregistered_structural": sum(v["class"] == "unregistered-structural" for v in cls.values()),
                   "registered_mismatch": len(mismatches), "missing_file": len(missing)},
        "verdict": verdict,
        "verdict_scope": ("artifact/process verification of the C4 registration condition only; "
                          "not a G-NUM gate verdict, not an N0 node verdict, not a lock release"),
        "falsifier": ("Re-run at the same pins: falsified if any pre/post sha differs, if a corrupted "
                      "registry hash is not reported as registered-mismatch, if a planted non-existent "
                      "path is not missing-file, if an unregistered-structural verdict is not explained "
                      "by the extracted roots, or if any N1/spherical-solver artifact appears. A moved "
                      "registry voids the counts for the new bytes."),
        "next_falsifier": ("a registry snapshot in which the three worker-046/057/081 verdict artifacts "
                           "are registered-match, or a controller-recorded root extension after which "
                           "the residual set is empty"),
    }
    text = json.dumps(report, indent=1, sort_keys=True)
    if args.stdout:
        print(text)
    else:
        (HERE / "report.json").write_text(text + "\n")
        print(json.dumps({"verdict": verdict, "counts": report["counts"],
                          "controls": {k: v for k, v in controls.items() if k.startswith("C")},
                          "lock_guard": report["lock_guard"], "remediation": len(remediation)}, indent=1))
    return 0 if verdict != "REVISE" else 1


if __name__ == "__main__":
    sys.exit(main())
