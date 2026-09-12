#!/usr/bin/env python3
"""W064-R03-CAUSE-01 -- root cause and repair sensitivity of the canonical WCC R03 rejection.

Worker: worker-064.  Node A1 (calibration evidence), gate G-AUDIT.  Classes: the three
frozen class schemas, primary AF-WCC-VAC-GEN.

Question: the adopted semantic auditor (`artifacts/worker-06/spec_conformance_audit.py`,
sha256 c79d8ab8440a) rejects canonical `schemas/af_wcc_vacuum.yaml` (sha256 d9cebb9404b2, FROZEN rev29)
on exactly one rule, R03 `binder '(q,t0)' absent from formal sentence`.  This script
establishes, from bytes:

  Q1  is R03 a true positive (schema text inconsistent with its own declared binder list)
      or an auditor false positive?
  Q2  did the rejection exist before the rev12 WCC revision, or is it a rev12/rev13 regression?
  Q3  what is the minimal spec-faithful repair, and does it preserve the rest of the schema?
  Q4  is R03 the *sole* residual blocker to `valid_for_calibration=true` once the
      independently-reported ADJ-CONTROL-STALENESS control rebase and pin refresh are
      applied?

Read-only with respect to all canonical artifacts: every mutation happens in a mirror
under `work/` built from pinned bytes at the start of the run.  The canonical suite
runner is never executed in place (it writes observed_verdicts.json next to itself); a
copy is run inside each mirror.

Exit codes
  0   all measured expectations reproduced
  1   snapshot drift on a pinned canonical artifact (moving target; report still written)
  2   a measured expectation was falsified (report written with status=falsified)
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

CST = timezone(timedelta(hours=8))
HERE = Path(__file__).resolve().parent          # artifacts/worker-064/r03_cause
REPO = HERE.parents[2]                           # ai4math-swarm
WORK = HERE / "work"
RAW = HERE / "raw"
PATCH = HERE / "patch_candidates"

# ---- pinned snapshot (canonical bytes this audit binds to) -------------------------
# FROZEN rev29 (frozen_at 2026-09-12T00:55:02+08:00): F1 rev13 d9cebb9404b2, F2a rev13
# e9a27996dfd3, F2b rev13 b2ab6acb2bbe.  The previous rev28 bytes (cce9c60146d6 / 5476a3f2c6bc
# / 55d0a1ea9bda) were replaced while this audit was being developed; see
# report.json#churn_observation.  A one-time snapshot is taken at run start and every mirror
# is built from it, so the run is atomic with respect to further canonical churn.
PINS = {
    "schemas/af_wcc_vacuum.yaml": "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "schemas/af_scc_c2_vacuum.yaml": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "schemas/af_scc_c0_vacuum.yaml": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "artifacts/formulation/tools/check_class_schema.py": "000e09e46b2fb4abc047c21e99165cbc55692f3132744fb27e84645609263aff",
    "artifacts/worker-06/spec_conformance_audit.py": "c79d8ab8440ac6738bb61df5a33e9fd5f8319b4e74e1f2e9c0fc5083fb408cec",
    "artifacts/formulation/rule_spec.json": None,   # pinned at run start, drift-checked
    "artifacts/formulation/KEY_MANIFEST.json": "014e2d3019781632cdb78ace266cf08cc11f9cf8b8ef0a049beb74eb9c6b6b9a",
    "schemas/semantic_contract_tests/manifest.json": "b2e8bd17892b6c5eba1b2d7dde48c9205d07854d025df042fb7a3d919a574f65",
    "schemas/semantic_contract_tests/fixtures/controls/control_comment_only_composite.yaml": "a6ad2638dc993c32f7cc46a1a84441581ab785ba02c84a5197663e6284c86f2a",
    "schemas/semantic_contract_tests/fixtures/controls/control_conforming_base.yaml": "7b910cf34e64baa7d2d02e229f7bfb5224ffb3fa70d264e1cc1f5ec3173e41eb",
    "schemas/semantic_contract_tests/fixtures/controls/control_quoted_forbidden_phrase.yaml": "687fd697130497633e63b696ac90d0939c2699fd6d5f3b1bca06b55f5948dee6",
    # historical (rev11) WCC bytes, accepted by the same auditor at the same tool hash
    "artifacts/worker-061/f1_independent_verdict/pinned/af_wcc_vacuum.yaml": "9a8bd4c9680042a40894f6085f183661500966f2d787a6bf28a7098a271ed503",
    # FROZEN revision marker (informational pin only; never staged or verified)
    "artifacts/formulation/FROZEN.json": "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
}

MIRROR_FILES = [
    "artifacts/formulation/tools/check_class_schema.py",
    "artifacts/formulation/rule_spec.json",
    "artifacts/formulation/KEY_MANIFEST.json",
    "artifacts/worker-06/spec_conformance_audit.py",
    "schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
]

SNAP_FILES = MIRROR_FILES + [
    "artifacts/worker-061/f1_independent_verdict/pinned/af_wcc_vacuum.yaml",
]

# canonical WCC path hashes observed while this audit was being built (churn evidence)
CHURN_OBSERVATION = {
    "live_wcc_hashes_observed": [
        {"hash_prefix": "cce9c60146d6", "frozen_revision": 28,
         "source": "run-start snapshot of the first complete harness run (raw/report.pre_final.json)"},
        {"hash_prefix": "bf0c28fa673e", "frozen_revision": 28,
         "source": "unmodified canonical copy in work/S1 of the second complete harness run (schema edit applied only in S2/S3)"},
        {"hash_prefix": "d9cebb9404b2", "frozen_revision": 29,
         "source": "unmodified canonical copy in work/S4 of the second complete harness run; pinned by FROZEN rev29"},
    ],
    "note": ("The canonical WCC path was observed at three distinct live hashes inside ~3 minutes; FROZEN "
             "moved rev28 (frozen_at 00:35:08, WCC cce9c60146d6) -> rev29 (frozen_at 00:55:02, WCC d9cebb9404b2), "
             "and C0/C2 were re-pinned to b2ab6acb2bbe / e9a27996dfd3 at the same time. FROZEN.json itself moved "
             "again during the final run (3d9e3d77fd87 -> 815e08079aef, still revision 29). Any verdict bound to the "
             "rev28 hashes (WCC cce9c60146d6, C2 5476a3f2c6bc, C0 55d0a1ea9bda) is void. "
             "2f51ace6ef74 is NOT a live hash: it is the deterministic E1a repair applied to rev13 bytes "
             "(work/S2 mirror, candidate E1a), reported here to avoid mis-citing it as churn."),
}

FORMAL_TAIL = "not exists q in I+ and t0 in [0,T) with gamma([t0,T)) subset J^-(q) intersect M."
BINDER_LINE = '- {kind: not_exists, binder: "(q,t0)", domain_id: D5}'

CANDIDATES = {
    "E1a": ("schema-side, tuple binder + D5 domain reference",
            "not exists (q,t0) in D5 with gamma([t0,T)) subset J^-(q) intersect M."),
    "E1b": ("schema-side, tuple binder + explicit product domain",
            "not exists (q,t0) in I+ x [0,T) with gamma([t0,T)) subset J^-(q) intersect M."),
    "E1c": ("schema-side, tuple binder + split domain clauses",
            "not exists (q,t0) with q in I+ and t0 in [0,T) and gamma([t0,T)) subset J^-(q) intersect M."),
}

CONTROL_EDITS = {
    # (A) top-level revised_at_unused -> extensions.revised_at_unused   (R22)
    # (B) delete the 8-line misplaced finite_codimension_complement -> residual_comeager
    #     'direction: transfers' entry from genericity.transfer_failures (R28)
    "A_from": "revised_at_unused: '2026-09-11T23:30:35+08:00'\n",
    "A_to": "extensions:\n  revised_at_unused: '2026-09-11T23:30:35+08:00'\n",
    "B_block": (
        "  - pair:\n"
        "    - finite_codimension_complement\n"
        "    - residual_comeager\n"
        "    direction: transfers\n"
        "    witness: a countable union of proper closed finite-codimension submanifolds is\n"
        "      meager\n"
        "    status: elementary\n"
        "    citation_status: n/a\n"
    ),
}

R03_ORIG = (
    "                for b in binders:\n"
    "                    if b not in formal:\n"
    "                        bad.append(f\"binder {b!r} absent from formal sentence\")\n"
)
R03_RELAXED = (
    "                for b in binders:\n"
    "                    if b in formal:\n"
    "                        continue\n"
    "                    parts = [p.strip() for p in b.strip(\"()\").split(\",\") if p.strip()]\n"
    "                    if parts and all(p in formal for p in parts):\n"
    "                        continue\n"
    "                    bad.append(f\"binder {b!r} absent from formal sentence\")\n"
)


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def read_json(p: Path):
    return json.loads(Path(p).read_text())


def write_json(p: Path, obj) -> None:
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(json.dumps(obj, indent=1) + "\n")


def run(cmd, timeout=180):
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return {"cmd": [str(c) for c in cmd], "exit": proc.returncode,
            "stdout": proc.stdout, "stderr": proc.stderr.strip()[:500]}


def structural(mirror: Path, target: Path) -> dict:
    tool = mirror / "artifacts/formulation/tools/check_class_schema.py"
    r = run([sys.executable, str(tool), "--json", str(target)])
    try:
        rep = json.loads(r["stdout"][r["stdout"].index("{"):])
    except (ValueError, json.JSONDecodeError):
        rep = {}
    accepted = r["exit"] == 0 and rep.get("verdict") == "pass"
    return {"tool": "structural", "exit": r["exit"], "verdict": rep.get("verdict", "no_verdict"),
            "failed_rules": rep.get("failed_rules", []), "accepted": accepted,
            "rejected": rep.get("verdict") == "fail", "checks": rep.get("checks", []),
            "stderr": r["stderr"]}


def semantic(mirror: Path, target: Path, out: Path, hardened: bool, tool: Path | None = None) -> dict:
    tool = tool or (mirror / "artifacts/worker-06/spec_conformance_audit.py")
    cmd = [sys.executable, str(tool), str(target)]
    if hardened:
        cmd.append("--hardened")
    cmd += ["--json", str(out)]
    r = run(cmd)
    rep = read_json(out) if out.exists() else {}
    return {"tool": "semantic_hardened" if hardened else "semantic_baseline",
            "exit": r["exit"], "verdict": rep.get("verdict", "no_verdict"),
            "failed_rules": rep.get("failed_rules", []),
            "undecided_rules": rep.get("undecided_rules", []),
            "accepted": rep.get("verdict") == "accept", "rejected": rep.get("verdict") == "reject",
            "checks": rep.get("checks", []), "doc_sha256": rep.get("doc_sha256"),
            "stderr": r["stderr"]}


def triplet(mirror: Path, target: Path, tag: str, sem_tool: Path | None = None) -> dict:
    out_b = RAW / f"{tag}.semantic_baseline.json"
    out_h = RAW / f"{tag}.semantic_hardened.json"
    return {"structural": structural(mirror, target),
            "semantic_baseline": semantic(mirror, target, out_b, False, sem_tool),
            "semantic_hardened": semantic(mirror, target, out_h, True, sem_tool)}


SNAP = WORK / "_frozen"


def build_snapshot() -> dict:
    """One-time copy of every pinned input; all mirrors are built from this, never from REPO."""
    if SNAP.exists():
        shutil.rmtree(SNAP)
    for rel in SNAP_FILES:
        src, dst = REPO / rel, SNAP / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    shutil.copytree(REPO / "schemas/semantic_contract_tests", SNAP / "schemas/semantic_contract_tests",
                    ignore=shutil.ignore_patterns("__pycache__", ".tmp_audit_*"))
    bad = {rel: {"expected": PINS[rel], "frozen": sha(SNAP / rel)}
           for rel in SNAP_FILES if PINS.get(rel) and sha(SNAP / rel) != PINS[rel]}
    return bad


def build_mirror(dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    for rel in MIRROR_FILES:
        src, dst = SNAP / rel, dest / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    shutil.copytree(SNAP / "schemas/semantic_contract_tests", dest / "schemas/semantic_contract_tests",
                    ignore=shutil.ignore_patterns("__pycache__", ".tmp_audit_*"))


def rebase_controls(mirror: Path) -> dict:
    out = {}
    for rel in [k for k in PINS if k.startswith("schemas/semantic_contract_tests/fixtures/controls/")]:
        p = mirror / rel
        raw = p.read_text()
        assert raw.count(CONTROL_EDITS["A_from"]) == 1, f"A anchor not unique in {rel}"
        assert raw.count(CONTROL_EDITS["B_block"]) == 1, f"B block not unique in {rel}"
        new = raw.replace(CONTROL_EDITS["A_from"], CONTROL_EDITS["A_to"], 1)
        new = new.replace(CONTROL_EDITS["B_block"], "", 1)
        p.write_text(new)
        out[Path(rel).name] = {"old_sha256": sha(SNAP / rel), "rebased_sha256": sha(p),
                               "removed_lines": len(CONTROL_EDITS["B_block"].splitlines()),
                               "added_lines": len(CONTROL_EDITS["A_to"].splitlines())}
    return out


def refresh_pins(mirror: Path, groups=("fixtures", "controls", "conforming_canonical_controls")) -> dict:
    mp = mirror / "schemas/semantic_contract_tests/manifest.json"
    m = read_json(mp)
    changed = {}
    for group in groups:
        for e in m[group]:
            f = e["fixture"]
            target = (mirror / "schemas/semantic_contract_tests" / f) if f.startswith("fixtures/") \
                else (mirror / f)
            got = sha(target)
            if got != e["sha256"]:
                changed[e["test_id"]] = {"old": e["sha256"][:12], "new": got[:12]}
                e["sha256"] = got
    write_json(mp, m)
    return changed


def run_suite(mirror: Path, label: str) -> dict:
    runner = mirror / "schemas/semantic_contract_tests/run_contract_tests.py"
    r = run([sys.executable, str(runner)], timeout=900)
    (RAW / f"{label}.stdout.txt").write_text(r["stdout"] + "\n--- stderr ---\n" + r["stderr"] + "\n")
    obs = mirror / "schemas/semantic_contract_tests/observed_verdicts.json"
    rep = read_json(obs) if obs.exists() else {}
    if obs.exists():
        shutil.copy2(obs, RAW / f"{label}.observed_verdicts.json")
    summary = rep.get("summary", {})
    validity = rep.get("validity", {})
    conforming = [x for x in rep.get("results", []) if x.get("kind") == "conforming_canonical"]
    controls = [x for x in rep.get("results", []) if x.get("kind") == "frozen_control"]
    return {
        "label": label, "exit": r["exit"], "valid_for_calibration": validity.get("valid_for_calibration"),
        "blocking_adjudication": validity.get("blocking_adjudication"),
        "mutants_structural": summary.get("structural_caught"),
        "mutants_baseline": summary.get("semantic_baseline_caught"),
        "mutants_hardened": summary.get("semantic_hardened_caught"),
        "controls_accepted": summary.get("controls_accepted_both_stages"),
        "conforming_accepted": summary.get("conforming_canonical_accepted_both_stages"),
        "conforming_rejections": {x["test_id"]: {"fixture": x["fixture"],
                                                 "accepted_by": x["observed"]["accepted_by"],
                                                 "rejected_by": x["observed"]["rejected_by"],
                                                 "failed_rules": {s: v.get("failed_rules")
                                                                  for s, v in x["observed"]["stages"].items()}}
                                  for x in conforming if x["observed"]["rejected_by"]},
        "controls_rejections": {x["test_id"]: x["observed"]["rejected_by"]
                                for x in controls if x["observed"]["rejected_by"]},
        "fixture_hashes": {x["test_id"]: x.get("sha256") for x in rep.get("results", [])},
        "stdout_tail": r["stdout"].strip().splitlines()[-6:],
    }


def main() -> int:
    started = now()
    WORK.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    PATCH.mkdir(parents=True, exist_ok=True)

    report = {
        "task_id": "W064-R03-CAUSE-01",
        "worker": "worker-064",
        "created_at": started,
        "node_id": "A1",
        "gate": "G-AUDIT",
        "class_id": "AF-WCC-VAC-GEN",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "not_claimed": ["no gate verdict", "no node completion", "no modification of any canonical artifact",
                        "no mathematical verdict beyond the measured rule text",
                        "no claim of first discovery: worker-080 (00:42:43) and worker-16 (00:46:41) "
                        "independently identified the R03 literal-match blocker first; this task replicates "
                        "it independently and adds the regression provenance and the end-to-end sole-blocker "
                        "determination"],
        "prior_work_cross_reference": {
            "w080-sr-20260912T004243-blocker-f1r03 (00:42:43)": "rebased-control suite still invalid at rev28 because SCT-K03 fails R03; Probe B: lexical, not semantic; equivalent D5-relative rewrite clears R03",
            "w16-R03-ADJ-01 (00:46:41)": "independent R03 adjudication; one-clause literal rendering (V1) accepted; variable-wise tool patch accepts frozen bytes and still rejects an unbound control; Options A (amend tool) / B (edit F1, new hash + re-review)",
            "W064-SEMCT-REBASE-01 (00:43:59)": "rebased-control proposal and suite numbers this audit re-derives independently",
            "W004-SEMCT-CONTROL-REBASE-01 (00:39:40)": "control rebase end-to-end; rev27_patched exit 0 valid true, rev28_patched exit 3 valid false",
            "unique_here": ["rev11->rev12 regression provenance with pinned rev11 bytes both semantic stages R03-pass",
                            "three schema-side one-clause candidates + binder-list alternative + tool-relaxation with mutant-loss measurement",
                            "S1 vs S2 end-to-end: R03 is the sole residual blocker after the control rebase and pin refresh (exit 3 -> 0, valid false -> true, mutants unchanged 32/11/32)"],
        },
    }

    # ---- step 0: pins / drift -------------------------------------------------------
    pins, drift, info_drift = {}, {}, {}
    for rel, want in PINS.items():
        got = sha(REPO / rel)
        pins[rel] = got
        if want and got != want:
            (info_drift if rel.endswith("FROZEN.json") else drift)[rel] = {"expected": want, "measured": got}
    rule_spec_sha = sha(REPO / "artifacts/formulation/rule_spec.json")
    pins["artifacts/formulation/rule_spec.json"] = rule_spec_sha
    report["snapshot"] = pins
    report["snapshot_drift"] = drift
    report["informational_drift"] = info_drift
    if drift:
        report["status"] = "measurement_error_snapshot_drift"
        write_json(HERE / "report.json", report)
        print("SNAPSHOT DRIFT:", json.dumps(drift, indent=1))
        return 1

    # ---- step 1: one-time frozen snapshot + base mirror (never read REPO again) -----
    frozen_bad = build_snapshot()
    if frozen_bad:
        report["status"] = "measurement_error_snapshot_drift"
        report["snapshot_verify_error"] = frozen_bad
        write_json(HERE / "report.json", report)
        print("SNAPSHOT VERIFY FAILED:", json.dumps(frozen_bad, indent=1))
        return 1
    build_mirror(WORK / "base")
    report["stage_hashes"] = {
        "structural": sha(SNAP / "artifacts/formulation/tools/check_class_schema.py"),
        "semantic": sha(SNAP / "artifacts/worker-06/spec_conformance_audit.py"),
        "manifest": sha(SNAP / "schemas/semantic_contract_tests/manifest.json"),
        "wcc_canonical": sha(SNAP / "schemas/af_wcc_vacuum.yaml"),
        "wcc_rev11_historical": sha(SNAP / "artifacts/worker-061/f1_independent_verdict/pinned/af_wcc_vacuum.yaml"),
    }
    report["churn_observation"] = CHURN_OBSERVATION

    # ---- step 2: baseline stage triplet on the three canonical schemas --------------
    baseline = {}
    for name in ("af_wcc_vacuum", "af_scc_c2_vacuum", "af_scc_c0_vacuum"):
        baseline[name] = triplet(WORK / "base", WORK / "base" / f"schemas/{name}.yaml", f"baseline_{name}")
    report["baseline"] = baseline

    wcc_base = baseline["af_wcc_vacuum"]
    base_ok = (wcc_base["structural"]["accepted"]
               and wcc_base["semantic_baseline"]["failed_rules"] == ["R03"]
               and wcc_base["semantic_hardened"]["failed_rules"] == ["R03"])
    others_ok = all(baseline[n]["structural"]["accepted"]
                    and baseline[n]["semantic_baseline"]["accepted"]
                    and baseline[n]["semantic_hardened"]["accepted"]
                    for n in ("af_scc_c2_vacuum", "af_scc_c0_vacuum"))

    # ---- step 3: root cause + historical regression ---------------------------------
    import yaml  # noqa: E402  (mirror-verified dependency, same as both stage tools)
    binder_table = {}
    for name in ("af_wcc_vacuum", "af_scc_c2_vacuum", "af_scc_c0_vacuum"):
        doc = yaml.safe_load((SNAP / f"schemas/{name}.yaml").read_text())
        q = doc["quantifiers"]
        binder_table[name] = [{"idx": i, "kind": e["kind"], "binder": str(e["binder"]),
                               "domain_id": e["domain_id"], "in_formal": str(e["binder"]) in q["formal"]}
                              for i, e in enumerate(q["ordered"])]
    spec = read_json(SNAP / "artifacts/formulation/rule_spec.json")
    r03_spec = next(r for r in spec["rules"] if r["id"] == "R03")
    auditor_src = (SNAP / "artifacts/worker-06/spec_conformance_audit.py").read_text()
    enforce_lines = [i + 1 for i, l in enumerate(auditor_src.splitlines())
                     if "absent from formal sentence" in l]

    hist = SNAP / "artifacts/worker-061/f1_independent_verdict/pinned/af_wcc_vacuum.yaml"
    hist_triplet = triplet(WORK / "base", hist, "historical_rev11_wcc")
    hist_passes = hist_triplet["semantic_baseline"]["accepted"] and hist_triplet["semantic_hardened"]["accepted"]

    # exact rev11->rev12 quantifier diff, from bytes, restricted to the quantifiers block
    def quant_block(p: Path):
        doc = yaml.safe_load(p.read_text())
        return doc["quantifiers"]
    q_old, q_new = quant_block(hist), quant_block(SNAP / "schemas/af_wcc_vacuum.yaml")
    changed_quant_keys = sorted(k for k in set(q_old) | set(q_new) if q_old.get(k) != q_new.get(k))

    report["root_cause"] = {
        "rule": "R03",
        "spec_text": r03_spec["require"],
        "spec_rule_id": "R03",
        "rule_spec_sha256": rule_spec_sha,
        "enforcement_lines_in_auditor": enforce_lines,
        "enforcement": "every declared ordered[].binder must be a verbatim substring of quantifiers.formal",
        "binder_table": binder_table,
        "wcc_failing_binder": "(q,t0)",
        "wcc_formal_tail": FORMAL_TAIL,
        "wcc_binder_line": BINDER_LINE,
        "c0_c2_convention": "both SCC classes render their tuple binder (M',g',iota) verbatim in formal; R03 passes",
        "classification": "literal_match_artifact_of_the_R03_implementation_on_a_corpus_rendering_inconsistency__rule_adjudication_required",
        "classification_note": (
            "Under a literal reading of R03 ('using those binders') the schema is non-conforming, because the "
            "declared token '(q,t0)' is not printed. Under a variable-wise reading the sentence does use the "
            "binder (q and t0 are both bound in the clause, D5 resolves and defines the pair domain), so the "
            "rejection is a tool-side literal-match false positive. Two independent prior adjudications read "
            "it variable-wise: worker-080 w080-sr-20260912T004243-blocker-f1r03 and worker-16 W16-R03-ADJ-01. "
            "This audit does not re-adjudicate; it measures the corpus inconsistency that makes the "
            "interpretation load-bearing and verifies both repair routes end-to-end."),
        "historical": {
            "path": "artifacts/worker-061/f1_independent_verdict/pinned/af_wcc_vacuum.yaml",
            "sha256": pins["artifacts/worker-061/f1_independent_verdict/pinned/af_wcc_vacuum.yaml"],
            "semantic_baseline": hist_triplet["semantic_baseline"]["verdict"],
            "semantic_hardened": hist_triplet["semantic_hardened"]["verdict"],
            "passed": hist_passes,
            "quantifier_keys_changed_rev11_to_rev12": changed_quant_keys,
            "rev11_binder_tail": [e for e in q_old["ordered"]][-1],
            "rev12_binder_tail": [e for e in q_new["ordered"]][-1],
        },
        "regression": ("R03 failure is introduced by the rev12 WCC revision: the rev11 binder was 'q' "
                       "and the formal sentence used it (R03 pass, both semantic stages); rev12 changed "
                       "the binder to the tuple '(q,t0)' and redefined D5 as pairs, but rendered the "
                       "formal tail in split notation 'q in I+ and t0 in [0,T)'.") if hist_passes else "undetermined",
    }

    # ---- step 4: repair candidates --------------------------------------------------
    candidates = {}
    for tag, (desc, new_tail) in CANDIDATES.items():
        m = WORK / f"cand_{tag}"
        build_mirror(m)
        p = m / "schemas/af_wcc_vacuum.yaml"
        raw = p.read_text()
        assert raw.count(FORMAL_TAIL) == 1
        p.write_text(raw.replace(FORMAL_TAIL, new_tail, 1))
        new_doc = yaml.safe_load(p.read_text())
        old_doc = yaml.safe_load((SNAP / "schemas/af_wcc_vacuum.yaml").read_text())
        only_formal_differs = all(
            old_doc[k] == new_doc[k] for k in old_doc if k != "quantifiers"
        ) and all(k == "formal" or old_doc["quantifiers"][k] == new_doc["quantifiers"][k]
                  for k in old_doc["quantifiers"])
        t = triplet(m, p, f"cand_{tag}")
        candidates[tag] = {"description": desc, "replacement_tail": new_tail,
                           "variant_sha256": sha(p), "only_quantifiers_formal_differs": only_formal_differs,
                           "stages": t,
                           "accepted_both_semantic": t["semantic_baseline"]["accepted"] and t["semantic_hardened"]["accepted"],
                           "structural_pass": t["structural"]["accepted"]}
        shutil.copy2(p, PATCH / f"wcc_candidate_{tag}.yaml")

    # E2: binder-list side repair (weakens the machine-readable binding; t0 unbound)
    m = WORK / "cand_E2"
    build_mirror(m)
    p = m / "schemas/af_wcc_vacuum.yaml"
    raw = p.read_text()
    assert raw.count(BINDER_LINE) == 1
    p.write_text(raw.replace(BINDER_LINE, BINDER_LINE.replace('"(q,t0)"', '"q"'), 1))
    t = triplet(m, p, "cand_E2")
    candidates["E2"] = {
        "description": "schema-side, binder-list repair: ordered[5].binder '(q,t0)' -> 'q' (formal untouched)",
        "variant_sha256": sha(p), "stages": t,
        "accepted_both_semantic": t["semantic_baseline"]["accepted"] and t["semantic_hardened"]["accepted"],
        "structural_pass": t["structural"]["accepted"],
        "caveat": "passes only by dropping the t0 component from the declared binder; D5 still defines pairs, so the machine-readable binding is weaker than E1a/E1b.",
    }
    shutil.copy2(p, PATCH / "wcc_candidate_E2.yaml")

    # E3: auditor-side relaxation simulation (requires a rule adjudication; measured cost)
    m = WORK / "cand_E3"
    build_mirror(m)
    ap = m / "artifacts/worker-06/spec_conformance_audit.py"
    src = ap.read_text()
    assert src.count(R03_ORIG) == 1
    ap.write_text(src.replace(R03_ORIG, R03_RELAXED, 1))
    t = triplet(m, m / "schemas/af_wcc_vacuum.yaml", "cand_E3")
    # measured cost on the mutant corpus: catch counts must not drop
    e3_mutants_rejected = 0
    manifest = read_json(m / "schemas/semantic_contract_tests/manifest.json")
    mutant_dirs = [e for e in manifest["fixtures"]]
    for e in mutant_dirs:
        f = m / "schemas/semantic_contract_tests" / e["fixture"]
        s = semantic(m, f, RAW / f"E3_{e['test_id']}.json", False)
        if s["rejected"]:
            e3_mutants_rejected += 1
    base_mutants_rejected = 0
    for e in mutant_dirs:
        f = WORK / "base/schemas/semantic_contract_tests" / e["fixture"]
        s = semantic(WORK / "base", f, RAW / f"BASE_{e['test_id']}.json", False)
        if s["rejected"]:
            base_mutants_rejected += 1
    candidates["E3"] = {
        "description": "auditor-side relaxation simulation: accept a tuple binder if all comma-separated components appear in formal",
        "auditor_variant_sha256": sha(ap), "stages": t,
        "accepted_both_semantic": t["semantic_baseline"]["accepted"] and t["semantic_hardened"]["accepted"],
        "mutant_semantic_baseline_rejected_patched": e3_mutants_rejected,
        "mutant_semantic_baseline_rejected_canonical_tool": base_mutants_rejected,
        "mutant_total": len(mutant_dirs),
        "caveat": "a tool change, not a schema repair: needs rule adjudication by the spec owner (FORM-RULE-SPEC R03 says the formal sentence must use 'those binders').",
    }
    shutil.copy2(ap, PATCH / "spec_conformance_audit_relaxed.py")
    report["candidates"] = candidates

    # ---- step 5: full-suite discriminating experiment -------------------------------
    # S0 unmodified manifest -> integrity failure
    s0 = run_suite(WORK / "base", "S0_unmodified_manifest")
    # S1 rebased controls + refreshed pins + canonical (R03-failing) WCC -> validity false
    m1 = WORK / "S1"
    build_mirror(m1)
    rebase = rebase_controls(m1)
    changed1 = refresh_pins(m1)
    s1 = run_suite(m1, "S1_rebased_canonical_wcc")
    # S2 same but WCC = E1a (spec-faithful notation repair) -> expect exit 0 / valid true
    m2 = WORK / "S2"
    build_mirror(m2)
    rebase2 = rebase_controls(m2)
    p2 = m2 / "schemas/af_wcc_vacuum.yaml"
    p2.write_text(p2.read_text().replace(FORMAL_TAIL, CANDIDATES["E1a"][1], 1))
    changed2 = refresh_pins(m2)
    s2 = run_suite(m2, "S2_rebased_E1a_wcc")
    # S3 negative control: E1a WCC + rebased control bytes but pre-rebase control pins
    # (canonical pins refreshed) -> integrity failure
    m3 = WORK / "S3"
    build_mirror(m3)
    p3 = m3 / "schemas/af_wcc_vacuum.yaml"
    p3.write_text(p3.read_text().replace(FORMAL_TAIL, CANDIDATES["E1a"][1], 1))
    rebase_controls(m3)
    refresh_pins(m3, groups=("conforming_canonical_controls",))
    s3 = run_suite(m3, "S3_E1a_wcc_stale_control_pins")
    # S4 resolution route A (tool amendment, canonical bytes untouched): rebased controls +
    # refreshed pins + canonical WCC + variable-wise R03 in the worker-local auditor copy
    m4 = WORK / "S4"
    build_mirror(m4)
    rebase_controls(m4)
    ap4 = m4 / "artifacts/worker-06/spec_conformance_audit.py"
    src4 = ap4.read_text()
    assert src4.count(R03_ORIG) == 1
    ap4.write_text(src4.replace(R03_ORIG, R03_RELAXED, 1))
    refresh_pins(m4)
    s4 = run_suite(m4, "S4_tool_amended_canonical_wcc")

    report["full_suite"] = {
        "S0": s0, "S1": s1, "S2": s2, "S3": s3, "S4": s4,
        "control_rebase": rebase,
        "control_rebase_expected_new_hashes": {
            "control_comment_only_composite.yaml": "ce8b15e22722faf18693ef4bd77be9663e245e088e03179ad347bfa14dc8b99f",
            "control_conforming_base.yaml": "253c28e03c535e9d61c69a68a185deca11fa7ed4c4d544a1ce93c5ba1d09f271",
            "control_quoted_forbidden_phrase.yaml": "2399f5752af18fcff02c7c36888c765333a6011b3dbc78abd72df988ffb06364",
        },
        "pins_refreshed_S1": changed1, "pins_refreshed_S2": changed2,
    }

    # ---- step 6: expectations, claims, verdict --------------------------------------
    e1a = candidates["E1a"]["accepted_both_semantic"] and candidates["E1a"]["structural_pass"]
    e1b = candidates["E1b"]["accepted_both_semantic"] and candidates["E1b"]["structural_pass"]
    e2 = candidates["E2"]["accepted_both_semantic"]
    e3 = candidates["E3"]["accepted_both_semantic"]
    expectations = {
        "baseline_wcc_rejected_R03_only_both_semantic": bool(base_ok),
        "baseline_c0_c2_accepted_all_stages": bool(others_ok),
        "rev11_wcc_accepted_regression_confirmed": bool(hist_passes and {"formal", "ordered"} <= set(changed_quant_keys)),
        "control_rebase_matches_prior_published_hashes": bool(all(
            info["rebased_sha256"] == report["full_suite"]["control_rebase_expected_new_hashes"][name]
            for name, info in rebase.items())),
        "E1a_fixes_wcc_all_stages": bool(e1a),
        "E1b_fixes_wcc_all_stages": bool(e1b),
        "E1c_fixes_wcc_all_stages": bool(candidates["E1c"]["accepted_both_semantic"] and candidates["E1c"]["structural_pass"]),
        "E2_binder_list_fix_also_passes": bool(e2),
        "E3_auditor_relaxation_passes_without_mutant_loss": bool(e3 and candidates["E3"]["mutant_semantic_baseline_rejected_patched"] >= candidates["E3"]["mutant_semantic_baseline_rejected_canonical_tool"]),
        "S0_exit2_integrity_failure": s0["exit"] == 2,
        "S1_exit3_invalid_wcc_is_sole_conforming_rejection": bool(
            s1["exit"] == 3 and s1["valid_for_calibration"] is False
            and set(s1["conforming_rejections"]) == {"SCT-K03"}),
        "S2_exit0_valid_true_sole_blocker_was_R03": bool(s2["exit"] == 0 and s2["valid_for_calibration"] is True),
        "S3_exit2_stale_control_pins_still_caught": s3["exit"] == 2,
        "S4_exit0_valid_true_with_canonical_bytes_and_amended_tool": bool(
            s4["exit"] == 0 and s4["valid_for_calibration"] is True),
        "S4_keeps_canonical_wcc_sha_in_results": str(
            s4["fixture_hashes"].get("SCT-K03", "")).startswith("d9cebb9404b2"),
        "mutant_counts_unchanged_32_11_32_in_S1_and_S2": bool(
            (s1["mutants_structural"], s1["mutants_baseline"], s1["mutants_hardened"]) == (32, 11, 32)
            and (s2["mutants_structural"], s2["mutants_baseline"], s2["mutants_hardened"]) == (32, 11, 32)),
    }
    report["expectations"] = expectations
    report["falsified"] = [k for k, v in expectations.items() if not v]

    # ---- step 6b: end-of-run canonical drift (report stays bound to the frozen snapshot) ----
    report["canonical_drift_at_end"] = {
        rel: {"at_run_start": pins.get(rel), "at_run_end": sha(REPO / rel), "pinned_expected": want}
        for rel, want in PINS.items() if sha(REPO / rel) != pins.get(rel)}
    report["canonical_drift_at_end_note"] = (
        "The audit binds to the one-time snapshot under work/_frozen taken at run start; entries here "
        "mean the live canonical path moved after the snapshot and do not affect the measurements. "
        "Observed churn while this task was built: live canonical WCC at cce9c60146d6 (FROZEN rev28, "
        "frozen_at 00:35:08) -> bf0c28fa673e -> d9cebb9404b2 (FROZEN rev29, frozen_at 00:55:02); C0/C2 "
        "re-pinned to b2ab6acb2bbe / e9a27996dfd3; FROZEN.json rewritten again at 00:57:26 (still rev29). "
        "Any verdict bound to the rev28 hashes is void.")

    report["claims"] = [
        {
            "claim_id": "W064-R03-CAUSE-01-C1",
            "class_id": "AF-WCC-VAC-GEN",
            "conclusion_type": "numerical_evidence",
            "statement": ("At the pinned rev29 bytes (WCC d9cebb9404b2, C2 e9a27996dfd3, C0 b2ab6acb2bbe; "
                          "auditor c79d8ab8440a; structural 000e09e46b2f), canonical WCC is rejected by the "
                          "adopted semantic auditor on exactly one rule, R03, with detail \"binder '(q,t0)' "
                          "absent from formal sentence\", because ordered[5] declares the tuple binder "
                          "'(q,t0)' while quantifiers.formal renders the same quantifier variable-wise as "
                          "'not exists q in I+ and t0 in [0,T) with ...'. All other 15 rules pass; C0 and C2 "
                          "pass all three stages. Independently reproduces worker-080's Probe B and worker-16's "
                          "W16-R03-ADJ-01 blocker. Measured addition: the corpus is not uniformly "
                          "self-presenting -- C0/C2 print their tuple binders literally, rev13 WCC does not -- "
                          "so the rejection is a literal-match artifact of the R03 implementation whose "
                          "resolution (amend the tool vs edit the schema) is a spec-owner adjudication, not a "
                          "mathematical defect."),
            "artifact_refs": ["artifacts/worker-064/r03_cause/report.json"],
            "falsifier": ("Re-run w064_r03_cause_audit.py: WCC accepted by both semantic stages at "
                          "d9cebb9404b2, or an additional failing rule, or '(q,t0)' present in the formal "
                          "sentence, or q/t0 not both bound in the clause, or D5 unresolved, falsifies C1."),
        },
        {
            "claim_id": "W064-R03-CAUSE-01-C2",
            "class_id": "AF-WCC-VAC-GEN",
            "conclusion_type": "numerical_evidence",
            "statement": ("The R03 failure is a rev12 regression that survives the rev13 re-pin, not a long-standing condition: the pinned "
                          "rev11 WCC bytes 9a8bd4c96800 (path artifacts/worker-061/f1_independent_verdict/"
                          "pinned/af_wcc_vacuum.yaml, same auditor hash) are accepted by both semantic stages "
                          "with R03 pass, and the rev11->rev12 quantifier diff changes formal and ordered "
                          "(binder 'q' -> '(q,t0)', whole-curve -> tail predicate) together with the aligned "
                          "domains and negation entries. The rev12 mathematical repair is correct; only its "
                          "formal-sentence rendering fails to use the newly declared tuple binder."),
            "artifact_refs": ["artifacts/worker-064/r03_cause/report.json"],
            "falsifier": ("A rev11 WCC record showing R03 fail or rejection, or a rev12 diff that does not "
                          "touch quantifiers.formal or quantifiers.ordered, falsifies C2."),
        },
        {
            "claim_id": "W064-R03-CAUSE-01-C3",
            "class_id": "AF-WCC-VAC-GEN",
            "conclusion_type": "numerical_evidence",
            "statement": ("A one-clause, semantics-preserving text repair of the formal sentence that uses "
                          "the declared tuple binder verbatim (E1a: 'not exists (q,t0) in D5 with ...'; "
                          "equivalently E1b with an explicit I+ x [0,T) domain) makes canonical WCC pass "
                          "structural + semantic baseline + semantic hardened with no other YAML key "
                          "changed. Repairing the ordered binder list instead (E2: '(q,t0)' -> 'q') also "
                          "passes but drops t0 from the machine-readable binding. Relaxing the auditor (E3) "
                          "passes WCC and loses no mutant catches, but is a tool change requiring rule "
                          "adjudication, not a schema repair."),
            "artifact_refs": ["artifacts/worker-064/r03_cause/report.json",
                              "artifacts/worker-064/r03_cause/patch_candidates/wcc_candidate_E1a.yaml"],
            "falsifier": ("A re-run in which E1a/E1b changes any YAML key other than quantifiers.formal, or "
                          "is rejected by any stage, or E2 fails, or E3 loses a mutant catch, falsifies C3."),
        },
        {
            "claim_id": "W064-R03-CAUSE-01-C4",
            "class_id": "AF-WCC-VAC-GEN",
            "conclusion_type": "numerical_evidence",
            "statement": ("Discriminating full-suite experiment at the pinned bytes: with the three frozen "
                          "controls rebased by the two previously reported mechanical edits and manifest pins "
                          "refreshed, the unmodified canonical WCC yields suite exit 3, "
                          "valid_for_calibration=false, with SCT-K03 (WCC) the only non-accepted control and "
                          "mutants 32/11/32; applying only the E1a formal-sentence repair on top yields exit "
                          "0, valid_for_calibration=true, 6/6 controls accepted and mutants unchanged "
                          "32/11/32. Therefore, on that basis, R03 was the sole residual blocker to suite "
                          "validity. The same is reached without touching canonical bytes by the "
                          "variable-wise R03 tool amendment (S4: exit 0, valid true, WCC still "
                          "d9cebb9404b2 in the results), so both routes recorded here turn the suite "
                          "valid. The pre-rebase control pins are still caught (S3 exit 2), so the "
                          "integrity check is not weakened."),
            "artifact_refs": ["artifacts/worker-064/r03_cause/report.json",
                              "artifacts/worker-064/r03_cause/raw/S2_rebased_E1a_wcc.observed_verdicts.json"],
            "falsifier": ("A rerun in which S1 shows any conforming rejection other than SCT-K03, or S2 "
                          "returns non-zero/false validity, or S3 does not exit 2, or S4 does not exit 0 "
                          "with the canonical WCC hash, falsifies C4."),
        },
    ]

    ok = all(expectations.values())
    report["verdict"] = ("INDEPENDENT_REPLICATION__R03_ROOT_CAUSE__REV12_REGRESSION__SOLE_RESIDUAL_BLOCKER__"
                         "SINGLE_CLAUSE_REPAIR_VERIFIED__RULES_ADJUDICATION_OPEN") if ok else "FALSIFIED"
    report["status"] = "findings_reproduced" if ok else "falsified"
    report["falsified_count"] = len(report["falsified"])
    report["finished_at"] = now()
    write_json(HERE / "report.json", report)

    print(json.dumps({"task_id": report["task_id"], "status": report["status"],
                      "verdict": report["verdict"], "falsified": report["falsified"],
                      "S0": s0["exit"], "S1": s1["exit"], "S2": s2["exit"], "S3": s3["exit"], "S4": s4["exit"],
                      "E1a": e1a, "E1b": e1b, "E2": e2, "E3": e3,
                      "report_sha256": sha(HERE / "report.json")}, indent=1))
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
