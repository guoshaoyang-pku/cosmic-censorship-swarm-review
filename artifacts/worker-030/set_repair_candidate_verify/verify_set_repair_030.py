#!/usr/bin/env python3
"""W030-SET-REPAIR-CANDIDATE-INDEPENDENT-VERIFY-01.

Independent, non-author, read-only verification of worker-024's unfrozen SET-strength
repair candidate (W024-SET-STRENGTH-REPAIR-01) at frozen rev29 pins.

What is verified (all from primary bytes; nothing is taken from the author's verifier):
  P  pins        six canonical pins + guard set measured T0/T1; drift -> exit 2 (void)
  H  hashes      the three candidate files and repair.patch measure to the claimed sha256
  S  structure   line-diff minimality per target; repair.patch applies cleanly and
                 reproduces the three candidates byte-for-byte on a sandbox tree
  L  level       an independently written level predicate classifies the live label as
                 LEVEL_MIXED and the candidate label as LEVEL_QUALIFIED, and both
                 against the two frozen anchors (taxonomy:94 class / F1:235 predicate)
  B  behaviour   a mutation matrix over sandbox registry copies exercises the live and
                 candidate checkers: candidate fails closed on live + 3 assertion
                 mutants and passes on candidate + a benign mutation
  R  regression  check_variant_deltas.py and check_taxonomy_consistency.py run on the
                 candidate sandbox tree (never on canonical paths)
  W  write-guard the full guard set (incl. the two sibling evidence JSONs the checkers
                 write) is byte-identical T0->T1; sandboxes live outside the repo

Exit codes: 0 = candidate independently verified; 1 = candidate falsified (a check
failed); 2 = pin drift / void.  No canonical write.  Worker evidence only: no gate
verdict, no node status, no validation_status.

Falsifier: this verification is falsified if, at the pins it records, (a) any guard
byte moves; (b) a candidate differs from live outside its declared sites; (c) the
patch does not reproduce the candidates; (d) the live label is level-qualified and
anchor-consistent under the published predicate, or the candidate label is not; (e) a
declared mutation does not flip the expected checker exit code; or (f) a sibling
checker regresses on the candidate tree.  An adopted revision at a new hash voids the
pins and requires a re-run.
"""
from __future__ import annotations

import difflib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[3]
W024 = ROOT / "artifacts/worker-024/set_strength_repair"

CANON = Path("artifacts/formulation/VARIANT_REGISTRY.json")
DELTA = Path("artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json")
CHECKER = Path("artifacts/formulation/tools/check_variant_registry.py")
TAXONOMY = Path("research_map/formulation_taxonomy.yaml")
SUPPLEMENT = Path("artifacts/formulation/formulation_taxonomy.yaml")
F1 = Path("schemas/af_wcc_vacuum.yaml")
FROZEN = Path("artifacts/formulation/FROZEN.json")
EVID_REG = Path("artifacts/formulation/evidence/variant_registry_check.json")
EVID_DELTA = Path("artifacts/formulation/evidence/variant_delta_check.json")
SIBLING_DELTAS = Path("artifacts/formulation/tools/check_variant_deltas.py")
SIBLING_TAX = Path("artifacts/formulation/tools/check_taxonomy_consistency.py")

CLAIMED_PINS = {
    str(CANON): "6bac9adea19e17efe625342ef4d2098e3775491aa3d0e06596cd5d75912348fb",
    str(DELTA): "64b8d6394a044686de770879675eb4932ff980a942d45d16758b295d4851cecf",
    str(CHECKER): "c471da4b7be9a9b0ac884d3722a223c1c7a9fc7dcf5718a0f4707d65e8757f4d",
    str(TAXONOMY): "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    str(SUPPLEMENT): "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
    str(F1): "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    str(FROZEN): "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
}
CLAIMED_CANDIDATES = {
    "CANDIDATE_VARIANT_REGISTRY.json":
        "5c05a8cc7ea2583a97d3a977d81aef4de74ff9378337b42a00ef992b61aa1c2a",
    "CANDIDATE_AF-WCC-VAC-GEN.variant-SET.delta.json":
        "7a1f6212ad70e55ee760e0c271c339eca30ac7bdfca2dd5969ba14df771e6927",
    "CANDIDATE_check_variant_registry.py":
        "8b15f43e843dfcce87035215b92efd4b995b8fba4ac272391932364ee2ecd7fe",
    "repair.patch":
        "9fb0c6674849477350bbac7a0ef838f7c344dae6b3d3d918b30bc5aebf1be6ba",
}
DECLARED_SITES = {
    str(CANON): [57],
    str(DELTA): [11],
}
GUARD = sorted(set(CLAIMED_PINS) | {str(EVID_REG), str(EVID_DELTA),
                                    str(SIBLING_DELTAS), str(SIBLING_TAX)})


