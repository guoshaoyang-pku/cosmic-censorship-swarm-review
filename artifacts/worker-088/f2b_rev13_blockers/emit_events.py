#!/usr/bin/env python3
"""Checkpoint + outbox emission for W088-F2B-REV13-BLOCKERS.

Writes (worker-owned):
  runtime/state/w088_checkpoint_f2b_rev13_blockers.json
  comms/outbox/worker-088.jsonl   (append, one valid JSON object per line)

Never writes a canonical schema, the map, or any other agent's file.
"""
import datetime as dt
import hashlib
import json
import os

ROOT = "/data3/guoshaoyang/workdir/ai4math-swarm"
BASE = f"{ROOT}/artifacts/worker-088/f2b_rev13_blockers"
OUTBOX = f"{ROOT}/comms/outbox/worker-088.jsonl"
CKPT = f"{ROOT}/runtime/state/w088_checkpoint_f2b_rev13_blockers.json"
ACTOR = "worker-088"
NOW = dt.datetime.now().astimezone().isoformat()


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def h8(path):
    return sha(path)[:12]


artifacts = {
    "probe": f"{BASE}/check_f2b_rev13_blockers.py",
    "builder": f"{BASE}/build_candidate.py",
    "report_live": f"{BASE}/evidence/report.live.json",
    "report_candidate": f"{BASE}/evidence/report.candidate.json",
    "report_md": f"{BASE}/REPORT.md",
    "pinned_live": f"{BASE}/evidence/pinned_live_f2b.b2ab6acb.yaml",
    "candidate_schema": f"{BASE}/candidate/af_scc_c0_vacuum.rev13repair.yaml",
    "candidate_manifest": f"{BASE}/candidate/MANIFEST.json",
    "candidate_evidence": f"{BASE}/candidate/artifacts/formulation/evidence/taxonomy_consistency.json",
}
H = {k: sha(v) for k, v in artifacts.items()}

live = json.load(open(artifacts["report_live"]))
cand = json.load(open(artifacts["report_candidate"]))
manifest = json.load(open(artifacts["candidate_manifest"]))

checkpoint = {
    "schema": "w088-checkpoint/v1",
    "worker": ACTOR,
    "task_id": "W088-F2B-REV13-BLOCKERS-01",
    "created_at": NOW,
    "class_id": "AF-SCC-C0-VAC-GEN",
    "node_id": "F2b",
    "gate": "G-FORM",
    "status": "checkpoint",
    "pins": {
        "f2b_canonical": {"path": "schemas/af_scc_c0_vacuum.yaml", "sha256": live["pins"]["schema"]["sha256_before"]},
        "f2a_sibling": {"path": "schemas/af_scc_c2_vacuum.yaml", "sha256": live["pins"]["sibling"]["sha256"]},
        "f0_taxonomy": {"path": "research_map/formulation_taxonomy.yaml", "sha256": live["pins"]["taxonomy"]["sha256"]},
        "vocab_aliases": {"path": "artifacts/formulation/VOCAB_ALIASES.json", "sha256": live["pins"]["aliases"]["sha256"]},
        "consistency_evidence_live": {"path": "artifacts/formulation/evidence/taxonomy_consistency.json", "sha256": live["pins"]["evidence"]["sha256"]},
        "drift_during_read": live["drift_during_read"],
    },
    "dispositions_live": {
        i["id"]: i["disposition"] for i in live["items"]
    },
    "dispositions_candidate": {
        i["id"]: i["disposition"] for i in cand["items"]
    },
    "candidate": {
        "schema_path": manifest["candidate_schema"]["path"],
        "schema_sha256": manifest["candidate_schema"]["sha256"],
        "evidence_sha256": manifest["candidate_evidence"]["sha256"],
        "structural_checker": "pass, 0 failed rules",
        "class_separation_findings": [],
        "duplicate_keys": [],
    },
    "artifact_hashes": H,
    "next_falsifier": "any write to schemas/af_scc_c0_vacuum.yaml or the pinned inputs voids these measurements; at a "
    "new F2b revision re-run check_f2b_rev13_blockers.py and require NOT_LIVE for B1-B4 plus a passing structural "
    "checker and an empty class-separation scan before an accept; the candidate binds only live b2ab6acb2bbe and "
    "FROZEN rev29 815e08079aef",
    "authority_note": "bounded execution worker: no gate verdict, node status, validation_status or theorem is set; "
    "canonical paths were not modified",
}
with open(CKPT, "w", encoding="utf-8") as fh:
    json.dump(checkpoint, fh, indent=1, sort_keys=True)
    fh.write("\n")
H["checkpoint"] = sha(CKPT)
artifacts["checkpoint"] = CKPT

ev = []


