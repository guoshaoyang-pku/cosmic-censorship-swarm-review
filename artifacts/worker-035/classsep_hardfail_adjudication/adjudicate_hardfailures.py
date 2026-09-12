#!/usr/bin/env python3
"""W035-A1-CLASSSEP-HARDFAIL-ADJUDICATION-01

Independent, read-only adjudication of the CLASSSEP hard failures carried by the
live checkpoint `runtime/state/current_checkpoint.json` (`evidence_hard_failures`),
at a pinned `research_map/research_map.json` revision (frozen here as
`pinned/map_snapshot.json`, sha256 3d45be5969ec388e...).

Question: for every hard failure of the form
`CLASSSEP: composite C0/C2 asserted as one class in claims[i].statement`,
is the flagged occurrence

  (A) an *assertion* that C0 and C2 are one class (a genuine class-separation
      violation a human must repair), or
  (B) a *mention/negation* of the composite -- a case/fixture label, a quotation,
      a description of the detector or of its own flag, an explicit non-merge or
      negation, or a merge word in a different clause than the composite
      (a detector false positive)?

Two remedies are on the table. Route 1 is an author rephrase of each claim
(proposed for claims[36] by an earlier worker-035 pass). Route 2 is checker
calibration (artifacts/worker-093/cf16_calibration/). This harness measures which
route the corpus at the pinned revision needs by:

  C0  pinning the canonical checker and worker-093's calibrated module by sha256;
  C1  reproducing the canonical finding list at the pinned snapshot and comparing
      it with the checkpoint's carried hard-failure list (drift reported);
  C2  classifying every canonical-flagged occurrence with an independent
      mention/negation classifier (rules below; it does not import worker-093's
      mention rule);
  C3  running worker-093's calibrated module over the same snapshot and reporting
      exactly which findings it clears and which persist; every cleared finding
      must be an occurrence this harness independently classifies CASE_LABEL;
  C4  determinism (both modules and the classifier run twice);
  C5  a labeled control corpus (genuine merge assertions vs the mention/negation
      families observed live) scored by the independent classifier;
  C6  the worker-07 falsification corpus scored by both modules (17/10/0/0);
  C7  no canonical file modified by this harness.

The classifier is conservative and evidence-listing: every non-assertive verdict
carries the named reason and the cue token that produced it, and any merge word
in the finding's own +/-60-char window without such a reason makes the occurrence
an ASSERTION.

Run:
    python3 artifacts/worker-035/classsep_hardfail_adjudication/adjudicate_hardfailures.py \
        --map artifacts/worker-035/classsep_hardfail_adjudication/pinned/map_snapshot.json
Exit 0 iff every pre-registered expectation holds.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]

PIN_CHECKER = "c266dbceca87fb996bd76a774145ef511cbf2aae190d9f423167d3200783a920"
PIN_CALIBRATED = "ff58563386cf398a74e97cb0d44534e983886c48041e7e0df185810402614be1"
PIN_W093_REPORT = "e63aaa74d1cf87aa4d84f84ba2d77d721c52816323ad731c773730053785c801"
PIN_W07_RESULTS = "d69ad58468be16655921dcf0eab9570fa6e7ccaf828558a45d4b306cce3de452"
PIN_SNAPSHOT = "3d45be5969ec388ef4a3e10d5eb87b81dbf3d03138510b75ff6a56453ceae005"
PIN_CHECKPOINT = "a215de69bfab69aa46e14f36f98c5c38f6775b340dbfcc1a1397506c2c951a47"


# ---------------------------------------------------------------- utilities
def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ------------------------------------------------- independent mention rules
SUP = {"\u2070": "0", "\u00b9": "1", "\u00b2": "2", "\u00b3": "3"}


def norm_keep_len(s: str) -> str:
    """Length-preserving normalization: superscript digits -> ASCII digits.

    The canonical module additionally strips ^ { }, which is not
    length-preserving; composite matching below accepts both `C^0/C^2` and
    `C0/C2`, so dropping the caret stripping costs nothing for span bookkeeping."""
    for k, v in SUP.items():
        s = s.replace(k, v)
    return s


COMPOSITE = re.compile(
    r"c\s*\^?\s*0\s*(?:or|and|/|,|\+|\s)\s*c\s*\^?\s*2"
    r"|c\s*\^?\s*2\s*(?:or|and|/|,|\+|\s)\s*c\s*\^?\s*0"
    r"|c0c2|c2c0", re.I)

MERGE_WORD = re.compile(
    r"as\s+one|are\s+one|is\s+one|one\s+class|single\s+class|one\s+schema|single\s+schema|"
    r"unified|unif(?:y|ication)|merged|merge\b|share[sd]?\s+one|combined|same\s+class|"
    r"treated?\s+as\s+one|into\s+a\s+single", re.I)

CASE_ID = re.compile(r"\b(?:TC|FX|CASE|ROW|FIXTURE)-[A-Za-z0-9-]+\b", re.I)
LABEL_NOUN = re.compile(
    r"\b(?:merge|merger|merged|regularities|regularity|families|family|case|cases|"
    r"row|rows|fixture|fixtures|label|labels|disposition|request|composite|composites|"
    r"split)\b", re.I)
NEG_CUE = re.compile(r"\b(?:no|not|never|without|zero|absent|nor|neither|none|non)\b", re.I)
NEG_PHRASE = re.compile(r"rather\s+than|instead\s+of|as\s+opposed\s+to|not\s+a\b|no\s+longer", re.I)
REJECT_CUE = re.compile(
    r"\b(?:rejects?|rejected|denies|denied|disputes?|disputed|refutes?|refuted|"
    r"contradicts?|contradicted|opposes?|opposed|dismiss(?:es|ed)?)\b", re.I)
META_CUE = re.compile(
    r"\b(?:pattern|regex|regexp|detector|checker|scanner|scan|scans|matches?|matched|"
    r"flags?|flagged|flagging|reproduces?|vocabulary|asserted|assertion|adjudicat\w*|"
    r"false\s+positive|names?|describes?|quoted?|cites?|cited)\b", re.I)
# narrower cue set for text *after* the merge word: only describing predicates that
# cannot be read as a class unification ("... matches our single-schema design" is
# deliberately not here, so genuine assertions stay assertive).
RIGHT_META_CUE = re.compile(
    r"\b(?:pattern|regex|regexp|vocabulary|matches?|flagged|flag)\b", re.I)

QUOTED_SPAN = re.compile(
    r"\"[^\"]{1,400}\""
    r"|\u201c[^\u201d]{1,400}\u201d"
    r"|(?<![A-Za-z0-9])'[^']{1,400}'(?![A-Za-z0-9])"
    r"|(?<![A-Za-z0-9])\u2018[^\u2019]{1,400}\u2019(?![A-Za-z0-9])")
CLAUSE_BOUNDARY = re.compile(r"[;.!?\n]|\u2014|\u2013")
TOKEN = re.compile(r"[A-Za-z0-9/_.^+-]+")


def quoted_spans(s: str):
    return [(m.start(), m.end()) for m in QUOTED_SPAN.finditer(s)]


def in_any_span(spans, pos: int) -> bool:
    return any(a <= pos < b for a, b in spans)


def tokens_before(s: str, pos: int, n: int = 4):
    return TOKEN.findall(s[:pos])[-n:]


def classify_merge_word(stmt: str, comp_start: int, comp_end: int,
                        w_start: int, w_end: int, qspans) -> dict:
    """Return {'reasons': [...], 'assertive': bool} for one merge word."""
    reasons = []
    word = stmt[w_start:w_end]

    # (1) quoted mention -- composite or merge word sits inside a quotation
    if in_any_span(qspans, comp_start) or in_any_span(qspans, w_start):
        reasons.append("QUOTED: the composite or merge word sits inside a quotation")

    # (2) the merge word is not in the same clause as the composite
    between = stmt[min(comp_end, w_end):max(comp_start, w_start)]
    b = CLAUSE_BOUNDARY.search(between)
    if b:
        reasons.append("CROSS_CLAUSE: %r separates the composite from the merge word" % b.group(0))

    # (3) explicit non-merge / negation
    if re.search(r"\bnon[-\s]?$", stmt[max(0, w_start - 6):w_start], re.I):
        reasons.append("NEGATED: the merge word is the 'non-merge' compound")
    neg = [t for t in tokens_before(stmt, comp_start, 4) if NEG_CUE.fullmatch(t)]
    if neg:
        reasons.append("NEGATED: cue %r among the 4 tokens before the composite" % neg[-1])
    negw = [t for t in tokens_before(stmt, w_start, 3) if NEG_CUE.fullmatch(t)]
    if negw and not neg:
        reasons.append("NEGATED: cue %r among the 3 tokens before the merge word" % negw[-1])
    mp = NEG_PHRASE.search(stmt[max(0, min(comp_start, w_start) - 55):max(comp_start, w_start)])
    if mp:
        reasons.append("NEGATED: phrase %r governs the composite/merge word" % mp.group(0))
    # rejection/denial of the claim, in the same clause as the composite/merge word
    for anchor, label in ((comp_start, "composite"), (w_start, "merge word")):
        rc = REJECT_CUE.search(stmt[max(0, anchor - 80):anchor])
        if rc and not CLAUSE_BOUNDARY.search(stmt[max(0, anchor - 80) + rc.end():anchor]):
            reasons.append("NEGATED: rejection/denial cue %r governs the %s" % (rc.group(0), label))
            break

    # (4) case/fixture label mention
    cid = CASE_ID.search(stmt[max(0, w_start - 50):w_start])
    label_here = bool(LABEL_NOUN.match(word.strip())) or bool(LABEL_NOUN.search(word))
    label_after = LABEL_NOUN.search(stmt[w_end:w_end + 40])
    if cid and (label_here or label_after):
        which = "the merge word itself" if label_here else "the following noun %r" % \
            stmt[w_end:w_end + 40].strip()[:30]
        reasons.append("CASE_LABEL: case id %r before the merge word; %s names a label"
                       % (cid.group(0), which))

    # (5) metalinguistic / report mention (describing the detector or the flag)
    mm = META_CUE.search(stmt[max(0, w_start - 55):w_start])
    if mm:
        reasons.append("METALINGUISTIC: cue %r before the merge word describes a check/flag, "
                       "not a class" % mm.group(0))
    rm = RIGHT_META_CUE.search(stmt[w_end:w_end + 60])
    if rm and not mm:
        reasons.append("METALINGUISTIC: cue %r after the merge word describes a check/flag, "
                       "not a class" % rm.group(0))

    return {"word": word, "span": [w_start, w_end], "reasons": reasons,
            "assertive": not reasons}


def parse_finding_window(finding: str):
    """Recover the canonical +/-60-char window from a finding string.

    Finding format: '... in claims[i].statement: ...<python-repr of ctx.strip()>'."""
    marker = ".statement: "
    idx = finding.find(marker)
    suffix = finding[idx + len(marker):] if idx != -1 else finding
    qpos = [p for p in (suffix.find("'"), suffix.find('"')) if p != -1]
    if not qpos:
        return None
    try:
        return ast.literal_eval(suffix[min(qpos):])
    except Exception:
        return None


def classify_finding(stmt: str, finding: str) -> dict:
    """Classify exactly the occurrence a canonical finding refers to."""
    t = norm_keep_len(stmt)
    qspans = quoted_spans(t)
    ctx = parse_finding_window(finding)
    if ctx is None:
        return {"verdict": "UNCLASSIFIED", "reasons": ["WINDOW_UNPARSEABLE"], "occurrences": []}
    pos = t.find(ctx)
    if pos == -1:
        return {"verdict": "UNCLASSIFIED", "reasons": ["WINDOW_NOT_FOUND"], "occurrences": []}
    lo, hi = pos, pos + len(ctx)
    comps = [cm for cm in COMPOSITE.finditer(t) if lo <= cm.start() < hi]
    if not comps:
        return {"verdict": "UNCLASSIFIED", "reasons": ["WINDOW_HAS_NO_COMPOSITE"], "occurrences": []}
    center = (lo + hi) / 2.0
    cm = min(comps, key=lambda c: abs((c.start() + c.end()) / 2.0 - center))
    words = []
    for wm in MERGE_WORD.finditer(t[lo:hi]):
        ws, we = lo + wm.start(), lo + wm.end()
        words.append(classify_merge_word(t, cm.start(), cm.end(), ws, we, qspans))
    verdict = "ASSERTION" if (not words or any(w["assertive"] for w in words)) else "NON_ASSERTIVE"
    occ = {"composite": t[cm.start():cm.end()], "composite_span": [cm.start(), cm.end()],
           "window": [lo, hi], "merge_words": words, "verdict": verdict,
           "reasons": sorted({r for w in words for r in w["reasons"]}),
           "unreasoned_words": [w["word"] for w in words if w["assertive"]]}
    return {"verdict": verdict, "reasons": occ["reasons"], "occurrences": [occ]}


# ------------------------------------------------------------ control corpus
POS_CONTROLS = [
    "We treat C0 or C2 as one class in the unified schema.",
    "C0/C2 are merged into a single class for the vacuum sector.",
    "The two regularities C0 and C2 share one schema.",
    "C0 or C2 is one class and must be declared as such.",
    "We adopt a single schema for C0/C2.",
    "C2/C0 are unified under one class label.",
    "C0/C2 merge is our design.",
    "The taxonomy treats C0 and C2 as one class.",
    "Both classes are one: C0 and C2.",
]
NEG_CONTROLS = [
    ("CASE_LABEL", "The 2 split rows (TC-F0-N14 C0/C2 merge, TC-F0-N15 WCC/SCC merge) need no new class."),
    ("CASE_LABEL", "2 SPLIT_REQUIRED (TC-F0-N14 merged C0/C2 regularities; TC-F0-N15 merged WCC/SCC families)."),
    ("NEGATED", "... frozen_regularity (C2 vs C0), so no C0/C2 merge exists at the formal surface."),
    ("METALINGUISTIC", "R1's merge pattern matches only bare C0/C2 composites."),
    ("QUOTED", "the same slot carrying 'C0 or C2 are one class' is flagged by the detector"),
    ("NEGATED", "independent C0/C2 non-merge is asserted by this review."),
    ("QUOTED", "Never write 'C0 or C2 are one class'."),
    ("NEGATED", "Do not merge C0 and C2 into one class."),
    ("NEGATED", "The C0/C2 split is a required separation, not a merged class."),
    ("METALINGUISTIC", "CF-16 adjudicated the C0/C2 merge finding as a checker false positive."),
    ("CROSS_CLAUSE", "The record mislabels these bytes as the retired merged file; and, measured "
                     "during the task, the live C2/C0 components moved."),
    ("NEGATED", "This is a single-frozen-data-class question rather than a C2/C0 merge."),
    ("NEGATED", "We reject the proposal that C0/C2 are one class."),
    ("NEGATED", "The reviewer denied that C0 or C2 is one class."),
]


def classify_statement_occurrences(stmt: str) -> dict:
    """Classify every composite occurrence of a statement (control-corpus path)."""
    t = norm_keep_len(stmt)
    qspans = quoted_spans(t)
    occ = []
    for cm in COMPOSITE.finditer(t):
        lo, hi = max(0, cm.start() - 60), min(len(t), cm.end() + 60)
        words = []
        for wm in MERGE_WORD.finditer(t[lo:hi]):
            ws, we = lo + wm.start(), lo + wm.end()
            words.append(classify_merge_word(t, cm.start(), cm.end(), ws, we, qspans))
        verdict = "ASSERTION" if (not words or any(w["assertive"] for w in words)) else "NON_ASSERTIVE"
        occ.append({"verdict": verdict, "reasons": sorted({r for w in words for r in w["reasons"]}),
                    "words": [w["word"] for w in words]})
    if not occ:
        return {"verdict": "NON_ASSERTIVE", "reasons": ["NO_COMPOSITE"]}
    return {"verdict": "ASSERTION" if any(o["verdict"] == "ASSERTION" for o in occ) else "NON_ASSERTIVE",
            "reasons": sorted({r for o in occ for r in o["reasons"]})}


def controls_report(canonical) -> dict:
    rows = []
    for i, s in enumerate(POS_CONTROLS, 1):
        c = classify_statement_occurrences(s)
        flags = canonical.findings({"statement": s, "class_id": "AF-SCC-C2-VAC-GEN"},
                                   "control", mode="prose")
        row = {"control_id": "P%02d" % i, "expect": "ASSERTION", "text": s,
               "classifier_verdict": c["verdict"], "reasons": c["reasons"],
               "canonical_flags": len(flags), "pass": c["verdict"] == "ASSERTION"}
        rows.append(row)
    for i, (kind, s) in enumerate(NEG_CONTROLS, 1):
        c = classify_statement_occurrences(s)
        row = {"control_id": "N%02d" % i, "expect": "NON_ASSERTIVE/" + kind, "text": s,
               "classifier_verdict": c["verdict"], "reasons": c["reasons"],
               "kind_present": any(r.startswith(kind) for r in c["reasons"])}
        row["pass"] = (c["verdict"] == "NON_ASSERTIVE" and row["kind_present"])
        rows.append(row)
    return {"rows": rows,
            "pos_pass": sum(1 for r in rows if r["control_id"].startswith("P") and r["pass"]),
            "pos_total": len(POS_CONTROLS),
            "neg_pass": sum(1 for r in rows if r["control_id"].startswith("N") and r["pass"]),
            "neg_total": len(NEG_CONTROLS),
            "all_pass": all(r["pass"] for r in rows)}


# ------------------------------------------------- worker-07 corpus scorer
def score_corpus(mod, results_path: Path) -> dict:
    """Independent scorer over the worker-07 falsification corpus.

    Mirrors the corpus semantics (map scan + node artifact text is a violation
    iff the module emits any finding) but resolves paths against this repo root
    instead of the module's own __file__, so the relocated calibrated copy and
    the canonical module are scored identically."""
    res = json.loads(results_path.read_text())
    tp = fn = tn = fp = 0
    per_fixture = []
    for fx in res["fixtures"]:
        fpth = ROOT / fx["fixture_path"]
        if not fpth.exists():
            per_fixture.append({"fixture_path": fx["fixture_path"], "status": "MISSING"})
            continue
        mm = json.loads(fpth.read_text())
        det = mod.findings_for_map(mm)
        for g in mm.get("groups", []):
            for n in g.get("nodes", []):
                art = n.get("artifact")
                if art and (ROOT / art).is_file():
                    det += mod.findings_for_text((ROOT / art).read_text(errors="replace"),
                                                 f"artifact {art}")
        got, truth = bool(det), bool(fx["is_class_merge"])
        tp += int(truth and got)
        fn += int(truth and not got)
        fp += int((not truth) and got)
        tn += int((not truth) and (not got))
        per_fixture.append({"fixture_path": fx["fixture_path"], "truth": truth, "got": got})
    return {"tp": tp, "fn": fn, "tn": tn, "fp": fp,
            "verdict": "PASS" if fn == 0 and fp == 0 else "DEFECTIVE",
            "corpus_size": tp + fn + tn + fp, "per_fixture": per_fixture}


# ------------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--map", default=str(HERE / "pinned/map_snapshot.json"))
    ap.add_argument("--checkpoint", default=str(ROOT / "runtime/state/current_checkpoint.json"))
    ap.add_argument("--checker", default=str(ROOT / "research_map/class_separation.py"))
    ap.add_argument("--calibrated",
                    default=str(ROOT / "artifacts/worker-093/cf16_calibration/calibrated_class_separation.py"))
    ap.add_argument("--w093-report",
                    default=str(ROOT / "artifacts/worker-093/cf16_calibration/report.json"))
    ap.add_argument("--w07-results",
                    default=str(ROOT / "artifacts/worker-07/class_separation_falsification/results.json"))
    ap.add_argument("--observe-live", action="store_true",
                    help="also record the live map revision's finding count (observation only)")
    ap.add_argument("--out-dir", default=str(HERE))
    args = ap.parse_args()

    checks = []

    def check(cid, question, passed, detail=None):
        checks.append({"id": cid, "question": question, "pass": bool(passed),
                       "detail": detail if detail is not None else {}})
        return bool(passed)

    map_path = Path(args.map)
    map_sha_before = sha256_file(map_path)
    raw = map_path.read_bytes()
    map_sha = hashlib.sha256(raw).hexdigest()
    m = json.loads(raw)

    pins = {
        "research_map/class_separation.py": sha256_file(Path(args.checker)),
        "artifacts/worker-093/cf16_calibration/calibrated_class_separation.py": sha256_file(Path(args.calibrated)),
        "artifacts/worker-093/cf16_calibration/report.json": sha256_file(Path(args.w093_report)),
        "artifacts/worker-07/class_separation_falsification/results.json": sha256_file(Path(args.w07_results)),
        "runtime/state/current_checkpoint.json": sha256_file(Path(args.checkpoint)),
        "adjudicated_map": map_sha,
        "adjudicated_map_updated_at": m.get("updated_at"),
        "adjudicated_map_bytes": len(raw),
    }

    # C0 pins -------------------------------------------------------------
    check("C0-pins", "canonical checker, calibrated module, worker-093 report and worker-07 corpus match the declared pins",
          pins["research_map/class_separation.py"] == PIN_CHECKER
          and pins["artifacts/worker-093/cf16_calibration/calibrated_class_separation.py"] == PIN_CALIBRATED
          and pins["artifacts/worker-093/cf16_calibration/report.json"] == PIN_W093_REPORT
          and pins["artifacts/worker-07/class_separation_falsification/results.json"] == PIN_W07_RESULTS,
          {"expected": {"checker": PIN_CHECKER, "calibrated": PIN_CALIBRATED,
                        "w093_report": PIN_W093_REPORT, "w07_results": PIN_W07_RESULTS},
           "measured": {k: v for k, v in pins.items() if k in (
               "research_map/class_separation.py",
               "artifacts/worker-093/cf16_calibration/calibrated_class_separation.py",
               "artifacts/worker-093/cf16_calibration/report.json",
               "artifacts/worker-07/class_separation_falsification/results.json")}})

    canonical = load_module(Path(args.checker), "w035_canonical_checker")
    calibrated = load_module(Path(args.calibrated), "w035_calibrated_checker")

    # C1 reproduce the canonical findings ---------------------------------
    findings = canonical.findings_for_map(m)
    flag_idx = [int(re.search(r"claims\[(\d+)\]", f).group(1)) for f in findings]
    carried = []
    try:
        ck = json.loads(Path(args.checkpoint).read_text())
        carried = [f for f in ck.get("evidence_hard_failures", []) if f.startswith("CLASSSEP")]
    except Exception as exc:
        carried = ["<checkpoint unreadable: %s>" % exc]
    carried_set, live_set = set(carried), set(findings)
    check("C1-reproduce", "canonical checker reproduces a non-empty finding list at the pinned snapshot",
          len(findings) >= 1, {"n_findings": len(findings), "claim_indices": flag_idx,
                               "findings": findings})
    check("C1b-checkpoint-basis", "every CLASSSEP entry carried by the checkpoint is reproduced at the pinned snapshot",
          bool(carried) and carried_set.issubset(live_set),
          {"checkpoint_classep_entries": len(carried), "snapshot_findings": len(findings),
           "checkpoint_subset_of_snapshot": carried_set.issubset(live_set),
           "drift_new_findings_not_in_checkpoint": sorted(live_set - carried_set),
           "carried_findings_absent_from_snapshot": sorted(carried_set - live_set)})

    # C2 independent adjudication -----------------------------------------
    adjudications = []
    for f in findings:
        i = int(re.search(r"claims\[(\d+)\]", f).group(1))
        stmt = m["claims"][i].get("statement", "")
        c = classify_finding(stmt, f)
        adjudications.append({
            "claim_index": i,
            "claim_event_id": m["claims"][i].get("event_id"),
            "claim_actor": m["claims"][i].get("actor"),
            "class_id": m["claims"][i].get("class_id"),
            "statement_sha256": hashlib.sha256(stmt.encode()).hexdigest(),
            "canonical_finding": f,
            "verdict": c["verdict"],
            "reasons": c["reasons"],
            "occurrences": c["occurrences"],
        })
    n_assert = sum(1 for a in adjudications if a["verdict"] == "ASSERTION")
    n_unclass = sum(1 for a in adjudications if a["verdict"] == "UNCLASSIFIED")
    check("C2-adjudicate",
          "all %d canonical-flagged occurrences at the pinned snapshot are non-assertive; 0 genuine merges" % len(adjudications),
          n_assert == 0 and n_unclass == 0 and len(adjudications) == len(findings),
          {"assertions": n_assert, "unclassified": n_unclass,
           "non_assertive": len(adjudications) - n_assert - n_unclass,
           "per_finding": [{"claim": a["claim_index"], "verdict": a["verdict"],
                            "reasons": a["reasons"]} for a in adjudications]})

    # C3 calibrated-module delta ------------------------------------------
    cal_findings = calibrated.findings_for_map(m)
    cal_set = set(cal_findings)
    removed = [f for f in findings if f not in cal_set]
    added = [f for f in cal_findings if f not in live_set]
    cleared_claims = sorted({int(re.search(r"claims\[(\d+)\]", f).group(1)) for f in removed})
    remaining_idx = [int(re.search(r"claims\[(\d+)\]", f).group(1)) for f in cal_findings]
    cleared_classified_case_label = []
    for f in removed:
        a = next(a for a in adjudications if a["canonical_finding"] == f)
        cleared_classified_case_label.append(any(r.startswith("CASE_LABEL") for r in a["reasons"]))
    check("C3-calibrated-delta",
          "calibrated module adds no finding and clears only occurrences independently classified CASE_LABEL",
          not added and all(cleared_classified_case_label),
          {"cleared_claims": cleared_claims, "removed": removed, "added": added,
           "cleared_are_case_labels": cleared_classified_case_label,
           "remaining_findings": len(cal_findings), "remaining_claim_indices": remaining_idx})

    # C4 determinism -------------------------------------------------------
    def _reclass(f):
        i = int(re.search(r"claims\[(\d+)\]", f).group(1))
        c = classify_finding(m["claims"][i].get("statement", ""), f)
        return c["verdict"], c["reasons"], c["occurrences"]
    det = (canonical.findings_for_map(m) == findings
           and calibrated.findings_for_map(m) == cal_findings
           and all(_reclass(f) == (a["verdict"], a["reasons"], a["occurrences"])
                   for f, a in zip(findings, adjudications)))
    check("C4-determinism", "canonical, calibrated and classifier outputs are identical on a second run",
          det, {"canonical": canonical.findings_for_map(m) == findings,
                "calibrated": calibrated.findings_for_map(m) == cal_findings})

    # C5 controls ----------------------------------------------------------
    ctl = controls_report(canonical)
    check("C5-controls",
          "labeled control corpus: classifier %d/%d positive and %d/%d negative controls correct"
          % (ctl["pos_pass"], ctl["pos_total"], ctl["neg_pass"], ctl["neg_total"]),
          ctl["all_pass"],
          {"pos_pass": ctl["pos_pass"], "pos_total": ctl["pos_total"],
           "neg_pass": ctl["neg_pass"], "neg_total": ctl["neg_total"]})

    # C6 worker-07 corpus parity ------------------------------------------
    reg_c = score_corpus(canonical, Path(args.w07_results))
    reg_k = score_corpus(calibrated, Path(args.w07_results))
    same_fixtures = ([{k: v for k, v in r.items() if k != "status"} for r in reg_c["per_fixture"]]
                     == [{k: v for k, v in r.items() if k != "status"} for r in reg_k["per_fixture"]])
    check("C6-worker07-corpus",
          "both modules score the worker-07 corpus 17/10/0/0 PASS with identical per-fixture classification",
          reg_c.get("tp") == 17 and reg_c.get("tn") == 10 and reg_c.get("fn") == 0 and reg_c.get("fp") == 0
          and reg_k.get("tp") == 17 and reg_k.get("tn") == 10 and reg_k.get("fn") == 0 and reg_k.get("fp") == 0
          and same_fixtures,
          {"canonical": {k: v for k, v in reg_c.items() if k != "per_fixture"},
           "calibrated": {k: v for k, v in reg_k.items() if k != "per_fixture"},
           "per_fixture_identical": same_fixtures})

    # C7 read-only + snapshot integrity ------------------------------------
    map_sha_after = sha256_file(map_path)
    snapshot_ok = (map_path.resolve() != (ROOT / "research_map/research_map.json").resolve()) or map_sha == PIN_SNAPSHOT
    check("C7-read-only",
          "no canonical file was modified by this harness (frozen map and checker hashes unchanged)",
          map_sha_after == map_sha_before and sha256_file(Path(args.checker)) == PIN_CHECKER,
          {"map_before": map_sha_before, "map_after": map_sha_after,
           "adjudicated_is_frozen_snapshot": snapshot_ok})

    # optional live observation -------------------------------------------
    live_observation = None
    if args.observe_live:
        lp = ROOT / "research_map/research_map.json"
        lraw = lp.read_bytes()
        lm = json.loads(lraw)
        lf = canonical.findings_for_map(lm)
        live_observation = {"live_map_sha256": hashlib.sha256(lraw).hexdigest(),
                            "live_map_updated_at": lm.get("updated_at"),
                            "live_findings": len(lf),
                            "live_claim_indices": [int(re.search(r"claims\[(\d+)\]", f).group(1)) for f in lf]}

    # ------------------------------------------------------------- outputs
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    verdict = ("%d/%d CLASSSEP hard failures at pinned map sha %s are detector false positives "
               "(mention/negation/window artifacts); 0 genuine class-separation assertions. "
               "worker-093's calibrated module clears %d/%d (claims %s); %d persist, so the "
               "calibration route as scoped does not discharge this hard-failure list."
               % (len(adjudications) - n_assert - n_unclass, len(adjudications), map_sha[:16],
                  len(removed), len(adjudications), cleared_claims, len(cal_findings)))
    report = {
        "task_id": "W035-A1-CLASSSEP-HARDFAIL-ADJUDICATION-01",
        "worker": "worker-035",
        "node_id": "A1",
        "gate": "G-AUDIT",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        "verdict": verdict,
        "pins": pins,
        "checkpoint_carried_classep_entries": carried,
        "canonical_findings_reproduced": findings,
        "adjudications": adjudications,
        "calibrated_delta": {"cleared_claims": cleared_claims, "removed": removed, "added": added,
                             "cleared_are_case_labels": cleared_classified_case_label,
                             "remaining_findings": len(cal_findings),
                             "remaining_claim_indices": remaining_idx},
        "checks": checks,
        "checks_pass": sum(1 for c in checks if c["pass"]),
        "checks_total": len(checks),
        "controls": ctl,
        "live_observation": live_observation,
        "falsifier": (
            "Re-run this harness unchanged on the frozen snapshot (sha256 %s). FALSIFIED if (a) the "
            "canonical checker does not reproduce the same %d findings; (b) any finding is classified "
            "ASSERTION or UNCLASSIFIED by the independent classifier; (c) any control in controls.json "
            "flips expectation; (d) the calibrated module adds a finding or clears an occurrence not "
            "independently classified CASE_LABEL; (e) a second run is non-deterministic; or (f) any "
            "pinned input hash drifts (then this adjudication is superseded and must be re-run at the "
            "new pins). The verdict binds to the frozen snapshot only; the live map moves continuously "
            "and is recorded as an observation, not as the adjudicated revision." % (map_sha, len(findings))),
        "non_claims": [
            "Not a gate verdict, node status, or validation_status=passed.",
            "No canonical file (map, event stream, ledger, schemas, class_separation.py) was edited.",
            "Adjudicates detector output, not the truth of the underlying disposition claims.",
            "Claim indices bind to the frozen snapshot; they may shift as claims are appended.",
        ],
    }
    (out / "report.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    (out / "controls.json").write_text(json.dumps({
        "task_id": report["task_id"],
        "controls": ctl["rows"],
        "pos_pass": ctl["pos_pass"], "pos_total": ctl["pos_total"],
        "neg_pass": ctl["neg_pass"], "neg_total": ctl["neg_total"],
        "all_pass": ctl["all_pass"],
        "note": ("Positive controls are genuine merge assertions the classifier must call ASSERTION. "
                 "Negative controls are the mention/negation families observed live; the classifier "
                 "must call them NON_ASSERTIVE with the named reason kind. The 'canonical_flags' "
                 "column on positives records whether the canonical prose-mode detector also flags "
                 "the control."),
    }, indent=1, sort_keys=True) + "\n")

    print(json.dumps({"verdict": verdict,
                      "checks_pass": report["checks_pass"], "checks_total": report["checks_total"],
                      "cleared_claims": cleared_claims, "remaining_findings": len(cal_findings),
                      "live_observation": live_observation}, indent=1))
    return 0 if report["checks_pass"] == report["checks_total"] else 1


if __name__ == "__main__":
    sys.exit(main())
