#!/usr/bin/env python3
"""Phase 1 (pre-registration, no network): freeze the L1 rows under adjudication.

Bounded task W025-L1-MISMATCH-ADJ-01 (actor worker-025, node L1, gate G-LIT).

Target: the three MISMATCH hard failures reported by L1 spot check #4
(artifacts/worker-086/l1_spotcheck/spotcheck-l1-086.json):
    SRC-004  (class AF-SCC-C0-VAC-GEN;AF-SCC-C2-VAC-GEN)
    SRC-025  (class AF-SCC-C2-VAC-GEN)
    SRC-033  (class AF-SCC-C2-VAC-GEN)
plus one positive control row (SRC-001, reported MATCH by spot check #4).

This phase records, before any fetch:
  * sha256 of ledger/citation_audit.csv and of spot check #4's artifact;
  * the exact CSV records (canonical field dict + raw line bytes + line sha256)
    for the frozen ids;
  * the hypotheses, falsifier and control plan.

Run:  python3 freeze_inputs.py            # writes freeze/frozen_inputs.json + freeze/frozen_rows.json
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone

CST = timezone(timedelta(hours=8))
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
LEDGER = os.path.join(ROOT, "ledger", "citation_audit.csv")
SPOT4 = os.path.join(ROOT, "artifacts", "worker-086", "l1_spotcheck", "spotcheck-l1-086.json")
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
FREEZE_DIR = os.path.join(OUT_DIR, "freeze")

TARGET_IDS = ["SRC-004", "SRC-025", "SRC-033"]
CONTROL_IDS = ["SRC-001"]


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_state() -> dict:
    try:
        rev = subprocess.run(
            ["git", "-C", ROOT, "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=10,
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "-C", ROOT, "status", "--porcelain"],
            capture_output=True, text=True, timeout=10,
        ).stdout.strip()
        return {"head": rev, "dirty": bool(dirty)}
    except Exception as exc:  # pragma: no cover - provenance only
        return {"head": None, "dirty": None, "error": f"{type(exc).__name__}: {exc}"}


def main() -> int:
    os.makedirs(FREEZE_DIR, exist_ok=True)
    raw = open(LEDGER, "rb").read()
    text = raw.decode("utf-8")
    lines = text.splitlines(keepends=True)
    reader = csv.DictReader(io.StringIO(text))
    rows = {r["citation_id"]: r for r in reader}
    # 1-based data-row index in file order (header excluded), matching spot check #4's convention
    order = [r["citation_id"] for r in csv.DictReader(io.StringIO(text))]

    frozen_rows = {}
    for cid in TARGET_IDS + CONTROL_IDS:
        if cid not in rows:
            raise SystemExit(f"frozen id missing from ledger: {cid}")
        row = rows[cid]
        line_idx = order.index(cid)  # 0-based over data rows
        raw_line = lines[line_idx + 1]  # +1 skips the header line
        frozen_rows[cid] = {
            "citation_id": cid,
            "data_row_1based": line_idx + 1,
            "raw_line_sha256": sha256_bytes(raw_line.encode("utf-8")),
            "raw_line_bytes": len(raw_line.encode("utf-8")),
            "fields": row,
        }

    frozen = {
        "schema": "w025-l1-mismatch-adjudication/freeze/v1",
        "task_id": "W025-L1-MISMATCH-ADJ-01",
        "actor": "worker-025",
        "node_id": "L1",
        "gate": "G-LIT",
        "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "created_at": now(),
        "phase": "pre_registration_before_any_fetch",
        "inputs": {
            "ledger/citation_audit.csv": {
                "path": "ledger/citation_audit.csv",
                "sha256": sha256_bytes(raw),
                "data_rows": len(order),
            },
            "artifacts/worker-086/l1_spotcheck/spotcheck-l1-086.json": {
                "path": "artifacts/worker-086/l1_spotcheck/spotcheck-l1-086.json",
                "sha256": sha256_file(SPOT4),
                "role": "claims under adjudication (spot check #4)",
            },
        },
        "target_ids": TARGET_IDS,
        "control_ids": CONTROL_IDS,
        "hypotheses": {
            "H1_genuine_defect": (
                "The three MISMATCH verdicts of spot check #4 are genuine citation defects: "
                "the cited work's registry metadata disagrees with the ledger row."
            ),
            "H0_comparison_artifact": (
                "The three MISMATCH verdicts are artifacts of comparing an arXiv preprint "
                "(fetched by spot check #4) against a journal-of-record citation: the ledger's "
                "declared DOI resolves to a registry record that matches the ledger's journal "
                "metadata (title, authors, venue, year of record)."
            ),
        },
        "decision_rule": (
            "Per target row: fetch the declared DOI via Crossref (registry of record). "
            "DOI_MATCH = resolves AND title identity matches AND author overlap AND year within 1 "
            "AND container-title token present -> H0 (false positive) for that row; "
            "DOI_MISMATCH = resolves but work identity differs -> H1 for that row; "
            "DOI_UNRESOLVED = declared DOI does not resolve -> blocks adjudication "
            "(fed back as a genuine locator defect, not a false positive)."
        ),
        "falsifier": (
            "Any target row whose declared DOI fails to resolve, or whose Crossref record "
            "disagrees with the ledger on work identity (title/authors) or year beyond +/-1, "
            "refutes the false-positive adjudication for that row and confirms a genuine defect. "
            "The adjudication is void if the mutated-DOI negative control is not rejected by the "
            "same comparator (rubber-stamp check), or if the ledger hash drifts from the frozen "
            "sha during the fetch window (fail-closed)."
        ),
        "control_plan": {
            "CTRL-POS-SRC-001": "declared DOI fetch must classify DOI_MATCH (pipeline can return MATCH)",
            "CTRL-NEG-MUTATED-DOI": "SRC-004 DOI with final digit changed must NOT classify DOI_MATCH",
            "CTRL-NEG-SYNTHETIC-TITLE": "offline: SRC-004 ledger title replaced by 'Zeta functions of nothing' must classify DOI_MISMATCH against the real fetched record",
        },
        "stop_rule": "bounded: 4 DOI fetches + 2 arXiv fetches; no ledger writes; no gate or node status.",
        "provenance": {"git": git_state(), "python": sys.version.split()[0]},
    }

    with open(os.path.join(FREEZE_DIR, "frozen_rows.json"), "w", encoding="utf-8") as f:
        json.dump(frozen_rows, f, indent=1, sort_keys=True)
        f.write("\n")
    with open(os.path.join(FREEZE_DIR, "frozen_inputs.json"), "w", encoding="utf-8") as f:
        json.dump(frozen, f, indent=1, sort_keys=True)
        f.write("\n")

    print(json.dumps({
        "ledger_sha256": frozen["inputs"]["ledger/citation_audit.csv"]["sha256"],
        "spot4_sha256": frozen["inputs"]["artifacts/worker-086/l1_spotcheck/spotcheck-l1-086.json"]["sha256"],
        "frozen_ids": TARGET_IDS + CONTROL_IDS,
        "out": ["freeze/frozen_inputs.json", "freeze/frozen_rows.json"],
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
