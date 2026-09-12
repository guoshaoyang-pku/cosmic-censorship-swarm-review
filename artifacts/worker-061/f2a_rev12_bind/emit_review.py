#!/usr/bin/env python3
"""W061-F2A-REV12-BIND-04 emitter.

Builds REVIEW.json / REVIEW.md / CHECKPOINT.json / SHA256SUMS from the probe output, copies
the checkpoint to runtime/state/, and appends the upward events to comms/outbox/worker-061.jsonl.

Authority note: worker evidence only. This does not set node status, validation_status or a gate
verdict, and it writes only:
  artifacts/worker-061/f2a_rev12_bind/**
  runtime/state/w061_f2a_rev12_bind_checkpoint.json
  comms/outbox/worker-061.jsonl
"""
from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
TASK = REPO / "artifacts/worker-061/f2a_rev12_bind"
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST)
STAMP = NOW.strftime("%Y%m%dT%H%M%S")
TASK_ID = "W061-F2A-REV12-BIND-04"
OUTBOX = REPO / "comms/outbox/worker-061.jsonl"


def sha256_path(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def h12(p: Path) -> str:
    return sha256_path(p)[:12]


def rel(p: Path) -> str:
    return str(p.relative_to(REPO))


probe = json.loads((TASK / "probe_f2a_rev12_output.json").read_text())
_probe_by_id = {p["id"]: p for p in probe["probes"]}
P7 = _probe_by_id["P7-REVIEW-STATUS-LEDGER"]["detail"]
mapd = json.loads((REPO / "research_map/research_map.json").read_text())
PIN = TASK / "pinned"
GATE_CUR = TASK / "gate/gate_current_manifest.json"
GATE_R27 = TASK / "gate/gate_shadow_rev27_manifest.json"
TARGET = REPO / "schemas/af_scc_c2_vacuum.yaml"
LEDGER = REPO / "ledger/theorems.jsonl"
W029_SNAP = REPO / "artifacts/worker-029/rev12_closure_verify/ledger_theorems_snapshot.jsonl"
FROZEN = REPO / "artifacts/formulation/FROZEN.json"
VOCAB = REPO / "artifacts/formulation/VOCAB_ALIASES.json"
INDEX = REPO / "schemas/af_scc_regularities.yaml"

pm = probe["pins"]
gate = probe["gate_matrix"]
xb = probe["cross_class_binding"]

reviewed_sha = pm["schemas/af_scc_c2_vacuum.yaml"]["measured"]

hard_failures = [
    {
        "id": "HF-W061-F2AB-01",
        "severity": "hard",
        "axis": "F0 vocabulary binding: conclusion_type",
        "finding": (
            "F2a declares conclusion.conclusion_type='scc_c2_future_inextendibility'. At the bound canonical "
            "F0 taxonomy (research_map/formulation_taxonomy.yaml 0abb9ed8a961), field_vocabulary.conclusion_type."
            "allowed is ['weak_cosmic_censorship','strong_cosmic_censorship_C2','strong_cosmic_censorship_C0'], "
            "so the declared token is NOT literally allowed, and the same class contract's axes.conclusion_type "
            "is 'strong_cosmic_censorship_C2'. The token does match rule_spec.json#vocabularies."
            "class_conclusion_type.AF-SCC-C2-VAC-GEN and is the canonical key of VOCAB_ALIASES.conclusion_type "
            "(members include the F0 token), but F2a carries vocabulary_aliases_ref=null and never names "
            "VOCAB_ALIASES.json, so the alias equivalence is unbound at artifact level. Root cause is a "
            "canonical-vocabulary conflict (F0 field_vocabulary vs rule_spec vs the alias registry's direction), "
            "not a class-semantics change: exactly one class token, family SCC, no C0/WCC content (P1/P13 pass). "
            "Reproduces worker-059 HF-059-F2A-01 and worker-005's F2b vocab audit (P4/P5/P6) on F2a."
        ),
        "evidence_refs": [
            f"schemas/af_scc_c2_vacuum.yaml#sha256:{reviewed_sha[:12]}",
            f"research_map/formulation_taxonomy.yaml#sha256:{pm['research_map/formulation_taxonomy.yaml']['measured'][:12]}",
            f"artifacts/formulation/rule_spec.json#sha256:{pm['artifacts/formulation/rule_spec.json']['measured'][:12]}",
            f"artifacts/formulation/VOCAB_ALIASES.json#sha256:{pm['artifacts/formulation/VOCAB_ALIASES.json']['measured'][:12]}",
            f"{rel(TASK / 'probe_f2a_rev12_output.json')}#P2-F0-VOCAB-CONCLUSION-BINDING",
        ],
        "falsifier": (
            "An F0 revision whose field_vocabulary.conclusion_type.allowed contains the F2a token, or an F2a "
            "revision that binds the alias registry (vocabulary_aliases_ref), or a controller decision recorded "
            "in research_map/research_map.json that alias-equivalence satisfies the G-FORM class-binding "
            "criterion for this axis."
        ),
    },
    {
        "id": "HF-W061-F2AB-02",
        "severity": "hard",
        "axis": "F0 vocabulary binding: genericity_kind",
        "finding": (
            "F2a declares genericity.kind='residual_comeager'. At the bound canonical F0 taxonomy 0abb9ed8a961, "
            "field_vocabulary.genericity_kind.allowed is ['baire_residual','dense_open','measure_one',"
            "'provisional_baire_residual','unresolved'], so the declared token is NOT literally allowed; the "
            "class contract's axes.genericity_kind is 'provisional_baire_residual'. The token matches "
            "rule_spec.json#vocabularies.genericity_kind and is the canonical key of VOCAB_ALIASES.genericity_kind "
            "(members include baire_residual and provisional_baire_residual), but the artifact binds no alias "
            "reference (same root cause as HF-W061-F2AB-01). Reproduces worker-005's F2b P5 on F2a."
        ),
        "evidence_refs": [
            f"schemas/af_scc_c2_vacuum.yaml#sha256:{reviewed_sha[:12]}",
            f"research_map/formulation_taxonomy.yaml#sha256:{pm['research_map/formulation_taxonomy.yaml']['measured'][:12]}",
            f"artifacts/formulation/VOCAB_ALIASES.json#sha256:{pm['artifacts/formulation/VOCAB_ALIASES.json']['measured'][:12]}",
            f"{rel(TASK / 'probe_f2a_rev12_output.json')}#P3-F0-VOCAB-GENERICITY-BINDING",
        ],
        "falsifier": (
            "An F0 revision whose field_vocabulary.genericity_kind.allowed contains residual_comeager, or an F2a "
            "revision that binds the alias registry, or a controller decision that alias-equivalence satisfies "
            "the G-FORM class-binding criterion for this axis."
        ),
    },
    {
        "id": "HF-W061-F2AB-03",
        "severity": "hard",
        "axis": "binding-hash freshness: consistency evidence",
        "finding": (
            "F2a f0_binding.consistency_evidence_sha256 declares 675a99d0d25b2b37c9b9e9b965aec1c1ff0e388d2665fd9"
            "247b58c04733eba48, while the evidence file artifacts/formulation/evidence/taxonomy_consistency.json "
            "measures 9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b and FROZEN rev28 "
            "(2f358f6722d9) pins that same 9e335e9b hash. The declared F0 taxonomy hash is fresh "
            "(0abb9ed8a961 == measured). Reproduces worker-059 HF-059-F2A-02, worker-039 S8 (F1), worker-005 P9 "
            "(F2b): the declaration is one evidence regeneration behind."
        ),
        "evidence_refs": [
            f"schemas/af_scc_c2_vacuum.yaml#sha256:{reviewed_sha[:12]}",
            f"artifacts/formulation/evidence/taxonomy_consistency.json#sha256:{pm['artifacts/formulation/evidence/taxonomy_consistency.json']['measured'][:12]}",
            f"artifacts/formulation/FROZEN.json#sha256:{pm['artifacts/formulation/FROZEN.json']['measured'][:12]}",
            f"{rel(TASK / 'probe_f2a_rev12_output.json')}#P4-EVIDENCE-BINDING-FRESHNESS",
        ],
        "falsifier": (
            "A revision whose f0_binding.consistency_evidence_sha256 equals the measured and FROZEN-pinned "
            "evidence bytes, at the same F2a sha256."
        ),
    },
    {
        "id": "HF-W061-F2AB-04",
        "severity": "hard",
        "axis": "citation scope: l1_ledger_refs vs frozen ledger",
        "finding": (
            "Four of the five l1_ledger_refs rows assert citation_status='verified_by_L1' (T-401, T-402, T-514, "
            "T-520), while ledger/theorems.jsonl records verification_status='abstract-read' and "
            "review_status='not_independently_reviewed' for every one of them. This holds both at the current "
            "ledger hash a1674f094979 and at the worker-029 pinned snapshot 3e3d35531421, and the token "
            "'verified_by_L1' occurs 0 times in both ledger texts. The remaining row T-305 is 'unresolved' and "
            "is consistent with its abstract-read ledger row. Additionally the artifact's l1_status='accepted' "
            "(T-402/T-514/T-520) has no defined mapping to the ledger vocabulary. Independent reproduction of "
            "worker-029 HF-29-02 at the pinned F2a hash."
        ),
        "evidence_refs": [
            f"schemas/af_scc_c2_vacuum.yaml#sha256:{reviewed_sha[:12]}",
            f"ledger/theorems.jsonl#sha256:{h12(LEDGER)}",
            f"{rel(W029_SNAP)}#sha256:{h12(W029_SNAP)}",
            f"{rel(TASK / 'probe_f2a_rev12_output.json')}#P5-CITATION-SCOPE-BINDING",
        ],
        "falsifier": (
            "Any l1_ledger_refs row with a verified citation_status backed by a ledger row whose "
            "verification_status or review_status records independent verification, or a revision that demotes "
            "the four rows to the ledger's vocabulary ('abstract-read' / 'unresolved')."
        ),
    },
]

findings = [
    {
        "id": "F-W061-F2AB-01",
        "severity": "positive",
        "finding": (
            "Identity and class binding clean at 5476a3f2c6bc: exactly one class_id AF-SCC-C2-VAC-GEN, "
            "node_id F2a, class_components censorship=SCC / regularity_token=C2, conclusion family SCC. "
            "Probe P1 pass."
        ),
        "evidence_refs": [f"{rel(TASK / 'probe_f2a_rev12_output.json')}#P1-IDENTITY-CLASS-BINDING"],
    },    {
        "id": "F-W061-F2AB-02",
        "severity": "positive",
        "finding": (
            "The rev11->rev12 repair set is independently verified at the pinned bytes: strict YAML census "
            "finds 0 duplicate mapping keys in F2a/F1/F2b; class_contract_pointer resolves inside canonical "
            "research_map/formulation_taxonomy.yaml#classes.AF-SCC-C2-VAC-GEN; D0 is re-typed as a tagged "
            "disjoint union over the bare index r and quantifiers.formal binds 'forall r in D0'; revision_history "
            "indices are monotone 1..10; revised_at 00:31:41 is behind the file mtime 00:32:02 and the wall "
            "clock; extension_predicate 'proper_future_extension_in_class' is present and D3.definition_ref "
            "resolves to it. Probes P9/P10 pass. The worker-096 BEFORE-01/02/03 and worker-005 F2-01/02/03 "
            "rev11 defect classes are therefore closed at rev12."
        ),
        "evidence_refs": [
            f"{rel(TASK / 'probe_f2a_rev12_output.json')}#P9-REV11-REPAIRS-AT-REV12",
            f"schemas/af_scc_c2_vacuum.yaml#sha256:{reviewed_sha[:12]}",
        ],
    },
    {
        "id": "F-W061-F2AB-03",
        "severity": "positive",
        "finding": (
            "R22 adjudication (worker-096 W096-F2A-AFTER-01 + worker-005 HF-W005-F2D-01): the claim is "
            "FALSIFIED at the current manifest. The canonical gate tool (000e09e46b2f, rule_spec 40f9bb9e) "
            "returns verdict=pass failed_rules=[] exit=0 on the pinned bytes under KEY_MANIFEST 014e2d301978 "
            "(rev28); replaying the same tool against the rev27 manifest fce91948ba3a in a shadow tree "
            "reproduces verdict=fail failed_rules=['R22'] for exactly the six rev12 keys. The finding was "
            "manifest-staleness, not a schema defect; its own falsifier is met."
        ),
        "evidence_refs": [
            f"{rel(GATE_CUR)}#sha256:{h12(GATE_CUR)}",
            f"{rel(GATE_R27)}#sha256:{h12(GATE_R27)}",
            f"artifacts/formulation/KEY_MANIFEST.json#sha256:{pm['artifacts/formulation/KEY_MANIFEST.json']['measured'][:12]}",
        ],
    },
    {
        "id": "F-W061-F2AB-04",
        "severity": "positive",
        "finding": (
            "Standing structural controls pass at the pinned triple: canonical gate verdict=pass; "
            "class_separation.py finds nothing on the pinned text and the frozen regression corpus scores "
            "leaks 17/17, controls 10/10, FP 0, FN 0; F1/F2a/F2b agree on all 12 restricting data-class paths "
            "(2 residual differences are gloss-only); the conclusion surface carries no WCC/visibility content "
            "and asserts no C0 token. Probes P11/P12/P13 pass."
        ),
        "evidence_refs": [
            f"{rel(TASK / 'probe_f2a_rev12_output.json')}#P11-CLASS-SEPARATION",
            f"{rel(TASK / 'probe_f2a_rev12_output.json')}#P12-SIBLING-DATA-CLASS",
            f"{rel(TASK / 'probe_f2a_rev12_output.json')}#P13-CONCLUSION-DIRECTION",
        ],
    },
    {
        "id": "F-W061-F2AB-05",
        "severity": "soft",
        "finding": (
            "review_status drift (worker-096 W096-F2A-AFTER-02): F2a declares independent_reviewers=[] and "
            f"verdict=pending while the live map ledger at the pinned hash records {P7['map_reviews_at_pin']['count']} "
            "verdict(s), including 10 revise and 1 accept (worker-089). Classified SOFT/process, not a hard "
            "failure: the field is an authoring-time snapshot taken before any rev12 review existed, and the "
            "authoritative review state is research_map/research_map.json#reviews. Recommendation: refresh the "
            "field at the next revision or record explicitly that the map ledger dominates it."
        ),
        "evidence_refs": [
            f"{rel(TASK / 'probe_f2a_rev12_output.json')}#P7-REVIEW-STATUS-LEDGER",
            "research_map/research_map.json#reviews",
        ],
    },
    {
        "id": "F-W061-F2AB-06",
        "severity": "soft",
        "finding": (
            "Index pin staleness (worker-005 HF-W005-F2D-02): schemas/af_scc_regularities.yaml (94562101a816) "
            "still pins components C2 -> b6123750b37d and C0 -> 1bb78ce9b357, both superseded rev11 hashes; "
            "live bytes are 5476a3f2c6bc / 55d0a1ea9bda and FROZEN rev28 pins both. This is a defect of the "
            "index file, not of F2a; the index must be re-pinned before it can be used as a binding surface."
        ),
        "evidence_refs": [
            f"schemas/af_scc_regularities.yaml#sha256:{h12(INDEX)}",
            f"{rel(TASK / 'probe_f2a_rev12_output.json')}#P8-INDEX-PIN-ADJUDICATION",
        ],
    },
    {
        "id": "F-W061-F2AB-07",
        "severity": "advisory",
        "finding": (
            "Non-vacuity branch coverage (worker-059 F-059-F2A-02): genericity.ambient_space justifies "
            "non-emptiness with 'X_vac is a closed subset of a Banach space, hence Baire', which covers the "
            "Sobolev branch r=(sobolev,s,delta) only; D0 also contains the Frechet smooth-with-decay branch "
            "(declared in genericity.topology_or_measure). No semantic change is implied; a branchwise Baire "
            "statement is needed before non-vacuity can be read for all r in D0."
        ),
        "evidence_refs": [f"{rel(TASK / 'probe_f2a_rev12_output.json')}#P14-NONVACUITY-BRANCHWISE"],
    },
    {
        "id": "F-W061-F2AB-08",
        "severity": "cross-class-measured",
        "finding": (
            "The same binding axes are family-wide. Measured: F1 and F2b both declare "
            f"consistency_evidence_sha256={xb['F1']['declared_consistency_evidence'][:12]} (stale, measured "
            f"{xb['measured_consistency_evidence'][:12]}); neither F1 nor F2b names VOCAB_ALIASES.json; F1's "
            f"conclusion token {xb['F1']['conclusion_type']} is literally in the F0 allowed list while its "
            f"genericity.kind {xb['F1']['genericity_kind']} needs the same alias adjudication as F2a. This is "
            "recorded as a measured fact for the controller, not as a verdict on F1/F2b; a single F0 / "
            "alias-registry repair may be cheaper than three per-schema edits."
        ),
        "evidence_refs": [
            f"{rel(TASK / 'probe_f2a_rev12_output.json')}#cross_class_binding",
            f"schemas/af_wcc_vacuum.yaml#sha256:{pm['schemas/af_wcc_vacuum.yaml']['measured'][:12]}",
            f"schemas/af_scc_c0_vacuum.yaml#sha256:{pm['schemas/af_scc_c0_vacuum.yaml']['measured'][:12]}",
        ],
    },
]

review = {
    "task_id": TASK_ID,
    "event_kind": "independent_review",
    "created_at": NOW.isoformat(timespec="seconds"),
    "reviewer": "worker-061",
    "target": {
        "node_id": "F2a",
        "class_id": "AF-SCC-C2-VAC-GEN",
        "gate": "G-FORM",
        "artifact": "schemas/af_scc_c2_vacuum.yaml",
        "reviewed_sha256": reviewed_sha,
    },
    "verdict": probe["verdict"],
    "score": probe["score"],
    "hard_failures": hard_failures,
    "findings": findings,
    "probes": probe["probes"],
    "adjudications": probe["adjudications"],
    "gate_matrix": gate,
    "evidence_refs": [
        f"schemas/af_scc_c2_vacuum.yaml#sha256:{reviewed_sha[:12]}",
        f"{rel(TASK / 'probe_f2a_rev12_output.json')}#sha256:{h12(TASK / 'probe_f2a_rev12_output.json')}",
        f"{rel(GATE_CUR)}#sha256:{h12(GATE_CUR)}",
        f"{rel(GATE_R27)}#sha256:{h12(GATE_R27)}",
        f"research_map/formulation_taxonomy.yaml#sha256:{pm['research_map/formulation_taxonomy.yaml']['measured'][:12]}",
        f"artifacts/formulation/FROZEN.json#sha256:{pm['artifacts/formulation/FROZEN.json']['measured'][:12]}",
        f"artifacts/formulation/VOCAB_ALIASES.json#sha256:{pm['artifacts/formulation/VOCAB_ALIASES.json']['measured'][:12]}",
        f"ledger/theorems.jsonl#sha256:{h12(LEDGER)}",
        f"{rel(W029_SNAP)}#sha256:{h12(W029_SNAP)}",
        f"schemas/af_scc_regularities.yaml#sha256:{h12(INDEX)}",
    ],
    "next_falsifier": probe["next_falsifier"],
    "independence": {
        "author_of_target": "astra-lead-formulation (rev12 authored via artifacts/formulation/tools/close_findings_rev27.py)",
        "reviewer_is_author": False,
        "correlated_exposure": (
            "Follow-on to W061-F2A-INDEP-REV-01 (rev11) and W061-F1-REV12-GATE-03: the reviewer has read this "
            "schema family across three revisions. The hard-failure axes were selected from the open claims of "
            "worker-096/worker-005/worker-059/worker-029/worker-039, so finding-selection is correlated with "
            "those reviewers; the pass/fail computations themselves are fresh machine runs over the pinned bytes."
        ),
        "conflicts": "none declared; no artifact in the formulation tree was modified",
    },
    "scope_limits": probe["scope_limits"] + [
        "The reviewer's own earlier F1 rev12 accept (W061-F1-REV12-GATE-03) did not include the P2/P3/P4 axes; F-W061-F2AB-08 records the measured cross-class facts and that accept should be read with this scope limit.",
        "research_map.json is live: the map read for the F-05 count was updated 2026-09-12T00:43:08+08:00; the controller must re-measure review coverage at ingest.",
    ],
    "authority_note": probe["authority_note"],
}

review_path = TASK / "REVIEW.json"
review_path.write_text(json.dumps(review, indent=1))

# ---- REVIEW.md -----------------------------------------------------------------
lines = [
    f"# {TASK_ID} — F2a (AF-SCC-C2-VAC-GEN) rev12 binding review",
    "",
    f"- target: `schemas/af_scc_c2_vacuum.yaml` @ `{reviewed_sha}`",
    f"- verdict: **{probe['verdict']}** (score {probe['score']})",
    f"- reviewer: worker-061, {NOW.isoformat(timespec='seconds')}",
    "",
    "## Hard failures",
]
for hf in hard_failures:
    lines += [f"### {hf['id']} — {hf['axis']}", "", hf["finding"], "",
              "Falsifier: " + hf["falsifier"], ""]
lines += ["## Findings", ""]
for f in findings:
    lines += [f"### {f['id']} ({f['severity']})", "", f["finding"], ""]
lines += [
    "## Adjudications of open claims",
    "",
]
for a in probe["adjudications"]:
    lines += [f"- **{', '.join(a['claim_ids'])}** — {a['disposition']}"]
lines += ["", "## Probe matrix", "", "| probe | status | hard |", "|---|---|---|"]
for p in probe["probes"]:
    lines.append(f"| {p['id']} | {p['status']} | {p['hard']} |")
lines += ["", "## Authority", "", review["authority_note"], ""]
(TASK / "REVIEW.md").write_text("\n".join(lines))

# ---- CHECKPOINT.json -----------------------------------------------------------
artifacts = {}
for p in sorted(TASK.rglob("*")):
    if p.is_file() and p.name not in ("CHECKPOINT.json", "SHA256SUMS"):
        artifacts[rel(p)] = {"sha256": sha256_path(p), "bytes": p.stat().st_size}
artifacts[rel(review_path)] = {"sha256": sha256_path(review_path), "bytes": review_path.stat().st_size}
checkpoint = {
    "task_id": TASK_ID,
    "created_at": NOW.isoformat(timespec="seconds"),
    "actor": "worker-061",
    "node_id": "F2a",
    "class_id": "AF-SCC-C2-VAC-GEN",
    "gate": "G-FORM",
    "reviewed_sha256": reviewed_sha,
    "verdict": probe["verdict"],
    "score": probe["score"],
    "hard_failures": [hf["id"] for hf in hard_failures],
    "artifacts": artifacts,
    "pins": {k: v["measured"] for k, v in pm.items() if isinstance(v, dict) and "measured" in v},
    "map_updated_at_at_emit": mapd.get("updated_at"),
    "authority_note": "Worker checkpoint only; not a controller checkpoint and not a gate verdict.",
}
cp_path = TASK / "CHECKPOINT.json"
cp_path.write_text(json.dumps(checkpoint, indent=1))
runtime_cp = REPO / "runtime/state/w061_f2a_rev12_bind_checkpoint.json"
shutil.copyfile(cp_path, runtime_cp)

# ---- SHA256SUMS ----------------------------------------------------------------
sums = []
for p in sorted(TASK.rglob("*")):
    if p.is_file() and p.name != "SHA256SUMS":
        sums.append(f"{sha256_path(p)}  {rel(p)}")
(TASK / "SHA256SUMS").write_text("\n".join(sums) + "\n")

# ---- outbox events -------------------------------------------------------------
def ev(eid, etype, **kw):
    base = {"event_id": eid, "event_type": etype, "created_at": NOW.isoformat(timespec="seconds"),
            "actor": "worker-061", "task_id": TASK_ID, "node_id": "F2a",
            "class_id": "AF-SCC-C2-VAC-GEN", "gate": "G-FORM"}
    base.update(kw)
    return base


refs = review["evidence_refs"]
next_f = probe["next_falsifier"]
events = [
    ev(f"w061-f2ab-{STAMP}-claim", "claim",
       conclusion_type="independent_review_verdict",
       statement=(f"Independent machine-checked review of F2a (AF-SCC-C2-VAC-GEN) at the pinned canonical rev12 "
                  f"bytes {reviewed_sha[:12]}: verdict revise, score {probe['score']}, four hard failures "
                  "(F0 conclusion-vocabulary binding unbound; F0 genericity-vocabulary binding unbound; "
                  "declared consistency-evidence hash one regeneration stale; four l1_ledger_refs claiming "
                  "verified_by_L1 against a ledger that records abstract-read / not_independently_reviewed). "
                  "All five rev11 defect classes are independently confirmed repaired, the canonical gate passes "
                  "under the rev28 manifest, and the rev11-vintage R22 failure is reproduced only under the "
                  "rev27 manifest, so the open R22 claim is falsified at current state."),
       assumptions=["the pinned bytes and the pinned F0/FROZEN/manifest/ledger artifacts are the revision under test; any byte change voids the verdict",
                    "alias-equivalence is not treated as satisfying the F0 allowed-list binding unless the artifact or the controller binds it",
                    "worker events cannot set node status, validation_status or a gate verdict"],
       falsifier=next_f, evidence_refs=refs,
       artifact_refs=[f"{rel(review_path)}#sha256:{h12(review_path)}",
                      f"{rel(TASK / 'probe_f2a_rev12_output.json')}#sha256:{h12(TASK / 'probe_f2a_rev12_output.json')}"]),
    ev(f"w061-f2ab-{STAMP}-artifact-probe", "artifact",
       artifact_type="machine_probe_output", path=rel(TASK / "probe_f2a_rev12_output.json"),
       sha256=sha256_path(TASK / "probe_f2a_rev12_output.json"), validation_status="unverified",
       note="15 probes (P1-P15) + two-manifest gate replay over the pinned bytes; rerunnable via run_all.py."),
    ev(f"w061-f2ab-{STAMP}-artifact-gate-current", "artifact",
       artifact_type="canonical_gate_report", path=rel(GATE_CUR), sha256=sha256_path(GATE_CUR),
       validation_status="unverified",
       note="check_class_schema.py under KEY_MANIFEST rev28 014e2d30: verdict=pass failed_rules=[] exit=0."),
    ev(f"w061-f2ab-{STAMP}-artifact-gate-rev27", "artifact",
       artifact_type="gate_replay_report", path=rel(GATE_R27), sha256=sha256_path(GATE_R27),
       validation_status="unverified",
       note="same gate tool replayed with rev27 manifest fce91948 in a shadow tree: verdict=fail failed_rules=['R22']."),
    ev(f"w061-f2ab-{STAMP}-artifact-review", "artifact",
       artifact_type="independent_review_json", path=rel(review_path), sha256=sha256_path(review_path),
       validation_status="unverified",
       note="Worker evidence, not a gate verdict and not a node completion claim; controller/lead adjudication required."),
    ev(f"w061-f2ab-{STAMP}-artifact-checkpoint", "artifact",
       artifact_type="checkpoint_json", path=rel(cp_path), sha256=sha256_path(cp_path),
       validation_status="unverified",
       note="Hash ledger for every emitted artifact; copy at runtime/state/w061_f2a_rev12_bind_checkpoint.json."),
    ev(f"w061-f2ab-{STAMP}-review", "review",
       reviewer="worker-061", target_id="F2a", artifact="schemas/af_scc_c2_vacuum.yaml",
       artifact_sha256=reviewed_sha, reviewed_sha256=reviewed_sha,
       verdict=probe["verdict"], score=probe["score"],
       hard_failures=[f"{hf['id']}: {hf['axis']}" for hf in hard_failures],
       findings=[f"{f['id']} [{f['severity']}] {f['finding'][:400]}" for f in findings],
       evidence_refs=refs, next_falsifier=next_f,
       independence=review["independence"], authority_note=review["authority_note"]),
    ev(f"w061-f2ab-{STAMP}-final", "status", status="active", hours=0.7,
       summary=("Bounded class-bound task complete: probe matrix, two-manifest gate replay, REVIEW.json/.md, "
                "CHECKPOINT.json + runtime/state copy, SHA256SUMS written and hashed; review + artifact + claim "
                "events emitted. No node status, validation_status or gate verdict is claimed (worker authority "
                "rule). Verdict binds only to 5476a3f2c6bc; the map ledger should be re-measured at ingest."),
       evidence_refs=[f"{rel(review_path)}#sha256:{h12(review_path)}",
                      f"{rel(cp_path)}#sha256:{h12(cp_path)}",
                      f"comms/outbox/worker-061.jsonl#w061-f2ab-{STAMP}-review"],
       next_falsifier=next_f),
]
with OUTBOX.open("a") as fh:
    for e in events:
        fh.write(json.dumps(e) + "\n")

print(json.dumps({
    "review": rel(review_path), "sha256": sha256_path(review_path),
    "checkpoint": rel(cp_path), "sha256": sha256_path(cp_path),
    "runtime_checkpoint": rel(runtime_cp),
    "event_ids": [e["event_id"] for e in events],
    "verdict": probe["verdict"], "score": probe["score"],
    "hard_failures": [hf["id"] for hf in hard_failures],
}, indent=1))
