#!/usr/bin/env python3
"""W067-N0-FIXEDVERDICT-REV2-INDEP-01 -- independent verification of the N0 fixed-replication
verdict rebind repair.

Task (one bounded class-bound task): verify, at pinned hashes, that
``numerics/protocol/fixed_replication_verdict_rev2.json`` (successor, declared
7954d2d355451e3d...) is a correct *metadata-only* rebind of the superseded
``numerics/protocol/fixed_replication_verdict.json`` (dcad962324e3be15...), and that the
supersession actually reaches the live chain (or state exactly where it does not).

Actor authority: bounded breadth worker. Advisory only: no gate verdict, no node transition,
no validation_status=passed, no numerics_lock change. Read-only on every canonical path.

Checks (all machine-decided; exit 2 on anchor drift or failed control, exit 1 on an
unexpected difference, exit 0 otherwise):

  A1 anchor pin + no-write canary
  A2 declared-hash chain resolution in the successor (arbitrary file-hash claims)
  A3 independent metadata-only comparison successor vs predecessor:
       - every numeric leaf equal (this reproduces/rejects the 79-leaf, delta-0.0 claim)
       - the set of changed/new/removed leaves is exactly the declared rebind metadata
  A4 frozen-run-flag semantics: recompute the generator's
       ``fixed_taxonomy_sha256_matches_on_disk`` definition from the frozen run pin and the
       live taxonomy; report the field-name reading ambiguity explicitly
  A5 supersession operativity: which live consumers cite the superseded artifact vs the
       successor; a repair not bound anywhere live does not discharge the dissent

Controls (in-memory only, no canonical write): C1 no-write canary, C2 chain mutation,
C3 numeric-leaf mutation, C4 frozen-flag flips, C5 operator count.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

# Exact pins this task is bound to. A moved byte is a moving target -> exit 2, not a verdict.
HARD_PINS = {
    "numerics/protocol/fixed_replication_verdict.json":
        "dcad962324e3be156d1ef1577b7ee2613fac803058351b643d2c8f67bc787a36",
    "numerics/protocol/fixed_replication_verdict_rev2.json":
        "7954d2d355451e3dbd3e7b7c23769ba204451cc8adf5eb04515910069a10fa60",
    "research_map/formulation_taxonomy.yaml":
        "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "runtime/state/controller_verification/n0_replication_astra_run2_FIXED.json":
        "6542db93eebc5095cb903478dfa6a8d24f09776513f9accb1e73f9d0a58ba38e",
    "numerics/tests/n0_gate_proposal.json":
        "b4192221ff7d" ,
    "numerics/protocol/verify_fixed_scheme_independence.py":
        "a0daf1271bfb" ,
}
# Canary-only files: measure before/after, no hardcoded expected value.
CANARY = [
    "numerics/protocol/n0_gate_proposal_leadverify.json",
    "numerics/protocol/n0_c4_registration_manifest.json",
    "numerics/protocol/format_conditions_disposition.json",
    "numerics/CONVERGENCE_PROTOCOL.md",
]
# Live consumers whose citation of the superseded artifact matters for discharge-by-binding.
CONSUMERS = [
    "numerics/tests/n0_gate_proposal.json",
    "numerics/protocol/n0_gate_proposal_leadverify.json",
    "numerics/protocol/n0_c4_registration_manifest.json",
    "numerics/protocol/format_conditions_disposition.json",
]
SUPERSEDED_PREFIX = "dcad962324e3be15"
SUCCESSOR_PREFIX = "7954d2d355451e3d"

# Leaves the successor is allowed to add / change relative to the predecessor.
NEW_KEY_ALLOWLIST = {
    "/refreshed_at", "/refreshed_by", "/supersedes", "/taxonomy_rebind",
    "/numeric_delta_vs_superseded", "/source_verifier",
}
CHANGED_LEAF_ALLOWLIST = {
    "/chained_evidence_hashes/research_map/formulation_taxonomy.yaml",
    "/provenance/taxonomy_sha256",
    "/provenance/fixed_taxonomy_sha256_matches_on_disk",
    "/provenance/checked_at",
}
VOLATILE_LEAVES = {"/runtime_seconds"}


def _allowed_new(path: str) -> bool:
    return any(path == k or path.startswith(k + "/") for k in NEW_KEY_ALLOWLIST)


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def leaf_walk(doc, prefix=""):
    """Yield (path, kind, value) for every leaf; kind in num/str/bool/null."""
    if isinstance(doc, dict):
        for k, v in doc.items():
            yield from leaf_walk(v, f"{prefix}/{k}")
    elif isinstance(doc, list):
        for i, v in enumerate(doc):
            yield from leaf_walk(v, f"{prefix}/{i}")
    else:
        if isinstance(doc, bool):
            kind = "bool"
        elif isinstance(doc, (int, float)):
            kind = "num"
        elif doc is None:
            kind = "null"
        else:
            kind = "str"
        yield prefix, kind, doc


def compare_docs(pred: dict, succ: dict) -> dict:
    """Independent leaf-level comparison. Returns counts + differences."""
    pl = {p: (k, v) for p, k, v in leaf_walk(pred)}
    sl = {p: (k, v) for p, k, v in leaf_walk(succ)}
    unexpected, expected = [], []
    numeric_equal = numeric_differ = 0
    for p in sorted(set(pl) | set(sl)):
        if p in pl and p in sl:
            (pk, pv), (sk, sv) = pl[p], sl[p]
            if p in VOLATILE_LEAVES:
                expected.append({"path": p, "change": "volatile", "before": pv, "after": sv})
                continue
            if pk == sk == "num":
                if pv == sv:
                    numeric_equal += 1
                else:
                    numeric_differ += 1
                    unexpected.append({"path": p, "change": "numeric", "before": pv, "after": sv})
                continue
            if pv != sv:
                rec = {"path": p, "change": "value", "before": pv, "after": sv}
                (expected if p in CHANGED_LEAF_ALLOWLIST else unexpected).append(rec)
        elif p in sl:
            rec = {"path": p, "change": "added", "after": sl[p][1]}
            (expected if _allowed_new(p) else unexpected).append(rec)
        else:
            unexpected.append({"path": p, "change": "removed", "before": pl[p][1]})
    return {
        "numeric_leaves_equal": numeric_equal,
        "numeric_leaves_differ": numeric_differ,
        "expected_changes": expected,
        "unexpected_differences": unexpected,
        "verdict": "METADATA_ONLY" if not unexpected else "UNEXPECTED_DIFFERENCE",
    }


def declared_pairs(succ: dict) -> list:
    """(label, path, declared) for every resolvable file-hash claim in the successor."""
    out = []
    for rel, h in (succ.get("chained_evidence_hashes") or {}).items():
        out.append({"label": f"chained:{rel}", "path": rel, "declared": h, "historical": False})
    prov = succ.get("provenance") or {}
    for key, rel in (("fixed_json_sha256", prov.get("fixed_json")),
                     ("harness_sha256", "artifacts/flash-04/n0_acceptance/harness.py"),
                     ("replication_script_sha256", "numerics/tests/flat_wave_replication.py"),
                     ("taxonomy_sha256", "research_map/formulation_taxonomy.yaml")):
        if rel and prov.get(key):
            out.append({"label": f"provenance:{key}", "path": rel,
                        "declared": prov[key], "historical": False})
    sv = succ.get("source_verifier") or {}
    if sv.get("path") and sv.get("sha256"):
        out.append({"label": "source_verifier", "path": sv["path"],
                    "declared": sv["sha256"], "historical": False})
    rebind = succ.get("taxonomy_rebind") or {}
    if rebind.get("frozen_run_f0_pin"):
        out.append({"label": "taxonomy_rebind:frozen_run_f0_pin",
                    "path": None, "declared": rebind["frozen_run_f0_pin"], "historical": True})
    return out


def resolve_chain(root: Path, succ: dict) -> dict:
    rows = []
    for rec in declared_pairs(succ):
        if rec["historical"]:
            rows.append({**rec, "measured": None, "status": "HISTORICAL_NOT_ON_DISK"})
            continue
        p = root / rec["path"]
        if not p.is_file():
            rows.append({**rec, "measured": None, "status": "MISSING"})
            continue
        measured = sha256_file(p)
        d = rec["declared"]
        status = "RESOLVED" if (measured == d or measured.startswith(d) or d.startswith(measured)) \
            else "MISMATCH"
        rows.append({**rec, "measured": measured, "status": status})
    bad = [r for r in rows if r["status"] in ("MISSING", "MISMATCH")]
    return {"rows": rows, "unresolved": bad, "verdict": "ALL_RESOLVE" if not bad else "CHAIN_DEFECT"}


def frozen_flag_semantics(root: Path, succ: dict) -> dict:
    """Recompute the generator's flag: frozen run pin == live taxonomy sha."""
    sys.path.insert(0, str(root / "numerics" / "protocol"))
    src = (root / "numerics" / "protocol" / "verify_fixed_scheme_independence.py").read_text()
    uses_expression = ('fixed["provenance"]["f0_taxonomy_sha256"] == taxonomy_sha' in src)
    frozen = json.loads((root / "runtime/state/controller_verification"
                         "/n0_replication_astra_run2_FIXED.json").read_text())
    frozen_pin = (frozen.get("provenance") or {}).get("f0_taxonomy_sha256")
    live = sha256_file(root / "research_map" / "formulation_taxonomy.yaml")
    recomputed = (frozen_pin == live)
    actual = (succ.get("provenance") or {}).get("fixed_taxonomy_sha256_matches_on_disk")
    rebound = (succ.get("provenance") or {}).get("taxonomy_sha256")
    return {
        "generator_expression_present": uses_expression,
        "frozen_run_f0_pin": frozen_pin,
        "live_taxonomy_sha256": live,
        "flag_recomputed_from_generator_semantics": recomputed,
        "flag_in_successor": actual,
        "flag_consistent_with_generator_semantics": actual == recomputed,
        # The name reads as "the record's taxonomy pin matches disk"; under that reading the
        # rebound pin RESOLVES while the flag is false. Report, do not silently resolve.
        "rebound_pin_resolves_on_disk": rebound == live,
        "field_name_reading_ambiguous": (rebound == live) and (actual is False),
    }


