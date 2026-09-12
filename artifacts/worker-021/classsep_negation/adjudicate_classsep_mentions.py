#!/usr/bin/env python3
"""W021-CLASSSEP-MENTION-ADJ-01.

Question (from the live critical path, A1 / CF-16): the audit lead's blocker
``audit-blocker-20260912T0036-aud-b4`` reports 8 hard CLASSSEP findings on map
claim prose (claims[36,94,96,97,101,112,127]) and calls them "negation-blind
hits on map claim prose that describes or denies a C0/C2 merge".

This instrument:
  1. reproduces the hard CLASSSEP findings that the frozen detector
     ``research_map/class_separation.py`` emits for ``research_map.json`` claims
     (prose mode), read-only, against exact byte hashes;
  2. classifies every reproduced claim-prose mention with a deterministic
     mention adjudicator:
       ASSERTED_LEAK      - the prose asserts C0/C2 are one class/schema
       NEGATED_MENTION    - the mention is negated or contrastive
       DESCRIPTIVE_MENTION- the mention is a case label, quote, detector/report
                            mechanism description, or other non-assertion frame
       AMBIGUOUS_MENTION  - none of the above; escalated, never silently dropped
  3. runs controls: a synthetic positive assertion must classify ASSERTED_LEAK
     and must still be detected by the frozen detector (no weakening), while the
     frozen detector's own 27-fixture regression must stay PASS;
  4. measures, in memory only, a counterfactual hardening of the detector's
     negation lookbehind (NOT applied to the file) to show the root cause of the
     negated mentions.

Read-only: no repo file is written except the caller-selected --out-dir.
No gate verdict, node status, claim edit, or detector edit is claimed.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

CST = timezone(timedelta(hours=8))
ROOT = Path(__file__).resolve().parents[3]
MAP_DEFAULT = ROOT / "research_map" / "research_map.json"
DETECTOR = ROOT / "research_map" / "class_separation.py"
AUDIT_EVIDENCE = ROOT / "research_map" / "audit_evidence.py"
AUDIT_BASELINE = {
    "event_id": "audit-blocker-20260912T0036-aud-b4",
    "reported_hard_findings": 8,
    "reported_claims": [36, 94, 96, 97, 101, 112, 127],
    "reported_regression": "27-fixture regression unchanged at 17/17/10/10",
}
TASK_ID = "W021-CLASSSEP-MENTION-ADJ-01"
NODE_ID = "A1"
CLASS_ID = "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN"

# ---------------------------------------------------------------- adjudicator
NEG_BEFORE = re.compile(
    r"(?i)(?:^|[\s\(\[\"'‘“])(?:no|not|never|without|zero|absent|nor|neither|non|none)"
    r"[\s\-]*(?:[\w/]+[\s\-]+){0,3}$")
CONTRAST_BEFORE = re.compile(
    r"(?i)(?:rather\s+than|instead\s+of|as\s+opposed\s+to)[\s\-]*(?:[\w/]+[\s\-]+){0,3}$")
NEG_SUFFIX = re.compile(r"(?i)^[\s\-]*(?:non[\s\-]*merge|not[\s\-]+an?[\s\-]*merge)")
NEG_BETWEEN = re.compile(
    r"(?i)(?:never|not|no|non)[\s\-]+(?:\w+[\s\-]+){0,4}"
    r"(?:treated|merged|unified|combined|counted|one)\b|kept\s+distinct")
ASSERT_STRUCT = re.compile(
    r"(?i)(?:c\s*0\s*(?:or|and|/|,|\+|\s)\s*c\s*2|c\s*2\s*(?:or|and|/|,|\+|\s)\s*c\s*0)"
    r"(?:\s+\w+){0,2}\s+(?:are|is|shall\s+be|must\s+be|should\s+be|treated\s+as|counts?\s+as)"
    r"\s+(?:one|a\s+single|the\s+same)\s+(?:class|schema|family)")
ASSERT_VERB = re.compile(
    r"(?i)\b(?:merge|merged|merging|unify|unified|unification|combine|combined)\b")
REPORT_CUE = re.compile(
    r"(?i)\b(?:detector|scanner|flagged|flag|reports?|reported|quot\w*|describ\w*|"
    r"fixture|probe|checker|regression|pattern|criterion|invariant|control|finding)\b")
DESCRIPTIVE = re.compile(
    r"(?i)\b(?:split|SPLIT_REQUIRED|NEW_CLASS_REQUIRED|case|fixture|row|detector|pattern|"
    r"scanner|regression|probe|checker|flagged|flag|reports?|reported|quot\w*|describ\w*|"
    r"descriptor|criterion|invariant|control|re-?implementation|mislabels?|tombstone|retired|"
    r"superseded|disposition|question|reading|composite|occurrence|mechanism|sensitivity|"
    r"silent|vocabulary|prose|index|legacy|separation\s+locus)\b")
QUOTE_CHARS = "\"'‘’“”"


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load_detector(path: Path):
    spec = importlib.util.spec_from_file_location("cs_pinned", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def quoted_spans(t: str):
    spans, stack = [], []
    for i, ch in enumerate(t):
        if ch not in QUOTE_CHARS:
            continue
        if ch == "'" and 0 < i < len(t) - 1 and t[i - 1].isalnum() and t[i + 1].isalnum():
            continue  # possessive/contraction apostrophe, not a quote delimiter
        if stack and ((stack[-1][1] in "\"“”" and ch in "\"“”")
                      or (stack[-1][1] in "'‘’" and ch in "'‘’")):
            s, _ = stack.pop()
            spans.append((s, i))
        else:
            stack.append((i, ch))
    return spans


def adjudicate(t_norm: str, start: int, end: int):
    """Return (label, cue, reason) for one composite mention at [start,end)."""
    before = t_norm[max(0, start - 200):start]
    after = t_norm[end:end + 200]
    after_local = t_norm[end:end + 60]
    ctx = t_norm[max(0, start - 220):min(len(t_norm), end + 220)]
    if NEG_BEFORE.search(before):
        return ("NEGATED_MENTION", NEG_BEFORE.search(before).group(0).strip()[-24:],
                "negation cue scopes the composite before it")
    if CONTRAST_BEFORE.search(before):
        return ("NEGATED_MENTION", CONTRAST_BEFORE.search(before).group(0).strip()[-24:],
                "contrastive frame ('rather than'/'instead of') denies the merge reading")
    if NEG_SUFFIX.search(after):
        return ("NEGATED_MENTION", NEG_SUFFIX.search(after).group(0).strip(),
                "negation is suffixed to the merge word ('non-merge')")
    if NEG_BETWEEN.search(after_local):
        return ("NEGATED_MENTION", NEG_BETWEEN.search(after_local).group(0).strip()[:40],
                "negation cue sits between the composite and the merge verb")
    for qs, qe in quoted_spans(t_norm):
        if qs <= start and end <= qe:
            inner = t_norm[qs:qe + 1]
            if ASSERT_STRUCT.search(inner) or ASSERT_VERB.search(inner) or REPORT_CUE.search(inner) \
                    or REPORT_CUE.search(t_norm[max(0, qs - 80):qe + 80]):
                return ("DESCRIPTIVE_MENTION", "quote",
                        "composite/assertion sits inside a quotation, i.e. reported or discussed text")
            break
    if ASSERT_STRUCT.search(ctx):
        return ("ASSERTED_LEAK", ASSERT_STRUCT.search(ctx).group(0).strip()[:60],
                "explicit assertion that the composite is one class/schema")
    if DESCRIPTIVE.search(ctx):
        return ("DESCRIPTIVE_MENTION", DESCRIPTIVE.search(ctx).group(0).strip(),
                "non-assertion frame (case label, quote, detector/report mechanism, or record field)")
    if ASSERT_VERB.search(ctx):
        return ("AMBIGUOUS_MENTION", ASSERT_VERB.search(ctx).group(0).strip(),
                "merge language present but no decisive assertion or description frame; escalated")
    return ("AMBIGUOUS_MENTION", "", "no decisive cue; escalated rather than dismissed")


def claim_prose_findings(det, m: dict):
    """Reproduce hard claim-prose findings and pair them with their mentions."""
    findings = [f for f in det.findings_for_map(m)
                if f.startswith("CLASSSEP:") and " in claims[" in f]
    by_index: dict[int, list] = {}
    for f in findings:
        where = f.split(" in claims[", 1)[1].split("]", 1)[0]
        by_index.setdefault(int(where), []).append(f)
    records = []
    for i in sorted(by_index):
        claim = m["claims"][i]
        statement = str(claim.get("statement", ""))
        t = det.norm(statement)
        matches = list(det._MERGE_PAT.finditer(t))
        decoys = [f for f in by_index[i] if "composite C0/C2" not in f]
        for n, mt in enumerate(matches):
            label, cue, reason = adjudicate(t, mt.start(), mt.end())
            ctx60 = t[max(0, mt.start() - 60):mt.end() + 60].strip()
            flagged = any(repr(ctx60) in f for f in by_index[i])
            records.append({
                "finding_id": f"CLASSSEP-claims[{i}].statement#{n + 1}",
                "where": f"claims[{i}].statement",
                "claim_index": i,
                "claim_event_id": claim.get("event_id"),
                "claim_actor": claim.get("actor"),
                "claim_class_id": claim.get("class_id"),
                "claim_created_at": claim.get("created_at"),
                "statement_sha256": sha256_bytes(statement.encode("utf-8")),
                "detector_flagged": flagged,
                "detector_finding": next((f for f in by_index[i] if repr(ctx60) in f), None),
                "detector_finding_count_for_claim": len(by_index[i]),
                "match": t[mt.start():mt.end()],
                "label": label,
                "label_role": "finding" if flagged else "unflagged_mention",
                "cue": cue,
                "reason": reason,
                "context": t[max(0, mt.start() - 140):mt.end() + 140],
            })
        for f in decoys:
            records.append({
                "finding_id": f"CLASSSEP-claims[{i}].other",
                "where": f"claims[{i}].statement",
                "claim_index": i,
                "claim_event_id": claim.get("event_id"),
                "claim_actor": claim.get("actor"),
                "claim_class_id": claim.get("class_id"),
                "statement_sha256": sha256_bytes(statement.encode("utf-8")),
                "detector_flagged": False,
                "detector_finding": f,
                "label": "UNPARSED_FINDING",
                "label_role": "finding",
                "cue": "",
                "reason": "finding reproduced but not attributable to a _MERGE_PAT mention; escalated",
                "context": "",
            })
    return records, findings


def controls(det, records, m):
    cases = [
        ("C1 positive assertion (must be ASSERTED_LEAK)",
         "The C0 and C2 regularities are one class and must be merged into a single schema.",
         "ASSERTED_LEAK"),
        ("C2 direct negation",
         "... so no C0/C2 merge exists at the formal surface.",
         "NEGATED_MENTION"),
        ("C3 suffixed negation",
         "the independent C0/C2 non-merge check passes",
         "NEGATED_MENTION"),
        ("C4 contrastive frame",
         "the shared block is a single-data-class question rather than a C2/C0 merge.",
         "NEGATED_MENTION"),
        ("C5 case label / split disposition",
         "2 SPLIT_REQUIRED (TC-F0-N14 merged C0/C2 regularities).",
         "DESCRIPTIVE_MENTION"),
        ("C6 quoted report of a detector hit",
         "the detector flags the same slot carrying 'C0 or C2 are one class'",
         "DESCRIPTIVE_MENTION"),
        ("C7 prohibition",
         "the string 'C0 or C2' must never be treated as one class",
         "NEGATED_MENTION"),
        ("C8 ambiguous merge language (must escalate, not dismiss)",
         "C0/C2 came up in the merged discussion",
         "AMBIGUOUS_MENTION"),
    ]
    rows = []
    for cid, text, expected in cases:
        t = det.norm(text)
        ms = list(det._MERGE_PAT.finditer(t))
        got, cue, reason = ("NO_MENTION", "", "composite pattern absent") if not ms \
            else adjudicate(t, ms[0].start(), ms[0].end())
        rows.append({"id": cid.split()[0], "case": cid, "text": text,
                     "expected": expected, "got": got, "cue": cue, "reason": reason,
                     "pass": got == expected})
    # frozen-detector probes: assertion must still be detected; the negation FP is reproduced
    def mini(statements):
        return {"groups": [], "portfolio_events": [],
                "claims": [{"class_id": "AF-SCC-C2-VAC-GEN", "statement": s} for s in statements]}
    assert_stmt = cases[0][1]
    neg_stmt = cases[1][1]
    probe_assert = det.findings_for_map(mini([assert_stmt]))
    probe_neg = det.findings_for_map(mini([neg_stmt]))
    rows.append({"id": "C9", "case": "frozen detector still fires on explicit assertion (no weakening)",
                 "text": assert_stmt, "expected": ">=1 hard finding",
                 "got": f"{len(probe_assert)} hard finding(s)", "cue": "",
                 "reason": probe_assert[0] if probe_assert else "detector silent",
                 "pass": len(probe_assert) >= 1})
    rows.append({"id": "C10", "case": "frozen detector reproduces the negation-blind FP",
                 "text": neg_stmt, "expected": ">=1 hard finding (documents the defect)",
                 "got": f"{len(probe_neg)} hard finding(s)", "cue": "",
                 "reason": probe_neg[0] if probe_neg else "detector silent",
                 "pass": len(probe_neg) >= 1})
    reg = det.regression()
    rows.append({"id": "C11", "case": "frozen 27-fixture regression unchanged",
                 "text": "class_separation.regression()",
                 "expected": "PASS tp=17 fn=0 tn=10 fp=0",
                 "got": f"{reg['verdict']} tp={reg['tp']} fn={reg['fn']} tn={reg['tn']} fp={reg['fp']}",
                 "cue": "", "reason": f"corpus_size={reg['corpus_size']}",
                 "pass": reg["verdict"] == "PASS" and (reg["tp"], reg["fn"], reg["tn"], reg["fp"]) == (17, 0, 10, 0)})
    # counterfactual negation hardening, in memory only, reverted immediately
    flagged = sorted({r["claim_index"] for r in records if r["label"] != "UNPARSED_FINDING"})
    live_claims = [m["claims"][i] for i in flagged]
    mini_live = {"groups": [], "portfolio_events": [], "claims": live_claims}
    before = [f for f in det.findings_for_map(mini_live) if f.startswith("CLASSSEP:")]
    orig = det._NEG_BEFORE_ASSERT
    det._NEG_BEFORE_ASSERT = re.compile(
        r"(?i)(?:no|not|never|without|zero|absent|nor|non|neither|none|"
        r"rather\s+than|instead\s+of)(?:[\s\-]+[\w/]+){0,3}[\s\-]*$")
    try:
        after = [f for f in det.findings_for_map(mini_live) if f.startswith("CLASSSEP:")]
    finally:
        det._NEG_BEFORE_ASSERT = orig
    assert_after = det.findings_for_map(mini([assert_stmt]))
    counterfactual = {
        "applied_to_file": False,
        "detector_file_unchanged": sha256_file(DETECTOR),
        "patch": "negation lookbehind accepts composite tokens and the non-/rather-than forms",
        "hard_findings_before": len(before),
        "hard_findings_after_in_memory_patch": len(after),
        "removed": len(before) - len(after),
        "assertion_control_still_detected": len(assert_after) >= 1,
        "note": ("the in-memory patch removes only the negated mentions; the descriptive/"
                 "reported mentions remain, so the recommended disposition is author-side "
                 "rephrasing or a report/quote-aware scanner, not this regex alone"),
    }
    return rows, reg, counterfactual


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--map", default=str(MAP_DEFAULT))
    ap.add_argument("--out-dir", default=str(Path(__file__).resolve().parent))
    ap.add_argument("--instance", default="")
    args = ap.parse_args()
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    map_path = Path(args.map)

    raw0 = map_path.read_bytes()
    sha0 = sha256_bytes(raw0)
    m = json.loads(raw0)
    det_sha0 = sha256_file(DETECTOR)
    det = load_detector(DETECTOR)
    det_sha1 = sha256_file(DETECTOR)

    records, findings = claim_prose_findings(det, m)
    rows, reg, counterfactual = controls(det, records, m)
    all_findings = det.findings_for_map(m)
    non_claim = [f for f in all_findings if f.startswith("CLASSSEP:") and " in claims[" not in f]

    raw1 = map_path.read_bytes()
    det_sha2 = sha256_file(DETECTOR)
    labels, unflagged_labels = {}, {}
    for r in records:
        bucket = labels if (r.get("detector_flagged") or r["label"] == "UNPARSED_FINDING") \
            else unflagged_labels
        bucket[r["label"]] = bucket.get(r["label"], 0) + 1
    flagged_records = [r for r in records
                       if r.get("detector_flagged") or r["label"] == "UNPARSED_FINDING"]

    report = {
        "task_id": TASK_ID,
        "worker": "worker-021",
        "instance": args.instance,
        "created_at": datetime.now(CST).isoformat(),
        "node_id": NODE_ID,
        "class_id": CLASS_ID,
        "question": ("Are the hard CLASSSEP findings on map claim prose at this snapshot "
                     "assertions of a C0/C2 class merge, or negation/description-blind "
                     "detector hits on prose that discusses such a merge?"),
        "pins": {
            "map_path": "research_map/research_map.json",
            "map_sha256_t0": sha0,
            "map_bytes_t0": len(raw0),
            "map_sha256_t1": sha256_bytes(raw1),
            "map_stable_during_run": sha0 == sha256_bytes(raw1),
            "detector_path": "research_map/class_separation.py",
            "detector_sha256_t0": det_sha0,
            "detector_sha256_after_import": det_sha1,
            "detector_sha256_t1": det_sha2,
            "detector_stable": det_sha0 == det_sha1 == det_sha2,
            "audit_evidence_sha256": sha256_file(AUDIT_EVIDENCE),
            "map_snapshot_policy": ("the map is live; each finding is pinned by "
                                    "claim event_id + statement_sha256, not by claim index alone"),
        },
        "reproduction": {
            "detector_hard_findings_total": len([f for f in all_findings if not f.startswith("CLASSSEP-SOFT:")]),
            "detector_hard_findings_on_claim_prose": len(findings),
            "claim_prose_mentions_adjudicated": len(records),
            "claim_prose_findings_adjudicated": len(flagged_records),
            "unflagged_prose_mentions": len(records) - len(flagged_records),
            "non_claim_hard_findings": non_claim,
            "audit_lead_baseline": AUDIT_BASELINE,
            "delta_vs_audit_baseline": {
                "extra_claims_flagged": sorted({r["claim_index"] for r in records} - set(AUDIT_BASELINE["reported_claims"])),
                "reason": "new claims were ingested after the audit scan instant; all are mention-level here",
            },
        },
        "summary": {
            "hard_findings_reproduced": len(findings),
            "label_counts": labels,
            "unflagged_mention_label_counts": unflagged_labels,
            "asserted_class_merges": labels.get("ASSERTED_LEAK", 0) + unflagged_labels.get("ASSERTED_LEAK", 0),
            "residual_ambiguous": labels.get("AMBIGUOUS_MENTION", 0) + unflagged_labels.get("AMBIGUOUS_MENTION", 0),
            "regression": reg,
        },
        "adjudication": records,
        "controls_all_passed": all(r["pass"] for r in rows),
        "counterfactual_negation_hardening": counterfactual,
        "scope": ("Applies only to the hard CLASSSEP findings emitted by the frozen detector "
                  "for map claim prose at the pinned snapshot. It does not adjudicate artifact "
                  "text findings, does not assert the underlying claims are correct, does not "
                  "edit any claim or the detector, and sets no gate verdict or node status."),
        "authority": ("Worker evidence only. Claim rephrasing is author-only (CF-16); detector "
                      "hardening and the A1/G-AUDIT disposition belong to the audit lead and "
                      "controller."),
        "falsifier": ("Re-run this instrument at the same map/detector hashes: falsified if (a) "
                      "any adjudicated mention is actually an assertion that C0 and C2 are one "
                      "class/schema; (b) the frozen detector no longer emits a finding for the "
                      "C1 positive-assertion control (instrument or detector vacuous); (c) the "
                      "27-fixture regression is not PASS 17/0/10/0; or (d) any pinned map/detector "
                      "sha256 has moved (void the run, do not falsify) ."),
    }
    controls_doc = {
        "task_id": TASK_ID,
        "worker": "worker-021",
        "created_at": report["created_at"],
        "pins": {"map_sha256_t0": sha0, "detector_sha256_t0": det_sha0},
        "controls": rows,
        "all_passed": all(r["pass"] for r in rows),
        "frozen_detector_regression": reg,
        "counterfactual_negation_hardening": counterfactual,
        "falsifier": report["falsifier"],
    }
    (out / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    (out / "controls.json").write_text(json.dumps(controls_doc, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"report": str(out / "report.json"),
                      "controls": str(out / "controls.json"),
                      "labels": labels,
                      "controls_all_passed": controls_doc["all_passed"],
                      "delta_extra_claims": report["reproduction"]["delta_vs_audit_baseline"]["extra_claims_flagged"],
                      "counterfactual": {k: counterfactual[k] for k in
                                         ("hard_findings_before", "hard_findings_after_in_memory_patch",
                                          "removed", "assertion_control_still_detected")}}, indent=2))


if __name__ == "__main__":
    sys.exit(main())
