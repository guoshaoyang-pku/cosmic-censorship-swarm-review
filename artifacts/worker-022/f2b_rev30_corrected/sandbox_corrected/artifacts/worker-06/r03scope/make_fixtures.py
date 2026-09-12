#!/usr/bin/env python3
"""Deterministic scope-safety corpus generator for W006-R03-SCOPE-01.

Question: the formulation lead's lifecycle-08 probe showed the variable-wise R03 patch
(cand_E3) accepts a negation-scope-error rendering. Does any published candidate separate
correct composite-binder renderings from scope-erroneous ones?

This generator builds a FRESH corpus (no fixture reused from the head-to-head or from
either author's calibration set) by single-target raw-text surgery on the live canonical
AF-WCC-VAC-GEN `quantifiers.formal` folded scalar. Every non-control fixture is asserted
(parsed deep diff base -> mutant) to change exactly that one leaf. Writes fixtures/ and
fixture_manifest.json. Run ONCE, before preregistration; never re-run after scoring
(the runner re-verifies fixture bytes against the preregistered manifest hash).
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
FIX = HERE / "fixtures"
CST = timezone(timedelta(hours=8))
WCC = ROOT / "schemas" / "af_wcc_vacuum.yaml"

# The exact raw last line of the canonical `quantifiers.formal` folded scalar.
RAW_TAIL = ("    not exists q in I+ and t0 in [0,T) with "
            "gamma([t0,T)) subset J^-(q) intersect M.")

# name -> (category, scored, expected per candidate, tail raw text, rationale)
# expected: accept|reject per the DECLARED semantics of each tool, fixed before scoring.
#   frozen    literal `(q,t0)` substring of quantifiers.formal
#   cand_r03v2  binder-head co-binding: one quantifier clause head contains q then t0,
#               each within span=80 of the previous identifier
#   cand_004    every alphanumeric component of the binder occurs in formal as a whole word
#   cand_E3     literal binder, else all comma-separated components occur as substrings
FIXTURES = [
    dict(name="ctrl_canonical_wcc", category="control", scored=False,
         expected={"frozen": "reject", "cand_r03v2": "accept",
                   "cand_004": "accept", "cand_E3": "accept"},
         tail=None,
         rationale="Live canonical AF-WCC-VAC-GEN is the class contract. The frozen literal "
                   "R03 rejects it (known false positive); every repair must accept it. "
                   "Not scored: it is a control, not a mutant."),

    # ---- positives: a scope-safe repair must accept all of these -----------------
    dict(name="pos_grouped_tuple", category="pos", scored=True,
         expected={"frozen": "accept", "cand_r03v2": "accept",
                   "cand_004": "accept", "cand_E3": "accept"},
         tail="    not exists (q,t0) in D5 with "
              "gamma([t0,T)) subset J^-(q) intersect M.",
         rationale="Canonical binder rendered as its literal grouped tuple; the reference "
                   "legal rendering."),
    dict(name="pos_grouped_tuple_space", category="pos", scored=True,
         expected={"frozen": "reject", "cand_r03v2": "accept",
                   "cand_004": "accept", "cand_E3": "accept"},
         tail="    not exists (q, t0) in D5 with "
              "gamma([t0,T)) subset J^-(q) intersect M.",
         rationale="Legal grouped tuple with one space after the comma. The frozen literal "
                   "test misses the exact token and is a declared FP; any variable-wise "
                   "repair must accept it."),
    dict(name="pos_variablewise_double_space", category="pos", scored=True,
         expected={"frozen": "reject", "cand_r03v2": "accept",
                   "cand_004": "accept", "cand_E3": "accept"},
         tail="    not exists q in I+  and  t0 in [0,T) with "
              "gamma([t0,T)) subset J^-(q) intersect M.",
         rationale="The frozen rendering with doubled spaces around the coordination; parsed "
                   "formal binds both variables before the body. Legitimate; frozen literal "
                   "test FP."),
    dict(name="pos_such_that_grouped", category="pos", scored=True,
         expected={"frozen": "accept", "cand_r03v2": "accept",
                   "cand_004": "accept", "cand_E3": "accept"},
         tail="    not exists (q,t0) in D5 such that "
              "gamma([t0,T)) subset J^-(q) intersect M.",
         rationale="Grouped tuple followed by `such that` rather than `with`; tests that the "
                   "binder-head scanner stops at a different body marker. Legitimate."),
    dict(name="pos_filler_also", category="pos", scored=True,
         expected={"frozen": "reject", "cand_r03v2": "accept",
                   "cand_004": "accept", "cand_E3": "accept"},
         tail="    not exists q in I+ and also t0 in [0,T) with "
              "gamma([t0,T)) subset J^-(q) intersect M.",
         rationale="Coordinated binder with a filler adverb, both variables still introduced "
                   "before the body. Legitimate; frozen literal test FP."),
    dict(name="pos_wide_whitespace", category="pos", scored=True,
         expected={"frozen": "reject", "cand_r03v2": "accept",
                   "cand_004": "accept", "cand_E3": "accept"},
         tail="    not exists   q   in   I+   and   t0   in   [0,T)   with "
              "gamma([t0,T)) subset J^-(q) intersect M.",
         rationale="Same binding, whitespace-expanded; identifiers stay well inside span=80. "
                   "Legitimate; frozen literal test FP."),

    # ---- negatives: scope / binding-scope errors, must be rejected ---------------
    dict(name="neg_scope_after_body_and", category="neg", scored=True,
         expected={"frozen": "reject", "cand_r03v2": "reject",
                   "cand_004": "accept", "cand_E3": "accept"},
         tail="    not exists q in I+ with gamma([t0,T)) subset J^-(q) intersect M, "
              "and t0 in [0,T).",
         rationale="SCOPE ERROR: the negation binds q only; t0 is conjoined after the body. "
                   "This is the formulation lead's lifecycle-08 scope-error variant, "
                   "independently re-derived here."),
    dict(name="neg_scope_after_body_paren", category="neg", scored=True,
         expected={"frozen": "reject", "cand_r03v2": "reject",
                   "cand_004": "accept", "cand_E3": "accept"},
         tail="    not exists q in I+ with gamma([t0,T)) subset J^-(q) intersect M "
              "(and t0 in [0,T)).",
         rationale="SCOPE ERROR, parenthesised form: t0 is outside the negation, inside a "
                   "trailing parenthetical."),
    dict(name="neg_literal_tuple_elsewhere", category="neg", scored=True,
         expected={"frozen": "accept", "cand_r03v2": "reject",
                   "cand_004": "accept", "cand_E3": "accept"},
         tail="    not exists q in I+ with gamma([t0,T)) subset J^-(q) intersect M, "
              "and (q,t0) in D5.",
         rationale="SCOPE ERROR with the literal tuple present but non-binding: the exact "
                   "token `(q,t0)` appears in a trailing clause after the body, while the "
                   "negation still binds only q. Frozen R03 has a scope FALSE NEGATIVE here."),
    dict(name="neg_reversed_binding", category="neg", scored=True,
         expected={"frozen": "reject", "cand_r03v2": "reject",
                   "cand_004": "accept", "cand_E3": "accept"},
         tail="    not exists t0 in [0,T) with gamma([t0,T)) subset J^-(q) intersect M, "
              "and q in I+.",
         rationale="SCOPE/ORDER ERROR: the negated quantifier binds t0 only and q is conjoined "
                   "after the body, in reverse of the declared binder order (q,t0)."),
    dict(name="neg_ids_in_consequent", category="neg", scored=True,
         expected={"frozen": "reject", "cand_r03v2": "reject",
                   "cand_004": "accept", "cand_E3": "accept"},
         tail="    not exists q in I+ with (gamma([t0,T)) subset J^-(q) intersect M "
              "implies t0 in [0,T)).",
         rationale="SCOPE ERROR: t0 is bound in the consequent of an implication inside the "
                   "body, not by the negated quantifier."),
    dict(name="neg_ids_in_earlier_quantifier", category="neg", scored=True,
         expected={"frozen": "reject", "cand_r03v2": "reject",
                   "cand_004": "accept", "cand_E3": "accept"},
         tail="    forall t0 in [0,T): not exists q in I+ with "
              "gamma([t0,T)) subset J^-(q) intersect M.",
         rationale="SCOPE ERROR: t0 is bound by an earlier forall clause; the declared "
                   "composite binder (q,t0) of the `not_exists` entry is never formed."),
    dict(name="neg_ids_in_body_letting", category="neg", scored=True,
         expected={"frozen": "accept", "cand_r03v2": "reject",
                   "cand_004": "accept", "cand_E3": "accept"},
         tail="    not exists q in I+ with letting (q,t0) in D5: "
              "gamma([t0,T)) subset J^-(q) intersect M.",
         rationale="SCOPE ERROR: the tuple is introduced by a `letting` inside the body; the "
                   "literal token is present but is not the binder of the negated quantifier. "
                   "Frozen R03 scope FALSE NEGATIVE."),
    dict(name="neg_substring_only", category="neg", scored=True,
         expected={"frozen": "reject", "cand_r03v2": "reject",
                   "cand_004": "reject", "cand_E3": "accept"},
         tail="    not exists q_0 in I+ and t0_0 in [0,T) with "
              "gamma([t0,T)) subset J^-(q_0) intersect M.",
         rationale="BINDING-SCOPE ERROR: only longer identifiers q_0/t0_0 are bound, so the "
                   "declared binders q,t0 are not introduced at all. Substring-only matching "
                   "(cand_E3) accepts."),

    # ---- edge probes: interpretation-dependent, declared but NOT scored ----------
    dict(name="edge_comma_coordinated", category="edge", scored=False,
         expected={"frozen": "reject", "cand_r03v2": "reject",
                   "cand_004": "accept", "cand_E3": "accept"},
         tail="    not exists q in I+, t0 in [0,T) with "
              "gamma([t0,T)) subset J^-(q) intersect M.",
         rationale="Comma-coordinated coordinated binder before the body. Interpretation-"
                   "dependent (R03-v2's declared over-reject residue; the lead's A-prime "
                   "grouping requirement would also reject it). Not scored."),
    dict(name="edge_long_span", category="edge", scored=False,
         expected={"frozen": "reject", "cand_r03v2": "reject",
                   "cand_004": "accept", "cand_E3": "accept"},
         tail="    not exists q in I+ and " + ("coordinated " * 12) +
              "and t0 in [0,T) with gamma([t0,T)) subset J^-(q) intersect M.",
         rationale="Both identifiers in one binder phrase but ~140 chars apart; R03-v2's "
                   "declared span=80 over-reject residue. Not scored."),
    dict(name="edge_split_quantifiers", category="edge", scored=False,
         expected={"frozen": "reject", "cand_r03v2": "reject",
                   "cand_004": "accept", "cand_E3": "accept"},
         tail="    not exists q in I+ such that not exists t0 in [0,T) with "
              "gamma([t0,T)) subset J^-(q) intersect M.",
         rationale="Composite binding spelled as two nested same-kind quantifiers. Whether "
                   "that 'uses the binders' is interpretation-dependent. Not scored."),
    dict(name="edge_braces_group", category="edge", scored=False,
         expected={"frozen": "reject", "cand_r03v2": "reject",
                   "cand_004": "accept", "cand_E3": "accept"},
         tail="    not exists {q,t0} in D5 with "
              "gamma([t0,T)) subset J^-(q) intersect M.",
         rationale="Grouped binding in braces rather than parentheses; notation outside the "
                   "canonical spelling. Not scored."),
]


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def parsed(text_or_path, is_text: bool = False):
    if is_text:
        return yaml.safe_load(text_or_path)
    return yaml.safe_load(Path(text_or_path).read_text())


def walk(x, prefix=""):
    if isinstance(x, dict):
        for k, v in x.items():
            yield from walk(v, f"{prefix}.{k}" if prefix else str(k))
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from walk(v, f"{prefix}[{i}]")
    else:
        yield prefix, x


def leaf_diff(a, b):
    la, lb = dict(walk(a)), dict(walk(b))
    return sorted(k for k in set(la) | set(lb) if la.get(k, "<absent>") != lb.get(k, "<absent>"))


def main() -> int:
    FIX.mkdir(parents=True, exist_ok=True)
    raw_base = WCC.read_text(encoding="utf-8")
    if raw_base.count(RAW_TAIL) != 1:
        raise SystemExit(f"FATAL: canonical tail occurs {raw_base.count(RAW_TAIL)} times")
    manifest = {
        "corpus_id": "W006-R03-SCOPE-01",
        "created_at": datetime.now(CST).isoformat(timespec="seconds"),
        "worker": "worker-006",
        "node_id": "A1",
        "gate": "G-CLASSBIND",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "base": {"schemas/af_wcc_vacuum.yaml": sha256_bytes(raw_base.encode("utf-8"))},
        "target_leaf": "quantifiers.formal",
        "fixtures": [],
    }
    base_parsed = parsed(WCC)
    for spec in FIXTURES:
        name = spec["name"]
        if spec["tail"] is None:
            raw = raw_base
            diff = []
            mutation = "unmodified copy of schemas/af_wcc_vacuum.yaml"
        else:
            raw = raw_base.replace(RAW_TAIL, spec["tail"], 1)
            diff = leaf_diff(base_parsed, parsed(raw, is_text=True))
            if diff != ["quantifiers.formal"]:
                raise SystemExit(f"FATAL {name}: parsed diff {diff} != ['quantifiers.formal']")
            mutation = f"replace quantifiers.formal last clause with: {spec['tail']!r}"
        path = FIX / f"{name}.yaml"
        path.write_text(raw, encoding="utf-8")
        # re-parse from disk (what the tools will read)
        parsed_on_disk = parsed(path)
        if spec["tail"] is None:
            assert leaf_diff(base_parsed, parsed_on_disk) == []
        else:
            assert leaf_diff(base_parsed, parsed_on_disk) == ["quantifiers.formal"]
        manifest["fixtures"].append({
            "fixture": path.name,
            "base": "schemas/af_wcc_vacuum.yaml",
            "base_sha256": manifest["base"]["schemas/af_wcc_vacuum.yaml"],
            "category": spec["category"],
            "scored": spec["scored"],
            "expected": spec["expected"],
            "declared_target_paths": diff,
            "mutation": mutation,
            "rationale": spec["rationale"],
            "sha256": sha256_bytes(path.read_bytes()),
            "bytes": len(path.read_bytes()),
        })
    (HERE / "fixture_manifest.json").write_text(
        json.dumps(manifest, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "fixtures": len(manifest["fixtures"]),
        "scored_pos": sum(1 for f in manifest["fixtures"] if f["scored"] and f["category"] == "pos"),
        "scored_neg": sum(1 for f in manifest["fixtures"] if f["scored"] and f["category"] == "neg"),
        "edges": sum(1 for f in manifest["fixtures"] if f["category"] == "edge"),
        "controls": sum(1 for f in manifest["fixtures"] if f["category"] == "control"),
        "manifest_sha256": sha256_bytes((HERE / "fixture_manifest.json").read_bytes()),
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
