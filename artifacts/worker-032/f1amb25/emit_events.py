#!/usr/bin/env python3
"""Emit W032-F1AMB25-STALE-VERIFY-01 artifacts/checkpoints/events.

Reads the already-produced artifacts, writes CHECKPOINT.json plus the worker-local
runtime/state checkpoints, then appends validated JSON events to
comms/outbox/worker-032.jsonl. Fail-closed: every event is validated with
research_map.schemas.validate_event before anything is appended, and every declared
artifact must exist with the declared sha256.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event, SchemaError  # noqa: E402

CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat(timespec="seconds")
TS = datetime.now(CST).strftime("%Y%m%dT%H%M%S")
OUTBOX = ROOT / "comms" / "outbox" / "worker-032.jsonl"
STATE = ROOT / "runtime" / "state"

SUITE = "schemas/f1_falsifier_tests.jsonl"
F1 = "schemas/af_wcc_vacuum.yaml"
F0 = "research_map/formulation_taxonomy.yaml"
FROZEN = "artifacts/formulation/FROZEN.json"
PINS = {
    SUITE: "56bcb4b3234bc86c324bec6e38f142c5ef39517f20d823b6a333f578b7d0851e",
    F1: "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3",
    F0: "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    FROZEN: "2f358f6722d920621a66c0259cb48d35a5e3c1b706f28adf37ed467325fcedf1",
}
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def relhash(rel: str) -> str:
    return sha(ROOT / rel)


def main() -> int:
    art = {
        "checker": HERE / "check_amb25.py",
        "report": HERE / "report.json",
        "readme": HERE / "README.md",
        "run_vendor": HERE / "run_vendor.py",
        "vendor_report": HERE / "vendor_report.json",
        "vendor_tool": ROOT / "artifacts/worker-032/run/verify_freeze_current.py",
    }
    missing = [str(p) for p in art.values() if not p.exists()]
    if missing:
        print(json.dumps({"error": "missing artifacts", "missing": missing}, indent=1))
        return 2
    H = {k: sha(v) for k, v in art.items()}

    live = {rel: relhash(rel) for rel in PINS}
    drift = {rel: {"pinned": PINS[rel], "live": live[rel]} for rel in PINS if live[rel] != PINS[rel]}

    report = json.loads(art["report"].read_text())
    vendor = json.loads(art["vendor_report"].read_text())
    if report.get("verdict") != "stale_assertion_confirmed" or report.get("failures"):
        print(json.dumps({"error": "own checker did not confirm", "verdict": report.get("verdict"),
                          "failures": report.get("failures")}, indent=1))
        return 2

    checkpoint = {
        "checkpoint_id": f"w032-f1amb25-ckpt1-{TS}",
        "created_at": NOW,
        "actor": "worker-032",
        "task_id": "W032-F1AMB25-STALE-VERIFY-01",
        "node_id": "F1",
        "class_id": "AF-WCC-VAC-GEN",
        "class_ids": CLASS_IDS,
        "gate": "G-FORM",
        "stage": "worker-lifecycle-complete",
        "pins": PINS,
        "post_report_live_drift": drift,
        "artifacts": {k: {"path": str(v.relative_to(ROOT)), "sha256": H[k]} for k, v in art.items()},
        "verdict": report["verdict"],
        "own_checker": {"probes_stored_pass": report["suite"]["stored_pass"],
                        "probes_recomputed_pass": report["suite"]["probes_total"] - len(report["mismatches"]),
                        "mismatches": len(report["mismatches"]),
                        "stale_cross_artifacts": len(report["cross_artifact"]["stale"]),
                        "expectations_failed": report["failures"]},
        "author_verifier": {"verdict": vendor["verdict"], "failures": vendor["failures"]},
        "next_falsifier": "Re-run check_amb25.py after any suite/F0/F1/FROZEN rewrite; the "
                          "measurement is retired by a hash move and falsified if the AMB-25 "
                          "deciding probe recomputes true against live F0.",
    }
    (HERE / "CHECKPOINT.json").write_text(json.dumps(checkpoint, indent=1, ensure_ascii=False) + "\n")
    H["checkpoint"] = sha(HERE / "CHECKPOINT.json")
    checkpoint["artifacts"]["checkpoint"] = {"path": "artifacts/worker-032/f1amb25/CHECKPOINT.json",
                                             "sha256": H["checkpoint"]}
    (HERE / "CHECKPOINT.json").write_text(json.dumps(checkpoint, indent=1, ensure_ascii=False) + "\n")
    H["checkpoint"] = sha(HERE / "CHECKPOINT.json")

    (STATE / "w032_f1amb25_checkpoint_1.json").write_text(
        json.dumps(checkpoint, indent=1, ensure_ascii=False) + "\n")
    with open(STATE / "w032_f1amb25_checkpoints.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"checkpoint_id": checkpoint["checkpoint_id"], "created_at": NOW,
                            "verdict": report["verdict"], "mismatches": len(report["mismatches"]),
                            "stale_cross_artifacts": len(report["cross_artifact"]["stale"]),
                            "checkpoint_sha256": H["checkpoint"]}, ensure_ascii=False) + "\n")
    H["emit_events"] = sha(HERE / "emit_events.py")

    def ev(eid: str, typ: str, **kw) -> dict:
        e = {"event_id": f"w032-f1amb25-{TS}-{eid}", "event_type": typ, "created_at": NOW,
             "actor": "worker-032", "class_ids": CLASS_IDS, **kw}
        return e

    art_events = [
        ("artifact-checker", "verification_tool", "artifacts/worker-032/f1amb25/check_amb25.py",
         H["checker"], "Independent stdlib+PyYAML recomputation of all 84 stored probes; "
                       "--selftest 11/11; exit 0 iff EXP1..EXP8 hold."),
        ("artifact-report", "verification_report", "artifacts/worker-032/f1amb25/report.json",
         H["report"], "Pinned measurement: 84 stored passes, 82 recomputed, 2 mismatches both "
                      "in F1-AMB-25, 1 stale cross-artifact, drift 0, verdict stale_assertion_confirmed."),
        ("artifact-vendor-report", "cross_tool_log", "artifacts/worker-032/f1amb25/vendor_report.json",
         H["vendor_report"], "Suite author's own verify_freeze_current.py re-run at the same pins "
                             "(output redirected): verify_fail, failures [C3, C8, C9]; C8 82/84."),
        ("artifact-run-vendor", "verification_tool", "artifacts/worker-032/f1amb25/run_vendor.py",
         H["run_vendor"], "Runner that imports the byte-identical vendored author verifier "
                          f"(sha256 {H['vendor_tool'][:16]}) and redirects only its report path."),
        ("artifact-readme", "documentation", "artifacts/worker-032/f1amb25/README.md",
         H["readme"], "Method, pins, result table, controls, cross-check, falsifier, reproduce, "
                      "scope limits."),
        ("artifact-checkpoint", "checkpoint", "artifacts/worker-032/f1amb25/CHECKPOINT.json",
         H["checkpoint"], "Worker-local checkpoint: pins, artifact hashes, verdict, next falsifier."),
    ]
    events = [ev("status-claim", "status", node_id="F1", status="active", hours=0.0,
                 summary="No assignment card exists in comms/inbox/worker-032.jsonl. Took ONE "
                         "unclaimed class-bound task: W032-F1AMB25-STALE-VERIFY-01, independent "
                         "recomputation of schemas/f1_falsifier_tests.jsonl#56bcb4b3234b against "
                         "live F0 research_map/formulation_taxonomy.yaml#0abb9ed8a961, focused on "
                         "row F1-AMB-25 (declared-F0 staleness). Read-only; no gate verdict.",
                 evidence_refs=[f"{SUITE}#{PINS[SUITE][:16]}", f"{F0}#{PINS[F0][:16]}"],
                 next_falsifier="check_amb25.py re-run; see report.json falsifier field.")]
    for eid, atype, path, digest, note in art_events:
        events.append(ev(eid, "artifact", node_id="F1", artifact_type=atype, path=path,
                         sha256=digest, validation_status="unverified", note=note,
                         evidence_refs=[f"{path}#{digest[:16]}"]))
    events.append(ev("claim", "claim", node_id="F1", gate="G-FORM", class_id="AF-WCC-VAC-GEN",
                     conclusion_type="formal_model",
                     statement="At pins suite schemas/f1_falsifier_tests.jsonl#56bcb4b3234b, F1 "
                               "schemas/af_wcc_vacuum.yaml#cce9c60146d6, F0 "
                               "research_map/formulation_taxonomy.yaml#0abb9ed8a961 and FROZEN "
                               "artifacts/formulation/FROZEN.json#2f358f6722d9, the suite's stored "
                               "84/84 probe-pass claim is false against the live canonical pair: an "
                               "independent recomputation yields 82/84, with exactly two mismatches, "
                               "both in row F1-AMB-25 - (a) f0_binding.declared_f0_sha256 equals "
                               "expects the superseded F0 rev4 hash 276009f4f63d while live F0 rev5 is "
                               "0abb9ed8a961, and (b) f0_binding.binding_note still requires "
                               "'astra-classscope-02'. The row's cross_artifact binding declares F0 "
                               "276009f4f63d and is stale against disk, while its binding_sha256 "
                               "correctly names F1 rev12 cce9c60146d6, so the re-pin moved only the F1 "
                               "axis. The suite author's own verifier, re-run at the same pins, "
                               "returns verify_fail with C8 (82/84) and C9 (1 stale cross-artifact). "
                               "The suite must not be cited as 84/84 G-FORM evidence until F1-AMB-25's "
                               "F0 expectations are refreshed and the suite re-emitted.",
                     assumptions=[
                         "checks read only the pinned byte copies under artifacts/worker-032/f1amb25/pinned/",
                         "probe semantics mirror the suite author's verify_freeze_current.py; the implementation is independent, the semantics are not",
                         "the suite's stored 84/84 claim is the object under test, not an input",
                         "worker events cannot set node status or gate verdicts"],
                     falsifier="Re-run check_amb25.py against the pinned copies; falsified if "
                               "F1-AMB-25's f0_binding.declared_f0_sha256 equality probe recomputes "
                               "true against the live F0 canonical, or the stored-vs-recomputed "
                               "mismatch set is empty, or the AMB-25 cross_artifact hash equals the "
                               "live F0 canonical, or the suite no longer hashes to 56bcb4b3234b.",
                     evidence_refs=[
                         f"{SUITE}#{PINS[SUITE][:16]}", f"{F1}#{PINS[F1][:16]}",
                         f"{F0}#{PINS[F0][:16]}", f"{FROZEN}#{PINS[FROZEN][:16]}",
                         f"artifacts/worker-032/f1amb25/report.json#{H['report'][:16]}",
                         f"artifacts/worker-032/f1amb25/vendor_report.json#{H['vendor_report'][:16]}"],
                     artifact_refs=[f"artifacts/worker-032/f1amb25/report.json#{H['report'][:16]}",
                                    f"artifacts/worker-032/f1amb25/vendor_report.json#{H['vendor_report'][:16]}"]))
    events.append(ev("review", "review", node_id="F1", gate="G-FORM", class_id="AF-WCC-VAC-GEN",
                     target_id=f"{SUITE}#{PINS[SUITE][:16]}", reviewer="worker-032",
                     verdict="revise", score=2.5,
                     hard_failures=["HF-W032-AMB25-1: the suite's stored 84/84 probe-pass claim is "
                                    "false at its own bound pins (82/84 recomputed); F1-AMB-25 "
                                    "asserts the superseded F0 rev4 expectation 276009f4f63d and a "
                                    "stale cross-artifact binding while recording pass=true"],
                     findings=[
                         {"id": "F1", "severity": "hard", "finding": "F1-AMB-25 deciding probe "
                          "f0_binding.declared_f0_sha256 equals expects 276009f4f63d (F0 rev4); live F0 rev5 is 0abb9ed8a961; stored pass=true is unsupported."},
                         {"id": "F2", "severity": "hard", "finding": "F1-AMB-25 f0_binding.binding_note contains 'astra-classscope-02' is false against the rev12 note."},
                         {"id": "F3", "severity": "hard", "finding": "F1-AMB-25 cross_artifact declares research_map/formulation_taxonomy.yaml = 276009f4f63d; measured 0abb9ed8a961 (C9 stale 1/1)."},
                         {"id": "F4", "severity": "major", "finding": "astra-life03-repin-claims moved only the F1-axis binding (binding_sha256 = cce9c60146d6 is current) and left the F0 axis superseded; the row's own next_falsifier fired."},
                         {"id": "F5", "severity": "minor", "finding": "author verifier C3: suite re-pinned to 56bcb4b3234b after the last submitted report c4c477adcb7a, so the 84/84 record trails the frozen suite."}],
                     evidence_refs=[f"{SUITE}#{PINS[SUITE][:16]}", f"{F0}#{PINS[F0][:16]}",
                                    f"artifacts/worker-032/f1amb25/report.json#{H['report'][:16]}",
                                    f"artifacts/worker-032/f1amb25/vendor_report.json#{H['vendor_report'][:16]}"]))
    events.append(ev("blocker", "blocker", node_id="F1",
                     description="G-FORM evidence schemas/f1_falsifier_tests.jsonl#56bcb4b3234b "
                                 "stores 84/84 probe passes but recomputes 82/84 at the live canonical "
                                 "pair (F1 rev12 cce9c60146d6, F0 rev5 0abb9ed8a961): F1-AMB-25 still "
                                 "expects F0 rev4 276009f4f63d in both its deciding equality probe and "
                                 "its cross_artifact binding, and its binding_note probe expects the "
                                 "superseded 'astra-classscope-02' text. The suite's own verifier "
                                 "returns verify_fail (C8/C9).",
                     needed_to_unblock="Formulation lead (owner of astra-life03-repin-claims): refresh "
                                       "F1-AMB-25's f0_binding.declared_f0_sha256 expectation and "
                                       "cross_artifact[0].sha256 to the live F0 canonical 0abb9ed8a961 "
                                       "and update the binding_note expectation, re-run the row's probes, "
                                       "re-emit the suite artifact + sha256; then an independent re-run of "
                                       "check_amb25.py must return zero mismatches. Controller: do not bind "
                                       "a G-FORM verdict to the 84/84 claim until this is repaired.",
                     evidence_refs=[f"{SUITE}#{PINS[SUITE][:16]}", f"{F0}#{PINS[F0][:16]}",
                                    f"artifacts/worker-032/f1amb25/report.json#{H['report'][:16]}",
                                    f"artifacts/worker-032/f1amb25/vendor_report.json#{H['vendor_report'][:16]}"]))
    events.append(ev("status-final", "status", node_id="F1", status="active", hours=0.3,
                     summary="CHECKPOINT + EXIT. W032-F1AMB25-STALE-VERIFY-01 complete at worker "
                             "level: one bounded class-bound task taken without an inbox card; "
                             "independent recomputation + the suite author's own verifier both show "
                             "the 84/84 stored claim is 82/84 at the pinned F1 rev12 / F0 rev5 pair, "
                             "with exactly two F1-AMB-25 mismatches and one stale cross-artifact. No "
                             "node status, gate verdict, or shared map state was modified.",
                     evidence_refs=[f"artifacts/worker-032/f1amb25/report.json#{H['report'][:16]}",
                                    f"artifacts/worker-032/f1amb25/vendor_report.json#{H['vendor_report'][:16]}",
                                    f"artifacts/worker-032/f1amb25/CHECKPOINT.json#{H['checkpoint'][:16]}",
                                    f"runtime/state/w032_f1amb25_checkpoint_1.json#{sha(STATE / 'w032_f1amb25_checkpoint_1.json')[:16]}"],
                     next_falsifier="Any rewrite of suite/F0/F1/FROZEN retires this measurement; "
                                    "re-pin and re-run check_amb25.py. Cleared only if the AMB-25 "
                                    "F0-axis expectations are refreshed and zero mismatches recompute."))

    bad = []
    for e in events:
        try:
            validate_event(e)
        except SchemaError as exc:
            bad.append({"event_id": e.get("event_id"), "error": str(exc)})
    if bad:
        print(json.dumps({"error": "event validation failed; nothing appended", "bad": bad}, indent=1))
        return 2

    with open(OUTBOX, "a", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    print(json.dumps({"appended": len(events), "outbox": str(OUTBOX.relative_to(ROOT)),
                      "checkpoint_sha256": H["checkpoint"], "artifact_hashes": H,
                      "live_drift": drift, "event_ids": [e["event_id"] for e in events]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
