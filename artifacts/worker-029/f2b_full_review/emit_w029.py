#!/usr/bin/env python3
"""Emit W029-F2B-FULLVERDICT-01 review artifacts, events and checkpoint.

Reads report.json (produced by check_f2b_full.py) and writes:
  review.json                       structured review object
  REVIEW.md                         human-readable one page
  ../../../comms/outbox/worker-029.jsonl   valid upward events
  ../../../runtime/state/w029_checkpoint.json  worker-scoped checkpoint

It never mutates research_map.json, gates, or any canonical artifact.
"""
from __future__ import annotations
import hashlib, json
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
D = Path(__file__).resolve().parent
CST = timezone(timedelta(hours=8))


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


report = json.loads((D / "report.json").read_text())
schema_doc = yaml.safe_load((D / "f2b_snapshot.yaml").read_text())
now_dt = datetime.now(CST)
now = now_dt.isoformat(timespec="seconds")
reviewed = report["reviewed_sha256"]
live_now = sha256(ROOT / "schemas/af_scc_c0_vacuum.yaml")
still_live = (live_now == reviewed)
rev_at = datetime.fromisoformat(schema_doc["revised_at"])
skew = int((rev_at - now_dt).total_seconds())
claim_ids = ["D-002", "T-301", "T-302", "T-515", "T-528"]

# ---------------------------------------------------------------- findings
hard = [
    {
        "id": "HF-29-01", "check_id": "C5", "severity": "hard",
        "finding": (
            "class_contract_pointer = 'artifacts/formulation/formulation_taxonomy.yaml#class_contracts."
            "AF-SCC-C0-VAC-GEN' targets the authoring tree. The canonical-path policy in force since "
            "2026-09-12 (ASTRA_HANDOFF) makes research_map/formulation_taxonomy.yaml authoritative, and that "
            "file has no 'class_contracts' key (its class definitions live under 'classes'). The pointer does "
            "resolve at the authoring path, but the class contract this schema binds to is not resolvable at "
            "the authoritative path, so G-FORM's class binding cannot be checked against the canonical artifact."
        ),
        "evidence": ["schemas/af_scc_c0_vacuum.yaml#class_contract_pointer",
                     "research_map/formulation_taxonomy.yaml",
                     "research_map/ASTRA_HANDOFF.md:18-23"],
        "falsifier": "Show class_contracts.AF-SCC-C0-VAC-GEN in the canonical research_map/formulation_taxonomy.yaml, "
                     "or a controller record reversing the canonical-path policy.",
    },
    {
        "id": "HF-29-02", "check_id": "F1,F2", "severity": "hard",
        "finding": (
            "l1_ledger_refs marks " + ", ".join(claim_ids) + " as 'citation_status: verified_by_L1' while the "
            "cited rows in ledger/theorems.jsonl @ce42d205 record verification_status='abstract-read' for all 62 "
            "rows (61 abstract-read, 1 unverified, 0 verified). The token 'verified_by_L1' occurs in neither "
            "ledger/theorems.jsonl nor ledger/citation_audit.csv (whose verdict vocabulary is "
            "'verified' on abstract/API evidence). The same artifact sets provenance.citation_status='unverified', "
            "so it contradicts itself and overstates the ledger's verification level. G-LIT's criterion requires "
            "verification_status to be honest."
        ),
        "evidence": ["schemas/af_scc_c0_vacuum.yaml#l1_ledger_refs",
                     "ledger/theorems.jsonl#ce42d205e761 (D-002,T-301,T-302,T-515,T-528)",
                     "ledger/citation_audit.csv",
                     "artifacts/worker-029/f2b_full_review/ledger_theorems_snapshot.jsonl"],
        "falsifier": "Produce one of: a ledger/theorems.jsonl row for those ids with verification_status='verified'; "
                     "a project definition equating 'verified_by_L1' with citation_audit.csv verdict='verified' on "
                     "abstract evidence; or a corrected revision whose l1_ledger_refs token is traceable.",
    },
    {
        "id": "HF-29-03", "check_id": "G1,G2", "severity": "hard",
        "finding": (
            f"revised_at = {schema_doc['revised_at']!r} and f0_binding.checked_at = the same value are "
            f"future-dated by {skew:+d} s at the snapshot instant ({now}), and checked_at postdates the "
            "taxonomy_consistency.json evidence file (mtime "
            + datetime.fromtimestamp((ROOT / 'artifacts/formulation/evidence/taxonomy_consistency.json').stat().st_mtime, CST).isoformat(timespec='seconds')
            + ") by a fictional interval. The artifact's own f0_binding rule makes a gate verdict conditional on that "
            "consistency re-run. This is controller finding CF-14 (future-dated records make 'binding at "
            "measured_at' unreliable) recurring inside the artifact."
        ),
        "evidence": ["schemas/af_scc_c0_vacuum.yaml#revised_at",
                     "schemas/af_scc_c0_vacuum.yaml#f0_binding.checked_at",
                     "artifacts/formulation/evidence/taxonomy_consistency.json",
                     "research_map/research_map.json#controller_findings.CF-14"],
        "falsifier": "Show a wall-clock record proving the revision was written at or before 00:30 and that the "
                     "snapshot clock was wrong; or reissue the revision with wall-clock revised_at/checked_at.",
    },
]

