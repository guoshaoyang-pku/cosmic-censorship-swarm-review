#!/usr/bin/env python3
"""W048-F1-PROVENANCE-ANCHOR-CENSUS-01.

Independent, read-only, deterministic census of the citation obligations that
`schemas/af_wcc_vacuum.yaml` (F1, class AF-WCC-VAC-GEN) declares about itself as
UNRESOLVED, against the frozen literature artifacts.

Question: do the frozen L0 ledger and L1 citation audit contain any primary-source
anchor for F1's `provenance.sources` concepts and `unresolved_citations` items?
The literature lead asserts these have 0 hits (BL-11, lit-l7-...-007 / lit-l8-...-008).
This instrument measures that assertion from pinned bytes instead of repeating it.

Authority boundary: worker evidence only. No canonical write, no gate verdict, no node
status, no validation_status=passed, no citation-support adjudication. See
PREREGISTRATION.json for the predicates and the run conditions, frozen before the run.

Exit codes: 0 = all controls pass; 3 = pinned input drift; 4 = control failure.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

# --- pins: the bytes this census is about (measured, not trusted) ------------------------
PINS = {
    "schemas/af_wcc_vacuum.yaml": "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "ledger/theorems.jsonl": "a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28",
    "ledger/citation_audit.csv": "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9",
    "artifacts/literature/registry.jsonl": "ea02d1943fda50e5e1c7ce10fe2a1cd6e7784a2c9f2467c7cb8597c63442652d",
    "evaluation_rubric.yaml": "d748a9e3574ebe0c34c22b608ba0bf018d525a644ebff815371c6dcfca055885",
    "artifacts/literature/FORMULATION_ANCHORS.md": "d952d136f880491e451e67bf24d545d78b7593278f5ac37ad4616b1eb040557b",
}

FROZEN_CLASSES = (
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
)

# --- pre-registered predicates -----------------------------------------------------------
# Each regex is derived from the obligation string in the frozen F1 bytes, before the run.
# Text is lowercased and whitespace-normalised; the regexes are matched with re.search.
OBLIGATIONS = (
    {
        "id": "O1-weighted-sobolev",
        "f1_field": "provenance.sources[0]",
        "needed_for": "data_class, regularity",
        "concept": "asymptotically flat initial data and weighted Sobolev classes",
        "regex": (
            r"weighted\s+sobolev"
            r"|sobolev[^.]{0,60}(threshold|weight|regularity|delta|s\s*>)"
            r"|\bs\s*>\s*5\s*/\s*2\b"
            r"|\bdelta\b[^.]{0,40}\(\s*1\s*/\s*2\s*,\s*1\s*\)"
        ),
        "bl11_item": "weighted-Sobolev thresholds s>5/2 and delta in (1/2,1)",
    },
    {
        "id": "O2-mghd",
        "f1_field": "provenance.sources[1]",
        "needed_for": "regularity, quantifiers D2",
        "concept": "existence and uniqueness of the maximal globally hyperbolic development",
        "regex": (
            r"(maximal\s+(globally\s+hyperbolic|cauchy)\s+development|\bmghd\b)"
            r"[^.]{0,120}(exist|uniqu)"
            r"|(exist|uniqu)[^.]{0,120}"
            r"(maximal\s+(globally\s+hyperbolic|cauchy)\s+development|\bmghd\b)"
        ),
        "bl11_item": None,
    },
    {
        "id": "O3-positive-mass",
        "f1_field": "provenance.sources[2]",
        "needed_for": "data_class.adm_mass",
        "concept": "positive mass theorem and rigidity",
        "regex": (
            r"positive\s+(mass|energy)[^.]{0,80}(theorem|rigidit|adm)"
            r"|adm\s+mass[^.]{0,80}(positive|non-?negativ|theorem)"
        ),
        "bl11_item": "positive mass theorem and rigidity",
    },
    {
        "id": "O4-predictability-def",
        "f1_field": "provenance.sources[3]",
        "needed_for": "conclusion.equivalent_standard_formulation",
        "concept": "definition of future asymptotic predictability and its relation to the schema conclusion",
        "regex": r"future\s+asymptotic\s+predictab|asymptotic\s+predictab",
        "bl11_item": "future-asymptotic-predictability equivalence",
    },
    {
        "id": "O5-wcc-status",
        "f1_field": "provenance.sources[4]",
        "needed_for": "no status claim is made by this schema",
        "concept": "known status (proved/refuted/open) of weak cosmic censorship for generic AF vacuum data",
        "regex": (
            r"weak\s+cosmic\s+censorship[^.]{0,200}(generic|genericit|open|proved|proof|refut|unresolved)"
            r"|(generic|genericit)[^.]{0,200}weak\s+cosmic\s+censorship"
        ),
        "bl11_item": None,
    },
    {
        "id": "U1-s-threshold-delta",
        "f1_field": "provenance.unresolved_citations[0]",
        "needed_for": "data_class.regularity (D0 threshold)",
        "concept": "s > 5/2 threshold and delta in (1/2,1) weight range",
        "regex": (
            r"s\s*>\s*5\s*/\s*2"
            r"|\b5\s*/\s*2\b"
            r"|\bdelta\b[^.]{0,40}\(\s*1\s*/\s*2\s*,\s*1\s*\)"
        ),
        "bl11_item": "weighted-Sobolev thresholds s>5/2 and delta in (1/2,1)",
    },
    {
        "id": "U2-conformal-completion",
        "f1_field": "provenance.unresolved_citations[1]",
        "needed_for": "data_class.end_structure (conformal completion)",
        "concept": "conformal completion regularity k >= 3 and the required order of the conformal Einstein equations",
        "regex": (
            r"conformal\s+(completion|compactification)"
            r"|k\s*>=?\s*3[^.]{0,80}conformal"
            r"|conformal\s+einstein\s+equations"
        ),
        "bl11_item": None,
    },
    {
        "id": "U3-predictability-equivalence",
        "f1_field": "provenance.unresolved_citations[2]",
        "needed_for": "conclusion.equivalent_standard_formulation",
        "concept": "equivalence with future asymptotic predictability",
        "regex": (
            r"(equivalen|equivalent)[^.]{0,120}(future\s+asymptotic\s+predictab|asymptotic\s+predictab)"
            r"|(future\s+asymptotic\s+predictab|asymptotic\s+predictab)[^.]{0,120}(equivalen|equivalent)"
        ),
        "bl11_item": "future-asymptotic-predictability equivalence",
    },
)

POSITIVE_CONTROL = {"id": "PC-cauchy-horizon", "regex": r"cauchy\s+horizon",
                    "min_l0": 20, "min_l1": 20}
NEGATIVE_CONTROL = {"id": "NC-nonsense", "regex": r"zzz_no_such_concept_qqq"}
SYNTHETIC = (
    {"name": "pos_positive_mass", "obligation": "O3-positive-mass",
     "text": "the positive mass theorem and rigidity for asymptotically flat data", "expect": True},
    {"name": "neg_energy_condition", "obligation": "O3-positive-mass",
     "text": "the dominant energy condition holds on the initial data", "expect": False},
    {"name": "pos_mghd", "obligation": "O2-mghd",
     "text": "existence and uniqueness of the maximal globally hyperbolic development", "expect": True},
    {"name": "neg_mghd_unrelated", "obligation": "O2-mghd",
     "text": "the development of the initial data is maximal", "expect": False},
    {"name": "neg_nonsense", "obligation": "O4-predictability-def",
     "text": "zzz qqq no such concept", "expect": False},
)

L0_STATEMENT_FIELDS = ("statement_exact",)
L0_SUBJECT_FIELDS = ("label",)
L1_TITLE_FIELDS = ("title",)
L1_EVIDENCE_FIELDS = ("evidence_excerpt", "elided_quote")
REG_TITLE_FIELDS = ("title",)
REG_EVIDENCE_FIELDS = ("verification.evidence",)
MAX_HITS_STORED = 25
QUOTE_PAD = 70


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", str(text)).strip().lower()


def flatten(obj, prefix=""):
    """Yield (field_path, string) for every string value in a JSON structure."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from flatten(v, f"{prefix}.{k}" if prefix else str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from flatten(v, f"{prefix}[{i}]")
    elif isinstance(obj, str):
        if obj.strip():
            yield prefix, obj
    elif obj is not None and not isinstance(obj, bool):
        yield prefix, str(obj)


