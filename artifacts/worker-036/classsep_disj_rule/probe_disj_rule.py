#!/usr/bin/env python3
"""W036-CLASSSEP-DISJ-RULE-01 probe — staged container-disjunction rule for the
class-separation detector.

Bounded, class-bound worker measurement (worker-036, node A1, gate G-AUDIT/G-CLASSBIND,
frozen classes AF-WCC-VAC-GEN / AF-SCC-C2-VAC-GEN / AF-SCC-C0-VAC-GEN / AF-WCC-SCALAR-SPH).

Question: canonical `research_map/class_separation.py` at c266dbceca87 checks `class_id` /
`class_ids` tokens one at a time, so a container binding two or more distinct frozen classes
is invisible (W036-CLASSSEP-DISJ-01/02/03).  Does a mechanically generated candidate that
adds exactly one container-level rule (R5) close that blind spot, without changing any other
surface, and what would it flag on the live pinned map / the three pinned L0 ledger revisions?

All input bytes are read from snapshots taken under this directory.  Canonical artifacts are
never written.  Verdict is measurement evidence only: no gate verdict, no node status.

Run: python3 artifacts/worker-036/classsep_disj_rule/probe_disj_rule.py
"""
from __future__ import annotations

import datetime
import difflib
import hashlib
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]

# ---------------------------------------------------------------- pins
PIN_CANONICAL = "c266dbceca87fb996bd76a774145ef511cbf2aae190d9f423167d3200783a920"
PIN_MAP = "3d45be5969ec388ef4a3e10d5eb87b81dbf3d03138510b75ff6a56453ceae005"
PIN_CORPUS_W07 = "d69ad58468be16655921dcf0eab9570fa6e7ccaf828558a45d4b306cce3de452"
LEDGER_PINS = {
    "a1674f094979": "a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28",
    "3e3d35531421": "3e3d35531421388a17ca7bad7f6c7093dd1cc21a3a808ca8ff65ce6c2b79c6a6",
    "ce42d205e761": "ce42d205e7617e3a032c109b24a00b57c7c6b104f37dad5125745af15deebd72",
}
EXPECTED_DISJ_ROWS = {3, 4, 24, 26, 29, 45, 57, 59}
FROZEN_CLASSES = {
    "AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH",
}


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def load_text(name: str, text: str):
    d = HERE / "controls"
    d.mkdir(exist_ok=True)
    p = d / f"{name}.py"
    p.write_text(text)
    return load(name, p), p


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


def scan(mod, surface: str, obj, where: str):
    if surface == "object":
        return mod.findings(obj, where, mode="declaration")
    if surface == "map":
        return mod.findings_for_map(obj)
    if surface == "text":
        return mod.findings_for_text(obj, where)
    raise ValueError(surface)


def score_corpus(mod, corpus_dir: Path):
    """Independent re-implementation of class_separation.regression() with an explicit
    repo root (the module's own helper derives the root from its __file__, which is wrong
    for a snapshot-loaded copy)."""
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
    return {"tp": tp, "fn": fn, "tn": tn, "fp": fp, "corpus_size": tp + fn + tn + fp, "per_fixture": per}


def _known_in(value):
    if isinstance(value, str):
        toks = [t.strip().upper() for t in value.replace(";", ",").split(",")]
    elif isinstance(value, list):
        toks = [str(t).strip().upper() for t in value]
    else:
        toks = []
    return {t for t in toks if t in FROZEN_CLASSES}


def _walk_containers(obj, where, hits):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in ("class_id", "class_ids"):
                known = _known_in(v)
                if len(known) >= 2:
                    hits.append({"where": f"{where}.{k}", "classes": sorted(known)})
            _walk_containers(v, f"{where}.{k}", hits)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _walk_containers(v, f"{where}[{i}]", hits)


def containers_in_map_surfaces(m: dict) -> list:
    """Direct re-derivation on exactly the surfaces findings_for_map() scans."""
    hits: list = []
    for g in m.get("groups", []):
        for n in g.get("nodes", []):
            _walk_containers(n, f"node {n.get('id', '?')}", hits)
    for i, ev in enumerate(m.get("portfolio_events", [])):
        _walk_containers(ev, f"portfolio_events[{i}]", hits)
    for i, c in enumerate(m.get("claims", [])):
        _walk_containers(c, f"claims[{i}]", hits)
    return hits


