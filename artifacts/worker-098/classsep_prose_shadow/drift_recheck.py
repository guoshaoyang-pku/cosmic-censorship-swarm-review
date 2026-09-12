#!/usr/bin/env python3
"""W098-CLASSSEP-PROSE-SHADOW-01 drift recheck.

The canonical detector moved c266dbceca87 -> a8c04fc31e4a at 00:52:00 (a controller-applied
narrow meta-quotation skip, NOT the lead's proposal). Pass 1 therefore binds a superseded hash
and is advisory. This recheck measures the SAME batteries against the live detector, on the
frozen map snapshot (comparable to pass 1) and on the live map (liveness). Read-only.
"""
from __future__ import annotations

import difflib
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
SNAP = HERE / "snapshot"
RAW = HERE / "raw"
sys.path.insert(0, str(ROOT / "research_map"))


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


live_path = ROOT / "research_map/class_separation.py"
live_sha = sha(live_path)
old_text = (SNAP / "class_separation.canonical.py").read_text()
new_text = live_path.read_text()
diff = list(difflib.unified_diff(old_text.splitlines(keepends=True), new_text.splitlines(keepends=True)))
removed = [l for l in diff if l.startswith("-") and not l.startswith("---")]
added = [l for l in diff if l.startswith("+") and not l.startswith("+++")]

canon = load_module("w098_canon2", SNAP / "class_separation.canonical.py")
live = load_module("w098_live2", live_path)

# ---- corpus
corpus = json.loads((ROOT / "artifacts/worker-07/class_separation_falsification/results.json").read_text())


def run_corpus(mod):
    tp = fp = tn = fn = 0
    for fx in corpus["fixtures"]:
        p = ROOT / fx["fixture_path"]
        if not p.exists():
            continue
        m = json.loads(p.read_text())
        det = mod.findings_for_map(m)
        for g in m.get("groups", []):
            for n in g.get("nodes", []):
                art = n.get("artifact")
                if art and (ROOT / art).is_file():
                    det += mod.findings_for_text((ROOT / art).read_text(errors="replace"), f"artifact {art}")
        got, truth = bool(det), bool(fx["is_class_merge"])
        tp += truth and got; fn += truth and not got; fp += (not truth) and got; tn += (not truth) and not got
    return {"tp": tp, "fn": fn, "tn": tn, "fp": fp, "verdict": "PASS" if fn == 0 and fp == 0 else "DEFECTIVE"}


# ---- probes
FP_PROBES = [
    "so no C0/C2 merge exists at the formal surface.",
    "2 SPLIT_REQUIRED (TC-F0-N14 merged C0/C2 regularities; the two rows require a split)",
    "R1's merge pattern matches only bare C0/C2 composites",
    "This is a class separation check: independent C0/C2 non-merge evidence.",
]
TP_PROBES = [
    "The C0/C2 merged class is the right unit of analysis for this portfolio.",
    "This result covers the C0/C2 unified class.",
]
FN_PROBES = [
    ("FN1_meta_case", "The C0/C2 merged class is the only case we consider."),
    ("FN2_meta_test", "We test that the C0/C2 unified class is the right unit."),
    ("FN3_meta_corpus", "This corpus treats the C0/C2 as one class."),
    ("FN4_meta_independent", "The independent C0/C2 merged class is our unit of analysis."),
    ("FN5_meta_pattern", "The C0/C2 combined pattern is the portfolio's chosen unit."),
    ("FN6_neg_scope", "It is not the case that the classes are separate; the C0/C2 are one class."),
]


def fires(mod, text):
    out = []
    mod._scan_composite(text, "probe", out, mode="prose")
    return out


def map_hard(mod, m):
    hard = [x for x in mod.findings_for_map(m) if not str(x).startswith("CLASSSEP-SOFT:")]
    for g in m.get("groups", []):
        for n in g.get("nodes", []):
            art = n.get("artifact")
            p = ROOT / art if art else None
            if p and p.is_file() and p.stat().st_size < 2_000_000:
                hard += [x for x in mod.findings_for_text(p.read_text(errors="replace"),
                                                          f"{n['id']} artifact {art}")
                         if not str(x).startswith("CLASSSEP-SOFT:")]
    return hard


snap_map = json.loads((SNAP / "research_map.pinned.json").read_text())
live_map_path = ROOT / "research_map/research_map.json"
live_map_sha = sha(live_map_path)
live_map = json.loads(live_map_path.read_text())

prob_rows = {"fp": [], "tp": [], "fn": []}
for t in FP_PROBES:
    prob_rows["fp"].append({"text": t, "canonical": bool(fires(canon, t)), "live": bool(fires(live, t)),
                            "expected_live": False})
for t in TP_PROBES:
    prob_rows["tp"].append({"text": t, "canonical": bool(fires(canon, t)), "live": bool(fires(live, t)),
                            "expected_live": True})
for n, t in FN_PROBES:
    prob_rows["fn"].append({"name": n, "text": t, "canonical": bool(fires(canon, t)),
                            "live": bool(fires(live, t)), "over_suppressed": bool(fires(canon, t)) and not fires(live, t)})

GROWTH = [
    ("G1_meta_mention", "The audit flags our discussion of the C0/C2 merged label, but that is a metalinguistic mention, not a proposed merge."),
    ("G2_rejected_hypothesis", "We analysed the C0/C2 unified class only as a rejected hypothesis; the portfolio keeps the two classes split."),
    ("G3_counting_prose", "This note measures how often the C0/C2 combined pattern appears in review prose."),
]
growth = [{"name": n, "canonical": len([x for x in canon.findings({"statement": t}, n, mode="prose")
                                        if not x.startswith("CLASSSEP-SOFT:")]),
           "live": len([x for x in live.findings({"statement": t}, n, mode="prose")
                        if not x.startswith("CLASSSEP-SOFT:")])} for n, t in GROWTH]

out = {
    "recheck_at": "2026-09-12T00:53:00+08:00",
    "live_detector_sha256": live_sha,
    "pass1_detector_sha256": "c266dbceca87fb996bd76a774145ef511cbf2aae190d9f423167d3200783a920",
    "detector_diff": {"added_lines": len(added), "removed_lines": len(removed),
                      "added": [l.rstrip("\n") for l in added]},
    "corpus_snapshot_canonical": run_corpus(canon),
    "corpus_live": run_corpus(live),
    "probes": prob_rows,
    "map_snapshot_6d3f0f2792a2": {"canonical_hard": len(map_hard(canon, snap_map)),
                                  "live_hard": len(map_hard(live, snap_map))},
    "map_live": {"sha256": live_map_sha, "claims": len(live_map.get("claims", [])),
                 "canonical_hard": len(map_hard(canon, live_map)),
                 "live_hard": len(map_hard(live, live_map))},
    "growth": growth,
    "growth_totals": {"canonical": sum(r["canonical"] for r in growth),
                      "live": sum(r["live"] for r in growth)},
    "acceptance_live": {
        "declared_fp_probes_clean": all(not r["live"] for r in prob_rows["fp"]),
        "declared_tp_probes_fire": all(r["live"] for r in prob_rows["tp"]),
        "no_over_suppression": all(not r["over_suppressed"] for r in prob_rows["fn"]),
        "corpus_pass": run_corpus(live)["verdict"] == "PASS",
    },
}
(RAW / "drift_recheck.json").write_text(json.dumps(out, indent=2, sort_keys=True))
(HERE / "drift_recheck.json").write_text(json.dumps(out, indent=2, sort_keys=True))
print(json.dumps(out, indent=2, sort_keys=True))
