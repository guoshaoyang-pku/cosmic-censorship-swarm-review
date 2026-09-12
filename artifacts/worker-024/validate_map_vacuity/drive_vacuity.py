#!/usr/bin/env python3
"""W024-VALIDATE-MAP-VACUITY-01 -- independent instrument audit of research_map/validate_map.py.

Class ids: AF-WCC-VAC-GEN; AF-SCC-C2-VAC-GEN; AF-SCC-C0-VAC-GEN; AF-WCC-SCALAR-SPH
Node A1 / gate G-AUDIT.  The map is the sole global state in which every class binding,
gate verdict and claim lives; this driver measures what the canonical map validator's
`VALID` verdict actually certifies.

Two measured claims, both on pinned bytes (no canonical file is modified, no map write):

  (A) fail-open: `validate_map` asserts nothing about required structures; {} and
      structurally stripped maps print VALID / exit 0.
  (B) base divergence: the done-node artifact-existence check resolves declared artifact
      paths against `research_map/`, while the map's own convention -- and the demotion
      check in apply_events.py:19,393 -- resolves them against the repo root.  Measured
      both directions: a correctly declared repo-root-relative artifact is reported
      missing (false INVALID), and a research_map/-relative artifact that apply_events
      would demote is certified VALID.

Reproduce:  python3 artifacts/worker-024/validate_map_vacuity/drive_vacuity.py
Exit codes: 0 all assertions held; 2 snapshot hash mismatch (tamper); 1 assertion failed.
"""
from __future__ import annotations

import copy
import difflib
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

ART = Path(__file__).resolve().parent
ROOT = ART.parents[2]                      # repo root (ai4math-swarm)
SNAP = ART / "snapshots"
TMP = ART / "tmp"
LOGS = ART / "logs"
PATCHED = ART / "patched"
MIRROR = TMP / "mirror"                    # stand-in repo-root layout for the patched CLI

VM_SNAP = SNAP / "validate_map.aa4bd61c55cb.py"
SCH_SNAP = SNAP / "schemas.75214a75353b.py"
MAP_SNAP = SNAP / "research_map.snapshot.json"

PINS = {
    "validate_map.py": "aa4bd61c55cbb0361f56626888bfd722a03d0cb98addec8b63d67114b91ed211",
    "schemas.py": "75214a75353b9cd16952958c4711896a46f1f1bda1529622441f14eacf04003b",
    "research_map.snapshot.json": "3d45be5969ec388ef4a3e10d5eb87b81dbf3d03138510b75ff6a56453ceae005",
}

GOVERNANCE_KEYS = [
    "gates", "numerics_lock", "claims", "reviews", "resource_requests", "assignments",
    "applied_event_ids", "frozen_artifacts", "controller_findings", "publication_status",
    "controller_gate_audit", "portfolio_events",
]


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_module(name: str, path: Path):
    sys.path.insert(0, str(path.parent))
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        sys.path.remove(str(path.parent))


def ensure_pinned_schemas():
    """Register the pinned schemas snapshot under the module name `schemas`."""
    spec = importlib.util.spec_from_file_location("schemas", SCH_SNAP)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["schemas"] = mod
    spec.loader.exec_module(mod)
    assert Path(mod.__file__).resolve() == SCH_SNAP.resolve()
    return mod


def run_cli(validator: Path, case_path: Path, extra=None, cwd=None, timeout=120):
    cmd = [sys.executable, str(validator), "--map", str(case_path)] + list(extra or [])
    env = dict(os.environ)
    env["PYTHONPATH"] = str(validator.parent)
    p = subprocess.run(cmd, capture_output=True, text=True,
                       cwd=str(cwd or validator.parent), env=env, timeout=timeout)
    return p


def verdict(rc: int, out: str) -> str:
    if rc == 0 and out.strip().splitlines() and out.strip().splitlines()[0] == "VALID":
        return "VALID"
    return "INVALID"


