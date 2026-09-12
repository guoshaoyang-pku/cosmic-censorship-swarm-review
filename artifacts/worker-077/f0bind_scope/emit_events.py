#!/usr/bin/env python3
"""Append the W077-F0BIND-SCOPE-01 event batch to comms/outbox/worker-077.jsonl.

Writes only: runtime/state/w077_f0bind_scope_checkpoint.json and the outbox append.
Validates every appended line against research_map/schemas.py requirements before writing.
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TASK = "artifacts/worker-077/f0bind_scope"
OUTBOX = ROOT / "comms/outbox/worker-077.jsonl"
CKPT = ROOT / "runtime/state/w077_f0bind_scope_checkpoint.json"
CREATED = "2026-09-12T01:30:00+08:00"
ACTOR = "worker-077"
BATCH = "w077-f0bindscope-20260912T013000"

REPORT = "d6fc3913f23f6df64b2d91510daa9ac72b7fdb9e702400f31ab7b74a13f1748d"


def sh(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


H = {f: sh(f) for f in [
    f"{TASK}/PREREGISTRATION.json", f"{TASK}/check_f0bind_scope.py", f"{TASK}/report.json",
    f"{TASK}/run1.report.json", f"{TASK}/run2.report.json", f"{TASK}/README.md",
    f"{TASK}/determinism.json", f"{TASK}/drift_observation.json", f"{TASK}/entry_hashes.json",
    "research_map/formulation_taxonomy.yaml", "schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml", "schemas/af_scc_c0_vacuum.yaml",
    "artifacts/formulation/FROZEN.json", "artifacts/formulation/evidence/taxonomy_consistency.json",
    "artifacts/formulation/tools/check_taxonomy_consistency.py",
    "artifacts/worker-079/rev29_bindchain/report.json",
    "artifacts/worker-004/f1_strictness_direction/report.json",
    "reviews/F1-review-worker-089.json",
]}

EV = lambda p: f"{p}#sha256:{H[p]}"  # noqa: E731

PINNED = [
    EV("research_map/formulation_taxonomy.yaml"), EV("schemas/af_wcc_vacuum.yaml"),
    EV("schemas/af_scc_c2_vacuum.yaml"), EV("schemas/af_scc_c0_vacuum.yaml"),
    EV("artifacts/formulation/FROZEN.json"), EV("artifacts/formulation/evidence/taxonomy_consistency.json"),
    EV("artifacts/formulation/tools/check_taxonomy_consistency.py"),
]
ARTIFACTS = [
    EV(f"{TASK}/PREREGISTRATION.json"), EV(f"{TASK}/check_f0bind_scope.py"),
    EV(f"{TASK}/report.json"), EV(f"{TASK}/README.md"), EV(f"{TASK}/determinism.json"),
    EV(f"{TASK}/entry_hashes.json"), EV(f"{TASK}/drift_observation.json"),
]

EVENT_IDS = {
    "take": f"{BATCH}-status-take",
    "a_prereg": f"{BATCH}-artifact-prereg",
    "a_instr": f"{BATCH}-artifact-instrument",
    "a_report": f"{BATCH}-artifact-report",
    "a_readme": f"{BATCH}-artifact-readme",
    "a_det": f"{BATCH}-artifact-determinism",
    "a_entry": f"{BATCH}-artifact-entry-hashes",
    "a_drift": f"{BATCH}-artifact-drift",
    "a_ckpt": f"{BATCH}-artifact-checkpoint",
    "claim": f"{BATCH}-claim",
    "review": f"{BATCH}-review",
    "blocker": f"{BATCH}-blocker",
    "complete": f"{BATCH}-status-complete",
}

# ---------- checkpoint (written before the events that cite it) ----------
checkpoint = {
    "task_id": "W077-F0BIND-SCOPE-01",
    "actor": ACTOR,
    "created_at": CREATED,
    "gate": "G-FORM",
    "node_id": "F1",
    "class_id": "AF-WCC-VAC-GEN",
    "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
    "verdict": "SCOPE_GAP_CONFIRMED",
    "run_window_pins": {
        "research_map/formulation_taxonomy.yaml": H["research_map/formulation_taxonomy.yaml"],
        "schemas/af_wcc_vacuum.yaml": H["schemas/af_wcc_vacuum.yaml"],
        "schemas/af_scc_c2_vacuum.yaml": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
        "schemas/af_scc_c0_vacuum.yaml": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
        "artifacts/formulation/FROZEN.json": H["artifacts/formulation/FROZEN.json"],
        "artifacts/formulation/evidence/taxonomy_consistency.json": H["artifacts/formulation/evidence/taxonomy_consistency.json"],
        "artifacts/formulation/tools/check_taxonomy_consistency.py": H["artifacts/formulation/tools/check_taxonomy_consistency.py"],
    },
    "artifact_hashes": {k: H[k] for k in H if k.startswith(TASK)},
    "outbox_event_ids": list(EVENT_IDS.values()),
    "post_run_moved_pins": ["schemas/af_scc_c2_vacuum.yaml", "schemas/af_scc_c0_vacuum.yaml",
                            "artifacts/formulation/VARIANT_REGISTRY.json",
                            "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json"],
    "canonical_paths_written": [],
    "note": "Worker-local checkpoint (controller runtime checkpoint untouched). Measurement valid at its run-window pins; rev14 landed 21 s after report.json was written and is recorded in drift_observation.json.",
    "next_falsifier": "re-run at the settled rev14 pins under a fresh pre-registration; or a pipeline checker whose compared fields cover the F0-variants vs schema-SET strength relation",
}
CKPT.parent.mkdir(parents=True, exist_ok=True)
CKPT.write_text(json.dumps(checkpoint, indent=2, sort_keys=True) + "\n")
H[f"{TASK}/checkpoint_runtime.json"] = hashlib.sha256(
    json.dumps(checkpoint, indent=2, sort_keys=True).encode() + b"\n").hexdigest()

CHECKPOINT_EV = f"runtime/state/w077_f0bind_scope_checkpoint.json#sha256:{sh('runtime/state/w077_f0bind_scope_checkpoint.json')}"

SUMMARY = (
    "TASK COMPLETE (unverified, worker-level): W077-F0BIND-SCOPE-01. At the run-window pins (F0 "
    "0abb9ed8a961 rev5; F1 d9cebb9404b2 rev13; F2a e9a27996dfd3; F2b b2ab6acb2bbe; evidence "
    "9e335e9ba1bf; checker de356d999ea3; FROZEN rev29 815e08079aef): 3/3 vacuum class schemas declare "
    "f0_binding.consistency_evidence = taxonomy_consistency.json#9e335e9b and the canonical checker "
    "bytes reproduce that evidence byte-for-byte in a sandbox ROOT (exit 0, CONSISTENT, 4 classes, 0 "
    "contract-text divergences). But the checker opens no schemas/* file and never compares the F0 "
    "variants block; its only direction probe is the lexical test J-(I+)/J^-(I+) in the AF-WCC-VAC-GEN "
    "conclusion text, which does not fire on the live rev5 wording. Live F0 asserts SET strictly "
    "stronger at variants[0].definition:94 and conclusion.text:200 while live F1 rev13 asserts strictly "
    "WEAKER at class_identity_variants[SET].relation:235; coverage of the live superseded-direction "
    "sites by the declared evidence is 0/2. 5/5 sandbox mutation controls behaved as preregistered "
    "(M1b/M1c flip either live F0 direction site -> still CONSISTENT; M1a probe token -> D1 fires; M2 "
    "in-domain lead-contract mutation -> fires; M3 F1 schema SET WEAKER->STRONGER -> invisible, "
    "evidence byte-unchanged). 89 review files cite the declared evidence (e.g. "
    "reviews/F1-review-worker-089.json). Verdict SCOPE_GAP_CONFIRMED: the declared consistency evidence "
    "is hash-valid but semantically non-covering on the bound visibility-strength axis, so a gate "
    "acceptance relying on consistency_evidence.consistent=true cannot detect the ESC-2 F0/F1 "
    "contradiction. Post-run addendum: rev14 landed 21 s after the report (F2a->c1013e48, "
    "F2b->c4d17fe6, registry->08afa691, SET delta->518cab5d; evidence re-emitted byte-identically); "
    "F0/F1/checker/evidence bytes unchanged, so the finding persists. No canonical write, no node "
    "status, no gate verdict."
)

FBS01 = ("All three schemas bind F0 0abb9ed8a961 with consistency_evidence "
         "taxonomy_consistency.json#9e335e9b, but that evidence is produced by a "
         "map-taxonomy-vs-lead-contract checker whose compared-field domain contains no schema file and "
         "no F0 variants block. Its only direction probe (D1) is a lexical test for J-(I+)/J^-(I+) in "
         "the WCC conclusion text and does not fire on the live rev5 wording, so the evidence reports "
         "consistent=true while live F0 asserts SET strictly stronger (lines 94, 200) and live F1 rev13 "
         "asserts strictly weaker (line 235).")
FBS02 = ("The canonical checker's only direction-bearing text is its dormant D1 record "
         "(relation: 'the F0 condition is strictly STRONGER'), which encodes the superseded label; if "
         "D1 fires at a future hash the emitted evidence would record that direction as the tool's "
         "ruling.")
FALSIFIER = ("A pinned artifact in the formulation acceptance pipeline whose compared-field set covers "
             "the visibility strength relation between F0's SET variant text and the class schemas' SET "
             "relation; or a live F0 revision whose direction statements agree with F1 rev13; or a "
             "sandbox control handled contrary to H5 (which would falsify the harness rather than the "
             "finding).")
NEXT_FALSIFIER = ("Re-run at the settled rev14 pins under a fresh pre-registration: any schema whose "
                  "f0_binding names a direction-covering checker or evidence; any live F0/F1 revision "
                  "whose SET strength statements agree; any checker revision that compares F0 variants "
                  "text against the schemas; or drift of any pinned input (voids the run).")

events = [
    {
        "event_id": EVENT_IDS["take"], "event_type": "status", "created_at": CREATED, "actor": ACTOR,
        "node_id": "F1", "gate": "G-FORM", "status": "active", "hours": 1.0,
        "class_id": "AF-WCC-VAC-GEN", "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "summary": ("No inbox card exists for worker-077 (fleet slot recycled after the 01:17 "
                    "pin-provenance task). Took ONE bounded class-bound task W077-F0BIND-SCOPE-01: "
                    "read-only scope audit of the f0_binding.consistency_evidence declared by the "
                    "three vacuum class schemas, at the run-window pins F0 0abb9ed8a961, F1 "
                    "d9cebb9404b2, F2a e9a27996dfd3, F2b b2ab6acb2bbe, evidence 9e335e9b, checker "
                    "de356d999ea3. Pre-registered; no canonical write."),
        "evidence_refs": ARTIFACTS + PINNED, "next_falsifier": NEXT_FALSIFIER,
    },
    *[{
        "event_id": EVENT_IDS[key], "event_type": "artifact", "created_at": CREATED, "actor": ACTOR,
        "node_id": "F1", "gate": "G-FORM", "task_id": "W077-F0BIND-SCOPE-01",
        "class_id": "AF-WCC-VAC-GEN", "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "artifact_type": atype, "path": path, "sha256": H[path],
        "validation_status": "unverified", "summary": note, "evidence_refs": ARTIFACTS + PINNED[:3],
    } for key, atype, path, note in [
        ("a_prereg", "preregistration", f"{TASK}/PREREGISTRATION.json",
         "pre-registered task, pins, hypotheses H1-H5, verdict rules, falsifier and non-claims"),
        ("a_instr", "scope_audit_instrument", f"{TASK}/check_f0bind_scope.py",
         "deterministic read-only instrument; sandbox reproduction of the canonical checker plus 5 mutation controls; exit 0/2/3"),
        ("a_report", "scope_audit_report", f"{TASK}/report.json",
         "machine-readable report: pins, binding blocks, checker domain, direction-site coverage 0/2, controls 5/5, findings FBS-01/02, decision inputs, content digest ab4ac42543f1"),
        ("a_readme", "scope_audit_readme", f"{TASK}/README.md",
         "cold-start method, headline, controls table, findings, reliance, post-run drift, reproduction, non-claims"),
        ("a_det", "determinism_record", f"{TASK}/determinism.json",
         "two runs byte-identical at report.json#d6fc3913; sandbox evidence bytes == live 9e335e9b; no in-run drift"),
        ("a_entry", "entry_hashes", f"{TASK}/entry_hashes.json",
         "sha256 of every task artifact plus run-window pins and post-run moved-pin list"),
        ("a_drift", "post_run_drift_observation", f"{TASK}/drift_observation.json",
         "rev14 landed 21 s after the report (F2a/F2b/registry/SET-delta moved; evidence re-emitted byte-identically); measurement scoped to its run-window pins"),
    ]],
    {
        "event_id": EVENT_IDS["a_ckpt"], "event_type": "artifact", "created_at": CREATED, "actor": ACTOR,
        "node_id": "F1", "gate": "G-FORM", "task_id": "W077-F0BIND-SCOPE-01",
        "class_id": "AF-WCC-VAC-GEN", "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "artifact_type": "worker_checkpoint", "path": "runtime/state/w077_f0bind_scope_checkpoint.json",
        "sha256": sh("runtime/state/w077_f0bind_scope_checkpoint.json"),
        "validation_status": "unverified",
        "summary": "worker-local checkpoint (controller runtime checkpoint untouched): pins, artifact hashes, event ids, post-run moved pins, no canonical write",
        "evidence_refs": ARTIFACTS,
    },
    {
        "event_id": EVENT_IDS["claim"], "event_type": "claim", "created_at": CREATED, "actor": ACTOR,
        "node_id": "F1", "gate": "G-FORM", "class_id": "AF-WCC-VAC-GEN",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "conclusion_type": "formal_model",
        "statement": (
            "Artifact-and-checker measurement (not a mathematics claim, not a gate verdict) at the "
            "run-window pins F0 research_map/formulation_taxonomy.yaml#sha256:0abb9ed8a961 (rev5), F1 "
            "schemas/af_wcc_vacuum.yaml#sha256:d9cebb9404b2 (rev13), F2a #e9a27996dfd3 (rev13), F2b "
            "#b2ab6acb2bbe (rev13), evidence "
            "artifacts/formulation/evidence/taxonomy_consistency.json#sha256:9e335e9ba1bf, checker "
            "artifacts/formulation/tools/check_taxonomy_consistency.py#sha256:de356d999ea3, FROZEN "
            "rev29 815e08079aef: (1) 3/3 vacuum class schemas declare f0_binding.consistency_evidence "
            "= taxonomy_consistency.json#9e335e9b against the same declared F0 0abb9ed8a961 and the "
            "declared hash resolves; (2) the canonical checker bytes reproduce the live evidence "
            "byte-for-byte in a sandbox ROOT (exit 0, CONSISTENT, 4 classes, 0 contract-text "
            "divergences); (3) the checker opens no schemas/* file and never compares the F0 top-level "
            "variants block; its only direction-sensitive probe is a lexical test for 'J-(I+)' or "
            "'J^-(I+)' in the AF-WCC-VAC-GEN conclusion text; (4) live F0 asserts the SET reading "
            "strictly stronger at variants[0].definition line 94 and conclusion.text line 200 while "
            "live F1 rev13 asserts strictly WEAKER at class_identity_variants[SET].relation line 235 "
            "and discloses the correction; the probe token is absent from the live conclusion text, so "
            "the declared evidence reports consistent=true with 0/2 coverage of the live "
            "superseded-direction sites; (5) 5/5 sandbox mutation controls as preregistered: flipping "
            "either live F0 direction site leaves the checker CONSISTENT (M1b/M1c), injecting the "
            "probe token fires divergence D1 (M1a), an in-domain lead-contract regularity mutation "
            "fires (M2), and an F1 schema SET WEAKER->STRONGER mutation is invisible with "
            "byte-unchanged evidence (M3); (6) 89 review files cite the declared evidence, e.g. "
            "reviews/F1-review-worker-089.json#sha256:9a4bb3f3268c records the rev13 refresh as "
            "resolving via consistency_evidence.consistent=true. Operative consequence: the declared "
            "f0_binding consistency evidence is hash-valid but semantically non-covering on the bound "
            "visibility-strength axis, so a gate acceptance relying on consistent=true cannot detect "
            "the ESC-2 F0/F1 direction contradiction. Post-run addendum (recorded, outside the pinned "
            "run): the authorized rev14 landed 21 s after the report at 01:25:42, moving F2a to "
            "c1013e48, F2b to c4d17fe6, VARIANT_REGISTRY to 08afa691 and the SET delta to 518cab5d, "
            "and re-emitting the evidence file byte-identically (mtime 01:25:55, hash 9e335e9b); F0, "
            "F1, the checker and the evidence bytes are unchanged, so the finding persists at the "
            "settled bytes."),
        "assumptions": [
            "The declared consistency evidence is what the f0_binding rule means by 'the consistency check'; the pinned checker bytes are its only producer at the pinned revision.",
            "The coverage claim is scoped to the checker's compared-field domain as measured from its bytes and the sandbox mutation controls, not to unstated intent.",
            "D1's token test is the checker's only direction-sensitive probe; the other compared fields carry no visibility-strength relation.",
            "The pinned claim is void if any run-window pin drifts; the post-run rev14 drift is recorded separately and does not extend the pinned claim.",
            "Worker events cannot set node status, validation_status=passed, or a gate verdict.",
        ],
        "falsifier": FALSIFIER,
        "evidence_refs": ARTIFACTS + PINNED + [
            EV("artifacts/worker-079/rev29_bindchain/report.json"),
            EV("artifacts/worker-004/f1_strictness_direction/report.json"),
            EV("reviews/F1-review-worker-089.json"),
            CHECKPOINT_EV,
        ],
        "artifact_refs": [EV(f"{TASK}/report.json")],
    },
    {
        "event_id": EVENT_IDS["review"], "event_type": "review", "created_at": CREATED, "actor": ACTOR,
        "node_id": "F1", "gate": "G-FORM", "reviewer": ACTOR,
        "class_id": "AF-WCC-VAC-GEN", "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "target_id": EV(f"{TASK}/report.json"), "verdict": "accept", "score": 4.0,
        "hard_failures": [],
        "counts_as_full_schema_verdict": False,
        "reviewer_independence": "self-review of the instrument and its controls (non-independent); not a full-schema verdict",
        "findings": [
            {"id": "W077-FBS-01", "severity": "major", "type": "declared_consistency_evidence_does_not_cover_bound_direction_axis",
             "finding": FBS01, "falsifier": "a pipeline checker whose compared fields cover the F0-variants vs schema-SET strength relation; or live F0/F1 direction agreement."},
            {"id": "W077-FBS-02", "severity": "minor", "type": "dormant_direction_bearing_text_in_checker",
             "finding": FBS02, "falsifier": "a canonical checker revision whose D1 record states the independently proved direction (set-based weaker)."},
        ],
        "evidence_refs": ARTIFACTS + PINNED[:3],
    },
    {
        "event_id": EVENT_IDS["blocker"], "event_type": "blocker", "created_at": CREATED, "actor": ACTOR,
        "node_id": "F1", "gate": "G-FORM", "class_id": "AF-WCC-VAC-GEN",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "description": ("G-FORM F1 evidence-scope blocker at the run-window pins: all three vacuum "
                        "class schemas certify F0 consistency with taxonomy_consistency.json#9e335e9b, "
                        "but that evidence cannot see the live F0 (strictly stronger, lines 94/200) vs "
                        "F1 rev13 (strictly WEAKER, line 235) direction contradiction. Reviews are "
                        "already recording the refresh as resolving (89 files cite it; "
                        "reviews/F1-review-worker-089.json records consistent=true), so the binding is "
                        "being read as semantic F0-consistency evidence it does not provide. Secondary: "
                        "the checker's dormant D1 record asserts the superseded direction."),
        "needed_to_unblock": ("Controller / ESC-2 disposition of one of the pre-registered options: "
                              "(A) extend the checker/evidence to cover the F0 variants vs schema SET "
                              "relation and re-stamp the three f0_binding blocks; (B) correct or "
                              "explicitly scope the two live F0 sites (voids G-F0, fresh accepts "
                              "required); or (C) record the binding's scope limit in binding_note/rule. "
                              "Then re-run this instrument at the settled rev14 pins under a fresh "
                              "pre-registration."),
        "next_falsifier": NEXT_FALSIFIER,
        "evidence_refs": ARTIFACTS + PINNED + [CHECKPOINT_EV],
    },
    {
        "event_id": EVENT_IDS["complete"], "event_type": "status", "created_at": CREATED, "actor": ACTOR,
        "node_id": "F1", "gate": "G-FORM", "status": "active", "hours": 1.0,
        "class_id": "AF-WCC-VAC-GEN", "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "summary": SUMMARY, "evidence_refs": ARTIFACTS + PINNED + [CHECKPOINT_EV],
        "next_falsifier": NEXT_FALSIFIER,
    },
]

# ---------- validate before writing ----------
ALLOWED = {"theorem", "conditional_theorem", "stability_result", "counterexample",
           "numerical_evidence", "formal_model", "open_problem"}
REQ = {
    "claim": ("class_id", "statement", "conclusion_type", "assumptions", "falsifier", "evidence_refs"),
    "artifact": ("node_id", "artifact_type", "path", "sha256", "validation_status"),
    "review": ("target_id", "reviewer", "verdict", "score", "hard_failures", "findings"),
}
base = ("event_id", "event_type", "created_at", "actor")
for e in events:
    for k in base:
        assert e.get(k), f"{e.get('event_id')}: missing {k}"
    for k in REQ.get(e["event_type"], ()):
        assert e.get(k) is not None, f"{e['event_id']}: missing {k}"
    if e["event_type"] == "claim":
        assert e["conclusion_type"] in ALLOWED, f"{e['event_id']}: bad conclusion_type"
        if e["conclusion_type"] == "theorem":
            assert e.get("artifact_refs"), f"{e['event_id']}: theorem without artifact_refs"
    for r in e.get("evidence_refs", []) + e.get("artifact_refs", []):
        assert "#sha256:" in r, f"{e['event_id']}: malformed ref {r}"
    if e["event_type"] == "artifact":
        assert (ROOT / e["path"]).exists(), f"{e['event_id']}: artifact path missing"
        assert sh(e["path"]) == e["sha256"], f"{e['event_id']}: sha256 mismatch for {e['path']}"

ids = [e["event_id"] for e in events]
assert len(ids) == len(set(ids)), "duplicate event ids"

# ---------- append ----------
with OUTBOX.open("a") as f:
    for e in events:
        f.write(json.dumps(e, sort_keys=True) + "\n")

# verify every line of the outbox still parses
n = 0
for i, line in enumerate(OUTBOX.read_text().splitlines(), 1):
    line = line.strip()
    if not line:
        continue
    json.loads(line)
    n += 1
print(json.dumps({"appended": len(events), "event_ids": ids, "outbox_lines_valid": n,
                  "checkpoint": str(CKPT.relative_to(ROOT)),
                  "checkpoint_sha256": sh("runtime/state/w077_f0bind_scope_checkpoint.json")},
                 indent=1, sort_keys=True))
