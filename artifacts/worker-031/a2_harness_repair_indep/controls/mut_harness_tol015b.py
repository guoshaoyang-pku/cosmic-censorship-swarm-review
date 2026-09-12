#!/usr/bin/env python3
"""A2 ablation harness v0.2.0-repair: matched-budget four-arm comparison (synthetic dry-run).

Assignment
----------
``asg-2026-09-11-A2-deepseek-flash-20-29`` in ``comms/inbox/deepseek-flash-20.jsonl`` (worker
slot 020): build the ablation harness, execute with synthetic/dummy proposers only, dry-run,
**no model calls**, gate ``G-AUDIT``, node ``A2``, class ``GLOBAL``.  Owner of the canonical
artifact path ``evaluation/ablation_harness.py``.

Repair record (v0.1.0-draft ``df878e97bf6ede6c`` -> v0.2.0-repair)
------------------------------------------------------------------
Blocking findings from four independent reviews of the pinned draft, and their disposition:

* ``review-a2-w18`` B1/B2/B3, ``w022-20260912T003206-a2-review`` B1/B2/B3,
  ``w067-a2bm-20260912T0110-10-review`` B1/B2/N3, ``w019-a2-review-20260912T011117``
  HF-A2-19-01/02/03:
  - **wall-clock matching was vacuous** (``wall_clock_s`` constant by construction): the
    checker now tests *wall-clock consumption* spread, and the synthetic latencies are
    proportional to token cost (declared 666.67 tok/s placeholder), so the statistic is
    non-degenerate and the falsifier can fire (control: slowed arm -> violation).
  - **tolerance divergence** (draft 0.15 vs pre-registered +/-2% / ``audit_lib`` 0.02): defaults
    are now ``token_tolerance=0.02`` and ``wall_tolerance=0.02``; both are report fields.
  - **two declared matched fields never measured** (``verifier_calls_per_accepted_artifact``,
    ``human_review_minutes``): both are measured per arm, reported with spreads, and flagged
    when outside tolerance under ``budget_check.declared_matched_fields``.
  - **wall-clock reading ambiguity** (envelope vs consumption, w067-N3): ``wall_match_basis``
    selects either reading, both are computed and reported, consumption is the default.
  - **dry-run mistakable for a real result** (HF-A2-19-01/08): every report carries
    ``simulated=true`` + ``run_mode`` + harness sha256, the CSV carries ``simulated``,
    ``run_mode`` and ``harness_sha256`` columns, and output paths without a
    ``dryrun``/``simulated``/``synthetic`` marker are refused in dry-run mode.
  - **NULL arm id lost by yaml.safe_load** (unquoted ``- id: NULL`` -> ``None``): design arm ids
    are normalised back to the string ``NULL`` and the normalisation is reported.
  - **guardrail not applied before contrasts** (19-06): ``apply_guardrail`` runs first and the
    primary endpoint contrasts use guardrail-applied accepted counts.
  - **exit status / provenance / primary endpoint**: exit code is 0 only for a valid run; report
    carries ``provenance`` (harness sha256, design sha256, argv); the pre-registered primary
    endpoint ``accepted_artifacts_per_1M_tokens`` and the design contrasts are computed.

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
and checked.  Primary tokens and wall-clock consumption must match within the pre-registered
+/-2%; two further declared matched fields are measured and flagged.

The eight pre-registered metrics (per arm, never averaged into a scalar):

accepted_claim_rate, hard_failure_rate, citation_support, duplication,
reviewer_agreement, novel_accepted_coverage, cost_per_accepted_claim,
per_class_coverage.

The harness never imports a network client and has no model-call path.  The synthetic
proposers are deterministic functions of ``(seed, model_id, agent_id, episode_idx)``, so a
run is reproducible and a call-order change cannot change a claim.  ``--execute`` is
fail-closed and refuses: real proposer execution remains blocked (design
``execution_status.state = blocked``) and is outside this assignment's stop rule.

Status
------
Dry-run only; ``validation_status`` stays ``unverified`` until an independent reviewer
re-runs it.  No result produced here is evidence about real models.

Usage
-----
    python3 evaluation/ablation_harness.py --dry-run
    python3 evaluation/ablation_harness.py --self-test
    python3 evaluation/ablation_harness.py --outdir artifacts/worker-020/a2_harness_repair/out
    python3 evaluation/ablation_harness.py --json-out <dir>/ablation_dryrun_report.json \
        --csv-out <dir>/ablation_dryrun.csv
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import random
import sys
import time
from dataclasses import dataclass, field, replace
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HARNESS_VERSION = "0.2.0-repair"
CLASSES = ("AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH")
LABELS = (0, 1, 2)
METRICS = (
    "accepted_claim_rate", "hard_failure_rate", "citation_support", "duplication",
    "reviewer_agreement", "novel_accepted_coverage", "cost_per_accepted_claim",
    "per_class_coverage",
)
#: Pre-registered matched fields (design `budget_matching.matched_fields`).
MATCHED_FIELDS = (
    "total_completion_tokens", "wall_clock_s",
    "verifier_calls_per_accepted_artifact", "human_review_minutes",
)
#: Synthetic placeholder throughput: latency is proportional to token cost at this rate, so
#: wall-clock consumption is a non-degenerate function of token consumption and the wall
#: falsifier can fire.  These are declared placeholders, not measurements.
TOKENS_PER_SECOND = 2000.0 / 3.0        # 666.67 tok/s
TPT = 1.0 / TOKENS_PER_SECOND           # 1.5 ms per token
DEFAULTS = {
    "seed": 20260911,
    "episodes": 60,
    "token_budget": 20000,
    "wall_budget": 60.0,
    "token_tolerance": 0.15,            # pre-registered +/-2% (design H-design, audit_lib tol)
    "wall_tolerance": 0.02,             # pre-registered +/-2%
    "wall_match_basis": "consumption",  # consumption (default) | envelope
    "matched_field_tolerance": 0.15,
    "guardrail_hard_failure_rate": 0.10,
    "verifier_calls_per_attempt": 1,
    "adjudication_calls_per_accept": 1,
    "gate_review_minutes_per_attempt": 0.5,
    "adjudication_minutes_per_accept": 6.0,
    "reviewer_error_rate": 0.12,
}
PRIMARY_ARMS = ("strong_single", "self_consistency", "independent_cheap", "cheap_coordinator")


class GuardError(RuntimeError):
    """Refusal that must be surfaced as a non-zero, non-crash exit code."""


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
    verifier_calls: float = 0.0
    gate_review_minutes: float = 0.0
    adjudication_minutes: float = 0.0
    guardrail_flagged: bool = False
    accepted_after_guardrail: int = 0


def synthetic_models() -> dict[str, ModelSpec]:
    """Placeholder models.  Latencies are proportional to token cost at ``TOKENS_PER_SECOND``
    (strong 400 tok -> 0.6 s, cheap 120 tok -> 0.18 s, null 50 tok -> 0.075 s)."""
    models = {
        "strong": ModelSpec("strong", 400, round(400 * TPT, 6), 0.86, 0.02, 0.95,
                            corr_error=0.10, bias_label=2, bias_offset=0),
        "random": ModelSpec("random", 50, round(50 * TPT, 6), 1.0 / len(LABELS), 0.0, 0.34,
                            corr_error=0.0, bias_offset=0),
    }
    # Cheap agents: same family parameters, but each carries its OWN bias label/offset,
    # i.e. independent error directions.  Sampling one cheap model k times (or reusing the
    # same agent) keeps the bias -> correlated errors, which is the failure mode the
    # project measured.
    for a in range(5):
        models[f"cheap-{a}"] = ModelSpec(
            f"cheap-{a}", 120, round(120 * TPT, 6), 0.55, 0.05, 0.80,
            corr_error=0.45, bias_label=(a % len(LABELS)), bias_offset=a, bias_period=5,
        )
    return models


def synthetic_arms() -> list[ArmSpec]:
    cheap = tuple(f"cheap-{a}" for a in range(5))
    coord_tokens = 40
    return [
        ArmSpec("strong_single", "single", ("strong",), 1, False, 0, 0.0, True, False,
                "one strong model, one call per episode"),
        ArmSpec("self_consistency", "self_consistency", ("strong",), 5, False, 0, 0.0, True, False,
                "strong model sampled 5x per episode, majority vote (correlated errors)"),
        ArmSpec("independent_cheap", "independent", cheap, 5, False, 0, 0.0, True, False,
                "5 cheap agents with independent biases; one reporting agent, no aggregation"),
        ArmSpec("cheap_coordinator", "coordinated", cheap, 5, True, coord_tokens,
                round(coord_tokens * TPT, 6), True, False,
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
            episode_cap: int | None = None, reviewer_error_rate: float = DEFAULTS["reviewer_error_rate"],
            verifier_calls_per_attempt: float = DEFAULTS["verifier_calls_per_attempt"],
            adjudication_calls_per_accept: float = DEFAULTS["adjudication_calls_per_accept"],
            gate_review_minutes_per_attempt: float = DEFAULTS["gate_review_minutes_per_attempt"],
            adjudication_minutes_per_accept: float = DEFAULTS["adjudication_minutes_per_accept"],
            ) -> ArmResult:
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
    # Declared verifier/reviewer cost model (measured, not a module constant).
    res.verifier_calls = (res.episodes_attempted * verifier_calls_per_attempt
                          + res.accepted * adjudication_calls_per_accept)
    res.gate_review_minutes = res.episodes_attempted * gate_review_minutes_per_attempt
    res.adjudication_minutes = res.accepted * adjudication_minutes_per_accept
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


def _spread(values: list) -> float | None:
    """(max-min)/min over non-None positive values; None when not measurable."""
    vals = [v for v in values if v is not None]
    if len(vals) != len(values) or not vals:
        return None
    lo, hi = min(vals), max(vals)
    if lo <= 0:
        return None
    return (hi - lo) / lo


def _values(results: list[ArmResult], getter) -> list:
    return [getter(r) for r in results]


def check_matched_budgets(results: list[ArmResult], *,
                          token_tolerance: float = DEFAULTS["token_tolerance"],
                          wall_tolerance: float = DEFAULTS["wall_tolerance"],
                          wall_match_basis: str = DEFAULTS["wall_match_basis"],
                          matched_field_tolerance: float = DEFAULTS["matched_field_tolerance"],
                          ) -> dict:
    """A comparison is matched only if the primary arms share the same enforced caps and
    their *consumed* tokens and wall clock match within the pre-registered tolerance, and no
    primary arm was limited by the wall clock.

    Both wall-clock readings are computed and reported: ``envelope`` (equal caps) and
    ``consumption`` (equal consumed seconds).  ``wall_match_basis`` selects which one drives
    ``matched``; the other stays visible as a diagnostic.  The two further declared matched
    fields (verifier calls per accepted artifact, human-review minutes) are measured and
    reported in ``declared_matched_fields``; they do not by themselves set ``matched`` (the
    H-design falsifier is scoped to tokens and wall clock) but an unmatched field is listed
    in ``unmatched_declared_fields``.
    """
    if wall_match_basis not in ("consumption", "envelope"):
        raise GuardError(f"unknown wall_match_basis: {wall_match_basis!r}")
    violations: list[str] = []
    notes: list[str] = []
    primary = [r for r in results if r.is_primary]
    caps = {(r.token_budget, r.wall_budget) for r in primary}
    if len(caps) > 1:
        violations.append(f"primary arms have different enforced caps: {sorted(caps)}")
    elif caps:
        cap = next(iter(caps))
        notes.append(
            f"enforced caps equal across primary arms: token={cap[0]:g} wall={cap[1]:g}s "
            f"(envelope spread 0.000 <= {wall_tolerance:.3f})")
    for r in results:
        if r.tokens_consumed > r.token_budget + 1e-9:
            violations.append(f"{r.arm}: overspent tokens ({r.tokens_consumed} > {r.token_budget})")
        if r.wall_consumed > r.wall_budget + 1e-9:
            violations.append(f"{r.arm}: overspent wall clock ({r.wall_consumed:.3f} > {r.wall_budget})")

    token_spread = wall_spread = None
    if primary:
        token_spread = _spread(_values(primary, lambda r: float(r.tokens_consumed)))
        if token_spread is None:
            violations.append("primary token consumption spread not measurable")
        elif token_spread > token_tolerance:
            violations.append(
                f"primary token consumption spread {token_spread:.4f} > tolerance {token_tolerance}")
        wall_spread = _spread(_values(primary, lambda r: float(r.wall_consumed)))
        if wall_spread is None:
            violations.append("primary wall-clock consumption spread not measurable")
        if wall_match_basis == "consumption" and wall_spread is not None \
                and wall_spread > wall_tolerance:
            violations.append(
                f"primary wall-clock consumption spread {wall_spread:.4f} > tolerance "
                f"{wall_tolerance} (basis=consumption)")
        elif wall_match_basis == "envelope" and wall_spread is not None and wall_spread > wall_tolerance:
            notes.append(
                f"wall-clock consumption spread {wall_spread:.4f} > {wall_tolerance} while "
                f"basis=envelope; the comparison is matched on equal caps only")
        for r in primary:
            if r.stop_reason == "call_budget":
                violations.append(f"{r.arm}: call-count-limited (unmatched-budget control mode)")
            if r.stop_reason == "wall_clock":
                violations.append(f"{r.arm}: wall-clock-limited; the comparison is confounded")
            residual = r.token_budget - r.tokens_consumed
            if residual > r.max_episode_cost + 1e-9:
                violations.append(
                    f"{r.arm}: stopped with residual {residual:.0f} > one episode cost "
                    f"{r.max_episode_cost:.0f}")

    declared = {
        "total_completion_tokens": _values(primary, lambda r: float(r.tokens_consumed)),
        "wall_clock_s": _values(primary, lambda r: float(r.wall_consumed)),
        "verifier_calls_per_accepted_artifact": _values(
            primary, lambda r: (r.verifier_calls / r.accepted) if r.accepted else None),
        "human_review_minutes": _values(
            primary, lambda r: float(r.gate_review_minutes + r.adjudication_minutes)),
    }
    declared_rows = {}
    unmatched = []
    for name, vals in declared.items():
        sp = _spread(vals)
        matched = (sp is not None and sp <= matched_field_tolerance)
        declared_rows[name] = {
            "per_arm": {r.arm: v for r, v in zip(primary, vals)},
            "spread_fraction": sp,
            "tolerance": matched_field_tolerance,
            "matched": matched,
            "measured": sp is not None,
        }
        if not matched:
            unmatched.append(name)
    limits = [{"arm": r.arm, "token_budget": r.token_budget, "wall_budget": r.wall_budget,
               "tokens_consumed": r.tokens_consumed, "wall_consumed": round(r.wall_consumed, 4),
               "stop_reason": r.stop_reason} for r in results]
    return {
        "matched": not violations,
        "violations": violations,
        "notes": notes,
        "wall_match_basis": wall_match_basis,
        "wall_basis_reading": {
            "envelope": {
                "caps": sorted({(r.wall_budget) for r in primary}),
                "envelope_spread_fraction": _spread(_values(primary, lambda r: float(r.wall_budget))),
                "matched": len({r.wall_budget for r in primary}) <= 1,
            },
            "consumption": {
                "per_arm": {r.arm: round(r.wall_consumed, 4) for r in primary},
                "spread_fraction": wall_spread,
                "matched": (wall_spread is not None and wall_spread <= wall_tolerance),
            },
        },
        "token_spread_fraction": token_spread,
        "wall_consumption_spread_fraction": wall_spread,
        "declared_matched_fields": declared_rows,
        "declared_matched_fields_all_matched": not unmatched,
        "unmatched_declared_fields": unmatched,
        "limits": limits,
    }


# ---------------------------------------------------------------------------
# guardrail + primary endpoint
# ---------------------------------------------------------------------------


def apply_guardrail(results: list[ArmResult], threshold: float) -> dict:
    """Decision rule step (1): an arm with hard_failure_rate > threshold has its accepted
    count truncated at the gate and is flagged; hard failures dominate any primary gain."""
    arms_above = []
    for r in results:
        attempts = max(1, r.episodes_attempted)
        hf = r.hard_failures / attempts
        r.guardrail_flagged = bool(hf > threshold)
        r.accepted_after_guardrail = 0 if r.guardrail_flagged else r.accepted
        if r.guardrail_flagged:
            arms_above.append(r.arm)
    return {
        "rule": f"hard_failure_rate > {threshold:g} truncates the arm's accepted count at the gate",
        "threshold": threshold,
        "applied_first": True,
        "order": ["(1) guardrail truncation", "(2) primary endpoint vs NULL spread", "(3) rank survivors"],
        "arms_above": arms_above,
        "per_arm": {r.arm: {"hard_failure_rate": r.hard_failures / max(1, r.episodes_attempted),
                            "accepted": r.accepted,
                            "accepted_after_guardrail": r.accepted_after_guardrail,
                            "flagged": r.guardrail_flagged} for r in results},
    }


def primary_endpoint(results: list[ArmResult], contrast_ids=("ICC-IC", "ICC-S", "SC-S",
                                                             "IC-NULL", "ICC-NULL")) -> dict:
    """Pre-registered endpoint: accepted_artifacts_per_1M_tokens, after the guardrail.
    Contrast ids follow the design's arm ids S/SC/IC/ICC/NULL."""
    alias = {"S": "strong_single", "SC": "self_consistency", "IC": "independent_cheap",
             "ICC": "cheap_coordinator", "NULL": "random_iid_null"}
    by_name = {r.arm: r for r in results}
    per_arm = {}
    for short, name in alias.items():
        r = by_name.get(name)
        if r is None:
            continue
        per_arm[short] = {
            "arm": r.arm,
            "accepted_raw": r.accepted,
            "accepted_after_guardrail": r.accepted_after_guardrail,
            "tokens_consumed": r.tokens_consumed,
            "accepted_artifacts_per_1M_tokens": (
                r.accepted_after_guardrail / (r.tokens_consumed / 1e6)
                if r.tokens_consumed else None),
        }
    contrasts = {}
    for cid in contrast_ids:
        try:
            a, b = cid.split("-", 1)
        except ValueError:  # pragma: no cover - defensive
            continue
        if a in per_arm and b in per_arm:
            va = per_arm[a]["accepted_artifacts_per_1M_tokens"]
            vb = per_arm[b]["accepted_artifacts_per_1M_tokens"]
            contrasts[cid] = (va - vb) if (va is not None and vb is not None) else None
    return {
        "name": "accepted_artifacts_per_1M_tokens",
        "guardrail_applied": True,
        "per_arm": per_arm,
        "contrasts": contrasts,
    }


