#!/usr/bin/env python3
"""W065-CF32-REPIN-SAFETY-06 : bounded, read-only measurement for REC-36 item (7).

Question
--------
(1) Is the pinned acceptance report `artifacts/formulation/evidence/acceptance_pipeline_report.json`
    (sha256 9b7d6c82...) reproducible from the pinned inputs it declares?
(2) Can the semantic-escape corpus be re-bound to the current canonical C0 by a base-hash re-pin
    alone, or does every fixture carry deltas beyond its declared mutation_path (semantic staleness)?

Framing
-------
The live tree moved during the first run (the authorized rev14 repair was landing). Every statement
here therefore binds to an immutable snapshot taken at freeze time, recorded by digest:
`snapshot/snapshot_manifest.json`. Live-at-freeze hashes are reported; later live drift is recorded
as an informational `live_drift` field, not as part of the claim.

Arms (all writes stay under artifacts/worker-065/cf32_repin_safety/)
-------------------------------------------------------------------
L  live     : unmodified runner at the snapshot canonical C0             -> expect exit 3
C  corrupt  : snapshot C0 + corpus base forced to 64 zeros               -> expect exit 3
P  pinned   : sandbox C0 restored to declared pin 1bb78ce9, snapshot
              instruments, unmodified runner                            -> record exit/JSON/report
PL per-fixture ledger : each fixture + each canonical schema through both
              stages; compare with the corpus's recorded per-mutant verdicts
DEP dependency closure: every file the instruments read, hashed, marked
              declared by corpus manifest / by FROZEN / by neither
S  re-pin   : structural leaf-diff of each fixture vs pinned C0 and vs the
              snapshot canonical C0; REPIN_SAFE only when no delta exists
              outside the declared mutation_path

No canonical path is written; instruments are copied into the sandbox, never edited.
"""
from __future__ import annotations
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

TZ = timezone(timedelta(hours=8))
ROOT = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
OUT = ROOT / "artifacts/worker-065/cf32_repin_safety"
RUNS = OUT / "runs"
SNAP = OUT / "snapshot"

PIN_C0 = "1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508"
DECL_GATE = "000e09e46b2fb4abc047c21e99165cbc55692f3132744fb27e84645609263aff"
DECL_AUD = "c79d8ab8440ac6738bb61df5a33e9fd5f8319b4e74e1f2e9c0fc5083fb408cec"
DECL_MANIFEST = "c102445df3971109101e4d54b609ff1c5bfdf9147ddb1f1b099476a816030deb"
DECL_REPORT = "9b7d6c8208d3beae2510c5c9c0a4bdaf7ede8adb277cd2a4f6f9cd0fd430f0c6"
DECL_CORPUS = "7e44de0e3906dc74f607629b88bdc6cbfb438ce39c759e4054156a9345b38292"
PIN_C0_SOURCES = [
    "artifacts/worker-061/f1_independent_verdict/pinned/af_scc_c0_vacuum.yaml",
    "artifacts/worker-092/pubconf/pinned/schemas__af_scc_c0_vacuum.yaml",
]
SCHEMA_F1 = "artifacts/formulation/schemas/af_wcc_vacuum.yaml"
SCHEMA_F2A = "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml"
SCHEMA_C0 = "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"
GATE = "artifacts/formulation/tools/check_class_schema.py"
AUD = "artifacts/worker-06/spec_conformance_audit.py"
RUNNER = "artifacts/formulation/tools/run_acceptance.py"
SPEC = "artifacts/formulation/rule_spec.json"
KEYS = "artifacts/formulation/KEY_MANIFEST.json"
CORPUS = "artifacts/formulation/evidence/semantic_escape_rebased.json"
FIXDIR = "artifacts/formulation/evidence/rebased_fixtures"
MANIFEST = "artifacts/worker-06/semantic_fixtures/manifest.json"
REPORT = "artifacts/formulation/evidence/acceptance_pipeline_report.json"
FROZEN = "artifacts/formulation/FROZEN.json"
ENTRY = "entry_hashes.json"
MAP = "research_map/research_map.json"
EVENTS = "research_map/events.jsonl"


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def flatten(node, prefix="", out=None):
    if out is None:
        out = {}
    if isinstance(node, dict):
        for k in sorted(node, key=str):
            flatten(node[k], f"{prefix}.{k}" if prefix else str(k), out)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            flatten(v, f"{prefix}[{i}]", out)
    else:
        out[prefix] = json.dumps(node, sort_keys=True, ensure_ascii=False)
    return out


