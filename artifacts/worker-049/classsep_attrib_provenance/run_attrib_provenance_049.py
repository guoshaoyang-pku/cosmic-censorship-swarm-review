#!/usr/bin/env python3
"""W049-CLASSSEP-ATTRIB-PROVENANCE-04 (worker-049, node A1, gate G-AUDIT).

Read-only provenance audit: which pinned (detector, corpus) arm is the source of the
figure quoted by card astra-life06-classsep-detector-adjudication, and is the controller's
REC-32 re-attribution of it to dc8aa0de3869 (classsep_prosefix) source-faithful?

Fail-closed: any pin mismatch exits 2; a non-deterministic double run exits 3; the quoted
card text missing at the pinned line exits 4. Writes only results.json next to this file.
No gate verdict, no node status, no validation_status.

Run: python3 artifacts/worker-049/classsep_attrib_provenance/run_attrib_provenance_049.py
"""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))

TASK_ID = "W049-CLASSSEP-ATTRIB-PROVENANCE-04"
PRE_REG = os.path.join(HERE, "pre_registration.json")
OUT = os.path.join(HERE, "results.json")

QUOTED = {
    "adversarial_cleared": 10,
    "adversarial_total": 10,
    "cue_induced_fn_high_confidence": 9,
    "declaration_diffs": 13,
}

PINS = [
    ("fn_audit_results", "artifacts/worker-049/classsep_fn_audit/results.json",
     "9e1bf20439349eb352c6b32f39984c8c2557311bc6886342c5ab7bdfd72a2717"),
    ("successor_audit_results", "artifacts/worker-049/classsep_successor_audit/results.json",
     "e3110ee9b7cf7a4ae904b24774f0f9df60bf39e029651bf20bc2b81557d03313"),
    ("r3_adjudication", "reviews/CLASSSEP-calibration-adjudication.json",
     "7714ffd5b467c506bc8a8736ba1626a9f8a9211092e5313e74c77a4ccb51cec1"),
    ("life07_decisions", "runtime/state/controller_verification/astra-lifecycle-07-decisions.json",
     "fc1d6fb4da6f9998d5e02f2314a24fc643eef011bb2ed434a092d4f7171d0ba8"),
]

CARD_PATH = "comms/inbox/astra-lead-audit.jsonl"
CARD_LINE = 26
CARD_LINE_SHA = "794137ddc9cbd9e99c2a7e1a40f77ce438185b5c3323b7586d7dfbfd05877305"
CARD_EVENT_ID = "astra-life06-classsep-detector-adjudication"
CARD_FIGURE_TEXT = "10/10 cue-carrying genuine assertions suppressed, 9 HIGH; 13 declaration diffs"

CORPUS_V2_TOKENS = ["G01", "G02", "G03", "G04", "G05", "G06", "G07", "G08", "G09", "G10",
                    "G01T", "G02T", "G03T", "G04T", "G05T", "G06T", "G07T", "G08T", "G09T",
                    "G10T", "GM2", "GM3", "GM4", "GM5"]
CORPUS_V2_HASHES = ["db6dff9f4edaf585a78c2a5e084665c037db61bc354a86c5cba74f5f71c6ed8b"]
PROSEFIX_DETECTORS = {"staged_prosefix", "staged_prosefix_worker049"}
LIVE_DETECTORS = {"live_canonical"}


