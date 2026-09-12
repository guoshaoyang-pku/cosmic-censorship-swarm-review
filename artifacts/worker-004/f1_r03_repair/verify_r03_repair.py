#!/usr/bin/env python3
"""W004-F1-R03-REPAIR-01: adjudicate and repair the stage-2 R03 rejection of F1.

Class-bound task (self-selected from the live queue; no inbox card for worker-004 at
2026-09-12T00:45+08:00):

  class : AF-WCC-VAC-GEN
  node  : F1
  gates : G-FORM (F1 content acceptance) / G-AUDIT (calibration evidence)

PROBLEM.  At the frozen canonical bytes schemas/af_wcc_vacuum.yaml#cce9c60146d6 the
binding structural stage passes, but the adopted semantic stage
(artifacts/worker-06/spec_conformance_audit.py#c79d8ab8440a, baseline AND hardened)
rejects on R03 alone: "binder '(q,t0)' absent from formal sentence".  The same failure
is reported by worker-016, worker-068 and worker-080; worker-080 classified it as a
lexical false positive with a probe but produced no repaired rule and no end-to-end
re-measurement.  The two-stage acceptance pipeline therefore cannot report a valid
calibration run at the frozen F1 revision.

WHAT THIS SCRIPT DOES (read-only on every canonical path; all writes under
artifacts/worker-004/f1_r03_repair/ and the report path):

  1. pins every input by sha256 and fails closed on drift;
  2. reproduces the R03 failure and decomposes it (literal-token vs identifier
     coverage, quantifier-scope sequence), independent of the original report;
  3. builds a minimal, byte-diffed repair of the R03 binder check in an artifact-local
     copy of the auditor (the canonical tool is never written);
  4. runs a rule-level control battery: true defects must still be caught by the
     repaired rule (absent identifier, extra composite component, missing clause),
     and the full per-rule verdict vector of the three canonical schemas must be
     unchanged except for F1/R03;
  5. runs the semantic-contract suite end-to-end in artifact-local shadow repos, two
     runs differing only in the auditor bytes, with the frozen F1 rev12 bytes bound as
     the F1 conforming-canonical control, and reports exit code, validity, control and
     canonical acceptance and mutant catch counts.

HARNESS NOTE (disclosed, not hidden): the live calibration corpus is simultaneously
stale in two directions -- the rev27 KEY_MANIFEST admits the rebased controls but
rejects the live schemas (R22), the rev28 KEY_MANIFEST admits the live schemas but
rejects the rebased controls (R22).  To isolate the R03 variable the shadow suite uses
the union allowlist (272 keys, rev27 U rev28) as a harness-only input.  The union is
not proposed here as a canonical artifact; the KEY_MANIFEST instability is already
reported separately (W004-SEMCT-CONTROL-REBASE-02 blocker, worker-080).

AUTHORITY.  Worker event only: this is a measurement plus a repair proposal for the
owners (auditor: worker-06 / lead-audit; canonical schema: lead-formulation).  It sets
no gate verdict, no node status and no validation_status=passed.

Usage:  python3 artifacts/worker-004/f1_r03_repair/verify_r03_repair.py
Exit :  0 all checks ran; 2 pin drift / integrity failure.
"""
from __future__ import annotations