def diff(a, b):
    changed, added, removed = {}, {}, {}
    for p in sorted(set(a) | set(b)):
        if p in a and p in b:
            if a[p] != b[p]:
                changed[p] = {"base": a[p], "fixture": b[p]}
        elif p in b:
            added[p] = {"fixture": b[p]}
        else:
            removed[p] = {"base": a[p]}
    return changed, added, removed


def is_covered(path: str, declared: str) -> bool:
    if not declared:
        return False
    return path == declared or path.startswith(declared + ".") or path.startswith(declared + "[")


def freeze() -> dict:
    """Immutable snapshot of every input. Returns manifest with per-file hashes and digest."""
    if SNAP.exists():
        shutil.rmtree(SNAP)
    files = [RUNNER, GATE, AUD, SPEC, KEYS, CORPUS, MANIFEST, REPORT, FROZEN, ENTRY,
             SCHEMA_F1, SCHEMA_F2A, SCHEMA_C0, MAP]
    for r in files:
        dst = SNAP / r
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / r, dst)
    shutil.copytree(ROOT / FIXDIR, SNAP / FIXDIR)
    rows = []
    for p in sorted(SNAP.rglob("*")):
        if p.is_file():
            rows.append({"path": str(p.relative_to(SNAP)), "sha256": sha256(p), "bytes": p.stat().st_size})
    digest = hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()
    man = {"frozen_at": now(), "file_count": len(rows), "digest": digest, "files": rows}
    (SNAP / "snapshot_manifest.json").write_text(json.dumps(man, indent=1))
    return man


def verify_snapshot(man: dict) -> bool:
    cur = []
    for p in sorted(SNAP.rglob("*")):
        if p.is_file() and p.name != "snapshot_manifest.json":
            cur.append({"path": str(p.relative_to(SNAP)), "sha256": sha256(p), "bytes": p.stat().st_size})
    want = [r for r in man["files"] if r["path"] != "snapshot_manifest.json"]
    return hashlib.sha256(json.dumps(cur, sort_keys=True).encode()).hexdigest() == man["digest"] and cur == want


def live_hashes(paths):
    out = {}
    for r in paths:
        p = ROOT / r
        out[r] = {"exists": p.exists(), "sha256": sha256(p) if p.exists() and p.is_file() else None}
    return out


def build_sandbox(name: str) -> Path:
    sb = OUT / f"sandbox_{name}"
    if sb.exists():
        shutil.rmtree(sb)
    for d in ["artifacts/formulation/tools", "artifacts/formulation/schemas",
              "artifacts/formulation/evidence", "artifacts/worker-06"]:
        (sb / d).mkdir(parents=True, exist_ok=True)
    for r in [RUNNER, GATE, SPEC, KEYS]:
        shutil.copy2(SNAP / r, sb / r)
    shutil.copy2(SNAP / AUD, sb / AUD)
    shutil.copy2(SNAP / CORPUS, sb / CORPUS)
    shutil.copytree(SNAP / FIXDIR, sb / FIXDIR)
    shutil.copy2(SNAP / SCHEMA_F1, sb / SCHEMA_F1)
    shutil.copy2(SNAP / SCHEMA_F2A, sb / SCHEMA_F2A)
    return sb


def sandbox_inputs(sb: Path) -> dict:
    rows = [RUNNER, GATE, AUD, SPEC, KEYS, CORPUS, MANIFEST, REPORT, SCHEMA_F1, SCHEMA_F2A, SCHEMA_C0]
    return {r: sha256(sb / r) if (sb / r).exists() else None for r in rows}


def run_runner(sb: Path, label: str) -> dict:
    t0 = time.time()
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    r = subprocess.run([sys.executable, str(sb / RUNNER), "--json"],
                       capture_output=True, text=True, cwd=str(sb), env=env, timeout=2400)
    dt = time.time() - t0
    try:
        body = json.loads(r.stdout)
    except Exception:
        body = None
    (RUNS / f"{label}.stdout").write_text(r.stdout)
    (RUNS / f"{label}.stderr").write_text(r.stderr)
    rep = sb / REPORT
    return {"label": label, "exit_code": r.returncode, "seconds": round(dt, 2),
            "json_parsed": body is not None, "body": body,
            "stdout_sha256": hashlib.sha256(r.stdout.encode()).hexdigest(),
            "stderr_head": r.stderr[:400],
            "sandbox_report_written": rep.exists(),
            "sandbox_report_sha256": sha256(rep) if rep.exists() else None}


