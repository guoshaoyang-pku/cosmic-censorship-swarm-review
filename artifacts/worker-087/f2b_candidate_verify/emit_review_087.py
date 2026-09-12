#!/usr/bin/env python3
"""W087 emitter: writes report.json + REVIEW.json + checkpoint and appends the outbox events.

Writes only worker-owned paths plus the worker's own outbox line and the checkpoint under
runtime/state/. Never touches canonical schemas, FROZEN.json, the alias registry, evidence
documents, review files belonging to other agents, or the research map.
"""
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
W = ROOT / "artifacts/worker-087/f2b_candidate_verify"
sys.path.insert(0, str(ROOT))
from research_map.schemas import validate_event  # noqa: E402


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


NOW = datetime.now(timezone(timedelta(hours=8)))
NOW_ISO = NOW.isoformat(timespec="seconds")
TOK = NOW.strftime("%Y%m%dT%H%M%S")

INSTRUMENT = W / "verify_candidate_087.py"
RAW = W / "run1.json"
REPORT_MD = W / "REPORT.md"
REPORT = W / "report.json"
REVIEW = W / "REVIEW.json"
CKPT = ROOT / "runtime/state/worker-087_checkpoint_f2b_candidate_verify.json"
OUTBOX = ROOT / "comms/outbox/worker-087.jsonl"

CANON = ROOT / "schemas/af_scc_c0_vacuum.yaml"
CAND = ROOT / "artifacts/worker-088/f2b_rev13_blockers/candidate/af_scc_c0_vacuum.rev13repair.yaml"
CAND_EVID = ROOT / "artifacts/worker-088/f2b_rev13_blockers/candidate/artifacts/formulation/evidence/taxonomy_consistency.json"
CANON_EVID = ROOT / "artifacts/formulation/evidence/taxonomy_consistency.json"
FROZEN = ROOT / "artifacts/formulation/FROZEN.json"
VOCAB = ROOT / "artifacts/formulation/VOCAB_ALIASES.json"
MANIFEST = ROOT / "artifacts/worker-088/f2b_rev13_blockers/candidate/MANIFEST.json"

raw = json.loads(RAW.read_text())
assert raw["verdict"].startswith("accept_packet_conditional"), raw["verdict"]
assert raw["controls_all_pass"] and raw["drift_free"] and raw["diff"]["unexpected_count"] == 0

hashes = {str(p.relative_to(ROOT)): sha(p) for p in
          [CANON, CAND, CAND_EVID, CANON_EVID, FROZEN, VOCAB, MANIFEST, INSTRUMENT, RAW, REPORT_MD]}
CAND_SHA = hashes["artifacts/worker-088/f2b_rev13_blockers/candidate/af_scc_c0_vacuum.rev13repair.yaml"]
CANON_SHA = hashes["schemas/af_scc_c0_vacuum.yaml"]

FINDINGS = [
    {"id": "W087-F2B-01", "severity": "verified", "status": "closed_by_candidate",
     "finding": "Canonical B1/B2 defects reproduce at b2ab6acb2bbe with this worker's own detectors (4/4 mutation controls fire): forbidden_transfers[0].reason calls C2 'strictly larger' against the file's own chain, and regularity.must_not_conflate[0] carries the stale 'No containment with C2 or C0 is asserted here' denial. The candidate clears both; its containment sentence agrees with the F2a sibling's settled correction (schemas/af_scc_c2_vacuum.yaml:152) and its 'strictly between' token appears only inside the ban, so it does NOT repeat the REP-CD-02 wording defect worker-100 measured in the competing worker-022 candidate (artifacts/worker-100/f2b_candidate_verify/report.json HF-W100-02)."},
    {"id": "W087-F2B-02", "severity": "conditional-hard-for-landing", "status": "open",
     "finding": "Landing condition: the candidate SCHEMA ALONE placed at schemas/af_scc_c0_vacuum.yaml declares f0_binding.consistency_evidence_sha256 = a03ba9c529e88e0d at path artifacts/formulation/evidence/taxonomy_consistency.json, whose live bytes are 9e335e9ba1bfcf77 -> declared hash fails to resolve at the declared path. Packet mode (candidate root applied to repo root, schema + evidence together) resolves a03ba9c5 and passes B4. Owner must land the two files atomically and update artifacts/formulation/tools/check_taxonomy_consistency.py to emit the three input hashes, as the candidate's own generator note states; FROZEN then moves to a new revision and all rev13 verdicts are void."},
    {"id": "W087-F2B-03", "severity": "open-dependency", "status": "not-discharged",
     "finding": "B3 is bound, not adjudicated: the candidate binds VOCAB_ALIASES.json = 46cd9f1eb534 (measured, matches) and both declared aliases are members of their registry lists, but the two tokens (conclusion_type=scc_c0_future_inextendibility and genericity.kind=residual_comeager) remain non-literal members of the frozen F0 allowed lists. The candidate itself flags owner_adjudication_required; literal-membership detectors still flag until the owner rules which list is operative. This is an instrument-policy decision, not a candidate defect."},
    {"id": "W087-F2B-04", "severity": "info", "status": "measurement",
     "finding": "The canonical class-schema checker artifacts/formulation/tools/check_class_schema.py returns pass (rc=0, failed_rules=[]) on BOTH the canonical bytes and the candidate, so it does not discriminate B1/B2; the repair's acceptance evidence must cite the B1-B4 detectors, not the checker exit code."},
    {"id": "W087-F2B-05", "severity": "info", "status": "measurement",
     "finding": "Scope integrity: 0 unexpected leaf-path diffs between canonical and candidate; class_id/node_id/schema_version/scope_statement/quantifiers/topology/conclusion statements/anti_scope are byte-equal; 4/4 mutation controls fire; all 8 pins re-measured before and after the run with zero drift."},
]