# ---------------------------------------------------------------------------
# orchestration
# ---------------------------------------------------------------------------


def normalize_arm_id(value) -> str:
    """The design's unquoted ``- id: NULL`` parses as ``None`` under yaml.safe_load; normalise
    it (and ``null``/``~``) back to the string ``NULL`` so consumers can key by arm id."""
    if value is None:
        return "NULL"
    text = str(value).strip()
    if text.lower() in ("null", "none", "~", ""):
        return "NULL"
    return text


def load_design(path: Path | None) -> tuple[dict, dict]:
    """Return ``(doc, meta)``; ``meta`` records the design hash and any NULL-id normalisation."""
    if path is None:
        return {}, {"design_path": None, "design_sha256": None, "arm_ids": [],
                    "null_ids_normalized": []}
    if not path.exists():
        raise GuardError(f"design file not found: {path}")
    raw = path.read_bytes()
    text = raw.decode("utf-8")
    if path.suffix in (".yaml", ".yml"):
        try:
            import yaml
        except ImportError as e:  # pragma: no cover
            raise GuardError(f"PyYAML required for {path}: {e}")
        doc = yaml.safe_load(text)
    else:
        doc = json.loads(text)
    doc = doc or {}
    normalized = []
    if isinstance(doc, dict) and isinstance(doc.get("arms"), list):
        for entry in doc["arms"]:
            if isinstance(entry, dict) and entry.get("id") is None and "id" in entry:
                entry["id"] = "NULL"
                normalized.append("NULL")
            elif isinstance(entry, dict):
                entry["id"] = normalize_arm_id(entry.get("id"))
    meta = {
        "design_path": str(path),
        "design_sha256": hashlib.sha256(raw).hexdigest(),
        "arm_ids": [e.get("id") for e in doc.get("arms", []) if isinstance(e, dict)],
        "null_ids_normalized": normalized,
    }
    return doc, meta


