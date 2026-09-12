#!/usr/bin/env python3
"""W058-F2B-ACCEPT-DISPOSITION-06 instrument.

Bounded, class-bound (AF-SCC-C0-VAC-GEN / node F2b) artifact-consistency audit.

Question: at the live F2b pin, the F2b verdict corpus contains ACCEPTs with
hard_failures=[] while same-pin REVISE verdicts record two live hard carriers
(C0 containment denial; C0 class-size premise inversion) plus one minor mislabel.
Does any accepting verdict explicitly DISPOSE of those recorded carriers, or is the
accept set merely silent about them?

This is a measurement over verdict bytes and schema bytes. It is NOT a gate verdict,
not a node transition, not an independence/blindness adjudication (the audit lead owns
that), and it makes no mathematical claim.

Outputs (written next to this file):
  disposition_report.json     -- pins, corpus manifest, carrier x reviewer matrix, verdict
  sensitivity_selftest.json   -- 6 synthetic controls/mutants with expected outcomes

Reproduce:  python3 artifacts/worker-058/f2b_accept_disposition/check_accept_disposition.py --root .
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys

C0_REL = "schemas/af_scc_c0_vacuum.yaml"
C2_REL = "schemas/af_scc_c2_vacuum.yaml"
FROZEN_REL = "artifacts/formulation/FROZEN.json"
REVIEWS_REL = "reviews"

# Live pins measured 2026-09-12 ~01:12 +08:00 (re-measured at run time; drift is reported).
DECLARED_PINS = {
    C0_REL: "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    C2_REL: "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    FROZEN_REL: "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
}

# Carriers: distinctive phrases that define each recorded defect in the C0 bytes.
# Located by content, not by line number, so a line shift cannot silently miss them.
CARRIERS = [
    {
        "id": "H1",
        "severity": "hard",
        "file": C0_REL,
        "field": "regularity.must_not_conflate[0]",
        "phrase": "No containment with C2 or C0 is asserted here",
        "record_keywords": ["must_not_conflate", "containment with C2"],
        "recorded_by": ["worker-018 (W018-R13-F2B-B1)", "worker-066 (W066-R13-F2B-H1)"],
        "contradicted_by": "implication_ledger.extension_class_containment (same file asserts E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2)",
    },
    {
        "id": "H2",
        "severity": "hard",
        "file": C0_REL,
        "field": "implication_ledger.forbidden_transfers[0].reason",
        "phrase": "C2 is a strictly larger extension class",
        "record_keywords": ["forbidden_transfers", "strictly larger"],
        "recorded_by": ["worker-053 (corroborates HF-075-F2b-LARGER / L-FORM-01)", "worker-066 (W066-R13-F2B-H2)"],
        "contradicted_by": "implication_ledger.extension_class_containment (E_C2 is the smallest set in the chain, so 'larger' is the inverted premise)",
    },
    {
        "id": "M1",
        "severity": "minor",
        "file": C0_REL,
        "field": "conclusion.forbidden_weakenings (two-sided direction item)",
        "phrase": "replacing future by two-sided direction",
        "record_keywords": ["forbidden_weakenings", "two-sided"],
        "recorded_by": ["worker-058 (W058-REPAIR-CERT-02 MINOR-1, R2-10 refresh)"],
        "contradicted_by": "conclusion.forbidden_strengthenings lists two-sided inextendibility as the stronger statement",
    },
]

# Phrases an accepting verdict could use to dispose of a carrier. Heuristic, documented.
DISPOSITION_MARKERS = [
    "dispos", "discharged", "not a defect", "no defect", "non-normative", "advisory only",
    "withdrawn", "refuted", "no longer live", "superseded", "adjudicated", "resolved",
    "not material", "steelman",
]
# Scoped containers searched for carrier mention + disposition marker co-occurrence.
BLOCK_KEYS = ("findings", "hard_failures", "checks", "checklist", "carriers", "adjudication",
              "disposition", "verdict_rationale", "notes", "blocking_failures", "controls")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def as_text(v) -> str:
    if isinstance(v, str):
        return v
    if isinstance(v, dict):
        for k in ("value", "verdict", "status", "name"):
            if isinstance(v.get(k), str):
                return v[k]
    return ""


def measure(path: pathlib.Path) -> dict:
    b = path.read_bytes()
    return {"path": str(path), "sha256": sha256_bytes(b), "bytes": len(b), "text": b.decode("utf-8", "replace")}


def locate(text: str, phrase: str) -> dict:
    idx = text.find(phrase)
    if idx < 0:
        return {"present": False, "line": None, "col": None}
    line = text.count("\n", 0, idx) + 1
    col = idx - (text.rfind("\n", 0, idx) + 1) + 1
    return {"present": True, "line": line, "col": col}


def binding_basis(doc: dict, text: str, pin_prefix: str) -> str:
    """strict_field: a declared 64-hex pin field matches.
    explicit_measured: the file names the live pin as the target it measured.
    none: not bound to the live pin (stale or unrelated)."""
    strict_fields = {}
    for f in ("reviewed_sha256", "artifact_sha256", "reviewed_frozen_sha256", "target_sha256"):
        v = doc.get(f)
        if isinstance(v, str):
            strict_fields[f] = v
    pins = doc.get("reviewed_pins")
    if isinstance(pins, dict):
        for k, v in pins.items():
            if isinstance(v, str) and re.fullmatch(r"[0-9a-fA-F]{64}", v):
                strict_fields[f"reviewed_pins.{k}"] = v
            elif isinstance(v, dict) and isinstance(v.get("sha256"), str):
                strict_fields[f"reviewed_pins.{k}.sha256"] = v["sha256"]
    if any(v.startswith(pin_prefix) for v in strict_fields.values()):
        return "strict_field"
    for m in re.finditer(re.escape(pin_prefix), text):
        ctx = text[max(0, m.start() - 200):m.start()]
        if re.search(r"(target identity|measured|measures|reviewed_sha256|target_sha256|reviewed pin)", ctx, re.I):
            return "explicit_measured"
    return "none"


def disposition_blocks(doc: dict) -> list[tuple[str, str]]:
    blocks = []
    for key in BLOCK_KEYS:
        v = doc.get(key)
        if isinstance(v, list):
            for i, el in enumerate(v):
                blocks.append((f"{key}[{i}]", json.dumps(el)))
        elif isinstance(v, str):
            blocks.append((key, v))
    for key, v in doc.items():
        if isinstance(v, str) and re.search(r"dispos|adjudicat", key, re.I):
            blocks.append((key, v))
    return blocks


def classify_review(doc: dict, text: str, pin_prefix: str, carriers: list[dict]) -> dict:
    hf = doc.get("hard_failures")
    n_hard = len(hf) if isinstance(hf, list) else (hf if isinstance(hf, int) else 0)
    blocking = doc.get("blocking_failures")
    n_block = len(blocking) if isinstance(blocking, list) else 0
    blocks = disposition_blocks(doc)
    disp = {}
    for c in carriers:
        phrase = c["phrase"]
        kws = c.get("record_keywords") or []
        keyword_hit = bool(kws) and all(k in text for k in kws)
        mention = phrase in text or keyword_hit
        hard_record = False
        for item in (hf if isinstance(hf, list) else []):
            blob = json.dumps(item)
            if phrase in blob or (kws and all(k in blob for k in kws)):
                hard_record = True
        disposition = None
        for bid, blob in blocks:
            if phrase in blob or (kws and all(k in blob for k in kws)):
                for m in DISPOSITION_MARKERS:
                    if m in blob.lower():
                        disposition = {"block": bid, "marker": m, "snippet": blob[:220]}
                        break
            if disposition:
                break
        disp[c["id"]] = {
            "mention": bool(mention),
            "keyword_hit": bool(keyword_hit),
            "hard_record": hard_record,
            "disposition": disposition,
            "disposed": bool(disposition and mention and not hard_record),
        }
    return {
        "review_id": doc.get("review_id") or doc.get("event_id"),
        "reviewer": doc.get("reviewer") or doc.get("actor"),
        "verdict": as_text(doc.get("verdict")),
        "score": doc.get("score"),
        "created_at": doc.get("created_at"),
        "gate": doc.get("gate"),
        "blind": doc.get("blind"),
        "counts_as_full_schema_verdict": doc.get("counts_as_full_schema_verdict"),
        "binding_basis": binding_basis(doc, text, pin_prefix),
        "n_hard_failures": n_hard,
        "n_blocking_failures": n_block,
        "carriers": disp,
    }


def analyse(root: pathlib.Path, c0_text: str, c0_pin_prefix: str, reviews: list[tuple[str, dict, str]]) -> dict:
    carriers_live = []
    for c in CARRIERS:
        loc = locate(c0_text, c["phrase"])
        carriers_live.append({**{k: c[k] for k in ("id", "severity", "file", "field", "phrase")},
                              "live": loc["present"], "line": loc["line"]})
    rows = []
    for relpath, doc, text in reviews:
        row = classify_review(doc, text, c0_pin_prefix, carriers_live)
        row["file"] = relpath
        row["sha256"] = sha256_bytes(text.encode("utf-8", "replace"))
        rows.append(row)
    live = [r for r in rows if r["binding_basis"] != "none"]
    stale = [r for r in rows if r["binding_basis"] == "none"]
    accepts = [r for r in live if (r["verdict"] or "").lower() == "accept"]
    nonaccepts = [r for r in live if (r["verdict"] or "").lower() != "accept"]
    active = [c for c in carriers_live if c["live"]]
    hard_records = {c["id"]: [r["reviewer"] for r in live if r["carriers"][c["id"]]["hard_record"]] for c in active}
    dispositions = {c["id"]: [r["reviewer"] for r in accepts if r["carriers"][c["id"]]["disposed"]] for c in active}
    accepts_with_hard = [(r["reviewer"], c["id"]) for r in accepts for c in active if r["carriers"][c["id"]]["hard_record"]]
    if not active:
        verdict = "CARRIERS_ABSENT_REPAIRED"
    elif not accepts:
        verdict = "NO_ACCEPT_AT_PIN"
    elif accepts_with_hard and not any(dispositions.values()):
        verdict = "ACCEPT_CONTRADICTS_OWN_HARD_RECORD"
    elif not any(hard_records.values()):
        verdict = "ACCEPTS_UNOPPOSED_AT_PIN"
    elif any(dispositions.values()):
        verdict = "PARTIAL_DISPOSITION"
    else:
        verdict = "CONFLICT_UNRESOLVED_NO_DISPOSITION"
    matrix = []
    for r in live:
        matrix.append({
            "reviewer": r["reviewer"], "verdict": r["verdict"], "score": r["score"],
            "binding_basis": r["binding_basis"], "n_hard_failures": r["n_hard_failures"],
            "carriers": {cid: {"mention": v["mention"], "hard_record": v["hard_record"],
                               "disposed": v["disposed"], "disposition": v["disposition"]}
                         for cid, v in r["carriers"].items()},
        })
    return {
        "verdict": verdict,
        "carriers_live": carriers_live,
        "hard_recorded_by": hard_records,
        "disposed_by_accepts": dispositions,
        "accepts_with_hard_record": accepts_with_hard,
        "n_live_reviews": len(live),
        "n_accepts": len(accepts),
        "n_nonaccepts": len(nonaccepts),
        "accepts": [{"reviewer": r["reviewer"], "score": r["score"], "n_hard_failures": r["n_hard_failures"],
                     "binding_basis": r["binding_basis"], "blind": r["blind"]} for r in accepts],
        "nonaccepts": [{"reviewer": r["reviewer"], "verdict": r["verdict"], "score": r["score"],
                        "n_hard_failures": r["n_hard_failures"], "binding_basis": r["binding_basis"]}
                       for r in nonaccepts],
        "matrix": matrix,
        "stale_pin_reviews": [{"file": r["file"], "reviewer": r["reviewer"], "verdict": r["verdict"]} for r in stale],
        "rows": rows,
    }


SYNTH_ACCEPT_DISPOSES = {
    "reviewer": "mut-ant", "verdict": "accept", "reviewed_sha256": "PIN", "hard_failures": [],
    "findings": ["H2 carrier implication_ledger.forbidden_transfers[0] 'C2 is a strictly larger extension class' is disposed: adjudicated non-normative prose."],
}
SYNTH_ACCEPT_CLEAN = {"reviewer": "mut-clean", "verdict": "accept", "reviewed_sha256": "PIN", "hard_failures": []}
SYNTH_REVISE_HARD = {
    "reviewer": "mut-rev", "verdict": "revise", "reviewed_sha256": "PIN",
    "hard_failures": [{"carrier": "implication_ledger.forbidden_transfers[0].reason",
                       "finding": "C2 is a strictly larger extension class is inverted"}],
}
SYNTH_STALE = {"reviewer": "mut-stale", "verdict": "accept", "reviewed_sha256": "0" * 64, "hard_failures": []}


def run_selftest(root: pathlib.Path, c0_text: str, pin_prefix: str) -> dict:
    patched = c0_text.replace("C2 is a strictly larger extension class", "C2 is a strictly smaller extension class")
    patched = patched.replace("No containment with C2 or C0 is asserted here", "Containment with C2 and C0 is asserted and used")
    patched = patched.replace("replacing future by two-sided direction", "replacing future by past direction")
    accept_with_hard = dict(SYNTH_ACCEPT_CLEAN)
    accept_with_hard["hard_failures"] = [{"carrier": "implication_ledger.forbidden_transfers[0].reason",
                                          "finding": "C2 is a strictly larger extension class is inverted"}]
    cases = []
    for name, docs, text, expect in [
        ("CONFLICT_accept_plus_revise_hard", [SYNTH_ACCEPT_CLEAN, SYNTH_REVISE_HARD], c0_text, "CONFLICT_UNRESOLVED_NO_DISPOSITION"),
        ("MUT_accept_disposes_H2", [SYNTH_ACCEPT_DISPOSES, SYNTH_REVISE_HARD], c0_text, "PARTIAL_DISPOSITION"),
        ("MUT_accept_carrying_hard_H2", [accept_with_hard], c0_text, "ACCEPT_CONTRADICTS_OWN_HARD_RECORD"),
        ("MUT_carriers_absent_repaired", [SYNTH_ACCEPT_CLEAN, SYNTH_REVISE_HARD], patched, "CARRIERS_ABSENT_REPAIRED"),
        ("MUT_stale_pin_excluded", [SYNTH_STALE], c0_text, "NO_ACCEPT_AT_PIN"),
        ("MUT_no_revise_side", [SYNTH_ACCEPT_CLEAN], c0_text, "ACCEPTS_UNOPPOSED_AT_PIN"),
    ]:
        corpus = []
        for i, d in enumerate(docs):
            dd = dict(d)
            if dd.get("reviewed_sha256") == "PIN":
                dd["reviewed_sha256"] = pin_prefix + "0" * (64 - len(pin_prefix))
            corpus.append((f"{name}-{i}", dd, json.dumps(dd)))
        out = analyse(root, text, pin_prefix, corpus)
        ok = out["verdict"] == expect
        cases.append({"case": name, "expected": expect, "measured": out["verdict"], "pass": ok})
    return {"cases": cases, "passed": sum(1 for c in cases if c["pass"]), "total": len(cases),
            "all_pass": all(c["pass"] for c in cases)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    args = ap.parse_args()
    root = pathlib.Path(args.root).resolve()

    c0 = measure(root / C0_REL)
    c2 = measure(root / C2_REL)
    frozen = measure(root / FROZEN_REL)

    reviews = []
    for p in sorted((root / REVIEWS_REL).glob("*.json")):
        try:
            doc = json.loads(p.read_text())
        except Exception:
            continue
        blob = json.dumps(doc)
        if (doc.get("target_id") == "F2b" or "F2b" in p.name or doc.get("node_id") == "F2b"
                or doc.get("class_id") == "AF-SCC-C0-VAC-GEN" or "AF-SCC-C0-VAC-GEN" in blob):
            reviews.append((str(p.relative_to(root)), doc, p.read_text()))

    out = analyse(root, c0["text"], c0["sha256"][:12], reviews)
    out["pins_measured"] = {k: v["sha256"] for k, v in ((C0_REL, c0), (C2_REL, c2), (FROZEN_REL, frozen))}
    out["pins_declared"] = dict(DECLARED_PINS)
    out["pin_drift"] = {k: (DECLARED_PINS[k] != out["pins_measured"][k]) for k in DECLARED_PINS}
    out["corpus_filter"] = ("reviews/*.json with target_id==F2b or node_id==F2b or 'F2b' in filename or "
                            "class_id==AF-SCC-C0-VAC-GEN")
    selftest = run_selftest(root, c0["text"], c0["sha256"][:12])
    out["sensitivity_selftest"] = selftest
    out["boundary"] = [
        "Verdicts bind to the measured sha256 values, not to revision labels.",
        "Mention/disposition classification is lexical and documented; a review can examine a carrier without using the carrier phrase (recorded as no mention, not as absence of examination).",
        "A 'disposed' row requires carrier mention and a disposition marker inside one scoped verdict element; top-level or future-falsifier prose is not counted.",
        "Blindness/independence and any gate consequence are the audit lead's adjudication; this report only measures what the verdict bytes record.",
        "No mathematical truth, node completion, validation_status or gate verdict is claimed.",
    ]
    out["falsifier"] = ("A reader shows (a) an accepting verdict at the bound pin that explicitly disposes of H1 or H2 "
                        "in bytes this classifier missed, (b) that a listed hard carrier is absent from the bound C0 bytes, "
                        "or (c) that a listed hard record is not present in the cited review at its measured hash. "
                        "Any of these refutes the corresponding row.")

    c0_after = sha256_bytes((root / C0_REL).read_bytes())
    out["pin_stable_during_run"] = (c0_after == c0["sha256"])

    here = pathlib.Path(__file__).resolve().parent
    (here / "disposition_report.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    (here / "sensitivity_selftest.json").write_text(json.dumps(selftest, indent=1, sort_keys=True) + "\n")

    print(json.dumps({"verdict": out["verdict"], "pins": out["pins_measured"], "pin_drift": out["pin_drift"],
                      "pin_stable_during_run": out["pin_stable_during_run"],
                      "n_live_reviews": out["n_live_reviews"], "n_accepts": out["n_accepts"],
                      "hard_recorded_by": out["hard_recorded_by"], "disposed_by_accepts": out["disposed_by_accepts"],
                      "accepts": out["accepts"],
                      "selftest": {"passed": selftest["passed"], "total": selftest["total"],
                                   "all_pass": selftest["all_pass"]}}, indent=1))
    return 0 if selftest["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
