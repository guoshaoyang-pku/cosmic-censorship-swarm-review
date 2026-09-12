#!/usr/bin/env python3
"""Independent-checker agreement audit (A1), adjudicated.

Four execution workers independently built class-binding gates for F1/F2. This harness
runs every checker over the union of their fixture corpora and reports:

  1. per-checker score against *adjudicated* labels (artifacts/audit/fixture_adjudication.json),
     not against the authors' own labels;
  2. cross-acceptance matrix: does a checker accept other checkers' declared-good documents?
     (a shared schema does not exist yet, so this measures interface compatibility);
  3. blind-spot probes: fixtures the authors documented as escapes;
  4. pairwise agreement, Cohen's kappa and the Kish effective sample size of the pool.

Usage: python3 artifacts/audit/checker_agreement.py [--out artifacts/audit/reports]
"""
from __future__ import annotations

import argparse
import itertools
import json
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import audit_lib as A  # noqa: E402

CHECKERS = {
    "w06": ["python3", "artifacts/worker-06/check_class_binding.py"],
    "f11": ["python3", "artifacts/flash-11/f1_aux_class_binding/check_schema.py"],
    "f13": ["python3", "artifacts/flash-13/f1_gate/check_schema.py"],
    "w17": ["python3", "artifacts/worker-17/class_binding_gate/class_binding_gate.py"],
}
FIXTURE_DIRS = ["artifacts/flash-11/f1_aux_class_binding/fixtures",
                "artifacts/flash-13/f1_gate/fixtures"]
EXTRA = ["artifacts/flash-12/f2_scc_split/af_scc_c2_c0.draft.yaml"]


def load_json(p: Path) -> dict:
    return json.loads(p.read_text()) if p.exists() else {}


def load_declared() -> dict[str, str]:
    exp: dict[str, str] = {}
    p11 = ROOT / FIXTURE_DIRS[0] / "EXPECTATIONS.json"
    for name, meta in load_json(p11).items():
        v = str(meta.get("verdict", "")).lower()
        kind = meta.get("kind", "")
        exp[name] = "probe" if kind == "expected_escape" else ("pass" if v == "accept" else "fail")
    p13 = ROOT / FIXTURE_DIRS[1] / "manifest.json"
    for name, meta in load_json(p13).items():
        v = str(meta.get("expected_verdict", "")).lower()
        n = Path(meta["path"]).name
        exp[n] = "probe" if "probe" in name else ("pass" if v == "accept" else "fail")
    for n in ("good_af_wcc_vac_gen.yaml", "good_af_scc_c2_vac_gen.yaml",
              "good_af_scc_c0_vac_gen.yaml", "good_af_wcc_scalar_sph.yaml"):
        exp.setdefault(n, "pass")
    exp.setdefault("valid_af_wcc_vac_gen.yaml", "pass")
    return exp


def fixtures() -> list[Path]:
    out: list[Path] = []
    for d in FIXTURE_DIRS:
        out += sorted((ROOT / d).glob("*.yaml"))
    out += [ROOT / p for p in EXTRA if (ROOT / p).exists()]
    return out


