#!/usr/bin/env python3
"""FD-13 rebase: does the field-global R12 geodesic exemption still let SCC content escape
the WCC gate at the revision currently on disk?

Tool/rule_spec/KEY_MANIFEST/independent-gate hashes are hard-asserted; any move aborts before
measuring. Schema hashes are recorded, not asserted, because the lead was mid-revision while
this ran (FROZEN rev26 manifest vs on-disk rev12 schemas); `binding.frozen_manifest_stale`
records that explicitly. The FROZEN-bound rev26 measurement is preserved in
`rev26_snapshot/rev26_results.json`; this script writes `<label>_results.json` for the
on-disk revision named by --label (default `diskhead`).

Gates compared (identical set to fd13/run_fd13.py):
  canonical_base    artifacts/formulation/tools/check_class_schema.py     000e09e4...
  canonical_patched fd13/tools/patched_check_class_schema.py            5eaab3f8... (proposal)
  flash11           check_schema.py  (independent implementation)        a89b221c...

Writes only under this directory. Read-only w.r.t. every shared tree.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BIND = HERE.parent
REPO = BIND.parents[2]

_ap = argparse.ArgumentParser()
_ap.add_argument("--label", default="diskhead")
_ap.add_argument("--schema-dir", default=None,
                 help="schema directory to measure (default: live artifacts/formulation/schemas)")
_args = _ap.parse_args()
LABEL = _args.label

CANON_BASE = REPO / "artifacts/formulation/tools/check_class_schema.py"
CANON_PATCHED = BIND / "fd13/tools/patched_check_class_schema.py"
FLASH11 = BIND / "check_schema.py"
RULE_SPEC = REPO / "artifacts/formulation/rule_spec.json"
FROZEN = REPO / "artifacts/formulation/FROZEN.json"
SCHEMAS = (Path(_args.schema_dir).resolve() if _args.schema_dir
           else REPO / "artifacts/formulation/schemas")
WCC = SCHEMAS / "af_wcc_vacuum.yaml"
SCHEMA_NAMES = ("af_wcc_vacuum.yaml", "af_scc_c2_vacuum.yaml", "af_scc_c0_vacuum.yaml")
CASE_DIR = HERE / f"{LABEL}_canonical"

EXPECT = {
    "artifacts/formulation/tools/check_class_schema.py":
        "000e09e46b2fb4abc047c21e99165cbc55692f3132744fb27e84645609263aff",
    "artifacts/formulation/rule_spec.json":
        "40f9bb9e657b2c6b0cce04a9c05e9cdbf18083669060727a8e31d83031f5901e",
    "artifacts/formulation/KEY_MANIFEST.json":
        "014e2d3019781632cdb78ace266cf08cc11f9cf8b8ef0a049beb74eb9c6b6b9a",
    "artifacts/flash-11/f1_aux_class_binding/check_schema.py":
        "a89b221c1c68e34f87776e5648a8e890d2a0f9f0b919280d3e176422b2d689f0",
    "artifacts/flash-11/f1_aux_class_binding/fd13/tools/patched_check_class_schema.py":
        "5eaab3f8f031396e9d787fd975ebc9d2a647cab6d144cd4a3c31ea45e70b215d",
}

ANCHOR = "(worker-16 F1-16-03 accepted).\""
LEAK_SENTENCE = " The maximal development is C^2-inextendible.\""
CONTROL_SENTENCE = (" Any singular point is witnessed by a future-inextendible causal geodesic "
                    "of finite affine length.\"")

IMPLS = {
    "canonical_base": {"path": CANON_BASE, "cwd": CANON_BASE.parent},
    "canonical_patched": {"path": HERE / "patched/tools/patched_check_class_schema.py",
                          "cwd": HERE / "patched/tools"},
    "flash11": {"path": FLASH11, "cwd": BIND},
}
# Stale-environment control: the fd13 copy of the patched tool sits beside the rev19
# KEY_MANIFEST (8ce752b5), which lacks the rev26 `binding_note` key -> spurious R22.
STALE_IMPL = {"path": CANON_PATCHED, "cwd": CANON_PATCHED.parent}


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def schema_revision(p: Path) -> int | None:
    m = re.search(r"^revision:\s*(\d+)", p.read_text(), re.M)
    return int(m.group(1)) if m else None


def check_binding() -> dict:
    frozen = json.loads(FROZEN.read_text())
    binding = {"frozen_revision": frozen.get("revision"), "frozen_at": frozen.get("frozen_at"),
               "measured_schema_dir": str(SCHEMAS.relative_to(REPO)) if SCHEMAS.is_relative_to(REPO)
                                      else str(SCHEMAS),
               "label": LABEL, "checks": [], "schemas": []}
    problems = []
    for rel, want in EXPECT.items():
        p = REPO / rel
        real = sha256_file(p) if p.exists() else "MISSING"
        man = (frozen.get("files", {}).get(rel) or {}).get("sha256")
        binding["checks"].append({"path": rel, "expected_sha256": want, "disk_sha256": real,
                                  "frozen_manifest_sha256": man,
                                  "disk_matches_expected": real == want})
        if real != want:
            problems.append(f"disk hash mismatch {rel}: {real} != {want}")
    for name in SCHEMA_NAMES:
        p = SCHEMAS / name
        rel = f"artifacts/formulation/schemas/{name}"
        man = (frozen.get("files", {}).get(rel) or {}).get("sha256")
        real = sha256_file(p)
        binding["schemas"].append({"path": str(p), "revision": schema_revision(p),
                                   "disk_sha256": real, "frozen_manifest_sha256": man,
                                   "frozen_manifest_matches_disk": man == real})
    binding["frozen_manifest_binds_schemas"] = all(
        s["frozen_manifest_matches_disk"] for s in binding["schemas"])
    binding["frozen_manifest_stale"] = not binding["frozen_manifest_binds_schemas"]
    if problems:
        raise SystemExit("BINDING ABORT: " + "; ".join(problems))
    if binding["frozen_manifest_stale"]:
        print("NOTE: FROZEN manifest does not bind the on-disk schemas "
              f"(manifest rev {binding['frozen_revision']}); measuring and recording disk hashes.",
              file=sys.stderr)
    return binding


def build_fixture(name: str, sentence: str) -> dict:
    base = WCC.read_bytes()
    if base.count(ANCHOR.encode()) != 1:
        raise SystemExit(f"anchor not unique in {WCC}")
    out = base.replace(ANCHOR.encode(), (ANCHOR[:-1] + sentence).encode())
    p = HERE / name
    p.write_bytes(out)
    return {"fixture": p.name, "sha256": sha256_file(p),
            "base": str(WCC.relative_to(REPO)) if WCC.is_relative_to(REPO) else str(WCC),
            "base_sha256": sha256_file(WCC), "bytes_added": len(out) - len(base),
            "mutation": f"append one sentence inside non_vacuity.condition (anchor {ANCHOR!r})"}


def run_spec(spec: dict, fixture: Path, kind: str) -> dict:
    cmd = [sys.executable, str(spec["path"]), str(fixture), "--json"]
    try:
        proc = subprocess.run(cmd, cwd=spec["cwd"], capture_output=True, text=True, timeout=90)
    except subprocess.TimeoutExpired:
        return {"verdict": "error", "rule_ids": [], "detail": "timeout(90s)"}
    raw = proc.stdout.strip()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {"verdict": "crash" if "Traceback" in proc.stderr else "error", "rule_ids": [],
                "detail": (proc.stderr.strip().splitlines() or [""])[-1][:160]}
    if kind == "flash11":
        rec = payload[0] if isinstance(payload, list) else payload
        return {"verdict": {"ACCEPT": "accept", "REJECT": "reject"}.get(rec.get("verdict"), "error"),
                "rule_ids": rec.get("failed_codes", []), "detail": rec.get("layout", "")}
    return {"verdict": "accept" if payload.get("verdict") == "pass" else
                       ("reject" if payload.get("verdict") == "fail" else "error"),
            "rule_ids": payload.get("failed_rules", []),
            "failures": payload.get("failures", payload.get("failed_checks", [])), "detail": ""}


def run(name: str, fixture: Path) -> dict:
    return run_spec(IMPLS[name], fixture, "flash11" if name == "flash11" else "canonical")


# (fixture, expect canonical_base, expect patched, expect flash11, rule)
LEAK = f"leak_{LABEL}.yaml"
CONTROL = f"control_{LABEL}.yaml"
CANON = f"{LABEL}_canonical"
TARGETS = [
    (LEAK, "accept", "reject", "reject", "R12"),
    (CONTROL, "accept", "accept", "accept", None),
    (f"{CANON}/canonical_af_wcc_vacuum.yaml", "accept", "accept", "accept", None),
    (f"{CANON}/canonical_af_scc_c2_vacuum.yaml", "accept", "accept", "accept", None),
    (f"{CANON}/canonical_af_scc_c0_vacuum.yaml", "accept", "accept", "accept", None),
    ("../fd13/leak_rev19.yaml", "accept", "reject", "reject", "R12"),      # historical comparator
    ("../fd13/control_rev19.yaml", "accept", "accept", "accept", None),    # historical comparator
]

out: dict = {
    "artifact": (f"FD-13 rebase measurement, label={LABEL} "
                 f"(unverified draft; no completion claim)"),
    "task_id": "FORM-DIFF-02",
    "assignment_event_id": "assign-FORM-DIFF-02-20260911T2331",
    "node_id": "F1",
    "group_id": "formulation",
    "gate": "G-CLASSBIND",
    "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
    "binding": check_binding(),
    "fixtures": [],
    "targets": [],
}

# ------- self-contained patched environment: patched tool + CURRENT rule_spec/KEY_MANIFEST
# check_class_schema.py resolves rule_spec.json and KEY_MANIFEST.json from Path(__file__).parents[1];
# the manifest is copied from a pinned snapshot so a live head move cannot silently change this run.
PATCHED_DIR = HERE / "patched"
(PATCHED_DIR / "tools").mkdir(parents=True, exist_ok=True)
(PATCHED_DIR / "tools/patched_check_class_schema.py").write_bytes(CANON_PATCHED.read_bytes())
(PATCHED_DIR / "rule_spec.json").write_bytes(RULE_SPEC.read_bytes())
KM_PIN = HERE / "key_manifest_014e2d30.json"
if KM_PIN.exists():
    assert sha256_file(KM_PIN) == EXPECT["artifacts/formulation/KEY_MANIFEST.json"]
    (PATCHED_DIR / "KEY_MANIFEST.json").write_bytes(KM_PIN.read_bytes())
else:
    (PATCHED_DIR / "KEY_MANIFEST.json").write_bytes(
        (REPO / "artifacts/formulation/KEY_MANIFEST.json").read_bytes())
assert sha256_file(PATCHED_DIR / "tools/patched_check_class_schema.py") == EXPECT[
    "artifacts/flash-11/f1_aux_class_binding/fd13/tools/patched_check_class_schema.py"]

# ------- byte copies of the three measured canonical schemas (hashes recorded in binding) ----
CASE_DIR.mkdir(exist_ok=True)
for src in (SCHEMAS / "af_wcc_vacuum.yaml", SCHEMAS / "af_scc_c2_vacuum.yaml",
            SCHEMAS / "af_scc_c0_vacuum.yaml"):
    (CASE_DIR / f"canonical_{src.name}").write_bytes(src.read_bytes())

built = {LEAK: build_fixture(LEAK, LEAK_SENTENCE),
         CONTROL: build_fixture(CONTROL, CONTROL_SENTENCE)}
out["fixtures"] = list(built.values())

for rel, e_base, e_patched, e_flash, rule in TARGETS:
    fx = (HERE / rel).resolve()
    row = {"fixture": rel, "abs_sha256": sha256_file(fx),
           "expect": {"canonical_base": e_base, "canonical_patched": e_patched, "flash11": e_flash},
           "expect_rule": rule, "verdicts": {}}
    for name in IMPLS:
        row["verdicts"][name] = run(name, fx)

    def ok(name: str, v: dict) -> bool:
        if v["verdict"] != row["expect"][name]:
            return False
        if row["expect"][name] == "reject" and rule and rule not in v["rule_ids"]:
            return False
        return True

    row["pass"] = all(ok(n, v) for n, v in row["verdicts"].items())
    out["targets"].append(row)

leaks = [r for r in out["targets"] if "leak" in r["fixture"] and not r["fixture"].startswith("../fd13/")]
controls = [r for r in out["targets"] if "leak" not in r["fixture"] and not r["fixture"].startswith("../fd13/")]
hist = [r for r in out["targets"] if r["fixture"].startswith("../fd13/")]
te = {
    "leaks_total": len(leaks),
    "leaks_base_escape": sum(1 for r in leaks if r["verdicts"]["canonical_base"]["verdict"] == "accept"),
    "leaks_flash11_catch": sum(1 for r in leaks if r["verdicts"]["flash11"]["verdict"] == "reject"),
    "leaks_patched_catch": sum(1 for r in leaks if r["verdicts"]["canonical_patched"]["verdict"] == "reject"),
    "controls_false_positive_base": sum(1 for r in controls if r["verdicts"]["canonical_base"]["verdict"] == "reject"),
    "controls_false_positive_patched": sum(1 for r in controls if r["verdicts"]["canonical_patched"]["verdict"] == "reject"),
    "controls_false_positive_flash11": sum(1 for r in controls if r["verdicts"]["flash11"]["verdict"] == "reject"),
}
out["targeted_effect"] = te
out["historical_rev19_fixtures"] = {
    "note": ("rev19-era fixtures are kept only as cross-revision comparators; under the rev28 "
             "KEY_MANIFEST they may be rejected at R22 for keys that no longer appear in the "
             "manifest. They are excluded from targeted_effect and from the falsifier."),
    "rows": [{"fixture": r["fixture"], "verdicts": {k: {"verdict": v["verdict"],
                                                        "rule_ids": v["rule_ids"]}
                                                    for k, v in r["verdicts"].items()}}
             for r in hist],
}

# ---- stale-environment control: same patched bytes, rev19 KEY_MANIFEST beside them ----
stale = {"tool": str(CANON_PATCHED.relative_to(REPO)),
         "key_manifest_beside_tool": "artifacts/flash-11/f1_aux_class_binding/fd13/KEY_MANIFEST.json",
         "key_manifest_sha256": sha256_file(CANON_PATCHED.parents[1] / "KEY_MANIFEST.json"),
         "current_key_manifest_sha256": EXPECT["artifacts/formulation/KEY_MANIFEST.json"],
         "note": ("R22 unknown-key failures seen with this environment are a stale-manifest artifact, "
                  "not an effect of the R12 patch: fd13/KEY_MANIFEST.json predates the rev26 "
                  "`binding_note` key."),
         "rows": []}
for rel, *_ in TARGETS:
    fx = (HERE / rel).resolve()
    v = run_spec(STALE_IMPL, fx, "canonical")
    stale["rows"].append({"fixture": rel, "verdict": v["verdict"], "rule_ids": v["rule_ids"]})
out["stale_env_control"] = stale

# ---- is FD-13 testable at the measured revision? ----
canon_rows = [r for r in out["targets"] if CANON in r["fixture"]]
base_rejects_canon = [r["fixture"] for r in canon_rows
                      if r["verdicts"]["canonical_base"]["verdict"] == "reject"]
leak_row = next(r for r in out["targets"] if r["fixture"] == LEAK)
if base_rejects_canon:
    first = next(r for r in canon_rows if r["verdicts"]["canonical_base"]["verdict"] == "reject")
    fails = [f for f in first["verdicts"]["canonical_base"].get("failures", [])
             if f.get("rule") in first["verdicts"]["canonical_base"]["rule_ids"]]
    out["head_interpretation"] = {
        "state": "MASKED_BY_R22",
        "detail": ("the measured canonical gate rejects the measured canonical schema(s) themselves, so "
                   "the R12 differential cannot be read at this revision: base rejects leak and controls "
                   "alike. The leak row is NOT evidence that FD-13 closed."),
        "canonical_rejected": base_rejects_canon,
        "example_failures": fails[:4],
    }
elif leak_row["verdicts"]["canonical_base"]["verdict"] == "accept":
    out["head_interpretation"] = {"state": "FD13_OPEN",
                                  "detail": "base accepts the leak; controls clean"}
else:
    out["head_interpretation"] = {
        "state": "FD13_CLOSED_AT_HEAD",
        "detail": f"base rejects the leak with {leak_row['verdicts']['canonical_base']['rule_ids']}"}
live = REPO / "artifacts/formulation/schemas"
out["stability"] = {
    "key_manifest_after_run_sha256": sha256_file(REPO / "artifacts/formulation/KEY_MANIFEST.json"),
    "key_manifest_stable_during_run":
        sha256_file(REPO / "artifacts/formulation/KEY_MANIFEST.json")
        == EXPECT["artifacts/formulation/KEY_MANIFEST.json"],
    "measured_schemas_equal_live_disk": all(
        sha256_file(SCHEMAS / name) == sha256_file(live / name) for name in SCHEMA_NAMES),
    "measured_schema_dir": str(SCHEMAS.relative_to(REPO)) if SCHEMAS.is_relative_to(REPO) else str(SCHEMAS),
}

out["delta_vs_rev19"] = {
    "tool_unchanged": EXPECT["artifacts/formulation/tools/check_class_schema.py"] == sha256_file(CANON_BASE),
    "rule_spec_unchanged": EXPECT["artifacts/formulation/rule_spec.json"] == sha256_file(RULE_SPEC),
    "key_manifest_changed": "rev19 8ce752b5 -> rev26 fce91948 (adds `binding_note`)",
    "wcc_schema": {"rev19_base": "f962c117 (recorded in fd13/build_manifest.json)",
                   "rev26_base": "9a8bd4c96800 (recorded in rev26_snapshot/)",
                   f"{LABEL}_base": sha256_file(WCC)[:12]},
    "prior_fd13_collateral_sweep_still_valid": (
        "patched tool 5eaab3f8 and base tool 000e09e4 are byte-identical to the fd13 sweep; "
        "57/57 corpus fixtures identical, 0 verdict changes, provided the patched tool is run "
        "with a KEY_MANIFEST at least as new as the fixtures"),
}
out["falsifier"] = {
    "statement": (f"FIRED IF: (a) the measured canonical gate REJECTS {LEAK} (FD-13 no longer "
                  "reproduces -> the finding is superseded/closed), or (b) it rejects a control or a "
                  "measured canonical schema (false positive), or (c) the independent flash11 gate no "
                  "longer rejects a leak or rejects a control (false negative/positive), or (d) any "
                  "asserted tool/rule_spec/KEY_MANIFEST/independent-gate hash does not match on disk "
                  "(binding abort happens before measurement)."),
    "measured_status": "not fired" if (te["leaks_base_escape"] == te["leaks_total"]
                                       and te["controls_false_positive_base"] == 0
                                       and te["leaks_flash11_catch"] == te["leaks_total"]
                                       and te["controls_false_positive_flash11"] == 0) else "FIRED",
}
out["proposal_falsifier"] = {
    "statement": ("The fd13 proposal's own falsifier: FIRED if the patched gate rejects a legitimate "
                  "schema the base accepted (false positive) or fails to reject a leak (false negative), "
                  "run with a current KEY_MANIFEST beside the patched tool."),
    "measured_status": "not fired" if (te["leaks_patched_catch"] == te["leaks_total"]
                                       and te["controls_false_positive_patched"] == 0) else "FIRED",
    "stale_env_confound": ("if the patched tool is instead run from fd13/tools/ beside the rev19 "
                           "KEY_MANIFEST (8ce752b5), R22 fires on every fixture containing the rev26 "
                           "`binding_note` key (see stale_env_control); that is an environment defect, "
                           "not an R12 effect"),
}
out["caveats"] = [
    "Format-dominated rejections: the canonical gate rejects non-canonical layouts at R01/R02 before "
    "R12; agreement at corpus level is not semantic agreement. Fixtures here keep the canonical layout.",
    "R12 is a lexical token scan even when patched; a leak phrased without inextendib/extension/horizon "
    "tokens is out of scope (worker-06 owns the rephrased corpus).",
    "The patch is a proposal only; artifacts/formulation/tools/check_class_schema.py was NOT modified.",
    "No node completion, no theorem, no physics result. Schema owner (lead-formulation) binds interpretation.",
]
if out["binding"]["frozen_manifest_stale"]:
    out["caveats"].append(
        "FROZEN.json is stale w.r.t. the measured schemas (rev26 manifest vs on-disk rev "
        f"{[s['revision'] for s in out['binding']['schemas']]}); the measurement binds the disk "
        "sha256s recorded in binding.schemas, not the manifest revision.")

(HERE / f"{LABEL}_results.json").write_text(json.dumps(out, indent=1, sort_keys=True))

print(json.dumps({"label": LABEL, "targeted_effect": te, "falsifier": out["falsifier"]["measured_status"],
                  "proposal_falsifier": out["proposal_falsifier"]["measured_status"],
                  "frozen_revision": out["binding"]["frozen_revision"],
                  "frozen_manifest_stale": out["binding"]["frozen_manifest_stale"],
                  "schema_revisions": {s["path"].split("/")[-1]: s["revision"]
                                       for s in out["binding"]["schemas"]}}, indent=1))
for r in out["targets"]:
    print(f"{r['fixture']:45s} base={r['verdicts']['canonical_base']['verdict']:6s} "
          f"rules={','.join(r['verdicts']['canonical_base']['rule_ids']) or '-':8s} "
          f"patched={r['verdicts']['canonical_patched']['verdict']:6s} "
          f"flash11={r['verdicts']['flash11']['verdict']:6s} pass={r['pass']}")
