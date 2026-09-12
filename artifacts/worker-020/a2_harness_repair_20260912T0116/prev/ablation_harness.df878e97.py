#!/usr/bin/env python3
"""A2 ablation harness (draft, UNVERIFIED): matched-budget four-arm comparison.

Assignment
----------
``asg-2026-09-11-A2-deepseek-flash-20-29`` in ``comms/inbox/deepseek-flash-20.jsonl``:
build the ablation harness, run it on synthetic/dummy proposers only, dry-run, **no
model calls**, gate ``G-AUDIT``.  Node A2, class GLOBAL.

What it does
------------
Runs five arms over a deterministic synthetic episode suite:

1. ``strong_single``        one strong model, one call per episode
2. ``self_consistency``     same model, k samples, majority vote
3. ``independent_cheap``    N cheap agents, answer reported by one of them (no aggregation)
4. ``cheap_coordinator``    same N cheap agents plus a coordinator that aggregates
5. ``random_iid_null``      iid-uniform null baseline (control, not a primary arm)

Every arm gets the *same enforced caps* ``(token_budget, wall_clock_budget)``.  A call is
only issued when it fits inside both caps, so no arm can overspend; residuals are reported
and checked.  The comparison is declared invalid if the primary arms are not all limited by
the same resource, or if token consumption spreads beyond tolerance.

The eight pre-registered metrics (per arm, never averaged into a scalar):

accepted_claim_rate, hard_failure_rate, citation_support, duplication,
reviewer_agreement, novel_accepted_coverage, cost_per_accepted_claim,
per_class_coverage.

The harness never imports a network client and has no model-call path.  The synthetic
proposers are deterministic functions of ``(seed, model_id, agent_id, episode_idx)``, so a
run is reproducible and a call-order change cannot change a claim.

Status
------
Draft for lead-audit.  The built-in model parameters are placeholders for wiring real
proposers later; **no result produced here is evidence about real models**.  When the audit
lead publishes ``evaluation/ablation_design.yaml`` its keys override the defaults via
``--design``.  ``validation_status`` stays ``unverified`` until reviewed.

Usage
-----
    python3 evaluation/ablation_harness.py --dry-run
    python3 evaluation/ablation_harness.py --self-test
    python3 evaluation/ablation_harness.py --json-out evaluation/ablation_report.json \
        --csv-out evaluation/ablation.csv
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLASSES = ("AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH")
LABELS = (0, 1, 2)
METRICS = (
    "accepted_claim_rate", "hard_failure_rate", "citation_support", "duplication",
    "reviewer_agreement", "novel_accepted_coverage", "cost_per_accepted_claim",
    "per_class_coverage",
)
DEFAULTS = {
    "seed": 20260911,
    "episodes": 60,
    "token_budget": 20000,
    "wall_budget": 60.0,
    "token_tolerance": 0.15,
    "reviewer_error_rate": 0.12,
}


# ---------------------------------------------------------------------------
# specs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ModelSpec:
    model_id: str
    tokens_per_call: int
    latency_s: float
    accuracy: float
    failure_rate: float = 0.0
    citation_honesty: float = 0.9
    corr_error: float = 0.0          # probability of the shared/biased error on bias episodes
    bias_label: int = 0
    bias_offset: int = 0
    bias_period: int = 7


@dataclass(frozen=True)
class ArmSpec:
    name: str
    kind: str                        # single | self_consistency | independent | coordinated | null
    models: tuple[str, ...]
    samples: int = 1
    coordinator: bool = False
    coordinator_tokens: int = 40
    coordinator_latency_s: float = 0.05
    is_primary: bool = True
    is_null: bool = False
    description: str = ""


@dataclass(frozen=True)
class Episode:
    idx: int
    episode_id: str
    class_id: str
    label: int


@dataclass
class ArmResult:
    arm: str
    kind: str
    is_primary: bool
    is_null: bool
    token_budget: float
    wall_budget: float
    tokens_consumed: float
    wall_consumed: float
    max_episode_cost: float
    stop_reason: str
    episodes_attempted: int
    calls: int
    claims: list = field(default_factory=list)
    accepted: int = 0
    rejected: int = 0
    hard_failures: int = 0
    citations_supported: int = 0
    reviewer_agreed: int = 0
    reviewer_reviewed: int = 0
    accepted_episode_ids: list = field(default_factory=list)
    metrics: dict = field(default_factory=dict)


def synthetic_models() -> dict[str, ModelSpec]:
    models = {
        "strong": ModelSpec("strong", 400, 0.60, 0.86, 0.02, 0.95,
                            corr_error=0.10, bias_label=2, bias_offset=0),
        "random": ModelSpec("random", 50, 0.05, 1.0 / len(LABELS), 0.0, 0.34,
                            corr_error=0.0, bias_offset=0),
    }
    # Cheap agents: same family parameters, but each carries its OWN bias label/offset,
    # i.e. independent error directions.  Sampling one cheap model k times (or reusing the
    # same agent) keeps the bias -> correlated errors, which is the failure mode the
    # project measured.
    for a in range(5):
        models[f"cheap-{a}"] = ModelSpec(
            f"cheap-{a}", 120, 0.15, 0.55, 0.05, 0.80,
            corr_error=0.45, bias_label=(a % len(LABELS)), bias_offset=a, bias_period=5,
        )
    return models


def synthetic_arms() -> list[ArmSpec]:
    cheap = tuple(f"cheap-{a}" for a in range(5))
    return [
        ArmSpec("strong_single", "single", ("strong",), 1, False, 0, 0.0, True, False,
                "one strong model, one call per episode"),
        ArmSpec("self_consistency", "self_consistency", ("strong",), 5, False, 0, 0.0, True, False,
                "strong model sampled 5x per episode, majority vote (correlated errors)"),
        ArmSpec("independent_cheap", "independent", cheap, 5, False, 0, 0.0, True, False,
                "5 cheap agents with independent biases; one reporting agent, no aggregation"),
        ArmSpec("cheap_coordinator", "coordinated", cheap, 5, True, 40, 0.05, True, False,
                "5 cheap agents plus a coordinator that majority-aggregates"),
        ArmSpec("random_iid_null", "null", ("random",), 1, False, 0, 0.0, False, True,
                "iid-uniform null baseline; control arm, not part of the four-arm claim"),
    ]


def build_episodes(n: int) -> list[Episode]:
    eps = []
    for i in range(n):
        cls = CLASSES[i % len(CLASSES)]
        eps.append(Episode(i, f"ep-{i:04d}", cls, LABELS[i % len(LABELS)]))
    return eps


# ---------------------------------------------------------------------------
# synthetic proposer (deterministic; no network, no model call)
# ---------------------------------------------------------------------------


def propose(model: ModelSpec, ep: Episode, agent_id: int, seed: int):
    """Return a claim dict or None (invalid output).  Pure function of the key."""
    rng = random.Random(f"{seed}|{model.model_id}|{agent_id}|{ep.idx}")
    if rng.random() < model.failure_rate:
        return None
    biased = (ep.idx % model.bias_period) == (model.bias_offset % model.bias_period)
    if biased and rng.random() < model.corr_error:
        label = model.bias_label
    elif rng.random() < model.accuracy:
        label = ep.label
    else:
        label = rng.choice([l for l in LABELS if l != ep.label])
    return {
        "episode_id": ep.episode_id,
        "episode_idx": ep.idx,
        "class_id": ep.class_id,
        "label": label,
        "citation": f"cite-{ep.class_id}-{model.model_id}-{label}",
        "citation_ok": rng.random() < model.citation_honesty,
        "tokens": model.tokens_per_call,
        "model_id": model.model_id,
        "agent_id": agent_id,
    }


def majority(claims: list[dict]):
    counts: dict[int, int] = {}
    for c in claims:
        counts[c["label"]] = counts.get(c["label"], 0) + 1
    best = max(counts.values())
    winners = sorted(l for l, v in counts.items() if v == best)
    winner = winners[0]
    winner_claim = next(c for c in claims if c["label"] == winner)
    return winner_claim, best / len(claims)


def verify_final(final, ep: Episode) -> str:
    if final is None:
        return "hard_failure"
    if final["class_id"] != ep.class_id:
        return "rejected"
    if final["label"] != ep.label:
        return "rejected"
    if not final["citation_ok"]:
        return "rejected"
    return "accepted"


def reviewers_agree(claim: dict, seed: int, error_rate: float) -> bool:
    verdicts = []
    for r in (0, 1):
        rng = random.Random(f"review|{seed}|{r}|{claim['episode_id']}|{claim['label']}")
        wrong = rng.random() < error_rate
        verdicts.append(not wrong)
    return verdicts[0] == verdicts[1]


# ---------------------------------------------------------------------------
# arm execution
# ---------------------------------------------------------------------------


def _per_sample_models(arm: ArmSpec) -> list[str]:
    """Model used by each sample: round-robin for independent/coordinated, fixed otherwise."""
    if arm.kind in ("independent", "coordinated"):
        return [arm.models[s % len(arm.models)] for s in range(arm.samples)]
    return [arm.models[0]] * arm.samples


def episode_cost(arm: ArmSpec, models: dict[str, ModelSpec]) -> float:
    cost = sum(models[m].tokens_per_call for m in _per_sample_models(arm))
    if arm.coordinator:
        cost += arm.coordinator_tokens
    return float(cost)


def episode_latency(arm: ArmSpec, models: dict[str, ModelSpec]) -> float:
    lat = sum(models[m].latency_s for m in _per_sample_models(arm))
    if arm.coordinator:
        lat += arm.coordinator_latency_s
    return float(lat)


def _sample_claims(arm: ArmSpec, ep: Episode, models: dict[str, ModelSpec], seed: int):
    claims = []
    for s in range(arm.samples):
        if arm.kind in ("independent", "coordinated"):
            model_id = arm.models[s % len(arm.models)]
            agent_id = s
        else:
            model_id = arm.models[0]
            agent_id = 0
        c = propose(models[model_id], ep, agent_id, seed)
        if c is not None:
            claims.append(c)
    return claims


def run_arm(arm: ArmSpec, episodes: list[Episode], models: dict[str, ModelSpec], *,
            token_budget: float, wall_budget: float, seed: int, budget_mode: str = "tokens",
            episode_cap: int | None = None,
            reviewer_error_rate: float = DEFAULTS["reviewer_error_rate"]) -> ArmResult:
    """Run one arm.  ``budget_mode='calls'`` is the deliberately flawed control: it caps the
    episode count instead of tokens, so arms end up at unequal token budgets."""
    res = ArmResult(arm=arm.name, kind=arm.kind, is_primary=arm.is_primary, is_null=arm.is_null,
                    token_budget=float(token_budget), wall_budget=float(wall_budget),
                    tokens_consumed=0.0, wall_consumed=0.0,
                    max_episode_cost=episode_cost(arm, models), stop_reason="episodes_exhausted",
                    episodes_attempted=0, calls=0)
    if budget_mode == "calls" and episode_cap is None:
        episode_cap = len(episodes)
    idx = 0
    while idx < len(episodes):
        ep = episodes[idx]
        est = res.max_episode_cost
        if budget_mode == "tokens" and res.tokens_consumed + est > token_budget:
            res.stop_reason = "token_budget"
            break
        if budget_mode == "calls" and res.episodes_attempted >= (episode_cap or len(episodes)):
            res.stop_reason = "call_budget"
            break
        if res.wall_consumed + episode_latency(arm, models) > wall_budget:
            res.stop_reason = "wall_clock"
            break
        claims = _sample_claims(arm, ep, models, seed)
        res.calls += arm.samples
        # Failed/invalid calls still consume the full episode budget; counting only the
        # surviving claims would under-report cost and silently break budget matching.
        res.tokens_consumed += res.max_episode_cost
        res.wall_consumed += episode_latency(arm, models)
        res.episodes_attempted += 1
        res.claims.extend(claims)

        if not claims:
            final = None
        elif arm.kind in ("single", "independent", "null"):
            # no aggregation: independent agents each answer; the arm reports one of them
            pick = idx % len(claims) if arm.kind == "independent" else 0
            final = claims[pick]
        elif arm.kind == "self_consistency":
            final, _ = majority(claims)
        elif arm.kind == "coordinated":
            final, _ = majority(claims)
        else:  # pragma: no cover - defensive
            final = claims[0]

        verdict = verify_final(final, ep)
        if verdict == "accepted":
            res.accepted += 1
            res.accepted_episode_ids.append(ep.episode_id)
            if reviewers_agree(final, seed, reviewer_error_rate):
                res.reviewer_agreed += 1
            res.reviewer_reviewed += 1
        elif verdict == "hard_failure":
            res.hard_failures += 1
        else:
            res.rejected += 1
        idx += 1
    res.citations_supported = sum(1 for c in res.claims if c["citation_ok"])
    res.metrics = compute_metrics(res, episodes)
    return res


def compute_metrics(res: ArmResult, episodes: list[Episode]) -> dict:
    attempts = max(1, res.episodes_attempted)
    total_claims = len(res.claims)
    distinct = len({(c["episode_id"], c["label"], c["class_id"]) for c in res.claims})
    per_class = {}
    for cls in CLASSES:
        total_cls = sum(1 for e in episodes if e.class_id == cls)
        got = len({eid for eid in res.accepted_episode_ids
                   if next(e for e in episodes if e.episode_id == eid).class_id == cls})
        per_class[cls] = (got / total_cls) if total_cls else None
    return {
        "accepted_claim_rate": res.accepted / attempts,
        "hard_failure_rate": res.hard_failures / attempts,
        "citation_support": (res.citations_supported / total_claims) if total_claims else None,
        "duplication": (1.0 - distinct / total_claims) if total_claims else None,
        "reviewer_agreement": (res.reviewer_agreed / res.reviewer_reviewed) if res.reviewer_reviewed else None,
        "novel_accepted_coverage": len(set(res.accepted_episode_ids)) / max(1, len(episodes)),
        "cost_per_accepted_claim": (res.tokens_consumed / res.accepted) if res.accepted else None,
        "per_class_coverage": per_class,
    }


# ---------------------------------------------------------------------------
# budget matching
# ---------------------------------------------------------------------------


def check_matched_budgets(results: list[ArmResult], token_tolerance: float) -> dict:
    """A comparison is matched only if the primary arms share the same enforced caps and
    were limited by the same resource, with token residuals inside one episode's cost."""
    violations = []
    primary = [r for r in results if r.is_primary]
    caps = {(r.token_budget, r.wall_budget) for r in primary}
    if len(caps) > 1:
        violations.append(f"primary arms have different enforced caps: {sorted(caps)}")
    for r in results:
        if r.tokens_consumed > r.token_budget + 1e-9:
            violations.append(f"{r.arm}: overspent tokens ({r.tokens_consumed} > {r.token_budget})")
        if r.wall_consumed > r.wall_budget + 1e-9:
            violations.append(f"{r.arm}: overspent wall clock ({r.wall_consumed:.3f} > {r.wall_budget})")
        if r.stop_reason == "wall_clock" and r.is_primary:
            violations.append(f"{r.arm}: wall-clock-limited; the comparison is confounded")
    if primary:
        consumed = [r.tokens_consumed for r in primary]
        spread = (max(consumed) - min(consumed)) / max(1.0, primary[0].token_budget)
        if spread > token_tolerance:
            violations.append(
                f"primary token consumption spread {spread:.3f} > tolerance {token_tolerance}")
        for r in primary:
            if r.stop_reason == "call_budget":
                violations.append(f"{r.arm}: call-count-limited (unmatched-budget control mode)")
            residual = r.token_budget - r.tokens_consumed
            if residual > r.max_episode_cost + 1e-9:
                violations.append(
                    f"{r.arm}: stopped with residual {residual:.0f} > one episode cost "
                    f"{r.max_episode_cost:.0f}")
    return {
        "matched": not violations,
        "violations": violations,
        "token_spread_fraction": (spread := (
            (max([r.tokens_consumed for r in primary]) - min([r.tokens_consumed for r in primary]))
            / max(1.0, primary[0].token_budget)) if primary else None),
        "limits": [{"arm": r.arm, "token_budget": r.token_budget, "wall_budget": r.wall_budget,
                    "tokens_consumed": r.tokens_consumed, "wall_consumed": round(r.wall_consumed, 4),
                    "stop_reason": r.stop_reason} for r in results],
    }


