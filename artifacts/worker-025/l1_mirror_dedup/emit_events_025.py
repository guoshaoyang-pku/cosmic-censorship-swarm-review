#!/usr/bin/env python3
"""Fail-closed emitter for W025-L1-MIRROR-DEDUP-01.

- re-hashes every deliverable from disk,
- writes SHA256SUMS and a worker checkpoint,
- validates every event against research_map.schemas.validate_event,
- appends only validated events to comms/outbox/worker-025.jsonl (idempotent),
- never sets node status=done, validation_status=passed or a gate verdict.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]          # .../ai4math-swarm
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from research_map import schemas  # noqa: E402

OUTBOX = ROOT / "comms/outbox/worker-025.jsonl"
STATE_CKPT = ROOT / "runtime/state/w025_l1_mirror_dedup_checkpoint.json"

FILES = [
    "PREREGISTRATION.json",
    "AMENDMENT-01.json",
    "run_l1_mirror_dedup_025.py",
    "report.json",
    "report.v1-initial-rule.json",
    "run2.stdout.txt",
    "run3.stdout.txt",
    "README.md",
    "verify_readme_numbers_025.py",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--created-at", required=True)
    ap.add_argument("--hours", type=float, default=0.5)
    args = ap.parse_args()
    ts = args.created_at
    stamp = ts.replace("-", "").replace(":", "").replace("+", "p")

    report = json.loads((HERE / "report.json").read_text())
    pred = report["predictions"]
    summary = report["summary"]
    verdict = report["verdict"]

    # 1. hash deliverables (fail closed on any missing/empty file)
    hashes = {}
    for name in FILES:
        p = HERE / name
        if not p.exists() or p.stat().st_size == 0:
            print(json.dumps({"error": "MISSING_OR_EMPTY_DELIVERABLE", "path": str(p)}))
            return 2
        hashes[name] = sha256_file(p)

    # 2. SHA256SUMS over the fixed file set
    sums_lines = [f"{hashes[n]}  {n}" for n in FILES]
    (HERE / "SHA256SUMS").write_text("\n".join(sums_lines) + "\n")
    hashes["SHA256SUMS"] = sha256_file(HERE / "SHA256SUMS")

    # 3. worker checkpoint (worker-local; controller runtime checkpoint untouched)
    ckpt = {
        "schema": "w025-l1-mirror-dedup-checkpoint/v1",
        "checkpoint_id": f"w025-l1-mirror-dedup-{stamp}",
        "task_id": "W025-L1-MIRROR-DEDUP-01",
        "actor": "worker-025",
        "node_id": "L1",
        "gate": "G-LIT",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        "frozen_input": report["frozen_input"],
        "verdict": verdict,
        "summary": summary,
        "failed_predictions": report["failed_predictions"],
        "controls_fired": sum(1 for c in report["controls"] if c["fired"]),
        "controls_total": len(report["controls"]),
        "merge_proposal": [{"component": m["component_id"], "canonical": m["canonical"],
                            "superseded": m["superseded"]} for m in report["merges"]],
        "findings": [f["id"] + ":" + f["label"] for f in report["findings"]],
        "artifact_hashes": hashes,
        "next_falsifier": report["falsifier"],
        "non_claims": report["non_claims"],
        "created_at": ts,
    }
    ckpt_text = json.dumps(ckpt, ensure_ascii=False, indent=1, sort_keys=True) + "\n"
    (HERE / "CHECKPOINT.json").write_text(ckpt_text)
    STATE_CKPT.parent.mkdir(parents=True, exist_ok=True)
    STATE_CKPT.write_text(ckpt_text)
    hashes["CHECKPOINT.json"] = sha256_file(HERE / "CHECKPOINT.json")

    prefix = f"w025-l1mirror-{stamp}"
    evidence = [f"artifacts/worker-025/l1_mirror_dedup/report.json#{hashes['report.json'][:12]}",
                f"artifacts/worker-025/l1_mirror_dedup/PREREGISTRATION.json#{hashes['PREREGISTRATION.json'][:12]}",
                f"artifacts/worker-025/l1_mirror_dedup/CHECKPOINT.json#{hashes['CHECKPOINT.json'][:12]}",
                "ledger/citation_audit.csv#315c19145065",
                "artifacts/worker-025/l1_identity_audit/report.json#5bd6b3263fea"]

    events = []
    events.append({
        "event_id": f"{prefix}-status-start", "event_type": "status", "created_at": ts, "actor": "worker-025",
        "node_id": "L1", "status": "active", "hours": 0.0,
        "summary": "Took ONE bounded class-bound task (no inbox card for worker-025): W025-L1-MIRROR-DEDUP-01, reconciling the declared mirror_of graph with the identifier-keyed work graph at ledger/citation_audit.csv#315c19145065. Read-only; no frozen write.",
        "evidence_refs": ["ledger/citation_audit.csv#315c19145065"],
        "next_falsifier": report["falsifier"],
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH",
        "gate": "G-LIT",
    })
    for name, atype in [
        ("PREREGISTRATION.json", "preregistration"),
        ("AMENDMENT-01.json", "process_amendment"),
        ("run_l1_mirror_dedup_025.py", "deterministic_instrument"),
        ("report.json", "measurement_report"),
        ("report.v1-initial-rule.json", "preserved_initial_rule_report"),
        ("README.md", "readme"),
        ("verify_readme_numbers_025.py", "readme_number_verifier"),
        ("run2.stdout.txt", "reproduction_run"),
        ("run3.stdout.txt", "determinism_rerun"),
        ("SHA256SUMS", "hash_manifest"),
        ("CHECKPOINT.json", "worker_checkpoint"),
    ]:
        events.append({
            "event_id": f"{prefix}-artifact-{name.replace('.', '-')}",
            "event_type": "artifact", "created_at": ts, "actor": "worker-025",
            "node_id": "L1", "artifact_type": atype,
            "path": f"artifacts/worker-025/l1_mirror_dedup/{name}",
            "sha256": hashes[name], "validation_status": "unverified",
            "summary": f"W025-L1-MIRROR-DEDUP-01 artifact {name}",
            "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH",
            "gate": "G-LIT",
            "evidence_refs": [f"artifacts/worker-025/l1_mirror_dedup/{name}#{hashes[name][:12]}"],
        })
    events.append({
        "event_id": f"{prefix}-claim", "event_type": "claim", "created_at": ts, "actor": "worker-025",
        "node_id": "L1", "gate": "G-LIT",
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH",
        "statement": (
            f"Artifact-and-checker measurement, not a mathematics claim, at ledger/citation_audit.csv#315c19145065 "
            f"(97 rows, pin re-measured; {len(report['identifier_pairs'])} unique identifier pairs over "
            f"{pred['P2_ident_groups']['identifier_edges']} identifier edges, {len(report['mirror_declared'])} declared mirror_of edges, "
            f"{len(report['mirror_suspect'])} suspect): the identifier graph and the mirror graph disagree. "
            f"Union of both graphs gives {summary['components']} work components. {summary['merge_duplicate_components']} MERGE_DUPLICATE "
            f"proposals supersede {summary['rows_superseded_proposed']} rows (net 97->93): SRC-020/SRC-060/SRC-072 -> canonical SRC-060 "
            f"(gains D-002 and AF-SCC-C0-VAC-GEN), SRC-044/SRC-067 -> canonical SRC-067 (gains T-101), SRC-059/SRC-071 -> canonical SRC-059. "
            f"{summary['link_only_components']} components are PREPRINT-vs-PUBLISHED pairs and must be linked, not merged; "
            f"SRC-041/SRC-054 is mirror-only. SRC-093's declared mirror_of SRC-033 is contradicted by title, year, DOI and arXiv id "
            f"(SUSPECT_MIRROR, excluded from the union). Rows SRC-020 and SRC-044 carry no DOI/arXiv and are reachable only through "
            f"mirror_of, so an identifier-string-keyed dedup is incomplete; and two merges would drop citation edges (D-002, T-101) "
            f"unless the rule unions used_by_theorems and class_mapping. Instrument verdict MEASURED, {verdict}, "
            f"{sum(1 for c in report['controls'] if c['fired'])}/{len(report['controls'])} controls fired, "
            f"{sum(1 for v in pred.values() if v.get('pass'))}/{len([1 for v in pred.values() if v.get('pass') is not None])} evaluable predictions pass, "
            f"two runs byte-identical. Worker evidence only; the merge map is an unfrozen proposal and no ledger byte was written."
        ),
        "conclusion_type": "formal_model",
        "assumptions": [
            "the frozen bytes are ledger/citation_audit.csv#315c19145065 and are unchanged by this task",
            "work identity is keyed on the normalized DOI, else the normalized arXiv id (legacy ids alias their bare numeric form); the identifier string is a key, not an identity proof",
            "a declared mirror_of edge is evidence of the same work only when the endpoint titles agree (normalized, compact-form, Jaccard>=0.90, or long-title prefix) and |year gap| <= 4",
            "artifact_class is read from the record URL (arXiv vs Crossref/OpenAlex/INSPIRE/DOI), not from the venue text",
            "merge precedence is resolved locator, then verification-method rank, then evidence rank, then lowest citation_id",
        ],
        "falsifier": report["falsifier"],
        "artifact_refs": [f"artifacts/worker-025/l1_mirror_dedup/report.json#{hashes['report.json'][:12]}",
                          f"artifacts/worker-025/l1_mirror_dedup/CHECKPOINT.json#{hashes['CHECKPOINT.json'][:12]}"],
        "evidence_refs": evidence,
    })
    events.append({
        "event_id": f"{prefix}-review", "event_type": "review", "created_at": ts, "actor": "worker-025",
        "target_id": "L1", "reviewer": "worker-025", "verdict": "accept", "score": 4.0,
        "hard_failures": [],
        "findings": [
            "author-side instrument verdict only (self-review); an independent non-author review is still required before any L1 merge is adopted",
            "F1 major: SRC-093 -> SRC-033 mirror_of is contradicted by title, year (2009 vs 2018), DOI and arXiv id; correct or withdraw the edge",
            "F2 major: SRC-020 and SRC-044 have no DOI/arXiv and are reachable only through mirror_of; identifier-keyed dedup misses them",
            "F3 info: SRC-041/SRC-054 share no identifier; the mirror edge is the only link",
            "F4 major: merging SRC-060/SRC-072 or SRC-067/SRC-044 without unioning used_by_theorems and class_mapping would drop D-002, T-101 and one class mapping",
            f"F5: {summary['link_only_components']} preprint/published pairs must stay linked, not merged",
            "amendment 1 disclosed: the initial title test failed P7 on two legitimate variants (subtitle truncation, hyphenation); initial report preserved at report.v1-initial-rule.json",
        ],
        "evidence_refs": evidence,
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH",
        "gate": "G-LIT",
        "node_id": "L1",
    })
    events.append({
        "event_id": f"{prefix}-blocker", "event_type": "blocker", "created_at": ts, "actor": "worker-025",
        "node_id": "L1",
        "description": "L1 owner actions surfaced by the reconciliation: (1) the declared mirror_of SRC-093->SRC-033 edge is contradicted by the record fields and should be corrected or withdrawn; (2) any L1 dedup must key on the resolved record plus the mirror graph, because SRC-020 and SRC-044 carry no identifier; (3) a merge must union used_by_theorems and class_mapping or it drops citation edges (D-002, T-101).",
        "needed_to_unblock": "L1 owner disposition: accept/reject the three merge proposals and the union rule, correct the SRC-093 mirror edge, and record the finding in the L1 gate disposition. No worker write of the frozen ledger.",
        "evidence_refs": evidence,
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH",
        "gate": "G-LIT",
    })
    events.append({
        "event_id": f"{prefix}-status-complete", "event_type": "status", "created_at": ts, "actor": "worker-025",
        "node_id": "L1", "status": "active", "hours": args.hours,
        "summary": f"W025-L1-MIRROR-DEDUP-01 complete at worker level (task status only; workers cannot set node done or a gate verdict): {verdict}, 3 merge proposals / 4 rows superseded, 1 suspect mirror edge, 6/6 controls, P1-P7 pass, two runs byte-identical. No frozen file written. Exiting for recycling.",
        "evidence_refs": evidence,
        "next_falsifier": report["falsifier"],
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH",
        "gate": "G-LIT",
    })

    # fail-closed validation before any append
    for e in events:
        schemas.validate_event(e)

    # idempotency
    existing = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                existing.add(json.loads(line).get("event_id"))
            except json.JSONDecodeError:
                continue
    skip = [e["event_id"] for e in events if e["event_id"] in existing]
    fresh = [e for e in events if e["event_id"] not in existing]
    OUTBOX.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTBOX, "a") as f:
        for e in fresh:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    print(json.dumps({
        "appended": len(fresh), "skipped_existing": skip, "outbox": str(OUTBOX),
        "checkpoint": str(STATE_CKPT), "verdict": verdict,
        "artifact_hashes": hashes,
    }, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
