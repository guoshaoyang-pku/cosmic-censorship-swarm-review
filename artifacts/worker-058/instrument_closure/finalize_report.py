#!/usr/bin/env python3
"""Assemble the W058 instrument-closure report from the measured JSON artifacts.

Reads (all in this directory): closure_manifest.json, closure_manifest_all_scope.json,
sensitivity_selftest.json, flip_probe.json, plus the canonical preflight/drift checks it
re-measures read-only at run time. Writes report.json. No canonical path is written.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
CST = timezone(timedelta(hours=8))
ENGINE = "artifacts/worker-06/spec_conformance_audit.py"
EVIDENCE = "artifacts/formulation/evidence/semantic_escape_rebased.json"
DRIFT_PATH = "artifacts/formulation/tools/check_variant_registry.py"


def sha(p: Path) -> str | None:
    try:
        return hashlib.sha256(p.read_bytes()).hexdigest()
    except (FileNotFoundError, IsADirectoryError):
        return None


def main() -> int:
    closure = json.loads((HERE / "closure_manifest.json").read_text())
    closure_all = json.loads((HERE / "closure_manifest_all_scope.json").read_text())
    selftest = json.loads((HERE / "sensitivity_selftest.json").read_text())
    flip = json.loads((HERE / "flip_probe.json").read_text())
    frozen = json.loads((REPO / "artifacts/formulation/FROZEN.json").read_text())

    # read-only live re-measurements
    ev = json.loads((REPO / EVIDENCE).read_text())
    live_c0 = sha(REPO / "schemas/af_scc_c0_vacuum.yaml")
    preflight_ok = ev.get("base_sha256") == live_c0
    vf = subprocess.run([sys.executable,
                         str(REPO / "artifacts/formulation/tools/verify_frozen.py")],
                        cwd=str(REPO), capture_output=True, text=True)
    drift_live = sha(REPO / DRIFT_PATH) != frozen["files"][DRIFT_PATH]["sha256"]

    gaps = [closure["nodes"][k] for k in closure["effect_capable_unpinned"]]
    by_parent = Counter(n["parent_dir"] or n["path"] for n in gaps)
    by_tier = Counter(n["tier"] for n in gaps)

    findings = [
        {"id": "W058-IC-01", "severity": "hard",
         "finding": "The stage-2 semantic rule engine of the G-FORM acceptance pipeline is not pinned. "
                    f"`{ENGINE}` (live {sha(REPO / ENGINE)[:12]}) is subprocess-executed by the pinned drivers "
                    "`run_acceptance.py` (line 25) and `measure_semantic_escape.py` (line 29) and has ZERO "
                    "occurrences in `artifacts/formulation/FROZEN.json` (rev29, 50 files). Its bytes can "
                    "therefore change semantic verdicts, the pinned `acceptance_pipeline_report.json` and the "
                    "mutant-union criterion without moving any pinned hash.",
         "evidence": [f"{ENGINE}#{sha(REPO / ENGINE)}",
                      "artifacts/formulation/tools/run_acceptance.py#e544c36d2d16",
                      "artifacts/formulation/tools/measure_semantic_escape.py#c6e4f9ccce7f",
                      "artifacts/formulation/FROZEN.json#815e08079aef"]},
        {"id": "W058-IC-02", "severity": "hard",
         "finding": f"69 unpinned corpus/input files are read by the same pinned drivers: 33 "
                    f"`artifacts/formulation/evidence/rebased_fixtures/*.yaml`, 32 "
                    f"`artifacts/worker-06/semantic_fixtures/*.yaml`, 3 controls, and "
                    f"`artifacts/worker-06/semantic_fixtures/manifest.json`. Editing any of them moves the "
                    f"acceptance outcome while FROZEN rev29 stays byte-identical.",
         "evidence": ["artifacts/worker-058/instrument_closure/closure_manifest.json#see effect_capable_unpinned",
                      "artifacts/worker-06/semantic_fixtures/manifest.json",
                      "artifacts/formulation/evidence/rebased_fixtures/"]},
        {"id": "W058-IC-03", "severity": "hard",
         "finding": f"The pinned preflight evidence is stale against the live C0 pin: "
                    f"`{EVIDENCE}` declares base_sha256 {ev.get('base_sha256')[:12]} while live "
                    f"`schemas/af_scc_c0_vacuum.yaml` is {live_c0[:12]}. `run_acceptance.py::preflight` "
                    f"compares these two and returns exit 3 on mismatch, so the canonical acceptance "
                    f"pipeline currently fails closed as stale; the pinned PASS report cannot be reproduced "
                    f"from the live pin without regenerating the corpus with the unpinned engine.",
         "evidence": [f"{EVIDENCE}#{sha(REPO / EVIDENCE)}",
                      f"schemas/af_scc_c0_vacuum.yaml#{live_c0}",
                      "artifacts/formulation/tools/run_acceptance.py:53-66"]},
        {"id": "W058-IC-04", "severity": "hard",
         "finding": f"A live pinned-instrument drift exists at report time: `{DRIFT_PATH}` is declared "
                    f"{frozen['files'][DRIFT_PATH]['sha256'][:12]} in FROZEN rev29 but measures "
                    f"{sha(REPO / DRIFT_PATH)[:12]}; `verify_frozen.py` exits {vf.returncode} on the canonical "
                    f"tree. FROZEN rev29 is therefore not currently a valid pin set, and any gate verdict "
                    f"that cites it must be re-measured after a re-freeze. (External event: the file mtime is "
                    f"2026-09-12T01:21:56, after the 00:57:26 freeze; authorship/intent not adjudicated here.)",
         "evidence": [f"{DRIFT_PATH}#{sha(REPO / DRIFT_PATH)}",
                      "artifacts/formulation/FROZEN.json#815e08079aef",
                      "artifacts/formulation/tools/verify_frozen.py#0a65b657e498"]},
        {"id": "W058-IC-05", "severity": "hard",
         "finding": f"At the live bytes the acceptance instrument returns FAIL: the unpinned stage-2 engine "
                    f"rejects canonical F1 (`af_wcc_vacuum.yaml`, structural pass / semantic fail, R03), so "
                    f"the pinned `acceptance_pipeline_report.json` (PASS, canonical all-pass) does not bind "
                    f"the live engine+schema bytes. Sandbox baseline run: verdict FAIL, canonical F1 semantic "
                    f"fail, mutants union {flip['B_baseline'].get('mutants', {}).get('union_caught')}/"
                    f"{flip['B_baseline'].get('mutants', {}).get('total')}.",
         "evidence": ["artifacts/worker-058/instrument_closure/flip_baseline_acceptance.json",
                      f"{ENGINE}#{sha(REPO / ENGINE)}",
                      "schemas/af_wcc_vacuum.yaml#d9cebb9404b2"]},
        {"id": "W058-IC-06", "severity": "hard",
         "finding": "Outcome-flip confirmed in an isolated sandbox: replacing the unpinned engine with an "
                    "always-accept stub flips canonical F1 semantic fail->pass and drops semantic mutant "
                    f"catches 11->0 (union 31/31 -> {flip['E_acceptance_tampered'].get('mutants', {}).get('union_caught')}/31) "
                    "while 0 of the pinned files move and `verify_frozen.py` still exits 0. The gap is "
                    "outcome-changing, not documentary.",
         "evidence": ["artifacts/worker-058/instrument_closure/flip_probe.json",
                      "artifacts/worker-058/instrument_closure/flip_tampered_acceptance.json"]},
        {"id": "W058-IC-07", "severity": "info",
         "finding": "Remedy validated in the sandbox: pinning the 70-path effect-capable closure makes "
                    "`closure_check.py --strict` exit 0 (CLOSED); re-tampering the now-pinned engine makes it "
                    "exit 1 with status PINNED_DRIFT. The freeze-time guard is therefore both sufficient "
                    "(green when the closure is pinned) and sensitive (red on drift).",
         "evidence": ["artifacts/worker-058/instrument_closure/_sandbox_closure_pinned.json",
                      "artifacts/worker-058/instrument_closure/_sandbox_closure_drift.json",
                      "artifacts/worker-058/instrument_closure/flip_probe.json"]},
    ]

    deliverables = {}
    for name in ("closure_check.py", "flip_probe.py", "closure_manifest.json",
                 "closure_manifest_all_scope.json", "sensitivity_selftest.json",
                 "flip_probe.json", "flip_baseline_acceptance.json",
                 "flip_tampered_acceptance.json", "README.md"):
        p = HERE / name
        if p.exists():
            deliverables[name] = sha(p)

    report = {
        "schema": "w058/instrument-closure-report/v1",
        "actor": "worker-058",
        "task_id": "W058-INSTRUMENT-CLOSURE-07",
        "created_at": datetime.now(CST).isoformat(timespec="seconds"),
        "node_ids": ["F1", "F2a", "F2b"],
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "gate_context": "G-FORM",
        "assignment_card": "none (comms/inbox/worker-058.jsonl absent; one bounded successor task taken "
                           "from the live queue: the formulation lead's 01:15:16 INSTRUMENT GOVERNANCE GAP blocker)",
        "pins": {
            "frozen_manifest": f"artifacts/formulation/FROZEN.json#{sha(REPO / 'artifacts/formulation/FROZEN.json')}",
            "frozen_revision": frozen["revision"],
            "c0": f"schemas/af_scc_c0_vacuum.yaml#{live_c0}",
            "c2": f"schemas/af_scc_c2_vacuum.yaml#{sha(REPO / 'schemas/af_scc_c2_vacuum.yaml')}",
            "f1": f"schemas/af_wcc_vacuum.yaml#{sha(REPO / 'schemas/af_wcc_vacuum.yaml')}",
            "stage2_engine": f"{ENGINE}#{sha(REPO / ENGINE)}",
            "pin_drift_live": drift_live,
            "preflight_ok_live": preflight_ok,
            "verify_frozen_rc_live": vf.returncode,
            "pin_stable_during_own_runs": True,
        },
        "closure": {
            "scope_acceptance": {
                "verdict": closure["verdict"], "counts": closure["counts"],
                "tier_counts": closure["tier_counts"],
                "effect_capable_unpinned_by_parent": dict(sorted(by_parent.items())),
                "effect_capable_unpinned_by_tier": dict(sorted(by_tier.items())),
                "manifest": "artifacts/worker-058/instrument_closure/closure_manifest.json",
                "entries": closure["entries"],
            },
            "scope_all_pinned_tools": {
                "verdict": closure_all["verdict"], "counts": closure_all["counts"],
                "manifest": "artifacts/worker-058/instrument_closure/closure_manifest_all_scope.json",
            },
        },
        "sensitivity_selftest": {"passed": selftest["passed"], "total": selftest["total"],
                                 "all_pass": selftest["all_pass"]},
        "outcome_flip": {"verdict": flip["verdict"], "checks": flip["checks"],
                         "baseline": {k: flip["B_baseline"].get(k) for k in ("verdict", "mutants")},
                         "tampered": {k: flip["E_acceptance_tampered"].get(k) for k in ("verdict", "mutants")},
                         "external_drift_absorbed": flip.get("A_external_drift_absorbed", []),
                         "pins_moved_by_rebase": flip["A1_preflight"].get("pins_moved_by_rebase", [])},
        "findings": findings,
        "deliverables": deliverables,
        "boundary": [
            "Static reachability + sandbox experiment only. Paths reached through computed runtime values "
            "(f-strings, argv, environment) are not discovered; absence of a finding outside the discovered "
            "set is not proof of closure.",
            "The sandbox FROZEN manifest is a simulation used to validate the guard, not a publication, and "
            "confers no validation status.",
            "No gate verdict, no node transition, no validation_status promotion, no mathematics claim.",
            "The check_variant_registry.py drift is reported as an external measured event; authorship, "
            "authorization and consequence belong to the controller.",
        ],
        "falsifier": "A reader shows (a) the stage-2 engine hash is pinned in FROZEN rev29 under another "
                     "path/alias, (b) an outcome-changing reachable path outside the reported closure set, "
                     "(c) the sandbox baseline/tampered acceptance reports are not reproducible from the cited "
                     "hashes, (d) the remedy control does not close the strict guard, or (e) a canonical byte "
                     "was written by this task.",
        "next_falsifier": "After the next freeze: re-run `closure_check.py --scope acceptance --strict` and "
                          "require CLOSED; re-run the acceptance pipeline at the published pin and require a "
                          "PASS whose canonical rows are all ok; verify the engine and corpus pins move in the "
                          "same revision that adopts them.",
        "authority": "worker evidence only; the formulation lead and controller own the remediation freeze, "
                     "any gate consequence and the adjudication of the observed drift.",
    }
    (HERE / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(f"REPORT {report['closure']['scope_acceptance']['verdict']} "
          f"gaps={len(gaps)} selftest={selftest['passed']}/{selftest['total']} "
          f"flip={flip['verdict']} preflight_ok={preflight_ok} verify_frozen_rc={vf.returncode}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
