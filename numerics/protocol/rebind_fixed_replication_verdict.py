#!/usr/bin/env python3
"""Lead rebind of the N0 fixed-replication scheme-independence verdict (successor artifact).

The frozen verdict ``numerics/protocol/fixed_replication_verdict.json#dcad962324e3`` asserts
``provenance.fixed_taxonomy_sha256_matches_on_disk = true`` while its own chained pin (L7) and
``provenance.taxonomy_sha256`` (L39) hold F0 rev2 ``66bf917bd368``; the live taxonomy is rev5
``0abb9ed8a961``.  Worker-067's read-only drift ledger measured the assertion as CONTRADICTED
(``W067-N0-PROVENANCE-DRIFT-LEDGER-01``) and named ``astra-lead-numerics`` as repair owner.

This driver produces a **successor** artifact instead of editing the frozen one, because
``dcad962324e3`` is pinned by the current gate proposal (``evidence_hashes``) and by worker
verdicts; an in-place edit would move a pinned hash during the protocol adjudication window
and cascade into the proposal revision.  The successor carries the same R1/R2/R4/R5
arithmetic (re-run here from the frozen inputs), the corrected taxonomy measurement, and an
explicit supersession/rebind block.

Only file written: ``numerics/protocol/fixed_replication_verdict_rev2.json``.

    python3 numerics/protocol/rebind_fixed_replication_verdict.py
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "numerics/protocol/verify_fixed_scheme_independence.py"
OLD = ROOT / "numerics/protocol/fixed_replication_verdict.json"
NEW = ROOT / "numerics/protocol/fixed_replication_verdict_rev2.json"
TAXONOMY = ROOT / "research_map/formulation_taxonomy.yaml"
FIXED = ROOT / "runtime/state/controller_verification/n0_replication_astra_run2_FIXED.json"
CST = timezone(timedelta(hours=8))

EXPECT_OLD = "dcad962324e3be156d1ef1577b7ee2613fac803058351b643d2c8f67bc787a36"
EXPECT_FIXED = "6542db93eebc5095cb903478dfa6a8d24f09776513f9accb1e73f9d0a58ba38e"
F0_REV5 = "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"
F0_REV2 = "66bf917bd368ebd96ee46baa31fb435df106cb4e10152fa0baee8bdd51dfc232"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def numeric_leaves(node, prefix=""):
    """Flatten numeric leaves of a JSON tree into {path: number}."""
    out = {}
    if isinstance(node, dict):
        for k, v in node.items():
            out.update(numeric_leaves(v, f"{prefix}/{k}"))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            out.update(numeric_leaves(v, f"{prefix}/{i}"))
    elif isinstance(node, (int, float)) and not isinstance(node, bool):
        out[prefix] = float(node)
    return out


def main() -> int:
    if sha(OLD) != EXPECT_OLD:
        print(f"REFUTED: superseded verdict moved ({sha(OLD)[:16]})")
        return 2
    if sha(FIXED) != EXPECT_FIXED:
        print("REFUTED: frozen replication run moved")
        return 2
    if sha(TAXONOMY) != F0_REV5:
        print("REFUTED: taxonomy is not rev5 on disk")
        return 2

    # load the worker-14 verifier without executing its __main__ block, redirect its OUT
    spec = importlib.util.spec_from_file_location("w14_scheme_independence", SRC)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    mod.OUT = NEW
    rc = mod.main()
    if rc != 0:
        print(f"REFUTED: verifier main() returned {rc}")
        return 1

    new = json.loads(NEW.read_text())
    old = json.loads(OLD.read_text())

    # numeric delta vs the superseded verdict (must be exactly zero: same frozen inputs);
    # wall-clock leaves are the only ones allowed to differ and are reported separately
    a, b = numeric_leaves(old), numeric_leaves(new)
    wall = lambda k: ("runtime_seconds" in k) or ("refreshed_at" in k)
    keys = sorted(k for k in set(a) & set(b) if not wall(k))
    diffs = {k: abs(a[k] - b[k]) for k in keys if a[k] != b[k]}
    max_diff = max(diffs.values()) if diffs else 0.0
    excluded_wall = sorted(k for k in set(a) & set(b) if wall(k))

    new["supersedes"] = {
        "path": "numerics/protocol/fixed_replication_verdict.json",
        "sha256": EXPECT_OLD,
        "reason": (
            "the superseded record asserts fixed_taxonomy_sha256_matches_on_disk=true while "
            "its own chained pin (L7) and provenance.taxonomy_sha256 (L39) hold superseded "
            "F0 rev2 66bf917bd368; live bytes are F0 rev5 0abb9ed8a961. Measured as "
            "CONTRADICTED by worker-067 W067-N0-PROVENANCE-DRIFT-LEDGER-01 "
            "(LEDGER_COMPLETE_WITH_CONTRADICTED_ASSERTION, 7/7 controls)."
        ),
        "not_edited_in_place_because": (
            "dcad962324e3 is pinned by numerics/tests/n0_gate_proposal.json#evidence_hashes "
            "and by worker verdicts; moving it during the protocol adjudication window would "
            "cascade into the proposal revision and void hash-bound verdicts"
        ),
        "repair_style": "successor artifact; the superseded file is retained as historical",
    }
    new["taxonomy_rebind"] = {
        "frozen_run_f0_pin": F0_REV2,
        "frozen_run_f0_pin_matches_current_disk": False,
        "current_f0_disk": F0_REV5,
        "fixed_taxonomy_sha256_matches_on_disk_recomputed": new.get("provenance", {}).get(
            "fixed_taxonomy_sha256_matches_on_disk"
        ),
        "class_binding_for_forward_use": (
            "AF-WCC-SCALAR-SPH <-> research_map/formulation_taxonomy.yaml#0abb9ed8a961 "
            "(rev5, provisional); membership invariance rev2->rev5 measured by worker-067 "
            "REBIND_INERT_FOR_CLASS_MEMBERSHIP, controls 5/5"
        ),
        "load_bearing_for_order_claim": False,
    }
    new["numeric_delta_vs_superseded"] = {
        "numeric_leaves_compared": len(keys),
        "differing_leaves": diffs,
        "max_abs_difference": max_diff,
        "excluded_wall_clock_leaves": excluded_wall,
        "note": "0.0 expected: the R1/R2/R4/R5 arithmetic depends only on the frozen run and module, not on the taxonomy pin; only runtime_seconds may differ",
    }
    new["refreshed_at"] = datetime.now(CST).isoformat(timespec="seconds")
    new["refreshed_by"] = "astra-lead-numerics (lead-numerics-01-20260912T004903-968807)"
    new["source_verifier"] = {
        "path": "numerics/protocol/verify_fixed_scheme_independence.py",
        "sha256": sha(SRC),
        "method": "imported and re-run with OUT redirected; no pinned artifact written",
    }
    NEW.write_text(json.dumps(new, indent=2, sort_keys=True) + "\n")

    print(json.dumps({
        "wrote": str(NEW.relative_to(ROOT)),
        "sha256": sha(NEW),
        "supersedes": EXPECT_OLD,
        "numeric_leaves_compared": len(keys),
        "max_abs_difference": max_diff,
        "taxonomy_assertion_recomputed": new.get("provenance", {}).get(
            "fixed_taxonomy_sha256_matches_on_disk"
        ),
        "q1_answer": (new.get("q1_invariant_functional_scheme_appropriate") or {}).get("answer"),
        "q2_answer": (new.get("q2_order_fit_carries_uncertainty") or {}).get("answer"),
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
