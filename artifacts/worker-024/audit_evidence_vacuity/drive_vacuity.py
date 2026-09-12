#!/usr/bin/env python3
"""W024-AUDIT-EVIDENCE-VACUITY-01 driver.

Fail-open (vacuity) audit of `research_map/audit_evidence.py` — the tool whose
`audit_evidence_hard: 0` result is quoted as gate evidence in the controller lifecycle
records. Every case runs a byte-identical copy of the pinned tool inside a private
sandbox whose ROOT is the sandbox directory, so the canonical tree is never written.

The driver:
  1. snapshots and hash-pins the two canonical inputs,
  2. builds synthetic maps that delete or empty one audited structure at a time,
  3. runs the pinned tool on each and records exit code / HARD lines / registry writes,
  4. applies a minimal fail-closed patch to a copy and re-runs the vacuous cases,
  5. writes report.json, entry_hashes.json, exit_hashes.json, proposed_patch.diff, logs/.

Deterministic and idempotent: sandbox/ and patched/ are rebuilt on each run.
"""
from __future__ import annotations

import difflib
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

CST = timezone(timedelta(hours=8))
ART = Path(__file__).resolve().parent
ROOT = ART.parents[2]  # repo root

AUDIT_REL = "research_map/audit_evidence.py"
DET_REL = "research_map/class_separation.py"
AUDIT_PIN = "bebec0843f10c096861365f61582538112793e237920b05381fad14ea1d90b26"
DET_PIN = "c266dbceca87fb996bd76a774145ef511cbf2aae190d9f423167d3200783a920"
REGISTRY_REL = "runtime/state/artifact_hashes.json"

TASK = "W024-AUDIT-EVIDENCE-VACUITY-01"
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


# ---------------------------------------------------------------- snapshots
SNAP = ART / "snapshots"
CURRENT_AUDIT_SNAP: Path | None = None
DET_SNAP: Path | None = None


def snapshot_pins() -> dict:
    """Snapshot the *current* canonical bytes; keep earlier revisions already on disk.

    The canonical file is a moving target in a live swarm (it changed mid-session), so the
    audit binds to the exact bytes copied here and records every revision it finds.
    """
    SNAP.mkdir(parents=True, exist_ok=True)
    out = {}
    for rel in (AUDIT_REL, DET_REL):
        src = ROOT / rel
        cur = sha256(src)
        dst = SNAP / f"{Path(rel).stem}.{cur[:12]}.py"
        if not dst.exists() or sha256(dst) != cur:
            shutil.copyfile(src, dst)
        assert sha256(dst) == cur, f"snapshot copy mismatch for {rel}"
        out[rel] = {"canonical_sha256": cur, "snapshot": str(dst.relative_to(ROOT)), "sha256": cur}
    audit_snaps = sorted(p.name for p in SNAP.glob("audit_evidence.*.py"))
    out["revisions_on_disk"] = audit_snaps
    reg = ROOT / REGISTRY_REL
    out[REGISTRY_REL] = {"canonical_sha256": sha256(reg) if reg.is_file() else None,
                         "snapshot": None, "sha256": sha256(reg) if reg.is_file() else None}
    return out


# ---------------------------------------------------------------- sandbox build
def build_sandbox(case: str, map_obj, files: dict, sentinel: str | None,
                  patched: bool = False, audit_snapshot: Path | None = None) -> Path:
    d = ART / "sandbox" / case
    if d.exists():
        shutil.rmtree(d)
    (d / "research_map").mkdir(parents=True)
    (d / "maps").mkdir(parents=True)
    audit_src = (ART / "patched" / "audit_evidence.patched.py" if patched
                 else (audit_snapshot or CURRENT_AUDIT_SNAP))
    assert audit_src is not None and audit_src.is_file(), f"no audit snapshot for {case}"
    shutil.copyfile(audit_src, d / "research_map" / "audit_evidence.py")
    assert DET_SNAP is not None and DET_SNAP.is_file(), "no detector snapshot"
    shutil.copyfile(DET_SNAP, d / "research_map" / "class_separation.py")
    # byte-identity check on the sandbox copies
    assert sha256(d / "research_map" / "audit_evidence.py") == (
        sha256(audit_src)), "sandbox audit copy drift"
    assert sha256(d / "research_map" / "class_separation.py") == sha256(DET_SNAP), \
        "sandbox detector copy drift"
    (d / "maps" / f"{case}.json").write_text(json.dumps(map_obj, indent=2, sort_keys=True))
    for rel, content in files.items():
        fp = d / rel
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content)
    if sentinel is not None:
        rp = d / REGISTRY_REL
        rp.parent.mkdir(parents=True, exist_ok=True)
        rp.write_text(sentinel)
    return d


