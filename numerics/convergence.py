"""Convergence-order utilities for the N0 calibration suite."""
from __future__ import annotations

import math
from typing import Iterable, Sequence


def observed_order(errors: Sequence[float], refinement: float = 2.0) -> list[float]:
    """Observed orders p_i = log(e_i / e_{i+1}) / log(refinement).

    ``errors`` must be ordered from coarse to fine.  Returns one entry per
    consecutive pair.  Errors that are exactly zero return ``inf`` and are a
    red flag (usually an exact-solution leak or a too-loose check).
    """
    out: list[float] = []
    for e_coarse, e_fine in zip(errors[:-1], errors[1:]):
        if e_fine <= 0.0:
            out.append(float("inf") if e_coarse > 0 else 0.0)
        elif e_coarse <= 0.0:
            out.append(float("-inf"))
        else:
            out.append(math.log(e_coarse / e_fine) / math.log(refinement))
    return out


def fit_order(hs: Sequence[float], errors: Sequence[float]) -> float:
    """Least-squares slope of log(error) vs log(h); NaN for a single sample."""
    if len(hs) != len(errors):
        raise ValueError("need matched h/error samples")
    if len(hs) == 1:
        return float("nan")
    if len(hs) < 1:
        raise ValueError("need at least one h/error sample")
    xs = [math.log(h) for h in hs]
    ys = [math.log(e) if e > 0 else float("-inf") for e in errors]
    if any(y == float("-inf") for y in ys):
        raise ValueError("cannot fit an order to a zero error")
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = sum((x - mx) ** 2 for x in xs)
    if den == 0:
        raise ValueError("all resolutions identical")
    return num / den


def order_summary(hs: Sequence[float], errors: Sequence[float], refinement: float = 2.0) -> dict:
    """Convenience bundle: per-pair orders plus a fitted slope."""
    return {
        "h": list(hs),
        "errors": list(errors),
        "pair_orders": observed_order(errors, refinement),
        "fitted_order": fit_order(hs, errors),
    }


def format_table(header: Iterable[str], rows: Iterable[Iterable[object]]) -> str:
    """Minimal fixed-width table formatter (no third-party dependencies)."""
    cols = [list(map(str, header))] + [[str(c) for c in row] for row in rows]
    widths = [max(len(r[i]) for r in cols) for i in range(len(cols[0]))]
    lines = []
    for k, row in enumerate(cols):
        lines.append("  ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)))
        if k == 0:
            lines.append("  ".join("-" * w for w in widths))
    return "\n".join(lines)
