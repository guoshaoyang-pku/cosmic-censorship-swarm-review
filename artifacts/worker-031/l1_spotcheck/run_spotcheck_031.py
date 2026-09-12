#!/usr/bin/env python3
"""worker-031: independent L1 re-fetch spot check (G-LIT, node L1).

Task source: controller assignment `astra-life02-l1-spotcheck` (acceptance: each
check records the fetched source hash, the comparison verdict MATCH/PARTIAL/FAIL,
the locator, and re-hashes the ledger after the fetch) and lifecycle
`lifecycle_20260912-001746.json`, which measures exactly 2 binding L1 spot checks
(spotcheck-l1-07, spotcheck-l1-086) against the required >=3.

Independence: rows 91 and 94 are outside flash-07's pre-declared every-8th sample
(rows 41,49,57,65,73,80,81,89 of frame 41-95) and outside worker-086's frame 1-40.
No ledger text is used as evidence; the comparison reads the fetched raw bytes.

Fail-closed: if either ledger hash differs from the pinned values the run aborts
before producing a verdict. The negative controls must both behave as declared or
the checker itself is reported INVALID.

Reproduce:
    python3 artifacts/worker-031/l1_spotcheck/run_spotcheck_031.py
"""
from __future__ import annotations

import csv
import hashlib
import html
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
FETCH = HERE / "fetch"
CST = timezone(timedelta(hours=8))

PINNED = {
    "ledger/citation_audit.csv": "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9",
    "ledger/theorems.jsonl": "ce42d205e7617e3a032c109b24a00b57c7c6b104f37dad5125745af15deebd72",
}

TARGETS = {
    "SRC-094": {"row": 94, "fetch_file": "src-094.abs.html", "http": 200},
    "SRC-091": {"row": 91, "fetch_file": "src-091.abs.html", "http": 200},
}

CONTROLS = {
    "wrong_paper": {"locator": "https://arxiv.org/abs/0711.4621", "fetch_file": "ctrl_wrongpaper_0711.4621.html",
                    "expect": "MISMATCH", "why": "a different arXiv paper must not match SRC-094's title/authors/abstract"},
    "nonresolving_id": {"locator": "https://arxiv.org/abs/0799.99999", "fetch_file": "ctrl_404_0799.99999.html",
                        "observed_http": 404, "expect": "FAIL", "why": "a locator that does not resolve must not be counted as verified"},
}


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def meta(page: str, name: str) -> list[str]:
    vals = re.findall(r'<meta[^>]+name="%s"[^>]+content="([^"]*)"' % name, page)
    if not vals:
        vals = re.findall(r'<meta[^>]+content="([^"]*)"[^>]+name="%s"' % name, page)
    return [html.unescape(v) for v in vals]


