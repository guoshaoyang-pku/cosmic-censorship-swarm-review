#!/usr/bin/env python3
"""Emit W089-F2B-REV12-REVIEW-04 evidence: outbox events, KEY_MANIFEST, checkpoint 4.

Appends valid JSON events (one object per line) to comms/outbox/worker-089.jsonl.
Every event carries event_id, event_type, created_at, actor plus node/class ids,
evidence_refs (path#sha256-prefix), and falsifier/next_falsifier.
"""
import datetime as dt
import hashlib
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
TARGET = "schemas/af_scc_c0_vacuum.yaml"
TARGET_AUTHORING = "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"
TASK = "W089-F2B-REV12-REVIEW-04"
CLASS = "AF-SCC-C0-VAC-GEN"
NODE = "F2b"
GATE = "G-FORM"
CHECKPOINT_N = 4


def sha256_file(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def ref(path, h):
    return f"{path}#{h[:12]}"


now = dt.datetime.now().astimezone()
stamp = now.strftime("%Y%m%dT%H%M%S")
created = now.isoformat(timespec="seconds")

report = json.load(open(os.path.join(HERE, "f2b_review_report.json")))
target_sha = report["target"]["sha256"]
authoring_sha = report["target"]["authoring_sha256"]
frozen_sha = report["frozen_manifest"]["sha256"]
canon_tax_sha = sha256_file(os.path.join(REPO, "research_map/formulation_taxonomy.yaml"))
supp_tax_sha = sha256_file(os.path.join(REPO, "artifacts/formulation/formulation_taxonomy.yaml"))
falsifier = report["falsifier"]
next_falsifier = report["next_falsifier"]
scope = report["scope"]
independence = report["independence"]

paths = {
    "checker": "artifacts/worker-089/f2b_rev12_review/check_f2b_rev12.py",
    "report": "artifacts/worker-089/f2b_rev12_review/f2b_review_report.json",
    "readme": "artifacts/worker-089/f2b_rev12_review/README.md",
    "review": "artifacts/worker-089/f2b_rev12_review/REVIEW.json",
    "snapshot": f"artifacts/worker-089/f2b_rev12_review/pinned/af_scc_c0_vacuum.{target_sha[:12]}.yaml",
    "authoring_snapshot": f"artifacts/worker-089/f2b_rev12_review/pinned/af_scc_c0_vacuum.authoring.{authoring_sha[:12]}.yaml",
    "frozen_snapshot": "artifacts/worker-089/f2b_rev12_review/pinned/FROZEN.rev28.json",
}
# byte-exact authoring-twin snapshot (equal to the canonical snapshot at this revision)
auth_snap = os.path.join(REPO, paths["authoring_snapshot"])
if not os.path.exists(auth_snap):
    with open(os.path.join(REPO, TARGET_AUTHORING), "rb") as src, open(auth_snap, "wb") as dst:
        dst.write(src.read())
hashes = {key: sha256_file(os.path.join(REPO, p)) for key, p in paths.items()}

base = dict(
    actor="worker-089",
    class_id=CLASS,
    node_id=NODE,
    gate=GATE,
    task_id=TASK,
    created_at=created,
    falsifier=falsifier,
    next_falsifier=next_falsifier,
)

events = [
    dict(
        base,
        event_id=f"w089-{stamp}-claim",
        event_type="status",
        status="active",
        hours=0.4,
        summary=(
            "No worker-089 inbox card exists. Took one bounded class-bound task from the audit lead's "
            "blocking item B-GFORM-1 (F2b had 0 independent verdicts at the FROZEN rev28 hash): "
            "independent review of F2b (AF-SCC-C0-VAC-GEN) revision 12 at 55d0a1ea9bda, FROZEN rev28 "
            "2f358f6722d9. 15 machine checks + 14 planted-defect controls + no-false-positive baseline + "
            "90 s stability window. Closes HF-034-1/HF-034-2 at this hash as evidence; worker evidence "
            "only, no gate verdict, no node completion."
        ),
        evidence_refs=[
            ref("reviews/G-FORM-final-verify.json", sha256_file(os.path.join(REPO, "reviews/G-FORM-final-verify.json"))),
            ref(TARGET, target_sha),
            ref("artifacts/formulation/FROZEN.json", frozen_sha),
        ],
    ),
    dict(
        base,
        event_id=f"w089-{stamp}-art-checker_code",
        event_type="artifact",
        artifact_type="checker_code",
        path=paths["checker"],
        sha256=hashes["checker"],
        validation_status="unverified",
        note=(
            "Deterministic read-only stdlib+PyYAML checker: 15 scored checks (C01-C15), 14 "
            "planted-defect controls (M1-M14), no-false-positive baseline, hash-stability window; "
            "writes only inside its artifact directory."
        ),
        evidence_refs=[ref(paths["checker"], hashes["checker"]), ref(TARGET, target_sha)],
    ),
    dict(
        base,
        event_id=f"w089-{stamp}-art-audit_report",
        event_type="artifact",
        artifact_type="audit_report",
        path=paths["report"],
        sha256=hashes["report"],
        validation_status="unverified",
        note=(
            "Result at pin 55d0a1ea9bda / FROZEN rev28: verdict=accept, checks=15/15 pass, controls=14/14 "
            "caught, drift_detected=false; observations OBS-089-2 (stale inline consistency-evidence "
            "pointer, = HF-034-F2A-3/HF-086-R1 family) and OBS-089-3 (data_class differentiation input to "
            "O-GFORM-1), both excluded from scope."
        ),
        evidence_refs=[
            ref(paths["report"], hashes["report"]),
            ref(TARGET, target_sha),
            ref("artifacts/formulation/FROZEN.json", frozen_sha),
        ],
    ),
    dict(
        base,
        event_id=f"w089-{stamp}-art-readme",
        event_type="artifact",
        artifact_type="summary",
        path=paths["readme"],
        sha256=hashes["readme"],
        validation_status="unverified",
        note="One-page summary: target pins, check table, controls, observations, scope limits, falsifier, re-run command.",
        evidence_refs=[ref(paths["readme"], hashes["readme"])],
    ),
    dict(
        base,
        event_id=f"w089-{stamp}-art-review_record",
        event_type="artifact",
        artifact_type="review_record",
        path=paths["review"],
        sha256=hashes["review"],
        validation_status="unverified",
        note="Structured review record (verdict accept 4.0) with scope, independence, findings POS-089-6..11, OBS-089-2/3 and CHECKER-NOTE-089-1.",
        evidence_refs=[ref(paths["review"], hashes["review"])],
    ),
    dict(
        base,
        event_id=f"w089-{stamp}-art-pinned-snapshot",
        event_type="artifact",
        artifact_type="pinned_snapshot",
        path=paths["snapshot"],
        sha256=hashes["snapshot"],
        validation_status="unverified",
        note="Byte-exact copy of the reviewed canonical revision, so the review survives later drift.",
        evidence_refs=[ref(paths["snapshot"], hashes["snapshot"])],
    ),
    dict(
        base,
        event_id=f"w089-{stamp}-art-frozen-snapshot",
        event_type="artifact",
        artifact_type="pinned_snapshot",
        path=paths["frozen_snapshot"],
        sha256=hashes["frozen_snapshot"],
        validation_status="unverified",
        note="Byte-exact copy of FROZEN rev28 (2f358f6722d9) as measured at review time.",
        evidence_refs=[ref(paths["frozen_snapshot"], hashes["frozen_snapshot"])],
    ),
]

review_event = dict(
    base,
    event_id=f"w089-{stamp}-review",
    event_type="review",
    reviewer="worker-089",
    verdict="accept",
    score=4.0,
    hard_failures=[],
    target_id=f"{TARGET}#{target_sha[:12]}",
    artifact=TARGET,
    artifact_sha256=target_sha,
    artifact_revision_read=12,
    counts_as_gate_accept=False,
    review_kind="independent_machine_checked_class_review",
    scope=scope,
    independence=independence,
    findings=[
        "POS-089-6: HF-034-1 closed at this hash; D0 tagged disjoint union with forall r over D0, byte-identical across F1/F2a/F2b (C09).",
        "POS-089-7: HF-034-2 closed at this hash; canonical pointer resolves at the declared F0 artifact, supplement pointer separate and resolvable (C04, C05).",
        "POS-089-8: C0 extension predicate frozen: C0/none/future, clauses (a)-(f), continuity + nondegeneracy + c0_uniqueness_caveat (C10).",
        "POS-089-9: class separation clean; conclusion typed scc_c0_future_inextendibility, no C0/C2 merge, no WCC/I+ content in the conclusion (C08, C11, C12).",
        "POS-089-10: one-way ledger C0=>H2loc=>C2 complete; C2=>this class and WCC=>this class forbidden; (s,delta) shared with F1/F2a (C15).",
        "POS-089-11: FROZEN rev28 pins both paths, mirror equal, no duplicate keys, wall-clock timestamps, no drift over 90 s (C01, C02, C03, C07, stability).",
        "OBS-089-2 (non-blocking, excluded from scope): inline f0_binding.consistency_evidence_sha256 675a99d0 no longer resolves (live 9e335e9b, FROZEN rev28 pin); same family defect as HF-034-F2A-3/HF-086-R1.",
        "OBS-089-3 (non-blocking, excluded from scope): F2a/F2b data_class blocks differ only in adm_mass annotation text; C0/C2 separation rests on regularity_token + extension_predicate. Measured input to O-GFORM-1, not adjudicated here.",
        "Controls M1-M14 each planted one defect class and all 14 were caught; the unmutated baseline passed all 15 checks.",
    ],
    evidence_refs=[
        ref(paths["report"], hashes["report"]),
        ref(paths["review"], hashes["review"]),
        ref(TARGET, target_sha),
        ref(TARGET_AUTHORING, authoring_sha),
        ref("artifacts/formulation/FROZEN.json", frozen_sha),
        ref("research_map/formulation_taxonomy.yaml", canon_tax_sha),
        ref("artifacts/formulation/formulation_taxonomy.yaml", supp_tax_sha),
    ],
)
events.append(review_event)

# key manifest before the done event so its hash can be cited
manifest_paths = dict(paths)
manifest_paths["events"] = "artifacts/worker-089/f2b_rev12_review/events.jsonl"
manifest = {
    "schema_version": "1.0",
    "task_id": TASK,
    "worker": "worker-089",
    "class_id": CLASS,
    "node_id": NODE,
    "gate": GATE,
    "created_at": created,
    "target": {"path": TARGET, "sha256": target_sha, "revision": 12},
    "authoring_twin": {"path": TARGET_AUTHORING, "sha256": authoring_sha},
    "frozen_manifest": {"path": "artifacts/formulation/FROZEN.json", "sha256": frozen_sha, "revision": 28},
    "files": {},
}
for key, p in manifest_paths.items():
    full = os.path.join(REPO, p)
    if os.path.exists(full):
        manifest["files"][p] = sha256_file(full)

events.append(
    dict(
        base,
        event_id=f"w089-{stamp}-done",
        event_type="status",
        status="done",
        hours=0.4,
        summary=(
            "Worker lifecycle complete (completion claim only; not a node done and not a gate verdict). "
            "One class-bound task delivered: F2b rev12 accept at 55d0a1ea9bda on the FROZEN rev28 pin, "
            "checks 15/15, controls 14/14, no drift; HF-034-1/HF-034-2 closed as evidence at this hash. "
            "OBS-089-2/OBS-089-3 recorded outside scope. This is the first worker-089 verdict bound to the "
            "F2b rev28 hash."
        ),
        evidence_refs=[
            ref(paths["report"], hashes["report"]),
            ref(paths["review"], hashes["review"]),
            "runtime/state/w089_checkpoint_4.json",
        ],
    )
)

outbox = os.path.join(REPO, "comms/outbox/worker-089.jsonl")
with open(outbox, "a", encoding="utf-8") as fh:
    for e in events:
        fh.write(json.dumps(e, sort_keys=True) + "\n")

with open(os.path.join(HERE, "events.jsonl"), "w", encoding="utf-8") as fh:
    for e in events:
        fh.write(json.dumps(e, sort_keys=True) + "\n")

manifest["files"][manifest_paths["events"]] = sha256_file(os.path.join(HERE, "events.jsonl"))
with open(os.path.join(HERE, "KEY_MANIFEST.json"), "w", encoding="utf-8") as fh:
    json.dump(manifest, fh, indent=1, sort_keys=True)

all_files = {}
for root, _dirs, files in os.walk(HERE):
    for f in files:
        full = os.path.join(root, f)
        rel = os.path.relpath(full, REPO)
        all_files[rel] = sha256_file(full)

pins = {
    TARGET: target_sha,
    TARGET_AUTHORING: authoring_sha,
    "artifacts/formulation/FROZEN.json": frozen_sha,
    "research_map/formulation_taxonomy.yaml": canon_tax_sha,
    "artifacts/formulation/formulation_taxonomy.yaml": supp_tax_sha,
    "schemas/af_wcc_vacuum.yaml": sha256_file(os.path.join(REPO, "schemas/af_wcc_vacuum.yaml")),
    "schemas/af_scc_c2_vacuum.yaml": sha256_file(os.path.join(REPO, "schemas/af_scc_c2_vacuum.yaml")),
}
stability = {}
for p, h in pins.items():
    samples = [s["hashes"][p] for s in report["stability"]["timeline"]]
    stability[p] = {
        "samples": len(samples),
        "distinct_hashes": len(set(samples)),
        "first": samples[0],
        "last": samples[-1],
        "drift": len(set(samples)) > 1,
    }

checkpoint = {
    "worker": "worker-089",
    "checkpoint": CHECKPOINT_N,
    "at": created,
    "task_id": TASK,
    "class_id": CLASS,
    "node_id": NODE,
    "gate": GATE,
    "verdict": report["verdict"],
    "verdict_scope": scope,
    "gate_verdict_claimed": False,
    "checks": {cid: c["status"] for cid, c in report["checks"].items()},
    "observations": {oid: o["detail"] for oid, o in report["observations"].items()},
    "controls": {mid: ("caught" if c["caught"] else "MISSED") for mid, c in report["controls"].items()},
    "no_false_positive_baseline": report["control_summary"]["no_false_positive_baseline"],
    "target": {
        "path": TARGET,
        "audited_sha256": target_sha,
        "recheck_sha256": target_sha,
        "drift_since_audit": report["stability"]["drift_detected"],
    },
    "pins": pins,
    "stability": stability,
    "notes": [
        "OBS-089-2: inline f0_binding.consistency_evidence_sha256 675a99d0 is stale after the rev28 re-freeze "
        "(live 9e335e9b, which FROZEN rev28 pins); same family defect as HF-034-F2A-3/HF-086-R1; excluded from scope.",
        "OBS-089-3: F2a/F2b data_class blocks differ only in adm_mass annotation text; measured input to the "
        "audit-lead O-GFORM-1 objection, not adjudicated here.",
        "Review is class-content only; it does not adjudicate O-GFORM-1 or any gate verdict.",
    ],
    "falsifier": falsifier,
    "next_falsifier": next_falsifier,
    "events_emitted": [e["event_id"] for e in events],
    "events_new": [e["event_id"] for e in events],
    "artifacts": all_files,
}
cp_path = os.path.join(REPO, f"runtime/state/w089_checkpoint_{CHECKPOINT_N}.json")
with open(cp_path, "w", encoding="utf-8") as fh:
    json.dump(checkpoint, fh, indent=1, sort_keys=True)

with open(os.path.join(REPO, "runtime/state/w089_checkpoints.jsonl"), "a", encoding="utf-8") as fh:
    fh.write(
        json.dumps(
            {
                "at": created,
                "worker": "worker-089",
                "task_id": TASK,
                "checkpoint": CHECKPOINT_N,
                "verdict": report["verdict"],
                "class_id": CLASS,
                "node_id": NODE,
                "gate": GATE,
                "target_sha256": target_sha,
                "checks": {cid: c["status"] for cid, c in report["checks"].items()},
                "controls": {mid: ("caught" if c["caught"] else "MISSED") for mid, c in report["controls"].items()},
                "drift_detected": report["stability"]["drift_detected"],
                "notes": checkpoint["notes"],
            },
            sort_keys=True,
        )
        + "\n"
    )

print(
    json.dumps(
        {
            "events": [e["event_id"] for e in events],
            "outbox": outbox,
            "checkpoint": cp_path,
            "manifest": os.path.join(HERE, "KEY_MANIFEST.json"),
            "n_artifact_files": len(all_files),
            "target_sha256": target_sha,
            "verdict": report["verdict"],
        },
        indent=1,
    )
)
