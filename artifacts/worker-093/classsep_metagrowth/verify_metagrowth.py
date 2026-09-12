#!/usr/bin/env python3
"""W093-CLASSSEP-METAGROWTH-01 independent verifier.

Question: between controller pass-04 (10 CLASSSEP hard failures, map 3d45be59) and
pass-05 (17, map 11311ab3), is the growth of the class-separation hard list
first-order class-leakage assertion, formulation-context mention, or meta-traffic
about the audit itself?

Read-only on canonical paths: the pinned detector copy is imported, the maps are
read from frozen snapshots, and nothing under research_map/ is written.

Exit semantics (fail-closed):
  0 = all pre-registered checks E1-E9 pass
  1 = at least one check failed
  2 = missing target or hash drift against a pen
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent

PIN_DETECTOR = "c266dbceca87fb996bd76a774145ef511cbf2aae190d9f423167d3200783a920"
PIN_MAP_PASS05 = "11311ab3600514cd34ca7332714a4aa27b97e4fdc124f29179122e11f844974d"
PIN_MAP_PASS04 = "3d45be5969ec388ef4a3e10d5eb87b81dbf3d03138510b75ff6a56453ceae005"
PIN_LIFECYCLE_PASS04 = "dae3e6fbda025e836da0f16702c4cef394a9129cbc2cb0a24e08db949514f767"
PIN_LIFECYCLE_PASS05 = "2aa847cc28659ed403c500a2e52d429c529428c089f8cfc0e03eedb94f6eb3bd"
PIN_W035_REPORT = "47f0c15834e655dcfa971219f400b08103fcf479786d6ae0d9df62ece4d5aafd"

PINNED = HERE / "pinned"
SNAP = HERE / "snapshot"
DETECTOR = PINNED / "class_separation.c266dbce.py"
MAP_PASS05 = SNAP / "map.pass05.json"
MAP_PASS04 = PINNED / "map.pass04.worker-035.json"
LC_PASS04 = PINNED / "lifecycle-pass04.json"
LC_PASS05 = PINNED / "lifecycle-pass05.json"
W035 = PINNED / "worker-035-report.json"
FIXTURES = HERE / "preregistered_fixtures.jsonl"
SELF_CLAIM = HERE / "self_claim_statement.txt"
LIVE_MAP = REPO / "research_map/research_map.json"
LIVE_DETECTOR = REPO / "research_map/class_separation.py"

BOUNDARY = set(";.!?\u2014\n")
META_MARK = re.compile(
    r"CLASSSEP|class[_\s-]?separation|detector|checker|audit|false\s+positive|"
    r"hard[_\s-]?failure|regex|findings_for_map|regression\s+corpus|"
    r"flag(?:s|ged)?|\bscan(?:s|ned)?\b", re.I)
NEG_CUE = re.compile(r"\b(?:no|not|never|without|zero|absent|nor)\b|non-|rather\s+than|instead\s+of",
                     re.I)
CASE_ID = re.compile(r"\b(?:TC|FX|CASE|ROW|FIXTURE)-[A-Za-z0-9-]+\b")


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def enum_composite(mod, text: str, where: str, mode: str = "prose") -> list:
    """Faithful span-carrying re-implementation of mod._scan_composite."""
    t = mod.norm(text)
    out = []
    for m in mod._MERGE_PAT.finditer(t):
        lo, hi = max(0, m.start() - 60), min(len(t), m.end() + 60)
        ctx = t[lo:hi]
        if mod._BENIGN.search(t[max(0, m.start() - 8):m.end() + 8]):
            continue
        am = mod._MERGE_ASSERT.search(ctx)
        if am:
            before = ctx[:am.start()]
            if mod._NEG_BEFORE_ASSERT.search(before):
                continue
            out.append({"finding": (f"CLASSSEP: composite C0/C2 asserted as one class in {where}: "
                                    f"...{ctx.strip()!r}"),
                        "kind": "composite_assert",
                        "trigger": (m.start(), m.end()),
                        "window": (lo, hi),
                        "assert": (am.start() + lo, am.end() + lo),
                        "text_len": len(t)})
        elif mod._PROHIBIT.search(ctx):
            continue
        elif mod._SPLIT.search(ctx):
            continue
        elif mode == "declaration":
            out.append({"finding": f"CLASSSEP: bare composite C0/C2 expression in {where}: ...{ctx.strip()!r}",
                        "kind": "composite_bare",
                        "trigger": (m.start(), m.end()),
                        "window": (lo, hi),
                        "assert": None,
                        "text_len": len(t)})
    return out


def enum_findings(mod, obj, where: str, mode: str = "prose") -> list:
    """Faithful span-carrying re-implementation of mod.findings()."""
    out = []
    if not isinstance(obj, dict):
        return out
    class_id = str(obj.get("class_id") or "")
    for key, val in obj.items():
        if key in ("class_id", "class_ids"):
            probe = []
            mod._scan_class_ids(val, f"{where}.{key}", probe)
            out += [{"finding": s, "kind": "class_id", "trigger": None, "window": None,
                     "assert": None, "text_len": 0} for s in probe]
            continue
        if key not in mod.DECLARATION_KEYS:
            continue
        if isinstance(val, str):
            out += enum_composite(mod, val, f"{where}.{key}", mode)
            if mode == "declaration":
                pass
            if key in ("conclusion", "conclusion_type", "scope", "scope_statement"):
                probe = []
                mod._scan_conclusion(val, class_id, f"{where}.{key}", probe)
                out += [{"finding": s, "kind": "conclusion", "trigger": None, "window": None,
                         "assert": None, "text_len": 0} for s in probe]
        elif isinstance(val, list):
            for i, v in enumerate(val):
                if isinstance(v, str):
                    out += enum_composite(mod, v, f"{where}.{key}[{i}]", mode)
    return out


def classify(mod, stmt: str, item: dict, meta_scope: str = "statement") -> dict:
    """Apply the pre-registered label rule. Returns {label, reason}.

    meta_scope="statement" is the pre-registered rule (E3/E4). meta_scope="window" is the
    secondary diagnostic only: the apparatus marker must sit inside the detector's own window.
    """
    if item["trigger"] is None:
        return {"label": "OTHER", "reason": "non-composite finding (no trigger span)"}
    t = mod.norm(stmt)
    ts, te = item["trigger"]
    if meta_scope == "window":
        lo, hi = item["window"]
        hit = META_MARK.search(t[lo:hi])
    else:
        hit = META_MARK.search(t)
    if hit:
        return {"label": "META", "reason": f"{meta_scope}-level audit/apparatus marker {hit.group(0)!r}"}
    # clause boundaries around the trigger
    cs = 0
    for j in range(ts - 1, -1, -1):
        if t[j] in BOUNDARY:
            cs = j + 1
            break
    ce = len(t)
    for j in range(te, len(t)):
        if t[j] in BOUNDARY:
            ce = j
            break
    clause = t[cs:ce]
    rel = ts - cs
    prefix = clause[:max(0, rel)]
    if (prefix.count("'") % 2 == 1) or (prefix.count('"') % 2 == 1):
        return {"label": "MENTION", "reason": "QUOTED: trigger inside an unclosed straight-quote span",
                "clause": clause}
    if NEG_CUE.search(clause):
        return {"label": "MENTION", "reason": "NEGATED: negation/rejection cue in the trigger clause",
                "clause": clause}
    if CASE_ID.search(prefix):
        return {"label": "MENTION", "reason": "CASE_LABEL: case id before the trigger in the clause",
                "clause": clause}
    if item["assert"] is not None:
        a0, a1 = item["assert"]
        between = t[min(a0, ts):max(a1, te)] if (a1 <= ts or te <= a0) else ""
        if any(ch in BOUNDARY for ch in between):
            return {"label": "MENTION", "reason": "CROSS_CLAUSE: clause boundary between trigger and merge word",
                    "clause": clause}
    return {"label": "ASSERTION", "reason": "no meta marker, quote, negation, case label or clause gap",
            "clause": clause}


def lifecycle_classep(path: Path) -> list:
    d = json.loads(path.read_text())
    return [h for h in (d.get("evidence_hard_failures") or []) if str(h).startswith("CLASSSEP")]


def main() -> int:
    checks = []
    for p in (DETECTOR, MAP_PASS05, MAP_PASS04, LC_PASS04, LC_PASS05, W035, FIXTURES, SELF_CLAIM):
        if not p.exists():
            print(f"MISSING TARGET: {p}", file=sys.stderr)
            return 2
    drift = []
    pins_before = {str(p.relative_to(HERE)): sha256_file(p) for p in
                   (DETECTOR, MAP_PASS05, MAP_PASS04, LC_PASS04, LC_PASS05, W035)}
    expected_pins = {
        "pinned/class_separation.c266dbce.py": PIN_DETECTOR,
        "snapshot/map.pass05.json": PIN_MAP_PASS05,
        "pinned/map.pass04.worker-035.json": PIN_MAP_PASS04,
        "pinned/lifecycle-pass04.json": PIN_LIFECYCLE_PASS04,
        "pinned/lifecycle-pass05.json": PIN_LIFECYCLE_PASS05,
        "pinned/worker-035-report.json": PIN_W035_REPORT,
    }
    for k, v in expected_pins.items():
        if pins_before[k] != v:
            print(f"HASH DRIFT on pinned input {k}", file=sys.stderr)
            return 2
    live_det_sha = sha256_file(LIVE_DETECTOR)
    if live_det_sha != PIN_DETECTOR:
        drift.append({"item": "live research_map/class_separation.py", "pin": PIN_DETECTOR,
                      "measured": live_det_sha})
    live_map_sha = sha256_file(LIVE_MAP)

    mod = load_module("w093_metagrowth_detector", DETECTOR)
    m5 = json.loads(MAP_PASS05.read_text())
    m4 = json.loads(MAP_PASS04.read_text())

    # ---------------- E1: reproduce both lifecycle hard lists -----------------
    can5 = mod.findings_for_map(m5)
    can4 = mod.findings_for_map(m4)
    lc5 = lifecycle_classep(LC_PASS05)
    lc4 = lifecycle_classep(LC_PASS04)
    e1a = sorted(can5) == sorted(lc5) and len(can5) == 17
    e1b = sorted(can4) == sorted(lc4) and len(can4) == 10
    outside5 = [f for f in can5 if "claims[" not in f]
    checks.append({"id": "E1a-pass05-list-reproduced", "pass": bool(e1a),
                   "detail": {"canonical": len(can5), "lifecycle": len(lc5),
                              "identical": sorted(can5) == sorted(lc5),
                              "findings_outside_claims": outside5}})
    checks.append({"id": "E1b-pass04-list-reproduced", "pass": bool(e1b),
                   "detail": {"canonical": len(can4), "lifecycle": len(lc4),
                              "identical": sorted(can4) == sorted(lc4)}})

    # ---------------- E1c: span enumeration reproduces canonical -------------
    enum5 = []
    for i, c in enumerate(m5.get("claims", [])):
        if isinstance(c, dict):
            enum5 += enum_findings(mod, c, f"claims[{i}]", mode="prose")
    e1c = sorted(x["finding"] for x in enum5) == sorted(can5)
    checks.append({"id": "E1c-span-enumeration-equivalence", "pass": bool(e1c),
                   "detail": {"enumerated": len(enum5), "canonical": len(can5),
                              "missing": sorted(set(can5) - {x["finding"] for x in enum5}),
                              "extra": sorted({x["finding"] for x in enum5} - set(can5))}})

    # ---------------- E2: delta is exactly claims 180/187/192 ----------------
    root5 = sorted({int(re.search(r"claims\[(\d+)\]", f).group(1)) for f in can5})
    root4 = sorted({int(re.search(r"claims\[(\d+)\]", f).group(1)) for f in can4})
    delta_findings = sorted(set(can5) - set(can4))
    delta_roots = sorted({int(re.search(r"claims\[(\d+)\]", f).group(1)) for f in delta_findings})
    added_roots = sorted(set(root5) - set(root4))
    e2 = (len(delta_findings) == 7 and added_roots == [180, 187, 192]
          and len(can5) - len(can4) == 7 and not (set(can4) - set(can5)))
    checks.append({"id": "E2-delta-is-7-new-meta-claims", "pass": bool(e2),
                   "detail": {"pass04_n": len(can4), "pass05_n": len(can5),
                              "delta_n": len(delta_findings), "delta_roots": delta_roots,
                              "added_root_claims": added_roots, "removed": sorted(set(can4) - set(can5))}})

    # ---------------- E3/E4: classification -----------------------------------
    enum5_by_finding = {x["finding"]: x for x in enum5}
    per_finding = []
    for f in can5:
        item = enum5_by_finding[f]
        ci = int(re.search(r"claims\[(\d+)\]", f).group(1))
        lab = classify(mod, m5["claims"][ci]["statement"], item)
        per_finding.append({"claim_index": ci, "label": lab["label"], "reason": lab["reason"],
                            "clause": lab.get("clause", "")[:220],
                            "finding_sha256": hashlib.sha256(f.encode()).hexdigest()[:16]})
    counts = {}
    for r in per_finding:
        counts[r["label"]] = counts.get(r["label"], 0) + 1
    e3 = counts.get("ASSERTION", 0) == 0
    delta_labels = {}
    for f in delta_findings:
        r = next(x for x in per_finding
                 if x["finding_sha256"] == hashlib.sha256(f.encode()).hexdigest()[:16])
        delta_labels[r["label"]] = delta_labels.get(r["label"], 0) + 1
    e4 = delta_labels.get("META", 0) == 7 and delta_labels.get("ASSERTION", 0) == 0
    # Secondary diagnostic, NOT part of the pre-registered E-suite: the statement-level META
    # marker is broad (every claim is a measurement report), so also report the split when the
    # apparatus marker must sit inside the detector's own +/-60-char window.
    proximal = []
    for f in can5:
        item = enum5_by_finding[f]
        ci = int(re.search(r"claims\[(\d+)\]", f).group(1))
        lab = classify(mod, m5["claims"][ci]["statement"], item, meta_scope="window")
        proximal.append(lab["label"])
    prox_counts = {}
    for x in proximal:
        prox_counts[x] = prox_counts.get(x, 0) + 1
    prox_delta = {}
    for f in delta_findings:
        ci = int(re.search(r"claims\[(\d+)\]", f).group(1))
        lab = proximal[[i for i, x in enumerate(can5) if x == f][0]]
        prox_delta[lab] = prox_delta.get(lab, 0) + 1
    # Factual observation (no expectation): is the trigger inside an unclosed straight-quote span
    # measured on the whole statement? Resolves the one window-diagnostic ASSERTION flag.
    quoted_obs = []
    for idx, f in enumerate(can5):
        item = enum5_by_finding[f]
        ci = int(re.search(r"claims\[(\d+)\]", f).group(1))
        t = mod.norm(m5["claims"][ci]["statement"])
        ts = item["trigger"][0]
        quoted = (t[:ts].count("'") % 2 == 1) or (t[:ts].count('"') % 2 == 1)
        quoted_obs.append({"claim_index": ci, "window_label": proximal[idx],
                           "trigger_inside_statement_quote_span": bool(quoted)})
    prox_assertions = [q for q in quoted_obs if q["window_label"] == "ASSERTION"]
    checks.append({"id": "E3-zero-first-order-assertions", "pass": bool(e3),
                   "detail": {"label_counts": counts, "n": len(per_finding)}})
    checks.append({"id": "E4-delta-all-meta", "pass": bool(e4),
                   "detail": {"delta_label_counts": delta_labels}})

    # ---------------- E5: labeled controls ------------------------------------
    fixture_fail = []
    fixture_rows = [json.loads(l) for l in FIXTURES.read_text().splitlines() if l.strip()]
    for r in fixture_rows:
        labs = {classify(mod, r["text"], x)["label"] for x in enum_composite(mod, r["text"], r["fixture_id"])}
        got = ("META" if "META" in labs else
               "ASSERTION" if "ASSERTION" in labs else "MENTION" if labs else "NONE")
        flagged = bool(mod.findings_for_text(r["text"], r["fixture_id"]))
        if got != r["expect_label_class"] or flagged != r["expect_canonical_flagged"]:
            fixture_fail.append({"fixture_id": r["fixture_id"], "kind": r["kind"],
                                 "expected": [r["expect_label_class"], r["expect_canonical_flagged"]],
                                 "got": [got, flagged]})
    kinds = {}
    for r in fixture_rows:
        kinds[r["kind"]] = kinds.get(r["kind"], 0) + 1
    e5 = not fixture_fail
    checks.append({"id": "E5-labeled-controls", "pass": bool(e5),
                   "detail": {"n": len(fixture_rows), "kinds": kinds, "failures": fixture_fail}})

    # ---------------- E6: external agreement with worker-035 -----------------
    # Pairing is by the exact canonical finding string (two adjudications share claim_index 112,
    # so index-keyed pairing collapses them; fixed after the first run, no rule/expectation change).
    w35 = json.loads(W035.read_text())
    mine_by_finding = {f: r for f in can5 for r in per_finding
                       if r["finding_sha256"] == hashlib.sha256(f.encode()).hexdigest()[:16]}
    agree = []
    for a in w35["adjudications"]:
        ci = a["claim_index"]
        stmt = m5["claims"][ci]["statement"]
        sha_ok = hashlib.sha256(stmt.encode()).hexdigest() == a.get("statement_sha256")
        mine = mine_by_finding.get(a["canonical_finding"])
        agree.append({"claim_index": ci, "worker035": a["verdict"],
                      "mine": mine["label"] if mine else "NOT_PAIRED",
                      "finding_pair": mine is not None,
                      "statement_sha256_match": sha_ok,
                      "agrees_non_assertion": bool(mine) and mine["label"] != "ASSERTION"})
    e6 = (len(agree) == 10 and all(x["finding_pair"] and x["statement_sha256_match"]
                                   and x["agrees_non_assertion"] for x in agree))
    checks.append({"id": "E6-worker035-agreement", "pass": bool(e6),
                   "detail": {"n": len(agree),
                              "all_paired": all(x["finding_pair"] for x in agree),
                              "all_non_assertion": all(x["agrees_non_assertion"] for x in agree),
                              "all_statement_hashes_match": all(x["statement_sha256_match"] for x in agree),
                              "rows": agree}})

    # ---------------- E7: self-reproduction -----------------------------------
    finding36 = next((f for f in can4 if "claims[36]" in f), None)
    repro_text = f"Verification note: the canonical audit reports {finding36!r} in the frozen map."
    repro_map_hits = mod.findings_for_text(repro_text, "self_reproduction")
    repro_claim_hits = enum_findings(mod, {"statement": repro_text, "class_id": "AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN"},
                                     "claims[self_reproduction]", mode="prose")
    e7 = len(repro_claim_hits) >= 1 and len(repro_map_hits) >= 1
    checks.append({"id": "E7-self-reproduction", "pass": bool(e7),
                   "detail": {"quoted_finding_claim_findings": len(repro_claim_hits),
                              "quoted_finding_text_findings": len(repro_map_hits),
                              "source_finding_claim": 36}})

    # ---------------- E8: self-application prediction -------------------------
    self_stmt = SELF_CLAIM.read_text().strip()
    self_hits = enum_findings(mod, {"statement": self_stmt, "class_id": "AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN"},
                              "claims[self_claim]", mode="prose")
    e8 = len(self_hits) >= 1
    checks.append({"id": "E8-self-application-flagged", "pass": bool(e8),
                   "detail": {"predicted_findings_on_own_claim": len(self_hits),
                              "previews": [h["finding"][:160] for h in self_hits],
                              "self_claim_sha256": hashlib.sha256(self_stmt.encode()).hexdigest()}})

    # ---------------- E9: no drift --------------------------------------------
    pins_after = {k: sha256_file(HERE / k) for k in pins_before}
    e9 = pins_after == pins_before
    checks.append({"id": "E9-no-input-drift", "pass": bool(e9),
                   "detail": {"unchanged": e9, "drift": drift,
                              "live_map_sha256_at_read": live_map_sha,
                              "live_map_matches_pass05_pin": live_map_sha == PIN_MAP_PASS05}})

    verdict = "PASS" if all(c["pass"] for c in checks) else "FAIL"
    report = {
        "schema": "w093/classsep-metagrowth/v1",
        "task_id": "W093-CLASSSEP-METAGROWTH-01",
        "worker": "worker-093",
        "role": "bounded execution worker",
        "created_at": now(),
        "node_id": "A1",
        "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "gate_scope": ["G-AUDIT"],
        "question": ("Between controller pass-04 (10 CLASSSEP hard failures) and pass-05 (17), "
                     "is the growth first-order class-leakage assertion, formulation-context "
                     "mention, or meta-traffic about the audit itself?"),
        "pins": {k: {"sha256": v} for k, v in pins_before.items()},
        "live_observation": {"research_map/research_map.json": live_map_sha,
                             "research_map/class_separation.py": live_det_sha,
                             "detector_matches_pin": live_det_sha == PIN_DETECTOR},
        "checks": checks,
        "classification": {"label_counts": counts, "per_finding": per_finding,
                           "proximal_marker_diagnostic": {
                               "note": ("secondary diagnostic, not a pre-registered check: label when "
                                        "the audit/apparatus marker must sit inside the detector's own "
                                        "+/-60-char window"),
                               "label_counts": prox_counts}},
        "growth": {"pass04_hard": len(can4), "pass05_hard": len(can5),
                   "delta_hard": len(delta_findings), "delta_roots": delta_roots,
                   "delta_label_counts": delta_labels,
                   "delta_proximal_label_counts": prox_delta,
                   "meta_share_of_delta": (delta_labels.get("META", 0) / len(delta_findings)
                                           if delta_findings else None)},
        "self_application": {"self_claim_sha256": hashlib.sha256(self_stmt.encode()).hexdigest(),
                             "predicted_new_hard_findings": len(self_hits)},
        "observations": {
            "window_diagnostic_assertion_flags": prox_assertions,
            "note": ("the single window-scope ASSERTION flag (claims[187]) has its trigger inside a "
                     "straight-quote span of the statement ('... merged C0/C2 ...'); it is a quoted "
                     "mention, so the pre-registered statement-scope E3 result (0 assertions) stands"),
            "quoted_trigger_count": sum(1 for q in quoted_obs
                                        if q["trigger_inside_statement_quote_span"]),
        },
        "drift": drift,
        "result": {"verdict": verdict},
        "falsifier": ("FALSIFIED if any of E1-E9 fails, or if any of the 17 findings is "
                      "independently a first-order assertion that C0 and C2 are one class, or if a "
                      "pinned input drifts, or if the span enumeration does not reproduce the "
                      "canonical list. A detector-rule edit after seeing these results voids the run."),
        "non_claims": [
            "no canonical file was modified; read-only measurement",
            "no gate verdict, no node status, no validation_status=passed",
            "the META/MENTION/ASSERTION labels are this instrument's pre-registered rule, not a "
            "replacement for worker-035's adjudication; they are reported with the clause text",
            "this task does not propose or apply a detector change; it measures the audit list's growth",
        ],
        "reproduce": "python3 artifacts/worker-093/classsep_metagrowth/verify_metagrowth.py",
    }
    (HERE / "report.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    print("checks: " + ", ".join(f"{c['id']}={'PASS' if c['pass'] else 'FAIL'}" for c in checks))
    print(f"VERDICT: {verdict}")
    print(f"pass04 hard={len(can4)} pass05 hard={len(can5)} delta={len(delta_findings)} "
          f"roots={delta_roots} delta_labels={delta_labels}")
    print(f"all-17 labels: {counts}")
    print(f"proximal-marker diagnostic: {prox_counts} (delta {prox_delta})")
    print(f"self-application predicted findings on own claim: {len(self_hits)}")
    if drift:
        print("DRIFT:", json.dumps(drift))
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
