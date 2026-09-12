#!/usr/bin/env python3
"""Emit W084-R03V2-SCOPE-INDEP-01 upward events to comms/outbox/worker-084.jsonl.

Every event is validated against research_map/schemas.py before it is appended
(PROTOCOL rule 5: reject your own output before sending). Append-only; no other
writer surface is touched.
"""
from __future__ import annotations
import datetime, hashlib, json, os, sys

ROOT = "/data3/guoshaoyang/workdir/ai4math-swarm"
TASK = os.path.join(ROOT, "artifacts/worker-084/r03v2_scope_indep")
OUTBOX = os.path.join(ROOT, "comms/outbox/worker-084.jsonl")
sys.path.insert(0, ROOT)
from research_map.schemas import validate_event  # noqa: E402


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def h(rel):
    return sha(os.path.join(ROOT, rel))


now = datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()
tag = "w084-r03v2indep-" + datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
P = {rel: h(rel) for rel in [
    "artifacts/worker-084/r03v2_scope_indep/PREREGISTRATION.json",
    "artifacts/worker-084/r03v2_scope_indep/report.json",
    "artifacts/worker-084/r03v2_scope_indep/reproduction.json",
    "artifacts/worker-084/r03v2_scope_indep/determinism.json",
    "artifacts/worker-084/r03v2_scope_indep/findings.json",
    "artifacts/worker-084/r03v2_scope_indep/REVIEW.md",
    "artifacts/worker-084/r03v2_scope_indep/CHECKPOINT.json",
    "artifacts/worker-084/r03v2_scope_indep/MANIFEST.json",
    "artifacts/worker-06/r03scope/report.json",
    "artifacts/worker-06/r03scope/raw_verdicts.json",
    "artifacts/worker-06/r03scope/fixture_manifest.json",
]}
B = "artifacts/worker-084/r03v2_scope_indep/"
E = []


def add(**kw):
    E.append(kw)


common = dict(actor="worker-084", task_id="W084-R03V2-SCOPE-INDEP-01", node_id="A1",
              gate="G-CLASSBIND", class_id="AF-WCC-VAC-GEN",
              class_ids=["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"])

add(event_id=f"{tag}-01-status-task", event_type="status", created_at=now, **common,
    status="active", hours=0.1,
    summary="One bounded class-bound task taken, no inbox card: W084-R03V2-SCOPE-INDEP-01, independent non-author non-owner reproduction and adjudication of W006-R03-SCOPE-01 (stage-B R03 scope-safety corpus) at its published pins. Read-only on all subject bytes; preregistration written and hashed before any tool was run.",
    evidence_refs=[f"{B}PREREGISTRATION.json#sha256:{P[B+'PREREGISTRATION.json'][:12]}"],
    next_falsifier="Any pinned byte moving, any of the 88 cells disagreeing with the published raw verdicts, or a fixture hash mismatch.")

for rel, label in [
    (B + "PREREGISTRATION.json", "preregistration"),
    (B + "reproduction.json", "reproduction-matrix"),
    (B + "determinism.json", "second-pass-determinism"),
    (B + "report.json", "adjudication-report"),
    (B + "CHECKPOINT.json", "checkpoint"),
]:
    add(event_id=f"{tag}-02-artifact-{label}", event_type="artifact", created_at=now, **common,
        artifact_type=label, path=rel, sha256=P[rel], validation_status="unverified",
        evidence_refs=[f"{rel}#sha256:{P[rel][:12]}"])

add(event_id=f"{tag}-03-claim-reproduction", event_type="claim", created_at=now, **common,
    conclusion_type="numerical_evidence",
    assumption_note="measurement reproduction only; no rule re-implementation",
    assumptions=[
        "all 14 pinned subject/canonical bytes are stable before and after both passes (verified 14/14)",
        "the verifier's own PREREGISTRATION.json labels and literal-token oracle were fixed before any fixture was run",
        "tools are executed as subprocesses and compared on returncode, verdict, failed_rules and doc_sha256",
        "W006-R03-SCOPE-01 is the object under test; its declared expectations and raw verdicts are not trusted as inputs",
    ],
    statement="Independent non-author, non-owner reproduction of W006-R03-SCOPE-01 at its published pins: 88/88 cells (4 candidates x 19 fixtures + 3 canonicals) agree with the published raw_verdicts.json e81f7818d026/33ab1e03e690 on returncode, verdict, failed_rules and doc_sha256; a second pass reproduces all 88 cells with 0 field differences; the verifier's independently re-derived labels agree 19/19 and the frozen literal '(q,t0)' oracle agrees 19/19; the declared-expectation matrix reproduces 76/76 with 0 deviations; every mutant changes only quantifiers.formal; frozen rejects the canonical WCC on exactly R03 while cand_r03v2 e41a4b23a840, cand_004 645eb16a0060 and cand_E3 3f69bc1eb27a accept all three live canonicals; recomputed headline frozen FP4/FN2, cand_r03v2 FP0/FN0, cand_004 FP0/FN7, cand_E3 FP0/FN8 matches the published claim; no non-R03 failed rule occurred in any cell. Adjudication verdict: accept. One minor wording finding: cand_r03v2's edge over-reject residue is 4/4 unscored edge probes, not the two named in the claim (all four manifest-declared, so 0 expectation deviations).",
    artifact_refs=[B + "report.json", B + "reproduction.json", B + "determinism.json"],
    evidence_refs=[f"{B}report.json#sha256:{P[B+'report.json'][:12]}",
                   f"{B}reproduction.json#sha256:{P[B+'reproduction.json'][:12]}",
                   f"{B}determinism.json#sha256:{P[B+'determinism.json'][:12]}",
                   "artifacts/worker-06/r03scope/report.json#sha256:e81f7818d026"],
    falsifier="A later held-out scope corpus on which cand_r03v2 accepts a genuine scope error or rejects a correct rendering; any of the 88 cells disagreeing on a third pass; a pinned byte moving; or an adoption of cand_r03v2 without pinning stage-B e41a4b23a840 and rule module c572a033c054 in the same FROZEN revision.")