# --------------------------------------------------------------------------- cases
def build_cases(base: dict):
    """Return case list; each case builds a map per channel ('inproc' | 'cli' | 'patched')."""

    def cl():
        return copy.deepcopy(base)

    def skeleton(m):
        """Governance skeleton copied from the real map, so controls isolate one defect."""
        for key in ("gates", "claims", "reviews", "assignments", "numerics_lock"):
            m[key] = copy.deepcopy(base[key])
        return m

    def minimal_done(artifact, with_evidence=True, with_validation=True):
        n = {"id": "A1", "status": "done", "artifact": artifact}
        if with_validation:
            n["validation_status"] = "passed"
        if with_evidence:
            n["evidence_refs"] = ["schemas/af_wcc_vacuum.yaml"]
        return skeleton({"groups": [{"id": "G-AUDIT", "nodes": [n]}]})

    def artifact_for(channel):
        # repo-root-relative path that exists; mirrored under snapshots/ and tmp/mirror/
        if channel == "inproc":
            return "schemas/af_wcc_vacuum.yaml"
        return "probe/schemas/af_wcc_vacuum.yaml"

    cases = []

    def add(cid, kind, builder, cur, pat, note):
        cases.append(dict(id=cid, kind=kind, builder=builder, expect_current=cur,
                          expect_patched=pat, note=note))

    add("C1_empty_object", "vacuous", lambda ch: {}, "VALID", "INVALID",
        "empty JSON object validates")
    add("C2_groups_and_edges_removed", "vacuous",
        lambda ch: {k: v for k, v in cl().items() if k not in ("groups", "cross_group_edges")},
        "VALID", "INVALID", "groups key and cross_group_edges removed validates")
    add("C2b_groups_removed_edges_kept", "partial_guard",
        lambda ch: {k: v for k, v in cl().items() if k != "groups"}, "INVALID", "INVALID",
        "groups removed but cross_group_edges kept -> dangling-edge error (partial indirect guard only)")
    add("C3_groups_empty_edges_removed", "vacuous",
        lambda ch: {k: v for k, v in {**cl(), "groups": []}.items() if k != "cross_group_edges"},
        "VALID", "INVALID", "group list emptied and cross edges removed validates")
    add("C3b_groups_empty_edges_kept", "partial_guard",
        lambda ch: {**cl(), "groups": []}, "INVALID", "INVALID",
        "group list emptied but cross_group_edges kept -> dangling-edge error (partial guard)")
    add("C4_nodes_emptied_edges_removed", "vacuous",
        lambda ch: {k: v for k, v in
                    {**cl(), "groups": [{**g, "nodes": []} for g in cl()["groups"]]}.items()
                    if k != "cross_group_edges"},
        "VALID", "INVALID", "every node list emptied and cross edges removed validates")
    add("C4b_nodes_emptied_edges_kept", "partial_guard",
        lambda ch: {**cl(), "groups": [{**g, "nodes": []} for g in cl()["groups"]]},
        "INVALID", "INVALID",
        "node lists emptied but cross_group_edges kept -> dangling-edge error (partial guard)")
    add("C5_governance_removed", "vacuous",
        lambda ch: {k: v for k, v in cl().items() if k not in GOVERNANCE_KEYS},
        "VALID", "INVALID", "all governance sections (gates, lock, claims, reviews, ...) removed")
    add("C6_gates_empty_lock_removed", "vacuous",
        lambda ch: {k: v for k, v in {**cl(), "gates": []}.items() if k != "numerics_lock"},
        "VALID", "INVALID", "gates list emptied and numerics_lock removed")
    add("C7_truncated_prefix", "vacuous",
        lambda ch: {k: base[k] for k in ("schema_version", "updated_at", "project", "actors")
                    if k in base},
        "VALID", "INVALID", "only header keys survive (truncation-shaped object)")
    add("C8_lock_violated", "vacuous",
        lambda ch: _lock_violation(cl()), "VALID", "INVALID",
        "numerics_lock=locked but the locked node N1 is active (hard decision 2 violated)")

    add("P0_real_map", "healthy", lambda ch: cl(), "VALID", "VALID",
        "healthy canonical map snapshot (0 done nodes at this revision)")
    add("P1_done_missing_artifact", "control",
        lambda ch: minimal_done(f"probe/absent-{ch}.yaml"), "INVALID", "INVALID",
        "done node whose declared artifact is absent")
    add("P2_done_without_evidence_refs", "control",
        lambda ch: minimal_done(artifact_for(ch), with_evidence=False), "INVALID", "INVALID",
        "done node with an existing artifact but no evidence_refs")
    add("P3_cycle", "control",
        lambda ch: skeleton({"groups": [{"id": "G-AUDIT", "nodes": [
            {"id": "A1", "status": "active", "depends_on": ["A2"]},
            {"id": "A2", "status": "active", "depends_on": ["A1"]}]}]}),
        "INVALID", "INVALID", "dependency cycle")
    add("P4_duplicate_node", "control",
        lambda ch: skeleton({"groups": [{"id": "G-AUDIT", "nodes": [
            {"id": "A1", "status": "active"}, {"id": "A1", "status": "active"}]}]}),
        "INVALID", "INVALID", "duplicate node id")
    add("P5_unknown_dependency", "control",
        lambda ch: skeleton({"groups": [{"id": "G-AUDIT", "nodes": [
            {"id": "A1", "status": "active", "depends_on": ["NOPE"]}]}]}),
        "INVALID", "INVALID", "dependency on an unknown node")
    add("P6_done_without_validation_status", "control",
        lambda ch: minimal_done(artifact_for(ch), with_validation=False), "INVALID", "INVALID",
        "done node with an existing artifact but no validation_status")
    return cases