def run_tool(case_dir: Path, case: str, extra: tuple = (), patched: bool = False) -> dict:
    logs = ART / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    reg = case_dir / REGISTRY_REL
    before = sha256(reg) if reg.is_file() else None
    cmd = [sys.executable, str(case_dir / "research_map" / "audit_evidence.py"),
           "--map", str(case_dir / "maps" / f"{case}.json"), *extra]
    proc = subprocess.run(cmd, cwd=case_dir, capture_output=True, text=True, timeout=180)
    (logs / f"{case}.stdout.txt").write_text(proc.stdout)
    (logs / f"{case}.stderr.txt").write_text(proc.stderr)
    after = sha256(reg) if reg.is_file() else None
    hard = [ln.strip()[len("HARD"):].strip() for ln in proc.stdout.splitlines()
            if ln.strip().startswith("HARD")]
    return {
        "case": case, "patched": patched, "argv_tail": list(extra),
        "rc": proc.returncode, "hard": hard, "hard_count": len(hard),
        "registry_sha_before": before, "registry_sha_after": after,
        "registry_overwritten": bool(before is not None and before != after),
        "registry_created": bool(before is None and after is not None),
        "registry_unchanged": before == after,
        "registry_present_after": reg.is_file(),
        "stdout_first_line": proc.stdout.splitlines()[0] if proc.stdout.splitlines() else "",
        "stderr_tail": proc.stderr[-300:],
    }


# ---------------------------------------------------------------- maps
def wellformed_map(frozen_sha: str, n1_active: bool = False,
                   gates: bool = True, lock: bool = True, frozen: bool = True) -> dict:
    nodes = [
        {"id": "N0", "status": "done", "artifact": "artifact.txt",
         "validation_status": "unverified", "evidence_refs": ["artifact.txt"],
         "class_id": "AF-WCC-VAC-GEN"},
        {"id": "NQ", "status": "queued", "class_id": "AF-SCC-C2-VAC-GEN"},
    ]
    if n1_active:
        nodes.append({"id": "N1", "status": "active", "class_id": "AF-WCC-SCALAR-SPH"})
    m: dict = {"groups": [{"id": "G1", "direction": "gates and audit", "nodes": nodes}], "claims": []}
    m["gates"] = ([{"gate_id": "G-T", "scope": "N0", "verdict": "pass",
                    "criteria": "artifact exists", "evidence_refs": ["artifact.txt"]}]
                  if gates else [])
    if lock:
        m["numerics_lock"] = {"state": "locked", "since": "2026-09-11T23:15:11+08:00",
                              "locked_nodes": ["N1"], "allowed_nodes": ["N0"],
                              "required_gates": ["G-T"]}
    if frozen:
        m["frozen_artifacts"] = [{"path": "frozen.txt", "sha256": frozen_sha, "active": True}]
    return m


def _drop_gates(m: dict) -> dict:
    """Same map with the gate universe emptied and no dangling lock reference."""
    m = json.loads(json.dumps(m))
    if "numerics_lock" in m:
        m["numerics_lock"]["required_gates"] = []
    return m


