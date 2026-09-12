#!/usr/bin/env python3
"""A2 ablation harness: matched-budget scheduler + metrics pipeline + synthetic dry-run.

Modes:
  --dry-run   simulate the five arms with declared ground-truth rates, exercise the full
              pipeline (budget match, gate, adjudication, metrics), and write the CSV/report.
  --execute   would call framework/pool.py; refuses to run without SWARM_PROVIDERS
              (fail-closed: no synthetic numbers are ever written as if they were real).

The dry-run validates the pipeline and the power analysis. It estimates nothing about real
arms: acceptance rates are declared inputs.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import audit_lib as A  # noqa: E402

ARMS = ["S", "SC", "IC", "ICC", "NULL"]
# Declared simulation inputs (NOT results).
SIM = {
    "S":   {"p_accept": 0.42, "tokens_per_call": 12842, "hf": 0.04, "effort": "high"},
    "SC":  {"p_accept": 0.46, "tokens_per_call": 12842, "hf": 0.05, "effort": "high"},
    "IC":  {"p_accept": 0.30, "tokens_per_call": 2137,  "hf": 0.16, "effort": "low"},
    "ICC": {"p_accept": 0.36, "tokens_per_call": 2137,  "hf": 0.09, "effort": "low"},
    "NULL": {"p_accept": 0.06, "tokens_per_call": 2137, "hf": 0.16, "effort": "low"},
}
TASKS = 24
SEEDS = 8
BUDGET_TOKENS = 4_000_000      # matched completion-token budget per arm
WALL_CLOCK_S = 4 * 3600
VERIFIER_CALLS_PER_ACCEPT = 3
HUMAN_REVIEW_MINUTES = 30


def mdes_two_proportions(p1: float, n: int, alpha: float = 0.05, power: float = 0.80) -> float:
    """Absolute difference detectable with n independent outputs per arm."""
    z_a, z_b = 1.959963985, 0.8416212336
    lo, hi = 1e-4, 0.99
    for _ in range(100):
        mid = (lo + hi) / 2
        p2 = min(0.999, p1 + mid)
        pbar = (p1 + p2) / 2
        need = (z_a + z_b) * math.sqrt(2 * pbar * (1 - pbar) / n)
        lo, hi = (mid, hi) if mid < need else (lo, mid)
    return round(hi, 4)


def n_for_effect(p1: float, delta: float, alpha: float = 0.05, power: float = 0.80) -> int:
    z_a, z_b = 1.959963985, 0.8416212336
    p2 = min(0.999, p1 + delta)
    pbar = (p1 + p2) / 2
    return math.ceil(((z_a + z_b) ** 2) * 2 * pbar * (1 - pbar) / (delta ** 2))


def simulate(rng: random.Random) -> list[dict]:
    rows: list[dict] = []
    cells = [(s, t) for s in range(SEEDS) for t in range(TASKS)]
    for arm in ARMS:
        cfg = SIM[arm]
        n_out = BUDGET_TOKENS // cfg["tokens_per_call"]
        counts = {c: 0 for c in cells}
        for i in range(n_out):
            counts[cells[i % len(cells)]] += 1
        for (seed, task), k in counts.items():
            for _ in range(k):
                raw = 1 if rng.random() < cfg["p_accept"] else 0
                hf = 1 if rng.random() < cfg["hf"] else 0
                gated = raw and not hf
                rows.append({
                    "arm": arm, "seed": seed, "task": task,
                    "tokens": cfg["tokens_per_call"], "wall_clock_s": WALL_CLOCK_S,
                    "proposed": 1, "gate_accepted": raw, "hard_failure": hf,
                    "accepted": int(gated),
                    "citation_support": round(rng.uniform(.4, 1.0) if gated else 0, 3),
                    "novelty": round(rng.uniform(.5, 1.0) if gated else 0, 3),
                    "reviewer": f"rev-{rng.randint(1, 6)}",
                })
    return rows


def summarize(rows: list[dict]) -> dict:
    out = {}
    for arm in ARMS:
        rs = [r for r in rows if r["arm"] == arm]
        acc = sum(r["accepted"] for r in rs)
        tokens = sum(r["tokens"] for r in rs)
        hf = sum(r["hard_failure"] for r in rs)
        accepted_rows = [r for r in rs if r["accepted"]]
        out[arm] = {
            "outputs": len(rs), "accepted": acc,
            "accept_rate": round(acc / len(rs), 4),
            "hard_failure_rate": round(hf / len(rs), 4),
            "accepts_per_1M_tokens": round(acc / (tokens / 1e6), 4),
            "total_tokens": tokens, "wall_clock_s": rs[0]["wall_clock_s"] if rs else None,
            "citation_support_mean": round(sum(r["citation_support"] for r in accepted_rows) / max(1, acc), 4),
            "mean_novelty": round(sum(r["novelty"] for r in accepted_rows) / max(1, acc), 4),
            "cost_per_accepted_tokens": (round(tokens / acc, 1) if acc else None),
            "kish_ess_reviewers": round(A.kish_ess([r["reviewer"] for r in accepted_rows]), 3),
            "tasks_covered": len({r["task"] for r in accepted_rows}),
        }
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--outdir", default=str(ROOT / "evaluation"))
    ap.add_argument("--seed", type=int, default=20260911)
    a = ap.parse_args()
    if a.execute:
        import os
        if not (os.environ.get("SWARM_PROVIDERS") or (Path.home() / ".maso/model-providers.yaml").exists()):
            print("REFUSED: --execute requires SWARM_PROVIDERS or ~/.maso/model-providers.yaml; "
                  "no synthetic numbers will be written as results.")
            return 3
        print("provider config present; only the dry-run scheduler is implemented in this harness revision.")
        return 0
    if not a.dry_run:
        ap.error("choose --dry-run or --execute")

    rng = random.Random(a.seed)
    rows = simulate(rng)
    summary = summarize(rows)
    outdir = Path(a.outdir); outdir.mkdir(parents=True, exist_ok=True)

    csv_path = outdir / "ablation_dryrun.csv"
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)

    arms_budget = [{"total_tokens": summary[x]["total_tokens"],
                    "wall_clock_s": summary[x]["wall_clock_s"]} for x in ARMS]
    budget_violations = A.check_budget_match(arms_budget)
    broken = [dict(x) for x in arms_budget]
    broken[0]["total_tokens"] = int(broken[0]["total_tokens"] * 1.3)   # break exactly one arm
    negative_control_fires = bool(A.check_budget_match(broken))

    n_by_arm = {arm: summary[arm]["outputs"] for arm in ARMS}
    power = {
        "seeds_per_arm": SEEDS,
        "outputs_per_arm": n_by_arm,
        "mdes_absolute_at_p1_0.30": {arm: mdes_two_proportions(0.30, n_by_arm[arm]) for arm in ARMS},
        "n_needed_for_15pt_at_p1_0.30": n_for_effect(0.30, 0.15),
        "n_needed_for_5pt_at_p1_0.30": n_for_effect(0.30, 0.05),
        "n_needed_for_3pt_at_p1_0.30": n_for_effect(0.30, 0.03),
        "seed_rule": ("8 seeds is the minimum for reporting a max-statistic; it is NOT the power "
                      "unit. Power is driven by the number of independent outputs, which is "
                      "budget/tokens_per_call and therefore differs by arm by design."),
    }
    contrasts = {}
    for name, (x, y) in {"ICC-IC": ("ICC", "IC"), "ICC-S": ("ICC", "S"),
                         "SC-S": ("SC", "S"), "ICC-NULL": ("ICC", "NULL"),
                         "IC-NULL": ("IC", "NULL")}.items():
        contrasts[name] = round(summary[x]["accepts_per_1M_tokens"] -
                                summary[y]["accepts_per_1M_tokens"], 4)

    report = {
        "artifact": "A2-ablation-dry-run",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "status": "SIMULATED — inputs are declared rates, not measurements; no arm was run",
        "simulation_inputs": SIM,
        "design_ref": "evaluation/ablation_design.yaml",
        "budget_tokens_per_arm": BUDGET_TOKENS,
        "wall_clock_s": WALL_CLOCK_S,
        "seeds": SEEDS, "tasks": TASKS,
        "per_arm": summary,
        "primary_contrasts_accepts_per_1M_tokens": contrasts,
        "budget_match_check": {
            "violations_on_matched_arms": [v.as_dict() for v in budget_violations],
            "negative_control_breaks_one_arm": True,
            "negative_control_fires": negative_control_fires,
        },
        "guardrail_example": {
            "rule": "hard_failure_rate > 0.10 truncates the arm's accepted count",
            "arms_above": [arm for arm in ARMS if summary[arm]["hard_failure_rate"] > 0.10],
        },
        "power": power,
        "null_arm_note": ("NULL must be implemented as iid random selection from the candidate "
                          "pool at matched tokens; here it is a declared low-acceptance arm"),
        "provider_blocker": "no provider config in this environment; --execute refuses to run",
    }
    (outdir / "ablation_dryrun_report.json").write_text(json.dumps(report, indent=2) + "\n")

    print(f"dry-run outputs={len(rows)} -> {csv_path.relative_to(ROOT)}")
    print(f"budget violations on matched arms: {len(budget_violations)} "
          f"(negative control fires: {negative_control_fires})")
    for arm in ARMS:
        s = summary[arm]
        print(f"  {arm:4s} n={s['outputs']:5d} accept={s['accept_rate']:.3f} hf={s['hard_failure_rate']:.3f} "
              f"per1M={s['accepts_per_1M_tokens']:7.2f} ESS={s['kish_ess_reviewers']}")
    print(f"  MDES at n=S/IC: {power['mdes_absolute_at_p1_0.30']['S']}/"
          f"{power['mdes_absolute_at_p1_0.30']['IC']} | n for 5pt: "
          f"{power['n_needed_for_5pt_at_p1_0.30']} | n for 3pt: {power['n_needed_for_3pt_at_p1_0.30']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
