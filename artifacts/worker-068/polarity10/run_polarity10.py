#!/usr/bin/env python3
"""W068-FORM-POLARITY-10 runner.

Runs the two pinned class-binding stages over the polarity probe corpus:
  stage A (structural): artifacts/formulation/tools/check_class_schema.py --json FIXTURE
  stage B (semantic):   artifacts/worker-06/spec_conformance_audit.py FIXTURE --json OUT

A probe "escapes" iff BOTH stages accept it.

Validity (measurement integrity) requires: no fixture tamper, stage tools + rule spec
at the manifest hashes, and every known-rejected liveness control rejected. A class
arm is INFORMATIVE only if its identity (unmutated) control is accepted by both
stages; if the unmutated base is rejected, every probe in that arm is rejected for
reasons unrelated to the probe op, and the arm is excluded from the primary escape
aggregate (it is still reported raw, and the base rejection is itself a finding).

Stage A also reads artifacts/formulation/KEY_MANIFEST.json, which is NOT hashed by
the stage tool; its measured sha256 is recorded here as an input dependency.

Live canonical schema hashes are measured before and after the run and recorded as
context only: the probe targets the pinned pipeline over a shipped byte snapshot, so
a later canonical republish does not invalidate the fixture set.

Writes raw_verdicts.json and report.json. Never sets a map gate verdict or a node
status; every output is a measurement for the lead/controller to adjudicate.

Usage: python3 run_polarity10.py
Exit: 0 run completed (valid or not); 2 precondition failure.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
CST = timezone(timedelta(hours=8))
MANIFEST = HERE / "manifest.json"
DIAG = HERE / "diag"
PY = sys.executable

CANON = [
    "schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
]
KEY_MANIFEST = "artifacts/formulation/KEY_MANIFEST.json"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def measure_key_manifest() -> dict:
    p = ROOT / KEY_MANIFEST
    out = {"path": KEY_MANIFEST, "sha256": sha256_file(p), "bytes": p.stat().st_size,
           "mtime": datetime.fromtimestamp(p.stat().st_mtime, CST).isoformat(timespec="seconds"),
           "pinned_by_stage_hash": False,
           "note": "stage A (structural) reads this file; it is not covered by the stage tool sha256."}
    try:
        km = json.loads(p.read_text())
        allowed = km.get("allowed_keys", [])
        out["allowed_key_count"] = len(allowed)
        out["allows_revised_at_unused"] = "revised_at_unused" in allowed
    except Exception as exc:  # pragma: no cover
        out["parse_error"] = str(exc)
    return out


def run_cmd(args, timeout=120):
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=timeout, cwd=str(ROOT))
        return {"exit": p.returncode, "stdout": p.stdout, "stderr": p.stderr[-4000:]}
    except subprocess.TimeoutExpired:
        return {"exit": 124, "stdout": "", "stderr": f"timeout after {timeout}s"}


def parse_json(text):
    try:
        return json.loads(text)
    except Exception:
        return None


def main() -> int:
    manifest_bytes = MANIFEST.read_bytes()
    manifest_sha = hashlib.sha256(manifest_bytes).hexdigest()
    m = json.loads(manifest_bytes)
    tb = m["target_binding"]
    stages = tb["stages"]

    invalid_reasons = []

    for key in ("structural", "semantic", "rule_spec"):
        rel, expected = stages[key], stages[key + "_sha256"]
        live = sha256_file(ROOT / rel)
        if live != expected:
            invalid_reasons.append(f"stage drift: {rel} {expected[:12]} -> {live[:12]}")

    key_manifest = measure_key_manifest()
    canon_before = {rel: sha256_file(ROOT / rel) for rel in CANON}

    results = []
    for fx in m["fixtures"]:
        path = ROOT / fx["fixture"]
        disk_sha = sha256_file(path)
        if disk_sha != fx["sha256"]:
            invalid_reasons.append(f"fixture hash mismatch (tamper): {fx['fixture']}")

        a = run_cmd([PY, str(ROOT / stages["structural"]), "--json", str(path)])
        a_json = parse_json(a["stdout"])
        a_verdict = (a_json or {}).get("verdict", "error")
        a_rules = (a_json or {}).get("failed_rules", [])
        a_failures = (a_json or {}).get("failures", [])

        diag_out = DIAG / (Path(fx["fixture"]).stem + ".semantic.json")
        b = run_cmd([PY, str(ROOT / stages["semantic"]), str(path), "--json", str(diag_out)])
        b_json = parse_json(b["stdout"]) or {}
        b_verdict = b_json.get("verdict", "error")
        b_rules = b_json.get("failed_rules", [])
        diag_json = parse_json(diag_out.read_text()) if diag_out.is_file() else None
        b_checks = (diag_json or b_json).get("checks", [])

        caught_a = a_verdict != "pass"
        caught_b = b_verdict != "accept"
        escaped = (not caught_a) and (not caught_b)
        results.append({
            "fixture": fx["fixture"],
            "file": fx["file"],
            "base": fx["base"],
            "class_id": fx["class_id"],
            "family": fx["family"],
            "op_id": fx["op_id"],
            "op_kind": fx["op_kind"],
            "expectation": fx["expectation"],
            "expected_catcher_rules": fx["expected_catcher_rules"],
            "sha256": fx["sha256"],
            "stage_a": {"exit": a["exit"], "verdict": a_verdict, "failed_rules": a_rules,
                        "failures": a_failures[:6], "stderr": a["stderr"][-800:]},
            "stage_b": {"exit": b["exit"], "verdict": b_verdict, "failed_rules": b_rules,
                        "undecided_rules": b_json.get("undecided_rules", []),
                        "failed_checks": [c for c in b_checks if c.get("verdict") == "fail"][:8],
                        "stderr": b["stderr"][-800:]},
            "caught_stage_a": caught_a,
            "caught_stage_b": caught_b,
            "caught_union": caught_a or caught_b,
            "escaped_union": escaped,
        })

    canon_after = {rel: sha256_file(ROOT / rel) for rel in CANON}
    at_build = {v["canonical_path"]: v["measured_sha256"]
                for v in tb["canonical_bases_measured_at_build"].values()}
    live_drift = {rel: {"at_build": at_build[rel], "before_run": canon_before[rel], "after_run": canon_after[rel]}
                  for rel in CANON
                  if not (at_build[rel] == canon_before[rel] == canon_after[rel])}

    probes = [r for r in results if r["expectation"] == "should_be_caught"]
    controls = [r for r in results if r["expectation"] == "must_be_accepted"]
    known = [r for r in results if r["expectation"] == "known_rejected_positive_control"]
    refs = [r for r in results if r["expectation"] == "known_escape_reference"]

    # ---- arm calibration: is the unmutated base accepted by both stages? ----------
    identity = {r["base"]: r for r in controls}
    arms = {}
    for base in ("W", "C2", "C0"):
        r = identity.get(base)
        if r is None:
            arms[base] = {"informative": False, "reason": "no identity control"}
            continue
        ok = r["stage_a"]["verdict"] == "pass" and r["stage_b"]["verdict"] == "accept"
        arms[base] = {
            "informative": ok,
            "identity_fixture": r["file"],
            "identity_stage_a": r["stage_a"]["verdict"],
            "identity_stage_a_failed_rules": r["stage_a"]["failed_rules"],
            "identity_stage_b": r["stage_b"]["verdict"],
            "identity_stage_b_failed_rules": r["stage_b"]["failed_rules"],
            "identity_stage_b_failed_checks": r["stage_b"]["failed_checks"],
            "reason": "unmutated base accepted by both stages" if ok
                      else "unmutated base rejected: probes in this arm are non-informative about the probe op",
        }

    primary = [r for r in probes if arms.get(r["base"], {}).get("informative")]
    non_informative = [r for r in probes if not arms.get(r["base"], {}).get("informative")]
    escaped_probes = [r for r in probes if r["escaped_union"]]
    escaped_primary = [r for r in primary if r["escaped_union"]]
    false_positives = [r for r in controls if not (r["stage_a"]["verdict"] == "pass" and r["stage_b"]["verdict"] == "accept")]
    known_accepted = [r for r in known if not r["caught_union"]]

    # ---- validity: integrity only; a rejecting base is a finding, not an invalid run --
    if known_accepted:
        invalid_reasons.append("KNOWN-REJECTED POSITIVE CONTROLS ACCEPTED (evaluator dead): "
                               + ", ".join(r["file"] for r in known_accepted))
    valid = not invalid_reasons

    def rate(rows, key="escaped_union"):
        n = len(rows)
        return (sum(1 for r in rows if r[key]) / n) if n else None

    def group(rows, by):
        out = {}
        for r in rows:
            d = out.setdefault(r[by], {"probes": 0, "escaped": 0, "caught_stage_a": 0,
                                       "caught_stage_b": 0, "escaped_fixtures": [], "caught_fixtures": []})
            d["probes"] += 1
            d["escaped"] += int(r["escaped_union"])
            d["caught_stage_a"] += int(r["caught_stage_a"])
            d["caught_stage_b"] += int(r["caught_stage_b"])
            (d["escaped_fixtures"] if r["escaped_union"] else d["caught_fixtures"]).append(r["file"])
        for d in out.values():
            d["escape_rate"] = d["escaped"] / d["probes"]
        return out

    per_class = group(primary, "base")
    per_op = group(primary, "op_id")
    per_class_all = group(probes, "base")

    rule_hits = {}
    for r in probes:
        for rule in r["expected_catcher_rules"]:
            if rule == "NONE":
                continue
            fired = rule in (r["stage_a"]["failed_rules"] + r["stage_b"]["failed_rules"])
            d = rule_hits.setdefault(rule, {"expected": 0, "fired": 0, "missed_fixtures": []})
            d["expected"] += 1
            if fired:
                d["fired"] += 1
            else:
                d["missed_fixtures"].append(r["file"])
    for rule, d in rule_hits.items():
        d["fired_rate"] = d["fired"] / d["expected"]

    wcc_finding = None
    if not arms["W"]["informative"]:
        wcc_finding = {
            "finding": "WCC arm non-informative: stage B rejects the unmutated canonical WCC base",
            "base": "W",
            "class_id": "AF-WCC-VAC-GEN",
            "identity_fixture": arms["W"]["identity_fixture"],
            "stage_a": arms["W"]["identity_stage_a"],
            "stage_b": arms["W"]["identity_stage_b"],
            "stage_b_failed_rules": arms["W"]["identity_stage_b_failed_rules"],
            "stage_b_failed_checks": arms["W"]["identity_stage_b_failed_checks"],
            "consequence": ("all 6 WCC probes are rejected regardless of the polarity op; their catches are not "
                            "evidence that polarity is detected. The live canonical WCC schema was separately "
                            "re-run in place by worker-068 and returns the same stage B R03 verdict."),
        }

    ref = refs[0] if refs else None
    masking_finding = None
    if ref is not None:
        masking_finding = {
            "finding": "FORM-HELDOUT-09 reference escape is now masked by an unpinned input dependency",
            "reference_fixture": ref["file"],
            "reference_sha256": ref["sha256"],
            "stage_a": ref["stage_a"]["verdict"],
            "stage_a_failed_rules": ref["stage_a"]["failed_rules"],
            "stage_a_failures": ref["stage_a"]["failures"],
            "stage_b": ref["stage_b"]["verdict"],
            "escaped_union_before": True,
            "escaped_union_now": ref["escaped_union"],
            "key_manifest": key_manifest,
            "mechanism": ("stage A now fails the unchanged rev11-vintage fixture on R22 key hygiene because "
                          "'revised_at_unused' is absent from the current KEY_MANIFEST allowlist; stage B still "
                          "accepts it. The catch is therefore attributable to KEY_MANIFEST.json, an input not "
                          "pinned by FROZEN/HELDOUT-09, and not to any conclusion-polarity check."),
            "control": ("the rebuilt probe p7_heldout09_conclusion_negation_rebuilt applies the identical C0 "
                        "conclusion inversion to the rev12 base (which has no stale key); if it escapes, the "
                        "blind spot persists and the original catch is key-hygiene only."),
        }

    raw = {
        "corpus_id": m["corpus_id"],
        "task_id": m["task_id"],
        "actor": "worker-068",
        "run_at": datetime.now(CST).isoformat(timespec="seconds"),
        "manifest_sha256_before_run": manifest_sha,
        "target_binding": tb,
        "input_dependencies": {"key_manifest": key_manifest},
        "canonical_live_before_run": canon_before,
        "canonical_live_after_run": canon_after,
        "live_canonical_drift_observed": live_drift,
        "stage_hashes": {k: stages[k + "_sha256"] for k in ("structural", "semantic", "rule_spec")},
        "arm_calibration": arms,
        "valid": valid,
        "invalid_reasons": invalid_reasons,
        "fixtures": results,
    }
    (HERE / "raw_verdicts.json").write_text(json.dumps(raw, indent=2) + "\n")

    report = {
        "corpus_id": m["corpus_id"],
        "task_id": m["task_id"],
        "worker": "worker-068",
        "actor": "worker-068",
        "generated_at": datetime.now(CST).isoformat(timespec="seconds"),
        "manifest_sha256_before_run": manifest_sha,
        "target_binding": tb,
        "input_dependencies": {"key_manifest": key_manifest},
        "live_canonical_drift_observed": live_drift,
        "valid": valid,
        "invalid_reasons": invalid_reasons,
        "stages": raw["stage_hashes"],
        "arm_calibration": arms,
        "counts": m["counts"],
        "aggregates": {
            "probes_all": len(probes),
            "probes_all_escaped_union": len(escaped_probes),
            "probe_union_escape_rate_all": rate(probes),
            "probes_informative": len(primary),
            "probes_informative_escaped_union": len(escaped_primary),
            "probe_union_escape_rate_informative": rate(primary),
            "probes_non_informative": len(non_informative),
            "probes_caught_stage_a": sum(1 for r in probes if r["caught_stage_a"]),
            "probes_caught_stage_b": sum(1 for r in probes if r["caught_stage_b"]),
            "probes_caught_union": sum(1 for r in probes if r["caught_union"]),
            "identity_controls": len(controls),
            "identity_controls_accepted": sum(1 for r in controls if r["escaped_union"]),
            "known_rejected_controls": len(known),
            "known_rejected_controls_rejected": sum(1 for r in known if r["caught_union"]),
            "known_escape_references": len(refs),
            "known_escape_references_still_escaping": sum(1 for r in refs if r["escaped_union"]),
        },
        "per_class_informative": per_class,
        "per_class_all": per_class_all,
        "per_op_informative": per_op,
        "expected_rule_hit_matrix": rule_hits,
        "escaped_probes_informative": [
            {
                "fixture": r["fixture"], "class_id": r["class_id"], "op_id": r["op_id"], "family": r["family"],
                "leak_claim": next(f["leak_claim"] for f in m["fixtures"] if f["fixture"] == r["fixture"]),
                "stage_a": r["stage_a"]["verdict"], "stage_b": r["stage_b"]["verdict"],
                "why_not_caught": "neither stage A failed nor stage B rejected this fixture",
            }
            for r in escaped_primary
        ],
        "caught_probes": [
            {
                "fixture": r["fixture"], "class_id": r["class_id"], "op_id": r["op_id"],
                "stage_a": r["stage_a"]["verdict"], "failed_rules_a": r["stage_a"]["failed_rules"],
                "stage_b": r["stage_b"]["verdict"], "failed_rules_b": r["stage_b"]["failed_rules"],
            }
            for r in probes if r["caught_union"]
        ],
        "identity_control_results": [
            {"fixture": r["fixture"], "base": r["base"], "stage_a": r["stage_a"]["verdict"],
             "failed_rules_a": r["stage_a"]["failed_rules"], "stage_b": r["stage_b"]["verdict"],
             "failed_rules_b": r["stage_b"]["failed_rules"], "accepted": r["escaped_union"]} for r in controls
        ],
        "known_rejected_control_results": [
            {"fixture": r["fixture"], "stage_a": r["stage_a"]["verdict"], "failed_rules_a": r["stage_a"]["failed_rules"],
             "stage_b": r["stage_b"]["verdict"], "caught_union": r["caught_union"]} for r in known
        ],
        "heldout09_reference_result": [
            {"fixture": r["fixture"], "sha256": r["sha256"], "stage_a": r["stage_a"]["verdict"],
             "failed_rules_a": r["stage_a"]["failed_rules"], "stage_b": r["stage_b"]["verdict"],
             "escaped_union": r["escaped_union"]}
            for r in refs
        ],
        "findings": [f for f in (wcc_finding, masking_finding) if f],
        "binding_scope": [
            "Claim scope is the pinned pipeline (stage A sha, stage B sha, rule spec sha, KEY_MANIFEST sha recorded) applied to the shipped fixture bytes.",
            "The bases are byte copies of the canonical schemas measured at build time; live canonical republish after build is recorded as context and does not change the fixture set.",
            "Probe labels ('should_be_caught') are the author's and follow from class-binding: a schema asserting the negation of the class conclusion is not a valid instance of the class. Independent adjudication is required before escape families are cited.",
            "Primary escape aggregate covers only arms whose unmutated base is accepted by both stages.",
        ],
        "limitations": [
            "Author-built corpus: leak labels are worker-068's, calibrated only by the rule spec; an independent reviewer must adjudicate them.",
            "Stage B is worker-06's semantic auditor, not the F2 gate; a probe accepted by both stages is an escape from this pipeline, not proof that a class is wrong.",
            "Stage A has an unpinned data dependency (KEY_MANIFEST.json): verdicts on unchanged fixture bytes are not stable across KEY_MANIFEST revisions.",
            "Probe ops are lexical/polarity edits to conclusion fields; they do not cover every content-inversion family (e.g. hypothesis substitution, quantifier-domain change).",
            "This is measurement only: no gate verdict, no node completion, no theorem, no R11 extension.",
        ],
        "next_falsifier": (
            "An independent re-run at the same pinned stage hashes that classifies any probe differently; an independent "
            "reviewer showing a probe is not a well-formed conclusion-content inversion (or that a probe is not class-bound); "
            "or a gate revision at a new stage/rule-spec hash that catches probes reported as escaping here."
        ),
    }
    (HERE / "report.json").write_text(json.dumps(report, indent=2) + "\n")

    print(json.dumps({
        "valid": valid,
        "invalid_reasons": invalid_reasons,
        "arm_calibration": {k: v["informative"] for k, v in arms.items()},
        "probes_all": len(probes),
        "escaped_all": len(escaped_probes),
        "probes_informative": len(primary),
        "escaped_informative": len(escaped_primary),
        "union_escape_rate_informative": rate(primary),
        "caught_stage_a": sum(1 for r in probes if r["caught_stage_a"]),
        "caught_stage_b": sum(1 for r in probes if r["caught_stage_b"]),
        "identity_controls_accepted": f"{sum(1 for r in controls if r['escaped_union'])}/{len(controls)}",
        "known_rejected_rejected": f"{sum(1 for r in known if r['caught_union'])}/{len(known)}",
        "heldout09_reference_escapes": f"{sum(1 for r in refs if r['escaped_union'])}/{len(refs)}",
        "live_canonical_drift": live_drift,
        "escaped_informative": [r["file"] for r in escaped_primary],
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