import copy
import difflib
import hashlib
import json
import py_compile
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
CST = timezone(timedelta(hours=8))


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# --------------------------------------------------------------------------------------
# 1. PINS
# --------------------------------------------------------------------------------------
PINS = {
    "schemas/af_wcc_vacuum.yaml":
        "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3",
    "schemas/af_scc_c2_vacuum.yaml":
        "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce",
    "schemas/af_scc_c0_vacuum.yaml":
        "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6",
    "artifacts/worker-06/spec_conformance_audit.py":
        "c79d8ab8440ac6738bb61df5a33e9fd5f8319b4e74e1f2e9c0fc5083fb408cec",
    "artifacts/formulation/tools/check_class_schema.py":
        "000e09e46b2fb4abc047c21e99165cbc55692f3132744fb27e84645609263aff",
    "artifacts/formulation/rule_spec.json":
        "40f9bb9e657b2c6b0cce04a9c05e9cdbf18083669060727a8e31d83031f5901e",
    "schemas/semantic_contract_tests/run_contract_tests.py":
        "3be197c3729cebb51d43d9c3da87a0325743f399faf65cd7cb9cf293eee9b2f3",
    "schemas/semantic_contract_tests/manifest.json":
        "b2e8bd17892b6c5eba1b2d7dde48c9205d07854d025df042fb7a3d919a574f65",
    "artifacts/worker-061/f1_rev12_gate/pinned/hist/KEY_MANIFEST.rev27.json":
        "fce91948ba3a59a5bd34c8bcb03202ee479a95dbc3e4d6c327a0c4d1a9170d33",
    "artifacts/formulation/KEY_MANIFEST.json":
        "014e2d3019781632cdb78ace266cf08cc11f9cf8b8ef0a049beb74eb9c6b6b9a",
    "artifacts/worker-004/semct_control_rebase/rebased_controls/control_comment_only_composite.yaml":
        "2babcc7d3430d66578a7100543c3f654136ae53438e59966879b1b9a02432578",
    "artifacts/worker-004/semct_control_rebase/rebased_controls/control_conforming_base.yaml":
        "7ab748114243cbf48497326fefba65d26524455068f459410f6ee35eda1508cd",
    "artifacts/worker-004/semct_control_rebase/rebased_controls/control_quoted_forbidden_phrase.yaml":
        "47dd3f9ec2857bd1727c6c364eecc196c22ec3b77c3c37b266e405df8bee9d12",
    "schemas/semantic_contract_tests/fixtures/controls/control_comment_only_composite.yaml":
        "a6ad2638dc993c32f7cc46a1a84441581ab785ba02c84a5197663e6284c86f2a",
    "schemas/semantic_contract_tests/fixtures/controls/control_conforming_base.yaml":
        "7b910cf34e64baa7d2d02e229f7bfb5224ffb3fa70d264e1cc1f5ec3173e41eb",
    "schemas/semantic_contract_tests/fixtures/controls/control_quoted_forbidden_phrase.yaml":
        "687fd697130497633e63b696ac90d0939c2699fd6d5f3b1bca06b55f5948dee6",
}

F1 = "schemas/af_wcc_vacuum.yaml"
C2 = "schemas/af_scc_c2_vacuum.yaml"
C0 = "schemas/af_scc_c0_vacuum.yaml"
AUDITOR = "artifacts/worker-06/spec_conformance_audit.py"
STRUCT = "artifacts/formulation/tools/check_class_schema.py"
RUNNER = "schemas/semantic_contract_tests/run_contract_tests.py"
MANIFEST = "schemas/semantic_contract_tests/manifest.json"
KM27 = "artifacts/worker-061/f1_rev12_gate/pinned/hist/KEY_MANIFEST.rev27.json"
KM28 = "artifacts/formulation/KEY_MANIFEST.json"
REBASED = "artifacts/worker-004/semct_control_rebase/rebased_controls"
STALE = "schemas/semantic_contract_tests/fixtures"

CONTROL_FILES = {
    "SCT-C01": "control_comment_only_composite.yaml",
    "SCT-C02": "control_conforming_base.yaml",
    "SCT-C03": "control_quoted_forbidden_phrase.yaml",
}
CANON_FILES = {
    "SCT-K01": C0,
    "SCT-K02": C2,
    "SCT-K03": F1,
}

NO_ABSENT_TOKEN_MSG = "absent from formal sentence"

# The exact 4-line block in the pinned auditor that implements the literal R03 binder
# check (verified by exact-match count == 1 at run time).
OLD_BLOCK = (
    '            else:\n'
    '                for b in binders:\n'
    '                    if b not in formal:\n'
    "                        bad.append(f\"binder {b!r} absent from formal sentence\")\n"
)
NEW_BLOCK = (
    '            else:\n'
    '                for b in binders:\n'
    '                    # R03 repair proposal (worker-004 W004-F1-R03-REPAIR-01):\n'
    '                    # a binder may be a composite tuple such as "(q,t0)"; require\n'
    '                    # every identifier component to occur in the formal sentence\n'
    '                    # as a whole word instead of requiring the literal tuple token.\n'
    '                    # Power control: any genuinely absent component (or an extra\n'
    '                    # component absent from formal) is still reported.\n'
    '                    _toks = [t for t in re.split(r"[^0-9A-Za-z_]+", str(b)) if t]\n'
    '                    _missing = [t for t in _toks if not re.search(\n'
    '                        r"(?<![0-9A-Za-z_])" + re.escape(t) + r"(?![0-9A-Za-z_])", formal)]\n'
    '                    if _missing:\n'
    "                        bad.append(f\"binder {b!r} absent from formal sentence (missing {_missing})\")\n"
)

IDENT_RE = re.compile(r"[^0-9A-Za-z_]+")
QUANT_RE = re.compile(r"\b(not\s+exists|exists_unique|exists|forall)\b")


def binder_tokens(b) -> list:
    return [t for t in IDENT_RE.split(str(b)) if t]