report = {
    "task_id": "W087-F2B-CANDIDATE-INDEP-VERIFY-01",
    "actor": "worker-087",
    "role": "independent verification of a worker repair candidate; read-only; no canonical write; no gate verdict",
    "node_id": "F2b",
    "class_id": "AF-SCC-C0-VAC-GEN",
    "class_ids": ["AF-SCC-C0-VAC-GEN"],
    "gate": "G-FORM",
    "created_at": NOW_ISO,
    "candidate": {"path": str(CAND.relative_to(ROOT)), "sha256": CAND_SHA,
                  "packet_evidence": {"path": str(CAND_EVID.relative_to(ROOT)),
                                      "sha256": hashes[str(CAND_EVID.relative_to(ROOT))]},
                  "manifest": {"path": str(MANIFEST.relative_to(ROOT)),
                               "sha256": hashes[str(MANIFEST.relative_to(ROOT))]}},
    "canonical": {"path": "schemas/af_scc_c0_vacuum.yaml", "sha256": CANON_SHA},
    "frozen": {"path": "artifacts/formulation/FROZEN.json",
               "sha256": hashes[str(FROZEN.relative_to(ROOT))], "revision": 29},
    "instrument": {"path": str(INSTRUMENT.relative_to(ROOT)), "sha256": hashes[str(INSTRUMENT.relative_to(ROOT))],
                   "raw_run": {"path": str(RAW.relative_to(ROOT)), "sha256": hashes[str(RAW.relative_to(ROOT))]}},
    "verdict": "accept",
    "verdict_scope": "candidate packet (schema + evidence landed together)",
    "score": 4.0,
    "counts_toward_gate_accept": False,
    "hard_failures": [],
    "conditional_hard_failures_for_schema_only_landing": ["W087-HF-LAND-01"],
    "findings": FINDINGS,
    "facts": raw["facts"],
    "controls": raw["controls"],
    "pins": raw["pins"],
    "drift_free": raw["drift_free"],
    "diff": raw["diff"],
    "identity_all_preserved": raw["identity_all_preserved"],
    "checker": raw["checker"],
    "assumptions": [
        "the candidate directory root maps onto the repository root at landing time (schema -> schemas/, evidence -> artifacts/formulation/evidence/); a schema-only landing is explicitly out of scope and fails W087-F2B-02",
        "B1/B2 are read as normative content of the frozen artifact per worker-036's two-defect adjudication and the F2a sibling's settled correction",
        "the alias registry is accepted only as a bound equivalence table until the owner adjudicates literal F0 membership (W087-F2B-03)",
    ],
    "falsifier": ("Re-run verify_candidate_087.py at the same eight pins: any pin move, any changed detector "
                  "verdict, a packet whose declared evidence hash fails to resolve inside the packet, or a "
                  "schema-only landing whose declared hash does not resolve at the declared path voids this "
                  "verification. A containment-respecting reading with E_C2 strictly larger than E_C0, or a "
                  "reading in which canonical regularity.must_not_conflate[0] is not normative content, voids "
                  "the B1/B2 defect reproduction."),
    "reproduce": "python3 artifacts/worker-087/f2b_candidate_verify/verify_candidate_087.py",
    "authority": "worker measurement only; no gate verdict, no node status, no validation_status, no adoption of the candidate",
}
REPORT.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")