def _lock_violation(m: dict) -> dict:
    locked = set((m.get("numerics_lock") or {}).get("locked_nodes") or ["N1"])
    hit = False
    for g in m.get("groups", []):
        for n in g.get("nodes", []):
            if n.get("id") in locked:
                n["status"] = "active"
                hit = True
    if not hit and m.get("groups"):
        m["groups"][0].setdefault("nodes", []).append({"id": sorted(locked)[0], "status": "active"})
    return m


# --------------------------------------------------------------------------- patch
PATCHED_SRC_NAME = "validate_map.patched.py"


def make_patch(vm_src: str) -> str:
    old_head = (
        "def validate_map(m, base=None):\n"
        "    # integrated from worker-19's proposed patch (artifacts/audit/flash19_validate_map_gate.patch)\n"
        "    base = Path(base) if base else ROOT\n"
        "    errors=[]; groups={g[\"id\"]:g for g in m.get(\"groups\",[])}; nodes={}\n"
    )
    new_head = (
        "def validate_map(m, base=None):\n"
        "    # W024-VALIDATE-MAP-VACUITY-01 proposed patch (owner decision to apply):\n"
        "    #  (1) non-vacuity block -- a structurally stripped map must not validate;\n"
        "    #  (2) map artifact paths are repo-root-relative (apply_events.py:19,393),\n"
        "    #      so the default base is the repo root, not the research_map/ dir.\n"
        "    base = Path(base) if base else ROOT.parent\n"
        "    errors=[]\n"
        "    groups_raw=m.get(\"groups\")\n"
        "    if not isinstance(groups_raw,list) or not groups_raw:\n"
        "        errors.append(\"vacuity guard: map has no groups\")\n"
        "    if not any(isinstance(g,dict) and g.get(\"nodes\") for g in (groups_raw or [])):\n"
        "        errors.append(\"vacuity guard: map has no nodes\")\n"
        "    for _key in (\"gates\",\"claims\",\"reviews\",\"assignments\",\"numerics_lock\"):\n"
        "        if _key not in m:\n"
        "            errors.append(f\"vacuity guard: missing required section {_key}\")\n"
        "    if isinstance(m.get(\"gates\"),list) and not m[\"gates\"]:\n"
        "        errors.append(\"vacuity guard: gates list is empty\")\n"
        "    _lock=m.get(\"numerics_lock\") or {}\n"
        "    if isinstance(_lock,dict) and _lock.get(\"state\")==\"locked\":\n"
        "        _locked=set(_lock.get(\"locked_nodes\") or [])\n"
        "        for _g in groups_raw or []:\n"
        "            if not isinstance(_g,dict): continue\n"
        "            for _n in _g.get(\"nodes\",[]) or []:\n"
        "                if isinstance(_n,dict) and _n.get(\"id\") in _locked and _n.get(\"status\") in {\"active\",\"done\"}:\n"
        "                    errors.append(f\"locked node {_n['id']} status {_n['status']} while numerics_lock=locked (hard decision 2)\")\n"
        "    groups={g[\"id\"]:g for g in (groups_raw or [])}; nodes={}\n"
    )
    if old_head not in vm_src:
        raise SystemExit("PATCH ANCHOR NOT FOUND -- pinned validator changed")
    src = vm_src.replace(old_head, new_head, 1)
    old_cli = (
        "    ap=argparse.ArgumentParser(); ap.add_argument(\"--map\",default=str(ROOT/\"research_map.json\"));"
        " ap.add_argument(\"events\",nargs=\"*\"); a=ap.parse_args()\n"
        "    errs=validate_map(load(a.map))+validate_events(a.events)\n"
    )
    new_cli = (
        "    ap=argparse.ArgumentParser(); ap.add_argument(\"--map\",default=str(ROOT/\"research_map.json\"));"
        " ap.add_argument(\"--base\",default=None); ap.add_argument(\"events\",nargs=\"*\"); a=ap.parse_args()\n"
        "    errs=validate_map(load(a.map), base=a.base)+validate_events(a.events)\n"
    )
    if old_cli not in src:
        raise SystemExit("PATCH CLI ANCHOR NOT FOUND -- pinned validator changed")
    return src.replace(old_cli, new_cli, 1)


