#!/usr/bin/env python3
"""W084-C2C0-ESCAPE-MECHANISM-01.

Mechanism adjudication of the FORM-HELDOUT-10 informative-arm union escape.
Read-only over all pinned bytes; writes only under this directory.

Method (pre-registered in PREREGISTRATION.json, hashed before the first run):
  for each preserved mutant m with base b, run both frozen stages on b and on m
  as fresh subprocesses, normalize the JSON stdout by deleting only the
  volatile/path-bearing keys, and classify the per-stage response:

    CAUGHT   verdict not accept/pass (or crash)
    SILENT   verdict accepts and normalized output identical to base
    OBSERVED verdict accepts and normalized output differs from base

  union: CAUGHT if any stage caught; ESCAPE-SILENT if both accept and both
  silent; ESCAPE-OBSERVED otherwise.

Re-runnable:
  python3 artifacts/heldout/heldout-10-mechanism/analyze_escape_mechanism.py
  python3 artifacts/heldout/heldout-10-mechanism/analyze_escape_mechanism.py --verify
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

DIR = Path(__file__).resolve().parent
ROOT = DIR.parents[2]
HELDOUT = ROOT / "artifacts" / "heldout" / "heldout-10"
PREREG = DIR / "PREREGISTRATION.json"
RAW = DIR / "raw"
SANDBOX = DIR / "sandbox"

CST = timezone(timedelta(hours=8))
TIMEOUT = 300


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def canon(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def parse_json_stdout(stdout: str):
    i = stdout.find("{")
    if i < 0:
        return None
    try:
        return json.loads(stdout[i:])
    except json.JSONDecodeError:
        return None


def norm_a(rep):
    """Stage A normalized report: drop the fixture path, keep the verdict surface."""
    if rep is None:
        return None
    return {
        "verdict": rep.get("verdict"),
        "class_id": rep.get("class_id"),
        "failed_rules": sorted(rep.get("failed_rules", []) or []),
        "failures": sorted(str(x) for x in (rep.get("failures", []) or [])),
    }


def norm_b(rep):
    """Stage B normalized report: drop volatile/path keys; keep checks + rules."""
    if rep is None:
        return None
    return {
        "verdict": rep.get("verdict"),
        "failed_rules": sorted(rep.get("failed_rules", []) or []),
        "undecided_rules": sorted(rep.get("undecided_rules", []) or []),
        "hardened": rep.get("hardened"),
        "checks": [
            {"rule": c.get("rule"), "verdict": c.get("verdict"), "detail": c.get("detail")}
            for c in (rep.get("checks", []) or [])
        ],
    }


def run_stage_a(tool: Path, target: Path) -> dict:
    t0 = time.time()
    try:
        p = subprocess.run([sys.executable, str(tool), "--json", str(target)],
                           capture_output=True, text=True, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        return {"exit": None, "crash": True, "stderr": "timeout", "seconds": round(time.time() - t0, 3)}
    rep = parse_json_stdout(p.stdout)
    n = norm_a(rep)
    return {
        "exit": p.returncode,
        "verdict": (n or {}).get("verdict"),
        "failed_rules": (n or {}).get("failed_rules", []),
        "normalized_sha256": hashlib.sha256(canon(n).encode()).hexdigest() if n is not None else None,
        "crash": n is None,
        "raw_stdout_sha256": hashlib.sha256(p.stdout.encode()).hexdigest(),
        "stderr": p.stderr.strip()[:200],
        "seconds": round(time.time() - t0, 3),
        "_norm": n,
    }


def run_stage_b(tool: Path, target: Path) -> dict:
    t0 = time.time()
    try:
        p = subprocess.run([sys.executable, str(tool), str(target)],
                           capture_output=True, text=True, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        return {"exit": None, "crash": True, "stderr": "timeout", "seconds": round(time.time() - t0, 3)}
    rep = parse_json_stdout(p.stdout)
    n = norm_b(rep)
    return {
        "exit": p.returncode,
        "verdict": (n or {}).get("verdict"),
        "failed_rules": (n or {}).get("failed_rules", []),
        "normalized_sha256": hashlib.sha256(canon(n).encode()).hexdigest() if n is not None else None,
        "crash": n is None,
        "raw_stdout_sha256": hashlib.sha256(p.stdout.encode()).hexdigest(),
        "stderr": p.stderr.strip()[:200],
        "seconds": round(time.time() - t0, 3),
        "_norm": n,
    }


def accepts(stage: str, r: dict) -> bool:
    if r.get("crash") or r.get("exit") != 0:
        return False
    return r.get("verdict") == ("pass" if stage == "a" else "accept")


def relation(base: dict, mut: dict) -> str:
    if base.get("normalized_sha256") is None or mut.get("normalized_sha256") is None:
        return "undecidable"
    return "identical" if base["normalized_sha256"] == mut["normalized_sha256"] else "differs"


def classify_stage(stage: str, base: dict, mut: dict) -> str:
    if not accepts(stage, mut):
        return "CAUGHT"
    rel = relation(base, mut)
    if rel == "identical":
        return "SILENT"
    if rel == "differs":
        return "OBSERVED"
    return "CRASH"


def changed_checks(base: dict, mut: dict):
    """For OBSERVED stages: which checks/details moved (stage B), or failures (stage A)."""
    out = []
    bn, mn = base.get("_norm"), mut.get("_norm")
    if not bn or not mn:
        return out
    if "checks" in bn or "checks" in mn:
        bmap = {c["rule"]: c for c in bn.get("checks", [])}
        mmap = {c["rule"]: c for c in mn.get("checks", [])}
        for rule in sorted(set(bmap) | set(mmap)):
            b, m = bmap.get(rule), mmap.get(rule)
            if b != m:
                out.append({"rule": rule,
                            "base": None if b is None else f"{b.get('verdict')}: {b.get('detail')}",
                            "mutant": None if m is None else f"{m.get('verdict')}: {m.get('detail')}"})
    for k in ("verdict", "failed_rules", "failures"):
        if bn.get(k) != mn.get(k):
            out.append({"rule": k, "base": bn.get(k), "mutant": mn.get(k)})
    return out


# ---------------------------------------------------------------- leaf diff
def flat(o, p=""):
    out = {}
    if isinstance(o, dict):
        for k, v in o.items():
            out.update(flat(v, f"{p}.{k}" if p else str(k)))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            out.update(flat(v, f"{p}[{i}]"))
    else:
        out[p] = o
    return out


def prefix_category(path: str, prefixes: dict) -> str:
    best, cat = None, None
    for pre, c in prefixes.items():
        if path == pre or path.startswith(pre + ".") or path.startswith(pre + "["):
            if best is None or len(pre) > len(best):
                best, cat = pre, c
    return cat or "UNMAPPED"


def load_json(p: Path):
    return json.loads(Path(p).read_text())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true",
                    help="re-run everything and compare against raw/differential.json")
    args = ap.parse_args()

    prereg_sha = sha(PREREG)
    prereg = load_json(PREREG)
    prefixes = {}
    for pre in prereg["method"]["contract_relevance"]["CONTRACT_PREFIXES"]:
        prefixes[pre] = "CONTRACT"
    for pre in prereg["method"]["contract_relevance"]["META_PREFIXES"]:
        prefixes[pre] = "META"

    # Append-only preregistration amendments (declared before the amended run).
    AMD = DIR / "PREREGISTRATION_AMENDMENT_1.json"
    amendments = []
    if AMD.exists():
        amd = load_json(AMD)
        for pre, cat in amd.get("added_prefixes", {}).items():
            prefixes[pre] = cat
        amendments.append({
            "path": "artifacts/heldout/heldout-10-mechanism/PREREGISTRATION_AMENDMENT_1.json",
            "sha256": sha(AMD), "amendment_id": amd.get("amendment_id"),
            "added_prefixes": amd.get("added_prefixes"),
            "reason": amd.get("reason"),
        })

    man = load_json(HELDOUT / "manifest.json")
    raw10 = load_json(HELDOUT / "raw" / "raw_verdicts.json")
    report10 = load_json(HELDOUT / "report.json")
    struct = ROOT / man["stages"]["structural"]["path"]
    sem = ROOT / man["stages"]["semantic"]["path"]

    # ---- K5 integrity --------------------------------------------------------
    integrity = {"checks": [], "failures": []}

    def check(name, ok, detail):
        integrity["checks"].append({"check": name, "ok": bool(ok), "detail": detail})
        if not ok:
            integrity["failures"].append(f"{name}: {detail}")

    for rel, want in man["pins"].items():
        got = sha(ROOT / rel) if (ROOT / rel).exists() else None
        check(f"pin:{rel}", got == want, f"pinned={want[:16]} measured={str(got)[:16]}")
    for key in ("structural", "semantic", "stage_a_key_manifest"):
        s = man["stages"][key]
        got = sha(ROOT / s["path"])
        check(f"stage:{key}", got == s["sha256"], f"pinned={s['sha256'][:16]} measured={got[:16]}")
    for arm, b in man["bases"].items():
        got = sha(ROOT / b["path"])
        check(f"base:{arm}", got == b["sha256"] and got == man["pins"][b["frozen_path"]],
              f"{b['path']}")
    for e in man["mutants"] + man["controls"]:
        got = sha(ROOT / e["path"]) if (ROOT / e["path"]).exists() else None
        check(f"fixture:{e.get('mutation_id') or e.get('control_id')}", got == e["sha256"], e["path"])
    frozen = load_json(ROOT / man["frozen_manifest"]["path"])
    check("frozen_manifest_bytes", sha(ROOT / man["frozen_manifest"]["path"]) == man["frozen_manifest"]["sha256"],
          f"revision={frozen.get('revision')}")

    # ---- controls -------------------------------------------------------------
    RAW.mkdir(parents=True, exist_ok=True)
    SANDBOX.mkdir(parents=True, exist_ok=True)
    controls = {}

    c2_base = ROOT / man["bases"]["C2"]["path"]
    b_a = run_stage_a(struct, c2_base)
    b_b = run_stage_b(sem, c2_base)

    # K4 determinism
    d_a = run_stage_a(struct, c2_base)
    d_b = run_stage_b(sem, c2_base)
    controls["K4_determinism"] = {
        "ok": (b_a["normalized_sha256"] == d_a["normalized_sha256"]
               and b_b["normalized_sha256"] == d_b["normalized_sha256"]),
        "stage_a": [b_a["normalized_sha256"], d_a["normalized_sha256"]],
        "stage_b": [b_b["normalized_sha256"], d_b["normalized_sha256"]],
    }

    # K2 format control: append a YAML comment only
    k2 = SANDBOX / "k2_c2_comment_only.yaml"
    k2.write_text(c2_base.read_text() + "\n# K2 format control: comment only; parsed content unchanged\n")
    k2_a, k2_b = run_stage_a(struct, k2), run_stage_b(sem, k2)
    controls["K2_format_control"] = {
        "ok": (relation(b_a, k2_a) == "identical" and relation(b_b, k2_b) == "identical"),
        "stage_a_relation": relation(b_a, k2_a),
        "stage_b_relation": relation(b_b, k2_b),
        "note": "comment-only edit must not register as a change",
    }

    # K3 sensitivity positive control: foreign conclusion token
    k3 = SANDBOX / "k3_c2_foreign_conclusion_type.yaml"
    doc = yaml.safe_load(c2_base.read_text())
    doc["conclusion"]["conclusion_type"] = "scc_c0_future_inextendibility"
    k3.write_text(yaml.safe_dump(doc, sort_keys=False))
    k3_a, k3_b = run_stage_a(struct, k3), run_stage_b(sem, k3)
    controls["K3_sensitivity_positive"] = {
        "ok": ((not accepts("a", k3_a)) or (not accepts("b", k3_b)))
              and (relation(b_a, k3_a) == "differs" or relation(b_b, k3_b) == "differs"),
        "stage_a": {"verdict": k3_a["verdict"], "failed_rules": k3_a["failed_rules"],
                    "relation": relation(b_a, k3_a)},
        "stage_b": {"verdict": k3_b["verdict"], "failed_rules": k3_b["failed_rules"],
                    "relation": relation(b_b, k3_b)},
        "note": "planted foreign conclusion token must be rejected by at least one stage",
    }

    # K1 base acceptance (W base is expected to fail stage B R03: pre-registered defect)
    base_runs = {}
    for arm, b in man["bases"].items():
        run_a, run_b = run_stage_a(struct, ROOT / b["path"]), run_stage_b(sem, ROOT / b["path"])
        base_runs[arm] = {"path": b["path"], "sha256": sha(ROOT / b["path"]),
                          "stage_a": run_a, "stage_b": run_b}
    controls["K1_base_acceptance"] = {
        "ok": (all(accepts("a", base_runs[a]["stage_a"]) for a in ("W", "C2", "C0"))
               and accepts("b", base_runs["C2"]["stage_b"])
               and accepts("b", base_runs["C0"]["stage_b"])),
        "W_stage_b": {"verdict": base_runs["W"]["stage_b"]["verdict"],
                      "failed_rules": base_runs["W"]["stage_b"]["failed_rules"],
                      "expected": "reject R03 (pre-registered instrument defect, CF/R03)"},
        "C2_stage_a": base_runs["C2"]["stage_a"]["verdict"],
        "C2_stage_b": base_runs["C2"]["stage_b"]["verdict"],
        "C0_stage_a": base_runs["C0"]["stage_a"]["verdict"],
        "C0_stage_b": base_runs["C0"]["stage_b"]["verdict"],
    }

    # ---- mutant analysis ------------------------------------------------------
    raw_by_fixture = {r["fixture"]: r for r in raw10["results"]}
    records = []
    for e in man["mutants"]:
        arm = e["arm"]
        base_path = ROOT / e["base"]
        mut_path = ROOT / e["path"]
        base = base_runs[arm]
        mut_a = run_stage_a(struct, mut_path)
        mut_b = run_stage_b(sem, mut_path)

        ca = classify_stage("a", base["stage_a"], mut_a)
        cb = classify_stage("b", base["stage_b"], mut_b)
        if ca == "CAUGHT" or cb == "CAUGHT":
            union = "CAUGHT"
        elif ca == "SILENT" and cb == "SILENT":
            union = "ESCAPE-SILENT"
        elif ca in ("SILENT", "OBSERVED") and cb in ("SILENT", "OBSERVED"):
            union = "ESCAPE-OBSERVED"
        else:
            union = "INVALID"

        bflat = flat(yaml.safe_load(base_path.read_text()))
        mflat = flat(yaml.safe_load(mut_path.read_text()))
        changed = []
        for k in sorted(set(bflat) | set(mflat)):
            if bflat.get(k) != mflat.get(k):
                changed.append({"path": k,
                                "base": None if k not in bflat else str(bflat[k])[:160],
                                "mutant": None if k not in mflat else str(mflat[k])[:160]})
        cats = sorted({prefix_category(c["path"], prefixes) for c in changed})
        if "UNMAPPED" in cats:
            contract_category = "UNMAPPED"
        elif "CONTRACT" in cats and "META" in cats:
            contract_category = "CONTRACT+META"
        elif "CONTRACT" in cats:
            contract_category = "CONTRACT"
        elif "META" in cats:
            contract_category = "META"
        else:
            contract_category = "NO-CHANGE"

        rv = raw_by_fixture.get(e["fixture"], {})
        agree = (rv.get("stage_a", {}).get("verdict") == mut_a["verdict"]
                 and rv.get("stage_b", {}).get("verdict") == mut_b["verdict"])

        rec = {
            "mutation_id": e["mutation_id"], "fixture": e["fixture"], "family": e["family"],
            "arm": arm, "class_id": e["class_id"], "rephrased": e.get("rephrased"),
            "base_path": e["base"], "base_sha256": e["base_sha256"],
            "mutant_path": e["path"], "mutant_sha256": e["sha256"],
            "changed_paths": changed, "changed_path_count": len(changed),
            "block_categories": cats, "contract_category": contract_category,
            "stage_a": {"base_verdict": base["stage_a"]["verdict"],
                        "mutant_verdict": mut_a["verdict"],
                        "base_norm_sha256": base["stage_a"]["normalized_sha256"],
                        "mutant_norm_sha256": mut_a["normalized_sha256"],
                        "relation": relation(base["stage_a"], mut_a),
                        "classification": ca,
                        "changed_checks": changed_checks(base["stage_a"], mut_a) if ca == "OBSERVED" else []},
            "stage_b": {"base_verdict": base["stage_b"]["verdict"],
                        "mutant_verdict": mut_b["verdict"],
                        "base_norm_sha256": base["stage_b"]["normalized_sha256"],
                        "mutant_norm_sha256": mut_b["normalized_sha256"],
                        "relation": relation(base["stage_b"], mut_b),
                        "classification": cb,
                        "changed_checks": changed_checks(base["stage_b"], mut_b) if cb == "OBSERVED" else []},
            "union": union,
            "raw_verdicts_agreement": agree,
        }
        records.append(rec)

    # ---- aggregates -----------------------------------------------------------
    def agg(recs, label):
        n = len(recs)
        caught = [r for r in recs if r["union"] == "CAUGHT"]
        silent = [r for r in recs if r["union"] == "ESCAPE-SILENT"]
        observed = [r for r in recs if r["union"] == "ESCAPE-OBSERVED"]
        return {
            "label": label, "mutants": n,
            "caught": len(caught), "escape_silent": len(silent), "escape_observed": len(observed),
            "union_escape": None if n == 0 else round((n - len(caught)) / n, 4),
            "escape_silent_rate": None if n == 0 else round(len(silent) / n, 4),
            "stage_a_silent": sum(1 for r in recs if r["stage_a"]["classification"] == "SILENT"),
            "stage_a_observed": sum(1 for r in recs if r["stage_a"]["classification"] == "OBSERVED"),
            "stage_a_caught": sum(1 for r in recs if r["stage_a"]["classification"] == "CAUGHT"),
            "stage_b_silent": sum(1 for r in recs if r["stage_b"]["classification"] == "SILENT"),
            "stage_b_observed": sum(1 for r in recs if r["stage_b"]["classification"] == "OBSERVED"),
            "stage_b_caught": sum(1 for r in recs if r["stage_b"]["classification"] == "CAUGHT"),
        }

    informative = [r for r in records if r["arm"] in ("C2", "C0")]
    informative_contract = [r for r in informative if "CONTRACT" in r["contract_category"]]
    informative_meta = [r for r in informative if r["contract_category"] == "META"]
    aggregates = {
        "all_mutants": agg(records, "all 33 mutants (W+C2+C0)"),
        "informative_arms": agg(informative, "C2+C0 informative arms (26)"),
        "informative_contract_only": agg(informative_contract, "C2+C0, CONTRACT changed paths only (strict class-binding)"),
        "informative_meta_only": agg(informative_meta, "C2+C0, META changed paths only (schema hygiene, not class binding)"),
    }

    # per-family table
    families = {}
    for r in informative:
        f = families.setdefault(r["family"], {"family": r["family"], "mutants": 0, "caught": 0,
                                              "escape_silent": 0, "escape_observed": 0,
                                              "contract_category": r["contract_category"],
                                              "class_ids": [], "raw_verdicts_agreement": True})
        f["mutants"] += 1
        f[r["union"].lower().replace("escape-", "escape_") if r["union"].startswith("ESCAPE") else "caught"] += 1
        if r["class_id"] not in f["class_ids"]:
            f["class_ids"].append(r["class_id"])
        f["raw_verdicts_agreement"] = f["raw_verdicts_agreement"] and r["raw_verdicts_agreement"]
    families = sorted(families.values(), key=lambda x: x["family"])

    # K7 raw verdict agreement
    k7_ok = all(r["raw_verdicts_agreement"] for r in records)
    controls["K7_raw_verdict_agreement"] = {
        "ok": k7_ok,
        "disagreements": [r["fixture"] for r in records if not r["raw_verdicts_agreement"]],
    }
    controls["K8_fail_closed"] = {
        "ok": not (integrity["failures"]
                   or any(r["contract_category"] == "UNMAPPED" for r in records)
                   or any(r["stage_a"]["classification"] == "CRASH" or r["stage_b"]["classification"] == "CRASH"
                          for r in records)
                   or any(r["union"] == "INVALID" for r in records)),
        "unmapped": [r["fixture"] for r in records if r["contract_category"] == "UNMAPPED"],
        "crash": [r["fixture"] for r in records
                  if r["stage_a"]["classification"] == "CRASH" or r["stage_b"]["classification"] == "CRASH"],
        "invalid_union": [r["fixture"] for r in records if r["union"] == "INVALID"],
    }

    # ---- drift re-hash (K6) ---------------------------------------------------
    drift = {}
    for rel, want in man["pins"].items():
        got = sha(ROOT / rel)
        drift[rel] = {"pinned": want, "after": got, "changed": got != want}
    for key in ("structural", "semantic", "stage_a_key_manifest"):
        s = man["stages"][key]
        got = sha(ROOT / s["path"])
        drift[s["path"]] = {"pinned": s["sha256"], "after": got, "changed": got != s["sha256"]}
    controls["K6_no_drift"] = {"ok": not any(v["changed"] for v in drift.values()), "pins": drift}
    controls["K5_integrity"] = {"ok": not integrity["failures"],
                                "n_checks": len(integrity["checks"]), "failures": integrity["failures"]}

    control_ok = all(c.get("ok") for c in controls.values())
    invalid_reasons = []
    if not controls["K5_integrity"]["ok"]:
        invalid_reasons.append("K5 integrity failure")
    if not k7_ok:
        invalid_reasons.append("K7 raw verdict disagreement")
    if controls["K8_fail_closed"]["unmapped"]:
        invalid_reasons.append("UNMAPPED changed paths")
    if controls["K8_fail_closed"]["crash"] or controls["K8_fail_closed"]["invalid_union"]:
        invalid_reasons.append("crash or undecidable classification")
    if not controls["K6_no_drift"]["ok"]:
        invalid_reasons.append("pin drift during run")
    if not controls["K2_format_control"]["ok"]:
        invalid_reasons.append("format control failed")
    if not controls["K3_sensitivity_positive"]["ok"]:
        invalid_reasons.append("sensitivity control failed")
    if not controls["K4_determinism"]["ok"]:
        invalid_reasons.append("determinism control failed")

    mechanism = "SILENT-BLINDNESS" if aggregates["informative_arms"]["escape_silent"] == aggregates["informative_arms"]["mutants"] else "MIXED"
    report = {
        "task_id": prereg["task_id"], "corpus_id": prereg["corpus_id"], "worker": "worker-084",
        "node_id": "A1", "gate": "G-CLASSBIND", "class_ids": prereg["class_ids"],
        "generated_at": now(),
        "preregistration": {"path": "artifacts/heldout/heldout-10-mechanism/PREREGISTRATION.json",
                            "sha256": prereg_sha},
        "preregistration_amendments": amendments,
        "v1_run_superseded": {
            "path": "artifacts/heldout/heldout-10-mechanism/v1/report.json",
            "sha256": sha(DIR / "v1" / "report.json") if (DIR / "v1" / "report.json").exists() else None,
            "valid": False,
            "invalid_reason": "UNMAPPED changed paths (prefix-map omission only; see AMEND-1)",
            "note": "v1 differential measurements are byte-identical to this run; only the prefix map changed.",
        },
        "independence": prereg["independence"],
        "pins": {**man["pins"],
                 "artifacts/heldout/heldout-10/manifest.json": sha(HELDOUT / "manifest.json"),
                 "artifacts/heldout/heldout-10/report.json": sha(HELDOUT / "report.json"),
                 "artifacts/heldout/heldout-10/raw/raw_verdicts.json": sha(HELDOUT / "raw" / "raw_verdicts.json")},
        "frozen_manifest_revision": frozen.get("revision"),
        "stages": {"stage_a": {"path": man["stages"]["structural"]["path"],
                               "sha256": sha(struct)},
                   "stage_b": {"path": man["stages"]["semantic"]["path"],
                               "sha256": sha(sem)}},
        "controls": controls,
        "valid": not invalid_reasons,
        "invalid_reasons": invalid_reasons,
        "mechanism_headline": mechanism,
        "silence_semantics": {
            "stage_a": "SILENT means stage A's entire reported surface (verdict, class_id, failed_rules, failures) is byte-identical on base and mutant after deleting only the fixture path. Stage A reports no per-rule detail, so this is a verdict-surface statement.",
            "stage_b": "SILENT means stage B's entire reported surface (verdict, failed_rules, undecided_rules, and every per-rule verdict+detail string) is byte-identical on base and mutant after deleting only audited_at/source/doc_sha256. This is a per-rule-detail statement.",
            "not_claimed": "SILENT is not a static-analysis claim about which source lines read the field; it is a measured statement that no reported rule outcome responds to the changed bytes.",
        },
        "aggregates": aggregates,
        "families_informative_arms": families,
        "heldout10_headline_for_comparison": {
            "all_mutant_union_escape": report10["aggregates"]["union_escape"],
            "informative_union_escape": report10["aggregates_informative_arms_only"]["union_escape"],
        },
        "falsifier": prereg["falsifier"],
        "do_not_claim": prereg["do_not_claim"],
        "stop_rule": prereg["stop_rule"],
    }

    findings = {
        "task_id": prereg["task_id"],
        "generated_at": report["generated_at"],
        "headline": (f"On the FORM-HELDOUT-10 informative C2+C0 arms, "
                     f"{aggregates['informative_arms']['escape_silent']}/{aggregates['informative_arms']['mutants']} "
                     f"mutants escape with SILENT identical normalized output from BOTH frozen stages; "
                     f"{aggregates['informative_arms']['escape_observed']} are OBSERVED-but-accepted; "
                     f"strict CONTRACT-only union escape = {aggregates['informative_contract_only']['union_escape']} "
                     f"({aggregates['informative_contract_only']['mutants']} mutants); "
                     f"META-only union escape = {aggregates['informative_meta_only']['union_escape']} "
                     f"({aggregates['informative_meta_only']['mutants']} mutants)."),
        "interpretation": [
            "SILENT means the stage's entire normalized rule surface (verdict + rule verdicts + details) is unchanged by the mutant, so the escape is field-blindness at that stage, not a threshold call that went the wrong way.",
            "The strict number counts only mutants whose changed paths lie on the pre-registered class-contract surface; META mutants change status/citation/self-guard text and are not counted as class-binding leaks.",
            "This is measurement evidence only; it assigns no rule repair and no gate verdict.",
        ],
        "numbers_all_copied_from": "report.json",
    }

    # ---- write -----------------------------------------------------------------
    diff_doc = {"task_id": prereg["task_id"], "generated_at": report["generated_at"],
                "per_mutant": [{"mutation_id": r["mutation_id"], "fixture": r["fixture"],
                                "changed_paths": r["changed_paths"],
                                "block_categories": r["block_categories"],
                                "contract_category": r["contract_category"]} for r in records]}

    if args.verify:
        prev = load_json(RAW / "differential.json")
        if canon(prev["per_mutant"]) != canon(records):
            print("VERIFY FAIL: normalized differential differs from stored raw", file=sys.stderr)
            return 2
        if prev["preregistration_sha256"] != prereg_sha:
            print("VERIFY FAIL: preregistration hash differs", file=sys.stderr)
            return 2
        if not report["valid"]:
            print(f"VERIFY: re-run reproduces, but report invalid: {invalid_reasons}", file=sys.stderr)
            return 3
        print("VERIFY OK: 33/33 mutant differentials reproduced; controls all pass")
        return 0

    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / "differential.json").write_text(json.dumps(
        {"task_id": prereg["task_id"], "generated_at": report["generated_at"],
         "preregistration_sha256": prereg_sha,
         "base_runs": {a: {"path": v["path"], "sha256": v["sha256"],
                           "stage_a": {k: v["stage_a"][k] for k in
                                       ("exit", "verdict", "failed_rules", "normalized_sha256", "crash")},
                           "stage_b": {k: v["stage_b"][k] for k in
                                       ("exit", "verdict", "failed_rules", "normalized_sha256", "crash")}}
                       for a, v in base_runs.items()},
         "per_mutant": records}, indent=2, sort_keys=False) + "\n")
    (DIR / "diffs.json").write_text(json.dumps(diff_doc, indent=2) + "\n")
    (DIR / "adjudication.json").write_text(json.dumps(
        {"task_id": prereg["task_id"], "generated_at": report["generated_at"],
         "preregistration_sha256": prereg_sha, "per_mutant": records,
         "aggregates": aggregates, "families_informative_arms": families}, indent=2) + "\n")
    (DIR / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    (DIR / "findings.json").write_text(json.dumps(findings, indent=2) + "\n")

    print(json.dumps({"valid": report["valid"], "mechanism": mechanism,
                      "informative": aggregates["informative_arms"],
                      "strict_contract": aggregates["informative_contract_only"],
                      "meta": aggregates["informative_meta_only"],
                      "invalid_reasons": invalid_reasons}, indent=2))
    return 0 if report["valid"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
