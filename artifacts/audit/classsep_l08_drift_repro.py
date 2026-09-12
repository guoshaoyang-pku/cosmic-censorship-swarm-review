#!/usr/bin/env python3
"""CLASSSEP lifecycle-08 detector-drift independent reproduction (v2, corrected).

v1 (classsep_l08_drift_repro_20260912T010856.json) mislabeled its live arm: it ran at
01:08:56, AFTER the controller's 01:08:14 mechanical restore, so the arm it called
LIVE_E36B actually measured the restored a8c04fc3 bytes. v1 is preserved renamed with a
MISLABELED marker and is superseded by this run, which declares every arm by its own hash.

State this round binds (controller CF-29 / REC-29/30/31):
  declared frozen pin        c266dbec   (unchanged by ruling)
  restored operative bytes   a8c04fc3   (adjudicated r3 APPLIED; live since 01:08:14)
  void evidence write        e36b0d644ca7 (01:06:12; not adopted; any further write voids round)
  independent review         reviews/CLASSSEP-adjudication-review-017.json (worker-017, revise 4.0)

Read-only on every canonical / proposed / corpus file. Writes only artifacts/audit/pins/*
and artifacts/audit/classsep_l08_drift_repro_*. No gate verdict, no detector write.
"""
from __future__ import annotations

import difflib
import hashlib
import importlib.util
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import classsep_calibration as cal          # noqa: E402
import classsep_r3_adjudication as r3       # noqa: E402

STAMP = datetime.now().astimezone().strftime("%Y%m%dT%H%M%S")
NOW = datetime.now().astimezone().isoformat(timespec="seconds")
PINS_DIR = HERE / "pins"
PINS_DIR.mkdir(parents=True, exist_ok=True)

LIVE = "research_map/class_separation.py"
L07_SNAP = "artifacts/audit/classsep_r3_map_snapshot_20260912T010324.json"
META_FIXTURES = "artifacts/audit/meta_audit_fixtures_l08.json"
MAP = "research_map/research_map.json"
R3_ADJ = "reviews/CLASSSEP-calibration-adjudication.json"
REVIEW_017 = "reviews/CLASSSEP-adjudication-review-017.json"
CF29 = "runtime/state/controller_verification/cf29-detector-write-forensics.json"

# Every arm is explicit; the void write is measured as evidence, never as operative.
ARMS = {
    "PRE_C266": ("artifacts/worker-049/classsep_fn_audit/pinned/class_separation_c266_recovered.py",
                 "c266dbceca87"),
    "LIVE_A8C04FC3": ("artifacts/worker-073/classsep_union_separability/pinned/"
                      "class_separation.live.a8c04fc31e4a.py", "a8c04fc31e4a"),
    "VOID_E36B": ("artifacts/worker-073/classsep_union_separability/pinned/"
                  "class_separation.live.e36b0d644ca7.py", "e36b0d644ca7"),
    "STAGED_E2D2": ("proposed/class_separation.py", "e2d24b927ee8"),
    "PROSEFIX_DC8A": ("artifacts/worker-049/classsep_prose_fix/class_separation_prosefix.py",
                      "dc8aa0de3869"),
}

# independent observations of the live canonical path by this agent, for the drift timeline
LIVE_HISTORY = [
    {"at": "2026-09-12T01:07:0x+08:00", "sha256_prefix": "e36b0d644ca7",
     "method": "direct sha256sum x4 over 12s; stable",
     "note": "void write observed live before the controller restore; matches CF-29 unauthorized sha"},
    {"at": "2026-09-12T01:08:14+08:00", "sha256_prefix": "a8c04fc31e4a",
     "method": "mtime of research_map/class_separation.py (01:08:14.862); sha measured after",
     "note": "mechanical restore; matches CF-29 restored_sha256"},
    {"at": "2026-09-12T01:11:0x+08:00", "sha256_prefix": "a8c04fc31e4a",
     "method": "direct sha256sum x3 over 6s; stable",
     "note": "quiescent at the operative bytes at audit measurement time"},
]