class Void(Exception):
    """Pin drift: the whole verification is void."""


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def measure(rel: str) -> str:
    p = ROOT / rel
    return sha(p) if p.exists() else "ABSENT"


def measure_all(rels) -> dict:
    return {r: measure(r) for r in rels}


def read_text(p: Path) -> str:
    return Path(p).read_text(encoding="utf-8")


# --------------------------------------------------------------------------- level
DIR_RE = re.compile(r"(STRONGER|WEAKER|stronger|weaker)\s+than\s+(?:AF-WCC-VAC-GEN|the\s+parent\s+class)")


def strip_notes(s: str) -> str:
    while "[" in s and "]" in s:
        s = s[:s.index("[")] + s[s.index("]") + 1:]
    return s


def level_predicate(label: str, class_anchor: str, predicate_anchor: str) -> dict:
    """Independent classifier: a label comparing a variant to its parent class must
    assert the CLASS-level direction explicitly and, separately, any PREDICATE-level
    direction.  Directions are taken from the label text; anchors from frozen bytes."""
    subject = strip_notes(label)
    class_qualified = "class statement" in subject
    class_dir = None
    m = re.search(r"(STRONGER|WEAKER|stronger|weaker)\s+than\s+AF-WCC-VAC-GEN", subject)
    if m:
        class_dir = m.group(1).upper()
    pred_dir = None
    for mm in re.finditer(r"predicate[^.;)]{0,120}", subject):
        dm = re.search(r"(STRONGER|WEAKER|stronger|weaker)", mm.group(0))
        if dm:
            pred_dir = dm.group(1).upper()
            break
    a_class = "STRONGER" if "stronger than the parent class" in class_anchor.lower() else \
              ("WEAKER" if "weaker than the parent class" in class_anchor.lower() else None)
    a_pred = "WEAKER" if "weaker than this class's single-q tail predicate" in predicate_anchor.lower() \
        else ("STRONGER" if "stronger than this class's single-q tail predicate" in predicate_anchor.lower() else None)
    level_qualified = class_qualified and pred_dir is not None
    if level_qualified and class_dir == a_class and pred_dir == a_pred:
        verdict = "LEVEL_QUALIFIED_AND_ANCHOR_CONSISTENT"
    elif not level_qualified:
        verdict = "LEVEL_MIXED" if class_dir is not None else "UNDECIDABLE"
    else:
        verdict = "LEVEL_QUALIFIED_BUT_ANCHOR_CONFLICT"
    return {
        "class_direction": class_dir, "class_qualified": class_qualified,
        "predicate_direction": pred_dir, "level_qualified": level_qualified,
        "anchor_class_direction": a_class, "anchor_predicate_direction": a_pred,
        "verdict": verdict,
    }


# ------------------------------------------------------------------------ sandbox
def build_sandbox(dest: Path, registry: Path, delta: Path, checker: Path) -> Path:
    root = dest
    (root / "artifacts").mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT / "artifacts/formulation", root / "artifacts/formulation",
                    symlinks=True, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(ROOT / "schemas", root / "schemas", symlinks=True,
                    dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__"))
    (root / "research_map").mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / TAXONOMY, root / TAXONOMY)
    shutil.copy2(registry, root / CANON)
    shutil.copy2(delta, root / DELTA)
    shutil.copy2(checker, root / CHECKER)
    return root


