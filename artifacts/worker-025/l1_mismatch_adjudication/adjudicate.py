#!/usr/bin/env python3
"""Phase 2: DOI-side adjudication of the three MISMATCH verdicts from L1 spot check #4.

Bounded task W025-L1-MISMATCH-ADJ-01 (actor worker-025, node L1, gate G-LIT).
Reads freeze/frozen_inputs.json + freeze/frozen_rows.json (phase 1, no network there),
re-verifies the frozen ledger hash, then performs live registry fetches and writes:

    raw/<id>_crossref.json          raw Crossref responses (bytes hashed)
    raw/<id>_arxiv.html             raw arXiv abs pages where the row has an arXiv id
    report.json                     per-row evidence + verdict + falsifier
    controls.json                   positive / mutated-DOI / synthetic-title controls
    raw/fetch_manifest.json         url, http status, bytes, sha256, seconds per fetch
    run.log                         stdout transcript

Never writes the ledger; makes no gate or node-status claim. Network fetch failures are
recorded, not retried silently.
"""
from __future__ import annotations

import hashlib
import html
import json
import os
import re
import time
import unicodedata
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

CST = timezone(timedelta(hours=8))
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
LEDGER = os.path.join(ROOT, "ledger", "citation_audit.csv")
FREEZE = os.path.join(HERE, "freeze", "frozen_inputs.json")
FROZEN_ROWS = os.path.join(HERE, "freeze", "frozen_rows.json")
RAW_DIR = os.path.join(HERE, "raw")
UA = "ai4math-swarm-worker-025/1.0 (L1 citation adjudication; mailto:worker-025@invalid)"
TARGETS = ["SRC-004", "SRC-025", "SRC-033"]
CONTROLS = ["SRC-001"]


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


GREEK = {
    "α": "alpha", "β": "beta", "γ": "gamma", "δ": "delta", "ε": "epsilon", "ζ": "zeta",
    "η": "eta", "θ": "theta", "ι": "iota", "κ": "kappa", "λ": "lambda", "μ": "mu",
    "ν": "nu", "ξ": "xi", "ο": "omicron", "π": "pi", "ρ": "rho", "σ": "sigma",
    "ς": "sigma", "τ": "tau", "υ": "upsilon", "φ": "phi", "χ": "chi", "ψ": "psi",
    "ω": "omega", "Α": "alpha", "Β": "beta", "Γ": "gamma", "Δ": "delta", "Ε": "epsilon",
    "Ζ": "zeta", "Η": "eta", "Θ": "theta", "Ι": "iota", "Κ": "kappa", "Λ": "lambda",
    "Μ": "mu", "Ν": "nu", "Ξ": "xi", "Ο": "omicron", "Π": "pi", "Ρ": "rho",
    "Σ": "sigma", "Τ": "tau", "Υ": "upsilon", "Φ": "phi", "Χ": "chi", "Ψ": "psi",
    "Ω": "omega", "∂": "partial", "∞": "infinity", "≤": "le", "≥": "ge", "≠": "ne",
}


def norm(s: str | None) -> str:
    if not s:
        return ""
    s = html.unescape(s)  # registry titles arrive HTML-escaped (e.g. "&gt;")
    s = "".join(GREEK.get(c, c) for c in s)  # Greek letters do not NFKD-decompose to Latin
    s = unicodedata.normalize("NFKD", s)
    s = s.replace("$", " ")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9]+", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def ledger_authors(s: str) -> list[str]:
    out = []
    for part in re.split(r"[;,]", s or ""):
        part = norm(part)
        if not part:
            continue
        out.append(part.split()[-1])
    return out


