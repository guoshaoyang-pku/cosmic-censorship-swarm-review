#!/usr/bin/env python3
"""Assemble verdict.json, README.md and MANIFEST.json for W095-F2B-STREAM-BINDING-R6-VERIFY-01.

Reads the raw evidence produced by run_probe_r6.py (same directory). Does not modify
canonical bytes and does not touch the probed files.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE / "evidence" / "raw"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    report = json.loads((RAW / "probe_report_r6.json").read_text())
    pins = json.loads((RAW / "instant_pins_r6.json").read_text())
    r2 = json.loads((RAW / "f2b_resolution_r6.json").read_text())
    r3 = json.loads((RAW / "future_cohort_r6.json").read_text())
    r4 = json.loads((RAW / "block_provenance_r6.json").read_text())
    r5 = json.loads((RAW / "applied_effects_r6.json").read_text())
    r6 = json.loads((RAW / "controls_r6.json").read_text())

    f2b = r2["schemas/af_scc_c0_vacuum.yaml"]
    mirror = r2["artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"]
    rev6 = r5["rev6_f2b_event"]

    verdict = {
        "task_id": "W095-F2B-STREAM-BINDING-R6-VERIFY-01",
        "worker": "worker-095",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "artifact_type": "stream_binding_integrity_verdict",
        "probe_at": report["probe_at"],
        "frozen_revision_reviewed": report["frozen_revision_reviewed"],
        "frozen_manifest_sha256": report["frozen_manifest_sha256"],
        "pinned_inputs": {
            k: v for k, v in pins["inputs_start"].items()
        },
        "verdict": report["verdict"],
        "score_0_5": 3,
        "counts_as_full_schema_verdict": False,
        "checks": report["checks"],
        "r2_summary": {
            "schemas/af_scc_c0_vacuum.yaml": {
                "pin": f2b["pin_sha256"],
                "n_artifact_events": f2b["n_artifact_events"],
                "file_order_last": f2b["rules"]["file_order_last"],
                "received_at_max": f2b["rules"]["received_at_max"],
                "created_at_max": f2b["rules"]["created_at_max"],
                "fail_closed_received_then_file": f2b["rules"]["fail_closed_received_then_file"],
                "all_rules_resolve_to_pin": f2b["all_rules_resolve_to_pin"],
            },
            "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml": {
                "all_rules_resolve_to_pin": mirror["all_rules_resolve_to_pin"],
            },
        },
        "r3_summary": {k: v for k, v in r3.items() if k != "cohort"},
        "r4_summary": {k: v for k, v in r4.items() if k != "block"},
        "r5_summary": {k: v for k, v in r5.items()},
        "r6_summary": r6,
        "hard_failures": [
            {
                "id": "HF-R6-01",
                "severity": "hard",
                "statement": (
                    f"At the pinned accepted-stream snapshot ({pins['inputs_start']['research_map/events.jsonl'][:12]}, "
                    f"{r3['n_future_dated']} events with created_at > {r3['probe_at']}), "
                    f"{r3['n_applied']} are already applied to research_map.json and "
                    f"{r3['n_with_map_content_locations']} are materialized in map content "
                    "(claims/reviews). The sole global state therefore carries evidence dated after "
                    "the probe instant."
                ),
            },
            {
                "id": "HF-R6-02",
                "severity": "hard",
                "statement": (
                    "The held path schemas/af_scc_c0_vacuum.yaml does not resolve to its FROZEN rev29 "
                    "pin b2ab6acb2bbe under every candidate ordering rule: created_at-max resolves to "
                    "e6b1af2bd692 from w06-20260912T0115-f2b-rev6 (stream line 712, no _received_at, "
                    "outbox write time 00:42:23 vs claimed created_at 01:15:00, supersedes "
                    "cb897b29db12). File order, _received_at-max and the fail-closed "
                    "received-then-file rule all resolve to the pin (lead-form-20260912T005743-02, "
                    "line 4832). The F2b mirror resolves to the pin under all rules."
                ),
            },
            {
                "id": "HF-R6-03",
                "severity": "hard",
                "statement": (
                    f"The deepseek-flash-06 pre-dated block ({r4['block_ids_found']}/15 events, "
                    f"stream lines {r4['block_lines_min']}-{r4['block_lines_max']}) lies entirely "
                    f"inside the {r4['first_line_with_received_at'] - 1}-line unstamped prefix "
                    f"(first _received_at is line {r4['first_line_with_received_at']} = "
                    f"{r4['first_received_at_value']}); its outbox ({r4['outbox_files'][0]}) was "
                    f"written {r4['outbox_mtimes'][0]} while claimed created_at runs to "
                    f"{r4['block_created_max']} (max lead {r4['max_lead_seconds']} s). All 15 are "
                    f"applied; {r4['n_with_map_content_locations']} are materialized as claims in "
                    "map content."
                ),
            },
        ],
        "findings": [
            {
                "id": "F-R6-01",
                "severity": "info",
                "statement": (
                    "Canonical bytes are intact: 6/6 pinned paths (5 held + F2b mirror) match the "
                    "FROZEN rev29 manifest 815e08079aef, and no canonical pin moved inside the probe "
                    "window (R1 PASS, R7 PASS)."
                ),
            },
            {
                "id": "F-R6-02",
                "severity": "info",
                "statement": (
                    "The fail-closed rule proposed by r4 (rank by _received_at; events lacking it "
                    "never confer precedence; created_at never confers precedence) resolves the F2b "
                    "held path and its mirror to the pin; it is an instrument-level recommendation, "
                    "not a repo declaration."
                ),
            },
            {
                "id": "F-R6-03",
                "severity": "info",
                "statement": (
                    "All five worker-06 artifacts referenced by the block exist on disk, so this is a "
                    "timestamp/ordering defect, not a phantom-artifact defect."
                ),
            },
        ],
        "recommendation_not_enacted": [
            "Declare the artifact-binding read path in the repo (controller/lead decision).",
            "Rank by _received_at; events lacking _received_at sort before every received event and "
            "can never shadow a frozen pin; agent-declared created_at never confers precedence.",
            "Re-stamp or annotate the deepseek-flash-06 block to its 00:42:23 write time so its "
            "pre-dated claims/statuses cannot outrank later evidence.",
            "Treat an artifact event whose claimed created_at post-dates its outbox write time as "
            "inadmissible for pin resolution until re-emitted.",
        ],
        "next_falsifier": report["next_falsifier"],
        "scope_note": report["scope_note"] + "; worker verdicts cannot set node status, "
                      "validation_status or a gate verdict",
        "deliverables": {
            "probe": "run_probe_r6.py",
            "probe_report": "evidence/raw/probe_report_r6.json",
            "raw_evidence": [
                "evidence/raw/instant_pins_r6.json",
                "evidence/raw/f2b_resolution_r6.json",
                "evidence/raw/future_cohort_r6.json",
                "evidence/raw/block_provenance_r6.json",
                "evidence/raw/applied_effects_r6.json",
                "evidence/raw/controls_r6.json",
            ],
        },
    }
    (HERE / "verdict.json").write_text(json.dumps(verdict, indent=1) + "\n")

    readme = f"""# W095-F2B-STREAM-BINDING-R6-VERIFY-01

