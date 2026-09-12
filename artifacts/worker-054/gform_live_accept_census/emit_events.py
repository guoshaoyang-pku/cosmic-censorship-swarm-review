#!/usr/bin/env python3
"""Emit W054-GFORM-LIVE-ACCEPT-CENSUS-01 protocol events + worker checkpoint.

Writes:
  comms/outbox/worker-054.jsonl                       (append, duplicate-safe)
  runtime/state/w054_gform_live_accept_census_checkpoint.json
  artifacts/worker-054/gform_live_accept_census/SHA256SUMS   (regenerated)

Does not touch canonical research artifacts.  Workers cannot set gate verdicts,
node status=done or validation_status=passed; the events say so explicitly.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
CST = timezone(timedelta(hours=8))
TASK = "W054-GFORM-LIVE-ACCEPT-CENSUS-01"
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
NODE = "F1,F2a,F2b"
GATE = "G-FORM"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    created = sys.argv[1] if len(sys.argv) > 1 else datetime.now(CST).isoformat(timespec="seconds")
    files = ["checker.py", "report.json", "census.json", "README.md", "emit_events.py"]
    hashes = {f: sha(OUT / f) for f in files}
    (OUT / "SHA256SUMS").write_text(
        "\n".join(f"{hashes[f]}  {f}" for f in files) + "\n")
    sums_sha = sha(OUT / "SHA256SUMS")
    report = json.loads((OUT / "report.json").read_text())

    A = {
        "report": f"artifacts/worker-054/gform_live_accept_census/report.json#{hashes['report.json'][:12]}",
        "census": f"artifacts/worker-054/gform_live_accept_census/census.json#{hashes['census.json'][:12]}",
        "checker": f"artifacts/worker-054/gform_live_accept_census/checker.py#{hashes['checker.py'][:12]}",
        "readme": f"artifacts/worker-054/gform_live_accept_census/README.md#{hashes['README.md'][:12]}",
        "sums": f"artifacts/worker-054/gform_live_accept_census/SHA256SUMS#{sums_sha[:12]}",
        "emitter": f"artifacts/worker-054/gform_live_accept_census/emit_events.py#{hashes['emit_events.py'][:12]}",
        "f1": "schemas/af_wcc_vacuum.yaml#d9cebb9404b2",
        "f2a": "schemas/af_scc_c2_vacuum.yaml#e9a27996dfd3",
        "f2b": "schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe",
        "frozen": "artifacts/formulation/FROZEN.json#815e08079aef",
        "r072": "reviews/F2b-review-worker-072-rev29.json#5db91bb0781d",
        "r071": "reviews/F2b-review-rev13-worker-071.json#e5a313894f7c",
        "r090": "reviews/F2b-rev13-full-090.json#345f74bb73f4",
        "r052b": "reviews/F2b-review-rev13-052.json#c3f720292e47",
        "r018": "reviews/F2a-review-18-rev13.json#53ed7b7ab385",
        "r085a": "reviews/F2a-review-rev29-085.json#b86ce67c4c0b",
        "r017": "reviews/F2a-review-worker-017.json#61cbd185f982",
        "r075f1": "reviews/F1-review-rev29-075.json#9276f4b41547",
        "r072f1": "reviews/F1-review-worker-072-rev13.json#c656cc819381",
        "r089": "reviews/F1-review-worker-089.json#9a4bb3f3268c",
        "w48": "artifacts/worker-048/gform_coverage_recount/report.json#53faf0cccd1d",
        "w59": "artifacts/worker-059/gform_frozen_gen_census/report.json#1893028ee4ab",
    }
    ev = {
        "report": f"w054-gformcov-{created}-artifact-report",
        "census": f"w054-gformcov-{created}-artifact-census",
        "checker": f"w054-gformcov-{created}-artifact-checker",
        "readme": f"w054-gformcov-{created}-artifact-readme",
        "sums": f"w054-gformcov-{created}-artifact-sums",
        "emitter": f"w054-gformcov-{created}-artifact-emitter",
        "claim": f"w054-gformcov-{created}-claim",
        "review": f"w054-gformcov-{created}-review",
        "status_task": f"w054-gformcov-{created}-status-task",
        "status_done": f"w054-gformcov-{created}-status-complete",
    }
    common = {"actor": "worker-054", "class_ids": CLASS_IDS, "node_id": NODE, "gate": GATE,
              "created_at": created, "task_id": TASK}

    events = [
        dict(common, event_id=ev["report"], event_type="artifact",
             artifact_type="measurement_report", path=A["report"].split("#")[0],
             sha256=hashes["report.json"], validation_status="unverified",
             summary="Live G-FORM accept-coverage census at the rev13/rev29 pins: for every "
                     "review file in reviews/ (230 scanned, 12/12 controls, zero drift), the "
                     "declared target hash, full-schema flag, live-FROZEN declaration, author-set "
                     "independence and verdict are classified under pre-registered rules; all four "
                     "count variants per leg are reported."),
        dict(common, event_id=ev["census"], event_type="artifact",
             artifact_type="census_table", path=A["census"].split("#")[0],
             sha256=hashes["census.json"], validation_status="unverified",
             summary="Machine census: per-file sha256, scope reason, declared/stale hashes, "
                     "verdict, full flag, FROZEN generation, reviewer and non-author flag, plus "
                     "the frozen pin set."),
        dict(common, event_id=ev["checker"], event_type="artifact",
             artifact_type="measurement_instrument", path=A["checker"].split("#")[0],
             sha256=hashes["checker.py"], validation_status="unverified",
             summary="Deterministic read-only instrument (python3 checker.py --created-at "
                     f"{created}); 12 planted controls, fail-closed exit 2 on drift or control "
                     "deviation."),
        dict(common, event_id=ev["readme"], event_type="artifact", artifact_type="summary",
             path=A["readme"].split("#")[0], sha256=hashes["README.md"],
             validation_status="unverified",
             summary="One-page rendering generated from report.json: per-leg counts, counted "
                     "files, the worker-072 self-supersession record, the worker-017 HF-059 "
                     "check, controls and non-claims."),
        dict(common, event_id=ev["sums"], event_type="artifact", artifact_type="artifact_manifest",
             path=A["sums"].split("#")[0], sha256=sums_sha, validation_status="unverified",
             summary="SHA256SUMS over checker.py, report.json, census.json, README.md, "
                     "emit_events.py."),
        dict(common, event_id=ev["emitter"], event_type="artifact", artifact_type="event_emitter",
             path=A["emitter"].split("#")[0], sha256=hashes["emit_events.py"],
             validation_status="unverified",
             summary="Reproducible emitter of these events and of the worker-local checkpoint."),
        dict(common, event_id=ev["claim"], event_type="claim", conclusion_type="formal_model",
             statement=(
                 "At the live G-FORM pins (F1 d9cebb9404b2, F2a e9a27996dfd3, F2b b2ab6acb2bbe, "
                 "FROZEN rev29 815e08079aef) the machine census finds exactly two strict "
                 "full-schema non-author accepts bound to both the live schema hash and the live "
                 "FROZEN generation on each leg: F1 = F1-review-rev29-075 + "
                 "F1-review-worker-072-rev13; F2a = F2a-review-18-rev13 + F2a-review-rev29-085; "
                 "F2b = F2b-rev13-full-090 + F2b-review-rev13-worker-071. Two record corrections: "
                 "(i) reviews/F2b-review-worker-072-rev29.json self-superseded its 01:10:13 accept "
                 "to revise at 01:14:51 (supersedes 7487f310d208) with blocking W072-F2B-HF-01/02, "
                 "so the 01:12 W48 recount 'F2b 2 = 090,072' is stale and the live pair is "
                 "(090,071); (ii) worker-059's HF-059-FROZEN-01 is independently confirmed: "
                 "reviews/F2a-review-worker-017.json accepts the live F2a schema hash but declares "
                 "FROZEN generation A 3d9e3d77, not live 815e0807, and F2a reaches two strict "
                 "live-FROZEN accepts without it. Coverage counts are not adjudication: F2b also "
                 "carries 13 live-bound revise verdicts and F2a 4, so which verdicts stand remains "
                 "the audit lead's call."),
             assumptions=[
                 "A review belongs to a leg only by node_id/target_id/reviewed_path identity; a "
                 "cross-mention of another leg's schema in findings or notes creates no scope.",
                 "counts_as_full_schema_verdict absent defaults to full for an accept verdict "
                 "(controller default documented in W48-CR-F3); STRICT and DEFAULT are both reported.",
                 "A live-FROZEN declaration is a full hash, a FROZEN.json#hash reference, or an "
                 "8+ hex prefix of 815e0807; the strict structured variant is reported separately "
                 "(frozen_live_structured).",
                 "non-author = reviewer absent from the artifact-author set derived from accepted "
                 "artifact events for that leg's canonical/mirror path (F1 {astra, "
                 "astra-lead-formulation, deepseek-flash-03}; F2a {astra-lead-formulation, "
                 "deepseek-flash-05}; F2b {astra-lead-formulation, deepseek-flash-06, worker-008, "
                 "worker-020, worker-083}).",
                 "reviews/*.json is mutable; every classified file carries its measured sha256 and "
                 "later writes are new revisions to re-census, not falsifiers of a past measurement.",
                 "Worker events cannot set status=done, validation_status=passed, or a gate verdict.",
             ],
             evidence_refs=[A["report"], A["census"], A["checker"], A["f1"], A["f2a"], A["f2b"],
                            A["frozen"], A["r072"], A["r071"], A["r090"], A["r018"], A["r085a"],
                            A["r017"], A["r075f1"], A["r072f1"], A["r089"], A["w48"], A["w59"]],
             artifact_refs=[A["report"], A["census"], A["checker"], A["readme"], A["sums"]],
             falsifier=report["falsifier"]),
        dict(common, event_id=ev["review"], event_type="review",
             target_id=ev["report"], reviewed_artifact=ev["report"], reviewer="worker-054",
             verdict="accept", score=4.5, hard_failures=[],
             counts_as_full_schema_verdict=False, counts_toward_gate_accept=False,
             counts_as_independent_verdict=False,
             review_scope="self-review of the worker deliverable only (instrument validity, rule "
                          "pre-registration, controls, pin discipline, replayability); NOT an "
                          "F1/F2a/F2b schema verdict, NOT a gate verdict, NOT an acceptance or "
                          "rejection of any review verdict counted",
             evidence_refs=[A["report"], A["census"], A["checker"], A["readme"], A["sums"]],
             findings=[
                 "F-054-C1: under the strictest rule (accept + strict full + live schema + live "
                 "FROZEN + non-author) each of F1/F2a/F2b has exactly 2 files; the gate's count "
                 "criterion is met at live bytes, subject to the audit lead's independence and "
                 "adjudication call.",
                 "F-054-C2: reviews/F2b-review-worker-072-rev29.json moved accept -> revise at "
                 "01:14:51 (sha256 5db91bb0781d, supersedes 7487f310d208, blocking "
                 "W072-F2B-HF-01/02); any coverage number computed before that instant, including "
                 "the 01:12 W48 recount 'F2b 2 = 090,072', is stale at live bytes.",
                 "F-054-C3: HF-059-FROZEN-01 independently reproduced: F2a-review-worker-017 "
                 "accepts live F2a e9a27996 but its only FROZEN reference is generation A "
                 "3d9e3d77; it is no longer pivotal because F2a has 2 strict live-FROZEN accepts "
                 "(F2a-review-18-rev13 01:10:43, F2a-review-rev29-085).",
                 "F-054-C4: target normalization matters: F1-review-worker-089 (target_id "
                 "path#hash, counts flag absent) is a live-bound accept that a path-prefix-only "
                 "scan drops; controls C5a/C5b/C9/C10 pin the behavior.",
                 "F-054-C5: F2b carries 13 live-bound revise verdicts against 2 strict live "
                 "accepts and F2a 4 revises against 4 strict accepts: coverage is satisfied, "
                 "verdict sufficiency is contested and unresolved by this measurement.",
                 "F-054-C6: three review files (F1-review-rev13-085, F2a-review-rev29-085, "
                 "F2b-review-rev13-052) carry no created_at / no explicit full flag; they are "
                 "counted only under the documented default rule and are flagged in census.json.",
             ],
             next_falsifier="Re-run checker.py at --created-at " + created + " on unchanged bytes; "
                            "any changed classification, control or input hash falsifies the "
                            "measurement."),
        dict(common, event_id=ev["status_task"], event_type="status", status="active", hours=0.3,
             summary="Task taken (no inbox card exists for worker-054; self-selected, one bounded "
                     "class-bound task): W054-GFORM-LIVE-ACCEPT-CENSUS-01 at F1/F2a/F2b, G-FORM. "
                     "Read-only; no canonical write.",
             evidence_refs=[A["report"], A["checker"]],
             next_falsifier="drift of any pinned input voids the census."),
        dict(common, event_id=ev["status_done"], event_type="status", status="active", hours=0.3,
             task_complete_pending_review=True,
             summary="CHECKPOINT + EXIT. W054-GFORM-LIVE-ACCEPT-CENSUS-01 complete at worker "
                     "level: 230 review files scanned, 12/12 controls as declared, zero input "
                     "drift, 0 files added/removed during the run. Strict live full-schema "
                     "accepts per leg = 2 (F1/F2a/F2b), all non-author; F2b live pair is now "
                     "(090,071) after the 072 self-supersession; HF-059 independently reproduced "
                     "and no longer pivotal. No gate verdict, no node status, no "
                     "validation_status=passed, no canonical artifact written.",
             evidence_refs=[A["report"], A["census"], A["checker"], A["readme"], A["sums"]],
             checkpoint_id="w054-ckpt-gform-live-accept-census-20260912T0125",
             next_falsifier=report["falsifier"]),
    ]

    outbox = ROOT / "comms" / "outbox" / "worker-054.jsonl"
    existing = set()
    if outbox.exists():
        for line in outbox.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                existing.add(json.loads(line).get("event_id"))
            except Exception:
                continue
    new = [e for e in events if e["event_id"] not in existing]
    with outbox.open("a", encoding="utf-8") as fh:
        for e in new:
            fh.write(json.dumps(e, sort_keys=True) + "\n")

    ckpt = {
        "checkpoint_id": "w054-ckpt-gform-live-accept-census-20260912T0125",
        "actor": "worker-054",
        "created_at": created,
        "task_id": TASK,
        "status": "complete_at_worker_level",
        "pins": {k: v["sha256"] for k, v in report["pins"].items()},
        "verdict_summary": report["verdict_summary"],
        "controls_all_as_declared": report["controls_all_as_declared"],
        "drift_detected": report["drift_detected"],
        "artifact_hashes": {f: hashes[f] for f in files},
        "sha256sums_sha256": sums_sha,
        "events_emitted": [e["event_id"] for e in new],
        "not_claimed": ["no gate verdict", "no node status", "no validation_status=passed",
                        "no canonical artifact written", "no schema review verdict authored"],
        "next_falsifier": report["falsifier"],
    }
    (ROOT / "runtime" / "state" / "w054_gform_live_accept_census_checkpoint.json").write_text(
        json.dumps(ckpt, indent=1, sort_keys=True) + "\n")

    print(json.dumps({"emitted": [e["event_id"] for e in new],
                      "skipped_duplicates": [e["event_id"] for e in events if e["event_id"] in existing],
                      "checkpoint": ckpt["checkpoint_id"],
                      "outbox": str(outbox)}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
