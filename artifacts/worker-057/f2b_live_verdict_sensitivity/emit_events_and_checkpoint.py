#!/usr/bin/env python3
"""
W057-GFORM-F2B-VERDICT-SENSITIVITY-01 -- emitter.

Writes, in order:
  1. manifest.json            (hashes of report.json / REPORT.md / instrument / this file)
  2. comms/outbox/worker-057.jsonl   (status, 4x artifact, claim, blocker, status-complete)
  3. runtime/state/w057_checkpoint_f2b_verdict_sensitivity.json
     runtime/state/w057_checkpoints.jsonl  (append)

Idempotent: event ids are derived from the report corpus digest, and already-present ids are
skipped.  Validates every event with research_map/schemas.validate_event before writing.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
TASK = "W057-GFORM-F2B-VERDICT-SENSITIVITY-01"
ACTOR = "worker-057"
NODE = "F2b"
CLASS_ID = "AF-SCC-C0-VAC-GEN"
GATE = "G-FORM"
CST = timezone(timedelta(hours=8))


def sha256_file(p: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def jdump(o) -> str:
    return json.dumps(o, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main() -> int:
    sys.path.insert(0, str(ROOT / "research_map"))
    from schemas import validate_event, SchemaError  # noqa: E402

    rep_p = HERE / "report.json"
    md_p = HERE / "REPORT.md"
    inst_p = HERE / "audit_f2b_verdict_sensitivity.py"
    emit_p = HERE / "emit_events_and_checkpoint.py"
    for p in (rep_p, md_p, inst_p):
        if not p.exists():
            raise SystemExit("missing %s" % p)
    report = json.loads(rep_p.read_text(encoding="utf-8"))
    corpus = report["review_corpus"]["corpus_sha256"]
    tag = "w057-f2bsens-%s" % corpus[:8]
    w072 = next((v for v in report["verdict_inventory"]
                 if v["reviewer"] == "worker-072" and v["verdict"] == "accept"
                 and v.get("current_file")), None)
    w072_ref = ("reviews/F2b-review-worker-072-rev29.json#"
                + (w072["current_file"]["sha256"][:12] if w072 else "unresolved"))

    hashes = {
        "artifacts/worker-057/f2b_live_verdict_sensitivity/report.json": sha256_file(rep_p),
        "artifacts/worker-057/f2b_live_verdict_sensitivity/REPORT.md": sha256_file(md_p),
        "artifacts/worker-057/f2b_live_verdict_sensitivity/audit_f2b_verdict_sensitivity.py": sha256_file(inst_p),
        "artifacts/worker-057/f2b_live_verdict_sensitivity/emit_events_and_checkpoint.py": sha256_file(emit_p),
    }
    manifest = {
        "schema": "worker-057/artifact-manifest/v1",
        "task_id": TASK,
        "actor": ACTOR,
        "node_id": NODE,
        "class_id": CLASS_ID,
        "gate": GATE,
        "generated_from_corpus": corpus,
        "artifact_sha256": hashes,
        "verdict": report["verdict"],
        "controls": "%d/%d" % (report["controls_passed"], report["controls_total"]),
        "authority_note": report["authority_note"],
    }
    man_p = HERE / "manifest.json"
    man_p.write_text(jdump(manifest), encoding="utf-8")
    man_hash = sha256_file(man_p)
    hashes["artifacts/worker-057/f2b_live_verdict_sensitivity/manifest.json"] = man_hash

    # ------------------------------------------------------------------ build + validate events
    t = now()
    ev = []
    ev.append({
        "event_id": tag + "-status-start", "event_type": "status", "created_at": t, "actor": ACTOR,
        "node_id": NODE, "class_id": CLASS_ID, "class_ids": [CLASS_ID], "gate": GATE, "task_id": TASK,
        "status": "active", "hours": 0.4,
        "summary": ("Bounded read-only census opened: F2b live-hash accept-vs-revise instrument "
                    "sensitivity at schemas/af_scc_c0_vacuum.yaml#%s (corpus %s)."
                    % (report["live_carriers"]["sha256"][:12], corpus[:12])),
        "evidence_refs": [report["live_carriers"]["file"] + "#" + report["live_carriers"]["sha256"][:12]],
        "next_falsifier": report["falsifier"],
    })
    for slug, rel in [
        ("report", "artifacts/worker-057/f2b_live_verdict_sensitivity/report.json"),
        ("reportmd", "artifacts/worker-057/f2b_live_verdict_sensitivity/REPORT.md"),
        ("instrument", "artifacts/worker-057/f2b_live_verdict_sensitivity/audit_f2b_verdict_sensitivity.py"),
        ("manifest", "artifacts/worker-057/f2b_live_verdict_sensitivity/manifest.json"),
    ]:
        ev.append({
            "event_id": tag + "-artifact-" + slug, "event_type": "artifact", "created_at": t,
            "actor": ACTOR, "node_id": NODE, "class_id": CLASS_ID, "gate": GATE, "task_id": TASK,
            "artifact_type": "worker_measurement", "path": rel, "sha256": hashes[rel],
            "validation_status": "unverified",
            "evidence_refs": [rel + "#" + hashes[rel][:12]],
        })
    ev.append({
        "event_id": tag + "-claim", "event_type": "claim", "created_at": t, "actor": ACTOR,
        "node_id": NODE, "class_id": CLASS_ID, "class_ids": [CLASS_ID], "gate": GATE, "task_id": TASK,
        "conclusion_type": "formal_model",
        "statement": (
            "Artifact-and-instrument census at the pinned F2b bytes "
            "schemas/af_scc_c0_vacuum.yaml#%s (FROZEN rev29 %s): the live-hash verdict corpus holds "
            "%d accept(s) and %d revise(s); 0 of %d accept instruments name either live blocking "
            "carrier text (regularity.must_not_conflate[0] line 152 'No containment with C2 or C0 is "
            "asserted here'; implication_ledger.forbidden_transfers[0].reason line 246 'C2 is a "
            "strictly larger extension class') and 0 of %d read the contradicted chain field "
            "extension_class_containment (line 239), while %d of %d revise instruments do; the "
            "controller's own 01:10 scan counts 3 full accepts [worker-071, worker-072, worker-090] "
            "at these bytes and 0 of those 3 is carrier-capable; and 1 accepted-event row "
            "(worker-072, accept 4.0 at 01:10:13) has an on-disk same-review_id file now carrying "
            "verdict=revise 3.0 with blocking finding W072-F2B-HF-01 on the line-152 carrier. "
            "Therefore the >=2-accept coverage count at this hash is met only by instruments that "
            "cannot have exercised the two live carriers, and the count is unstable in time. "
            "Measurement only: no gate verdict, no review verdict, no truth value."
            % (report["live_carriers"]["sha256"][:12],
               report["pins"]["artifacts/formulation/FROZEN.json"]["sha256"][:12],
               report["conflict_matrix"]["accepts"]["n"],
               report["conflict_matrix"]["revises"]["n"],
               report["conflict_matrix"]["accepts"]["n"],
               report["conflict_matrix"]["accepts"]["n"],
               report["conflict_matrix"]["revises"]["hc2_detect_capable"],
               report["conflict_matrix"]["revises"]["n"])),
        "assumptions": [
            "the seven pinned inputs hash to their recorded values; a moved byte voids the census",
            "an instrument whose source contains none of the seven pre-registered probes cannot have "
            "exercised the corresponding carrier text (deductive, not statistical)",
            "instrument paths are taken from each verdict's own declared references; unresolved "
            "instruments are reported as unresolved, not as blind",
            "the census is bound to review_corpus.corpus_sha256; review files are live and one was "
            "rewritten in place during the measurement window (F2BS-07)",
        ],
        "falsifier": report["falsifier"],
        "evidence_refs": [
            "artifacts/worker-057/f2b_live_verdict_sensitivity/report.json#" + hashes[
                "artifacts/worker-057/f2b_live_verdict_sensitivity/report.json"][:12],
            "artifacts/worker-057/f2b_live_verdict_sensitivity/REPORT.md#" + hashes[
                "artifacts/worker-057/f2b_live_verdict_sensitivity/REPORT.md"][:12],
            "schemas/af_scc_c0_vacuum.yaml#" + report["live_carriers"]["sha256"][:12],
            "artifacts/formulation/FROZEN.json#" + report["pins"][
                "artifacts/formulation/FROZEN.json"]["sha256"][:12],
            w072_ref,
        ],
        "artifact_refs": ["artifacts/worker-057/f2b_live_verdict_sensitivity/manifest.json#" + man_hash[:12]],
    })
    ev.append({
        "event_id": tag + "-blocker-adjudication", "event_type": "blocker", "created_at": t,
        "actor": ACTOR, "node_id": NODE, "class_id": CLASS_ID, "gate": GATE, "task_id": TASK,
        "description": (
            "Live-hash accept coverage for F2b is met by carrier-blind instruments: 0 of 7 accept "
            "instruments (0 of the 3 controller-counted full accepts) name either live blocking "
            "carrier and 0 read the contradicted chain, while 13 of 32 revise instruments do; one "
            "controller-counted accept (worker-072) has already been rewritten to revise on disk."),
        "needed_to_unblock": (
            "Adjudication by the audit lead (astra-life05-verify-gform-r3): (a) rule whether the "
            "line-152 denial and line-246 inverted size premise are material to a G-FORM F2b pass; "
            "and (b) if material, require the F2b owner to land a repair at a new hash and re-collect "
            ">=2 full accepts from instruments that read the carriers. The alternative discharge is a "
            "live-hash accept whose instrument exercises both carriers and records why they are "
            "non-material. No mathematics is required from this worker."),
        "evidence_refs": [
            "artifacts/worker-057/f2b_live_verdict_sensitivity/report.json#" + hashes[
                "artifacts/worker-057/f2b_live_verdict_sensitivity/report.json"][:12],
            "reviews/F2b-review-worker-018-rev13.json",
            "reviews/F2b-review-rev29-075.json",
            "reviews/F2b-review-worker-072-rev29.json",
            "runtime/state/controller_verification/lifecycle_20260912-011029.json#717a7bb370fe",
        ],
        "next_falsifier": report["next_falsifier"],
    })
    ev.append({
        "event_id": tag + "-status-complete", "event_type": "status", "created_at": t, "actor": ACTOR,
        "node_id": NODE, "class_id": CLASS_ID, "class_ids": [CLASS_ID], "gate": GATE, "task_id": TASK,
        "status": "active", "task_state": "complete", "claims_completion": False, "hours": 0.4,
        "summary": ("Bounded task complete; node status unchanged (worker events cannot set done): "
                    "instrument written, 12/12 controls pass, report emitted, adjudication blocker "
                    "recorded, no schema modified, no review or gate verdict claimed. Checkpoint written "
                    "to runtime/state/w057_checkpoint_f2b_verdict_sensitivity.json and appended to "
                    "runtime/state/w057_checkpoints.jsonl. This worker slot exits after this event."),
        "evidence_refs": [rel + "#" + h[:12] for rel, h in sorted(hashes.items())],
        "next_falsifier": report["next_falsifier"],
    })

    for e in ev:
        try:
            validate_event(e)
        except SchemaError as ex:
            raise SystemExit("event schema error in %s: %s" % (e.get("event_id"), ex))

    outbox = ROOT / "comms/outbox/worker-057.jsonl"
    existing = set()
    if outbox.exists():
        for line in outbox.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                existing.add(json.loads(line).get("event_id"))
            except Exception:
                continue
    new = [e for e in ev if e["event_id"] not in existing]
    with open(outbox, "a", encoding="utf-8") as f:
        for e in new:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    # ------------------------------------------------------------------------------ checkpoint
    def ck(name):
        return next(c for c in report["controls"] if c["name"] == name)["pass"]

    checks_true = [
        "all_controls_C1_C12_pass",
        "live_F2b_pins_match",
        "both_live_carriers_present_at_line_152_line_246",
        "contradicting_chain_present_at_line_239",
        "zero_of_seven_accept_instruments_name_a_carrier_text",
        "zero_of_seven_accept_instruments_read_the_contradicted_chain",
        "thirteen_of_thirtytwo_revise_instruments_carrier_capable",
        "controller_counted_accepts_carrier_blind_0_of_3",
        "accept_to_revise_on_disk_flip_recorded",
    ]
    checks_false = [
        "accept_instrument_carrier_capable",
        "controller_counted_accept_carrier_capable",
        "live_full_accept_count_stable_in_time",
        "accepts_and_blocking_findings_mutually_discharged",
    ]
    ckpt = {
        "agent": ACTOR,
        "artifacts": hashes,
        "checkpointed_at": t,
        "checks_false": checks_false,
        "checks_true": checks_true,
        "claims_completion": False,
        "class_ids": [CLASS_ID],
        "controls_passed": report["controls_passed"],
        "controls_total": report["controls_total"],
        "emitted_event_ids": [e["event_id"] for e in ev],
        "events_appended_now": [e["event_id"] for e in new],
        "findings": [{"id": f["id"], "state": f["state"], "statement": f["statement"]}
                     for f in report["findings"]],
        "gate": GATE,
        "inputs": {k: {"sha256": v["sha256"], "match": v["match"], "bytes": v.get("bytes")}
                   for k, v in report["pins"].items()},
        "next_falsifier": report["next_falsifier"],
        "node_id": NODE,
        "reserved_adjudication": (
            "Are the line-152 containment denial and the line-246 inverted size premise material to a "
            "G-FORM F2b pass, given that the >=2-accept count at this hash rests on instruments that "
            "do not read either carrier?"),
        "review_corpus": report["review_corpus"],
        "task_id": TASK,
        "task_state": "complete",
        "verdict": report["verdict"],
    }
    cp = ROOT / "runtime/state/w057_checkpoint_f2b_verdict_sensitivity.json"
    cp.write_text(jdump(ckpt), encoding="utf-8")
    with open(ROOT / "runtime/state/w057_checkpoints.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(ckpt, ensure_ascii=False) + "\n")

    print(jdump({
        "task": TASK,
        "verdict": report["verdict"],
        "controls": "%d/%d" % (report["controls_passed"], report["controls_total"]),
        "events_appended": len(new),
        "events_total": len(ev),
        "manifest_sha256": man_hash,
        "checkpoint": str(cp.relative_to(ROOT)),
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
