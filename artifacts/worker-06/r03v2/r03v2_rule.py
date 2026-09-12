#!/usr/bin/env python3
"""R03-v2 PROPOSAL: replace R03's literal-substring binder test with a binder-head co-binding test.

Frozen R03 (artifacts/worker-06/spec_conformance_audit.py @ c79d8ab8440a, lines 210-212) fails a
quantifier entry when its `binder` string is not a literal substring of `quantifiers.formal`.
Canonical AF-WCC-VAC-GEN writes binder "(q,t0)" but its formal sentence renders the same binding
as "not exists q in I+ and t0 in [0,T)", so the canonical schema is falsely rejected on R03.
That false positive is the standing A1 blocker in lead-form-20260912T005843-94.

R03-v2 keeps the spec requirement ("quantifiers.formal is a single sentence using those binders")
but tests *binding* instead of spelling:

  ids(b)  identifiers of binder b, in order; empty -> fail
  heads   for each quantifier clause of formal, its prefix up to the first top-level separator
          among   : ; ,   with   such that   where   of   letting
          (parenthesised groups are never split; a top-level separator is one at paren depth 0)
  bound   some head contains ids(b) in order, each within `span` characters of the previous
          identifier; the first identifier is not windowed

  no binding head -> fail "binder ... not co-bound in one binder head"

This is a deterministic heuristic, not a parser. It can over-reject a legitimate coordinated
binder whose variables sit more than `span` characters apart in one head (measured in the
calibration report), and it can under-reject a declared binder whose identifiers happen to appear
in a head that does not actually introduce them. Both residues are reported, not hidden.

Proposal only: the frozen tool is never modified.
"""
from __future__ import annotations

import re

DEFAULT_SPAN = 80

_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_QUANT = re.compile(r"(?:not\s+exists|forall|exists)\b")
# One scan so separators outside and inside parentheses are seen in textual order.
_SEP = re.compile(r"[()]|:|;|,|\bwith\b|\bsuch that\b|\bwhere\b|\bof\b|\bletting\b")


def identifiers(binder: str) -> list[str]:
    """Identifiers of a binder string, in order. '(q,t0)' -> ['q','t0']."""
    return _IDENT.findall(str(binder))


def binder_head(clause: str) -> str:
    """Prefix of a quantifier clause before its first top-level separator."""
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


def clause_heads(formal: str) -> list[str]:
    """Binder heads of every quantifier clause of a formal sentence."""
    starts = [m.start() for m in _QUANT.finditer(formal)]
    return [binder_head(formal[a:b]) for a, b in zip(starts, starts[1:] + [len(formal)])]


def binder_bound(binder: str, formal: str, span: int = DEFAULT_SPAN) -> tuple[bool, str]:
    """R03-v2 predicate. Returns (ok, reason)."""
    ids = identifiers(binder)
    if not ids:
        return False, f"binder {binder!r} carries no identifier"
    for head in clause_heads(formal):
        pos, ok = 0, True
        for ident in ids:
            m = re.search(rf"\b{re.escape(ident)}\b", head[pos:])
            if not m or (pos and m.start() > span):
                ok = False
                break
            pos += m.start() + len(ident)
        if ok:
            return True, "co-bound in binder head"
    return False, f"binder {binder!r} not co-bound in one binder head"


def binder_bound_frozen(binder: str, formal: str) -> tuple[bool, str]:
    """Frozen R03 predicate, reproduced for side-by-side reporting."""
    if str(binder) in formal:
        return True, "literal substring present"
    return False, f"binder {binder!r} absent from formal sentence"


if __name__ == "__main__":  # tiny self-check on the canonical WCC sentence
    _wcc = ('forall r in D0: exists G_r subset X^r_vac(AF) with G_r comeager: '
            'forall (Sigma,h,K) in G_r, letting (M,g) be the maximal globally hyperbolic '
            'development: exists a conformal completion (Mtilde,gtilde,Omega) of (M,g) at I+ '
            'such that (i) I+ is null, and (ii) every generator is future-complete, and '
            'forall future-inextendible causal geodesics gamma of (M,g) with finite affine '
            'length: not exists q in I+ and t0 in [0,T) with gamma([t0,T)) subset J^-(q).')
    for _b in ["r", "G_r", "(Sigma,h,K)", "(Mtilde,gtilde,Omega)", "gamma", "(q,t0)"]:
        print(_b, binder_bound(_b, _wcc), binder_bound_frozen(_b, _wcc))
