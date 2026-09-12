#!/usr/bin/env python3
"""W049-CLASSSEP-LIVE4-STOPRULE-03 runner (worker-049, node A1, gate G-AUDIT).

Measures the post-card drift endpoint of the class-separation instrument against
the same pre-registered adversarial corpora used by W049-CLASSSEP-FN-AUDIT-01 and
W049-CLASSSEP-SUCCESSOR-AUDIT-02, and emits the adjudication stop-rule
determination verbatim from two booleans.

Panel (all four hash-pinned before measurement):
  * recovered_c266        pre-change canonical, recovered copy (baseline)
  * applied_a8c04fc3      hash named 'applied canonical' in the 01:00:35 card
  * staged_e2d24b92       hash named 'staged candidate' in the card
  * live_e36b0d644ca7     the bytes live now; NOT in the card

Harness functions are imported unmodified from the predecessor runner (sha256
recorded in results.json). Read-only on every input; fail-closed (exit 2) on any
pin mismatch; double in-memory run must be byte-identical (exit 3 otherwise).
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
RESULTS_PATH = HERE / "results.json"
PRE_REG_PATH = HERE / "pre_registration.json"
HARNESS_PATH = REPO / "artifacts/worker-049/classsep_successor_audit/run_successor_audit_049.py"
HARNESS_PIN = None  # filled at runtime from pre-registration of the predecessor task

PANEL = [
    {"id": "recovered_c266",
     "path": "artifacts/worker-049/classsep_fn_audit/pinned/class_separation_c266_recovered.py",
     "sha256": "c266dbceca87fb996bd76a774145ef511cbf2aae190d9f423167d3200783a920",
     "in_card": True},
    {"id": "applied_a8c04fc3",
     "path": "artifacts/worker-032/classsep-prose-01/pinned/class_separation.a8c04fc31e4a.py",
     "sha256": "a8c04fc31e4afa1b691cd6bfb6bf8b4f953a0adc925939a8351bab9cf453c5bd",
     "in_card": True},
    {"id": "staged_e2d24b92",
     "path": "proposed/class_separation.py",
     "sha256": "e2d24b927ee81c45996f8a4853d2f4b6899e8a3ea405c9e68b1ba5bb37448819",
     "in_card": True},
    {"id": "drift_e36b0d644ca7",
     "path": "artifacts/worker-045/classsep_e36_arm/pinned/class_separation_e36b0d644ca.py",
     "sha256": "e36b0d644ca75b1efc291b44a3188facb7839d81790073341431f3bb77b86eed",
     "in_card": False},
]

# Live path monitor. The live bytes are NOT loaded as a panel module by path: the
# live path is observed at start and end only, because it oscillated inside this
# task's window (e36b0d644ca7 at 01:06-01:08:14, a8c04fc31e4a restored 01:08:14).
LIVE_PATH = "research_map/class_separation.py"
LIVE_OBSERVATION = {
    "fail_closed_pin_check_1": {
        "at": "2026-09-12T01:07:5x+08:00",
        "measured_sha256": "e36b0d644ca75b1efc291b44a3188facb7839d81790073341431f3bb77b86eed",
        "source": "run_live4_audit_049.py exit 2 fail-closed output; live path no longer "
                  "matched the a8c04fc31e4a pin carried by the 01:00:35 adjudication card",
    },
    "pin_check_2_and_measurement": {
        "at": "2026-09-12T01:08:38+08:00",
        "measured_sha256": "a8c04fc31e4afa1b691cd6bfb6bf8b4f953a0adc925939a8351bab9cf453c5bd",
        "file_mtime": "2026-09-12T01:08:14.862303480+08:00",
        "source": "sha256sum + stat on research_map/class_separation.py",
    },
    "controller_record": "comms/inbox/astra.jsonl#astra-detector-patch-result-0112: "
                         "previous c266dbceca87, current e36b0d644ca, patch not accepted",
}

CORPORA_PINS = {
    "corpus_v1": ("artifacts/worker-049/classsep_fn_audit/corpus.json",
                  "9eb2ea9e27439703ffe7c91168348e6539e5a1fbd268f36383d09d0d3aeeea23"),
    "corpus_v2": ("artifacts/worker-049/classsep_fn_audit/corpus_guard_probe.json",
                  "db6dff9f4edaf585a78c2a5e084665c037db61bc354a86c5cba74f5f71c6ed8b"),
    "corpus_v3": ("artifacts/worker-049/classsep_successor_audit/corpus_v3.json",
                  "6764c04978c994c377dfc1e31558029cacb1203c15f83258f16798ecd73b219f"),
}
W07_RESULTS = ("artifacts/worker-07/class_separation_falsification/results.json",
               "d69ad58468be16655921dcf0eab9570fa6e7ccaf828558a45d4b306cce3de452")
W035_BATTERY = ("artifacts/worker-049/classsep_prose_fix/worker035_controls.json",
                "ef881c3aa6ef392c2068828b02d6645043913a0ff88ab0487264a6b770c5914d")
W098_SOURCE = ("artifacts/worker-098/classsep_mention_scope/run_battery_final.py",
               "bc8f58bb6cbddbf3ba30be40443b29d3865f296e54a3ba84391f653c2617f6b3")
W098_CONTROLS = "artifacts/worker-049/classsep_successor_audit/w098_controls.json"

APPLIED_CARD_HASH = "a8c04fc31e4afa1b691cd6bfb6bf8b4f953a0adc925939a8351bab9cf453c5bd"
RECOVERED_C266_HASH = "c266dbceca87fb996bd76a774145ef511cbf2aae190d9f423167d3200783a920"
CORPUS_ORDER = ("corpus_v1", "corpus_v2", "corpus_v3")


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    prereg = json.loads(PRE_REG_PATH.read_text())
    pins = {"panel": {}, "inputs": {}}
    bad = []

    for c in PANEL:
        p = REPO / c["path"]
        if not p.is_file():
            bad.append(f"panel {c['id']}: missing {p}")
            continue
        got = sha256_file(p)
        pins["panel"][c["id"]] = {"path": c["path"], "sha256": got,
                                  "expected": c["sha256"], "match": got == c["sha256"],
                                  "in_card": c["in_card"]}
        if got != c["sha256"]:
            bad.append(f"panel {c['id']}: {got} != {c['sha256']}")

    input_paths = dict(CORPORA_PINS)
    input_paths["worker07_corpus_results"] = W07_RESULTS
    input_paths["worker035_control_battery"] = W035_BATTERY
    input_paths["w098_controls_source"] = W098_SOURCE
    for name, (rel, want) in input_paths.items():
        p = REPO / rel
        if not p.is_file():
            bad.append(f"input {name}: missing {p}")
            continue
        got = sha256_file(p)
        pins["inputs"][name] = {"path": rel, "sha256": got, "expected": want,
                                "match": got == want}
        if got != want:
            bad.append(f"input {name}: {got} != {want}")

    if bad:
        print("PIN MISMATCH (fail closed):")
        for b in bad:
            print("  -", b)
        return 2

    harness_pin = prereg.get("harness_provenance", "")
    harness = load_module("w049_prev_harness", HARNESS_PATH)
    harness_sha = sha256_file(HARNESS_PATH)

    live_start = sha256_file(REPO / LIVE_PATH)
    live_mtime = (REPO / LIVE_PATH).stat().st_mtime
    dets = {c["id"]: load_module(f"cs_{c['id']}", REPO / c["path"]) for c in PANEL}
    corpora = {k: json.loads((REPO / v[0]).read_text()) for k, v in CORPORA_PINS.items()}
    controls = json.loads((REPO / W098_CONTROLS).read_text())
    source_text = (REPO / W098_SOURCE[0]).read_text(errors="replace")
    map_snapshot = json.loads((REPO / "research_map/research_map.json").read_text())

    def run_once() -> dict:
        out = {"corpora": {}, "controls": {}}
        for cname in CORPUS_ORDER:
            measured = {mid: harness.measure_fixtures(mod, corpora[cname]) for mid, mod in dets.items()}
            base = {r["id"]: r for r in measured["recovered_c266"]}
            block = {}
            for mid in dets:
                block[mid] = {
                    "rows": measured[mid],
                    "aggregates": harness.corpus_aggregates(
                        measured[mid], None if mid == "recovered_c266" else base),
                }
            out["corpora"][cname] = {"path": CORPORA_PINS[cname][0],
                                     "sha256": CORPORA_PINS[cname][1],
                                     "fixtures_total": len(corpora[cname]["fixtures"]),
                                     "modules": block}
        out["controls"]["worker07_regression"] = {
            mid: harness.re_score_worker07(mod, REPO / W07_RESULTS[0]) for mid, mod in dets.items()}
        out["controls"]["worker035_battery_advisory"] = {
            mid: harness.re_score_worker035(mod, REPO / W035_BATTERY[0]) for mid, mod in dets.items()}
        out["controls"]["w098_declared_controls"] = {
            mid: harness.re_score_w098(mod, controls, source_text) for mid, mod in dets.items()}
        out["controls"]["live_map_snapshot_hard_findings"] = {
            mid: len(mod.findings_for_map(map_snapshot)) for mid, mod in dets.items()}
        return out

    first = run_once()
    second = run_once()
    deterministic = json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)

    summary = {}
    for c in PANEL:
        mid = c["id"]
        s = {"cue_fn_total_all_corpora": 0, "non_cue_fn_total_all_corpora": 0,
             "adversarial_cleared_total_all_corpora": 0, "plain_fn_total_all_corpora": 0,
             "twins_not_flagged_all_corpora": 0, "per_corpus": {}}
        for cn in CORPUS_ORDER:
            a = first["corpora"][cn]["modules"][mid]["aggregates"]
            s["cue_fn_total_all_corpora"] += a["cue_induced_fn_total"]
            s["non_cue_fn_total_all_corpora"] += a["non_cue_fn_total"]
            s["adversarial_cleared_total_all_corpora"] += a["adversarial_cleared_total"]
            s["plain_fn_total_all_corpora"] += len(a["plain_positive_fn"])
            s["twins_not_flagged_all_corpora"] += len(a["twins_not_flagged"])
            s["per_corpus"][cn] = {
                "cue_fn": a["cue_induced_fn_total"],
                "cue_fn_high": a["cue_induced_fn_high_confidence"],
                "non_cue_fn": a["non_cue_fn_total"],
                "adversarial_cleared": a["adversarial_cleared_total"],
                "adversarial_total": a["adversarial_total"],
                "plain_fn": a["plain_positive_fn"],
                "twins_not_flagged": a["twins_not_flagged"],
                "mention_fp": a["mention_fp"],
            }
        w7 = first["controls"]["worker07_regression"][mid]
        w98 = first["controls"]["w098_declared_controls"][mid]
        s["worker07"] = f"{w7['tp']}/{w7['fn']}/{w7['tn']}/{w7['fp']}"
        s["worker07_verdict"] = w7["verdict"]
        s["w098_fire_all"] = w98["fire_all"]
        s["w098_clean_all_silent"] = w98["clean_all_silent"]
        s["w098_growth_all_zero"] = w98["growth_all_zero"]
        summary[mid] = s

    live_measured = pins["panel"]["drift_e36b0d644ca7"]["sha256"]
    live_end = sha256_file(REPO / LIVE_PATH)
    stop = {
        "condition_1_live_moved": True,  # observed e36b0d644ca7 live after the 01:00:35 card
        "condition_1_basis": LIVE_OBSERVATION,
        "condition_2_recovery_failed": pins["panel"]["recovered_c266"]["sha256"] != RECOVERED_C266_HASH,
        "card_named_hashes": [APPLIED_CARD_HASH, RECOVERED_C266_HASH,
                              "e2d24b927ee81c45996f8a4853d2f4b6899e8a3ea405c9e68b1ba5bb37448819"],
        "live_path": LIVE_PATH,
        "live_at_measure_start": live_start,
        "live_at_measure_end": live_end,
        "live_mtime_at_measure_start": live_mtime,
        "live_equals_card_applied_at_measurement": live_start == APPLIED_CARD_HASH,
        "drift_revision_measured_from_pinned_copy": live_measured,
        "stop_rule_text": "Stop if the live detector moves again or the recovered c266dbec copy fails hash verification; record the contest as unresolved rather than shipping a patch.",
        "determination": ("LIVE_MOVED_AND_REVERTED__INSTRUMENT_UNSTABLE__RECORD_UNRESOLVED"
                          if (live_start == APPLIED_CARD_HASH and pins["panel"]["recovered_c266"]["sha256"] == RECOVERED_C266_HASH)
                          else "RECOVERY_FAILED__RECORD_UNRESOLVED"),
    }

    first["schema"] = "worker-049/classsep-live4-stoprule-results/v1"
    first["task_id"] = "W049-CLASSSEP-LIVE4-STOPRULE-03"
    first["actor"] = "worker-049"
    first["node_id"] = "A1"
    first["gate"] = "G-AUDIT"
    first["class_id"] = "AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN"
    first["pins"] = pins
    first["corpora_pins"] = {k: {"path": v[0], "sha256": v[1]} for k, v in CORPORA_PINS.items()}
    first["panel"] = PANEL
    first["pre_registration_sha256"] = sha256_file(PRE_REG_PATH)
    first["harness"] = {"path": HARNESS_PATH.relative_to(REPO).as_posix(),
                        "sha256": harness_sha, "note": harness_pin}
    first["summary"] = summary
    first["stop_rule_determination"] = stop
    first["double_run_byte_deterministic"] = deterministic
    first["non_claims"] = prereg["non_claims"]

    # drift check after measurement
    drift = {"panel": {}, "inputs": {}}
    for c in PANEL:
        now = sha256_file(REPO / c["path"])
        drift["panel"][c["id"]] = {"pinned": c["sha256"], "at_end": now, "moved": now != c["sha256"]}
    for name, (rel, want) in input_paths.items():
        now = sha256_file(REPO / rel)
        drift["inputs"][name] = {"pinned": want, "at_end": now, "moved": now != want}
    map_end = sha256_file(REPO / "research_map/research_map.json")
    drift["inputs"]["live_map"] = {"pinned": None, "at_end": map_end, "moved": None}
    first["drift"] = drift
    if not deterministic:
        print("INTERNAL INCONSISTENCY: double run differs", file=sys.stderr)
        return 3

    RESULTS_PATH.write_text(json.dumps(first, indent=1, sort_keys=False) + "\n")
    print(f"wrote {RESULTS_PATH.relative_to(REPO)} sha256={sha256_file(RESULTS_PATH)}")
    for cn in CORPUS_ORDER:
        print(f"-- {cn} --")
        for c in PANEL:
            a = first["corpora"][cn]["modules"][c["id"]]["aggregates"]
            print(f"   {c['id']:22s} cueFN={a['cue_induced_fn_total']:2d} "
                  f"(H={a['cue_induced_fn_high_confidence']}) "
                  f"cleared={len(a['adversarial_cleared'])}/{a['adversarial_total']} "
                  f"twins={a['twin_controls_flagged']} mentionFP={len(a['mention_fp'])} "
                  f"declDiff={len(a.get('declaration_diff_vs_c266', []))}")
    print("-- summary --")
    for mid, s in summary.items():
        print(f"   {mid:22s} cueFN={s['cue_fn_total_all_corpora']:2d} "
              f"plainFN={s['plain_fn_total_all_corpora']} w07={s['worker07']} {s['worker07_verdict']}")
    print("-- stop rule --")
    print("  ", json.dumps({k: v for k, v in stop.items() if k != "stop_rule_text"}))
    print(f"deterministic={deterministic} panel_drift="
          f"{any(v['moved'] for v in drift['panel'].values())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
