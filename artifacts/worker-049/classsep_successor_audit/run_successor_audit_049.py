#!/usr/bin/env python3
"""W049-CLASSSEP-SUCCESSOR-AUDIT-02 runner (worker-049, node A1, gate G-AUDIT).

Independent out-of-sample over-suppression (false-negative) acceptance audit of
every class-separation detector candidate currently staged to succeed the live
3-line guard a8c04fc31e4a.

Measured per candidate:
  * corpus v1 (corpus.json 9eb2ea9e2743)   - frozen 00:51, pre-registered
  * corpus v2 (corpus_guard_probe.json db6dff9f4eda) - frozen 00:53, pre-registered
  * corpus v3 (corpus_v3.json 6764c04978c9) - authored 01:00, before any detector
    read it; targets successor-specific suppression cues
  * worker-07 falsification corpus (17/0/10/0 PASS gate)
  * worker-098 declared FIRE/CLEAN/GROWTH controls, re-scored independently
  * worker-035 advisory battery
  * live-map hard findings at a pinned map snapshot (diagnostic)

Primary endpoint: cue-induced false negatives = ADVERSARIAL_ASSERTION fixtures
that clear while their cue-stripped TWIN flags on the same detector. Acceptance
requires 0 on all three corpora.

Read-only on all inputs. Fail-closed (exit 2) on any pin mismatch before
measurement. Drift during the run does not abort: results are written with
candidate_set_drift/input_drift flags and verdicts marked VOID. Double in-memory
run must be byte-identical (exit 3 otherwise). Exit 0 ok.
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
    "corpus_v1": (REPO / "artifacts/worker-049/classsep_fn_audit/corpus.json",
                  "9eb2ea9e27439703ffe7c91168348e6539e5a1fbd268f36383d09d0d3aeeea23"),
    "corpus_v2": (REPO / "artifacts/worker-049/classsep_fn_audit/corpus_guard_probe.json",
                  "db6dff9f4edaf585a78c2a5e084665c037db61bc354a86c5cba74f5f71c6ed8b"),
    "corpus_v3": (HERE / "corpus_v3.json",
                  "6764c04978c994c377dfc1e31558029cacb1203c15f83258f16798ecd73b219f"),
    "worker07_corpus_results": (REPO / "artifacts/worker-07/class_separation_falsification/results.json",
                                "d69ad58468be16655921dcf0eab9570fa6e7ccaf828558a45d4b306cce3de452"),
    "worker035_control_battery": (REPO / "artifacts/worker-049/classsep_prose_fix/worker035_controls.json",
                                  "ef881c3aa6ef392c2068828b02d6645043913a0ff88ab0487264a6b770c5914d"),
    "w098_controls_source": (REPO / "artifacts/worker-098/classsep_mention_scope/run_battery_final.py",
                             "bc8f58bb6cbddbf3ba30be40443b29d3865f296e54a3ba84391f653c2617f6b3"),
}

CORPUS_ORDER = ("corpus_v1", "corpus_v2", "corpus_v3")


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def verify_pins() -> dict:
    out, bad = {}, []
    for name, (path, want) in PINS.items():
        if not path.is_file():
            bad.append(f"{name}: missing at {path}")
            continue
        got = sha256_file(path)
        out[name] = {"path": path.relative_to(REPO).as_posix(), "sha256": got,
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
        declaration = mod.findings(obj, where, mode="declaration")
        rows.append({
            "id": fx["id"],
            "category": fx["category"],
            "adversarial_cue": fx.get("adversarial_cue"),
            "expected_findings": fx["expected_findings"],
            "confidence": fx.get("confidence"),
            "twin_of": fx.get("twin_of"),
            "flags": len(prose) > 0,
            "n_findings": len(prose),
            "findings": prose,
            "declaration_n_findings": len(declaration),
        })
    return rows


def corpus_aggregates(rows: list, baseline_by_id: dict) -> dict:
    by_id = {r["id"]: r for r in rows}
    adv = [r for r in rows if r["category"] == "ADVERSARIAL_ASSERTION"]
    twins = [r for r in rows if r["category"] == "TWIN_CONTROL"]
    plain = [r for r in rows if r["category"] == "PLAIN_POSITIVE"]
    mentions = [r for r in rows if r["category"] == "MENTION"]
    twin_by_adv = {t["twin_of"]: t["id"] for t in twins if t.get("twin_of")}

    cue_induced, twin_missing, non_cue = [], [], []
    for r in adv:
        tw = by_id.get(twin_by_adv.get(r["id"])) if twin_by_adv.get(r["id"]) else None
        if tw is None:
            twin_missing.append(r["id"])
            continue
        if (not r["flags"]) and tw["flags"]:
            cue_induced.append({"adversarial": r["id"], "twin": tw["id"],
                                "confidence": r["confidence"], "cue": r["adversarial_cue"]})
        elif not r["flags"]:
            # cleared although the cue-stripped twin also clears: the clear is NOT
            # attributable to the cue (worse than a cue-induced FN)
            non_cue.append({"adversarial": r["id"], "twin": tw["id"],
                            "confidence": r["confidence"], "cue": r["adversarial_cue"]})
    cleared = [r["id"] for r in adv if not r["flags"]]
    agg = {
        "fixtures_total": len(rows),
        "adversarial_total": len(adv),
        "adversarial_cleared": cleared,
        "twin_controls_flagged": f"{sum(1 for r in twins if r['flags'])}/{len(twins)}",
        "twins_not_flagged": [r["id"] for r in twins if not r["flags"]],
        "adversarial_without_twin": twin_missing,
        "cue_induced_fn_total": len(cue_induced),
        "cue_induced_fn_high_confidence": sum(1 for c in cue_induced if c["confidence"] == "HIGH"),
        "cue_induced_fn_non_high_confidence": sum(1 for c in cue_induced if c["confidence"] != "HIGH"),
        "cue_induced_fn_detail": cue_induced,
        "non_cue_fn_total": len(non_cue),
        "non_cue_fn_detail": non_cue,
        "adversarial_cleared_total": len(cleared),
        "plain_positive_fn": [r["id"] for r in plain if not r["flags"]],
        "mention_fp": [r["id"] for r in mentions if r["flags"]],
    }
    if baseline_by_id is not None:
        agg["declaration_diff_vs_c266"] = [
            r["id"] for r in rows
            if r["declaration_n_findings"] != baseline_by_id[r["id"]]["declaration_n_findings"]]
    return agg


def re_score_worker07(mod, corpus_results_path: Path) -> dict:
    res = json.loads(corpus_results_path.read_text())
    tp = fn = tn = fp = 0
    rows = []
    for fx in res["fixtures"]:
        fpth = REPO / fx["fixture_path"]
        if not fpth.is_file():
            continue
        m = json.loads(fpth.read_text())
        det = mod.findings_for_map(m)
        for g in m.get("groups", []):
            for n in g.get("nodes", []):
                art = n.get("artifact")
                if art and (REPO / art).is_file():
                    det += mod.findings_for_text((REPO / art).read_text(errors="replace"),
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
    rows, passed = [], 0
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


def re_score_w098(mod, controls: dict, source_text: str) -> dict:
    def fired(text: str) -> bool:
        return len(mod.findings({"statement": text, "class_id": PRIMARY_CLASS_ID},
                                "w098control", mode="prose")) > 0

    def nfind(text: str) -> int:
        return len(mod.findings({"statement": text, "class_id": PRIMARY_CLASS_ID},
                                "w098growth", mode="prose"))
    fire = [{"name": c["name"], "text": c["text"], "fires": fired(c["text"]),
             "in_source": c["text"] in source_text} for c in controls["fire"]]
    clean = [{"name": c["name"], "text": c["text"], "fires": fired(c["text"]),
              "in_source": c["text"] in source_text} for c in controls["clean"]]
    growth = [{"name": c["name"], "text": c["text"], "findings": nfind(c["text"]),
               "in_source": c["text"] in source_text} for c in controls["growth"]]
    tp = [{"name": c["name"], "text": c["text"], "fires": fired(c["text"]),
           "in_source": c["text"] in source_text} for c in controls["tp"]]
    return {
        "fire": fire, "clean": clean, "growth": growth, "tp": tp,
        "fire_all": all(r["fires"] for r in fire),
        "clean_all_silent": all(not r["fires"] for r in clean),
        "growth_all_zero": all(r["findings"] == 0 for r in growth),
        "tp_all_fire": all(r["fires"] for r in tp),
        "all_texts_verified_in_source": all(r["in_source"] for r in fire + clean + growth + tp),
        "fire_failures": [r["name"] for r in fire if not r["fires"]],
        "clean_failures": [r["name"] for r in clean if r["fires"]],
        "growth_failures": [r["name"] for r in growth if r["findings"] != 0],
    }


def leak_check(corpus: dict) -> dict:
    """Bounded contamination scan: does any adversarial fixture string occur in
    any other candidate/battery/corpus-bearing file on the shared tree? Scans the
    recorded roots only (bounded, directory-excluded); this task's own directory
    is excluded because it holds corpus_v3.json itself."""
    scan_roots = [REPO / "proposed", REPO / "research_map",
                  REPO / "artifacts/worker-098", REPO / "artifacts/worker-016",
                  REPO / "artifacts/worker-049/classsep_fn_audit",
                  REPO / "artifacts/worker-049/classsep_prose_fix",
                  REPO / "artifacts/worker-07"]
    shards = [f["text"][:40] for f in corpus["fixtures"]
              if f["category"] == "ADVERSARIAL_ASSERTION"]
    scanned, hits = 0, []
    for root in scan_roots:
        if not root.exists():
            continue
        for p in root.rglob("*"):
            if not p.is_file() or "__pycache__" in p.parts:
                continue
            if p.stat().st_size > 3_000_000:
                continue
            try:
                txt = p.read_text(errors="replace")
            except OSError:
                continue
            scanned += 1
            for sh in shards:
                if sh in txt:
                    hits.append({"shard": sh, "file": p.relative_to(REPO).as_posix()})
    return {"scanned_files": scanned, "hits": hits, "clean": not hits,
            "scope": [r.relative_to(REPO).as_posix() for r in scan_roots],
            "rule": "any occurrence of a 40-char adversarial fixture shard outside this "
                    "task's own directory falsifies out-of-sample authorship"}


def run_once(mods: dict, corpora: dict, controls: dict, source_text: str,
             map_snapshot: dict, paths: dict) -> dict:
    measured = {cname: {mid: measure_fixtures(mod, corpus) for mid, mod in mods.items()}
                for cname, corpus in corpora.items()}
    corpora_block = {}
    for cname, corpus in corpora.items():
        per_mod = measured[cname]
        base = {r["id"]: r for r in per_mod["recovered_c266"]}
        block = {}
        for mid in mods:
            block[mid] = {
                "rows": per_mod[mid],
                "aggregates": corpus_aggregates(per_mod[mid], None if mid == "recovered_c266" else base),
            }
        corpora_block[cname] = {
            "path": PINS[cname][0].relative_to(REPO).as_posix(),
            "sha256": PINS[cname][1],
            "fixtures_total": len(corpus["fixtures"]),
            "modules": block,
        }

    w07 = {mid: re_score_worker07(mod, paths["worker07_corpus_results"]) for mid, mod in mods.items()}
    w35 = {mid: re_score_worker035(mod, paths["worker035_control_battery"]) for mid, mod in mods.items()}
    w98 = {mid: re_score_w098(mod, controls, source_text) for mid, mod in mods.items()}
    live_map = {mid: {"hard_findings": len(mod.findings_for_map(map_snapshot))} for mid, mod in mods.items()}

    return {
        "schema": "worker-049/classsep-successor-audit-results/v1",
        "task_id": "W049-CLASSSEP-SUCCESSOR-AUDIT-02",
        "actor": "worker-049",
        "node_id": "A1",
        "gate": "G-AUDIT",
        "class_id": "AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "corpora": corpora_block,
        "controls": {
            "worker07_regression": w07,
            "worker035_battery_advisory": w35,
            "w098_declared_controls": w98,
            "live_map_snapshot": live_map,
        },
        "non_claims": [
            "no gate verdict, no node status, no validation_status",
            "no adopt/reject recommendation; numbers only",
            "no natural-text FN/FP rate: corpora are adversarial by construction",
            "no edit to any canonical, staged or pinned input",
        ],
    }


def main() -> int:
    pins = verify_pins()
    paths = {k: v[0] for k, v in PINS.items()}

    pin_manifest_path = HERE / "candidates_pinned.json"
    pin_manifest = json.loads(pin_manifest_path.read_text())
    panel = pin_manifest["panel"]

    bad = []
    for c in panel:
        p = REPO / c["path"]
        if not p.is_file():
            bad.append(f"{c['id']}: missing at {p}")
        elif sha256_file(p) != c["sha256"]:
            bad.append(f"{c['id']}: hash moved since pin")
    if bad:
        print("CANDIDATE PIN MISMATCH (fail closed):")
        for b in bad:
            print("  -", b)
        return 2

    corpora = {c: json.loads(paths[c].read_text()) for c in CORPUS_ORDER}
    controls = json.loads((HERE / "w098_controls.json").read_text())
    source_text = paths["w098_controls_source"].read_text(errors="replace")
    map_snapshot = json.loads((REPO / "research_map/research_map.json").read_text())
    map_sha = sha256_file(REPO / "research_map/research_map.json")

    mods = {c["id"]: load_module(f"cs_{c['id']}", REPO / c["path"]) for c in panel}

    first = run_once(mods, corpora, controls, source_text, map_snapshot, paths)
    second = run_once(mods, corpora, controls, source_text, map_snapshot, paths)
    deterministic = json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)

    # ---- acceptance verdicts ----
    verdicts = {}
    for c in panel:
        mid = c["id"]
        gates = {}
        for cname in CORPUS_ORDER:
            agg = first["corpora"][cname]["modules"][mid]["aggregates"]
            gates[f"g_cue_fn_zero_{cname}"] = agg["cue_induced_fn_total"] == 0
        w7 = first["controls"]["worker07_regression"][mid]
        gates["g_worker07_pass"] = w7["verdict"] == "PASS" and w7["tp"] == 17 and w7["fn"] == 0 \
            and w7["tn"] == 10 and w7["fp"] == 0
        w = first["controls"]["w098_declared_controls"][mid]
        gates["g_w098_fire_all"] = w["fire_all"] and w["tp_all_fire"]
        gates["g_w098_clean_silent"] = w["clean_all_silent"]
        gates["g_w098_growth_zero"] = w["growth_all_zero"]
        if c.get("decl_parity_gated"):
            gates["g_decl_parity_vs_c266"] = all(
                not first["corpora"][cn]["modules"][mid]["aggregates"]["declaration_diff_vs_c266"]
                for cn in CORPUS_ORDER)
        failed = [k for k, v in gates.items() if not v]
        verdicts[mid] = {
            "verdict": "ACCEPTANCE_PASS" if not failed else "FAIL",
            "failed_gates": failed,
            "gates": gates,
            "decl_parity_gated": bool(c.get("decl_parity_gated")),
            "role": c["role"],
            "sha256": c["sha256"],
        }

    # ---- cross-corpus summary ----
    summary = {}
    for c in panel:
        mid = c["id"]
        s = {"cue_fn_total_all_corpora": 0, "non_cue_fn_total_all_corpora": 0,
             "adversarial_cleared_total_all_corpora": 0, "plain_fn_total_all_corpora": 0,
             "twins_not_flagged_all_corpora": 0, "per_corpus": {}}
        for cn in CORPUS_ORDER:
            a = first["corpora"][cn]["modules"][mid]["aggregates"]
            s["cue_fn_total_all_corpora"] += a["cue_induced_fn_total"]
            s["non_cue_fn_total_all_corpora"] += a["non_cue_fn_total"]
            s["adversarial_cleared_total_all_corpora"] += a["adversarial_cleared_total"]
            s["plain_fn_total_all_corpora"] += len(a["plain_positive_fn"])
            s["twins_not_flagged_all_corpora"] += len(a["twins_not_flagged"])
            s["per_corpus"][cn] = {
                "cue_fn": a["cue_induced_fn_total"],
                "non_cue_fn": a["non_cue_fn_total"],
                "adversarial_cleared": a["adversarial_cleared_total"],
                "adversarial_total": a["adversarial_total"],
                "plain_fn": a["plain_positive_fn"],
                "twins_not_flagged": a["twins_not_flagged"],
                "mention_fp": a["mention_fp"],
            }
        summary[mid] = s

    # ---- drift check ----
    drift = {"candidates": {}, "inputs": {}}
    for c in panel:
        now = sha256_file(REPO / c["path"])
        drift["candidates"][c["id"]] = {"pinned": c["sha256"], "at_end": now, "moved": now != c["sha256"]}
    for k, (p, want) in PINS.items():
        now = sha256_file(p)
        drift["inputs"][k] = {"pinned": want, "at_end": now, "moved": now != want}
    live_map_end = sha256_file(REPO / "research_map/research_map.json")
    entry = drift["inputs"].setdefault("live_map", {"pinned": map_sha, "at_end": live_map_end,
                                                    "moved": live_map_end != map_sha})
    candidate_set_drift = any(v["moved"] for v in drift["candidates"].values())
    input_drift = any(v["moved"] for v in drift["inputs"].values())
    if candidate_set_drift or input_drift:
        for mid in verdicts:
            verdicts[mid]["verdict"] = "VOID"
            verdicts[mid]["void_reason"] = {
                "candidate_set_drift": candidate_set_drift, "input_drift": input_drift}

    leak = leak_check(corpora["corpus_v3"])
    first["pins"] = pins
    first["candidate_panel"] = panel
    first["candidates_pinned_manifest_sha256"] = sha256_file(pin_manifest_path)
    first["w098_controls_copy_sha256"] = sha256_file(HERE / "w098_controls.json")
    first["pre_registration_sha256"] = sha256_file(HERE / "pre_registration.json")
    first["leak_check"] = leak
    first["summary"] = summary
    first["verdicts"] = verdicts
    first["drift"] = drift
    first["controls"]["double_run_byte_deterministic"] = deterministic

    if not deterministic:
        print("INTERNAL INCONSISTENCY: double run differs", file=sys.stderr)
        return 3

    RESULTS_PATH.write_text(json.dumps(first, indent=1, sort_keys=False) + "\n")
    print(f"wrote {RESULTS_PATH.relative_to(REPO)} sha256={sha256_file(RESULTS_PATH)}")
    for cname in CORPUS_ORDER:
        print(f"-- {cname} --")
        for c in panel:
            a = first["corpora"][cname]["modules"][c["id"]]["aggregates"]
            print(f"   {c['id']:28s} cueFN={a['cue_induced_fn_total']:2d} "
                  f"(H={a['cue_induced_fn_high_confidence']},M={a['cue_induced_fn_non_high_confidence']}) "
                  f"cleared={len(a['adversarial_cleared'])}/{a['adversarial_total']} "
                  f"twins={a['twin_controls_flagged']} mentionFP={len(a['mention_fp'])} "
                  f"declDiff={len(a.get('declaration_diff_vs_c266', []))}")
    print("-- verdicts --")
    for mid, v in verdicts.items():
        print(f"   {mid:28s} {v['verdict']:16s} failed={v['failed_gates']}")
    print("-- worker07 --")
    for mid, r in first["controls"]["worker07_regression"].items():
        print(f"   {mid:28s} {r['tp']}/{r['fn']}/{r['tn']}/{r['fp']} {r['verdict']}")
    print(f"deterministic={deterministic} leak_check_clean={leak['clean']} "
          f"scanned={leak['scanned_files']} candidate_set_drift={candidate_set_drift} "
          f"input_drift={input_drift}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
