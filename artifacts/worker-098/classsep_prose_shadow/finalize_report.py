#!/usr/bin/env python3
"""W098-CLASSSEP-PROSE-SHADOW-01 finalizer.

Reads the frozen raw outputs (never re-measures, never touches the map) and adds
the structured findings + verdict to report.json. Deterministic.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
report = json.loads((HERE / "report.json").read_text())
probes = json.loads((RAW / "probes.json").read_text())
mapb = json.loads((RAW / "map_battery.json").read_text())
growth = json.loads((RAW / "growth.json").read_text())
accept = json.loads((RAW / "acceptance.json").read_text())

fp_failed = [r["text"] for r in probes["fp"] if not r["ok"]]
over_suppressed = [r["name"] for r in probes["fn"] if r["over_suppressed"]]
residual = report["residual_named_claims"]
residual_rows = [{"index": int(i), "event_id": v["event_id"], "canonical": v["canonical"],
                  "shadow": v["shadow"]} for i, v in sorted(residual.items(), key=lambda kv: int(kv[0]))]
shadow_hard_claims = sorted({f.split(" in claims[")[1].split("]")[0]
                             for f in mapb["shadow_hard"] if " in claims[" in f})

findings = [
    {
        "id": "W098-CPS-01", "severity": "major",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "acceptance_criterion": "#3 (the 4 declared false-positive probes become clean)",
        "measured": f"{len(probes['fp']) - len(fp_failed)}/{len(probes['fp'])} declared FP probes clean under the shadow; still firing: {fp_failed}",
        "root_cause": ("the patch reuses _NEG_BEFORE_ASSERT (anchored, and its \\w+ cannot span the composite) "
                       "at sentence scope, so a negative cue separated from the assertion word by the composite "
                       "token ('no <composite> merge') is still not recognised"),
        "impact": "acceptance criterion #3 is NOT met as written; the live claim with this shape remains hard",
        "suggested_minimal_repair": ("add a sentence-scoped negative cue, e.g. r'\\bno\\b[^.!?]{0,40}\\bmerge' "
                                     "in prose mode, or allow the composite span inside _NEG_BEFORE_ASSERT"),
    },
    {
        "id": "W098-CPS-02", "severity": "major",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "acceptance_criterion": "#4 (the named claims drop to 0 findings)",
        "measured": (f"live-map hard count {mapb['canonical_hard_count']} -> {mapb['shadow_hard_count']} under the shadow, "
                     f"not 0; residual hard findings on claims at snapshot indices {shadow_hard_claims} "
                     f"({[r['event_id'] for r in residual_rows]})"),
        "root_cause": "same metalinguistic-mention class as W098-CPS-01 (no explicit negative/metalinguistic cue the patch recognises)",
        "impact": "G-AUDIT would still see 4 hard CLASSSEP findings after the patch as written",
        "note": ("proposal indices were taken at map 11311ab36005; this run snapshots 6d3f0f2792a2. "
                 "7 of the proposal's 8 named indices clear; index 144 persists; indices 152/187/192 arrived after the proposal"),
    },
    {
        "id": "W098-CPS-03", "severity": "major",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "acceptance_criterion": "over-suppression control (not stated in the proposal)",
        "measured": f"{len(over_suppressed)}/{len(probes['fn'])} pre-registered genuine merge assertions are suppressed by the shadow: {over_suppressed}",
        "root_cause": "_META is applied to the whole sentence and skips the match unconditionally, so a genuine merge assertion co-occurring with 'case', 'test', 'corpus', 'independent', 'pattern' or 'not the case ... separate' is dropped",
        "impact": "the patch as written introduces at least 6 false-negative classes; the 27-fixture corpus still PASSes, so its acceptance #1/#2 do not detect them",
        "suggested_minimal_repair": "gate the _META skip on the absence of a positive merge assertion in the same sentence, and narrow _META to mention-only words",
    },
    {
        "id": "W098-CPS-04", "severity": "info",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "acceptance_criterion": "mechanism confirmation",
        "measured": (f"growth probes canonical {growth['canonical_delta_total']} -> shadow {growth['shadow_delta_total']}; "
                     f"shadow clears {mapb['canonical_hard_count'] - mapb['shadow_hard_count']}/{mapb['canonical_hard_count']} live hard findings; "
                     f"declaration parity 10/10 identical; shadow diff = {report['shadow_provenance']['diff_lines_added']} added lines, "
                     f"{report['shadow_provenance']['diff_lines_removed']} removed lines, {report['shadow_provenance']['hunks']} hunks"),
        "impact": "the patch direction is confirmed: metalinguistic-mention false positives are the dominant G-AUDIT blocker and prose-sentence scoping removes most of them without touching declaration mode",
    },
    {
        "id": "W098-CPS-05", "severity": "info",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "acceptance_criterion": "corpus sensitivity",
        "measured": (f"worker-07 corpus: canonical {report['corpus']['canonical']['tp']}/{report['corpus']['canonical']['tp'] + report['corpus']['canonical']['fn']} leaks, "
                     f"{report['corpus']['canonical']['tn']}/{report['corpus']['canonical']['tn'] + report['corpus']['canonical']['fp']} controls, FP {report['corpus']['canonical']['fp']}, FN {report['corpus']['canonical']['fn']}; "
                     f"shadow PASS identically, yet 6 over-suppression probes are missed"),
        "impact": "the corpus under-specifies the false-negative side; recommend adding the 6 FN probes (raw/probes.json fn battery) before re-running the acceptance",
    },
    {
        "id": "W098-CPS-06", "severity": "info",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "acceptance_criterion": "provenance",
        "measured": (f"all {mapb['canonical_hard_count']} canonical hard findings are claim-statement findings in the frozen map JSON; "
                     f"the done-node artifact scan contributed 0 hard findings"),
        "impact": "the map-level hard count is a function of the frozen map snapshot alone; concurrent artifact churn does not affect it",
    },
]

verdict = {
    "verdict": "revise",
    "score": 3.0,
    "scope": ("independent shadow implementation and acceptance test of classsep_prose_precision_patch.md at the pinned hashes; "
              "NOT a gate verdict, NOT a canonical patch, NOT a node completion"),
    "acceptance_pass": f"{sum(accept.values())}/{len(accept)}",
    "blocking": ["W098-CPS-01", "W098-CPS-02", "W098-CPS-03"],
    "falsifier": ("Re-run run_shadow_test.py at the pinned hashes: this verdict is falsified if the shadow clears the "
                  "'no <composite> merge' probe and all residual live claims while the 6 genuine-merge probes still fire "
                  "and declaration parity holds; or if research_map/class_separation.py moves off c266dbceca87, "
                  "artifacts/formulation/proposals/classsep_prose_precision_patch.md moves off edeb6588a17b, or the map "
                  "snapshot moves off its recorded sha256."),
}

report["findings"] = findings
report["verdict"] = verdict
report["shadow_hard_claim_indices"] = shadow_hard_claims
report["fp_probes_still_firing"] = fp_failed
report["over_suppressed_probes"] = over_suppressed
report["generated_by"] = "finalize_report.py (reads raw/*.json only; no re-measurement)"
(HERE / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True))

manifest_path = HERE / "snapshot" / "MANIFEST.json"
man = json.loads(manifest_path.read_text())
man["report_sha256"] = hashlib.sha256((HERE / "report.json").read_bytes()).hexdigest()
man["finalize_sha256"] = hashlib.sha256((HERE / "finalize_report.py").read_bytes()).hexdigest()
man["instrument_sha256"] = hashlib.sha256((HERE / "run_shadow_test.py").read_bytes()).hexdigest()
man["finalized_at"] = "2026-09-12T00:52:00+08:00"
manifest_path.write_text(json.dumps(man, indent=2, sort_keys=True))
print(json.dumps({"findings": [f["id"] + ":" + f["severity"] for f in findings],
                  "verdict": verdict["verdict"], "acceptance": verdict["acceptance_pass"],
                  "residual_claims": residual_rows,
                  "report_sha256": man["report_sha256"]}, indent=2))
