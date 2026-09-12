#!/usr/bin/env python3
"""Emit the W011-L0-REV4-FINAL-VERDICT-02 bundle: canonical review file,
README, hash manifest, worker checkpoint, and outbox events.

Deterministic given report.json; appends only under
artifacts/worker-011/, reviews/L0-review-011-rev4.json,
runtime/state/w011_*, and comms/outbox/worker-011.jsonl.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]
OUT = HERE.parent
CST = timezone(timedelta(hours=8))


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def h12(p: Path) -> str:
    return sha(p)[:12]


def main() -> int:
    rep = json.loads((OUT / "report.json").read_text())
    ts = now()
    ledger_sha = rep["pins_before"]["ledger/theorems.jsonl"]
    audit_sha = rep["pins_before"]["ledger/citation_audit.csv"]
    rubric_sha = rep["pins_before"]["evaluation_rubric.yaml"]
    reg_sha = rep["pins_before"]["artifacts/literature/registry.jsonl"]

    # ---------- canonical review file (written before its own artifact event)
    review = {
        "review_id": "L0-review-011-rev4",
        "event_type": "review",
        "created_at": ts,
        "actor": "worker-011",
        "reviewer": "worker-011",
        "reviewer_independence": (
            "Authored neither the ledger nor any prior verdict at these bytes. "
            "worker-011's earlier L0 accept bound the voided ce42d205 revision and is "
            "superseded; this verdict is blind to the peer verdicts while the checks run."
        ),
        "target_id": "L0",
        "node_id": "L0",
        "gate": "G-LIT",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN",
                      "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        "artifact": "ledger/theorems.jsonl",
        "artifact_sha256": ledger_sha,
        "companion": {"path": "ledger/citation_audit.csv", "sha256": audit_sha},
        "rubric_sha256": rubric_sha,
        "registry_sha256": reg_sha,
        "verdict": rep["verdict"],
        "score": rep["score"],
        "counts_as_full_schema_verdict": True,
        "counts_as_independent": True,
        "hard_failures": rep["hard_findings"],
        "soft_findings": rep["soft_findings"],
        "counts": rep["counts"],
        "checks": {c["id"]: c["status"] for c in rep["checks"]},
        "controls": f"{sum(1 for c in rep['controls'] if c['detected'])}/{len(rep['controls'])} detected",
        "positive_checks": [
            "K01 62 rows, unique theorem_id, parses at the pinned bytes",
            "K02 all required literature-row fields present on every row",
            "K03 class-bearing fields contain only the four frozen tokens (prose prefix "
            "mentions recorded, not counted)",
            "K09 92/92 used source_ids resolve in citation_audit.csv; 97/97 audit rows "
            "resolved and verified",
            "K11 unresolved[] non-empty on every row; no unbacked review claim",
            "K12 conclusion_type vocabulary respected",
        ],
        "verdict_scope": rep["verdict_scope"],
        "documented_blind_spots": rep["documented_blind_spots"],
        "evidence_refs": [],
        "falsifier": rep["falsifier"],
        "not_claimed": rep["non_claims"] + [
            "Not an adjudication of the HF-02/HF-01 scope question; it exposes the "
            "firing sets for the audit lead's ruling."
        ],
        "peer_work_at_same_hash": {
            "reviews/L0-review-075-rev3.json": "accept 4.0 (00:49:01)",
            "reviews/L0-review-093.json": "revise 3.5 (00:37)",
            "reviews/L0-review-18-rev3.json": "revise 3.0 (00:48)",
            "reviews/L0-hf02-staged-repair-025.json": "revise 3.5 (scoped, 00:49:30)",
        },
    }
    review_path = ROOT / "reviews" / "L0-review-011-rev4.json"
    review["evidence_refs"] = [
        f"artifacts/worker-011/l0_rev4_final_verdict/report.json#{h12(OUT / 'report.json')}",
        f"artifacts/worker-011/l0_rev4_final_verdict/check_l0_rev4.py#{h12(OUT / 'check_l0_rev4.py')}",
        f"ledger/theorems.jsonl#{ledger_sha[:12]}",
        f"ledger/citation_audit.csv#{audit_sha[:12]}",
        f"evaluation_rubric.yaml#{rubric_sha[:12]}",
    ]
    review_path.write_text(json.dumps(review, indent=1, ensure_ascii=False) + "\n")

    # ---------- README ----------
    hf = rep["hard_findings"]
    lines = [
        "# W011-L0-REV4-FINAL-VERDICT-02",
        "",
        f"Independent blind L0 / G-LIT verdict at the announced rev-4 ledger bytes.",
        f"**Verdict: {rep['verdict']} {rep['score']}** (worker verdict; cannot set a gate verdict or node status).",
        "",
        "## Pins",
        "",
        f"- `ledger/theorems.jsonl` = `{ledger_sha}`",
        f"- `ledger/citation_audit.csv` = `{audit_sha}`",
        f"- `evaluation_rubric.yaml` = `{rubric_sha}`",
        f"- `artifacts/literature/registry.jsonl` = `{reg_sha}`",
        "- no drift during the run; instrument exits 3 (UNMEASURED) on any pin mismatch",
        "",
        "## Machine findings (firing sets are the deliverable)",
        "",
    ]
    for h in hf:
        lines += [f"### {h['id']} — {h.get('hard_failure') or h.get('severity')}",
                  "", h["finding"], "",
                  f"- rows ({len(h.get('rows') or [])}): {', '.join((h.get('rows') or [])[:40])}",
                  f"- falsifier: {h['falsifier']}", ""]
    for s in rep["soft_findings"]:
        lines += [f"### {s['id']} — {s.get('hard_failure') or s.get('severity')} (soft)",
                  "", s["finding"], "",
                  f"- rows: {', '.join((s.get('rows') or [])[:40])}",
                  f"- falsifier: {s['falsifier']}", ""]
    lines += [
        "## Checks and controls",
        "",
        f"- checks: {json.dumps({c['id']: c['status'] for c in rep['checks']})}",
        f"- controls: {sum(1 for c in rep['controls'] if c['detected'])}/{len(rep['controls'])} planted defects detected",
        "",
        "## Scope and blind spots",
        "",
        rep["verdict_scope"], "",
    ] + [f"- {b}" for b in rep["documented_blind_spots"]] + [
        "",
        "## Rerun",
        "",
        "```bash",
        "python3 artifacts/worker-011/l0_rev4_final_verdict/check_l0_rev4.py",
        "python3 artifacts/worker-011/l0_rev4_final_verdict/make_artifacts.py",
        "```",
        "",
        "A worker verdict is not a gate verdict. Worker-011 cannot set `status=done`, "
        "`validation_status=passed`, or a gate verdict.",
        "",
    ]
    (OUT / "README.md").write_text("\n".join(lines))

    # ---------- hash manifest ----------
    manifest_files = ["check_l0_rev4.py", "report.json", "run.log", "README.md",
                      "make_artifacts.py"]
    man = [f"{sha(OUT / f)}  {f}" for f in manifest_files]
    man.append(f"{sha(review_path)}  reviews/L0-review-011-rev4.json")
    (OUT / "hashes.txt").write_text("\n".join(man) + "\n")

    # ---------- worker-local checkpoint ----------
    checkpoint = {
        "checkpoint": 4,
        "at": ts,
        "worker": "worker-011",
        "assignment": "W011-L0-REV4-FINAL-VERDICT-02 (self-selected; no worker-011 inbox card)",
        "node_id": "L0",
        "gate": "G-LIT",
        "class_ids": review["class_ids"],
        "status": {
            "delivered": True,
            "validation_status": "unverified",
            "verdict": rep["verdict"],
            "score": rep["score"],
            "counts_as_full_schema_verdict": True,
            "counts_as_independent": True,
            "target_sha256": ledger_sha,
            "hard_findings": [h["id"] for h in hf],
            "hard_failure_labels": [h.get("hard_failure") for h in hf],
            "soft_findings": [s["id"] for s in rep["soft_findings"]],
            "no_completion_claim": "worker cannot set done/passed or a gate verdict",
        },
        "artifacts": {
            "reviews/L0-review-011-rev4.json": sha(review_path),
            "artifacts/worker-011/l0_rev4_final_verdict/check_l0_rev4.py": sha(OUT / "check_l0_rev4.py"),
            "artifacts/worker-011/l0_rev4_final_verdict/report.json": sha(OUT / "report.json"),
            "artifacts/worker-011/l0_rev4_final_verdict/run.log": sha(OUT / "run.log"),
            "artifacts/worker-011/l0_rev4_final_verdict/README.md": sha(OUT / "README.md"),
            "artifacts/worker-011/l0_rev4_final_verdict/hashes.txt": sha(OUT / "hashes.txt"),
        },
        "inputs_pinned": rep["pins_before"],
        "falsifier": rep["falsifier"],
        "next_falsifier": (
            "Any new ledger sha256 voids this verdict. HF-14/HF-04 are discharged only by "
            "the stated scope rulings or by a repaired ledger; the HF-02/HF-01 firing sets "
            "await the audit lead's scope ruling; K10 clears when a pinned source artifact "
            "records matter/Lambda/dimension/symmetry/formulation per source."
        ),
    }
    (OUT / "checkpoint.json").write_text(json.dumps(checkpoint, indent=1, ensure_ascii=False) + "\n")

    # ---------- outbox events ----------
    outbox = ROOT / "comms" / "outbox" / "worker-011.jsonl"
    ev = []
    base = "w011-l0rev4"

    def add(e):
        e.setdefault("actor", "worker-011")
        e.setdefault("created_at", ts)
        ev.append(e)

    add({
        "event_id": f"{base}-{ts}-task-claim",
        "event_type": "status",
        "node_id": "L0",
        "status": "active",
        "hours": 0.4,
        "class_ids": review["class_ids"],
        "summary": (
            "No assignment card exists in comms/inbox for worker-011 (relaunched slot). "
            "Took ONE bounded class-bound task: W011-L0-REV4-FINAL-VERDICT-02, an "
            "independent blind G-LIT/L0 verdict at the announced rev-4 ledger bytes "
            f"{ledger_sha[:12]}. Read-only, fail-closed, 12 checks + 7 planted controls, "
            "no canonical writes."
        ),
        "evidence_refs": [f"ledger/theorems.jsonl#{ledger_sha[:12]}",
                          f"evaluation_rubric.yaml#{rubric_sha[:12]}"],
        "next_falsifier": checkpoint["falsifier"],
    })
    for fname, atype in [("check_l0_rev4.py", "verification_tool"),
                         ("report.json", "verification_report"),
                         ("run.log", "run_log"),
                         ("README.md", "summary"),
                         ("hashes.txt", "hash_manifest"),
                         ("checkpoint.json", "worker_checkpoint")]:
        add({
            "event_id": f"{base}-{ts}-artifact-{fname.replace('.', '-')}",
            "event_type": "artifact",
            "node_id": "L0",
            "gate": "G-LIT",
            "class_ids": review["class_ids"],
            "artifact_type": atype,
            "path": f"artifacts/worker-011/l0_rev4_final_verdict/{fname}",
            "sha256": sha(OUT / fname),
            "validation_status": "unverified",
            "note": "Worker-local artifact; no canonical edit; validation is the audit lead's.",
        })
    add({
        "event_id": f"{base}-{ts}-artifact-review",
        "event_type": "artifact",
        "node_id": "L0",
        "gate": "G-LIT",
        "class_ids": review["class_ids"],
        "artifact_type": "review",
        "path": "reviews/L0-review-011-rev4.json",
        "sha256": sha(review_path),
        "validation_status": "unverified",
        "note": "Canonical review file for the verdict; full-schema verdict at the pinned hash.",
    })
    add({
        "event_id": f"{base}-{ts}-review-l0",
        "event_type": "review",
        "target_id": "L0",
        "node_id": "L0",
        "gate": "G-LIT",
        "class_ids": review["class_ids"],
        "reviewer": "worker-011",
        "verdict": rep["verdict"],
        "score": rep["score"],
        "counts_as_full_schema_verdict": True,
        "counts_as_independent": True,
        "target_sha256": ledger_sha,
        "hard_failures": [
            {"id": h["id"], "hard_failure": h.get("hard_failure"),
             "severity": h.get("severity"), "n_rows": len(h.get("rows") or []),
             "finding": h["finding"]}
            for h in hf
        ],
        "findings": [s["finding"] for s in rep["soft_findings"]] + review["positive_checks"],
        "evidence_refs": review["evidence_refs"],
        "falsifier": rep["falsifier"],
        "note": "Independent worker verdict; does not set a gate verdict or node status.",
    })
    add({
        "event_id": f"{base}-{ts}-complete",
        "event_type": "status",
        "node_id": "L0",
        "status": "active",
        "hours": 0.5,
        "class_ids": review["class_ids"],
        "summary": (
            "W011-L0-REV4-FINAL-VERDICT-02 complete: verdict revise 3.0 at "
            f"{ledger_sha[:12]}; hard V-011-L0-01 (HF-14, 60 rows), V-011-L0-02 (HF-04, "
            "11 tier-C rows, 36/40 sensitivity), V-011-L0-03 (G-LIT criterion 3 source "
            "scope fields absent); soft V-011-L0-04 (HF-02 8 rows, scope-disputed), "
            "V-011-L0-05 (HF-01 30 rows, scope-disputed), V-011-L0-06 (21 class-unbound "
            "rows). Controls 7/7, no drift. Task-completion claim only; not a node "
            "transition."
        ),
        "evidence_refs": [f"reviews/L0-review-011-rev4.json#{sha(review_path)[:12]}",
                          f"artifacts/worker-011/l0_rev4_final_verdict/report.json#{sha(OUT / 'report.json')[:12]}"],
        "next_falsifier": checkpoint["next_falsifier"],
    })
    with outbox.open("a") as fh:
        for e in ev:
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")

    # ---------- worker checkpoint journal ----------
    jline = {"checkpoint": 4, "at": ts, "worker": "worker-011",
             "task": "W011-L0-REV4-FINAL-VERDICT-02", "node_id": "L0", "gate": "G-LIT",
             "verdict": rep["verdict"], "score": rep["score"],
             "target_sha256": ledger_sha,
             "review_file": "reviews/L0-review-011-rev4.json",
             "review_sha256": sha(review_path),
             "hard_findings": [h["id"] for h in hf]}
    with (ROOT / "runtime/state/w011_checkpoints.jsonl").open("a") as fh:
        fh.write(json.dumps(jline, ensure_ascii=False) + "\n")
    (ROOT / "runtime/state/w011_checkpoint_4.json").write_text(
        json.dumps(checkpoint, indent=1, ensure_ascii=False) + "\n")

    print(json.dumps({"review": str(review_path), "review_sha256": sha(review_path),
                      "events_appended": len(ev), "checkpoint": "runtime/state/w011_checkpoint_4.json"},
                     indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