def reverse_apply(canon_text: str, cand_text: str):
    """Remove the inserted lines (sequence order) from the candidate; return the result
    or None if any inserted line is absent."""
    diff = list(difflib.unified_diff(canon_text.splitlines(keepends=True),
                                     cand_text.splitlines(keepends=True), n=0))
    inserted = [ln[1:] for ln in diff if ln.startswith("+") and not ln.startswith("+++")]
    removed = [ln[1:] for ln in diff if ln.startswith("-") and not ln.startswith("---")]
    cur = cand_text
    for ln in inserted:
        if ln not in cur:
            return None, inserted, removed
        cur = cur.replace(ln, "", 1)
    return cur, inserted, removed


def main() -> int:
    checks: list = []

    def check(cid, desc, ok, measured):
        checks.append({"id": cid, "desc": desc, "ok": bool(ok), "measured": measured})
        return bool(ok)

    # ------------------------------------------------ H0 pins + drift window (start)
    cand_path = HERE / "candidate_class_separation.py"
    snap_canon = HERE / "snapshots" / "class_separation.canonical.c266dbceca87.py"
    snap_map = HERE / "snapshots" / "research_map.3d45be5969ec.json"
    snap_ledgers = {
        "a1674f094979": HERE / "snapshots" / "theorems.a1674f094979.jsonl",
        "3e3d35531421": HERE / "snapshots" / "theorems.3e3d35531421.jsonl",
        "ce42d205e761": HERE / "snapshots" / "theorems.ce42d205e761.jsonl",
    }
    fixtures_path = HERE / "fixtures" / "disj_fixtures.jsonl"
    probe_path = Path(__file__).resolve()

    measured_start = {
        "snapshot_canonical": sha256_file(snap_canon),
        "snapshot_map": sha256_file(snap_map),
        "snapshot_theorems_a1674f094979": sha256_file(snap_ledgers["a1674f094979"]),
        "snapshot_theorems_3e3d35531421": sha256_file(snap_ledgers["3e3d35531421"]),
        "snapshot_theorems_ce42d205e761": sha256_file(snap_ledgers["ce42d205e761"]),
        "candidate": sha256_file(cand_path),
        "fixtures": sha256_file(fixtures_path),
        "probe": sha256_file(probe_path),
        "build_candidate": sha256_file(HERE / "build_candidate.py"),
        "live_canonical": sha256_file(ROOT / "research_map/class_separation.py"),
        "live_map": sha256_file(ROOT / "research_map/research_map.json"),
        "live_ledger": sha256_file(ROOT / "ledger/theorems.jsonl"),
        "corpus_w07_results": sha256_file(ROOT / "artifacts/worker-07/class_separation_falsification/results.json"),
    }
    check("H0a", "canonical snapshot is the pinned module c266dbceca87",
          measured_start["snapshot_canonical"] == PIN_CANONICAL, measured_start["snapshot_canonical"])
    check("H0b", "live research_map/class_separation.py still equals the pinned canonical bytes",
          measured_start["live_canonical"] == PIN_CANONICAL, measured_start["live_canonical"])
    check("H0c", "frozen map snapshot is 3d45be5969ec",
          measured_start["snapshot_map"] == PIN_MAP, measured_start["snapshot_map"])
    # The map is live traffic and moves between controller cycles; the study binds to the
    # frozen snapshot 3d45be5969ec and records the live hash as an observation (not a void).
    check("H0d", "live L0 ledger revision still equals the pinned a1674f094979 at run start",
          measured_start["live_ledger"] == LEDGER_PINS["a1674f094979"], measured_start["live_ledger"])
    check("H0e", "three pinned L0 ledger revisions match their published sha256",
          all(measured_start[f"snapshot_theorems_{k}"] == v for k, v in LEDGER_PINS.items()),
          {k: measured_start[f"snapshot_theorems_{k}"][:12] for k in LEDGER_PINS})
    check("H0f", "worker-07 falsification corpus results.json is d69ad58468be",
          measured_start["corpus_w07_results"] == PIN_CORPUS_W07, measured_start["corpus_w07_results"][:12])

    # ------------------------------------------------ load modules + structural check
    canonical = load("w036_canonical", snap_canon)
    candidate = load("w036_candidate", cand_path)
    build = json.loads((HERE / "candidate_build.json").read_text())
    canon_text, cand_text = snap_canon.read_text(), cand_path.read_text()
    reconstructed, inserted, deleted = reverse_apply(canon_text, cand_text)
    check("H1a", "candidate = canonical + exactly one inserted hunk, 0 removed lines",
          deleted == [] and len(inserted) > 0 and reconstructed == canon_text,
          {"inserted_lines": len(inserted), "removed_lines": len(deleted),
           "reverse_apply_equals_canonical": reconstructed == canon_text})
    check("H1b", "candidate_build.json record agrees with the re-derived diff",
          build["diff_removed_lines"] == len(deleted) and build["diff_added_lines"] == len(inserted)
          and build["candidate_sha256"] == measured_start["candidate"],
          {"record": {"added": build["diff_added_lines"], "removed": build["diff_removed_lines"]},
           "rederived": {"added": len(inserted), "removed": len(deleted)}})

    # ------------------------------------------------ H2 fixture battery
    fixtures = [json.loads(l) for l in fixtures_path.read_text().splitlines() if l.strip()]
    fx_results = []
    fx_ok = True
    for fx in fixtures:
        where = f"fixture {fx['id']}"
        fc = scan(canonical, fx["surface"], fx["obj"], where)
        fd = scan(candidate, fx["surface"], fx["obj"], where)
        kinds_c, kinds_d = Counter(kind_of(x) for x in fc), Counter(kind_of(x) for x in fd)
        exp_c, exp_d = fx["expect_canonical"], fx["expect_candidate"]
        ek = fx["expect_candidate_kind"]
        ok = len(fc) == exp_c and len(fd) == exp_d
        if ek == "none":
            ok = ok and "disjunction" not in kinds_d
        elif ek == "disjunction":
            ok = ok and kinds_d.get("disjunction", 0) >= 1
        elif ek in ("unknown", "merge", "prose"):
            ok = ok and kinds_d.get(ek, 0) >= 1 and "disjunction" not in kinds_d
        elif ek == "disjunction_plus_prose":
            ok = ok and kinds_d.get("disjunction", 0) == 1 and kinds_d.get("prose", 0) == 1
        fx_ok = fx_ok and ok
        fx_results.append({
            "id": fx["id"], "surface": fx["surface"], "ok": ok,
            "canonical_n": len(fc), "candidate_n": len(fd),
            "expect_canonical": exp_c, "expect_candidate": exp_d,
            "candidate_kinds": dict(kinds_d), "note": fx["note"],
        })
    check("H2a", "fixture battery: all positive/negative/orthogonality cases match expectations",
          fx_ok, {"cases": len(fixtures), "failing": [r["id"] for r in fx_results if not r["ok"]]})
    n_pos = sum(1 for f in fixtures if f["expect_candidate"] > f["expect_canonical"])
    n_neg = sum(1 for f in fixtures if f["expect_candidate"] == 0 == f["expect_canonical"])
    check("H2b", "battery contains >=5 positives, >=5 negatives, >=3 text-route scope cases",
          n_pos >= 5 and n_neg >= 5 and sum(1 for f in fixtures if f["surface"] == "text") >= 3,
          {"positives": n_pos, "negatives": n_neg, "text_cases": sum(1 for f in fixtures if f["surface"] == "text")})

    # ------------------------------------------------ H3 live map counterfactual
    m = json.loads(snap_map.read_text())
    map_c = canonical.findings_for_map(m)
    map_d = candidate.findings_for_map(m)
    added = [x for x in map_d if x not in map_c]
    removed = [x for x in map_c if x not in map_d]
    added_disj = [x for x in added if "container disjoins" in x]
    direct = containers_in_map_surfaces(m)
    import re as _re
    def _label_of(finding: str):
        mm = _re.search(r" in (.+?): \[", finding)
        return mm.group(1) if mm else finding
    added_labels = sorted(_label_of(x) for x in added_disj)
    direct_labels = sorted(f"{h['where']}" for h in direct)
    check("H3a", "candidate adds findings on the frozen map and removes none",
          len(added) > 0 and len(removed) == 0, {"added": len(added), "removed": len(removed)})
    check("H3b", "every added map finding is the container-disjunction rule (no prose change)",
          len(added_disj) == len(added), {"added_disjunction": len(added_disj), "added_other": len(added) - len(added_disj)})
    check("H3c", "independent re-derivation on the same surfaces matches the added findings label-for-label",
          added_labels == direct_labels,
          {"direct": len(direct_labels), "candidate_added": len(added_labels),
           "only_in_candidate": [x for x in added_labels if x not in direct_labels],
           "only_in_direct": [x for x in direct_labels if x not in added_labels]})
    surface_breakdown = Counter(
        ("node" if lbl.startswith("node ") else "claims" if lbl.startswith("claims[") else "portfolio_events")
        for lbl in added_labels
    )
    class_count_hist = Counter(
        int(_re.search(r"disjoins (\d+) frozen", x).group(1)) for x in added_disj
    )
    two_class_labels = sorted(lbl for lbl, x in zip(added_labels, added_disj)
                              if "disjoins 2 frozen" in x)

    # ------------------------------------------------ H4 pinned ledger counterfactual
    ledger_meas = {}
    for tag, path in snap_ledgers.items():
        rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
        rows_c, rows_d = [], []
        for i, row in enumerate(rows):
            w = f"theorems[{i}]"
            fc = [x for x in canonical.findings(row, w) if "container disjoins" in x]
            fd = [x for x in candidate.findings(row, w) if "container disjoins" in x]
            if fc:
                rows_c.append(i)
            if fd:
                rows_d.append(i)
        ledger_meas[tag] = {"rows": len(rows), "canonical_disj_rows": rows_c, "candidate_disj_rows": rows_d}
    check("H4a", "canonical finds zero container disjunctions on all three pinned ledger revisions",
          all(v["canonical_disj_rows"] == [] for v in ledger_meas.values()),
          {k: v["canonical_disj_rows"] for k, v in ledger_meas.items()})
    check("H4b", "candidate finds exactly the 8 named rows on every pinned ledger revision",
          all(set(v["candidate_disj_rows"]) == EXPECTED_DISJ_ROWS for v in ledger_meas.values()),
          {k: v["candidate_disj_rows"] for k, v in ledger_meas.items()})

    # ------------------------------------------------ H5 corpus regression
    w07_dir = ROOT / "artifacts/worker-07/class_separation_falsification"
    live_canon = load("w036_live_canonical", ROOT / "research_map/class_separation.py")
    reg_c, reg_d = score_corpus(canonical, w07_dir), score_corpus(candidate, w07_dir)
    own = live_canon.regression(corpus_dir=w07_dir)
    check("H5a", "standing worker-07 corpus: canonical remains 17/0/10/0 PASS",
          (reg_c["tp"], reg_c["fn"], reg_c["tn"], reg_c["fp"]) == (17, 0, 10, 0) and own["verdict"] == "PASS",
          {"scorer": {k: reg_c[k] for k in ("tp", "fn", "tn", "fp")}, "module_own": own["verdict"]})
    check("H5b", "candidate does not change any standing-corpus fixture",
          reg_c["per_fixture"] == reg_d["per_fixture"],
          {"changed": [a["id"] for a, b in zip(reg_c["per_fixture"], reg_d["per_fixture"]) if a != b]})
    check("H5c", "probe's independent corpus scorer agrees with the module's own regression()",
          (reg_c["tp"], reg_c["fn"], reg_c["tn"], reg_c["fp"]) == (own["tp"], own["fn"], own["tn"], own["fp"]),
          {"probe": {k: reg_c[k] for k in ("tp", "fn", "tn", "fp")}, "module": {k: own[k] for k in ("tp", "fn", "tn", "fp")}})
    ood_dir = ROOT / "artifacts/worker-027/classsep_token_binding/ood_corpus"
    ood = None
    if (ood_dir / "results.json").exists():
        ood_res = json.loads((ood_dir / "results.json").read_text())
        ood_pin = hashlib.sha256((ood_dir / "results.json").read_bytes()).hexdigest()
        rc, rd = score_corpus(canonical, ood_dir), score_corpus(candidate, ood_dir)
        ood = {"results_sha256": ood_pin,
               "canonical": {k: rc[k] for k in ("tp", "fn", "tn", "fp")},
               "candidate": {k: rd[k] for k in ("tp", "fn", "tn", "fp")},
               "unchanged": rc["per_fixture"] == rd["per_fixture"]}
        check("H5d", "worker-027 OOD arity corpus: candidate classification unchanged",
              ood["unchanged"], ood)

    # ------------------------------------------------ H6 harness power controls (null + overfire)
    inert_text = cand_text.replace("if len(known) >= 2:", "if len(known) >= 99:")
    inert, inert_p = load_text("w036_control_inert_r5", inert_text)
    over_text = cand_text.replace("if len(known) >= 2:", "if len(known) >= 1:")
    over, over_p = load_text("w036_control_overfire_r5", over_text)

    map_c_inert = canonical.findings_for_map(m)
    inert_added_map = len([x for x in inert.findings_for_map(m) if x not in map_c_inert])
    ledger_rows = [json.loads(l) for l in snap_ledgers["a1674f094979"].read_text().splitlines() if l.strip()]
    inert_added_led = sum(
        1 for i, row in enumerate(ledger_rows)
        for x in inert.findings(row, f"theorems[{i}]") if "container disjoins" in x
    )
    inert_neg_hits = sum(
        1 for f in fixtures
        if f["expect_candidate"] == 0
        and len(scan(inert, f["surface"], f["obj"], f["id"])) > len(scan(canonical, f["surface"], f["obj"], f["id"]))
    )
    over_neg_hits = sum(
        1 for f in fixtures
        if f["expect_candidate"] == 0
        and len(scan(over, f["surface"], f["obj"], f["id"])) > len(scan(canonical, f["surface"], f["obj"], f["id"]))
    )
    check("H6a", "NULL control: an inert R5 (threshold 99) adds no finding anywhere",
          inert_added_map == 0 and inert_added_led == 0 and inert_neg_hits == 0,
          {"map_added": inert_added_map, "ledger_added": inert_added_led, "negative_fixtures_newly_flagged": inert_neg_hits})
    check("H6b", "OVERFIRE control: threshold 1 would break negative fixtures (battery has power)",
          over_neg_hits >= 5, {"negative_fixtures_newly_flagged": over_neg_hits})

    # ------------------------------------------------ H7 scope limitation, measured
    t_cases = [r for r in fx_results if r["surface"] == "text"]
    text_blind = all(r["canonical_n"] == 0 and r["candidate_n"] == 0 for r in t_cases)
    check("H7", "artifact-text route remains blind to container disjunction (documented limitation)",
          text_blind, {"text_cases": len(t_cases), "all_blind": text_blind})

    # ------------------------------------------------ H8 drift window (end)
    # Void window = the bytes this study measures (artifact-dir snapshots + candidate +
    # fixtures + probe).  Live canonical files are recorded as observations: they may move
    # under swarm traffic, and a move only means the staged patch needs a rebase, not that
    # the pinned-snapshot result is void.
    measured_end = {
        "snapshot_canonical": sha256_file(snap_canon),
        "snapshot_map": sha256_file(snap_map),
        "snapshot_theorems_a1674f094979": sha256_file(snap_ledgers["a1674f094979"]),
        "snapshot_theorems_3e3d35531421": sha256_file(snap_ledgers["3e3d35531421"]),
        "snapshot_theorems_ce42d205e761": sha256_file(snap_ledgers["ce42d205e761"]),
        "candidate": sha256_file(cand_path),
        "fixtures": sha256_file(fixtures_path),
        "probe": sha256_file(probe_path),
        "build_candidate": sha256_file(HERE / "build_candidate.py"),
    }
    drift = {k: (measured_start[k], measured_end[k]) for k in measured_end if measured_start[k] != measured_end[k]}
    check("H8", "all measured inputs (snapshots, candidate, fixtures, probe) were byte-stable during the run",
          not drift, {"drift": drift, "checked": list(measured_end)})
    live_end = {
        "live_canonical": sha256_file(ROOT / "research_map/class_separation.py"),
        "live_map": sha256_file(ROOT / "research_map/research_map.json"),
        "live_ledger": sha256_file(ROOT / "ledger/theorems.jsonl"),
    }
    live_drift = {k: {"start": measured_start[k], "end": live_end[k]}
                  for k in live_end if measured_start[k] != live_end[k]}

    overall = "PASS" if all(c["ok"] for c in checks) else "FAIL"
    report = {
        "task_id": "W036-CLASSSEP-DISJ-RULE-01",
        "worker": "worker-036",
        "node_id": "A1",
        "gate": "G-AUDIT/G-CLASSBIND",
        "class_ids": sorted(FROZEN_CLASSES),
        "created_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "authority": "Worker measurement evidence only. No gate verdict, no node status, no canonical file modified.",
        "question": "Does a mechanically generated container-disjunction rule (R5) close the class_ids blind spot found in W036-CLASSSEP-DISJ-01/02/03 without changing any other surface?",
        "candidate_sha256": measured_start["candidate"],
        "canonical_sha256": PIN_CANONICAL,
        "snapshot_map_sha256": measured_start["snapshot_map"],
        "snapshot_theorems_a1674f094979": measured_start["snapshot_theorems_a1674f094979"],
        "snapshot_theorems_3e3d35531421": measured_start["snapshot_theorems_3e3d35531421"],
        "snapshot_theorems_ce42d205e761": measured_start["snapshot_theorems_ce42d205e761"],
        "fixtures_sha256": measured_start["fixtures"],
        "probe_sha256": measured_start["probe"],
        "build_candidate_sha256": measured_start["build_candidate"],
        "checks": checks,
        "fixture_results": fx_results,
        "map_counterfactual": {
            "map_sha256": measured_start["snapshot_map"],
            "canonical_total": len(map_c),
            "candidate_total": len(map_d),
            "added": added,
            "removed": removed,
            "added_by_surface": dict(surface_breakdown),
            "added_by_distinct_class_count": dict(sorted(class_count_hist.items())),
            "two_class_container_labels": two_class_labels,
            "direct_containers": direct,
        },
        "live_drift_observations": {
            "note": "Live canonical files move under swarm traffic; the result binds to the snapshots above. A live move of class_separation.py means the staged candidate needs rebasing before any owner-side application.",
            "drift": live_drift,
            "live_map_sha256_start": measured_start["live_map"],
            "live_map_sha256_end": live_end["live_map"],
        },
        "ledger_counterfactual": ledger_meas,
        "corpus_regression": {
            "worker_07": {k: reg_c[k] for k in ("tp", "fn", "tn", "fp", "corpus_size")},
            "worker_07_candidate": {k: reg_d[k] for k in ("tp", "fn", "tn", "fp", "corpus_size")},
            "worker_027_ood": ood,
        },
        "control_module_hashes": {"inert_r5": sha256_file(inert_p), "overfire_r5": sha256_file(over_p)},
        "limitations": [
            "findings_for_text (artifact-body route) has no class_ids-container parser; R5 is scoped to structured findings()/findings_for_map() surfaces and the text route stays blind (H7 measured).",
            "PRECISION IS NOT FREE ON THE MAP-CLAIM SURFACE: R5-as-staged flags every class_ids container with >=2 frozen classes. On the frozen map that is 100 containers (94 claim containers, 6 node containers), dominated by 3-class (32) and 4-class (58) scope-metadata shapes; only 10 are 2-class. The HF-02 target population (singular bindings) is the 8 ledger rows plus those 10 map containers. The owner must set the surface/cardinality policy; this packet measures both the rule and its live blast radius rather than assuming it.",
            "A container finding is a detector signal, not an adjudication: whether each flagged live claim/row is a genuine HF-02 violation remains with the audit owner (worker-023 argues the 8 L0 rows should carry relation bindings instead of two class_ids).",
            "The candidate is staged under artifacts/worker-036/; canonical research_map/class_separation.py is untouched (owner applies checker changes, CF-4).",
        ],
        "falsifiers": [
            "F1: any positive fixture not flagged by the candidate, or any negative fixture newly flagged -> rule wrong or too broad.",
            "F2: any added frozen-map finding not carrying 'container disjoins' -> candidate changed a surface other than containers.",
            "F3: any of the 8 named ledger rows not flagged on any pinned revision, or canonical flags a container there -> rule incomplete or redundant.",
            "F4: worker-07 (or worker-027 OOD) per-fixture classification changes under the candidate -> regression.",
            "F5: reverse-applying the R5 hunk does not reproduce the pinned canonical bytes -> candidate carries hidden edits.",
            "F6: the inert-R5 control adds any finding, or the overfire-R5 control does not break negatives -> harness has no power.",
            "F7: any pinned input hash drifts mid-run -> window void, restore from snapshots and re-run.",
        ],
        "overall": overall,
    }
    (HERE / "report.json").write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({c["id"]: ("PASS" if c["ok"] else "FAIL") for c in checks}, indent=1))
    print("overall:", overall)
    print("map: canonical", len(map_c), "candidate", len(map_d), "added", len(added), "removed", len(removed))
    print("ledger disj rows:", {k: v["candidate_disj_rows"] for k, v in ledger_meas.items()})
    print("w07 regression canonical/candidate:",
          {k: reg_c[k] for k in ("tp", "fn", "tn", "fp")}, {k: reg_d[k] for k in ("tp", "fn", "tn", "fp")})
    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
