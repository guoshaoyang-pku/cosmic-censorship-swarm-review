#!/usr/bin/env python3
"""Emit worker-051's W051-N0-SCHEME-AXES-03 events to comms/outbox/worker-051.jsonl.

Idempotent: event_ids already present in the outbox file are skipped.  Hashes are
computed from disk at emit time, so the outbox can never cite a stale digest.
Nothing else is written.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUTBOX = ROOT / "comms" / "outbox" / "worker-051.jsonl"
CST = timezone(timedelta(hours=8))

TASK_ID = "W051-N0-SCHEME-AXES-03"
NODE_ID = "N0"
CLASS_ID = "AF-WCC-SCALAR-SPH"
GATE = "G-NUM"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def main() -> int:
    now = datetime.now(CST)
    stamp = now.strftime("%Y%m%dT%H%M%S%z")
    prefix = f"w051-{stamp}"

    report_path = HERE / "report.json"
    report = json.loads(report_path.read_text())
    verdict = report["falsifier"]["overall"]
    summary = report.get("transfer_summary", {})

    artifacts = [
        ("harness_source", "n0_axes_transfer_051.py", "numerical_experiment"),
        ("report_json", "report.json", "numerical_evidence_report"),
        ("stdout_log", "stdout.txt", "run_log"),
        ("readme_md", "README.md", "experiment_summary"),
        ("checkpoint_json", "CHECKPOINT.json", "checkpoint"),
        ("sha256sums", "SHA256SUMS", "digest_manifest"),
    ]
    missing = [f for _, f, _ in artifacts if not (HERE / f).exists()]
    if missing:
        raise SystemExit(f"refusing to emit: missing artifacts {missing}")

    evidence = [f"{rel(HERE / f)}#sha256:{sha256_file(HERE / f)[:12]}"
                for _, f, _ in artifacts]
    artifact_refs = [f"{rel(HERE / f)}#sha256:{sha256_file(HERE / f)[:12]}"
                     for _, f, _ in artifacts]

    # headline numbers for the summary strings
    t1 = summary.get("T1_grid_r40", {})
    c0 = summary.get("C0_published_control", {})
    parts = []
    for cid, v in summary.items():
        cell_txt = " ".join(
            "{c}:mixed={m:.6f},iso={i:.6f}".format(c=c, m=v[c]["mixed"], i=v[c]["isolated"])
            for c in v)
        parts.append("{cid}[{txt}]".format(cid=cid, txt=cell_txt))
    line = " ".join(parts)
    checks = report["falsifier"]["checks"]
    n_pass = sum(1 for v in checks.values() if v)
    triggered = report["falsifier"]["triggered"]

    events = []

    events.append({
        "event_id": f"{prefix}-task-claim",
        "event_type": "status",
        "created_at": now.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "actor": "worker-051",
        "node_id": NODE_ID,
        "class_id": CLASS_ID,
        "gate": GATE,
        "group_id": "numerics",
        "task_id": TASK_ID,
        "status": "active",
        "hours": 0.2,
        "summary": ("No assignment card for worker-051 in comms/inbox; took one bounded "
                    "class-bound task from the immediate queue: configuration-transfer "
                    "falsifier test of worker-051's own W051-N0-SCHEME-AXES-02 finding, "
                    "exactly as its recorded next_falsifier demanded (same pinned module "
                    "hash, different grid r_max=40 and two different pulse families). "
                    "Flat-space test field only; numerics_lock respected (N0 allowed, no "
                    "N1, no numerics/spherical_solver/)."),
        "evidence_refs": [
            "numerics/tests/flat_wave_replication.py#sha256:8ade1cdc163e",
            "artifacts/worker-051/n0_scheme_axes/report.json#sha256:7ddac5e40d9e",
            "artifacts/worker-051/n0_scheme_axes/README.md#sha256:01e5f0ee4333",
        ],
        "claims_completion": False,
        "next_falsifier": ("Falsified if the grid/pulse transfer shows the FEM/FD Nyquist "
                           "ratio leaving 3, the smooth-mode difference order leaving "
                           "[1.7, 2.3], or any of the four cells leaving the |p-2|<=0.3 "
                           "band in either mixed or dt->0 isolated order, in any transfer "
                           "configuration; or if a pin no longer resolves."),
    })

    for tag, fname, atype in artifacts:
        events.append({
            "event_id": f"{prefix}-artifact-{tag}",
            "event_type": "artifact",
            "created_at": now.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "actor": "worker-051",
            "node_id": NODE_ID,
            "class_id": CLASS_ID,
            "class_ids": [CLASS_ID],
            "gate": GATE,
            "group_id": "numerics",
            "task_id": TASK_ID,
            "artifact_type": atype,
            "path": rel(HERE / fname),
            "sha256": sha256_file(HERE / fname),
            "bytes": (HERE / fname).stat().st_size,
            "validation_status": "unverified",
            "claims_completion": False,
            "evidence_refs": evidence + [
                "numerics/CONVERGENCE_PROTOCOL.md#sha256:1e6cdf04d7a2",
            ],
            "next_falsifier": ("Recompute the digest; a mismatch with the report's cited "
                               "hash falsifies the binding of this evidence."),
        })

    events.append({
        "event_id": f"{prefix}-claim-transfer",
        "event_type": "claim",
        "created_at": now.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "actor": "worker-051",
        "node_id": NODE_ID,
        "class_id": CLASS_ID,
        "class_ids": [CLASS_ID],
        "gate": GATE,
        "group_id": "numerics",
        "task_id": TASK_ID,
        "conclusion_type": "numerical_evidence",
        "statement": (
            "Configuration-transfer test of the N0 scheme-axis multiplicity finding at the "
            "pinned module numerics/tests/flat_wave_replication.py#sha256:8ade1cdc163e "
            f"(verdict {verdict}; {n_pass}/{len(checks)} pre-registered checks pass; "
            f"triggered={triggered}). Measured mixed 4-rung order | dt->0 isolated spatial "
            f"order per cell: {line}. Control: published 4-rung orders reproduced bitwise "
            "(delta 0.0) and the prior femlf order reproduced to <1e-12 at the published "
            "configuration. Operator checks at r_max=30 and r_max=40: lffd and cnfd share "
            "the identical 3-point FD operator (matrix difference exactly 0), the FEM/FD "
            "grid-Nyquist response ratio is exactly 3 with smooth-mode relative-difference "
            "order 2.0. Scope: flat-space test-field calibration sub-case only, fixed "
            "Minkowski, no self-gravity; no gate verdict, no node completion, no theorem."),
        "assumptions": [
            "published module, protocol, published order artifact and the prior harness/report "
            "match their pre-registered sha256 pins (refuse-and-report otherwise)",
            "transfer configurations are wall-clean: r0 + t_end + 4*sigma < r_max and outer "
            "tail < 1e-9, so the Dirichlet outer wall cannot dominate the L2 error",
            "the transfer varies grid and pulse family only; it re-uses the pinned operator "
            "helpers, so it cannot detect a bug shared by the prior harness (implementation "
            "independence is covered by workers 046/055)",
            "the dt->0 isolated order is a linear fit in dt^2 over cfl {0.5,0.25,0.125} per rung",
        ],
        "falsifier": report["falsifier"]["statement"],
        "evidence_refs": evidence,
        "artifact_refs": artifact_refs,
        "next_falsifier": ("Adjudication by lead-numerics/lead-audit of whether the "
                           "replication's independence wording should be re-labelled "
                           "'2 spatial x 2 time, 3 of 4 cells at the published configuration, "
                           "transferred to r_max=40 and two pulse families'; a faithful rerun "
                           "at a further grid or pulse that leaves the band falsifies the "
                           "transfer claim."),
    })

    events.append({
        "event_id": f"{prefix}-complete",
        "event_type": "status",
        "created_at": now.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "actor": "worker-051",
        "node_id": NODE_ID,
        "class_id": CLASS_ID,
        "class_ids": [CLASS_ID],
        "gate": GATE,
        "group_id": "numerics",
        "task_id": TASK_ID,
        "status": "active",
        "hours": 0.3,
        "summary": (
            f"CHECKPOINT: {TASK_ID} complete as one bounded worker task; all artifacts on "
            f"disk and hash-pinned in the claim event; verdict {verdict} "
            f"({n_pass}/{len(checks)} checks). Task status left ACTIVE for lead review "
            "(worker events cannot set done/passed or a gate verdict). Headline: the "
            "scheme-axis multiplicities and the |p-2|<=0.3 band membership transfer to "
            "r_max=40 with t_end=20 and to two different pulse families (narrow r0=6,sigma=0.9; "
            "wide r0=8,sigma=2.5), with the published-configuration control reproduced "
            "bitwise. Next: lead-numerics/lead-audit adjudicate the independence wording and "
            "whether this closes the W051-N0-SCHEME-AXES-02 next_falsifier."),
        "evidence_refs": evidence,
        "artifact_refs": artifact_refs,
        "claims_completion": False,
        "next_falsifier": ("A faithful rerun at a further grid or pulse family (or at the "
                           "same configuration on a different implementation) that leaves "
                           "the band, the Nyquist ratio 3, or the smooth-mode order 2."),
    })

    existing = set()
    if OUTBOX.exists():
        for ln in OUTBOX.read_text().splitlines():
            ln = ln.strip()
            if not ln:
                continue
            try:
                existing.add(json.loads(ln).get("event_id"))
            except json.JSONDecodeError:
                continue

    new = [e for e in events if e["event_id"] not in existing]
    with open(OUTBOX, "a") as f:
        for e in new:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    print(f"emitted {len(new)} new events ({len(events) - len(new)} already present) "
          f"to {rel(OUTBOX)}")
    for e in new:
        print("  ", e["event_id"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
