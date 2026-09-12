#!/usr/bin/env python3
"""Emit W094G-CF21-SCOPE-PRECISION-01 events to comms/outbox/worker-094.jsonl.

Each event is validated against research_map.schemas before appending; a
malformed event cannot enter the stream.  Append-only; never rewrites existing
lines.  Read-only on all canonical inputs.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research_map"))
import schemas  # noqa: E402

CST = timezone(timedelta(hours=8))
STAMP = "20260912T011822"
NOW = datetime.now(CST).replace(microsecond=0).isoformat()
OUTBOX = ROOT / "comms/outbox/worker-094.jsonl"
ACTOR = "worker-094"
TASK = "W094G-CF21-SCOPE-PRECISION-01"
CLASSES = ["AF-WCC-SCALAR-SPH", "AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
CLASS_STR = ";".join(CLASSES)
NODES = ["F0", "N0"]
TO = ["astra", "lead-formulation", "lead-audit", "lead-numerics"]

HERE = "artifacts/worker-094/cf21_scope_audit"
REPORT = f"{HERE}/run/report.json"
REPORT_SHA = "7e57bcc26a298b040117f90c55de9c62a0b540c8e0a91afb2a2191091c0572b6"
INSTRUMENT = f"{HERE}/audit_cf21_scope.py"
INSTRUMENT_SHA = "e2a53b214a6a563bed166ff3555b7746008f6f9d89fd076ced33f201064387a7"
README = f"{HERE}/README.md"
README_SHA = "f13e2887a43953e80d10af4b4758fc32156a823916f5bca01cc6e7433c43358b"
MANIFEST = f"{HERE}/run/manifest.json"
MANIFEST_SHA = "a8fb3b26e3df767e5c62341a705e6d9b86120a73a332be9ef270a9bc5eb60279"
CHECKPOINT = "runtime/state/w094_cf21_scope_checkpoint.json"
CHECKPOINT_SHA = "9cdd9be4b6d1958adeed94494906d11133906afee931a30e8d06165548fe5090"
PRIOR_A = "artifacts/worker-094/genericity_consistency/run/report.json"
PRIOR_A_SHA = "10a92ff3c9c1d4271a584b8fa6c79fe94ac505fcfe1db74189a256f76708f282"
PRIOR_B = "artifacts/worker-094/cf21_rev13_recheck/run/report.json"
PRIOR_B_SHA = "629a3232bb84fc8a77b60b782d6f6a3705e5277096d9391b3cb07abd97a0cea9"

EVIDENCE = [
    f"{REPORT}#{REPORT_SHA[:12]}",
    f"{INSTRUMENT}#{INSTRUMENT_SHA[:12]}",
    f"{README}#{README_SHA[:12]}",
    f"{MANIFEST}#{MANIFEST_SHA[:12]}",
    f"{CHECKPOINT}#{CHECKPOINT_SHA[:12]}",
    f"{PRIOR_A}#{PRIOR_A_SHA[:12]}",
    f"{PRIOR_B}#{PRIOR_B_SHA[:12]}",
    "research_map/formulation_taxonomy.yaml#0abb9ed8a961:81",
    "research_map/formulation_taxonomy.yaml#0abb9ed8a961:393",
    "research_map/formulation_taxonomy.yaml#0abb9ed8a961:395",
    "research_map/formulation_taxonomy.yaml#0abb9ed8a961:407",
    "research_map/formulation_taxonomy.yaml#0abb9ed8a961:414",
    "artifacts/formulation/formulation_taxonomy.yaml#d7419b4e8963",
    "schemas/taxonomy_cases.jsonl#ccf7041bd0ff",
    "numerics/N0_CLASS_BINDING_AUTHORITY.json#effd20b0ea09",
    "numerics/results/flat_wave_convergence_rev3.json#da7c36071995",
]

FALSIFIER = (
    "Re-run artifacts/worker-094/cf21_scope_audit/audit_cf21_scope.py at unchanged pins. The "
    "correction is falsified if D3's resolution text is shown to claim a genericity-notion "
    "discharge, or if the AF-WCC-SCALAR-SPH conclusion does not state the bound comeager quantifier "
    "(taxonomy:414); the underlying CF-21 core is falsified (becomes not-live) if the scalar axis "
    "is resolved or the conclusion gains a machine-readable provisional/blocked marker; any pinned "
    "sha256 change voids the measurement for the new bytes; any of the 12 controls departing from "
    "its pre-registered expectation voids the instrument."
)
NEXT_FALSIFIER = (
    "python3 artifacts/worker-094/cf21_scope_audit/audit_cf21_scope.py ; exit 0 with "
    "CF21_STANDS_D3_ATTRIBUTION_CORRECTED re-confirms. A repaired scalar axis/conclusion flips to "
    "CF21_CORE_NOT_REPRODUCED (residual void); a D3 text rewrite that claims a genericity-notion "
    "discharge flips the correction (control M9 demonstrates the discrimination)."
)


def artifact(event_id, artifact_type, path, sha, summary, bytes_=None):
    e = {
        "event_id": event_id,
        "event_type": "artifact",
        "created_at": NOW,
        "actor": ACTOR,
        "task_id": TASK,
        "class_id": CLASS_STR,
        "class_ids": CLASSES,
        "node_id": "F0",
        "node_ids": NODES,
        "gate": "G-F0",
        "artifact_type": artifact_type,
        "path": path,
        "sha256": sha,
        "validation_status": "unverified",
        "claims_completion": False,
        "summary": summary,
        "evidence_refs": EVIDENCE,
    }
    if bytes_ is not None:
        e["bytes"] = bytes_
    return e


def build():
    events = [
        artifact(
            f"w094g-cf21scope-{STAMP}-artifact-report",
            "cf21_scope_audit_report", REPORT, REPORT_SHA,
            "CF-21 disposition-scope audit at the frozen F0 bytes: verdict "
            "CF21_STANDS_D3_ATTRIBUTION_CORRECTED. C1-C4 (axis unresolved / value status / H4 "
            "claim-blocking / comeager conclusion without marker) reproduce on AF-WCC-SCALAR-SPH "
            "only; C5-C7 measure D3's own scope (conclusion wording) and show the scalar conclusion "
            "satisfies it, so the prior D3-unsupported sub-clause is withdrawn as mis-attributed; "
            "C8/C9 measure that the companion supplement does not discharge the axis (uniform 'GEN' "
            "token); the rev5-bound case corpus shows the unresolved axis is load-bearing (4/4 "
            "scalar rows, 3/4 decisive_axes); the N0 binding-of-record names the taxonomy pin with 0 "
            "genericity tokens in the carrier. 12/12 controls, 9/9 pins, 0 drift. Advisory.",
            bytes_=11820),
        artifact(
            f"w094g-cf21scope-{STAMP}-artifact-instrument",
            "cf21_scope_audit_instrument", INSTRUMENT, INSTRUMENT_SHA,
            "Pin-gated read-only audit instrument: decomposes CF-21 into C1-C10, runs 12 "
            "pre-registered in-memory mutation controls (including a D3-text rewrite control that "
            "discriminates conclusion-wording from genericity-notion scope, and a pin-drift gate), "
            "and fail-closes (exit 3 control deviation, 4 drift). Writes only run/report.json.",
            bytes_=24786),
        artifact(
            f"w094g-cf21scope-{STAMP}-artifact-readme",
            "cf21_scope_audit_readme", README, README_SHA,
            "Task README: why the correction exists, the nine pins, the sub-claim table, the "
            "withdrawn clause, the retained core, the supplement/corpus/N0 measurements, controls, "
            "falsifier, boundaries and reproduction.",
            bytes_=7888),
        artifact(
            f"w094g-cf21scope-{STAMP}-artifact-manifest",
            "cf21_scope_audit_manifest", MANIFEST, MANIFEST_SHA,
            "sha256 manifest of instrument/report/readme plus the nine pinned inputs, the verdict, "
            "control status and drift record.",
            bytes_=3160),
        {
            "event_id": f"w094g-cf21scope-{STAMP}-claim-correction",
            "event_type": "claim",
            "created_at": NOW,
            "actor": ACTOR,
            "task_id": TASK,
            "class_id": CLASS_STR,
            "class_ids": CLASSES,
            "node_id": "F0",
            "node_ids": NODES,
            "gate": "G-F0",
            "conclusion_type": "formal_model",
            "statement": (
                "Declaration-level scope correction at the frozen F0 pin 0abb9ed8a961 (companion "
                "supplement d7419b4e8963, case corpus ccf7041bd0ff, N0 record effd20b0ea09, carrier "
                "da7c36071995; 9/9 pin match, 0 drift). (1) WITHDRAWN: worker-094's sub-clause that "
                "the class_scope_adjudication D3 record 'is unsupported for AF-WCC-SCALAR-SPH' "
                "(events w094-gencons-20260912T005630-claim-declaration-consistency / -review-cf21 / "
                "-blocker and w094f-cf21rev13-20260912T011015-claim / -blocker) is mis-attributed. "
                "D3's resolution text is scoped to the comeager quantifier being stated explicitly "
                "in each class conclusion text (the D1/D3 wording divergence, taxonomy:81), and the "
                "scalar conclusion satisfies it: 'For a comeager set G of data in the class, chosen "
                "before and independently of the data' (taxonomy:414). D3 does not claim a "
                "genericity-notion discharge (measured C6=false). No D3 re-adjudication is needed. "
                "(2) RETAINED: the CF-21 core reproduces on AF-WCC-SCALAR-SPH only -- "
                "axes.genericity_kind='unresolved' (:393), genericity_value_status="
                "'unresolved_pending_L1' (:395), H4 unresolved:true/machine_checkable:false with "
                "'must be named before any claim is filed' (:407), while the conclusion commits to "
                "the comeager quantifier with no machine-readable provisional/blocked marker (:414). "
                "(3) NEW: the companion supplement does not discharge the axis -- its scalar "
                "class_contract declares genericity only as the uniform token 'GEN' plus a "
                "qualitative ambient-space hypothesis, and all four contracts carry the same token "
                "(C8=false, C9=true), so there is no third repair path via the supplement. (4) NEW: "
                "the unresolved axis is load-bearing, not stale metadata -- in the rev5-bound corpus "
                "all 4 scalar rows carry axis_vector.genericity_kind='unresolved', 3 of 4 list "
                "genericity_kind in decisive_axes, and TC-F0-P15 files Christodoulou 1999 with "
                "genericity_kind=unresolved and defers the codimension-to-Baire mapping to L1. (5) "
                "NEW: the N0 class-binding record and carrier both bind this taxonomy pin with 0 "
                "genericity tokens in the carrier, so the certified second-order result is "
                "materially independent while the binding-of-record names the inconsistent bytes. "
                "The repair surface is unchanged: taxonomy rev6 (voids G-F0 at 0abb9ed8a961 and "
                "forces a full F0 re-run) or an explicit controller record of residual acceptance. "
                "This is a declaration-level measurement at pinned hashes; it asserts no theorem, "
                "sets no gate or node status, and no prior claim text is edited."
            ),
            "assumptions": [
                "The canonical taxonomy 0abb9ed8a961 is the F0 artifact the gate passed on; any write voids G-F0 and this measurement with it.",
                "D3's declared scope is read from its own resolution text at :81; the audit measures that text rather than assuming it (control M9 rewrites the text and the scope predicate flips).",
                "The companion supplement d7419b4e8963 is the class-contract layer REC-3 pairs with the canonical taxonomy; byte-identity between the pair is not required, so a supplement that named a kind could in principle discharge the axis -- it does not (measured).",
                "The case corpus ccf7041bd0ff is bound to taxonomy rev5 (binding_status bound_taxonomy_sha_0abb9ed8a961); it is the class-separation surface that the F0 gate's disjointness criterion consumes.",
                "Worker events are advisory; the controller owns the CF-21 disposition and any D3 note.",
            ],
            "falsifier": FALSIFIER,
            "evidence_refs": EVIDENCE,
            "artifact_refs": [
                f"{REPORT}#{REPORT_SHA[:12]}",
                f"{INSTRUMENT}#{INSTRUMENT_SHA[:12]}",
                f"{MANIFEST}#{MANIFEST_SHA[:12]}",
                f"{README}#{README_SHA[:12]}",
            ],
        },
        {
            "event_id": f"w094g-cf21scope-{STAMP}-review-prior",
            "event_type": "review",
            "created_at": NOW,
            "actor": ACTOR,
            "to": TO,
            "task_id": TASK,
            "class_id": CLASS_STR,
            "class_ids": CLASSES,
            "node_id": "F0",
            "node_ids": NODES,
            "gate": "G-F0",
            "target_id": f"{PRIOR_B}#{PRIOR_B_SHA[:12]} (worker-094 CF-21 claim surface, both prior batches)",
            "reviewer": ACTOR,
            "reviewed_artifact": REPORT,
            "reviewed_sha256": REPORT_SHA,
            "verdict": "revise",
            "score": 3.0,
            "scope": (
                "Author self-correction, scoped to the D3 sub-clause of worker-094's own prior CF-21 "
                "claims only; the core CF-21 measurement in those claims is re-confirmed unchanged. "
                "Not a gate verdict, not a full-schema review, and not an edit of any prior event."
            ),
            "counts_as_full_schema_verdict": False,
            "hard_failures": [
                "The D3-unsupported sub-clause in w094-gencons-20260912T005630-claim-declaration-consistency / -review-cf21 / -blocker and w094f-cf21rev13-20260912T011015-claim / -blocker is mis-attributed: D3's resolution text discharges the conclusion-wording divergence (D1/D3) and the scalar conclusion satisfies it at :414."
            ],
            "findings": [
                "Correction: withdraw the D3 sub-clause; the residual is the axis/H4-vs-conclusion tension, which stands (C1-C4 true).",
                "No third path: the companion supplement declares genericity only as the uniform token 'GEN' for all four classes, so it does not discharge the scalar axis (C8 false, C9 true).",
                "Severity input for the controller: the unresolved axis is load-bearing for the bound class-separation corpus (4/4 scalar rows carry it; 3/4 list genericity_kind in decisive_axes), so the pass-07 'stale metadata' rationale is not supported by the corpus that binds the same taxonomy hash.",
                "G-NUM input: the N0 binding record and carrier bind the inconsistent taxonomy hash by reference with 0 genericity tokens in the carrier -- material independence holds; the binding-of-record should be noted, not treated as withholding evidence.",
                "Boundary: this review corrects a claim-attribution defect in worker-094's own output; it does not re-adjudicate D3, the taxonomy, the supplement, the corpus, the N0 record, or any other agent's artifact.",
            ],
            "next_falsifier": NEXT_FALSIFIER,
        },
        {
            "event_id": f"w094g-cf21scope-{STAMP}-blocker-disposition",
            "event_type": "blocker",
            "created_at": NOW,
            "actor": ACTOR,
            "to": TO,
            "task_id": TASK,
            "class_id": CLASS_STR,
            "class_ids": CLASSES,
            "node_id": "F0",
            "node_ids": NODES,
            "gate": "G-F0",
            "description": (
                "CF-21's disposition surface needs one controller edit and one controller decision. "
                "(1) The withdrawn D3 sub-clause is still present in the accepted stream (4 "
                "worker-094 events) and must not be propagated into the CF-21 record: D3 is "
                "satisfied for its declared scope; no D3 re-adjudication is needed. (2) The retained "
                "residual cannot be repaired inside the freeze: any write to "
                "research_map/formulation_taxonomy.yaml voids G-F0 at 0abb9ed8a961. The companion "
                "supplement is not a discharge path (measured), and the unresolved axis is "
                "load-bearing for the rev5-bound case corpus, so a silent inheritance of the "
                "residual is not supported by the taxonomy's own machine-readable structure."
            ),
            "needed_to_unblock": (
                "Controller: (a) record the correction in the CF-21 disposition (drop the "
                "D3-unsupported attribution; keep the residual recorded-open), and (b) choose "
                "either taxonomy rev6 -- resolve axes.genericity_kind to residual_comeager with the "
                "corpus rebound, or add a machine-readable provisional/blocked marker on the "
                "conclusion -- followed by a full F0 re-run (this voids G-F0 at 0abb9ed8a961), or "
                "an explicit recorded acceptance of residual CF-21 with a rationale. Additionally, "
                "for astra-life04-n0-verify: the N0 class binding of record names the inconsistent "
                "bytes while the certified order is materially independent (0 genericity tokens in "
                "the carrier)."
            ),
            "expected_information_gain": (
                "Removes a false attribution from the decision surface and forces the residual to be "
                "either repaired or knowingly accepted at the frozen bytes, instead of being "
                "silently inherited or mis-attributed to D3."
            ),
            "evidence_refs": EVIDENCE,
        },
        {
            "event_id": f"w094g-cf21scope-{STAMP}-status-complete",
            "event_type": "status",
            "created_at": NOW,
            "actor": ACTOR,
            "to": TO,
            "task_id": TASK,
            "class_id": CLASS_STR,
            "class_ids": CLASSES,
            "node_id": "F0",
            "node_ids": NODES,
            "gate": "G-F0",
            "status": "active",
            "hours": 0.4,
            "summary": (
                "W094G-CF21-SCOPE-PRECISION-01 complete at worker level (not a node done, not a gate "
                "verdict): one class-bound task taken from live state (no inbox card for slot 094) "
                "-- precision audit of CF-21's disposition surface at the frozen F0 bytes. Verdict "
                "CF21_STANDS_D3_ATTRIBUTION_CORRECTED: the core (axis/H4 vs comeager conclusion) is "
                "re-confirmed on AF-WCC-SCALAR-SPH only; worker-094's own D3-unsupported sub-clause "
                "is withdrawn as mis-scoped (D3 discharges the conclusion-wording divergence, which "
                "the scalar conclusion satisfies); the companion supplement does not discharge the "
                "axis; the unresolved axis is load-bearing for the rev5-bound case corpus; the N0 "
                "binding is materially independent but names the inconsistent bytes. 12/12 controls, "
                "9/9 pins, 0 drift. 4 artifacts + claim + review + blocker emitted; checkpoint "
                "runtime/state/w094_cf21_scope_checkpoint.json. No canonical write, no gate verdict, "
                "no node status; worker exits now."
            ),
            "evidence_refs": EVIDENCE,
            "next_falsifier": NEXT_FALSIFIER,
        },
    ]
    for e in events:
        schemas.validate_event(e)
    return events


def main() -> int:
    events = build()
    lines = [json.dumps(e, ensure_ascii=True) + "\n" for e in events]
    with OUTBOX.open("a") as fh:
        fh.writelines(lines)
    h = hashlib.sha256(OUTBOX.read_bytes()).hexdigest()
    print(json.dumps({
        "appended": len(events),
        "event_ids": [e["event_id"] for e in events],
        "outbox": str(OUTBOX),
        "outbox_sha256_after_append": h,
        "stamp": STAMP,
    }, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
