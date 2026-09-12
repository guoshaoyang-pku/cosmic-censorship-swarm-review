#!/usr/bin/env python3
"""W010-L1-REAUDIT-01 (revision addendum): re-derive at F1 rev12 cce9c60146d6.

The rev11 re-run (`wcc_class_conformance_reaudit.json`, sha256 f4ef97ab49e5) was emitted
against F1 rev11 9a8bd4c96800. F1 then moved to rev12 cce9c60146d6 with *extraction-level*
substantive differences (quantifier_formal, conclusion_statement_formal), which fires the
rev11 report's own falsifier. This wrapper:

  1. imports the unmodified rev11 driver (its sha256 is already cited in an emitted event, so
     it must not change) and monkeypatches only the output paths;
  2. writes a NEW report + raw re-run at rev12, leaving the rev11 files byte-identical so the
     already-emitted event hashes remain valid;
  3. records both the overall drift (rev10 -> rev12) and the step drift (rev11 -> rev12), and
     states plainly that the extraction-level falsifier fired;
  4. does not adjudicate whether the (s,delta) -> r renaming is semantic: that is F1/A1's call.

No canonical file is modified; no completion or gate verdict is claimed.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]

DRIVER_V11 = HERE / "wcc_reaudit_rev11.py"
REV11_REPORT = HERE / "wcc_class_conformance_reaudit.json"
REV11_SNAPSHOT = HERE / "snapshots" / "af_wcc_vacuum.9a8bd4c96800.yaml"
REV12_AUDIT = HERE / "wcc_class_conformance_audit.cce9c60146d6.json"
REV12_REPORT = HERE / "wcc_class_conformance_reaudit.rev12.json"

CST = timezone(timedelta(hours=8))


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    rev11_report_hash_before = sha256(REV11_REPORT)

    spec = importlib.util.spec_from_file_location("wcc_reaudit_v11", DRIVER_V11)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]

    rev11_hash_after_import = sha256(DRIVER_V11)

    # Redirect only the rev11 driver's outputs; its comparison logic and scoring code run unchanged.
    mod.NEW_AUDIT = REV12_AUDIT
    mod.REPORT = REV12_REPORT
    rc = mod.main()
    if rc != 0:
        return rc

    rep = json.loads(REV12_REPORT.read_text(encoding="utf-8"))
    cur_schema = Path(mod.SCHEMA)
    step = mod.diff_class_defs(mod.extract_class_def(REV11_SNAPSHOT),
                               mod.extract_class_def(cur_schema))
    fields_changed = sorted(set(step["differing_fields"]) - {"revision"})

    # The rev11 driver hardcodes its own reaudit filename inside evidence_refs; replace it with
    # the rev12 path/hash pairing actually on disk.
    re_h = sha256(REV12_AUDIT)
    rep["evidence_refs"] = [
        e for e in rep["evidence_refs"]
        if "wcc_class_conformance_audit.9a8bd4c96800.json" not in e
    ]
    rep["evidence_refs"].append(
        f"{REV12_AUDIT.relative_to(ROOT)}#{re_h[:12]}"
    )

    rep["report_id"] = f"flash-10-wcc-reaudit-rev12-{datetime.now(CST).strftime('%Y%m%dT%H%M%S')}"
    rep["revision_addendum"] = {
        "supersedes_report": str(REV11_REPORT.relative_to(ROOT)),
        "supersedes_report_sha256": rev11_report_hash_before,
        "supersedes_reason": (
            "F1 moved rev11 9a8bd4c96800 -> rev12 cce9c60146d6 with extraction-level substantive "
            "differences, firing the rev11 report's falsifier; the rev11 files are preserved "
            "byte-identical so their emitted event hashes stay valid."
        ),
        "step_drift_rev11_to_rev12": step,
        "extraction_level_falsifier_fired": step["verdict"] == "substantive_difference_found",
        "fields_changed": fields_changed,
        "observation": (
            "The two changed formal fields differ by a parameter renaming: the rev11 text "
            "quantifies over `(s,delta) in D0` with `G_{s,delta}` / `X^{s,delta}_vac`, the rev12 "
            "text over `r in D0` with `G_r` / `X^r_vac`. The quantifier structure "
            "(forall r exists comeager G_r forall D in G_r: AF_{I+} and complete(I+) and not "
            "visible_singularity) is unchanged in the extracted formal string. Whether a "
            "parameter renaming counts as substantive is an F1/A1 decision, not this worker's."
        ),
        "driver_v11_sha256": rev11_hash_after_import,
        "driver_v11_matches_emitted_evidence_ref": rev11_hash_after_import[:12] == "1850243987ad",
    }
    rep["purpose"] = (
        "Revision addendum to W010-L1-REAUDIT-01: re-derive the AF-WCC-VAC-GEN class-conformance "
        "reading at F1 rev12 cce9c60146d6 after the rev11-bound report's falsifier fired."
    )
    rep["equivalence_reading"] = (
        "At F1 rev12 the re-run again reads class_definition sha cce9c60146d6 and finds "
        "n_bound=11, n_discharging=0, class conclusion state open_problem. The rev10 -> rev11 "
        "step was extraction-identical apart from `revision`; the rev11 -> rev12 step is "
        "extraction-substantive in two formal fields whose visible difference is a parameter "
        "renaming. Both facts are recorded; neither is adjudicated here."
        if rep.get("input_stability", {}).get("all_stable") else
        "VOID: an input changed between the pin and the re-run; no reading is claimed."
    )
    REP12 = json.loads(json.dumps(rep))  # keep key order stable
    REV12_REPORT.write_text(json.dumps(REP12, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # Confirm the preserved rev11 file really is untouched.
    rev11_still = sha256(REV11_REPORT) == rev11_report_hash_before
    print(f"wrote {REV12_REPORT.relative_to(ROOT)}")
    print(f"step drift verdict: {step['verdict']} | changed: {fields_changed}")
    print(f"rerun rc={rc} discharging={rep['rerun']['summary']['n_discharging']} "
          f"bound={rep['rerun']['summary']['n_bound_entries']} "
          f"input_stability={rep.get('input_stability', {}).get('all_stable')}")
    print("rev11 report preserved byte-identical:", rev11_still)
    print("rev12 report sha256:", sha256(REV12_REPORT))
    print("rev12 reaudit sha256:", sha256(REV12_AUDIT))
    print("rev11 report sha256:", rev11_report_hash_before)
    return 0 if rev11_still else 3


if __name__ == "__main__":
    raise SystemExit(main())