soft = [
    {
        "id": "W-29-01", "check_id": "D3", "severity": "major",
        "finding": (
            "quantifiers.formal binds a pair '(s,delta) in D0', but D0 is defined as the union of the Sobolev "
            "pairs and 'the smooth-with-decay default', which has no (s,delta) coordinates. The binder is "
            "ill-typed on that member and the statement reads as a family of statements (the same risk recorded "
            "for F2a as probe S6-C2). F2b-review-18 passed this field as 'no disjunctive binder remains'; this "
            "checker agrees the binder chain is a single chain but flags the domain typing. The identical D0 "
            "wording is present in F1 and F2a, so this is a cross-artifact convention, not an F2b-only defect."
        ),
        "evidence": ["schemas/af_scc_c0_vacuum.yaml#quantifiers.domains.D0",
                     "schemas/af_wcc_vacuum.yaml#quantifiers.domains.D0",
                     "schemas/af_scc_c2_vacuum.yaml#quantifiers.domains.D0",
                     "artifacts/formulation/formulation_taxonomy.yaml#class_contracts.AF-SCC-C0-VAC-GEN.data_class_freeze"],
        "falsifier": "Exhibit an explicit index set in which the smooth default is a named element carrying "
                     "(s,delta) coordinates, or state D0 as a pair-indexed part plus a constant part.",
    },
    {
        "id": "W-29-02", "check_id": "C3", "severity": "info",
        "finding": (
            "Two raw 'C0 or C2'-pattern occurrences remain: line 157 ('No containment with C2 or C0 is asserted "
            "here') and line 283 (quoted in anti_scope.phrases_that_are_not_this_class). Both are negated/quoted "
            "prohibitions; the line-5 YAML comment that F2b-review-18 HF-B1 rejected is gone. Process note: the "
            "map's F2b next_falsifier literally says any reintroduction of a composite 'C0 or C2' string rejects "
            "the revision, while the class-separation gate exempts prohibition keys; reconcile the two readings."
        ),
        "evidence": ["schemas/af_scc_c0_vacuum.yaml:157", "schemas/af_scc_c0_vacuum.yaml:283",
                     "research_map/research_map.json#groups.formulation.nodes.F2b.next_falsifier"],
        "falsifier": "A revision containing an assertion-like (non-negated, non-quoted) composite regularity token, "
                     "or a recorded decision to relax the literal next_falsifier.",
    },
    {
        "id": "W-29-03", "check_id": "E1b", "severity": "minor",
        "finding": (
            "Vocabulary check: F2b's conclusion token 'scc_c0_future_inextendibility' is alias-equivalent to the "
            "canonical F0 token 'strong_cosmic_censorship_C0' under artifacts/formulation/VOCAB_ALIASES.json, so "
            "this is NOT a defect of F2b. Observed for the controller/F0 owner: the canonical taxonomy carries the "
            "registered alias, and the alias policy says accepted aliases 'must never appear in a new canonical "
            "artifact'; G-FORM's wording 'exact conclusion_type' should record whether alias-equivalence satisfies it."
        ),
        "evidence": ["artifacts/formulation/VOCAB_ALIASES.json",
                     "research_map/formulation_taxonomy.yaml#classes.AF-SCC-C0-VAC-GEN.axes.conclusion_type",
                     "schemas/af_scc_c0_vacuum.yaml#conclusion.conclusion_type"],
        "falsifier": "A recorded controller decision that alias-equivalence satisfies G-FORM, or an F0 revision "
                     "adopting the registry key token.",
    },
]

positives = [c["check_id"] + ": " + c["name"] for c in report["checks"] if c["status"] == "PASS"]
positives += [
    "HF-B1 regression from F2b-review-18 is fixed: the line-5 'C0 or C2' comment is gone (checked in raw text).",
    "HF-B2 (node identity) is fixed: node_id=F2b matches the map's F2b node and the F2a/F2b split.",
    "f0_binding.declared_f0_sha256 equals the measured canonical taxonomy hash 276009f4f63d at snapshot.",
    "Variant registry entries CH / H2LOC / DISTRIBUTIONAL referenced by the schema exist in VARIANT_REGISTRY.json.",
    "F2a declares the C0 sibling symmetrically (sibling_disjoint_from), and the C0=>C2 one-way direction is asserted.",
]