def token_present(tok: str, formal: str) -> bool:
    return re.search(r"(?<![0-9A-Za-z_])" + re.escape(tok) + r"(?![0-9A-Za-z_])", formal) is not None


def quantifier_sequence(formal: str) -> list:
    seq = []
    for m in QUANT_RE.finditer(formal):
        seq.append(m.group(1).replace(" ", "_"))
    return seq


def run_auditor(tool: Path, target: Path, hardened: bool = False) -> dict:
    # --spec is passed explicitly: the auditor's default resolves relative to its own
    # directory, which is wrong for the artifact-local patched copy.
    out = HERE / "tmp" / f"audit_{tool.parent.name}_{target.stem}_{'h' if hardened else 'b'}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, str(tool), str(target), "--spec",
           str(REPO / "artifacts" / "formulation" / "rule_spec.json"),
           "--json", str(out)]
    if hardened:
        cmd.insert(-2, "--hardened")
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    rep = {}
    if out.exists():
        try:
            rep = json.loads(out.read_text())
        finally:
            out.unlink()
    return {"exit": proc.returncode, "verdict": rep.get("verdict", "no_verdict"),
            "failed_rules": rep.get("failed_rules", []),
            "checks": rep.get("checks", []),
            "stderr": proc.stderr.strip()[-300:]}


def rule_vector(rep: dict) -> dict:
    """rule -> (verdict, detail) for exact before/after comparison."""
    return {r.get("rule"): (r.get("verdict"), r.get("detail", "")) for r in rep.get("checks", [])}


def run_selftest(tool: Path, hardened: bool = False) -> dict:
    cmd = [sys.executable, str(tool), "--spec",
           str(REPO / "artifacts" / "formulation" / "rule_spec.json"), "--selftest"]
    if hardened:
        cmd.append("--hardened")
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    try:
        rep = json.loads(proc.stdout[proc.stdout.index("{"):])
    except (ValueError, json.JSONDecodeError):
        rep = {}
    return {"exit": proc.returncode, "fixtures": rep.get("fixtures"),
            "caught": rep.get("caught"), "missed": rep.get("missed"),
            "controls": [c.get("verdict") for c in
                         rep.get("controls", {}).get("positive_controls", [])]}


def staged_selftest_tool(src_tool: Path, tag: str) -> Path:
    """Copy a tool to a directory shaped like artifacts/worker-06 so that its own
    selftest finds semantic_fixtures/ relative to itself (both copies identical env)."""
    d = HERE / "tmp" / tag / "artifacts" / "worker-06"
    d.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src_tool, d / "spec_conformance_audit.py")
    fx = REPO / "artifacts" / "worker-06" / "semantic_fixtures"
    if fx.exists():
        shutil.copytree(fx, d / "semantic_fixtures", dirs_exist_ok=True)
    return d / "spec_conformance_audit.py"


def run_structural(tool: Path, target: Path) -> dict:
    proc = subprocess.run([sys.executable, str(tool), "--json", str(target)],
                          capture_output=True, text=True, timeout=300)
    try:
        rep = json.loads(proc.stdout[proc.stdout.index("{"):])
    except (ValueError, json.JSONDecodeError):
        rep = {}
    return {"exit": proc.returncode, "verdict": rep.get("verdict", "no_verdict"),
            "failed_rules": rep.get("failed_rules", [])}


