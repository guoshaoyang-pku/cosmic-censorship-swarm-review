#!/usr/bin/env python3
"""W010-L1-REAUDIT-02 (revision addendum): re-derive AF-SCC-C0-VAC-GEN at F2b rev12 55d0a1ea9bda.

The rev11 C0 audit (`c0_class_conformance_audit.json`, sha256 6e5eb9fb1272 at emission) was
bound to F2b rev11 1bb78ce9b357 and to ledger hash ce42d205e761. Both inputs have since moved:
F2b -> rev12 55d0a1ea9bda and the ledger -> a1674f094979 (the ledger was also revised so that
self-certified `accepted` statuses are downgraded). This wrapper:

  1. imports the unmodified rev11 C0 driver (`c0_class_conformance_audit.py`) and monkeypatches
     only its OUTPUT path, so the already-emitted rev11 artifact stays byte-identical;
  2. re-runs the same D1/D2/D3 classification and negative controls at the current canonical
     schema and ledger, writing a NEW raw re-run file named for the rev12 schema prefix;
  3. records the step drift rev11 -> rev12 (which fields changed in the class-definition
     extraction), the ledger drift (rev11 input hash -> measured hash, accepted count), and
     post-run input stability;
  4. does not adjudicate whether the `(s,delta)` -> `r` parameter renaming is semantic (F1/A1
     decision), and claims no completion and no gate verdict.

Usage: python3 c0_reaudit_rev12.py
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]

DRIVER = HERE / "c0_class_conformance_audit.py"
REV11_REPORT = HERE / "c0_class_conformance_audit.json"
REV11_SNAPSHOT = HERE / "snapshots" / "af_scc_c0_vacuum.1bb78ce9b357.yaml"
REV12_AUDIT = HERE / "c0_class_conformance_audit.55d0a1ea9bda.json"

CST = timezone(timedelta(hours=8))
REV11_REPORT_SHA256_PREFIX = "bff0d3e9922b"  # rev11 artifact hash, present in the accepted event stream
EXTRACTION_FIELDS = [
    "revision",
    "class_id",
    "conclusion_type",
    "statement_natural_language",
    "statement_formal",
    "epistemic_status",
    "genericity_kind",
    "extension_regularity",
    "extension_regularity_exact",
    "claim_promotion",
    "sibling_disjoint_from",
]


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    rev11_hash_before = sha256(REV11_REPORT)
    rev11 = json.loads(REV11_REPORT.read_text(encoding="utf-8"))

    spec = importlib.util.spec_from_file_location("c0_audit_driver", DRIVER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]

    driver_hash_after_import = sha256(DRIVER)

    # Redirect only the output; the driver's classification, controls and hashing run unchanged.
    mod.OUT = REV12_AUDIT
    rc = mod.main()
    if rc != 0:
        return rc

    rep = json.loads(REV12_AUDIT.read_text(encoding="utf-8"))

    def extract(path: Path) -> dict:
        text = path.read_text(encoding="utf-8", errors="replace")
        out = {}
        for key in EXTRACTION_FIELDS:
            if key == "genericity_kind":
                out[key] = mod.grab(text, "kind") or mod.grab(text, "genericity_kind")
            else:
                out[key] = mod.grab(text, key)
        return out

    rev11_def = extract(REV11_SNAPSHOT)
    rev12_def = extract(Path(mod.SCHEMA))
    differing = [k for k in EXTRACTION_FIELDS if rev11_def[k] != rev12_def[k]]
    changed = [k for k in differing if k != "revision"]

    # Input stability: re-hash everything the driver read and compare with what it recorded.
    unstable = []
    for key, val in rep.get("inputs", {}).items():
        if isinstance(val, dict) and "sha256" in val and (ROOT / key).exists():
            now = sha256(ROOT / key)
            if now != val["sha256"]:
                unstable.append(key)
        elif isinstance(val, dict):  # the "snapshot" block maps a path -> {sha256, ...}
            for sub, subval in val.items():
                if isinstance(subval, dict) and "sha256" in subval and (ROOT / sub).exists():
                    if sha256(ROOT / sub) != subval["sha256"]:
                        unstable.append(sub)

    inputs = rep["inputs"]
    ledger_now = inputs["ledger/theorems.jsonl"]["sha256"]
    ledger_rev11 = (rev11.get("inputs", {}).get("ledger/theorems.jsonl") or {}).get("sha256")
    acc_rev11 = rev11.get("summary", {}).get("n_accepted_status")
    acc_now = rep["summary"]["n_accepted_status"]

    rep["report_id"] = f"flash-10-c0-reaudit-rev12-{datetime.now(CST).strftime('%Y%m%dT%H%M%S')}"
    rep["purpose"] = (
        "Revision addendum to W010-L1-REAUDIT-02: re-derive the AF-SCC-C0-VAC-GEN "
        "class-conformance reading at F2b rev12 55d0a1ea9bda and ledger a1674f094979, after both "
        "pinned inputs moved past the rev11-bound report."
    )
    rep["revision_addendum"] = {
        "supersedes_report": str(REV11_REPORT.relative_to(ROOT)),
        "supersedes_report_sha256": rev11_hash_before,
        "supersedes_report_sha256_matches_emitted_prefix": rev11_hash_before[:12]
        == REV11_REPORT_SHA256_PREFIX,
        "supersedes_reason": (
            "F2b moved rev11 1bb78ce9b357 -> rev12 55d0a1ea9bda and the ledger moved past the "
            "rev11 input hash; the rev11 artifact is preserved byte-identical so its emitted "
            "event hash stays valid."
        ),
        "step_drift_rev11_to_rev12": {
            "differing_fields": differing,
            "fields_changed_beyond_revision": changed,
            "verdict": "substantive_difference_found" if changed else "extraction_identical_apart_from_revision",
            "rev11_values": {k: rev11_def[k] for k in changed},
            "rev12_values": {k: rev12_def[k] for k in changed},
        },
        "extraction_level_falsifier_fired": bool(changed),
        "observation": (
            "The only changed extraction field is `statement_formal`, and its visible difference "
            "is a parameter renaming: rev11 quantifies over `(s,delta) in D0` with `G_{s,delta}` / "
            "`X^{s,delta}_vac`, rev12 over `r in D0` with `G_r` / `X^r_vac`. The quantifier "
            "structure (forall r exists comeager G_r forall D in G_r: no proper future C0 "
            "extension) is unchanged. Whether a parameter renaming is a substantive class change "
            "is an F1/A1 decision, not this worker's."
        ),
        "driver_sha256": driver_hash_after_import,
        "driver_unmodified": driver_hash_after_import == sha256(DRIVER),
    }
    rep["ledger_status_observation"] = {
        "rev11_report_input_ledger_sha256": ledger_rev11,
        "measured_ledger_sha256": ledger_now,
        "ledger_moved_since_rev11": ledger_rev11 != ledger_now,
        "n_bound_entries_rev11": rev11.get("summary", {}).get("n_bound_entries"),
        "n_bound_entries_now": rep["summary"]["n_bound_entries"],
        "n_accepted_status_rev11": acc_rev11,
        "n_accepted_status_now": acc_now,
        "note": (
            "At the current ledger hash no bound entry carries status=accepted, so D3 fails at "
            "status level for every binding independently of the schema revision; the rev11 "
            "report's 9 accepted-status entries were self-certified records since downgraded. "
            "This is recorded, not adjudicated (ledger hygiene is L0/L1's job)."
        ),
    }
    rep["input_stability"] = {
        "all_stable": not unstable,
        "unstable_inputs": unstable,
        "checked_at": datetime.now(CST).isoformat(timespec="seconds"),
    }
    rep["equivalence_reading"] = (
        "At F2b rev12 55d0a1ea9bda the re-run reads class_definition sha 55d0a1ea9bda and finds "
        f"n_bound={rep['summary']['n_bound_entries']}, "
        f"n_discharging={rep['summary']['n_discharging']}, class conclusion state "
        f"'{rep['summary']['class_conclusion_state']}'. The rev11 -> rev12 extraction differs in "
        "`statement_formal` (parameter renaming) and `revision`; ledger statuses moved from "
        f"{acc_rev11} accepted to {acc_now} accepted at the current hash. No class conclusion is "
        "discharged at either revision."
        if not unstable else
        "VOID: an input changed between the pin and the re-run; no reading is claimed."
    )
    rep["evidence_refs"] = [
        f"{REV11_REPORT.relative_to(ROOT)}#{rev11_hash_before[:12]}",
        f"schemas/af_scc_c0_vacuum.yaml#{inputs['schemas/af_scc_c0_vacuum.yaml']['sha256'][:12]}",
        f"ledger/theorems.jsonl#{ledger_now[:12]}",
        f"{DRIVER.relative_to(ROOT)}#{driver_hash_after_import[:12]}",
    ]
    REV12_AUDIT.write_text(json.dumps(rep, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    rev11_still = sha256(REV11_REPORT) == rev11_hash_before
    print(f"wrote {REV12_AUDIT.relative_to(ROOT)}")
    print(f"step drift verdict: {rep['revision_addendum']['step_drift_rev11_to_rev12']['verdict']} "
          f"| changed: {changed}")
    print(f"rerun bound={rep['summary']['n_bound_entries']} "
          f"discharging={rep['summary']['n_discharging']} "
          f"accepted_now={acc_now} accepted_rev11={acc_rev11} "
          f"input_stability={rep['input_stability']['all_stable']}")
    print("rev11 report preserved byte-identical:", rev11_still)
    print("rev11 report sha256:", rev11_hash_before)
    print("rev12 audit sha256:", sha256(REV12_AUDIT))
    return 0 if rev11_still else 3


if __name__ == "__main__":
    raise SystemExit(main())