PINS = {
    LIVE: None, MAP: None, L07_SNAP: None, META_FIXTURES: None,
    R3_ADJ: None, REVIEW_017: None, CF29: None,
    "artifacts/worker-017/classsep_adjudication_review/drift_timeline.json": None,
    "artifacts/worker-017/classsep_adjudication_review/report.json": None,
    "artifacts/worker-017/classsep_adjudication_review/report_pinned_a8c04fc3.json": None,
    "artifacts/worker-07/class_separation_falsification/results.json": None,
    "artifacts/worker-049/classsep_fn_audit/run_fn_audit_049.py": None,
    "artifacts/worker-049/classsep_fn_audit/corpus.json": None,
    "artifacts/worker-049/classsep_prose_fix/worker035_controls.json": None,
    "artifacts/worker-049/classsep_fn_audit/results.json": None,
    "artifacts/worker-098/classsep_prose_shadow/drift_recheck.json": None,
    "runtime/bin/classsep_regression.py": None,
    "evaluation_rubric.yaml": None, "ledger/theorems.jsonl": None,
    "research_map/formulation_taxonomy.yaml": None,
    "artifacts/formulation/FROZEN.json": None,
}
for _rel, _ in ARMS.values():
    PINS[_rel] = None


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else "ABSENT"


def measure() -> dict:
    return {rel: sha256(ROOT / rel) for rel in PINS}


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def diffstat(a_text: str, b_text: str) -> dict:
    d = list(difflib.unified_diff(a_text.splitlines(), b_text.splitlines(),
                                  fromfile="before", tofile="after", lineterm="", n=1))
    return {"added_lines": sum(1 for l in d if l.startswith("+") and not l.startswith("+++")),
            "removed_lines": sum(1 for l in d if l.startswith("-") and not l.startswith("---")),
            "unified_diff": "\n".join(d[:120])}


def meta_fixture_census(mod, fixtures: dict) -> dict:
    rows = []
    tp = fp = tn = fn = 0
    for fx in fixtures["fixtures"]:
        fired = bool(mod.findings_for_text(fx["text"], f"fixture {fx['id']}"))
        truth = bool(fx["expect_fire"])
        cls = ("TP" if truth and fired else "FN" if truth else "FP" if fired else "TN")
        if cls == "TP": tp += 1
        elif cls == "FN": fn += 1
        elif cls == "FP": fp += 1
        else: tn += 1
        rows.append({"id": fx["id"], "mechanism": fx["mechanism"], "expect_fire": truth,
                     "fired": fired, "class": cls})
    return {"tp": tp, "fn": fn, "fp": fp, "tn": tn, "n": len(rows),
            "assertion_recall": f"{tp}/{tp+fn}", "mention_specificity": f"{tn}/{tn+fp}",
            "rows": rows}


