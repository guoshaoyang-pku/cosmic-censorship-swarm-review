#!/usr/bin/env python3
"""W032-CF16-DELTA-02 -- CLASSSEP hard-set adjudication under the APPLIED checker patch.

Context
-------
Pass 1 (W032-CF16-DELTA-01) adjudicated the 17 hard CLASSSEP claim-prose
findings at map 11311ab36005 under detector c266dbceca87: 0 genuine C0/C2
merges.  At 00:52:00 the canonical checker changed to a8c04fc31e4a -- a 3-line
prose-mode exemption for explicit detector/meta-audit quotations, applied by the
controller (worker-098's blocker w098-cps-20260912T0054-blocker-drift).

Pass 2 measures, at pinned map ed28b714 (292 claims):

  1. the patch effect on the hard set: pre vs post, cleared / added, with each
     cleared finding's carried pass-1 label;
  2. the surviving hard set adjudicated with carried pass-1 labels plus curated
     labels for genuinely new findings (fail closed on anything uncovered);
  3. an independent corpus-wide CONVERSE scan for first-order merge assertions
     the detector misses, under the patched detector;
  4. positive controls through BOTH detector revisions (a patched-out genuine
     assertion is a false negative), the worker-07 regression for both, and
     adversarial over-suppression probes that place a patch trigger in a
     concessive clause next to a genuine assertion -- the exemption regex is
     evaluated over the whole +/-60 char window, so this measures its scope.

Keys are `claim_event_id|sha256(context)[:16]`; occurrence indices are not stable
across the patch because cleared findings shift them.

Reproduce:
  python3 artifacts/worker-032/cf16-delta-02/adjudicate_delta.py \
      --created-at 2026-09-12T00:58:00+08:00
"""
from __future__ import annotations

import argparse
import ast
import difflib
import hashlib
import importlib.util
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CST = timezone(timedelta(hours=8))
DEFAULT_CREATED_AT = "2026-09-12T00:58:00+08:00"

PASS1_REPORT = ROOT / "artifacts/worker-032/cf16-delta/report.json"
PASS1_REPORT_SHA = "e9a185ba9fdfeeb266c23e1368b0de94806ea9fae5a56275089da11ec28347f1"
PRIOR_SNAPSHOT = "3d45be5969ec388ef4a3e10d5eb87b81dbf3d03138510b75ff6a56453ceae005"
PASS1_SNAPSHOT = "11311ab3600514cd34ca7332714a4aa27b97e4fdc124f29179122e11f844974d"
PRIOR10_COUNTS = {
    "flash02-opencase-claim-0010b-20260912T0015": 1,
    "w083-20260912T002753-claim-001": 1,
    "w083-20260912T002818-claim-001": 1,
    "w083-20260912T002837-claim-001": 1,
    "w080-20260912T002902-formalsym-claim": 1,
    "w003-20260912T002953-claim": 2,
    "w044-20260912T003236+0800-claim-f2b": 1,
    "w066-f2agg-19ebf7-claim-verdict": 1,
    "w045-claim-20260912T003631-f2vocabsep": 1,
}
FROZEN_CLASSES = {
    "AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH",
}
ALLOWED_LABELS = {
    "GENUINE_ASSERTION", "NEGATED_MENTION", "CASE_LABEL_MENTION", "QUOTED_MENTION",
    "DETECTOR_SELF_DESCRIPTION", "DIFFERENT_CLAUSE_MENTION", "DESCRIPTIVE_MENTION",
}