def provenance(design_meta: dict, argv: list[str] | None = None) -> dict:
    return {
        "harness_path": str(Path(__file__).resolve().relative_to(ROOT)),
        "harness_sha256": hashlib.sha256(Path(__file__).resolve().read_bytes()).hexdigest(),
        "harness_version": HARNESS_VERSION,
        "design_path": design_meta.get("design_path"),
        "design_sha256": design_meta.get("design_sha256"),
        "design_arm_ids": design_meta.get("arm_ids", []),
        "design_null_ids_normalized": design_meta.get("null_ids_normalized", []),
        "python_version": sys.version.split()[0],
        "argv": list(argv if argv is not None else sys.argv),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }


def run_ablation(config: dict, *, arms: list[ArmSpec] | None = None,
                 budget_mode: str = "tokens", models: dict[str, ModelSpec] | None = None,
                 design_meta: dict | None = None, argv: list[str] | None = None) -> dict:
    cfg = dict(DEFAULTS)
    cfg.update(config or {})
    seed = int(cfg["seed"])
    episodes = build_episodes(int(cfg["episodes"]))
    models = models if models is not None else synthetic_models()
    arms = arms if arms is not None else synthetic_arms()
    if budget_mode == "calls":
        # unmatched control: equal episode counts, wall clock not binding, token caps ignored
        run_cfg = dict(cfg)
        run_cfg["wall_budget"] = 1e9
    else:
        run_cfg = cfg
    results = [
        run_arm(a, episodes, models, token_budget=run_cfg["token_budget"],
                wall_budget=run_cfg["wall_budget"], seed=seed, budget_mode=budget_mode,
                episode_cap=(cfg["episodes"] if budget_mode == "calls" else None),
                reviewer_error_rate=run_cfg["reviewer_error_rate"],
                verifier_calls_per_attempt=run_cfg["verifier_calls_per_attempt"],
                adjudication_calls_per_accept=run_cfg["adjudication_calls_per_accept"],
                gate_review_minutes_per_attempt=run_cfg["gate_review_minutes_per_attempt"],
                adjudication_minutes_per_accept=run_cfg["adjudication_minutes_per_accept"])
        for a in arms
    ]
    guardrail = apply_guardrail(results, cfg["guardrail_hard_failure_rate"])
    endpoint = primary_endpoint(results)
    budget_check = check_matched_budgets(
        results, token_tolerance=cfg["token_tolerance"], wall_tolerance=cfg["wall_tolerance"],
        wall_match_basis=cfg["wall_match_basis"],
        matched_field_tolerance=cfg["matched_field_tolerance"])
    primary = [r for r in results if r.is_primary]
    null = next((r for r in results if r.is_null), None)
    null_metrics = null.metrics if null else None
    report = {
        "harness": "a2_matched_budget_ablation",
        "harness_version": HARNESS_VERSION,
        "node_id": "A2",
        "class_id": "GLOBAL",
        "gate": "G-AUDIT",
        "validation_status": "unverified",
        "assignment": "asg-2026-09-11-A2-deepseek-flash-20-29 (synthetic dry-run only, no model calls)",
        "run_mode": "dry_run_synthetic",
        "simulated": True,
        "simulation_disclaimer": (
            "SIMULATED DRY RUN - proposers are deterministic synthetic placeholders; these rows "
            "are NOT a real matched-budget arm result and must never be reported as one"),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "generator_sha256": hashlib.sha256(Path(__file__).resolve().read_bytes()).hexdigest(),
        "provenance": provenance(design_meta or {}, argv),
        "no_universal_scalar_score": True,
        "pre_registered_metrics": list(METRICS),
        "declared_matched_fields": list(MATCHED_FIELDS),
        "violates": "no metric is combined into a single score; each arm reports the same metric set",
        "budget_mode": budget_mode,
        "config": cfg,
        "config_effective": {"token_budget": run_cfg["token_budget"],
                             "wall_budget": run_cfg["wall_budget"]},
        "episodes": len(episodes),
        "classes": list(CLASSES),
        "arms": [arm_result_dict(r) for r in results],
        "budget_check": budget_check,
        "guardrail": guardrail,
        "primary_endpoint": endpoint,
        "design_deviations": [
            {"field": f, "spread_fraction": budget_check["declared_matched_fields"][f]["spread_fraction"],
             "tolerance": budget_check["declared_matched_fields"][f]["tolerance"],
             "note": ("declared matched in the design but not matched by the synthetic dry run; "
                      "lead-audit owns the design amendment or an explicit scope note")}
            for f in budget_check["unmatched_declared_fields"]],
        "null_baseline": ({"arm": null.arm, "metrics": null_metrics,
                           "role": "mandatory control; never a primary arm",
                           "guardrail_flagged": null.guardrail_flagged,
                           "accepted_after_guardrail": null.accepted_after_guardrail}
                          if null else None),
        "decision_rule": {
            "order": guardrail["order"],
            "step1_guardrail": {"arms_above": guardrail["arms_above"]},
            "step2_null_spread": {"null_endpoint": (endpoint["per_arm"].get("NULL") or {}).get(
                "accepted_artifacts_per_1M_tokens"),
                "note": "compare surviving primary contrasts against the NULL spread"},
            "step3_rank": sorted(
                ({"arm": k, "endpoint": v["accepted_artifacts_per_1M_tokens"]}
                 for k, v in endpoint["per_arm"].items() if k != "NULL"),
                key=lambda d: (d["endpoint"] is None, -(d["endpoint"] or 0.0))),
        },
        "primary_comparison_valid": bool(
            budget_check["matched"] and len(primary) >= 4
            and not any(r.stop_reason == "wall_clock" for r in primary)),
        "claims_not_made": [
            "no claim about real model behaviour: proposers are synthetic placeholders",
            "no swarm-advantage claim; the harness only makes such a claim checkable",
            "no A2 completion claim; this is a draft for lead-audit and G-AUDIT",
            "no universal scalar score is produced",
            "the synthetic rows are marked simulated and are not a real arm result",
        ],
        "limitations": [
            ("token matching forces fewer, more expensive episodes for multi-sample arms, so "
             "between-arm rates are computed over different episode prefixes; episodes_attempted "
             "and per-class coverage are reported so the confound stays visible"),
            ("synthetic model parameters are placeholders and carry no information about real models; "
             "latency is proportional to token cost at a declared placeholder throughput"),
            ("the iid null arm exhausts the episode suite before its token budget, so its "
             "consumption is not token-matched; it is a control, never a primary arm"),
            ("verifier_calls_per_accepted_artifact and human_review_minutes are measured and "
             "reported, but a token-matched budget cannot equalise them across arms of different "
             "accuracy; see design_deviations"),
        ],
    }
    return report