# --------------------------------------------------------------------------------------
# 2. SHADOW SUITE
# --------------------------------------------------------------------------------------
def build_shadow(root: Path, auditor_src: Path, controls: str, tag: str) -> dict:
    """Artifact-local shadow repo with the suite; auditor bytes are the only variable."""
    if root.exists():
        shutil.rmtree(root)
    suite = root / "artifacts" / "worker-004" / "suite"
    (root / "artifacts" / "formulation" / "tools").mkdir(parents=True)
    (root / "artifacts" / "worker-06").mkdir(parents=True)
    suite.mkdir(parents=True)

    shutil.copy2(REPO / STRUCT, root / "artifacts" / "formulation" / "tools" / "check_class_schema.py")
    shutil.copy2(REPO / "artifacts" / "formulation" / "rule_spec.json",
                 root / "artifacts" / "formulation" / "rule_spec.json")
    shutil.copy2(auditor_src, root / "artifacts" / "worker-06" / "spec_conformance_audit.py")

    # Harness-only union allowlist (rev27 U rev28): admits both the live schemas and the
    # rebased controls so that the semantic stage is the only stage that decides.  See
    # module docstring; not proposed as a canonical artifact.
    a27 = set(json.loads((REPO / KM27).read_text())["allowed_keys"])
    a28 = set(json.loads((REPO / KM28).read_text())["allowed_keys"])
    union = sorted(a27 | a28)
    (root / "artifacts" / "formulation" / "KEY_MANIFEST.json").write_text(
        json.dumps({"allowed_keys": union}))

    shutil.copytree(REPO / "schemas" / "semantic_contract_tests" / "fixtures",
                    suite / "fixtures")
    if controls == "rebased":
        for name in CONTROL_FILES.values():
            shutil.copy2(REPO / REBASED / name, suite / "fixtures" / "controls" / name)
    elif controls != "stale":
        raise SystemExit("controls must be rebased|stale (fails closed)")

    src_text = (REPO / RUNNER).read_text()
    old_line = "REPO = HERE.parent.parent\n"
    new_line = "REPO = HERE.parents[2]  # patched by worker-004 W004-F1-R03-REPAIR-01 shadow\n"
    if src_text.count(old_line) != 1:
        raise SystemExit("runner REPO line not found exactly once (fails closed)")
    (suite / "run_contract_tests.py").write_text(src_text.replace(old_line, new_line, 1))

    man = json.loads((REPO / MANIFEST).read_text())
    snap_dir = suite / "fixtures" / "canonical_snapshot"
    snap_dir.mkdir(parents=True, exist_ok=True)
    patch_ops = []
    for e in man["controls"]:
        tid = e["test_id"]
        new = sha(suite / "fixtures" / "controls" / CONTROL_FILES[tid])
        patch_ops.append({"test_id": tid, "field": "sha256", "old": e["sha256"], "new": new})
        if controls == "rebased":
            e["rebased_from_sha256"] = e["sha256"]
            e["sha256"] = new
            e["note"] = e["note"] + " [rebased 2026-09-12 (worker-004 W004-SEMCT-CONTROL-REBASE-02)]"
        elif new != e["sha256"]:
            raise SystemExit(f"stale control hash mismatch {tid} (fails closed)")
    for e in man["conforming_canonical_controls"]:
        tid = e["test_id"]
        src = REPO / CANON_FILES[tid]
        snap = snap_dir / Path(CANON_FILES[tid]).name
        shutil.copy2(src, snap)
        new = sha(snap)
        patch_ops.append({"test_id": tid, "field": "fixture", "old": e["fixture"],
                          "new": f"fixtures/canonical_snapshot/{snap.name}"})
        patch_ops.append({"test_id": tid, "field": "sha256", "old": e["sha256"], "new": new})
        e["canonical_path"] = CANON_FILES[tid]
        e["snapshot_source_sha256"] = new
        e["snapshot_at"] = now()
        e["fixture"] = f"fixtures/canonical_snapshot/{snap.name}"
        e["sha256"] = new
    man["copy_provenance"] = {
        "built_by": "worker-004",
        "built_at": now(),
        "kind": f"shadow-repo suite copy ({controls} controls, live canonical pins, union harness allowlist)",
        "canonical_manifest_sha256": sha(REPO / MANIFEST),
        "canonical_runner_sha256": sha(REPO / RUNNER),
        "key_manifest_union": {"rev27_sha256": sha(REPO / KM27), "rev28_sha256": sha(REPO / KM28),
                               "allowed_keys": len(union)},
        "rule_spec_sha256": sha(REPO / "artifacts" / "formulation" / "rule_spec.json"),
        "runner_patch": "REPO = HERE.parent.parent -> HERE.parents[2] (one line, shadow path resolution)",
    }
    (suite / "manifest.json").write_text(json.dumps(man, indent=1) + "\n")
    return {"tag": tag, "shadow_root": str(root.relative_to(REPO)), "suite": str(suite.relative_to(REPO)),
            "controls_mode": controls, "auditor_sha256": sha(root / "artifacts" / "worker-06" / "spec_conformance_audit.py"),
            "allowlist_size": len(union), "patch_ops": patch_ops}