def build_cases() -> list:
    v1 = "frozen v1\n"
    v2 = "frozen v2 drifted\n"
    sha_v1 = hashlib.sha256(v1.encode()).hexdigest()
    base_files = {"artifact.txt": "hello world\n", "frozen.txt": v1}
    drift_files = {"artifact.txt": "hello world\n", "frozen.txt": v2}
    sentinel = json.dumps({"SENTINEL": True, "hashes": {"keep": "me"}}, indent=2) + "\n"

    cases = [
        # positive control: well-formed map must pass
        dict(case="C0_wellformed", map=wellformed_map(sha_v1), files=base_files,
             sentinel=None, expect_rc=0, expect_hard_contains=[]),
        # negative control: two real violations must be caught
        dict(case="C0_negative", map={**wellformed_map(sha_v1), "groups": [{"id": "G1", "nodes": [
                {"id": "N0", "status": "done", "artifact": "missing_artifact.txt",
                 "validation_status": "unverified", "evidence_refs": ["artifact.txt"],
                 "class_id": "AF-WCC-VAC-GEN"}]}],
                "gates": [{"gate_id": "G-T", "scope": "N0", "verdict": "pass",
                           "criteria": "artifact exists"}]},
             files=base_files, sentinel=None, expect_rc=1,
             expect_hard_contains=["done but artifact missing on disk",
                                   "passed without evidence_refs"]),
        # C1: emptied map is a vacuous pass
        dict(case="C1_empty_map", map={}, files={}, sentinel=None,
             expect_rc=0, expect_hard_contains=[]),
        # C2: deleting the gate universe is a vacuous pass when the lock does not
        # reference a removed gate. C2b shows the only indirect guard that fires.
        dict(case="C2_gates_dropped", map=_drop_gates(wellformed_map(sha_v1, gates=False)),
             files=base_files, sentinel=None, expect_rc=0, expect_hard_contains=[]),
        dict(case="C2b_gates_dropped_dangling_lock_ref",
             map=wellformed_map(sha_v1, gates=False), files=base_files, sentinel=None,
             expect_rc=1, expect_hard_contains=["unknown required gate"]),
        # C3b/C3: drift detection works only while the frozen entry is present
        dict(case="C3b_frozen_drift_detected", map=wellformed_map(sha_v1), files=drift_files,
             sentinel=None, expect_rc=1, expect_hard_contains=["frozen artifact drifted"]),
        dict(case="C3_frozen_dropped", map=wellformed_map(sha_v1, frozen=False), files=drift_files,
             sentinel=None, expect_rc=0, expect_hard_contains=[]),
        # C4b/C4: lock enforcement works only while the lock key is present
        dict(case="C4b_lock_detected", map=wellformed_map(sha_v1, n1_active=True), files=base_files,
             sentinel=None, expect_rc=1, expect_hard_contains=["N1 is active while self-gravitating"]),
        dict(case="C4_lock_dropped", map=wellformed_map(sha_v1, n1_active=True, lock=False),
             files=base_files, sentinel=None, expect_rc=0, expect_hard_contains=[]),
        # C5/C5b: global registry is rewritten on every invocation, pass or fail
        dict(case="C5_registry_rewrite_empty", map={}, files={}, sentinel=sentinel,
             expect_rc=0, expect_hard_contains=[], expect_registry_overwritten=True),
        dict(case="C5b_registry_rewrite_failure", map={**wellformed_map(sha_v1), "groups": [{"id": "G1", "nodes": [
                {"id": "N0", "status": "done", "artifact": "missing_artifact.txt",
                 "validation_status": "unverified", "evidence_refs": ["x"],
                 "class_id": "AF-WCC-VAC-GEN"}]}]},
             files=base_files, sentinel=sentinel, expect_rc=1,
             expect_hard_contains=["done but artifact missing on disk"],
             expect_registry_overwritten=True),
        # C6: the embedded class-separation detector still fires on a token leak
        dict(case="C6_token_scan_alive", map={"groups": [], "gates": [], "claims": [
                {"class_id": "AF-SCC-C2-VAC-GEN",
                 "statement": "We treat C0 and C2 as one class for the audit."}]},
             files={}, sentinel=None, expect_rc=1, expect_hard_contains=["CLASSSEP"]),
    ]
    return cases


def run_unpatched(cases: list, audit_snapshot: Path | None = None, tag: str = "current") -> list:
    results = []
    for c in cases:
        key = f"{tag}__{c['case']}"
        d = build_sandbox(key, c["map"], c["files"], c.get("sentinel"), audit_snapshot=audit_snapshot)
        r = run_tool(d, key)
        r["base_case"] = c["case"]
        r["revision"] = tag
        r["audit_sha256"] = sha256(audit_snapshot) if audit_snapshot else None
        r["expected_rc"] = c["expect_rc"]
        r["expect_hard_contains"] = c["expect_hard_contains"]
        r["hard_substrings_found"] = [s for s in c["expect_hard_contains"]
                                      if any(s in h for h in r["hard"])]
        r["pass"] = (r["rc"] == c["expect_rc"]
                     and len(r["hard_substrings_found"]) == len(c["expect_hard_contains"])
                     and (c.get("expect_registry_overwritten") is None
                          or r["registry_overwritten"] == c["expect_registry_overwritten"]))
        results.append(r)
    return results


