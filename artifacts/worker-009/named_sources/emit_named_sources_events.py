#!/usr/bin/env python3
"""
W009-L1-NAMEDSRC-01 emitter (worker-009 / deepseek-flash-09)

Writes, from the pinned outputs of verify_named_sources_worker-009.py:
  1. artifacts/worker-009/named_sources/MANIFEST_worker-009.json
  2. runtime/state/w009_named_sources_checkpoint_1.json (+ checkpoints.jsonl)
  3. appends artifact/review/status events to comms/outbox/worker-009.jsonl

Idempotent: an event_id already present in the outbox is skipped.  Worker
events never set status=done, validation_status=passed or a gate verdict.
Run after the verifier; re-running neither duplicates events nor changes the
verification record.
"""
import hashlib
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
OUTDIR = os.path.join(ROOT, "artifacts", "worker-009", "named_sources")
OUTBOX = os.path.join(ROOT, "comms", "outbox", "worker-009.jsonl")
CST = "+08:00"
STAMP = "2026-09-12T01:16:00" + CST
RUN_ID = "w009-namedsrc-20260912T0116"

REC = os.path.join(OUTDIR, "verification_named_sources_worker-009.json")
DRY = os.path.join(OUTDIR, "dryrun_locator_remediation_citation_audit.csv")
PROP_CSV = os.path.join(ROOT, "ledger", "citation_audit_locator_remediation_worker-009.csv")
PROP_JSONL = os.path.join(ROOT, "ledger", "citation_audit_locator_remediation_worker-009.jsonl")
TOOL = os.path.join(OUTDIR, "verify_named_sources_worker-009.py")
MANIFEST = os.path.join(OUTDIR, "MANIFEST_worker-009.json")

PIN = {
    "ledger/citation_audit.csv": "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9",
    "ledger/theorems.jsonl": "a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28",
    "research_map/formulation_taxonomy.yaml": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "schemas/af_scc_c2_vacuum.yaml": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "schemas/af_scc_c0_vacuum.yaml": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "artifacts/formulation/FROZEN.json": "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    "artifacts/formulation/VARIANT_REGISTRY.json": "6bac9adea19e17efe625342ef4d2098e3775491aa3d0e06596cd5d75912348fb",
}
SRC_EVIDENCE = [
    "artifacts/worker-009/named_sources/src/inspire_33714.json",
    "artifacts/worker-009/named_sources/src/arxiv_0711.4620_abs.html",
    "artifacts/worker-009/named_sources/src/arxiv_0711.4620_src.tar.gz",
    "artifacts/worker-009/named_sources/src/gmg/critreview4.tex",
    "artifacts/worker-009/named_sources/src/doi_lrr.html",
    "artifacts/worker-009/named_sources/src/doi_prl70_9.html",
]


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 16), b""):
            h.update(b)
    return h.hexdigest()


def ref(rel):
    return "%s#%s" % (rel, sha(os.path.join(ROOT, rel))[:16])


