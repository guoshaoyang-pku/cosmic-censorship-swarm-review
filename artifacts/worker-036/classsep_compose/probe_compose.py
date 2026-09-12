#!/usr/bin/env python3
"""W036-CLASSSEP-COMPOSE-01 probe — do the two staged class-separation candidates compose,
and do they rebase onto the live canonical that moved mid-lifecycle?

Bounded, class-bound worker measurement (worker-036, node A1, gate G-AUDIT/G-CLASSBIND,
primary class binding AF-SCC-C0-VAC-GEN; the four frozen classes are the measured scope).

Revisions measured:
  C0  research_map/class_separation.py  c266dbceca87   pinned study base
  C1  research_map/class_separation.py  a8c04fc31e4a   live base (CF-16 meta-quote exemption)
  P   proposed/class_separation.py      e2d24b927ee8   staged prose-precision patch (worker-16)
  R   artifacts/worker-036/...          1bc87c9542ed   staged container-recall patch (worker-036, R5)
  PR0 C0 + P + R (2-way)                                primary composition
  P1/C1 + P, R1/C1 + R, PR1/C1 + P + R (3-way rebase)   rebase window

All inputs are read from ./snapshots (hash-pinned).  Canonical files are never written.
Verdict is measurement evidence only: no gate verdict, no node status, no canonical patch applied.

Run: python3 artifacts/worker-036/classsep_compose/probe_compose.py
"""
from __future__ import annotations

import datetime
import difflib
import hashlib
import importlib.util
import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SNAP = HERE / "snapshots"

# ---------------------------------------------------------------------------- pins
PIN_C0 = "c266dbceca87fb996bd76a774145ef511cbf2aae190d9f423167d3200783a920"
PIN_C1 = "a8c04fc31e4afa1b691cd6bfb6bf8b4f953a0adc925939a8351bab9cf453c5bd"
PIN_P = "e2d24b927ee81c45996f8a4853d2f4b6899e8a3ea405c9e68b1ba5bb37448819"
PIN_R = "1bc87c9542ed329334258ad3d87996fe87fc80a1b81c53a255130a1846d1ed49"
PIN_MAP_FROZEN = "3d45be5969ec388ef4a3e10d5eb87b81dbf3d03138510b75ff6a56453ceae005"
PIN_LEDGER = "a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28"
PIN_W07 = "d69ad58468be16655921dcf0eab9570fa6e7ccaf828558a45d4b306cce3de452"
PIN_W085_REPORT = "439822557fd9d98e7e2080387aac8088b29b3447c65104aa442eade8ea7ecdd0"
PIN_DISJ_FIXTURES = "de7ac7498c3463f9146005f867132864f09706a54556a6b8f9a39f64ce527b08"
PIN_DISJ_REPORT = "093ece84adf5b8c0abdc70ab819d895f62518e934a0c90f42dd31ca9482ca133"
PIN_INERT_R5 = "695e3c1cf0c26d87fbeb7c268184dec1b1e476c9052026f65ae699aa7662a5be"
PIN_OVERFIRE_R5 = "1e9eaf6b2412431193d788e91e415e07dec5fd212ee0c1df02457f0ba8b25372"

EXPECTED_DISJ_ROWS = {3, 4, 24, 26, 29, 45, 57, 59}
FROZEN_CLASSES = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]
REVS0 = ["C0", "P", "R", "PR0"]
REVS1 = ["C1", "P1", "R1", "PR1"]
ALL_REVS = REVS0 + REVS1
EXPECT_KEY = {"C0": "C", "P": "P", "R": "R", "PR0": "PR",
              "C1": "C", "P1": "P", "R1": "R", "PR1": "PR"}