# ---------------------------------------------------------------------------
# orchestration
# ---------------------------------------------------------------------------


def load_design(path: Path | None) -> dict:
    if path is None:
        return {}
    if not path.exists():
        raise SystemExit(f"design file not found: {path}")
    text = path.read_text()
    if path.suffix in (".yaml", ".yml"):
        try:
            import yaml
        except ImportError as e:  # pragma: no cover
            raise SystemExit(f"PyYAML required for {path}: {e}")
        doc = yaml.safe_load(text)
    else:
        doc = json.loads(text)
    return doc or {}


def run_ablation(config: dict, *, arms: list[ArmSpec] | None = None,
                 budget_mode: str = "tokens") -> dict:
    seed = int(config["seed"])
    episodes = build_episodes(int(config["episodes"]))
    models = synthetic_models()
    arms = arms if arms is not None else synthetic_arms()
    if budget_mode == "calls":
        # unmatched control: equal episode counts, wall clock not binding, token caps ignored
        run_cfg = dict(config)
        run_cfg["wall_budget"] = 1e9
    else:
        run_cfg = config
    results = [
        run_arm(a, episodes, models, token_budget=run_cfg["token_budget"],
                wall_budget=run_cfg["wall_budget"], seed=seed, budget_mode=budget_mode,
                episode_cap=(config["episodes"] if budget_mode == "calls" else None),
                reviewer_error_rate=run_cfg["reviewer_error_rate"])
        for a in arms
    ]
    budget_check = check_matched_budgets(results, config["token_tolerance"])
    primary = [r for r in results if r.is_primary]
    null = next((r for r in results if r.is_null), None)
    report = {
        "harness": "a2_matched_budget_ablation",
        "harness_version": "0.1.0-draft",
        "node_id": "A2",
        "class_id": "GLOBAL",
        "gate": "G-AUDIT",
        "validation_status": "unverified",
        "assignment": "asg-2026-09-11-A2-deepseek-flash-20-29 (synthetic dry-run only, no model calls)",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "generator_sha256": hashlib.sha256(Path(__file__).resolve().read_bytes()).hexdigest(),
        "no_universal_scalar_score": True,
        "pre_registered_metrics": list(METRICS),
        "violates": "no metric is combined into a single score; each arm reports the same metric set",
        "config": config,
        "episodes": len(episodes),
        "classes": list(CLASSES),
        "arms": [arm_result_dict(r) for r in results],
        "budget_check": budget_check,
        "null_baseline": ({"arm": null.arm, "metrics": null.metrics} if null else None),
        "primary_comparison_valid": bool(budget_check["matched"] and len(primary) >= 4),
        "claims_not_made": [
            "no claim about real model behaviour: proposers are synthetic placeholders",
            "no swarm-advantage claim; the harness only makes such a claim checkable",
            "no A2 completion claim; this is a draft for lead-audit and G-AUDIT",
            "no universal scalar score is produced",
        ],
        "limitations": [
            ("token matching forces fewer, more expensive episodes for multi-sample arms, so "
             "between-arm rates are computed over different episode prefixes; episodes_attempted "
             "and per-class coverage are reported so the confound stays visible"),
            "synthetic model parameters are placeholders and carry no information about real models",
            ("the iid null arm exhausts the episode suite before its token budget, so its "
             "consumption is not token-matched; it is a control, never a primary arm"),
        ],
    }
    return report