def operativity(root: Path, override: dict | None = None) -> dict:
    override = override or {}
    rows = []
    for rel in CONSUMERS:
        text = override.get(rel)
        if text is None:
            text = (root / rel).read_text()
        rows.append({
            "path": rel,
            "cites_superseded": text.count(SUPERSEDED_PREFIX)
                                + text.count("fixed_replication_verdict.json"),
            "cites_successor": text.count(SUCCESSOR_PREFIX)
                               + text.count("fixed_replication_verdict_rev2.json"),
        })
    unbound = [r["path"] for r in rows if r["cites_superseded"] and not r["cites_successor"]]
    return {"rows": rows, "unbound_consumers": unbound,
            "verdict": "SUPERSESSION_NOT_YET_BOUND" if unbound else "SUPERSESSION_BOUND"}


def measure_anchors(root: Path) -> dict:
    out = {}
    for rel in list(HARD_PINS) + CANARY:
        p = root / rel
        out[rel] = sha256_file(p) if p.is_file() else None
    return out


def check_hard_pins(anchors: dict) -> list:
    bad = []
    for rel, want in HARD_PINS.items():
        got = anchors.get(rel)
        if got is None or not got.startswith(want):
            bad.append({"path": rel, "expected_prefix": want, "measured": got})
    return bad