def run_suite(suite: Path, tag: str) -> dict:
    # remove stale observed verdicts so a crashed run cannot be mistaken for a run
    obs_path = suite / "observed_verdicts.json"
    if obs_path.exists():
        obs_path.unlink()
    proc = subprocess.run([sys.executable, str(suite / "run_contract_tests.py")],
                          capture_output=True, text=True, timeout=1800)
    (HERE / "logs").mkdir(parents=True, exist_ok=True)
    (HERE / "logs" / f"{tag}.stdout.log").write_text(proc.stdout)
    (HERE / "logs" / f"{tag}.stderr.log").write_text(proc.stderr)
    obs = json.loads(obs_path.read_text()) if obs_path.exists() else {}
    # save a private copy (the next run in the same suite dir overwrites observed_verdicts)
    saved = None
    if obs:
        saved = HERE / "observed" / f"{tag}.json"
        saved.parent.mkdir(parents=True, exist_ok=True)
        saved.write_text(json.dumps(obs, indent=1) + "\n")
    rows = {}
    for r in obs.get("results", []):
        rows[r["test_id"]] = {"kind": r.get("kind"), "observed": r["observed"]["verdict"],
                              "accepted_by": r["observed"]["accepted_by"],
                              "rejected_by": r["observed"]["rejected_by"],
                              "failed_rules": {k: v.get("failed_rules")
                                               for k, v in r["observed"]["stages"].items()}}
    return {"tag": tag, "exit": proc.returncode,
            "stdout_tail": proc.stdout.strip().splitlines()[-6:],
            "summary": obs.get("summary", {}), "validity": obs.get("validity", {}),
            "stage_hashes": obs.get("stage_hashes", {}),
            "rows": rows,
            "observed_verdicts_copy": str(saved.relative_to(REPO)) if saved else None}


def normalized_projection(run: dict) -> dict:
    """Volatile-free projection for determinism comparison (no run_at / manifest sha)."""
    return {"exit": run["exit"], "summary": run["summary"], "validity": run["validity"],
            "rows": run["rows"]}