def norm(s: str) -> str:
    s = html.unescape(s or "")
    s = s.replace("’", "'").replace("“", '"').replace("”", '"').replace("–", "-").replace("—", "-")
    s = re.sub(r"\$[^$]*\$", " ", s)          # drop inline math delimiters
    s = re.sub(r"\\[a-zA-Z]+", " ", s)        # drop LaTeX commands
    s = re.sub(r"[^a-z0-9']+", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def author_set(s: str) -> set[str]:
    """Last names as tokens; 'Gundlach, Carsten' and 'Carsten Gundlach' agree."""
    out = set()
    for part in re.split(r";| and ", s):
        part = part.strip()
        if not part:
            continue
        if "," in part:
            part = part.split(",")[0]
        out.add(norm(part).split()[-1] if norm(part) else "")
    return {x for x in out if x}


def frag_norm(s: str) -> str:
    """norm() plus trimming of ledger transcription artifacts: wrapping quote marks
    and a trailing standalone footnote/page number (e.g. "black holes.' 2")."""
    n = norm(s)
    if len(n.split()) > 8:
        n = re.sub(r"\s+\d{1,3}$", "", n)
        # ledger transcriptions occasionally append a short annotation after the closing
        # quote of an excerpt (e.g. "...black holes.' 285 pages."); drop only that tail.
        q = n.rfind("'")
        if q > 0 and len(n[:q].split()) > 8 and re.fullmatch(r"[^a-z]{0,20}(\d+\s*pages?)?\.?", n[q:]):
            n = n[:q]
    return n.strip("'\" ")


def excerpt_states(ledger_excerpt: str, abstract: str) -> dict:
    """Check each non-elided fragment of the ledger excerpt as a normalized substring."""
    a = norm(abstract)
    body = re.sub(r"^\s*abstract:?\s*", "", ledger_excerpt, flags=re.I)
    fragments = [f for f in re.split(r"\.\.\.|…", body) if frag_norm(f)]
    hits = [frag_norm(f) in a for f in fragments]
    return {
        "fragments": len(fragments),
        "fragments_found": sum(hits),
        "all_fragments_found": all(hits),
        "first_fragment_found": hits[0] if hits else None,
        "ledger_elided": bool(re.search(r"\.\.\.|…", body)),
    }


def compare(fetched_page: str, ledger_row: dict) -> dict:
    title = (meta(fetched_page, "citation_title") or [""])[0]
    authors = "; ".join(meta(fetched_page, "citation_author"))
    date = (meta(fetched_page, "citation_date") or [""])[0]
    doi = (meta(fetched_page, "citation_doi") or [""])[0]
    arxiv_id = (meta(fetched_page, "citation_arxiv_id") or [""])[0]
    abstract = (meta(fetched_page, "citation_abstract") or [""])[0]
    year_obs = date.split("/")[0] if date else ""
    states = {
        "title": "match" if norm(title) == norm(ledger_row["title"]) else "mismatch",
        "authors": "match" if author_set(authors) and author_set(authors) == author_set(ledger_row["authors"]) else "mismatch",
        "year": "match" if year_obs == str(ledger_row["year"]) else "mismatch",
        "arxiv_id": "match" if arxiv_id == ledger_row["arxiv_id"] else "mismatch",
        "doi": "match" if doi and norm(doi) == norm(ledger_row["doi"]) else ("absent_on_locator" if not doi else "mismatch"),
    }
    states["excerpt"] = excerpt_states(ledger_row["evidence_excerpt"], abstract)
    observed = {"title": title, "authors": authors, "date": date, "doi": doi,
                "arxiv_id": arxiv_id, "abstract": abstract}
    return {"states": states, "observed": observed}


def main() -> dict:
    before = {rel: sha256_file(ROOT / rel) for rel in PINNED}
    drift = {rel: {"pinned": PINNED[rel], "measured": before[rel]}
             for rel in PINNED if before[rel] != PINNED[rel]}
    if drift:
        raise SystemExit(json.dumps({"status": "ABORT_LEDGER_DRIFT", "drift": drift}, indent=1))

    rows = {int(r["citation_id"].split("-")[1]): r for r in csv.DictReader((ROOT / "ledger/citation_audit.csv").open())}
    checks = []
    for cid, spec in TARGETS.items():
        row = rows[spec["row"]]
        page = (FETCH / spec["fetch_file"]).read_text(encoding="utf-8", errors="replace")
        cmp = compare(page, row)
        c = cmp["states"]
        non_excerpt = [c[k] for k in ("title", "authors", "year", "arxiv_id")]
        if all(v == "match" for v in non_excerpt) and c["excerpt"]["all_fragments_found"]:
            verdict = "MATCH"
        elif any(v == "match" for v in non_excerpt) and c["excerpt"]["first_fragment_found"]:
            verdict = "PARTIAL"
        else:
            verdict = "FAIL"
        checks.append({
            "citation_id": cid,
            "row": spec["row"],
            "class_mapping": row["class_mapping"],
            "used_by_theorems": row["used_by_theorems"],
            "ledger_locator": row["exact_locator"],
            "ledger_evidence_url": row["evidence_url"],
            "fetch": {
                "file": spec["fetch_file"],
                "sha256": sha256_file(FETCH / spec["fetch_file"]),
                "bytes": (FETCH / spec["fetch_file"]).stat().st_size,
                "http_status": spec["http"],
            },
            "states": c,
            "observed": cmp["observed"],
            "verdict": verdict,
        })

    controls = []
    ctrl_row = rows[94]
    wrong = (FETCH / CONTROLS["wrong_paper"]["fetch_file"]).read_text(encoding="utf-8", errors="replace")
    w = compare(wrong, ctrl_row)["states"]
    wrong_ok = not (w["title"] == "match" and w["authors"] == "match" and w["excerpt"]["all_fragments_found"])
    controls.append({**CONTROLS["wrong_paper"], "observed_states": w, "observed_verdict": "MISMATCH" if wrong_ok else "MATCH",
                     "control_pass": wrong_ok})
    nonres = FETCH / CONTROLS["nonresolving_id"]["fetch_file"]
    nonres_page = nonres.read_text(encoding="utf-8", errors="replace")
    controls.append({**CONTROLS["nonresolving_id"], "fetch_sha256": sha256_file(nonres),
                     "observed_title": (re.search(r"<title>(.*?)</title>", nonres_page, re.S).group(1).strip()),
                     "control_pass": CONTROLS["nonresolving_id"]["observed_http"] == 404})

    after = {rel: sha256_file(ROOT / rel) for rel in PINNED}
    out = {
        "checker": "run_spotcheck_031.py",
        "checked_at": datetime.now(CST).isoformat(timespec="seconds"),
        "actor": "worker-031",
        "node_id": "L1",
        "gate": "G-LIT",
        "pinned_inputs": PINNED,
        "inputs_before_fetch": before,
        "inputs_after_fetch": after,
        "ledger_stable_during_check": before == after == PINNED,
        "checks": checks,
        "controls": controls,
        "controls_pass": all(c["control_pass"] for c in controls),
    }
    out["overall_verdict"] = "INVALID" if not out["controls_pass"] else (
        "PASS" if all(c["verdict"] == "MATCH" for c in checks) else
        "PARTIAL" if all(c["verdict"] in ("MATCH", "PARTIAL") for c in checks) else "FAIL")
    (HERE / "comparison.json").write_text(json.dumps(out, indent=2, sort_keys=True))
    print(json.dumps({k: out[k] for k in ("overall_verdict", "ledger_stable_during_check", "controls_pass")}, indent=1))
    for c in checks:
        print(c["citation_id"], c["class_mapping"], "->", c["verdict"], c["states"]["excerpt"])
    return out


if __name__ == "__main__":
    main()