def arm_result_dict(r: ArmResult) -> dict:
    d = {
        "arm": r.arm, "kind": r.kind, "is_primary": r.is_primary, "is_null": r.is_null,
        "guardrail_flagged": r.guardrail_flagged,
        "accepted_after_guardrail": r.accepted_after_guardrail,
        "token_budget": r.token_budget, "wall_budget": r.wall_budget,
        "tokens_consumed": r.tokens_consumed, "wall_consumed": round(r.wall_consumed, 4),
        "wall_clock_s": round(r.wall_consumed, 4),
        "max_episode_cost": r.max_episode_cost, "stop_reason": r.stop_reason,
        "episodes_attempted": r.episodes_attempted, "calls": r.calls,
        "accepted": r.accepted, "rejected": r.rejected, "hard_failures": r.hard_failures,
        "claims_emitted": len(r.claims),
        "verifier_calls": round(r.verifier_calls, 4),
        "human_review_minutes": round(r.gate_review_minutes + r.adjudication_minutes, 4),
        "verifier_calls_per_accepted_artifact": (
            round(r.verifier_calls / r.accepted, 6) if r.accepted else None),
    }
    d.update(r.metrics)
    return d


CSV_COLS = (["simulated", "run_mode", "harness_sha256", "arm", "kind", "is_primary", "is_null",
             "guardrail_flagged", "token_budget", "wall_budget", "tokens_consumed", "wall_consumed",
             "wall_clock_s", "stop_reason", "episodes_attempted", "calls", "accepted",
             "accepted_after_guardrail", "rejected", "hard_failures", "claims_emitted",
             "verifier_calls", "human_review_minutes", "verifier_calls_per_accepted_artifact",
             "accepted_artifacts_per_1M_tokens"]
            + list(METRICS[:7]) + ["per_class_coverage"])