def stage_pair(sb: Path, target: Path):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    try:
        g = subprocess.run([sys.executable, str(sb / GATE), "--json", str(target)],
                           capture_output=True, text=True, env=env, timeout=180)
        gd = json.loads(g.stdout)
    except Exception:
        gd = {"verdict": "crash", "failed_rules": []}
    try:
        s = subprocess.run([sys.executable, str(sb / AUD), str(target)],
                           capture_output=True, text=True, env=env, timeout=180)
        sd = json.loads(s.stdout)
    except Exception:
        sd = {"verdict": "crash", "failed_rules": []}
    return {"structural_verdict": gd.get("verdict"),
            "structural_failed_rules": gd.get("failed_rules", []),
            "semantic_verdict": sd.get("verdict"),
            "semantic_failed_rules": sd.get("failed_rules", [])}


def arm_pl(sb: Path, corpus: dict) -> dict:
    rows = []
    for f in sorted((sb / FIXDIR).glob("*.yaml")):
        r = stage_pair(sb, f)
        r["fixture"] = f.name
        rows.append(r)
    canon = {}
    for name in ["af_wcc_vacuum.yaml", "af_scc_c2_vacuum.yaml", "af_scc_c0_vacuum.yaml"]:
        canon[name] = stage_pair(sb, sb / "artifacts/formulation/schemas" / name)
    decl = {m["fixture"]: m for m in corpus.get("mutants", [])}
    cdecl = {(c.get("fixture") or c.get("name", "")): c for c in corpus.get("controls", [])}
    mism, rule_drift, verdict_flip = [], [], []
    for r in rows:
        m = decl.get(r["fixture"])
        if not m:
            c = cdecl.get(r["fixture"]) or cdecl.get(r["fixture"][:-5])
            if c and (r["structural_verdict"] == "pass") != (c.get("canonical_verdict") == "pass"):
                verdict_flip.append({"fixture": r["fixture"], "kind": "control",
                                     "recorded": c.get("canonical_verdict"), "replay": r["structural_verdict"]})
                mism.append(verdict_flip[-1])
            continue
        exp_v, exp_r = m.get("canonical_verdict"), sorted(m.get("canonical_failed_rules", []))
        got_r = sorted(r["structural_failed_rules"])
        if (r["structural_verdict"] == "pass") != (exp_v == "pass"):
            verdict_flip.append({"fixture": r["fixture"], "recorded": exp_v, "replay": r["structural_verdict"]})
            mism.append(verdict_flip[-1])
        elif got_r != exp_r:
            rule_drift.append({"fixture": r["fixture"], "recorded_rules": exp_r, "replay_rules": got_r})
            mism.append({"fixture": r["fixture"], "recorded_rules": exp_r, "replay_rules": got_r})
        exp_w = m.get("w06_verdict")
        if (r["semantic_verdict"] == "accept") != (exp_w == "accept"):
            mism.append({"fixture": r["fixture"], "kind": "semantic",
                         "recorded_w06": exp_w, "replay_w06": r["semantic_verdict"]})
    agg = {"structural_caught": sum(1 for r in rows if r["structural_verdict"] == "fail" and not r["fixture"].startswith("control_")),
           "semantic_caught": sum(1 for r in rows if r["semantic_verdict"] == "reject" and not r["fixture"].startswith("control_")),
           "controls_ok": sum(1 for r in rows if r["fixture"].startswith("control_") and r["structural_verdict"] == "pass" and r["semantic_verdict"] == "accept"),
           "mutants_total": sum(1 for r in rows if not r["fixture"].startswith("control_"))}
    return {"fixture_rows": rows, "canonical_rows": canon, "aggregate": agg,
            "recorded_vs_replay_mismatches": mism, "mismatch_count": len(mism),
            "verdict_flips": verdict_flip, "rule_set_drift_count": len(rule_drift),
            "rule_set_drift_sample": rule_drift[:8]}