def run_controls(root: Path, pred: dict, succ: dict, anchors: dict) -> dict:
    ctl = {}
    # C1 no-write canary checked by caller after run; here mark precondition.
    ctl["C1_no_write_canary"] = "PENDING"
    # C2 chain mutation: rebind the successor's chain pin back to the superseded rev2 hash.
    m = copy.deepcopy(succ)
    m["chained_evidence_hashes"]["research_map/formulation_taxonomy.yaml"] = \
        "66bf917bd368ebd96ee46baa31fb435df106cb4e10152fa0baee8bdd51dfc232"
    ctl["C2_chain_mutation_detected"] = bool(resolve_chain(root, m)["unresolved"])
    # C3 numeric-leaf mutation: perturb a numeric leaf present in BOTH docs (an added-only
    # numeric leaf would classify as an expected addition and would not exercise the test).
    m = copy.deepcopy(succ)
    p_paths = {p: k for p, k, _ in leaf_walk(pred)}
    target = next((p for p, k, _ in leaf_walk(m)
                   if k == "num" and p_paths.get(p) == "num" and p not in VOLATILE_LEAVES),
                  None)
    if target is not None:
        node = m
        parts = target.strip("/").split("/")
        for part in parts[:-1]:
            node = node[int(part)] if isinstance(node, list) else node[part]
        last = parts[-1]
        if isinstance(node, list):
            node[int(last)] = float(node[int(last)]) + 1.0
        else:
            node[last] = float(node[last]) + 1.0
    ctl["C3_numeric_mutation_detected"] = target is not None and \
        compare_docs(pred, m)["verdict"] == "UNEXPECTED_DIFFERENCE"
    # C4 frozen-flag flip: stored true while the frozen pin still differs from disk.
    m = copy.deepcopy(succ)
    m["provenance"]["fixed_taxonomy_sha256_matches_on_disk"] = True
    ctl["C4_flag_flip_detected"] = not \
        frozen_flag_semantics(root, m)["flag_consistent_with_generator_semantics"]
    # C5 operator count: a copy of the first consumer that also cites the successor must have
    # that consumer's row leave the unbound set (per-consumer, not a global flip).
    prop = (root / CONSUMERS[0]).read_text()
    ov = operativity(root, {CONSUMERS[0]: prop + "\n" + SUCCESSOR_PREFIX})
    row0 = next(r for r in ov["rows"] if r["path"] == CONSUMERS[0])
    ctl["C5_operator_override_binds"] = (row0["cites_successor"] > 0
                                        and CONSUMERS[0] not in ov["unbound_consumers"])
    ctl_pass = all(v is True for k, v in ctl.items() if k != "C1_no_write_canary")
    ctl["controls_pass"] = ctl_pass
    return ctl


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(REPO_ROOT))
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    root = Path(args.root).resolve()

    anchors_before = measure_anchors(root)
    pin_failures = check_hard_pins(anchors_before)
    if pin_failures:
        report = {"schema": "w067-fixedverdict-rev2-indep/v1", "verdict": "ANCHOR_DRIFT",
                  "hard_pin_failures": pin_failures, "anchors_before": anchors_before}
        print(json.dumps(report, indent=2))
        return 2

    pred = json.loads((root / "numerics/protocol/fixed_replication_verdict.json").read_text())
    succ = json.loads((root / "numerics/protocol/fixed_replication_verdict_rev2.json").read_text())

    compare = compare_docs(pred, succ)
    chain = resolve_chain(root, succ)
    semantics = frozen_flag_semantics(root, succ)
    op = operativity(root)
    controls = run_controls(root, pred, succ, anchors_before)

    anchors_after = measure_anchors(root)
    canary_ok = anchors_after == anchors_before
    controls["C1_no_write_canary"] = canary_ok

    reproduced = {
        "numeric_leaves_equal_mine": compare["numeric_leaves_equal"],
        "numeric_leaves_differ_mine": compare["numeric_leaves_differ"],
        "declared_numeric_leaves_compared": (succ.get("numeric_delta_vs_superseded") or {})
                                            .get("numeric_leaves_compared"),
        "declared_max_abs_difference": (succ.get("numeric_delta_vs_superseded") or {})
                                       .get("max_abs_difference"),
        "declared_differing_leaves": (succ.get("numeric_delta_vs_superseded") or {})
                                     .get("differing_leaves"),
        "all_numeric_leaves_equal": compare["numeric_leaves_differ"] == 0,
    }

    hard = []
    if compare["verdict"] != "METADATA_ONLY":
        hard.append("successor differs from predecessor outside the declared rebind metadata")
    if chain["verdict"] != "ALL_RESOLVE":
        hard.append("successor declared-hash chain has unresolved entries")
    if not semantics["flag_consistent_with_generator_semantics"]:
        hard.append("fixed_taxonomy_sha256_matches_on_disk is inconsistent with the generator")
    if not controls.get("controls_pass"):
        hard.append("one or more in-memory controls failed")
    if not canary_ok:
        hard.append("anchor bytes moved during the run (no-write canary failed)")

    findings = []
    if semantics["field_name_reading_ambiguous"]:
        findings.append(
            "FIELD-NAME AMBIGUITY (non-blocking): successor carries the rebound pin "
            f"provenance.taxonomy_sha256={semantics['live_taxonomy_sha256'][:12]} (resolves on "
            f"disk) while provenance.fixed_taxonomy_sha256_matches_on_disk=false. Under the "
            f"generating script's definition the flag means 'the FROZEN RUN pin "
            f"{str(semantics['frozen_run_f0_pin'])[:12]} equals live taxonomy' -- false is "
            "correct there. Under the field NAME it reads 'this record's taxonomy pin does not "
            "match disk', which contradicts the rebound pin. The rebind block documents the "
            "intended reading; a fail-closed consumer keying on the bare boolean would misread "
            "the record as unbound.")
    if op["verdict"] == "SUPERSESSION_NOT_YET_BOUND":
        findings.append(
            "OPERATIVITY (adjudication input): live consumers still cite the superseded "
            "artifact without citing the successor at: " + ", ".join(op["unbound_consumers"])
            + ". The repair is therefore dischargeable-by-binding but NOT yet bound: until the "
              "audit adjudication (astra-life05-gnum-protocol-adjudication) or the controller "
              "binds fixed_replication_verdict_rev2.json#7954d2d355451e3d as the replication "
              "evidence of record, the C8 w067-provledger dissent remains live.")

    verdict = "HARD_FAILURE" if hard else (
        "REV2_METADATA_ONLY_AND_PINS_RESOLVE__SUPERSESSION_NOT_YET_BOUND"
        if op["verdict"] == "SUPERSESSION_NOT_YET_BOUND"
        else "REV2_METADATA_ONLY_AND_PINS_RESOLVE__SUPERSESSION_BOUND")

    report = {
        "schema": "w067-fixedverdict-rev2-indep/v1",
        "task_id": "W067-N0-FIXEDVERDICT-REV2-INDEP-01",
        "actor": "worker-067",
        "class_id": "AF-WCC-SCALAR-SPH",
        "node_id": "N0",
        "gate": "G-NUM",
        "authority_note": ("Advisory worker verification; does not set status=done, "
                           "validation_status=passed, or any gate verdict. Read-only on every "
                           "canonical path; wrote only under artifacts/worker-067/ and "
                           "runtime/state/worker-067_checkpoint_9.json."),
        "verdict": verdict,
        "hard_failures": hard,
        "findings": findings,
        "anchors_before": anchors_before,
        "anchors_after": anchors_after,
        "no_write_canary_ok": canary_ok,
        "compare": compare,
        "reproduced_claim": reproduced,
        "chain": chain,
        "frozen_flag_semantics": semantics,
        "operativity": op,
        "controls": controls,
        "next_falsifier": (
            "Withdrawn if any of: (a) either verdict artifact, the canonical taxonomy, the "
            "frozen run, or verify_fixed_scheme_independence.py no longer hashes to its pinned "
            "prefix at re-measurement (moving target); (b) a re-run of this checker finds any "
            "differing numeric leaf or any successor difference outside the declared rebind "
            "metadata (then the metadata-only claim is false); (c) the successor's declared "
            "chain has an unresolved entry; (d) a live consumer that cites dcad9623 without "
            "rev2 is re-pinned to rev2 by an authoritative event (then the operativity finding "
            "is discharged, and only that finding); (e) the rebind/naming ambiguity is removed "
            "by renaming or documenting the flag in the successor (then that finding is "
            "withdrawn)."),
        "not_claimed": [
            "no G-NUM verdict, no node completion, no gate self-pass",
            "no numerics_lock change; N1 remains locked and no solver artifact is touched",
            "no physics/censorship claim",
            "no repair of either artifact (CF-12 one canonical path, one owner)",
        ],
    }
    text = json.dumps(report, indent=2)
    if args.out:
        Path(args.out).write_text(text)
    print(text)
    return 1 if hard else 0


if __name__ == "__main__":
    sys.exit(main())