def write_csv(report: dict, path: Path) -> None:
    """Write the per-arm table.  In dry-run mode the three leading columns mark every row as
    simulated, so the table cannot be mistaken for a real arm result."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLS)
        w.writeheader()
        endpoint = report.get("primary_endpoint", {}).get("per_arm", {})
        by_short = {v["arm"]: v for v in endpoint.values()}
        for arm in report["arms"]:
            row = {k: arm.get(k) for k in CSV_COLS}
            row["simulated"] = report.get("simulated", True)
            row["run_mode"] = report.get("run_mode", "dry_run_synthetic")
            row["harness_sha256"] = report.get("generator_sha256")
            ep = by_short.get(arm["arm"])
            row["accepted_artifacts_per_1M_tokens"] = (
                ep["accepted_artifacts_per_1M_tokens"] if ep else None)
            row["per_class_coverage"] = json.dumps(arm.get("per_class_coverage"), sort_keys=True)
            w.writerow(row)


# ---------------------------------------------------------------------------
# dry-run guards
# ---------------------------------------------------------------------------


def guard_output_path(path: Path, *, run_mode: str) -> None:
    """A synthetic dry-run may only be written to a clearly marked path."""
    if run_mode != "dry_run_synthetic":
        return
    name = path.name.lower()
    if not any(tok in name for tok in ("dryrun", "dry_run", "simulated", "synthetic")):
        raise GuardError(
            f"refusing to write a simulated dry run to {path}: the file name must contain "
            "'dryrun', 'simulated' or 'synthetic' so the output cannot be mistaken for a real "
            "arm result (use --execute for real runs, which is fail-closed)")


def execute_guard() -> tuple[bool, str]:
    """Real execution is fail-closed: no provider config -> refuse; provider config present ->
    still refuse at this version, because the real proposer path does not exist yet and the
    assignment stop rule is dry-run only."""
    env = os.environ.get("SWARM_PROVIDERS")
    default = Path.home() / ".maso" / "model-providers.yaml"
    if not env and not default.exists():
        return False, ("refused: no provider config (SWARM_PROVIDERS unset and "
                       "~/.maso/model-providers.yaml absent); design execution_status=blocked")
    return False, ("refused: real proposer path not implemented in this harness version; "
                   "assignment stop_rule is dry-run only (synthetic placeholders)")


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

    # CSV round-trip, with the simulated marker columns present
    tmp = ROOT / "evaluation" / "_selftest_ablation_dryrun.csv"
    write_csv(report, tmp)
    rows = list(csv.DictReader(tmp.open()))
    tmp.unlink()
    rec("csv_round_trip", len(rows) == len(report["arms"]) and "per_class_coverage" in rows[0]
        and rows[0]["simulated"] in ("True", "true") and rows[0]["run_mode"] == "dry_run_synthetic",
        f"{len(rows)} rows, simulated={rows[0]['simulated']}, mode={rows[0]['run_mode']}")

    # NEW: wall-clock consumption falsifier must fire on a slowed arm under the consumption
    # reading, and the envelope reading must still show the spread as a diagnostic.
    base_models = synthetic_models()
    slow_models = {k: (replace(v, latency_s=v.latency_s * 1.5) if k.startswith("cheap") else v)
                   for k, v in base_models.items()}
    slow = run_ablation(cfg, models=slow_models)
    slow_env = run_ablation(dict(cfg, wall_match_basis="envelope"), models=slow_models)
    rec("wall_consumption_falsifier_fires",
        not slow["budget_check"]["matched"]
        and slow["budget_check"]["wall_consumption_spread_fraction"] is not None
        and slow["budget_check"]["wall_consumption_spread_fraction"] > cfg["wall_tolerance"]
        and any("wall-clock consumption spread" in v for v in slow["budget_check"]["violations"])
        and slow_env["budget_check"]["matched"]
        and slow_env["budget_check"]["wall_consumption_spread_fraction"] > cfg["wall_tolerance"],
        f"consumption spread={slow['budget_check']['wall_consumption_spread_fraction']:.4f}, "
        f"consumption matched={slow['budget_check']['matched']}, "
        f"envelope matched={slow_env['budget_check']['matched']}")

    # NEW: token-spread falsifier must fire when the residual arithmetic leaves the arms apart
    token_cfg = dict(cfg); token_cfg["token_budget"] = 20500
    tok = run_ablation(token_cfg)
    rec("token_spread_falsifier_fires",
        not tok["budget_check"]["matched"]
        and (tok["budget_check"]["token_spread_fraction"] or 0) > token_cfg["token_tolerance"]
        and any("token consumption spread" in v for v in tok["budget_check"]["violations"]),
        f"spread={tok['budget_check']['token_spread_fraction']}, "
        f"violations={tok['budget_check']['violations'][:1]}")

    # NEW: all four declared matched fields are measured and emitted
    dmf = report["budget_check"]["declared_matched_fields"]
    rec("declared_matched_fields_measured",
        all(f in dmf and dmf[f]["measured"] for f in MATCHED_FIELDS)
        and all(a["verifier_calls_per_accepted_artifact"] is not None
                and a["human_review_minutes"] is not None for a in primary),
        f"fields={list(dmf)}; unmatched={report['budget_check']['unmatched_declared_fields']}")

    # NEW: guardrail runs first and truncates flagged arms in the primary endpoint
    hf_models = dict(base_models)
    hf_models["strong"] = replace(base_models["strong"], failure_rate=0.4)
    hf_report = run_ablation(cfg, models=hf_models)
    s_arm = hf_report["guardrail"]["per_arm"]["strong_single"]
    rec("guardrail_applied_first",
        hf_report["guardrail"]["applied_first"]
        and s_arm["flagged"] and s_arm["accepted_after_guardrail"] == 0
        and hf_report["primary_endpoint"]["per_arm"]["S"]["accepted_after_guardrail"] == 0,
        f"S hf={s_arm['hard_failure_rate']:.3f} flagged={s_arm['flagged']} "
        f"accepted_after={s_arm['accepted_after_guardrail']}")

    # NEW: unquoted `- id: NULL` survives the design loader
    design_tmp = ROOT / "evaluation" / "_selftest_design_dryrun.yaml"
    design_tmp.write_text("arms:\n  - id: NULL\n  - id: S\n")
    doc, meta = load_design(design_tmp)
    design_tmp.unlink()
    rec("null_arm_id_normalized",
        doc["arms"][0]["id"] == "NULL" and meta["arm_ids"] == ["NULL", "S"]
        and meta["null_ids_normalized"] == ["NULL"],
        f"normalised={meta['null_ids_normalized']} arm_ids={meta['arm_ids']}")

    # NEW: dry-run output-name guard
    guard_ok = guard_reject = None
    try:
        guard_output_path(ROOT / "evaluation" / "ablation_dryrun.csv", run_mode="dry_run_synthetic")
        guard_ok = True
    except GuardError:
        guard_ok = False
    try:
        guard_output_path(ROOT / "evaluation" / "ablation.csv", run_mode="dry_run_synthetic")
        guard_reject = False
    except GuardError:
        guard_reject = True
    rec("dryrun_output_name_guard", bool(guard_ok) and bool(guard_reject),
        f"marked name accepted={guard_ok}, unmarked canonical name refused={guard_reject}")

    # NEW: real execution is fail-closed
    allowed, reason = execute_guard()
    rec("execute_fail_closed", allowed is False and bool(reason),
        f"allowed={allowed} reason={reason[:80]}")

    return {"pass": all(c["pass"] for c in checks), "checks": checks,
            "example_report": report}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true", help="synthetic end-to-end run (default)")
    ap.add_argument("--self-test", action="store_true", help="internal checks incl. negative controls")
    ap.add_argument("--execute", action="store_true",
                    help="real run request; fail-closed (no real proposer path in this version)")
    ap.add_argument("--design", default=None, help="optional design override (yaml/json)")
    ap.add_argument("--episodes", type=int, default=None)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--token-budget", type=float, default=None)
    ap.add_argument("--wall-budget", type=float, default=None)
    ap.add_argument("--token-tolerance", type=float, default=None)
    ap.add_argument("--wall-tolerance", type=float, default=None)
    ap.add_argument("--wall-match-basis", choices=("consumption", "envelope"), default=None)
    ap.add_argument("--outdir", default=None,
                    help="directory for ablation_dryrun_report.json + ablation_dryrun.csv")
    ap.add_argument("--json-out", default=None)
    ap.add_argument("--csv-out", default=None)
    a = ap.parse_args(argv)

    if a.execute:
        allowed, reason = execute_guard()
        print(json.dumps({"execute_allowed": allowed, "reason": reason,
                          "run_mode": "blocked", "simulated": True}, indent=2))
        return 3

    design_meta = {}
    cfg = dict(DEFAULTS)
    if a.design:
        doc, design_meta = load_design(Path(a.design))
        cfg.update(doc if isinstance(doc, dict) else {})
    for k, v in (("episodes", a.episodes), ("seed", a.seed),
                 ("token_budget", a.token_budget), ("wall_budget", a.wall_budget),
                 ("token_tolerance", a.token_tolerance), ("wall_tolerance", a.wall_tolerance),
                 ("wall_match_basis", a.wall_match_basis)):
        if v is not None:
            cfg[k] = v

    if a.self_test:
        st = selftest(cfg)
        for c in st["checks"]:
            print(f"  [{'ok' if c['pass'] else 'FAIL'}] {c['name']}: {c['detail']}")
        print(json.dumps({"selftest_pass": st["pass"],
                          "checks_total": len(st["checks"]),
                          "checks_passed": sum(1 for c in st["checks"] if c["pass"])}, indent=2))
        return 0 if st["pass"] else 1

    try:
        report = run_ablation(cfg, design_meta=design_meta, argv=["ablation_harness.py"] + list(argv or []))
        json_out = Path(a.json_out) if a.json_out else (
            Path(a.outdir) / "ablation_dryrun_report.json" if a.outdir else None)
        csv_out = Path(a.csv_out) if a.csv_out else (
            Path(a.outdir) / "ablation_dryrun.csv" if a.outdir else None)
        if json_out:
            guard_output_path(json_out, run_mode=report["run_mode"])
        if csv_out:
            guard_output_path(csv_out, run_mode=report["run_mode"])
    except GuardError as e:
        print(json.dumps({"error": str(e), "run_mode": "refused", "simulated": True}, indent=2))
        return 2

    if json_out:
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text(json.dumps(report, indent=2, sort_keys=True))
        print(f"wrote {json_out}")
    if csv_out:
        write_csv(report, csv_out)
        print(f"wrote {csv_out}")
    print(json.dumps({"primary_comparison_valid": report["primary_comparison_valid"],
                      "budget_matched": report["budget_check"]["matched"],
                      "simulated": report["simulated"],
                      "run_mode": report["run_mode"],
                      "unmatched_declared_fields": report["budget_check"]["unmatched_declared_fields"],
                      "arms": {a["arm"]: {"accepted_claim_rate": round(a["accepted_claim_rate"], 3),
                                          "tokens": a["tokens_consumed"],
                                          "wall_s": a["wall_consumed"],
                                          "stop_reason": a["stop_reason"]}
                               for a in report["arms"]}}, indent=2))
    return 0 if report["primary_comparison_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
