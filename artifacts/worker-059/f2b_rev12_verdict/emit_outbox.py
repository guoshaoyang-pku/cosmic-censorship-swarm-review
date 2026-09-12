#!/usr/bin/env python3
"""Append worker-059's F2b rev12 verdict events to comms/outbox/worker-059.jsonl.

Append-only (the lead's 00:36 truncation incident is the reason).  Verifies the
line count before/after and that canonical artifacts did not move.
"""
import datetime as dt
import hashlib
import json
from pathlib import Path

ROOT = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
D = ROOT / "artifacts/worker-059/f2b_rev12_verdict"
OUTBOX = ROOT / "comms/outbox/worker-059.jsonl"


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


now = dt.datetime.now().astimezone()
ts = now.isoformat(timespec="seconds")


def ref(path, digest):
    return f"{path}#{digest[:12]}"


snap_sha = sha(D / "snapshot/f2b.55d0a1ea9bda.yaml")
ev_sha = sha(D / "independent_evidence.json")
instr_sha = sha(D / "check_f2b_rev12.py")
adj_sha = sha(D / "consistency_adjudication.json")
rev_sha = sha(D / "review_F2b_55d0a1ea.json")
ckpt_sha = sha(D / "checkpoint_w059_f2b_rev12.json")

canon = {
    "schemas/af_scc_c0_vacuum.yaml": sha(ROOT / "schemas/af_scc_c0_vacuum.yaml"),
    "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml":
        sha(ROOT / "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"),
    "research_map/formulation_taxonomy.yaml":
        sha(ROOT / "research_map/formulation_taxonomy.yaml"),
    "artifacts/formulation/evidence/taxonomy_consistency.json":
        sha(ROOT / "artifacts/formulation/evidence/taxonomy_consistency.json"),
}

annex = {
    "artifact": "post-run drift annex",
    "task_id": "W059-F2B-REV12-VERDICT-01",
    "worker": "worker-059",
    "created_at": ts,
    "reviewed_sha256": snap_sha,
    "pinned_snapshot_sha256": snap_sha,
    "canonical_sha256_at_finalize": canon["schemas/af_scc_c0_vacuum.yaml"],
    "drift": canon["schemas/af_scc_c0_vacuum.yaml"] != snap_sha,
    "canonical_hashes_at_finalize": canon,
    "canonical_mtime":
        dt.datetime.fromtimestamp(
            (ROOT / "schemas/af_scc_c0_vacuum.yaml").stat().st_mtime).astimezone().isoformat(),
    "verdict_validity": "binding only while schemas/af_scc_c0_vacuum.yaml remains "
                        + snap_sha[:12],
    "artifacts": {
        "instrument_sha256": instr_sha, "evidence_sha256": ev_sha,
        "adjudication_sha256": adj_sha, "review_sha256": rev_sha,
        "checkpoint_sha256": ckpt_sha,
    },
}
(D / "postrun_annex.json").write_text(json.dumps(annex, indent=1, ensure_ascii=False) + "\n")
annex_sha = sha(D / "postrun_annex.json")
adj = json.loads((D / "consistency_adjudication.json").read_text())

falsifier = ("A F2b revision (or controller ruling) in which (i) f0_binding."
             "consistency_evidence_sha256 equals the measured bytes at the declared canonical "
             "evidence path, that path equals the FROZEN pin, and the canonical evidence embeds "
             "map_taxonomy_sha256=0abb9ed8 and lead_contract_sha256=d7419b4e; (ii) one governing "
             "conclusion-token registry is designated. Hash drift of schemas/af_scc_c0_vacuum.yaml "
             "voids this verdict (pinned 55d0a1ea9bda).")

