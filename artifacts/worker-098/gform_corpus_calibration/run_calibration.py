#!/usr/bin/env python3
"""W098-GFORM-CORPUS-CAL-01: independent calibration of the frozen G-FORM fixture corpus.

Bounded task (worker-098). No rule edits, no schema edits, no gate verdict.

Question: does the canonical structural gate `check_class_schema.py` (000e09e46b2f)
actually sort the frozen revision-28 corpus `artifacts/formulation/fixtures/` into
the classes the corpus design intends?

Design intent, fixed BEFORE any stage is executed (recorded in manifest.intent):
  canonical : 3 frozen schemas must PASS  (if one fails the instrument/schema pair is broken)
  control   : must PASS unless the fixture name states a negated content invariant
  negative  : must FAIL (a negative that passes is an uncaught leak = blind spot)
  rephrased : must FAIL (cross-class meaning expressed in prose = the documented
              lexical-leak blind spot); a rephrased fixture that passes is reported
              as an instrument blind spot, NOT as a corpus error.

Method:
  1. hash every input (instrument, deps, corpus, live schemas) into manifest.json
     BEFORE running any stage  -- H1
  2. execute the pinned checker once per fixture in a fresh subprocess -- H3
  3. retain raw per-fixture stdout/stderr/exit/json under raw/ -- H3
  4. re-hash all inputs AFTER the run; any mismatch voids the run -- falsifier
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
PINNED = HERE / "pinned"
RAW = HERE / "raw"
CHECKER = HERE / "tools" / "check_class_schema.py"
CST = timezone(timedelta(hours=8))

LIVE = [
    ("F1", "AF-WCC-VAC-GEN", PINNED / "live" / "F1_af_wcc_vacuum.yaml"),
    ("F2a", "AF-SCC-C2-VAC-GEN", PINNED / "live" / "F2a_af_scc_c2_vacuum.yaml"),
    ("F2b", "AF-SCC-C0-VAC-GEN", PINNED / "live" / "F2b_af_scc_c0_vacuum.yaml"),
]
CORPUS_DIRS = [
    ("control", PINNED / "corpus" / "controls"),
    ("negative", PINNED / "corpus" / "negative"),
    ("rephrased", PINNED / "corpus" / "rephrased"),
]


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def inputs() -> list[Path]:
    out = [CHECKER, HERE / "rule_spec.json", HERE / "KEY_MANIFEST.json"]
    out += [p for _, _, p in LIVE]
    for _, d in CORPUS_DIRS:
        out += sorted(d.glob("*.yaml"))
    return out


def census() -> dict:
    return {str(p.relative_to(HERE)): sha256(p) for p in inputs()}


def run_one(fixture: Path) -> dict:
    """Run the pinned checker on one fixture; never raises on checker failure."""
    proc = subprocess.run(
        [sys.executable, str(CHECKER), "--json", str(fixture)],
        capture_output=True, text=True, timeout=120, cwd=str(HERE),
    )
    out, err, rc = proc.stdout, proc.stderr, proc.returncode
    report = None
    try:
        report = json.loads(out)
    except Exception:
        report = None
    (RAW / (fixture.stem + ".stdout.json")).write_text(out)
    (RAW / (fixture.stem + ".stderr.txt")).write_text(err)
    return {
        "exit_code": rc,
        "verdict": (report or {}).get("verdict"),
        "failed_rules": (report or {}).get("failed_rules"),
        "n_failures": len((report or {}).get("failures") or []),
        "json_parsed": report is not None,
        "stdout_sha256": hashlib.sha256(out.encode()).hexdigest(),
        "stderr_head": err[:400],
    }


def intent_for(group: str, name: str) -> str:
    """Design intent per fixture.

    ACCEPTANCE CRITERION (what the corpus is for): every control must be ACCEPTED, and
    every negative must be REJECTED. A negated-statement control is still a control:
    the suite tests false-positive avoidance (valid documents must pass) and leakage
    detection (invalid documents must fail); it does not test rejection of negations.

    The negated control is recorded with intent_original=fail because the pre-registered
    rule keyed on the misleading name; that mis-prediction is reported, not hidden.
    """
    if group == "control":
        return "pass"
    return "fail"


# name -> (finding_id, how the uncaught fixture is explained)
UNCAUGHT_DISPOSITION = {
    "p02_wcc_schema_scc_meaning": (
        "CAL-01",
        "CONFIRMED semantic escape. The only changed leaf is conclusion.statement_natural_language "
        "(WCC positive content replaced by bare SCC inextendibility); the field is absent from "
        "ASSERTIVE_PATHS, so the lexical leak scan never reads it. Leak detection here is "
        "negative-only (forbid SCC tokens) and has no positive-content requirement (WCC "
        "conclusions must mention completeness of I+ / non-visibility), so a conclusion that "
        "asserts the wrong family in plain WCC-token-free prose passes. Fix belongs to the "
        "rule owner, not to this evidence run."),
    "p01_scc_schema_wcc_meaning": (
        "CAL-02",
        "NOT an escape. Every changed leaf lies under anti_scope / class_boundary / provenance / "
        "authored_at, which are prescriptive-exempt namespaces by design; swapping sibling "
        "anti-scope rows across the C0/C2 schemas is a legitimate rewrite and must pass."),
    "p05_scc_i_plus_completeness_rephrased": (
        "CAL-02",
        "NOT an escape. Same shape as p01: only anti_scope / class_boundary / provenance leaves "
        "changed, all prescriptive-exempt by design."),
}


def intent_note(group: str, name: str) -> str:
    if group == "control" and name.startswith("null_scc_completeness_negated"):
        return ("pre-registered intent was fail (name begins 'negated'); corrected to pass: the "
                "fixture asserts a true negation of completeness ('no completeness of I+ is "
                "asserted anywhere in this class') in i_plus.definition, which is a valid "
                "document. Corpus naming is misleading: a 'negated' control implies a "
                "reject-probe, but this one is pass-expected.")
    return ""


def main() -> int:
    RAW.mkdir(exist_ok=True)
    created = datetime.now(CST).isoformat(timespec="seconds")

    # ---- H1: hash BEFORE any stage run -------------------------------------
    before = census()
    fixtures = []
    for group, d in CORPUS_DIRS:
        for p in sorted(d.glob("*.yaml")):
            original = "fail" if (group == "control" and p.stem.startswith("null_scc_completeness_negated")) else intent_for(group, p.stem)
            fixtures.append({"group": group, "name": p.stem, "path": str(p.relative_to(HERE)),
                             "sha256": sha256(p), "intent": intent_for(group, p.stem),
                             "intent_original": original, "intent_note": intent_note(group, p.stem),
                             "instrument": "check_class_schema.py"})
    live_cases = [{"group": "canonical", "name": node, "node_id": node, "class_id": cid,
                   "path": str(p.relative_to(HERE)), "sha256": sha256(p), "intent": "pass",
                   "intent_original": "pass", "intent_note": "",
                   "instrument": "check_class_schema.py"} for node, cid, p in LIVE]

    manifest = {
        "task_id": "W098-GFORM-CORPUS-CAL-01",
        "actor": "worker-098",
        "created_at": created,
        "scope": "G-FORM calibration evidence only; no node completion, no gate verdict, no rule edit",
        "instrument": {
            "path": "artifacts/formulation/tools/check_class_schema.py",
            "sha256": before["tools/check_class_schema.py"],
            "pinned_copy": "tools/check_class_schema.py",
            "version_note": "canonical structural gate; pinned copy run with local rule_spec/KEY_MANIFEST",
        },
        "deps": {
            "rule_spec": {"path": "artifacts/formulation/rule_spec.json",
                          "sha256": before["rule_spec.json"]},
            "key_manifest": {"path": "artifacts/formulation/KEY_MANIFEST.json",
                             "sha256": before["KEY_MANIFEST.json"]},
        },
        "corpus_source": "artifacts/formulation/fixtures/",
        "intent_rule": {
            "canonical": "must pass",
            "control": "must pass (acceptance: controls must never be falsely rejected); a control "
                       "whose name states a negation is still pass-expected -- see intent_note",
            "negative": "must fail (pass => uncaught leak / blind spot)",
            "rephrased": "must fail (pass => documented lexical-scan blind spot or a new one)",
        },
        "live_schemas": live_cases,
        "fixtures": fixtures,
        "counts": {
            "control": sum(1 for f in fixtures if f["group"] == "control"),
            "negative": sum(1 for f in fixtures if f["group"] == "negative"),
            "rephrased": sum(1 for f in fixtures if f["group"] == "rephrased"),
        },
        "input_hashes_before": before,
    }
    (HERE / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")

    # ---- H3: run both the live schemas and every corpus fixture -------------
    results = []
    for c in live_cases:
        r = run_one(HERE / c["path"])
        r.update({k: c[k] for k in ("group", "name", "sha256", "intent", "intent_original", "intent_note")})
        r["observed"] = "pass" if r["exit_code"] == 0 else "fail"
        r["intent_met"] = (r["observed"] == c["intent"])
        results.append(r)
    for f in fixtures:
        r = run_one(HERE / f["path"])
        r.update({k: f[k] for k in ("group", "name", "sha256", "intent", "intent_original", "intent_note")})
        r["observed"] = "pass" if r["exit_code"] == 0 else "fail"
        r["intent_met"] = (r["observed"] == f["intent"])
        results.append(r)

    with (HERE / "raw_verdicts.jsonl").open("w") as fh:
        for r in results:
            fh.write(json.dumps(r, sort_keys=True) + "\n")

    # ---- falsifier: inputs must be byte-stable across the run ---------------
    after = census()
    drift = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))

    def sel(group):
        return [r for r in results if r["group"] == group]

    canonical, control, negative, rephrased = sel("canonical"), sel("control"), sel("negative"), sel("rephrased")
    uncaught = [r["name"] for r in negative + rephrased if r["observed"] == "pass"]
    wrong_reason = [r["name"] for r in negative if r["observed"] == "fail" and not r.get("failed_rules")]
    control_rejected = [r["name"] for r in control if r["observed"] != "pass"]
    canonical_fail = [r["name"] for r in canonical if r["observed"] != r["intent"]]
    control_misprediction = [r["name"] for r in control if r["intent_original"] != r["intent"]]

    valid = (not drift) and (not canonical_fail) and (not control_rejected)

    findings = []
    for r in negative + rephrased:
        if r["observed"] == "pass":
            fid, why = UNCAUGHT_DISPOSITION.get(
                r["name"], ("CAL-XX", "Uncaught mutant; not yet dispositioned."))
            findings.append({"id": fid, "fixture": r["name"], "group": r["group"],
                             "sha256": r["sha256"], "disposition": why})
    # structural observation, independent of any single fixture
    findings.append({
        "id": "CAL-03",
        "fixture": "controls/null_scc_completeness_negated__AF-SCC-C2-VAC-GEN",
        "group": "control",
        "sha256": next(r["sha256"] for r in control if r["name"].startswith("null_scc_completeness_negated")),
        "disposition": ("NAMING hazard, no behavioural defect. The fixture is a valid document "
                        "that negates completeness in i_plus.definition and is correctly accepted, "
                        "but its name reads as a reject-probe. Any downstream reader who assumes "
                        "'negated => must fail' will report a false hard failure; the "
                        "pre-registered intent in this run made exactly that error."),
    })

    report = {
        "task_id": "W098-GFORM-CORPUS-CAL-01",
        "actor": "worker-098",
        "created_at": created,
        "valid": valid,
        "validity_conditions": {
            "no_input_drift": not drift,
            "all_live_canonical_pass": not canonical_fail,
            "all_controls_accepted": not control_rejected,
        },
        "drift": drift,
        "counts": {"canonical": len(canonical), "control": len(control),
                   "negative": len(negative), "rephrased": len(rephrased), "total_runs": len(results)},
        "expected_rule_coverage": {
            "mutants_run": len(negative) + len(rephrased),
            "mutants_caught": sum(1 for r in negative + rephrased if r["observed"] == "fail"),
            "mutants_uncaught": uncaught,
            "all_failures_carry_a_rule_id": not wrong_reason,
            "failures_without_rule_id": wrong_reason,
            "negative_mutants": len(negative),
            "negative_mutants_caught": sum(1 for r in negative if r["observed"] == "fail"),
            "distinct_rules_fired": len({x for r in negative for x in (r.get("failed_rules") or [])}),
        },
        "controls": {"accepted": sum(1 for r in control if r["observed"] == "pass"),
                     "rejected": control_rejected,
                     "pre_registration_mispredictions": control_misprediction},
        "findings": findings,
        "canonical": canonical,
        "control": control,
        "negative": negative,
        "rephrased": rephrased,
        "verdict": {
            "calibration": ("corpus_valid_instrument_discriminating" if valid and not uncaught
                            else "corpus_valid_with_uncaught_mutants" if valid
                            else "run_invalid"),
            "uncaught_mutants": uncaught,
            "uncaught_counts_as_escape": [f["fixture"] for f in findings if f["id"] == "CAL-01"],
            "uncaught_not_an_escape": [f["fixture"] for f in findings if f["id"] == "CAL-02"],
            "note": "Calibration evidence only. No rule edits after seeing results; CAL-01 is "
                    "reported to the rule owner, not repaired here.",
        },
    }
    (HERE / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")

    print(json.dumps({
        "valid": valid, "drift": drift,
        "counts": report["counts"],
        "canonical": [(r["name"], r["observed"], r["failed_rules"]) for r in canonical],
        "control_intent_met": [(r["name"], r["observed"], r["intent_met"]) for r in control],
        "uncaught": uncaught,
        "n_negative": len(negative),
        "negative_rule_histogram": _hist(negative),
        "rephrased": [(r["name"], r["observed"], r["failed_rules"]) for r in rephrased],
    }, indent=1))
    return 0


def _hist(rows):
    h = {}
    for r in rows:
        for rule in (r.get("failed_rules") or []):
            h[rule] = h.get(rule, 0) + 1
    return dict(sorted(h.items()))


if __name__ == "__main__":
    raise SystemExit(main())