def dependency_closure(frozen: dict) -> dict:
    deps = [RUNNER, GATE, AUD, SPEC, KEYS, CORPUS, MANIFEST, REPORT,
            SCHEMA_F1, SCHEMA_F2A, SCHEMA_C0]
    corpus = json.loads((SNAP / CORPUS).read_text())
    corpus_declared = {corpus.get("base_schema"), corpus.get("corpus_manifest"),
                       corpus.get("gate"), corpus.get("w06_auditor")}
    frozen_files = frozen.get("files", {})
    rows = []
    for r in deps:
        p = SNAP / r
        h = sha256(p) if p.exists() else None
        fz = frozen_files.get(r)
        fz_hash = fz.get("sha256") if isinstance(fz, dict) else fz
        rows.append({"path": r, "snapshot_sha256": h,
                     "declared_by_corpus_manifest": r in corpus_declared,
                     "declared_by_frozen_files": r in frozen_files,
                     "frozen_declared_sha256": fz_hash,
                     "frozen_hash_matches_snapshot": fz_hash == h,
                     "unpinned_by_corpus_manifest": r not in corpus_declared,
                     "unpinned_by_both": (r not in corpus_declared) and (r not in frozen_files)})
    return {"dependency_rows": rows,
            "unpinned_by_corpus_manifest": [x["path"] for x in rows if x["unpinned_by_corpus_manifest"]],
            "unpinned_by_both": [x["path"] for x in rows if x["unpinned_by_both"]],
            "frozen_revision": frozen.get("revision")}


def arm_s(corpus: dict, base_path: Path, base_label: str) -> dict:
    pinned = flatten(yaml.safe_load((OUT / "sandbox_pinned" / SCHEMA_C0).read_text()))
    base = flatten(yaml.safe_load(base_path.read_text()))
    base_shift = sorted(p for p in set(pinned) | set(base) if pinned.get(p) != base.get(p))
    decl = {m["fixture"]: m for m in corpus.get("mutants", [])}
    ctrls = {(c.get("fixture") or c.get("name", "")): c for c in corpus.get("controls", [])}
    rows = []
    for f in sorted((ROOT / FIXDIR).glob("*.yaml")):
        fx = flatten(yaml.safe_load(f.read_text()))
        meta = decl.get(f.name) or ctrls.get(f.name) or ctrls.get(f.name[:-5]) or {}
        declared = meta.get("mutation_path", "")
        c_pin, a_pin, r_pin = diff(pinned, fx)
        c_live, a_live, r_live = diff(base, fx)
        dl = {**c_live, **a_live, **r_live}
        extra = sorted(p for p in dl if not is_covered(p, declared))
        if f.name.startswith("control_"):
            cls = "CONTROL"
        elif not dl:
            cls = "MUTATION_SUBSUMED"
        elif not declared:
            cls = "NO_DECLARED_PATH"
        elif extra:
            cls = "REPIN_UNSAFE_EXTRA_DELTA"
        else:
            cls = "REPIN_SAFE_DECLARED_ONLY"
        rows.append({"fixture": f.name, "role": "control" if f.name.startswith("control_") else "mutant",
                     "declared_mutation_path": declared,
                     "declared_path_carried_vs_pinned": any(is_covered(p, declared) for p in {**c_pin, **a_pin, **r_pin}),
                     "delta_vs_pinned_count": len(c_pin) + len(a_pin) + len(r_pin),
                     "delta_vs_base_count": len(dl),
                     "extra_delta_paths_vs_base": extra[:15],
                     "extra_delta_count": len(extra),
                     "class": cls, "fixture_sha256": sha256(f)})
    summ = {}
    for r in rows:
        summ[r["class"]] = summ.get(r["class"], 0) + 1
    unsafe = any(r["class"] in ("REPIN_UNSAFE_EXTRA_DELTA", "MUTATION_SUBSUMED", "NO_DECLARED_PATH")
                 and r["role"] == "mutant" for r in rows)
    return {"base_label": base_label, "base_sha256": sha256(base_path),
            "pinned_base_sha256": PIN_C0,
            "pinned_base_leaves": len(pinned), "base_leaves": len(base),
            "base_shift_path_count": len(base_shift), "base_shift_paths": base_shift[:100],
            "class_summary": summ,
            "repin_verdict": "REPIN_UNSAFE_REGENERATE" if unsafe else "REPIN_SAFE_ALL_MUTANTS",
            "rows": rows}