events = []
e = {
    "event_id": f"w059-f2b-rev12-{ts.replace(':', '').replace('-', '')}-task-claim",
    "event_type": "status",
    "created_at": ts,
    "actor": "worker-059",
    "node_id": "F2b",
    "group_id": "formulation",
    "class_id": "AF-SCC-C0-VAC-GEN",
    "gate": "G-FORM",
    "status": "active",
    "hours": 0.4,
    "summary": "No inbox card exists for worker-059. Took ONE bounded class-bound task: "
               "W059-F2B-REV12-VERDICT-01 = independent full-schema verification of F2b rev12 "
               "at pinned sha256 55d0a1ea9bda, with closure-delta against the prior hard-finding "
               "set and drift-void. Own instrument (stdlib+PyYAML, no canonical-gate imports), "
               "34 checks, 24/24 single-defect mutants detected. Also adjudicates the "
               "consistency-evidence binding chain across F1/F2a/F2b. Does not claim node "
               "completion or any gate verdict.",
    "evidence_refs": [
        ref("artifacts/worker-059/f2b_rev12_verdict/review_F2b_55d0a1ea.json", rev_sha),
        ref("artifacts/worker-059/f2b_rev12_verdict/independent_evidence.json", ev_sha),
        ref("artifacts/worker-059/f2b_rev12_verdict/consistency_adjudication.json", adj_sha),
        ref("artifacts/worker-059/f2b_rev12_verdict/check_f2b_rev12.py", instr_sha),
        ref("artifacts/worker-059/f2b_rev12_verdict/snapshot/f2b.55d0a1ea9bda.yaml", snap_sha),
    ],
    "next_falsifier": falsifier,
}
events.append(e)

e = {
    "event_id": f"w059-f2b-rev12-{ts.replace(':', '').replace('-', '')}-artifact-evidence",
    "event_type": "artifact",
    "created_at": ts,
    "actor": "worker-059",
    "node_id": "F2b",
    "group_id": "formulation",
    "class_id": "AF-SCC-C0-VAC-GEN",
    "gate": "G-FORM",
    "artifact_type": "independent_measurement",
    "path": "artifacts/worker-059/f2b_rev12_verdict/independent_evidence.json",
    "sha256": ev_sha,
    "reviewed_sha256": snap_sha,
    "validation_status": "unverified",
    "evidence_refs": [ref("artifacts/worker-059/f2b_rev12_verdict/check_f2b_rev12.py", instr_sha)],
    "falsifier": "Re-running check_f2b_rev12.py on the pinned snapshot must reproduce every "
                 "recorded boolean and all 24 mutant detections; any difference falsifies this "
                 "evidence file.",
}
events.append(e)

e = {
    "event_id": f"w059-f2b-rev12-{ts.replace(':', '').replace('-', '')}-artifact-instrument",
    "event_type": "artifact",
    "created_at": ts,
    "actor": "worker-059",
    "node_id": "F2b",
    "group_id": "formulation",
    "class_id": "AF-SCC-C0-VAC-GEN",
    "gate": "G-FORM",
    "artifact_type": "review_instrument",
    "path": "artifacts/worker-059/f2b_rev12_verdict/check_f2b_rev12.py",
    "sha256": instr_sha,
    "validation_status": "unverified",
    "evidence_refs": [ref("artifacts/worker-059/f2b_rev12_verdict/independent_evidence.json", ev_sha)],
    "note": "Strict duplicate-key-rejecting loader, 34 named checks over one class-bound schema, "
            "24 deterministic single-defect mutants with per-mutant target-check sensitivity.",
    "falsifier": "A single-defect mutant in the recorded set that escapes its target check on "
                 "re-run, or a false positive on the unmodified pinned snapshot.",
}
events.append(e)

