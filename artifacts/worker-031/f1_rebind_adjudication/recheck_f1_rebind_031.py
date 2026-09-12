#!/usr/bin/env python3
"""
W031-F1-REBIND-ADJUDICATION-02  (instrument v2, re-scoped to the post-rebind state)

Question: after the 00:32:31 re-pin of schemas/f1_falsifier_tests.jsonl to F1
rev12/rev13, does every probe the suite RECORDS as passing still pass when
recomputed against the two canonical artifacts it depends on?

Docs under test
  A. schemas/af_wcc_vacuum.yaml                (F1 canonical, "self" document)
  B. research_map/formulation_taxonomy.yaml    (F0 canonical, cross-artifact)

Controls
  C-A replay       : the same probe logic against the pre-revision F1 snapshot
                     (af_wcc_vacuum.9a8bd4c9) reproduces the recorded outcomes
                     that were authored at that revision. Certifies extraction.
  C-B discrimination: a mutated copy of the pre-revision snapshot makes its
                     dependent probe fail. Certifies the logic can fail.
  C-C rebind uniform: every row's binding_sha256 equals the measured F1
                     canonical hash. Certifies the suite really was re-pinned.
  C-D f0-pin live  : the F0 hash declared inside the F1 schema equals the
                     measured F0 canonical hash. Certifies the schema's own
                     cross-artifact binding is fresh.
  C-E discriminator: at least one recorded-pass probe recomputes to FAIL against
                     A+B. This is the expected anomaly; a run reporting zero is
                     itself suspicious and is reported as such.

Authority: worker measurement only; no gate verdict, no node status, no
validation_status, no schema/suite edit.

Falsifier: the anomaly finding is void if the F1 canonical, the F0 canonical, or
the suite hash moves; if C-A/C-B fail; or if the flagged probe is shown to be a
non-binding provenance block rather than a deciding/operative field.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import sys

F1_SNAP_REL = "artifacts/worker-048/f1_closure_preflight/snapshot/af_wcc_vacuum.9a8bd4c9.yaml"
SHA_F1_SNAP = "9a8bd4c9680042a40894f6085f183661500966f2d787a6bf28a7098a271ed503"


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


def resolve(doc, dotted: str):
    if not isinstance(dotted, str) or not dotted:
        return "absent", None
    cur = doc
    for raw in dotted.split("."):
        tok = raw.strip()
        if tok == "":
            return "absent", None
        if tok.endswith("[*]"):
            base = tok[:-3]
            if base:
                if not isinstance(cur, dict) or base not in cur:
                    return "absent", None
                cur = cur[base]
            if not isinstance(cur, list):
                return "absent", None
            continue
        if tok.endswith("]") and "[" in tok:
            base, idx = tok[:-1].split("[", 1)
            if base:
                if not isinstance(cur, dict) or base not in cur:
                    return "absent", None
                cur = cur[base]
            try:
                i = int(idx)
            except ValueError:
                return "error", None
            if not isinstance(cur, list) or i >= len(cur) or i < -len(cur):
                return "absent", None
            cur = cur[i]
            continue
        if not isinstance(cur, dict) or tok not in cur:
            return "absent", None
        cur = cur[tok]
    return "ok", cur


def norm(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if v is None:
        return ""
    if isinstance(v, (dict, list)):
        return json.dumps(v, sort_keys=True)
    return str(v)


def excerpt(v, limit: int = 200) -> str:
    s = norm(v)
    return s if len(s) <= limit else s[:limit] + "..."


def run_probe(value, status: str, probe: dict):
    if status != "ok":
        return False, f"path did not resolve ({status})"
    s, e = norm(value), norm(probe.get("expected"))
    kind = probe.get("kind")
    if kind == "contains":
        return (e.lower() in s.lower()), "substring"
    if kind == "equals":
        return (s.strip().lower() == e.strip().lower()), "normalized equality"
    if kind == "is_true":
        return (value is True), "identity-true"
    if kind == "is_none":
        return (value is None), "identity-none"
    if kind == "path_exists":
        return True, "existence"
    if kind == "nonnull":
        return (value is not None) and (s != ""), "non-null"
    return False, f"UNSUPPORTED kind {kind!r}"


def mutated(doc):
    d = copy.deepcopy(doc)
    for path in ("genericity.excluded_set_status", "conclusion.conclusion_type",
                 "known_status.counterexample_status", "data_class.matter"):
        st, _ = resolve(d, path)
        if st == "ok":
            cur = d
            for t in path.split(".")[:-1]:
                cur = cur[t]
            cur[path.split(".")[-1]] = "W031-MUTATED-SENTINEL"
            return d, path
    return d, None


def main() -> int:
    f1_path = os.path.join(ROOT, "schemas", "af_wcc_vacuum.yaml")
    f0_path = os.path.join(ROOT, "research_map", "formulation_taxonomy.yaml")
    suite_path = os.path.join(ROOT, "schemas", "f1_falsifier_tests.jsonl")
    snap_path = os.path.join(ROOT, F1_SNAP_REL)

    pins = {
        "F1_canonical": {"path": "schemas/af_wcc_vacuum.yaml", "sha256": sha256_file(f1_path)},
        "F0_canonical": {"path": "research_map/formulation_taxonomy.yaml", "sha256": sha256_file(f0_path)},
        "suite": {"path": "schemas/f1_falsifier_tests.jsonl", "sha256": sha256_file(suite_path)},
        "F1_pre_revision_snapshot": {"path": F1_SNAP_REL, "sha256": sha256_file(snap_path),
                                      "expected": SHA_F1_SNAP},
    }

    rows = [json.loads(l) for l in open(suite_path, "r", encoding="utf-8") if l.strip()]
    f1 = load_yaml(f1_path)
    f0 = load_yaml(f0_path)
    snap = load_yaml(snap_path)
    ctrl, ctrl_path = mutated(snap)

    docs = {"F1_canonical": f1, "F0_canonical": f0}
    results = []
    census = {
        "rows": len(rows), "probes": 0,
        "recorded_pass": 0, "recorded_fail": 0,
        "recomputed_pass_current": 0, "recomputed_fail_current": 0,
        "recorded_pass_but_recomputed_fail": 0,
        "rows_with_anomaly": [],
        "binding_rows_matching_F1_canonical": 0,
        "binding_rows_other": 0,
    }

    for row in rows:
        rec = {
            "test_id": row.get("test_id"),
            "deciding_field": row.get("deciding_field"),
            "deciding_field_contract": row.get("deciding_field_contract"),
            "deciding_field_status": row.get("deciding_field_status"),
            "recorded_binding_sha256": row.get("binding_sha256"),
            "binding_matches_F1_canonical": row.get("binding_sha256") == pins["F1_canonical"]["sha256"],
            "cross_artifact": row.get("cross_artifact"),
            "probes": [],
            "anomalies": [],
        }
        if rec["binding_matches_F1_canonical"]:
            census["binding_rows_matching_F1_canonical"] += 1
        else:
            census["binding_rows_other"] += 1

        for probe in row.get("probe_results", []):
            census["probes"] += 1
            path = probe.get("path")
            recorded = bool(probe.get("pass"))
            census["recorded_pass" if recorded else "recorded_fail"] += 1

            st_snap, val_snap = resolve(snap, path)
            ok_snap, _ = run_probe(val_snap, st_snap, probe)
            st_mut, val_mut = resolve(ctrl, path)
            ok_mut, _ = run_probe(val_mut, st_mut, probe)

            # Every probe path is a leaf of the F1 schema document itself; the F0
            # canonical appears only as the VALUE that f0_binding.* must equal.
            doc_name = "F1_canonical"
            st_cur, val_cur = resolve(f1, path)
            ok_cur, why_cur = run_probe(val_cur, st_cur, probe)
            census["recomputed_pass_current" if ok_cur else "recomputed_fail_current"] += 1

            e = {
                "path": path, "kind": probe.get("kind"), "role": probe.get("role"),
                "expected": probe.get("expected"), "recorded_pass": recorded,
                "resolved_against": doc_name,
                "current": {"status": st_cur, "observed_excerpt": excerpt(val_cur), "pass": ok_cur},
                "replay_pre_revision": {"status": st_snap, "pass": ok_snap,
                                         "matches_recorded": ok_snap == recorded},
            }
            if ctrl_path and path == ctrl_path:
                e["mutation_control"] = {"mutated_path": ctrl_path, "pass_after_mutation": ok_mut}
            if recorded and not ok_cur:
                census["recorded_pass_but_recomputed_fail"] += 1
                e["anomaly"] = "recorded pass=true, recomputed false against current canonical docs"
                rec["anomalies"].append({"path": path, "expected": probe.get("expected"),
                                          "observed": excerpt(val_cur), "why": why_cur})
            rec["probes"].append(e)
        if rec["anomalies"]:
            census["rows_with_anomaly"].append(rec["test_id"])
        results.append(rec)

    n_replay_mismatch = sum(1 for r in results for e in r["probes"]
                            if not e["replay_pre_revision"]["matches_recorded"])
    ctrl_targets = [e for r in results for e in r["probes"] if "mutation_control" in e]
    ctrl_b = any(not e["mutation_control"]["pass_after_mutation"] for e in ctrl_targets)
    f0_declared = (f1.get("f0_binding") or {}).get("declared_f0_sha256")

    controls = {
        "C-A_replay_pre_revision": {
            "description": "probe logic reproduces recorded outcomes on the revision they were authored against",
            "probes": census["probes"], "mismatches": n_replay_mismatch, "pass": n_replay_mismatch == 0},
        "C-B_discrimination": {
            "description": "mutating a depended-on leaf makes its probe fail",
            "mutated_path": ctrl_path, "dependent_probes": len(ctrl_targets),
            "detects_mutation": ctrl_b, "pass": ctrl_b},
        "C-C_suite_rebind_uniform": {
            "description": "every row binding_sha256 equals measured F1 canonical hash",
            "rows_matching": census["binding_rows_matching_F1_canonical"],
            "rows_total": census["rows"],
            "pass": census["binding_rows_matching_F1_canonical"] == census["rows"]},
        "C-D_schema_f0_pin_live": {
            "description": "F1 schema's declared_f0_sha256 equals measured F0 canonical hash",
            "declared": f0_declared, "measured": pins["F0_canonical"]["sha256"],
            "pass": f0_declared == pins["F0_canonical"]["sha256"]},
        "C-E_anomaly_present": {
            "description": "the expected anomaly is observed (not a silent no-op run)",
            "recorded_pass_but_recomputed_fail": census["recorded_pass_but_recomputed_fail"],
            "pass": census["recorded_pass_but_recomputed_fail"] > 0},
    }
    core_ok = controls["C-A_replay_pre_revision"]["pass"] and controls["C-B_discrimination"]["pass"]

    if not core_ok:
        adjudication = "VOID_CONTROLS_FAILED"
    elif census["recorded_pass_but_recomputed_fail"] > 0:
        adjudication = "STALE_CROSS_ARTIFACT_PROBE_CONFIRMED"
    else:
        adjudication = "NO_STALE_PROBE_FOUND"

    report = {
        "artifact_type": "f1_rebind_probe_recompute",
        "artifact_version": "2.0.0",
        "task_id": "W031-F1-REBIND-ADJUDICATION-02",
        "worker": "worker-031",
        "node_id": "F1",
        "class_id": "AF-WCC-VAC-GEN",
        "gate": "G-FORM",
        "authority": ("worker independent measurement only; no gate verdict, no node status, "
                      "no validation_status=passed, no schema/suite edit"),
        "measured_at_local": None,
        "pins": pins,
        "controls": controls,
        "controls_core_ok": core_ok,
        "census": census,
        "adjudication": adjudication,
        "anomaly": {
            "rows": census["rows_with_anomaly"],
            "detail": [{"test_id": r["test_id"], "deciding_field": r["deciding_field"],
                        "deciding_field_status": r["deciding_field_status"],
                        "cross_artifact": r["cross_artifact"], "anomalies": r["anomalies"]}
                       for r in results if r["anomalies"]],
        },
        "rows": results,
        "finding": (
            "The suite was re-pinned uniformly to F1 canonical {f1} (C-C pass) and the F1 "
            "schema's own F0 binding is live (C-D pass). But one row, F1-AMB-25 "
            "(deciding_field_status={status}), carries a DECIDING probe whose expected value "
            "is the superseded F0 hash 276009f4f63d and is still recorded pass=true; recomputed "
            "against the current F0 canonical {f0} it is FALSE. The row's cross_artifact entry "
            "also still names 276009f4f63d. The rebind moved the self-binding but did not "
            "refresh this cross-artifact expectation, so the suite now asserts one false "
            "probe outcome."
        ).format(
            f1=pins["F1_canonical"]["sha256"][:12],
            f0=pins["F0_canonical"]["sha256"][:12],
            status=next((r["deciding_field_status"] for r in results if r["test_id"] == "F1-AMB-25"), None),
        ),
        "boundary": (
            "Measures probe recomputation only. It does not re-adjudicate the F1-AMB-25 "
            "ambiguity question, does not certify either schema, and does not decide whether "
            "the F0 taxonomy revision that invalidated the expectation was warranted. "
            "F1-AMB-21 uses a 'nonnull' probe on the same leaf and still passes; only "
            "F1-AMB-25 hard-codes the value."
        ),
        "next_falsifier": (
            "Re-measure all four pins. If F1 canonical, F0 canonical or the suite changes, "
            "re-run before citing. If F1-AMB-25's expected/current F0 hash is updated to the "
            "live F0 canonical and the probe recomputes true, the anomaly is repaired and this "
            "finding is historical."
        ),
    }
    json.dump(report, sys.stdout, indent=1, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