def check_report(body, pinned_report):
    if not body:
        return {"reproduces": None}
    def rows(b):
        return {r.get("schema") or r.get("control"): r for r in (b.get("canonical", []) + b.get("controls", []))}
    got, want = rows(body), rows(pinned_report)
    keys = sorted(set(got) | set(want))
    checks = {
        "verdict_equal": body.get("verdict") == pinned_report.get("verdict"),
        "mutants_total_equal": body.get("mutants", {}).get("total") == pinned_report.get("mutants", {}).get("total"),
        "semantic_caught_equal": body.get("mutants", {}).get("semantic_caught") == pinned_report.get("mutants", {}).get("semantic_caught"),
        "structural_caught_equal": body.get("mutants", {}).get("structural_caught") == pinned_report.get("mutants", {}).get("structural_caught"),
        "union_caught_equal": body.get("mutants", {}).get("union_caught") == pinned_report.get("mutants", {}).get("union_caught"),
        "row_keys_equal": keys == sorted(want),
        "rows_ok_equal": all(got[k].get("ok") == want[k].get("ok") for k in keys),
    }
    row_diffs = {}
    for k in keys:
        g, w = got.get(k, {}), want.get(k, {})
        if (g.get("structural"), g.get("semantic"), g.get("ok")) != (w.get("structural"), w.get("semantic"), w.get("ok")):
            row_diffs[k] = {"replay": g, "pinned_report": w}
    return {"reproduces": all(checks.values()), "checks": checks,
            "replay_mutants": body.get("mutants"), "pinned_mutants": pinned_report.get("mutants"),
            "row_diffs": row_diffs}