def add(obj):
    ev.append(obj)


base = {"actor": ACTOR, "created_at": NOW}

for key, etype, note in (
    ("probe", "f2b_blocker_probe", "Revision-fair F2b blocker probe: four families (inverted containment premise, stale containment denial, vocabulary binding gap, non-self-verifying evidence); reads only canonical inputs, writes only --out."),
    ("report_live", "f2b_blocker_report", "Live disposition ledger at canonical F2b b2ab6acb2bbe: B1/B2/B4 LIVE_DEFECT, B3 BINDING_GAP; no drift; F0/FROZEN/ledger/evidence pins re-measured at declared values."),
    ("report_md", "f2b_blocker_report", "Consolidated human-readable blocker ledger + repair contract + falsifiers for the rev13 F2b review wave."),
    ("candidate_schema", "f2b_repair_candidate", "Worker-owned F2b repair candidate (R1 inverted premise, R2 containment denial, R3 extensions.vocabulary_binding, R4 self-verifying evidence + re-stamp); all four families NOT_LIVE; structural checker pass; class-separation []."),
    ("candidate_evidence", "f2b_repair_candidate_evidence", "Self-verifying evidence copy recording map_taxonomy_sha256, lead_contract_sha256 and alias_registry_sha256; generator update required by the owner."),
    ("candidate_manifest", "f2b_repair_candidate_manifest", "Candidate manifest: base pin, edit list, candidate hashes, authority note."),
    ("pinned_live", "pinned_revision_copy", "Byte copy of the reviewed F2b rev13 revision b2ab6acb."),
):
    add({
        **base,
        "event_id": f"w088-f2b13-{key}",
        "event_type": "artifact",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "artifact_type": etype,
        "path": os.path.relpath(artifacts[key], ROOT),
        "sha256": H[key],
        "validation_status": "unverified",
        "evidence_refs": [f"schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe", f"artifacts/formulation/FROZEN.json#815e08079aef"],
        "note": note,
    })

add({
    **base,
    "event_id": "w088-f2b13-review",
    "event_type": "review",
    "reviewer": ACTOR,
    "target_id": "F2b",
    "node_id": "F2b",
    "class_id": "AF-SCC-C0-VAC-GEN",
    "gate": "G-FORM",
    "verdict": "revise",
    "score": 3.5,
    "counts_as_full_schema_verdict": False,
    "reviewed_sha256": live["pins"]["schema"]["sha256_before"],
    "artifact": "schemas/af_scc_c0_vacuum.yaml",
    "hard_failures": [
        "B1 inverted_containment_premise: implication_ledger.forbidden_transfers[0].reason (line 246) calls C2 the strictly larger extension class while the file's own chain is E_C2 subset E_{C^1,1} subset E_H2loc subset E_C0 (replicates W034/W044/W066/W075 at this hash)",
        "B2 stale_containment_denial: regularity.must_not_conflate[0] (line 152) denies containment with C2/C0 while the same file asserts it at 239/243/254; the F2a sibling records that exact phrase as wrong (replicates W066 R13-F2B-H1)",
        "B4 evidence_not_self_verifying: f0_binding consistency evidence resolves but records no sha256 of the compared inputs, so consistent=true is not reproducible from the evidence file alone (replicates W044 HF-044-INT-A2)",
    ],
    "findings": [
        {"id": "W088-R13-B3", "severity": "major", "axis": "vocabulary binding", "finding": "conclusion_type=scc_c0_future_inextendibility and genericity.kind=residual_comeager are VOCAB_ALIASES canonical tokens; F0's frozen allowed-lists contain only their aliases and no registry is bound, so literal-membership detectors fail and equivalence is undecidable from the artifact alone. The two vocabularies are mutually inverse; an F0 edit would void G-F0, so the decidable repair is an explicit binding (candidate R3).", "adjudication": "gate owner must rule whether the bound registry or F0's allowed-list is operative"},
        {"id": "W088-R13-CAND", "severity": "info", "axis": "repair candidate", "finding": "worker-owned candidate b598b59e09e5 clears B1-B4 (probe NOT_LIVE for all four), passes check_class_schema.py with 0 failed rules, empty class-separation scan, 0 duplicate keys; canonical paths untouched."},
    ],
    "independence": {
        "reviewer": ACTOR,
        "reviewer_is_author": False,
        "author": "astra-lead-formulation",
        "no_author_contact": True,
        "no_network": True,
        "prior_use": "The four families were measured mechanically from the b2ab6acb bytes by this worker's own probe; prior verdicts are cited for corroboration only and no text was copied. No prior F2b verdict was read before the probe run.",
    },
    "evidence_refs": [
        "schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe",
        f"artifacts/worker-088/f2b_rev13_blockers/evidence/report.live.json#{H['report_live'][:12]}",
        f"artifacts/worker-088/f2b_rev13_blockers/check_f2b_rev13_blockers.py#{H['probe'][:12]}",
        "artifacts/formulation/FROZEN.json#815e08079aef",
        "schemas/af_scc_c2_vacuum.yaml#e9a27996dfd3",
        "research_map/formulation_taxonomy.yaml#0abb9ed8a961",
        "artifacts/formulation/VOCAB_ALIASES.json#" + live["pins"]["aliases"]["sha256"][:12],
        "artifacts/formulation/evidence/taxonomy_consistency.json#9e335e9ba1bf",
    ],
    "next_falsifier": "Re-run check_f2b_rev13_blockers.py at the next F2b revision; an accept requires NOT_LIVE for B1-B4 (or a gate-owner ruling voiding B3), a passing check_class_schema.py, an empty class-separation scan, and the repaired evidence document recording each compared input sha256. This verdict binds b2ab6acb2bbe only.",
    "not_claimed": ["no gate verdict, node status or validation_status", "no physics or theorem claim", "no novelty claim for the consolidated findings"],
})

