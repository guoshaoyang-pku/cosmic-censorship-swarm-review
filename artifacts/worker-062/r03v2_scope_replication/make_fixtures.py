#!/usr/bin/env python3
"""W062-GFORM-R03V2-SCOPE-REPLICATION-01 -- fresh held-out scope corpus generator.

Independent of artifacts/worker-06/r03scope/make_fixtures.py. Builds each fixture by
text-level replacement of the LAST clause of quantifiers.formal in the pinned canonical
AF-WCC-VAC-GEN schema (schemas/af_wcc_vacuum.yaml @ d9cebb9404b2). No other leaf is touched.

Corpus semantics pre-declared (same convention as W006-R03-SCOPE-01, stated here so the
scoring is reproducible): the ordered list `quantifiers.ordered` declares, per entry, the
binder that entry must introduce. A fixture is a SCOPE ERROR (must reject) iff the declared
ordered binder of some entry is not introduced by that entry's own quantifier clause -- e.g.
a declared variable is left free, is only mentioned non-bindingly, or is bound by a
different clause. A fixture is CORRECT (must accept) iff every declared binder is introduced
by its own clause.

The corpus was authored after reading both the frozen literal R03 and the cand_r03v2
binder-head rule, deliberately targeting the residue cand_r03v2's own docstring admits
("it can under-reject a declared binder whose identifiers happen to appear in a head that
does not actually introduce them"). Predictions are frozen in PREREGISTRATION.json before
any candidate is executed.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
FIX = HERE / "fixtures"
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat(timespec="seconds")

WCC = ROOT / "schemas/af_wcc_vacuum.yaml"
F2A = ROOT / "schemas/af_scc_c2_vacuum.yaml"
F2B = ROOT / "schemas/af_scc_c0_vacuum.yaml"

# Exact canonical tail clause (last line of the formal block scalar).
CANON_TAIL = ("    not exists q in I+ and t0 in [0,T) with "
              "gamma([t0,T)) subset J^-(q) intersect M.")


def sha256_path(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def span_filler(target_distance: int) -> str:
    """Padding between `q` and `t0`; exact character distance from end of `q` to `t0`.

    Text layout of the clause: 'not exists q in I+ and {filler} t0 in [0,T) ...'
    distance = len(' in I+ and ') + len(filler) + 1 = 12 + len(filler).
    """
    n = target_distance - 12
    assert n > 0, target_distance
    base = "very " * (n // 5)
    rem = n - len(base)
    return base + ("x" * rem)


CLAUSES = {
    # ---- controls (unscored) -------------------------------------------------
    "ctrl_canonical_wcc.yaml": None,          # byte copy of canonical F1
    "ctrl_canonical_f2a.yaml": None,          # byte copy of canonical F2a
    "ctrl_canonical_f2b.yaml": None,          # byte copy of canonical F2b

    # ---- scored positives: declared binder (q,t0) genuinely introduced in its own clause
    "pos_for_which.yaml":
        "    not exists q in I+ and t0 in [0,T) for which "
        "gamma([t0,T)) subset J^-(q) intersect M.",
    "pos_interval_words.yaml":
        "    not exists q in I+ and t0 in the interval from 0 to T with "
        "gamma([t0,T)) subset J^-(q) intersect M.",
    "pos_long_span_40.yaml":
        "    not exists q in I+ and " + span_filler(40) + " t0 in [0,T) with "
        "gamma([t0,T)) subset J^-(q) intersect M.",

    # ---- scored negatives: genuine scope errors, all predicted to fool cand_r03v2
    # N1 t0 occurs free inside q's own restriction; no quantifier binds t0.
    "neg_free_in_restriction.yaml":
        "    not exists q in J^-(t0) with "
        "gamma([t0,T)) subset J^-(q) intersect M.",
    # N2 t0 occurs free as a predicate operand, never introduced as a binder.
    "neg_free_predicate.yaml":
        "    not exists q in I+ and t0 < T with "
        "gamma([t0,T)) subset J^-(q) intersect M.",
    # N3 the declared not_exists binder (q,t0) is co-bound in a DIFFERENT clause (a forall
    #    that is not the entry's clause); its own clause introduces only q.
    "neg_wrong_clause_cobind.yaml":
        "    forall q in I+ and t0 in [0,T): not exists q in I+ with "
        "gamma([t0,T)) subset J^-(q) intersect M.",
    # N4 t0 occurs only inside a parenthesised non-binding aside in the quantifier head.
    "neg_head_paren_aside.yaml":
        "    not exists q in I+ and (t0, T) with "
        "gamma([t0,T)) subset J^-(q) intersect M.",

    # ---- unscored edge probes: span boundary of cand_r03v2 (same legal binding, filler only)
    "edge_span_79.yaml":
        "    not exists q in I+ and " + span_filler(79) + " t0 in [0,T) with "
        "gamma([t0,T)) subset J^-(q) intersect M.",
    "edge_span_80.yaml":
        "    not exists q in I+ and " + span_filler(80) + " t0 in [0,T) with "
        "gamma([t0,T)) subset J^-(q) intersect M.",
    "edge_span_81.yaml":
        "    not exists q in I+ and " + span_filler(81) + " t0 in [0,T) with "
        "gamma([t0,T)) subset J^-(q) intersect M.",
    "edge_span_120.yaml":
        "    not exists q in I+ and " + span_filler(120) + " t0 in [0,T) with "
        "gamma([t0,T)) subset J^-(q) intersect M.",
}

CATEGORY = {}
for name in CLAUSES:
    if name.startswith("ctrl"):
        CATEGORY[name] = ("control", False)
    elif name.startswith("pos"):
        CATEGORY[name] = ("pos", True)
    elif name.startswith("neg"):
        CATEGORY[name] = ("neg", True)
    else:
        CATEGORY[name] = ("edge", False)

# Measured character distance from end of identifier `q` to start of `t0` inside the clause
# head, using the same scanner semantics as cand_r03v2 (top-level `)` is transparent; `,`
# and `with` terminate the head). Recorded for the edge probes and every fixture.
_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_QUANT = re.compile(r"(?:not\s+exists|forall|exists)\b")
_SEP = re.compile(r"[()]|:|;|,|\bwith\b|\bsuch that\b|\bwhere\b|\bof\b|\bletting\b")


def head_of(clause: str) -> str:
    depth = 0
    for m in _SEP.finditer(clause):
        tok = m.group(0)
        if tok == "(":
            depth += 1
        elif tok == ")":
            depth = max(0, depth - 1)
        elif depth == 0:
            return clause[: m.start()]
    return clause


def q_to_t0(clause: str) -> int | None:
    h = head_of(clause)
    mq = re.search(r"\bq\b", h)
    if not mq:
        return None
    mt = re.search(r"\bt0\b", h[mq.end():])
    return mt.start() if mt else None


def main() -> None:
    FIX.mkdir(parents=True, exist_ok=True)
    base_text = WCC.read_text()
    if CANON_TAIL not in base_text:
        raise SystemExit("FAIL: canonical tail clause not found; pins moved")
    wcc_sha = sha256_path(WCC)
    f2a_sha = sha256_path(F2A)
    f2b_sha = sha256_path(F2B)

    entries = []
    for name, clause in CLAUSES.items():
        dst = FIX / name
        if name == "ctrl_canonical_wcc.yaml":
            dst.write_bytes(WCC.read_bytes())
            origin, mutation = "schemas/af_wcc_vacuum.yaml", "byte copy of canonical F1"
            base, bsha = "schemas/af_wcc_vacuum.yaml", wcc_sha
        elif name == "ctrl_canonical_f2a.yaml":
            dst.write_bytes(F2A.read_bytes())
            origin, mutation = "schemas/af_scc_c2_vacuum.yaml", "byte copy of canonical F2a"
            base, bsha = "schemas/af_scc_c2_vacuum.yaml", f2a_sha
        elif name == "ctrl_canonical_f2b.yaml":
            dst.write_bytes(F2B.read_bytes())
            origin, mutation = "schemas/af_scc_c0_vacuum.yaml", "byte copy of canonical F2b"
            base, bsha = "schemas/af_scc_c0_vacuum.yaml", f2b_sha
        else:
            out = base_text.replace(CANON_TAIL, clause)
            if out == base_text:
                raise SystemExit(f"FAIL: mutation had no effect for {name}")
            dst.write_text(out)
            origin, mutation = ("schemas/af_wcc_vacuum.yaml",
                                "replace the final quantifier clause of quantifiers.formal with: "
                                + json.dumps(clause))
            base, bsha = "schemas/af_wcc_vacuum.yaml", wcc_sha
        cat, scored = CATEGORY[name]
        rec = {
            "fixture": name,
            "base": base,
            "base_sha256": bsha,
            "category": cat,
            "scored": scored,
            "declared_target_paths": ["quantifiers.formal"] if clause else [],
            "mutation": mutation,
            "sha256": sha256_path(dst),
            "bytes": dst.stat().st_size,
            "q_to_t0_distance_in_head": q_to_t0(clause) if clause else q_to_t0(CANON_TAIL),
            "head": head_of(clause) if clause else head_of(CANON_TAIL.strip()),
        }
        entries.append(rec)

    manifest = {
        "corpus_id": "W062-R03V2-SCOPE-REPLICATION-01",
        "created_at": NOW,
        "worker": "worker-062",
        "node_id": "A1",
        "gate": "G-FORM/G-CLASSBIND",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "base": {"schemas/af_wcc_vacuum.yaml": wcc_sha},
        "target_leaf": "quantifiers.formal",
        "semantics": ("scope error iff a declared ordered binder is not introduced by that "
                      "entry's own quantifier clause; same convention as W006-R03-SCOPE-01."),
        "freshness": ("no fixture is copied from W006-R03-SCOPE-01, W006-R03-CAND-HEADTOHEAD-01, "
                      "the R03-v2 calibration set, the worker-004 calibration set or the held-out "
                      "corpora; the four negatives are new families (free-in-restriction, "
                      "free-predicate, wrong-clause co-binding, head-parenthesised aside)"),
        "fixtures": entries,
    }
    (HERE / "fixture_manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    print(f"wrote {len(entries)} fixtures; manifest sha256 pending")
    for e in entries:
        print(f"  {e['category']:8s} scored={str(e['scored']):5s} {e['fixture']:32s} "
              f"d(q,t0)={e['q_to_t0_distance_in_head']}")


if __name__ == "__main__":
    main()
