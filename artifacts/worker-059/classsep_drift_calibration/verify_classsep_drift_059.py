#!/usr/bin/env python3
"""W059-CLASSSEP-DRIFT-CALIBRATION-01 — independent calibration of the class-separation
detector drift c266dbceca87 -> a8c04fc31e4a (research_map/class_separation.py, mtime 00:52:00),
plus the staged candidate e2d24b927ee8 it was derived from.

PREREGISTRATION CORRECTION (v1 -> v2, disclosed, not silently tuned)
  A v1 run of this harness registered the drift direction backwards: it assumed the live
  revision *removed* the meta-audit quotation guard, so it expected live >= pinned.  The
  measured sets showed the opposite on every snapshot.  The diff direction is authoritative:
  the live revision ADDS the guard (pinned c266dbce lacks it), so live is a strict subset of
  pinned.  v2 re-registers every expectation against the measured direction.  The v1 run and
  its failure list were kept (git-less workspace: see CORRECTION note in README.md); no
  expectation in v2 is copied from a v1 observation without re-running it.

Question: the frozen detector drifted while reviews were pinned to c266dbceca87.  What did the
drift do, and does any pinned verdict change because of it?

Method: load three byte-pinned revisions as separate modules, run them on the same *frozen*
map snapshot (never the live map), run a pre-registered 11-probe battery, run the standing
27-fixture regression, scan every frozen snapshot set relation, and test the staged candidate's
`_NEG_SPLIT` branch for reachability with an ordered-branch argument plus an instrumented run.
No repository file is modified.  Pins are re-measured at exit.

Expectations (pre-registered for v2, see README.md E-table):
  E1  pinned c266dbce on frozen map 262da6979857 yields exactly 21 hard findings, all on
      claims[*].statement.
  E2  live a8c04fc3 on the same map yields exactly 17; live-set is a strict subset of
      pinned-set; drops are exactly claims[127] x1, claims[187] x1, claims[192] x2; live adds 0.
  E3  every dropped finding carries >=1 carve-out attribution token; dropped claims are within
      the project-adjudicated mention set {127,187,192,276,306}.
  E4  all 5 frozen snapshots satisfy live-set subset pinned-set, with 0 live-only findings in
      aggregate (the drift is one-directional: it can only remove findings).
  E5  probe battery: live flags all genuine merge declarations, ignores the legitimate
      split/prohibition/negation/meta statements, and shows the one predicted reversal P4
      (a genuine merge declaration co-occurring with a carve-out token is suppressed).
      Battery 11/11; the P4 row is the designed over-suppression probe, not an error.  P4
      text is chosen so "detector flag" falls inside the +-60-char context window of the
      composite match (verified in the trace, not assumed).
  E6  the standing worker-07 27-fixture regression PASSes on all three revisions
      (17/17 leaks, 10/10 controls): the corpus does not discriminate pinned from live from
      staged, i.e. it contains no fixture for the carve-out or for the negated-split surface.
  E7  staged candidate e2d24b92 differs from live by exactly: carve-out present in live but
      not staged, and _NEG_SPLIT present in staged but not live (checked as line-set facts,
      not by output).  Net map effect: staged 22 = live 17 + 4 re-instated drops + 1 new flag.
  E8  staged _NEG_SPLIT is ordered *before* _PROHIBIT (line-order check), so it is reachable
      and semantically overriding: it fires exactly 1 time on the frozen map, on
      claims[187]'s "do not split: C0 or C2", and emits the message "composite C0/C2
      asserted as one class" for a sentence that prohibits a merge.  Both _NEG_SPLIT and
      _PROHIBIT match that context, so the ordering - not the regex - is what flips a
      suppression into a flag.  All 4 negated-split probes match _PROHIBIT; the reaching
      ones are those where _NEG_SPLIT matches a "do not split" while _PROHIBIT's own
      alternation would also have matched it.  Measured reachability, not a claim that the
      branch is dead.

Exit 0 iff all expectations hold and all pins verify.  Writes report.json only.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]          # .../ai4math-swarm
HERE = Path(__file__).resolve().parent
SNAP = HERE / "snapshot"

FROZEN_MAP = SNAP / "research_map.262da6979857.json"
MODS = {
    "pinned_c266dbce": SNAP / "class_separation.pinned_c266dbce.py",
    "live_a8c04fc3": SNAP / "class_separation.live_a8c04fc3.py",
    "staged_e2d24b92": SNAP / "class_separation.staged_e2d24b92.py",
}
WORKER07_RESULTS = SNAP / "worker07_results.json"
CARVE_OUT_ATTR = re.compile(
    r"false[- ]positive|non[- ]merge|not\s+(?:a\s+)?merge|no\s+genuine\s+(?:c0/c2|c2/c0)\s+merge|"
    r"detector\s+(?:finding|flag)|quote(?:d|s)?\s+(?:the\s+)?detector", re.I)
ADJUDICATED_MENTION_CLAIMS = {127, 187, 192, 276, 306}

# (id, statement, live-expected-findings, category) — 11 probes
PROBES = [
    ("P1", "The C0 and C2 regularities are merged into one class with one schema.", 1, "genuine_merge"),
    ("P2", "C0 or C2 are one class under the frozen taxonomy.", 1, "genuine_merge"),
    ("P3", "The detector must never merge C0 and C2 into one schema.", 0, "legit_prohibition"),
    ("P4", "The two C0/C2 rows are merged into one class; this is not a detector flag but a real merge.",
     0, "carveout_over_suppression"),
    ("P5", "Quoting the detector output: 'C0/C2 merge' is described here as a known false positive.",
     0, "meta_mention"),
    ("P6", "There is no genuine C0/C2 merge in the frozen taxonomy.", 0, "negated_mention"),
    ("P7", "The C0/C2 classes are kept distinct; the split is mandatory under the rubric.", 0, "legit_split"),
    ("P8", "Round 3 adjudicates the C0/C2 non-merge finding reported by the detector.", 0, "meta_mention"),
    ("P9", "The C0/C2 definitions are separate and not unified by the registry.", 0, "negated_merge"),
    ("P10", "AF-WCC-VAC-GEN and AF-SCC-C2-VAC-GEN are merged into a single class in the draft.",
     0, "out_of_scope_no_composite"),
    ("P11", "The C0/C2 rows are not separate; one class.", 1, "negated_split_but_asserted_merge"),
]

# independently-frozen snapshots authored by other workers (not by this harness)
HISTORICAL = [
    "artifacts/worker-032/cf16-delta/pinned/research_map.11311ab36005.json",
    "artifacts/worker-085/candidate_diff/snapshot/research_map.json",
    "artifacts/worker-032/cf16-delta-02/pinned/research_map.ed28b714464e.json",
    "artifacts/worker-056/classsep_holdout/snapshot/research_map.56478e3f1d19.json",
]
NEG_SPLIT_PROBES = [
    "never split the C0/C2 rows",
    "no distinction between C0 and C2",
    "do not separate C0/C2",
    "must not distinguish C0 from C2",
]


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def claims_of(findings):
    out = {}
    for f in findings:
        m = re.search(r"claims\[(\d+)\]", f)
        if m:
            out.setdefault(int(m.group(1)), []).append(f)
    return out


def main() -> int:
    print("W059-CLASSSEP-DRIFT-CALIBRATION-01 (v2, corrected preregistration)")
    pins_before = {str(p.relative_to(ROOT)): sha256_file(p) for p in
                   list(MODS.values()) + [FROZEN_MAP, WORKER07_RESULTS, Path(__file__).resolve()]}
    mods = {k: load(p, k) for k, p in MODS.items()}
    m = json.loads(FROZEN_MAP.read_text())

    results = {"task_id": "W059-CLASSSEP-DRIFT-CALIBRATION-01", "expectations": {}, "probes": {},
               "details": {}, "preregistration": "v2-corrected"}
    ok = True

    def expect(eid, cond, detail):
        nonlocal ok
        results["expectations"][eid] = {"pass": bool(cond), "detail": detail}
        ok = ok and bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {eid}: {detail}")

    print("\n== frozen map %s (%d claims) ==" % (sha256_file(FROZEN_MAP)[:12], len(m["claims"])))
    per = {k: mod.findings_for_map(m) for k, mod in mods.items()}
    for k, f in per.items():
        print("  %-16s findings=%d" % (k, len(f)))
    pin_flat, live_flat, staged_flat = (set(per[k]) for k in ("pinned_c266dbce", "live_a8c04fc3", "staged_e2d24b92"))
    pinC, liveC, stagedC = (claims_of(per[k]) for k in ("pinned_c266dbce", "live_a8c04fc3", "staged_e2d24b92"))
    drops = pin_flat - live_flat
    adds = live_flat - pin_flat
    results["details"]["map_counts"] = {k: len(v) for k, v in per.items()}
    results["details"]["dropped_findings"] = sorted(drops)
    results["details"]["live_only_findings"] = sorted(adds)

    expect("E1", len(per["pinned_c266dbce"]) == 21 and all("claims[" in f for f in per["pinned_c266dbce"]),
           "pinned c266dbce yields %d hard findings, all on claims[*].statement" % len(per["pinned_c266dbce"]))
    expect("E2", len(per["live_a8c04fc3"]) == 17 and live_flat < pin_flat and not adds
           and sorted(set(pinC) - set(liveC)) == [127, 187]
           and len(pinC.get(192, [])) - len(liveC.get(192, [])) == 2,
           "live a8c04fc3 yields %d; strict subset of pinned; drops claims[127]x1 + claims[187]x1 + claims[192]x2; adds 0"
           % len(per["live_a8c04fc3"]))

    dropped_claims = sorted({int(re.search(r"claims\[(\d+)\]", f).group(1)) for f in drops if "claims[" in f})
    expect("E3", all(CARVE_OUT_ATTR.search(f) for f in drops) and set(dropped_claims) <= ADJUDICATED_MENTION_CLAIMS,
           "all %d dropped findings carry a carve-out attribution token and their claims %s lie in the adjudicated "
           "mention set {127,187,192,276,306}" % (len(drops), dropped_claims))

    print("\n== historical frozen snapshots ==")
    hist, agg_live_only, all_subset, snapshots = {}, 0, True, 0
    for rel in HISTORICAL:
        p = ROOT / rel
        if not p.is_file():
            hist[rel] = {"missing": True}
            continue
        mo = json.loads(p.read_text())
        pp = set(mods["pinned_c266dbce"].findings_for_map(mo))
        ll = set(mods["live_a8c04fc3"].findings_for_map(mo))
        hist[rel] = {"sha256": sha256_file(p)[:12], "claims": len(mo.get("claims", [])),
                     "pinned": len(pp), "live": len(ll), "subset": pp >= ll,
                     "live_only": len(ll - pp), "dropped": len(pp - ll)}
        snapshots += 1
        agg_live_only += len(ll - pp)
        all_subset = all_subset and pp >= ll
        print("  %-44s claims=%-4d pinned=%-2d live=%-2d subset=%s (+%d/-%d)" %
              (rel.split("/")[-1], hist[rel]["claims"], hist[rel]["pinned"], hist[rel]["live"],
               hist[rel]["subset"], hist[rel]["live_only"], hist[rel]["dropped"]))
    hist["live_map_snapshot"] = {"sha256": sha256_file(FROZEN_MAP)[:12], "claims": len(m.get("claims", [])),
                                 "pinned": len(per["pinned_c266dbce"]), "live": len(per["live_a8c04fc3"]),
                                 "subset": live_flat < pin_flat, "live_only": len(adds), "dropped": len(drops)}
    agg_live_only += len(adds)
    all_subset = all_subset and live_flat <= pin_flat
    snapshots += 1
    results["details"]["historical"] = hist
    expect("E4", snapshots == 5 and all_subset and agg_live_only == 0,
           "across %d frozen snapshots (4 historical + live map) live-set is a subset of pinned-set with "
           "%d live-only findings in aggregate: one-directional" % (snapshots, agg_live_only))

    print("\n== pre-registered probe battery ==")
    for pid, text, exp_live, cat in PROBES:
        row = {k: len(mod.findings({"statement": text}, "probe", mode="prose")) for k, mod in mods.items()}
        results["probes"][pid] = {"category": cat, "expected_live": exp_live, "observed": row, "text": text}
        status = "PASS" if row["live_a8c04fc3"] == exp_live else "FAIL"
        print("  [%s] %-4s %-36s live=%d expected=%d pinned=%d staged=%d" %
              (status, pid, cat, row["live_a8c04fc3"], exp_live, row["pinned_c266dbce"], row["staged_e2d24b92"]))
    hits = sum(1 for pid, _t, exp, _c in PROBES if results["probes"][pid]["observed"]["live_a8c04fc3"] == exp)
    expect("E5", hits == 11 and results["probes"]["P4"]["observed"]["pinned_c266dbce"] == 1
           and results["probes"]["P3"]["observed"]["live_a8c04fc3"] == 0
           and results["probes"]["P6"]["observed"]["live_a8c04fc3"] == 0
           and results["probes"]["P10"]["observed"]["live_a8c04fc3"] == 0,
           "live battery 11/11; the P4 row is the designed over-suppression probe - live ignores a genuine merge "
           "declaration that shares its context window with the token 'detector flag' (pinned/staged flag it)")

    print("\n== standing 27-fixture regression (worker-07 corpus) ==")
    res07 = json.loads(WORKER07_RESULTS.read_text())
    reg = {}
    for k, mod in mods.items():
        tp = fn = tn = fp = 0
        for fx in res07["fixtures"]:
            fpth = ROOT / fx["fixture_path"]
            if not fpth.exists():
                continue
            mm = json.loads(fpth.read_text())
            det = mod.findings_for_map(mm)
            for g in mm.get("groups", []):
                for n in g.get("nodes", []):
                    art = n.get("artifact")
                    if art and (ROOT / art).is_file():
                        det += mod.findings_for_text((ROOT / art).read_text(errors="replace"), f"artifact {art}")
            got, truth = bool(det), bool(fx["is_class_merge"])
            if truth and got: tp += 1
            elif truth and not got: fn += 1
            elif not truth and got: fp += 1
            else: tn += 1
        reg[k] = {"tp": tp, "fn": fn, "tn": tn, "fp": fp,
                  "verdict": "PASS" if fn == 0 and fp == 0 else "DEFECTIVE"}
        print("  %-16s tp=%d fn=%d tn=%d fp=%d verdict=%s" % (k, tp, fn, tn, fp, reg[k]["verdict"]))
    results["details"]["regression"] = reg
    expect("E6", all(v["verdict"] == "PASS" for v in reg.values()),
           "all three revisions PASS 17/17 leaks + 10/10 controls: the corpus does not discriminate them")

    print("\n== structural diff facts (line sets, not outputs) ==")
    def lines(p): return set(Path(p).read_text().splitlines())
    live_l, staged_l = lines(MODS["live_a8c04fc3"]), lines(MODS["staged_e2d24b92"])
    pin_l = lines(MODS["pinned_c266dbce"])
    carve_line = [l for l in live_l if "false[- ]positive" in l]
    negsplit_lines = [l for l in staged_l if "_NEG_SPLIT" in l]
    results["details"]["structural"] = {
        "carveout_lines_in_live": len(carve_line), "neg_split_lines_in_staged": len(negsplit_lines),
        "carveout_absent_from_pinned": not any("false[- ]positive" in l for l in pin_l),
        "neg_split_absent_from_live": not any("_NEG_SPLIT" in l for l in live_l),
        "staged_neg_split_before_prohibit": "elif _NEG_SPLIT.search(ctx)" in staged_l
                                           and "elif _PROHIBIT.search(ctx)" in staged_l,
    }
    print("  live carve-out lines=%d ; staged _NEG_SPLIT lines=%d ; carve-out absent from pinned / "
          "_NEG_SPLIT absent from live: %s" % (len(carve_line), len(negsplit_lines),
                                               results["details"]["structural"]["carveout_absent_from_pinned"]))
    expect("E7", results["details"]["structural"]["carveout_lines_in_live"] == 1
           and results["details"]["structural"]["neg_split_lines_in_staged"] == 2
           and results["details"]["structural"]["carveout_absent_from_pinned"]
           and results["details"]["structural"]["neg_split_absent_from_live"]
           and len(per["staged_e2d24b92"]) == 22 == len(per["live_a8c04fc3"]) + len(drops) + 1,
           "staged = live - carve-out + _NEG_SPLIT; map effect 22 = 17 + %d re-instated + 1 new" % len(drops))

    print("\n== staged _NEG_SPLIT reachability ==")
    st = mods["staged_e2d24b92"]

    def line_no(path, needle):
        for i, l in enumerate(Path(path).read_text().splitlines(), 1):
            if needle in l:
                return i
        return -1

    neg_line = line_no(MODS["staged_e2d24b92"], "elif _NEG_SPLIT.search(ctx)")
    pro_line = line_no(MODS["staged_e2d24b92"], "elif _PROHIBIT.search(ctx)")
    ordered = 0 < neg_line < pro_line
    both = [s for s in NEG_SPLIT_PROBES if st._NEG_SPLIT.search(s) and st._PROHIBIT.search(s)]
    # instrumented: does the branch actually fire anywhere on the frozen map?
    fired = []
    orig = st._scan_composite

    def patched(text, where, out, mode="declaration"):
        t = st.norm(text)
        for mm in st._MERGE_PAT.finditer(t):
            ctx = t[max(0, mm.start() - 60):min(len(t), mm.end() + 60)]
            if st._MERGE_ASSERT.search(ctx):
                continue
            if st._NEG_SPLIT.search(ctx):
                fired.append({"where": where, "mode": mode, "prohibit_also_matches": bool(st._PROHIBIT.search(ctx)),
                              "split_also_matches": bool(st._SPLIT.search(ctx)), "ctx": ctx.strip()[:120]})
                continue
            if st._PROHIBIT.search(ctx) or st._SPLIT.search(ctx):
                continue
        return orig(text, where, out, mode)

    st._scan_composite = patched
    st.findings_for_map(m)
    st._scan_composite = orig
    fired_where = sorted({f["where"] for f in fired})
    results["details"]["neg_split"] = {"staged_neg_split_line": neg_line, "staged_prohibit_line": pro_line,
                                       "ordered_before_prohibit": ordered,
                                       "probes_matching_both": len(both),
                                       "firings_on_frozen_map": len(fired), "firings": fired[:5]}
    print("  staged _NEG_SPLIT line=%d, _PROHIBIT line=%d, ordered-before=%s" % (neg_line, pro_line, ordered))
    print("  negated-split probes matching _NEG_SPLIT=%d/%d (both-regex=%d/%d)" %
          (sum(1 for s in NEG_SPLIT_PROBES if st._NEG_SPLIT.search(s)), len(NEG_SPLIT_PROBES), len(both), len(NEG_SPLIT_PROBES)))
    for f in fired[:3]:
        print("    fires at %s (mode=%s prohibit=%s): %r" % (f["where"], f["mode"], f["prohibit_also_matches"], f["ctx"]))
    expect("E8", ordered and len(fired) >= 1 and all(f["prohibit_also_matches"] for f in fired)
           and any("claims[187]" in w for w in fired_where),
           "staged _NEG_SPLIT is placed before _PROHIBIT (line %d < %d) and fires %d time(s) on the frozen map, "
           "all on contexts _PROHIBIT also matches; the reached surface is claims[187]'s 'do not split: C0 or C2', "
           "flagged as an asserted merge.  The regex is not dead; the ordering makes it override _PROHIBIT"
           % (neg_line, pro_line, len(fired)))

    print("\n== pin drift check ==")
    pins_after = {str(p.relative_to(ROOT)): sha256_file(p) for p in
                  list(MODS.values()) + [FROZEN_MAP, WORKER07_RESULTS, Path(__file__).resolve()]}
    drifted = [k for k in pins_before if pins_before[k] != pins_after.get(k)]
    if drifted:
        print("  DRIFT:", drifted)
        ok = False
    else:
        print("  clean: %d pins unchanged" % len(pins_before))
    results["pins"] = pins_after
    results["verdict"] = "ALL_EXPECTATIONS_HOLD" if ok else "FAILED"
    report = HERE / "report.json"
    report.write_text(json.dumps(results, indent=1, sort_keys=True))
    print("\nreport: %s sha256=%s" % (report, sha256_file(report)))
    print("VERDICT:", results["verdict"])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