def run_checker(root: Path, checker_rel: Path, timeout=90):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    p = subprocess.run([sys.executable, str(root / checker_rel)], cwd=str(root),
                       capture_output=True, text=True, timeout=timeout, env=env)
    ev = root / EVID_REG
    return {"exit": p.returncode,
            "stdout_tail": (p.stdout.strip().splitlines() or [""])[-1],
            "stderr_tail": (p.stderr.strip().splitlines() or [""])[-1][:200],
            "evidence_written": ev.exists(),
            "evidence_sha256": sha(ev) if ev.exists() else None}


def run_tool(root: Path, tool: Path):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    p = subprocess.run([sys.executable, str(root / tool)], cwd=str(root),
                       capture_output=True, text=True, timeout=120, env=env)
    return {"exit": p.returncode, "stdout_tail": (p.stdout.strip().splitlines() or [""])[-1],
            "stderr_tail": (p.stderr.strip().splitlines() or [""])[-1][:200]}


def set_strength(path: Path, new: str) -> None:
    d = json.loads(path.read_text())
    if "variants" in d:
        for v in d["variants"]:
            if v.get("parent_class") == "AF-WCC-VAC-GEN" and v.get("variant_id") == "SET":
                v["strength"] = new
    else:
        d["strength"] = new
    path.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def live_strengths():
    reg = json.loads(read_text(ROOT / CANON))
    for v in reg["variants"]:
        if v.get("parent_class") == "AF-WCC-VAC-GEN" and v.get("variant_id") == "SET":
            return v["strength"], json.loads(read_text(ROOT / DELTA))["strength"]
    raise SystemExit("SET variant not found")