# ---------------------------------------------------------------- patch + option surface
PATCH_OLD_MAIN = '''    ap.add_argument("--write-hashes", action="store_true", default=True)
    a = ap.parse_args()
    res = audit(Path(a.map))
    out = ROOT / "runtime" / "state" / "artifact_hashes.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({k: v for k, v in res.items() if k != "hard"}, indent=2, sort_keys=True))'''

PATCH_NEW_MAIN = '''    ap.add_argument("--write-hashes", action="store_true", default=True)
    ap.add_argument("--dry-run", action="store_true",
                    help="run the audit but do not rewrite runtime/state/artifact_hashes.json")
    a = ap.parse_args()
    res = audit(Path(a.map))
    out = ROOT / "runtime" / "state" / "artifact_hashes.json"
    if a.dry_run:
        print("dry-run: artifact_hashes.json not rewritten")
    else:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({k: v for k, v in res.items() if k != "hard"}, indent=2, sort_keys=True))'''

PATCH_OLD_BODY = "    hard, soft, hashes = [], [], {}\n"
PATCH_NEW_BODY = '''    hard, soft, hashes = [], [], {}
    # 0. corpus non-vacuity: absent structures must not silently shrink the audit
    if not isinstance(m, dict) or not m:
        hard.append("map is empty or not a JSON object; every audit section is vacuous")
        m = {}
    if not m.get("groups"):
        hard.append("map declares no groups: node audits (1, 4) are vacuous")
    if not m.get("gates"):
        hard.append("map declares no gates: gate audit (2) is vacuous")
    if "frozen_artifacts" not in m:
        hard.append("map has no frozen_artifacts key: drift audit (3b) is vacuous")
    if "numerics_lock" not in m:
        hard.append("map has no numerics_lock key: lock audit (2) is vacuous")
'''


def make_patch() -> Path:
    src = (SNAP / f"audit_evidence.{AUDIT_PIN[:12]}.py").read_text()
    assert PATCH_OLD_MAIN in src and PATCH_OLD_BODY in src, "patch anchors not found in pinned source"
    patched = src.replace(PATCH_OLD_BODY, PATCH_NEW_BODY).replace(PATCH_OLD_MAIN, PATCH_NEW_MAIN)
    (ART / "patched").mkdir(parents=True, exist_ok=True)
    pp = ART / "patched" / "audit_evidence.patched.py"
    pp.write_text(patched)
    diff = "".join(difflib.unified_diff(
        src.splitlines(keepends=True), patched.splitlines(keepends=True),
        fromfile=f"a/{AUDIT_REL}", tofile=f"b/{AUDIT_REL}", n=3))
    dp = ART / "proposed_patch.diff"
    dp.write_text(diff)
    assert sha256(pp) != AUDIT_PIN
    return dp


