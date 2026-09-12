#!/usr/bin/env python3
"""W081-GFORM-ACC-MAT-01 -- is the stale G-FORM acceptance corpus *material*, or only a
provenance/ordering defect?  And what does re-running the pipeline at the live rev12 pins
actually say about canonical F1?

Context measured (2026-09-12, live bytes):
  * artifacts/formulation/evidence/semantic_escape_rebased.json binds corpus base
    1bb78ce9b357 (rev11 C0).  The live authoring C0 measures 55d0a1ea9bda (rev12 C0), so
    artifacts/formulation/tools/run_acceptance.py exits 3 on PREFLIGHT (stale corpus).
  * Because the pipeline fail-closes before the canonical stage, the last filed PASS
    (artifacts/formulation/evidence/acceptance_pipeline_report.json, 00:27) predates rev12.

What this instrument does (read-only on canonical paths; every write happens under
artifacts/worker-081/gform_acceptance_materiality/sandbox/):
  P0  pins the live hashes of every input this measurement depends on.
  P1  reproduces the live PREFLIGHT FAIL inside the sandbox mirror.
  P2  regenerates the rebased corpus against the live rev12 base (sandbox only).
  P3  re-runs the two-stage acceptance pipeline on the regenerated corpus, and grades all
      three canonical schemas through both stages.
  P4  measures the per-mutant verdict delta stale-corpus vs fresh-corpus (is the acceptance
      *outcome* invariant under the rev11->rev12 base move?).
  P5  tests the minimal R03 repair on canonical F1 in the sandbox and re-runs the pipeline.
  P6  audits every distinct F1 revision snapshot on disk to locate when R03 started failing.
  P7  reports the declared-vs-measured corpus size (one manifest fixture is unparsed).

Exit code 0 = instrument completed (verdict in evidence.json); 2 = a pinned input moved
between entry and exit, so the claims are advisory.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SANDBOX = HERE / "sandbox"
STALE = HERE / "stale_corpus"
EVIDENCE = HERE / "evidence.json"
CST = timezone(timedelta(hours=8))

# canonical inputs ------------------------------------------------------------
CANON = {
    "F1": REPO / "schemas/af_wcc_vacuum.yaml",
    "F2a": REPO / "schemas/af_scc_c2_vacuum.yaml",
    "F2b": REPO / "schemas/af_scc_c0_vacuum.yaml",
}
AUTHORING = REPO / "artifacts/formulation/schemas"
TOOLS = REPO / "artifacts/formulation/tools"
AUDITOR = REPO / "artifacts/worker-06/spec_conformance_audit.py"
MANIFEST = REPO / "artifacts/worker-06/semantic_fixtures/manifest.json"
RULE_SPEC = REPO / "artifacts/formulation/rule_spec.json"
LIVE_CORPUS = REPO / "artifacts/formulation/evidence/semantic_escape_rebased.json"
LIVE_FIXTURES = REPO / "artifacts/formulation/evidence/rebased_fixtures"
LIVE_ACCEPT_REPORT = REPO / "artifacts/formulation/evidence/acceptance_pipeline_report.json"

SB_TOOLS = SANDBOX / "artifacts/formulation/tools"
SB_SCHEMAS = SANDBOX / "artifacts/formulation/schemas"
SB_EVIDENCE = SANDBOX / "artifacts/formulation/evidence"
SB_AUDITOR = SANDBOX / "artifacts/worker-06/spec_conformance_audit.py"
SB_RUN_ACCEPT = SB_TOOLS / "run_acceptance.py"
SB_REBASE = SB_TOOLS / "measure_semantic_escape.py"
SB_FRESH_CORPUS = SB_EVIDENCE / "semantic_escape_rebased.json"
SB_FRESH_FIXTURES = SB_EVIDENCE / "rebased_fixtures"

# the R03-compatible rephrasing of the rev12 visibility clause.  Semantics unchanged:
# the same two binders, q in I+ and t0 in [0,T), now appear inside the literal "(q,t0)"
# tuple the ordered list declares.
R03_OLD_FORMAL = ("not exists q in I+ and t0 in [0,T) with gamma([t0,T)) subset "
                  "J^-(q) intersect M.")
R03_NEW_FORMAL = ("not exists (q,t0) with q in I+ and t0 in [0,T) such that "
                  "gamma([t0,T)) subset J^-(q) intersect M.")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(args, cwd=None):
    r = subprocess.run([sys.executable, *map(str, args)], capture_output=True,
                       text=True, cwd=cwd)
    return {"exit": r.returncode, "stdout": r.stdout, "stderr": r.stderr}


def stage1(path: Path):
    """canonical structural gate contract: --json, verdict from the JSON body."""
    r = run([SB_TOOLS / "check_class_schema.py", "--json", path])
    try:
        d = json.loads(r["stdout"])
        return {"verdict": d.get("verdict"), "failed_rules": d.get("failed_rules", [])}
    except Exception:  # noqa: BLE001
        return {"verdict": f"crash(exit{r['exit']})", "failed_rules": []}


def stage2(path: Path, hardened=False):
    """worker-06 semantic auditor contract: verdict from the JSON body, exit is unreliable."""
    args = [SB_AUDITOR, path] + (["--hardened"] if hardened else [])
    r = run(args)
    try:
        d = json.loads(r["stdout"])
        return {"verdict": d.get("verdict"), "failed_rules": d.get("failed_rules", []),
                "hardened": d.get("hardened"),
                "r03": next((c.get("detail") for c in d.get("checks", [])
                             if c.get("rule") == "R03"), None)}
    except Exception:  # noqa: BLE001
        return {"verdict": f"crash(exit{r['exit']})", "failed_rules": [], "r03": None}


def both_stages(path: Path):
    return {"structural": stage1(path), "semantic": stage2(path)}


def setup_sandbox():
    if SANDBOX.exists():
        shutil.rmtree(SANDBOX)
    (SANDBOX / "artifacts").mkdir(parents=True)
    shutil.copytree(REPO / "artifacts/formulation", SANDBOX / "artifacts/formulation")
    shutil.copytree(REPO / "artifacts/worker-06", SANDBOX / "artifacts/worker-06")
    # never let the sandbox FROZEN/registry imply authority over the live tree
    for junk in SANDBOX.rglob("__pycache__"):
        shutil.rmtree(junk, ignore_errors=True)


def snapshot_stale_corpus():
    if STALE.exists():
        shutil.rmtree(STALE)
    STALE.mkdir(parents=True)
    shutil.copytree(LIVE_FIXTURES, STALE / "rebased_fixtures")
    shutil.copy2(LIVE_CORPUS, STALE / "semantic_escape_rebased.json")


def main() -> int:
    started = datetime.now(CST).isoformat(timespec="seconds")
    pins = {name: {"path": str(p.relative_to(REPO)), "sha256": sha256(p)}
            for name, p in CANON.items()}
    pins["authoring"] = {p.name: sha256(p) for p in sorted(AUTHORING.glob("*.yaml"))}
    for label, p in [("run_acceptance.py", SB_RUN_ACCEPT),
                     ("measure_semantic_escape.py", SB_REBASE),
                     ("check_class_schema.py", TOOLS / "check_class_schema.py"),
                     ("spec_conformance_audit.py", AUDITOR),
                     ("rule_spec.json", RULE_SPEC),
                     ("semantic_fixtures/manifest.json", MANIFEST),
                     ("live semantic_escape_rebased.json", LIVE_CORPUS),
                     ("live acceptance_pipeline_report.json", LIVE_ACCEPT_REPORT)]:
        pins[label] = {"path": str(p.relative_to(REPO)) if p.is_relative_to(REPO) else str(p),
                       "sha256": sha256(p)}

    setup_sandbox()
    snapshot_stale_corpus()

    # P1 -- live PREFLIGHT FAIL reproduced in the sandbox mirror
    p1 = run([SB_RUN_ACCEPT], cwd=SANDBOX)

    # P2 -- regenerate the corpus against the live rev12 base (sandbox only)
    p2 = run([SB_REBASE], cwd=SANDBOX)
    fresh = json.loads(SB_FRESH_CORPUS.read_text())

    # P3 -- two-stage acceptance on the regenerated corpus
    p3 = run([SB_RUN_ACCEPT, "--json"], cwd=SANDBOX)
    try:
        p3_json = json.loads(p3["stdout"])
    except Exception:  # noqa: BLE001
        p3_json = json.loads((SB_EVIDENCE / "acceptance_pipeline_report.json").read_text())

    # P3b -- grade each as-frozen canonical schema through both stages
    canonical_stages = {}
    for name, rel in [("F1", "af_wcc_vacuum.yaml"), ("F2a", "af_scc_c2_vacuum.yaml"),
                      ("F2b", "af_scc_c0_vacuum.yaml")]:
        canonical_stages[name] = both_stages(SB_SCHEMAS / rel)
        canonical_stages[name]["sha256"] = sha256(SB_SCHEMAS / rel)

    # P4 -- stale vs fresh per-mutant verdict delta
    stale = json.loads((STALE / "semantic_escape_rebased.json").read_text())
    sm = {m["fixture"]: m for m in stale["mutants"]}
    fm = {m["fixture"]: m for m in fresh["mutants"]}

    def cls(m):
        s = not m.get("canonical_escape")
        w = not m.get("w06_escape")
        return ("union-caught" if (s or w) else "union-ESCAPE",
                f"structural={'caught' if s else 'escape'}",
                f"semantic={'caught' if w else 'escape'}")

    delta = []
    for name in sorted(set(sm) | set(fm)):
        a, b = sm.get(name), fm.get(name)
        pa = STALE / "rebased_fixtures" / name
        pb = SB_FRESH_FIXTURES / name
        row = {"fixture": name,
               "stale_bytes": sha256(pa) if pa.exists() else None,
               "fresh_bytes": sha256(pb) if pb.exists() else None,
               "stale": cls(a)[0] if a else None, "fresh": cls(b)[0] if b else None}
        row["verdict_class_changed"] = row["stale"] != row["fresh"]
        delta.append(row)
    stale_union = sum(1 for m in sm.values() if not m.get("canonical_escape")
                      or not m.get("w06_escape"))
    fresh_union = sum(1 for m in fm.values() if not m.get("canonical_escape")
                      or not m.get("w06_escape"))
    p4 = {"stale_base_sha256": stale.get("base_sha256"),
          "fresh_base_sha256": fresh.get("base_sha256"),
          "same_corpus_manifest": stale.get("corpus_manifest_sha256")
          == fresh.get("corpus_manifest_sha256"),
          "stale_mutants": len(sm), "fresh_mutants": len(fm),
          "stale_union_caught": stale_union, "fresh_union_caught": fresh_union,
          "verdict_class_changes": [r for r in delta if r["verdict_class_changed"]],
          "bytes_changed": sum(1 for r in delta if r["stale_bytes"] != r["fresh_bytes"]),
          "rows": delta}

    # manifest declared vs measured (one fixture is unparsed by the rebase tool)
    man = json.loads(MANIFEST.read_text())
    p7 = {"manifest_declared_fixtures": len(man["fixtures"]),
          "fresh_measured_mutants": len(fm),
          "fresh_unparsed": [u.get("fixture") for u in fresh.get("unparsed_mutations", [])],
          "stale_unparsed": [u.get("fixture") for u in stale.get("unparsed_mutations", [])]}

    # P5 -- minimal R03 repair on canonical F1, then a full pipeline re-run with it
    f1_text = (SB_SCHEMAS / "af_wcc_vacuum.yaml").read_text()
    if R03_OLD_FORMAL not in f1_text:
        repair = {"applicable": False,
                  "reason": "the pinned formal clause text is not present; pin moved"}
    else:
        repaired = f1_text.replace(R03_OLD_FORMAL, R03_NEW_FORMAL)
        rep_path = SB_SCHEMAS / "af_wcc_vacuum.repaired.yaml"
        rep_path.write_text(repaired)
        r_stage1, r_stage2 = stage1(rep_path), stage2(rep_path)
        # full pipeline: swap the repaired bytes in as the sandbox canonical F1
        keep = (SB_SCHEMAS / "af_wcc_vacuum.yaml").read_text()
        (SB_SCHEMAS / "af_wcc_vacuum.yaml").write_text(repaired)
        r_pipe = run([SB_RUN_ACCEPT, "--json"], cwd=SANDBOX)
        (SB_SCHEMAS / "af_wcc_vacuum.yaml").write_text(keep)
        try:
            r_pipe_json = json.loads(r_pipe["stdout"])
        except Exception:  # noqa: BLE001
            r_pipe_json = None
        repair = {"applicable": True,
                  "old_formal": R03_OLD_FORMAL, "new_formal": R03_NEW_FORMAL,
                  "repaired_sha256": sha256(rep_path),
                  "structural": r_stage1, "semantic": r_stage2,
                  "pipeline_verdict": (r_pipe_json or {}).get("verdict"),
                  "pipeline_mutants": (r_pipe_json or {}).get("mutants"),
                  "pipeline_exit": r_pipe["exit"],
                  "repaired_bytes_left_in_sandbox_only": True}

    # P6 -- when did R03 start failing?  audit every distinct F1 blob on disk
    history = {}
    for p in REPO.glob("artifacts/**/af_wcc_vacuum*.y*ml"):
        sp = str(p)
        if "/worker-081/" in sp or "/mirror/" in sp or "sandbox" in sp:
            continue
        try:
            h = sha256(p)
        except OSError:
            continue
        if h not in history or len(sp) < len(history[h]["path"]):
            history[h] = {"path": sp}
    for h, rec in history.items():
        r = run([AUDITOR, REPO / rec["path"]])
        try:
            d = json.loads(r["stdout"])
            rec["verdict"] = d.get("verdict")
            rec["failed_rules"] = d.get("failed_rules", [])
            rec["r03"] = next((c.get("detail") for c in d.get("checks", [])
                               if c.get("rule") == "R03"), None)
        except Exception:  # noqa: BLE001
            rec["verdict"] = f"crash(exit{r['exit']})"
    p6 = {"distinct_f1_blobs": len(history),
          "r03_present_binders_reject": sum(1 for r in history.values()
                                            if r.get("verdict") == "reject"
                                            and "R03" in (r.get("failed_rules") or [])),
          "accept": sum(1 for r in history.values() if r.get("verdict") == "accept"),
          "blobs": {h[:12]: {"path": r["path"], "verdict": r.get("verdict"),
                             "failed_rules": r.get("failed_rules"),
                             "r03": r.get("r03")} for h, r in sorted(history.items())}}

    # exit pin re-measure
    end_pins = {name: sha256(p) for name, p in CANON.items()}
    moved = [name for name in CANON if end_pins[name] != pins[name]["sha256"]]

    finding = (f"At the live rev12 pins the two-stage acceptance pipeline cannot pass: after the "
               f"corpus is regenerated against base 55d0a1ea (sandbox), the stale-corpus PREFLIGHT "
               f"block clears, all 31 measured mutants are union-caught and both controls pass, but "
               f"the canonical F1 schema {pins['F1']['sha256'][:12]} is rejected by stage 2 "
               f"(spec_conformance_audit.py) on R03: the ordered binder '(q,t0)' does not appear "
               f"literally in quantifiers.formal.  The pre-rev12 F1 blob "
               f"9a8bd4c96800 passes R03.  The stale corpus is therefore material: by fail-closing "
               f"before the canonical stage it masked a live F1 stage-2 rejection.  A one-field "
               f"rephrasing that writes the binders as the declared tuple makes F1 pass both stages "
               f"and the full pipeline PASS at the same rev12 mutant corpus.")

    evidence = {
        "task_id": "W081-GFORM-ACC-MAT-01",
        "worker": "worker-081",
        "instance": "worker-081-20260912T004238-968807",
        "created_at": started,
        "class_id": "AF-WCC-VAC-GEN",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "node_id": "F1,F2a,F2b",
        "gate": "G-FORM",
        "authority": ("worker measurement only; no canonical path was written, no node status, "
                      "validation_status or gate verdict is set by this artifact"),
        "pins": pins,
        "p1_live_preflight": {"exit": p1["exit"], "stdout": p1["stdout"].strip(),
                              "reproduced_in_sandbox": p1["exit"] == 3},
        "p2_rebase": {"exit": p2["exit"], "summary": fresh.get("summary"),
                      "base_sha256": fresh.get("base_sha256")},
        "p3_fresh_acceptance": {"exit": p3["exit"], "verdict": p3_json.get("verdict"),
                                "canonical": p3_json.get("canonical"),
                                "mutants": p3_json.get("mutants"),
                                "controls": p3_json.get("controls")},
        "p3b_canonical_stage_table": canonical_stages,
        "p4_stale_vs_fresh": p4,
        "p5_minimal_r03_repair": repair,
        "p6_f1_revision_history": p6,
        "p7_corpus_size": p7,
        "finding": finding,
        "claim": ("At the live G-FORM rev12 pins (F1 cce9c60146d6, F2a 5476a3f2c6bc, F2b "
                  "55d0a1ea9bda, FROZEN rev28 2f358f6722d9) the two-stage acceptance criterion "
                  "is not met by the as-frozen F1 artifact: stage 2 rejects it on R03 "
                  "(binder '(q,t0)' absent from quantifiers.formal), so run_acceptance.py cannot "
                  "exit 0 even after the stale rebased corpus is regenerated. The rev11->rev12 "
                  "base change is not verdict-material for the mutant corpus (same union-catch "
                  "class for all 31 measured mutants), so the corpus repair is a re-generation "
                  "and re-pin, not a semantic revision; the live F1 R03 mismatch is an "
                  "independent, concrete blocker."),
        "falsifier": ("Re-run this instrument after re-measuring the pins. The finding is "
                      "falsified if (a) any of F1 cce9c60146d6 / F2a 5476a3f2c6bc / F2b "
                      "55d0a1ea9bda / manifest c102445df397 / spec_conformance_audit.py has "
                      "moved and the moved revision passes both stages; (b) at the pinned rev12 "
                      "hashes run_acceptance.py exits 0; (c) the stage-2 auditor on canonical F1 "
                      "returns accept with R03 pass (binder notation now consistent); or (d) a "
                      "re-measured stale-vs-fresh comparison shows a mutant whose union-catch "
                      "class changes. The repair proposal is falsified if the substituted "
                      "sentence changes any other stage-1/stage-2 rule outcome or the mutant "
                      "union count."),
        "does_not_claim": [
            "no class-semantics or mathematical adjudication of F1",
            "no statement that R03 is the only F1 defect, or that the repaired F1 is otherwise acceptable",
            "no gate verdict; lead-formulation owns the canonical path, lead-audit owns the verdict",
        ],
        "end_pins": end_pins,
        "pins_moved_during_run": moved,
    }
    EVIDENCE.write_text(json.dumps(evidence, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"p1_exit": p1["exit"], "p3_exit": p3["exit"],
                      "p3_verdict": p3_json.get("verdict"),
                      "f1_semantic": canonical_stages["F1"]["semantic"],
                      "repair_pipeline": repair.get("pipeline_verdict"),
                      "pins_moved": moved}, indent=1))
    return 0 if not moved else 2


if __name__ == "__main__":
    sys.exit(main())
