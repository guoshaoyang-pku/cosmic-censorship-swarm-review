#!/usr/bin/env python3
"""Emit W038-F0-CONFORMANCE-01 evidence: review corpus file + outbox events.

Writes (append-only for the outbox; the review file is this worker's own path):
  reviews/F0-conformance-038.json
  comms/outbox/worker-038.jsonl   (append)

Every event is validated with research_map.schemas.validate_event before writing.
Idempotent: re-running rewrites the review file and skips an outbox event whose
event_id already exists.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

TZ = timezone(timedelta(hours=8))
NOW = datetime.now(TZ).replace(microsecond=0).isoformat()
STAMP = NOW.replace(":", "").replace("+", "").replace("-", "")[:15]
D = ROOT / "artifacts/worker-038/f0_conformance"


def sha(p: str) -> str:
    h = hashlib.sha256()
    with (ROOT / p).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    rep = json.loads((D / "report.json").read_text())
    pin = rep["reviewed_revision"]["sha256"]
    report_sha = sha("artifacts/worker-038/f0_conformance/report.json")
    checker_sha = sha("artifacts/worker-038/f0_conformance/check_f0_independent.py")
    readme_sha = sha("artifacts/worker-038/f0_conformance/README.md")
    class_ids = rep["class_ids"]

    findings = [
        {"id": "F038-01", "kind": "positive",
         "text": ("declared F0 acceptance checker executed fresh at the pinned bytes: "
                  "253 checks passed, 0 failed, 37 taxonomy cases, exit 0; self-test exit 0 "
                  "(checker sha256 2cc8ee04023e). Author-family tooling, used as one input only."),
         "evidence": ["artifacts/worker-038/f0_conformance/worker01_validation.json",
                      "artifacts/worker-038/f0_conformance/run_manifest.txt"]},
        {"id": "F038-02", "kind": "positive",
         "text": ("exactly four class ids, duplicated nowhere: class_ids == classes keys == "
                  "evaluation_rubric.yaml#frozen_classes ids."),
         "evidence": ["research_map/formulation_taxonomy.yaml#276009f4f63d",
                      "evaluation_rubric.yaml#d748a9e3574e"]},
        {"id": "F038-03", "kind": "positive",
         "text": ("all 6 disjointness pairs present; IND-03 recomputed each named decisive axis "
                  "from the parsed axis vectors and every one genuinely differs. Separately the "
                  "declared checker reports no merged-regularity class."),
         "evidence": ["artifacts/worker-038/f0_conformance/independent_checks.json#IND-03"]},
        {"id": "F038-04", "kind": "positive",
         "text": ("G2 recomputed: SCC classes carry exactly one regularity token in {C0,C2}, WCC "
                  "classes carry none. IND-08 finds no merged-regularity token in the four class "
                  "blocks; whole-file occurrences are prohibition/guard text."),
         "evidence": ["artifacts/worker-038/f0_conformance/independent_checks.json#IND-04",
                      "artifacts/worker-038/f0_conformance/independent_checks.json#IND-08"]},
        {"id": "F038-05", "kind": "positive",
         "text": ("FROZEN.json rev26 logical_artifacts pins match the measured canonical "
                  "(276009f4) and supplement (c8e979a1) byte-for-byte, so the F0 publication "
                  "divergence is now role separation, not an unpinned revision."),
         "evidence": ["artifacts/formulation/FROZEN.json#2554e276a0db",
                      "artifacts/worker-038/f0_conformance/independent_checks.json#IND-06"]},
        {"id": "F038-06", "kind": "positive",
         "text": ("canonical/supplement role separation is internally consistent: identical "
                  "four-class id sets, disjoint role keys, `classes` absent from the supplement "
                  "and `class_contracts` absent from the canonical file."),
         "evidence": ["artifacts/worker-038/f0_conformance/independent_checks.json#IND-07"]},
        {"id": "F038-07", "kind": "positive",
         "text": ("A0 rubric frozen-class axes agree with the taxonomy under an explicit, "
                  "documented vocabulary mapping (formulation/family, regularity token, matter, "
                  "symmetry, Lambda=0 in hypotheses)."),
         "evidence": ["artifacts/worker-038/f0_conformance/independent_checks.json#IND-11"]},
        {"id": "F038-08", "kind": "observation",
         "text": ("non-blocking: the A0 rubric's conclusion_primary label "
                  "(future_asymptotic_predictability) differs from the taxonomy's conclusion_type "
                  "(weak_cosmic_censorship); F1 records that equivalence as UNVERIFIED. This is a "
                  "cross-artifact vocabulary divergence, not a G-F0 criterion failure."),
         "evidence": ["evaluation_rubric.yaml#d748a9e3574e",
                      "research_map/formulation_taxonomy.yaml#276009f4f63d"]},
        {"id": "F038-09", "kind": "observation",
         "text": ("non-blocking by design: genericity_kind is provisional_baire_residual for the "
                  "three vacuum classes and unresolved for AF-WCC-SCALAR-SPH, all owned downstream; "
                  "the taxonomy declares coverage gap CG1 rather than hiding it."),
         "evidence": ["research_map/formulation_taxonomy.yaml#276009f4f63d"]},
    ]

    review = {
        "review_id": "W038-F0-CONFORMANCE-01",
        "target_id": "F0",
        "target": {"node_id": "F0", "gate": "G-F0", "class_ids": class_ids,
                   "path": "research_map/formulation_taxonomy.yaml", "sha256": pin},
        "target_path": "research_map/formulation_taxonomy.yaml",
        "target_sha256": pin,
        "artifact_path": "research_map/formulation_taxonomy.yaml",
        "artifact_sha256": pin,
        "reviewed_sha256": pin,
        "reviewer": "worker-038",
        "reviewer_role": "bounded execution worker; not an author of F0, the supplement, the rubric, FROZEN.json or the declared checker",
        "review_kind": "independent machine-criteria conformance review at a pinned hash",
        "verdict": "accept",
        "score": 4.0,
        "counts_as_full_schema_verdict": True,
        "created_at": NOW,
        "gate_criteria_results": [
            {"criterion": "formulation_taxonomy.yaml exists and is hash-pinned", "result": "pass"},
            {"criterion": "exactly 4 separate class ids", "result": "pass"},
            {"criterion": "disjointness tests present and recomputed valid for 6/6 pairs", "result": "pass"},
            {"criterion": "no theorem-status promotion in a draft artifact", "result": "pass"},
            {"criterion": "independent reviewer verdict", "result": "this review is one such verdict"},
        ],
        "hard_failures": [],
        "hard_failures_note": ("no HF-01..HF-14 detected at the pinned hash: no theorem promotion, "
                               "no class leakage, no citation or quantitative claim, no merged "
                               "regularity token in class blocks."),
        "findings": findings,
        "residual_observations": rep["residual_observations"],
        "falsifier": rep["falsifier"],
        "evidence_refs": [
            f"research_map/formulation_taxonomy.yaml#{pin}",
            f"artifacts/worker-038/f0_conformance/report.json#{report_sha}",
            f"artifacts/worker-038/f0_conformance/check_f0_independent.py#{checker_sha}",
            f"artifacts/worker-038/f0_conformance/README.md#{readme_sha}",
            f"artifacts/formulation/FROZEN.json#{rep['pins']['before']['artifacts/formulation/FROZEN.json']}",
        ],
        "independence": rep["independence"],
        "authority_note": rep["authority_note"],
        "claims_not_made": rep["claims_not_made"],
    }
    rp = ROOT / "reviews/F0-conformance-038.json"
    rp.write_text(json.dumps(review, indent=1) + "\n", encoding="utf-8")
    review_sha = sha("reviews/F0-conformance-038.json")

    evidence = [f"artifacts/worker-038/f0_conformance/report.json#{report_sha}",
                f"artifacts/worker-038/f0_conformance/independent_checks.json#{sha('artifacts/worker-038/f0_conformance/independent_checks.json')}",
                f"reviews/F0-conformance-038.json#{review_sha}",
                f"research_map/formulation_taxonomy.yaml#{pin}"]
    common = {"actor": "worker-038", "created_at": NOW, "class_ids": class_ids,
              "gate": "G-F0", "node_id": "F0"}
    events = [
        dict(common, event_id=f"w038-f0-conformance-artifact-{STAMP}",
             event_type="artifact", artifact_type="f0_conformance_report",
             path="artifacts/worker-038/f0_conformance/report.json", sha256=report_sha,
             validation_status="unverified",
             evidence_refs=evidence,
             summary=("independent F0 conformance check at 276009f4f63d: declared checker 253/0/37 "
                      "(exit 0) + 11 independent PASS / 0 FAIL / 2 NOTE; verdict accept; worker "
                      "evidence only, no gate verdict.")),
        dict(common, event_id=f"w038-f0-conformance-checker-{STAMP}",
             event_type="artifact", artifact_type="f0_conformance_checker",
             path="artifacts/worker-038/f0_conformance/check_f0_independent.py", sha256=checker_sha,
             validation_status="unverified",
             evidence_refs=[f"artifacts/worker-038/f0_conformance/check_f0_independent.py#{checker_sha}",
                            f"artifacts/worker-038/f0_conformance/report.json#{report_sha}"],
             summary="deterministic re-runnable checker for the 11 independent G-F0 criteria checks"),
        dict(common, event_id=f"w038-f0-conformance-review-{STAMP}",
             event_type="review", reviewer="worker-038", target_id="F0",
             target_path="research_map/formulation_taxonomy.yaml", target_sha256=pin,
             artifact="research_map/formulation_taxonomy.yaml", artifact_sha256=pin,
             counts_as_full_schema_verdict=True,
             verdict="accept", score=4.0, hard_failures=[],
             findings=[f["text"] for f in findings],
             evidence_refs=evidence, artifact_refs=["reviews/F0-conformance-038.json"],
             falsifier=rep["falsifier"],
             summary=("independent accept of canonical F0 at 276009f4f63d on the machine-checkable "
                      "G-F0 criteria; 2 non-blocking observations; advisory worker verdict.")),
        dict(common, event_id=f"w038-f0-conformance-status-{STAMP}",
             event_type="status", status="active", hours=0.35,
             summary=("Executed an independent F0 conformance check at 276009f4f63d after the rev26 "
                      "role-separation adjudication: declared checker 253/0/37 exit 0; own checker 11 "
                      "PASS/0 FAIL/2 NOTE; FROZEN pins match; verdict accept (one advisory full-schema "
                      "verdict; G-F0 still needs a second independent accept)."),
             evidence_refs=evidence, next_falsifier=rep["falsifier"]),
    ]
    out = ROOT / "comms/outbox/worker-038.jsonl"
    existing = set()
    if out.exists():
        for line in out.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                existing.add(json.loads(line).get("event_id"))
            except Exception:
                pass
    written = []
    with out.open("a", encoding="utf-8") as f:
        for ev in events:
            validate_event(ev)
            if ev["event_id"] in existing:
                continue
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")
            written.append(ev["event_id"])
    print(json.dumps({"review_file": str(rp), "review_sha256": review_sha,
                      "events_written": written, "events_skipped_existing":
                      [e["event_id"] for e in events if e["event_id"] in existing]}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