e = {
    "event_id": f"w059-f2b-rev12-{ts.replace(':', '').replace('-', '')}-artifact-adjudication",
    "event_type": "artifact",
    "created_at": ts,
    "actor": "worker-059",
    "node_id": "F2b",
    "group_id": "formulation",
    "class_id": "AF-SCC-C0-VAC-GEN",
    "gate": "G-FORM",
    "artifact_type": "consistency_adjudication",
    "path": "artifacts/worker-059/f2b_rev12_verdict/consistency_adjudication.json",
    "sha256": adj_sha,
    "reviewed_sha256": snap_sha,
    "validation_status": "unverified",
    "evidence_refs": [
        ref("artifacts/worker-059/f2b_rev12_verdict/sandbox_consistency/artifacts/formulation/evidence/taxonomy_consistency.json", sha(D / "sandbox_consistency/artifacts/formulation/evidence/taxonomy_consistency.json")),
        ref("artifacts/formulation/evidence/taxonomy_consistency.json", canon["artifacts/formulation/evidence/taxonomy_consistency.json"]),
        ref("artifacts/worker-086/gform_rev12/pinned/taxonomy_consistency.675a99d0d25b.json", sha(ROOT / "artifacts/worker-086/gform_rev12/pinned/taxonomy_consistency.675a99d0d25b.json")),
    ],
    "note": "Independent sandbox re-run of the canonical consistency tool on the current canonical "
            "trees exits 0, prints CONSISTENT (4 classes, 0 divergences), and is byte-identical to "
            "the canonical evidence file (9e335e9b). The schemas declare 675a99d0 (worker-086's "
            "out-of-tree enriched pin). Declaration is content-true and path-unbound.",
    "falsifier": adj["falsifier"],
}
events.append(e)

e = {
    "event_id": f"w059-f2b-rev12-{ts.replace(':', '').replace('-', '')}-artifact-review",
    "event_type": "artifact",
    "created_at": ts,
    "actor": "worker-059",
    "node_id": "F2b",
    "group_id": "formulation",
    "class_id": "AF-SCC-C0-VAC-GEN",
    "gate": "G-FORM",
    "artifact_type": "independent_review",
    "path": "artifacts/worker-059/f2b_rev12_verdict/review_F2b_55d0a1ea.json",
    "sha256": rev_sha,
    "reviewed_sha256": snap_sha,
    "validation_status": "unverified",
    "evidence_refs": [
        ref("artifacts/worker-059/f2b_rev12_verdict/independent_evidence.json", ev_sha),
        ref("artifacts/worker-059/f2b_rev12_verdict/consistency_adjudication.json", adj_sha),
    ],
    "falsifier": falsifier,
}
events.append(e)

e = {
    "event_id": f"w059-f2b-rev12-{ts.replace(':', '').replace('-', '')}-review",
    "event_type": "review",
    "created_at": ts,
    "actor": "worker-059",
    "reviewer": "worker-059",
    "target_id": "F2b",
    "target_path": "schemas/af_scc_c0_vacuum.yaml",
    "node_id": "F2b",
    "group_id": "formulation",
    "class_id": "AF-SCC-C0-VAC-GEN",
    "gate": "G-FORM",
    "reviewed_revision": 12,
    "reviewed_sha256": snap_sha,
    "artifact": "artifacts/worker-059/f2b_rev12_verdict/review_F2b_55d0a1ea.json",
    "sha256": rev_sha,
    "verdict": "revise",
    "score": 4.0,
    "counts_as_independent_verdict": True,
    "counts_as_full_schema_verdict": True,
    "counts_as_independent_second_verdict": False,
    "hard_failures": [
        "HF-059-F2B-01 (binding): f0_binding declares consistency_evidence_sha256=675a99d0 but "
        "the declared canonical path measures 9e335e9b and FROZEN rev28 pins 9e335e9b; 675a99d0 "
        "is worker-086's out-of-tree enriched pin and the canonical file embeds no compared-tree "
        "digests (checks B9/B10). Content independently reproduced true.",
        "HF-059-F2B-02 (registry conflict): canonical F0 rev5 stores the conclusion_type alias "
        "'strong_cosmic_censorship_C0' and lists aliases in field_vocabulary.conclusion_type."
        "allowed, while FROZEN-pinned VOCAB_ALIASES.json declares 'scc_c0_future_inextendibility' "
        "canonical and forbids aliases in new canonical artifacts; F2b is policy-compliant, the "
        "repair needs an F0 revision or a controller ruling.",
    ],
    "findings": [
        "Content surface green: 34 independent checks, 32 pass, 24/24 single-defect mutants "
        "detected; only the two binding items fail.",
        "Consistency adjudication: canonical tool re-run in sandbox reproduces the canonical "
        "evidence file byte-identically (9e335e9b, CONSISTENT, 0 divergences); enriched pin "
        "675a99d0 embeds map_taxonomy_sha256=0abb9ed8 and lead_contract_sha256=d7419b4e, both "
        "matching measurement. Fix = teach the canonical tool to embed the tree digests, "
        "regenerate, refresh the three declarations, re-freeze.",
        "Canonical gates corroborate: check_class_schema pass 0 failed rules; classsep_regression "
        "PASS 17/17, 10/10, FP/FN 0; validate_map VALID.",
        "Prior defect classes independently confirmed resolved at this hash: duplicate keys, "
        "future revised_at, cross-tree pointer, stale F0 hash, D0 tagged-union typing, clause (f) "
        "interior requirement, mirror divergence, FROZEN staleness.",
        "Advisory: l1_ledger_refs l1_status=accepted vs ledger verification_status='abstract-read' "
        "for D-002/T-301/T-515/T-528/T-302; advisory revision_history row 9 unused+out-of-order.",
    ],
    "evidence_refs": [
        ref("artifacts/worker-059/f2b_rev12_verdict/snapshot/f2b.55d0a1ea9bda.yaml", snap_sha),
        ref("artifacts/worker-059/f2b_rev12_verdict/independent_evidence.json", ev_sha),
        ref("artifacts/worker-059/f2b_rev12_verdict/consistency_adjudication.json", adj_sha),
        ref("artifacts/worker-059/f2b_rev12_verdict/check_f2b_rev12.py", instr_sha),
        ref("artifacts/worker-059/f2b_rev12_verdict/postrun_annex.json", annex_sha),
    ],
    "next_falsifier": falsifier,
    "validation_status": "unverified",
    "note": "Advisory worker verdict; cannot set gate verdict or node status. Semantics pass; "
            "binding/publication state fails.",
}
events.append(e)

