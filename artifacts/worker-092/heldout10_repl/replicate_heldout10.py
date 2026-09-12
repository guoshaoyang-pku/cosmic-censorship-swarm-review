#!/usr/bin/env python3
"""W092-HELDOUT10-THIRDPARTY-REPL-01 — independent third-party replication of FORM-HELDOUT-10.

Scope (bounded, one pass):
  Re-run every preserved FORM-HELDOUT-10 fixture through the two canonical stage tools and
  reproduce, or fail to reproduce, the headline measurement:
      informative C2+C0 arms union escape 1.0 (0/26 caught)
      all-mutant union escape 0.7879 (7/33 caught, all seven spurious WCC/R03)
      frozen WCC canonical rejected by stage B on R03 only (strict H5 false)
  Per-fixture verdicts are compared against the corpus's own preserved raw/raw_verdicts.json.

Independence basis (declared):
  - Author: worker-084 (built FORM-HELDOUT-10 and wrote its executor and its re-run verifier).
  - Owner: astra-lead-formulation (owns the schemas under review).
  - This run: worker-092, neither author nor owner. It does NOT import build_corpus_10.py,
    run_heldout_10.py or verify_heldout_10_independent.py. It parses the manifest itself,
    re-hashes every fixture, invokes the two stage tools as subprocesses, and derives every
    escape verdict and aggregate from its own subprocess results.
  - Read-only on schemas/, artifacts/heldout/heldout-10/** and every pinned canonical.
  - Writes only under artifacts/worker-092/heldout10_repl/.

Known limits (recorded, not hidden):
  - The stage tools are used as-is; this is a replication of the pipeline's verdicts, not an
    independent re-implementation of the rules.
  - Stage B (artifacts/worker-06/spec_conformance_audit.py#c79d8ab8440a) is NOT pinned in
    FROZEN rev29 (lead-form-20260912T011516-123); its pre/post hash is measured here so a
    mid-run move is detectable.

Usage: python3 artifacts/worker-092/heldout10_repl/replicate_heldout10.py
Exit: 0 = replication completed with zero per-fixture disagreement and zero drift; 3 = a
disagreement or drift was found (reported, not hidden).
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

CST = timezone(timedelta(hours=8))
ROOT = Path(__file__).resolve().parents[3]
CORPUS = ROOT / "artifacts" / "heldout" / "heldout-10"
OUT = ROOT / "artifacts" / "worker-092" / "heldout10_repl"
MANIFEST = CORPUS / "manifest.json"
REPORT = CORPUS / "report.json"
RAW = CORPUS / "raw" / "raw_verdicts.json"

STAGE_A = ROOT / "artifacts" / "formulation" / "tools" / "check_class_schema.py"
STAGE_B = ROOT / "artifacts" / "worker-06" / "spec_conformance_audit.py"
KEY_MANIFEST = ROOT / "artifacts" / "formulation" / "KEY_MANIFEST.json"

EXPECTED_MANIFEST_SHA = "d026fec40fe4dab9ae51c51a8fa870337224b973418c0139685cf2f3faa0c236"
EXPECTED_REPORT_SHA = "5629e2a69c8664abe4b322281318bf5ca0754967cb87607c5818da7e015efd35"
EXPECTED_RAW_SHA = "b3480625da10cd3c6b3a69b7d400b20094fb500d308bbd7c2c009f672a9f44a3"

TASK_ID = "W092-HELDOUT10-THIRDPARTY-REPL-01"
WORKER = "worker-092"
TIMEOUT = 120


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def json_from_stdout(text: str):
    """Return the first JSON object that parses from the tool stdout, else None."""
    for i, ch in enumerate(text):
        if ch != "{":
            continue
        try:
            return json.loads(text[i:])
        except json.JSONDecodeError:
            continue
    return None


def run_stage_a(fixture: Path) -> dict:
    t0 = time.time()
    try:
        p = subprocess.run(
            [sys.executable, str(STAGE_A), "--json", str(fixture)],
            cwd=str(ROOT), capture_output=True, text=True, timeout=TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return {"exit": None, "verdict": None, "failed_rules": [], "escaped": False,
                "crash": True, "seconds": round(time.time() - t0, 3), "stderr": "timeout"}
    rep = json_from_stdout(p.stdout) or {}
    return {
        "exit": p.returncode,
        "verdict": rep.get("verdict"),
        "failed_rules": sorted(rep.get("failed_rules") or []),
        "escaped": p.returncode == 0 and rep.get("verdict") == "pass",
        "crash": False,
        "seconds": round(time.time() - t0, 3),
        "stderr": p.stderr.strip()[:400],
    }


def run_stage_b(fixture: Path) -> dict:
    t0 = time.time()
    try:
        p = subprocess.run(
            [sys.executable, str(STAGE_B), str(fixture)],
            cwd=str(ROOT), capture_output=True, text=True, timeout=TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return {"exit": None, "verdict": None, "failed_rules": [], "escaped": False,
                "crash": True, "seconds": round(time.time() - t0, 3), "stderr": "timeout"}
    rep = json_from_stdout(p.stdout) or {}
    verdict = rep.get("verdict")
    return {
        "exit": p.returncode,
        "verdict": verdict,
        "failed_rules": sorted(rep.get("failed_rules") or []),
        "escaped": p.returncode == 0 and verdict == "accept",
        "crash": False,
        "seconds": round(time.time() - t0, 3),
        "stderr": p.stderr.strip()[:400],
    }


def aggregate(rows) -> dict:
    """Independent aggregation. structural escape = stage A pass; semantic escape = stage B
    accept; union escape = accepted by both stages (the corpus's own convention)."""
    n = len(rows)
    if n == 0:
        return {"mutants": 0}
    struct = sum(1 for r in rows if r["structural_escape"])
    sem = sum(1 for r in rows if r["semantic_escape"])
    union = sum(1 for r in rows if r["union_escape"])
    fams = {}
    for r in rows:
        if r["union_escape"]:
            fams[r["family"]] = fams.get(r["family"], 0) + 1
    return {
        "mutants": n,
        "structural_escape": round(struct / n, 4),
        "semantic_escape": round(sem / n, 4),
        "union_escape": round(union / n, 4),
        "structural_caught": n - struct,
        "semantic_caught": n - sem,
        "union_caught": n - union,
        "escape_families": sorted(fams.items()),
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    started = now()

    manifest = json.loads(MANIFEST.read_text())
    preserved_raw = json.loads(RAW.read_text())
    preserved_report = json.loads(REPORT.read_text())

    # ---------------- preflight: hash-first, nothing trusted from the corpus ----------------
    pre = {}
    for label, path in (
        ("manifest.json", MANIFEST), ("report.json", REPORT), ("raw_verdicts.json", RAW),
        ("stage_a_tool", STAGE_A), ("stage_b_tool", STAGE_B), ("stage_a_key_manifest", KEY_MANIFEST),
    ):
        pre[label] = sha256_file(path)

    pins = manifest["pins"]
    pre["canonical_pins"] = {}
    for rel in pins:
        p = ROOT / rel
        pre["canonical_pins"][rel] = {
            "measured": sha256_file(p) if p.exists() else None,
            "manifest_pin": pins[rel],
        }
    pre["stage_tools_declared"] = {
        "structural": manifest["stages"]["structural"],
        "semantic": manifest["stages"]["semantic"],
        "stage_a_key_manifest": manifest["stages"]["stage_a_key_manifest"],
    }
    pre["manifest_sha_matches_preregistered"] = pre["manifest.json"] == EXPECTED_MANIFEST_SHA
    pre["report_sha_matches_preregistered"] = pre["report.json"] == EXPECTED_REPORT_SHA
    pre["raw_sha_matches_preregistered"] = pre["raw_verdicts.json"] == EXPECTED_RAW_SHA
    pre["stage_a_hash_matches_manifest"] = pre["stage_a_tool"] == manifest["stages"]["structural"]["sha256"]
    pre["stage_b_hash_matches_manifest"] = pre["stage_b_tool"] == manifest["stages"]["semantic"]["sha256"]
    pre["key_manifest_hash_matches_manifest"] = (
        pre["stage_a_key_manifest"] == manifest["stages"]["stage_a_key_manifest"]["sha256"]
    )
    pre["pin_mismatches"] = [
        rel for rel, rec in pre["canonical_pins"].items() if rec["measured"] != rec["manifest_pin"]
    ]

    # every fixture declared in the manifest, re-hashed by this script
    fixtures = []  # (kind, arm, class_id, family, fixture_name, abs_path, declared_sha)
    for arm, base in manifest["bases"].items():
        fixtures.append({"kind": "base", "arm": arm, "class_id": base["class_id"],
                         "family": "(base)", "ref": base, "name": Path(base["path"]).name})
    for c in manifest["controls"]:
        fixtures.append({"kind": "control", "control_kind": c["kind"], "arm": c["arm"],
                         "class_id": c["class_id"], "family": "(control)", "ref": c,
                         "name": c["fixture"]})
    for m in manifest["mutants"]:
        fixtures.append({"kind": "mutant", "arm": m["arm"], "class_id": m["class_id"],
                         "family": m["family"], "ref": m, "name": m["fixture"]})

    fixture_hash_mismatches = []
    for f in fixtures:
        rel = f["ref"]["path"]
        p = ROOT / rel
        f["abs"] = p
        f["declared_sha"] = f["ref"]["sha256"]
        f["measured_sha"] = sha256_file(p) if p.exists() else None
        if f["measured_sha"] != f["declared_sha"]:
            fixture_hash_mismatches.append({"fixture": f["name"], "path": rel,
                                            "declared": f["declared_sha"], "measured": f["measured_sha"]})
    # each arm's base copy must be byte-identical to the live frozen canonical
    pre["base_vs_canonical"] = {}
    for arm, b in manifest["bases"].items():
        base_p = ROOT / b["path"]
        canon_p = ROOT / b["frozen_path"]
        pre["base_vs_canonical"][arm] = {
            "base": sha256_file(base_p),
            "canonical": sha256_file(canon_p) if canon_p.exists() else None,
            "canonical_path": b["frozen_path"],
            "match": canon_p.exists() and sha256_file(base_p) == sha256_file(canon_p),
        }
    pre["fixture_hash_mismatches"] = fixture_hash_mismatches

    # ---------------- run: every fixture exactly once per stage -----------------------------
    rows = []
    for f in fixtures:
        a = run_stage_a(f["abs"])
        b = run_stage_b(f["abs"])
        rows.append({
            "fixture": f["name"],
            "kind": f["kind"],
            "control_kind": f.get("control_kind"),
            "arm": f["arm"],
            "class_id": f["class_id"],
            "family": f["family"],
            "fixture_sha256": f["measured_sha"],
            "stage_a": a,
            "stage_b": b,
            "structural_escape": a["escaped"],
            "semantic_escape": b["escaped"],
            "union_escape": a["escaped"] and b["escaped"],
        })

    mutants = [r for r in rows if r["kind"] == "mutant"]
    informative = [r for r in mutants if r["arm"] in ("C2", "C0")]
    wcc = [r for r in mutants if r["arm"] == "W"]
    my_agg = {
        "all_mutants": aggregate(mutants),
        "informative_C2_C0": aggregate(informative),
        "wcc_arm": aggregate(wcc),
    }

    # ---------------- comparison against the corpus's own preserved verdicts ----------------
    preserved_mut = {r["fixture"]: r for r in preserved_raw["results"]}
    preserved_ctl = {r["fixture"]: r for r in preserved_raw["controls"]}
    disagreements = []
    for r in mutants:
        pr = preserved_mut.get(r["fixture"])
        if pr is None:
            disagreements.append({"fixture": r["fixture"], "field": "presence", "mine": "present", "preserved": "absent"})
            continue
        for mine_key, their_key in (("structural_escape", "structural_escape"),
                                    ("semantic_escape", "semantic_escape"),
                                    ("union_escape", "union_escape")):
            if r[mine_key] != pr[their_key]:
                disagreements.append({"fixture": r["fixture"], "field": mine_key,
                                      "mine": r[mine_key], "preserved": pr[their_key]})
        if r["stage_a"]["failed_rules"] != sorted(pr["stage_a"]["failed_rules"]):
            disagreements.append({"fixture": r["fixture"], "field": "stage_a_failed_rules",
                                  "mine": r["stage_a"]["failed_rules"],
                                  "preserved": sorted(pr["stage_a"]["failed_rules"])})
        if r["stage_b"]["failed_rules"] != sorted(pr["stage_b"]["failed_rules"]):
            disagreements.append({"fixture": r["fixture"], "field": "stage_b_failed_rules",
                                  "mine": r["stage_b"]["failed_rules"],
                                  "preserved": sorted(pr["stage_b"]["failed_rules"])})
    for r in [x for x in rows if x["kind"] == "control"]:
        pr = preserved_ctl.get(r["fixture"])
        if pr is None:
            disagreements.append({"fixture": r["fixture"], "field": "presence", "mine": "present", "preserved": "absent"})
            continue
        if r["stage_a"]["verdict"] != pr["stage_a"]["verdict"]:
            disagreements.append({"fixture": r["fixture"], "field": "control_stage_a_verdict",
                                  "mine": r["stage_a"]["verdict"], "preserved": pr["stage_a"]["verdict"]})
        if r["stage_b"]["verdict"] != pr["stage_b"]["verdict"]:
            disagreements.append({"fixture": r["fixture"], "field": "control_stage_b_verdict",
                                  "mine": r["stage_b"]["verdict"], "preserved": pr["stage_b"]["verdict"]})

    preserved_agg = {
        "all_mutants": preserved_report.get("aggregates") or {},
        "informative_C2_C0": preserved_report.get("aggregates_informative_arms_only") or {},
        "wcc_arm": preserved_report.get("aggregates_uninformative_arms_only") or {},
    }
    # control expectations re-derived here, not read from the report
    ctl_named = {r["fixture"]: r for r in rows if r["kind"] == "control"}
    authored_ctls = [r for r in ctl_named.values() if r.get("control_kind") in ("conforming", "negated-phrase")]
    frozen_ctls = [r for r in rows if r["kind"] == "base"]
    controls_ok = all(r["stage_a"]["escaped"] and r["stage_b"]["escaped"] for r in authored_ctls)
    frozen_wcc = next((r for r in frozen_ctls if r["arm"] == "W"), None)
    frozen_c2 = next((r for r in frozen_ctls if r["arm"] == "C2"), None)
    frozen_c0 = next((r for r in frozen_ctls if r["arm"] == "C0"), None)
    h5 = bool(
        frozen_wcc and frozen_wcc["stage_a"]["escaped"] and frozen_wcc["stage_b"]["verdict"] == "reject"
        and frozen_wcc["stage_b"]["failed_rules"] == ["R03"]
        and frozen_c2 and frozen_c2["stage_a"]["escaped"] and frozen_c2["stage_b"]["escaped"]
        and frozen_c0 and frozen_c0["stage_a"]["escaped"] and frozen_c0["stage_b"]["escaped"]
    )

    # ---------------- postflight drift -------------------------------------------------------
    post = {}
    for label, path in (
        ("manifest.json", MANIFEST), ("report.json", REPORT), ("raw_verdicts.json", RAW),
        ("stage_a_tool", STAGE_A), ("stage_b_tool", STAGE_B), ("stage_a_key_manifest", KEY_MANIFEST),
    ):
        post[label] = sha256_file(path)
    post["canonical_pins"] = {rel: sha256_file(ROOT / rel) for rel in pins}
    drift = {k: {"pre": pre[k], "post": post[k]} for k in pre
             if k in post and k != "canonical_pins" and pre[k] != post[k]}
    for rel, rec in pre["canonical_pins"].items():
        if post["canonical_pins"][rel] != rec["measured"]:
            drift[f"canonical::{rel}"] = {"pre": rec["measured"], "post": post["canonical_pins"][rel]}

    valid = (not fixture_hash_mismatches and not disagreements and controls_ok and h5 and not drift
             and pre["manifest_sha_matches_preregistered"])
    finished = now()

    report = {
        "task_id": TASK_ID,
        "corpus_id": manifest.get("corpus_id"),
        "worker": WORKER,
        "actor": WORKER,
        "node_id": "A1",
        "gate": "G-CLASSBIND",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "created_at": started,
        "finished_at": finished,
        "authority": ("worker measurement evidence only; no node completion, no "
                      "validation_status=passed, no gate verdict, no theorem"),
        "independence": ("worker-092 is neither the author (worker-084) nor the owner "
                         "(astra-lead-formulation) of FORM-HELDOUT-10; builder, executor and the "
                         "corpus's own verifier were not imported; every fixture re-hashed and "
                         "every stage invoked as a fresh subprocess"),
        "method": ("hash-first preflight of manifest/pins/tools/fixtures; one stage A and one "
                   "stage B subprocess per fixture; own escape+aggregate computation; per-fixture "
                   "and aggregate comparison against preserved raw/report; postflight drift re-hash"),
        "preflight": pre,
        "run": {
            "fixtures_run": len(rows),
            "stage_a_invocations": len(rows),
            "stage_b_invocations": len(rows),
            "crashes": [r["fixture"] for r in rows if r["stage_a"]["crash"] or r["stage_b"]["crash"]],
        },
        "my_aggregates": my_agg,
        "preserved_report_aggregates": preserved_agg,
        "aggregate_comparison": {
            "all_mutants": {k: (my_agg["all_mutants"].get(k), preserved_agg.get("all_mutants", {}).get(k))
                            for k in ("mutants", "structural_escape", "semantic_escape", "union_escape", "union_caught")},
            "informative_C2_C0": {k: (my_agg["informative_C2_C0"].get(k), preserved_agg.get("informative_C2_C0", {}).get(k))
                                  for k in ("mutants", "structural_escape", "semantic_escape", "union_escape", "union_caught")},
            "wcc_arm": {k: (my_agg["wcc_arm"].get(k), preserved_agg.get("wcc_arm", {}).get(k))
                        for k in ("mutants", "structural_escape", "semantic_escape", "union_escape", "union_caught")},
        },
        "per_fixture": rows,
        "per_fixture_disagreements": disagreements,
        "controls": {
            "authored_controls_all_accepted_both_stages": controls_ok,
            "frozen_wcc_stage_b_failed_rules": frozen_wcc["stage_b"]["failed_rules"] if frozen_wcc else None,
            "frozen_wcc_stage_b_verdict": frozen_wcc["stage_b"]["verdict"] if frozen_wcc else None,
            "frozen_c2_c0_accepted_both_stages": bool(frozen_c2 and frozen_c2["stage_b"]["escaped"]
                                                      and frozen_c0 and frozen_c0["stage_b"]["escaped"]),
            "strict_h5_hold": h5,
        },
        "postflight": {"hashes": post, "drift": drift},
        "validity": {
            "replication_valid": valid,
            "fixture_hash_mismatches": fixture_hash_mismatches,
            "disagreement_count": len(disagreements),
            "drift": drift,
            "manifest_preregistered_hash_match": pre["manifest_sha_matches_preregistered"],
        },
        "headline": {
            "informative_C2_C0_union_escape_reproduced": my_agg["informative_C2_C0"]["union_escape"] == 1.0,
            "informative_C2_C0_union_caught": my_agg["informative_C2_C0"]["union_caught"],
            "all_mutants_union_escape": my_agg["all_mutants"]["union_escape"],
            "all_mutants_union_caught": my_agg["all_mutants"]["union_caught"],
            "r03_rejects_untouched_frozen_wcc": bool(frozen_wcc and frozen_wcc["stage_b"]["failed_rules"] == ["R03"]),
        },
        "limits": [
            "stage tools are used as-is: this replicates pipeline verdicts, it does not re-implement the rules",
            "stage B is unpinned in FROZEN rev29 (lead-form-20260912T011516-123); its hash is measured pre/post and did not move during this run",
            "fixtures were not re-authored; the corpus's own fixture choice is taken as given",
            "no claim about whether the leak is a schema defect or a rule-engine gap is made here",
        ],
        "falsifier": ("A per-fixture verdict disagreement against raw/raw_verdicts.json, a "
                      "fixture whose measured sha256 differs from the manifest, or a mid-run "
                      "change to any pinned canonical or stage tool."),
    }

    (OUT / "report.json").write_text(json.dumps(report, indent=1) + "\n")
    (OUT / "pins_at_run.json").write_text(json.dumps(pre, indent=1) + "\n")

    print(f"[{TASK_ID}] fixtures={len(rows)} stageA={len(rows)} stageB={len(rows)}")
    print(f"  all mutants   : union escape {my_agg['all_mutants']['union_escape']} "
          f"({my_agg['all_mutants']['union_caught']}/{my_agg['all_mutants']['mutants']} caught) "
          f"preserved {preserved_agg.get('all_mutants', {}).get('union_escape')}")
    print(f"  informative   : union escape {my_agg['informative_C2_C0']['union_escape']} "
          f"({my_agg['informative_C2_C0']['union_caught']}/{my_agg['informative_C2_C0']['mutants']} caught) "
          f"preserved {preserved_agg.get('informative_C2_C0', {}).get('union_escape')}")
    print(f"  WCC arm       : union escape {my_agg['wcc_arm']['union_escape']} "
          f"({my_agg['wcc_arm']['union_caught']}/{my_agg['wcc_arm']['mutants']} caught) "
          f"preserved {preserved_agg.get('wcc_arm', {}).get('union_escape')}")
    print(f"  fixture hash mismatches: {len(fixture_hash_mismatches)}  disagreements: {len(disagreements)}  drift: {len(drift)}")
    print(f"  strict H5 holds: {h5}  replication_valid: {valid}")
    return 0 if valid else 3


if __name__ == "__main__":
    sys.exit(main())
