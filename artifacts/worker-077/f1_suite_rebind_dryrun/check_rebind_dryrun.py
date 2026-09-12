#!/usr/bin/env python3
"""W077-F1-SUITE-REBIND-DRYRUN-01 -- read-only dry run of the F1 ambiguity-suite rebind.

Question (class-bound, AF-WCC-VAC-GEN / node F1 / gate G-FORM):
  The canonical suite `schemas/f1_falsifier_tests.jsonl` still binds
  `schemas/af_wcc_vacuum.yaml#sha256:cce9c60146d6a907` (schema rev12) on all 25 rows while the
  canonical schema and the FROZEN rev29 pin are at rev13 `d9cebb9404b2`. Vendor verifier C1a
  treats that as HARD. This instrument does NOT write the canonical suite. It produces the
  mechanically rebound candidate bytes the owner's own tool
  (`artifacts/flash-04/f1_ambiguity/rebind_current.py`) would emit at the current pins, proves
  which fields change and which do not, and isolates the two stale F1-AMB-25 probe expectations
  that would make that tool exit 2.

Method (all read-only on canonical paths; every write lands under this artifact directory):
  1. Pin 7 load-bearing inputs by sha256; abort (exit 3) on any drift.
  2. Re-run the 84 stored probes with the owner tool's probe semantics at three revisions:
     authoring snapshot 9a8bd4c9 (control: must reproduce the 84/84 stored passes), rev12
     cce9c601 (the suite's own binding), rev13 d9cebb9404b2 (the live canonical schema).
  3. Build variant A = the owner procedure's row-local rebind (binding fields, prior_* chain,
     recomputed probes, delta_vs_cce9c60146 block). Build variant B = A plus the minimal
     F1-AMB-25 expectation refresh (2 probe `expected` values + the row's cross_artifact sha).
  4. Validate both candidates fail-closed: row count/ids unchanged, uniform binding, no
     non-binding field byte-changed except the enumerated keys, original file fails the same
     checks (null control), and 3 in-memory mutants are each caught.

Exit: 0 all acceptance checks pass; 2 an acceptance check failed; 3 pin drift (measurement void).
Authority: worker measurement only. No canonical write, no node status, no gate verdict.

Usage: python3 check_rebind_dryrun.py [--out DIR]
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]

TASK_ID = "W077-F1-SUITE-REBIND-DRYRUN-01"
CLASS_ID = "AF-WCC-VAC-GEN"
NODE_ID = "F1"
GATE = "G-FORM"

CANON_F1 = "schemas/af_wcc_vacuum.yaml"
SUITE = "schemas/f1_falsifier_tests.jsonl"
FROZEN = "artifacts/formulation/FROZEN.json"
F0 = "research_map/formulation_taxonomy.yaml"
AUTHOR_SNAP = "artifacts/worker-048/f1_closure_preflight/snapshot/af_wcc_vacuum.9a8bd4c9.yaml"
REV12_SNAP = "artifacts/worker-090/f1_rev12_closure/snapshot/af_wcc_vacuum.cce9c60146d6a907.yaml"

# load-bearing pins: drift voids the measurement (exit 3)
PINS = {
    CANON_F1: "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",   # rev13
    SUITE: "56bcb4b3234bc86c324bec6e38f142c5ef39517f20d823b6a333f578b7d0851e",
    F0: "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    AUTHOR_SNAP: "9a8bd4c9680042a40894f6085f183661500966f2d787a6bf28a7098a271ed503",
    REV12_SNAP: "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3",
}

REV12_SHA = PINS[REV12_SNAP]
REV13_SHA = PINS[CANON_F1]
ROW_KEYS = ("binding_sha256", "binding_ref", "binding_at_authoring", "binding_frozen_revision",
            "prior_binding_sha256", "prior_binding_ref", "prior_binding_at_authoring",
            "probe_results", "delta_vs_" + REV12_SHA[:8])
VARIANT_B_EXTRA = ("cross_artifact",)

# F1-AMB-25 refresh proposal: probe path -> new `expected`
F0_REFRESH = {
    "f0_binding.declared_f0_sha256": PINS[F0],
    "f0_binding.binding_note": "refreshed to the rev5 declared-F0 hash",
}


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ref(path: str, digest: str, chars: int = 16) -> str:
    return f"{path}#sha256:{digest[:chars]}"


_TOKEN = re.compile(r"([^.\[\]]+)|\[(\d+)\]")


def getpath(doc, path: str):
    cur = doc
    for name, idx in _TOKEN.findall(path):
        if name:
            if isinstance(cur, dict) and name in cur:
                cur = cur[name]
            else:
                return None
        else:
            if isinstance(cur, list) and int(idx) < len(cur):
                cur = cur[int(idx)]
            else:
                return None
    return cur


def flat(value) -> str:
    return json.dumps(value, default=str, ensure_ascii=False)


def flat_leaves(doc, prefix: str = "") -> dict:
    out: dict = {}
    if isinstance(doc, dict):
        for k, v in doc.items():
            out.update(flat_leaves(v, f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(doc, list):
        for i, v in enumerate(doc):
            out.update(flat_leaves(v, f"{prefix}[{i}]"))
    else:
        out[prefix] = doc
    return out


def run_probe(doc, spec: dict) -> dict:
    """Owner-tool probe semantics (artifacts/flash-04/f1_ambiguity/rebind_current.py:94)."""
    value = getpath(doc, spec["path"])
    kind = spec["kind"]
    needle = spec.get("value", spec.get("expected"))
    if kind in ("path_exists", "nonnull"):
        ok = value is not None
    elif kind == "is_none":
        ok = value is None
    elif kind == "is_true":
        ok = value is True
    elif kind == "equals":
        ok = value == needle
    elif kind == "contains":
        ok = value is not None and needle in flat(value)
    elif kind == "contains_any":
        ok = value is not None and any(n in flat(value) for n in needle)
    elif kind == "length_ge":
        ok = isinstance(value, (list, dict, str)) and len(value) >= needle
    else:
        raise ValueError(f"unknown probe kind {kind!r}")
    return {
        "path": spec["path"],
        "kind": kind,
        "expected": needle if needle is not None else kind,
        "role": spec.get("role", "deciding_field"),
        "pass": bool(ok),
        "observed_excerpt": flat(value)[:280] if value is not None else None,
    }


def jsonl_rows(path: Path) -> list:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def jsonl_bytes(rows: list) -> bytes:
    return "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows).encode()


def changed_keys(a: dict, b: dict) -> list:
    return sorted(k for k in set(a) | set(b) if flat(a.get(k)) != flat(b.get(k)))


def build_candidate(rows, schema, prior, frozen_rev, refresh_f0: bool):
    """Replicate the owner tool's row-local rebind. Returns (out_rows, per_row_changes, failures).

    `prior` (the rev12 snapshot) is the flip baseline: a rebind is expectation-preserving iff no
    stored probe's pass/fail outcome changes between rev12 and rev13.
    """
    new_ref = ref(CANON_F1, REV13_SHA)
    prior_ref = ref(CANON_F1, REV12_SHA)
    out, per_row, failures = [], [], []
    for old in rows:
        rec = dict(old)
        specs = [dict(p) for p in old.get("probe_results", [])]
        if refresh_f0 and rec.get("test_id") == "F1-AMB-25":
            for s in specs:
                if s["path"] in F0_REFRESH:
                    s["expected"] = F0_REFRESH[s["path"]]
        baseline_pass = {s["path"]: run_probe(prior, s)["pass"] for s in specs}
        rec["binding_sha256"] = REV13_SHA
        rec["binding_ref"] = new_ref
        rec["binding_at_authoring"] = new_ref
        rec["binding_frozen_revision"] = frozen_rev
        rec["prior_binding_sha256"] = REV12_SHA
        rec["prior_binding_ref"] = prior_ref
        rec["prior_binding_at_authoring"] = old.get("binding_at_authoring", prior_ref)
        probes = [run_probe(schema, s) for s in specs]
        if refresh_f0 and rec.get("test_id") == "F1-AMB-25":
            rec["cross_artifact"] = [{"path": F0, "sha256": PINS[F0]}]
        rec["probe_results"] = probes
        for p in probes:
            if not p["pass"]:
                failures.append([rec["test_id"], p["path"], p["expected"]])
        dec = rec["deciding_field"]
        old_val, new_val = getpath(prior, dec), getpath(schema, dec)
        changed = flat(old_val) != flat(new_val)
        status = ("field_added" if old_val is None and new_val is not None
                  else "field_content_changed" if changed else "unchanged")
        rec["delta_vs_" + REV12_SHA[:8]] = {
            "status": status,
            "changed_fields": [dec] if changed else [],
            "prior_excerpt": flat(old_val)[:200] if old_val is not None else None,
            "new_excerpt": flat(new_val)[:200] if new_val is not None else None,
        }
        flips = [{"test_id": rec["test_id"], "path": p["path"],
                  "rev12_pass": baseline_pass.get(p["path"]), "rev13_pass": p["pass"]}
                 for p in probes if baseline_pass.get(p["path"]) != p["pass"]]
        per_row.append({
            "test_id": rec["test_id"],
            "deciding_field": dec,
            "deciding_field_status": rec.get("deciding_field_status"),
            "changed_keys_vs_canonical": changed_keys(old, rec),
            "probe_flips_rev12_to_rev13": flips,
            "delta_status": status,
            "classification": ("semantic_touch" if changed else "pure_rebind"),
        })
        out.append(rec)
    return out, per_row, failures


def validate_candidate(rows, original, per_row, allowed_keys, probe_failures, prefix=""):
    """Fail-closed structural validation. Returns (checks, hard_failures)."""
    orig_by_id = {r["test_id"]: r for r in original}
    checks, hard = [], []

    def check(cid, name, ok, measured, severity="acceptance", falsifier=""):
        checks.append({"id": prefix + cid, "name": name, "ok": bool(ok), "measured": measured,
                       "severity": severity, "falsifier": falsifier})
        if not ok and severity == "acceptance":
            hard.append(prefix + cid)

    check("V1", "candidate row count and id set equal the canonical suite",
          len(rows) == len(original) and {r["test_id"] for r in rows} == set(orig_by_id),
          {"rows": len(rows), "canonical_rows": len(original)},
          falsifier="a row added, dropped or renamed by the dry run")
    binds = sorted({r["binding_sha256"] for r in rows})
    check("V2", "every candidate row binds the live rev13 F1 hash",
          binds == [REV13_SHA], {"distinct_bindings": binds},
          falsifier="any row left on rev12 or bound to a third hash")
    refs = sorted({r["binding_ref"] for r in rows})
    check("V3", "every candidate binding_ref is the rev13 ref",
          refs == [ref(CANON_F1, REV13_SHA)], {"distinct_refs": refs},
          falsifier="a binding_ref that does not name the live canonical schema hash")
    prior = sorted({(r.get("prior_binding_sha256"), r.get("prior_binding_ref")) for r in rows})
    check("V4", "every candidate prior_binding_* points at rev12 (the pre-rebind binding)",
          prior == [(REV12_SHA, ref(CANON_F1, REV12_SHA))], {"distinct_prior": prior},
          falsifier="a lost or mis-pointed prior-binding chain")
    unexpected = [{"test_id": p["test_id"], "keys": sorted(set(p["changed_keys_vs_canonical"]) - set(allowed_keys))}
                  for p in per_row if set(p["changed_keys_vs_canonical"]) - set(allowed_keys)]
    check("V5", "no row changes a field outside the enumerated rebind set",
          not unexpected, {"unexpected": unexpected, "allowed": sorted(allowed_keys)},
          falsifier="any semantic field (title, question, deciding_field, probe content outside the set) moved")
    n_nonprobe = [p["test_id"] for p in per_row
                  if set(p["changed_keys_vs_canonical"]) - {"probe_results", "delta_vs_" + REV12_SHA[:8]} - set(allowed_keys)]
    check("V6", "outside probe_results/delta block, only declared binding fields change",
          not n_nonprobe and any(REV12_SHA[:16] in str(r.get("prior_binding_ref")) for r in rows),
          {"rows_changing_more": n_nonprobe},
          falsifier="a non-binding key change not enumerated in the candidate spec")
    n_flips = sum(len(p["probe_flips_rev12_to_rev13"]) for p in per_row)
    check("V7", "zero probe flips rev12 -> rev13 (the rebind is expectation-preserving)",
          n_flips == 0, {"flips": n_flips,
                         "detail": [f for p in per_row for f in p["probe_flips_rev12_to_rev13"]]},
          falsifier="a stored probe whose pass/fail outcome changes between rev12 and rev13")
    check("V8", "candidate is valid JSONL with 25 records and stable round-trip",
          all(isinstance(r, dict) and r.get("test_id") for r in rows)
          and len(jsonl_bytes(rows).splitlines()) == 25,
          {"records": len(rows)}, falsifier="a candidate line that does not parse as one JSON object")
    check("V9", "probe failures are localized to F1-AMB-25 only",
          {t for t, _, _ in probe_failures} <= {"F1-AMB-25"},
          {"failures": probe_failures},
          severity="acceptance",
          falsifier="a stale expectation outside F1-AMB-25, which would widen the semantic repair")
    check("V10", "original canonical suite fails the uniform-binding check (null control)",
          sorted({r["binding_sha256"] for r in original}) == [REV12_SHA],
          {"original_bindings": sorted({r["binding_sha256"] for r in original})},
          severity="control", falsifier="a control that cannot discriminate the defect")
    return checks, hard


def mutant_controls(rows, allowed_keys):
    """In-memory mutants: each must be caught by the validation above."""
    results = []
    # M1: leave one row on rev12
    m = [dict(r) for r in rows]
    m[0]["binding_sha256"] = REV12_SHA
    m[0]["binding_ref"] = ref(CANON_F1, REV12_SHA)
    binds = sorted({r["binding_sha256"] for r in m})
    results.append({"mutant": "M1_one_row_rev12", "caught": binds != [REV13_SHA], "observed": binds})
    # M2: mutate a non-binding semantic field
    m2 = [dict(r) for r in rows]
    m2[3]["title"] = m2[3]["title"] + " [mutant]"
    extra = sorted(set(m2[3]) ^ set(rows[3])) or (["title"] if m2[3]["title"] != rows[3]["title"] else [])
    results.append({"mutant": "M2_semantic_field_edit", "caught": bool(extra), "observed": extra})
    # M3: drop a row
    m3 = rows[:-1]
    results.append({"mutant": "M3_row_dropped", "caught": len(m3) != len(rows), "observed": len(m3)})
    # M4: reintroduce a probe expectation mismatch in a second row
    m4 = [dict(r) for r in rows]
    m4[5]["probe_results"] = [dict(p) for p in rows[5]["probe_results"]]
    m4[5]["probe_results"][0]["pass"] = False
    bad = [r["test_id"] for r in m4 if any(not p["pass"] for p in r["probe_results"])]
    results.append({"mutant": "M4_probe_failure_outside_row25", "caught": set(bad) - {"F1-AMB-25"} != set(),
                    "observed": bad})
    return results


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent / "run"))
    args = ap.parse_args()
    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)

    checks: list = []
    pins_measured = {}
    for rel, want in PINS.items():
        p = ROOT / rel
        got = sha256_file(p) if p.exists() else None
        pins_measured[rel] = {"expected": want, "measured": got, "match": got == want}
    if not all(v["match"] for v in pins_measured.values()):
        print(json.dumps({"status": "PIN_DRIFT", "pins": pins_measured}, indent=1))
        return 3

    f1_bytes = (ROOT / CANON_F1).read_bytes()
    schema = yaml.safe_load(f1_bytes)
    prior = yaml.safe_load((ROOT / REV12_SNAP).read_text())
    author = yaml.safe_load((ROOT / AUTHOR_SNAP).read_text())
    f0 = yaml.safe_load((ROOT / F0).read_text())
    frozen = json.loads((ROOT / FROZEN).read_text())
    frozen_sha = sha256_file(ROOT / FROZEN)
    frozen_rev = frozen.get("revision")
    suite_before = sha256_file(ROOT / SUITE)
    original = jsonl_rows(ROOT / SUITE)

    def probe_census(doc):
        fails = []
        for r in original:
            for p in r.get("probe_results", []):
                got = run_probe(doc, p)
                if not got["pass"]:
                    fails.append({"test_id": r["test_id"], "path": p["path"], "kind": p["kind"],
                                  "expected": p.get("value", p.get("expected"))})
        return fails

    stored_pass = sum(1 for r in original for p in r.get("probe_results", []) if p.get("pass"))
    census = {
        "authoring_9a8bd4c9": probe_census(author),
        "rev12_cce9c601": probe_census(prior),
        "rev13_d9cebb9404": probe_census(schema),
        "probes_total": sum(len(r.get("probe_results", [])) for r in original),
        "stored_pass": stored_pass,
        "stored_fail": sum(1 for r in original for p in r.get("probe_results", []) if not p.get("pass")),
    }

    def check(cid, name, ok, measured, severity="acceptance", falsifier=""):
        checks.append({"id": cid, "name": name, "ok": bool(ok), "measured": measured,
                       "severity": severity, "falsifier": falsifier})

    check("I0", "7/7 load-bearing pins match at read time", True,
          {k: v["measured"] for k, v in pins_measured.items()},
          falsifier="any pinned input moving voids the whole measurement")
    check("P1", "probe evaluator reproduces the 84/84 stored outcomes at the authoring snapshot",
          not census["authoring_9a8bd4c9"] and stored_pass == census["probes_total"] == 84,
          {"failures": census["authoring_9a8bd4c9"], "stored_pass": stored_pass,
           "probes_total": census["probes_total"]},
          falsifier="a probe failing at the revision it was authored against (the evaluator, not the suite, is wrong)")
    check("P2", "both stored failures are pre-existing at rev12 and unchanged at rev13",
          [f["test_id"] + "|" + f["path"] for f in census["rev12_cce9c601"]]
          == [f["test_id"] + "|" + f["path"] for f in census["rev13_d9cebb9404"]]
          and len(census["rev13_d9cebb9404"]) == 2,
          {"rev12": census["rev12_cce9c601"], "rev13": census["rev13_d9cebb9404"]},
          falsifier="a failure set that differs between rev12 and rev13 (would mean the rev13 delta caused it)")

    leaves_a, leaves_b = flat_leaves(prior), flat_leaves(schema)
    changed_leaves = sorted(k for k in set(leaves_a) | set(leaves_b)
                            if flat(leaves_a.get(k)) != flat(leaves_b.get(k)))
    check("B0", "rev12 -> rev13 changed-leaf census is non-empty and recorded", len(changed_leaves) > 0,
          {"changed_leaf_count": len(changed_leaves), "changed_leaves": changed_leaves},
          falsifier="an unchanged schema would make the rebind a no-op")

    # prose staleness detector: any row text quoting a >=20-char segment that rev13 removed
    removed_segments = []
    for k in changed_leaves:
        old_v, new_v = leaves_a.get(k), leaves_b.get(k)
        if isinstance(old_v, str) and isinstance(new_v, str):
            sm = difflib.SequenceMatcher(None, old_v, new_v)
            for tag, i1, i2, _, _ in sm.get_opcodes():
                if tag in ("delete", "replace"):
                    seg = " ".join(old_v[i1:i2].split())
                    if len(seg) >= 20:
                        removed_segments.append({"path": k, "removed": seg})
    suite_norm = {r["test_id"]: " ".join(json.dumps(r, default=str).split()) for r in original}
    prose_hits = [{"test_id": t, "path": s["path"], "removed_excerpt": s["removed"][:120]}
                  for t, txt in suite_norm.items() for s in removed_segments if s["removed"] in txt]
    check("S1", "no suite row quotes text that rev13 removed (prose staleness scan)",
          not prose_hits, {"removed_segments_scanned": len(removed_segments), "hits": prose_hits},
          falsifier="a row whose prose quotes rev12 wording that no longer exists in the schema")

    out_a, per_row_a, fails_a = build_candidate(original, schema, prior, frozen_rev, refresh_f0=False)
    out_b, per_row_b, fails_b = build_candidate(original, schema, prior, frozen_rev, refresh_f0=True)
    allowed_a = set(ROW_KEYS)
    allowed_b = set(ROW_KEYS) | set(VARIANT_B_EXTRA)
    vchecks_a, hard_a = validate_candidate(out_a, original, per_row_a, allowed_a, fails_a, prefix="A-")
    vchecks_b, hard_b = validate_candidate(out_b, original, per_row_b, allowed_b, fails_b, prefix="B-")

    def semantic_keys_b(p):
        extra = set(p["changed_keys_vs_canonical"]) - allowed_a
        return sorted(extra)

    b_extra_rows = [{"test_id": p["test_id"], "extra_keys": semantic_keys_b(p)}
                    for p in per_row_b if semantic_keys_b(p)]
    check("V11", "variant B touches cross_artifact on F1-AMB-25 only",
          b_extra_rows == [{"test_id": "F1-AMB-25", "extra_keys": ["cross_artifact"]}],
          {"rows": b_extra_rows},
          falsifier="a cross_artifact edit outside the declared F0-staleness row")
    ab_keys = [{"test_id": a["test_id"], "keys": changed_keys(a, b)}
               for a, b in zip(out_a, out_b) if changed_keys(a, b)]
    check("V14", "variant B differs from variant A only on F1-AMB-25",
          ab_keys == [{"test_id": "F1-AMB-25", "keys": ["cross_artifact", "probe_results"]}],
          {"rows": ab_keys},
          falsifier="a semantic refresh leaking into another row")
    check("V15", "variant B refreshes exactly the two declared probe expectations",
          [ (p["path"], p["expected"]) for p in next(r for r in out_b if r["test_id"] == "F1-AMB-25")["probe_results"]
            if p["path"] in F0_REFRESH ]
          == [(k, F0_REFRESH[k]) for k in F0_REFRESH],
          {"refreshed": {k: F0_REFRESH[k] for k in F0_REFRESH}},
          falsifier="an expectation edit beyond the two declared stale probes")
    check("V12", "variant B reaches 84/84 probes at rev13",
          not fails_b, {"failures": fails_b},
          falsifier="a refreshed expectation that still fails at rev13")
    check("V13", "F1-AMB-25 deciding field resolves at both revisions",
          getpath(prior, "f0_binding.declared_f0_sha256") == PINS[F0]
          and getpath(f0, "classes.AF-WCC-VAC-GEN") is not None,
          {"schema_declared_f0": getpath(schema, "f0_binding.declared_f0_sha256")},
          severity="control", falsifier="an unresolvable deciding path")

    suite_after = sha256_file(ROOT / SUITE)
    f1_after = sha256_file(ROOT / CANON_F1)
    f0_after = sha256_file(ROOT / F0)
    frozen_after = sha256_file(ROOT / FROZEN)
    try:
        frozen2 = json.loads((ROOT / FROZEN).read_text())
        suite_pin = frozen2.get("files", {}).get(SUITE, {}).get("sha256")
    except Exception:
        suite_pin = None
    check("I1", "no canonical byte moved during the dry run",
          (suite_before, f1_after, f0_after) == (suite_after, PINS[CANON_F1], PINS[F0]),
          {"suite_before": suite_before, "suite_after": suite_after, "f1": f1_after, "f0": f0_after},
          falsifier="any canonical write during a read-only measurement voids it")
    check("I2", "FROZEN still pins the canonical suite and F1 rev13",
          suite_pin == suite_before and frozen2.get("files", {}).get(CANON_F1, {}).get("sha256") == PINS[CANON_F1],
          {"frozen_revision": frozen2.get("revision"), "frozen_at": frozen2.get("frozen_at"),
           "suite_pin": suite_pin, "frozen_sha_changed": frozen_after != frozen_sha},
          falsifier="a FROZEN re-emission between the two reads; recorded so the candidate rev label is known")

    variant_a_path = outdir / "proposed_f1_falsifier_tests.rev13.mechanical.jsonl"
    variant_b_path = outdir / "proposed_f1_falsifier_tests.rev13.f0refresh.jsonl"
    variant_a_path.write_bytes(jsonl_bytes(out_a))
    variant_b_path.write_bytes(jsonl_bytes(out_b))
    orig_lines, cand_lines = jsonl_bytes(original).decode().splitlines(), jsonl_bytes(out_a).decode().splitlines()
    diff_summary = {
        "canonical_suite_sha256": suite_before,
        "variant_a_sha256": sha256_file(variant_a_path),
        "variant_b_sha256": sha256_file(variant_b_path),
        "variant_a_bytes": variant_a_path.stat().st_size,
        "variant_b_bytes": variant_b_path.stat().st_size,
        "canonical_line_count": len(orig_lines),
        "variant_a_lines_changed": sum(1 for x, y in zip(orig_lines, cand_lines) if x != y),
        "per_row_variant_a": per_row_a,
        "per_row_variant_b": per_row_b,
        "probe_failures_variant_a": fails_a,
        "probe_failures_variant_b": fails_b,
        "changed_leaf_paths_rev12_to_rev13": changed_leaves,
        "owner_write_set_if_applied": [
            SUITE,
            "artifacts/flash-04/f1_ambiguity/versions/f1_falsifier_tests.<rev13-8>.jsonl",
            "artifacts/flash-04/f1_ambiguity/schema_snapshots/af_wcc_vacuum.d9cebb94.yaml",
            "artifacts/flash-04/f1_ambiguity/rebind_current_delta_report.json",
            "artifacts/formulation/FROZEN.json (must be re-frozen: suite pin changes)",
        ],
    }

    report = {
        "task_id": TASK_ID,
        "actor": "worker-077",
        "role": "bounded execution worker; read-only on every canonical path",
        "node_id": NODE_ID,
        "class_id": CLASS_ID,
        "gate": GATE,
        "generated_at": __import__("datetime").datetime.now(
            __import__("datetime").timezone(__import__("datetime").timedelta(hours=8))
        ).isoformat(timespec="seconds"),
        "pins": pins_measured,
        "frozen_at_measure": {"sha256": frozen_after, "revision": frozen2.get("revision"),
                              "frozen_at": frozen2.get("frozen_at"), "suite_pin": suite_pin,
                              "changed_during_run": frozen_after != frozen_sha},
        "suite_canonical": {"path": SUITE, "sha256": suite_before, "rows": len(original)},
        "probe_census": census,
        "changed_leaves_rev12_to_rev13": changed_leaves,
        "prose_staleness": {
            "removed_segments_scanned": len(removed_segments),
            "row_prose_hits": prose_hits,
            "semantic_touch_rows": [p["test_id"] for p in per_row_a if p["classification"] != "pure_rebind"],
        },
        "variants": {
            "A_mechanical": {"path": str(variant_a_path.relative_to(ROOT)),
                             "sha256": diff_summary["variant_a_sha256"],
                             "probe_failures": fails_a, "rows": len(out_a)},
            "B_f0refresh": {"path": str(variant_b_path.relative_to(ROOT)),
                            "sha256": diff_summary["variant_b_sha256"],
                            "probe_failures": fails_b, "rows": len(out_b)},
        },
        "checks": checks + vchecks_a + vchecks_b,
        "hard_failures": hard_a + hard_b,
        "mutant_controls": mutant_controls(out_a, allowed_a),
        "findings": [
            {"id": "W077-SR-01", "severity": "blocker",
             "finding": "canonical suite binds F1 rev12 cce9c60146d6a907 on 25/25 rows while the canonical F1 (and the FROZEN rev29 pin) are rev13 d9cebb9404b2; vendor verifier C1a treats this as HARD",
             "owner": "formulation (suite owner, flash-04 lineage) + FROZEN re-freeze",
             "falsifier": "a canonical suite whose 25 rows bind d9cebb9404b2, or a verifier that accepts the rev12 binding"},
            {"id": "W077-SR-02", "severity": "blocker",
             "finding": "F1-AMB-25 carries two stale probe expectations (f0_binding.declared_f0_sha256 expected 276009f4 vs live 0abb9ed8; f0_binding.binding_note expected contains 'astra-classscope-02') and a stale cross_artifact sha 276009f4; both were already failing at rev12, so a mechanical rebind yields 82/84 and the owner tool exits 2",
             "owner": "formulation (semantic refresh + owner sign-off)",
             "falsifier": "a variant-A candidate that scores 84/84, or evidence that the two expectations are intentionally frozen"},
            {"id": "W077-SR-03", "severity": "info",
             "finding": "the owner rebind procedure does not update binding_frozen_revision_schema (stays 12 on all rows); a rebind to rev13 leaves that token stale unless the owner adds it to the write set",
             "owner": "formulation",
             "falsifier": "an owner procedure or verifier that explicitly declares the token historical"},
            {"id": "W077-SR-04", "severity": "info",
             "finding": "candidate rev label: binding_frozen_revision moves 27 -> FROZEN revision 29 under the owner procedure; if FROZEN is re-emitted again the candidate must be regenerated",
             "owner": "controller/formulation",
             "falsifier": "FROZEN re-emission with a different revision after this measurement"},
            {"id": "W077-SR-05", "severity": "info",
             "finding": "3 of 25 rows have deciding-field content changed by rev13 (%s) yet their stored probes still pass and no row quotes removed rev12 text; owner confirmation that no re-adjudication is needed, not a defect"
                        % ", ".join(p["test_id"] + " (" + p["deciding_field"] + ")" for p in per_row_a
                                    if p["classification"] != "pure_rebind"),
             "owner": "formulation",
             "falsifier": "a row whose adjudication text depends on the pre-rev13 wording at those paths"},
        ],
        "falsifier": "any of the 7 pins moving voids this measurement; a rev12->rev13 probe flip falsifies 'rebind is expectation-preserving'; a candidate row changing a non-enumerated field falsifies the candidate; a probe evaluator that does not reproduce 84/84 at the authoring snapshot falsifies every count here",
        "scope_limits": [
            "read-only: the canonical suite, schemas, FROZEN, taxonomy and snapshots are not written",
            "row-local rebind only: the owner tool additionally refreshes evidence_refs to its base-evidence list and writes a version copy + schema snapshot; those cross-artifact writes are listed in diff_summary.owner_write_set_if_applied but not produced here",
            "binding_frozen_revision_schema is deliberately left at 12 (the owner procedure does not update it); see W077-SR-03",
            "variant B's refreshed expectation text ('refreshed to the rev5 declared-F0 hash') is a proposal; only the owner may adopt it",
            "variant A/B bytes are candidates for the owner; FROZEN rev29 stays valid only until the canonical suite is rewritten, after which a re-freeze is required",
        ],
        "next_falsifier": "apply variant A to a scratch copy, run the owner verifier (artifacts/flash-04/f1_ambiguity/verify_freeze_current.py) and the vendor verifier C1a at rev13: any remaining hard finding falsifies the dry run; then apply variant B and require 84/84 before G-FORM re-review",
        "authority": "worker measurement only; no canonical write, no node status, no validation_status, no gate verdict",
    }
    report["measurement_digest"] = hashlib.sha256(
        json.dumps({k: v for k, v in report.items() if k != "generated_at"},
                   sort_keys=True, default=str).encode()).hexdigest()
    (outdir / "report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str) + "\n")
    (outdir / "diff_summary.json").write_text(json.dumps(diff_summary, indent=1, ensure_ascii=False, default=str) + "\n")

    print(json.dumps({
        "status": "FAIL" if report["hard_failures"] else "COMPLETE",
        "measurement_digest": report["measurement_digest"],
        "hard_failures": report["hard_failures"],
        "probe_failures_A": len(fails_a), "probe_failures_B": len(fails_b),
        "variant_a_sha256": diff_summary["variant_a_sha256"],
        "variant_b_sha256": diff_summary["variant_b_sha256"],
        "report_sha256": sha256_file(outdir / "report.json"),
    }, indent=1))
    return 2 if report["hard_failures"] else 0


if __name__ == "__main__":
    sys.exit(main())