review = {
    "event_type": "review",
    "actor": "worker-087",
    "reviewer": "worker-087",
    "node_id": "F2b",
    "class_id": "AF-SCC-C0-VAC-GEN",
    "class_ids": ["AF-SCC-C0-VAC-GEN"],
    "gate": "G-FORM",
    "target_id": f"{CAND.relative_to(ROOT)}#{CAND_SHA[:12]}",
    "reviewed_path": str(CAND.relative_to(ROOT)),
    "reviewed_sha256": CAND_SHA,
    "verdict": "accept",
    "score": 4.0,
    "hard_failures": [],
    "conditional_hard_failures_for_schema_only_landing": ["W087-HF-LAND-01"],
    "findings": FINDINGS,
    "counts_toward_gate_accept": False,
    "scope_note": ("Independent verification of the worker-088 F2b rev13repair candidate PACKET. It is not a "
                   "full-schema verdict at a canonical pin and must not be counted as one of the two G-FORM "
                   "F2b accepts; the canonical bytes still carry the two reproduced content defects."),
    "artifact_refs": [f"{REPORT.relative_to(ROOT)}#sha256:{sha(REPORT)[:16]}",
                      f"{INSTRUMENT.relative_to(ROOT)}#sha256:{hashes[str(INSTRUMENT.relative_to(ROOT))][:16]}",
                      f"{RAW.relative_to(ROOT)}#sha256:{hashes[str(RAW.relative_to(ROOT))][:16]}"],
    "evidence_refs": [f"{CANON.relative_to(ROOT)}#sha256:{CANON_SHA[:12]}",
                      f"{CAND.relative_to(ROOT)}#sha256:{CAND_SHA[:12]}",
                      f"{CAND_EVID.relative_to(ROOT)}#sha256:{hashes[str(CAND_EVID.relative_to(ROOT))][:12]}",
                      f"{CANON_EVID.relative_to(ROOT)}#sha256:{hashes[str(CANON_EVID.relative_to(ROOT))][:12]}",
                      f"{FROZEN.relative_to(ROOT)}#sha256:{hashes[str(FROZEN.relative_to(ROOT))][:12]}",
                      f"{VOCAB.relative_to(ROOT)}#sha256:{hashes[str(VOCAB.relative_to(ROOT))][:12]}",
                      "artifacts/worker-100/f2b_candidate_verify/report.json",
                      "artifacts/worker-088/f2b_rev13_blockers/REPORT.md",
                      "artifacts/worker-036/f2b_containment_adjudication/report.json",
                      "schemas/af_scc_c2_vacuum.yaml:152"],
    "falsifier": report["falsifier"],
}
REVIEW.write_text(json.dumps(review, indent=1, sort_keys=True) + "\n")

checkpoint = {
    "task_id": "W087-F2B-CANDIDATE-INDEP-VERIFY-01",
    "actor": "worker-087",
    "slot": "087",
    "node_id": "F2b",
    "class_id": "AF-SCC-C0-VAC-GEN",
    "gate": "G-FORM",
    "created_at": NOW_ISO,
    "verdict": "accept (candidate packet; conditional landing)",
    "score": 4.0,
    "counts_toward_gate_accept": False,
    "pins": {k: v["sha256"] for k, v in raw["pins"].items()},
    "pins_drift_free": raw["drift_free"],
    "facts": raw["facts"],
    "controls": raw["controls"],
    "artifacts": {
        REPORT.name: sha(REPORT),
        REVIEW.name: sha(REVIEW),
        INSTRUMENT.name: sha(INSTRUMENT),
        RAW.name: sha(RAW),
        REPORT_MD.name: sha(REPORT_MD),
    },
    "checkpoint_state_copy": str(CKPT.relative_to(ROOT)),
    "open_conditions": [
        "land schema + evidence atomically and update check_taxonomy_consistency.py to emit the three input hashes (W087-F2B-02)",
        "owner adjudication of literal F0 membership vs bound alias registry for the two class tokens (W087-F2B-03)",
    ],
    "falsifier": report["falsifier"],
    "next_falsifier": ("a landing that drops the evidence file (declared hash a03ba9c5 fails to resolve at "
                       "artifacts/formulation/evidence/taxonomy_consistency.json), or a re-run at the same pins "
                       "with a changed verdict"),
    "authority_note": "worker checkpoint; no gate verdict, no node status, no validation_status promotion",
}
CKPT.write_text(json.dumps(checkpoint, indent=1, sort_keys=True) + "\n")

