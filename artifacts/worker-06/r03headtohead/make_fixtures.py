#!/usr/bin/env python3
"""Deterministic fixture generator for W006-R03-CAND-HEADTOHEAD-01.

Builds a fresh (unseen-by-either-candidate) binder-layout corpus on the LIVE FROZEN
rev29 canonical bytes, by single-target raw-text surgery on the canonical schemas.
Every non-copy fixture is asserted (parsed deep diff base -> mutant) to change exactly
the declared target path(s). Writes fixtures/ and fixture_manifest.json. Run once,
before preregistration; never re-run after scoring (the runner re-verifies hashes).
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
LIVE = {
    "c0": ROOT / "schemas" / "af_scc_c0_vacuum.yaml",
    "c2": ROOT / "schemas" / "af_scc_c2_vacuum.yaml",
    "wcc": ROOT / "schemas" / "af_wcc_vacuum.yaml",
}
CST = timezone(timedelta(hours=8))
FIX = HERE / "fixtures"

# ---------------------------------------------------------------- surgery helpers

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def replace_once(text: str, old: str, new: str, label: str) -> str:
    n = text.count(old)
    if n != 1:
        raise SystemExit(f"FATAL {label}: expected 1 occurrence of {old!r}, found {n}")
    return text.replace(old, new, 1)


def parsed(path_or_text, is_text=False):
    if is_text:
        return yaml.safe_load(path_or_text)
    return yaml.safe_load(Path(path_or_text).read_text())


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
    out = []
    for k in sorted(set(la) | set(lb)):
        if la.get(k, "<absent>") != lb.get(k, "<absent>"):
            out.append(k)
    return out


def mutate(base_key: str, repls: list[tuple[str, str]], targets: list[str], label: str):
    raw = LIVE[base_key].read_text(encoding="utf-8")
    for old, new in repls:
        raw = replace_once(raw, old, new, label)
    diff = leaf_diff(parsed(LIVE[base_key]), parsed(raw, is_text=True))
    if sorted(diff) != sorted(targets):
        raise SystemExit(f"FATAL {label}: parsed diff {diff} != declared targets {targets}")
    return raw


# ---------------------------------------------------------------- corpus definition
# Each entry: name, base, category, expected (accept|reject), scored, rationale,
# mutation description, raw replacements, declared target leaf paths.

CANON_FORMAL_TAIL = (
    "    not exists a proper future C0 metric extension (M',g',iota) of (M,g).\n"
)

FIXTURES = [
    # ---- positives: a correct repair must accept all of these -------------------
    dict(name="pos00_canonical_c0", base="c0", category="pos", expected="accept",
         scored=True, targets=[],
         rationale="Live canonical AF-SCC-C0-VAC-GEN is the class contract; any repair that "
                   "rejects it is invalid at these bytes (this is a control, not a mutant).",
         mutation="unmodified copy of schemas/af_scc_c0_vacuum.yaml"),
    dict(name="pos01_canonical_c2", base="c2", category="pos", expected="accept",
         scored=True, targets=[],
         rationale="Live canonical AF-SCC-C2-VAC-GEN control for the sibling class.",
         mutation="unmodified copy of schemas/af_scc_c2_vacuum.yaml"),
    dict(name="pos02_canonical_wcc", base="wcc", category="pos", expected="accept",
         scored=True, targets=[],
         rationale="Live canonical AF-WCC-VAC-GEN; frozen R03 rejects it because binder "
                   "'(q,t0)' is spelled 'q in I+ and t0 in [0,T)'. This is the false "
                   "positive that motivates both candidate repairs.",
         mutation="unmodified copy of schemas/af_wcc_vacuum.yaml"),
    dict(name="pos03_tuple_whitespace", base="c0", category="pos", expected="accept",
         scored=True, targets=["quantifiers.formal"],
         rationale="FORM-RULE-SPEC R03 requires formal to *use* the binders; whitespace "
                   "inside a displayed tuple is notation, not a different binding. Binder "
                   "(M',g',iota) is displayed as (M', g', iota).",
         mutation="formal: '(M',g',iota)' -> '(M', g', iota)'",
         repls=[("not exists a proper future C0 metric extension (M',g',iota) of (M,g).",
                 "not exists a proper future C0 metric extension (M', g', iota) of (M,g).")]),
    dict(name="pos04_expanded_coordinated", base="c0", category="pos", expected="accept",
         scored=True, targets=["quantifiers.formal"],
         rationale="Same three variables bound by one quantifier clause in an expanded "
                   "coordinated spelling; R03's 'using those binders' is satisfied.",
         mutation="formal: 'forall (Sigma,h,K) in G_r' -> 'forall Sigma in G_r and h in G_r and K in G_r'",
         repls=[("forall (Sigma,h,K) in G_r, letting",
                 "forall Sigma in G_r and h in G_r and K in G_r, letting")]),

    # ---- negatives: a correct repair must reject all of these --------------------
    dict(name="neg01_component_absent", base="c0", category="neg", expected="reject",
         scored=True, targets=["quantifiers.formal"],
         rationale="Binder (M',g',iota) declared but iota is genuinely absent from the "
                   "formal sentence: the fourth quantifier is unbound (R03 fail).",
         mutation="formal: '(M',g',iota)' -> '(M',g')'",
         repls=[("not exists a proper future C0 metric extension (M',g',iota) of (M,g).",
                 "not exists a proper future C0 metric extension (M',g') of (M,g).")]),
    dict(name="neg02_substring_only", base="c0", category="neg", expected="reject",
         scored=True, targets=["quantifiers.ordered[1].binder"],
         rationale="Binder changed to 'G', which occurs only as a substring of 'G_r' in "
                   "formal. Frozen substring testing accepts this unbound identifier; a "
                   "correct whole-identifier test rejects it.",
         mutation="binder[1]: 'G_r' -> 'G'",
         repls=[('{kind: exists, binder: "G_r", domain_id: D1}',
                 '{kind: exists, binder: "G", domain_id: D1}')]),
    dict(name="neg03_other_clause_only", base="c0", category="neg", expected="reject",
         scored=True, targets=["quantifiers.formal"],
         rationale="The triple (M',g',iota) is demoted to a trailing clause that does not "
                   "bind it as the extension quantifier; the negated-existential binder is "
                   "not used by the sentence.",
         mutation="formal tail rewritten so the triple appears in a non-binding trailing clause",
         repls=[(CANON_FORMAL_TAIL,
                 "    not exists a proper future C0 metric extension E of (M,g), and the triple\n"
                 "    (M',g',iota) is discussed in a separate remark.\n")]),
    dict(name="neg04_body_not_binder", base="c0", category="neg", expected="reject",
         scored=True, targets=["quantifiers.formal"],
         rationale="(Sigma,h,K) moved out of the quantifier's binder position into the "
                   "body introduced by 'letting'; the binder D is not used, so the "
                   "declared (Sigma,h,K) entry is unbound.",
         mutation="formal: binder position takes D; (Sigma,h,K) appears only after the comma",
         repls=[("forall (Sigma,h,K) in G_r, letting (M,g) be the maximal globally hyperbolic development:",
                 "forall D in G_r, letting (Sigma,h,K) be the data and (M,g) its maximal globally hyperbolic development:")]),
    dict(name="neg05_empty_tuple", base="c0", category="neg", expected="reject",
         scored=True, targets=["quantifiers.ordered[3].binder"],
         rationale="Binder '()' carries no identifier at all; nothing can be bound. A "
                   "component-wise split of '()' yields an empty list and must not "
                   "silently accept.",
         mutation="binder[3]: \"(M',g',iota)\" -> \"()\"",
         repls=[('{kind: not_exists, binder: "(M\',g\',iota)", domain_id: D3}',
                 '{kind: not_exists, binder: "()", domain_id: D3}')]),
    dict(name="neg06_case_mismatch", base="c0", category="neg", expected="reject",
         scored=True, targets=["quantifiers.ordered[0].binder"],
         rationale="Binder 'R' vs formal 'r': case is not binding. All three predicates "
                   "are case-sensitive, so this is a non-discriminative control.",
         mutation="binder[0]: 'r' -> 'R'",
         repls=[('{kind: forall, binder: "r", domain_id: D0}',
                 '{kind: forall, binder: "R", domain_id: D0}')]),

    # ---- edge probes: spec-legitimate, measure each candidate's declared residue --
    dict(name="probe01_comma_coordinated", base="c0", category="probe", expected="accept",
         scored=False, targets=["quantifiers.formal"],
         rationale="Spec-legitimate comma-coordinated binding 'M' in E, g' in Met, "
                   "iota in Emb' inside one clause. R03-v2 stops a binder head at a "
                   "top-level comma and is pre-declared to over-reject this shape; the "
                   "component-wise candidate is expected to accept.",
         mutation="formal tail: coordinated comma-separated binding of the three identifiers",
         repls=[(CANON_FORMAL_TAIL,
                 "    not exists M' in E, g' in Met, iota in Emb: a proper future C0 metric\n"
                 "    extension of (M,g).\n")]),
    dict(name="probe02_span_filler", base="c0", category="probe", expected="accept",
         scored=False, targets=["quantifiers.formal"],
         rationale="Spec-legitimate binding whose two identifiers sit ~120 chars apart in "
                   "one clause head with no top-level separator between them. R03-v2's "
                   "span=80 is pre-declared to over-reject this shape; the component-wise "
                   "candidate is expected to accept.",
         mutation="formal tail: same clause, filler with no top-level separators between M' and g'",
         repls=[(CANON_FORMAL_TAIL,
                 "    not exists M' in E and then one considers the extension problem for a\n"
                 "    sufficiently smooth background with several auxiliary structures fixed\n"
                 "    throughout the argument and g' in Met and iota in Emb: a proper future C0\n"
                 "    metric extension of (M,g).\n")]),
]

ORIGIN = {k: sha256_bytes(p.read_bytes()) for k, p in LIVE.items()}


def main():
    FIX.mkdir(parents=True, exist_ok=True)
    manifest_fixtures = []
    for f in FIXTURES:
        base_bytes = LIVE[f["base"]].read_bytes()
        if f.get("repls"):
            text = mutate(f["base"], f["repls"], f["targets"], f["name"])
            data = text.encode("utf-8")
        else:
            data = base_bytes
        p = FIX / f"{f['name']}.yaml"
        p.write_bytes(data)
        manifest_fixtures.append({
            "fixture": p.name,
            "base": f"schemas/{LIVE[f['base']].name}",
            "base_sha256": ORIGIN[f["base"]],
            "category": f["category"],
            "expected": f["expected"],
            "scored": f["scored"],
            "declared_target_paths": f["targets"],
            "mutation": f["mutation"],
            "rationale": f["rationale"],
            "sha256": sha256_bytes(data),
            "bytes": len(data),
        })
    manifest = {
        "corpus_id": "W006-R03-CAND-HEADTOHEAD-01",
        "created_at": datetime.now(CST).isoformat(timespec="seconds"),
        "worker": "worker-006",
        "node_id": "A1",
        "gate": "G-CLASSBIND",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "bases": {f"schemas/{LIVE[k].name}": v for k, v in ORIGIN.items()},
        "fixtures": manifest_fixtures,
        "provenance": {
            "generator": "artifacts/worker-06/r03headtohead/make_fixtures.py",
            "out_of_sample": "This corpus was written after both candidate repairs were "
                             "published (R03-v2 01:06, worker-004 patch 00:51) and reuses "
                             "no fixture from either author's calibration set.",
        },
    }
    (HERE / "fixture_manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    counts = {}
    for m in manifest_fixtures:
        counts[m["category"]] = counts.get(m["category"], 0) + 1
    print(json.dumps({"written": len(manifest_fixtures), "counts": counts,
                      "manifest_sha256": sha256_bytes((HERE / "fixture_manifest.json").read_bytes())},
                     indent=1))


if __name__ == "__main__":
    main()
