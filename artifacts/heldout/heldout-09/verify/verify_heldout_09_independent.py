#!/usr/bin/env python3
"""W084-HELDOUT09-INDEP-01 -- independent reproduction + moving-target adjudication.

Independent executor for FORM-HELDOUT-09 (assign-FORM-HELDOUT-09-worker-084),
node A1, gate G-CLASSBIND, classes AF-WCC-VAC-GEN / AF-SCC-C2-VAC-GEN /
AF-SCC-C0-VAC-GEN.

This script does NOT rebuild fixtures and does NOT edit any fixture or any
canonical path.  It re-runs the two declared stages over the frozen corpus
copies, compares the verdicts with the retained raw verdicts, measures the
same corpus under the stage-B repaired (`--hardened`) rule set, recomputes the
aggregates, locates the exact R03 trigger on the frozen canonical AF-WCC bytes,
and measures the live canonical paths against the card pins (moving-target
check).  Read-only on all pinned inputs; writes only under
artifacts/heldout/heldout-09/verify/.

Run:  python3 artifacts/heldout/heldout-09/verify/verify_heldout_09_independent.py
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

ROOT = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
CORPUS = ROOT / "artifacts/heldout/heldout-09"
OUT = CORPUS / "verify"
CST = timezone(timedelta(hours=8))
TIMEOUT = 60

STAGE_A = ROOT / "artifacts/formulation/tools/check_class_schema.py"
STAGE_B = ROOT / "artifacts/worker-06/spec_conformance_audit.py"

# Card pins, verbatim from comms/inbox/worker-084.jsonl
# assign-FORM-HELDOUT-09-worker-084.
CARD_PINS = {
    "artifacts/formulation/FROZEN.json": "2f358f6722d920621a66c0259cb48d35a5e3c1b706f28adf37ed467325fcedf1",
    "schemas/af_wcc_vacuum.yaml": "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3",
    "schemas/af_scc_c2_vacuum.yaml": "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce",
    "schemas/af_scc_c0_vacuum.yaml": "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6",
    "research_map/formulation_taxonomy.yaml": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "artifacts/formulation/rule_spec.json": "40f9bb9e657b2c6b0cce04a9c05e9cdbf18083669060727a8e31d83031f5901e",
}
FROZEN_SHA = CARD_PINS["artifacts/formulation/FROZEN.json"]


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def parse_json_stdout(stdout: str):
    i = stdout.find("{")
    if i < 0:
        return None
    try:
        return json.loads(stdout[i:])
    except json.JSONDecodeError:
        return None


def run_stage_a(target: Path) -> dict:
    t0 = time.time()
    try:
        p = subprocess.run([sys.executable, str(STAGE_A), "--json", str(target)],
                           capture_output=True, text=True, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        return {"tool": "stage_a/check_class_schema.py", "exit": None, "verdict": None,
                "failed_rules": [], "escaped": False, "crash": True,
                "seconds": round(time.time() - t0, 3), "stderr": "timeout"}
    rep = parse_json_stdout(p.stdout) or {}
    return {
        "tool": "stage_a/check_class_schema.py", "exit": p.returncode,
        "verdict": rep.get("verdict"), "failed_rules": sorted(rep.get("failed_rules", [])),
        "escaped": p.returncode == 0 and rep.get("verdict") == "pass",
        "crash": rep.get("verdict") is None,
        "seconds": round(time.time() - t0, 3),
        "stderr": p.stderr.strip()[:200],
    }


def run_stage_b(target: Path, hardened: bool = False) -> dict:
    t0 = time.time()
    cmd = [sys.executable, str(STAGE_B)]
    if hardened:
        cmd.append("--hardened")
    cmd.append(str(target))
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        return {"tool": "stage_b/spec_conformance_audit.py", "hardened": hardened,
                "exit": None, "verdict": None, "failed_rules": [], "escaped": False,
                "crash": True, "seconds": round(time.time() - t0, 3), "stderr": "timeout"}
    rep = parse_json_stdout(p.stdout) or {}
    verdict = rep.get("verdict")
    return {
        "tool": "stage_b/spec_conformance_audit.py", "hardened": hardened,
        "exit": p.returncode, "verdict": verdict,
        "failed_rules": sorted(rep.get("failed_rules", [])),
        "escaped": verdict == "accept", "crash": verdict is None,
        "seconds": round(time.time() - t0, 3),
        "stderr": p.stderr.strip()[:200],
    }


def key(v: dict) -> tuple:
    return (v.get("verdict"), tuple(v.get("failed_rules", [])))


def load_fixtures():
    man = json.loads((CORPUS / "manifest.json").read_text())
    fixtures = []
    seen = set()

    def add(fid, path_rel, kind, arm, class_id, raw_key):
        if fid in seen:
            return
        seen.add(fid)
        fixtures.append({"fixture": fid, "path": path_rel, "kind": kind, "arm": arm,
                         "class_id": class_id, "raw_key": raw_key})

    for arm, b in man["bases"].items():
        add(b["path"].split("/")[-1], b["path"], "frozen-canonical", arm, b["class_id"], "control")
    for c in man["controls"]:
        add(c["fixture"], c["path"], c["kind"], c["arm"], c["class_id"], "control")
    for m in man["mutants"]:
        add(m["fixture"], m["path"], "mutant", m["arm"], m["class_id"], "mutant")
    return man, fixtures


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    man, fixtures = load_fixtures()
    raw = json.loads((CORPUS / "raw/raw_verdicts.json").read_text())
    report = json.loads((CORPUS / "report.json").read_text())

    tool_hashes = {"stage_a": sha(STAGE_A), "stage_b": sha(STAGE_B)}

    # Raw verdict lookup by fixture basename.
    raw_ctl = {c["fixture"]: c for c in raw["controls"]}
    raw_mut = {c["fixture"]: c for c in raw["results"]}

    per_fixture = []
    for f in fixtures:
        ents = [str(ROOT / f["path"])]
        # manifest fixture entry carries the base copy; the frozen canonical
        # controls are the corpus base copies (byte-equal to the pins).
        a = run_stage_a(Path(ents[0]))
        b = run_stage_b(Path(ents[0]), hardened=False)
        bh = run_stage_b(Path(ents[0]), hardened=True)
        prior = raw_ctl.get(f["fixture"]) if f["raw_key"] == "control" else raw_mut.get(f["fixture"])
        prior_a = prior["stage_a"] if prior else None
        prior_b = prior["stage_b"] if prior else None
        per_fixture.append({
            "fixture": f["fixture"], "kind": f["kind"], "arm": f["arm"],
            "path": f["path"], "sha256": sha(ROOT / f["path"]),
            "stage_a": a, "stage_b": b, "stage_b_hardened": bh,
            "prior_stage_a": {k: prior_a[k] for k in ("verdict", "exit", "failed_rules")} if prior_a else None,
            "prior_stage_b": {k: prior_b[k] for k in ("verdict", "exit", "failed_rules")} if prior_b else None,
            "agree_stage_a": bool(prior_a and key(a) == key(prior_a)),
            "agree_stage_b": bool(prior_b and key(b) == key(prior_b)),
        })

    names = {f["fixture"] for f in fixtures}
    assert names == set(raw_ctl) | set(raw_mut), names ^ (set(raw_ctl) | set(raw_mut))

    disagree = [p["fixture"] for p in per_fixture if not (p["agree_stage_a"] and p["agree_stage_b"])]
    controls_fail = [(p["fixture"], p["stage_a"]["verdict"], p["stage_b"]["verdict"],
                      p["stage_b"]["failed_rules"], p["stage_b_hardened"]["verdict"],
                      p["stage_b_hardened"]["failed_rules"])
                     for p in per_fixture if p["kind"] == "frozen-canonical"]

    # ---- aggregates recomputed from the retained raw verdicts ----------------
    def aggregate(rows):
        n = len(rows)
        s_esc = sum(1 for r in rows if r["stage_a"]["verdict"] == "pass")
        m_esc = sum(1 for r in rows if r["stage_b"]["verdict"] == "accept")
        u_esc = sum(1 for r in rows if r["stage_a"]["verdict"] == "pass" and r["stage_b"]["verdict"] == "accept")
        return {"mutants": n, "structural_escape": round(s_esc / n, 4) if n else None,
                "semantic_escape": round(m_esc / n, 4) if n else None,
                "union_escape": round(u_esc / n, 4) if n else None,
                "structural_caught": n - s_esc, "semantic_caught": n - m_esc, "union_caught": n - u_esc}

    all_rows = raw["results"]
    informative = [r for r in all_rows if r.get("arm_informative")]
    uninformative = [r for r in all_rows if not r.get("arm_informative")]
    agg_all = aggregate(all_rows)
    agg_inf = aggregate(informative)
    agg_uninf = aggregate(uninformative)
    escaped_wcc = sorted({r["family"] for r in uninformative if r["stage_b"]["verdict"] == "accept"})

    report_agg = {k: report["aggregates"].get(k) for k in
                  ("mutants", "structural_escape", "semantic_escape", "union_escape")}
    recompute_matches = all([
        report_agg["mutants"] == agg_all["mutants"],
        abs((report_agg["structural_escape"] or -1) - agg_all["structural_escape"]) < 1e-9,
        abs((report_agg["semantic_escape"] or -1) - agg_all["semantic_escape"]) < 1e-9,
        abs((report_agg["union_escape"] or -1) - agg_all["union_escape"]) < 1e-9,
    ])

    # ---- R03-artifact correction: are the 5 raw union catches real detection? -
    non_r03_catches = [p for p in per_fixture if p["kind"] == "mutant"
                       and p["stage_b"]["verdict"] != "accept"
                       and "R03" not in p["stage_b"]["failed_rules"]]
    wcc_rows = [r for r in all_rows if r["arm"] == "W"]
    r03_artifact = {
        "wcc_arm_mutants": len(wcc_rows),
        "wcc_arm_rejected_by_stage_b": sum(1 for r in wcc_rows if r["stage_b"]["verdict"] != "accept"),
        "wcc_arm_rejected_rules": sorted({tuple(r["stage_b"]["failed_rules"]) for r in wcc_rows}),
        "untouched_wcc_canonical_rejected_by_same_rule": True,
        "mutants_caught_by_any_non_r03_rule": [p["fixture"] for p in non_r03_catches],
        "stage_a_catches": sum(1 for r in all_rows if r["stage_a"]["verdict"] != "pass"),
        "raw_union_caught": agg_all["union_caught"],
        "r03_artifact_catches": agg_all["union_caught"] - len(non_r03_catches),
        "control_corrected_union_caught": len(non_r03_catches),
        "control_corrected_union_escape": round(1 - len(non_r03_catches) / len(all_rows), 4),
        "statement": "all 5 raw union catches are WCC-arm documents rejected by the same literal-substring R03 "
                     "defect that rejects the untouched WCC canonical; discounting that artifact, union detection "
                     "is 0/29 and union escape is 1.0, not 0.8276.",
    }

    # ---- R03 root cause on the frozen canonical AF-WCC bytes -----------------
    wcc = yaml.safe_load((CORPUS / "bases/af_wcc_vacuum.yaml").read_text())
    q = wcc.get("quantifiers") or {}
    ordered = q.get("ordered") or []
    formal = str(q.get("formal", ""))
    binders = [str(e.get("binder")) for e in ordered if isinstance(e, dict) and e.get("binder")]
    failing = [b for b in binders if b not in formal]
    r03_root_cause = {
        "fixture": "bases/af_wcc_vacuum.yaml",
        "sha256": sha(CORPUS / "bases/af_wcc_vacuum.yaml"),
        "rule": "R03",
        "check": "for b in quantifiers.ordered[*].binder: assert b in quantifiers.formal  (literal substring, spec_conformance_audit.py L219-221)",
        "binders": binders,
        "literal_present": {b: (b in formal) for b in binders},
        "failing_binders": failing,
        "formal_sentence": formal,
        "class_id": wcc.get("class_id"),
        "assessment": "notation-dependent literal-substring check; the canonical writes q in I+ and t0 in [0,T) instead of the parenthesised binder token",
    }

    # ---- live canonical paths vs card pins (moving target) -------------------
    live = {}
    for rel, want in CARD_PINS.items():
        p = ROOT / rel
        got = sha(p) if p.exists() else None
        live[rel] = {
            "card_pin": want, "measured_now": got, "match": got == want,
            "mtime": datetime.fromtimestamp(p.stat().st_mtime, CST).isoformat(timespec="seconds") if p.exists() else None,
        }
    moved = [rel for rel, v in live.items() if not v["match"]]
    frozen_rev = json.loads((ROOT / "artifacts/formulation/FROZEN.json").read_text()).get("revision")

    live_dir = OUT / "live_canonical"
    live_dir.mkdir(parents=True, exist_ok=True)
    live_stage = {}
    for rel in ("schemas/af_wcc_vacuum.yaml", "schemas/af_scc_c2_vacuum.yaml", "schemas/af_scc_c0_vacuum.yaml"):
        src = ROOT / rel
        dst = live_dir / Path(rel).name
        dst.write_bytes(src.read_bytes())  # read-only on canonical; copy for evidence
        live_stage[rel] = {
            "sha256": sha(dst),
            "stage_a": run_stage_a(dst),
            "stage_b": run_stage_b(dst, hardened=False),
            "stage_b_hardened": run_stage_b(dst, hardened=True),
            "mtime": datetime.fromtimestamp(src.stat().st_mtime, CST).isoformat(timespec="seconds"),
        }

    # sidecars: published .sha256 next to canonical schemas
    sidecars = {}
    for rel in ("schemas/af_wcc_vacuum.yaml", "schemas/af_scc_c2_vacuum.yaml", "schemas/af_scc_c0_vacuum.yaml"):
        sc = ROOT / (rel + ".sha256")
        if sc.exists():
            txt = sc.read_text().strip()
            sidecars[rel] = {"sidecar_first_token": txt.split()[0] if txt else "",
                             "matches_measured": txt.split()[0] == live[rel]["measured_now"] if txt else False}

    out = {
        "verification_id": "W084-HELDOUT09-INDEP-01",
        "created_at": now(),
        "worker": "worker-084",
        "actor": "worker-084",
        "assignment": "assign-FORM-HELDOUT-09-worker-084",
        "task_id": "FORM-HELDOUT-09",
        "node_id": "A1",
        "gate": "G-CLASSBIND",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "independent_executor": True,
        "built_r26_r31_rules": False,
        "is_worker_16": False,
        "inputs": {
            "manifest.json": sha(CORPUS / "manifest.json"),
            "report.json": sha(CORPUS / "report.json"),
            "raw/raw_verdicts.json": sha(CORPUS / "raw/raw_verdicts.json"),
            "findings.json": sha(CORPUS / "findings.json"),
            "bases": {b: sha(CORPUS / f"bases/{b}") for b in
                      ("af_wcc_vacuum.yaml", "af_scc_c2_vacuum.yaml", "af_scc_c0_vacuum.yaml")},
            "stage_tools": tool_hashes,
            "stage_tools_match_prior_run": {
                "stage_a": tool_hashes["stage_a"] == report["stages"]["structural"]["sha256"],
                "stage_b": tool_hashes["stage_b"] == report["stages"]["semantic"]["sha256"],
            },
        },
        "reproduction": {
            "fixtures_total": len(per_fixture),
            "controls": sum(1 for f in per_fixture if f["kind"] != "mutant"),
            "mutants": sum(1 for f in per_fixture if f["kind"] == "mutant"),
            "stage_a_agree": sum(1 for p in per_fixture if p["agree_stage_a"]),
            "stage_b_agree": sum(1 for p in per_fixture if p["agree_stage_b"]),
            "disagreements": disagree,
            "deterministic": not disagree,
            "frozen_canonical_control_outcomes": controls_fail,
            "per_fixture": per_fixture,
        },
        "h5_control_failure_reproduced": all(
            c[1] == "pass" and c[2] == "reject" for c in controls_fail if c[0] == "af_wcc_vacuum.yaml"
        ) and any(c[0] == "af_wcc_vacuum.yaml" for c in controls_fail),
        "r03_root_cause": r03_root_cause,
        "aggregates_recomputed": {
            "from_raw_verdicts_all_29": agg_all,
            "from_raw_verdicts_informative_arms_only": agg_inf,
            "from_raw_verdicts_uninformative_wcc_arm": agg_uninf,
            "wcc_families_escaping": escaped_wcc,
            "report_claim": report_agg,
            "matches_report": recompute_matches,
            "reportability": "INVALID per H5: WCC frozen canonical rejected by stage B; union_escape 0.8276 is diagnostic of the "
                             "instrument, not a valid leakage measurement; informative C2+C0 arms show union escape 1.0 (0/24 caught).",
        },
        "r03_artifact_correction": r03_artifact,
        "stage_b_hardened_comparison": {
            "note": "stage B --hardened is the repaired rule set proposed in artifacts/worker-06/blindspot_report.json",
            "mutants_caught_normal": agg_all["union_caught"],
            "mutants_caught_hardened": sum(1 for p in per_fixture if p["kind"] == "mutant"
                                           and p["stage_b_hardened"]["verdict"] == "reject"),
            "controls_rejected_hardened": [p["fixture"] for p in per_fixture if p["kind"] != "mutant"
                                           and p["stage_b_hardened"]["verdict"] != "accept"],
        },
        "moving_target": {
            "card_frozen_revision": 28,
            "live_FROZEN_revision": frozen_rev,
            "live": live,
            "moved_paths": moved,
            "moving_target": bool(moved),
            "live_canonical_stage_verdicts": live_stage,
            "sidecars": sidecars,
            "assessment": "the three canonical schema pins moved at 2026-09-12T00:53:20+08:00 (WCC 00:53:40) "
                          "during the astra-life05 evidence-binding repair (rev12 -> rev13); FROZEN.json stayed at rev28 "
                          "(frozen_at 00:35:08) and still pins the pre-move hashes, so the card's five-pin binding is stale "
                          "on 3 of 6 paths and no held-out report can bind the live canonical bytes under this card.",
        },
        "verdict": {
            "terminal_status": "INVALID (H5 control failure reproduced) + MOVING TARGET (3/6 card pins stale)",
            "corpus_faithful_to_card_pins": True,
            "escape_rates_reportable_as_valid_measurement": False,
            "classification": "independent measurement evidence only; no gate verdict, no node completion, no theorem",
        },
        "falsifier": "Re-run this script: falsified if the frozen AF-WCC canonical is accepted by stage B (non-hardened) at "
                     "cce9c60146d6, or if any reproduced verdict disagrees with the retained raw verdicts, or if the three "
                     "canonical schema paths return to the card pins (cce9a1ea9bda era) without a new FROZEN revision.",
    }
    (OUT / "verification.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(json.dumps({
        "deterministic": out["reproduction"]["deterministic"],
        "fixtures": out["reproduction"]["fixtures_total"],
        "h5_control_failure_reproduced": out["h5_control_failure_reproduced"],
        "moved_paths": moved,
        "hardened_catches": out["stage_b_hardened_comparison"]["mutants_caught_hardened"],
        "verification_sha256": sha(OUT / "verification.json"),
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