def fetch(url: str, label: str) -> dict:
    t0 = time.time()
    rec = {"label": label, "url": url, "fetched_at": now(), "http_status": None,
           "bytes": 0, "seconds": None, "sha256": None, "ok": False, "error": None}
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read()
            rec["http_status"] = r.status
        rec.update(bytes=len(body), sha256=sha256_bytes(body), ok=True)
        ext = "json" if "crossref" in url else "html"
        name = re.sub(r"[^A-Za-z0-9._-]+", "_", label) + "." + ext
        path = os.path.join(RAW_DIR, name)
        with open(path, "wb") as f:
            f.write(body)
        rec["raw_path"] = os.path.relpath(path, ROOT)
    except urllib.error.HTTPError as e:
        rec["http_status"] = e.code
        rec["error"] = f"HTTPError {e.code}"
    except Exception as e:  # noqa: BLE001 - fetch failures are recorded evidence
        rec["error"] = f"{type(e).__name__}: {e}"
    rec["seconds"] = round(time.time() - t0, 2)
    return rec


def crossref_meta(body: bytes) -> dict:
    msg = json.loads(body.decode("utf-8"))["message"]
    families = [a.get("family", "") for a in msg.get("author", [])]
    issued = None
    for k in ("published-print", "published", "issued"):
        parts = (msg.get(k) or {}).get("date-parts") or []
        if parts and parts[0] and parts[0][0]:
            issued = parts[0][0] if k != "issued" else issued or parts[0][0]
    return {
        "doi": msg.get("DOI"),
        "title": (msg.get("title") or [""])[0],
        "container_title": (msg.get("container-title") or [""])[0],
        "authors": families,
        "issued_year": (msg.get("issued", {}).get("date-parts") or [[None]])[0][0],
        "published_print_year": ((msg.get("published-print") or {}).get("date-parts") or [[None]])[0][0],
        "volume": msg.get("volume"),
        "page": msg.get("page"),
        "type": msg.get("type"),
    }


def arxiv_meta(body: bytes) -> dict:
    text = body.decode("utf-8", "replace")
    def meta(name):
        m = re.search(r'<meta\s+name="%s"\s+content="([^"]*)"' % re.escape(name), text)
        return m.group(1) if m else None
    return {
        "citation_date": meta("citation_date"),
        "citation_title": meta("citation_title"),
        "citation_author": re.findall(r'<meta\s+name="citation_author"\s+content="([^"]*)"', text),
    }


def compare(ledger: dict, fetched: dict) -> dict:
    lt, ft = norm(ledger["title"]), norm(fetched["title"])
    if lt and ft and lt == ft:
        title_state = "exact"
    elif lt and ft and (lt.startswith(ft) or ft.startswith(lt)):
        title_state = "prefix"
    else:
        title_state = "mismatch"
    la = set(ledger_authors(ledger["authors"]))
    fa = {norm(a).split()[-1] for a in fetched["authors"] if norm(a)}
    overlap = bool(la & fa)
    try:
        ly = int(str(ledger["year"]).strip()[:4])
    except (ValueError, TypeError):
        ly = None
    fy = fetched.get("issued_year") or fetched.get("published_print_year")
    if ly is None or fy is None:
        year_state = "unknown"
    elif ly == fy:
        year_state = "exact"
    elif abs(ly - fy) == 1:
        year_state = "within1"
    else:
        year_state = "mismatch"
    venue_tokens = [norm(t) for t in [fetched.get("container_title"), fetched.get("volume"), fetched.get("page")] if t]
    lv = norm(ledger["venue"])
    venue_tokens = [t for t in venue_tokens if t]
    venue_token_present = all(t in lv for t in venue_tokens) if venue_tokens else False
    doi_match = (norm(ledger["doi"]) == norm(fetched.get("doi"))) if fetched.get("doi") else None
    if title_state in ("exact", "prefix") and overlap and year_state in ("exact", "within1") and venue_token_present and doi_match:
        verdict = "DOI_MATCH"
    elif title_state in ("exact", "prefix") and overlap:
        verdict = "DOI_PARTIAL"
    else:
        verdict = "DOI_MISMATCH"
    return {
        "title_state": title_state,
        "author_overlap": overlap,
        "ledger_author_families": sorted(la),
        "fetched_author_families": sorted(fa),
        "year_state": year_state,
        "ledger_year": ly,
        "fetched_year": fy,
        "venue_token_present": venue_token_present,
        "doi_identity_match": doi_match,
        "verdict": verdict,
    }