def main() -> int:
    # snapshot whichever bytes are live now, under a name derived from the measured hash
    live_sha = sha256(ROOT / LIVE)
    live_pin = PINS_DIR / f"class_separation.live_now.{live_sha[:12]}.py"
    if not live_pin.exists():
        shutil.copyfile(ROOT / LIVE, live_pin)
    if sha256(live_pin) != live_sha:
        print("FAIL-CLOSED: live detector moved during snapshot copy")
        return 2
    live_rel = live_pin.relative_to(ROOT).as_posix()
    ARMS[f"LIVE_NOW_{live_sha[:12]}"] = (live_rel, live_sha[:12])

    map_sha = sha256(ROOT / MAP)
    l08_snap = PINS_DIR / f"classsep_l08b_map_snapshot_{STAMP}.json"
    shutil.copyfile(ROOT / MAP, l08_snap)
    if sha256(l08_snap) != map_sha:
        print("FAIL-CLOSED: map moved during snapshot copy")
        return 2
    l08_rel = l08_snap.relative_to(ROOT).as_posix()
    PINS[l08_rel] = None
    pre = measure()

    arm_pins, bad = {}, []
    for arm, (rel, cited) in ARMS.items():
        got = sha256(ROOT / rel)
        ok = got.startswith(cited)
        arm_pins[arm] = {"path": rel, "sha256": got, "cited_prefix": cited, "cited_match": ok}
        if not ok:
            bad.append(f"{arm}: {got[:12]} != {cited}")
    if bad:
        print("FAIL-CLOSED cited hash mismatch:", bad)
        return 2

    mods = {arm: load(ROOT / rel, f"cs_{arm.lower()}") for arm, (rel, _) in ARMS.items()}
    text = lambda rel: (ROOT / rel).read_text(errors="replace")

    chain = {
        "c266dbec -> a8c04fc3 (REC-22 pin -> adjudicated APPLIED)":
            diffstat(text(ARMS["PRE_C266"][0]), text(ARMS["LIVE_A8C04FC3"][0])),
        "a8c04fc3 -> e36b0d644ca7 (APPLIED -> void write 01:06:12)":
            diffstat(text(ARMS["LIVE_A8C04FC3"][0]), text(ARMS["VOID_E36B"][0])),
        "c266dbec -> e36b0d644ca7 (pin -> void write)":
            diffstat(text(ARMS["PRE_C266"][0]), text(ARMS["VOID_E36B"][0])),
    }

    w049 = load(ROOT / "artifacts/worker-049/classsep_fn_audit/run_fn_audit_049.py", "w049")
    corpus_a = {arm: cal.corpus_census(m) for arm, m in mods.items()}
    corpus_c = {arm: cal.fixture_census(m) for arm, m in mods.items()}
    corpus_d = r3.worker049_census(w049, mods)
    corpus_b_l07 = {arm: r3.live_census_frozen(m, ROOT / L07_SNAP) for arm, m in mods.items()}
    corpus_b_l08 = {arm: r3.live_census_frozen(m, l08_snap) for arm, m in mods.items()}
    fixtures = json.loads((ROOT / META_FIXTURES).read_text())
    corpus_m = {arm: meta_fixture_census(m, fixtures) for arm, m in mods.items()}

    cal.MAP = l08_snap
    converse = {}
    for arm, m in mods.items():
        flagged = sorted({r["claim_index"] for r in corpus_b_l08[arm]["labeled_detail"]}
                         | {r["claim_index"] for r in corpus_b_l08[arm]["unlabeled"]})
        converse[arm] = cal.converse_scan(m, {"claims_affected": flagged})

    def bar(a, c, d, mm):
        sens = c["tp"] / (c["tp"] + c["fn"]) if (c["tp"] + c["fn"]) else 0.0
        spec = c["tn"] / (c["tn"] + c["fp"]) if (c["tn"] + c["fp"]) else 0.0
        meta_ok = mm["fn"] == 0 and mm["fp"] == 0
        return {"corpus_a_pass": a["verdict"] == "PASS",
                "sensitivity": f"{c['tp']}/{c['tp']+c['fn']}", "sens_ok": sens >= 5 / 6,
                "specificity": f"{c['tn']}/{c['tn']+c['fp']}", "spec_ok": spec >= 9 / 10,
                "cue_fn_high": d["cue_induced_fn_high_confidence"],
                "battery": f"{d['worker035_battery']['passed']}/{d['worker035_battery']['total']}",
                "meta_fixture_pass": meta_ok,
                "meta_probe": f"assert {mm['assertion_recall']} mention {mm['mention_specificity']}",
                "meets_bar": (a["verdict"] == "PASS" and sens >= 5 / 6 and spec >= 9 / 10
                              and d["cue_induced_fn_high_confidence"] == 0 and meta_ok)}
    bars = {arm: bar(corpus_a[arm], corpus_c[arm], corpus_d[arm], corpus_m[arm]) for arm in ARMS}

    post = measure()
    moved = {rel: {"pre": pre[rel], "post": post[rel]} for rel in pre if pre[rel] != post[rel]}

    out = {
        "artifact": "classsep-l08-drift-repro",
        "revision": "l08-v2-corrected",
        "supersedes": {
            "path": "artifacts/audit/classsep_l08_drift_repro_20260912T010856.MISLABELED-live-arm-void.json",
            "defect": "v1 ran at 01:08:56, after the 01:08:14 restore, so its arm named "
                      "LIVE_E36B actually measured the restored a8c04fc3 bytes; its 461-claim "
                      "census numbers are valid for a8c04fc3 but the arm label is wrong. v1 was "
                      "never emitted as an event and is preserved renamed, not deleted.",
        },
        "actor": "astra-lead-audit", "created_at": NOW,
        "assignment": "astra-life07-classsep-adjudication-review (notice) + controller REC-29/30/31",
        "node_id": "A1", "gate": "G-AUDIT",
        "scope": "independent measurement only; read-only on canonical/proposed/corpus files; "
                 "no gate verdict, no node status, no detector write, no action on quarantined cards",
        "live_history": LIVE_HISTORY,
        "pins_pre": pre, "pins_post": post, "pins_moved_during_round": moved,
        "arm_pins": arm_pins,
        "live_now": {"sha256": live_sha, "path": live_rel,
                     "is_operative_a8c04fc3": live_sha.startswith("a8c04fc31e4a")},
        "l08_map_snapshot": {"path": l08_rel, "sha256": map_sha,
                             "claims": corpus_b_l08[f"LIVE_NOW_{live_sha[:12]}"]["claims_in_map"]},
        "l07_map_snapshot": {"path": L07_SNAP, "sha256": sha256(ROOT / L07_SNAP),
                             "claims": corpus_b_l07[f"LIVE_NOW_{live_sha[:12]}"]["claims_in_map"]},
        "drift_chain": chain,
        "corpus_a_27fixtures": {k: {kk: vv for kk, vv in v.items() if kk != "non_pass_rows"}
                                for k, v in corpus_a.items()},
        "corpus_b_l07_live": {k: {kk: vv for kk, vv in v.items()
                                  if kk not in ("labeled_detail", "unlabeled")}
                              for k, v in corpus_b_l07.items()},
        "corpus_b_l08_live": {k: {kk: vv for kk, vv in v.items()
                                  if kk not in ("labeled_detail", "unlabeled")}
                              for k, v in corpus_b_l08.items()},
        "corpus_b_l08_live_detail": {k: {"labeled_detail": v["labeled_detail"],
                                         "unlabeled": v["unlabeled"],
                                         "non_claim_findings": v["non_claim_findings"]}
                                     for k, v in corpus_b_l08.items()},
        "corpus_c_assertion_mention": corpus_c,
        "corpus_d_worker049_cue_fn": {k: {kk: vv for kk, vv in v.items() if kk != "per_fixture"}
                                      for k, v in corpus_d.items()},
        "corpus_d_fixture_classes": {k: r3.census_summary(v) for k, v in corpus_d.items()},
        "corpus_m_meta_audit_fixtures": corpus_m,
        "converse_scan_l08": {k: {kk: vv for kk, vv in v.items() if kk != "unflagged_detail"}
                              for k, v in converse.items()},
        "adoption_bars": bars,
        "adoptable_arms": [k for k, v in bars.items() if v["meets_bar"]],
        "review_017_reproduction": {
            "review_verdict": "revise", "review_score": 4.0,
            "cited_prefixes_verified": {
                R3_ADJ: pre[R3_ADJ][:12] == "7714ffd5b467",
                "artifacts/worker-017/classsep_adjudication_review/drift_timeline.json":
                    pre["artifacts/worker-017/classsep_adjudication_review/drift_timeline.json"][:12] == "141bcca91972",
                "artifacts/worker-017/classsep_adjudication_review/report.json":
                    pre["artifacts/worker-017/classsep_adjudication_review/report.json"][:12] == "07960bdf4f93",
                "artifacts/worker-017/classsep_adjudication_review/report_pinned_a8c04fc3.json":
                    pre["artifacts/worker-017/classsep_adjudication_review/report_pinned_a8c04fc3.json"][:12] == "afd993767da5",
            },
        },
    }
    out_path = HERE / f"classsep_l08_drift_repro_{STAMP}.json"
    out_path.write_text(json.dumps(out, indent=2, sort_keys=True))
    shutil.copyfile(out_path, HERE / "classsep_l08_drift_repro_latest.json")

    print(f"wrote {out_path.name} sha={sha256(out_path)[:12]}")
    print(f"live now = {live_sha[:12]} (operative a8c04fc3: {out['live_now']['is_operative_a8c04fc3']})")
    print(f"pins moved during round: {list(moved) or 'NONE'}")
    print(f"l07 claims={out['l07_map_snapshot']['claims']} l08 claims={out['l08_map_snapshot']['claims']}")
    print(f"{'arm':<24} {'27fix':<8} {'sens':<6} {'spec':<7} {'cueFNhi':<8} {'w035':<7} "
          f"{'metaProbe':<22} meets")
    for arm in ARMS:
        b = bars[arm]
        print(f"{arm:<24} {corpus_a[arm]['verdict']:<8} {b['sensitivity']:<6} {b['specificity']:<7} "
              f"{b['cue_fn_high']:<8} {b['battery']:<7} {b['meta_probe']:<22} {b['meets_bar']}")
    print("drift a8c04fc3->e36b:", chain["a8c04fc3 -> e36b0d644ca7 (APPLIED -> void write 01:06:12)"]["added_lines"],
          "added,", chain["a8c04fc3 -> e36b0d644ca7 (APPLIED -> void write 01:06:12)"]["removed_lines"], "removed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