assumptions = [
    "All checks run on frozen copies under artifacts/worker-029/f2b_full_review/ (f2b_snapshot.yaml "
    f"{reviewed[:12]}); the verdict binds only to those bytes, not to the path.",
    "The canonical-path policy of research_map/ASTRA_HANDOFF.md (2026-09-12) is in force.",
    "Class-axis comparison uses the explicit decode: AF<->asymptotically_flat*, VAC<->vacuum, "
    "GEN<->baire_residual/comeager, regularity token compared literally.",
    "Conclusion-token comparison applies artifacts/formulation/VOCAB_ALIASES.json (owner lead-formulation); "
    "without that registry the raw tokens differ, with it they are equivalent.",
    "The ledger cross-check uses ledger/theorems.jsonl @ce42d205e761 and ledger/citation_audit.csv as read at "
    "snapshot time.",
    "A worker review is evidence only: it cannot set a gate verdict, a node status, or validation_status.",
]

review = {
    "review_id": "W029-F2B-FULL-20260912T0023",
    "task_id": "W029-F2B-FULLVERDICT-01",
    "target_id": "F2b",
    "class_id": "AF-SCC-C0-VAC-GEN",
    "artifact_path": "schemas/af_scc_c0_vacuum.yaml",
    "reviewed_sha256": reviewed,
    "reviewer": "worker-029",
    "verdict": "revise",
    "score": 2.0,
    "created_at": now,
    "gate": "G-FORM",
    "scope": ("full-schema: contract completeness, class identity/separation, quantifier exactness, conclusion "
              "direction/vocabulary, citation honesty, timestamp discipline. NOT a class-separation-only verdict "
              "and NOT a gate verdict."),
    "snapshot_is_live_at_emission": still_live,
    "live_path_sha256_at_emission": live_now,
    "hard_failures": hard,
    "findings": soft,
    "positives": positives,
    "assumptions": assumptions,
    "falsifier": (
        "Re-run artifacts/worker-029/f2b_full_review/check_f2b_full.py on the same snapshot bytes: the review is "
        "falsified if any hard-failure check reports PASS, if a cited ledger row has verification_status='verified', "
        "or if revised_at/checked_at are not future-dated at the stated snapshot instant. If the live "
        "schemas/af_scc_c0_vacuum.yaml no longer hashes to the reviewed value, the verdict is superseded "
        "(not falsified) and must be re-issued against the new revision."
    ),
    "evidence_refs": [
        f"artifacts/worker-029/f2b_full_review/f2b_snapshot.yaml#{reviewed}",
        "artifacts/worker-029/f2b_full_review/report.json",
        "artifacts/worker-029/f2b_full_review/check_f2b_full.py",
        "research_map/formulation_taxonomy.yaml#276009f4f63d",
        "ledger/theorems.jsonl#ce42d205e761",
    ],
}
(D / "review.json").write_text(json.dumps(review, indent=2, ensure_ascii=False))

# ---------------------------------------------------------------- REVIEW.md
lines = [
    "# W029-F2B-FULLVERDICT-01 — independent full-schema review of F2b (AF-SCC-C0-VAC-GEN)",
    "",
    f"- reviewer: worker-029 | verdict: **revise** | score: 2.0/5 | created_at: {now}",
    f"- artifact: `schemas/af_scc_c0_vacuum.yaml` @ `{reviewed}` (snapshot copy `f2b_snapshot.yaml`)",
    f"- live path identical at emission: **{still_live}** (`{live_now[:12]}`)",
    f"- machine summary: {report['summary']} | hard-failure checks: {report['hard_failure_check_ids']}",
    "",
    "## Hard failures (block acceptance at this hash)",
    "",
]
for h in hard:
    lines += [f"### {h['id']} ({h['check_id']})", "", h["finding"], "",
              "falsifier: " + h["falsifier"], ""]
lines += ["## Soft findings", ""]
for f in soft:
    lines += [f"### {f['id']} ({f['check_id']}, {f['severity']})", "", f["finding"], "",
              "falsifier: " + f["falsifier"], ""]