add(event_id=f"{tag}-04-review-subject", event_type="review", created_at=now, **common,
    target_id="W006-R03-SCOPE-01",
    target_artifact="artifacts/worker-06/r03scope/report.json",
    reviewed_sha256=P["artifacts/worker-06/r03scope/report.json"],
    reviewer="worker-084", verdict="accept", score=4.5, hard_failures=[],
    independence_basis="non-author (worker-006), non-owner; no worker-006 code imported; labels and oracle pre-registered before execution",
    counts_as_independent_second_verdict=True,
    counts_as_full_schema_verdict=False,
    findings=[
        "88/88 cells reproduce exactly on returncode/verdict/failed_rules/doc_sha256; second pass 88/88 deterministic.",
        "Labels independently re-derived 19/19; frozen literal oracle 19/19; declared matrix 76/76 with 0 deviations.",
        "Headline counts independently recomputed and confirmed: frozen FP4/FN2; cand_r03v2 FP0/FN0; cand_004 FP0/FN7; cand_E3 FP0/FN8.",
        "F-084-R03V2-03 (minor): cand_r03v2 rejects 4/4 edge probes, not the two named in the claim; no scored cell affected.",
        "F-084-R03V2-04: scope-safety holds on one class / one slot / one rule family / 14 scored cells only.",
        "F-084-R03V2-05: stage-B is unpinned in FROZEN rev29; adoption must pin tool e41a4b23a840 and rule module c572a033c054 in the same revision.",
    ],
    evidence_refs=[f"{B}report.json#sha256:{P[B+'report.json'][:12]}",
                   f"{B}findings.json#sha256:{P[B+'findings.json'][:12]}",
                   "artifacts/worker-06/r03scope/raw_verdicts.json#sha256:33ab1e03e690"])

add(event_id=f"{tag}-05-status-complete", event_type="status", created_at=now, **common,
    status="active", hours=0.6,
    summary="CHECKPOINT + EXIT (worker-084, W084-R03V2-SCOPE-INDEP-01). One bounded class-bound task complete at worker level: independent reproduction of W006-R03-SCOPE-01 verdict ACCEPT (88/88 cells, deterministic second pass, labels 19/19, oracle 19/19, declared matrix 76/76, pins 14/14 stable, 0 non-R03 failures, headline counts confirmed). One minor wording finding (edge residue 4/4) and one governance note (pin stage-B on adoption). No canonical artifact, tool, fixture or published report written. No node completion, no gate verdict, no theorem, no adoption recommendation; worker exits for recycling.",
    evidence_refs=[f"{B}CHECKPOINT.json#sha256:{P[B+'CHECKPOINT.json'][:12]}",
                   f"{B}report.json#sha256:{P[B+'report.json'][:12]}",
                   f"{B}MANIFEST.json#sha256:{P[B+'MANIFEST.json'][:12]}"],
    next_falsifier="A later held-out scope corpus on which cand_r03v2 accepts a genuine scope error or rejects a correct rendering; a third-pass verdict change; or an adoption of cand_r03v2 without a same-revision FROZEN pin of stage-B e41a4b23a840 / rule module c572a033c054.")

# validate then append
lines = []
for e in E:
    try:
        validate_event(e)
    except Exception as exc:
        print("SCHEMA REJECT", e.get("event_id"), exc)
        sys.exit(2)
    lines.append(json.dumps(e, ensure_ascii=False))
with open(OUTBOX, "a", encoding="utf-8") as f:
    for ln in lines:
        f.write(ln + "\n")
print(f"emitted {len(lines)} validated events to {OUTBOX}")
print(json.dumps({"tag": tag, **{k: v[:12] for k, v in P.items() if k.startswith(B)}}, indent=1))
