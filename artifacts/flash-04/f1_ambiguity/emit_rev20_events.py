#!/usr/bin/env python3
"""Emit worker-04 rev20 rebind events to comms/outbox and write a worker checkpoint.

Self-checks every event before appending: required keys per event type, artifact paths exist and
hash to the declared sha256, evidence refs carry a hash or line anchor, and event_ids are unique
across the outbox. No map mutation, no gate verdict, no status promotion.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUTBOX = ROOT / "comms/outbox/deepseek-flash-04.jsonl"
CHECKPOINT = ROOT / "runtime/state/w04_checkpoint_f1_rev20.json"
CHECKPOINT_LOG = ROOT / "runtime/state/w04_checkpoints.jsonl"
ACTOR = "deepseek-flash-04"
CST = timezone(timedelta(hours=8))


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ref(path: str, digest: str, chars: int = 16) -> str:
    return f"{path}#sha256:{digest[:chars]}"


def main() -> int:
    schema = "artifacts/formulation/schemas/af_wcc_vacuum.yaml"
    frozen = "artifacts/formulation/FROZEN.json"
    suite = "schemas/f1_falsifier_tests.jsonl"
    report = "artifacts/flash-04/f1_ambiguity/rebind_b65fcc0f_delta_report.json"
    script = "artifacts/flash-04/f1_ambiguity/rebind_b65fcc0f.py"
    snap_prior = "artifacts/flash-04/f1_ambiguity/schema_snapshots/af_wcc_vacuum.f962c117.yaml"
    snap_new = "artifacts/flash-04/f1_ambiguity/schema_snapshots/af_wcc_vacuum.b65fcc0f.yaml"
    version_copy = "artifacts/flash-04/f1_ambiguity/versions/f1_falsifier_tests.b65fcc0f.prefreeze.jsonl"
    adjudication = "artifacts/formulation/reviews/ADJUDICATION_flash04_ambiguity.md"
    rule_spec = "artifacts/formulation/rule_spec.json"
    aliases = "artifacts/formulation/VOCAB_ALIASES.json"
    taxonomy = "artifacts/formulation/formulation_taxonomy.yaml"

    hashes = {p: sha256_file(ROOT / p) for p in
              [schema, "schemas/af_wcc_vacuum.yaml", frozen, suite, report, script, snap_prior, snap_new,
               version_copy, adjudication, rule_spec, aliases, taxonomy]}
    ev = ref(schema, hashes[schema])
    fz = ref(frozen, hashes[frozen])
    su = ref(suite, hashes[suite])
    rp = ref(report, hashes[report])
    sc = ref(script, hashes[script])
    sp = ref(snap_prior, hashes[snap_prior])
    sn = ref(snap_new, hashes[snap_new])
    vc = ref(version_copy, hashes[version_copy])
    aj = ref(adjudication, hashes[adjudication])
    rs = ref(rule_spec, hashes[rule_spec])
    al = ref(aliases, hashes[aliases])
    tx = ref(taxonomy, hashes[taxonomy])
    ts = datetime.now(CST).strftime("%Y%m%dT%H%M%S")

    events = [
        {
            "actor": ACTOR,
            "artifact_type": "falsifier_test_suite",
            "bytes": (ROOT / suite).stat().st_size,
            "class_id": "AF-WCC-VAC-GEN",
            "created_at": now(),
            "event_id": f"flash-04-art-F1-rev20-suite-{ts}",
            "event_type": "artifact",
            "evidence_refs": [ev, fz, su, aj, rs, al, tx, sp, "comms/inbox/deepseek-flash-04.jsonl:1-3"],
            "falsifier": "A carried probe failing to resolve in b65fcc0f, or a class_identity_variants/anti_scope binding that leaks variant SET or scalar-matter content into AF-WCC-VAC-GEN.",
            "gate": "G-FORM",
            "group_id": "formulation",
            "next_falsifier": "Re-run after any freeze-hash change; a row that cannot be rebound is rejected.",
            "node_id": "F1",
            "path": suite,
            "sha256": hashes[suite],
            "summary": "24 class-bound ambiguity probes for AF-WCC-VAC-GEN rebound to frozen rev20 sha256 b65fcc0f (FROZEN.json revision 20, schema internal rev9); 22 carried unchanged, 1 field_added (class_identity_variants), 1 field_content_changed (anti_scope.not_this_class), 2 new probes F1-AMB-23/24; 0 probe failures, 0 probe flips vs rev19.",
            "supersedes": ["flash-04-art-F1-rebind-suite-20260912T000807", "flash-04-art-F1-drift-note-20260912T000910"],
            "validation_status": "unverified",
        },
        {
            "actor": ACTOR,
            "artifact_type": "delta_report",
            "bytes": (ROOT / report).stat().st_size,
            "class_id": "AF-WCC-VAC-GEN",
            "created_at": now(),
            "event_id": f"flash-04-art-F1-rev20-report-{ts}",
            "event_type": "artifact",
            "evidence_refs": [ev, fz, rp, su, sp, sn, vc],
            "falsifier": "A report count or suite hash that does not reproduce under python3 artifacts/flash-04/f1_ambiguity/rebind_b65fcc0f.py.",
            "gate": "G-FORM",
            "group_id": "formulation",
            "next_falsifier": "A G-FORM verdict citing a hash other than b65fcc0f while the suite still binds b65fcc0f.",
            "node_id": "F1",
            "path": report,
            "sha256": hashes[report],
            "summary": "Delta report rev19 f962c117 (internal rev8) -> rev20 b65fcc0f (internal rev9): exact deciding-field diffs, added top-level block class_identity_variants, anti_scope change, 4 retained obligations, canonical-path publication now RESOLVED (published schemas/af_wcc_vacuum.yaml equals the rev20 pin).",
            "supersedes": ["flash-04-art-F1-rebind-report-20260912T000807", "flash-04-art-F1-drift-note-20260912T000910"],
            "validation_status": "unverified",
        },
        {
            "actor": ACTOR,
            "artifact_refs": [su, rp],
            "assumptions": [
                "FROZEN.json revision 20 pins artifacts/formulation/schemas/af_wcc_vacuum.yaml at b65fcc0f0118980f",
                "the f962c117 snapshot is a faithful copy of the rev19 artifact (two independent 30904-byte copies agree)",
                "probe predicates are necessary, not jointly sufficient, readings of the deciding fields",
                "a variant registry entry with is_this_class=false is the schema's decision procedure for the set-based reading",
            ],
            "class_id": "AF-WCC-VAC-GEN",
            "conclusion_type": "formal_model",
            "created_at": now(),
            "event_id": f"flash-04-claim-F1-rev20-{ts}",
            "event_type": "claim",
            "evidence_refs": [ev, fz, su, rp, sc, sp, sn, vc, aj, rs, al, tx],
            "falsifier": "A carried probe failing to resolve in b65fcc0f, a deciding-field verdict flipping without a FROZEN revision entry, or a set-based/scalar-matter result accepted against AF-WCC-VAC-GEN.",
            "node_id": "F1",
            "statement": "The F1 (AF-WCC-VAC-GEN) ambiguity suite rebinds to the frozen schema sha256 b65fcc0f (FROZEN rev20, internal rev9) with 24/24 probes resolving: 22 carried tests have identical deciding-field content to rev19 f962c117, F1-AMB-23 decides the new class_identity_variants block (variant SET, is_this_class=false, registered_variant_not_written), and F1-AMB-24 decides the new AF-WCC-SCALAR-SPH anti-scope entry. No deciding-field verdict flipped between rev19 and rev20. The four prior open obligations (AMB-01 non-vacuity witness membership, AMB-02/03 meagerness of excluded families, AMB-15 equivalence to future asymptotic predictability) remain open.",
        },
        {
            "actor": ACTOR,
            "class_id": "AF-WCC-VAC-GEN",
            "created_at": now(),
            "event_id": f"flash-04-status-F1-rev20-{ts}",
            "event_type": "status",
            "evidence_refs": [su, rp, ev, fz, sc, sp, sn, vc, "research_map/ASTRA_HANDOFF.md:3-38"],
            "group_id": "formulation",
            "hours": 0.4,
            "next_falsifier": "A frozen F1 revision after b65fcc0f without a delta re-run; an open obligation (AMB-01/02/03/15) closed without L1/L0 evidence; or a G-FORM verdict citing a revision label instead of a sha256.",
            "node_id": "F1",
            "status": "active",
            "summary": "Assignment asg-2026-09-11-F1-deepseek-flash-04-13 delta re-run delivered against the current freeze: FROZEN.json revision 20 pins F1 at b65fcc0f (internal rev9), superseding the rev19 f962c117 binding of the 00:08 run. Suite rewritten at schemas/f1_falsifier_tests.jsonl (24 tests, 0 probe failures, 0 flips); report at artifacts/flash-04/f1_ambiguity/rebind_b65fcc0f_delta_report.json. Two rev9 delta surfaces covered by new probes: the set-based visibility reading is a registered variant with is_this_class=false (not the class), and AF-WCC-SCALAR-SPH is anti-scope. The 00:09 drift note is discharged: the authoring tree, the canonical published copy schemas/af_wcc_vacuum.yaml, and the FROZEN rev20 pin are byte-identical at b65fcc0f. No completion or gate verdict claimed; validation_status unverified. Remaining open: AMB-01/02/03/15.",
            "supersedes": ["flash-04-status-F1-rebind-20260912T000807", "flash-04-status-F1-drift-note-20260912T000910"],
        },
    ]

    # --- self-validation ---
    prior_ids = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            if line.strip():
                prior_ids.add(json.loads(line).get("event_id"))
    seen = set()
    for e in events:
        eid = e.get("event_id")
        assert eid and eid not in prior_ids and eid not in seen, f"duplicate event_id {eid}"
        seen.add(eid)
        for k in ("event_id", "event_type", "created_at", "actor"):
            assert e.get(k), f"{eid}: missing {k}"
        assert e.get("evidence_refs"), f"{eid}: missing evidence_refs"
        assert all(("#" in r) or (":" in r) for r in e["evidence_refs"]), f"{eid}: evidence ref without hash/line anchor"
        t = e["event_type"]
        if t == "artifact":
            for k in ("node_id", "artifact_type", "path", "sha256", "validation_status"):
                assert e.get(k), f"{eid}: missing {k}"
            p = ROOT / e["path"]
            assert p.is_file(), f"{eid}: artifact missing {p}"
            assert sha256_file(p) == e["sha256"], f"{eid}: sha256 mismatch for {p}"
            assert e["validation_status"] in {"unverified", "passed", "failed", "retracted"}
        elif t == "claim":
            for k in ("class_id", "statement", "conclusion_type", "assumptions", "falsifier"):
                assert e.get(k), f"{eid}: missing {k}"
            assert isinstance(e["assumptions"], list) and e["assumptions"]
        elif t == "status":
            for k in ("node_id", "status", "hours", "summary", "next_falsifier"):
                assert e.get(k), f"{eid}: missing {k}"
            assert e["status"] in {"queued", "active", "blocked", "done", "rejected", "killed"}
        else:  # pragma: no cover
            raise AssertionError(f"{eid}: unsupported event type {t}")

    with OUTBOX.open("a") as f:
        for e in events:
            f.write(json.dumps(e, ensure_ascii=False, sort_keys=True) + "\n")

    checkpoint = {
        "checkpoint_id": "w04-cp14-f1-rev20",
        "created_at": now(),
        "actor": ACTOR,
        "assignment": "asg-2026-09-11-F1-deepseek-flash-04-13",
        "node_id": "F1",
        "class_id": "AF-WCC-VAC-GEN",
        "gate": "G-FORM",
        "status": "active",
        "hours": 0.4,
        "binding": {"path": schema, "sha256": hashes[schema], "frozen_revision": 20, "schema_internal_revision": 9},
        "prior_binding": {"sha256": hashes[snap_prior], "frozen_revision": 19, "schema_internal_revision": 8},
        "canonical_path": {"path": "schemas/af_wcc_vacuum.yaml", "sha256": hashes["schemas/af_wcc_vacuum.yaml"], "matches_frozen_pin": hashes["schemas/af_wcc_vacuum.yaml"] == hashes[schema]},
        "artifacts": {suite: hashes[suite], report: hashes[report], script: hashes[script],
                      snap_prior: hashes[snap_prior], snap_new: hashes[snap_new], version_copy: hashes[version_copy]},
        "results": {"tests_total": 24, "probe_failures": [], "probe_flips": [],
                    "delta_counts": {"unchanged": 22, "field_added": 1, "field_content_changed": 1},
                    "added_top_level_blocks": ["class_identity_variants"],
                    "open_obligations": ["F1-AMB-01", "F1-AMB-02", "F1-AMB-03", "F1-AMB-15"]},
        "events_emitted": [e["event_id"] for e in events],
        "next_falsifier": "A frozen F1 revision after b65fcc0f without a delta re-run; an open obligation closed without L1/L0 evidence; or a G-FORM verdict citing a revision label instead of a sha256.",
        "reproduce": "python3 artifacts/flash-04/f1_ambiguity/rebind_b65fcc0f.py",
    }
    CHECKPOINT.write_text(json.dumps(checkpoint, indent=1, ensure_ascii=False) + "\n")
    with CHECKPOINT_LOG.open("a") as f:
        f.write(json.dumps(checkpoint, ensure_ascii=False, sort_keys=True) + "\n")
    print(json.dumps({"events_written": len(events), "outbox": str(OUTBOX.relative_to(ROOT)),
                      "checkpoint": str(CHECKPOINT.relative_to(ROOT)),
                      "checkpoint_log": str(CHECKPOINT_LOG.relative_to(ROOT))}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