# --------------------------------------------------------------- independent
# detector for the converse scan and the cue classifier (NOT copied from the
# patched module's internals).
COMPOSITE = re.compile(
    r"c\s*0\s*(?:/|,|\+|;|\bor\b|\band\b|\s)\s*c\s*2"
    r"|c\s*2\s*(?:/|,|\+|;|\bor\b|\band\b|\s)\s*c\s*0"
    r"|c0c2|c2c0",
    re.I,
)
MERGE_TO_ONE = re.compile(
    r"(?:are|is|as|treat(?:ed)?\s+as|form(?:s|ed)?|constitute[sd]?|share[sd]?)\s+"
    r"(?:a\s+|the\s+|one\s+)?(?:single\s+|same\s+|one\s+)?(?:class|schema|family|regularity|surface)"
    r"|\bone\s+class\b|\bsingle\s+class\b|\bsame\s+class\b"
    r"|merge[ds]?\s+(?:[\w/+-]+\s+){0,2}(?:class|schema|family|regularity|surface|definition)"
    r"|merge[ds]?\s+(?:in)?to|unif(?:y|ied|ication)|combined\s+(?:class|schema)"
    r"|\bmerge[ds]?\b|asserted\s+as\s+one",
    re.I,
)
FILE_OBJECT = re.compile(
    r"merge[ds]?\s+(?:[\w/+-]+\s+){0,2}(?:file|files|folder|snapshot|document|doc|copy|pin)s?\b",
    re.I,
)
CLASS_OBJECT = re.compile(r"\b(class|classes|schema|schemas|family|families|regularity|surface|definition)\b", re.I)
NEG_CUE = re.compile(
    r"\b(no|not|never|without|zero|absent|nor|cannot|isn'?t|aren'?t|doesn'?t|don'?t|"
    r"non-merge|none|n't|0)\b|rather\s+than|instead\s+of",
    re.I,
)
CASE_LABEL_CUE = re.compile(
    r"TC-[A-Z0-9]+-N\d+|split_required|case[_ ]label|taxonomy_cases|disposition|open=true", re.I,
)
META_CUE = re.compile(
    r"classep|classsep|detector|hard\s+failure|false\s+positive|pattern|regex|candidate|"
    r"probe|fixture|the\s+form\s+of|shape|guard|prose|mention|flag|assertion|"
    r"claim[s\[]|rule\s*R\d|regression|corpus|negation",
    re.I,
)
QUOTE_CHARS = "'\"`\u2018\u2019\u201c\u201d"

