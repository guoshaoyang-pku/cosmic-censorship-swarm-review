#!/usr/bin/env python3
"""W074-L1-L11-SCOPE-VERIFY-01 — independent non-author verification of the L11 L1
locator-scope machine record and of the ruling basis its gate-owner adjudication cites.

Target of verification (all read-only):
  * artifacts/literature/reviews/L1-locator-scope-L11-machine.json (astra-lead-literature)
  * reviews/L1-gate-adjudication-lead-literature-L11.json (astra-lead-literature, gate owner)
  * the rule it invokes: controller ruling REC-6, cited by the adjudication as
    runtime/state/controller_verification/astra-lifecycle-07-decisions.json#REC-6

What this worker does NOT do:
  * it does not run the lead's scanner (that script rewrites the lead's machine-record path;
    freezing discipline forbids it). The classification below is an independent
    reimplementation from the same declared predicate semantics.
  * it writes nothing outside artifacts/worker-074/l11_scope_verify/ and does not touch the
    ledger, the map, the lead's artifacts, or any canonical path.

Falsifier:
  FALSIFIED IF any pinned input fails to re-hash to its recorded sha256, or a re-run of this
  instrument on the same tree state yields a different per-row classification, count table,
  finding set, or exit code; or if the 4-row worker-025 residual is shown to involve
  inspirehep.net/api/literature/<id> values in exact_locator; or if REC-6 is shown to be
  present in astra-lifecycle-07-decisions.json.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[3]
OUTDIR = ROOT / "artifacts" / "worker-074" / "l11_scope_verify"

PATHS = {
    "ledger/citation_audit.csv": ROOT / "ledger" / "citation_audit.csv",
    "artifacts/literature/reviews/L1-locator-scope-L11-machine.json": ROOT / "artifacts/literature/reviews/L1-locator-scope-L11-machine.json",
    "reviews/L1-gate-adjudication-lead-literature-L11.json": ROOT / "reviews/L1-gate-adjudication-lead-literature-L11.json",
    "artifacts/literature/reviews/l11_l1_locator_scope_audit.py": ROOT / "artifacts/literature/reviews/l11_l1_locator_scope_audit.py",
    "evaluation_rubric.yaml": ROOT / "evaluation_rubric.yaml",
    "runtime/state/controller_verification/astra-lifecycle-04-decisions.json": ROOT / "runtime/state/controller_verification/astra-lifecycle-04-decisions.json",
    "runtime/state/controller_verification/astra-lifecycle-07-decisions.json": ROOT / "runtime/state/controller_verification/astra-lifecycle-07-decisions.json",
    "artifacts/worker-025/l1_locator_adj/report.json": ROOT / "artifacts/worker-025/l1_locator_adj/report.json",
}

PINS = {
    "ledger/citation_audit.csv": "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9",
    "artifacts/literature/reviews/L1-locator-scope-L11-machine.json": "2a9f73b223ec257171ecbd85b735aea933f0a1b7ccdf0c63b37953a7fb57abea",
    "reviews/L1-gate-adjudication-lead-literature-L11.json": "6d8e86e360c9f3fd6a2acce1bb9d30c0a2c4a3b19d1718882d55c00f1b8b5afd",
    "artifacts/literature/reviews/l11_l1_locator_scope_audit.py": "1f70d279255c4e651523af35cde672deff7e4ca5a6080f9e49c44edfe60d1123",
    "evaluation_rubric.yaml": "d748a9e3574ebe0c34c22b608ba0bf018d525a644ebff815371c6dcfca055885",
    "runtime/state/controller_verification/astra-lifecycle-04-decisions.json": "15bc7d645dccd9c2352dcc34603b00777b2212fb7080bfc9ea72a26b420604a3",
    "runtime/state/controller_verification/astra-lifecycle-07-decisions.json": "fc1d6fb4da6f9998d5e02f2314a24fc643eef011bb2ed434a092d4f7171d0ba8",
    "artifacts/worker-025/l1_locator_adj/report.json": "26f0071c558e99c573d1f1cbfaea4a27f996555f50963e6ec478c7dc09fc2c5d",
}

RECORD_CLASSES = {"DOI", "RECORD_PAGE", "RECORD_ENDPOINT"}
# Per the machine record's declared predicate, ABSENT is tracked as its own bucket, not as
# "non-record"; non-record is the three id-less/query/truncated classes.
NON_RECORD_CLASSES = {"TRUNCATED", "DISCOVERY_QUERY", "METADATA_ENDPOINT"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def classify(value: str) -> str:
    """Independent reimplementation of the declared record-locator predicate.

    Declared semantics (from the L11 machine record's `predicate` block): a locator is
    record-shaped if it is a DOI, an arXiv abs/pdf page, a publisher/journal record page, or
    an API record endpoint carrying a record id.  TRUNCATED (literal '...'), DISCOVERY_QUERY
    (api/query, ?q=, /search) and id-less METADATA_ENDPOINT are not record locators.
    """
    v = (value or "").strip()
    if not v:
        return "ABSENT"
    if "..." in v:
        return "TRUNCATED"
    if re.search(r"[?&]q=|search_query=|/search|\bquery=", v, re.I):
        return "DISCOVERY_QUERY"
    parsed = urlparse(v)
    host = parsed.netloc.lower()
    path = parsed.path.lower()
    # API record endpoints that carry a record id.
    if "inspirehep.net" in host and re.match(r"/api/literature/\d+/?$", path):
        return "RECORD_ENDPOINT"
    if "api.crossref.org" in host and path.startswith("/works/"):
        return "RECORD_ENDPOINT"
    if "api.openalex.org" in host and path.startswith("/works/"):
        return "RECORD_ENDPOINT"
    if "api.semanticscholar.org" in host and path.startswith(("/paper/", "/graph/")):
        return "RECORD_ENDPOINT"
    # arXiv record pages.
    if "arxiv.org" in host and re.search(r"/(abs|pdf)/", path):
        return "RECORD_PAGE"
    # DOI resolvers and bare DOIs.
    if host.endswith("doi.org") or re.match(r"^10\.\d{4,9}/", v):
        return "DOI"
    # Id-less metadata APIs.
    if re.search(r"(^|\.)api\.|/api/|export\.arxiv\.org", host + path):
        return "METADATA_ENDPOINT"
    # Publisher/journal record page or other document page.
    return "RECORD_PAGE"


def main() -> int:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    (OUTDIR / "raw").mkdir(parents=True, exist_ok=True)

    checks: list[dict] = []

    def check(cid: str, ok: bool, detail: str, binding: bool = True) -> None:
        checks.append({"id": cid, "status": "PASS" if ok else "FAIL", "binding": binding, "detail": detail})

    # --- Pins -------------------------------------------------------------------------------
    t0 = {rel: sha256(p) for rel, p in PATHS.items()}
    for rel, pin in PINS.items():
        check(f"PIN::{rel}", t0[rel] == pin, f"measured {t0[rel][:16]} declared {pin[:16]}")

    ledger_rows = list(csv.DictReader(PATHS["ledger/citation_audit.csv"].open(newline="", encoding="utf-8")))
    machine = json.loads(PATHS["artifacts/literature/reviews/L1-locator-scope-L11-machine.json"].read_text())
    adj = json.loads(PATHS["reviews/L1-gate-adjudication-lead-literature-L11.json"].read_text())
    w025 = json.loads(PATHS["artifacts/worker-025/l1_locator_adj/report.json"].read_text())
    dec04 = json.loads(PATHS["runtime/state/controller_verification/astra-lifecycle-04-decisions.json"].read_text())
    dec07 = json.loads(PATHS["runtime/state/controller_verification/astra-lifecycle-07-decisions.json"].read_text())
    rubric_text = PATHS["evaluation_rubric.yaml"].read_text()

    # --- Machine record self-consistency ----------------------------------------------------
    check("MACHINE::pins_match_all_true", all(machine.get("pins_match", {}).values()),
          json.dumps(machine.get("pins_match")))
    check("MACHINE::declared_pins_equal_measured", machine.get("pins_declared") == machine.get("pins_measured"),
          "pins_declared == pins_measured")

    # --- Independent per-row classification -------------------------------------------------
    l11_rows = {r["citation_id"]: r for r in machine["row_detail"]}
    ex_counts: Counter = Counter()
    ev_counts: Counter = Counter()
    diffs: list[dict] = []
    absent_ev: list[str] = []
    no_anchor: list[str] = []
    alt_anchor_for_absent: dict = {}
    for row in ledger_rows:
        cid = row["citation_id"]
        ex = classify(row.get("exact_locator", ""))
        ev = classify(row.get("evidence_url", ""))
        alts = {k: classify(row.get(k, "")) for k in ("url", "doi", "arxiv_id")}
        alt_records = {k: v for k, v in alts.items() if v in RECORD_CLASSES}
        ex_counts[ex] += 1
        ev_counts[ev] += 1
        if ev == "ABSENT":
            absent_ev.append(cid)
            alt_anchor_for_absent[cid] = alt_records
        if ev not in RECORD_CLASSES and not alt_records:
            no_anchor.append(cid)
        target = l11_rows.get(cid)
        if target is None:
            diffs.append({"citation_id": cid, "axis": "missing_in_machine_record"})
            continue
        if ex != target.get("exact_locator_class"):
            diffs.append({"citation_id": cid, "axis": "exact_locator", "ours": ex, "theirs": target.get("exact_locator_class")})
        if ev != target.get("evidence_url_class"):
            diffs.append({"citation_id": cid, "axis": "evidence_url", "ours": ev, "theirs": target.get("evidence_url_class")})
    check("ROWS::count_97", len(ledger_rows) == 97, f"rows={len(ledger_rows)}")
    check("ROWS::exact_locator_class_equality", not [d for d in diffs if d["axis"] == "exact_locator"],
          f"{len([d for d in diffs if d['axis'] == 'exact_locator'])} diffs")
    check("ROWS::evidence_url_class_equality", not [d for d in diffs if d["axis"] == "evidence_url"],
          f"{len([d for d in diffs if d['axis'] == 'evidence_url'])} diffs")

    # --- Count table equality ----------------------------------------------------------------
    declared_counts = machine["counts"]
    measured_counts = {
        "exact_locator_record": sum(v for k, v in ex_counts.items() if k in RECORD_CLASSES),
        "exact_locator_non_record": sum(v for k, v in ex_counts.items() if k in NON_RECORD_CLASSES),
        "evidence_url_record": sum(v for k, v in ev_counts.items() if k in RECORD_CLASSES),
        "evidence_url_absent": ev_counts.get("ABSENT", 0),
        "evidence_url_non_record": sum(v for k, v in ev_counts.items() if k in NON_RECORD_CLASSES),
        "any_record_anchor": 97 - len(no_anchor),
        "rows_with_no_record_anchor": len(no_anchor),
    }
    count_ok = all(measured_counts[k] == declared_counts[k] for k in measured_counts)
    check("COUNTS::machine_record_equality", count_ok, json.dumps({"measured": measured_counts, "declared": {k: declared_counts[k] for k in measured_counts}}))
    check("COUNTS::exact_locator_breakdown",
          dict(ex_counts) == {k: machine["predicate"]["exact_locator_classes"][k] for k in ex_counts},
          json.dumps(dict(ex_counts), sort_keys=True))
    check("COUNTS::evidence_url_breakdown",
          dict(ev_counts) == {k: machine["predicate"]["evidence_url_classes"][k] for k in ev_counts},
          json.dumps(dict(ev_counts), sort_keys=True))

    # --- The two absent-evidence_url rows ----------------------------------------------------
    check("ABSENT_EVIDENCE_URL::exactly_SRC-094_SRC-095", sorted(absent_ev) == ["SRC-094", "SRC-095"], str(sorted(absent_ev)))
    check("ABSENT_EVIDENCE_URL::both_have_alt_record_anchor",
          all(alt_anchor_for_absent.get(c) for c in ("SRC-094", "SRC-095")),
          json.dumps(alt_anchor_for_absent))
    check("NO_ANCHOR::zero_rows", not no_anchor, str(no_anchor))

    # --- REC-6 provenance (the ruling basis the adjudication cites) ---------------------------
    def all_rulings(doc: dict) -> list:
        out = []
        for key in ("rulings", "recommendations", "decisions"):
            v = doc.get(key)
            if isinstance(v, list):
                out.extend([r for r in v if isinstance(r, dict)])
            elif isinstance(v, dict):
                out.extend([r for r in v.values() if isinstance(r, dict)])
        return out

    def ruling_ids(doc: dict) -> list:
        return [r.get("id") for r in all_rulings(doc)]

    rec6_in_07 = "REC-6" in ruling_ids(dec07)
    rec6_in_04 = "REC-6" in ruling_ids(dec04)
    rec6_04 = next((r for r in all_rulings(dec04) if r.get("id") == "REC-6"), {})
    rec35_in_07 = "REC-35" in ruling_ids(dec07)
    rec6_04_dec = " ".join(str(rec6_04.get(k, "")) for k in ("decision", "ruling"))
    cited = "runtime/state/controller_verification/astra-lifecycle-07-decisions.json#REC-6"
    check("REC6::cited_ref_resolves", rec6_in_07, f"cited {cited}; REC ids in cited file: {ruling_ids(dec07)}")
    check("REC6::text_present_at_correct_path", rec6_in_04 and "evidence_url is the locator column" in rec6_04_dec,
          f"astra-lifecycle-04-decisions.json REC ids: {ruling_ids(dec04)}; decision={rec6_04_dec[:200]}")
    check("REC35::cited_ref_resolves", rec35_in_07, f"REC ids in -07: {ruling_ids(dec07)}")

    # --- Residual 4-row reconciliation vs worker-025 ------------------------------------------
    w025_class = {r["citation_id"]: r["exact_locator_class"] for r in w025["rows"]}
    w025_rows = {r["citation_id"]: r for r in w025["rows"]}
    residual = [
        {"citation_id": cid, "worker_025": w025_class[cid], "l11": l11_rows[cid]["exact_locator_class"],
         "value": (w025_rows[cid].get("exact_locator") or "")[:120]}
        for cid in sorted(w025_class)
        if l11_rows[cid]["exact_locator_class"] in RECORD_CLASSES and w025_class[cid] != "DIRECT"
    ]
    # the machine record row_detail does not carry raw values; measure from the ledger instead
    ledger_by_id = {r["citation_id"]: r for r in ledger_rows}
    inspire_exact_values = [
        cid for cid, r in ledger_by_id.items()
        if re.match(r"https?://inspirehep\.net/api/literature/\d+/?$", (r.get("exact_locator") or "").strip())
    ]
    residual_ids = [d["citation_id"] for d in residual]
    check("RESIDUAL::four_rows_are_SRC-087_089_090_092", residual_ids == ["SRC-087", "SRC-089", "SRC-090", "SRC-092"],
          json.dumps(residual))
    check("RESIDUAL::none_is_inspirehep_exact_locator", not inspire_exact_values,
          f"{len(inspire_exact_values)} exact_locator values match inspirehep.net/api/literature/<id>; "
          f"the 10 exact_locator RECORD_ENDPOINT rows are SRC-059/060/067/068/071/072/086/087/089/092")

    # --- HF-03 resolution axis ----------------------------------------------------------------
    rr = Counter((r.get("resolver_result") or "").strip().lower() for r in ledger_rows)
    bad_rr = rr.get("unresolved", 0) + rr.get("contradicted", 0)
    check("HF03::resolution_axis_zero", bad_rr == 0, f"resolver_result counter={dict(rr)}")
    check("RUBRIC::hf03_definition_present", "unsupported_citation" in rubric_text, "evaluation_rubric.yaml HF-03")

    # --- Lead-scanner write-safety note (not installed/executed) ------------------------------
    scanner_text = PATHS["artifacts/literature/reviews/l11_l1_locator_scope_audit.py"].read_text()
    check("SCANNER::writes_its_own_output_only",
          "OUT_JSON" in scanner_text and "L1-locator-scope-L11-machine.json" in scanner_text,
          "lead scanner writes its machine-record path; not executed by this worker")

    # --- T1 == T0 stability -------------------------------------------------------------------
    t1 = {rel: sha256(p) for rel, p in PATHS.items()}
    check("STABILITY::T0_equals_T1", t0 == t1, f"{sum(1 for k in t0 if t0[k] != t1[k])} changed")

    # --- Findings -----------------------------------------------------------------------------
    findings = [
        {
            "id": "W074-L11-F1", "severity": "moderate", "kind": "provenance-binding",
            "target": "reviews/L1-gate-adjudication-lead-literature-L11.json",
            "statement": ("The adjudication binds its scope ruling to the ref "
                          "'runtime/state/controller_verification/astra-lifecycle-07-decisions.json#REC-6'. "
                          "That file contains REC-29..REC-35 only and has no REC-6. The operative text "
                          "('evidence_url is the locator column; exact_locator is query-provenance') is "
                          "REC-6 in astra-lifecycle-04-decisions.json. The ruling's substance is confirmed; "
                          "the citation does not resolve at the path given."),
            "falsifier": "Show REC-6 present in astra-lifecycle-07-decisions.json, or show the -07 file's REC-6 text.",
        },
        {
            "id": "W074-L11-F2", "severity": "moderate", "kind": "attribution-error",
            "target": "reviews/L1-gate-adjudication-lead-literature-L11.json",
            "statement": ("The reconciliation paragraph says the 4-row disagreement with worker-025 is "
                          "'a predicate call on inspirehep.net/api/literature/<id>'. Measured: 0/97 "
                          "exact_locator values are inspirehep record endpoints (the 27 inspirehep "
                          "api/literature ?q=... values are TRUNCATED and both sides classify them so). "
                          "The 4 rows worker-025 classes OTHER are SRC-087 and SRC-089 "
                          "(api.crossref.org/works/<DOI> -> RECORD_ENDPOINT), SRC-090 "
                          "(institutional PDF with a section locator -> RECORD_PAGE) and SRC-092 "
                          "(api.openalex.org/works/doi:<DOI> -> RECORD_ENDPOINT). The 30-vs-26 count "
                          "reproduces; the stated reason does not."),
            "falsifier": "Produce an exact_locator value of the form inspirehep.net/api/literature/<id> in the pinned ledger, or show the 4 residual rows are not SRC-087/089/090/092.",
        },
        {
            "id": "W074-L11-F3", "severity": "minor", "kind": "scope-extension",
            "target": "reviews/L1-gate-adjudication-lead-literature-L11.json",
            "statement": ("The MET conclusion is computed on any_record_anchor (evidence_url OR url/doi/arxiv_id). "
                          "REC-6 reads the G-LIT locator criterion 'per-row against evidence_url'. Under the "
                          "literal reading, 2/97 rows (SRC-094, SRC-095) have an empty evidence_url; both carry "
                          "record-shaped url/doi fallbacks, so the conclusion holds under the extension but the "
                          "extension itself is not in REC-6's text."),
            "falsifier": "Show REC-6 authorizes fallback beyond evidence_url, or show SRC-094/SRC-095 have a non-empty evidence_url.",
        },
        {
            "id": "W074-L11-F4", "severity": "info", "kind": "independence-provenance",
            "target": "artifacts/literature/reviews/L1-locator-scope-L11-machine.json",
            "statement": ("Machine record and adjudication are authored by the same actor "
                          "(astra-lead-literature), and the adjudication itself declares it is not an "
                          "independent verdict. The L11 pair is therefore owner measurement, not the "
                          "non-author independence the G-LIT criterion wants; that independence must come "
                          "from the worker re-fetch/spot-check stream (worker-025/062/070/075/079/009)."),
            "falsifier": "Name a non-author measurement inside the L11 pair.",
        },
        {
            "id": "W074-L11-F5", "severity": "positive", "kind": "reproduction",
            "target": "artifacts/literature/reviews/L1-locator-scope-L11-machine.json",
            "statement": ("Independent re-classification reproduces the machine record exactly: 97/97 rows, "
                          "0 class diffs on either column; exact_locator 30 record / 67 non-record "
                          "(40 DISCOVERY_QUERY + 27 TRUNCATED + 20 RECORD_PAGE + 10 RECORD_ENDPOINT); "
                          "evidence_url 95 record / 2 ABSENT / 0 non-record; 97/97 rows carry >=1 record anchor."),
            "falsifier": "Re-run this instrument and obtain a different per-row class or count.",
        },
    ]

    report = {
        "task_id": "W074-L1-L11-SCOPE-VERIFY-01",
        "actor": "worker-074",
        "created_at": None,  # filled by caller timestamp
        "node_id": "L1",
        "node_ids": ["L0", "L1"],
        "gate": "G-LIT",
        "class_id": "GLOBAL",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        "counts_as_gate_verdict": False,
        "counts_as_independent": True,
        "targets": {
            "machine_record": "artifacts/literature/reviews/L1-locator-scope-L11-machine.json#2a9f73b223ec",
            "adjudication": "reviews/L1-gate-adjudication-lead-literature-L11.json#6d8e86e360c9",
        },
        "pins": t0,
        "pins_declared": PINS,
        "pins_match": {rel: t0[rel] == PINS[rel] for rel in PINS},
        "independent_counts": measured_counts,
        "independent_breakdown": {"exact_locator": dict(ex_counts), "evidence_url": dict(ev_counts)},
        "per_row_diffs": diffs,
        "absent_evidence_url": {"rows": sorted(absent_ev), "alt_record_anchors": alt_anchor_for_absent},
        "no_record_anchor_rows": no_anchor,
        "residual_vs_worker_025": residual,
        "inspirehep_record_endpoints_in_exact_locator": inspire_exact_values,
        "hf03_resolution_axis": {"resolver_result": dict(rr), "unresolved_or_contradicted": bad_rr},
        "rulings": {
            "rec6_cited_path": cited,
            "rec6_in_cited_07_file": rec6_in_07,
            "rec6_in_04_file": rec6_in_04,
            "rec6_text_04": rec6_04_dec,
            "rec35_in_07_file": rec35_in_07,
            "rec_ids_04": ruling_ids(dec04),
            "rec_ids_07": ruling_ids(dec07),
        },
        "checks": checks,
        "checks_passed": sum(1 for c in checks if c["status"] == "PASS"),
        "checks_failed": sum(1 for c in checks if c["status"] == "FAIL"),
        "findings": findings,
        "verdict": "revise",
        "verdict_scope": "verdict on the L11 adjudication binding/attribution only; the machine record's counts are independently reproduced. Not a gate verdict, not a node status, no validation_status=passed.",
        "assumptions": [
            "the declared predicate semantics in the machine record's `predicate` block are the object under test; this worker reimplements them independently from URL semantics",
            "record_shaped = DOI | RECORD_PAGE | RECORD_ENDPOINT; non_record = ABSENT | TRUNCATED | DISCOVERY_QUERY | METADATA_ENDPOINT",
            "the lead's scanner is not executed because it rewrites the lead's own machine-record path; freeze discipline applies",
        ],
        "not_claimed": ["gate verdict", "node status", "validation_status", "ledger write", "map write", "canonical write", "HF-03 verdict"],
        "falsifier": ("FALSIFIED IF any pinned input fails to re-hash, or a re-run yields a different per-row "
                      "classification/count/finding set, or an exact_locator inspirehep.net/api/literature/<id> "
                      "value is produced, or REC-6 is produced inside astra-lifecycle-07-decisions.json."),
    }

    import datetime as _dt
    report["created_at"] = _dt.datetime.now().astimezone().isoformat(timespec="seconds")
    # Normalized digest: all evidence, excluding the volatile wall-clock field. A re-run must
    # reproduce this digest exactly; the created_at stamp is expected to differ.
    normalized = {k: v for k, v in report.items() if k not in ("created_at", "normalized_sha256")}
    report["normalized_sha256"] = hashlib.sha256(
        json.dumps(normalized, indent=1, sort_keys=True).encode()
    ).hexdigest()

    (OUTDIR / "report.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    log_lines = [f"{c['status']} {c['id']} :: {c['detail']}" for c in checks]
    (OUTDIR / "raw" / "run_log.txt").write_text("\n".join(log_lines) + "\n")

    print(json.dumps({
        "checks_passed": report["checks_passed"],
        "checks_failed": report["checks_failed"],
        "findings": [f["id"] for f in findings],
        "counts": measured_counts,
        "residual_ids": residual_ids,
        "inspirehep_exact_locator_rows": inspire_exact_values,
        "rec6_in_cited_file": rec6_in_07,
    }, indent=1))
    binding_fail = [c for c in checks if c["status"] == "FAIL" and c["binding"]]
    return 3 if binding_fail else 0


if __name__ == "__main__":
    sys.exit(main())