def main() -> int:
    os.makedirs(RAW_DIR, exist_ok=True)
    frozen = json.load(open(FREEZE, encoding="utf-8"))
    rows = json.load(open(FROZEN_ROWS, encoding="utf-8"))

    ledger_now = sha256_file(LEDGER)
    frozen_sha = frozen["inputs"]["ledger/citation_audit.csv"]["sha256"]
    pinned = ledger_now == frozen_sha
    print(f"[pin] frozen ledger sha256 = {frozen_sha}")
    print(f"[pin] ledger sha256 at adjudication start = {ledger_now}  pinned={pinned}")
    if not pinned:
        print("[fail-closed] ledger drifted after pre-registration; aborting before any fetch")
        json.dump({"schema": "w025-l1-mismatch-adjudication/v1", "task_id": frozen["task_id"],
                   "status": "ABORTED_LEDGER_DRIFT", "frozen_sha256": frozen_sha,
                   "observed_sha256": ledger_now, "created_at": now()},
                  open(os.path.join(HERE, "report.json"), "w", encoding="utf-8"), indent=1)
        return 3

    spot4 = json.load(open(os.path.join(ROOT, "artifacts", "worker-086", "l1_spotcheck",
                                        "spotcheck-l1-086.json"), encoding="utf-8"))
    spot4_claims = {r["citation_id"]: {"verdict": r["verdict"],
                                       "comparison": r.get("comparison"),
                                       "fetch_url": r.get("fetch", {}).get("url"),
                                       "fetched_years": (r.get("fetched") or {}).get("years"),
                                       "fetched_submitted": (r.get("fetched") or {}).get("submitted")}
                    for r in spot4.get("results", [])}

    manifest, report_rows, controls = [], {}, {}

    for cid in TARGETS + CONTROLS:
        row = rows[cid]["fields"]
        doi = (row.get("doi") or "").strip()
        rec = fetch(f"https://api.crossref.org/works/{doi}", f"{cid}_crossref")
        manifest.append(rec)
        entry = {"citation_id": cid, "data_row_1based": rows[cid]["data_row_1based"],
                 "raw_line_sha256": rows[cid]["raw_line_sha256"],
                 "class_mapping": row.get("class_mapping"),
                 "used_by_theorems": row.get("used_by_theorems"),
                 "declared_doi": doi,
                 "ledger": {k: row.get(k) for k in ("title", "authors", "year", "venue", "doi",
                                                    "arxiv_id", "exact_locator", "evidence_url",
                                                    "verification_status", "status")},
                 "spot4_claim": spot4_claims.get(cid),
                 "doi_fetch": rec}
        if not rec["ok"]:
            entry["verdict"] = "DOI_UNRESOLVED"
            entry["evidence"] = {"fetched_sha256": rec["sha256"], "registry": None}
        else:
            meta = crossref_meta(open(os.path.join(ROOT, rec["raw_path"]), "rb").read())
            cmp_ = compare(row, meta)
            entry["registry"] = meta
            entry["comparison"] = cmp_
            entry["verdict"] = cmp_["verdict"]
            entry["evidence"] = {"fetched_sha256": rec["sha256"], "registry": meta}
        # arXiv-side reproduction (explains spot check #4's fetched year when it differs)
        if row.get("arxiv_id"):
            arc = fetch(f"https://arxiv.org/abs/{row['arxiv_id']}", f"{cid}_arxiv")
            manifest.append(arc)
            if arc["ok"]:
                am = arxiv_meta(open(os.path.join(ROOT, arc["raw_path"]), "rb").read())
                entry["arxiv_fetch"] = arc
                entry["arxiv_meta"] = am
        report_rows[cid] = entry

    # CTRL-NEG-MUTATED-DOI: same row, declared DOI corrupted at the final digit
    base_doi = rows["SRC-004"]["fields"]["doi"]
    mut_doi = base_doi[:-1] + ("2" if base_doi[-1] != "2" else "3")
    mrec = fetch(f"https://api.crossref.org/works/{mut_doi}", "CTRL_mutated_doi_crossref")
    manifest.append(mrec)
    mutated = {"label": "CTRL-NEG-MUTATED-DOI", "base_doi": base_doi, "mutated_doi": mut_doi,
               "fetch": mrec, "expected": "not DOI_MATCH"}
    if mrec["ok"]:
        meta = crossref_meta(open(os.path.join(ROOT, mrec["raw_path"]), "rb").read())
        cmpres = compare(rows["SRC-004"]["fields"], meta)
        mutated["comparison"] = cmpres
        mutated["verdict"] = cmpres["verdict"]
        mutated["control_passed"] = cmpres["verdict"] != "DOI_MATCH"
    else:
        mutated["verdict"] = "DOI_UNRESOLVED"
        mutated["control_passed"] = True  # a non-resolving DOI is rejected, which is the point
    controls["CTRL-NEG-MUTATED-DOI"] = mutated

    # CTRL-NEG-SYNTHETIC-TITLE: offline discrimination test on the real SRC-004 registry record
    if report_rows["SRC-004"].get("registry"):
        synth = dict(rows["SRC-004"]["fields"])
        synth["title"] = "Zeta functions of nothing"
        cmpres = compare(synth, report_rows["SRC-004"]["registry"])
        controls["CTRL-NEG-SYNTHETIC-TITLE"] = {
            "label": "CTRL-NEG-SYNTHETIC-TITLE", "mutated_field": "title",
            "mutated_to": synth["title"], "comparison": cmpres, "verdict": cmpres["verdict"],
            "expected": "DOI_MISMATCH", "control_passed": cmpres["verdict"] == "DOI_MISMATCH",
        }

    # CTRL-POS: the positive control row must itself classify DOI_MATCH
    pos = report_rows["SRC-001"]
    controls["CTRL-POS-SRC-001"] = {
        "label": "CTRL-POS-SRC-001", "verdict": pos["verdict"], "expected": "DOI_MATCH",
        "control_passed": pos["verdict"] == "DOI_MATCH",
    }

    ledger_after = sha256_file(LEDGER)
    stable = ledger_after == frozen_sha
    claim_by_id = {cid: spot4_claims.get(cid, {}).get("verdict") for cid in TARGETS}
    adjudication = {}
    for cid in TARGETS:
        v = report_rows[cid]["verdict"]
        if v == "DOI_MATCH":
            adjudication[cid] = "SPOT4_MISMATCH_REFUTED (journal-of-record metadata matches the ledger; spot check #4 compared an arXiv preprint against a journal citation)"
        elif v == "DOI_PARTIAL":
            adjudication[cid] = "SPOT4_MISMATCH_PARTIALLY_REFUTED (work identity matches; residual convention/locator defect)"
        elif v == "DOI_UNRESOLVED":
            adjudication[cid] = "SPOT4_CLAIM_NOT_ADJUDICABLE (declared DOI did not resolve: locator defect, not a false positive)"
        else:
            adjudication[cid] = "SPOT4_MISMATCH_CONFIRMED (declared DOI resolves to a different work identity)"

    all_controls_pass = all(c.get("control_passed") for c in controls.values())
    report = {
        "schema": "w025-l1-mismatch-adjudication/v1",
        "task_id": frozen["task_id"],
        "actor": "worker-025",
        "node_id": "L1",
        "gate": "G-LIT",
        "class_ids": frozen["class_ids"],
        "created_at": now(),
        "status": "COMPLETE" if stable and all_controls_pass else "COMPLETE_WITH_CAVEAT",
        "question": "Are the three MISMATCH hard failures of L1 spot check #4 genuine citation defects or arXiv-vs-journal comparison artifacts?",
        "answer": adjudication,
        "hypothesis_supported": {cid: ("H0_comparison_artifact" if report_rows[cid]["verdict"] in ("DOI_MATCH", "DOI_PARTIAL") else
                                       ("H1_genuine_defect" if report_rows[cid]["verdict"] == "DOI_MISMATCH" else "UNRESOLVED"))
                                 for cid in TARGETS},
        "falsifier": frozen["falsifier"],
        "falsifier_status": "NOT_TRIGGERED" if all_controls_pass and stable else "TRIGGERED",
        "comparator_revision": {
            "revision": 2,
            "first_pass_artifact": "report.firstpass.json",
            "change": "norm(): added html.unescape + Greek-letter transliteration before NFKD",
            "reason": (
                "First pass classified SRC-033 DOI_MISMATCH on title_state=mismatch; the only "
                "difference was ledger 'Lambda > 0' vs registry 'Λ &gt; 0'. That is a normalizer "
                "false positive of exactly the kind under adjudication, so the comparator was "
                "corrected and the first pass is kept on disk as evidence of the defect."
            ),
            "first_pass_verdicts": {"SRC-004": "DOI_MATCH", "SRC-025": "DOI_MATCH",
                                    "SRC-033": "DOI_MISMATCH", "SRC-001": "DOI_MATCH"},
        },
        "inputs": {
            "ledger/citation_audit.csv": {"sha256_frozen": frozen_sha, "sha256_after_fetches": ledger_after,
                                          "stable_during_window": stable},
            "artifacts/worker-086/l1_spotcheck/spotcheck-l1-086.json": frozen["inputs"]["artifacts/worker-086/l1_spotcheck/spotcheck-l1-086.json"],
            "freeze/frozen_inputs.json": {"sha256": sha256_file(FREEZE)},
            "freeze/frozen_rows.json": {"sha256": sha256_file(FROZEN_ROWS)},
        },
        "spot4_claims_under_adjudication": claim_by_id,
        "results": report_rows,
        "controls": controls,
        "all_controls_passed": all_controls_pass,
        "limitations": [
            "Crossref registry metadata is the journal of record; it does not verify that the cited theorem's statement matches the source text.",
            "Adjudicates metadata identity only, not theorem-to-class scope binding (that is a literature-lead verdict).",
            "One row (SRC-004) is load-bearing for five theorem rows; scope binding remains outstanding regardless of this metadata verdict.",
        ],
        "authority": "no gate verdict, no node status, no ledger write; artifact-level evidence for the literature lead and audit lead.",
        "fetch_manifest": manifest,
        "run_seconds": None,
    }

    with open(os.path.join(HERE, "controls.json"), "w", encoding="utf-8") as f:
        json.dump(controls, f, indent=1, sort_keys=True)
        f.write("\n")
    with open(os.path.join(HERE, "report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1, sort_keys=True)
        f.write("\n")
    with open(os.path.join(RAW_DIR, "fetch_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1, sort_keys=True)
        f.write("\n")

    print(json.dumps({
        "status": report["status"],
        "verdicts": {cid: report_rows[cid]["verdict"] for cid in TARGETS + CONTROLS},
        "adjudication": adjudication,
        "controls_passed": {k: v.get("control_passed") for k, v in controls.items()},
        "ledger_stable": stable,
    }, indent=1))
    return 0 if (stable and all_controls_pass) else 1


if __name__ == "__main__":
    t0 = time.time()
    rc = main()
    print(f"[done] rc={rc} wall={time.time()-t0:.1f}s")
    raise SystemExit(rc)
