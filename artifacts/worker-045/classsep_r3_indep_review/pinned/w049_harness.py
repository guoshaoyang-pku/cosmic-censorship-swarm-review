#!/usr/bin/env python3
"""W049-CLASSSEP-FN-AUDIT-01 runner (worker-049, node A1, gate G-AUDIT).

Adversarial false-negative audit of class-separation detectors on two
pre-registered labeled corpora:

  corpus v1 (corpus.json, 9eb2ea9e2743) - written before any detector was run on
    it; every ADVERSARIAL_ASSERTION fixture has a cue-stripped TWIN so a clear is
    attributable to the mention-style cue. Primary subject: the staged prosefix
    artifact artifacts/worker-049/classsep_prose_fix/class_separation_prosefix.py
    (dc8aa0de3869).
  corpus v2 (corpus_guard_probe.json, db6dff9f4eda) - written after the live
    canonical detector changed mid-session (c266dbceca87 -> a8c04fc31e4a, mtime
    00:52) and targets the 3-line context-skip the change adds. Primary subject:
    the live canonical at a8c04fc31e4a.

Three detectors are measured on both corpora:
  recovered_c266 - the pre-change canonical bytes, reconstructed by removing the
    3 added lines from the live file; the reconstruction is hash-verified to
    equal c266dbceca87 (worker-098's drift_recheck.json independently records
    added_lines=3, removed_lines=0 between the two revisions).
  live_canonical - research_map/class_separation.py as measured at run start.
  staged_prosefix - worker-049's staged artifact, unchanged.

Fail-closed on every pinned input (corpus, all three detectors, worker-07 corpus
results, worker-035 control battery). Read-only on all pinned inputs; writes
only results.json next to this script. Payload contains no wall-clock field, so
a double run must be byte-identical (checked). Exit codes: 0 ok, 2 pin mismatch,
3 internal inconsistency.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
RESULTS_PATH = HERE / "results.json"

PRIMARY_CLASS_ID = "AF-SCC-C2-VAC-GEN"

PINS = {
    "corpus_v1": (HERE / "corpus.json",
                  "9eb2ea9e27439703ffe7c91168348e6539e5a1fbd268f36383d09d0d3aeeea23"),
    "corpus_v2": (HERE / "corpus_guard_probe.json",
                  "db6dff9f4edaf585a78c2a5e084665c037db61bc354a86c5cba74f5f71c6ed8b"),
    "corpus_twin_fix": (HERE / "corpus_guard_twin_fix.json",
                        "c3bbb5be3979eeb4dec2a85e352b8faa77d50a3aa15d9afa95a2a6b7159c5e43"),
    "recovered_c266": (HERE / "pinned/class_separation_c266_recovered.py",
                       "c266dbceca87fb996bd76a774145ef511cbf2aae190d9f423167d3200783a920"),
    "live_canonical": (REPO / "research_map/class_separation.py",
                       "a8c04fc31e4afa1b691cd6bfb6bf8b4f953a0adc925939a8351bab9cf453c5bd"),
    "staged_prosefix": (REPO / "artifacts/worker-049/classsep_prose_fix/class_separation_prosefix.py",
                        "dc8aa0de386931cd0de48e9e755bc9b0bf33a12ce1c464f9911f4e9469f12470"),
    "worker07_corpus_results": (REPO / "artifacts/worker-07/class_separation_falsification/results.json",
                                "d69ad58468be16655921dcf0eab9570fa6e7ccaf828558a45d4b306cce3de452"),
    "worker035_control_battery": (REPO / "artifacts/worker-049/classsep_prose_fix/worker035_controls.json",
                                  "ef881c3aa6ef392c2068828b02d6645043913a0ff88ab0487264a6b770c5914d"),
}

MODULE_ROLES = {
    "recovered_c266": "pre-change canonical (recovered, hash-verified)",
    "live_canonical": "live canonical at run start (carries the 3-line guard)",
    "staged_prosefix": "staged under artifacts/worker-049/ (CF-16 prosefix artifact)",
}
CORPUS_PRIMARY = {"corpus_v1": "staged_prosefix", "corpus_v2": "live_canonical"}


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def verify_pins() -> dict:
    out, bad = {}, []
    for name, (path, want) in PINS.items():
        if not path.is_file():
            bad.append(f"{name}: missing at {path}")
            continue
        got = sha256_file(path)
        out[name] = {"path": str(path.relative_to(REPO)), "sha256": got,
                     "expected": want, "match": got == want}
        if got != want:
            bad.append(f"{name}: {got} != {want}")
    if bad:
        print("PIN MISMATCH (fail closed):")
        for b in bad:
            print("  -", b)
        sys.exit(2)
    return out


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def measure_fixtures(mod, corpus: dict) -> list:
    rows = []
    for fx in corpus["fixtures"]:
        obj = {"statement": fx["text"], "class_id": PRIMARY_CLASS_ID}
        where = f"fx:{fx['id']}"
        prose = mod.findings(obj, where, mode="prose")
        surface_b = mod.findings_for_text(fx["text"], f"text:{fx['id']}")
        declaration = mod.findings(obj, where, mode="declaration")
        rows.append({
            "id": fx["id"],
            "category": fx["category"],
            "adversarial_cue": fx["adversarial_cue"],
            "expected_findings": fx["expected_findings"],
            "confidence": fx["confidence"],
            "twin_of": fx["twin_of"],
            "flags": len(prose) > 0,
            "n_findings": len(prose),
            "findings": prose,
            "surface_b_flags": len(surface_b) > 0,
            "declaration_n_findings": len(declaration),
        })
    return rows


def corpus_aggregates(rows: list, baseline_rows: list | None) -> dict:
    by_id = {r["id"]: r for r in rows}
    base = {r["id"]: r for r in (baseline_rows or [])}
    adv = [r for r in rows if r["category"] == "ADVERSARIAL_ASSERTION"]
    twins = [r for r in rows if r["category"] == "TWIN_CONTROL"]
    plain = [r for r in rows if r["category"] == "PLAIN_POSITIVE"]
    mentions = [r for r in rows if r["category"] == "MENTION"]

    cue_induced = []
    twin_missing = []
    twin_by_adv = {t["twin_of"]: t["id"] for t in twins if t.get("twin_of")}
    for r in adv:
        tw = by_id.get(twin_by_adv.get(r["id"])) if twin_by_adv.get(r["id"]) else None
        if tw is None:
            twin_missing.append(r["id"])
            continue
        if (not r["flags"]) and tw["flags"]:
            cue_induced.append({"adversarial": r["id"], "twin": tw["id"],
                                "confidence": r["confidence"], "cue": r["adversarial_cue"]})
    agg = {
        "fixtures_total": len(rows),
        "adversarial_total": len(adv),
        "adversarial_cleared": [r["id"] for r in adv if not r["flags"]],
        "twin_controls_flagged": f"{sum(1 for r in twins if r['flags'])}/{len(twins)}",
        "twins_not_flagged": [r["id"] for r in twins if not r["flags"]],
        "adversarial_without_twin": twin_missing,
        "cue_induced_fn_total": len(cue_induced),
        "cue_induced_fn_high_confidence": sum(1 for c in cue_induced if c["confidence"] == "HIGH"),
        "cue_induced_fn_medium_confidence": sum(1 for c in cue_induced if c["confidence"] != "HIGH"),
        "cue_induced_fn_detail": cue_induced,
        "plain_positive_fn": [r["id"] for r in plain if not r["flags"]],
        "mention_fp": [r["id"] for r in mentions if r["flags"]],
        "surface_a_b_disagreements": [r["id"] for r in rows if r["flags"] != r["surface_b_flags"]],
    }
    if baseline_rows is not None:
        agg["mention_fp_delta_vs_c266"] = sorted(
            set(agg["mention_fp"]) ^ set(r["id"] for r in mentions if base[r["id"]]["flags"]))
        agg["declaration_diff_vs_c266"] = [r["id"] for r in rows
                                           if r["declaration_n_findings"] != base[r["id"]]["declaration_n_findings"]]
    return agg


def re_score_worker07(mod, corpus_results_path: Path, repo: Path) -> dict:
    res = json.loads(corpus_results_path.read_text())
    tp = fn = tn = fp = 0
    rows = []
    for fx in res["fixtures"]:
        fpth = repo / fx["fixture_path"]
        if not fpth.is_file():
            continue
        m = json.loads(fpth.read_text())
        det = mod.findings_for_map(m)
        for g in m.get("groups", []):
            for n in g.get("nodes", []):
                art = n.get("artifact")
                if art and (repo / art).is_file():
                    det += mod.findings_for_text((repo / art).read_text(errors="replace"),
                                                 f"artifact {art}")
        got, truth = bool(det), bool(fx["is_class_merge"])
        if truth and got:
            tp += 1
        elif truth and not got:
            fn += 1
        elif not truth and got:
            fp += 1
        else:
            tn += 1
        if got != fx["detected"]:
            rows.append({"id": fx["id"], "recorded_detected": fx["detected"], "remeasured": got})
    return {"tp": tp, "fn": fn, "tn": tn, "fp": fp, "corpus_size": tp + fn + tn + fp,
            "verdict": "PASS" if fn == 0 and fp == 0 else "DEFECTIVE",
            "disagreements_with_recorded_detected": rows}


def re_score_worker035(mod, battery_path: Path) -> dict:
    battery = json.loads(battery_path.read_text())
    rows = []
    passed = 0
    for c in battery["controls"]:
        expect_assertion = c["expect"].startswith("ASSERTION")
        f = mod.findings({"statement": c["text"], "class_id": PRIMARY_CLASS_ID},
                         f"control:{c['control_id']}", mode="prose")
        got = len(f) > 0
        ok = got == expect_assertion
        passed += int(ok)
        rows.append({"control_id": c["control_id"], "expect_assertion": expect_assertion,
                     "measured_assertion": got, "pass": ok})
    return {"passed": passed, "total": len(rows), "rows": rows,
            "verdict": "PASS" if passed == len(rows) else "DEFECTIVE"}


def run_once(mods: dict, corpora: dict, paths: dict, addendum: dict) -> dict:
    measured = {}
    for cname, corpus in corpora.items():
        measured[cname] = {mname: measure_fixtures(mod, corpus) for mname, mod in mods.items()}
    addendum_rows = {mname: measure_fixtures(mod, addendum) for mname, mod in mods.items()}

    corpora_block = {}
    for cname, corpus in corpora.items():
        per_mod = measured[cname]
        baseline = per_mod["recovered_c266"]
        block = {}
        for mname in mods:
            block[mname] = {
                "role": MODULE_ROLES[mname],
                "rows": per_mod[mname],
                "aggregates": corpus_aggregates(per_mod[mname],
                                                None if mname == "recovered_c266" else baseline),
            }
        primary = CORPUS_PRIMARY[cname]
        p_agg = block[primary]["aggregates"]
        primary_result = {
            "cue_induced_fn_total": p_agg["cue_induced_fn_total"],
            "cue_induced_fn_high_confidence": p_agg["cue_induced_fn_high_confidence"],
            "cue_induced_fn_medium_confidence": p_agg["cue_induced_fn_medium_confidence"],
            "adversarial_cleared": p_agg["adversarial_cleared"],
            "adversarial_total": p_agg["adversarial_total"],
            "mention_fp": p_agg["mention_fp"],
        }
        corpora_block[cname] = {
            "path": PINS[cname][0].relative_to(REPO).as_posix(),
            "sha256": PINS[cname][1],
            "fixtures_total": len(corpus["fixtures"]),
            "primary_module": primary,
            "primary_result": primary_result,
            "modules": block,
        }

    controls = {
        "worker07_regression": {m: re_score_worker07(mod, paths["worker07_corpus_results"], REPO)
                                for m, mod in mods.items()},
        "worker035_battery": {m: re_score_worker035(mod, paths["worker035_control_battery"])
                              for m, mod in mods.items()},
        "repaired_twin_probe_G05T2": {
            m: {"text": addendum["fixtures"][0]["text"],
                "expected_findings": addendum["fixtures"][0]["expected_findings"],
                "flags": rows[0]["flags"], "n_findings": rows[0]["n_findings"]}
            for m, rows in addendum_rows.items()},
        "repaired_twin_note": (
            "G05T2 was authored after the frozen guard-probe corpus was executed "
            "(its G05T twin omitted the composite token); it is reported separately "
            "and is not part of the primary pre-registered endpoint."),
    }

    v1 = corpora_block["corpus_v1"]["primary_result"]
    v2 = corpora_block["corpus_v2"]["primary_result"]
    verdicts = {
        "corpus_v1_staged_prosefix": (
            "UNSAFE_AS_IS: cue-induced false negatives on the pre-registered corpus"
            if v1["cue_induced_fn_total"] else "NO_CUE_INDUCED_FN_ON_THIS_CORPUS"),
        "corpus_v2_live_guard": (
            "LIVE_GUARD_INTRODUCES_FN: cue-induced false negatives on the pre-registered guard corpus"
            if v2["cue_induced_fn_total"] else "NO_CUE_INDUCED_FN_ON_THIS_CORPUS"),
    }
    w07_live = controls["worker07_regression"]["live_canonical"]
    provenance = {
        "live_canonical_change": {
            "before": "c266dbceca87fb996bd76a774145ef511cbf2aae190d9f423167d3200783a920",
            "after": "a8c04fc31e4afa1b691cd6bfb6bf8b4f953a0adc925939a8351bab9cf453c5bd",
            "delta": "+3 lines, context-level skip in _scan_composite (both modes)",
            "recovery_check": "removing the 3 lines from the live file reproduces c266dbce exactly",
            "independent_corroboration": "artifacts/worker-098/classsep_prose_shadow/raw/drift_recheck.json (added_lines=3, removed_lines=0)",
            "live_worker07_regression_after_change": f"{w07_live['tp']}/{w07_live['fn']}/{w07_live['tn']}/{w07_live['fp']} {w07_live['verdict']}",
        },
        "map_sha256_at_run": sha256_file(REPO / "research_map/research_map.json"),
    }
    return {
        "schema": "worker-049/classsep-fn-audit-results/v2",
        "task_id": "W049-CLASSSEP-FN-AUDIT-01",
        "actor": "worker-049",
        "node_id": "A1",
        "gate": "G-AUDIT",
        "class_id": "AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "modules": {m: {"path": PINS[m][0].relative_to(REPO).as_posix(),
                        "sha256": PINS[m][1], "role": MODULE_ROLES[m]} for m in mods},
        "corpora": corpora_block,
        "controls": controls,
        "provenance": provenance,
        "verdicts": verdicts,
        "author_conflict_note": (
            "worker-049 authored the staged prosefix under audit; that audit returned "
            "adverse. worker-049 did not author and has no authority over the live "
            "canonical; the live-guard result is an independent measurement, but "
            "adoption or reversion is a controller/audit-lead decision."),
        "non_claims": [
            "no gate verdict, no node status, no validation_status=passed",
            "no mathematical, physical or class-separation verdict",
            "no natural-text FN/FP rate: both corpora are deliberately adversarial",
            "no edit to any canonical or pinned file; worker-049's published result.json untouched",
            "no claim about who changed the live canonical or with what authority",
        ],
    }


def main() -> int:
    pins = verify_pins()
    paths = {k: v[0] for k, v in PINS.items()}
    corpora = {c: json.loads(paths[c].read_text()) for c in ("corpus_v1", "corpus_v2")}
    addendum = json.loads(paths["corpus_twin_fix"].read_text())
    mods = {
        "recovered_c266": load_module("cs_c266", paths["recovered_c266"]),
        "live_canonical": load_module("cs_live", paths["live_canonical"]),
        "staged_prosefix": load_module("cs_staged", paths["staged_prosefix"]),
    }

    first = run_once(mods, corpora, paths, addendum)
    second = run_once(mods, corpora, paths, addendum)
    deterministic = json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    first["pins"] = pins
    first["controls"]["double_run_byte_deterministic"] = deterministic
    if not deterministic:
        print("INTERNAL INCONSISTENCY: double run differs", file=sys.stderr)
        return 3

    RESULTS_PATH.write_text(json.dumps(first, indent=1, sort_keys=False) + "\n")
    print(f"wrote {RESULTS_PATH.relative_to(REPO)} sha256={sha256_file(RESULTS_PATH)}")
    for v in ("corpus_v1", "corpus_v2"):
        pr = first["corpora"][v]["primary_result"]
        print(f"{v} primary={first['corpora'][v]['primary_module']} "
              f"cue_FN={pr['cue_induced_fn_total']} "
              f"(H={pr['cue_induced_fn_high_confidence']},M={pr['cue_induced_fn_medium_confidence']}) "
              f"cleared={len(pr['adversarial_cleared'])}/{pr['adversarial_total']} "
              f"mentionFP={pr['mention_fp']}")
    for m, r in first["controls"]["worker07_regression"].items():
        print(f"worker07 {m}: {r['tp']}/{r['fn']}/{r['tn']}/{r['fp']} {r['verdict']}")
    for m, r in first["controls"]["worker035_battery"].items():
        print(f"worker035 {m}: {r['passed']}/{r['total']} {r['verdict']}")
    print("verdicts:", json.dumps(first["verdicts"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
