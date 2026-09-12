#!/usr/bin/env python3
"""Negative control for the worker-006 L1 spot check.

Fetch a deliberately WRONG locator (a different work) and push it through the same
comparison functions. If the comparator still reports MATCH the spot check is
format-dominated and the whole measurement is invalid; a FAIL here is the control.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPORT = HERE / "spotcheck-006.json"
CST = timezone(timedelta(hours=8))
spec = importlib.util.spec_from_file_location("rs", HERE / "run_spotcheck_006.py")
rs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rs)

# control pair: apply SRC-047's ledger claim to SRC-085's paper (different work)
cid, wrong_aid = "SRC-047", "2201.12295"


def main() -> int:
    rep = json.loads(REPORT.read_text())
    row = next(r for r in rep["results"] if r["citation_id"] == cid)
    url = f"https://arxiv.org/abs/{wrong_aid}"
    dest = HERE / "raw" / f"control_wrong_{cid}_{wrong_aid}.html"
    proc = subprocess.run(["curl", "-sSL", "-m", "45", "-A",
                           "ai4math-swarm-spotcheck/1.0 (research verification)",
                           "-o", str(dest), "-w", "%{http_code} %{size_download}", url],
                          capture_output=True, text=True)
    http = (proc.stdout or "").split()[0]
    page = dest.read_text(errors="replace")
    parsed = rs.parse_abs_page(page) if http == "200" else {}
    title_match = rs.norm_text(parsed.get("title", "")) == rs.norm_text(row["ledger_title"])
    author_match = rs.norm_text(rs.first_author_surname(row["ledger_authors"])) in rs.norm_text(parsed.get("authors", ""))
    core = rs.excerpt_core(row["ledger_excerpt"])
    lt, ft = rs.tokens(core), rs.tokens(parsed.get("abstract", ""))
    lead = lt[:min(12, len(lt))]
    contiguous = any(ft[i:i + len(lead)] == lead for i in range(0, max(0, len(ft) - len(lead) + 1)))
    present = sum(1 for t in lt if t in set(ft)) / max(1, len(lt))
    grounding = "GROUNDED" if contiguous else ("PARTIAL" if present >= 0.8 else "NOT_GROUNDED")
    observed = "MATCH" if (title_match and author_match and grounding == "GROUNDED") else (
        "FAIL" if not author_match else "PARTIAL")
    control = {
        "kind": "negative-control-wrong-locator",
        "claim_row": cid, "claim_title": row["ledger_title"],
        "wrong_locator": url, "wrong_arxiv_id": wrong_aid,
        "wrong_fetched_title": parsed.get("title"),
        "http_status": http, "fetched_sha256": rs.sha_bytes(dest.read_bytes()),
        "title_match": title_match, "first_author_match": author_match,
        "excerpt_grounding": grounding,
        "expected_verdict": "FAIL", "observed_verdict": observed,
        "control_passed": observed != "MATCH",
        "checked_at": datetime.now(CST).isoformat(timespec="seconds"),
    }
    rep["negative_control"] = control
    REPORT.write_text(json.dumps(rep, indent=2) + "\n")
    print(json.dumps(control, indent=1))
    return 0 if control["control_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