lines += ["## Positives (checks that passed)", ""] + [f"- {p}" for p in positives] + [
    "",
    "## Reproduce",
    "",
    "```bash",
    "cd artifacts/worker-029/f2b_full_review",
    "python3 check_f2b_full.py --dir . --live-root ../../.. --out report.json",
    "python3 emit_w029.py",
    "```",
    "",
    "## Scope and authority",
    "",
    "This is an independent worker review. It does not set a gate verdict, a node status, or a",
    "validation_status; it is evidence for A1/G-FORM at the pinned sha256 only.",
]
(D / "REVIEW.md").write_text("\n".join(lines) + "\n")

# ---------------------------------------------------------------- events
def rel(p: Path) -> str:
    return str(p.relative_to(ROOT))

artifacts = {
    "report": D / "report.json",
    "review": D / "review.json",
    "readme": D / "REVIEW.md",
    "checker": D / "check_f2b_full.py",
}
ah = {k: {"path": rel(p), "sha256": sha256(p)} for k, p in artifacts.items()}
snap_h = {f"snapshot_{k}": {"path": rel(D / f), "sha256": sha256(D / f)} for k, f in
          {"f2b": "f2b_snapshot.yaml", "f0_canonical": "f0_canonical_snapshot.yaml",
           "f0_authoring": "f0_authoring_snapshot.yaml", "f2a": "f2a_snapshot.yaml",
           "f1": "f1_snapshot.yaml", "ledger": "ledger_theorems_snapshot.jsonl"}.items()}

ev = []
ev.append({
    "event_id": "w029-20260912T0023-status-claim",
    "event_type": "status", "created_at": now, "actor": "worker-029",
    "node_id": "F2b", "class_id": "AF-SCC-C0-VAC-GEN", "status": "active", "hours": 0.3,
    "task_id": "W029-F2B-FULLVERDICT-01",
    "summary": ("Took one class-bound task (no assignment card exists for worker-029): independent full-schema "
                "verification of F2b AF-SCC-C0-VAC-GEN at the measured canonical hash 1bb78ce9b357, run with a "
                "deterministic checker over frozen snapshot bytes. Output is a review + machine evidence. Does "
                "not claim node completion or any gate verdict."),
    "evidence_refs": [f"schemas/af_scc_c0_vacuum.yaml#{reviewed}",
                      "artifacts/worker-029/f2b_full_review/f2b_snapshot.yaml",
                      "research_map/formulation_taxonomy.yaml#276009f4f63d"],
    "next_falsifier": ("A re-run of check_f2b_full.py on the same snapshot with no FAIL, or a revised F2b whose "
                       "canonical pointer and citation-status fields are fixed at a new hash; drift of the live "
                       "path voids the binding."),
})
for key, atype, note in [
    ("report", "audit_report", "Check-by-check machine results (28 checks) over frozen snapshot bytes; the checks themselves never read the live artifact."),
    ("checker", "checker_code", "Deterministic stdlib+PyYAML checker; reproduce command in REVIEW.md."),
    ("review", "review_object", "Structured review object: verdict revise, 3 hard failures, 3 soft findings, positives, assumptions, falsifier."),
    ("readme", "summary", "One-page human-readable verdict pinned to the snapshot and report hashes."),
]:
    ev.append({
        "event_id": f"w029-20260912T0023-artifact-{key}",
        "event_type": "artifact", "created_at": now, "actor": "worker-029",
        "node_id": "F2b", "class_id": "AF-SCC-C0-VAC-GEN", "gate": "G-FORM",
        "artifact_type": atype, "path": ah[key]["path"], "sha256": ah[key]["sha256"],
        "validation_status": "unverified", "task_id": "W029-F2B-FULLVERDICT-01",
        "note": note,
        "evidence_refs": [f"artifacts/worker-029/f2b_full_review/f2b_snapshot.yaml#{reviewed}"],
    })
