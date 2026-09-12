#!/usr/bin/env python3
"""Emit W007-CITEBIND-CENSUS-01 events to comms/outbox/worker-007.jsonl.

Idempotent: event_ids already present in the outbox are skipped.  Every event is
validated with the project's own research_map/schemas.validate_event before being
appended.  Also (re)writes SHA256SUMS.txt for the artifact directory.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "research_map"))

from schemas import validate_event  # noqa: E402

OUTBOX = os.path.join(ROOT, "comms", "outbox", "worker-007.jsonl")
TASK_ID = "W007-CITEBIND-CENSUS-01"
ACTOR = "worker-007"
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
CLASS_ID = ";".join(CLASS_IDS)


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def rel(path: str) -> str:
    return os.path.relpath(path, ROOT)


def write_sha256sums() -> str:
    lines = []
    for dirpath, _dirnames, filenames in os.walk(HERE):
        for fn in sorted(filenames):
            if fn in ("SHA256SUMS.txt",):
                continue
            p = os.path.join(dirpath, fn)
            lines.append(f"{sha256(p)}  {os.path.relpath(p, HERE)}")
    out = os.path.join(HERE, "SHA256SUMS.txt")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(sorted(lines)) + "\n")
    return sha256(out)


def now() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def main() -> int:
    sums_sha = write_sha256sums()
    report = json.load(open(os.path.join(HERE, "report.json"), encoding="utf-8"))
    v = report["verdict"]
    counts = report["counts"]
    report_sha = sha256(os.path.join(HERE, "report.json"))
    checker_sha = sha256(os.path.join(HERE, "verify_citebind.py"))
    readme_sha = sha256(os.path.join(HERE, "README.md"))
    frozen = report["frozen_pin_check"]

    ev = [
        {
            "event_id": "w007-citebind-artifact-report-01",
            "event_type": "artifact", "created_at": now(), "actor": ACTOR,
            "node_id": "L1", "class_id": CLASS_ID, "class_ids": CLASS_IDS,
            "gates": ["G-LIT", "G-FORM"], "task_id": TASK_ID,
            "artifact_type": "citation_status_binding_census",
            "path": rel(os.path.join(HERE, "report.json")), "sha256": report_sha,
            "validation_status": "unverified",
            "summary": (
                "Independent hash-pinned census of l1_ledger_refs[*].citation_status across "
                "F1/F2a/F2b rev12: 11 verified_by_L1 refs out-of-vocabulary under FROZEN rule_spec "
                "vocabularies.citation_status [unverified, unresolved, verified]; token 0x in corpus; "
                "all 11 refs nonetheless resolve to L1 citation-audit rows with verdict=verified and "
                "resolver_result=resolved (97/97 audit rows verified); 0 missing, 0 bad."),
            "evidence_refs": [
                f"{rel(os.path.join(HERE, 'report.json'))}#{report_sha[:12]}",
                "artifacts/worker-007/citebind_census/snapshot/theorems.a1674f094979.jsonl#a1674f094979",
                "artifacts/worker-007/citebind_census/snapshot/citation_audit.315c19145065.csv#315c19145065",
                "artifacts/worker-007/citebind_census/snapshot/rule_spec.40f9bb9e657b.json#40f9bb9e657b",
            ],
            "falsifier": report["falsifier"],
        },
        {
            "event_id": "w007-citebind-artifact-checker-02",
            "event_type": "artifact", "created_at": now(), "actor": ACTOR,
            "node_id": "L1", "class_id": CLASS_ID, "class_ids": CLASS_IDS,
            "gates": ["G-LIT", "G-FORM"], "task_id": TASK_ID,
            "artifact_type": "independent_checker",
            "path": rel(os.path.join(HERE, "verify_citebind.py")), "sha256": checker_sha,
            "validation_status": "unverified",
            "summary": ("Self-contained deterministic checker (stdlib + PyYAML, no network, no "
                        "worker-077 code): re-derives the 15-ref census, executes worker-077's own "
                        "falsifier, and runs 7 mutation controls (7/7 PASS)."),
            "evidence_refs": [f"{rel(os.path.join(HERE, 'report.json'))}#{report_sha[:12]}"],
        },
        {
            "event_id": "w007-citebind-artifact-readme-03",
            "event_type": "artifact", "created_at": now(), "actor": ACTOR,
            "node_id": "L1", "class_id": CLASS_ID, "class_ids": CLASS_IDS,
            "gates": ["G-LIT", "G-FORM"], "task_id": TASK_ID,
            "artifact_type": "readme",
            "path": rel(os.path.join(HERE, "README.md")), "sha256": readme_sha,
            "validation_status": "unverified",
            "summary": ("Method, pins, verdict split (vocabulary violation confirmed / verification "
                        "overclaim refuted), residual vocab issues, advisory repairs, controls, "
                        "falsifier and non-claims."),
            "evidence_refs": [f"{rel(os.path.join(HERE, 'report.json'))}#{report_sha[:12]}"],
        },
        {
            "event_id": "w007-citebind-artifact-sums-04",
            "event_type": "artifact", "created_at": now(), "actor": ACTOR,
            "node_id": "L1", "class_id": CLASS_ID, "class_ids": CLASS_IDS,
            "gates": ["G-LIT", "G-FORM"], "task_id": TASK_ID,
            "artifact_type": "hash_manifest",
            "path": rel(os.path.join(HERE, "SHA256SUMS.txt")), "sha256": sums_sha,
            "validation_status": "unverified",
            "summary": "SHA256SUMS for all packet files including the 10 read-only input snapshots.",
            "evidence_refs": [f"{rel(os.path.join(HERE, 'report.json'))}#{report_sha[:12]}"],
        },
        {
            "event_id": "w007-citebind-claim-05",
            "event_type": "claim", "created_at": now(), "actor": ACTOR,
            "node_id": "L1", "class_id": CLASS_ID, "class_ids": CLASS_IDS,
            "gates": ["G-LIT", "G-FORM"], "task_id": TASK_ID,
            "conclusion_type": "formal_model",
            "statement": (
                "At the pinned rev12 bytes (F1 cce9c60146d6, F2a 5476a3f2c6bc, F2b 55d0a1ea9bda) "
                "with ledger a1674f094979 and citation audit 315c19145065: worker-077 W077-HF-03 is "
                "CONFIRMED as a vocabulary violation and REFUTED as a verification overclaim. "
                "11 l1_ledger_refs entries use citation_status=verified_by_L1, a token absent from "
                "the FROZEN-pinned rule_spec vocabulary [unverified, unresolved, verified] and from "
                "VOCAB_ALIASES; the token occurs 0 times in the ledger/audit/rule-spec/taxonomy/"
                "FROZEN corpus and all 62 ledger rows are review_status=not_independently_reviewed. "
                "However, all 11 refs resolve via citation_audit.csv used_by_theorems to audit rows "
                "with verdict=verified and resolver_result=resolved for every ledger source_id "
                "(0 missing, 0 bad; audit 97/97 verified), i.e. abstract/API-level verification is "
                "present. The defect is therefore a token/vocabulary repair, not a source or content "
                "downgrade; worker-077's own falsifier names exactly this branch. This is a statement "
                "about artifacts and vocabularies, not about cosmic censorship."),
            "assumptions": [
                "snapshot/ copies re-hash to the declared pins and the live paths equal the snapshots",
                "the authority for the token vocabulary is FROZEN-pinned artifacts/formulation/rule_spec.json "
                "(spec_version 1.2, vocabularies.citation_status)",
                "the bridge from schema refs to audit rows is the audit column used_by_theorems",
                "abstract-level audit evidence is treated as sufficient for the L1 gate per the pass-04 "
                "CF-18(b) ruling; this packet does not re-adjudicate that ruling",
                "per-source mutations can move the resolution count by more than one because audit rows "
                "are shared across refs (e.g. SRC-037)",
            ],
            "falsifier": report["falsifier"],
            "evidence_refs": [
                f"{rel(os.path.join(HERE, 'report.json'))}#{report_sha[:12]}",
                f"{rel(os.path.join(HERE, 'verify_citebind.py'))}#{checker_sha[:12]}",
                "artifacts/worker-007/citebind_census/snapshot/af_wcc_vacuum.cce9c60146d6.yaml#cce9c60146d6",
                "artifacts/worker-007/citebind_census/snapshot/af_scc_c2_vacuum.5476a3f2c6bc.yaml#5476a3f2c6bc",
                "artifacts/worker-007/citebind_census/snapshot/af_scc_c0_vacuum.55d0a1ea9bda.yaml#55d0a1ea9bda",
                "artifacts/worker-007/citebind_census/snapshot/rule_spec.40f9bb9e657b.json#40f9bb9e657b",
                "artifacts/worker-007/citebind_census/snapshot/FROZEN.2f358f6722d9.json#2f358f6722d9",
            ],
        },
        {
            "event_id": "w007-citebind-review-finding-06",
            "event_type": "review", "created_at": now(), "actor": ACTOR,
            "node_id": "L1", "class_id": CLASS_ID, "class_ids": CLASS_IDS,
            "gates": ["G-LIT", "G-FORM"], "task_id": TASK_ID,
            "target_id": "reviews/F2b-f0-binding-077.json#W077-HF-03",
            "reviewer": ACTOR, "verdict": "accept", "score": 4.0, "hard_failures": [],
            "findings": [
                "INDEPENDENTLY REPRODUCED at ledger a1674f094979: all five named F2b refs (D-002, T-301, "
                "T-515, T-528, T-302) carry citation_status=verified_by_L1 while their ledger rows record "
                "verification_status=abstract-read and review_status=not_independently_reviewed.",
                "EXTENDED: the token is systematic, not F2b-specific - 11 refs across F1 (T-204, T-208), "
                "F2a (T-401, T-402, T-514, T-520) and F2b (D-002, T-301, T-515, T-528, T-302).",
                "MECHANISM SHARPENED: the decisive defect is out-of-vocabulary token usage against the "
                "FROZEN-pinned rule_spec vocabularies.citation_status [unverified, unresolved, verified] "
                "(R15 applies_to=all), not a missing source verification.",
                "FALSIFIER BRANCH EXECUTED AND FOUND TRUE: every one of the 11 refs resolves via "
                "citation_audit.csv used_by_theorems to verdict=verified, resolver_result=resolved rows "
                "for all ledger source_ids (0 missing, 0 bad; 97/97 audit rows verified), i.e. the branch "
                "worker-077 named ('abstract/API evidence only') is the actual state.",
                "SEVERITY RE-SCOPE (advisory): keep blocking for a clean gate accept, but reclassify from "
                "'citation overclaim' to 'vocabulary repair'; the repair is lead-owned (alias registration "
                "or leaf rename), and no citation content needs downgrading.",
                "RESIDUAL: provenance.citation_status=unverified vs per-ref verified_by_L1 reads as a "
                "contradiction; F2a T-401 pairs l1_status=provisional with verified_by_L1; F1 D-001 lacks "
                "the field; 9 citation_status: n/a tokens in transfer_relations are also out-of-vocabulary.",
            ],
            "evidence_refs": [
                f"{rel(os.path.join(HERE, 'report.json'))}#{report_sha[:12]}",
                "reviews/F2b-f0-binding-077.json",
                "artifacts/worker-007/citebind_census/snapshot/rule_spec.40f9bb9e657b.json#40f9bb9e657b",
            ],
        },
        {
            "event_id": "w007-citebind-review-schemas-07",
            "event_type": "review", "created_at": now(), "actor": ACTOR,
            "node_id": "F1,F2a,F2b", "class_id": CLASS_ID, "class_ids": CLASS_IDS,
            "gates": ["G-FORM", "G-LIT"], "task_id": TASK_ID,
            "target_id": ("F1@cce9c60146d6, F2a@5476a3f2c6bc, F2b@55d0a1ea9bda "
                          "(schemas/af_wcc_vacuum.yaml, schemas/af_scc_c2_vacuum.yaml, "
                          "schemas/af_scc_c0_vacuum.yaml)"),
            "reviewer": ACTOR, "verdict": "revise", "score": 3.0,
            "hard_failures": [
                {"id": "W007-CB-HF-01", "severity": "major", "class": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
                 "type": "out_of_vocabulary_citation_status",
                 "finding": ("11 l1_ledger_refs entries carry citation_status=verified_by_L1, which is not a "
                             "member of the FROZEN-pinned rule_spec vocabularies.citation_status "
                             "[unverified, unresolved, verified] and is not a registered alias. R15 "
                             "(applies_to=all) requires citation_status in vocabulary; the literal token "
                             "occurs 0 times in the ledger, citation audit, rule spec, VOCAB_ALIASES, "
                             "taxonomy and FROZEN."),
                 "evidence": ["artifacts/worker-007/citebind_census/report.json#checks.C1_vocabulary",
                              "artifacts/worker-007/citebind_census/snapshot/rule_spec.40f9bb9e657b.json#vocabularies.citation_status"],
                 "repair": ("lead decision: alias-map verified_by_L1 -> verified with an explicit abstract-level "
                            "scope note, or rename the per-ref leaf (e.g. l1_citation_audit_status), or "
                            "substitute in-vocabulary verified + scope note. No source downgrade is required."),
                 "falsifier": "A FROZEN-pinned vocabulary or alias registry containing verified_by_L1, or a re-pin of the three schemas."},
            ],
            "findings": [
                "All non-token content checks in this packet pass: 11/11 verified_by_L1 refs have complete "
                "resolved+verified audit coverage (0 missing, 0 bad; audit 97/97 verified); 0 missing ledger rows.",
                "The same documents' provenance.citation_status=unverified is in-vocabulary and honest; the "
                "defect is confined to the l1_ledger_refs leaf.",
                "Residual non-blocking: F1 D-001 has no citation_status; F2a T-401 pairs l1_status=provisional "
                "with verified_by_L1; 9 transfer_relations witnesses use citation_status: n/a (also out-of-vocabulary).",
                "This revise verdict binds only the three measured hashes; it does not adjudicate W077-HF-01 "
                "(quantifier domain) or W077-HF-02 (consistency-evidence hash drift).",
            ],
            "evidence_refs": [
                f"{rel(os.path.join(HERE, 'report.json'))}#{report_sha[:12]}",
                f"{rel(os.path.join(HERE, 'README.md'))}#{readme_sha[:12]}",
            ],
        },
        {
            "event_id": "w007-citebind-status-08",
            "event_type": "status", "created_at": now(), "actor": ACTOR,
            "node_id": "L1", "class_id": CLASS_ID, "class_ids": CLASS_IDS,
            "gates": ["G-LIT", "G-FORM"], "task_id": TASK_ID,
            "status": "active", "hours": 0.5,
            "summary": ("W007-CITEBIND-CENSUS-01 complete: one bounded class-bound task taken (no card for "
                        "worker-007). Independent census of citation_status=verified_by_L1 across F1/F2a/F2b "
                        "rev12 at FROZEN rev28 pins -> CONFIRMED as out-of-vocabulary token (11 refs) and "
                        "REFUTED as verification overclaim (11/11 refs fully resolved+verified at abstract/API "
                        "level; audit 97/97). 7/7 mutation controls pass; pins stable; live==snapshot. Two review "
                        "events emitted (finding accepted + schemas revise) plus claim and artifacts. Worker "
                        "cannot set done/passed or a gate verdict."),
            "next_falsifier": report["next_falsifier"],
            "evidence_refs": [
                f"{rel(os.path.join(HERE, 'report.json'))}#{report_sha[:12]}",
                f"{rel(os.path.join(HERE, 'verify_citebind.py'))}#{checker_sha[:12]}",
                f"{rel(os.path.join(HERE, 'README.md'))}#{readme_sha[:12]}",
                f"{rel(os.path.join(HERE, 'SHA256SUMS.txt'))}#{sums_sha[:12]}",
            ],
        },
    ]

    for e in ev:
        validate_event(e)

    seen = set()
    if os.path.exists(OUTBOX):
        with open(OUTBOX, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    seen.add(json.loads(line).get("event_id"))
                except Exception:
                    pass
    appended = []
    with open(OUTBOX, "a", encoding="utf-8") as f:
        for e in ev:
            if e["event_id"] in seen:
                continue
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
            appended.append(e["event_id"])
    print(json.dumps({"outbox": rel(OUTBOX), "validated": len(ev),
                      "appended": appended,
                      "skipped_existing": [e["event_id"] for e in ev if e["event_id"] in seen]}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
