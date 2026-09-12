#!/usr/bin/env python3
"""Emit the W084-HELDOUT10-INDEP-01 upward events to comms/outbox/worker-084.jsonl.

Every event is validated with the project's own research_map/schemas.py::validate_event
BEFORE it is written, so a schema-invalid claim (the failure mode that silently rejected
the executor's first claim events) cannot recur.

Usage: python3 artifacts/heldout/heldout-10/verify/emit_indep_events.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

CST = timezone(timedelta(hours=8))
ROOT = Path(__file__).resolve().parents[4]
VERIFY = ROOT / "artifacts" / "heldout" / "heldout-10" / "verify"
OUTBOX = ROOT / "comms" / "outbox" / "worker-084.jsonl"
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ref(p: str, digest: str) -> str:
    return f"{p}#sha256:{digest[:12]}"


def main() -> int:
    stamp = datetime.now(CST).strftime("%Y%m%dT%H%M%S%z")
    created = datetime.now(CST).isoformat(timespec="seconds")
    task = "W084-HELDOUT10-INDEP-01"

    files = {
        "verifier": VERIFY / "verify_heldout_10_independent.py",
        "verification": VERIFY / "verification.json",
        "adjudication": VERIFY / "adjudication.json",
        "review": VERIFY / "INDEPENDENT_REVIEW.md",
    }
    H = {k: sha(p) for k, p in files.items()}
    v = json.loads(files["verification"].read_text())
    assert v["checks_total"] == 28 and v["checks_passed"] == 27, "unexpected verification totals"
    agg_inf = v["recomputed_aggregates"]["informative_arms"]
    agg_all = v["recomputed_aggregates"]["all_mutants"]

    common = {
        "actor": "worker-084",
        "node_id": "A1",
        "gate": "G-CLASSBIND",
        "task_id": task,
        "corpus_id": "FORM-HELDOUT-10",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "assignment": "assign-FORM-HELDOUT-09-worker-084 was voided by the rev28->rev29 move; "
                      "FORM-HELDOUT-10 is the preserved successor corpus; this is its independent "
                      "terminal verification",
    }

    events: list[dict] = []

    events.append(dict(common, event_id=f"w084-ind10-{stamp}-01-status-task", event_type="status",
                       created_at=created, status="active", hours=0.4,
                       summary="W084-HELDOUT10-INDEP-01: one bounded class-bound task taken and completed. "
                               "Independent terminal verification of the preserved FORM-HELDOUT-10 corpus: "
                               "both canonical stages re-invoked directly on all 40 fixtures (33 mutants "
                               "+ 7 controls) at the preserved bytes; all 40 stage-A/B verdicts and "
                               "failed-rule lists reproduced exactly; aggregates recomputed. Real "
                               "adjudication: reproducibility ACCEPT (27/27 non-H5 checks); strict H5 "
                               "corpus_valid=false (pre-registered WCC R03 instrument defect, independently "
                               "reproduced); informative C2+C0 union escape 1.0 (0/26 caught). No drift.",
                       evidence_refs=[ref("artifacts/heldout/heldout-10/verify/verification.json", H["verification"])],
                       next_falsifier="Re-run the verifier at the recorded hashes; falsified if any check "
                                      "now fails or any pinned byte moved."))

    for i, (kind, label, note) in enumerate([
            ("verifier", "independent_verification_script",
             "Re-runnable: no import of build_corpus_10.py or run_heldout_10.py; invokes both canonical "
             "stages as subprocesses and compares verdicts/failed_rules fixture-by-fixture."),
            ("verification", "independent_verification_json",
             "28 checks (27 pass; only strict-H5 C01 fails, pre-registered), independent re-run verdicts "
             "for 40 fixtures, recomputed aggregates, drift re-hash."),
            ("adjudication", "independent_adjudication",
             "Terminal adjudication: reproducibility accept; corpus_valid=false under strict H5; "
             "informative-arm union escape 1.0 (0/26)."),
            ("review", "independent_review_markdown",
             "Human-readable independent review; worker verdict only, no gate verdict."),
    ], start=2):
        events.append(dict(common, event_id=f"w084-ind10-{stamp}-{i:02d}-artifact-{kind}",
                           event_type="artifact", created_at=created, artifact_type=label,
                           path=str(files[kind].relative_to(ROOT)), sha256=H[kind],
                           validation_status="unverified", note=note,
                           evidence_refs=[ref(str(files[kind].relative_to(ROOT)), H[kind])]))

    events.append(dict(common, event_id=f"w084-ind10-{stamp}-06-review", event_type="review",
                       created_at=created, target_id="FORM-HELDOUT-10", reviewer="worker-084",
                       verdict="accept", score=3.0, hard_failures=[],
                       target_artifact="artifacts/heldout/heldout-10/report.json",
                       reviewed_sha256=sha(ROOT / "artifacts/heldout/heldout-10/report.json"),
                       findings=[
                           "Reproducibility ACCEPT: 27/27 non-H5 checks pass; all 40 fixture stage-A/B "
                           "verdicts and failed_rules reproduced exactly from the preserved bytes.",
                           "Strict H5 remains false and is terminal for the corpus as a strict measurement: "
                           "stage B c79d8ab8440a rejects the untouched frozen WCC canonical d9cebb9404b2 "
                           "on R03 only (literal-substring binder), independently reproduced; the executor "
                           "pre-registered this instrument defect before freezing the corpus.",
                           f"Informative C2+C0 arms: union escape {agg_inf['union_escape']} "
                           f"({agg_inf['union_caught']}/{agg_inf['mutants']} caught) — the independent "
                           "re-run catches nothing, confirming the executor's headline.",
                           f"All-mutant union escape {agg_all['union_escape']} "
                           f"({agg_all['union_caught']}/33 caught); all 7 catches are WCC-arm R03-only "
                           "and therefore spurious.",
                           "No pinned canonical, stage tool, fixture or preserved artifact moved during "
                           "the verification window.",
                           "Independence is process-level (fresh re-run from preserved bytes); the verifier "
                           "shares the worker-084 id with the executor, so this is not a third-party audit.",
                       ],
                       evidence_refs=[ref("artifacts/heldout/heldout-10/verify/verification.json", H["verification"]),
                                      ref("artifacts/heldout/heldout-10/verify/adjudication.json", H["adjudication"]),
                                      ref("artifacts/heldout/heldout-10/report.json",
                                          sha(ROOT / "artifacts/heldout/heldout-10/report.json"))],
                       note="review scope = reproducibility of the executed measurement; it does not accept "
                            "the corpus under strict H5 and sets no gate verdict"))

    claims = [
        ("AF-SCC-C2-VAC-GEN",
         f"Independent terminal re-run (W084-HELDOUT10-INDEP-01) of the preserved FORM-HELDOUT-10 corpus "
         f"at manifest#d026fec40fe4 / report#5629e2a69c86 / raw#b3480625da10 (live FROZEN rev29 "
         f"815e08079aef; C2 canonical e9a27996dfd3; stage tools 000e09e46b2f and c79d8ab8440a) reproduced "
         f"all 40 fixture verdicts and failed-rule lists exactly: C2 arm 13/13 mutants accepted by BOTH "
         f"stages, C2 union escape {agg_inf['union_escape']} (0/13 caught). The corpus is strict-H5 "
         f"INVALID (valid=false) because stage B rejects the untouched frozen WCC canonical on R03, "
         f"independently reproduced; this claim is confined to the informative C2 arm.",
         ["preserved fixture bytes are unmodified since the pre-registered manifest (40/40 hashes match)",
          "stage tool bytes and the five live pins were identical before and after the verification",
          "arm informative because the frozen C2 canonical is accepted by both stages",
          "worker-084 verifier did not author the scheme rules and did not build the corpus in this session"],
         "Re-run artifacts/heldout/heldout-10/verify/verify_heldout_10_independent.py at the recorded "
         "hashes: falsified if any C2 mutant is caught, any stage verdict or failed-rule list differs "
         "from raw_verdicts.json, any aggregate differs, or any pinned byte moved."),
        ("AF-SCC-C0-VAC-GEN",
         f"Independent terminal re-run (W084-HELDOUT10-INDEP-01) of the preserved FORM-HELDOUT-10 corpus "
         f"reproduced all 40 fixture verdicts and failed-rule lists exactly: C0 arm 13/13 mutants accepted "
         f"by BOTH stages, C0 union escape {agg_inf['union_escape']} (0/13 caught), including both "
         f"f0-binding-stale-hash mutants m32/m33. The corpus is strict-H5 INVALID (valid=false) for the "
         f"independently reproduced WCC R03 instrument defect; this claim is confined to the informative "
         f"C0 arm.",
         ["preserved fixture bytes are unmodified since the pre-registered manifest (40/40 hashes match)",
          "stage tool bytes and the five live pins were identical before and after the verification",
          "arm informative because the frozen C0 canonical is accepted by both stages",
          "worker-084 verifier did not author the scheme rules and did not build the corpus in this session"],
         "Re-run artifacts/heldout/heldout-10/verify/verify_heldout_10_independent.py at the recorded "
         "hashes: falsified if any C0 mutant is caught, any stage verdict or failed-rule list differs "
         "from raw_verdicts.json, any aggregate differs, or any pinned byte moved."),
        ("AF-WCC-VAC-GEN",
         "Independent terminal re-run (W084-HELDOUT10-INDEP-01) reproduced stage B c79d8ab8440a rejecting "
         "the untouched frozen WCC canonical schemas/af_wcc_vacuum.yaml#d9cebb9404b2 on R03 only "
         "(literal-substring binder '(q,t0)' absent from the formal sentence), before and after the "
         "preserved run. All 7 WCC-arm stage-B catches in the corpus are R03-only and spurious; the WCC "
         "arm is non-informative and strict H5 is false for this pre-registered instrument reason alone.",
         ["the canonical WCC bytes d9cebb9404b2 are unchanged across the preserved run and the verification",
          "R03 is the only failed rule in every WCC catch and in the canonical control",
          "the calibration defect was recorded in the manifest before the corpus was frozen"],
         "A stage-B revision at c79d8ab8440a that accepts d9cebb9404b2, or a re-run in which any WCC "
         "catch fails a rule other than R03, falsifies this calibration finding."),
    ]
    for i, (class_id, statement, assumptions, falsifier) in enumerate(claims, start=7):
        events.append(dict(common, event_id=f"w084-ind10-{stamp}-{i:02d}-claim-reproduction",
                           event_type="claim", created_at=created, class_id=class_id,
                           statement=statement, conclusion_type="numerical_evidence",
                           assumptions=assumptions, falsifier=falsifier,
                           evidence_refs=[ref("artifacts/heldout/heldout-10/verify/verification.json", H["verification"]),
                                          ref("artifacts/heldout/heldout-10/verify/adjudication.json", H["adjudication"]),
                                          ref("artifacts/heldout/heldout-10/raw/raw_verdicts.json",
                                              sha(ROOT / "artifacts/heldout/heldout-10/raw/raw_verdicts.json"))],
                           artifact_refs=["artifacts/heldout/heldout-10/verify/verification.json",
                                          "artifacts/heldout/heldout-10/verify/adjudication.json"],
                           conclusion_type_note="worker measurement evidence only; not a theorem, not a gate verdict"))

    events.append(dict(common, event_id=f"w084-ind10-{stamp}-10-status-complete", event_type="status",
                       created_at=created, status="active", hours=0.7,
                       summary="W084-HELDOUT10-INDEP-01 complete: one bounded class-bound task, artifacts on "
                               "disk and hash-pinned, deterministic verifier, no drift. Terminal adjudication: "
                               f"reproducibility accept ({v['checks_passed']}/{v['checks_total']} checks; the "
                               "sole failure is the pre-registered strict-H5 control test); corpus_valid=false "
                               f"under strict H5; informative C2+C0 union escape {agg_inf['union_escape']} "
                               f"(0/{agg_inf['mutants']} caught). Worker completion claim only — does NOT set "
                               "node status, validation_status, or any gate verdict; Astra/leads own those.",
                       evidence_refs=[ref("artifacts/heldout/heldout-10/verify/verification.json", H["verification"]),
                                      ref("artifacts/heldout/heldout-10/verify/adjudication.json", H["adjudication"])],
                       next_falsifier="Stage-B R03 structural binder repair would remove the sole H5 failure "
                                      "and make the corpus re-runnable unchanged; a successor schema revision "
                                      "moves the pinned bytes and voids this verification."))

    for e in events:
        validate_event(e)          # fail closed before writing anything
    with OUTBOX.open("a") as f:
        for e in events:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    print(json.dumps({"emitted": len(events), "event_ids": [e["event_id"] for e in events],
                      "hashes": {k: h[:16] for k, h in H.items()}}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