# --------------------------------------------------------------------------- main
def main() -> int:
    t_start = time.time()
    checks, controls, matrix = [], [], []
    sandboxes = Path(tempfile.mkdtemp(prefix="w030_setverify_"))
    report = {
        "schema": "w030-set-repair-independent-verify/v1",
        "task_id": "W030-SET-REPAIR-CANDIDATE-INDEPENDENT-VERIFY-01",
        "actor": "worker-030",
        "node_id": "F0",
        "class_id": "AF-WCC-VAC-GEN",
        "gate": "G-FORM",
        "authority_note": ("worker-side independent measurement only; cannot set status=done, "
                           "validation_status=passed or a gate verdict; no canonical write"),
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "sandbox_root": str(sandboxes),
        "target": {
            "author_task": "W024-SET-STRENGTH-REPAIR-01",
            "author_actor": "worker-024",
            "candidate_dir": "artifacts/worker-024/set_strength_repair",
        },
    }

    def add(cid, ok, detail):
        checks.append({"id": cid, "pass": bool(ok), "detail": detail})

    # P -- pin guard -------------------------------------------------------------
    t0 = measure_all(GUARD)
    bad = {r: (CLAIMED_PINS[r], t0[r]) for r in CLAIMED_PINS if r in t0 and t0[r] != CLAIMED_PINS[r]}
    if bad:
        report.update({"verdict": "VOID_PIN_DRIFT", "pin_drift": bad, "pins_T0": t0})
        (HERE / "report.json").write_text(json.dumps(report, indent=2) + "\n")
        print(f"VOID: pin drift {bad}")
        return 2
    report["pins_claimed"] = CLAIMED_PINS
    report["pins_T0"] = t0
    add("P1_canonical_pins_resolve", True, "6 claimed canonical pins + guard set measured; all match")

    # H -- candidate hashes ------------------------------------------------------
    ch = {name: sha(W024 / name) for name in CLAIMED_CANDIDATES}
    hok = all(ch[k] == v for k, v in CLAIMED_CANDIDATES.items())
    report["candidate_hashes_claimed"] = CLAIMED_CANDIDATES
    report["candidate_hashes_measured"] = ch
    add("H1_candidate_hashes", hok, ch)
    if not hok:
        report["verdict"] = "FALSIFIED_CANDIDATE_HASH_MISMATCH"
        (HERE / "report.json").write_text(json.dumps(report, indent=2) + "\n")
        print("FALSIFIED: candidate hash mismatch")
        return 1

    # S -- structure: minimality + patch round-trip ------------------------------
    diffs = {}
    for rel, declared in DECLARED_SITES.items():
        a = read_text(ROOT / rel).splitlines()
        b = read_text(W024 / ("CANDIDATE_" + Path(rel).name)).splitlines()
        changed = [i + 1 for i, (x, y) in enumerate(zip(a, b)) if x != y]
        extra = abs(len(a) - len(b))
        diffs[rel] = {"changed_lines": changed, "declared_lines": declared,
                      "len_live": len(a), "len_cand": len(b)}
        add("S1_minimality:" + Path(rel).name, changed == declared and extra == 0,
            diffs[rel])
    # checker diff confined to the SET clause
    a = read_text(ROOT / CHECKER).splitlines()
    b = read_text(W024 / "CANDIDATE_check_variant_registry.py").splitlines()
    sm = difflib.SequenceMatcher(None, a, b)
    blocks = [op for op in sm.get_opcodes() if op[0] != "equal"]
    clause_ok = bool(blocks) and all(80 <= op[1] <= 100 for op in blocks)
    add("S2_checker_diff_confined_to_set_clause", clause_ok,
        {"live_lines": len(a), "candidate_lines": len(b),
         "diff_blocks": [{"op": op[0], "live": [op[1] + 1, op[2]], "cand": [op[3] + 1, op[4]]}
                         for op in blocks]})
    # patch round-trip on a dedicated sandbox
    psb = build_sandbox(sandboxes / "patch", ROOT / CANON, ROOT / DELTA, ROOT / CHECKER)
    pr = subprocess.run(["patch", "-p1", "--no-backup-if-mismatch", "-i", str(W024 / "repair.patch")],
                        cwd=str(psb), capture_output=True, text=True)
    same = all(sha(psb / rel) == ch["CANDIDATE_" + Path(rel).name]
               for rel in list(DECLARED_SITES) + [str(CHECKER)])
    report["patch_roundtrip"] = {"exit": pr.returncode, "stdout": pr.stdout.strip()[:500],
                                 "reproduces_candidates": same}
    add("S3_patch_roundtrip", pr.returncode == 0 and same, report["patch_roundtrip"])

    # L -- independent level predicate ------------------------------------------
    tax_line = read_text(ROOT / TAXONOMY).splitlines()[93]
    f1_line = read_text(ROOT / F1).splitlines()[234]
    live_reg, live_delta = live_strengths()
    cand_reg = json.loads(read_text(W024 / "CANDIDATE_VARIANT_REGISTRY.json"))
    cand_delta = json.loads(read_text(W024 / "CANDIDATE_AF-WCC-VAC-GEN.variant-SET.delta.json"))
    cs = next(v["strength"] for v in cand_reg["variants"]
              if v.get("parent_class") == "AF-WCC-VAC-GEN" and v.get("variant_id") == "SET")
    lv = level_predicate(live_reg, tax_line, f1_line)
    cv = level_predicate(cs, tax_line, f1_line)
    cross = cs == cand_delta["strength"]
    report["level"] = {"anchors": {"taxonomy_94": tax_line.strip(),
                                   "f1_235": f1_line.strip()},
                       "live": lv, "candidate": cv,
                       "cross_artifact_byte_identical": cross,
                       "live_label": live_reg, "candidate_label": cs}
    add("L1_live_is_level_mixed", lv["verdict"] == "LEVEL_MIXED",
        {"live_verdict": lv["verdict"], "class_direction": lv["class_direction"],
         "class_qualified": lv["class_qualified"]})
    add("L2_candidate_is_qualified_and_anchor_consistent",
        cv["verdict"] == "LEVEL_QUALIFIED_AND_ANCHOR_CONSISTENT", cv)
    add("L3_cross_artifact_label_identity", cross, {"registry": cs[:60], "delta": cand_delta["strength"][:60]})

    # B -- behavioral matrix -----------------------------------------------------
    # Each scenario is its own sandbox with an explicit (registry, delta, checker) triple.
    CAND_REG = W024 / "CANDIDATE_VARIANT_REGISTRY.json"
    CAND_DELTA = W024 / "CANDIDATE_AF-WCC-VAC-GEN.variant-SET.delta.json"
    CAND_CHECKER = W024 / "CANDIDATE_check_variant_registry.py"
    muts = {
        "m1_live_label_in_candidate": (live_reg, live_delta),
        "m2_class_direction_flipped": (cs.replace("STRONGER than AF-WCC-VAC-GEN",
                                                  "WEAKER than AF-WCC-VAC-GEN"), None),
        "m3_predicate_direction_flipped": (cs.replace("predicate S is strictly WEAKER",
                                                      "predicate S is strictly STRONGER"), None),
        "m4_benign_suffix": (cs + " [w030 benign control]", None),
        "m5_live_note_stripped": (re.sub(r"\s*\[[^\]]*\]", "", live_reg), None),
    }
    scen, scen_pins = {}, {}
    scen["live_lc"] = build_sandbox(sandboxes / "live_lc", ROOT / CANON, ROOT / DELTA, ROOT / CHECKER)
    scen["cand_lc"] = build_sandbox(sandboxes / "cand_lc", CAND_REG, CAND_DELTA, ROOT / CHECKER)
    scen["live_cc"] = build_sandbox(sandboxes / "live_cc", ROOT / CANON, ROOT / DELTA, CAND_CHECKER)
    scen["cand_cc"] = build_sandbox(sandboxes / "cand_cc", CAND_REG, CAND_DELTA, CAND_CHECKER)
    for name, (reg_s, delta_s) in muts.items():
        use_cand_checker = name != "m5_live_note_stripped"
        sb = build_sandbox(sandboxes / name, CAND_REG, CAND_DELTA,
                           CAND_CHECKER if use_cand_checker else ROOT / CHECKER)
        set_strength(sb / CANON, reg_s)
        if delta_s is not None:
            set_strength(sb / DELTA, delta_s)
        scen[name] = sb
    runs = [
        ("B1_live_checker_on_live", "live_lc", 0),
        ("B2_live_checker_on_candidate", "cand_lc", 0),
        ("B3_candidate_checker_on_live", "live_cc", 1),
        ("B4_candidate_checker_on_candidate", "cand_cc", 0),
        ("B5_candidate_checker_m1_live_label", "m1_live_label_in_candidate", 1),
        ("B6_candidate_checker_m2_class_flip", "m2_class_direction_flipped", 1),
        ("B7_candidate_checker_m3_predicate_flip", "m3_predicate_direction_flipped", 1),
        ("B8_candidate_checker_m4_benign", "m4_benign_suffix", 0),
        ("B9_live_checker_m5_note_stripped", "m5_live_note_stripped", 1),
    ]
    for cid, sname, expect in runs:
        sb = scen[sname]
        scen_pins[sname] = {"registry": sha(sb / CANON), "delta": sha(sb / DELTA),
                            "checker": sha(sb / CHECKER)}
        res = run_checker(sb, CHECKER)
        matrix.append({"id": cid, "scenario": sname, "expected_exit": expect, **res})
        add(cid, res["exit"] == expect, {"expected": expect, "got": res["exit"],
                                         "stdout": res["stdout_tail"],
                                         "wrote_evidence_in_sandbox": res["evidence_written"]})
    report["sandbox_scenarios"] = scen_pins

    # R -- sibling regression on the candidate tree ------------------------------
    reg = {}
    for nm, tool, want in (("check_variant_deltas.py", SIBLING_DELTAS, "VALID"),
                           ("check_taxonomy_consistency.py", SIBLING_TAX, "CONSISTENT")):
        res = run_tool(scen["cand_cc"], tool)
        reg[nm] = res
        add("R1_" + nm, res["exit"] == 0 and res["stdout_tail"].startswith(want), res)
    report["sibling_regression"] = reg

    # W -- write guard T1 --------------------------------------------------------
    t1 = measure_all(GUARD)
    moved = {r: (t0[r], t1[r]) for r in GUARD if t0[r] != t1[r]}
    report["pins_T1"] = t1
    report["guard_moved"] = moved
    add("W1_no_canonical_write_T0_T1", not moved, moved or "all guard bytes identical")

    # C -- controls --------------------------------------------------------------
    # K1: pin guard self-test on a tampered expectation
    try:
        fake = dict(CLAIMED_PINS)
        fake[str(CANON)] = "0" * 64
        _drift = {r: (fake[r], t0[r]) for r in fake if fake[r] != t0[r]}
        raise Void("drift") if _drift else None
        k1 = False
    except Void:
        k1 = True
    controls.append({"id": "K1_pin_guard_selftest", "pass": k1,
                     "detail": "tampered expectation is detected by the same comparison"})
    # K2: patch round-trip on a mutated source must not reproduce the candidate
    tsb = build_sandbox(sandboxes / "tamper", ROOT / CANON, ROOT / DELTA, ROOT / CHECKER)
    with open(tsb / CANON, "a", encoding="utf-8") as fh:
        fh.write("\n")
    subprocess.run(["patch", "-p1", "--no-backup-if-mismatch", "-i", str(W024 / "repair.patch")],
                   cwd=str(tsb), capture_output=True, text=True)
    k2 = sha(tsb / CANON) != ch["CANDIDATE_VARIANT_REGISTRY.json"]
    controls.append({"id": "K2_tampered_source_not_reproduced", "pass": k2,
                     "detail": "appended byte to the source registry before patch -> output differs"})
    # K3: predicate discriminates live vs candidate
    k3 = lv["verdict"] != cv["verdict"] and lv["verdict"] == "LEVEL_MIXED"
    controls.append({"id": "K3_predicate_discrimination", "pass": k3,
                     "detail": {"live": lv["verdict"], "candidate": cv["verdict"]}})
    # K4: determinism of the level predicate on re-read
    k4 = level_predicate(live_strengths()[0], tax_line, f1_line) == lv and \
        level_predicate(cs, tax_line, f1_line) == cv
    controls.append({"id": "K4_predicate_determinism", "pass": k4, "detail": "recomputed payloads identical"})
    report["controls"] = controls

    all_ok = all(c["pass"] for c in checks) and all(c["pass"] for c in controls)
    report["checks"] = checks
    report["behavioral_matrix"] = matrix
    report["verdict"] = ("CANDIDATE_INDEPENDENTLY_VERIFIED_LEVEL_QUALIFIED_AND_ASSERTION_AWARE"
                         if all_ok else "FALSIFIED")
    report["falsifier"] = (
        "Falsified if, at the recorded pins: any guard byte moves; a candidate differs from live "
        "outside its declared sites; repair.patch does not reproduce the candidates; the live label "
        "is level-qualified and anchor-consistent under the published predicate (or the candidate "
        "label is not); any declared mutation does not flip the expected checker exit code; or a "
        "sibling checker regresses on the candidate tree. An adopted revision at a new hash voids "
        "these pins and requires a re-run.")
    report["not_claimed"] = ["gate verdict", "node status", "validation_status",
                             "adoption or application of the candidate",
                             "any mathematics or physics statement",
                             "review of findings unrelated to the SET strength label"]
    report["duration_s"] = round(time.time() - t_start, 3)
    digest_payload = {k: report[k] for k in
                      ("pins_T0", "candidate_hashes_measured", "level", "patch_roundtrip",
                       "behavioral_matrix", "sibling_regression", "controls", "checks")}
    report["run_digest"] = hashlib.sha256(
        json.dumps(digest_payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    (HERE / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                                      encoding="utf-8")
    print(("VERIFIED" if all_ok else "FALSIFIED") + f" digest={report['run_digest']}")
    for c in checks:
        if not c["pass"]:
            print("  FAIL " + c["id"] + " " + json.dumps(c["detail"])[:200])
    print(f"report: {HERE/'report.json'}  sandbox: {sandboxes}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
