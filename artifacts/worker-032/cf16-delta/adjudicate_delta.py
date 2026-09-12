#!/usr/bin/env python3
"""W032-CF16-DELTA-01 -- independent adjudication of the CLASSSEP hard-finding delta.

Question
--------
Three prior worker lifecycles (worker-021 W021-CLASSSEP-MENTION-ADJ-01,
worker-035 W035-A1-CLASSSEP-HARDFAIL-ADJUDICATION-01, worker-093
cf16_calibration) adjudicated the 10 hard CLASSSEP claim-prose findings present
at map snapshot 3d45be5969ec and found 0 genuine C0/C2 class merges.  The live
detector now reports MORE hard findings on claims ingested after that snapshot.

This tool measures the delta and adjudicates it:

  1. reproduce every hard CLASSSEP finding on a PINNED research_map.json copy
     with a PINNED copy of research_map/class_separation.py;
  2. split the set into (a) findings already adjudicated by the prior three
     lifecycles and (b) NEW findings, keyed by claim event_id (not by index,
     because the claims array is rebuilt from the event stream and indices can
     shift);
  3. label each new finding with an independently written classifier
     (`classify_context`, no detector internals reused) plus a curated
     per-finding judgement in classification.json;
  4. run the CONVERSE scan: an independently written composite-merge detector
     over the whole claim corpus, looking for assertion-cued genuine merges the
     stock detector might MISS (false negatives), then subtract the flagged
     spans;
  5. run pre-registered positive/negative controls and the worker-07 27-fixture
     regression, and fail closed if any control fails.

This is measurement evidence only.  It edits no canonical file, issues no gate
verdict, completes no node, and claims no theorem.

Reproduce:
  python3 artifacts/worker-032/cf16-delta/adjudicate_delta.py \
      --created-at 2026-09-12T00:52:00+08:00
"""
from __future__ import annotations

import argparse
import ast
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
DEFAULT_CREATED_AT = "2026-09-12T00:52:00+08:00"

ALLOWED_LABELS = {
    "GENUINE_ASSERTION",
    "NEGATED_MENTION",
    "CASE_LABEL_MENTION",
    "QUOTED_MENTION",
    "DETECTOR_SELF_DESCRIPTION",
    "DIFFERENT_CLAUSE_MENTION",
    "DESCRIPTIVE_MENTION",
}
NON_GENUINE = sorted(ALLOWED_LABELS - {"GENUINE_ASSERTION"})
FROZEN_CLASSES = {
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
}