add({
    **base,
    "event_id": "w088-f2b13-blocker",
    "event_type": "blocker",
    "actor": ACTOR,
    "node_id": "F2b",
    "class_id": "AF-SCC-C0-VAC-GEN",
    "gate": "G-FORM",
    "description": "F2b rev13 b2ab6acb carries three live schema-text/evidence defects and one vocabulary binding gap, measured mechanically and corroborated by six independent rev13 verdicts; F2b cannot reach the >=2 accepts at one stable hash that REC-23 requires until the owner lands a repair.",
    "needed_to_unblock": "formulation lead, in one revision at one hash: (1) forbidden_transfers[*].reason whose premise contradicts the chain -> smaller-set wording; (2) regularity.must_not_conflate[0] denial -> nested-sets wording; (3) bind VOCAB_ALIASES.json by path+sha256 with explicit per-field canonical/alias equivalence (or obtain a gate-owner ruling that the F0 allowed-list is operative and carry literal F0 tokens); (4) regenerate the consistency evidence with each compared input sha256 and re-stamp f0_binding in the same revision. A worker-owned candidate clearing (1)-(4) is at artifacts/worker-088/f2b_rev13_blockers/candidate/af_scc_c0_vacuum.rev13repair.yaml#b598b59e09e5.",
    "evidence_refs": [
        "schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe",
        f"artifacts/worker-088/f2b_rev13_blockers/evidence/report.live.json#{H['report_live'][:12]}",
        f"artifacts/worker-088/f2b_rev13_blockers/candidate/af_scc_c0_vacuum.rev13repair.yaml#{H['candidate_schema'][:12]}",
        "artifacts/formulation/FROZEN.json#815e08079aef",
    ],
    "falsifier": "a revision at one hash that passes all four probes as NOT_LIVE with a passing structural checker and clean class-separation scan; or a gate-owner ruling that any of B1-B4 is not blocking at the cited lines, with the reading exhibited.",
})

add({
    **base,
    "event_id": "w088-f2b13-claim",
    "event_type": "claim",
    "actor": ACTOR,
    "node_id": "F2b",
    "class_id": "AF-SCC-C0-VAC-GEN",
    "gate": "G-FORM",
    "conclusion_type": "formal_model",
    "status": "unverified",
    "statement": "At the measured live F2b rev13 bytes b2ab6acb2bbe (FROZEN rev29 815e08079aef; F0 0abb9ed8a961; evidence 9e335e9ba1bf untouched), the rev13 review wave's F2b hard failures consolidate to four machine-measured families: B1 inverted containment premise at line 246, B2 stale containment denial at line 152, B4 non-self-verifying consistency evidence at line 309 (all LIVE_DEFECT), and B3 vocabulary binding gap for conclusion_type/genericity.kind (canonical VOCAB_ALIASES tokens absent from the frozen F0 allowed-lists, no registry bound). A worker-owned candidate b598b59e09e5 applying four scoped edits clears B1-B4 (probe NOT_LIVE for all four), passes check_class_schema.py with 0 failed rules and yields an empty class-separation scan, with the canonical paths unchanged.",
    "assumptions": [
        "worker measurement only; read-only on canonical paths; no network",
        "disposition is a schema/binding conformance call, not a class-semantics or physics claim",
        "the candidate is a proposal; only the formulation lead may land it, and B3 additionally requires a gate-owner adjudication",
    ],
    "falsifier": "any write to schemas/af_scc_c0_vacuum.yaml or the pinned inputs after this measurement; a probe rerun at this hash that fails to reproduce the four dispositions; or a gate-owner ruling that B3's registry binding is not required and the literal F0 tokens are operative (which voids only the candidate's R3 item)",
    "evidence_refs": [
        f"artifacts/worker-088/f2b_rev13_blockers/evidence/report.live.json#{H['report_live'][:12]}",
        f"artifacts/worker-088/f2b_rev13_blockers/evidence/report.candidate.json#{H['report_candidate'][:12]}",
        f"artifacts/worker-088/f2b_rev13_blockers/candidate/af_scc_c0_vacuum.rev13repair.yaml#{H['candidate_schema'][:12]}",
        f"artifacts/worker-088/f2b_rev13_blockers/check_f2b_rev13_blockers.py#{H['probe'][:12]}",
        "schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe",
        "artifacts/formulation/FROZEN.json#815e08079aef",
    ],
    "artifact_refs": [
        "artifacts/worker-088/f2b_rev13_blockers/evidence/report.live.json",
        "artifacts/worker-088/f2b_rev13_blockers/candidate/af_scc_c0_vacuum.rev13repair.yaml",
    ],
})