e = {
    "event_id": f"w059-f2b-rev12-{ts.replace(':', '').replace('-', '')}-blocker",
    "event_type": "blocker",
    "created_at": ts,
    "actor": "worker-059",
    "node_id": "F2b",
    "group_id": "formulation",
    "class_id": "AF-SCC-C0-VAC-GEN",
    "gate": "G-FORM",
    "description": "A hash-bound accept for F2b at 55d0a1ea is blocked by two items. "
                   "HF-059-F2B-01: f0_binding.consistency_evidence_sha256 declares 675a99d0 "
                   "(worker-086's out-of-tree enriched pin) while the declared canonical path and "
                   "the FROZEN rev28 pin measure 9e335e9b; the canonical evidence file embeds no "
                   "compared-tree digests, so the declared consistency cannot be bound from "
                   "canonical artifacts. HF-059-F2B-02: the canonical F0 rev5 taxonomy stores the "
                   "conclusion_type alias 'strong_cosmic_censorship_C0' and lists aliases in "
                   "field_vocabulary.conclusion_type.allowed while VOCAB_ALIASES.json declares "
                   "'scc_c0_future_inextendibility' canonical and forbids aliases in new canonical "
                   "artifacts; F2b uses the canonical token, so the repair is in F0/ruling. The "
                   "content surface itself is green at this hash.",
    "needed_to_unblock": "Either (a) extend the canonical consistency tool to embed "
                         "map_taxonomy_sha256/lead_contract_sha256/measured_at, regenerate the "
                         "canonical evidence, refresh the consistency_evidence_sha256 + checked_at "
                         "in F1/F2a/F2b, re-freeze; or (b) repoint the three declarations to the "
                         "canonical bytes 9e335e9b and record the enriched pin path explicitly. "
                         "Plus one written controller ruling designating the governing "
                         "conclusion-token registry (or an F0 revision adopting the VOCAB canonical "
                         "keys). Then hold F2b + F0 stable for one full review window.",
    "evidence_refs": [
        ref("artifacts/worker-059/f2b_rev12_verdict/review_F2b_55d0a1ea.json", rev_sha),
        ref("artifacts/worker-059/f2b_rev12_verdict/consistency_adjudication.json", adj_sha),
        ref("artifacts/worker-059/f2b_rev12_verdict/independent_evidence.json", ev_sha),
    ],
    "expected_information_gain": "high: removes the last binding blocker on the F2b leg of G-FORM "
                                 "and gives the controller one coherent repair path for all three "
                                 "schemas.",
}
events.append(e)

