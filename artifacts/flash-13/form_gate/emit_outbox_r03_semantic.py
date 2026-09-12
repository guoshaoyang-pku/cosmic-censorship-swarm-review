#!/usr/bin/env python3
"""Emit the rev1.3 R03-reading events to comms/outbox/deepseek-flash-13.jsonl.

One bounded class-bound task (deepseek-flash-13 / worker 013, standing card
assign-FORM-GATE-01-20260911T2331, node F1 / G-CLASSBIND, classes F1+F2a+F2b):
make the R03 reading question decidable with controls, supersede gate 1.2's literal criterion with
a measured semantic realization criterion, and report both readings.

Emits (all schema-validated locally before append, deduped by event_id):
  * 12 artifact events (gate code, readings record, canonical recheck, reports, manifests, tools,
    README, archived 1.2 report)
  * 1 claim event (conclusion_type stability_result; falsifier in-event)
  * 1 gate proposal event (verdict pending: proposal only, owner adjudication open)
  * 1 status event
Aborts before writing anything if FROZEN rev29 or any canonical schema byte moved, if the readings
audit verdict is not pass, or if any cited path/hash does not match disk.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUTBOX = REPO / "comms/outbox/deepseek-flash-13.jsonl"
FROZEN = REPO / "artifacts/formulation/FROZEN.json"
CANON = {
    "AF-WCC-VAC-GEN": ("artifacts/formulation/schemas/af_wcc_vacuum.yaml", "d9cebb9404b2"),
    "AF-SCC-C2-VAC-GEN": ("artifacts/formulation/schemas/af_scc_c2_vacuum.yaml", "e9a27996dfd3"),
    "AF-SCC-C0-VAC-GEN": ("artifacts/formulation/schemas/af_scc_c0_vacuum.yaml", "b2ab6acb2bbe"),
}
FROZEN_SHA16 = "815e08079aefbc16"
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
NOW = datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")
TAG = "f13-r03sem-" + NOW.replace("-", "").replace(":", "").replace("+", "").replace("T", "T")[:15]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def ref(rel: str) -> str:
    return f"{rel}#{sha(REPO / rel)[:16]}"


ARTIFACTS = [
    ("artifacts/flash-13/form_gate/check_class_schema.py", "gate_code",
     "FORM-GATE-01 rev1.3: R03 semantic realization criterion; literal reading reported; "
     "--r03-mode literal reproduces rev1.2 pass/fail exactly."),
    ("artifacts/flash-13/form_gate/r03_readings_rev29.json", "gate_evidence",
     "Readings audit at FROZEN rev29: assertions A1-A6 pass; 4 controls L-accepts/S-rejects; "
     "canonical WCC L-fail/S-pass on (q,t0); m25 still caught."),
    ("artifacts/flash-13/form_gate/canonical_recheck_rev29_v13.json", "gate_evidence",
     "Three canonical schemas pass all 16 rules under S at pinned rev13 bytes."),
    ("artifacts/flash-13/form_gate/gate_report_rev29_r3_semantic.json", "gate_evidence",
     "CLI canonical run output under gate 1.3 (per-rule pass, frozen_match=true)."),
    ("artifacts/flash-13/form_gate/fixture_suite_report.json", "gate_evidence",
     "Acceptance suite on the repaired corpus: 3/3 positives, 25/25 mutants expected rule, "
     "17/25 single-rule keyed, 5/6 rephrased caught (metrics identical to rev1.2)."),
    ("artifacts/flash-13/form_gate/gate_report.json", "gate_evidence",
     "CLI acceptance summary for the repaired corpus."),
    ("artifacts/flash-13/form_gate/fixtures_r03/manifest.json", "gate_evidence",
     "10 R03 controls with expected dual-reading matrix and per-file sha256."),
    ("artifacts/flash-13/form_gate/fixtures_v13/manifest.json", "gate_evidence",
     "Repaired corpus manifest: one logical kind-token diff per file, legacy+new sha256."),
    ("artifacts/flash-13/form_gate/make_r03_controls.py", "gate_tooling",
     "Control generator (canonical-derived quantifier-only mutations)."),
    ("artifacts/flash-13/form_gate/make_fixtures_v13.py", "gate_tooling",
     "Corpus repair generator (refuses non-kind edits)."),
    ("artifacts/flash-13/form_gate/r03_readings_audit.py", "gate_tooling",
     "Readings audit driver."),
    ("artifacts/flash-13/form_gate/README.md", "gate_documentation",
     "Revision 1.3 section: change, delta, controls, corpus repair, non-claims, falsifiers."),
    ("artifacts/flash-13/form_gate/legacy_v12/fixture_suite_report.v12_r03.json", "gate_evidence",
     "Archived rev1.2 suite report (byte-identical to the 07674bac2ab2 citation)."),
]


def check_preconditions():
    problems = []
    if sha(FROZEN)[:16] != FROZEN_SHA16:
        problems.append("FROZEN.json moved")
    for cid, (rel, prefix) in CANON.items():
        got = sha(REPO / rel)[:12]
        if got != prefix:
            problems.append(f"{cid} {rel} {got} != {prefix}")
    rec = json.loads((HERE / "r03_readings_rev29.json").read_text())
    if rec.get("verdict") != "pass" or not all(rec.get("assertions", {}).values()):
        problems.append("r03_readings_rev29.json verdict is not pass")
    for rel, _t, _n in ARTIFACTS:
        if not (REPO / rel).exists():
            problems.append(f"missing artifact {rel}")
    return problems


def main() -> int:
    problems = check_preconditions()
    if problems:
        print("ABORT (nothing written):")
        for p in problems:
            print("  -", p)
        return 1
    events = []
    evidence = [ref(rel) for rel, _t, _n in ARTIFACTS] + [ref(f"artifacts/formulation/{p}")
                                                          for p in ("FROZEN.json",)]
    evidence += [ref(CANON[c][0]) for c in sorted(CANON)]

    for rel, atype, note in ARTIFACTS:
        slug = (rel.replace("artifacts/flash-13/form_gate/", "").replace("/", "-")
                .replace("_", "").replace(".json", "").replace(".py", "").replace(".md", ""))
        events.append({
            "event_id": f"{TAG}-art-" + slug[:24],
            "event_type": "artifact", "created_at": NOW, "actor": "deepseek-flash-13",
            "node_id": "F1", "gate": "G-CLASSBIND",
            "class_id": ";".join(CLASS_IDS), "class_ids": CLASS_IDS,
            "artifact_type": atype, "path": rel, "sha256": sha(REPO / rel),
            "validation_status": "unverified", "note": note,
            "evidence_refs": evidence[:14],
        })

    events.append({
        "event_id": f"{TAG}-claim", "event_type": "claim", "created_at": NOW,
        "actor": "deepseek-flash-13", "node_id": "F1", "gate": "G-CLASSBIND",
        "class_id": ";".join(CLASS_IDS), "class_ids": CLASS_IDS,
        "conclusion_type": "stability_result",
        "statement": (
            "Measured at FROZEN rev29 815e08079aefbc / rev13 canonicals (WCC d9cebb9404b2, "
            "C2 e9a27996dfd3, C0 b2ab6acb2bbe): (1) R03 admits two readings; under the literal "
            "reading L only canonical WCC fails, on exactly the tuple binder '(q,t0)'; under the "
            "semantic realization reading S all three canonicals pass all 16 rules. (2) S is "
            "strictly stronger, not a relaxation: 4 controls (c01 declared-kind reorder, c02 "
            "quantifier clause deleted with variables left in the body, c09 extra body keyword, "
            "c10 declared variable only before its quantifier) are ACCEPTED by L and REJECTED by S; "
            "m25_wcc_binder_unused still fails R03; consistent alpha-rename c05 is not punished. "
            "(3) The legacy 34-file fixture corpus declared ordered[2].kind='exists' while its own "
            "sentence says 'not exists p' -- a defect L cannot see; fixtures_v13 repairs the kind "
            "token only and reproduces the rev1.2 suite metrics exactly (3/3 positives, 25/25 "
            "mutants expected rule, 17/25 single-rule-keyed, 5 caught/1 blind rephrased). "
            "Conclusion: the earlier F-GATE-6 'canonical WCC fails R03' result was a false positive "
            "of the rev1.2 literal test, not a defect of the canonical schema; that earlier claim "
            "is superseded by this measurement."),
        "assumptions": [
            "structural R01-R16 conformance only: no mathematical truth, non-vacuity, citation "
            "adjudication, node completion or gate verdict is claimed",
            "which reading of R03 is normative remains the rule owner's adjudication "
            "(astra-life05-verify-gform-r3); this claim measures both and recommends S, it does not "
            "overrule the owner",
            "FROZEN rev29 pins the three canonical hashes measured here; any republication or byte "
            "change voids the readings and requires a re-run",
            "gate 1.3 supersedes 1.2 in place; 1.2's bytes are not archived byte-exactly, but "
            "--r03-mode literal reproduces its pass/fail with 0 mismatches against the archived "
            "1.2 suite report",
            "the repaired corpus under fixtures_v13/ is this worker's own artifact; the legacy "
            "corpus is preserved unmodified under fixtures/ and archived reports under legacy_v12/",
        ],
        "falsifier": (
            "A schema certified conforming by the rule owner that S rejects; or a schema S accepts "
            "whose formal sentence does not realise its declared quantifier structure; or any "
            "canonical/FROZEN byte change; or the rule owner ruling L normative (then the E1a/E1b "
            "one-clause repair is still required and S also accepts it); or a reachable fixture on "
            "which L and S disagree other than c07/c01/c02/c09/c10."),
        "evidence_refs": evidence,
        "artifact_refs": [{"path": rel, "sha256": sha(REPO / rel)} for rel, _t, _n in ARTIFACTS],
    })

    events.append({
        "event_id": f"{TAG}-gate-proposal", "event_type": "gate", "created_at": NOW,
        "actor": "deepseek-flash-13", "node_id": "F1", "gate_id": "G-CLASSBIND",
        "class_id": ";".join(CLASS_IDS), "class_ids": CLASS_IDS, "verdict": "pending",
        "scope": ("F1/F2a/F2b rev13 canonical schemas at FROZEN rev29; R03 semantic realization "
                  "reading S; literal reading L reported"),
        "criteria": (
            "PROPOSAL ONLY, not set by this worker. Measured: under S, all three canonical schemas "
            "pass R01-R16 at frozen bytes (gate sha256 in evidence), fixture suite exit 0 with "
            "25/25 mutants keyed to their expected rule, 10/10 controls match the expected L/S "
            "matrix, and 4 controls prove S catches scope errors L accepts. Under L (rev1.2) only "
            "canonical WCC fails, on '(q,t0)'. Proposed disposition: G-CLASSBIND is passable at "
            "these bytes under S; the F-GATE-6 failure is withdrawn as a rev1.2 literal-test false "
            "positive. Requested independent review before any gate movement; the R03 reading "
            "adjudication stays with the rule owner, and if the owner rules L then the worker-064 "
            "E1a/E1b repair (accepted by S) is the path, not a gate pass."),
        "supersedes": "f13-r29r03-20260912T010432-gate-proposal",
        "evidence_refs": evidence,
    })

    events.append({
        "event_id": f"{TAG}-status", "event_type": "status", "created_at": NOW,
        "actor": "deepseek-flash-13", "node_id": "F1", "gate": "G-CLASSBIND",
        "class_id": ";".join(CLASS_IDS), "class_ids": CLASS_IDS,
        "status": "active", "hours": 1.2,
        "summary": ("One class-bound task taken (standing FORM-GATE-01 card; no newer inbox card): "
                    "R03 reading decided by controls. Gate rev1.3 supersedes the literal test with "
                    "semantic realization; both readings reported. Self-refutation disclosed: the "
                    "rev1.2 F-GATE-6 canonical-WCC failure is withdrawn. Corpus kind defect found "
                    "and repaired in fixtures_v13 (legacy preserved). Proposal pending; owner "
                    "adjudication open. No canonical bytes modified."),
        "next_falsifier": ("Independent reviewer re-runs gate 1.3 on the frozen bytes and tries to "
                           "build an S-accepted schema whose sentence does not realise its declared "
                           "quantifier structure, or an owner-certified conforming schema S rejects."),
        "evidence_refs": evidence,
    })

    # local schema-required-key validation + dedupe + append
    required = {
        "artifact": ["event_id", "event_type", "created_at", "actor", "node_id", "artifact_type",
                     "path", "sha256", "validation_status"],
        "claim": ["event_id", "event_type", "created_at", "actor", "class_id", "statement",
                  "conclusion_type", "assumptions", "falsifier", "evidence_refs"],
        "gate": ["event_id", "event_type", "created_at", "actor", "gate_id", "verdict"],
        "status": ["event_id", "event_type", "created_at", "actor", "status"],
    }
    existing = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            if line.strip():
                try:
                    existing.add(json.loads(line).get("event_id"))
                except Exception:
                    pass
    fresh = []
    for e in events:
        missing = [k for k in required[e["event_type"]] if k not in e]
        if missing:
            print("ABORT: event missing keys", e["event_id"], missing)
            return 1
        if e["event_id"] in existing:
            print("skip duplicate", e["event_id"])
            continue
        fresh.append(e)
    with OUTBOX.open("a") as f:
        for e in fresh:
            f.write(json.dumps(e, sort_keys=True) + "\n")
    print(f"appended {len(fresh)} events to {OUTBOX.relative_to(REPO)} (tag {TAG})")
    for e in fresh:
        print(" ", e["event_type"], e["event_id"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
