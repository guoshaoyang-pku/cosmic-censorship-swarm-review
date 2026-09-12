#!/usr/bin/env python3
"""Emit worker-039 outbox events + checkpoint for W039-L1-SOBOLEV-CLASS-01.

Appends validated JSONL to comms/outbox/deepseek-flash-39.jsonl and writes a worker
checkpoint under runtime/state/.  Canonical artifacts are only read.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

TZ = dt.timezone(dt.timedelta(hours=8))
NOW = dt.datetime.now(TZ).replace(microsecond=0)
TS = NOW.isoformat()
STAMP = NOW.strftime("%Y%m%dT%H%M%S")

TASK_ID = "W039-L1-SOBOLEV-CLASS-01"
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
OUTBOX = ROOT / "comms/outbox/deepseek-flash-39.jsonl"


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def rel(p: Path) -> str:
    return str(p.relative_to(ROOT))


BUNDLE = [
    "verification.json",
    "checks.json",
    "SOURCE_MANIFEST.json",
    "README.md",
    "verify_sobolev_class_claim.py",
    "run.log",
]
raw_dir = HERE / "raw"
for p in sorted(raw_dir.iterdir()):
    if p.is_file():
        BUNDLE.append(f"raw/{p.name}")

hashes = {rel(HERE / b): sha(HERE / b) for b in BUNDLE}
canonical = {
    "schemas/af_wcc_vacuum.yaml": sha(ROOT / "schemas/af_wcc_vacuum.yaml"),
    "schemas/af_scc_c2_vacuum.yaml": sha(ROOT / "schemas/af_scc_c2_vacuum.yaml"),
    "schemas/af_scc_c0_vacuum.yaml": sha(ROOT / "schemas/af_scc_c0_vacuum.yaml"),
}

entry_hashes = {
    "task_id": TASK_ID,
    "actor": "worker-039",
    "created_at": TS,
    "artifact_dir": rel(HERE),
    "artifacts": hashes,
    "canonical_inputs_measured_at_this_run": canonical,
}
(HERE / "entry_hashes.json").write_text(json.dumps(entry_hashes, indent=2, ensure_ascii=False) + "\n")
hashes[rel(HERE / "entry_hashes.json")] = sha(HERE / "entry_hashes.json")

v = json.loads((HERE / "verification.json").read_text())
ev = {
    "event_id": f"w039-l1sobolev-{STAMP}-artifact-verification",
    "event_type": "artifact",
    "created_at": TS,
    "actor": "worker-039",
    "group_id": "literature",
    "node_id": "L1",
    "class_ids": CLASS_IDS,
    "task_id": TASK_ID,
    "artifact_type": "citation_verification",
    "path": rel(HERE / "verification.json"),
    "sha256": hashes[rel(HERE / "verification.json")],
    "validation_status": "unverified",
    "gate": "G-LIT",
    "summary": (
        "Fail-closed primary-source verification of the frozen F1/F2a/F2b declared-UNVERIFIED "
        "sobolev_variant citation (s > 5/2; delta in (1/2,1); h-delta_ij in H^s_delta, K in "
        "H^{s-1}_{delta+1}); verdict PARTIAL. SC1 threshold SUPPORTED (KR2001 Theorem 1.1 + "
        "Remark 1.2, s > 5/2 for AF vacuum data), SC2 decay family PARTIALLY_SUPPORTED (LR2005 "
        "CMP 256:43-110 Section 1, o(r^{-1-sigma})/o(r^{-2-sigma}), sigma>0), SC3 weighted "
        "encoding and SC4 delta interval NOT_FOUND_IN_CHECKED_SET in four pinned open sources; "
        "recommendation: RETAIN the UNVERIFIED flag."
    ),
    "evidence_refs": [
        f"schemas/af_scc_c2_vacuum.yaml#sha256:{canonical['schemas/af_scc_c2_vacuum.yaml']}",
        f"schemas/af_scc_c0_vacuum.yaml#sha256:{canonical['schemas/af_scc_c0_vacuum.yaml']}",
        f"schemas/af_wcc_vacuum.yaml#sha256:{canonical['schemas/af_wcc_vacuum.yaml']}",
        f"{rel(HERE / 'verification.json')}#sha256:{hashes[rel(HERE / 'verification.json')]}",
        f"{rel(HERE / 'checks.json')}#sha256:{hashes[rel(HERE / 'checks.json')]}",
    ],
    "next_falsifier": v["falsifier"],
    "claims_completion": False,
}
validate_event(ev)

ev2 = dict(ev)
ev2.update(
    event_id=f"w039-l1sobolev-{STAMP}-artifact-checks",
    artifact_type="verification_check_evidence",
    path=rel(HERE / "checks.json"),
    sha256=hashes[rel(HERE / "checks.json")],
    summary=(
        "Raw check evidence for W039-L1-SOBOLEV-CLASS-01: source integrity hashes, matched quote "
        "text with offsets/contexts from the pinned ar5iv renderings, absence checks for the exact "
        "weighted normalization across all four sources, fabricated-quote and mutation controls."
    ),
)
validate_event(ev2)

ev3 = {
    "event_id": f"w039-l1sobolev-{STAMP}-claim",
    "event_type": "claim",
    "created_at": TS,
    "actor": "worker-039",
    "group_id": "literature",
    "node_id": "L1",
    "class_id": "AF-SCC-C2-VAC-GEN",
    "class_ids": CLASS_IDS,
    "task_id": TASK_ID,
    "conclusion_type": "open_problem",
    "statement": (
        "Literature/citation finding (not a mathematical result) at pinned schema hashes F1 "
        "cce9c60146d6, F2a 5476a3f2c6bc, F2b 55d0a1ea9bda: the frozen schemas' data-class "
        "sobolev_variant (s > 5/2; delta in (1/2,1); h - delta_ij in H^s_delta, K in "
        "H^{s-1}_{delta+1}; status 'standard_choice; UNVERIFIED citation') is PARTIALLY supported "
        "by open primary sources. The threshold s > 5/2 is stated for asymptotically flat vacuum "
        "data in Klainerman-Rodnianski arXiv:math/0109173 Theorem 1.1 and Remark 1.2 (attributing "
        "the classical result to [H-K-M]), and the decay family is stated in Lindblad-Rodnianski "
        "arXiv:math/0312479 (= CMP 256:43-110, 2005) Section 1 as g_0ij = (1+2M/r)delta_ij + "
        "o(r^{-1-sigma}), k_0 = o(r^{-2-sigma}), sigma > 0. The exact weighted normalization and "
        "the delta in (1/2,1) interval were not found in any of the four checked sources; the "
        "checked sources that do treat weighted asymptotically flat phases use a different "
        "index-sign convention (Bartnik-Isenberg arXiv:gr-qc/0405092 Section 3: (g-ring + "
        "H^2_{-1/2}) x H^1_{-3/2}). Therefore the schema status must remain UNVERIFIED, with the "
        "KR2001/LR2005 locators admissible only as partial-support annotations. No theorem, no "
        "gate verdict, no schema edit."
    ),
    "assumptions": [
        "The claim under test is the verbatim sobolev_variant field of the three frozen schemas at the measured hashes; no other class content is assessed.",
        "The four fetched sources are the complete checked set; the ar5iv HTML renderings are the pinned evidence.",
        "Absence of an exact normalization in the checked set is not evidence of absence in the literature.",
        "KR2001 is an arXiv preprint record without journal-ref/DOI; the result it states is attributed by it to [H-K-M], not independently fetched.",
    ],
    "falsifier": v["falsifier"],
    "evidence_refs": [
        f"schemas/af_wcc_vacuum.yaml#sha256:{canonical['schemas/af_wcc_vacuum.yaml']}",
        f"schemas/af_scc_c2_vacuum.yaml#sha256:{canonical['schemas/af_scc_c2_vacuum.yaml']}",
        f"schemas/af_scc_c0_vacuum.yaml#sha256:{canonical['schemas/af_scc_c0_vacuum.yaml']}",
        f"{rel(HERE / 'verification.json')}#sha256:{hashes[rel(HERE / 'verification.json')]}",
        f"raw/kr2001_rough.html#sha256:{hashes[rel(HERE / 'raw/kr2001_rough.html')]}",
        f"raw/lr2005_wavecoord.html#sha256:{hashes[rel(HERE / 'raw/lr2005_wavecoord.html')]}",
        f"raw/bi2004_constraints.html#sha256:{hashes[rel(HERE / 'raw/bi2004_constraints.html')]}",
    ],
    "artifact_refs": [
        f"{rel(HERE / 'verification.json')}#sha256:{hashes[rel(HERE / 'verification.json')]}",
        f"{rel(HERE / 'checks.json')}#sha256:{hashes[rel(HERE / 'checks.json')]}",
        f"{rel(HERE / 'README.md')}#sha256:{hashes[rel(HERE / 'README.md')]}",
    ],
    "claims_completion": False,
}
validate_event(ev3)

ev4 = {
    "event_id": f"w039-l1sobolev-{STAMP}-review-schema-citation",
    "event_type": "review",
    "created_at": TS,
    "actor": "worker-039",
    "reviewer": "worker-039",
    "reviewer_independence": "worker-039 authored none of the three schemas and none of the checked sources; all quotes and locators are machine-extracted from the pinned fetched bytes",
    "target_id": "L1-SOBOLEV-CLAIM",
    "node_id": "L1",
    "class_ids": CLASS_IDS,
    "gate": "G-LIT",
    "artifact": "schemas/af_scc_c2_vacuum.yaml",
    "artifact_sha256": canonical["schemas/af_scc_c2_vacuum.yaml"],
    "review_kind": "citation_support_review",
    "counts_as_full_schema_verdict": False,
    "verdict": "revise",
    "score": 3.0,
    "hard_failures": [
        "S4_NO_PRIMARY_LOCATOR_FOR_WEIGHTED_ENCODING: the weighted normalization 'h - delta_ij in H^s_delta, K in H^{s-1}_{delta+1}' and the interval 'delta in (1/2,1)' have no locator in the checked open set; clearing 'UNVERIFIED citation' at the frozen hashes would over-promote."
    ],
    "findings": [
        "Positive: the s > 5/2 threshold for asymptotically flat vacuum data is locatable (KR2001 Theorem 1.1, Remark 1.2) and the AF decay family is locatable in a peer-reviewed source (LR2005 Section 1); these may be added as partial-support annotations.",
        "Convention hazard: weight indices appear with opposite signs across the literature (BI2004 Section 3: H^2_{-1/2} x H^1_{-3/2}); any borrowed locator must be checked for index-sign convention before it is bound to the schema.",
        "The schemas' provenance block names only 'Choquet-Bruhat-Geroch maximal globally hyperbolic development' with identifier null, which does not cover the sobolev_variant field; the owner must supply a section/page locator or drop the specific normalization.",
        "Interim: retain 'standard_choice; UNVERIFIED citation'; the KR2001/LR2005 locators are partial support for SC1/SC2 only.",
    ],
    "evidence_refs": [
        f"{rel(HERE / 'verification.json')}#sha256:{hashes[rel(HERE / 'verification.json')]}",
        f"schemas/af_scc_c2_vacuum.yaml#sha256:{canonical['schemas/af_scc_c2_vacuum.yaml']}",
    ],
    "next_falsifier": v["next_falsifier"],
    "claims_completion": False,
}
validate_event(ev4)

ev5 = {
    "event_id": f"w039-l1sobolev-{STAMP}-status",
    "event_type": "status",
    "created_at": TS,
    "actor": "worker-039",
    "group_id": "literature",
    "node_id": "L1",
    "class_ids": CLASS_IDS,
    "task_id": TASK_ID,
    "gate": "G-LIT",
    "status": "active",
    "hours": 0.5,
    "summary": (
        "No inbox assignment for worker-039; took one unclaimed class-bound task: fail-closed "
        "primary-source check of the frozen schemas' declared-UNVERIFIED sobolev_variant citation. "
        "Verdict PARTIAL: SC1 s > 5/2 SUPPORTED (KR2001), SC2 decay family PARTIALLY_SUPPORTED "
        "(LR2005 CMP 256:43-110), SC3 weighted encoding and SC4 delta interval "
        "NOT_FOUND_IN_CHECKED_SET across four pinned sources; recommendation RETAIN the UNVERIFIED "
        "flag. 4/4 integrity checks, all required quotes located with offsets, fabrication and "
        "mutation controls pass. No canonical artifact edited, no ledger row written, no node "
        "status, no gate verdict."
    ),
    "evidence_refs": [
        f"{rel(HERE / 'verification.json')}#sha256:{hashes[rel(HERE / 'verification.json')]}",
        f"{rel(HERE / 'checks.json')}#sha256:{hashes[rel(HERE / 'checks.json')]}",
        f"{rel(HERE / 'entry_hashes.json')}#sha256:{hashes[rel(HERE / 'entry_hashes.json')]}",
    ],
    "next_falsifier": v["next_falsifier"],
    "claims_completion": False,
}
validate_event(ev5)

events = [ev, ev2, ev3, ev4, ev5]
with open(OUTBOX, "a", encoding="utf-8") as fh:
    for e in events:
        fh.write(json.dumps(e, ensure_ascii=False) + "\n")

checkpoint = {
    "task_id": TASK_ID,
    "worker": "worker-039",
    "node_id": "L1",
    "class_ids": CLASS_IDS,
    "gate": "G-LIT",
    "status": "COMPLETE",
    "checkpoint_at": TS,
    "verdict": "PARTIAL_RETAIN_UNVERIFIED_FLAG",
    "sub_claims": {s["id"]: s["status"] for s in v["sub_claims"]},
    "artifacts": {rel(HERE / b): hashes[rel(HERE / b)] for b in BUNDLE + ["entry_hashes.json"]},
    "canonical_inputs_measured": canonical,
    "events_emitted": [e["event_id"] for e in events],
    "outbox": rel(OUTBOX),
    "controls_passed": True,
    "integrity_failures": v["integrity_failures"],
    "next_falsifier": v["next_falsifier"],
    "non_claims": v["non_claims"],
}
ckpt_path = ROOT / f"runtime/state/w039_l1sobolev_checkpoint_{STAMP}.json"
ckpt_path.write_text(json.dumps(checkpoint, indent=2, ensure_ascii=False) + "\n")

print(json.dumps({
    "outbox_appended": rel(OUTBOX),
    "events": [e["event_id"] for e in events],
    "checkpoint": rel(ckpt_path),
    "verification_sha256": hashes[rel(HERE / "verification.json")][:16],
}, indent=1))