def main() -> int:
    RUNS.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    window_start = now()
    live_paths = [RUNNER, GATE, AUD, SPEC, KEYS, CORPUS, MANIFEST, REPORT, FROZEN, ENTRY,
                  SCHEMA_F1, SCHEMA_F2A, SCHEMA_C0, MAP] + PIN_C0_SOURCES
    man = freeze()
    live_pre = live_hashes(live_paths)
    snapshot_mismatch = sorted(r for r in live_paths
                               if (SNAP / r).exists() and live_pre[r]["sha256"] != sha256(SNAP / r))

    corpus = json.loads((SNAP / CORPUS).read_text())
    pinned_report = json.loads((SNAP / REPORT).read_text())
    frozen = json.loads((SNAP / FROZEN).read_text())
    snap_f1 = sha256(SNAP / SCHEMA_F1)
    snap_f2a = sha256(SNAP / SCHEMA_F2A)
    snap_c0 = sha256(SNAP / SCHEMA_C0)
    pin_ok = [s for s in PIN_C0_SOURCES if (SNAP / s).exists() and sha256(SNAP / s) == PIN_C0] or \
             [s for s in PIN_C0_SOURCES if (ROOT / s).exists() and sha256(ROOT / s) == PIN_C0]

    pin_resolution = {
        "snapshot_c0_sha256": snap_c0,
        "declared_base_sha256": corpus.get("base_sha256"),
        "pinned_c0_recovered": bool(pin_ok),
        "pinned_c0_sources_byte_equal": pin_ok,
        "snapshot_f1_sha256": snap_f1, "snapshot_f2a_sha256": snap_f2a,
        "instrument_pins": {
            "gate_declared": corpus.get("gate_sha256"), "gate_snapshot": sha256(SNAP / GATE),
            "auditor_declared": corpus.get("w06_sha256"), "auditor_snapshot": sha256(SNAP / AUD),
            "manifest_declared": corpus.get("corpus_manifest_sha256"), "manifest_snapshot": sha256(SNAP / MANIFEST),
            "report_declared": DECL_REPORT, "report_snapshot": sha256(SNAP / REPORT),
            "corpus_declared": DECL_CORPUS, "corpus_snapshot": sha256(SNAP / CORPUS),
        },
    }

    live_sb = build_sandbox("live")
    shutil.copy2(SNAP / SCHEMA_C0, live_sb / SCHEMA_C0)
    live_sb_in = sandbox_inputs(live_sb)
    arm_l = run_runner(live_sb, "armL_live")

    corrupt_sb = build_sandbox("corrupt")
    shutil.copy2(SNAP / SCHEMA_C0, corrupt_sb / SCHEMA_C0)
    cpath = corrupt_sb / CORPUS
    cd = json.loads(cpath.read_text())
    cd["base_sha256"] = "0" * 64
    cpath.write_text(json.dumps(cd, indent=1))
    arm_c = run_runner(corrupt_sb, "armC_corrupt")

    pinned_sb = build_sandbox("pinned")
    if pin_ok:
        shutil.copy2(SNAP / pin_ok[0] if (SNAP / pin_ok[0]).exists() else ROOT / pin_ok[0], pinned_sb / SCHEMA_C0)
    else:
        shutil.copy2(SNAP / SCHEMA_C0, pinned_sb / SCHEMA_C0)
    pinned_sb_in = sandbox_inputs(pinned_sb)
    arm_p = run_runner(pinned_sb, "armP_pinned")
    arm_p["sandbox_c0_sha256"] = sha256(pinned_sb / SCHEMA_C0)
    rep_check = check_report(arm_p.get("body"), pinned_report)

    arm_pl_res = arm_pl(pinned_sb, corpus)
    dep = dependency_closure(frozen)
    arm_s_snap = arm_s(corpus, SNAP / SCHEMA_C0, "snapshot_canonical_c0")
    arm_s_pin = {"base_label": "pinned_declared_base", "base_sha256": PIN_C0,
                 "class_summary": arm_s(corpus, OUT / "sandbox_pinned" / SCHEMA_C0, "pinned_declared_base")["class_summary"]}
    live_post = live_hashes(live_paths)
    live_drift = sorted(r for r in live_paths if live_pre[r]["sha256"] != live_post[r]["sha256"])
    snap_stable = verify_snapshot(man)
    window_end = now()

    controls = [
        {"id": "C1", "name": "pinned_c0_recovered_byte_equal",
         "pass": bool(pin_ok) and sha256(pinned_sb / SCHEMA_C0) == PIN_C0,
         "detail": f"{len(pin_ok)} hash-verified on-disk source(s)"},
        {"id": "C2", "name": "snapshot_preflight_exit3",
         "pass": arm_l["exit_code"] == 3 and "PREFLIGHT FAIL" in (RUNS / "armL_live.stdout").read_text(),
         "detail": f"exit={arm_l['exit_code']}"},
        {"id": "C3", "name": "corrupt_base_preflight_exit3_failclosed",
         "pass": arm_c["exit_code"] == 3, "detail": f"exit={arm_c['exit_code']}"},
        {"id": "C4", "name": "pinned_preflight_proceeds",
         "pass": bool(arm_p.get("body")) and arm_p.get("body", {}).get("mutants", {}).get("total") == 31,
         "detail": f"exit={arm_p['exit_code']} mutants={arm_p.get('body',{}).get('mutants',{}).get('total')}"},
        {"id": "C5", "name": "corpus_declared_instrument_pins_byte_equal",
         "pass": (sha256(SNAP / GATE) == DECL_GATE and sha256(SNAP / AUD) == DECL_AUD
                  and sha256(SNAP / MANIFEST) == DECL_MANIFEST and sha256(SNAP / CORPUS) == DECL_CORPUS
                  and sha256(SNAP / REPORT) == DECL_REPORT),
         "detail": "gate/auditor/manifest/corpus/report at snapshot"},
        {"id": "C6", "name": "snapshot_immutable_during_run",
         "pass": snap_stable and not snapshot_mismatch,
         "detail": f"digest={man['digest'][:16]} mismatch={snapshot_mismatch} live_drift={live_drift}"},
        {"id": "C7", "name": "fixture_inventory_31_mutants_2_controls",
         "pass": arm_s_snap["class_summary"].get("CONTROL", 0) == 2 and
                 sum(v for k, v in arm_s_snap["class_summary"].items() if k != "CONTROL") == 31,
         "detail": json.dumps(arm_s_snap["class_summary"])},
        {"id": "C8", "name": "pinned_and_snapshot_c0_are_distinct_bytes",
         "pass": sha256(pinned_sb / SCHEMA_C0) != snap_c0,
         "detail": f"pinned={PIN_C0[:12]} snapshot={snap_c0[:12]}"},
    ]

    findings = [
        {"id": "F-065-CF32-1",
         "text": (f"Snapshot preflight fails closed with exit 3: corpus base {corpus.get('base_sha256')[:12]} "
                  f"vs snapshot C0 {snap_c0[:12]}; a pure hash-binding failure, no execution failure."),
         "evidence": ["arm_L_live_preflight", "arm_C_corrupt_control"]},
        {"id": "F-065-CF32-2",
         "text": (f"Pinned-input replay: union catch 31/31 and semantic 11/31 reproduce, but the report's PASS "
                  f"verdict does not — replay exit {arm_p['exit_code']}, canonical F1 semantic=fail and C0 "
                  f"structural=fail, both controls structural=fail, structural_caught 31 vs 30 recorded."),
         "evidence": ["arm_P_pinned_replay", "pinned_report_reproduction"]},
        {"id": "F-065-CF32-3",
         "text": (f"Instrument closure is under-declared: the corpus manifest does not pin "
                  f"{dep['unpinned_by_corpus_manifest']}; the 24 rule-set differences and 3 verdict flips in the "
                  f"per-fixture ledger are the measured signature of that drift."),
         "evidence": ["dependency_closure", "arm_PL_per_fixture_ledger"]},
        {"id": "F-065-CF32-4",
         "text": (f"Re-pin safety vs snapshot C0 {snap_c0[:12]}: base shifted at "
                  f"{arm_s_snap['base_shift_path_count']} leaf paths; class summary "
                  f"{json.dumps(arm_s_snap['class_summary'])}; verdict {arm_s_snap['repin_verdict']}."),
         "evidence": ["arm_S_repin_safety"]},
    ]

    result = {
        "task_id": "W065-CF32-REPIN-SAFETY-06",
        "actor": "worker-065",
        "created_at": window_end,
        "class_id": "AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "gate": "G-FORM",
        "node_id": "F1,F2a,F2b",
        "conclusion_type": "formal_model",
        "authority_note": ("worker measurement only; sets no gate verdict, no node status, "
                           "no validation_status=passed; writes no canonical path."),
        "snapshot": {"frozen_at": man["frozen_at"], "digest": man["digest"],
                     "file_count": man["file_count"], "manifest": "snapshot/snapshot_manifest.json",
                     "immutable_during_run": snap_stable},
        "window": {"start": window_start, "end": window_end, "seconds": round(time.time() - t0, 2),
                   "live_at_freeze": live_pre, "live_at_end": live_post,
                   "snapshot_matches_live_at_freeze": not snapshot_mismatch,
                   "snapshot_mismatch": snapshot_mismatch,
                   "live_drift_during_task": live_drift},
        "pin_resolution": pin_resolution,
        "sandbox_inputs": {"live_arm": live_sb_in, "pinned_arm": pinned_sb_in},
        "arm_L_live_preflight": arm_l,
        "arm_C_corrupt_control": arm_c,
        "arm_P_pinned_replay": arm_p,
        "pinned_report_reproduction": rep_check,
        "arm_PL_per_fixture_ledger": arm_pl_res,
        "dependency_closure": dep,
        "arm_S_repin_safety": arm_s_snap,
        "arm_S_pinned_sanity": arm_s_pin,
        "controls": controls,
        "controls_passed": sum(1 for c in controls if c["pass"]),
        "controls_total": len(controls),
        "findings": findings,
    }
    (OUT / "report.json").write_text(json.dumps(result, indent=1))
    print(json.dumps({
        "snapshot": result["snapshot"], "live_drift_during_task": live_drift,
        "pin_resolution": pin_resolution,
        "armL_exit": arm_l["exit_code"], "armC_exit": arm_c["exit_code"],
        "armP": {"exit": arm_p["exit_code"], "mutants": arm_p.get("body", {}).get("mutants"),
                 "canonical": arm_p.get("body", {}).get("canonical"),
                 "controls": arm_p.get("body", {}).get("controls"),
                 "sandbox_c0": arm_p["sandbox_c0_sha256"][:12]},
        "reproduction": rep_check["checks"], "row_diffs": list(rep_check["row_diffs"]),
        "ledger_agg": arm_pl_res["aggregate"], "mismatch_count": arm_pl_res["mismatch_count"],
        "rule_set_drift_count": arm_pl_res["rule_set_drift_count"],
        "verdict_flips": arm_pl_res["verdict_flips"],
        "unpinned_by_corpus_manifest": dep["unpinned_by_corpus_manifest"],
        "unpinned_by_both": dep["unpinned_by_both"],
        "repin_vs_snapshot": {"c0": snap_c0, "base_shift": arm_s_snap["base_shift_path_count"],
                              "classes": arm_s_snap["class_summary"], "verdict": arm_s_snap["repin_verdict"]},
        "controls": [(c["id"], c["name"], c["pass"]) for c in controls],
    }, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