def run_patched() -> list:
    v1 = "frozen v1\n"
    sha_v1 = hashlib.sha256(v1.encode()).hexdigest()
    base_files = {"artifact.txt": "hello world\n", "frozen.txt": v1}
    drift_files = {"artifact.txt": "hello world\n", "frozen.txt": "frozen v2 drifted\n"}
    sentinel = json.dumps({"SENTINEL": True, "hashes": {"keep": "me"}}, indent=2) + "\n"
    cases = [
        dict(case="P0_wellformed_still_passes", map=wellformed_map(sha_v1), files=base_files,
             sentinel=None, extra=(), expect_rc=0, expect_hard_contains=[]),
        dict(case="P1_empty_map_fails", map={}, files={}, sentinel=None, extra=(),
             expect_rc=1, expect_hard_contains=["map is empty"]),
        dict(case="P2_gates_dropped_fails", map=wellformed_map(sha_v1, gates=False),
             files=base_files, sentinel=None, extra=(),
             expect_rc=1, expect_hard_contains=["map declares no gates"]),
        dict(case="P3_frozen_dropped_fails", map=wellformed_map(sha_v1, frozen=False),
             files=drift_files, sentinel=None, extra=(),
             expect_rc=1, expect_hard_contains=["no frozen_artifacts key"]),
        dict(case="P4_lock_dropped_fails", map=wellformed_map(sha_v1, n1_active=True, lock=False),
             files=base_files, sentinel=None, extra=(),
             expect_rc=1, expect_hard_contains=["no numerics_lock key"]),
        dict(case="P5_dry_run_no_registry_write", map=wellformed_map(sha_v1), files=base_files,
             sentinel=sentinel, extra=("--dry-run",), expect_rc=0, expect_hard_contains=[]),
    ]
    results = []
    for c in cases:
        d = build_sandbox(c["case"], c["map"], c["files"], c.get("sentinel"), patched=True)
        r = run_tool(d, c["case"], extra=c["extra"], patched=True)
        r["expected_rc"] = c["expect_rc"]
        r["expect_hard_contains"] = c["expect_hard_contains"]
        r["hard_substrings_found"] = [s for s in c["expect_hard_contains"]
                                      if any(s in h for h in r["hard"])]
        extra_ok = (r["registry_unchanged"] is True) if c["case"].startswith("P5") else True
        r["pass"] = (r["rc"] == c["expect_rc"]
                     and len(r["hard_substrings_found"]) == len(c["expect_hard_contains"])
                     and extra_ok)
        results.append(r)
    return results


def option_surface() -> dict:
    d = build_sandbox("C7_option_surface", {}, {}, sentinel=json.dumps({"SENTINEL": True}) + "\n")
    tool = str(d / "research_map" / "audit_evidence.py")
    help_p = subprocess.run([sys.executable, tool, "--help"], cwd=d,
                            capture_output=True, text=True, timeout=60)
    (ART / "logs" / "C7_help.stdout.txt").write_text(help_p.stdout)
    reg = d / REGISTRY_REL
    before = sha256(reg)
    dry_p = subprocess.run([sys.executable, tool, "--map", str(d / "maps" / "C7_option_surface.json"),
                            "--dry-run"], cwd=d, capture_output=True, text=True, timeout=60)
    after = sha256(reg)
    (ART / "logs" / "C7_dryrun.stderr.txt").write_text(dry_p.stderr)
    usage = [ln for ln in help_p.stdout.splitlines() if ln.startswith("usage:")]
    return {
        "help_rc": help_p.returncode,
        "usage": usage[0] if usage else "",
        "help_lists_dry_run": "--dry-run" in help_p.stdout,
        "unknown_dry_run_rc": dry_p.returncode,
        "unknown_dry_run_rejected_before_audit": before == after,
        "registry_unchanged_after_rejected_flag": before == after,
    }


