#!/usr/bin/env python3
"""Write the worker-002 checkpoint for the R2 F0 binding-chain repair.

Outputs:
  runtime/state/w002_rebind_r2_checkpoint.json      (full snapshot)
  runtime/state/w002_rebind_r2_checkpoints.jsonl    (append-only log)
  artifacts/flash-02/checkpoints/checkpoints.jsonl  (artifact-local log)
  artifacts/flash-02/checkpoints/CHECKPOINT.md      (human line, appended)

Worker checkpoints are evidence only: they cannot set node status, validation
status or gate verdicts.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
from pathlib import Path

EVENTS_PATH = Path("comms/outbox/deepseek-flash-02.jsonl")
MAP = Path("research_map/research_map.json")
ARTIFACTS = [
    "schemas/taxonomy_cases.jsonl",
    "artifacts/flash-02/leak_rule_catalog.json",
    "artifacts/flash-02/rebind_rows_r2.py",
    "artifacts/flash-02/rebind_rows_r2_report.json",
    "artifacts/flash-02/rebind_catalog_pin.py",
    "artifacts/flash-02/rebind_catalog_pin_report.json",
    "artifacts/flash-02/check_taxonomy_cases.py",
    "artifacts/flash-02/taxonomy_cases_check_report.json",
    "artifacts/flash-02/reports/check_stale_pin_guard.fail.f0c20b96.json",
    "artifacts/flash-02/rebind_r2_independent_check.json",
    "artifacts/flash-02/snapshots/taxonomy_cases.pre-rebind-r2.f0c20b96.jsonl",
    "artifacts/flash-02/snapshots/leak_rule_catalog.pre-rebind-r2.215f6e22.json",
]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    now = _dt.datetime.now().astimezone().isoformat(timespec="seconds")
    ckpt_id = "w002-f0-rebind-r2-" + now
    checker = json.loads(Path("artifacts/flash-02/taxonomy_cases_check_report.json").read_text())
    indep = json.loads(Path("artifacts/flash-02/rebind_r2_independent_check.json").read_text())
    rows_rep = json.loads(Path("artifacts/flash-02/rebind_rows_r2_report.json").read_text())
    cat_rep = json.loads(Path("artifacts/flash-02/rebind_catalog_pin_report.json").read_text())
    outbox_ids = []
    if EVENTS_PATH.exists():
        for line in EVENTS_PATH.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except ValueError:
                continue
            if str(e.get("event_id", "")).startswith("flash02-f0rebindr2"):
                outbox_ids.append(e["event_id"])

    ckpt = {
        "checkpoint_id": ckpt_id,
        "actor": "worker-002",
        "agent_id": "deepseek-flash-02",
        "measured_at": now,
        "task": ("One class-bound task: repair HF-094C-1 (F0 corpus rows pinned a superseded "
                 "taxonomy revision while the meta pinned rev5) and the companion stale catalog "
                 "pin; harden the class-separation checker with a stale-pin guard + control C11; "
                 "verify independently; emit protocol events."),
        "node_id": "F0",
        "gate": "G-F0",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN",
                      "AF-WCC-SCALAR-SPH"],
        "authority_note": ("worker event; cannot set node status=done, validation_status=passed, "
                           "or a gate verdict"),
        "hash_moves": {
            "schemas/taxonomy_cases.jsonl": {
                "before": "f0c20b96f76dc21b32ae81962bb3aa207b04e90c28aa6da8a686e0d9f649a1e8",
                "after": sha(Path("schemas/taxonomy_cases.jsonl"))},
            "artifacts/flash-02/leak_rule_catalog.json": {
                "before": "215f6e228250827a3f80a6155fd9a71c0ed0548e347e1d7ec3332275f1fb6f17",
                "after": sha(Path("artifacts/flash-02/leak_rule_catalog.json"))},
        },
        "taxonomy_pin": {"path": "research_map/formulation_taxonomy.yaml",
                         "sha256": sha(Path("research_map/formulation_taxonomy.yaml")),
                         "revision": 5},
        "artifacts": {p: {"sha256": sha(Path(p)), "exists": Path(p).exists()} for p in ARTIFACTS},
        "measurements": {
            "rows_rebind": {"verdict": rows_rep.get("verdict"), "mode": rows_rep.get("mode"),
                            "stale_rows": rows_rep["counts"]["rows_stale"],
                            "replaced": rows_rep["counts"]["rows_replaced"],
                            "guards": rows_rep.get("guards")},
            "catalog_rebind": {"verdict": cat_rep.get("verdict"), "mode": cat_rep.get("mode"),
                               "applied_state_verified": cat_rep.get("applied_state_verified"),
                               "guards": cat_rep.get("guards")},
            "checker": {"verdict": checker.get("verdict"),
                        "controls": len(checker.get("controls", [])),
                        "controls_all_detected": checker.get("controls_all_detected"),
                        "cases": checker.get("counts"),
                        "errors": len(checker.get("errors", []))},
            "independent": {"verdict": indep.get("verdict"),
                            "checks": {c["id"]: c["pass"] for c in indep.get("checks", [])}},
        },
        "outbox_event_ids": outbox_ids,
        "concurrent_ingest_note": ("The controller ingested an intermediate emitter pass "
                                   "(...004433) before the corrected pass was deduplicated, so "
                                   "events.jsonl holds two identical artifact/status sets plus "
                                   "the accepted claim 0100b; the one rejected event "
                                   "(claim 0100, invalid conclusion_type) is superseded and "
                                   "recorded in comms/rejected.jsonl. Hashes are identical in "
                                   "both sets."),
        "map_observed": {"path": str(MAP), "sha256": sha(MAP),
                         "updated_at": json.loads(MAP.read_text()).get("updated_at")},
        "falsifier": indep.get("falsifier"),
        "next_falsifier": ("Re-run python3 artifacts/flash-02/verify_rebind_r2.py (expect PASS "
                           "8/8) and python3 artifacts/flash-02/check_taxonomy_cases.py (expect "
                           "PASS 11/11); restore the snapshot if any row content differs."),
        "rollback": {
            "corpus": "cp artifacts/flash-02/snapshots/taxonomy_cases.pre-rebind-r2.f0c20b96.jsonl schemas/taxonomy_cases.jsonl",
            "catalog": "cp artifacts/flash-02/snapshots/leak_rule_catalog.pre-rebind-r2.215f6e22.json artifacts/flash-02/leak_rule_catalog.json",
        },
    }
    out = Path("runtime/state/w002_rebind_r2_checkpoint.json")
    out.write_text(json.dumps(ckpt, indent=2) + "\n")
    with Path("runtime/state/w002_rebind_r2_checkpoints.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(ckpt, ensure_ascii=False) + "\n")

    local = {"checkpoint_id": ckpt_id, "measured_at": now, "hours": 0.5,
             "task": "F0 R2 binding-chain repair (HF-094C-1)",
             "artifacts": {p: sha(Path(p))[:12] for p in ARTIFACTS},
             "taxonomy": {"sha256": ckpt["taxonomy_pin"]["sha256"][:12], "revision": 5},
             "verdicts": {"rows_rebind": rows_rep.get("verdict"),
                          "catalog_rebind": cat_rep.get("verdict"),
                          "checker": checker.get("verdict"),
                          "independent": indep.get("verdict")},
             "note": "hash move f0c20b96 -> ccf7041b (corpus), 215f6e22 -> ccec815e (catalog)"}
    with Path("artifacts/flash-02/checkpoints/checkpoints.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(local, ensure_ascii=False) + "\n")
    md = Path("artifacts/flash-02/checkpoints/CHECKPOINT.md")
    with md.open("a", encoding="utf-8") as f:
        f.write(f"- {ckpt_id} {now} R2 repair: corpus ccf7041b catalog ccec815e "
                f"checker {checker.get('verdict')} indep {indep.get('verdict')}\n")

    print(f"checkpoint: {out}")
    print(f"events logged: {len(outbox_ids)}")
    print(f"hash moves: {json.dumps(ckpt['hash_moves'], indent=2)[:400]}")
    print(f"measurements: rows={rows_rep.get('verdict')} catalog={cat_rep.get('verdict')} "
          f"checker={checker.get('verdict')} independent={indep.get('verdict')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