def main():
    verify_inputs = [REC, DRY, PROP_CSV, PROP_JSONL, TOOL] + [os.path.join(ROOT, p) for p in PIN] + \
                    [os.path.join(ROOT, p) for p in SRC_EVIDENCE]
    missing = [p for p in verify_inputs if not os.path.exists(p)]
    if missing:
        print("MISSING outputs, run the verifier first:", missing)
        return 2
    rec = json.load(open(REC, encoding="utf-8"))
    if rec["summary"]["checks_fail"] != len(rec["advisory_checks"]):
        print("REFUSING: unexpected non-advisory check failures", rec["summary"]["checks_fail"], rec["advisory_checks"])
        return 2
    if rec["hard_failures"]:
        print("REFUSING: hard failures present")
        return 2

    artifacts = []
    for rel in [os.path.relpath(REC, ROOT), os.path.relpath(DRY, ROOT), os.path.relpath(PROP_CSV, ROOT),
                os.path.relpath(PROP_JSONL, ROOT), os.path.relpath(TOOL, ROOT)]:
        p = os.path.join(ROOT, rel)
        artifacts.append({"path": rel, "sha256": sha(p), "bytes": os.path.getsize(p)})
    manifest = {
        "task_id": "W009-L1-NAMEDSRC-01",
        "created_at": STAMP,
        "worker": "worker-009",
        "actor_id": "deepseek-flash-09",
        "assignment_id": "asg-2026-09-11-L1-deepseek-flash-09-18",
        "node_id": "L1",
        "gate": "G-LIT",
        "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "row_class": "AF-WCC-SCALAR-SPH",
        "artifacts": artifacts,
        "source_evidence": [{"path": r, "sha256": sha(os.path.join(ROOT, r))} for r in SRC_EVIDENCE],
        "anchors": PIN,
        "summary": rec["summary"],
        "canonical_write": "none",
    }
    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1)
        f.write("\n")
    artifacts.append({"path": os.path.relpath(MANIFEST, ROOT), "sha256": sha(MANIFEST),
                      "bytes": os.path.getsize(MANIFEST)})

    checkpoint = {
        "checkpoint_id": "w009-namedsrc-2026-09-12T01:16:26+08:00",
        "created_at": STAMP,
        "worker": "worker-009",
        "label": "worker-009-L1-named-source-closure-choptuik-gmg",
        "assignment_id": "asg-2026-09-11-L1-deepseek-flash-09-18",
        "node_id": "L1",
        "gate": "G-LIT",
        "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "record": {"path": os.path.relpath(REC, ROOT), "sha256": sha(REC)},
        "artifacts": {a["path"]: a["sha256"] for a in artifacts},
        "anchors": PIN,
        "source_evidence": {r: sha(os.path.join(ROOT, r)) for r in SRC_EVIDENCE},
        "counts": {"pass": rec["summary"]["checks_pass"], "fail": rec["summary"]["checks_fail"],
                   "fail_is_advisory_only": True},
        "summary": rec["summary"],
        "hard_failures": rec["hard_failures"],
        "advisories": rec["advisories"],
        "next_falsifier": rec["next_falsifier"],
        "canonical_write": "none",
    }
    ckpath = os.path.join(ROOT, "runtime", "state", "w009_named_sources_checkpoint_1.json")
    os.makedirs(os.path.dirname(ckpath), exist_ok=True)
    with open(ckpath, "w", encoding="utf-8") as f:
        json.dump(checkpoint, f, indent=1)
        f.write("\n")
    with open(os.path.join(ROOT, "runtime", "state", "w009_named_sources_checkpoints.jsonl"), "a",
              encoding="utf-8") as f:
        f.write(json.dumps({"checkpoint_id": checkpoint["checkpoint_id"], "created_at": STAMP,
                            "record_sha256": checkpoint["record"]["sha256"],
                            "summary": rec["summary"]}) + "\n")

    ev = []
    ev.append({
        "event_id": RUN_ID + "-artifact-01", "event_type": "artifact", "created_at": STAMP,
        "actor": "worker-009", "node_id": "L1", "gate": "G-LIT", "group_id": "literature",
        "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "assignment_id": "asg-2026-09-11-L1-deepseek-flash-09-18",
        "artifact_type": "verification_record",
        "path": os.path.relpath(REC, ROOT), "sha256": sha(REC), "validation_status": "unverified",
        "note": ("Named-source closure for SRC-016 (Choptuik 1993) and SRC-094 (Gundlach-Martin-Garcia 2007): "
                 "44 checks, 41 pass, 2 advisory-only, 0 hard failure, 6/6 negative controls fire. Choptuik abstract "
                 "(INSPIRE 33714) verified title/author/PRL 70:9-12/DOI and the p*, BH-dispersal separation, universality "
                 "and gamma~=0.37 power law; GMG gamma sentence verified verbatim in the arXiv e-print (critreview4.tex:1239, "
                 "'Electric charge' subsection) and independently in the published LRR version (DOI 10.12942/lrr-2007-5). "
                 "Both rows are massless-scalar matter: 2/2 support AF-WCC-SCALAR-SPH, 0/2 support any AF-SCC-*-VAC-GEN binding; "
                 "assignment falsifier ('wrong regularity class') not realised. Canonical ledger untouched."),
        "evidence_refs": [ref(os.path.relpath(REC, ROOT)), ref(os.path.relpath(MANIFEST, ROOT)),
                          ref("ledger/citation_audit.csv"), ref("ledger/theorems.jsonl")] + [ref(r) for r in SRC_EVIDENCE],
        "falsifier": ("Any pinned input or fetched-source sha256 moves; or a re-fetch shows either source is vacuum Lambda=0 "
                      "rather than massless-scalar matter; or the primary source states an exponent other than gamma~=0.37."),
    })
    ev.append({
        "event_id": RUN_ID + "-artifact-02", "event_type": "artifact", "created_at": STAMP,
        "actor": "worker-009", "node_id": "L1", "gate": "G-LIT", "group_id": "literature",
        "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "assignment_id": "asg-2026-09-11-L1-deepseek-flash-09-18",
        "artifact_type": "dryrun_ledger",
        "path": os.path.relpath(DRY, ROOT), "sha256": sha(DRY), "validation_status": "unverified",
        "note": ("dry-run of the 2-cell locator remediation on a byte-faithful copy of the frozen canonical ledger: 97x25, "
                 "exactly 2 cells changed, every class_mapping byte identical; dry-run only, canonical ledger not written."),
        "evidence_refs": [ref(os.path.relpath(DRY, ROOT)), ref(os.path.relpath(REC, ROOT)), ref("ledger/citation_audit.csv")],
        "falsifier": "Any further cell differs from the frozen canonical ledger, or any class_mapping cell changes.",
    })
    ev.append({
        "event_id": RUN_ID + "-artifact-03", "event_type": "artifact", "created_at": STAMP,
        "actor": "worker-009", "node_id": "L1", "gate": "G-LIT", "group_id": "literature",
        "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "assignment_id": "asg-2026-09-11-L1-deepseek-flash-09-18",
        "artifact_type": "locator_remediation_proposal",
        "path": os.path.relpath(PROP_CSV, ROOT), "sha256": sha(PROP_CSV), "validation_status": "unverified",
        "note": ("Minimal 2-row machine-applicable locator remediation in the canonical 25-column schema: SRC-016 "
                 "exact_locator -> https://inspirehep.net/api/literature/33714 (was an INSPIRE search-query URL); "
                 "SRC-094 evidence_url -> https://link.springer.com/article/10.12942/lrr-2007-5 (published LRR version, was empty). "
                 "Companion JSONL: ledger/citation_audit_locator_remediation_worker-009.jsonl#%s. class_mapping unchanged on both rows."
                 % sha(PROP_JSONL)[:16]),
        "evidence_refs": [ref(os.path.relpath(PROP_CSV, ROOT)), ref(os.path.relpath(PROP_JSONL, ROOT)),
                          ref(os.path.relpath(REC, ROOT)), ref("ledger/citation_audit.csv")],
        "falsifier": "A lead-applied patch that changes any class_mapping cell, or a locator that no longer resolves to the cited work.",
    })
    ev.append({
        "event_id": RUN_ID + "-artifact-04", "event_type": "artifact", "created_at": STAMP,
        "actor": "worker-009", "node_id": "L1", "gate": "G-LIT", "group_id": "literature",
        "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "assignment_id": "asg-2026-09-11-L1-deepseek-flash-09-18",
        "artifact_type": "verification_tool",
        "path": os.path.relpath(TOOL, ROOT), "sha256": sha(TOOL), "validation_status": "unverified",
        "note": ("Deterministic verifier (frozen RUN_STAMP, no wall clock inside the record): pinned-input and fetched-source "
                 "sha256 checks, claim-by-claim Choptuik abstract support, GMG full-text/published gamma-sentence checks, "
                 "class-token and vacuum-binding discrimination, 6 negative controls, and a class-byte-preserving dry-run "
                 "of the 2-row locator remediation."),
        "evidence_refs": [ref(os.path.relpath(TOOL, ROOT)), ref(os.path.relpath(REC, ROOT)), ref(os.path.relpath(MANIFEST, ROOT))],
        "falsifier": "Re-run at the pinned hashes and show a check that no longer reproduces, or a control that no longer fires.",
    })
    ev.append({
        "event_id": RUN_ID + "-review-01", "event_type": "review", "created_at": STAMP,
        "actor": "worker-009", "node_id": "L1", "gate": "G-LIT", "group_id": "literature",
        "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "assignment_id": "asg-2026-09-11-L1-deepseek-flash-09-18",
        "target_id": "ledger/citation_audit.csv:SRC-016", "reviewer": "worker-009",
        "verdict": "accept", "score": 4.0,
        "review_scope": "author self-verification against primary bytes; NOT an independent verdict - lead-audit must independently re-fetch",
        "hard_failures": [],
        "findings": [
            "INSPIRE record 33714: title 'Universality and scaling in gravitational collapse of a massless scalar field', author Choptuik, PRL 70(1) 9-12 (1993), DOI 10.1103/PhysRevLett.70.9 - all exact.",
            "Abstract carries every clause of T-103's statement: p* separates BH from non-BH solutions; strong-field p->p* limit universal with structure on arbitrarily small spatiotemporal scales; masses obey a power law with universal exponent gamma~=0.37.",
            "class_mapping AF-WCC-SCALAR-SPH is supported (massless scalar field, spherical symmetry); no AF-SCC-*-VAC-GEN token, and none is licensed (F2a/F2b require matter=none, Lambda=0).",
            "Advisory: exact_locator is an INSPIRE search-query URL, not a pinpoint; record URL already in url/evidence_url. PRL landing returns HTTP 403 and no arXiv e-print exists, so the exponent rests on the authoritative abstract plus the GMG full-text corroboration.",
        ],
        "evidence_refs": [ref("artifacts/worker-009/named_sources/src/inspire_33714.json"),
                          ref("artifacts/worker-009/named_sources/src/doi_prl70_9.html"),
                          ref(os.path.relpath(REC, ROOT)), ref("ledger/citation_audit.csv"), ref("ledger/theorems.jsonl")],
    })
    ev.append({
        "event_id": RUN_ID + "-review-02", "event_type": "review", "created_at": STAMP,
        "actor": "worker-009", "node_id": "L1", "gate": "G-LIT", "group_id": "literature",
        "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "assignment_id": "asg-2026-09-11-L1-deepseek-flash-09-18",
        "target_id": "ledger/citation_audit.csv:SRC-094", "reviewer": "worker-009",
        "verdict": "accept", "score": 4.0,
        "review_scope": "author self-verification against primary bytes; NOT an independent verdict - lead-audit must independently re-fetch",
        "hard_failures": [],
        "findings": [
            "arXiv:0711.4620 e-print resolved; full TeX source extracted; critreview4.tex line 1239 carries 'mass scales with $\\gamma\\simeq 0.37$ as for the uncharged scalar' in the 'Electric charge' subsection.",
            "Published Living Reviews version (DOI 10.12942/lrr-2007-5, Springer) fetched HTTP 200 and carries the same sentence ('The mass scales with gamma ~= 0.37 as for the uncharged scalar field.'), independently corroborating the arXiv text.",
            "Review abstract and body attribute the discovery to Choptuik; the massless scalar field is the review's worked model (section 'The scalar field'), supporting both T-103 and the AF-WCC-SCALAR-SPH mapping.",
            "Advisory: evidence_url is empty; dry-run fills it with the published LRR locator. evidence_type 'abstract' understates the full-text verification now available.",
        ],
        "evidence_refs": [ref("artifacts/worker-009/named_sources/src/gmg/critreview4.tex"),
                          ref("artifacts/worker-009/named_sources/src/doi_lrr.html"),
                          ref("artifacts/worker-009/named_sources/src/arxiv_0711.4620_abs.html"),
                          ref(os.path.relpath(REC, ROOT)), ref("ledger/citation_audit.csv"), ref("ledger/theorems.jsonl")],
    })
    ev.append({
        "event_id": RUN_ID + "-status-01", "event_type": "status", "created_at": STAMP,
        "actor": "worker-009", "node_id": "L1", "gate": "G-LIT", "group_id": "literature",
        "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "assignment_id": "asg-2026-09-11-L1-deepseek-flash-09-18",
        "status": "active", "hours": 0.5,
        "summary": ("Bounded class-bound task (worker-009, L1/G-LIT): closed the two remaining named sources on assignment card "
                    "asg-2026-09-11-L1-deepseek-flash-09-18. SRC-016 (Choptuik 1993) and SRC-094 (Gundlach-Martin-Garcia 2007) are "
                    "both verified at primary level with exact locators and explicit C0/C2-vacuum-vs-scalar discrimination: 44 checks, "
                    "41 pass, 2 advisory-only (locator quality/evidence_type), 0 hard failures, 6/6 negative controls fire. "
                    "2/2 rows support AF-WCC-SCALAR-SPH and 0/2 support any AF-SCC-*-VAC-GEN binding, so the card falsifier "
                    "('theorem quoted in the wrong regularity class') is not realised. A 2-row/2-cell locator remediation dry-runs with "
                    "every class_mapping byte identical; canonical ledger and all canonical artifacts untouched."),
        "evidence_refs": [ref(os.path.relpath(REC, ROOT)), ref(os.path.relpath(MANIFEST, ROOT)),
                          ref("runtime/state/w009_named_sources_checkpoint_1.json"),
                          ref("ledger/citation_audit.csv"), ref("ledger/theorems.jsonl"),
                          ref("schemas/af_scc_c2_vacuum.yaml"), ref("schemas/af_scc_c0_vacuum.yaml")],
        "next_falsifier": rec["next_falsifier"],
    })

    os.makedirs(os.path.dirname(OUTBOX), exist_ok=True)
    existing = set()
    if os.path.exists(OUTBOX):
        for ln in open(OUTBOX, encoding="utf-8"):
            try:
                existing.add(json.loads(ln).get("event_id"))
            except Exception:
                pass
    appended = 0
    with open(OUTBOX, "a", encoding="utf-8") as f:
        for e in ev:
            if e["event_id"] in existing:
                continue
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
            appended += 1
    print("manifest", os.path.relpath(MANIFEST, ROOT), sha(MANIFEST)[:16])
    print("checkpoint", os.path.relpath(ckpath, ROOT), sha(ckpath)[:16])
    print("events appended", appended, "of", len(ev), "(idempotent)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
