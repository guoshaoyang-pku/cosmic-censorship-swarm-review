#!/usr/bin/env python3
"""Mutation campaign that measures what the class-binding linter actually catches.

This is the falsification half of the artifact. It derives deterministic mutants
from the four ACCEPT fixtures and asserts that each mutation is caught. Every
mutant that still returns ACCEPT is an *escape*: the linter's sensitivity is
reported as (caught / attempted) per mutation family, not assumed.

Writes evidence/adversarial.json. Exit 0 always (the campaign reports; it does
not assert that the linter is good).
"""
from __future__ import annotations

import copy
import json
import random
from datetime import datetime, timezone
from pathlib import Path

import yaml

import check_schema

HERE = Path(__file__).resolve().parent
FIX = HERE / "fixtures"
EV = HERE / "evidence"
GOOD = sorted(FIX.glob("good_*.yaml"))

VAGUE_INJECT = ["suitable", "appropriate", "reasonable", "maybe", "roughly", "as needed"]

SCC_PHRASES = [
    "the maximal development is C^2-inextendible",
    "there is no extension of the maximal development",
    "the Cauchy horizon is non-degenerate",
]
WCC_PHRASES = [
    "no naked singularity is visible from future null infinity",
    "the singularity is not visible from I+",
    "observers at I+ see no singularity",
]


def required_keys(doc: dict) -> list[str]:
    cid = str(doc.get("class_id", ""))
    keys = ["quantifiers", "topology", "data_class", "matter", "genericity", "conclusion"]
    keys.append("i_plus" if cid.startswith("AF-WCC") else "inextendibility")
    return keys


def mutate(kind: str, doc: dict, rng: random.Random) -> str:
    """Apply one mutation in place; return a human-readable description."""
    if kind == "delete_required_top_key":
        k = rng.choice(required_keys(doc))
        doc.pop(k, None)
        return f"deleted top-level {k!r}"
    if kind == "inject_vague_term":
        term = rng.choice(VAGUE_INJECT)
        target = rng.choice(["quantifiers", "genericity", "conclusion"])
        if target == "quantifiers" and isinstance(doc.get("quantifiers"), dict):
            sub = rng.choice(list(doc["quantifiers"]))
            doc["quantifiers"][sub] = str(doc["quantifiers"][sub]) + f" ({term})"
        elif target == "conclusion" and isinstance(doc.get("conclusion"), dict):
            doc["conclusion"]["statement"] = str(doc["conclusion"].get("statement", "")) + f" ({term})"
        elif isinstance(doc.get("genericity"), dict):
            doc["genericity"]["kind"] = str(doc["genericity"].get("kind", "")) + f" ({term})"
        return f"injected vague term {term!r} into {target}"
    if kind == "swap_class_id":
        others = [c for c in sorted(check_schema.ALLOWED_CLASSES) if c != doc.get("class_id")]
        new = rng.choice(others)
        old = doc.get("class_id")
        doc["class_id"] = new
        return f"class_id {old} -> {new}"
    if kind == "conclusion_phrase_swap":
        stmt = doc.setdefault("conclusion", {}).get("statement", "")
        if str(doc.get("class_id", "")).startswith("AF-WCC"):
            doc["conclusion"]["statement"] = rng.choice(SCC_PHRASES)
            return f"WCC conclusion -> SCC phrase {doc['conclusion']['statement']!r}"
        doc["conclusion"]["statement"] = rng.choice(WCC_PHRASES)
        return f"SCC conclusion -> WCC phrase {doc['conclusion']['statement']!r} (was {stmt!r})"
    if kind == "corrupt_regularity":
        doc.setdefault("data_class", {})["regularity"] = "regular enough"
        return "data_class.regularity -> 'regular enough'"
    if kind == "drop_quantifier":
        q = doc.get("quantifiers")
        if isinstance(q, dict) and q:
            k = rng.choice(list(q))
            q.pop(k)
            return f"dropped quantifiers.{k}"
        return "no quantifiers to drop"
    if kind == "disjunction_inject":
        doc.setdefault("conclusion", {})["statement"] = "the maximal development is C^0 or C^2 inextendible"
        return "conclusion -> C0-or-C2 disjunction"
    raise ValueError(kind)


KINDS = [
    "delete_required_top_key",
    "inject_vague_term",
    "swap_class_id",
    "conclusion_phrase_swap",
    "corrupt_regularity",
    "drop_quantifier",
    "disjunction_inject",
]


def main() -> int:
    rng = random.Random(20260911)
    per_kind: dict[str, dict] = {k: {"attempted": 0, "caught": 0, "escapes": []} for k in KINDS}
    total = 0

    for _ in range(400):
        base_path = rng.choice(GOOD)
        kind = rng.choice(KINDS)
        doc = yaml.safe_load(base_path.read_text(encoding="utf-8"))
        before = copy.deepcopy(doc)
        desc = mutate(kind, doc, rng)
        res = check_schema.check(doc, f"<mutant:{base_path.name}>")
        per_kind[kind]["attempted"] += 1
        total += 1
        if res.verdict == "REJECT":
            per_kind[kind]["caught"] += 1
        else:
            per_kind[kind]["escapes"].append(
                {
                    "base": base_path.name,
                    "mutation": desc,
                    "class_id": res.class_id,
                    "before_class_id": before.get("class_id"),
                }
            )

    report = {
        "artifact": "f1_aux_class_binding",
        "campaign": "mutation-sensitivity",
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "seed": 20260911,
        "attempted": total,
        "caught": sum(v["caught"] for v in per_kind.values()),
        "per_kind": {
            k: {
                "attempted": v["attempted"],
                "caught": v["caught"],
                "detection_rate": round(v["caught"] / v["attempted"], 4) if v["attempted"] else None,
                "escapes": v["escapes"][:5],
            }
            for k, v in per_kind.items()
        },
    }
    EV.mkdir(exist_ok=True)
    (EV / "adversarial.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(f"mutation campaign: {report['caught']}/{report['attempted']} caught "
          f"({100.0 * report['caught'] / max(total, 1):.1f}%)")
    for k, v in report["per_kind"].items():
        print(f"  {k:26s} {v['caught']:3d}/{v['attempted']:3d}  rate={v['detection_rate']}  escapes={len(v['escapes'])}")
        for e in v["escapes"][:2]:
            print(f"      ESCAPE base={e['base']} :: {e['mutation']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
