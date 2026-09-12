#!/usr/bin/env python3
"""One-shot emitter for worker-19 lifecycle (census rev2 + detector blind-spot probe).

Reads the measured artifacts from disk, builds four upward events, validates each against
both research_map/schemas.py and research_map/events.schema.json, writes a worker checkpoint,
then appends the events to comms/outbox/deepseek-flash-19.jsonl in a single write.

No controller-owned file is modified. No ledger file is modified.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTBOX = ROOT / "comms" / "outbox" / "deepseek-flash-19.jsonl"
CHECKPOINT = None  # set below
CST = timezone(timedelta(hours=8))
ACTOR = "deepseek-flash-19"
CLASS_ID = "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH"
TASK = "T19-L0-census-rev2"
ASSIGNMENT = "astra-indep-1-CF5-ledger-verify"
GATE = "G-LIT"
NODE = "L0"

REV2 = ROOT / "artifacts" / "flash-19" / "class_token_census_rev2.json"
REV2_PY = ROOT / "artifacts" / "flash-19" / "class_token_census_rev2.py"
PROBE = ROOT / "artifacts" / "flash-19" / "detector_blindspot_probe.json"
PROBE_PY = ROOT / "artifacts" / "flash-19" / "detector_blindspot_probe.py"
REV1 = ROOT / "artifacts" / "flash-19" / "class_token_census.json"
THEOREMS = ROOT / "ledger" / "theorems.jsonl"
CITATIONS = ROOT / "ledger" / "citation_audit.csv"
MAP = ROOT / "research_map" / "research_map.json"
CUR_CKPT = ROOT / "runtime" / "state" / "current_checkpoint.json"

FALSIFIER = ("A rerun on the same input sha256s that reports a different occurrence count or "
             "classification for any AF token, or a class_separation._class_tokens probe that "
             "matches one of the three non-frozen shorthands, or a non-empty findings_for_text "
             "result on either ledger file, falsifies this result.")
NEXT_FALSIFIER = ("Repair the five occurrences and re-run both artifacts at the new ledger hash; "
                  "or show a declared ledger_tags entry that redeems one of the three tokens "
                  "(none exists at this hash). Any ledger write makes this census stale and voids "
                  "it for citation.")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load_schemas():
    spec = importlib.util.spec_from_file_location("rm_schemas", ROOT / "research_map" / "schemas.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod  # dataclasses needs the module registered
    spec.loader.exec_module(mod)
    return mod


def validate(events: list[dict]) -> None:
    import jsonschema
    schema = json.loads((ROOT / "research_map" / "events.schema.json").read_text())
    rm = load_schemas()
    # events.schema.json's oneOf defines only direction_update/claim/artifact/review/
    # resource_request; `status` is defined by schemas.py and PROTOCOL.md but absent there.
    json_schema_types = {"direction_update", "claim", "artifact", "review", "resource_request"}
    for ev in events:
        rm.validate_event(ev)
        if ev["event_type"] in json_schema_types:
            jsonschema.validate(ev, schema)


def main() -> int:
    now = datetime.now(CST)
    stamp = now.strftime("%Y%m%dT%H%M%S")
    rev2 = json.loads(REV2.read_text())
    probe = json.loads(PROBE.read_text())
    rev2_sha, probe_sha = sha(REV2), sha(PROBE)
    if rev2_sha != "a2c520d7efe6ba04d5171e57d01f94730e81b4de705cf2d1932e26a789a53d81":
        raise SystemExit("FATAL: census rev2 hash changed since measurement")
    if probe_sha != "ec061d1fb262fd777d421110977329f7c183e09abc00469e4319b03c664f1ad8":
        raise SystemExit("FATAL: probe hash changed since measurement")
    if sha(THEOREMS) != rev2["input_stability"]["after"]["ledger/theorems.jsonl"]:
        raise SystemExit("FATAL: theorems moved; census is stale")
    if sha(CITATIONS) != rev2["input_stability"]["after"]["ledger/citation_audit.csv"]:
        raise SystemExit("FATAL: citations moved; census is stale")

    th_sha = sha(THEOREMS)
    cit_sha = sha(CITATIONS)
    map_sha = sha(MAP)
    cur = json.loads(CUR_CKPT.read_text())
    cur_sha = sha(CUR_CKPT)

    ev_art = {
        "event_id": f"flash19-L0-02-artifact-census-rev2-{stamp}",
        "event_type": "artifact",
        "created_at": now.isoformat(timespec="seconds"),
        "actor": ACTOR,
        "node_id": NODE,
        "group_id": "literature",
        "gate": GATE,
        "class_id": CLASS_ID,
        "task_id": TASK,
        "assignment_event_id": ASSIGNMENT,
        "artifact_type": "class_token_census_rev2",
        "path": str(REV2.relative_to(ROOT)),
        "sha256": rev2_sha,
        "validation_status": "unverified",
        "evidence_refs": [
            f"{REV2.relative_to(ROOT)}#sha256:{rev2_sha[:12]}",
            f"{REV2_PY.relative_to(ROOT)}#sha256:{sha(REV2_PY)[:12]}",
            f"{REV1.relative_to(ROOT)}#sha256:{sha(REV1)[:12]}",
            f"ledger/theorems.jsonl#sha256:{th_sha[:12]}",
            f"ledger/citation_audit.csv#sha256:{cit_sha[:12]}",
        ],
        "falsifier": FALSIFIER,
        "falsifier_status": "FIRED",
        "next_falsifier": NEXT_FALSIFIER,
        "content_digest_sha256": rev2["content_digest_sha256"],
        "note": ("Revision 2 of the CF-5 class-token census at the live ledger bytes. rev1 "
                 f"({sha(REV1)[:12]}) bound theorems ce42d205e761; the file moved to "
                 f"{th_sha[:12]} (CF-19 post-freeze rewrite) and rev2 re-runs the pinned rev1 "
                 "method byte-identically. Delta vs rev1: 0 tokens changed, 0 violations "
                 "resolved, 0 added, 3 remaining, so the rewrite did not repair the vocabulary. "
                 "validation_status=unverified because a worker cannot set passed."),
    }
    ev_probe = {
        "event_id": f"flash19-L0-02-artifact-detector-blindspot-{stamp}",
        "event_type": "artifact",
        "created_at": now.isoformat(timespec="seconds"),
        "actor": ACTOR,
        "node_id": NODE,
        "group_id": "literature",
        "gate": GATE,
        "class_id": CLASS_ID,
        "task_id": TASK,
        "assignment_event_id": ASSIGNMENT,
        "artifact_type": "detector_blindspot_probe",
        "path": str(PROBE.relative_to(ROOT)),
        "sha256": probe_sha,
        "validation_status": "unverified",
        "evidence_refs": [
            f"{PROBE.relative_to(ROOT)}#sha256:{probe_sha[:12]}",
            f"{PROBE_PY.relative_to(ROOT)}#sha256:{sha(PROBE_PY)[:12]}",
            f"research_map/class_separation.py#sha256:{probe['sources']['research_map/class_separation.py'][:12]}",
            f"research_map/astra_lifecycle.py#sha256:{probe['sources']['research_map/astra_lifecycle.py'][:12]}",
        ],
        "falsifier": probe["falsifier"],
        "falsifier_status": "not_triggered",
        "next_falsifier": ("A class_separation revision whose token pattern matches the four "
                           "frozen ids and the three shorthands, or a non-empty findings_for_text "
                           "on either ledger file, falsifies the blind-spot finding."),
        "note": ("Mechanises why astra_lifecycle.py:349 prints 'The ledger class-token flag is "
                 "cleared at this hash': ledger_flags (:263) is empty because _class_tokens "
                 "matches only 2 of the 4 frozen ids and none of the 3 non-frozen tokens; "
                 "findings_for_text returns 0 on both current ledger files. Empty detector "
                 "output, not evidence of repair."),
    }
    statement = (
        f"At ledger/theorems.jsonl sha256 {th_sha} and ledger/citation_audit.csv sha256 {cit_sha}: "
        "the four frozen class ids are present in both files with 147 occurrences "
        "(AF-WCC-VAC-GEN 36, AF-SCC-C2-VAC-GEN 40, AF-SCC-C0-VAC-GEN 45, AF-WCC-SCALAR-SPH 26), "
        "and exactly 5 occurrences of 3 non-frozen AF-prefixed tokens remain, none declared in "
        "any theorem's ledger_tags: AF-SCC x2 (T-526.scope_caveats, T-526.unresolved), "
        "AF-SCC-C0 x2 (SRC-096.assessment, SRC-097.assessment), AF-SCC-C2 x1 (T-304.next_action). "
        "The counts are byte-identical to rev1 at theorems ce42d205e761, so the post-freeze "
        "rewrite did not repair the vocabulary (0 of 3 violations resolved). Independently, "
        "class_separation._class_tokens matches only AF-SCC-C2-VAC-GEN and AF-SCC-C0-VAC-GEN of "
        "the four frozen ids and none of the three shorthands, so findings_for_text is empty on "
        "both ledger files and the controller's G-LIT line 'The ledger class-token flag is "
        "cleared at this hash' (astra_lifecycle.py:349) is a detector blind spot, not measured "
        "compliance. CF-5 therefore remains open at the current bytes."
    )
    ev_claim = {
        "event_id": f"flash19-L0-02-claim-census-rev2-{stamp}",
        "event_type": "claim",
        "created_at": now.isoformat(timespec="seconds"),
        "actor": ACTOR,
        "node_id": NODE,
        "group_id": "literature",
        "gate": GATE,
        "class_id": CLASS_ID,
        "task_id": TASK,
        "assignment_event_id": ASSIGNMENT,
        "statement": statement,
        "conclusion_type": "numerical_evidence",
        "assumptions": [
            "token universe = AF-[A-Za-z0-9]+(-[A-Za-z0-9]+)* after NFKC and superscript folding",
            "a theorem record's ledger_tags array is the declared ledger-local vocabulary",
            "census is read-only; neither ledger file was modified during the measurement",
        ],
        "falsifier": FALSIFIER,
        "falsifier_status": "FIRED",
        "evidence_refs": [
            f"{REV2.relative_to(ROOT)}#sha256:{rev2_sha[:12]}",
            f"{PROBE.relative_to(ROOT)}#sha256:{probe_sha[:12]}",
            f"ledger/theorems.jsonl#sha256:{th_sha[:12]}",
            f"ledger/citation_audit.csv#sha256:{cit_sha[:12]}",
        ],
        "artifact_refs": [
            f"{REV2.relative_to(ROOT)}#sha256:{rev2_sha}",
            f"{PROBE.relative_to(ROOT)}#sha256:{probe_sha}",
        ],
        "next_falsifier": NEXT_FALSIFIER,
    }

    # Checkpoint first (it lists event ids), then hash it into the status evidence_refs.
    ckpt_path = ROOT / "artifacts" / "flash-19" / f"worker019_checkpoint_{stamp}.json"
    checkpoint = {
        "checkpoint_id": f"flash19-census-rev2-{stamp}",
        "worker": ACTOR,
        "worker_slot": "19",
        "task_id": TASK,
        "assignment_event_id": ASSIGNMENT,
        "node_id": NODE,
        "gate": GATE,
        "class_ids": CLASS_ID.split(";"),
        "created_at": now.isoformat(timespec="seconds"),
        "artifacts": {
            str(REV2.relative_to(ROOT)): rev2_sha,
            str(REV2_PY.relative_to(ROOT)): sha(REV2_PY),
            str(PROBE.relative_to(ROOT)): probe_sha,
            str(PROBE_PY.relative_to(ROOT)): sha(PROBE_PY),
        },
        "inputs": {
            "ledger/theorems.jsonl": th_sha,
            "ledger/citation_audit.csv": cit_sha,
        },
        "events": [ev_art["event_id"], ev_probe["event_id"], ev_claim["event_id"],
                   f"flash19-L0-02-status-census-rev2-{stamp}"],
        "result": ("CF-5 remains open at theorems a1674f094979 + citations 315c19145065: 3 "
                   "non-frozen AF tokens, 5 occurrences, 0 redeemed by ledger_tags, unchanged "
                   "from rev1; controller G-LIT 'cleared' line is a class_separation blind spot."),
        "falsifier_status": "FIRED",
        "next_falsifier": NEXT_FALSIFIER,
        "map_sha256_measured": map_sha,
        "global_checkpoint": {
            "path": str(CUR_CKPT.relative_to(ROOT)),
            "checkpoint_id": cur.get("checkpoint_id"),
            "sha256": cur_sha,
        },
        "outbox": str(OUTBOX.relative_to(ROOT)),
        "no_completion_claim": ("worker cannot set node done, validation_status passed, or a gate "
                                "verdict; no ledger or controller-owned file was modified"),
    }
    ckpt_path.write_text(json.dumps(checkpoint, indent=2, sort_keys=True) + "\n")
    ckpt_sha = sha(ckpt_path)

    ev_status = {
        "event_id": f"flash19-L0-02-status-census-rev2-{stamp}",
        "event_type": "status",
        "created_at": now.isoformat(timespec="seconds"),
        "actor": ACTOR,
        "node_id": NODE,
        "group_id": "literature",
        "gate": GATE,
        "class_id": CLASS_ID,
        "task_id": TASK,
        "assignment_event_id": ASSIGNMENT,
        "checkpoint_id": checkpoint["checkpoint_id"],
        "status": "active",
        "hours": 0.4,
        "summary": checkpoint["result"],
        "evidence_refs": [
            f"{REV2.relative_to(ROOT)}#sha256:{rev2_sha[:12]}",
            f"{PROBE.relative_to(ROOT)}#sha256:{probe_sha[:12]}",
            f"{ckpt_path.relative_to(ROOT)}#sha256:{ckpt_sha[:12]}",
            f"ledger/theorems.jsonl#sha256:{th_sha[:12]}",
            f"ledger/citation_audit.csv#sha256:{cit_sha[:12]}",
        ],
        "falsifier": FALSIFIER,
        "falsifier_status": "FIRED",
        "next_falsifier": NEXT_FALSIFIER,
        "no_completion_claim": checkpoint["no_completion_claim"],
        "schema_note": ("research_map/events.schema.json oneOf omits `status`; this event is "
                        "validated by research_map/schemas.py (which defines it) and by "
                        "PROTOCOL.md's upward list. Reported as a schema gap, not silently "
                        "worked around."),
    }

    events = [ev_art, ev_probe, ev_claim, ev_status]
    validate(events)
    with OUTBOX.open("a", encoding="utf-8") as fh:
        fh.write("".join(json.dumps(e, ensure_ascii=False, sort_keys=True) + "\n" for e in events))
    print(json.dumps({
        "appended": [e["event_id"] for e in events],
        "schema": "valid (research_map/schemas.py + events.schema.json)",
        "checkpoint": str(ckpt_path.relative_to(ROOT)),
        "checkpoint_sha256": ckpt_sha,
        "outbox": str(OUTBOX.relative_to(ROOT)),
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