def run_checker(key: str, fixture: Path) -> dict:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / "out.json"
        cmd = CHECKERS[key][:]
        if key == "w06":
            cmd += ["--json", str(tmp)]
        elif key == "f11":
            cmd += ["--json"]
        elif key == "w13" or key == "f13":
            cmd += ["--json-out", str(tmp)]
        elif key == "w17":
            cmd += ["--json"]
        cmd += [str(fixture)]
        try:
            r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=120)
        except subprocess.TimeoutExpired:
            return {"verdict": "error", "exit": None, "codes": [], "detail": "timeout"}
        code = r.returncode
        verdict = {0: "pass", 1: "fail", 2: "inconclusive"}.get(code, "error")
        codes: list[str] = []
        try:
            if key == "w06" and tmp.exists():
                d = json.loads(tmp.read_text())
                codes = [c.get("check_id") for c in d.get("checks", [])
                         if c.get("verdict") not in ("pass", None)]
            elif key == "f11":
                d = json.loads(r.stdout)
                d = d[0] if isinstance(d, list) and d else d
                codes = list(d.get("failed_codes", []))
            elif key == "f13" and tmp.exists():
                d = json.loads(tmp.read_text())
                codes = sorted({f.get("rule") for f in d.get("failed_rules", [])})
            elif key == "w17":
                d = json.loads(r.stdout)
                codes = sorted({v.get("code") for rep in d.get("reports", [])
                                for v in rep.get("violations", []) if v.get("code")})
        except Exception:
            codes = []
        return {"verdict": verdict, "exit": code, "codes": codes,
                "detail": "" if verdict != "error" else (r.stderr or r.stdout)[-160:]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE / "reports"))
    a = ap.parse_args()

    declared = load_declared()
    adj = load_json(HERE / "fixture_adjudication.json").get("fixtures", {})
    fx = fixtures()
    rows = []
    for f in fx:
        name = f.name
        if name in adj and isinstance(adj[name], dict) and "adjudicated" in adj[name]:
            adjudicated = "pass" if adj[name]["adjudicated"] == "accept" else "fail"
            severity = adj[name].get("severity")
            findings = adj[name].get("findings", [])
        else:
            adjudicated, severity, findings = None, None, []
        row = {"fixture": name, "path": str(f.relative_to(ROOT)),
               "declared": declared.get(name), "adjudicated": adjudicated,
               "severity": severity, "findings": findings, "checkers": {}}
        for key in CHECKERS:
            row["checkers"][key] = run_checker(key, f)
        rows.append(row)

    keys = list(CHECKERS)
    accept_intended = [r for r in rows if r["declared"] == "pass"]
    negatives = [r for r in rows if r["declared"] == "fail"]
    probes = [r for r in rows if r["declared"] == "probe"]

    scores = {}
    for key in keys:
        # against adjudicated labels (only rows that have one)
        acc = fa = 0
        for r in rows:
            if r["adjudicated"] is None:
                continue
            v = r["checkers"][key]["verdict"]
            if v == "error":
                continue
            if r["adjudicated"] == v:
                acc += 1
            elif r["adjudicated"] == "fail" and v == "pass":
                fa += 1
        false_accept_own_good = [r["fixture"] for r in accept_intended
                                 if r["adjudicated"] == "fail"
                                 and r["checkers"][key]["verdict"] == "pass"]
        neg_recall = [r["fixture"] for r in negatives
                      if r["checkers"][key]["verdict"] != "pass"]
        scores[key] = {
            "adjudicated_rows": sum(1 for r in rows if r["adjudicated"]),
            "accuracy_vs_adjudication": acc,
            "false_accepts_vs_adjudication": fa,
            "accepts_contaminated_good_fixtures": false_accept_own_good,
            "negative_recall": f"{len(neg_recall)}/{len(negatives)}",
            "errors": sum(1 for r in rows if r["checkers"][key]["verdict"] == "error"),
        }

    pairs = {}
    for k1, k2 in itertools.combinations(keys, 2):
        a1, a2 = [], []
        for r in rows:
            v1, v2 = r["checkers"][k1]["verdict"], r["checkers"][k2]["verdict"]
            if v1 in ("pass", "fail") and v2 in ("pass", "fail"):
                a1.append(v1); a2.append(v2)
        agree = sum(1 for x, y in zip(a1, a2) if x == y)
        pairs[f"{k1}|{k2}"] = {"n": len(a1),
                               "agreement": round(agree / len(a1), 4) if a1 else None,
                               "kappa": A.cohen_kappa(a1, a2)}
    vectors = {k: tuple(r["checkers"][k]["verdict"] for r in rows) for k in keys}
    clusters: dict[tuple, list[str]] = {}
    for k, v in vectors.items():
        clusters.setdefault(v, []).append(k)
    ess = A.kish_ess(list(vectors.values()))

    # cross-acceptance matrix on accept-intended documents only
    cross = {}
    for r in accept_intended:
        cross[r["fixture"]] = {"origin": ("flash-11" if r["fixture"].startswith("good_")
                                          else "flash-13" if r["fixture"].startswith("valid_")
                                          else "probe:" + (r["fixture"].split("_")[0])),
                               "adjudicated": r["adjudicated"],
                               "verdicts": {k: r["checkers"][k]["verdict"] for k in keys},
                               "codes": {k: r["checkers"][k]["codes"][:4] for k in keys}}

    out = {
        "audit": "A1-checker-agreement-adjudicated",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "adjudication_file": "artifacts/audit/fixture_adjudication.json",
        "n_fixtures": len(rows), "n_accept_intended": len(accept_intended),
        "n_negatives": len(negatives), "n_probes": len(probes),
        "per_checker_scores": scores,
        "cross_acceptance": cross,
        "pairwise": pairs,
        "verdict_vector_clusters": list(clusters.values()),
        "kish_ess_checkers": round(ess, 3),
        "nominal_checkers": len(keys),
        "preamble": ("No checker's own corpus is a valid gold standard: every flash-11 'good' "
                     "fixture is adjudicated reject (HF-01 conclusion inflation + HF-06 "
                     "genericity/quantifier mismatch). Scores are reported against the "
                     "adjudicated labels, and cross-acceptance measures whether a shared "
                     "artifact schema exists at all."),
        "rows": rows,
    }
    outp = Path(a.out); outp.mkdir(parents=True, exist_ok=True)
    A.write_json(outp / "checker_agreement.json", out)

    md = [f"# Independent checker agreement, adjudicated ({out['generated_at']})", "",
          f"- fixtures: {len(rows)} ({len(accept_intended)} accept-intended, "
          f"{len(negatives)} negatives, {len(probes)} escape probes)",
          f"- nominal checkers: {len(keys)} | **Kish ESS: {out['kish_ess_checkers']}**",
          f"- {out['preamble']}", "",
          "## Score against adjudicated labels", "",
          "| checker | adjudicated rows | accuracy | false accepts | accepts contaminated 'good' fixtures | negative recall |",
          "|---|---:|---:|---:|---|---:|"]
    for k, s in scores.items():
        md.append(f"| {k} | {s['adjudicated_rows']} | {s['accuracy_vs_adjudication']} | "
                  f"{s['false_accepts_vs_adjudication']} | "
                  f"{len(s['accepts_contaminated_good_fixtures'])} | {s['negative_recall']} |")
    md += ["", "## Cross-acceptance of declared-accept documents", "",
           "| fixture | origin | adjudicated | " + " | ".join(keys) + " |",
           "|---|---|---|" + "---|" * len(keys)]
    for name, c in cross.items():
        md.append(f"| `{name}` | {c['origin']} | {c['adjudicated']} | " +
                  " | ".join(c["verdicts"][k] for k in keys) + " |")
    md += ["", "## Pairwise agreement", "", "| pair | n | agreement | kappa |", "|---|---:|---:|---:|"]
    for k, v in pairs.items():
        md.append(f"| {k} | {v['n']} | {v['agreement']} | {v['kappa']} |")
    md += ["", f"## Verdict-vector clusters ({len(clusters)})", ""]
    for i, cl in enumerate(clusters.values()):
        md.append(f"- cluster {i}: {', '.join(cl)}")
    (outp / "checker_agreement.md").write_text("\n".join(md) + "\n")

    print(f"checkers={len(keys)} fixtures={len(rows)} ESS={out['kish_ess_checkers']}")
    for k, s in scores.items():
        print(f"  {k}: acc={s['accuracy_vs_adjudication']}/{s['adjudicated_rows']} "
              f"fa={s['false_accepts_vs_adjudication']} "
              f"contaminated_good_accepted={len(s['accepts_contaminated_good_fixtures'])} "
              f"neg_recall={s['negative_recall']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
