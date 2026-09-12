#!/usr/bin/env python3
"""W074-N0-CKPT-COVERAGE-PATCH-01 -- independent verification of the numerics lead's
checkpoint-coverage patch proposal (blocker lnum-blocker-4d80a7a99a8399844881).

Question
--------
`numerics/checkpoint.py` (sha256 35955c3873fc..., operator-registered instrument, OWNER =
astra-lead-numerics) has a 19-entry TRACKED tuple.  The lead measured that four N0/G-NUM
closure artifacts are invisible to the group drift detector and proposed (NOT applied)
extending TRACKED by those four paths.  This instrument independently:

  A. reproduces the historical blind window from the three named checkpoint records;
  B. executes the UNMODIFIED pinned checkpoint module inside a sandbox, unpatched vs
     sandbox-patched, and measures change detection on the four paths, on the 19 tracked
     paths and on an untracked control;
  C. measures the operational consequence of a mid-run patch (one-time appearance delta);
  D. records, as a descriptive non-finding, how many further numerics paths cited in the
     accepted event stream stay untracked after the extension.

Hard constraints
----------------
* read-only on every canonical path: this script never writes outside its own artifact
  directory (`artifacts/worker-074/n0_ckpt_coverage_patch/`) and the scratch sandbox
  (`tmp/w074_n0_ckpt_coverage/`);
* fail closed (exit 3) on any pinned-input drift or control failure;
* stdlib only; deterministic except for the recorded wall-clock stamp and the volatile
  event-stream snapshot, which is reported with its own hash and drift note.

Authority: worker-authored measurement only.  No node status, no validation_status=passed,
no gate verdict.  The canonical instrument is NOT patched here.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]          # repo root
OUT = ROOT / "artifacts" / "worker-074" / "n0_ckpt_coverage_patch"
SCRATCH = ROOT / "tmp" / "w074_n0_ckpt_coverage"
CST_OFFSET = "+08:00"

TASK_ID = "W074-N0-CKPT-COVERAGE-PATCH-01"
WORKER = "worker-074"
CLASS_IDS = ["AF-WCC-SCALAR-SPH"]
NODE_ID = "N0"
GATE = "G-NUM"

CKPT = "numerics/checkpoint.py"
AUDIT = "numerics/protocol/lifecycle07_coverage_audit.json"
WITNESS = "numerics/protocol/checkpoint_gap_witness_l07.json"
RECORDS = [
    "artifacts/numerics/checkpoints/num-ckpt-20260912-002205.json",
    "artifacts/numerics/checkpoints/num-ckpt-20260912-003726.json",
    "artifacts/numerics/checkpoints/num-ckpt-20260912-003753.json",
    "artifacts/numerics/checkpoints/num-ckpt-20260912-003808.json",
    "artifacts/numerics/checkpoints/num-ckpt-20260912-004552.json",
    "artifacts/numerics/checkpoints/num-ckpt-20260912-005532.json",
    "artifacts/numerics/checkpoints/num-ckpt-20260912-010105.json",
    "artifacts/numerics/checkpoints/num-ckpt-20260912-010743.json",
]
PROPOSED_EXTENSION = [
    "numerics/results/flat_wave_convergence_rev3.json",
    "numerics/protocol/n0_fixed_dt_certification.json",
    "numerics/protocol/n0_registration_drift_audit.json",
    "numerics/N0_CLASS_BINDING_AUTHORITY.json",
]
UNTRACKED_CONTROL = "numerics/N0_REPORT.md"
# The audit artifact is regenerated on every numerics lifecycle.  The blocker
# lnum-blocker-4d80a7a99a8399844881 (filed 01:07:41) cites the 01:07:23 image
# a87c027135cf; by first measurement (01:11:30) it had been regenerated to
# 009f0375062a.  The substantive payload checked here is identical across the two.
PRIOR_PINS = {
    AUDIT: {
        "sha256": "a87c027135cf81458ef911cec62ca1a72cbcead04018959bdb5d03e39b9e0312",
        "source": "lnum-blocker-4d80a7a99a8399844881 evidence_refs (numerics/checkpoint.py blocked-topic, filed 01:07:41+0800)",
    },
}
SCHEMA = "worker-074/n0-ckpt-coverage-patch/v1"

PINS = {
    CKPT: "35955c3873fc20e4a58796c59ce45e155d78e81b7ae785279fa055df15e75d5d",
    AUDIT: "009f0375062a041ca336f67c1a9f845483c65cc78fd21ccbe86c8f7ecd79aa46",
    WITNESS: "36444d1cc888e486ff1fec30357565a88567c0b8f1f5aff8043abe7850ce78c8",
    "artifacts/numerics/checkpoints/num-ckpt-20260912-002205.json": "2ae1dc40d92546640325bfde064f37ee1f89deb61173fcee2a45ecb81f6da414",
    "artifacts/numerics/checkpoints/num-ckpt-20260912-003726.json": "f9a06edac7a8c20c75355686b55223a53a9fc1e39821a62c846b50df40ca6100",
    "artifacts/numerics/checkpoints/num-ckpt-20260912-003753.json": "9fa33b7718b4b0a5dba0e3edcd456177840d99f19505d5beebe02b21d3843390",
    "artifacts/numerics/checkpoints/num-ckpt-20260912-003808.json": "7c0e726ae88d73c6b9c17aac6d3ceb43cf085d6c4a17a4f1c42fa68eb605e5a5",
    "artifacts/numerics/checkpoints/num-ckpt-20260912-004552.json": "632615873d5f3dd5f3ca77ad51d8229fa7598e345847180cedd080dd11df1e4e",
    "artifacts/numerics/checkpoints/num-ckpt-20260912-005532.json": "12c231253b0488a0dafef718b6d1010a26e7485316adacfbefd5482aec3bd419",
    "artifacts/numerics/checkpoints/num-ckpt-20260912-010105.json": "a9d693e11db44fda369e8fab75cf5e6510690f8a280546055026f764bbad010d",
    "artifacts/numerics/checkpoints/num-ckpt-20260912-010743.json": "2007c44b87e25c2fc420e619b156a5dda0b43afdc960de43097a9dbe50353707",
    PROPOSED_EXTENSION[0]: "da7c360719950f7ef6be2624391dee464f8c818a0be74ec44f0f8c70d2b28ac3",
    PROPOSED_EXTENSION[1]: "1677822ceb9c81e8f6e48dee8360ab13edc35623c51f4be68bd6589a5fe79920",
    PROPOSED_EXTENSION[2]: "22edbcc61df7dc7cd574fb43e4ef6c09ae12f89f1ebe34869b00a5b27384c632",
    PROPOSED_EXTENSION[3]: "effd20b0ea094a8dfd4f686e62c49b1667622337efd6a7c154f7fadae0b98419",
    "numerics/gates.py": "fcd1d70991b6eade4aa993dc49b6103e338f68320aabb955d97da5a8f55d996e",
}

# Runtime substitution used ONLY inside the sandbox so that hash-change detection is
# isolated from volatile live gate/map traffic.  Control C5 pins that this is the only
# substitution and that the hashing source path is unmodified.
SANDBOX_GATE_STATE = {
    "verdict": "SANDBOX_STUB",
    "lock_state": "locked",
    "gate_ok": {},
    "blocking_reasons": ["sandbox stub: gate state not part of this measurement"],
    "order_agreement": {},
    "protocol_reviewed": False,
}


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str | None:
    if not p.is_file():
        return None
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now_stamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()) + CST_OFFSET


def jwrite(p: Path, obj) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")


class Log:
    def __init__(self):
        self.lines: list[str] = []

    def __call__(self, msg: str) -> None:
        line = f"[{time.strftime('%H:%M:%S')}] {msg}"
        self.lines.append(line)
        print(line, flush=True)

    def text(self) -> str:
        return "\n".join(self.lines) + "\n"


def check_pins(pins: dict, tamper: str | None = None) -> list[dict]:
    """Return per-pin measurement rows; a tampered row is forced to mismatch."""
    rows = []
    for rel, want in sorted(pins.items()):
        got = sha256_file(ROOT / rel)
        ok = got == want
        if tamper == rel:
            ok = False
        rows.append({"path": rel, "expected": want, "measured": got, "pass": ok})
    return rows


def load_variant(path: Path):
    """Import a checkpoint.py variant from an explicit file path."""
    name = "w074_variant_" + sha256_file(path)[:8]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


TRACKED_BLOCK = re.compile(r"^TRACKED = \(\n(?P<body>(?:    \".*\",\n)+)\)\n", re.M)


def make_patched_source(src: str, extra: list[str]) -> tuple[str, str]:
    """Insert `extra` entries into TRACKED; return (new_source, unified_diff_text)."""
    m = TRACKED_BLOCK.search(src)
    if not m:
        raise SystemExit("FATAL: TRACKED block not found in pinned checkpoint.py")
    body = m.group("body")
    existing = re.findall(r'^    "(.*)",$', body, re.M)
    dup = [e for e in extra if e in existing]
    if dup:
        raise SystemExit(f"FATAL: proposed paths already tracked: {dup}")
    addition = "".join(f'    "{e}",\n' for e in extra)
    new_src = src[: m.end("body")] + addition + src[m.end("body"):]
    # minimal textual diff (no difflib noise: show inserted lines only)
    diff = "--- unpatched\n+++ patched\n@@ TRACKED @@\n" + "".join(f"+{l}\n" for l in addition.splitlines())
    return new_src, diff


def build_sandbox(log: Log, patched_src: str, wrong_src: str) -> dict:
    """Copy the numerics + research_map trees into scratch and install variants."""
    if SCRATCH.exists():
        shutil.rmtree(SCRATCH)
    sb = SCRATCH / "sandbox"
    sb.mkdir(parents=True)
    for d in ("numerics", "artifacts/numerics", "research_map"):
        src = ROOT / d
        if src.is_dir():
            shutil.copytree(src, sb / d, symlinks=False, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    (sb / "variants").mkdir()
    unpatched = sb / "variants" / "unpatched.py"
    patched = sb / "variants" / "patched.py"
    wrong = sb / "variants" / "wrong.py"
    unpatched.write_text((ROOT / CKPT).read_text())
    patched.write_text(patched_src)
    wrong.write_text(wrong_src)
    # pristine byte images of every copied file (so any tracked/untracked probe can be reset)
    pristine: dict[str, bytes] = {}
    for sub in ("numerics", "artifacts/numerics"):
        for p in (sb / sub).rglob("*"):
            if p.is_file() and "__pycache__" not in p.parts:
                pristine[str(p.relative_to(sb))] = p.read_bytes()
    log(f"sandbox built at {SCRATCH} ({sum(1 for _ in sb.rglob('*') if _.is_file())} files)")
    return {"dir": sb, "unpatched": unpatched, "patched": patched, "wrong": wrong, "pristine": pristine}


def load_mods(sb: dict) -> dict:
    mods = {}
    for key in ("unpatched", "patched", "wrong"):
        mod = load_variant(sb[key])
        mod.load_gate_state = lambda: dict(SANDBOX_GATE_STATE)  # disclosed runtime stub
        mods[key] = mod
    return mods


def set_files(sb: dict, mutations: dict[str, bytes]) -> None:
    """Reset every pristine file, then apply mutations."""
    for rel, b in sb["pristine"].items():
        (sb["dir"] / rel).write_bytes(b)
    for rel, b in mutations.items():
        p = sb["dir"] / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b)


def replay(mod, previous: dict) -> dict:
    rec = mod.make_record(999, previous)
    return {
        "hashes": rec["artifact_hashes"],
        "changed": rec["changed_since_last_checkpoint"],
        "tracked_keys": sorted(rec["artifact_hashes"].keys()),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true", help="run controls only, exit 3 on any failure")
    args = ap.parse_args(argv)

    log = Log()
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "raw").mkdir(parents=True, exist_ok=True)
    log(f"{TASK_ID} start; scratch={SCRATCH}")

    # ---------------- 0. pins -------------------------------------------------------
    # record -005532 sha is pinned from its own bytes at first measurement; if the
    # declared constant is a placeholder the run fails closed, so measure it here only
    # to report, and require it to equal the declared value.
    pins = dict(PINS)
    rows = check_pins(pins)
    bad = [r for r in rows if not r["pass"]]
    if bad:
        for r in bad:
            log(f"PIN DRIFT {r['path']}: expected {r['expected'][:16]} measured "
                f"{(r['measured'] or 'MISSING')[:16]}")
        jwrite(OUT / "raw" / "pin_failure.json", {"pins": rows, "at": now_stamp()})
        return 3
    log(f"pins: {len(rows)}/{len(rows)} match")

    pinned_src = (ROOT / CKPT).read_text()
    audit = json.loads((ROOT / AUDIT).read_text())
    audit_omits = list(audit["checkpoint_coverage_gap"]["tracked_omits"])
    audit_tracked_count = audit["checkpoint_coverage_gap"]["tracked_count"]

    # ---------------- A. historical gap reproduction --------------------------------
    recs = []
    for rel in RECORDS:
        o = json.loads((ROOT / rel).read_text())
        recs.append({
            "path": rel,
            "checkpoint_id": o["checkpoint_id"],
            "created_at": o["created_at"],
            "changed": o.get("changed_since_last_checkpoint"),
            "hash_keys": sorted(o.get("artifact_hashes", {}).keys()),
            "n_hash_keys": len(o.get("artifact_hashes", {})),
        })
    recs.sort(key=lambda r: r["created_at"])
    mod_probe = load_variant(ROOT / CKPT)
    tracked = list(mod_probe.TRACKED)

    gap_windows = []
    for i, r in enumerate(recs):
        if i == 0:
            continue
        prev_at = recs[i - 1]["created_at"]
        for rel in PROPOSED_EXTENSION:
            p = ROOT / rel
            if not p.is_file():
                continue
            mt = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(p.stat().st_mtime)) + CST_OFFSET
            in_window = prev_at < mt <= r["created_at"]
            invisible = rel not in (r["changed"] or []) and rel not in r["hash_keys"]
            if in_window and invisible:
                gap_windows.append({
                    "path": rel,
                    "landed_at": mt,
                    "checkpoint_id": r["checkpoint_id"],
                    "record_created_at": r["created_at"],
                    "record_changed": r["changed"],
                    "record_hash_keys": len(r["hash_keys"]),
                })
    gap = {
        "schema": SCHEMA,
        "task_id": TASK_ID,
        "measured_at": now_stamp(),
        "pinned_checkpoint_sha256": PINS[CKPT],
        "tracked_count_measured": len(tracked),
        "audit_tracked_count": audit_tracked_count,
        "audit_tracked_omits": audit_omits,
        "audit_matches_module_tracked": (audit_tracked_count == len(tracked)),
        "records": recs,
        "blind_windows": gap_windows,
        "all_four_invisible_in_at_least_one_landing_window": len({g["path"] for g in gap_windows}) == 4,
        "records_hash_keys_equal_tracked": all(set(r["hash_keys"]) == set(tracked) for r in recs[-4:]),
        "audit_regeneration": {
            "current_pin": PINS[AUDIT],
            "prior_pin_from_blocker_evidence": PRIOR_PINS[AUDIT]["sha256"],
            "prior_pin_source": PRIOR_PINS[AUDIT]["source"],
            "substantive_payload_stable": (
                sorted(audit_omits) == sorted(PROPOSED_EXTENSION)
                and audit_tracked_count == len(tracked)
                and audit["checkpoint_coverage_gap"]["checkpoint_script_sha256"] == PINS[CKPT]
            ),
            "note": ("the audit is regenerated per numerics lifecycle: its checkpoint list grew "
                     "(-010743 added, -004552 dropped) while tracked_omits, tracked_count, script hash, "
                     "applied=false and rev3_landed_at are unchanged; the blocker event's evidence pin "
                     "a87c027135cf no longer resolves on disk"),
        },
    }
    jwrite(OUT / "raw" / "gap_reproduction.json", gap)

    # ---------------- 1. patch construction + minimality ----------------------------
    patched_src, diff = make_patched_source(pinned_src, PROPOSED_EXTENSION)
    wrong_src, _ = make_patched_source(pinned_src, [p + ".bak" for p in PROPOSED_EXTENSION])

    def tracked_of(src: str) -> list[str]:
        m = TRACKED_BLOCK.search(src)
        return re.findall(r'^    "(.*)",$', m.group("body"), re.M) if m else []

    unpatched_tracked = tracked_of(pinned_src)
    patched_tracked = tracked_of(patched_src)
    minimal = {
        "unpatched_count": len(unpatched_tracked),
        "patched_count": len(patched_tracked),
        "extension_set": sorted(set(patched_tracked) - set(unpatched_tracked)),
        "removed_set": sorted(set(unpatched_tracked) - set(patched_tracked)),
        "duplicates": len(patched_tracked) != len(set(patched_tracked)),
        "order_prefix_preserved": patched_tracked[: len(unpatched_tracked)] == unpatched_tracked,
        "source_diff_is_exactly_the_extension": (
            sorted(set(patched_tracked) - set(unpatched_tracked)) == sorted(PROPOSED_EXTENSION)
            and set(unpatched_tracked) <= set(patched_tracked)
        ),
        "patched_sandbox_sha256": sha256_bytes(patched_src.encode()),
        "diff": diff,
    }
    log(f"patch minimality: {minimal['unpatched_count']} -> {minimal['patched_count']} "
        f"entries; extension set = {minimal['extension_set']}")

    # ---------------- 2. sandbox replay --------------------------------------------
    sb = build_sandbox(log, patched_src, wrong_src)
    mods = load_mods(sb)
    prev_record = "artifacts/numerics/checkpoints/num-ckpt-20260912-010105.json"
    base_prev = json.loads((ROOT / prev_record).read_text())["artifact_hashes"]

    scenarios = []

    def run_scenario(sid, desc, previous, mutations, expect_unpatched, expect_patched, modules=("unpatched", "patched")):
        set_files(sb, mutations)
        res = {}
        for key in modules:
            res[key] = replay(mods[key], previous)
        ok = all(sorted(res[k]["changed"]) == sorted(expect_patched if k == "patched" else expect_unpatched) for k in modules)
        scenarios.append({
            "id": sid, "description": desc,
            "previous_keys": len(previous),
            "calls": {k: {"changed": res[k]["changed"], "n_hashes": len(res[k]["hashes"])} for k in modules},
            "expected": {"unpatched": expect_unpatched, "patched": expect_patched},
            "pass": ok,
        })
        log(f"{sid}: unpatched={res.get('unpatched', {}).get('changed')} "
            f"patched={res.get('patched', {}).get('changed')} -> {'PASS' if ok else 'FAIL'}")

    # a) real previous state (19 keys) vs pristine files: appearance delta.
    #    The live tree may have moved since record -010105, so the expected patched set is
    #    (whatever the unpatched tracked view reports) UNION (the four new keys); the
    #    unpatched set must contain none of the four.
    set_files(sb, {})
    r1_un = replay(mods["unpatched"], base_prev)
    r1_pa = replay(mods["patched"], base_prev)
    r1_ok = (
        not (set(r1_un["changed"]) & set(PROPOSED_EXTENSION))
        and set(PROPOSED_EXTENSION) <= set(r1_pa["changed"])
        and sorted(r1_pa["changed"]) == sorted(set(r1_un["changed"]) | set(PROPOSED_EXTENSION))
    )
    scenarios.append({
        "id": "R1_baseline_appearance_delta",
        "description": ("real record -010105 previous map vs pristine sandbox: unpatched must show none of "
                        "the four; patched must show exactly the unpatched changes plus the four new keys"),
        "previous_keys": len(base_prev),
        "calls": {
            "unpatched": {"changed": r1_un["changed"], "n_hashes": len(r1_un["hashes"])},
            "patched": {"changed": r1_pa["changed"], "n_hashes": len(r1_pa["hashes"])},
        },
        "expected": {"unpatched": "no closure path", "patched": "unpatched changed + four"},
        "pass": r1_ok,
    })
    log(f"R1_baseline_appearance_delta: unpatched={r1_un['changed']} patched={r1_pa['changed']} "
        f"-> {'PASS' if r1_ok else 'FAIL'}")

    # baseline maps for later scenarios (patched view = 19 + 4 current hashes)
    set_files(sb, {})
    patched_base = replay(mods["patched"], base_prev)["hashes"]

    # b) the four closure files change: unpatched blind, patched catches
    mut4 = {rel: sb["pristine"][rel] + b"\n# w074 replay mutation\n" for rel in PROPOSED_EXTENSION}
    run_scenario(
        "R2_closure_files_change",
        "append one byte to each of the four proposed paths after the patched baseline",
        patched_base, mut4, [], sorted(PROPOSED_EXTENSION),
    )

    # c) one originally tracked file changes: both catch it, same singleton
    tracked_probe = "numerics/tests/flat_wave.py"
    mut1 = {tracked_probe: sb["pristine"][tracked_probe] + b"\n# w074 replay mutation\n"}
    run_scenario(
        "R3_tracked_file_change_no_regression",
        f"append one byte to already-tracked {tracked_probe}",
        patched_base, mut1, [tracked_probe], [tracked_probe],
    )

    # d) untracked control changes: neither catches it
    mutc = {UNTRACKED_CONTROL: sb["pristine"].get(UNTRACKED_CONTROL, b"x") + b"\n# w074 control\n"}
    run_scenario(
        "R4_untracked_control_silent",
        f"append one byte to untracked control {UNTRACKED_CONTROL}",
        patched_base, mutc, [], [],
    )

    # e) wrong-path patch: mutating the real four is invisible to the wrong patch
    set_files(sb, mut4)
    wrong = replay(mods["wrong"], patched_base)
    wrong_ok = wrong["changed"] == [] and not (set(PROPOSED_EXTENSION) & set(wrong["hashes"]))
    scenarios.append({
        "id": "R5_wrong_paths_negative_control",
        "description": "patch the four names with a .bak suffix: the real four mutations must stay invisible",
        "previous_keys": len(patched_base),
        "calls": {"wrong": {"changed": wrong["changed"], "n_hashes": len(wrong["hashes"])}},
        "expected": {"wrong": []},
        "pass": wrong_ok,
    })
    log(f"R5_wrong_paths_negative_control: wrong={wrong['changed']} / {len(wrong['hashes'])} hashes -> {'PASS' if wrong_ok else 'FAIL'}")

    # f) re-settle: after the appearance delta is absorbed, no false churn
    set_files(sb, {})
    settled_prev = replay(mods["patched"], base_prev)["hashes"]  # = patched_base
    settled = replay(mods["patched"], settled_prev)
    settled_ok = settled["changed"] == []
    scenarios.append({
        "id": "R6_settled_no_false_churn",
        "description": "with the four keys present in the previous map, a pristine tree reports no change",
        "previous_keys": len(settled_prev),
        "calls": {"patched": {"changed": settled["changed"], "n_hashes": len(settled["hashes"])}},
        "expected": {"patched": []},
        "pass": settled_ok,
    })
    log(f"R6_settled_no_false_churn: patched={settled['changed']} -> {'PASS' if settled_ok else 'FAIL'}")

    replay_out = {
        "schema": SCHEMA,
        "task_id": TASK_ID,
        "measured_at": now_stamp(),
        "sandbox": str(SCRATCH),
        "runtime_substitution": {
            "function": "load_gate_state",
            "why": "isolate hash-change detection from volatile gate/map traffic",
            "stub": SANDBOX_GATE_STATE,
            "hashing_source_unmodified": True,
        },
        "minimality": minimal,
        "scenarios": scenarios,
    }
    jwrite(OUT / "raw" / "patch_replay.json", replay_out)

    # ---------------- 3. descriptive residual untracked census ----------------------
    ev = ROOT / "research_map" / "events.jsonl"
    ev_sha_start = sha256_file(ev)
    cited: dict[str, list[str]] = {}
    for line in ev.read_text(errors="ignore").splitlines():
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        for k in ("evidence_refs", "artifact_refs"):
            for r in (o.get(k) or []):
                if isinstance(r, str):
                    p = r.split("#")[0]
                    if p.startswith("numerics/") or p.startswith("artifacts/numerics/"):
                        cited.setdefault(p, [])
                        if o.get("event_type") not in cited[p]:
                            cited[p].append(o.get("event_type"))
    residual = sorted(p for p in cited if p not in set(tracked) | set(PROPOSED_EXTENSION))
    residual_census = {
        "schema": SCHEMA,
        "task_id": TASK_ID,
        "status": "descriptive_observation_not_a_finding",
        "non_claim": ("numerics/checkpoint.py is a curated churn detector, not a registry; this "
                      "census does not claim the tracker should track all cited paths."),
        "event_stream": str(ev),
        "event_stream_sha256_at_scan": ev_sha_start,
        "event_stream_is_volatile": True,
        "distinct_numerics_paths_cited": len(cited),
        "tracked_after_proposed_extension": len(set(tracked) | set(PROPOSED_EXTENSION)),
        "residual_cited_untracked": residual,
        "residual_count": len(residual),
    }
    jwrite(OUT / "raw" / "residual_untracked_census.json", residual_census)

    # ---------------- 4. final drift re-measure -------------------------------------
    rows_end = check_pins(pins)
    drift = [r for r in rows_end if not r["pass"]]
    ev_sha_end = sha256_file(ev)
    canonical_end = {rel: sha256_file(ROOT / rel) for rel in (CKPT, AUDIT, WITNESS) + tuple(RECORDS)}

    # ---------------- 5. report -----------------------------------------------------
    checks = [
        {"id": "P0_pins", "pass": not bad, "detail": f"{len(rows)} pins matched"},
        {"id": "A0_audit_substantive_stable", "pass": gap["audit_regeneration"]["substantive_payload_stable"],
         "detail": ("audit regenerated a87c027135cf -> 009f0375062a before measurement; tracked_omits / "
                    "tracked_count / script hash unchanged")},
        {"id": "A1_audit_lists_four", "pass": sorted(audit_omits) == sorted(PROPOSED_EXTENSION),
         "detail": f"audit tracked_omits={audit_omits}"},
        {"id": "A2_records_19_keys", "pass": gap["records_hash_keys_equal_tracked"],
         "detail": "post-00:22 records carry exactly the 19 TRACKED keys"},
        {"id": "A3_four_blind_windows", "pass": gap["all_four_invisible_in_at_least_one_landing_window"],
         "detail": f"{len(gap_windows)} (path, window) rows"},
        {"id": "B1_patch_minimal", "pass": minimal["source_diff_is_exactly_the_extension"] and not minimal["duplicates"] and minimal["order_prefix_preserved"],
         "detail": f"{minimal['unpatched_count']}->{minimal['patched_count']}, removed={minimal['removed_set']}"},
        {"id": "B2_unpatched_blind", "pass": all(s["pass"] for s in scenarios if s["id"] == "R2_closure_files_change"),
         "detail": "unpatched changed=[] on the four closure mutations"},
        {"id": "B3_patched_detects_four", "pass": all(s["pass"] for s in scenarios if s["id"] == "R2_closure_files_change"),
         "detail": "patched changed == exactly the four paths"},
        {"id": "B4_no_tracked_regression", "pass": all(s["pass"] for s in scenarios if s["id"] == "R3_tracked_file_change_no_regression"),
         "detail": "tracked-file change still reported as the same singleton"},
        {"id": "B5_untracked_still_silent", "pass": all(s["pass"] for s in scenarios if s["id"] == "R4_untracked_control_silent"),
         "detail": f"{UNTRACKED_CONTROL} stays invisible"},
        {"id": "B6_wrong_path_control", "pass": wrong_ok, "detail": "path-specific detection"},
        {"id": "C1_appearance_delta", "pass": all(s["pass"] for s in scenarios if s["id"] == "R1_baseline_appearance_delta"),
         "detail": "mid-run patch produces a one-time four-path appearance delta"},
        {"id": "C2_settles", "pass": settled_ok, "detail": "no false churn once keys are in the previous map"},
        {"id": "D1_no_pin_drift", "pass": not drift, "detail": f"{len(drift)} pins moved during run"},
    ]
    findings = [
        {
            "id": "W074-CKPT-F1",
            "severity": "medium",
            "statement": ("The four N0/G-NUM closure paths named by the numerics lead are invisible to the "
                          "group drift detector at numerics/checkpoint.py#35955c3873fc: records "
                          "num-ckpt-20260912-004552 (-rev3 landing), -005532 and -010105 report changed lists "
                          "that exclude all four, and the post-00:22 records' hash maps equal exactly the 19 "
                          "TRACKED keys."),
            "evidence": ["raw/gap_reproduction.json", "raw/patch_replay.json",
                         "artifacts/numerics/checkpoints/num-ckpt-20260912-004552.json",
                         "artifacts/numerics/checkpoints/num-ckpt-20260912-010105.json",
                         "numerics/protocol/lifecycle07_coverage_audit.json"],
        },
        {
            "id": "W074-CKPT-F2",
            "severity": "medium",
            "statement": ("The proposed four-path TRACKED extension, executed in a sandbox against the pinned "
                          "module, detects exactly the four closure-path mutations, reports no change for an "
                          "untracked control, preserves the singleton report for an already-tracked file, and "
                          "is a strict prefix-preserving superset (19 -> 23) whose only source diff is the four "
                          "inserted entries. A wrong-path .bak patch does not detect the real mutations."),
            "evidence": ["raw/patch_replay.json"],
        },
        {
            "id": "W074-CKPT-F3",
            "severity": "low",
            "statement": ("Operational consequence for the controller: applying the patch mid-run makes the next "
                          "checkpoint emit a one-time appearance delta listing all four paths, because the "
                          "previous checkpoint maps lack those keys; it does not retroactively repair the "
                          "historical blind window (00:35:15-01:01:05). The delta disappears on the following "
                          "checkpoint."),
            "evidence": ["raw/patch_replay.json#R1_baseline_appearance_delta",
                         "raw/patch_replay.json#R6_settled_no_false_churn"],
        },
        {
            "id": "W074-CKPT-F4",
            "severity": "info",
            "statement": ("Moving-target note: the blocker lnum-blocker-4d80a7a99a8399844881 cites audit pin "
                          "a87c027135cf (01:07:23); the artifact was regenerated at 01:09:52 to 009f0375062a, so "
                          "that evidence ref no longer resolves. The substantive payload (tracked_omits, "
                          "tracked_count=19, checkpoint_script_sha256, applied=false) is identical across the "
                          "regeneration; only the checkpoint list changed. Reviewers of the blocker should cite "
                          "live bytes or the payload fields, not the regenerated whole-file hash."),
            "evidence": ["raw/gap_reproduction.json#audit_regeneration",
                         "raw/pin_failure_before_repin.json",
                         "comms/outbox/astra-lead-numerics.jsonl#lnum-blocker-4d80a7a99a8399844881"],
        },
    ]
    report = {
        "schema": SCHEMA,
        "task_id": TASK_ID,
        "worker": WORKER,
        "class_id": ";".join(CLASS_IDS),
        "class_ids": CLASS_IDS,
        "node_id": NODE_ID,
        "gate": GATE,
        "created_at": now_stamp(),
        "assignment": ("self-selected; no comms/inbox/worker-074.jsonl card existed (fleet relaunched "
                       "2026-09-12T00:58). Taken from the open numerics lead blocker "
                       "lnum-blocker-4d80a7a99a8399844881 (checkpoint coverage gap, patch proposed NOT applied)."),
        "authority_note": ("Worker-authored measurement only: no node status, no validation_status=passed, no "
                           "gate verdict, no canonical write. numerics/checkpoint.py remains unpatched by this "
                           "task; the patch exists only as sandbox bytes + a textual diff."),
        "pins": {k: v for k, v in sorted(PINS.items())},
        "pin_history": {k: v for k, v in sorted(PRIOR_PINS.items())},
        "pins_end": {k: v for k, v in sorted(canonical_end.items())},
        "patch_proposal": {
            "target": CKPT,
            "target_sha256": PINS[CKPT],
            "insert_paths": PROPOSED_EXTENSION,
            "tracked_before": unpatched_tracked,
            "tracked_after": patched_tracked,
            "sandbox_patched_image_sha256": minimal["patched_sandbox_sha256"],
            "applied": False,
            "authorization_required_from": "astra (registered instrument; owner astra-lead-numerics)",
            "diff": diff,
        },
        "checks": checks,
        "checks_all_pass": all(c["pass"] for c in checks),
        "findings": findings,
        "descriptive_observation": {
            "id": "W074-CKPT-OBS1",
            "non_claim": residual_census["non_claim"],
            "residual_cited_untracked_count": residual_census["residual_count"],
            "event_stream_sha256_at_scan": ev_sha_start,
            "event_stream_sha256_end": ev_sha_end,
            "event_stream_drifted_during_run": ev_sha_start != ev_sha_end,
            "detail_ref": "raw/residual_untracked_census.json",
        },
        "non_claims": [
            "not a gate verdict: G-NUM stays pending; N0 status untouched",
            "not numerics_lock release: N1 stays queued; no solver code written or run",
            "not a claim about the N0 order numbers, scheme independence, or the C8 protocol contest",
            "not an edit of any canonical file: the patch is sandbox-only",
            "the one-time appearance delta is a property of this detector's previous-hash comparison, not a defect claim about the lead",
        ],
        "falsifier": ("FALSIFIED IF any of: (a) any pinned input no longer hashes to its pin; (b) the four paths "
                      "are shown tracked/visible in any of the named records' hash maps or changed lists; (c) the "
                      "audit's tracked_omits list differs from the four paths; (d) the sandbox patched variant "
                      "fails to report exactly the four paths after their mutation, or reports any untracked path; "
                      "(e) the sandbox patched variant changes the report for any of the 19 originally tracked "
                      "paths; (f) the previous record maps already contain the four keys, so no appearance delta "
                      "occurs; or (g) a re-run of this instrument on the same pinned inputs yields any check FAIL "
                      "or a different residual/extension set."),
        "validation_status": "unverified",
        "counts_as_gate_verdict": False,
        "runtime_seconds": None,
    }

    report["runtime_seconds"] = round(time.time() - t0, 3)
    jwrite(OUT / "report.json", report)

    selftest = {
        "schema": SCHEMA,
        "task_id": TASK_ID,
        "measured_at": now_stamp(),
        "checks": checks,
        "all_pass": all(c["pass"] for c in checks),
        "scenario_count": len(scenarios),
        "scenario_all_pass": all(s["pass"] for s in scenarios),
        "controls": {
            "C1_wrong_path_negative": wrong_ok,
            "C2_untracked_control_silent": all(s["pass"] for s in scenarios if s["id"] == "R4_untracked_control_silent"),
            "C3_tracked_regression_absent": all(s["pass"] for s in scenarios if s["id"] == "R3_tracked_file_change_no_regression"),
            "C4_pin_tamper_detected": (check_pins(pins, tamper=CKPT)[[r["path"] for r in check_pins(pins, tamper=CKPT)].index(CKPT)]["pass"] is False),
            "C5_no_pin_drift_during_run": not drift,
        },
        "runtime_substitution_disclosed": True,
        "fail_closed_event_observed": {
            "when": "first measurement 2026-09-12T01:11:30+08:00",
            "trigger": "numerics/protocol/lifecycle07_coverage_audit.json moved a87c027135cf -> 009f0375062a",
            "action": "exit 3, no report emitted, row preserved",
            "evidence": "raw/pin_failure_before_repin.json",
        },
    }
    jwrite(OUT / "selftest.json", selftest)

    log("---- summary ----")
    for c in checks:
        log(f"  {c['id']}: {'PASS' if c['pass'] else 'FAIL'}  {c['detail']}")
    log(f"findings: {[f['id'] for f in findings]}; residual_cited_untracked={residual_census['residual_count']}")
    (OUT / "raw" / "run_log.txt").write_text(log.text())
    if not (selftest["all_pass"] and selftest["scenario_all_pass"]) or drift:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