# --------------------------------------------------------------------------------------
# 3. MAIN
# --------------------------------------------------------------------------------------
def main() -> int:
    # ---- pins ----
    pin_report = {}
    for rel, want in PINS.items():
        p = REPO / rel
        if not p.exists():
            print(f"FATAL: pinned input missing: {rel}", file=sys.stderr)
            return 2
        got = sha(p)
        pin_report[rel] = {"sha256": got, "expected": want, "match": got == want}
        if got != want:
            print(f"FATAL: pin drift {rel}: {got} != {want}", file=sys.stderr)
            return 2

    out = {"task": "W004-F1-R03-REPAIR-01", "created_at": now(), "actor": "worker-004",
           "class_id": "AF-WCC-VAC-GEN", "node_id": "F1", "gates": ["G-FORM", "G-AUDIT"],
           "authority": "worker measurement + repair proposal; no gate verdict, no node status, "
                        "no canonical artifact written",
           "pins": pin_report}

    # ---- 1. adjudication at the pinned bytes ----
    f1_doc = yaml.safe_load((REPO / F1).read_text())
    q = f1_doc["quantifiers"]
    ordered = q["ordered"]
    formal = q["formal"]
    binder_rows = []
    for i, e in enumerate(ordered):
        b = str(e["binder"])
        toks = binder_tokens(b)
        binder_rows.append({
            "index": i, "kind": e["kind"], "binder": b, "domain_id": e["domain_id"],
            "literal_in_formal": b in formal,
            "tokens": toks,
            "tokens_in_formal": {t: token_present(t, formal) for t in toks},
            "resolution": ("literal" if b in formal else
                           ("identifier-covered" if toks and all(token_present(t, formal) for t in toks)
                            else "MISSING-IDENTIFIER")),
        })
    f1_text = (REPO / F1).read_text()
    ordered_line = next((n for n, line in enumerate(f1_text.splitlines(), 1)
                         if 'binder: "(q,t0)"' in line), None)
    seq = quantifier_sequence(formal)
    kinds_seq = [e["kind"] for e in ordered]
    out["adjudication"] = {
        "schema": F1, "schema_sha256": sha(REPO / F1),
        "ordered_entry_line_for_q_t0": ordered_line,
        "binder_rows": binder_rows,
        "literal_misses": [r["binder"] for r in binder_rows if not r["literal_in_formal"]],
        "missing_identifiers": {r["binder"]: [t for t, ok in r["tokens_in_formal"].items() if not ok]
                                for r in binder_rows if not all(r["tokens_in_formal"].values())},
        "formal_quantifier_sequence": seq,
        "ordered_kind_sequence": kinds_seq,
        "quantifier_sequence_matches": seq == kinds_seq,
        "conclusion": ("R03 fires only on the composite token '(q,t0)'; every identifier "
                       "component (q, t0) occurs in quantifiers.formal as a whole word, and the "
                       "formal quantifier sequence matches the ordered kind sequence exactly. "
                       "At these bytes the R03 rejection is a literal-token (lexical) false "
                       "positive, not a missing quantifier."
                       if seq == kinds_seq and not any(
                           not all(r["tokens_in_formal"].values()) for r in binder_rows)
                       else "R03 identifies a real quantifier/binder defect at these bytes."),
    }

    # stage verdicts at the pinned bytes (unpatched)
    unpinned_auditor = REPO / AUDITOR
    stage_table = {}
    for rel in (F1, C2, C0):
        tgt = REPO / rel
        stage_table[rel] = {
            "structural": run_structural(REPO / STRUCT, tgt),
            "semantic_baseline": run_auditor(unpinned_auditor, tgt, False),
            "semantic_hardened": run_auditor(unpinned_auditor, tgt, True),
        }
    out["unpatched_stage_table"] = stage_table

    # ---- 2. build the repaired auditor (artifact-local) ----
    patched_dir = HERE / "patched"
    patched_dir.mkdir(parents=True, exist_ok=True)
    src = (REPO / AUDITOR).read_text()
    if src.count(OLD_BLOCK) != 1:
        print("FATAL: R03 block not found exactly once in the pinned auditor (fails closed)",
              file=sys.stderr)
        return 2
    patched_text = src.replace(OLD_BLOCK, NEW_BLOCK, 1)
    patched_path = patched_dir / "spec_conformance_audit.py"
    patched_path.write_text(patched_text)
    diff = "".join(difflib.unified_diff(
        src.splitlines(keepends=True), patched_text.splitlines(keepends=True),
        fromfile="a/artifacts/worker-06/spec_conformance_audit.py",
        tofile="b/artifacts/worker-004/f1_r03_repair/patched/spec_conformance_audit.py"))
    (patched_dir / "r03_binder_token_aware.patch").write_text(diff)
    py_compile.compile(str(patched_path), doraise=True)
    st_tools = {"unpatched": staged_selftest_tool(unpinned_auditor, "selftest_unpatched"),
                "patched": staged_selftest_tool(patched_path, "selftest_patched")}
    selftest_base = [run_selftest(st_tools["unpatched"], h) for h in (False, True)]
    selftest_patched = [run_selftest(st_tools["patched"], h) for h in (False, True)]
    out["patch"] = {
        "source_sha256": sha(REPO / AUDITOR),
        "patched_sha256": sha(patched_path),
        "patch_sha256": sha(patched_dir / "r03_binder_token_aware.patch"),
        "hunks": diff.count("@@ "),
        "old_block_occurrences": src.count(OLD_BLOCK),
        "old_block": OLD_BLOCK, "new_block": NEW_BLOCK,
        "selftest_unpatched": selftest_base,
        "selftest_patched": selftest_patched,
        "selftest_unchanged": selftest_base == selftest_patched,
    }

    # ---- 3. rule-level controls: repaired rule must still catch true defects ----
    patched = patched_path
    mutants = {}

    def add_mutant(name, path, expectation, note):
        mutants[name] = {"path": str(path.relative_to(REPO)) if str(path).startswith(str(REPO)) else str(path),
                         "expectation": expectation, "note": note,
                         "unpatched_baseline": run_auditor(unpinned_auditor, path, False),
                         "unpatched_hardened": run_auditor(unpinned_auditor, path, True),
                         "patched_baseline": run_auditor(patched, path, False),
                         "patched_hardened": run_auditor(patched, path, True)}

    mdir = HERE / "tmp" / "mutants"
    mdir.mkdir(parents=True, exist_ok=True)
    raw_f1 = (REPO / F1).read_text()

    # M-A: drop the whole quantifiers block
    d = copy.deepcopy(f1_doc); d.pop("quantifiers", None)
    p = mdir / "MA_drop_quantifiers.yaml"; p.write_text(yaml.safe_dump(d, sort_keys=False))
    add_mutant("M-A_drop_quantifiers", p, "reject R03", "structural defect; R03 must fire")

    # M-B: unresolved domain id on the final quantifier
    d = copy.deepcopy(f1_doc); d["quantifiers"]["ordered"][5]["domain_id"] = "D9"
    p = mdir / "MB_unresolved_domain.yaml"; p.write_text(yaml.safe_dump(d, sort_keys=False))
    add_mutant("M-B_unresolved_domain", p, "reject R03", "structural defect; R03 must fire")

    # M-C: delete the final not-exists clause from the formal sentence
    clause = ("    not exists q in I+ and t0 in [0,T) with gamma([t0,T)) subset J^-(q) "
              "intersect M.\n")
    if raw_f1.count(clause) != 1:
        print("FATAL: final not-exists clause not found exactly once (fails closed)", file=sys.stderr)
        return 2
    p = mdir / "MC_drop_final_clause.yaml"; p.write_text(raw_f1.replace(clause, "", 1))
    add_mutant("M-C_drop_final_not_exists", p, "reject R03",
               "quantifier genuinely absent; both rules must fire (repaired rule on missing q,t0)")

    # M-D: rename t0 -> t9 everywhere in the formal sentence only
    p = mdir / "MD_rename_t0.yaml"
    p.write_text(raw_f1.replace("t0 in [0,T)", "t9 in [0,T)").replace("gamma([t0,T))", "gamma([t9,T))"))
    add_mutant("M-D_rename_t0_in_formal", p, "reject R03",
               "declared binder component t0 genuinely absent from formal")

    # M-E: extra composite component in the ordered binder
    d = copy.deepcopy(f1_doc); d["quantifiers"]["ordered"][5]["binder"] = "(q,t0,t1)"
    p = mdir / "ME_extra_binder_component.yaml"; p.write_text(yaml.safe_dump(d, sort_keys=False))
    add_mutant("M-E_extra_binder_component", p, "reject R03",
               "component t1 absent from formal; repaired rule must not accept")

    # M-F: formal sentence emptied
    d = copy.deepcopy(f1_doc); d["quantifiers"]["formal"] = "suitable"
    p = mdir / "MF_vague_formal.yaml"; p.write_text(yaml.safe_dump(d, sort_keys=False))
    add_mutant("M-F_formal_emptied", p, "reject R03", "formal content absent")

    # M-G (boundary, measured honestly): composite binder components swapped
    d = copy.deepcopy(f1_doc); d["quantifiers"]["ordered"][5]["binder"] = "(t0,q)"
    p = mdir / "MG_component_order_swapped.yaml"; p.write_text(yaml.safe_dump(d, sort_keys=False))
    add_mutant("M-G_component_order_swapped", p, "boundary: order-insensitive accept expected",
               "not a truth defect; recorded to document the repaired rule's sensitivity boundary")

    out["rule_controls"] = {
        "M-A..M-F are true defects (expect reject R03 under both rules); "
        "M-G is a notation-order boundary": True,
        "mutants": mutants,
    }

    # no-other-rule-change: full per-rule verdict vector, patched vs unpatched
    rule_diff = {}
    for rel in (F1, C2, C0):
        tgt = REPO / rel
        for mode, hard in (("baseline", False), ("hardened", True)):
            a = rule_vector(run_auditor(unpinned_auditor, tgt, hard))
            b = rule_vector(run_auditor(patched, tgt, hard))
            changes = {}
            for k in sorted(set(a) | set(b)):
                if a.get(k) != b.get(k):
                    changes[k] = {"unpatched": a.get(k), "patched": b.get(k)}
            rule_diff[f"{rel}::{mode}"] = {
                "rules_compared": len(set(a) | set(b)),
                "changes": changes,
                "only_r03_on_f1": (set(changes) <= {"R03"}) and (not changes or rel == F1),
            }
    out["rule_vector_diff"] = rule_diff

    # ---- 4. end-to-end shadow suite ----
    st = REPO / STRUCT
    # safety: structural tool copy in shadow is byte-identical; confirm on the live one too
    shadows = {}
    runs = {}
    print("building shadow repo: unpatched auditor ...", flush=True)
    shadows["unpatched"] = build_shadow(HERE / "shadow_unpatched", unpinned_auditor, "rebased", "unpatched")
    print("building shadow repo: patched auditor ...", flush=True)
    shadows["patched"] = build_shadow(HERE / "shadow_patched", patched_path, "rebased", "patched")
    print("building shadow repo: patched auditor + stale controls (negative control) ...", flush=True)
    shadows["patched_stale"] = build_shadow(HERE / "shadow_patched_stale", patched_path, "stale", "patched_stale")
    out["shadows"] = shadows

    suite_unpatched = REPO / shadows["unpatched"]["suite"]
    suite_patched = REPO / shadows["patched"]["suite"]
    suite_patched_stale = REPO / shadows["patched_stale"]["suite"]

    print("run 1/4: shadow, unpatched auditor, rebased controls, live canonical ...", flush=True)
    runs["unpatched_rebased_live"] = run_suite(suite_unpatched, "unpatched_rebased_live")
    print("run 2/4: shadow, patched auditor, rebased controls, live canonical ...", flush=True)
    runs["patched_rebased_live"] = run_suite(suite_patched, "patched_rebased_live")
    print("run 3/4: rerun for determinism ...", flush=True)
    runs["patched_rebased_live_rerun"] = run_suite(suite_patched, "patched_rebased_live_rerun")
    print("run 4/4: negative control, patched auditor + stale controls ...", flush=True)
    runs["patched_stale_live"] = run_suite(suite_patched_stale, "patched_stale_live")
    out["suite_runs"] = runs

    # expectations
    up = runs["unpatched_rebased_live"]
    pa = runs["patched_rebased_live"]
    pa2 = runs["patched_rebased_live_rerun"]
    ps = runs["patched_stale_live"]
    canon_f1_unpatched = up["rows"].get("SCT-K03", {})
    canon_f1_patched = pa["rows"].get("SCT-K03", {})

    def rejected_by(row, stage):
        return stage in (row.get("rejected_by") or [])

    def failed_rule(row, stage, rule):
        return rule in ((row.get("failed_rules") or {}).get(stage) or [])

    def observed(row):
        return row.get("observed")

    true_defects = ("M-A_drop_quantifiers", "M-B_unresolved_domain", "M-C_drop_final_not_exists",
                    "M-D_rename_t0_in_formal", "M-E_extra_binder_component", "M-F_formal_emptied")
    out["expectations"] = {
        # the failure to repair: semantic stages reject F1 at the frozen bytes on R03 only,
        # while the binding structural stage passes those same bytes
        "unpatched_semantic_rejects_f1_r03":
            rejected_by(canon_f1_unpatched, "semantic_baseline")
            and rejected_by(canon_f1_unpatched, "semantic_hardened")
            and failed_rule(canon_f1_unpatched, "semantic_baseline", "R03")
            and failed_rule(canon_f1_unpatched, "semantic_hardened", "R03")
            and not rejected_by(canon_f1_unpatched, "structural"),
        "unpatched_exit_3_valid_false":
            up["exit"] == 3 and up["validity"].get("valid_for_calibration") is False,
        # the repaired rule flips exactly that: no stage rejects F1, suite valid
        "patched_accepts_f1_all_stages":
            observed(canon_f1_patched) == "accept" and not canon_f1_patched.get("rejected_by"),
        "patched_exit_0_valid_true":
            pa["exit"] == 0 and pa["validity"].get("valid_for_calibration") is True,
        "patched_controls_3_3":
            all(observed(pa["rows"].get(t, {})) == "accept" and not pa["rows"].get(t, {}).get("rejected_by")
                for t in CONTROL_FILES),
        "patched_canonical_3_3":
            all(observed(pa["rows"].get(t, {})) == "accept" and not pa["rows"].get(t, {}).get("rejected_by")
                for t in CANON_FILES),
        # no weakening: mutant corpus catch counts and every other rule verdict unchanged
        "mutants_unchanged":
            pa["summary"].get("structural_caught") == 32
            and pa["summary"].get("semantic_baseline_caught") == 11
            and pa["summary"].get("semantic_hardened_caught") == 32
            and not pa["summary"].get("escaped_adopted_stages"),
        "true_defects_still_caught":
            all(mutants[k]["patched_baseline"]["verdict"] == "reject"
                and "R03" in mutants[k]["patched_baseline"]["failed_rules"]
                and mutants[k]["patched_hardened"]["verdict"] == "reject"
                for k in true_defects),
        "component_order_boundary_measured":
            mutants["M-G_component_order_swapped"]["patched_baseline"]["verdict"] == "accept",
        "no_other_rule_changed":
            all((not v["changes"]) for k, v in rule_diff.items() if "af_wcc_vacuum" not in k)
            and rule_diff["schemas/af_wcc_vacuum.yaml::baseline"]["changes"].get("R03") is not None
            and set(rule_diff["schemas/af_wcc_vacuum.yaml::baseline"]["changes"]) <= {"R03"}
            and set(rule_diff["schemas/af_wcc_vacuum.yaml::hardened"]["changes"]) <= {"R03"},
        "selftest_unchanged":
            out["patch"]["selftest_unchanged"]
            and all(s["fixtures"] == 32 and s["controls"] == ["accept", "accept", "accept"]
                    for s in selftest_patched)
            and [s["missed"] for s in selftest_patched] == [21, 0],
        "deterministic": normalized_projection(pa) == normalized_projection(pa2),
        "stale_controls_rejected_by_structural":
            all(rejected_by(ps["rows"].get(t, {}), "structural")
                and failed_rule(ps["rows"].get(t, {}), "structural", "R28")
                for t in CONTROL_FILES)
            and ps["validity"].get("valid_for_calibration") is False,
    }

    (HERE / "r03_repair_report.json").write_text(json.dumps(out, indent=1, sort_keys=False) + "\n")
    print(json.dumps({"report": "artifacts/worker-004/f1_r03_repair/r03_repair_report.json",
                      "report_sha256": sha(HERE / "r03_repair_report.json"),
                      "expectations": out["expectations"]}, indent=1))
    return 0 if all(out["expectations"].values()) else 1


if __name__ == "__main__":
    sys.exit(main())