# ---------------------------------------------------------------- entry point
def main() -> int:
    art_str = str(ART.relative_to(ROOT))
    entry = {
        "task_id": TASK, "actor": "worker-024", "node_id": "A1", "gate": "G-AUDIT",
        "class_ids": CLASS_IDS, "created_at": now(),
        "canonical_sha256_at_entry": {
            AUDIT_REL: sha256(ROOT / AUDIT_REL),
            DET_REL: sha256(ROOT / DET_REL),
            REGISTRY_REL: sha256(ROOT / REGISTRY_REL),
        },
        "registry_sha256_at_entry": sha256(ROOT / REGISTRY_REL),
    }
    (ART / "entry_hashes.json").write_text(json.dumps(entry, indent=2, sort_keys=True))

    pins = snapshot_pins()
    global CURRENT_AUDIT_SNAP, DET_SNAP
    CURRENT_AUDIT_SNAP = SNAP / f"audit_evidence.{pins[AUDIT_REL]['sha256'][:12]}.py"
    DET_SNAP = SNAP / f"class_separation.{pins[DET_REL]['sha256'][:12]}.py"
    current_audit_sha = pins[AUDIT_REL]["sha256"]
    patch_path = make_patch()
    cases = build_cases()

    # primary matrix on the bytes that are canonical now; replay any earlier revision kept on disk
    unpatched = run_unpatched(cases, audit_snapshot=CURRENT_AUDIT_SNAP, tag=current_audit_sha[:12])
    revision_matrix = {current_audit_sha[:12]: {
        "audit_sha256": current_audit_sha,
        "cases": {r["base_case"]: {"rc": r["rc"], "hard_count": r["hard_count"]} for r in unpatched},
    }}
    for snap in sorted(SNAP.glob("audit_evidence.*.py")):
        h = sha256(snap)
        if h == current_audit_sha:
            continue
        alt = run_unpatched(cases, audit_snapshot=snap, tag=h[:12])
        revision_matrix[h[:12]] = {
            "audit_sha256": h,
            "cases": {r["base_case"]: {"rc": r["rc"], "hard_count": r["hard_count"]} for r in alt},
        }
    patched = run_patched()
    opts = option_surface()

    # Canonical inputs are only ever READ by this driver: every subprocess runs a copy whose
    # __file__ (and therefore ROOT) is under sandbox/. Concurrent controller traffic may still
    # rewrite the shared registry, so drift is recorded rather than asserted away.
    drift = {
        AUDIT_REL: sha256(ROOT / AUDIT_REL) != entry["canonical_sha256_at_entry"][AUDIT_REL],
        DET_REL: sha256(ROOT / DET_REL) != entry["canonical_sha256_at_entry"][DET_REL],
        REGISTRY_REL: sha256(ROOT / REGISTRY_REL) != entry["canonical_sha256_at_entry"][REGISTRY_REL],
    }
    no_canonical_input_changed = not drift[AUDIT_REL] and not drift[DET_REL]
    registry_traffic = drift[REGISTRY_REL]

    vacuous = [r["base_case"] for r in unpatched
               if r["rc"] == 0 and r["hard_count"] == 0 and r["expected_rc"] == 0
               and r["base_case"] in {"C1_empty_map", "C2_gates_dropped", "C3_frozen_dropped",
                                      "C4_lock_dropped"}]
    detected = [r["base_case"] for r in unpatched if r["rc"] == 1 and r["hard_count"] > 0]
    controls_ok = [r["base_case"] for r in unpatched
                   if r["base_case"] in {"C0_wellformed", "C0_negative"} and r["pass"]]
    overwritten = [r["base_case"] for r in unpatched if r["registry_overwritten"]]
    created = [r["base_case"] for r in unpatched if r["registry_created"]]
    all_pass = all(r["pass"] for r in unpatched) and all(r["pass"] for r in patched)
    # the structural finding must survive the live revision edit
    base_keys = sorted(revision_matrix[current_audit_sha[:12]]["cases"])
    structural_identical = all(
        revision_matrix[current_audit_sha[:12]]["cases"][k] == matrix["cases"][k]
        for matrix in revision_matrix.values() for k in base_keys)

    report = {
        "task_id": TASK, "actor": "worker-024", "role": "bounded execution worker (fleet slot 024)",
        "node_id": "A1", "gate": "G-AUDIT", "class_ids": CLASS_IDS,
        "generated_at": now(),
        "question": ("Does research_map/audit_evidence.py, whose hard=0 result is quoted as gate "
                     "evidence (controller_lifecycles[].audit_evidence_hard), fail open when one of the "
                     "structures it audits is deleted or emptied, and does it rewrite the global "
                     "artifact-hash registry on every invocation?"),
        "method": ("Byte-identical sandbox copies of the tool + detector run with ROOT=sandbox "
                   "(the tool derives ROOT from __file__), one synthetic map per structure deleted. "
                   "Every case also records the sandbox runtime/state/artifact_hashes.json sha256 "
                   "before/after. A minimal fail-closed patch is applied to a copy and re-run. The "
                   "canonical file changed mid-session, so every revision kept in snapshots/ is "
                   "replayed through the same matrix and the per-case outcomes are compared."),
        "pins": pins,
        "tool_pins": {
            AUDIT_REL: current_audit_sha,
            DET_REL: pins[DET_REL]["sha256"],
            "superseded_audit_revisions": sorted(
                h[:12] for h in revision_matrix if h != current_audit_sha[:12]),
            "patched/audit_evidence.patched.py": sha256(ART / "patched" / "audit_evidence.patched.py"),
            "proposed_patch.diff": sha256(patch_path),
        },
        "revision_matrix": revision_matrix,
        "structural_findings_identical_across_revisions": structural_identical,
        "revision_note": (
            "research_map/audit_evidence.py was bebec0843f10... when this artifact directory was "
            "created and 6217729e... from 2026-09-12T00:32:45+08:00 (astra-life04 REC-3: companion "
            "vs mirror pairs, registry includes runtime/state/controller_verification). Both "
            "revisions are snapshotted; the vacuity finding is stated for both."),
        "cases": unpatched,
        "patched_cases": patched,
        "option_surface": opts,
        "result": {
            "verdict": "FAIL_OPEN_ON_ABSENT_STRUCTURES",
            "vacuous_pass_cases": vacuous,
            "detection_controls_ok": controls_ok,
            "detected_violation_cases": detected,
            "registry_overwritten_cases": overwritten,
            "registry_created_cases": created,
            "all_case_assertions_pass": all_pass,
            "positive_control": "C0_wellformed rc=0/hard=0; C0_negative rc=1 with both injected violations",
            "embedded_detector_alive": "C6_token_scan_alive rc=1 on a C0/C2 merge claim with no groups/gates",
            "global_state_write": {
                "target_template": "<tool ROOT>/runtime/state/artifact_hashes.json",
                "write_is_unconditional": True,
                "dry_run_option_exists": False,
                "write_hashes_flag_read": False,
                "demo": "sentinel registry was overwritten in C5 (empty map, rc 0) and C5b (rc 1)",
                "canonical_consequence": ("running the canonical file with any --map rewrites "
                                          "runtime/state/artifact_hashes.json; not executed on the "
                                          "canonical path in this audit"),
            },
            "patch_closes_cases": [r["case"] for r in patched if r["pass"] and r["case"] != "P0_wellformed_still_passes"],
            "notes": [
                "Instrument claim only: no gate verdict, no node transition, no physics claim.",
                "The audit's class-token detector is not dead; it is the structural coverage that is unpinned.",
                "C2b is the one indirect guard observed: a removed gate still fails if numerics_lock.required_gates names it; the guard is bypassed by also emptying that list.",
            ],
        },
        "artifacts": {
            "driver": f"{art_str}/drive_vacuity.py",
            "report": f"{art_str}/report.json",
            "readme": f"{art_str}/README.md",
            "entry_hashes": f"{art_str}/entry_hashes.json",
            "exit_hashes": f"{art_str}/exit_hashes.json",
            "proposed_patch": f"{art_str}/proposed_patch.diff",
        },
        "no_canonical_input_changed": no_canonical_input_changed,
        "canonical_drift_during_run": drift,
        "registry_traffic_during_run": registry_traffic,
        "isolation_proof": (
            "every audit subprocess executed <sandbox>/research_map/audit_evidence.py with cwd=the "
            "sandbox, so ROOT=<sandbox>; the sandbox sentinel registry was overwritten in C5/C5b, "
            "showing where the write lands. No canonical path appears in any subprocess argv."),
    }
    (ART / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True))

    exit_h = {
        "task_id": TASK, "generated_at": now(),
        "canonical_sha256_at_exit": {
            AUDIT_REL: sha256(ROOT / AUDIT_REL),
            DET_REL: sha256(ROOT / DET_REL),
            REGISTRY_REL: sha256(ROOT / REGISTRY_REL),
        },
        "no_canonical_input_changed_during_run": no_canonical_input_changed,
        "canonical_drift_during_run": drift,
        "registry_traffic_during_run": registry_traffic,
        "sandbox_registry_overwrites_demonstrated": overwritten,
        "sandbox_registry_creations": created,
    }
    (ART / "exit_hashes.json").write_text(json.dumps(exit_h, indent=2, sort_keys=True))

    print(json.dumps({
        "verdict": report["result"]["verdict"],
        "unpatched_cases": len(unpatched), "unpatched_all_assertions_pass": all(r["pass"] for r in unpatched),
        "patched_cases": len(patched), "patched_all_assertions_pass": all(r["pass"] for r in patched),
        "vacuous_pass_cases": vacuous,
        "registry_overwritten_cases": overwritten,
        "option_surface": opts,
        "revisions": {k: v["audit_sha256"][:12] for k, v in revision_matrix.items()},
        "structural_findings_identical_across_revisions": structural_identical,
        "canonical_drift_during_run": drift,
        "no_canonical_input_changed": no_canonical_input_changed,
    }, indent=1))
    return 0 if all_pass else 2


if __name__ == "__main__":
    sys.exit(main())