REPORT_SHA = sha(REPORT)
REVIEW_SHA = sha(REVIEW)
CKPT_SHA = sha(CKPT)
EVID_REFS = [
    f"artifacts/worker-088/f2b_rev13_blockers/candidate/af_scc_c0_vacuum.rev13repair.yaml#sha256:{CAND_SHA[:12]}",
    f"artifacts/worker-088/f2b_rev13_blockers/REPORT.md#sha256:{sha(ROOT / 'artifacts/worker-088/f2b_rev13_blockers/REPORT.md')[:12]}",
    f"artifacts/worker-088/f2b_rev13_blockers/candidate/artifacts/formulation/evidence/taxonomy_consistency.json#sha256:{hashes[str(CAND_EVID.relative_to(ROOT))][:12]}",
    f"schemas/af_scc_c0_vacuum.yaml#sha256:{CANON_SHA[:12]}",
    f"artifacts/formulation/evidence/taxonomy_consistency.json#sha256:{hashes[str(CANON_EVID.relative_to(ROOT))][:12]}",
    f"artifacts/formulation/FROZEN.json#sha256:{hashes[str(FROZEN.relative_to(ROOT))][:12]}",
    f"artifacts/formulation/VOCAB_ALIASES.json#sha256:{hashes[str(VOCAB.relative_to(ROOT))][:12]}",
    f"{REPORT.relative_to(ROOT)}#sha256:{REPORT_SHA[:12]}",
    f"{INSTRUMENT.relative_to(ROOT)}#sha256:{hashes[str(INSTRUMENT.relative_to(ROOT))][:12]}",
]
E = "w087-f2bcand-" + TOK


def ev(eid, typ, **kw):
    d = {"event_id": eid, "event_type": typ, "created_at": NOW_ISO, "actor": "worker-087"}
    d.update(kw)
    return d