def find_quote(text: str, match: re.Match) -> str:
    a = max(0, match.start() - QUOTE_PAD)
    b = min(len(text), match.end() + QUOTE_PAD)
    return ("..." if a > 0 else "") + text[a:b] + ("..." if b < len(text) else "")


def first_match(fields, regex):
    """fields: iterable of (field_path, text). Returns (field, quote) or None."""
    for field, text in fields:
        m = regex.search(norm(text))
        if m:
            return field, find_quote(text, m)
    return None


def has_record_identifier(row: dict) -> bool:
    if str(row.get("doi") or "").strip() or str(row.get("arxiv_id") or "").strip():
        return True
    loc = str(row.get("exact_locator") or row.get("url") or "")
    return bool(re.search(r"arxiv\.org/(abs|pdf)|doi\.org/10\.|(crossref|openalex)\.org/works/", loc, re.I))


def measured_pins():
    out = {}
    for rel in PINS:
        p = ROOT / rel
        out[rel] = sha256_file(p) if p.is_file() else None
    return out


def load_populations():
    with (ROOT / "ledger" / "theorems.jsonl").open(encoding="utf-8") as f:
        l0 = [json.loads(line) for line in f if line.strip()]
    with (ROOT / "ledger" / "citation_audit.csv").open(encoding="utf-8", newline="") as f:
        l1 = list(csv.DictReader(f))
    with (ROOT / "artifacts" / "literature" / "registry.jsonl").open(encoding="utf-8") as f:
        reg = [json.loads(line) for line in f if line.strip()]
    anchors_text = (ROOT / "artifacts" / "literature" / "FORMULATION_ANCHORS.md").read_text(encoding="utf-8")
    return l0, l1, reg, anchors_text


