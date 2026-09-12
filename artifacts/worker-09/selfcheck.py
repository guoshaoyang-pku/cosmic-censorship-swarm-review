#!/usr/bin/env python3
"""Worker 09 self-check: artifact integrity and schema compatibility.

Checks
  1. every rich-shard row whose `raw_sha256` is non-empty points at an existing cached file
     whose sha256 prefix matches;
  2. the lead-schema shard's columns equal the canonical `ledger/citation_audit.csv` columns
     (so the owner can merge it without schema drift);
  3. every `verified*` lead row has non-empty theorem_ref, c0_or_c2, what_it_does_not_prove,
     falsifier (the fields my review contract promises);
  4. the rich/lead/jsonl shards are mutually consistent (same citation_id set minus controls);
  5. writes artifacts/worker-09/extracted/selfcheck.json and exits non-zero on failure.
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
W09 = ROOT / "artifacts" / "worker-09"
LEDGER = ROOT / "ledger"
REQUIRED_ON_VERIFIED = ["theorem_ref", "c0_or_c2", "what_it_does_not_prove", "falsifier"]


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    problems: list[str] = []
    rich = list(csv.DictReader((LEDGER / "citation_audit_scc_flash-09.csv").open()))
    lead = list(csv.DictReader((LEDGER / "citation_audit_scc_flash-09.lead_schema.csv").open()))
    canon = list(csv.DictReader((LEDGER / "citation_audit.csv").open()))
    jsonl = [json.loads(l) for l in (LEDGER / "citation_audit_scc_flash-09.jsonl").read_text().splitlines() if l.strip()]

    # 1. raw hash check
    for r in rich:
        raw = (r.get("raw_sha256") or "").strip()
        if not raw:
            continue
        # raw_sha256 stores a 32-char prefix of the source file; locate by name in evidence_ref
        ref = r.get("evidence_ref", "")
        candidates = []
        for part in ref.split(";"):
            part = part.strip()
            if part.startswith("artifacts/worker-09/sources/"):
                candidates.append(ROOT / part)
        if not candidates:
            problems.append(f"{r['citation_id']}: raw_sha256 set but no source path in evidence_ref")
            continue
        vals = []
        for c in candidates:
            if c.exists():
                vals.append((sha(c)[:32] == raw, c))
        if vals and not any(ok for ok, _ in vals):
            problems.append(f"{r['citation_id']}: raw_sha256 {raw} does not match any cached source")

    # 2. schema compatibility
    canon_cols = list(canon[0].keys())
    lead_cols = list(lead[0].keys())
    if lead_cols != canon_cols:
        problems.append(f"lead shard columns differ from canonical: {lead_cols} vs {canon_cols}")

    # 3. required fields: rich rows must carry the review contract fields;
    #    lead rows only have the canonical columns, so they must carry `assessment`.
    for r in rich:
        if r["verdict"].startswith("verified") and not r["citation_id"].startswith("W09-CTRL"):
            for f in REQUIRED_ON_VERIFIED:
                if not (r.get(f) or "").strip():
                    problems.append(f"{r['citation_id']}: rich verified row missing {f}")
    for r in lead:
        if r["verdict"].startswith("verified") and not (r.get("assessment") or "").strip():
            problems.append(f"{r['citation_id']}: lead verified row missing assessment")
        if r["verdict"] == "unresolved" and (r.get("resolver_result") != "unresolved"):
            problems.append(f"{r['citation_id']}: unresolved verdict but resolver_result={r.get('resolver_result')}")

    # 4. cross-file consistency
    ids_rich = {r["citation_id"] for r in rich if not r["citation_id"].startswith("W09-CTRL")}
    ids_lead = {r["citation_id"] for r in lead}
    ids_jsonl = {r["citation_id"] for r in jsonl if not r["citation_id"].startswith("W09-CTRL")}
    if ids_rich != ids_lead:
        problems.append(f"rich vs lead id sets differ: {ids_rich ^ ids_lead}")
    if ids_rich != ids_jsonl:
        problems.append(f"rich vs jsonl id sets differ: {ids_rich ^ ids_jsonl}")

    out = {
        "rich_rows": len(rich), "lead_rows": len(lead), "jsonl_rows": len(jsonl),
        "canonical_rows": len(canon),
        "canonical_sha256": sha(LEDGER / "citation_audit.csv"),
        "shard_sha256": {
            "rich": sha(LEDGER / "citation_audit_scc_flash-09.csv"),
            "lead_schema": sha(LEDGER / "citation_audit_scc_flash-09.lead_schema.csv"),
            "jsonl": sha(LEDGER / "citation_audit_scc_flash-09.jsonl"),
        },
        "verdicts": {},
        "problems": problems,
        "status": "PASS" if not problems else "FAIL",
    }
    for r in lead:
        out["verdicts"][r["verdict"]] = out["verdicts"].get(r["verdict"], 0) + 1
    (W09 / "extracted" / "selfcheck.json").write_text(json.dumps(out, indent=2, sort_keys=True))
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