def arm_result_dict(r: ArmResult) -> dict:
    d = {
        "arm": r.arm, "kind": r.kind, "is_primary": r.is_primary, "is_null": r.is_null,
        "token_budget": r.token_budget, "wall_budget": r.wall_budget,
        "tokens_consumed": r.tokens_consumed, "wall_consumed": round(r.wall_consumed, 4),
        "max_episode_cost": r.max_episode_cost, "stop_reason": r.stop_reason,
        "episodes_attempted": r.episodes_attempted, "calls": r.calls,
        "accepted": r.accepted, "rejected": r.rejected, "hard_failures": r.hard_failures,
        "claims_emitted": len(r.claims),
    }
    d.update(r.metrics)
    return d


def write_csv(results: list[ArmResult], path: Path) -> None:
    cols = (["arm", "kind", "is_primary", "is_null", "token_budget", "wall_budget",
             "tokens_consumed", "wall_consumed", "stop_reason", "episodes_attempted", "calls",
             "accepted", "rejected", "hard_failures", "claims_emitted"]
            + list(METRICS[:7]) + ["per_class_coverage"])
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in results:
            row = {"arm": r.arm, "kind": r.kind, "is_primary": r.is_primary, "is_null": r.is_null,
                   "token_budget": r.token_budget, "wall_budget": r.wall_budget,
                   "tokens_consumed": r.tokens_consumed, "wall_consumed": round(r.wall_consumed, 4),
                   "stop_reason": r.stop_reason, "episodes_attempted": r.episodes_attempted,
                   "calls": r.calls, "accepted": r.accepted, "rejected": r.rejected,
                   "hard_failures": r.hard_failures, "claims_emitted": len(r.claims)}
            row.update(r.metrics)
            row["per_class_coverage"] = json.dumps(r.metrics["per_class_coverage"], sort_keys=True)
            w.writerow(row)


