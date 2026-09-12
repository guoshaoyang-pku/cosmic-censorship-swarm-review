"""N0 — flat-space scalar-wave calibration package.

Scope discipline (Astra hard decision #2, 2026-09-11):
    This package performs *calibration, convergence tests and invariant
    diagnostics only* for the flat-space massless scalar wave equation.
    It must not contain, and must not launch, self-gravitating production.
    The production entry point (``numerics.spherical_solver``, node N1) is
    hard-gated by :mod:`numerics.gates` on the formulation and audit gates.

Every result produced here is a numerical measurement, not a claim about
cosmic censorship.  See ``numerics/README.md`` for the claim ladder.
"""

__version__ = "0.1.0"

NODE_ID = "N0"
GROUP_ID = "numerics"
