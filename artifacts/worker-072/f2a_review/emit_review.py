#!/usr/bin/env python3
"""Emit the W072-F2A-REVIEW-01 review verdict, MANIFEST and outbox events.

Binds to the schema hash measured at emission time; if the schema moves, the
verdict is void by construction (the hash is recorded in every artifact).
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
from datetime import datetime, timezone, timedelta

CST = timezone(timedelta(hours=8))
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
ART = os.path.join(ROOT, "artifacts", "worker-072", "f2a_review")
SCHEMA = "schemas/af_scc_c2_vacuum.yaml"
MIRROR = "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml"
TAX = "research_map/formulation_taxonomy.yaml"
SUPP = "artifacts/formulation/formulation_taxonomy.yaml"
EVID = "artifacts/formulation/evidence/taxonomy_consistency.json"
REV12 = "artifacts/worker-072/f2a_review/pins/af_scc_c2_vacuum.rev12.yaml"
TASK = "W072-F2A-REVIEW-01"


def now() -> str:
    return datetime.now(CST).replace(microsecond=0).isoformat()


def sh(rel: str) -> str:
    p = rel if os.path.isabs(rel) else os.path.join(ROOT, rel)
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def rel(p: str) -> str:
    return os.path.relpath(p, ROOT)


def main() -> int:
    report_path = os.path.join(ART, "report.json")
    report = json.load(open(report_path))
    inst = os.path.join(ART, "check_f2a.py")
    schema_sha = sh(SCHEMA)
    mirror_sha = sh(MIRROR)
    tax_sha = sh(TAX)
    supp_sha = sh(SUPP)
    evid_sha = sh(EVID)
    rev12_sha = sh(REV12)
    ts = datetime.now(CST).strftime("%Y%m%dT%H%M%S")
    counts = report["summary"]

    findings = [
        {
            "id": "W072F2A-01",
            "severity": "info",
            "finding": "All 20 conformance checks PASS at rev13 (class-id singularity, no C0/C2 composite in specification slots, conclusion_type/family, I+/visibility roles, quantifier chain and domain resolution, topology, genericity, extension predicate, F0 hash binding, contract pointers, consistency-evidence binding, falsifier completeness, forbidden transfers, implication direction, review hygiene, no duplicate YAML keys, F0 frozen stability, and the rev12->rev13 delta).",
            "evidence_refs": [f"{SCHEMA}#{schema_sha[:12]}", f"artifacts/worker-072/f2a_review/report.json#{sh(rel(report_path))[:12]}"],
        },
        {
            "id": "W072F2A-02",
            "severity": "info",
            "finding": "The rev12 (5476a3f2c6bc) -> rev13 (e9a27996dfd3) change set for F2a is exactly the carded evidence-binding refresh: revision, revised_at, revision_history, f0_binding.consistency_evidence_sha256, f0_binding.checked_at, f0_binding.binding_note. No class-semantics path (class_id, quantifiers, domains, topology, genericity, extension_predicate, conclusion, falsifier, implication_ledger) moved.",
            "evidence_refs": [f"{SCHEMA}#{schema_sha[:12]}", f"{REV12}#{rev12_sha[:12]}"],
        },
        {
            "id": "W072F2A-03",
            "severity": "non_blocking",
            "finding": "Residual weakness outside the schema bytes: the refreshed consistency evidence artifacts/formulation/evidence/taxonomy_consistency.json (9e335e9ba1bf) records the two compared PATHS and consistent=true but carries no sha256 of either compared tree and no comparison timestamp, so its own claim is not byte-attributable to the pinned F0 taxonomies. This is worker-047 CB-2, outside the four items of astra-life05-evidence-binding-repair; the schema-level binding (C13) is nevertheless declared==measured at the current bytes. The A1/A0 layer should adjudicate whether the G-F0 companion-pair criterion needs the evidence document itself to be hash-pinned; this review does not decide it.",
            "evidence_refs": [f"{EVID}#{evid_sha[:12]}", f"{TAX}#{tax_sha[:12]}", f"{SUPP}#{supp_sha[:12]}"],
        },
        {
            "id": "W072F2A-04",
            "severity": "non_blocking",
            "finding": "Scope of this review: the checks are structural/declarative and hash-bound. They do not verify the mathematics, the citations (L1 owns the ledger), the unresolved items the schema itself declares (diffeomorphism quotient, meagerness of excluded families, non-vacuity witness membership), or the r3 evidence-basis contest. The accept is a schema-conformance verdict at one measured hash, not a gate verdict and not a mathematics claim.",
            "evidence_refs": [f"{SCHEMA}#{schema_sha[:12]}"],
        },
        {
            "id": "W072F2A-05",
            "severity": "advisory",
            "finding": "Timing: the schema bytes moved from rev12 5476a3f2c6bc to rev13 e9a27996dfd3 at 2026-09-12T00:53:20+08:00, during this review window, by the lead's carded repair. artifacts/formulation/FROZEN.json is still revision 28 (rev29 not yet published), so the audit lead's r3 round (astra-life05-verify-gform-r3) cannot yet bind pins. Any further write to this schema voids this verdict; re-measure before counting it.",
            "evidence_refs": [f"{SCHEMA}#{schema_sha[:12]}"],
        },
    ]

    review = {
        "review_id": f"w072-f2a-rev13-review-{ts}",
        "created_at": now(),
        "reviewer": "worker-072",
        "worker": "worker-072",
        "role": "bounded execution worker",
        "target_id": "F2a",
        "target_subnode": "F2a",
        "class_id": "AF-SCC-C2-VAC-GEN",
        "node_id": "F2a",
        "gate": "G-FORM",
        "artifact": SCHEMA,
        "artifact_sha256": schema_sha,
        "artifact_mirror": MIRROR,
        "artifact_mirror_sha256": mirror_sha,
        "artifact_revision": 13,
        "verdict": "accept",
        "score": 4.5,
        "counts_as_full_schema_verdict": True,
        "hard_failures": [],
        "independence": ("Not an author of F2a, F0, the supplement, VARIANT_REGISTRY, FROZEN.json or the rev29 repair tool. "
                         "Instrument authorship disclosed: artifacts/worker-072/f2a_review/check_f2a.py is mine, written from scratch; "
                         "it does not import research_map/class_separation.py, artifacts/formulation/tools/check_class_schema.py or "
                         "artifacts/worker-06/spec_conformance_audit.py. No other reviewer's F2a verdict text was read before this verdict was formed."),
        "pins_measured_at_review": {
            SCHEMA: schema_sha, MIRROR: mirror_sha, TAX: tax_sha, SUPP: supp_sha, EVID: evid_sha, REV12: rev12_sha,
        },
        "machine_evidence": {
            "instrument": f"artifacts/worker-072/f2a_review/check_f2a.py#{sh(inst)[:12]}",
            "report": f"artifacts/worker-072/f2a_review/report.json#{sh(rel(report_path))[:12]}",
            "summary": counts,
            "controls": report.get("controls_run", {}).get("summary", {}),
            "delta_change_set": report.get("delta_rev12_rev13", {}).get("changed_paths", []),
        },
        "findings": findings,
        "falsifier": (f"A re-measure of {SCHEMA} differing from {schema_sha[:12]}; any of the 20 checks failing on a clean re-run; "
                      "a rev12->rev13 change path outside the six named non-semantic paths; or a mutation-control escape on re-run."),
        "next_falsifier": ("Re-run artifacts/worker-072/f2a_review/check_f2a.py --controls at the FROZEN rev29 pins; "
                           "the verdict is void if the F2a hash differs from " + schema_sha[:12] + "."),
        "not_claimed": ("No gate verdict, no node done, no theorem/counterexample, no mathematics verdict, no citation verdict, "
                        "no adjudication of the consistency-evidence content weakness (W072F2A-03) or of the protocol/CLASSSEP contests."),
        "authority_note": "Worker evidence only. G-FORM coverage is adjudicated by the audit lead and recorded by Astra; this file does not move a gate.",
    }
    review_path = os.path.join(ROOT, "reviews", f"F2a-review-worker-072-rev13.json")
    with open(review_path, "w", encoding="utf-8") as f:
        json.dump(review, f, indent=1)
        f.write("\n")

    # MANIFEST
    files = []
    for pat in ("check_f2a.py", "report.json", "README.md", "pins/*.yaml", "controls/controls_summary.json"):
        for p in sorted(glob.glob(os.path.join(ART, pat))):
            if os.path.isfile(p):
                files.append({"path": rel(p), "sha256": sh(p), "bytes": os.path.getsize(p)})
    files.append({"path": rel(review_path), "sha256": sh(rel(review_path)), "bytes": os.path.getsize(review_path)})
    manifest = {
        "task_id": TASK, "worker": "worker-072", "generated_at": now(),
        "class_id": "AF-SCC-C2-VAC-GEN", "node_id": "F2a", "gate": "G-FORM",
        "verdict": "accept", "score": 4.5,
        "bound_artifact_sha256": schema_sha,
        "files": files,
        "falsifier": review["falsifier"],
        "authority": "worker artifact; no gate verdict",
    }
    man_path = os.path.join(ART, "MANIFEST.json")
    with open(man_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1)
        f.write("\n")

    print(json.dumps({"review": rel(review_path), "review_sha256": sh(rel(review_path)),
                      "manifest": rel(man_path), "manifest_sha256": sh(rel(man_path)),
                      "schema_sha256": schema_sha, "counts": counts,
                      "controls": manifest and report.get("controls_run", {}).get("summary", {})}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