# ---------------------------------------------------------------------------
# self-tests (including the unmatched-budget negative control)
# ---------------------------------------------------------------------------


def selftest(config: dict | None = None) -> dict:
    cfg = dict(DEFAULTS)
    cfg.update(config or {})
    checks = []

    def rec(name, ok, detail):
        checks.append({"name": name, "pass": bool(ok), "detail": detail})

    report = run_ablation(cfg)
    arms = {a["arm"]: a for a in report["arms"]}
    primary = [a for a in report["arms"] if a["is_primary"]]

    rec("end_to_end_synthetic_run", len(report["arms"]) == 5 and report["episodes"] == cfg["episodes"],
        f"arms={len(report['arms'])} episodes={report['episodes']}")
    rec("matched_budget_primary_arms", report["budget_check"]["matched"],
        f"violations={report['budget_check']['violations']}")
    rec("no_overspend",
        all(a["tokens_consumed"] <= a["token_budget"] + 1e-9
            and a["wall_consumed"] <= a["wall_budget"] + 1e-9 for a in report["arms"]),
        "all arms within both caps")
    rec("all_primary_token_limited",
        all(a["stop_reason"] == "token_budget" for a in primary),
        f"stop reasons={[a['stop_reason'] for a in primary]}")
    rec("metrics_present",
        all(m in a for a in report["arms"] for m in METRICS),
        f"{len(METRICS)} metrics per arm")
    rec("no_universal_scalar_score",
        report["no_universal_scalar_score"] and "score" not in report,
        "report has no combined score field")
    rec("null_baseline_is_control", report["null_baseline"] is not None
        and not any(a["is_null"] and a["is_primary"] for a in report["arms"]),
        "iid null exists and is not a primary arm")
    strong = arms["strong_single"]["accepted_claim_rate"]
    null = arms["random_iid_null"]["accepted_claim_rate"]
    rec("harness_discriminates_strong_from_null", strong > null,
        f"strong={strong:.3f} null={null:.3f}")

    # negative control: call-count matching must be rejected by the budget checker,
    # and specifically by the token-spread test (not only by an overspend)
    bad = run_ablation(cfg, budget_mode="calls")
    bad_viol = bad["budget_check"]["violations"]
    rec("unmatched_budget_control_rejected",
        not bad["budget_check"]["matched"] and any("spread" in v for v in bad_viol),
        f"violations={bad_viol[:2]}")

    # hard-failure separation: an always-failing proposer must not be counted as accepted
    fail_model = ModelSpec("fail", 100, 0.1, 0.9, failure_rate=1.0)
    fail_arm = ArmSpec("always_fails", "single", ("fail",), 1, False, 0, 0.0, True, False)
    eps = build_episodes(cfg["episodes"])
    fr = run_arm(fail_arm, eps, {"fail": fail_model}, token_budget=cfg["token_budget"],
                 wall_budget=cfg["wall_budget"], seed=cfg["seed"])
    rec("hard_failure_separation", fr.accepted == 0 and fr.hard_failures == fr.episodes_attempted
        and fr.metrics["cost_per_accepted_claim"] is None,
        f"accepted={fr.accepted} hard={fr.hard_failures} attempts={fr.episodes_attempted}")

    # wall-clock enforcement
    wall_cfg = dict(cfg); wall_cfg["wall_budget"] = 3.0
    wall_report = run_ablation(wall_cfg)
    rec("wall_clock_enforced",
        all(a["wall_consumed"] <= a["wall_budget"] + 1e-9 for a in wall_report["arms"])
        and any(a["stop_reason"] == "wall_clock" for a in wall_report["arms"]),
        f"stop reasons={[a['stop_reason'] for a in wall_report['arms']]}")

    # determinism of the numeric report
    r2 = run_ablation(cfg)
    key = lambda d: json.dumps({k: v for k, v in d.items() if k != "generated_at"}, sort_keys=True)
    rec("deterministic_report", key(report) == key(r2), "same seed -> identical numeric report")

    # no network client is imported anywhere in this file
    src = Path(__file__).resolve().read_text()
    forbidden = [f"import {m}" for m in ("requests", "urllib", "socket", "http.client")]
    rec("no_network_client", not any(tok in src for tok in forbidden),
        "no requests/urllib/socket/http.client import")

    # CSV round-trip
    tmp = ROOT / "evaluation" / "_selftest_ablation.csv"
    write_csv([ArmResult(**{k: v for k, v in {
        "arm": a["arm"], "kind": a["kind"], "is_primary": a["is_primary"], "is_null": a["is_null"],
        "token_budget": a["token_budget"], "wall_budget": a["wall_budget"],
        "tokens_consumed": a["tokens_consumed"], "wall_consumed": a["wall_consumed"],
        "max_episode_cost": a["max_episode_cost"], "stop_reason": a["stop_reason"],
        "episodes_attempted": a["episodes_attempted"], "calls": a["calls"],
        "accepted": a["accepted"], "rejected": a["rejected"],
        "hard_failures": a["hard_failures"], "metrics": {
            m: a[m] for m in METRICS},
    }.items()}) for a in report["arms"]], tmp)
    rows = list(csv.DictReader(tmp.open()))
    tmp.unlink()
    rec("csv_round_trip", len(rows) == len(report["arms"]) and "per_class_coverage" in rows[0],
        f"{len(rows)} rows")

    return {"pass": all(c["pass"] for c in checks), "checks": checks,
            "example_report": report}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true", help="synthetic end-to-end run (default)")
    ap.add_argument("--self-test", action="store_true", help="internal checks incl. negative controls")
    ap.add_argument("--design", default=None, help="optional design override (yaml/json)")
    ap.add_argument("--episodes", type=int, default=None)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--token-budget", type=float, default=None)
    ap.add_argument("--wall-budget", type=float, default=None)
    ap.add_argument("--json-out", default=None)
    ap.add_argument("--csv-out", default=None)
    a = ap.parse_args(argv)

    cfg = dict(DEFAULTS)
    cfg.update(load_design(Path(a.design) if a.design else None))
    for k, v in (("episodes", a.episodes), ("seed", a.seed),
                 ("token_budget", a.token_budget), ("wall_budget", a.wall_budget)):
        if v is not None:
            cfg[k] = v

    if a.self_test:
        st = selftest(cfg)
        for c in st["checks"]:
            print(f"  [{'ok' if c['pass'] else 'FAIL'}] {c['name']}: {c['detail']}")
        print(json.dumps({"selftest_pass": st["pass"]}, indent=2))
        return 0 if st["pass"] else 1

    report = run_ablation(cfg)
    if a.json_out:
        p = Path(a.json_out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(report, indent=2, sort_keys=True))
        print(f"wrote {p}")
    if a.csv_out:
        eps = build_episodes(cfg["episodes"])
        arms = synthetic_arms()
        models = synthetic_models()
        results = [run_arm(arm, eps, models, token_budget=cfg["token_budget"],
                           wall_budget=cfg["wall_budget"], seed=cfg["seed"],
                           reviewer_error_rate=cfg["reviewer_error_rate"]) for arm in arms]
        write_csv(results, Path(a.csv_out))
        print(f"wrote {a.csv_out}")
    print(json.dumps({"primary_comparison_valid": report["primary_comparison_valid"],
                      "budget_matched": report["budget_check"]["matched"],
                      "arms": {a["arm"]: {"accepted_claim_rate": round(a["accepted_claim_rate"], 3),
                                          "tokens": a["tokens_consumed"],
                                          "stop_reason": a["stop_reason"]}
                               for a in report["arms"]}}, indent=2))
    return 0 if report["primary_comparison_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