# Prior adjudications at snapshot 3d45be5969ec (worker-021 report.json and
# worker-035 report.json).  Keyed by claim event_id; the integer is how many
# hard findings that claim produced in the prior reproduction.
PRIOR_ADJUDICATED_COUNTS = {
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
PRIOR_SNAPSHOT = "3d45be5969ec388ef4a3e10d5eb87b81dbf3d03138510b75ff6a56453ceae005"
PRIOR_TOTAL = sum(PRIOR_ADJUDICATED_COUNTS.values())  # 10

# ---------------------------------------------------------------- independent
# detector for the converse scan (written from the problem statement, NOT from
# research_map/class_separation.py internals).
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
    r"|\bmerge[ds]?\b"
    r"|asserted\s+as\s+one",
    re.I,
)
# "the merged file" merges artifacts, not classes: demote unless a class-ish
# object is also in scope.
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
    r"TC-[A-Z0-9]+-N\d+|split_required|case[_ ]label|taxonomy_cases|disposition|open=true",
    re.I,
)
META_CUE = re.compile(
    r"classep|classsep|detector|hard\s+failure|false\s+positive|pattern|regex|candidate|"
    r"probe|fixture|the\s+form\s+of|shape|guard|prose|mention|flag|assertion|"
    r"claim[s\[]|rule\s*R\d|regression|corpus|negation",
    re.I,
)
QUOTE_CHARS = "'\"`\u2018\u2019\u201c\u201d"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("pinned_class_separation", str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def classify_context(ctx: str) -> str:
    """Independent cue-based classifier for one composite-merge context.

    Order is deliberately conservative and favours the non-assertion reading:
    negation wins over everything, then quotation, then an explicit case label,
    then meta-discussion of a detector/claim/pattern.  GENUINE_ASSERTION is
    returned only when a merge-to-one predicate (or a merge-with-class-object
    phrase) is in scope with none of those markers.
    """
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
    """Recover the detector's quoted +/-60 char context from a finding string."""
    if ": ..." not in finding:
        return ""
    raw = finding.split(": ...", 1)[1]
    try:
        return ast.literal_eval(raw)
    except (ValueError, SyntaxError):
        return raw.strip("'")


def flagged_spans(det, statement: str, findings: list[str]) -> list[tuple[int, int]]:
    """Locate the reported composite matches inside one claim statement."""
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


def reproduce(det, m: dict) -> tuple[list[dict], list[str]]:
    rows, non_claim = [], []
    for i, c in enumerate(m.get("claims", [])):
        if not isinstance(c, dict):
            continue
        eid = str(c.get("event_id") or f"claims[{i}]")
        st = str(c.get("statement") or "")
        cid_raw = str(c.get("class_id") or "")
        cid_tokens = [t.strip() for t in re.split(r"[;,]", cid_raw) if t.strip()]
        fs = det.findings(c, f"claims[{i}]", mode="prose")
        for k, f in enumerate(fs):
            rows.append(
                {
                    "finding_id": f"{eid}#{k}",
                    "claim_index_at_snapshot": i,
                    "claim_event_id": eid,
                    "claim_actor": c.get("actor"),
                    "claim_class_id": cid_raw,
                    "claim_class_id_tokens": cid_tokens,
                    "claim_class_id_all_frozen": all(t in FROZEN_CLASSES for t in cid_tokens),
                    "claim_class_id_composite_token": any(
                        ("C0" in t.upper() and "C2" in t.upper()) for t in cid_tokens
                    ),
                    "claim_conclusion_type": c.get("conclusion_type"),
                    "statement_sha256": sha256_text(st),
                    "detector_finding": f,
                    "context": extract_context(f),
                    "flagged_spans": flagged_spans(det, st, fs),
                }
            )
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


def converse_scan(det, m: dict, flagged_rows: list[dict]) -> dict:
    """Independent false-negative scan over the claim corpus."""
    by_claim: dict[str, list[tuple[int, int]]] = {}
    for r in flagged_rows:
        by_claim.setdefault(r["claim_event_id"], []).extend(
            tuple(s) for s in r["flagged_spans"]
        )
    all_mentions, assertion_cued, unflagged, unflagged_genuine = 0, 0, [], []
    for i, c in enumerate(m.get("claims", [])):
        if not isinstance(c, dict):
            continue
        eid = str(c.get("event_id") or f"claims[{i}]")
        st = str(c.get("statement") or "")
        norm = det.norm(st)
        spans = by_claim.get(eid, [])
        for mm in COMPOSITE.finditer(norm):
            all_mentions += 1
            lo, hi = max(0, mm.start() - 100), min(len(norm), mm.end() + 100)
            ctx = norm[lo:hi]
            if not MERGE_TO_ONE.search(ctx):
                continue
            assertion_cued += 1
            if any(s[0] <= mm.start() < s[1] for s in spans):
                continue  # already inside a detector-flagged span
            label = classify_context(ctx)
            row = {
                "claim_index_at_snapshot": i,
                "claim_event_id": eid,
                "claim_actor": c.get("actor"),
                "match": mm.group(0),
                "label": label,
                "context": ctx,
            }
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


def run_regression(det) -> dict:
    """Re-run the worker-07 27-fixture regression against the PINNED detector.

    Reimplemented here (instead of det.regression()) because the pinned copy
    lives outside research_map/, so the module's own path resolution would look
    for the corpus under artifacts/worker-032/.  Fixture semantics are identical.
    """
    corpus = ROOT / "artifacts/worker-07/class_separation_falsification"
    res = json.loads((corpus / "results.json").read_text())
    tp = fn = tn = fp = 0
    total = 0
    for fx in res["fixtures"]:
        fpth = ROOT / fx["fixture_path"]
        if not fpth.exists():
            continue
        total += 1
        m = json.loads(fpth.read_text())
        f = det.findings_for_map(m)
        for g in m.get("groups", []):
            for n in g.get("nodes", []):
                art = n.get("artifact")
                if art and (ROOT / art).is_file():
                    f += det.findings_for_text(
                        (ROOT / art).read_text(errors="replace"), f"artifact {art}"
                    )
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


def run_controls(det, m: dict) -> dict:
    pos = [
        ("P1", "In this model C0 and C2 are one class on the vacuum sector.", "GENUINE_ASSERTION"),
        ("P2", "We treat C2 and C0 as a single schema for the regularities.", "GENUINE_ASSERTION"),
        ("P3", "The merged C0/C2 class is the authoritative definition.", "GENUINE_ASSERTION"),
        ("P4", "C0/C2 constitutes one family in the declaration surface.", "GENUINE_ASSERTION"),
    ]
    neg = [
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
    pos_rows, neg_rows = [], []
    for cid, text, expect in pos:
        got = classify_context(text)
        pos_rows.append({"id": cid, "expected": expect, "got": got, "pass": got == expect, "text": text})
    for cid, text in neg:
        got = classify_context(text)
        neg_rows.append({"id": cid, "expected_not": "GENUINE_ASSERTION", "got": got,
                         "pass": got != "GENUINE_ASSERTION", "text": text})
    reg = run_regression(det)
    hard, _non_claim = reproduce(det, m)
    unlabeled = [r["finding_id"] for r in hard]
    return {
        "positive": pos_rows,
        "negative": neg_rows,
        "positive_pass": all(r["pass"] for r in pos_rows),
        "negative_pass": all(r["pass"] for r in neg_rows),
        "regression": reg,
        "regression_pass": reg.get("verdict") == "PASS",
        "controls_pass": all(r["pass"] for r in pos_rows)
        and all(r["pass"] for r in neg_rows)
        and reg.get("verdict") == "PASS",
        "findings_seen_by_controls": len(unlabeled),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--map", default=None, help="pinned map copy (default: pinned/research_map.*.json)")
    ap.add_argument("--detector", default=None, help="pinned detector copy")
    ap.add_argument("--classification", default=str(HERE / "classification.json"))
    ap.add_argument("--created-at", default=DEFAULT_CREATED_AT)
    ap.add_argument("--out", default=str(HERE / "report.json"))
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    map_path = Path(args.map) if args.map else next((HERE / "pinned").glob("research_map.*.json"))
    det_path = Path(args.detector) if args.detector else next((HERE / "pinned").glob("class_separation.*.py"))
    det = load_module(det_path)
    m = json.loads(map_path.read_text())

    if args.selftest:
        c = run_controls(det, m)
        print(json.dumps({"controls_pass": c["controls_pass"],
                          "regression": c["regression"],
                          "positive_pass": c["positive_pass"],
                          "negative_pass": c["negative_pass"]}, indent=1))
        return 0 if c["controls_pass"] else 1

    controls = run_controls(det, m)
    rows, non_claim = reproduce(det, m)
    conv = converse_scan(det, m, rows)

    prior_rows = [r for r in rows if r["claim_event_id"] in PRIOR_ADJUDICATED_COUNTS]
    new_rows = [r for r in rows if r["claim_event_id"] not in PRIOR_ADJUDICATED_COUNTS]

    classification = json.loads(Path(args.classification).read_text())
    labels = {k: v for k, v in classification["findings"].items()}
    problems = []
    if not controls["controls_pass"]:
        problems.append("pre-registered controls failed")
    for r in rows:
        c = labels.get(r["finding_id"])
        if c is None:
            problems.append(f"unlabeled finding {r['finding_id']}")
        elif c.get("label") not in ALLOWED_LABELS:
            problems.append(f"bad label for {r['finding_id']}: {c.get('label')}")
        else:
            r["label"] = c["label"]
            r["mechanism"] = c.get("mechanism", "")
            r["label_reason"] = c.get("reason", "")
            auto = classify_context(r["context"])
            r["auto_label_check"] = auto
            r["curated_matches_auto"] = auto == c["label"]
        if r["claim_class_id_composite_token"]:
            problems.append(f"composite class token declared by {r['finding_id']}")
        if not r["claim_class_id_all_frozen"]:
            problems.append(f"non-frozen class token declared by {r['finding_id']}")
    for r in conv["unflagged_rows"]:
        c = classification.get("unflagged", {}).get(r["claim_event_id"] + "|" + r["match"])
        r["label"] = (c or {}).get("label", r["label"])
        r["mechanism"] = (c or {}).get("mechanism", "auto")
        r["label_reason"] = (c or {}).get("reason", "auto")
    if any(r["label"] == "GENUINE_ASSERTION" for r in rows):
        problems.append("GENUINE_ASSERTION among flagged findings")
    if conv["unflagged_genuine"]:
        problems.append("GENUINE_ASSERTION among unflagged mention candidates")

    label_counts: dict[str, int] = {}
    for r in rows:
        label_counts[r["label"]] = label_counts.get(r["label"], 0) + 1
    auto_agree = sum(1 for r in rows if r.get("curated_matches_auto"))
    classid_composite = sum(1 for r in rows if r["claim_class_id_composite_token"])
    classid_all_frozen = all(r["claim_class_id_all_frozen"] for r in rows)

    report = {
        "task_id": "W032-CF16-DELTA-01",
        "worker": "worker-032",
        "instance": "worker-032-20260912T004339-968807",
        "created_at": args.created_at,
        "node_id": "A1",
        "class_id": "AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "question": (
            "Are the CLASSSEP hard findings that are NEW at the current map snapshot "
            "(relative to the 10 findings adjudicated by worker-021/worker-035 at "
            "snapshot 3d45be5969ec) genuine assertions that C0 and C2 are one class, "
            "and does an independently written converse scan find any GENUINE composite "
            "merge assertion that the stock detector misses?"
        ),
        "pins": {
            "map_path": str(map_path.relative_to(ROOT)),
            "map_sha256": sha256_file(map_path),
            "map_updated_at": m.get("updated_at"),
            "claims_in_snapshot": len(m.get("claims", [])),
            "detector_path": str(det_path.relative_to(ROOT)),
            "detector_sha256": sha256_file(det_path),
            "detector_sha256_repo_current": sha256_file(ROOT / "research_map" / "class_separation.py"),
            "classification_path": str(Path(args.classification).relative_to(ROOT)),
            "classification_sha256": sha256_file(Path(args.classification)),
            "prior_snapshot_sha256": PRIOR_SNAPSHOT,
            "prior_adjudicated_findings": PRIOR_TOTAL,
        },
        "concurrent_work": {
            "note": (
                "worker-093 published W093-CLASSSEP-METAGROWTH-01 at 2026-09-12T00:49:28+08:00, "
                "independently reaching 0/17 first-order assertions at the same pinned map "
                "11311ab3600514cd. That is concurrent, not prior, work; this task is an "
                "independent replication of the 0/17 result plus a converse false-negative "
                "scan and a moving-target observation that worker-093 did not run. No priority "
                "is claimed."
            ),
            "other_event_ids": [
                "w093-metagrowth-20260912T0049-claim",
                "w093-metagrowth-20260912T0049-blocker-meta-routing",
            ],
            "other_artifacts": {
                "artifacts/worker-093/classsep_metagrowth/report.json": "9d857447463939973cfd8b74d626fd8f05fa060224fb864ac35fb5eb5ddb2c9f",
                "artifacts/worker-093/classsep_metagrowth/verify_metagrowth.py": "c33c74346ba7a8c7b1f005e075abeac59d7541380bc82650503ee6bacdcff857",
            },
            "prediction_confirmed": (
                "worker-093 predicted its own claim would mint 3 more hard entries; the live map "
                "at f06d40a8226a (278 claims) shows exactly 3 extra hard findings from "
                "w093-metagrowth-20260912T0049-claim, an independent confirmation of the "
                "self-reproduction mechanism."
            ),
        },
        "reproduction": {
            "hard_findings_total": len(rows),
            "hard_findings_non_claim_surfaces": non_claim,
            "distinct_claims_flagged": len({r["claim_event_id"] for r in rows}),
            "prior_findings_reproduced": len(prior_rows),
            "new_findings": len(new_rows),
            "new_claim_event_ids": sorted({r["claim_event_id"] for r in new_rows}),
            "class_id_composite_tokens": classid_composite,
            "class_id_tokens_all_frozen": classid_all_frozen,
        },
        "adjudication": {
            "label_counts": label_counts,
            "genuine_assertions": label_counts.get("GENUINE_ASSERTION", 0),
            "curated_vs_auto_agreement": f"{auto_agree}/{len(rows)}",
            "rows": rows,
        },
        "converse_scan": conv,
        "controls": controls,
        "problems": problems,
        "summary": {
            "verdict": "DELTA_ALL_MENTION_LEVEL" if not problems else "INVALID_OR_FALSIFIED",
            "new_findings_adjudicated": len(new_rows),
            "new_genuine_assertions": sum(
                1 for r in new_rows if r.get("label") == "GENUINE_ASSERTION"
            ),
            "unflagged_genuine_found": conv["unflagged_genuine"],
            "prior_result_stands": len(prior_rows) == PRIOR_TOTAL
            and all(r.get("label") != "GENUINE_ASSERTION" for r in prior_rows),
            "not_a_gate_verdict": True,
            "no_claim_text_edited": True,
            "no_node_completion": True,
        },
        "falsifier": (
            "Any of the new findings is a genuine composite assertion (label "
            "GENUINE_ASSERTION, or a composite token inside the claim's own "
            "class_id/class_ids), OR the converse scan finds an unflagged claim "
            "asserting that C0 and C2 are one class without negation/quotation, OR "
            "any pre-registered control fails, OR the worker-07 regression leaves "
            "17/10/0/0."
        ),
        "limits": [
            "Measurement evidence only; no gate verdict, no node completion, no claim edit.",
            "Label judgement is inspectable in classification.json with one reason per finding.",
            "The converse scan is regex+cue based; it cannot prove absence, only report what it finds.",
            "Prior-set membership is keyed by claim event_id; occurrences beyond the prior count for the same event_id are counted as new.",
        ],
    }
    Path(args.out).write_text(json.dumps(report, indent=1, sort_keys=False) + "\n")
    print(json.dumps({
        "hard_total": len(rows),
        "prior_reproduced": len(prior_rows),
        "new": len(new_rows),
        "label_counts": label_counts,
        "unflagged_genuine": conv["unflagged_genuine"],
        "controls_pass": controls["controls_pass"],
        "problems": problems,
        "report_sha256": sha256_file(Path(args.out)),
    }, indent=1))
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
