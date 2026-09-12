#!/usr/bin/env python3
"""F0 class-bound consistency check: the H2_loc implication rows.

Class-bound task (worker=001, 2026-09-12):
  class_id  : AF-SCC-C0-VAC-GEN   (parent class; H2LOC is its registered variant)
  node_id   : F0 (declared taxonomy) / F2b (C0 schema)
  gate      : G-F0 / G-FORM
  question  : is the H2_loc -> C0 row of the authoring supplement's
              implication_ledger consistent with the frozen containment chain?

Direction convention (the point this checker exists to pin down)
---------------------------------------------------------------
The artifacts nest the extension sets

    E_C2 subset E_{C^1,1} subset E_H2loc subset E_C0

so the LOWER the required regularity, the LARGER the extension set, and the
STRONGER the non-existence statement:
C0-inextendibility entails H2_loc-inextendibility entails C2-inextendibility.
Equivalently S_A entails S_B iff size(E_A) >= size(E_B), where S_A is
"no proper future extension in class A exists".

Therefore `H2_loc inextendibility -> AF-SCC-C0-VAC-GEN` is correctly recorded
as does_not_entail/forbidden: H2_loc is the stronger extension class (fewer
extensions) so its non-existence statement is the WEAKER one.

This script verifies, at hash-pinned bytes:
  A. the containment pairs derivable from the declared chain text agree with
     the ordering above (and their transitive closure contains every adjacent
     pair of the chain);
  B. every shared-axis row of the supplement ledger matches the expected
     entailment direction;
  C. the C0 and C2 frozen schemas' own one_way_entailments and
     forbidden_transfers match the same expectation;
  D. no pair is both transitively entailed and explicitly declared
     does_not_entail (an order-independent contradiction check).

Read-only over frozen artifacts.  Exit 0 = check completed (verdict in report);
exit 3 = missing input or declared-hash drift (fail-closed, no verdict).
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]  # ai4math-swarm/
CST = timezone(timedelta(hours=8))
OUT = Path(__file__).resolve().parent

# Hash-pinned inputs.  If a file changes, fail closed rather than silently
# re-interpret a moving target (protocol: bind to sha256, never the path alone).
PINNED = {
    "research_map/formulation_taxonomy.yaml":
        "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "artifacts/formulation/formulation_taxonomy.yaml":
        "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
    "schemas/af_scc_c0_vacuum.yaml":
        "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6",
    "schemas/af_scc_c2_vacuum.yaml":
        "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce",
}

# Extension-set size, largest first.  index 0 = weakest statement.
SIZE = {"C0": 0, "H2loc": 1, "C11": 2, "C2": 3}
# Equation-strength axis, largest extension set first (bare metric = largest).
EQ_SIZE = {"bare": 0, "distC0": 1, "classical": 2}
ADJACENT = [("C2", "C11"), ("C11", "H2loc"), ("H2loc", "C0")]


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def norm_class(s: str) -> str | None:
    """Map an endpoint phrase to a shared-axis token."""
    t = s.lower()
    if "distributional" in t:
        return "distC0"
    if re.search(r"\bbare\b", t):
        return "bare"
    if "h2" in t or "square-integrable" in t or "square integrable" in t:
        return "H2loc"
    if re.search(r"c\^?\{?1\s*,\s*1\}?", t):
        return "C11"
    if re.search(r"\bc2\b", t):
        return "C2"
    if re.search(r"\bc0\b", t):
        return "C0"
    return None


def axis(tok: str) -> str:
    return "equation" if tok in EQ_SIZE else "regularity"


def entails_expected(a: str, b: str) -> bool | None:
    """S_a entails S_b iff a's extension set is at least as large as b's."""
    if axis(a) != axis(b):
        return None
    order = EQ_SIZE if axis(a) == "equation" else SIZE
    return order[a] <= order[b]


def derive_subset_pairs(text: str) -> set[tuple[str, str]]:
    """Return {(A, B)} for each *consecutive* link of every containment chain,
    oriented as E_A subset E_B.

    'E_C2 subset E_C11 subset E_H2loc' must yield (C2,C11) and (C11,H2loc),
    not (C2,H2loc): the latter is a consequence, not a declared adjacency, and
    emitting it would hide a missing middle link.
    """
    pairs: set[tuple[str, str]] = set()
    flat = text.replace("\u2282", " subset ").replace("\u2286", " subset ")
    flat = re.sub(r"E_\{([^}]*)\}", r"E_\1", flat)
    tok = r"E_([A-Za-z0-9^{},]+)"
    for m in re.finditer(rf"{tok}((?:\s*(?:subset of|subset|contains)\s*{tok})+)", flat):
        prev = norm_class(m.group(1))
        if prev is None:
            continue
        for rel, nxt in re.findall(rf"(subset of|subset|contains)\s*{tok}", m.group(2)):
            cur = norm_class(nxt)
            if cur is None or cur == prev:
                continue
            # 'contains' reverses the edge direction: E_cur subset E_prev
            pairs.add((cur, prev) if rel == "contains" else (prev, cur))
            prev = cur
    return pairs


def closure(pairs: set[tuple[str, str]]) -> set[tuple[str, str]]:
    out = set(pairs)
    changed = True
    while changed:
        changed = False
        for (x, y) in list(out):
            for (y2, z) in list(out):
                if y == y2 and x != z and (x, z) not in out:
                    out.add((x, z))
                    changed = True
    return out


def check_rows(nodes: list[dict], source: str, this_class: str | None = None) -> list[dict]:
    """declared relation vs expectation for a list of {from,to,relation,...}."""
    def tok(s: str) -> str | None:
        if this_class and str(s).strip().lower() in {"this class", "this"}:
            return this_class
        return norm_class(str(s))

    rows = []
    for i, e in enumerate(nodes):
        a = tok(e.get("from", ""))
        b = tok(e.get("to", ""))
        if a is None or b is None or axis(a) != axis(b):
            rows.append({"index": i, "source": source, "from": e.get("from"),
                         "to": e.get("to"), "checked": False,
                         "why": ("endpoint not a shared-axis token: "
                                 f"{e.get('from')!r} -> {e.get('to')!r}")})
            continue
        exp = entails_expected(a, b)
        declared = e.get("relation", "entails" if "reason" in e else None)
        rows.append({
            "index": i, "source": source, "checked": True,
            "from_token": a, "to_token": b, "axis": axis(a),
            "declared_relation": declared,
            "expects": "entails" if exp else "does_not_entail",
            "consistent": (declared == "entails") == exp,
            "declared_reason": e.get("reason") or e.get("status"),
        })
    return rows


def detector_selftest(ledgers: dict[str, list[dict]]) -> list[dict]:
    """Seed known inversions into copies of the live rows and confirm each is
    caught.  A checker that cannot fail on a seeded defect proves nothing."""
    cases = []

    def run(nodes, src):
        rows = check_rows(nodes, src)
        return any(r["checked"] and not r["consistent"] for r in rows)

    phrase = {"H2loc": "no proper future H2_loc extension",
              "C0": "no proper future C0 extension",
              "C2": "no proper future C2 extension",
              "C11": "no proper future C^1,1 extension"}
    pool = [dict(e) for src_rows in ledgers.values() for e in src_rows]

    for name, a_tok, b_tok, new_rel in [
        ("flip H2loc->C0 to entails (the suspected defect)", "H2loc", "C0", "entails"),
        ("flip C0->H2loc to does_not_entail", "C0", "H2loc", "does_not_entail"),
        ("flip C0->C2 to does_not_entail", "C0", "C2", "does_not_entail"),
    ]:
        mutated, hit = [], False
        for e in pool:
            e = dict(e)
            if (norm_class(str(e.get("from", ""))) == a_tok
                    and norm_class(str(e.get("to", ""))) == b_tok):
                e["relation"] = new_rel
                hit = True
            mutated.append(e)
        if not hit:  # ensure the pair is exercised even if no live row carries it
            mutated.append({"from": phrase[a_tok], "to": phrase[b_tok], "relation": new_rel})
        cases.append({"mutation": name, "detected": run(mutated, "selftest")})

    # contradiction case: same pair declared entails in one file and forbidden in another
    mut = list(pool)
    mut.append({"from": phrase["H2loc"], "to": phrase["C2"],
                "relation": "does_not_entail", "reason": "seeded contradiction"})
    rows = check_rows(mut, "selftest")
    edges = {(r["from_token"], r["to_token"]) for r in rows
             if r["checked"] and r["declared_relation"] == "entails"}
    forb = {(r["from_token"], r["to_token"]) for r in rows
            if r["checked"] and r["declared_relation"] == "does_not_entail"}
    cases.append({"mutation": "same pair both entails and forbidden",
                  "detected": bool(closure(edges) & forb)})
    return cases


def main() -> int:
    files: dict[str, str] = {}
    for rel, want in PINNED.items():
        p = ROOT / rel
        if not p.exists():
            print(f"FAIL-CLOSED: missing {rel}", file=sys.stderr)
            return 3
        got = sha256_file(p)
        files[rel] = got
        if got != want:
            print(f"FAIL-CLOSED: hash drift {rel}\n  pinned {want}\n  live   {got}", file=sys.stderr)
            return 3

    supp = yaml.safe_load((ROOT / "artifacts/formulation/formulation_taxonomy.yaml").read_text())
    c0 = yaml.safe_load((ROOT / "schemas/af_scc_c0_vacuum.yaml").read_text())
    c2 = yaml.safe_load((ROOT / "schemas/af_scc_c2_vacuum.yaml").read_text())

    chains = {
        "research_map/formulation_taxonomy.yaml#axis_registry":
            supp["axis_registry"]["regularity_axis"]["containment"],
        "schemas/af_scc_c0_vacuum.yaml#implication_ledger":
            c0["implication_ledger"]["extension_class_containment"],
        "schemas/af_scc_c2_vacuum.yaml#implication_ledger":
            c2["implication_ledger"]["extension_class_containment"],
    }

    # --- A. derivation from declared text
    derived: set[tuple[str, str]] = set()
    per_source = {}
    for src, txt in chains.items():
        prs = derive_subset_pairs(str(txt))
        per_source[src] = sorted(prs)
        derived |= prs
    derivation_conflicts = [
        {"pair": [a, b], "why": f"declared E_{a} subset E_{b} but size order says E_{a} is "
                                 f"{'larger' if SIZE[a] < SIZE[b] else 'not larger'}"}
        for a, b in sorted(derived)
        if a in SIZE and b in SIZE and not (SIZE[a] >= SIZE[b])
    ]
    derived_closure = closure(derived)
    missing_adjacent = [list(p) for p in ADJACENT if p not in derived_closure]

    # --- B. supplement ledger rows
    supp_rows = check_rows(supp.get("implication_ledger", []),
                           "artifacts/formulation/formulation_taxonomy.yaml#implication_ledger")

    # --- C. frozen schema ledgers ("this class" resolves to the schema's class)
    c0_rows = check_rows(c0["implication_ledger"].get("one_way_entailments", []),
                         "schemas/af_scc_c0_vacuum.yaml#one_way_entailments", this_class="C0")
    c0_rows += check_rows([dict(e, relation="does_not_entail")
                           for e in c0["implication_ledger"].get("forbidden_transfers", [])],
                          "schemas/af_scc_c0_vacuum.yaml#forbidden_transfers", this_class="C0")
    c2_rows = check_rows(c2["implication_ledger"].get("one_way_entailments", []),
                         "schemas/af_scc_c2_vacuum.yaml#one_way_entailments", this_class="C2")
    c2_rows += check_rows([dict(e, relation="does_not_entail")
                           for e in c2["implication_ledger"].get("forbidden_transfers", [])],
                          "schemas/af_scc_c2_vacuum.yaml#forbidden_transfers", this_class="C2")
    all_rows = supp_rows + c0_rows + c2_rows
    row_violations = [r for r in all_rows if r["checked"] and not r["consistent"]]

    # --- D. order-independent contradiction: transitively entailed vs declared forbidden
    entails_edges = {(r["from_token"], r["to_token"]) for r in all_rows
                     if r["checked"] and r["declared_relation"] == "entails"}
    forbidden_edges = {(r["from_token"], r["to_token"]) for r in all_rows
                       if r["checked"] and r["declared_relation"] == "does_not_entail"}
    contradictions = sorted(closure(entails_edges) & forbidden_edges)

    defect = bool(derivation_conflicts or missing_adjacent or row_violations or contradictions)
    verdict = "DEFECT_CONFIRMED" if defect else "NO_DEFECT"

    selftest = detector_selftest({
        "supplement": supp.get("implication_ledger", []),
        "c0": c0["implication_ledger"].get("one_way_entailments", []),
        "c2": c2["implication_ledger"].get("one_way_entailments", []),
    })
    detector_ok = all(c["detected"] for c in selftest)
    if not detector_ok:
        verdict = "HARNESS_FAIL"  # the checker itself is not trustworthy

    report = {
        "report_id": "w001-f0-ledger-h2loc-consistency",
        "created_at": datetime.now(CST).isoformat(timespec="seconds"),
        "actor": "worker-001",
        "node_id": "F0",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "variant_id": "H2LOC",
        "gate": "G-F0",
        "check": "H2_loc implication rows vs the frozen extension-class containment chain",
        "direction_convention": "S_A entails S_B iff size(E_A) >= size(E_B); "
                                "size order (largest extension set first) = C0 > H2loc > C^{1,1} > C2",
        "inputs": files,
        "declared_chains": chains,
        "derived_subset_pairs": sorted(derived),
        "per_source_pairs": per_source,
        "derivation_conflicts": derivation_conflicts,
        "missing_adjacent_pairs": missing_adjacent,
        "rows": all_rows,
        "row_violations": row_violations,
        "transitive_entails_vs_forbidden": [list(p) for p in contradictions],
        "detector_selftest": selftest,
        "detector_ok": detector_ok,
        "verdict": verdict,
        "falsified_hypothesis": {
            "hypothesis": "the supplement row {from: H2_loc inextendibility, to: AF-SCC-C0-VAC-GEN, "
                          "relation: does_not_entail, direction: forbidden} contradicts the chain "
                          "E_C2 subset E_C^{1,1} subset E_H2loc subset E_C0 and should be `entails`.",
            "outcome": "REFUTED",
            "why": "H2_loc is the STRONGER extension class (fewer admissible extensions), so "
                   "H2_loc-inextendibility is the WEAKER statement; the chain licenses "
                   "C0 => H2loc => C2, never H2loc => C0. The frozen C0 schema states this "
                   "explicitly: 'H2_loc-inextendibility is weaker and entails the C2 sibling, "
                   "not this class' (anti_scope).",
            "caught_by": "re-deriving the entailment direction from the containment sentence and "
                         "the schema's own anti_scope line, before emission",
        },
        "finding": ("H2_loc implication rows are consistent with the frozen containment chain at "
                    "the pinned hashes: H2_loc-inextendibility entails C2-inextendibility and does "
                    "not entail C0-inextendibility."
                    if verdict == "NO_DEFECT" else
                    "inconsistency found; see row_violations / contradictions"),
    }

    out = OUT / "report.json"
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(f"verdict: {verdict}")
    print(f"  derivation_conflicts: {len(derivation_conflicts)}  missing_adjacent: {len(missing_adjacent)}")
    print(f"  rows checked: {sum(1 for r in all_rows if r['checked'])}/{len(all_rows)}  "
          f"row_violations: {len(row_violations)}  contradictions: {len(contradictions)}")
    print(f"  detector_selftest: {sum(1 for c in selftest if c['detected'])}/{len(selftest)} seeded defects caught")
    for v in row_violations:
        print(f"  VIOLATION {v['source']}[{v['index']}]: {v['from_token']}->{v['to_token']} "
              f"declared {v['declared_relation']}, expects {v['expects']}")
    for p in contradictions:
        print(f"  CONTRADICTION: {p[0]}->{p[1]} both entailed and forbidden")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