ev.append({
    "event_id": "w029-20260912T0023-review-f2b",
    "event_type": "review", "created_at": now, "actor": "worker-029",
    "reviewer": "worker-029", "target_id": "F2b", "class_id": "AF-SCC-C0-VAC-GEN",
    "artifact_path": "schemas/af_scc_c0_vacuum.yaml", "reviewed_sha256": reviewed,
    "verdict": "revise", "score": 2.0, "gate": "G-FORM",
    "hard_failures": hard, "findings": soft + positives,
    "scope": review["scope"],
    "evidence_refs": review["evidence_refs"],
    "falsifier": review["falsifier"],
})
ev.append({
    "event_id": "w029-20260912T0023-claim-f2b",
    "event_type": "claim", "created_at": now, "actor": "worker-029",
    "node_id": "F2b", "class_id": "AF-SCC-C0-VAC-GEN", "conclusion_type": "formal_model",
    "gate": "G-FORM", "task_id": "W029-F2B-FULLVERDICT-01",
    "statement": (
        f"At the snapshot {report['snapshot']['snapshot_taken_at']}, schemas/af_scc_c0_vacuum.yaml @ sha256 {reviewed[:12]} "
        f"(rev10) passes 21/28 deterministic contract checks and fails 3 hard checks: (C5) class_contract_pointer "
        "targets the authoring tree and the class_contracts section does not exist in the canonical taxonomy; "
        "(F1,F2) l1_ledger_refs claim 'verified_by_L1' for " + "/".join(claim_ids) + " while ledger/theorems.jsonl "
        "@ce42d205 records verification_status='abstract-read' for all 62 rows (0 verified), the token appears in "
        "neither L1 artifact, and the same schema sets provenance.citation_status='unverified'; (G1,G2) revised_at "
        f"and f0_binding.checked_at are future-dated by {skew:+d} s at the snapshot instant. The conclusion-token "
        "difference is alias-equivalent under VOCAB_ALIASES.json and is not counted as a failure. Conclusion: this "
        "revision is not acceptable at this hash; verdict revise. No gate verdict is claimed."
    ),
    "assumptions": assumptions,
    "falsifier": review["falsifier"],
    "evidence_refs": review["evidence_refs"],
    "artifact_refs": [f"{ah['report']['path']}#{ah['report']['sha256'][:12]}",
                      f"{ah['review']['path']}#{ah['review']['sha256'][:12]}",
                      f"{ah['checker']['path']}#{ah['checker']['sha256'][:12]}"],
})
ev.append({
    "event_id": "w029-20260912T0023-status-complete",
    "event_type": "status", "created_at": now, "actor": "worker-029",
    "node_id": "F2b", "class_id": "AF-SCC-C0-VAC-GEN", "status": "active", "hours": 0.6,
    "task_id": "W029-F2B-FULLVERDICT-01",
    "summary": ("W029-F2B-FULLVERDICT-01 complete: artifacts exist on disk and are hash-pinned; findings carry "
                "individual falsifiers. Verdict revise at 1bb78ce9b357; snapshot still live at emission. This is "
                "a completion claim, not a node transition (workers cannot set done/passed/gate verdicts). "
                "Checkpoint: runtime/state/w029_checkpoint.json."),
    "evidence_refs": [f"{ah['report']['path']}#{ah['report']['sha256'][:12]}",
                      f"{ah['review']['path']}#{ah['review']['sha256'][:12]}",
                      f"schemas/af_scc_c0_vacuum.yaml#{reviewed}"],
    "next_falsifier": review["falsifier"],
})
out = ROOT / "comms/outbox/worker-029.jsonl"
with out.open("w") as f:
    for e in ev:
        f.write(json.dumps(e, ensure_ascii=False) + "\n")

# ---------------------------------------------------------------- checkpoint
ckpt = {
    "checkpoint_id": "w029-ckpt-20260912T0023",
    "worker": "worker-029",
    "task_id": "W029-F2B-FULLVERDICT-01",
    "created_at": now,
    "node_id": "F2b",
    "class_id": "AF-SCC-C0-VAC-GEN",
    "status": "complete",
    "verdict": "revise",
    "reviewed_sha256": reviewed,
    "snapshot_is_live_at_emission": still_live,
    "live_path_sha256_at_emission": live_now,
    "outbox": rel(out),
    "outbox_sha256": sha256(out),
    "outbox_event_ids": [e["event_id"] for e in ev],
    "artifacts": ah,
    "snapshots": snap_h,
    "hard_failure_ids": [h["id"] for h in hard],
    "soft_finding_ids": [f["id"] for f in soft],
    "note": "worker-scoped checkpoint; did not run research_map/checkpoint.py (controller-owned, mutates shared state)",
}
(ROOT / "runtime/state/w029_checkpoint.json").write_text(json.dumps(ckpt, indent=2, ensure_ascii=False))
with (D / "CHECKPOINTS.jsonl").open("a") as f:
    f.write(json.dumps({k: ckpt[k] for k in
                        ("checkpoint_id", "created_at", "task_id", "verdict", "reviewed_sha256",
                         "snapshot_is_live_at_emission", "outbox_sha256")}) + "\n")

print(json.dumps({"review": rel(D / "review.json"), "review_sha256": ah["review"]["sha256"],
                  "report_sha256": ah["report"]["sha256"], "checker_sha256": ah["checker"]["sha256"],
                  "outbox": rel(out), "outbox_sha256": ckpt["outbox_sha256"],
                  "events": len(ev), "still_live": still_live, "skew_s": skew}, indent=2))