def census_row(population, row_id, grade, field, quote, ids):
    return {
        "population": population,
        "id": row_id,
        "grade": grade,
        "field": field,
        "anchor_grade": grade in ("statement", "subject", "title", "evidence"),
        "identifiers": ids,
        "quote": quote,
    }


def classify_l0(row, regex):
    fields = list(flatten(row))
    hit = first_match(fields, regex)
    if not hit:
        return None
    field, quote = hit
    if any(field == f for f in L0_STATEMENT_FIELDS):
        grade = "statement"
    elif any(field == f for f in L0_SUBJECT_FIELDS):
        grade = "subject"
    else:
        grade = "metadata"
    return census_row(
        "L0", row.get("theorem_id", "?"), grade, field, quote,
        {"source_ids": row.get("source_ids", []), "class_ids": row.get("class_ids", [])},
    )


def classify_l1(row, regex):
    fields = list(flatten(row))
    hit = first_match(fields, regex)
    if not hit:
        return None
    field, quote = hit
    if field in L1_TITLE_FIELDS:
        grade = "title"
    elif field in L1_EVIDENCE_FIELDS:
        grade = "evidence"
    else:
        grade = "metadata"
    anchor = grade in ("title", "evidence") and has_record_identifier(row)
    return census_row(
        "L1", row.get("citation_id", "?"), grade, field, quote,
        {"doi": row.get("doi") or None, "arxiv_id": row.get("arxiv_id") or None,
         "record_identifier": anchor, "class_mapping": row.get("class_mapping", "")},
    )