events = [
    ev(E + "-status-claim", "status", node_id="F2b", status="active", hours=1.0,
       summary=("W087-F2B-CANDIDATE-INDEP-VERIFY-01 taken (no inbox card for slot 087): independent read-only "
                "verification of the only complete on-disk F2b rev13repair candidate packet b598b59e at FROZEN "
                "rev29 815e0807, because the formulation lead's lifecycle-07 records F2b as content-blocked "
                "(0 accept / 7 revise) and rev14 authorization needs an independent candidate check."),
       evidence_refs=EVID_REFS,
       next_falsifier=("a re-run at the eight pinned hashes with a changed detector verdict, or a packet whose "
                       "declared evidence hash fails to resolve inside the packet")),
    ev(E + "-artifact-instrument", "artifact", node_id="F2b", class_id="AF-SCC-C0-VAC-GEN",
       artifact_type="verification_instrument", path=str(INSTRUMENT.relative_to(ROOT)),
       sha256=hashes[str(INSTRUMENT.relative_to(ROOT))], validation_status="unverified",
       task_id="W087-F2B-CANDIDATE-INDEP-VERIFY-01", gate="G-FORM"),
    ev(E + "-artifact-raw-run", "artifact", node_id="F2b", class_id="AF-SCC-C0-VAC-GEN",
       artifact_type="verification_raw_run", path=str(RAW.relative_to(ROOT)),
       sha256=hashes[str(RAW.relative_to(ROOT))], validation_status="unverified",
       task_id="W087-F2B-CANDIDATE-INDEP-VERIFY-01", gate="G-FORM"),
    ev(E + "-artifact-report", "artifact", node_id="F2b", class_id="AF-SCC-C0-VAC-GEN",
       artifact_type="f2b_candidate_independent_verification", path=str(REPORT.relative_to(ROOT)),
       sha256=REPORT_SHA, validation_status="unverified",
       task_id="W087-F2B-CANDIDATE-INDEP-VERIFY-01", gate="G-FORM"),
    ev(E + "-artifact-report-md", "artifact", node_id="F2b", class_id="AF-SCC-C0-VAC-GEN",
       artifact_type="verification_report_md", path=str(REPORT_MD.relative_to(ROOT)),
       sha256=hashes[str(REPORT_MD.relative_to(ROOT))], validation_status="unverified",
       task_id="W087-F2B-CANDIDATE-INDEP-VERIFY-01", gate="G-FORM"),
    ev(E + "-artifact-checkpoint", "artifact", node_id="F2b", class_id="AF-SCC-C0-VAC-GEN",
       artifact_type="worker_checkpoint_state_copy", path=str(CKPT.relative_to(ROOT)),
       sha256=CKPT_SHA, validation_status="unverified",
       task_id="W087-F2B-CANDIDATE-INDEP-VERIFY-01", gate="G-FORM"),
    ev(E + "-review", "review", node_id="F2b", class_id="AF-SCC-C0-VAC-GEN",
       gate="G-FORM", target_id=review["target_id"], reviewed_path=review["reviewed_path"],
       reviewed_sha256=CAND_SHA, reviewer="worker-087", verdict="accept", score=4.0,
       hard_failures=[], conditional_hard_failures_for_schema_only_landing=["W087-HF-LAND-01"],
       findings=FINDINGS, counts_toward_gate_accept=False, scope_note=review["scope_note"],
       evidence_refs=EVID_REFS, artifact_refs=review["artifact_refs"], falsifier=report["falsifier"]),
    ev(E + "-claim", "claim", node_id="F2b", class_id="AF-SCC-C0-VAC-GEN", class_ids=["AF-SCC-C0-VAC-GEN"],
       gate="G-FORM", conclusion_type="formal_model",
       statement=("Instrument/checker verification, not a mathematics or physics claim. At FROZEN rev29 815e0807, "
                  "the canonical F2b bytes b2ab6acb reproduce blocker families B1 (inverted containment premise), "
                  "B2 (stale containment denial), B3 (unbound vocabulary) and B4 (non-self-verifying consistency "
                  "evidence); the worker-088 candidate packet b598b59e clears B1/B2, binds VOCAB_ALIASES.json "
                  "46cd9f1e for B3 with owner adjudication flagged, and carries self-verifying evidence a03ba9c5 "
                  "for B4. Scope integrity: 0 unexpected leaf diffs, class identity fields byte-equal, 4/4 "
                  "mutation controls fire, 8/8 pins drift-free. Conditional finding W087-F2B-02: the candidate "
                  "schema alone at the canonical path declares consistency_evidence_sha256 a03ba9c5 while the "
                  "canonical evidence path holds 9e335e9b, so the packet must be landed atomically with the "
                  "generator update. No gate verdict, no adoption, and this is not a full-schema F2b accept."),
       assumptions=report["assumptions"], falsifier=report["falsifier"],
       evidence_refs=EVID_REFS, artifact_refs=review["artifact_refs"]),
    ev(E + "-blocker-landing", "blocker", node_id="F2b", class_id="AF-SCC-C0-VAC-GEN", gate="G-FORM",
       description=("Landing hazard measured, not a candidate defect: the rev13repair candidate schema declares "
                    "f0_binding.consistency_evidence_sha256 = a03ba9c529e88e0d at artifacts/formulation/evidence/"
                    "taxonomy_consistency.json, whose live bytes are 9e335e9ba1bfcf77. A schema-only landing fails "
                    "the declared-hash chain; the packet only resolves when the candidate evidence copy lands "
                    "with it. The candidate's own generator note requires check_taxonomy_consistency.py to emit "
                    "the three input hashes."),
       needed_to_unblock=("Owner lands schema + evidence atomically under one authorized FROZEN revision (rev30), "
                          "updates check_taxonomy_consistency.py to emit map_taxonomy_sha256/lead_contract_sha256/"
                          "alias_registry_sha256, and re-measures the declared chain at the new canonical bytes; "
                          "or keeps the current evidence document and re-stamps to a hash published at the "
                          "declared path."),
       evidence_refs=EVID_REFS),
    ev(E + "-status-exit", "status", node_id="F2b", status="active", hours=1.0,
       summary=("W087-F2B-CANDIDATE-INDEP-VERIFY-01 complete at worker level: one bounded class-bound task, "
                "read-only, verdict accept (candidate packet; conditional), score 4.0, counts_toward_gate_accept "
                "false. Canonical F2b still carries the two reproduced content defects, so this does not convert "
                "F2b to accept and does not move G-FORM. Checkpoint written; EXIT."),
       evidence_refs=EVID_REFS,
       next_falsifier=("a landing that drops the evidence file, or a re-run of the instrument at the same pins "
                       "yielding a different verdict, or the canonical F2b bytes moving before rev14")),
]

for e in events:
    validate_event(e)

with open(OUTBOX, "a", encoding="utf-8") as fh:
    for e in events:
        fh.write(json.dumps(e, sort_keys=True) + "\n")

print(f"wrote {REPORT.relative_to(ROOT)} sha256={REPORT_SHA}")
print(f"wrote {REVIEW.relative_to(ROOT)} sha256={REVIEW_SHA}")
print(f"wrote {CKPT.relative_to(ROOT)} sha256={CKPT_SHA}")
print(f"appended {len(events)} events to {OUTBOX.relative_to(ROOT)} at {NOW_ISO}")
print("event_ids:")
for e in events:
    print("  ", e["event_id"])
