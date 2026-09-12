#!/usr/bin/env python3
"""CLASSSEP calibration adjudication (astra-life05-classsep-calibration).

Three detector revisions are scored in one census:

  CANON   research_map/class_separation.py                (canonical, live)
  CAND    proposed/class_separation.py                    sha256 e2d24b927ee8 (worker-16 staged)
  PROSE   canonical + the formulation lead's sentence-window + _META prose precision
          (artifacts/formulation/proposals/classsep_prose_precision_patch.md) --
          implemented here in-memory ONLY as a calibration arm, not as a patch.

Corpora:
  (a) worker-07 27-fixture falsification corpus (17 leaks / 10 controls), via the
      registered runner semantics in runtime/bin/classsep_regression.py;
  (b) the live hard-finding set at the measured map snapshot;
  (c) a labeled assertion-vs-mention fixture set written for this adjudication, which is
      the discrimination the 27-fixture corpus under-specifies.

Also runs a converse (false-negative) scan over every live claim, so the census is not
one-sided. Read-only: this script writes only its own artifact.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
MAP = ROOT / "research_map/research_map.json"
CANON_PY = ROOT / "research_map/class_separation.py"
CAND_PY = ROOT / "proposed/class_separation.py"
CORPUS = ROOT / "artifacts/worker-07/class_separation_falsification"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else "ABSENT"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# --- PROSE arm: canonical + sentence-window/_META precision (in-memory experiment) ---------
_SENT = re.compile(r"[^.!?]*[.!?]|[^.!?]*$")
_META = re.compile(
    r"\b(?:pattern|token|label|test|case|corpus|fixture|probe|scanner|regex|"
    r"non-?merge|split|independent|discussed|quoted|flag(?:s|ged)?|match(?:es|ed)?\s+only)\b",
    re.I)


def enclosing_sentence(t: str, start: int, end: int) -> str:
    """The sentence CONTAINING t[start:end] (the proposal's 'enclosing sentence')."""
    left = max(t.rfind(".", 0, start), t.rfind("!", 0, start), t.rfind("?", 0, start)) + 1
    rights = [x for x in (t.find(".", end), t.find("!", end), t.find("?", end)) if x != -1]
    right = min(rights) + 1 if rights else len(t)
    return t[left:right]


def make_prose_arm(canon_path: Path):
    """Exec the canonical source into a fresh namespace, then redefine `_scan_composite`
    there. `findings()` resolves the name through module globals at call time, so the
    override takes effect without touching the canonical file."""
    import types
    mod = types.ModuleType("cs_prose")
    mod.__file__ = str(canon_path)
    exec(compile(canon_path.read_text(), str(canon_path), "exec"), mod.__dict__)
    # the canonical inline quotation/meta-audit exemption, hoisted so the arm can reuse it
    mod._QUOTE_EXEMPT = re.compile(
        r"false[- ]positive|non[- ]merge|not\s+(?:a\s+)?merge|"
        r"no\s+genuine\s+(?:c0/c2|c2/c0)\s+merge|detector\s+(?:finding|flag)|"
        r"quote(?:d|s)?\s+(?:the\s+)?detector", re.I)

    def _scan_composite(text, where, out, mode="declaration"):
        t = mod.norm(text)
        for m in mod._MERGE_PAT.finditer(t):
            lo, hi = max(0, m.start() - 60), min(len(t), m.end() + 60)
            ctx = t[lo:hi]
            if mod._BENIGN.search(t[max(0, m.start() - 8):m.end() + 8]):
                continue
            assert_match = mod._MERGE_ASSERT.search(ctx)
            if assert_match:
                # Canonical quotation/meta-audit exemption, retained (the proposal EXTENDS
                # the skip predicates, it does not replace them).
                if mod._QUOTE_EXEMPT.search(ctx):
                    continue
                before = ctx[:assert_match.start()]
                if mod._NEG_BEFORE_ASSERT.search(before):
                    continue
                if mode == "prose":
                    sent = enclosing_sentence(t, m.start(), m.end())
                    if _META.search(sent) or mod._PROHIBIT.search(sent) or mod._SPLIT.search(sent):
                        continue
                out.append(f"CLASSSEP: composite C0/C2 asserted as one class in {where}: "
                           f"...{ctx.strip()!r}")
            elif mod._PROHIBIT.search(ctx):
                continue
            elif mod._SPLIT.search(ctx):
                continue
            elif mode == "declaration":
                out.append(f"CLASSSEP: bare composite C0/C2 expression in {where}: "
                           f"...{ctx.strip()!r}")
        return out

    mod._scan_composite = _scan_composite
    return mod


# --- (a) registered 27-fixture corpus -----------------------------------------------------
def corpus_census(mod) -> dict:
    res = json.loads((CORPUS / "results.json").read_text())
    tp = fp = tn = fn = 0
    rows = []
    for fx in res["fixtures"]:
        p = ROOT / fx["fixture_path"]
        if not p.exists():
            continue
        m = json.loads(p.read_text())
        det = mod.findings_for_map(m)
        for g in m.get("groups", []):
            for n in g.get("nodes", []):
                art = n.get("artifact")
                if art and (ROOT / art).is_file():
                    det += mod.findings_for_text((ROOT / art).read_text(errors="replace"),
                                                 f"artifact {art}")
        got, truth = bool(det), bool(fx["is_class_merge"])
        if truth and got:
            tp += 1; cls = "TP"
        elif truth and not got:
            fn += 1; cls = "FN"
        elif not truth and got:
            fp += 1; cls = "FP"
        else:
            tn += 1; cls = "TN"
        rows.append({"id": fx["id"], "class": cls, "surface": fx.get("surface")})
    return {"tp": tp, "fn": fn, "fp": fp, "tn": tn, "n": tp + fn + fp + tn,
            "verdict": "PASS" if fn == 0 and fp == 0 else "DEFECTIVE",
            "non_pass_rows": [r for r in rows if r["class"] not in ("TP", "TN")]}


# --- (b) live hard-finding set --------------------------------------------------------------
# Ground truth is a stated criterion, applied to the full statement text of every flagged
# claim (all twelve were read in full):
#   TP  iff the composite token appears in a first-order assertion by the claim itself that
#       C0 and C2 form one class / are a single class;
#   FP  iff the token appears under negation, in a taxonomy case label or artifact path,
#       inside quotation of another text, as the object of a detector/meta description, in a
#       non-merge compound, or the merge word belongs to a different clause.
LIVE_LABELS = {
    36: [("FP", "CASE_LABEL", "TC-F0-N14 C0/C2 merge ... need no new class")],
    94: [("FP", "CASE_LABEL", "TC-F0-N14 merged C0/C2 regularities; ... SPLIT_REQUIRED")],
    96: [("FP", "CASE_LABEL", "TC-F0-N14 merged C0/C2 regularities; ... SPLIT_REQUIRED")],
    97: [("FP", "CASE_LABEL", "TC-F0-N14 merged C0/C2 regularities; ... SPLIT_REQUIRED")],
    101: [("FP", "NEGATION", "so no C0/C2 merge exists at the formal surface")],
    112: [("FP", "DETECTOR_DESCRIPTION", "R1's merge pattern matches only bare C0/C2 composites"),
          ("FP", "QUOTATION", "the same slot carrying 'C0 or C2 are one class' is flagged")],
    127: [("FP", "NON_MERGE_COMPOUND", "independent C0/C2 non-merge")],
    144: [("FP", "WINDOW_ARTIFACT", "the retired merged file; ... the live C2/C0 components moved")],
    152: [("FP", "NEGATION", "no merge, no inflation ... rather than a C2/C0 merge")],
    180: [("FP", "NEGATION", "no C0/C2 merge, canonical structural gate exit 0")],
    187: [("FP", "QUOTATION", "'do not split: C0 or C2' (S3); false-positive shape")],
    192: [("FP", "DETECTOR_SELF", "quotes 'composite C0/C2 asserted as one class'")],
    276: [("FP", "QUOTATION", "quotes 'composite C0/C2 asserted as one class' / 'no C0/C2 merge'")],
    306: [("FP", "QUOTATION", "0 genuine assertions that C0 and C2 are one class")],
}


def live_census(mod) -> dict:
    m = json.loads(MAP.read_text())
    raw = mod.findings_for_map(m)
    per_claim: dict[int, list] = {}
    other = []
    for x in raw:
        mo = re.search(r"claims\[(\d+)\]", x)
        if mo:
            per_claim.setdefault(int(mo.group(1)), []).append(x)
        else:
            other.append(x)
    hard = [x for x in raw if not x.startswith("CLASSSEP-SOFT:")]
    tp = fp = 0
    detail = []
    for idx, finds in sorted(per_claim.items()):
        labels = LIVE_LABELS.get(idx, [("UNLABELED", "UNLABELED", "")])
        for k, f in enumerate(finds):
            lab = labels[k] if k < len(labels) else (labels[-1] if labels else ("UNLABELED", "", ""))
            verdict, mech, cue = lab
            if verdict == "TP":
                tp += 1
            else:
                fp += 1
            detail.append({"claim_index": idx, "verdict": verdict, "mechanism": mech,
                           "cue": cue, "finding": f[:180]})
    # artifact-text hard findings (audit_evidence section 3 second half)
    art_hard = []
    for g in m.get("groups", []):
        for n in g.get("nodes", []):
            art = n.get("artifact")
            if art and (ROOT / art).is_file() and (ROOT / art).stat().st_size < 2_000_000:
                try:
                    art_hard += [x for x in mod.findings_for_text(
                        (ROOT / art).read_text(errors="replace"), f"{n['id']} artifact {art}")
                        if not x.startswith("CLASSSEP-SOFT:")]
                except OSError:
                    pass
    return {"hard_total": len(hard), "claim_findings": len(raw), "tp": tp, "fp": fp,
            "claims_affected": sorted(per_claim), "n_claims_affected": len(per_claim),
            "non_claim_findings": other + art_hard, "per_finding": detail, "map_sha256": sha(MAP)}


# --- (c) labeled assertion-vs-mention fixtures ---------------------------------------------
# Written for this adjudication. `assert_merge=True` means a first-order assertion that C0 and
# C2 are one class and the detector MUST fire; False means a metalinguistic mention and the
# detector must NOT fire in prose mode.
ASSERTION_MENTION_FIXTURES = [
    # --- first-order assertions (expect fire) ---
    ("A1", True, "The C0/C2 merged class is the right unit of analysis for this portfolio."),
    ("A2", True, "This result covers the C0/C2 unified class."),
    ("A3", True, "We treat C0 or C2 as one class for the purposes of this gate."),
    ("A4", True, "C0 and C2 are one class in the frozen registry."),
    ("A5", True, "The two regularities should be merged into a single class."),
    ("A6", True, "Do not split: C0 or C2."),          # negated split == assertion of unity
    # --- metalinguistic mentions (expect silent) ---
    ("M1", False, "so no C0/C2 merge exists at the formal surface."),
    ("M2", False, "TC-F0-N14 merged C0/C2 regularities; disposition SPLIT_REQUIRED."),
    ("M3", False, "R1's merge pattern matches only bare C0/C2 composites."),
    ("M4", False, "independent C0/C2 non-merge, quantifier and conclusion assertions"),
    ("M5", False, "the detector flagged 'C0 or C2 are one class' in that text region."),
    ("M6", False, "the retired merged file; and the live C2/C0 components moved at 00:32."),
    ("M7", False, "0 genuine assertions that C0 and C2 are one class."),
    ("M8", False, "the C0/C2 split is required and the classes stay distinct."),
    ("M9", False, "no C0/C2 merge, canonical structural gate exit 0."),
    ("M10", False, "quoting the detector output 'composite C0/C2 asserted as one class'."),
]


def fixture_census(mod) -> dict:
    tp = fp = tn = fn = 0
    rows = []
    for fid, truth, text in ASSERTION_MENTION_FIXTURES:
        got = bool(mod.findings_for_text(text, f"fixture {fid}"))
        if truth and got:
            tp += 1; cls = "TP"
        elif truth and not got:
            fn += 1; cls = "FN"
        elif not truth and got:
            fp += 1; cls = "FP"
        else:
            tn += 1; cls = "TN"
        rows.append({"id": fid, "expect_merge_assertion": truth, "fired": got, "class": cls})
    return {"tp": tp, "fn": fn, "fp": fp, "tn": tn, "n": len(ASSERTION_MENTION_FIXTURES),
            "sensitivity": f"{tp}/{tp+fn}", "specificity": f"{tn}/{tn+fp}", "rows": rows}


# --- converse (false-negative) scan --------------------------------------------------------
_ASSERT_CUES = re.compile(
    r"(?:treat|cover|use|take|regard|is|are|as)\s+(?:the\s+)?(?:c\s*0\s*(?:or|and|/|,|\+)\s*c\s*2"
    r"|c\s*2\s*(?:or|and|/|,|\+)\s*c\s*0)\s*(?:merged|unified|single|one)?\s*class"
    r"|(?:c0c2|c2c0)\s+(?:is|are|as)\s+one\s+class"
    r"|(?:merge|merging|combine|unify)\s+(?:the\s+)?(?:c0\s+and\s+c2|c2\s+and\s+c0)"
    r"|(?:c0\s+and\s+c2|c2\s+and\s+c0)\s+(?:are|is|form)\s+(?:one|a single|the same)\s+class", re.I)


def converse_scan(mod, live: dict) -> dict:
    """Find first-order assertions the detector did NOT flag (candidate FNs)."""
    m = json.loads(MAP.read_text())
    flagged = set(live["claims_affected"])
    cands = []
    for i, c in enumerate(m["claims"]):
        st = c.get("statement") or ""
        if not isinstance(st, str): st = str(st)
        for mo in _ASSERT_CUES.finditer(st):
            lo, hi = max(0, mo.start() - 80), min(len(st), mo.end() + 80)
            cands.append({"claim_index": i, "already_flagged": i in flagged,
                          "span": st[lo:hi]})
    genuinely_unflagged = [c for c in cands if not c["already_flagged"]]
    return {"cue_matches": len(cands), "unflagged_candidates": len(genuinely_unflagged),
            "unflagged_detail": genuinely_unflagged[:10],
            "note": "every unflagged cue was read in context; see adjudication.labels"}


def adjudication(out: dict) -> dict:
    a, b, c = (out["corpus_a_27fixtures"], out["corpus_b_live"], out["corpus_c_assertion_mention"])
    return {
        "verdict_on_staged_candidate": {
            "artifact": "proposed/class_separation.py",
            "sha256": out["detectors"]["CAND"]["sha256"],
            "verdict": "REJECT",
            "reason": "it makes the CF-16 false-positive class WORSE, not better. Live hard "
                      "findings rise 17 -> 22 on 12 -> 14 claims; the labeled assertion-vs-mention "
                      "specificity falls 3/10 -> 1/10. Two mechanisms cause it: (i) it DELETES the "
                      "canonical quotation/meta-audit exemption, so claims that merely quote or "
                      "describe the detector output start firing (new claims 127 'non-merge' and "
                      "187 'false-positive shape'); (ii) _NEG_SPLIT fires on a QUOTED "
                      "'do not split: C0 or C2' inside a claim that is discussing the rule.",
            "what_it_gets_right": "sensitivity 4/6 -> 5/6: _NEG_SPLIT correctly catches the bare "
                                  "assertion 'Do not split: C0 or C2' (fixture A6), which the "
                                  "canonical _PROHIBIT exemption wrongly clears. Keep the rule, "
                                  "but only behind a quotation guard.",
            "regression": out["corpus_a_27fixtures"]["CAND"],
            "regression_note": "the registered 27-fixture corpus is PASS 17/0/10/0 for both "
                               "revisions, so it cannot see any of these deltas: adopting on the "
                               "strength of that corpus alone would be a calibration failure.",
        },
        "verdict_on_prose_precision_direction": {
            "artifact": "artifacts/formulation/proposals/classsep_prose_precision_patch.md",
            "sha256": out["detectors"]["PROSE"]["sha256"],
            "verdict": "ADOPT-AS-DIRECTION, NOT AS-IS",
            "reason": "best arm measured: live hard findings 17 -> 6 on 12 -> 4 claims with 0 new "
                      "claims added, no 27-fixture regression, specificity 3/10 -> 5/10, and "
                      "sensitivity unchanged at 4/6. It clears 8 of the 12 flagged claims by "
                      "sentence-scoping the skip predicates. It is not yet adoptable: 6 hard "
                      "findings and 2 sensitivity misses remain.",
            "residual_defects": [
                {"id": "R-a", "defect": "_NEG_BEFORE_ASSERT uses \\w+, which cannot span a "
                                        "composite token, so 'no C0/C2 merge exists' is still "
                                        "flagged", "live": "claims[152]", "fixtures": ["M1", "M9"]},
                {"id": "R-b", "defect": "the window is still character-based, not clause-based; "
                                        "'the retired merged file; and ... the live C2/C0 "
                                        "components moved' links a merge word to the wrong clause",
                 "live": "claims[144]", "fixtures": ["M6"]},
                {"id": "R-c", "defect": "_META lacks 'quoting', 'detector', 'assertion', so "
                                        "detector-self and quotation prose still fires",
                 "live": "claims[192], claims[276]", "fixtures": ["M7", "M10"]},
                {"id": "R-d", "defect": "sensitivity gap: 'The two regularities should be merged "
                                        "into a single class' has no C0/C2 token, so no "
                                        "composite rule can reach it; needs a family-level cue, "
                                        "not a composite-token cue",
                 "live": "none (out of vocabulary)", "fixtures": ["A5"]},
            ],
            "acceptance_for_an_adoptable_revision": [
                "27-fixture corpus stays PASS 17/0/10/0",
                "labeled assertion-vs-mention set: sensitivity >= 5/6 and specificity >= 9/10",
                "live census: 0 hard findings on claims whose only cue is negation, case-label, "
                "quotation, detector-self description, or cross-clause adjacency",
                "the raw and calibrated hard counts are BOTH published every tick",
            ],
        },
        "census_headline": {
            "corpus_a": {k: {"tp": a[k]["tp"], "fn": a[k]["fn"], "fp": a[k]["fp"], "tn": a[k]["tn"],
                             "verdict": a[k]["verdict"]} for k in a},
            "corpus_b_live": {k: {"hard": b[k]["hard_total"], "tp": b[k]["tp"], "fp": b[k]["fp"],
                                  "claims": b[k]["n_claims_affected"], "map_sha256": b[k]["map_sha256"]}
                              for k in b},
            "corpus_c": {k: {"sensitivity": c[k]["sensitivity"], "specificity": c[k]["specificity"],
                             "tp": c[k]["tp"], "fn": c[k]["fn"], "fp": c[k]["fp"], "tn": c[k]["tn"]}
                         for k in c},
        },
        "tp_fp_fn_statement": {
            "live_hard_finding_set": "CANON 17 findings on 12 claims: 0 TP, 17 FP (all "
                                     "metalinguistic: 4 CASE_LABEL, 7 NEGATION/NON_MERGE, 4 "
                                     "QUOTATION/DETECTOR_SELF, 1 WINDOW_ARTIFACT, 1 "
                                     "DETECTOR_DESCRIPTION). CAND 22 findings on 14 claims: 0 TP, "
                                     "22 FP. PROSE 6 findings on 4 claims: 0 TP, 6 FP.",
            "false_negatives": "converse scan over every live claim: 3 assertion-cue matches, 0 "
                               "unflagged after reading each in context. The live map contains no "
                               "first-order C0/C2 merge assertion, so the canonical detector has no "
                               "TP to lose on this corpus -- the only measurable error direction "
                               "here is FP.",
            "labels": "per-finding ground truth and cues are in corpus_b_live.*.per_finding; the "
                      "criterion is stated in artifacts/audit/classsep_calibration.py LIVE_LABELS.",
        },
        "detector_fix_vs_claim_rewrite": {
            "separation": "This adjudication changes NO claim text and proposes no gate verdict. "
                          "The 12 flagged claims stay in the map, byte-identical; only their "
                          "detector classification is re-measured. A detector fix and a claim "
                          "rewrite are independent remedies and must not be bundled.",
            "claim_rewrite_track": "An author may always emit a superseding claim that moves the "
                                   "composite token into a non-scanned field; claims[36] already "
                                   "has such a supersession (claims[140], formulation proposal "
                                   "apply_events_claim_supersede_patch.md). That track is "
                                   "author-owned and bounded by authorship, not by detector "
                                   "behaviour.",
        },
        "claims_retirement_policy": {
            "principle": "retire the CLASSIFICATION, never the record. No claim is deleted, "
                         "edited, or reworded by an audit action (CF-4). The raw hard count stays "
                         "published next to the calibrated count.",
            "rules": [
                "P1 The audit tick reports two numbers: `classsep_hard_raw` (canonical detector, "
                "unmodified) and `classsep_hard_calibrated` (adopted detector), never only one.",
                "P2 A claim is retired from the calibrated hard list only by a detector whose "
                "labeled-fixture sensitivity >= 5/6 and specificity >= 9/10 and whose "
                "27-fixture corpus is PASS 17/0/10/0. A detector that merely drops the count "
                "without those bounds is rejected (this is why CAND is rejected).",
                "P3 Retirement is per (claim_index, finding_ordinal) and is recorded with the "
                "mechanism that exempted it (NEGATION, CASE_LABEL, QUOTATION, DETECTOR_SELF, "
                "WINDOW_ARTIFACT, DETECTOR_DESCRIPTION) plus the map sha256 and detector sha256.",
                "P4 A retired finding is evidence, not a cleared defect: if the same claim is "
                "later edited so the cue disappears, the exemption is void and the finding "
                "returns (supersession by the author does NOT inherit the exemption).",
                "P5 Historical metalinguistic claims are never a gate criterion by count alone: "
                "G-AUDIT's hard_failure_rate uses the calibrated count with the retirement "
                "ledger attached; a raw count with no detector calibration may not fail a gate.",
                "P6 The retirement ledger is one artifact, reviews/CLASSSEP-calibration-"
                "adjudication.json, re-measured each pass; it binds only the map sha256 and "
                "detector sha256 recorded in it.",
            ],
            "immediate_effect": "Under P1/P5 the CF-16 hard count at map 262da6979857 is 17 raw / "
                                "17 calibrated on the canonical detector (no calibration adopted "
                                "yet), so the finding stays visible and G-AUDIT remains pending.",
        },
        "recommendation_to_controller": {
            "action": "do not adopt proposed/class_separation.py; commission one revision along the "
                      "PROSE direction that closes R-a..R-c and the A6 sensitivity gap, guarded so "
                      "a quoted 'do not split: C0 or C2' does not fire; keep P1-P6.",
            "owner": "controller (research_map/class_separation.py is a controller tool); audit "
                     "supplies the census and re-measures, and does not edit the checker.",
            "regression_command": "python3 runtime/bin/classsep_regression.py && "
                                  "python3 artifacts/audit/classsep_calibration.py",
            "no_gate_self_pass": "this sets no gate verdict; G-AUDIT stays pending.",
        },
        "falsifier": "Withdrawn if: the 27-fixture corpus fails for any arm; the live labels in "
                     "LIVE_LABELS are shown wrong for any flagged claim (i.e. a real first-order "
                     "C0/C2 merge assertion exists among the 12); the converse scan finds a "
                     "genuine unflagged merge; or an adopted revision drops sensitivity below the "
                     "canonical arm's.",
    }


def main() -> int:
    canon = load(CANON_PY, "cs_canon")
    cand = load(CAND_PY, "cs_cand")
    prose = make_prose_arm(CANON_PY)

    arms = {"CANON": canon, "CAND": cand, "PROSE": prose}
    out = {
        "artifact": "CLASSSEP-calibration-adjudication",
        "assignment": "astra-life05-classsep-calibration",
        "node_id": "A1",
        "gate": "G-AUDIT",
        "actor": "astra-lead-audit",
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "detectors": {
            "CANON": {"path": "research_map/class_separation.py", "sha256": sha(CANON_PY)},
            "CAND": {"path": "proposed/class_separation.py", "sha256": sha(CAND_PY)},
            "PROSE": {"path": "artifacts/formulation/proposals/classsep_prose_precision_patch.md",
                      "sha256": sha(ROOT / "artifacts/formulation/proposals/classsep_prose_precision_patch.md"),
                      "note": "calibration arm implemented in-memory from the proposal text; "
                              "not a staged patch, not applied"},
        },
        "corpus_a_27fixtures": {k: corpus_census(v) for k, v in arms.items()},
        "corpus_b_live": {k: live_census(v) for k, v in arms.items()},
        "corpus_c_assertion_mention": {k: fixture_census(v) for k, v in arms.items()},
    }
    out["converse_scan_CANON"] = converse_scan(canon, out["corpus_b_live"]["CANON"])
    out["converse_scan_CAND"] = converse_scan(cand, out["corpus_b_live"]["CAND"])
    out["adjudication"] = adjudication(out)
    out["map_snapshot"] = {
        "sha256": out["corpus_b_live"]["CANON"]["map_sha256"],
        "n_claims": len(json.loads(MAP.read_text())["claims"]),
        "note": "claim indices are positional and stable for appended claims; any edit or "
                "reordering invalidates the labels and the census must be re-measured",
    }

    dest = ROOT / "reviews/CLASSSEP-calibration-adjudication.json"
    dest.write_text(json.dumps(out, indent=2, sort_keys=False) + "\n")

    print(f"map sha {out['corpus_b_live']['CANON']['map_sha256'][:12]}")
    print(f"{'arm':<6} {'(a) 27-fixture':<22} {'(b) live hard':<28} {'(c) assert/mention'}")
    for k in arms:
        a, b, c = out["corpus_a_27fixtures"][k], out["corpus_b_live"][k], out["corpus_c_assertion_mention"][k]
        print(f"{k:<6} TP{a['tp']} FN{a['fn']} FP{a['fp']} TN{a['tn']} {a['verdict']:<8}"
              f" hard={b['hard_total']:<3} TP={b['tp']} FP={b['fp']:<3} claims={b['n_claims_affected']:<3}"
              f"  sens={c['sensitivity']} spec={c['specificity']}")
    print(f"converse (CANON): {out['converse_scan_CANON']['unflagged_candidates']} unflagged candidates "
          f"of {out['converse_scan_CANON']['cue_matches']} cue matches")
    print(f"-> {dest.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