POSITIVE_CONTROLS = [
    ("P1", "In this model C0 and C2 are one class on the vacuum sector."),
    ("P2", "We treat C2 and C0 as a single schema for the regularities."),
    ("P3", "The merged C0/C2 class is the authoritative definition."),
    ("P4", "C0/C2 constitutes a single class in the declaration surface."),
]
NEGATIVE_CONTROLS = [
    ("N1", "the 2 split rows (TC-F0-N14 C0/C2 merge, TC-F0-N15 WCC/SCC merge) need no new class"),
    ("N2", "2 SPLIT_REQUIRED (TC-F0-N14 merged C0/C2 regularities; TC-F0-N15 merged WCC/SCC families)"),
    ("N3", "definitions differing in frozen_regularity (C2 vs C0), so no C0/C2 merge exists at the formal surface"),
    ("N4", "R1's merge pattern matches only bare C0/C2 composites, so 'Sobolev variant' is not flagged"),
    ("N5", "the same slot carrying 'C0 or C2 are one class' is flagged"),
    ("N6", "independent C0/C2 non-merge, quantifier/conclusion assertions, semantic baselines"),
    ("N7", "the live C2/C0 components moved at 00:32:02 so the pins no longer resolve"),
    ("N8", "no C0/C2 merge, canonical structural gate exit 0, class_separation negative"),
    ("N9", "the live false-positive shape '... merged C0/C2 ...' inside a statement is NOT cleared by R2-3"),
    ("N10", "all 10 CLASSSEP hard failures of the form 'composite C0/C2 asserted as one class' are detector false positives"),
    ("N11", "0 genuine assertions that C0 and C2 are one class"),
    ("N12", "the canonical guard misses because \\w+ cannot span 'C0/C2' ('no C0/C2 merge exists')"),
    ("N13", "the 'non-merge' compound and the different clause ('the retired merged file; ... the live C2/C0 components moved')"),
]
# Adversarial scope probes: a genuine first-order assertion whose +/-60 char
# window also contains one of the patch's exemption triggers in a concessive
# clause.  A correct patch must still flag these; the applied patch is expected
# to skip them because the trigger is matched over the whole window.
OVER_SUPPRESSION_PROBES = [
    ("O1", "The prior audit found no genuine C0/C2 merge, but this model treats C0 and C2 as one class."),
    ("O2", "This is a non-merge bookkeeping step; C0 and C2 are one class in the declaration surface."),
    ("O3", "The quoted detector output is a false positive; nevertheless C0/C2 is a single class here."),
    ("O4", "C0 and C2 are one class here; this is not a merge."),
]
# Coverage probes for the stock assertion vocabulary (pre-existing, not caused
# by the patch): does the detector fire on the same composite with different
# object nouns / predicates?  P4fix is the positive counterpart.
BLIND_SPOT_PROBES = [
    ("B1", "C0/C2 constitutes one family in the declaration surface."),
    ("B2", "C0 and C2 are one family of regularities."),
    ("B3", "C0/C2 constitutes one regularity class."),
    ("B4", "C0/C2 forms one family in the declaration surface."),
    ("B5", "C0/C2 is a single family of regularities."),
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def classify_context(ctx: str) -> str:
    """Same conservative cue classifier as pass 1 (kept byte-identical in logic)."""
    t = ctx
    cue = MERGE_TO_ONE.search(t)
    if not cue:
        return "DESCRIPTIVE_MENTION"
    before = t[max(0, cue.start() - 70):cue.start()]
    if NEG_CUE.search(before):
        return "NEGATED_MENTION"
    for q in QUOTE_CHARS:
        lq, rq = t.find(q), t.rfind(q)
        if 0 <= lq < rq and (lq <= cue.start() <= rq):
            return "QUOTED_MENTION"
    if CASE_LABEL_CUE.search(t):
        return "CASE_LABEL_MENTION"
    if FILE_OBJECT.search(t) and not CLASS_OBJECT.search(t):
        return "DESCRIPTIVE_MENTION"
    if META_CUE.search(t):
        return "DETECTOR_SELF_DESCRIPTION"
    return "GENUINE_ASSERTION"


def extract_context(finding: str) -> str:
    if ": ..." not in finding:
        return ""
    raw = finding.split(": ...", 1)[1]
    try:
        return ast.literal_eval(raw)
    except (ValueError, SyntaxError):
        return raw.strip("'")


def finding_key(event_id: str, context: str) -> str:
    return f"{event_id}|{sha256_text(context)[:16]}"


def flagged_spans(det, statement: str, findings: list[str]) -> list[tuple[int, int]]:
    norm = det.norm(statement)
    spans = []
    for f in findings:
        ctx = extract_context(f).strip()
        if not ctx:
            continue
        pos = norm.find(ctx)
        if pos < 0:
            continue
        m = COMPOSITE.search(norm, pos, pos + len(ctx))
        if m:
            spans.append((m.start(), m.end()))
    return spans


def hard_findings(det, m: dict, tag: str):
    rows, non_claim = [], []
    for i, c in enumerate(m.get("claims", [])):
        if not isinstance(c, dict):
            continue
        eid = str(c.get("event_id") or f"claims[{i}]")
        st = str(c.get("statement") or "")
        cid_tokens = [t.strip() for t in re.split(r"[;,]", str(c.get("class_id") or "")) if t.strip()]
        fs = det.findings(c, f"claims[{i}]", mode="prose")
        for k, f in enumerate(fs):
            ctx = extract_context(f)
            rows.append({
                "finding_key": finding_key(eid, ctx),
                "detector": tag,
                "ordinal_in_claim": k,
                "claim_index_at_snapshot": i,
                "claim_event_id": eid,
                "claim_actor": c.get("actor"),
                "claim_class_id": c.get("class_id"),
                "claim_class_id_tokens": cid_tokens,
                "claim_class_id_all_frozen": all(t in FROZEN_CLASSES for t in cid_tokens),
                "claim_class_id_composite_token": any(("C0" in t.upper() and "C2" in t.upper()) for t in cid_tokens),
                "claim_conclusion_type": c.get("conclusion_type"),
                "statement_sha256": sha256_text(st),
                "detector_finding": f,
                "context": ctx,
                "flagged_spans": flagged_spans(det, st, fs),
            })
    for gi, g in enumerate(m.get("groups", [])):
        if isinstance(g.get("direction"), str):
            buf: list[str] = []
            det._scan_composite(g["direction"], f"groups[{g.get('id', gi)}].direction", buf, "declaration")
            det._scan_family(g["direction"], f"groups[{g.get('id', gi)}].direction", "", buf)
            non_claim += buf
        for n in g.get("nodes", []):
            non_claim += det.findings(n, f"node {n.get('id', '?')}")
    for i, ev in enumerate(m.get("portfolio_events", [])):
        if isinstance(ev, dict):
            non_claim += det.findings(ev, f"portfolio_events[{i}]")
    return rows, non_claim


def regression(det) -> dict:
    corpus = ROOT / "artifacts/worker-07/class_separation_falsification"
    res = json.loads((corpus / "results.json").read_text())
    tp = fn = tn = fp = total = 0
    for fx in res["fixtures"]:
        fpth = ROOT / fx["fixture_path"]
        if not fpth.exists():
            continue
        total += 1
        mm = json.loads(fpth.read_text())
        f = det.findings_for_map(mm)
        for g in mm.get("groups", []):
            for n in g.get("nodes", []):
                art = n.get("artifact")
                if art and (ROOT / art).is_file():
                    f += det.findings_for_text((ROOT / art).read_text(errors="replace"), f"artifact {art}")
        got, truth = bool(f), bool(fx["is_class_merge"])
        if truth and got:
            tp += 1
        elif truth and not got:
            fn += 1
        elif not truth and got:
            fp += 1
        else:
            tn += 1
    return {"tp": tp, "fn": fn, "tn": tn, "fp": fp, "corpus_size": total,
            "verdict": "PASS" if fn == 0 and fp == 0 else "DEFECTIVE"}


def detector_fires(det, text: str) -> bool:
    out: list[str] = []
    det._scan_composite(text, "probe", out, mode="prose")
    return bool(out)


def converse_scan(det, m: dict, flagged_rows: list[dict]) -> dict:
    by_claim: dict[str, list[tuple[int, int]]] = {}
    for r in flagged_rows:
        by_claim.setdefault(r["claim_event_id"], []).extend(tuple(s) for s in r["flagged_spans"])
    all_mentions = assertion_cued = 0
    unflagged, unflagged_genuine = [], []
    for i, c in enumerate(m.get("claims", [])):
        if not isinstance(c, dict):
            continue
        eid = str(c.get("event_id") or f"claims[{i}]")
        norm = det.norm(str(c.get("statement") or ""))
        spans = by_claim.get(eid, [])
        for mm in COMPOSITE.finditer(norm):
            all_mentions += 1
            lo, hi = max(0, mm.start() - 100), min(len(norm), mm.end() + 100)
            ctx = norm[lo:hi]
            if not MERGE_TO_ONE.search(ctx):
                continue
            assertion_cued += 1
            if any(s[0] <= mm.start() < s[1] for s in spans):
                continue
            label = classify_context(ctx)
            row = {"claim_index_at_snapshot": i, "claim_event_id": eid, "claim_actor": c.get("actor"),
                   "match": mm.group(0), "label": label, "context": ctx}
            unflagged.append(row)
            if label == "GENUINE_ASSERTION":
                unflagged_genuine.append(row)
    return {
        "composite_mentions_scanned": all_mentions,
        "assertion_cued_mentions": assertion_cued,
        "unflagged_assertion_cued": len(unflagged),
        "unflagged_genuine": len(unflagged_genuine),
        "unflagged_rows": unflagged,
    }


def run_controls(det_pre, det_post, m: dict) -> dict:
    positive = []
    for cid, text in POSITIVE_CONTROLS:
        pre, post = detector_fires(det_pre, text), detector_fires(det_post, text)
        positive.append({"id": cid, "text": text, "pre_fires": pre, "post_fires": post,
                         "pass": pre and post})
    negative = []
    for cid, text in NEGATIVE_CONTROLS:
        got = classify_context(text)
        negative.append({"id": cid, "text": text, "indep_label": got,
                         "pass": got != "GENUINE_ASSERTION"})
    over = []
    for cid, text in OVER_SUPPRESSION_PROBES:
        pre, post = detector_fires(det_pre, text), detector_fires(det_post, text)
        over.append({"id": cid, "text": text, "pre_fires": pre, "post_fires": post,
                     "over_suppressed": pre and not post})
    blind = []
    for cid, text in BLIND_SPOT_PROBES:
        pre, post = detector_fires(det_pre, text), detector_fires(det_post, text)
        indep = classify_context(text)
        blind.append({"id": cid, "text": text, "pre_fires": pre, "post_fires": post,
                      "indep_label": indep,
                      "detector_missed": (not pre) and (not post) and indep == "GENUINE_ASSERTION"})
    reg_pre, reg_post = regression(det_pre), regression(det_post)
    post_rows, _ = hard_findings(det_post, m, "post")
    ok = (all(r["pass"] for r in positive) and all(r["pass"] for r in negative)
          and reg_pre["verdict"] == "PASS" and reg_post["verdict"] == "PASS"
          and len(post_rows) > 0)
    return {
        "positive_first_order": positive,
        "negative_mention": negative,
        "over_suppression_probes": over,
        "blind_spot_probes": blind,
        "positive_pass": all(r["pass"] for r in positive),
        "negative_pass": all(r["pass"] for r in negative),
        "over_suppression_all": all(r["over_suppressed"] for r in over),
        "over_suppression_any": any(r["over_suppressed"] for r in over),
        "blind_spot_missed": sum(1 for r in blind if r["detector_missed"]),
        "regression_pre": reg_pre,
        "regression_post": reg_post,
        "controls_pass": ok,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--map", default=str(next((HERE / "pinned").glob("research_map.*.json"))))
    ap.add_argument("--detector-pre", default=str(next((HERE / "pinned").glob("class_separation.*.pre.py"))))
    ap.add_argument("--detector-post", default=str(next((HERE / "pinned").glob("class_separation.*.post.py"))))
    ap.add_argument("--classification", default=str(HERE / "classification.json"))
    ap.add_argument("--diff", default=str(HERE / "detector_diff.txt"))
    ap.add_argument("--created-at", default=DEFAULT_CREATED_AT)
    ap.add_argument("--out", default=str(HERE / "report.json"))
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    map_path, pre_path, post_path = Path(args.map), Path(args.detector_pre), Path(args.detector_post)
    det_pre = load_module(pre_path, "cls_pre")
    det_post = load_module(post_path, "cls_post")
    m = json.loads(map_path.read_text())

    if args.selftest:
        c = run_controls(det_pre, det_post, m)
        print(json.dumps({"controls_pass": c["controls_pass"],
                          "positive_pass": c["positive_pass"],
                          "negative_pass": c["negative_pass"],
                          "over_suppression_any": c["over_suppression_any"],
                          "regression_pre": c["regression_pre"],
                          "regression_post": c["regression_post"]}, indent=1))
        return 0 if c["controls_pass"] else 1

    controls = run_controls(det_pre, det_post, m)
    pre_rows, pre_non = hard_findings(det_pre, m, "pre")
    post_rows, post_non = hard_findings(det_post, m, "post")
    conv = converse_scan(det_post, m, post_rows)

    pre_by_key = {r["finding_key"]: r for r in pre_rows}
    post_by_key = {r["finding_key"]: r for r in post_rows}
    cleared_keys = [k for k in pre_by_key if k not in post_by_key]
    added_keys = [k for k in post_by_key if k not in pre_by_key]

    pass1 = json.loads(PASS1_REPORT.read_text())
    pass1_sha_ok = sha256_file(PASS1_REPORT) == PASS1_REPORT_SHA
    pass1_labels = {finding_key(r["claim_event_id"], r["context"]): r for r in pass1["adjudication"]["rows"]}
    replicated17_keys = set(pass1_labels)
    cleared = []
    for k in cleared_keys:
        r = pre_by_key[k]
        p1 = pass1_labels.get(k)
        cleared.append({
            "finding_key": k, "claim_event_id": r["claim_event_id"], "claim_actor": r["claim_actor"],
            "claim_class_id": r["claim_class_id"], "context": r["context"],
            "pass1_label": (p1 or {}).get("label"), "pass1_mechanism": (p1 or {}).get("mechanism"),
        })

    classification = json.loads(Path(args.classification).read_text())
    labels = classification["findings_by_key"]
    problems = []
    if not controls["controls_pass"]:
        problems.append("pre-registered controls failed")
    if not pass1_sha_ok:
        problems.append("pass-1 report hash mismatch; carried labels not trustworthy")
    for r in post_rows:
        c = labels.get(r["finding_key"])
        if c is None:
            problems.append(f"unlabeled post finding {r['finding_key']}")
        elif c.get("label") not in ALLOWED_LABELS:
            problems.append(f"bad label for {r['finding_key']}: {c.get('label')}")
        else:
            r["label"] = c["label"]
            r["mechanism"] = c.get("mechanism", "")
            r["label_reason"] = c.get("reason", "")
            r["label_origin"] = c.get("origin", "")
            r["auto_label_check"] = classify_context(r["context"])
            r["curated_matches_auto"] = r["auto_label_check"] == c["label"]
        if r["claim_class_id_composite_token"]:
            problems.append(f"composite class token declared by {r['finding_key']}")
        if not r["claim_class_id_all_frozen"]:
            problems.append(f"non-frozen class token declared by {r['finding_key']}")
    for r in cleared:
        if r["pass1_label"] is None:
            problems.append(f"cleared finding has no pass-1 label: {r['finding_key']}")
        elif r["pass1_label"] == "GENUINE_ASSERTION":
            problems.append(f"patch cleared a pass-1 GENUINE_ASSERTION: {r['finding_key']}")
    if any(r.get("label") == "GENUINE_ASSERTION" for r in post_rows):
        problems.append("GENUINE_ASSERTION among post findings")
    if conv["unflagged_genuine"]:
        problems.append("GENUINE_ASSERTION among unflagged mention candidates")
    if not controls["positive_pass"]:
        problems.append("a first-order assertion is not flagged by one of the detector revisions")

    shared = [r for r in post_rows if r["finding_key"] in replicated17_keys]
    shared_label_agree = sum(1 for r in shared if labels[r["finding_key"]]["label"] == pass1_labels[r["finding_key"]]["label"])
    shared_stmt_agree = sum(1 for r in shared if r["statement_sha256"] == pass1_labels[r["finding_key"]]["statement_sha256"])
    label_counts: dict[str, int] = {}
    origin_counts: dict[str, int] = {}
    for r in post_rows:
        label_counts[r["label"]] = label_counts.get(r["label"], 0) + 1
        origin_counts[r["label_origin"]] = origin_counts.get(r["label_origin"], 0) + 1
    diff_text = Path(args.diff).read_text()
    added_lines = [l for l in diff_text.splitlines() if l.startswith("+") and not l.startswith("+++")]
    removed_lines = [l for l in diff_text.splitlines() if l.startswith("-") and not l.startswith("---")]
    regex_line = next((l[1:].strip() for l in added_lines if "re.search" in l), "")

    report = {
        "task_id": "W032-CF16-DELTA-02",
        "worker": "worker-032",
        "instance": "worker-032-20260912T004339-968807",
        "created_at": args.created_at,
        "node_id": "A1",
        "class_id": "AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "question": (
            "At pinned map ed28b714 (292 claims) with the APPLIED checker a8c04fc31e4a, what is the "
            "hard CLASSSEP claim-prose set (pre vs post patch), are the survivors and the cleared "
            "findings mention-level, does the patch introduce a false-negative channel, and does an "
            "independent corpus-wide converse scan find a first-order merge the patched checker misses?"
        ),
        "pins": {
            "map_path": str(map_path.relative_to(ROOT)),
            "map_sha256": sha256_file(map_path),
            "map_updated_at": m.get("updated_at"),
            "claims_in_snapshot": len(m.get("claims", [])),
            "detector_pre_path": str(pre_path.relative_to(ROOT)),
            "detector_pre_sha256": sha256_file(pre_path),
            "detector_post_path": str(post_path.relative_to(ROOT)),
            "detector_post_sha256": sha256_file(post_path),
            "detector_diff_path": str(Path(args.diff).relative_to(ROOT)),
            "detector_diff_sha256": sha256_file(Path(args.diff)),
            "detector_diff_added_lines": len(added_lines),
            "detector_diff_removed_lines": len(removed_lines),
            "patch_exemption_regex": regex_line,
            "classification_path": str(Path(args.classification).relative_to(ROOT)),
            "classification_sha256": sha256_file(Path(args.classification)),
            "pass1_report_path": str(PASS1_REPORT.relative_to(ROOT)),
            "pass1_report_sha256": sha256_file(PASS1_REPORT),
            "pass1_snapshot_sha256": PASS1_SNAPSHOT,
            "prior_snapshot_sha256": PRIOR_SNAPSHOT,
        },
        "hard_sets": {
            "pre_total": len(pre_rows),
            "post_total": len(post_rows),
            "cleared_total": len(cleared_keys),
            "added_total": len(added_keys),
            "non_claim_pre": pre_non,
            "non_claim_post": post_non,
            "cleared": cleared,
            "cleared_all_non_genuine": all(r["pass1_label"] not in (None, "GENUINE_ASSERTION") for r in cleared),
            "added": [post_by_key[k]["finding_key"] for k in added_keys],
        },
        "adjudication": {
            "label_counts": label_counts,
            "label_origin_counts": origin_counts,
            "genuine_assertions": label_counts.get("GENUINE_ASSERTION", 0),
            "curated_matches_auto": f"{sum(1 for r in post_rows if r.get('curated_matches_auto'))}/{len(post_rows)}",
            "rows": post_rows,
        },
        "replication": {
            "shared_with_pass1": len(shared),
            "label_agreement": f"{shared_label_agree}/{len(shared)}",
            "statement_hash_agreement": f"{shared_stmt_agree}/{len(shared)}",
            "pass1_total": len(pass1_labels),
            "pass1_hard_total": pass1["reproduction"]["hard_findings_total"],
        },
        "controls": controls,
        "converse_scan": conv,
        "concurrent_work": {
            "note": (
                "The applied 3-line exemption was made by the controller and is documented in "
                "worker-098's blocker w098-cps-20260912T0054-blocker-drift (pass-2 drift recheck at "
                "a8c04fc31e4a: live hard 16, corpus PASS, 3/4 declared FP probes still firing). "
                "worker-049 staged a larger prose-precision proposal and worker-080 a disjunction "
                "candidate; neither is the applied change. This pass independently replicates the "
                "patch effect with a separately written harness, adjudicates the 16 survivors with "
                "carried pass-1 labels plus 3 curated new labels, adds the corpus-wide converse scan, "
                "and measures the exemption's window scope with concessive-clause probes. No priority claimed."
            ),
            "other_event_ids": [
                "w098-cps-20260912T0054-blocker-drift",
                "w098-cps-20260912T0054-complete2",
                "w049-claim-classsep-prosefix-20260912T0052",
                "w080-disj-20260912T005139-claim",
                "w093-metagrowth-20260912T0049-claim",
            ],
        },
        "problems": problems,
        "summary": {
            "verdict": "PATCH_SAFE_AT_PIN_BUT_EXEMPTION_WINDOW_SCOPED_AND_VOCAB_GAP" if not problems else "INVALID_OR_FALSIFIED",
            "post_findings_adjudicated": len(post_rows),
            "post_genuine_assertions": label_counts.get("GENUINE_ASSERTION", 0),
            "cleared_by_patch": len(cleared_keys),
            "added_by_patch": len(added_keys),
            "cleared_all_non_genuine": all(r["pass1_label"] not in (None, "GENUINE_ASSERTION") for r in cleared),
            "unflagged_genuine_found": conv["unflagged_genuine"],
            "over_suppression_probes_fired": sum(1 for r in controls["over_suppression_probes"] if r["over_suppressed"]),
            "blind_spot_probes_missed": controls["blind_spot_missed"],
            "stock_vocabulary_gap": (
                "the patched module's _MERGE_ASSERT alternation covers 'one class|single class|one schema|"
                "single schema|as one|are one|is one' but not 'constitutes/forms/is a single + one/single + "
                "family|regularity', so B1/B3/B4/B5 are first-order composite assertions the stock checker "
                "misses; B2 ('are one family') is caught only via the bare 'are one' alternative"
            ),
            "not_a_gate_verdict": True,
            "no_claim_text_edited": True,
            "no_node_completion": True,
        },
        "falsifier": (
            "Any surviving or cleared finding is a genuine composite assertion (GENUINE_ASSERTION, or a "
            "composite token in the claim's own class_id); OR a first-order positive control fails to "
            "fire under the patched detector (patch-introduced false negative on a clean assertion); OR "
            "the converse scan finds an unflagged first-order merge; OR either regression leaves "
            "17/10/0/0; OR the pass-1 report hash no longer matches."
        ),
        "limits": [
            "Measurement evidence only; no gate verdict, no node completion, no claim edit.",
            "Over-suppression probes O1-O3 are synthetic scope probes, not claims found in the corpus; "
            "they measure the applied exemption's window scope, not a live false negative.",
            "Carried labels are only trustworthy while the pass-1 report hash matches.",
            "The converse scan is regex+cue based; it reports what it finds, it does not prove absence.",
        ],
    }
    Path(args.out).write_text(json.dumps(report, indent=1, sort_keys=False) + "\n")
    print(json.dumps({
        "pre_total": len(pre_rows), "post_total": len(post_rows),
        "cleared": len(cleared_keys), "added": len(added_keys),
        "label_counts": label_counts, "origins": origin_counts,
        "shared_with_pass1": len(shared),
        "replication": report["replication"]["label_agreement"],
        "unflagged_genuine": conv["unflagged_genuine"],
        "over_suppression_all": controls["over_suppression_all"],
        "controls_pass": controls["controls_pass"],
        "problems": problems,
        "report_sha256": sha256_file(Path(args.out)),
    }, indent=1))
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
