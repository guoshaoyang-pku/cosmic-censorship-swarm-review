#!/usr/bin/env python3
"""W012-N0-C3-DISCHARGE-01 event emitter.

Appends the task's events to comms/outbox/deepseek-flash-12.jsonl. Idempotent by
event_id (re-running never duplicates). Every event is validated with the repository's
own research_map.schemas.validate_event BEFORE it is written; a schema failure aborts
without writing. Artifact hashes are measured at emit time so no event can carry a
stale self-pin.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
OUTBOX = REPO / "comms" / "outbox" / "deepseek-flash-12.jsonl"
BASE = "artifacts/worker-012/n0/c3_discharge"
TASK_ID = "W012-N0-C3-DISCHARGE-01"
CLASS = "AF-WCC-SCALAR-SPH"
NODE = "N0"
GATE = "G-NUM"
ACTOR = "deepseek-flash-12"

sys.path.insert(0, str(REPO))
from research_map.schemas import validate_event  # noqa: E402


def sha(rel: str) -> str:
    h = hashlib.sha256()
    with open(REPO / rel, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ref(rel: str, n: int = 12) -> str:
    return f"{rel}#{sha(rel)[:n]}"


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def build() -> list[dict]:
    report_path = f"{BASE}/raw/report.json"
    verify_path = f"{BASE}/verify_c3_discharge.py"
    readme_path = f"{BASE}/README.md"
    checkpoint_path = f"{BASE}/checkpoint.json"
    emitter_path = f"{BASE}/emit_events.py"
    report = json.loads((REPO / report_path).read_text())
    orders = report["certification_audit"]["recomputed_certified_orders"]
    cs = report["check_summary"]
    fresh = report["fresh_rerun"]
    fresh_rungs = {k: len(v) for k, v in fresh.items() if not k.startswith("_")}
    fresh_secs = fresh.get("_runtime_seconds")
    xc = report["independent_crosschecks"]
    dispositions = report["dispositions"]
    majors = [d["finding"] for d in dispositions if "major" in d["severity"]]
    minors = report["open_minor_text_findings"]
    proto_pin = "numerics/CONVERGENCE_PROTOCOL.md#1e6cdf04d7a2"
    cert_pin = "numerics/protocol/n0_fixed_dt_certification.json#1677822ceb9c"
    frozen_pin = "numerics/tests/flat_wave_replication.py#8ade1cdc163e"
    pub_pin = "numerics/tests/n0_order_4rung.json#c88146a1375c"

    artifacts = [
        ("report", report_path, "adjudication_report", "machine-checked per-finding disposition + recomputed fits + fresh re-run"),
        ("freshrun", f"{BASE}/raw/fresh_rerun.json", "fresh_rerun_rows", "fresh frozen-module l2_error rows at dt=1e-4 (lffd x4, cnfd/cnfem endpoints) + runtime"),
        ("verify", verify_path, "verification_harness", "read-only checker: pins, protocol-text audit, independent lstsq, fresh frozen-module re-execution"),
        ("readme", readme_path, "readme", "task framing, method, independence, falsifiers, authority boundary"),
        ("checkpoint", checkpoint_path, "checkpoint", "pins, headline, checks, dispositions, artifact hashes"),
        ("emitter", emitter_path, "protocol_event_emitter", "idempotent, schema-validated event emitter for this task"),
    ]
    events: list[dict] = []
    for i, (name, path, atype, note) in enumerate(artifacts, start=1):
        events.append(
            {
                "event_id": f"w012-c3-artifact-{i:04d}-{name}",
                "event_type": "artifact",
                "created_at": now(),
                "actor": ACTOR,
                "node_id": NODE,
                "class_id": CLASS,
                "gate": GATE,
                "task_id": TASK_ID,
                "slot": "worker-012",
                "artifact_type": atype,
                "path": path,
                "sha256": sha(path),
                "validation_status": "unverified",
                "note": note,
            }
        )

    events.append(
        {
            "event_id": "w012-c3-review-0001-adjudication",
            "event_type": "review",
            "created_at": now(),
            "actor": ACTOR,
            "reviewer": ACTOR,
            "node_id": NODE,
            "class_id": CLASS,
            "gate": GATE,
            "task_id": TASK_ID,
            "target_id": proto_pin,
            "target_kind": "protocol",
            "verdict": "accept",
            "score": 4.0,
            "hard_failures": [],
            "adjudication_support": True,
            "not_a_gate_verdict": True,
            "counts_as_g_num_protocol_accept": False,
            "reviewed_pins": {
                "protocol": proto_pin,
                "certification": cert_pin,
                "frozen_module": frozen_pin,
                "published_4rung": pub_pin,
            },
            "findings": [
                f"C3 CONTEST ADJUDICATION at protocol {proto_pin}: all four MAJOR findings ({', '.join(majors)}) are DISCHARGED by the re-based fixed-dt certification {cert_pin} (four rungs, dt=1e-4 constant, lffd {orders['lffd']:.6f} / cnfd {orders['cnfd']:.6f} / cnfem {orders['cnfem']:.6f}, cross-scheme R5 agree, cfl=0.5 demoted to a labelled mixed-order control). The unchanged protocol text section 3.4 already prescribes fixed dt, so text and claim no longer conflict and no revision 4 is required to discharge the majors.",
                f"Two MINOR protocol-TEXT findings remain literally open at 1e6cdf04 and cannot be discharged by evidence re-basing: w067-F2 (R2 max(1e-12, 10 x solver_tolerance) has no defined null branch) and w067-F3 (section 6 body still carries the superseded 0.35 sentence; revision-2 amendment (a) in the same section already replaces it with R5). Both are non-blocking; they warrant a one-line rev-4 cleanup whenever the protocol is next touched (a rev 4 moves the hash and needs a fresh review).",
                f"Independent method: own least-squares recomputation of every declared fit from raw rows ({cs['passed']}/{cs['total']} checks pass, 0 fail); fresh bounded re-execution of frozen module {frozen_pin} at dt=1e-4 reproduced filed rows for {fresh_rungs} in {fresh_secs}s; cross-checks against flash-13, worker-046 (orders identical to {abs(xc['worker046']['orders']['lffd'] - orders['lffd']):.1e}) and worker-020 all consistent with the certification.",
                "w081-WITHDRAWAL stands and is not dischargeable: a withdrawn author verdict is procedural, not a finding against the protocol text.",
                "This is adjudication-support reviewer input from a non-audit worker; it does not set the G-NUM gate verdict or the audit accept, both of which remain controller/audit authority.",
            ],
            "falsifier": report["falsifier"],
            "evidence_refs": [
                ref(report_path),
                ref(verify_path),
                proto_pin,
                cert_pin,
                frozen_pin,
                pub_pin,
                "reviews/G-NUM-protocol-review.json#8137f18f1a3b",
            ],
        }
    )

    events.append(
        {
            "event_id": "w012-c3-claim-0001-discharge",
            "event_type": "claim",
            "created_at": now(),
            "actor": ACTOR,
            "node_id": NODE,
            "class_id": CLASS,
            "gate": GATE,
            "task_id": TASK_ID,
            "conclusion_type": "formal_model",
            "assumptions": [
                "the map's protocol hash 1e6cdf04d7a2 is the operative revision-3 pin and is unchanged",
                "the re-based certification 1677822ceb9c is the evidence the lead's claim lnum-claim-...-303b3a rests on",
                "the two revise verdicts (w067, w081) and the audit accept all bind the same protocol hash",
                "no canonical file was modified by this task",
            ],
            "statement": (
                f"Adjudication-support result for the C3 contest at {proto_pin}: the four major findings "
                f"({', '.join(majors)}) are discharged by the re-based fixed-dt certification {cert_pin} "
                f"(recomputed orders lffd {orders['lffd']:.6f}, cnfd {orders['cnfd']:.6f}, cnfem {orders['cnfem']:.6f}; "
                f"all four rungs at dt=1e-4; cross-scheme R5 agree; cfl=0.5 retained only as a labelled mixed-order control), "
                f"so the text/claim conflict the revise verdicts named no longer exists and no revision 4 is required to "
                f"discharge them. The two minor protocol-text findings ({', '.join(minors)}) remain literally open at "
                f"1e6cdf04 and are non-blocking; they are closable by a one-line rev-4 cleanup at the cost of a new hash. "
                f"Evidence: {cs['passed']}/{cs['total']} machine checks pass (0 fail), with an independent least-squares "
                f"recomputation and a fresh bounded re-execution of the frozen instrument."
            ),
            "falsifier": report["falsifier"],
            "evidence_refs": [
                ref(report_path),
                proto_pin,
                cert_pin,
                frozen_pin,
                ref(f"{BASE}/checkpoint.json"),
            ],
            "artifact_refs": [ref(report_path), ref(verify_path), ref(f"{BASE}/checkpoint.json")],
        }
    )

    events.append(
        {
            "event_id": "w012-c3-status-0001-active",
            "event_type": "status",
            "created_at": now(),
            "actor": ACTOR,
            "node_id": NODE,
            "class_id": CLASS,
            "gate": GATE,
            "task_id": TASK_ID,
            "status": "active",
            "hours": 0.6,
            "summary": (
                f"Took one class-bound task from the live N0/G-NUM queue (no card in inbox for this slot): "
                f"C3 adjudication support. {cs['passed']}/{cs['total']} machine checks pass, 0 fail; fresh frozen-module "
                f"re-execution at dt=1e-4 reproduced the filed l2_error rows for {fresh_rungs}; the four major revise "
                f"findings are discharged by the re-based certification {cert_pin}, while minor text findings {minors} "
                f"remain open and non-blocking. Review verdict accept (4.0) filed as adjudication support only; "
                f"no gate verdict, no node completion, no lock release, no canonical file written."
            ),
            "evidence_refs": [
                ref(report_path),
                proto_pin,
                cert_pin,
                frozen_pin,
            ],
            "next_falsifier": report["falsifier"],
        }
    )

    events.append(
        {
            "event_id": "w012-c3-status-0002-done",
            "event_type": "status",
            "created_at": now(),
            "actor": ACTOR,
            "node_id": NODE,
            "class_id": CLASS,
            "gate": GATE,
            "task_id": TASK_ID,
            "status": "done",
            "hours": 0.1,
            "worker_level_only": True,
            "no_completion_claimed": True,
            "sets_gate_verdict": False,
            "sets_node_status": False,
            "summary": (
                "WORKER-LEVEL closeout of W012-N0-C3-DISCHARGE-01: bounded task delivered, artifacts hashed and emitted, "
                "checkpoint written. This does NOT complete N0: the C3 adjudication is reviewer input for the controller, "
                "G-NUM stays pending, N0 stays active, numerics_lock stays LOCKED and N1 stays queued. Slot exiting."
            ),
            "evidence_refs": [ref(report_path), ref(f"{BASE}/checkpoint.json")],
            "next_falsifier": "Controller adjudication of the C3 contest; or a protocol revision to a new hash, which voids this review's binding.",
        }
    )
    return events


def main() -> int:
    events = build()
    for ev in events:
        try:
            validate_event(ev)
        except Exception as exc:  # SchemaError
            print(f"SCHEMA FAIL {ev.get('event_id')}: {exc}")
            return 2
    existing = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                existing.add(json.loads(line).get("event_id"))
            except Exception:
                pass
    new = [e for e in events if e["event_id"] not in existing]
    if not new:
        print(json.dumps({"appended": 0, "already_present": len(events)}))
        return 0
    with open(OUTBOX, "a") as f:
        for e in new:
            f.write(json.dumps(e, sort_keys=True) + "\n")
    print(json.dumps({"appended": len(new), "event_ids": [e["event_id"] for e in new]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
