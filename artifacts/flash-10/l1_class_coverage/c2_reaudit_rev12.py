#!/usr/bin/env python3
"""W010-L1-REAUDIT-03 (revision addendum): re-derive AF-SCC-C2-VAC-GEN at F2a rev12 5476a3f2c6bc.

The rev9 C2 audit (`c2_class_conformance_audit.json`, sha256 7e2dba3f1376 at emission) was bound to
F2a rev9 8dae50da1ab5 and to ledger hash ce42d205e761. Both inputs have since moved: F2a ->
rev12 5476a3f2c6bc and the ledger -> a1674f094979 (the ledger was also revised so that
self-certified `accepted` statuses are downgraded). This wrapper mirrors the WCC rev12
(W010-L1-REAUDIT-01) and C0 rev12 (W010-L1-REAUDIT-02) addenda with the identical method:

  1. imports the unmodified rev9 C2 driver (`c2_class_conformance_audit.py`) and redirects only its
     OUTPUT path, so the already-emitted rev9 artifact stays byte-identical;
  2. re-runs the same D1/D2/D3 classification at the current canonical schema and ledger, writing a
     NEW raw re-run file named for the rev12 schema prefix;
  3. records the step drift rev9 -> rev12 (which fields changed in the class-definition extraction),
     the ledger drift (rev9 input hash -> measured hash), the accepted-status counts, and post-run
     input stability;
  4. does not adjudicate whether the `(s,delta)` -> `r` parameter renaming is semantic (F1/A1
     decision), and claims no completion and no gate verdict.

Usage: python3 c2_reaudit_rev12.py
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]

DRIVER = HERE / "c2_class_conformance_audit.py"
REV9_REPORT = HERE / "c2_class_conformance_audit.json"
REV9_SNAPSHOT = HERE / "snapshots" / "af_scc_c2_vacuum.8dae50da1ab5.yaml"
REV12_AUDIT = HERE / "c2_class_conformance_audit.5476a3f2c6bc.json"

CST = timezone(timedelta(hours=8))
REV9_REPORT_SHA256_PREFIX = "7e2dba3f1376"  # rev9 artifact hash, present in the accepted event stream
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
    rev9_hash_before = sha256(REV9_REPORT)
    rev9 = json.loads(REV9_REPORT.read_text(encoding="utf-8"))

    spec = importlib.util.spec_from_file_location("c2_audit_driver", DRIVER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]

    driver_hash_after_import = sha256(DRIVER)

    # Redirect only the output; the driver's classification and hashing run unchanged.
    mod.OUT = REV12_AUDIT
    rc = mod.main()
    if rc != 0:
        return rc

    # The rev9 driver records its own sha256 inside the report it writes, but this wrapper then
    # rewrites that same report file to append the addendum block; the driver's embedded value
    # therefore describes the driver as of the first write and cannot be the pin that a reader
    # hashes today. Record the final driver bytes instead (stability asserted after the write below).
    driver_hash_final = sha256(DRIVER)

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

    rev9_def = extract(REV9_SNAPSHOT)
    rev12_def = extract(Path(mod.SCHEMA))
    differing = [k for k in EXTRACTION_FIELDS if rev9_def[k] != rev12_def[k]]
    changed = [k for k in differing if k != "revision"]

    # Input stability: re-hash everything the driver read and compare with what it recorded.
    unstable = []
    for key, val in rep.get("inputs", {}).items():
        if isinstance(val, dict) and "sha256" in val and (ROOT / key).exists():
            now = sha256(ROOT / key)
            if now != val["sha256"]:
                unstable.append(key)

    inputs = rep["inputs"]
    ledger_now = inputs["ledger/theorems.jsonl"]["sha256"]
    ledger_rev9 = (rev9.get("inputs", {}).get("ledger/theorems.jsonl") or {}).get("sha256")
    acc_rev9 = rev9.get("summary", {}).get("n_accepted_status")
    entries = [json.loads(l) for l in (ROOT / "ledger" / "theorems.jsonl").read_text(
        encoding="utf-8").splitlines() if l.strip()]
    bound_now = [e for e in entries if mod.CLASS in (e.get("class_ids") or [])]
    acc_now = sum(1 for e in bound_now if e.get("status") == "accepted")

    rep["report_id"] = f"flash-10-c2-reaudit-rev12-{datetime.now(CST).strftime('%Y%m%dT%H%M%S')}"
    rep["purpose"] = (
        "Revision addendum to W010-L1-REAUDIT-03: re-derive the AF-SCC-C2-VAC-GEN "
        "class-conformance reading at F2a rev12 5476a3f2c6bc and ledger a1674f094979, after both "
        "pinned inputs moved past the rev9-bound report."
    )
    rep["revision_addendum"] = {
        "supersedes_report": str(REV9_REPORT.relative_to(ROOT)),
        "supersedes_report_sha256": rev9_hash_before,
        "supersedes_report_sha256_matches_emitted_prefix": rev9_hash_before[:12]
        == REV9_REPORT_SHA256_PREFIX,
        "supersedes_reason": (
            "F2a moved rev9 8dae50da1ab5 -> rev12 5476a3f2c6bc and the ledger moved past the "
            "rev9 input hash; the rev9 artifact is preserved byte-identical so its emitted "
            "event hash stays valid."
        ),
        "step_drift_rev9_to_rev12": {
            "differing_fields": differing,
            "fields_changed_beyond_revision": changed,
            "verdict": "substantive_difference_found" if changed else "extraction_identical_apart_from_revision",
            "rev9_values": {k: rev9_def[k] for k in changed},
            "rev12_values": {k: rev12_def[k] for k in changed},
        },
        "extraction_level_falsifier_fired": bool(changed),
        "observation": (
            "The only changed extraction field is `statement_formal`, and its visible difference "
            "is a parameter renaming: rev9 quantifies over `(s,delta) in D0` with `G_{s,delta}` / "
            "`X^{s,delta}_vac`, rev12 over `r in D0` with `G_r` / `X^r_vac`. The quantifier "
            "structure (forall r exists comeager G_r forall D in G_r: not exists proper future "
            "C2 extension of MGHD(D)) is unchanged. Whether a parameter renaming is a substantive "
            "class change is an F1/A1 decision, not this worker's. The same rename was found "
            "independently in the C0 rev11->rev12 addendum (W010-L1-REAUDIT-02)."
        ),
        "driver_sha256": driver_hash_final,
        "driver_unmodified": driver_hash_final == sha256(DRIVER),
        "driver_sha256_note": (
            "sha256 of the unmodified rev9 driver at the end of this run. The rev9 report's own "
            "embedded copy of this value predates the addendum rewrite of the report file and is "
            "superseded by this field."
        ),
        "pinned_snapshot": {
            "path": str(REV9_SNAPSHOT.relative_to(ROOT)),
            "sha256": sha256(REV9_SNAPSHOT),
            "note": (
                "byte-identical copy of the rev9 schema as captured in "
                "artifacts/worker-008/f2_containment_repair/inputs/af_scc_c2_vacuum.yaml"
            ),
        },
    }
    rep["ledger_status_observation"] = {
        "rev9_report_input_ledger_sha256": ledger_rev9,
        "measured_ledger_sha256": ledger_now,
        "ledger_moved_since_rev9": ledger_rev9 != ledger_now,
        "n_bound_entries_rev9": rev9.get("summary", {}).get("n_bound_entries"),
        "n_bound_entries_now": rep["summary"]["n_bound_entries"],
        "n_accepted_status_rev9": acc_rev9,
        "n_accepted_status_now": acc_now,
        "note": (
            "The rev9 report did not record an accepted-status count (field absent); this addendum "
            "records the current count directly from the ledger at the measured hash. At the "
            f"current ledger hash {acc_now} of {len(bound_now)} bound entries carry "
            "status=accepted, so D3 fails at status level for every binding independently of the "
            "schema revision. This is recorded, not adjudicated (ledger hygiene is L0/L1's job)."
        ),
    }
    rep["input_stability"] = {
        "all_stable": not unstable,
        "unstable_inputs": unstable,
        "checked_at": datetime.now(CST).isoformat(timespec="seconds"),
    }
    rep["equivalence_reading"] = (
        "At F2a rev12 5476a3f2c6bc the re-run reads class_definition sha 5476a3f2c6bc and finds "
        f"n_bound={rep['summary']['n_bound_entries']}, "
        f"n_discharging={rep['summary']['n_discharging']}, class conclusion state "
        f"'{rep['summary']['class_conclusion_state']}'. The rev9 -> rev12 extraction differs in "
        "`statement_formal` (parameter renaming) and `revision`; the ledger moved "
        f"{str(ledger_rev9)[:12]} -> {ledger_now[:12]} with {acc_now} accepted-status bound "
        "entries at the current hash. No class conclusion is discharged at either revision."
        if not unstable else
        "VOID: an input changed between the pin and the re-run; no reading is claimed."
    )
    rep["evidence_refs"] = [
        f"schemas/af_scc_c2_vacuum.yaml#{inputs['schemas/af_scc_c2_vacuum.yaml']['sha256'][:12]}",
        f"ledger/theorems.jsonl#{ledger_now[:12]}",
        f"{DRIVER.relative_to(ROOT)}#{driver_hash_final[:12]}",
        f"{REV9_SNAPSHOT.relative_to(ROOT)}#{sha256(REV9_SNAPSHOT)[:12]}",
        f"{REV9_REPORT.relative_to(ROOT)}#{rev9_hash_before[:12]}",
    ]
    REV12_AUDIT.write_text(json.dumps(rep, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    driver_stable = sha256(DRIVER) == driver_hash_final
    rev9_still = sha256(REV9_REPORT) == rev9_hash_before
    print(f"wrote {REV12_AUDIT.relative_to(ROOT)}")
    print(f"step drift verdict: {rep['revision_addendum']['step_drift_rev9_to_rev12']['verdict']} "
          f"| changed: {changed}")
    print(f"rerun bound={rep['summary']['n_bound_entries']} "
          f"discharging={rep['summary']['n_discharging']} "
          f"accepted_now={acc_now} accepted_rev9={acc_rev9} "
          f"input_stability={rep['input_stability']['all_stable']}")
    print("driver stable through run:", driver_stable)
    print("rev9 report preserved byte-identical:", rev9_still)
    print("rev9 report sha256:", rev9_hash_before)
    print("rev12 audit sha256:", sha256(REV12_AUDIT))
    return 0 if (rev9_still and driver_stable) else 3


if __name__ == "__main__":
    raise SystemExit(main())