add({
    **base,
    "event_id": "w088-f2b13-checkpoint",
    "event_type": "status",
    "actor": ACTOR,
    "node_id": "F2b",
    "class_id": "AF-SCC-C0-VAC-GEN",
    "status": "active",
    "hours": 0.5,
    "summary": "W088-F2B-REV13-BLOCKERS-01 complete at worker level: independent consolidation of the rev13 F2b hard-failure wave into four measured families (B1/B2/B4 live defects, B3 binding gap) plus a worker-owned repair candidate b598b59e09e5 that clears all four under the probe, the structural checker and the class-separation scan. Read-only on canonical paths; checkpoint runtime/state/w088_checkpoint_f2b_rev13_blockers.json; worker exits. No gate verdict, node status, validation_status or theorem claimed.",
    "evidence_refs": [
        f"artifacts/worker-088/f2b_rev13_blockers/evidence/report.live.json#{H['report_live'][:12]}",
        f"artifacts/worker-088/f2b_rev13_blockers/candidate/MANIFEST.json#{H['candidate_manifest'][:12]}",
        f"runtime/state/w088_checkpoint_f2b_rev13_blockers.json#{H['checkpoint'][:12]}",
        "schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe",
    ],
    "next_falsifier": "re-run the probe at the next F2b revision; accept binds only if B1-B4 are NOT_LIVE with a passing structural checker and clean class-separation scan, and the candidate is re-verified at the owner's landed hash",
})

add({
    **base,
    "event_id": "w088-f2b13-artifact-checkpoint",
    "event_type": "artifact",
    "actor": ACTOR,
    "node_id": "F2b",
    "class_id": "AF-SCC-C0-VAC-GEN",
    "artifact_type": "checkpoint",
    "path": "runtime/state/w088_checkpoint_f2b_rev13_blockers.json",
    "sha256": H["checkpoint"],
    "validation_status": "unverified",
    "evidence_refs": [f"artifacts/worker-088/f2b_rev13_blockers/evidence/report.live.json#{H['report_live'][:12]}"],
    "note": "Worker-088 F2b rev13 blocker checkpoint: pins, dispositions live/candidate, candidate manifest and artifact hashes.",
})

with open(OUTBOX, "a", encoding="utf-8") as fh:
    for obj in ev:
        fh.write(json.dumps(obj, sort_keys=True) + "\n")

# validate everything just written is parseable and schema-required fields exist
req = {
    "artifact": ("node_id", "artifact_type", "path", "sha256", "validation_status"),
    "review": ("target_id", "reviewer", "verdict", "score", "hard_failures", "findings"),
    "claim": ("class_id", "statement", "conclusion_type", "assumptions", "falsifier", "evidence_refs"),
}
bad = []
with open(OUTBOX, "r", encoding="utf-8") as fh:
    for i, ln in enumerate(fh, 1):
        if not ln.strip():
            continue
        try:
            obj = json.loads(ln)
        except Exception as exc:
            bad.append((i, f"json: {exc}"))
            continue
        for k in ("event_id", "event_type", "created_at", "actor"):
            if k not in obj:
                bad.append((i, f"missing {k}"))
        need = req.get(obj.get("event_type"))
        if need:
            for k in need:
                if k not in obj:
                    bad.append((i, f"missing {k} for {obj.get('event_type')}"))
print(json.dumps({
    "appended": len(ev),
    "checkpoint": CKPT,
    "checkpoint_sha256": H["checkpoint"],
    "outbox": OUTBOX,
    "outbox_validation_errors": bad,
    "artifact_hashes": H,
}, indent=1, sort_keys=True))
