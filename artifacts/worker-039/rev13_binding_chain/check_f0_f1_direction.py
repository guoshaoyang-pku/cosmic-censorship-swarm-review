#!/usr/bin/env python3
"""Check K — cross-artifact direction divergence on variant SET (F0 vs F1 vs supplement vs registry).

worker-039, W039-REV13-BINDCHAIN-01. REC-12 item (3) corrects the F1 visibility strictness and
explicitly does not touch the G-F0-frozen declared taxonomy. FROZEN rev29's own residual note says
the inverted SET direction survives in four other places. This tool measures, per target, whether
the surviving statement is a *live normative* assertion that contradicts the repaired F1, or a
*historical record* (a superseded-reading ledger entry marked resolved/before/void), which is
not a contradiction.

Targets (all read-only):
  schemas/af_wcc_vacuum.yaml                              (repaired F1, rev13)
  research_map/formulation_taxonomy.yaml                  (G-F0-frozen declared taxonomy)
  artifacts/formulation/formulation_taxonomy.yaml         (F0 companion supplement / contract)
  artifacts/formulation/VARIANT_REGISTRY.json             (SET variant strength)
  artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json

Classification of a polarity hit:
  LIVE        the sentence asserts the strength as current fact ("the set-based reading is
              strictly stronger")
  HISTORICAL  the sentence/line is explicitly marked as superseded, resolved, a former reading,
              a delta ledger's `from` side, or is a bracketed revision note
  AGREEMENT   polarity equals the repaired F1's direction
  DIVERGENT   LIVE and polarity is the opposite of F1's

Exit 0 iff no DIVERGENT hit. Exit 1 otherwise. This is a finding for lead adjudication, not a
gate verdict.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
F1 = "schemas/af_wcc_vacuum.yaml"
TARGETS = [
    "research_map/formulation_taxonomy.yaml",
    "artifacts/formulation/formulation_taxonomy.yaml",
    "artifacts/formulation/VARIANT_REGISTRY.json",
    "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json",
]

STRONGER = re.compile(r"strict(?:ly)?[\s_]+stronger", re.I)
WEAKER = re.compile(r"strict(?:ly)?[\s_]+weaker", re.I)
EQUIV = re.compile(r"\bequivalen\w*", re.I)
SETCTX = re.compile(r"set[-_ ]?based|variant[\s_\"']*SET|union of J|J\^?-\(I\+\)|J-\(I\+\)", re.I)
REVNOTE = re.compile(r"\[[^\]]*(?:rev\d+|corrected|superseded)[^\]]*\]", re.I)
HISTORICAL = re.compile(
    r"superseded|resolved|was stronger|formerly|previously|used this set-based|"
    r"f0_reading|wcc_text_before|before the 2026|\"from\"|regenerated|unused", re.I)


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def polarity(text: str) -> str:
    t = REVNOTE.sub(" ", str(text))
    has_s, has_w, has_e = bool(STRONGER.search(t)), bool(WEAKER.search(t)), bool(EQUIV.search(t))
    # an explicit "NOT equivalent" is a strength claim, not an equivalence claim
    if re.search(r"\bnot\s+equivalen", t, re.I):
        has_e = False
    if has_w and not has_s:
        return "WEAKER"
    if has_s and not has_w:
        return "STRONGER"
    if has_e and not has_s and not has_w:
        return "EQUIVALENT"
    if has_s or has_w or has_e:
        return "MIXED"
    return "SILENT"


def f1_direction() -> tuple[str, dict]:
    doc = yaml.safe_load((ROOT / F1).read_text())
    for v in doc.get("class_identity_variants") or []:
        if isinstance(v, dict) and "set" in str(v.get("kind", "")).lower():
            return polarity(v.get("relation", "")), {"kind": v.get("kind"),
                                                     "relation": str(v.get("relation"))[:300]}
    return "UNKNOWN", {}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    f1d, f1_block = f1_direction()
    opposite = {"WEAKER": {"STRONGER"}, "EQUIVALENT": {"STRONGER", "WEAKER"},
                "STRONGER": {"WEAKER"}, "MIXED": {"STRONGER", "WEAKER"}, "UNKNOWN": set()}[f1d]

    results, divergent_total = [], 0
    for rel in TARGETS:
        p = ROOT / rel
        if not p.exists():
            results.append({"target": rel, "present": False, "divergent": False, "why": "missing"})
            continue
        lines = p.read_text().splitlines()
        hits = []
        for i, l in enumerate(lines, 1):
            # polarity is read ONLY on the line carrying the strength word; the context window is
            # used only to decide that the claim is about the set-based reading
            pol = polarity(l)
            if pol == "SILENT":
                continue
            window = " ".join(lines[max(0, i - 3):min(len(lines), i + 2)])
            if not SETCTX.search(window):
                continue
            # a line that is the `from` side of a delta ledger is a record of the old reading
            is_hist = bool(HISTORICAL.search(l)) or bool(re.search(r"\"from\"\s*:", l))
            # a delta ledger's `to` side is a counterfactual, not a claim about the live schema
            if re.search(r"\"to\"\s*:", l):
                is_hist = True
            if pol == f1d:
                kind = "AGREEMENT"
            elif is_hist:
                kind = "HISTORICAL"
            elif pol in opposite:
                kind = "DIVERGENT"
            else:
                kind = "OTHER"
            if kind == "DIVERGENT":
                divergent_total += 1
            hits.append({"line": i, "polarity": pol, "class": kind,
                         "excerpt": l.strip()[:240]})
        results.append({"target": rel, "present": True, "sha256": sha(p), "hits": hits,
                        "divergent": any(h["class"] == "DIVERGENT" for h in hits)})

    report = {
        "check_id": "K",
        "task_id": "W039-REV13-BINDCHAIN-01",
        "f1": {"path": F1, "sha256": sha(ROOT / F1), "direction": f1d, "set_variant_block": f1_block},
        "targets": results,
        "divergence_count": divergent_total,
        "verdict": "DIVERGENT" if divergent_total else "CONSISTENT",
        "note": ("Local-window lexical polarity test on the set-based reading, with historical-record "
                 "exclusion. check_taxonomy_consistency.py compares axes.family / regularity / "
                 "conclusion_type / genericity and does NOT compare predicate strength, so a clean "
                 "CONSISTENT report from it does not clear a direction divergence. The F0 declared "
                 "taxonomy is G-F0-frozen: a LIVE divergence there cannot be repaired without "
                 "voiding G-F0."),
    }
    text = json.dumps(report, indent=2, sort_keys=True)
    print(text)
    if args.out:
        outp = Path(args.out)
        if not outp.is_absolute():
            outp = ROOT / outp
        outp.write_text(text + "\n")
    return 1 if divergent_total else 0


if __name__ == "__main__":
    sys.exit(main())