def make_mirror() -> Path:
    """tmp/mirror/{research_map,schemas -> ROOT/schemas, ...}: faithful repo-root layout."""
    rm = MIRROR / "research_map"
    rm.mkdir(parents=True, exist_ok=True)
    for entry in ("schemas", "artifacts", "reviews", "ledger", "numerics", "data", "runs"):
        link = MIRROR / entry
        if not link.exists() and not link.is_symlink():
            os.symlink(ROOT / entry, link)
    for f in ("evaluation_rubric.yaml",):
        link = MIRROR / f
        if (ROOT / f).exists() and not link.exists() and not link.is_symlink():
            os.symlink(ROOT / f, link)
    return MIRROR


def main() -> int:
    for d in (TMP, LOGS, PATCHED):
        d.mkdir(parents=True, exist_ok=True)

    report = {
        "task_id": "W024-VALIDATE-MAP-VACUITY-01",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN",
                      "AF-WCC-SCALAR-SPH"],
        "node_id": "A1",
        "gate": "G-AUDIT",
        "pins": PINS,
        "snapshot_hashes": {},
        "live_code_hashes": {},
        "live_code_matches_pinned": {},
        "context_hashes": {},
        "cases": [],
        "checks_passed": 0,
        "checks_total": 0,
    }

    # tamper checks: pinned snapshot bytes are the authority
    snap_ok = True
    for name, path in (("validate_map.py", VM_SNAP), ("schemas.py", SCH_SNAP),
                       ("research_map.snapshot.json", MAP_SNAP)):
        h = sha256_file(path)
        report["snapshot_hashes"][name] = h
        if h != PINS[name]:
            report["snapshot_hashes"][name + ":PIN_MISMATCH"] = True
            snap_ok = False
    for name, path in (("validate_map.py", ROOT / "research_map/validate_map.py"),
                       ("schemas.py", ROOT / "research_map/schemas.py"),
                       ("apply_events.py", ROOT / "research_map/apply_events.py"),
                       ("research_map.json(live)", ROOT / "research_map/research_map.json")):
        h = sha256_file(path)
        report["live_code_hashes"][name] = h
        if name in PINS:
            report["live_code_matches_pinned"][name] = (h == PINS[name])
    if not snap_ok:
        (ART / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        print("TAMPER: pinned snapshot hash mismatch; refusing to run", file=sys.stderr)
        return 2

    entry = {
        "task_id": report["task_id"],
        "captured_at": subprocess.run(["date", "-Is"], capture_output=True, text=True).stdout.strip(),
        "pins": PINS,
        "snapshots": {k: v for k, v in report["snapshot_hashes"].items()},
        "driver": {"path": "artifacts/worker-024/validate_map_vacuity/drive_vacuity.py",
                   "sha256": sha256_file(Path(__file__))},
    }
    (ART / "entry_hashes.json").write_text(json.dumps(entry, indent=2, sort_keys=True) + "\n")

    base = json.loads(MAP_SNAP.read_text())
    vm_src = VM_SNAP.read_text()

    # patch proposal + mirror layout for patched CLI defaults
    patched_src = make_patch(vm_src)
    patched_path = PATCHED / PATCHED_SRC_NAME
    patched_path.write_text(patched_src)
    (ART / "fail_closed_patch.diff").write_text("".join(difflib.unified_diff(
        vm_src.splitlines(keepends=True), patched_src.splitlines(keepends=True),
        fromfile="research_map/validate_map.py@" + PINS["validate_map.py"][:12],
        tofile="artifacts/worker-024/validate_map_vacuity/patched/validate_map.patched.py")))
    mirror = make_mirror()
    patched_cli = mirror / "research_map" / PATCHED_SRC_NAME
    patched_cli.write_text(patched_src)
    (mirror / "research_map" / "schemas.py").write_text(SCH_SNAP.read_text())
    # byte-identical schemas.py beside the snapshot validator so the canonical CLI can import
    (SNAP / "schemas.py").write_text(SCH_SNAP.read_text())
    # probe artifact resolvable under the snapshots/ dir (unpatched CLI base) and mirror
    probe_rel = "probe/schemas/af_wcc_vacuum.yaml"
    for tree in (SNAP, mirror):
        p = tree / probe_rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes((ROOT / "schemas/af_wcc_vacuum.yaml").read_bytes())

    ensure_pinned_schemas()
    mod = load_module("pinned_validate_map", VM_SNAP)
    mod_p = load_module("pinned_validate_map_patched", patched_path)
    checks_passed = checks_total = 0

    def record(cid, channel, expected, observed, detail):
        nonlocal checks_passed, checks_total
        checks_total += 1
        ok = (expected == observed)
        if ok:
            checks_passed += 1
        return {"case": cid, "channel": channel, "expected": expected,
                "observed": observed, "assertion_held": ok, "detail": detail}

    cases = build_cases(base)
    for c in cases:
        cid = c["id"]
        errors_in = mod.validate_map(c["builder"]("inproc"), base=ROOT)
        cli_map = c["builder"]("cli")
        f_cli = TMP / f"{cid}.cli.json"
        f_cli.write_text(json.dumps(cli_map, indent=1))
        p = run_cli(VM_SNAP, f_cli, cwd=SNAP)
        (LOGS / f"{cid}.cli.stdout.txt").write_text(p.stdout)
        (LOGS / f"{cid}.cli.stderr.txt").write_text(p.stderr)
        obs_in = "VALID" if not errors_in else "INVALID"
        obs_cli = verdict(p.returncode, p.stdout)
        rec = {"case": cid, "kind": c["kind"], "note": c["note"],
               "expect_current": c["expect_current"],
               "observed_inproc": obs_in, "observed_cli": obs_cli,
               "inproc_errors": errors_in,
               "cli_rc": p.returncode, "cli_stdout_head": p.stdout.strip().splitlines()[:2],
               "checks": []}
        rec["checks"].append(record(cid, "inproc(base=repo_root)", c["expect_current"], obs_in,
                                    errors_in[:3]))
        rec["checks"].append(record(cid, "cli(base=snapshots)", c["expect_current"], obs_cli,
                                    p.stdout.strip().splitlines()[:2]))
        # patched channel (only meaningful to compare expectations)
        errs_p_in = mod_p.validate_map(c["builder"]("inproc"), base=ROOT)
        f_p = TMP / f"{cid}.patched.json"
        f_p.write_text(json.dumps(c["builder"]("inproc"), indent=1))
        pp = run_cli(patched_cli, f_p, cwd=mirror)
        (LOGS / f"{cid}.patched.stdout.txt").write_text(pp.stdout)
        (LOGS / f"{cid}.patched.stderr.txt").write_text(pp.stderr)
        obs_p_in = "VALID" if not errs_p_in else "INVALID"
        obs_p_cli = verdict(pp.returncode, pp.stdout)
        rec["observed_patched_inproc"] = obs_p_in
        rec["observed_patched_cli"] = obs_p_cli
        rec["patched_inproc_errors"] = errs_p_in
        rec["checks"].append(record(cid, "patched-inproc(base=repo_root)", c["expect_patched"],
                                    obs_p_in, errs_p_in[:3]))
        rec["checks"].append(record(cid, "patched-cli(default base=mirror root)",
                                    c["expect_patched"], obs_p_cli, pp.stdout.strip().splitlines()[:2]))
        report["cases"].append(rec)

    # ---------------------------------------------------------------- divergence D1/D2
    div = {"D1_repo_root_relative_artifact": {}, "D2_research_map_relative_artifact": {}}

    def minimal_done(artifact):
        m = {"groups": [{"id": "G-AUDIT", "nodes": [
            {"id": "A1", "status": "done", "artifact": artifact,
             "validation_status": "passed", "evidence_refs": ["x"]}]}]}
        for key in ("gates", "claims", "reviews", "assignments", "numerics_lock"):
            m[key] = copy.deepcopy(base[key])
        return m

    # D1: artifact exists at repo root (the map's declared-path convention)
    d1 = minimal_done("schemas/af_wcc_vacuum.yaml")
    assert (ROOT / "schemas/af_wcc_vacuum.yaml").exists()
    errs_root = mod.validate_map(copy.deepcopy(d1), base=ROOT)
    errs_mapdir = mod.validate_map(copy.deepcopy(d1), base=ROOT / "research_map")
    f = TMP / "D1.cli.json"
    f.write_text(json.dumps(d1, indent=1))
    pd1 = run_cli(ROOT / "research_map/validate_map.py", f, cwd=ROOT)
    pd1s = run_cli(VM_SNAP, f, cwd=SNAP)
    errs_p = mod_p.validate_map(copy.deepcopy(d1), base=ROOT)
    f_p = TMP / "D1.patched.json"
    f_p.write_text(json.dumps(d1, indent=1))
    pd1p = run_cli(patched_cli, f_p, cwd=mirror)
    div["D1_repo_root_relative_artifact"] = {
        "artifact": "schemas/af_wcc_vacuum.yaml",
        "exists_at_repo_root": True,
        "exists_under_research_map_dir": False,
        "current_inproc_base_repo_root": "VALID" if not errs_root else "INVALID",
        "current_inproc_base_research_map": "VALID" if not errs_mapdir else "INVALID",
        "current_cli": verdict(pd1.returncode, pd1.stdout),
        "current_cli_snapshot_copy": verdict(pd1s.returncode, pd1s.stdout),
        "current_cli_sha256": sha256_file(ROOT / "research_map/validate_map.py"),
        "patched_inproc_base_repo_root": "VALID" if not errs_p else "INVALID",
        "patched_cli_default_base": verdict(pd1p.returncode, pd1p.stdout),
        "current_errors_base_research_map": errs_mapdir,
        "apply_events_demotion_verdict": "keeps done (ROOT/art exists, apply_events.py:393)",
        "note": "correctly declared, existing artifact is reported missing by the canonical CLI",
    }
    checks_total += 1
    if div["D1_repo_root_relative_artifact"]["current_cli"] == "INVALID" \
            and div["D1_repo_root_relative_artifact"]["current_inproc_base_repo_root"] == "VALID" \
            and div["D1_repo_root_relative_artifact"]["patched_cli_default_base"] == "VALID":
        checks_passed += 1
        div["D1_repo_root_relative_artifact"]["assertion_held"] = True
    else:
        div["D1_repo_root_relative_artifact"]["assertion_held"] = False

    # D2: artifact exists only under research_map/ (would be demoted by apply_events)
    d2 = minimal_done("formulation_taxonomy.yaml")
    assert (ROOT / "research_map/formulation_taxonomy.yaml").exists()
    errs_root2 = mod.validate_map(copy.deepcopy(d2), base=ROOT)
    errs_mapdir2 = mod.validate_map(copy.deepcopy(d2), base=ROOT / "research_map")
    f2 = TMP / "D2.cli.json"
    f2.write_text(json.dumps(d2, indent=1))
    pd2 = run_cli(ROOT / "research_map/validate_map.py", f2, cwd=ROOT)
    pd2s = run_cli(VM_SNAP, f2, cwd=SNAP)
    errs_p2 = mod_p.validate_map(copy.deepcopy(d2), base=ROOT)
    f2p = TMP / "D2.patched.json"
    f2p.write_text(json.dumps(d2, indent=1))
    pd2p = run_cli(patched_cli, f2p, cwd=mirror)
    div["D2_research_map_relative_artifact"] = {
        "artifact": "formulation_taxonomy.yaml",
        "exists_at_repo_root": (ROOT / "formulation_taxonomy.yaml").exists(),
        "exists_under_research_map_dir": True,
        "current_inproc_base_repo_root": "VALID" if not errs_root2 else "INVALID",
        "current_inproc_base_research_map": "VALID" if not errs_mapdir2 else "INVALID",
        "current_cli": verdict(pd2.returncode, pd2.stdout),
        "current_cli_snapshot_copy": verdict(pd2s.returncode, pd2s.stdout),
        "patched_inproc_base_repo_root": "VALID" if not errs_p2 else "INVALID",
        "patched_cli_default_base": verdict(pd2p.returncode, pd2p.stdout),
        "current_errors_base_repo_root": errs_root2,
        "apply_events_demotion_verdict": "demotes (ROOT/art absent, apply_events.py:393)",
        "note": "an artifact apply_events would demote is certified VALID by the canonical CLI",
    }
    checks_total += 1
    if div["D2_research_map_relative_artifact"]["current_cli"] == "VALID" \
            and div["D2_research_map_relative_artifact"]["current_inproc_base_repo_root"] == "INVALID" \
            and div["D2_research_map_relative_artifact"]["patched_inproc_base_repo_root"] == "INVALID":
        checks_passed += 1
        div["D2_research_map_relative_artifact"]["assertion_held"] = True
    else:
        div["D2_research_map_relative_artifact"]["assertion_held"] = False

    report["divergence"] = div
    report["checks_passed"] = checks_passed
    report["checks_total"] = checks_total
    vac = [c["case"] for c in report["cases"] if c["kind"] == "vacuous"
           and c["observed_inproc"] == "VALID" and c["observed_cli"] == "VALID"]
    partial = [c["case"] for c in report["cases"] if c["kind"] == "partial_guard"
               and c["observed_inproc"] == "INVALID" and c["observed_cli"] == "INVALID"]
    report["summary"] = {
        "vacuous_current_passes": vac,
        "vacuous_count": len(vac),
        "partial_guards_current_fail": partial,
        "partial_guard_count": len(partial),
        "patched_closes_all_vacuous": all(
            c["observed_patched_inproc"] == "INVALID" and c["observed_patched_cli"] == "INVALID"
            for c in report["cases"] if c["kind"] == "vacuous"),
        "patched_keeps_partial_guards": all(
            c["observed_patched_inproc"] == "INVALID" and c["observed_patched_cli"] == "INVALID"
            for c in report["cases"] if c["kind"] == "partial_guard"),
        "controls_current_fail": all(
            c["observed_inproc"] == "INVALID" and c["observed_cli"] == "INVALID"
            for c in report["cases"] if c["kind"] == "control"),
        "healthy_current_valid": next(c["observed_cli"] for c in report["cases"]
                                      if c["case"] == "P0_real_map"),
        "d1_false_positive_reproduced": div["D1_repo_root_relative_artifact"]["assertion_held"],
        "d2_false_negative_reproduced": div["D2_research_map_relative_artifact"]["assertion_held"],
        "all_checks_passed": checks_passed == checks_total,
        "canonical_code_matches_pinned": report["live_code_matches_pinned"],
        "done_nodes_in_snapshot": sum(
            1 for g in base.get("groups", []) for n in g.get("nodes", [])
            if n.get("status") == "done"),
    }
    (ART / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")

    ckpt = {
        "actor": "worker-024",
        "task_id": report["task_id"],
        "class_ids": report["class_ids"],
        "node_id": "A1",
        "gate": "G-AUDIT",
        "checks_passed": checks_passed,
        "checks_total": checks_total,
        "vacuous_current_passes": vac,
        "d1_false_positive_reproduced": report["summary"]["d1_false_positive_reproduced"],
        "d2_false_negative_reproduced": report["summary"]["d2_false_negative_reproduced"],
        "artifact": "artifacts/worker-024/validate_map_vacuity/report.json",
        "artifact_sha256": sha256_file(ART / "report.json"),
        "authority_note": "worker checkpoint: no gate verdict, no node transition",
    }
    (ART / "checkpoint.json").write_text(json.dumps(ckpt, indent=2, sort_keys=True) + "\n")
    state_ckpt = ROOT / "runtime/state/w024_validate_map_vacuity_checkpoint.json"
    state_ckpt.write_text(json.dumps(ckpt, indent=2, sort_keys=True) + "\n")
    ckpt["state_checkpoint"] = "runtime/state/w024_validate_map_vacuity_checkpoint.json"

    print(json.dumps({"checks_passed": checks_passed, "checks_total": checks_total,
                      "vacuous_current_passes": vac,
                      "d1": div["D1_repo_root_relative_artifact"]["assertion_held"],
                      "d2": div["D2_research_map_relative_artifact"]["assertion_held"],
                      "all_checks_passed": checks_passed == checks_total}, indent=2))
    return 0 if checks_passed == checks_total else 1


if __name__ == "__main__":
    raise SystemExit(main())