def classify_registry(row, regex):
    fields = list(flatten(row))
    hit = first_match(fields, regex)
    if not hit:
        return None
    field, quote = hit
    grade = "title" if field in REG_TITLE_FIELDS else ("evidence" if field in REG_EVIDENCE_FIELDS else "metadata")
    return census_row(
        "REG", row.get("source_id", "?"), grade, field, quote,
        {"doi": row.get("doi") or None, "arxiv_id": row.get("arxiv_id") or None,
         "record_identifier": has_record_identifier(row)},
    )


def run(stamp: str):
    declared = dict(PINS)
    measured = measured_pins()
    drift = [{"path": k, "declared": v, "measured": measured.get(k)}
             for k, v in declared.items() if measured.get(k) != v]

    l0, l1, reg, anchors_text = load_populations()

    controls = {"C0_pins_resolve": not drift, "pin_drift": drift}
    # C1 population sizes
    controls["C1_populations"] = {"l0": len(l0), "l1": len(l1), "registry": len(reg),
                                  "expect": {"l0": 62, "l1": 97, "registry": 97},
                                  "pass": len(l0) == 62 and len(l1) == 97 and len(reg) == 97}
    # C2 class taxonomy on L0
    bad_classes = sorted({c for r in l0 for c in r.get("class_ids", []) if c not in FROZEN_CLASSES})
    controls["C2_l0_class_taxonomy"] = {"violations": bad_classes, "pass": not bad_classes}
    # C3 positive control
    pc = re.compile(POSITIVE_CONTROL["regex"])
    pc_l0 = sum(1 for r in l0 if first_match(list(flatten(r)), pc))
    pc_l1 = sum(1 for r in l1 if first_match(list(flatten(r)), pc))
    controls["C3_positive_control"] = {
        "id": POSITIVE_CONTROL["id"], "l0_hits": pc_l0, "l1_hits": pc_l1,
        "min_l0": POSITIVE_CONTROL["min_l0"], "min_l1": POSITIVE_CONTROL["min_l1"],
        "pass": pc_l0 >= POSITIVE_CONTROL["min_l0"] and pc_l1 >= POSITIVE_CONTROL["min_l1"],
    }
    # C4 negative control + synthetic fixtures
    nc = re.compile(NEGATIVE_CONTROL["regex"])
    nc_hits = sum(1 for r in list(l0) + list(l1) + list(reg) if first_match(list(flatten(r)), nc))
    synth = []
    synth_pass = True
    for case in SYNTHETIC:
        rx = re.compile(next(o["regex"] for o in OBLIGATIONS if o["id"] == case["obligation"]))
        got = bool(rx.search(norm(case["text"])))
        ok = got == case["expect"]
        synth_pass = synth_pass and ok
        synth.append({"name": case["name"], "obligation": case["obligation"], "expect": case["expect"],
                      "got": got, "pass": ok})
    controls["C4_negative_and_synthetic"] = {"nonsense_hits": nc_hits, "synthetic": synth,
                                             "pass": nc_hits == 0 and synth_pass}
    # C5 read-only pre/post
    post = measured_pins()
    controls["C5_read_only"] = {"pass": post == measured, "post": post}

    obligations_out = []
    for ob in OBLIGATIONS:
        rx = re.compile(ob["regex"])
        l0_hits = [h for h in (classify_l0(r, rx) for r in l0) if h]
        l1_hits = [h for h in (classify_l1(r, rx) for r in l1) if h]
        reg_hits = [h for h in (classify_registry(r, rx) for r in reg) if h]
        anchors_text_hit = bool(rx.search(norm(anchors_text)))
        l0_anchor = [h for h in l0_hits if h["grade"] in ("statement", "subject")]
        l1_anchor = [h for h in l1_hits if h["anchor_grade"]]
        reg_anchor = [h for h in reg_hits if h["grade"] in ("title", "evidence")]
        obligations_out.append({
            "id": ob["id"],
            "concept": ob["concept"],
            "binds_f1_field": ob["f1_field"],
            "needed_for": ob["needed_for"],
            "bl11_item": ob["bl11_item"],
            "regex": ob["regex"],
            "l0": {"rows_hit": len(l0_hits), "anchor_grade": len(l0_anchor),
                   "row_ids": [h["id"] for h in l0_hits],
                   "anchor_ids": [h["id"] for h in l0_anchor],
                   "hits_stored": l0_hits[:MAX_HITS_STORED]},
            "l1": {"rows_hit": len(l1_hits), "anchor_grade": len(l1_anchor),
                   "row_ids": [h["id"] for h in l1_hits],
                   "anchor_ids": [h["id"] for h in l1_anchor],
                   "hits_stored": l1_hits[:MAX_HITS_STORED]},
            "registry": {"rows_hit": len(reg_hits), "anchor_grade": len(reg_anchor),
                         "row_ids": [h["id"] for h in reg_hits],
                         "anchor_ids": [h["id"] for h in reg_anchor],
                         "hits_stored": reg_hits[:MAX_HITS_STORED]},
            "anchors_doc_mentions_concept": anchors_text_hit,
            "anchor_found": bool(l0_anchor or l1_anchor or reg_anchor),
        })

    bl11 = []
    for item in sorted({o["bl11_item"] for o in OBLIGATIONS if o["bl11_item"]}):
        ids = [o["id"] for o in OBLIGATIONS if o["bl11_item"] == item]
        sel = [o for o in obligations_out if o["id"] in ids]
        l0_hits = sum(o["l0"]["rows_hit"] for o in sel)
        l1_hits = sum(o["l1"]["rows_hit"] for o in sel)
        l0_anchor = sum(o["l0"]["anchor_grade"] for o in sel)
        l1_anchor = sum(o["l1"]["anchor_grade"] for o in sel)
        bl11.append({
            "bl11_item": item, "obligation_ids": ids,
            "l0_rows_hit": l0_hits, "l1_rows_hit": l1_hits,
            "l0_anchor_grade": l0_anchor, "l1_anchor_grade": l1_anchor,
            "supports_lead_zero_hit_claim": (l0_hits == 0 and l1_hits == 0),
        })

    all_pass = all((v.get("pass", True) if isinstance(v, dict) else v)
                   for v in controls.values() if isinstance(v, (dict, bool)))
    report = {
        "task_id": "W048-F1-PROVENANCE-ANCHOR-CENSUS-01",
        "actor": "worker-048",
        "stamp": stamp,
        "class_id": "AF-WCC-VAC-GEN",
        "node_id": "F1",
        "gates": ["G-FORM", "G-LIT"],
        "read_only": True,
        "authority": ("worker evidence only; cannot set status=done, validation_status=passed or a gate "
                      "verdict; no canonical artifact written; negative-result measurement, not a "
                      "mathematics claim"),
        "question": ("Do the frozen L0 ledger (ledger/theorems.jsonl) and L1 citation audit "
                     "(ledger/citation_audit.csv) contain any anchor for the citation obligations "
                     "F1 declares unresolved in schemas/af_wcc_vacuum.yaml provenance?"),
        "predicate_source": "derived verbatim from the F1 obligation strings before the run; see PREREGISTRATION.json",
        "pins_declared": declared,
        "pins_measured": measured,
        "pin_drift": drift,
        "population": {"l0_rows": len(l0), "l1_rows": len(l1), "registry_rows": len(reg)},
        "obligations": obligations_out,
        "bl11_claim_tests": bl11,
        "controls": controls,
        "controls_all_pass": all_pass,
        "falsifier": ("Re-run census_f1_provenance.py --stamp <same> on byte-identical pinned inputs: this "
                      "census is falsified by (i) any pinned input measuring a different sha256; (ii) any "
                      "row/citation in the pinned populations that the pre-registered predicates miss but "
                      "that a careful reader identifies as an anchor for one of the eight obligations; "
                      "(iii) any hit reported here that a careful reader shows is not a hit under the "
                      "published regex; (iv) a determinism failure between two runs."),
        "not_claimed": ["gate verdict", "node status", "validation_status", "citation-support adjudication",
                        "canonical write", "network resolution", "mathematics claim"],
    }
    return report, all_pass, bool(drift)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--stamp", default="2026-09-12T00:00:00+08:00")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent / "report.json"))
    ap.add_argument("--census-tsv", default=str(Path(__file__).resolve().parent / "census.tsv"))
    ap.add_argument("--emit-prereg", action="store_true")
    args = ap.parse_args(argv)

    if args.emit_prereg:
        prereg = {
            "task_id": "W048-F1-PROVENANCE-ANCHOR-CENSUS-01",
            "actor": "worker-048",
            "class_id": "AF-WCC-VAC-GEN",
            "node_id": "F1",
            "gates": ["G-FORM", "G-LIT"],
            "frozen_at": args.stamp,
            "read_only": True,
            "question": ("Do the frozen L0 ledger and L1 citation audit contain any anchor for the "
                         "citation obligations F1 declares unresolved?"),
            "populations": {"L0": "ledger/theorems.jsonl (62 rows)",
                            "L1": "ledger/citation_audit.csv (97 rows)",
                            "REG": "artifacts/literature/registry.jsonl (97 rows)",
                            "DOC": "artifacts/literature/FORMULATION_ANCHORS.md (lead narrative, not an anchor)"},
            "pins": PINS,
            "predicates": [{"id": o["id"], "binds_f1_field": o["f1_field"],
                            "concept": o["concept"], "regex": o["regex"],
                            "bl11_item": o["bl11_item"]} for o in OBLIGATIONS],
            "grades": {
                "L0": "statement (statement_exact), subject (label), metadata (other fields)",
                "L1": "title, evidence (evidence_excerpt/elided_quote), metadata",
                "anchor_grade": "statement/subject for L0; title/evidence with a record identifier for L1/REG",
            },
            "controls": {"C0": "pins resolve", "C1": "population sizes",
                         "C2": "L0 class tokens within the four frozen classes",
                         "C3": f"positive control {POSITIVE_CONTROL['id']} >= {POSITIVE_CONTROL['min_l0']} L0 / "
                               f"{POSITIVE_CONTROL['min_l1']} L1",
                         "C4": "nonsense predicate 0 hits + 5 synthetic fixtures",
                         "C5": "read-only pre/post hash equality"},
            "stop_rule": "0.5 agent-hour or one complete report, whichever is first",
            "authority_boundary": "measurement only; no ruling, no gate verdict, no canonical write",
        }
        out = Path(__file__).resolve().parent / "PREREGISTRATION.json"
        out.write_text(json.dumps(prereg, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"wrote {out}")
        return 0

    report, all_pass, drift = run(args.stamp)
    Path(args.out).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    rows = []
    for ob in report["obligations"]:
        for pop in ("l0", "l1", "registry"):
            for h in ob[pop]["hits_stored"]:
                rows.append([ob["id"], h["population"], h["id"], h["grade"], str(h["anchor_grade"]),
                             h["field"], h["quote"].replace("\t", " ").replace("\n", " ")])
    with Path(args.census_tsv).open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        w.writerow(["obligation", "population", "row_id", "grade", "anchor_grade", "field", "quote"])
        w.writerows(rows)

    print(f"task={report['task_id']} stamp={args.stamp}")
    for ob in report["obligations"]:
        print(f"  {ob['id']:26s} L0 hits={ob['l0']['rows_hit']:3d} anchor={ob['l0']['anchor_grade']:3d} | "
              f"L1 hits={ob['l1']['rows_hit']:3d} anchor={ob['l1']['anchor_grade']:3d} | "
              f"REG hits={ob['registry']['rows_hit']:3d} | anchor_found={ob['anchor_found']}")
    print("bl11 tests:")
    for t in report["bl11_claim_tests"]:
        print(f"  {t['bl11_item'][:60]:60s} L0={t['l0_rows_hit']:3d} L1={t['l1_rows_hit']:3d} "
              f"zero_hit_claim={t['supports_lead_zero_hit_claim']}")
    print(f"controls_all_pass={report['controls_all_pass']}")
    if drift:
        return 3
    if not all_pass:
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