def sha256_file(rel):
    h = hashlib.sha256()
    with open(os.path.join(ROOT, rel), "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_pins():
    out = []
    ok = True
    for pid, rel, expected in PINS:
        actual = sha256_file(rel)
        match = actual == expected
        ok = ok and match
        out.append({"id": pid, "path": rel, "expected": expected, "actual": actual, "match": match})
    return ok, out


def extract_audit_rows(source_id, doc):
    rows = []
    for corpus, cdata in doc.get("corpora", {}).items():
        for det, mdata in cdata.get("modules", {}).items():
            agg = mdata.get("aggregates", {})
            cleared = agg.get("adversarial_cleared", [])
            decl = agg.get("declaration_diff_vs_c266", None)
            rows.append({
                "source": source_id,
                "corpus": corpus,
                "corpus_sha256": cdata.get("sha256"),
                "detector": det,
                "adversarial_total": agg.get("adversarial_total"),
                "adversarial_cleared": len(cleared),
                "adversarial_cleared_ids": list(cleared),
                "cue_induced_fn_total": agg.get("cue_induced_fn_total"),
                "cue_induced_fn_high_confidence": agg.get("cue_induced_fn_high_confidence"),
                "declaration_diffs": (len(decl) if decl is not None else None),
                "declaration_diff_ids": list(decl) if decl is not None else None,
            })
    return rows


def extract_r3_rows(doc):
    rows = []
    for arm, adata in doc.get("corpus_d_worker049_cue_fn", {}).items():
        cleared = adata.get("adversarial_cleared", [])
        rows.append({
            "source": "r3_adjudication",
            "corpus": "corpus_d_worker049_cue_fn (=corpus v1: A01-A12)",
            "detector": arm,
            "adversarial_total": adata.get("adversarial_total"),
            "adversarial_cleared": len(cleared),
            "adversarial_cleared_ids": list(cleared),
            "cue_induced_fn_total": adata.get("cue_induced_fn_total"),
            "cue_induced_fn_high_confidence": adata.get("cue_induced_fn_high_confidence"),
            "declaration_diffs": None,
            "declaration_diff_ids": None,
        })
    return rows


def classify(row):
    components = {
        "adversarial_cleared": row["adversarial_cleared"] == QUOTED["adversarial_cleared"],
        "adversarial_total": row["adversarial_total"] == QUOTED["adversarial_total"],
        "cue_induced_fn_high_confidence":
            row["cue_induced_fn_high_confidence"] == QUOTED["cue_induced_fn_high_confidence"],
        "declaration_diffs": row["declaration_diffs"] == QUOTED["declaration_diffs"],
    }
    hits = sum(1 for v in components.values() if v)
    if hits == 4:
        verdict = "EXACT_MATCH"
    elif hits == 3:
        verdict = "PARTIAL_MATCH"
    else:
        verdict = "NO_MATCH"
    return verdict, components, hits


def analyze():
    fn_doc = json.load(open(os.path.join(ROOT, "artifacts/worker-049/classsep_fn_audit/results.json")))
    succ_doc = json.load(open(os.path.join(ROOT, "artifacts/worker-049/classsep_successor_audit/results.json")))
    r3_doc = json.load(open(os.path.join(ROOT, "reviews/CLASSSEP-calibration-adjudication.json")))

    rows = extract_audit_rows("fn_audit", fn_doc) + extract_audit_rows("successor_audit", succ_doc)
    r3_rows = extract_r3_rows(r3_doc)
    census_rows = rows + r3_rows
    for r in census_rows:
        r["match"], r["component_match"], r["component_hits"] = classify(r)

    exact = [r for r in census_rows if r["match"] == "EXACT_MATCH"]
    exact_sources = sorted({(r["source"], r["corpus"], r["detector"]) for r in exact})
    prosefix_exact = [r for r in exact if r["detector"] in PROSEFIX_DETECTORS]
    live_exact = [r for r in exact if r["detector"] in LIVE_DETECTORS]

    # r3 census corpus coverage: byte-level scan of the pinned adjudication file.
    raw = open(os.path.join(ROOT, "reviews/CLASSSEP-calibration-adjudication.json"), "rb").read()
    token_hits = sorted({t for t in CORPUS_V2_TOKENS if t.encode() in raw})
    hash_hits = [h for h in CORPUS_V2_HASHES if h.encode() in raw]
    r3_corpus_v2_bearing = bool(token_hits or hash_hits)
    r3_decl13 = b"declaration_diff" in raw

    if prosefix_exact:
        verdict = "REC32_FAITHFUL"
    elif exact:
        verdict = "REC32_NOT_SOURCE_FAITHFUL"
    else:
        verdict = "REC32_UNSUPPORTED"

    coverage_gap = bool(exact) and all(r["corpus"].startswith("corpus_v2") for r in exact) and not r3_corpus_v2_bearing

    # Falsification checks demanded by the pre-registered falsifier.
    checks = {
        "exact_match_set_is_only_live_applied_on_corpus_v2": (
            len(exact) > 0 and all(r["detector"] in LIVE_DETECTORS and r["corpus"] == "corpus_v2"
                                   for r in exact)),
        "prosefix_has_no_decl13_at_any_pinned_corpus": all(
            not (r["detector"] in PROSEFIX_DETECTORS and r["declaration_diffs"] == 13)
            for r in census_rows if r["source"] != "r3_adjudication"),
        "r3_has_no_corpus_v2_fixture_bytes": not r3_corpus_v2_bearing,
        "r3_corpus_d_no_exact_row": all(r["match"] != "EXACT_MATCH" for r in r3_rows),
    }

    payload = {
        "schema": "worker-049/classsep-attrib-provenance-results/v1",
        "task_id": TASK_ID,
        "actor": "worker-049",
        "node_id": "A1",
        "gate": "G-AUDIT",
        "class_id": "AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "pre_registration_sha256": sha256_file("artifacts/worker-049/classsep_attrib_provenance/pre_registration.json"),
        "quoted_figure": QUOTED,
        "quoted_figure_text": CARD_FIGURE_TEXT,
        "card": {
            "path": CARD_PATH,
            "line": CARD_LINE,
            "line_sha256_expected": CARD_LINE_SHA,
            "event_id": CARD_EVENT_ID,
        },
        "rows": census_rows,
        "exact_match_set": [{"source": s, "corpus": c, "detector": d} for (s, c, d) in exact_sources],
        "partial_match_set": [
            {"source": r["source"], "corpus": r["corpus"], "detector": r["detector"],
             "cleared": r["adversarial_cleared"], "high": r["cue_induced_fn_high_confidence"],
             "declaration_diffs": r["declaration_diffs"]}
            for r in census_rows if r["match"] == "PARTIAL_MATCH"],
        "r3_census_coverage": {
            "corpus_v2_fixture_tokens_found": token_hits,
            "corpus_v2_sha256_found": hash_hits,
            "corpus_v2_bearing": r3_corpus_v2_bearing,
            "declaration_diff_13_context_present": r3_decl13,
            "corpus_d_is": "corpus v1 (A01-A12) only",
        },
        "verdict": verdict,
        "verdict_detail": {
            "prosefix_exact_rows": [r["detector"] for r in prosefix_exact],
            "live_exact_rows": [f'{r["source"]}:{r["corpus"]}:{r["detector"]}' for r in live_exact],
            "coverage_gap": coverage_gap,
            "coverage_gap_statement": (
                "the only exact source of the quoted figure is corpus v2, which the r3 census "
                "does not measure; its corpus_d is corpus v1, where the applied arm scores 1/12 "
                "cleared (1 HIGH) and the prosefix arm 11/12 cleared (10 HIGH), and no arm scores "
                "10/10 cleared with 9 HIGH and 13 declaration diffs."
                if coverage_gap else "not applicable"),
        },
        "falsification_checks": checks,
        "falsifier": (
            "Re-run this runner at the pins: falsified by any pin mismatch, a non-deterministic "
            "double run, an EXACT_MATCH row other than the FN-audit/successor-audit live applied "
            "detector on corpus v2, a declaration-diff count of 13 for dc8aa0de3869 at any pinned "
            "corpus, or a byte-level hit for corpus v2 fixtures (G01..G10/GM2..GM5/db6dff9f4eda) "
            "inside reviews/CLASSSEP-calibration-adjudication.json."),
        "non_claims": [
            "No gate verdict, no node status, no validation_status, no adoption/rollback decision, no edit to any canonical, proposed, pinned or review file.",
            "Does not re-adjudicate decision (c) and does not dispute that classsep_prosefix dc8aa0de carries 10 HIGH cue-induced false negatives on corpus v1.",
            "worker-049 authored both audited results files; the provenance question is answered from their recorded bytes alone.",
            "No natural-text FN/FP rate is claimed; all corpora are adversarial by construction.",
        ],
    }
    return payload


def main():
    ok, pin_rows = verify_pins()
    if not ok:
        print("PIN MISMATCH", json.dumps([r for r in pin_rows if not r["match"]]), file=sys.stderr)
        return 2

    # Card line binding check (line bytes, not the growing file).
    raw_lines = open(os.path.join(ROOT, CARD_PATH), "rb").read().splitlines(True)
    if len(raw_lines) < CARD_LINE:
        print("CARD LINE MISSING", file=sys.stderr)
        return 4
    line_bytes = raw_lines[CARD_LINE - 1]
    line_sha = hashlib.sha256(line_bytes).hexdigest()
    card = json.loads(line_bytes)
    if line_sha != CARD_LINE_SHA or card.get("event_id") != CARD_EVENT_ID or CARD_FIGURE_TEXT not in card.get("acceptance", ""):
        print("CARD BINDING MISMATCH", line_sha, card.get("event_id"), file=sys.stderr)
        return 4

    first = analyze()
    second = analyze()
    if json.dumps(first, sort_keys=True) != json.dumps(second, sort_keys=True):
        print("NON-DETERMINISTIC DOUBLE RUN", file=sys.stderr)
        return 3

    first["pins"] = pin_rows
    first["card"]["line_sha256_measured"] = line_sha
    first["card"]["line_sha256_match"] = line_sha == CARD_LINE_SHA
    first["exact_source_count"] = len(first["exact_match_set"])

    with open(OUT, "w") as fh:
        json.dump(first, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print(json.dumps({
        "verdict": first["verdict"],
        "exact_match_set": first["exact_match_set"],
        "coverage_gap": first["verdict_detail"]["coverage_gap"],
        "checks": first["falsification_checks"],
    }, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