C1_EXEMPTION = re.compile(r"false[- ]positive|non[- ]merge|not\s+(?:a\s+)?merge|"
                          r"no\s+genuine\s+(?:c0/c2|c2/c0)\s+merge|detector\s+(?:finding|flag)|"
                          r"quote(?:d|s)?\s+(?:the\s+)?detector", re.I)


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load_mod(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def kind_of(finding: str) -> str:
    if "container disjoins" in finding:
        return "disjunction"
    if "unknown class token" in finding:
        return "unknown"
    if "merges C0 and C2" in finding:
        return "merge"
    if "composite C0/C2" in finding:
        return "prose"
    return "other"


def scan(mod, surface: str, payload, where: str, mode: str = "declaration"):
    if surface in ("obj", "object"):
        return mod.findings(payload, where, mode=mode)
    if surface == "map":
        return mod.findings_for_map(payload)
    if surface == "text":
        return mod.findings_for_text(payload, where)
    raise ValueError(surface)


def score_corpus(mod, corpus_dir: Path):
    """Independent re-implementation of class_separation.regression() with an explicit root."""
    res = json.loads((corpus_dir / "results.json").read_text())
    tp = fn = tn = fp = 0
    per = []
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
                    det += mod.findings_for_text((ROOT / art).read_text(errors="replace"), f"artifact {art}")
        got, truth = bool(det), bool(fx["is_class_merge"])
        if truth and got:
            tp += 1
        elif truth and not got:
            fn += 1
        elif not truth and got:
            fp += 1
        else:
            tn += 1
        per.append({"id": fx["id"], "truth": truth, "detected": got})
    return {"tp": tp, "fn": fn, "tn": tn, "fp": fp, "corpus_size": tp + fn + tn + fp,
            "per_fixture": per, "verdict": "PASS" if fn == 0 and fp == 0 else "DEFECTIVE"}


def corpus_digest(results_path: Path) -> str:
    res = json.loads(results_path.read_text())
    h = hashlib.sha256()
    for fx in sorted(res["fixtures"], key=lambda x: x["id"]):
        p = ROOT / fx["fixture_path"]
        h.update(fx["id"].encode())
        h.update(b"\0")
        h.update(p.read_bytes() if p.exists() else b"<missing>")
        h.update(b"\0")
    return h.hexdigest()


def map_elements(m: dict):
    """Decompose exactly the surfaces findings_for_map() scans into (kind, where, obj)."""
    els = []
    for g in m.get("groups", []):
        if isinstance(g.get("direction"), str):
            els.append(("direction", f"groups[{g.get('id', '?')}].direction", {"direction": g["direction"]}))
        for n in g.get("nodes", []):
            els.append(("node", f"node {n.get('id', '?')}", n))
    for i, ev in enumerate(m.get("portfolio_events", [])):
        if isinstance(ev, dict):
            els.append(("portfolio", f"portfolio_events[{i}]", ev))
    for i, c in enumerate(m.get("claims", [])):
        if isinstance(c, dict):
            els.append(("claim", f"claims[{i}]", c))
    return els


def element_findings(mod, kind: str, where: str, obj):
    if kind == "claim":
        return mod.findings(obj, where, mode="prose")
    return mod.findings(obj, where)


def additivity(mods, revs, per_item):
    """per_item: list of (label, callable(mod)->list[str]).  C = revs[0], P = revs[1],
    R = revs[2], PR = revs[3]; returns per-item census and interaction list."""
    c_rev, p_rev, r_rev, pr_rev = revs
    rows, interactions = [], []
    for label, fn in per_item:
        cnt = {rev: Counter(fn(mods[rev])) for rev in revs}
        lhs = cnt[pr_rev]
        rhs = cnt[p_rev] + cnt[r_rev] - cnt[c_rev]
        ok = lhs == rhs
        negative = {k: v for k, v in rhs.items() if v < 0}
        if not ok or negative:
            interactions.append({"item": label, "ok": ok, "negative_rhs": negative,
                                 "PR_only": dict(lhs - rhs), "PplusR_minusC_only": dict(rhs - lhs),
                                 "counts": {r: sum(cnt[r].values()) for r in revs}})
        rows.append({"item": label, "counts": {r: sum(cnt[r].values()) for r in revs}, "additive": ok})
    return rows, interactions


def main() -> int:
    checks = []

    def check(cid, desc, ok, measured):
        checks.append({"id": cid, "desc": desc, "ok": bool(ok), "measured": measured})
        return bool(ok)

    # ------------------------------------------------------------------ K0 pins
    build = json.loads((HERE / "candidate_build.json").read_text())
    paths = {
        "C0": SNAP / "class_separation.canonical.c266dbceca87.py",
        "C1": SNAP / "class_separation.canonical.a8c04fc31e4a.py",
        "P": SNAP / "class_separation.prose.e2d24b927ee8.py",
        "R": SNAP / "class_separation.container.1bc87c9542ed.py",
        "P1": SNAP / "class_separation.c1_prose_only.py",
        "R1": SNAP / "class_separation.c1_container_only.py",
        "PR0": ROOT / build["windows"]["base_c0"]["composed"]["snapshot_path"],
        "PR1": SNAP / "class_separation.c1_composed.py",
        "INERT0": SNAP / "class_separation.composed_inert_r5.py",
        "OVER0": SNAP / "class_separation.composed_overfire_r5.py",
        "INERT1": SNAP / "class_separation.c1_composed_inert_r5.py",
        "OVER1": SNAP / "class_separation.c1_composed_overfire_r5.py",
        "map_frozen": SNAP / "research_map.3d45be5969ec.json",
        "map_live": SNAP / "research_map.live.snapshot.json",
        "ledger": SNAP / "theorems.a1674f094979.jsonl",
        "w07": SNAP / "worker07_results.d69ad58468be.json",
        "w085": SNAP / "worker085_candidate_diff_report.json",
        "disj_fixtures": SNAP / "w036_disj_fixtures.de7ac7498c34.jsonl",
        "disj_report": SNAP / "w036_disj_report.json",
        "inert_r5": SNAP / "w036_control_inert_r5.py",
        "overfire_r5": SNAP / "w036_control_overfire_r5.py",
    }
    h_start = {k: sha256_file(p) for k, p in paths.items()}

    check("K0a", "canonical study base snapshot is c266dbceca87",
          h_start["C0"] == PIN_C0, h_start["C0"][:12])
    check("K0b", "live-base snapshot is a8c04fc31e4a (the canonical that moved mid-lifecycle)",
          h_start["C1"] == PIN_C1, h_start["C1"][:12])
    check("K0c", "prose-patch snapshot is the pinned module e2d24b927ee8",
          h_start["P"] == PIN_P, h_start["P"][:12])
    check("K0d", "container-patch snapshot is the pinned module 1bc87c9542ed",
          h_start["R"] == PIN_R, h_start["R"][:12])
    check("K0e", "frozen map snapshot is 3d45be5969ec (cross-check surface)",
          h_start["map_frozen"] == PIN_MAP_FROZEN, h_start["map_frozen"][:12])
    check("K0f", "L0 ledger snapshot is a1674f094979",
          h_start["ledger"] == PIN_LEDGER, h_start["ledger"][:12])
    check("K0g", "worker-07 corpus results.json is d69ad58468be",
          h_start["w07"] == PIN_W07, h_start["w07"][:12])
    check("K0h", "worker-085 candidate-diff report is the pinned input",
          h_start["w085"] == PIN_W085_REPORT, h_start["w085"][:12])
    check("K0i", "W036-CLASSSEP-DISJ-RULE-01 fixtures/report are the pinned inputs",
          h_start["disj_fixtures"] == PIN_DISJ_FIXTURES and h_start["disj_report"] == PIN_DISJ_REPORT,
          {"fixtures": h_start["disj_fixtures"][:12], "report": h_start["disj_report"][:12]})
    check("K0j", "prior R5 inert/overfire control snapshots are the pinned inputs",
          h_start["inert_r5"] == PIN_INERT_R5 and h_start["overfire_r5"] == PIN_OVERFIRE_R5,
          {"inert": h_start["inert_r5"][:12], "overfire": h_start["overfire_r5"][:12]})
    live_prose = sha256_file(ROOT / "proposed/class_separation.py")
    live_cont = sha256_file(ROOT / "artifacts/worker-036/classsep_disj_rule/candidate_class_separation.py")
    check("K0k", "live staged patch paths still equal the pinned bytes (no rebase needed for the patches)",
          live_prose == PIN_P and live_cont == PIN_R,
          {"prose": live_prose[:12], "container": live_cont[:12]})

    # ------------------------------------------------------------------ K1 both composition windows
    for wkey, base_pin in (("base_c0", PIN_C0), ("base_c1", PIN_C1)):
        w = build["windows"][wkey]
        check(f"K1{'' if wkey == 'base_c0' else 'b'}", f"{wkey}: hunks disjoint, no rebase conflict, reverse-apply to base, delta = union",
              w["ok"] and w["disjoint"] and not w["conflicts"]
              and all(not p["rebase_conflicts"] for p in w["patches"].values())
              and w["composed"]["reverse_apply_equals_base"]
              and w["composed"]["ascending_apply_equals_descending"]
              and w["composed"]["delta_equals_union_of_patch_deltas"]
              and w["hunk_counts"] == {"prose": 4, "container": 1},
              {"hunks": w["hunk_counts"], "disjoint": w["disjoint"],
               "rebase_conflicts": {n: len(p["rebase_conflicts"]) for n, p in w["patches"].items()},
               "reverse": w["composed"]["reverse_apply_equals_base"],
               "order_independent": w["composed"]["ascending_apply_equals_descending"],
               "delta_union": w["composed"]["delta_equals_union_of_patch_deltas"]})
    check("K1c", "composed snapshots match the build record",
          h_start["PR0"] == build["windows"]["base_c0"]["composed"]["sha256"]
          and h_start["PR1"] == build["windows"]["base_c1"]["composed"]["sha256"],
          {"PR0": h_start["PR0"][:12], "PR1": h_start["PR1"][:12]})
    # independent re-derivation of the primary composition from C0 + P + R bytes
    c0_lines = paths["C0"].read_text().splitlines(keepends=True)
    p_lines = paths["P"].read_text().splitlines(keepends=True)
    r_lines = paths["R"].read_text().splitlines(keepends=True)

    def blocks(a, b):
        sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
        return [(i1, i2, b[j1:j2]) for tag, i1, i2, j1, j2 in sm.get_opcodes() if tag != "equal"]

    out, drift = list(c0_lines), 0
    for i1, i2, rep in sorted(blocks(c0_lines, p_lines) + blocks(c0_lines, r_lines), key=lambda x: x[0]):
        out[i1 + drift:i2 + drift] = rep
        drift += len(rep) - (i2 - i1)
    check("K1d", "probe re-derives the primary composed bytes independently from C0 + P + R",
          "".join(out) == paths["PR0"].read_text(),
          {"independent_sha": hashlib.sha256("".join(out).encode()).hexdigest()[:12]})

    # ------------------------------------------------------------------ K12 rebase window structure
    c1_lines = paths["C1"].read_text().splitlines(keepends=True)
    c0_to_c1 = blocks(c0_lines, c1_lines)
    inv_c1 = blocks(c1_lines, c0_lines)

    def apply_desc(a, bl):
        o = list(a)
        for i1, i2, rep in sorted(bl, key=lambda x: x[0], reverse=True):
            o[i1:i2] = rep
        return o

    c1_reversed = "".join(apply_desc(c1_lines, inv_c1))
    check("K12a", "live-base delta is exactly one added 3-line hunk in _scan_composite and reverse-applies to C0",
          len(c0_to_c1) == 1 and sum(len(rep) for _, _, rep in c0_to_c1) == 3
          and sum(i2 - i1 for i1, i2, _ in c0_to_c1) == 0 and c1_reversed == "".join(c0_lines),
          {"hunks": len(c0_to_c1), "added": sum(len(rep) for _, _, rep in c0_to_c1),
           "removed": sum(i2 - i1 for i1, i2, _ in c0_to_c1),
           "reverse_equals_c0": c1_reversed == "".join(c0_lines)})
    naive = build["windows"]["base_c1"]["naive_reapply_hazard"]
    naive_lines = {k: v["reverts_new_base_lines"] for k, v in naive.items()}
    check("K12b", "rebase hazard measured: a naive 2-way re-diff of either patch file onto C1 would revert C1's own edit",
          all(v >= 3 for v in naive_lines.values()) and len(naive) == 2,
          {"naive_reverted_new_base_lines": naive_lines,
           "reverted_line_contents": {k: v["reverted_lines"] for k, v in naive.items()}})

    # ------------------------------------------------------------------ load revisions
    mods = {rev: load_mod(f"w036c_{rev}", paths[rev]) for rev in ALL_REVS}
    mods["INERT0"] = load_mod("w036c_INERT0", paths["INERT0"])
    mods["OVER0"] = load_mod("w036c_OVER0", paths["OVER0"])
    mods["INERT1"] = load_mod("w036c_INERT1", paths["INERT1"])
    mods["OVER1"] = load_mod("w036c_OVER1", paths["OVER1"])

    # ------------------------------------------------------------------ K2 worker-085 battery replay
    w085 = json.loads(paths["w085"].read_text())["probe_battery"]
    s_rows = []
    s_c_ok = s_p_ok = True
    for case in w085:
        cid = case["id"]
        res = {}
        for rev in ALL_REVS:
            if case["surface"] == "obj":
                res[rev] = scan(mods[rev], "obj", case["input"], cid, case.get("mode") or "declaration")
            else:
                res[rev] = scan(mods[rev], "text", case["input"], cid)
        c_ok = len(res["C0"]) == case["expected_canonical_n"]
        p_ok = len(res["P"]) == case["expected_proposed_n"]
        s_c_ok = s_c_ok and c_ok
        s_p_ok = s_p_ok and p_ok
        s_rows.append({"id": cid, "surface": case["surface"], "mode": case.get("mode"),
                       "counts": {rev: len(res[rev]) for rev in ALL_REVS},
                       "worker085_expected_canonical": case["expected_canonical_n"],
                       "worker085_expected_proposed": case["expected_proposed_n"],
                       "canonical_matches_w085": c_ok, "prose_matches_w085": p_ok})
    check("K2a", "external control: harness reproduces worker-085's 12 canonical counts",
          s_c_ok, {"cases": len(s_rows), "mismatches": [r["id"] for r in s_rows if not r["canonical_matches_w085"]]})
    check("K2b", "external control: harness reproduces worker-085's 12 prose-patch counts",
          s_p_ok, {"cases": len(s_rows), "mismatches": [r["id"] for r in s_rows if not r["prose_matches_w085"]]})

    # ------------------------------------------------------------------ K3 prior disj battery replay
    disj = [json.loads(l) for l in paths["disj_fixtures"].read_text().splitlines() if l.strip()]
    d_rows = []
    d_c_ok = d_r_ok = True
    for fx in disj:
        res = {rev: scan(mods[rev], fx["surface"], fx["obj"], f"fixture {fx['id']}") for rev in ALL_REVS}
        c_ok = len(res["C0"]) == fx["expect_canonical"]
        r_ok = len(res["R"]) == fx["expect_candidate"]
        d_c_ok = d_c_ok and c_ok
        d_r_ok = d_r_ok and r_ok
        d_rows.append({"id": fx["id"], "surface": fx["surface"],
                       "counts": {rev: len(res[rev]) for rev in ALL_REVS},
                       "prior_expect_canonical": fx["expect_canonical"],
                       "prior_expect_container": fx["expect_candidate"],
                       "canonical_matches_prior": c_ok, "container_matches_prior": r_ok})
    check("K3a", "external control: harness reproduces the prior packet's 26 canonical expectations",
          d_c_ok, {"cases": len(d_rows), "mismatches": [r["id"] for r in d_rows if not r["canonical_matches_prior"]]})
    check("K3b", "external control: harness reproduces the prior packet's 26 container-patch expectations",
          d_r_ok, {"cases": len(d_rows), "mismatches": [r["id"] for r in d_rows if not r["container_matches_prior"]]})

    # ------------------------------------------------------------------ K4 pre-registered compose battery
    comp_fx = [json.loads(l) for l in (HERE / "fixtures" / "compose_fixtures.jsonl").read_text().splitlines() if l.strip()]
    x_rows = []
    x0_ok = x0_kind_ok = x1_ok = x1_c1_indep = True
    for fx in comp_fx:
        res = {rev: scan(mods[rev], fx["surface"], fx["obj"], fx["id"], fx.get("mode") or "declaration")
               for rev in ALL_REVS}
        counts = {rev: len(res[rev]) for rev in ALL_REVS}
        row0_ok = all(counts[rev] == fx["expect"][EXPECT_KEY[rev]] for rev in REVS0)
        row1_ok = all(counts[rev] == fx["expect"][EXPECT_KEY[rev]] for rev in REVS1)
        kind_ok = dict(Counter(kind_of(x) for x in res["PR0"])) == fx["expect_PR_kinds"]
        # C1-window counts must equal the C0-window counts: no X case carries a C1 exemption marker
        marker = bool(C1_EXEMPTION.search(json.dumps(fx["obj"])))
        c1_indep = (not marker) and all(counts[rev1] == counts[rev0] for rev0, rev1 in zip(REVS0, REVS1))
        x0_ok = x0_ok and row0_ok
        x1_ok = x1_ok and row1_ok
        x0_kind_ok = x0_kind_ok and kind_ok
        x1_c1_indep = x1_c1_indep and c1_indep
        x_rows.append({"id": fx["id"], "surface": fx["surface"], "mode": fx.get("mode"),
                       "counts": counts, "expect": fx["expect"], "match_C0_window": row0_ok,
                       "match_C1_window": row1_ok,
                       "composed_kinds": dict(Counter(kind_of(x) for x in res["PR0"])),
                       "expect_PR_kinds": fx["expect_PR_kinds"], "kinds_match": kind_ok,
                       "carries_C1_exemption_marker": marker, "C1_equals_C0": c1_indep,
                       "note": fx["note"]})
    check("K4a", "pre-registered compose battery: all 12 cases match C0/P/R/PR0 count expectations",
          x0_ok, {"cases": len(x_rows), "mismatches": [r["id"] for r in x_rows if not r["match_C0_window"]]})
    check("K4b", "pre-registered compose battery: composed finding kinds match expectations",
          x0_kind_ok, {"mismatches": [r["id"] for r in x_rows if not r["kinds_match"]]})
    check("K4c", "pre-registered compose battery: rebased window matches the same expectations",
          x1_ok, {"cases": len(x_rows), "mismatches": [r["id"] for r in x_rows if not r["match_C1_window"]]})
    check("K4d", "control: no X case carries a C1 exemption marker, so C1-window == C0-window there",
          x1_c1_indep, {"violations": [r["id"] for r in x_rows if not r["C1_equals_C0"]]})

    # ------------------------------------------------------------------ K5 additivity / orthogonality, both windows
    items = []
    for case in w085:
        items.append((f"w085:{case['id']}", (lambda c: (lambda m: scan(m, c["surface"], c["input"], c["id"], c.get("mode") or "declaration")))(case)))
    for fx in disj:
        items.append((f"disj:{fx['id']}", (lambda f: (lambda m: scan(m, f["surface"], f["obj"], f"fixture {f['id']}")))(fx)))
    for fx in comp_fx:
        items.append((f"compose:{fx['id']}", (lambda f: (lambda m: scan(m, f["surface"], f["obj"], f["id"], f.get("mode") or "declaration")))(fx)))
    ledger_rows = [json.loads(l) for l in paths["ledger"].read_text().splitlines() if l.strip()]
    for i, row in enumerate(ledger_rows):
        items.append((f"ledger[{i}]", (lambda r, i=i: (lambda m: m.findings(r, f"theorems[{i}]")))(row)))
    for tag, mp in (("map_frozen", paths["map_frozen"]), ("map_live", paths["map_live"])):
        m = json.loads(mp.read_text())
        for kind, where, obj in map_elements(m):
            items.append((f"{tag}:{where}", (lambda k, w, o: (lambda mm: element_findings(mm, k, w, o)))(kind, where, obj)))

    add0, inter0 = additivity(mods, REVS0, items)
    add1, inter1 = additivity(mods, REVS1, items)
    agg0 = {rev: sum(r["counts"][rev] for r in add0) for rev in REVS0}
    agg1 = {rev: sum(r["counts"][rev] for r in add1) for rev in REVS1}
    check("K5a", "C0 window: PR0 = P + R - C0 is exact on every measured item (no interaction)",
          not inter0, {"items": len(add0), "interaction_count": len(inter0), "interactions": inter0[:10]})
    check("K5b", "C0 window aggregate is additive",
          agg0["PR0"] == agg0["P"] + agg0["R"] - agg0["C0"],
          {"aggregate_counts": agg0, "P_plus_R_minus_C": agg0["P"] + agg0["R"] - agg0["C0"]})
    check("K5c", "C1 rebase window: PR1 = P1 + R1 - C1 is exact on every measured item (no interaction)",
          not inter1, {"items": len(add1), "interaction_count": len(inter1), "interactions": inter1[:10]})
    check("K5d", "C1 rebase window aggregate is additive",
          agg1["PR1"] == agg1["P1"] + agg1["R1"] - agg1["C1"],
          {"aggregate_counts": agg1, "P_plus_R_minus_C": agg1["P1"] + agg1["R1"] - agg1["C1"]})

    # ------------------------------------------------------------------ K6 maps, both windows
    m_frozen = json.loads(paths["map_frozen"].read_text())
    m_live = json.loads(paths["map_live"].read_text())

    def measure_maps(mods_revs, revs, map_obj, map_path):
        fmap = {rev: mods_revs[rev].findings_for_map(map_obj) for rev in revs}
        concat = {rev: [x for k, w, o in map_elements(map_obj) for x in element_findings(mods_revs[rev], k, w, o)] for rev in revs}
        decomposition_ok = all(Counter(fmap[rev]) == Counter(concat[rev]) for rev in revs)
        c_rev, p_rev, r_rev, pr_rev = revs
        pairs = {}
        for a, b in ((c_rev, p_rev), (c_rev, r_rev), (c_rev, pr_rev)):
            removed = [x for x in fmap[a] if x not in fmap[b]]
            added = [x for x in fmap[b] if x not in fmap[a]]
            pairs[f"{a}->{b}"] = {
                "removed": len(removed), "added": len(added),
                "added_by_kind": dict(Counter(kind_of(x) for x in added)),
                "removed_by_kind": dict(Counter(kind_of(x) for x in removed)),
                "added_by_surface": dict(Counter(("node" if "node " in x else
                                                  "claims" if "claims[" in x else
                                                  "portfolio" if "portfolio_events[" in x else
                                                  "group_direction" if "groups[" in x else "other") for x in added)),
                "added_by_distinct_class_count": dict(sorted(Counter(
                    int(re.search(r"disjoins (\d+) frozen", x).group(1))
                    for x in added if "container disjoins" in x).items())),
            }
        return {"map_sha256": sha256_file(map_path), "totals": {rev: len(fmap[rev]) for rev in revs},
                "by_kind": {rev: dict(Counter(kind_of(x) for x in fmap[rev])) for rev in revs},
                "pairs": pairs, "decomposition_equals_findings_for_map": decomposition_ok,
                "removed_findings": {f"{a}->{b}": [x for x in fmap[revs[0]] if x not in fmap[b]]
                                     for a, b in ((c_rev, p_rev), (c_rev, r_rev), (c_rev, pr_rev))}}

    frozen0 = measure_maps(mods, REVS0, m_frozen, paths["map_frozen"])
    live0 = measure_maps(mods, REVS0, m_live, paths["map_live"])
    live1 = measure_maps(mods, REVS1, m_live, paths["map_live"])
    check("K6a", "findings_for_map equals the element-wise decomposition on every map snapshot and revision",
          frozen0["decomposition_equals_findings_for_map"] and live0["decomposition_equals_findings_for_map"]
          and live1["decomposition_equals_findings_for_map"],
          {"frozen_C0_window": frozen0["decomposition_equals_findings_for_map"],
           "live_C0_window": live0["decomposition_equals_findings_for_map"],
           "live_C1_window": live1["decomposition_equals_findings_for_map"]})
    check("K6b", "frozen-map control (C0 window): canonical 10 hard, container patch adds exactly 100 disjunctions",
          frozen0["totals"]["C0"] == 10 and frozen0["pairs"]["C0->R"]["added"] == 100
          and frozen0["pairs"]["C0->R"]["added_by_kind"] == {"disjunction": 100},
          {"totals": frozen0["totals"], "C0->R": frozen0["pairs"]["C0->R"]})
    live_r_ok = all(v["added_by_kind"].get("disjunction", 0) == v["added"]
                    for v in (live0["pairs"]["C0->R"], live1["pairs"]["C1->R1"]))
    check("K6c", "live-map snapshot: every finding the container patch adds (either window) is the container rule",
          live_r_ok, {"C0->R": live0["pairs"]["C0->R"], "C1->R1": live1["pairs"]["C1->R1"]})
    check("K6d", "live-map snapshot: the prose patch's added findings are statement-mode only (either window)",
          all(k == "prose" for k in live0["pairs"]["C0->P"]["added_by_kind"])
          and all(k == "prose" for k in live1["pairs"]["C1->P1"]["added_by_kind"]),
          {"C0->P": live0["pairs"]["C0->P"], "C1->P1": live1["pairs"]["C1->P1"]})
    check("K6e", "live-map snapshot (C0 window): composed delta equals the union of both single-patch deltas",
          live0["pairs"]["C0->PR0"]["added"] == (live0["pairs"]["C0->P"]["added"]
                                                 + live0["pairs"]["C0->R"]["added"]),
          {"C0->P": live0["pairs"]["C0->P"]["added"], "C0->R": live0["pairs"]["C0->R"]["added"],
           "C0->PR0": live0["pairs"]["C0->PR0"]["added"]})
    f_live_c0 = mods["C0"].findings_for_map(m_live)
    f_live_c1 = mods["C1"].findings_for_map(m_live)
    c0_c1_removed = [x for x in f_live_c0 if x not in f_live_c1]
    c0_c1_added = [x for x in f_live_c1 if x not in f_live_c0]
    check("K6f", "live-base delta (C0 -> C1) clears live findings and adds none",
          len(c0_c1_removed) > 0 and len(c0_c1_added) == 0,
          {"C0_total": len(f_live_c0), "C1_total": len(f_live_c1),
           "removed": len(c0_c1_removed), "added": len(c0_c1_added),
           "removed_by_kind": dict(Counter(kind_of(x) for x in c0_c1_removed)),
           "removed_findings": c0_c1_removed})

    # ------------------------------------------------------------------ K7 ledger
    led = {}
    for rev in ALL_REVS:
        led[rev] = [i for i, row in enumerate(ledger_rows)
                    if any("container disjoins" in x for x in mods[rev].findings(row, f"theorems[{i}]"))]
    check("K7a", "ledger a1674f094979: canonical 0 container rows, container patch exactly the 8 named rows (both windows)",
          led["C0"] == [] and set(led["R"]) == EXPECTED_DISJ_ROWS
          and led["C1"] == [] and set(led["R1"]) == EXPECTED_DISJ_ROWS,
          {"C0": led["C0"], "R": led["R"], "C1": led["C1"], "R1": led["R1"]})
    check("K7b", "ledger: prose patch adds no container finding and both compositions keep the 8 rows",
          led["P"] == [] and led["P1"] == [] and set(led["PR0"]) == EXPECTED_DISJ_ROWS
          and set(led["PR1"]) == EXPECTED_DISJ_ROWS,
          {"P": led["P"], "P1": led["P1"], "PR0": led["PR0"], "PR1": led["PR1"]})

    # ------------------------------------------------------------------ K8 standing regressions
    w07_dir = ROOT / "artifacts/worker-07/class_separation_falsification"
    w07_digest_start = corpus_digest(paths["w07"])
    reg = {rev: score_corpus(mods[rev], w07_dir) for rev in ALL_REVS}
    check("K8a", "worker-07 corpus: every revision passes 17/0/10/0 (no regression in either window)",
          all((r["tp"], r["fn"], r["tn"], r["fp"]) == (17, 0, 10, 0) for r in reg.values()),
          {rev: {k: reg[rev][k] for k in ("tp", "fn", "tn", "fp", "verdict")} for rev in ALL_REVS})
    check("K8b", "worker-07 corpus: per-fixture classification identical across all 8 revisions",
          all(reg[rev]["per_fixture"] == reg["C0"]["per_fixture"] for rev in ALL_REVS),
          {"changed": {rev: [a["id"] for a, b in zip(reg["C0"]["per_fixture"], reg[rev]["per_fixture"]) if a != b]
                       for rev in ALL_REVS if reg[rev]["per_fixture"] != reg["C0"]["per_fixture"]}})
    ood_dir = ROOT / "artifacts/worker-027/classsep_token_binding/ood_corpus"
    ood = None
    if (ood_dir / "results.json").exists():
        rc = {rev: score_corpus(mods[rev], ood_dir) for rev in ALL_REVS}
        ood = {"results_sha256": sha256_file(ood_dir / "results.json"),
               "counts": {rev: {k: rc[rev][k] for k in ("tp", "fn", "tn", "fp")} for rev in ALL_REVS},
               "per_fixture_identical": all(rc[rev]["per_fixture"] == rc["C0"]["per_fixture"] for rev in ALL_REVS)}
        check("K8c", "worker-027 OOD arity corpus: classification unchanged across all revisions",
              ood["per_fixture_identical"], ood)
    w07_digest_end = corpus_digest(paths["w07"])
    check("K8d", "corpus fixture bytes were stable during the run (digest)",
          w07_digest_start == w07_digest_end,
          {"digest_start": w07_digest_start[:12], "digest_end": w07_digest_end[:12]})

    # ------------------------------------------------------------------ K9 harness power controls
    def control_sweep(inert_mod, over_mod, pr_rev, negatives):
        inert_ok = True
        over_hits = 0
        for label, fn in negatives:
            base = Counter(fn(mods[pr_rev]))
            if Counter(fn(inert_mod)) != base:
                inert_ok = False
            if len(fn(over_mod)) > len(fn(mods[pr_rev])):
                over_hits += 1
        return inert_ok, over_hits

    neg_items = []
    for case in w085:
        if case["expected_proposed_n"] == 0:
            neg_items.append((case["id"], (lambda c: (lambda m: scan(m, c["surface"], c["input"], c["id"], c.get("mode") or "declaration")))(case)))
    for fx in comp_fx:
        if fx["expect"]["PR"] == 0:
            neg_items.append((fx["id"], (lambda f: (lambda m: scan(m, f["surface"], f["obj"], f["id"], f.get("mode") or "declaration")))(fx)))
    for fx in disj:
        if fx["expect_candidate"] == 0:
            neg_items.append((fx["id"], (lambda f: (lambda m: scan(m, f["surface"], f["obj"], f"fixture {f['id']}")))(fx)))

    inert_ok0, over_hits0 = control_sweep(mods["INERT0"], mods["OVER0"], "PR0", neg_items)
    inert_ok0 = inert_ok0 and Counter(mods["INERT0"].findings_for_map(m_live)) == Counter(mods["P"].findings_for_map(m_live))
    inert_ok1, over_hits1 = control_sweep(mods["INERT1"], mods["OVER1"], "PR1", neg_items)
    inert_ok1 = inert_ok1 and Counter(mods["INERT1"].findings_for_map(m_live)) == Counter(mods["P1"].findings_for_map(m_live))
    check("K9a", "C0 window NULL control: composed-inert R5 behaves exactly like the prose patch alone",
          inert_ok0, {"identical_on_batteries_and_live_map": inert_ok0})
    check("K9b", "C0 window OVERFIRE control: composed-overfire R5 breaks >=5 negative cases",
          over_hits0 >= 5, {"negative_cases_newly_flagged": over_hits0})
    check("K9c", "C1 window NULL control: composed-inert R5 behaves exactly like the rebased prose patch alone",
          inert_ok1, {"identical_on_batteries_and_live_map": inert_ok1})
    check("K9d", "C1 window OVERFIRE control: composed-overfire R5 breaks >=5 negative cases",
          over_hits1 >= 5, {"negative_cases_newly_flagged": over_hits1})

    # ------------------------------------------------------------------ K10 text-route scope
    text_rows = [r for r in x_rows if r["surface"] == "text"] + [r for r in s_rows if r["surface"] == "text"]
    text_flat = all(len(set(r["counts"].values())) == 1 for r in x_rows if r["surface"] == "text") and \
        all(len(set(r["counts"].values())) == 1 for r in s_rows if r["surface"] == "text")
    check("K10a", "artifact-text route: identical under all 8 revisions on every text-surface case",
          text_flat, {"text_cases": len(text_rows)})
    x11 = [r for r in x_rows if r["id"] == "X11_text_route_container_line"][0]
    check("K10b", "artifact-text route remains blind to class_ids containers (documented limitation)",
          all(x11["counts"][rev] == 0 for rev in ALL_REVS), x11["counts"])

    # ------------------------------------------------------------------ K11 drift
    h_end = {k: sha256_file(p) for k, p in paths.items()}
    drift = {k: {"start": h_start[k], "end": h_end[k]} for k in h_start if h_start[k] != h_end[k]}
    check("K11a", "all pinned snapshots, composed candidates and fixture batteries were byte-stable",
          not drift, {"drift": drift})
    live_end = {
        "canonical": sha256_file(ROOT / "research_map/class_separation.py"),
        "prose": sha256_file(ROOT / "proposed/class_separation.py"),
        "container": sha256_file(ROOT / "artifacts/worker-036/classsep_disj_rule/candidate_class_separation.py"),
        "map": sha256_file(ROOT / "research_map/research_map.json"),
        "ledger": sha256_file(ROOT / "ledger/theorems.jsonl"),
    }
    live_drift = {"canonical_start": PIN_C0, "canonical_live_end": live_end["canonical"],
                  "canonical_equals_pinned_C1": live_end["canonical"] == PIN_C1,
                  "prose_live_end": live_end["prose"], "container_live_end": live_end["container"],
                  "map_moved_under_traffic": live_end["map"] != h_start["map_live"],
                  "ledger_moved_under_traffic": live_end["ledger"] != PIN_LEDGER}

    overall = "PASS" if all(c["ok"] for c in checks) else "FAIL"
    report = {
        "task_id": "W036-CLASSSEP-COMPOSE-01",
        "worker": "worker-036",
        "node_id": "A1",
        "gate": "G-AUDIT/G-CLASSBIND",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "scope_classes": FROZEN_CLASSES,
        "created_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "authority": "Worker measurement evidence only. No canonical file, map, gate, node status or ledger modified; no canonical patch applied. A message is not a result until the controller applies it and records the artifact hash.",
        "question": "Do the two staged class-separation candidates (prose-precision e2d24b927ee8 and container-recall 1bc87c9542ed) compose mechanically and behave additively — on the pinned base, and rebased onto the live canonical a8c04fc31e4a that moved mid-lifecycle?",
        "revisions": {
            "C0": {"role": "pinned canonical base", "sha256": PIN_C0},
            "C1": {"role": "live canonical base (CF-16 meta-quote exemption)", "sha256": PIN_C1},
            "P": {"role": "prose-precision staged patch, authored on C0", "sha256": PIN_P, "owner": "worker-16"},
            "R": {"role": "container-recall staged patch, authored on C0", "sha256": PIN_R, "owner": "worker-036"},
            "PR0": {"role": "C0 + P + R (primary composition)", "sha256": h_start["PR0"]},
            "P1": {"role": "C1 + P (3-way rebase)", "sha256": h_start["P1"]},
            "R1": {"role": "C1 + R (3-way rebase)", "sha256": h_start["R1"]},
            "PR1": {"role": "C1 + P + R (3-way rebase composition)", "sha256": h_start["PR1"]},
            "INERT0": {"role": "primary null control (R5 threshold 99)", "sha256": h_start["INERT0"]},
            "OVER0": {"role": "primary power control (R5 threshold 1)", "sha256": h_start["OVER0"]},
            "INERT1": {"role": "rebased null control (R5 threshold 99)", "sha256": h_start["INERT1"]},
            "OVER1": {"role": "rebased power control (R5 threshold 1)", "sha256": h_start["OVER1"]},
        },
        "composition": {
            "base_c0": build["windows"]["base_c0"],
            "base_c1": build["windows"]["base_c1"],
            "naive_reapply_hazard": {
                "note": "Diffing each staged patch *file* against C1 (2-way) would delete C1's own 3-line exemption; the valid rebase is the 3-way delta merge used here.",
                "measured": build["windows"]["base_c1"]["naive_reapply_hazard"],
            },
        },
        "checks": checks,
        "worker085_battery_replay": s_rows,
        "prior_disj_battery_replay": d_rows,
        "compose_battery": x_rows,
        "additivity": {
            "base_c0": {"items": len(add0), "interaction_count": len(inter0), "interactions": inter0,
                        "aggregate_counts": agg0},
            "base_c1": {"items": len(add1), "interaction_count": len(inter1), "interactions": inter1,
                        "aggregate_counts": agg1},
        },
        "map_measurements": {"frozen_C0_window": frozen0, "live_C0_window": live0, "live_C1_window": live1},
        "ledger_container_rows": led,
        "corpus_regression": {
            "worker_07": {rev: {k: reg[rev][k] for k in ("tp", "fn", "tn", "fp", "verdict")} for rev in ALL_REVS},
            "worker_07_corpus_digest": w07_digest_end,
            "worker_027_ood": ood,
        },
        "controls": {
            "base_c0": {"inert_equals_prose_only": inert_ok0, "overfire_negative_hits": over_hits0},
            "base_c1": {"inert_equals_rebased_prose_only": inert_ok1, "overfire_negative_hits": over_hits1},
        },
        "live_drift_observations": {
            "note": "Live files move under swarm traffic; the measurement binds to the snapshots above. The canonical moved C0 -> C1 during this lifecycle; if it moves again the rebase window must be re-run.",
            "detectors": live_drift,
            "live_map_sha256_end": live_end["map"],
            "live_ledger_sha256_end": live_end["ledger"],
        },
        "limitations": [
            "Composition is measured for the two named staged candidates only; the C1 exemption is treated as the new base, not re-adjudicated here.",
            "The artifact-text route (findings_for_text) is out of scope for both patches and stays blind to class_ids containers (X11/K10b measured).",
            "R's container rule flags every class_ids container with >=2 frozen classes; the precision/cardinality policy for map claims remains an owner decision (W036-CLASSSEP-DISJ-RULE-01 limitation, re-measured here on the live snapshot).",
            "P does not clear the live CF-16 claim-statement shape (worker-085 S9 reproduced here; the C1 exemption clears 4 live findings instead); neither patch alone nor their composition restores the live claim-statement hard count below the C1 level.",
            "Adoption, rebasing and any canonical edit remain with the detector owner (CF-4); this packet is worker evidence, not an adopt/reject verdict.",
        ],
        "falsifiers": [
            "F1: any window where PR != C + P + R (conflicting hunks, rebase conflict, reverse-apply not the base, or delta content not the union) -> composition invalid.",
            "F2: any measured item where Counter(PR) != Counter(P) + Counter(R) - Counter(C) -> the two patches interact and single-patch measurements cannot be summed.",
            "F3: any external-control mismatch against worker-085's 12 counts or the prior packet's 26 expectations -> replay harness untrustworthy, all compose numbers void.",
            "F4: worker-07 corpus fn>0 or fp>0, or any per-fixture classification change under any of the 8 revisions -> regression.",
            "F5: a live-map added finding not carrying 'container disjoins' (R) or not in statement-mode (P) -> patch changed a surface it does not own.",
            "F6: a null control changing any finding, or an overfire control failing to break >=5 negative cases -> harness has no power.",
            "F7: a naive 2-way reapply of either patch file onto C1 that does NOT revert C1's own edit -> the rebase hazard claim is wrong (and naive reapply might be safe after all).",
            "F8: any pinned input drifting mid-run -> window void; restore from snapshots and re-run.",
        ],
        "overall": overall,
    }
    (HERE / "report.json").write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({c["id"]: ("PASS" if c["ok"] else "FAIL") for c in checks}, indent=1))
    print("overall:", overall)
    print("C0 window aggregate:", agg0)
    print("C1 window aggregate:", agg1)
    print("live map C0 window totals:", live0["totals"], "C1 window totals:", live1["totals"])
    print("C0-window interactions:", len(inter0), "C1-window interactions:", len(inter1))
    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
