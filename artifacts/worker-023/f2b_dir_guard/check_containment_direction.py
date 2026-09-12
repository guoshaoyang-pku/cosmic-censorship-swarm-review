#!/usr/bin/env python3
"""Standalone CLI for the proposed containment/entailment-direction lint (R31 hook).

    python3 check_containment_direction.py --json FILE.yaml [--expect-sha256 HEX]
    exit 0 = no direction inversion (warnings may still be reported)
    exit 1 = at least one direction inversion (hard, class-relative)
    exit 2 = unreadable file / YAML error / expected-sha256 mismatch (fail-closed)

Proposal by worker-023, task W023-F2B-DIR-GUARD-01. Non-canonical: read-only on every
canonical path. Adoption requires lead-formulation + controller because it changes the
frozen instrument hash.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from containment_direction_lint import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