e = {
    "event_id": f"w059-f2b-rev12-{ts.replace(':', '').replace('-', '')}-status-checkpoint",
    "event_type": "status",
    "created_at": ts,
    "actor": "worker-059",
    "node_id": "F2b",
    "group_id": "formulation",
    "class_id": "AF-SCC-C0-VAC-GEN",
    "gate": "G-FORM",
    "status": "active",
    "hours": 0.5,
    "checkpoint_id": "w059-ckpt-f2b-rev12",
    "summary": "W059-F2B-REV12-VERDICT-01 complete at worker level. Pinned F2b rev12 sha256 "
               "55d0a1ea9bda (stable 00:32:02 through the finalize re-measure, no drift). Verdict "
               "revise 4.0: content semantics, well-typedness, quantifiers, pointers, gates and "
               "class-separation green (34 checks, 24/24 mutants); blocking findings are HF-059-"
               "F2B-01 consistency-evidence hash binding and HF-059-F2B-02 conclusion-token "
               "registry conflict. Prior defect classes from the 1bb78ce9/b6123750 rounds "
               "independently confirmed resolved. Artifacts under "
               "artifacts/worker-059/f2b_rev12_verdict/; no global state mutated, no node "
               "completion or gate verdict claimed.",
    "evidence_refs": [
        ref("artifacts/worker-059/f2b_rev12_verdict/review_F2b_55d0a1ea.json", rev_sha),
        ref("artifacts/worker-059/f2b_rev12_verdict/independent_evidence.json", ev_sha),
        ref("artifacts/worker-059/f2b_rev12_verdict/consistency_adjudication.json", adj_sha),
        ref("artifacts/worker-059/f2b_rev12_verdict/checkpoint_w059_f2b_rev12.json", ckpt_sha),
        ref("artifacts/worker-059/f2b_rev12_verdict/postrun_annex.json", annex_sha),
    ],
    "next_falsifier": falsifier,
}
events.append(e)

e = {
    "event_id": f"w059-f2b-rev12-{ts.replace(':', '').replace('-', '')}-artifact-annex",
    "event_type": "artifact",
    "created_at": ts,
    "actor": "worker-059",
    "node_id": "F2b",
    "group_id": "formulation",
    "class_id": "AF-SCC-C0-VAC-GEN",
    "gate": "G-FORM",
    "artifact_type": "drift_annex",
    "path": "artifacts/worker-059/f2b_rev12_verdict/postrun_annex.json",
    "sha256": annex_sha,
    "reviewed_sha256": snap_sha,
    "validation_status": "unverified",
    "evidence_refs": [ref("schemas/af_scc_c0_vacuum.yaml", canon["schemas/af_scc_c0_vacuum.yaml"])],
    "falsifier": "Any later measurement of schemas/af_scc_c0_vacuum.yaml different from "
                 "55d0a1ea9bda falsifies the binding of this review.",
}
events.append(e)

before = OUTBOX.read_text().count("\n") if OUTBOX.exists() else 0

import sys
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

for ev in events:
    validate_event(ev)

with open(OUTBOX, "a", encoding="utf-8") as fh:
    for ev in events:
        fh.write(json.dumps(ev, ensure_ascii=False) + "\n")
after = OUTBOX.read_text().count("\n")
print(json.dumps({
    "outbox": str(OUTBOX), "lines_before": before, "lines_after": after,
    "events_appended": len(events),
    "append_only_ok": after == before + len(events),
    "postrun_annex_sha256": annex_sha,
    "drift": canon["schemas/af_scc_c0_vacuum.yaml"] != snap_sha,
    "canonical_f2b": canon["schemas/af_scc_c0_vacuum.yaml"][:12],
}, indent=1))
