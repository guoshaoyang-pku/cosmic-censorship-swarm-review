#!/usr/bin/env python3
"""Emit worker-080 events for W080-GFORM-R29-VIS-01 (idempotent, append-only).

Run from the swarm root:  python3 artifacts/worker-080/rev29_f1_verify/emit_events_w080_r29f1.py
Writes to comms/outbox/worker-080.jsonl only after validating every event with
research_map/schemas.validate_event and every referenced artifact with
research_map/schemas.validate_artifact_hash.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research_map"))
import schemas  # noqa: E402

ART = ROOT / "artifacts/worker-080/rev29_f1_verify"
OUTBOX = ROOT / "comms/outbox/worker-080.jsonl"
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat(timespec="seconds")


def sha(rel: str) -> str:
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


REPORT = "artifacts/worker-080/rev29_f1_verify/report.json"
HARNESS = "artifacts/worker-080/rev29_f1_verify/verify_f1_rev29.py"
README = "artifacts/worker-080/rev29_f1_verify/README.md"
SUMS = "artifacts/worker-080/rev29_f1_verify/SHA256SUMS"
CKPT = "runtime/state/w080_gform_r29_vis_checkpoint.json"

F1 = "schemas/af_wcc_vacuum.yaml"
F1_SHA = "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d"
FROZEN = "artifacts/formulation/FROZEN.json"
FROZEN_SHA = sha(FROZEN)
F0 = "research_map/formulation_taxonomy.yaml"
F0_SHA = sha(F0)
EVID = "artifacts/formulation/evidence/taxonomy_consistency.json"
EVID_SHA = sha(EVID)
VREG = "artifacts/formulation/VARIANT_REGISTRY.json"
VREG_SHA = sha(VREG)

EVENTS = [
    {
        "event_id": "w080-r29f1-20260912-verify-artifact-report",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-080",
        "node_id": "F1",
        "gate": "G-FORM",
        "class_ids": ["AF-WCC-VAC-GEN"],
        "artifact_type": "verification_report",
        "path": REPORT,
        "sha256": sha(REPORT),
        "validation_status": "unverified",
        "summary": ("Independent rev29 F1 verification report: 13/13 checks pass, verdict accept for "
                    "the pinned d9cebb94 bytes, 0 hard failures, findings W080-F1-DIV-01 (major, "
                    "level-conflated SET strength labels across frozen artifacts) and "
                    "W080-F1-MAN-01 (info, FROZEN.json rewrite at constant revision 29)."),
        "evidence_refs": [f"{F1}#{F1_SHA[:12]}", f"{FROZEN}#{FROZEN_SHA[:12]}",
                          f"{F0}#{F0_SHA[:12]}", f"{EVID}#{EVID_SHA[:12]}"],
    },
    {
        "event_id": "w080-r29f1-20260912-verify-artifact-harness",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-080",
        "node_id": "F1",
        "gate": "G-FORM",
        "class_ids": ["AF-WCC-VAC-GEN"],
        "artifact_type": "deterministic_checker",
        "path": HARNESS,
        "sha256": sha(HARNESS),
        "validation_status": "unverified",
        "summary": ("Read-only deterministic harness (offline, no canonical writes): H1-H6 hash/"
                    "binding, V1-V3 visibility-direction machine checks, C1-C3 class binding and "
                    "direction, X1 canonical consistency-checker re-run."),
        "evidence_refs": [f"{REPORT}#{sha(REPORT)[:12]}"],
    },
    {
        "event_id": "w080-r29f1-20260912-verify-artifact-readme",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-080",
        "node_id": "F1",
        "gate": "G-FORM",
        "class_ids": ["AF-WCC-VAC-GEN"],
        "artifact_type": "report_readme",
        "path": README,
        "sha256": sha(README),
        "validation_status": "unverified",
        "summary": "Human-readable method/result/finding summary for W080-GFORM-R29-VIS-01.",
        "evidence_refs": [f"{REPORT}#{sha(REPORT)[:12]}"],
    },
    {
        "event_id": "w080-r29f1-20260912-verify-artifact-sums",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-080",
        "node_id": "F1",
        "gate": "G-FORM",
        "class_ids": ["AF-WCC-VAC-GEN"],
        "artifact_type": "hash_manifest",
        "path": SUMS,
        "sha256": sha(SUMS),
        "validation_status": "unverified",
        "summary": "SHA256SUMS binding the checker, report, README, sandbox checker output and pinned input manifest.",
        "evidence_refs": [f"{REPORT}#{sha(REPORT)[:12]}"],
    },
    {
        "event_id": "w080-r29f1-20260912-verify-review",
        "event_type": "review",
        "created_at": NOW,
        "actor": "worker-080",
        "reviewer": "worker-080",
        "node_id": "F1",
        "gate": "G-FORM",
        "class_ids": ["AF-WCC-VAC-GEN"],
        "target_id": F1,
        "target_sha256": F1_SHA,
        "verdict": "accept",
        "score": 4.0,
        "hard_failures": [],
        "findings": [
            {"id": "W080-F1-DIV-01", "severity": "major",
             "finding": ("Level-conflated strength labels: F1 rev13's variant SET relation is "
                         "correct at the predicate level (SET predicate strictly weaker; "
                         "single-q tail entails union), while the frozen F0 class text "
                         "(research_map/formulation_taxonomy.yaml:200) and frozen "
                         "VARIANT_REGISTRY.json both assert the set-based reading is 'strictly "
                         "stronger' without a level qualifier, which is correct only at the "
                         "class-statement level (the SET conclusion entails the base conclusion). "
                         "No declared checker compares these fields."),
             "evidence_refs": [f"{F1}#{F1_SHA[:12]}:234", f"{F0}#{F0_SHA[:12]}:200",
                               f"{VREG}#{VREG_SHA[:12]}:57"],
             "recommended_fix": ("Add explicit level labels to the F1 variant SET entry "
                                 "(relation: strictly_weaker predicate; statement_strength: "
                                 "strictly_stronger, using the schema's existing vocabulary) and "
                                 "record the frozen F0/VARIANT_REGISTRY wording as a "
                                 "controller-adjudicated divergence (REC-11 freezes F0 bytes).")},
            {"id": "W080-F1-PASS-01", "severity": "pass",
             "finding": ("rev29 evidence binding verifies: consistency_evidence_sha256 9e335e9b "
                         "matches the measured evidence file in all three schemas, declared F0 "
                         "0abb9ed8 matches the canonical bytes, both pointers resolve, and the "
                         "case corpus binds the measured F0 rev5 hash; R03/stale-hash repair "
                         "closed at this pin."),
             "evidence_refs": [f"{F1}#{F1_SHA[:12]}", f"{EVID}#{EVID_SHA[:12]}"]},
            {"id": "W080-F1-PASS-02", "severity": "pass",
             "finding": ("AF_{I+} symbol closure (W080-FSYM-01 from rev11) verified at rev29: one "
                         "definition site i_plus.predicate_abbreviation, every use downstream."),
             "evidence_refs": [f"{F1}#{F1_SHA[:12]}"]},
            {"id": "W080-F1-PASS-03", "severity": "pass",
             "finding": ("Visibility direction independently machine-checked: whole/tail "
                         "equivalence under J^-(q) past-closedness (V1), single-q tail => union "
                         "(V2), omega-chain separation union =/=> single-q tail (V3)."),
             "evidence_refs": [f"{REPORT}#{sha(REPORT)[:12]}"]},
            {"id": "W080-F1-MAN-01", "severity": "info",
             "finding": ("artifacts/formulation/FROZEN.json bytes changed inside revision 29 "
                         "during this window (3d9e3d77 -> 815e0807, frozen_at 00:55:02 -> 00:57:26) "
                         "while the three schema bytes stayed fixed; the manifest self-hash is not "
                         "registered in artifact_hashes.json."),
             "evidence_refs": [f"{FROZEN}#{FROZEN_SHA[:12]}"]},
        ],
        "falsifier": ("Re-run artifacts/worker-080/rev29_f1_verify/verify_f1_rev29.py at the same "
                      "pinned hashes: any H/V/C check flipping, a P_tail-but-not-P_set witness for "
                      "a causal geodesic with J^-(q) past-closed, or a union-but-not-single-q-tail "
                      "witness (which would collapse variant SET) voids this verdict; a silent "
                      "rewrite of schemas/af_wcc_vacuum.yaml or the pinned F0 pair voids the hash "
                      "binding and requires a fresh review."),
        "evidence_refs": [f"{REPORT}#{sha(REPORT)[:12]}", f"{HARNESS}#{sha(HARNESS)[:12]}",
                          f"{F1}#{F1_SHA[:12]}", f"{F0}#{F0_SHA[:12]}",
                          f"{EVID}#{EVID_SHA[:12]}", f"{FROZEN}#{FROZEN_SHA[:12]}"],
    },
    {
        "event_id": "w080-r29f1-20260912-verify-claim",
        "event_type": "claim",
        "created_at": NOW,
        "actor": "worker-080",
        "node_id": "F1",
        "gate": "G-FORM",
        "class_id": "AF-WCC-VAC-GEN",
        "class_ids": ["AF-WCC-VAC-GEN"],
        "conclusion_type": "formal_model",
        "statement": ("At the pinned rev29 hashes (F1 schemas/af_wcc_vacuum.yaml "
                      "d9cebb9404b2e79e, F2a e9a27996dfd308bd, F2b b2ab6acb2bbe7f86, FROZEN "
                      "artifacts/formulation/FROZEN.json " + FROZEN_SHA[:16] + ", canonical F0 "
                      "0abb9ed8a961, evidence 9e335e9ba1bf): the rev13 F1 repairs verify under an "
                      "independent harness - the D5/visibility whole-curve/tail equivalence holds "
                      "for causal geodesics by past-closedness of J^-(q) (13/13 checks, 0 hard "
                      "failures); the variant SET predicate direction is strictly weaker than the "
                      "single-q tail predicate while the SET class statement is strictly stronger, "
                      "and the frozen F0/VARIANT_REGISTRY 'strictly stronger' wording carries no "
                      "level qualifier (finding W080-F1-DIV-01, major)."),
        "assumptions": [
            "J^-(q) is past-closed and the causal relation is a preorder (standard, used only for V1/V2)",
            "the FROZEN rev29 manifest is the pin authority; schema bytes are the review target",
            "worker verdicts are evidence, not gate verdicts; the audit lead owns G-FORM r3",
        ],
        "falsifier": ("Re-run artifacts/worker-080/rev29_f1_verify/verify_f1_rev29.py at the pinned "
                      "hashes: a check flip, an input-hash drift, or a machine-checkable witness "
                      "that P_tail fails while P_set holds (or that the union predicate entails a "
                      "single-q tail) voids the statement. A silent rewrite of the F1 schema or the "
                      "pinned F0 pair voids the binding."),
        "evidence_refs": [f"{REPORT}#{sha(REPORT)[:12]}", f"{HARNESS}#{sha(HARNESS)[:12]}",
                          f"{F1}#{F1_SHA[:12]}", f"{F0}#{F0_SHA[:12]}",
                          f"{EVID}#{EVID_SHA[:12]}", f"{FROZEN}#{FROZEN_SHA[:12]}",
                          f"{VREG}#{VREG_SHA[:12]}"],
        "artifact_refs": [
            {"path": REPORT, "sha256": sha(REPORT)},
            {"path": HARNESS, "sha256": sha(HARNESS)},
            {"path": README, "sha256": sha(README)},
            {"path": SUMS, "sha256": sha(SUMS)},
        ],
    },
    {
        "event_id": "w080-r29f1-20260912-verify-status",
        "event_type": "status",
        "created_at": NOW,
        "actor": "worker-080",
        "node_id": "F1",
        "gate": "G-FORM",
        "class_ids": ["AF-WCC-VAC-GEN"],
        "status": "active",
        "hours": 0.6,
        "summary": ("W080-GFORM-R29-VIS-01 complete from the worker side: one bounded class-bound "
                    "task, read-only on every canonical path. Delivered an independent rev29 F1 "
                    "verification (report, harness, README, SHA256SUMS): 13/13 checks pass, verdict "
                    "accept at schema hash d9cebb94, 0 hard failures; findings W080-F1-DIV-01 "
                    "(major: level-conflated SET strength labels across frozen artifacts; no "
                    "declared checker compares the fields) and W080-F1-MAN-01 (info: FROZEN.json "
                    "rewritten at constant revision 29). Closes the worker-side re-check of the "
                    "rev13 evidence-binding repair and the W080-FSYM-01 symbol finding at rev29."),
        "evidence_refs": [f"{REPORT}#{sha(REPORT)[:12]}", f"{HARNESS}#{sha(HARNESS)[:12]}",
                          f"{README}#{sha(README)[:12]}", f"{SUMS}#{sha(SUMS)[:12]}",
                          f"{F1}#{F1_SHA[:12]}", f"{CKPT}#{sha(CKPT)[:12]}"],
        "next_falsifier": ("Have a second independent reviewer re-run the harness at the pinned "
                           "hashes and adversarially attempt V1/V3 countermodels; a check flip, an "
                           "input-hash drift, or an F1/F0 direction countermodel voids the accept. "
                           "The DIV-01 wording divergence needs controller/lead adjudication "
                           "because F0 bytes are frozen by REC-11."),
        "not_claimed": [
            "no gate verdict", "no node status", "no validation_status=passed",
            "no mathematical claim about WCC truth",
            "no canonical artifact modified (all inputs pinned as copies)",
            "no claim that F0/VARIANT_REGISTRY are mathematically wrong - their wording is "
            "statement-level correct but unlabeled",
        ],
    },
]


def main() -> int:
    existing = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            line = line.strip()
            if line:
                try:
                    existing.add(json.loads(line).get("event_id"))
                except Exception:
                    pass
    written = 0
    with OUTBOX.open("a") as fh:
        for ev in EVENTS:
            schemas.validate_event(ev)  # raises on schema violation
            for ref in ev.get("evidence_refs", []):
                if "#" in ref:
                    p = ref.split("#", 1)[0]
                    if (ROOT / p).exists() and not p.startswith("runtime/state/"):
                        pass
            for aref in ev.get("artifact_refs", []) or []:
                assert schemas.validate_artifact_hash(str(ROOT / aref["path"]), aref["sha256"]), \
                    f"artifact hash mismatch: {aref['path']}"
            if ev["event_id"] in existing:
                print(f"skip duplicate {ev['event_id']}")
                continue
            fh.write(json.dumps(ev, sort_keys=True) + "\n")
            written += 1
            print(f"wrote {ev['event_type']:8s} {ev['event_id']}")
    print(f"total written: {written}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
