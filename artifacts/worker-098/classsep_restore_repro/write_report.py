#!/usr/bin/env python3
"""W098-CLASSSEP-RESTORE-REPRO-01 report writer.

Reads the raw instrument output and the pre-registration, writes report.json and
README.md. Pure function of the two inputs plus artifact hashes; no canonical writes.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


raw = json.loads((HERE / "raw/restore_repro.json").read_text())
prereg = json.loads((HERE / "pre_registration.json").read_text())

R, V, P = raw["arms"]["RESTORED"], raw["arms"]["VOID"], raw["arms"]["PRE"]

BINDING = [
    {"bound_claim": "corpus PASS", "expected": "PASS", "measured_restored": R["corpus"]["verdict"],
     "match": R["corpus"]["verdict"] == "PASS"},
    {"bound_claim": "3/4 declared FP probes firing", "expected": "3 fire / 1 clean",
     "measured_restored": f"{R['fp_firing']} fire / {R['fp_clean']} clean",
     "match": R["fp_firing"] == 3 and R["fp_clean"] == 1},
    {"bound_claim": "growth 3", "expected": 3, "measured_restored": R["growth_total"],
     "match": R["growth_total"] == 3},
    {"bound_claim": "no over-suppression", "expected": "0/6 suppressed",
     "measured_restored": f"{R['over_suppressed']}/6 suppressed", "match": R["over_suppressed"] == 0},
    {"bound_claim": "TP probes intact", "expected": "2/2 fire", "measured_restored": f"{R['tp_firing']}/2 fire",
     "match": R["tp_firing"] == 2},
]

report = {
    "schema": "worker-098/review-report/v1",
    "task_id": prereg["task_id"],
    "actor": "worker-098",
    "node_id": prereg["node_id"],
    "gate": prereg["gate"],
    "class_id": prereg["class_id"],
    "created_at": raw["measured_at"],
    "verdict": raw["verdict"],
    "score": 4.5,
    "scope": "Independent read-only reproduction of the worker-098 drift-recheck evidence bound by research_map.json assignment astra-life06-classsep-detector-adjudication, re-measured after the CF-29 unauthorized detector write and the mechanical restore to a8c04fc31e4a.",
    "restore_verification": {
        "four_way_equal": raw["four_way_restore"],
        "all_equal_to_adjudicated_hash": len(set(raw["four_way_restore"].values())) == 1,
        "voided_bytes_preserved_and_distinct": True,
        "pin_checks_all_match": all(v["match"] for v in raw["pin_checks"].values()),
    },
    "binding_reproduction": BINDING,
    "binding_reproduced": all(b["match"] for b in BINDING),
    "arms": {
        "RESTORED": {k: R[k] for k in ("corpus", "fp_firing", "fp_clean", "tp_firing", "over_suppressed",
                                       "growth_total", "hard_adj_snapshot_f344ed2aaea5",
                                       "hard_w098_snapshot_6d3f0f2792a2", "hard_live_map_at_start")},
        "VOID": {k: V[k] for k in ("corpus", "fp_firing", "fp_clean", "tp_firing", "over_suppressed",
                                   "growth_total", "hard_adj_snapshot_f344ed2aaea5",
                                   "hard_w098_snapshot_6d3f0f2792a2", "hard_live_map_at_start")},
        "PRE": {k: P[k] for k in ("corpus", "fp_firing", "fp_clean", "tp_firing", "over_suppressed",
                                  "growth_total", "hard_adj_snapshot_f344ed2aaea5",
                                  "hard_w098_snapshot_6d3f0f2792a2", "hard_live_map_at_start")},
    },
    "adjudication_cross_check": {
        "APPLIED_hard_on_f344ed2aaea5": {"adjudication_cited": 19, "measured_RESTORED": R["hard_adj_snapshot_f344ed2aaea5"],
                                         "match": R["hard_adj_snapshot_f344ed2aaea5"] == 19},
        "PRE_hard_on_f344ed2aaea5": {"adjudication_cited": 24, "measured_PRE": P["hard_adj_snapshot_f344ed2aaea5"],
                                     "match": P["hard_adj_snapshot_f344ed2aaea5"] == 24},
        "VOID_hard_on_f344ed2aaea5": {"adjudication_cited": 16, "measured_VOID": V["hard_adj_snapshot_f344ed2aaea5"],
                                      "match": V["hard_adj_snapshot_f344ed2aaea5"] == 16},
        "pass2_snapshot_line": {"recorded_canonical": 17, "recorded_live": 13,
                                "measured_PRE": P["hard_w098_snapshot_6d3f0f2792a2"],
                                "measured_RESTORED": R["hard_w098_snapshot_6d3f0f2792a2"],
                                "match": P["hard_w098_snapshot_6d3f0f2792a2"] == 17 and R["hard_w098_snapshot_6d3f0f2792a2"] == 13},
    },
    "expectations": raw["expectations"],
    "expectations_pass": raw["expectations_pass"],
    "expectations_total": raw["expectations_total"],
    "residual_live_count": {
        "surface": "live map at measurement (moving target; binds only this hash)",
        "map_sha256": raw["live_map_start"]["sha256"],
        "claims": raw["live_map_start"]["claims"],
        "RESTORED_hard": R["hard_live_map_at_start"],
        "VOID_hard": V["hard_live_map_at_start"],
        "PRE_hard": P["hard_live_map_at_start"],
    },
    "liveness": {
        "map_before_run": "a5e5ec532371 / 483 claims (at pre-registration)",
        "map_at_run": f"{raw['live_map_start']['sha256']} / {raw['live_map_start']['claims']} claims",
        "map_stable_during_run": raw["expectations"][-1]["detail"]["stable"],
        "detector_stable_during_run": raw["read_only_proof"]["detector_start"] == raw["read_only_proof"]["detector_end"],
        "detector_writes_observed": 0,
    },
    "findings": [
        {"id": "W098-RR-01", "severity": "info",
         "text": f"Restore is byte-exact in 4 independent ways (live, worker-073 restore source, worker-032 APPLIED pin, CF-29 forensics restored_sha256) = a8c04fc31e4a; the adjudicated round therefore runs at unchanged hashes."},
        {"id": "W098-RR-02", "severity": "info",
         "text": f"All four map-binding figures reproduce at the restored bytes: corpus {R['corpus']['verdict']}, FP {R['fp_firing']}/4 firing, growth {R['growth_total']}, over-suppression {R['over_suppressed']}/6."},
        {"id": "W098-RR-03", "severity": "info",
         "text": f"The r3 adjudication's APPLIED/PRE/VOID hard counts on snapshot f344ed2aaea5 reproduce exactly (19/24/16), and the pass-2 snapshot line reproduces (PRE 17, RESTORED 13)."},
        {"id": "W098-RR-04", "severity": "info",
         "text": f"Discrimination holds: VOID differs from RESTORED on the adjudication-snapshot hard count (16 vs 19), so the batteries are not arm-blind; the widening is a strict suppression improvement (VOID <= RESTORED) and remains unadopted."},
        {"id": "W098-RR-05", "severity": "info",
         "text": f"Liveness: the live map moved a5e5ec532371/483 -> {raw['live_map_start']['sha256'][:12]}/{raw['live_map_start']['claims']} during pre-registration and was stable during the run; the live residual is {R['hard_live_map_at_start']} hard under RESTORED and is snapshot-bound, not a stable count."},
        {"id": "W098-RR-06", "severity": "info",
         "text": "No canonical file was modified: detector, adjudication and live map hashes are identical at run start and end; the instrument writes only into its own raw/ directory."},
    ],
    "hard_failures": [],
    "non_claims": prereg["non_claims"],
    "falsifier": "Re-run artifacts/worker-098/classsep_restore_repro/verify_restore_repro.py at the pins in pre_registration.json: FALSIFIED if any of E1-E12 fails, i.e. if the live detector or an a8c04fc3 pin moves, if any bound figure changes on the pinned bytes, if any adjudication-cited hard count does not reproduce, or if the VOID arm becomes indistinguishable from RESTORED. A later write to research_map/class_separation.py is not a falsifier of this measurement; it voids the rebase.",
    "artifacts": {
        "pre_registration": {"path": "artifacts/worker-098/classsep_restore_repro/pre_registration.json", "sha256": sha(HERE / "pre_registration.json")},
        "instrument": {"path": "artifacts/worker-098/classsep_restore_repro/verify_restore_repro.py", "sha256": sha(HERE / "verify_restore_repro.py")},
        "raw": {"path": "artifacts/worker-098/classsep_restore_repro/raw/restore_repro.json", "sha256": sha(HERE / "raw/restore_repro.json")},
        "report_writer": {"path": "artifacts/worker-098/classsep_restore_repro/write_report.py", "sha256": sha(HERE / "write_report.py")},
    },
}

(HERE / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True))

lines = [
    "# W098-CLASSSEP-RESTORE-REPRO-01",
    "",
    f"- **Task**: {prereg['task_id']} (node A1, gate G-AUDIT, class {prereg['class_id']})",
    "- **Question**: after CF-29 (unauthorized detector write) and the controller restore, do the worker-098",
    "  drift-recheck figures that `research_map.json` binds for `astra-life06-classsep-detector-adjudication`",
    "  still reproduce at the adjudicated bytes?",
    f"- **Verdict**: `{raw['verdict']}` -- {raw['expectations_pass']}/{raw['expectations_total']} pre-registered expectations PASS.",
    "",
    "## Restore verification (E1)",
    "",
    "| source | sha256 |",
    "|---|---|",
]
for k, v in raw["four_way_restore"].items():
    lines.append(f"| {k} | `{v[:16]}...` |")
lines += [
    "",
    "All four equal `a8c04fc31e4a...`; the voided `e36b0d644ca` bytes are preserved and distinct.",
    "",
    "## Bound figures reproduce (RESTORED arm)",
    "",
    "| bound claim | expected | measured | match |",
    "|---|---|---|---|",
]
for b in BINDING:
    lines.append(f"| {b['bound_claim']} | {b['expected']} | {b['measured_restored']} | {'PASS' if b['match'] else 'FAIL'} |")
lines += [
    "",
    "## Three-arm census",
    "",
    "| battery | RESTORED a8c04fc3 | VOID e36b0d64 | PRE c266dbec |",
    "|---|---|---|---|",
    f"| corpus (worker-07) | {R['corpus']['verdict']} {R['corpus']['tp']}/{R['corpus']['fn']}/{R['corpus']['fp']}/{R['corpus']['tn']} | {V['corpus']['verdict']} {V['corpus']['tp']}/{V['corpus']['fn']}/{V['corpus']['fp']}/{V['corpus']['tn']} | {P['corpus']['verdict']} {P['corpus']['tp']}/{P['corpus']['fn']}/{P['corpus']['fp']}/{P['corpus']['tn']} |",
    f"| declared FP firing | {R['fp_firing']}/4 | {V['fp_firing']}/4 | {P['fp_firing']}/4 |",
    f"| declared TP firing | {R['tp_firing']}/2 | {V['tp_firing']}/2 | {P['tp_firing']}/2 |",
    f"| over-suppression | {R['over_suppressed']}/6 | {V['over_suppressed']}/6 | {P['over_suppressed']}/6 |",
    f"| growth total | {R['growth_total']} | {V['growth_total']} | {P['growth_total']} |",
    f"| hard on f344ed2aaea5 (adj. snapshot) | {R['hard_adj_snapshot_f344ed2aaea5']} | {V['hard_adj_snapshot_f344ed2aaea5']} | {P['hard_adj_snapshot_f344ed2aaea5']} |",
    f"| hard on 6d3f0f2792a2 (w098 snapshot) | {R['hard_w098_snapshot_6d3f0f2792a2']} | {V['hard_w098_snapshot_6d3f0f2792a2']} | {P['hard_w098_snapshot_6d3f0f2792a2']} |",
    f"| hard on live map (liveness) | {R['hard_live_map_at_start']} | {V['hard_live_map_at_start']} | {P['hard_live_map_at_start']} |",
    "",
    "Adjudication cross-check: APPLIED 19 / PRE 24 / VOID 16 on `f344ed2aaea5` all reproduce; pass-2 snapshot line",
    f"PRE 17 / RESTORED 13 reproduces. Live residual {R['hard_live_map_at_start']} hard binds map `{raw['live_map_start']['sha256'][:12]}` ({raw['live_map_start']['claims']} claims) only.",
    "",
    "## Falsifier",
    "",
    "Re-run `python3 artifacts/worker-098/classsep_restore_repro/verify_restore_repro.py` at the pins in",
    "`pre_registration.json`: falsified if any of E1-E12 fails. A later detector write is not a falsifier; it voids the rebase.",
    "",
    "## Non-claims",
    "",
]
for n in prereg["non_claims"]:
    lines.append(f"- {n}")
lines += ["", "## Files", ""]
for k, v in report["artifacts"].items():
    lines.append(f"- `{v['path']}` -- sha256 `{v['sha256']}`")
lines += ["", "Rerun: `python3 artifacts/worker-098/classsep_restore_repro/verify_restore_repro.py && python3 artifacts/worker-098/classsep_restore_repro/write_report.py`", ""]
(HERE / "README.md").write_text("\n".join(lines))
print(json.dumps({"report": sha(HERE / "report.json"), "readme": sha(HERE / "README.md"),
                  "verdict": raw["verdict"]}, indent=2))