Worker-095 bounded, class-bound, READ-ONLY probe. Node **F2b**, class
**AF-SCC-C0-VAC-GEN**, gate **G-FORM**. It does not set a node status, a
`validation_status`, or a gate verdict.

## Question

r4 (`artifacts/worker-095/freeze_hold_binding_integrity_r4/`) left one condition open:
is the accepted event stream, the stream that resolves "latest artifact per path" and
feeds `research_map.json`, able to bind bytes other than the FROZEN rev29 pin for the
held F2b artifact - and are the offending events already applied to the sole global
state?

## Answer (pinned at {report['probe_at']}, FROZEN rev29 `815e08079aef`)

Verdict **{report['verdict']}** (worker level).

- **R1 PASS.** 6/6 pinned paths match the manifest; {r3['n_future_dated']} events in the
  pinned stream snapshot claim `created_at` after the probe instant, and
  {r3['n_applied']} of them are applied; {r3['n_with_map_content_locations']} are
  materialized in map content (claims/reviews).
- **R2 FAIL.** `schemas/af_scc_c0_vacuum.yaml` resolves to the pin under file order
  (`lead-form-20260912T005743-02`, line {f2b['rules']['file_order_last']['line']}),
  `_received_at` max, and the fail-closed rule, but **created_at-max resolves to
  `e6b1af2bd692`** from `w06-20260912T0115-f2b-rev6` (line 712, no `_received_at`,
  outbox write time 00:42:23 vs claimed created_at 01:15:00, supersedes
  `cb897b29db12`). The F2b mirror resolves to the pin under all rules.
- **R4.** The deepseek-flash-06 block is {r4['block_ids_found']}/15 events at stream
  lines {r4['block_lines_min']}-{r4['block_lines_max']}, entirely inside the
  {r4['first_line_with_received_at'] - 1}-line unstamped prefix (first `_received_at`
  line {r4['first_line_with_received_at']}); written to
  `{r4['outbox_files'][0]}` at {r4['outbox_mtimes'][0]} with claimed created_at up to
  {r4['block_created_max']} (max lead {r4['max_lead_seconds']} s); all 15 applied,
  {r4['n_with_map_content_locations']} materialized as claims.
- **R6 PASS**: synthetic benign stream not flagged; synthetic pre-dated shadow flagged;
  double-run identical. **R7 PASS**: no canonical pin moved in the window.

Hard failures: {', '.join(h['id'] for h in verdict['hard_failures'])}.

## Files

- `run_probe_r6.py` - deterministic, read-only probe (writes only under this directory).
- `assemble_verdict_r6.py` - builds `verdict.json`, this README and `MANIFEST.json`.
- `evidence/raw/*.json` - raw measurements with their own sha256 in `MANIFEST.json`.
- `verdict.json` - worker-level verdict and falsifier.

## Falsifier

{report['next_falsifier']}

Any canonical byte move voids this window, not the finding. Worker measurement cannot
promote a gate or mark a node done.
"""
    (HERE / "README.md").write_text(readme)

    manifest = {"task_id": verdict["task_id"], "probe_at": report["probe_at"],
                "verdict": verdict["verdict"], "files": {}}
    for rel in ["run_probe_r6.py", "assemble_verdict_r6.py", "verdict.json", "README.md",
                "evidence/raw/instant_pins_r6.json", "evidence/raw/f2b_resolution_r6.json",
                "evidence/raw/future_cohort_r6.json", "evidence/raw/block_provenance_r6.json",
                "evidence/raw/applied_effects_r6.json", "evidence/raw/controls_r6.json",
                "evidence/raw/probe_report_r6.json"]:
        p = HERE / rel
        manifest["files"][rel] = sha256(p)
    (HERE / "MANIFEST.json").write_text(json.dumps(manifest, indent=1) + "\n")
    print(json.dumps({"verdict_json": sha256(HERE / "verdict.json"),
                      "manifest_sha256": sha256(HERE / "MANIFEST.json"),
                      "verdict": verdict["verdict"],
                      "hard_failures": [h["id"] for h in verdict["hard_failures"]]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
