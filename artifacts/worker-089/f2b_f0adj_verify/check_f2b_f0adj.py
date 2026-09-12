#!/usr/bin/env python3
"""
W089-F2B-F0ADJ-02 -- independent, controlled verification of the F0 mirror-conflict
dependency claims as they bind AF-SCC-C0-VAC-GEN (F2b).

Inputs (read-only; nothing outside this artifact directory is ever written):
  research_map/formulation_taxonomy.yaml                      (declared F0 taxonomy)
  artifacts/formulation/formulation_taxonomy.yaml             (class-contract supplement)
  schemas/af_scc_c0_vacuum.yaml                               (F2b, target class)
  schemas/af_scc_c2_vacuum.yaml, schemas/af_wcc_vacuum.yaml   (siblings)
  artifacts/formulation/FROZEN.json                           (frozen manifest)
  artifacts/formulation/evidence/f0_mirror_conflict.json      (claim under test)
  artifacts/formulation/evidence/taxonomy_consistency.json    (pinned evidence)
  artifacts/formulation/tools/check_taxonomy_consistency.py   (static dependency only)

Scope: mechanical only. This script does NOT adjudicate REC-1 vs REC-2, does NOT
review semantics, and is NOT a G-F0/G-FORM gate accept.

Usage: python3 check_f2b_f0adj.py [--window 60] [--interval 10]
Exit 0 = all checks pass and all planted controls are caught.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]  # artifacts/worker-089/<this>/ -> repo root

CANON = "research_map/formulation_taxonomy.yaml"
SUPP = "artifacts/formulation/formulation_taxonomy.yaml"
F2B = "schemas/af_scc_c0_vacuum.yaml"
F2A = "schemas/af_scc_c2_vacuum.yaml"
F1 = "schemas/af_wcc_vacuum.yaml"
FROZEN = "artifacts/formulation/FROZEN.json"
CONFLICT = "artifacts/formulation/evidence/f0_mirror_conflict.json"
CONSIST = "artifacts/formulation/evidence/taxonomy_consistency.json"
CONSIST_PY = "artifacts/formulation/tools/check_taxonomy_consistency.py"
CLASS = "AF-SCC-C0-VAC-GEN"
SCHEMAS = (F1, F2A, F2B)

# Hash pins this report binds to (measured 2026-09-12T00:2x+08:00).
PINS = {
    F2B: "1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508",
    F2A: "b6123750b37d8bee1e92eeb025979a6afdf3b29a33331a9d8499e21398d13fb2",
    F1: "9a8bd4c9680042a40894f6085f183661500966f2d787a6bf28a7098a271ed503",
    CANON: "276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc",
    SUPP: "c8e979a1eb48969be3b102e1e18203eb9e09b4e10fca3ef341854fdd73bae83f",
}

CANON_OWN_KEYS = ("class_ids", "classes", "transfer_rules")
SUPP_OWN_KEYS = ("class_contracts", "axis_registry", "implication_ledger")
POINTER_REQUIRED_KEYS = ("components", "conclusion_type", "exclusions", "positive_test_case")


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def digest(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def load_yaml(rel: str):
    return yaml.safe_load((ROOT / rel).read_text())


def load_json(rel: str):
    return json.loads((ROOT / rel).read_text())


def parse_pointer(ptr: str):
    """Return (path, fragment) or (None, None)."""
    if not isinstance(ptr, str) or "#" not in ptr:
        return None, None
    path, frag = ptr.split("#", 1)
    return path, frag


def resolve_fragment(doc, fragment: str):
    cur = doc
    for part in fragment.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return False, None
        cur = cur[part]
    return True, cur


def build_ctx():
    files = (CANON, SUPP, F2B, F2A, F1, FROZEN, CONFLICT, CONSIST, CONSIST_PY)
    raw = {rel: (ROOT / rel).read_bytes() for rel in files}
    return {
        "raw": raw,
        "hash": {rel: digest(b) for rel, b in raw.items()},
        "canon": load_yaml(CANON),
        "supp": load_yaml(SUPP),
        "f2b": load_yaml(F2B),
        "f2a": load_yaml(F2A),
        "f1": load_yaml(F1),
        "frozen": load_json(FROZEN),
        "conflict": load_json(CONFLICT),
        "consist": load_json(CONSIST),
        "consist_py": raw[CONSIST_PY].decode("utf-8", "replace"),
        "notes": [],
    }


# ---------------------------------------------------------------- checks ----
def c1_input_pins(ctx):
    """Measured hashes equal the hash pins AND the conflict evidence's own measurement."""
    ev = ctx["conflict"].get("measured", {})
    errs = []
    for rel, pin in PINS.items():
        if ctx["hash"][rel] != pin:
            errs.append(f"{rel}: measured {ctx['hash'][rel][:12]} != pin {pin[:12]}")
    m = ev.get("canonical", {})
    if m.get("path") != CANON or m.get("sha256") != ctx["hash"][CANON]:
        errs.append("conflict evidence 'canonical' measurement disagrees with measured bytes")
    if m.get("bytes") != len(ctx["raw"][CANON]):
        errs.append("conflict evidence canonical byte count disagrees")
    m = ev.get("authoring", {})
    if m.get("path") != SUPP or m.get("sha256") != ctx["hash"][SUPP]:
        errs.append("conflict evidence 'authoring' measurement disagrees with measured bytes")
    if m.get("bytes") != len(ctx["raw"][SUPP]):
        errs.append("conflict evidence authoring byte count disagrees")
    return ("fail" if errs else "pass",
            "; ".join(errs) if errs else
            f"5/5 pins match; conflict-evidence path/hash/byte measurements match live bytes "
            f"(canonical {ctx['hash'][CANON][:12]}, supplement {ctx['hash'][SUPP][:12]})",
            [f"{CANON}#{ctx['hash'][CANON][:12]}", f"{SUPP}#{ctx['hash'][SUPP][:12]}", CONFLICT])


def c2_canonical_partition(ctx):
    """Canonical declared-F0 carries class_ids/classes/transfer_rules and NOT the supplement keys."""
    has = {k: k in ctx["canon"] for k in CANON_OWN_KEYS}
    lacks = {k: k not in ctx["canon"] for k in SUPP_OWN_KEYS}
    ok = all(has.values()) and all(lacks.values())
    detail = f"has {has}; lacks {lacks}"
    return ("pass" if ok else "fail", detail, [CANON])


def c3_supplement_partition(ctx):
    """Supplement carries class_contracts/axis_registry/implication_ledger and NOT the canonical keys."""
    has = {k: k in ctx["supp"] for k in SUPP_OWN_KEYS}
    lacks = {k: k not in ctx["supp"] for k in CANON_OWN_KEYS}
    ok = all(has.values()) and all(lacks.values())
    detail = f"has {has}; lacks {lacks}"
    return ("pass" if ok else "fail", detail, [SUPP])


def c4_f2b_pointer_resolves_in_supplement(ctx):
    """F2b's class_contract_pointer names the supplement and its fragment resolves there."""
    ptr = ctx["f2b"].get("class_contract_pointer")
    path, frag = parse_pointer(ptr)
    errs = []
    if path != SUPP:
        errs.append(f"pointer path {path!r} != {SUPP!r}")
    if frag != f"class_contracts.{CLASS}":
        errs.append(f"pointer fragment {frag!r} != class_contracts.{CLASS}")
    resolved, node = resolve_fragment(ctx["supp"], frag or "")
    if not resolved or not isinstance(node, dict):
        errs.append("fragment does not resolve to a mapping in the supplement")
    else:
        missing = [k for k in POINTER_REQUIRED_KEYS if k not in node]
        if missing:
            errs.append(f"resolved class contract missing keys {missing}")
    return ("fail" if errs else "pass",
            "; ".join(errs) if errs else
            f"{ptr} resolves to a mapping with all of {list(POINTER_REQUIRED_KEYS)}",
            [F2B, SUPP])


def c5_f2b_pointer_absent_from_canonical(ctx):
    """The same fragment must NOT resolve in the canonical taxonomy (pointer is load-bearing)."""
    ptr = ctx["f2b"].get("class_contract_pointer")
    _, frag = parse_pointer(ptr)
    resolved, _ = resolve_fragment(ctx["canon"], frag or "")
    return ("fail" if resolved else "pass",
            "fragment unexpectedly resolves in canonical" if resolved else
            f"fragment {frag} does not resolve in the canonical taxonomy",
            [F2B, CANON])


def c6_f2b_f0_binding_measured(ctx):
    """F2b's f0_binding paths/hash equal live measurements."""
    b = ctx["f2b"].get("f0_binding") or {}
    errs = []
    if b.get("declared_f0_artifact") != CANON:
        errs.append(f"declared_f0_artifact {b.get('declared_f0_artifact')!r} != {CANON!r}")
    if b.get("declared_f0_sha256") != ctx["hash"][CANON]:
        errs.append("declared_f0_sha256 != measured canonical hash")
    if b.get("class_contract_supplement") != SUPP:
        errs.append(f"class_contract_supplement {b.get('class_contract_supplement')!r} != {SUPP!r}")
    if b.get("consistency_evidence") != CONSIST:
        errs.append("consistency_evidence path mismatch")
    return ("fail" if errs else "pass",
            "; ".join(errs) if errs else
            f"declared F0 {b.get('declared_f0_sha256','')[:12]} == measured; supplement path pinned",
            [F2B, CANON, SUPP])


def c7_all_schema_bindings(ctx):
    """All three frozen schemas: pointer resolves in supplement; f0_binding matches measured."""
    errs = []
    checked = []
    for rel in SCHEMAS:
        s = {"schemas/af_wcc_vacuum.yaml": ctx["f1"],
             "schemas/af_scc_c2_vacuum.yaml": ctx["f2a"],
             "schemas/af_scc_c0_vacuum.yaml": ctx["f2b"]}[rel]
        cid = s.get("class_id")
        path, frag = parse_pointer(s.get("class_contract_pointer"))
        if path != SUPP:
            errs.append(f"{rel}: pointer path != supplement")
        resolved, node = resolve_fragment(ctx["supp"], frag or "")
        if not (resolved and isinstance(node, dict)):
            errs.append(f"{rel}: pointer fragment {frag} unresolved in supplement")
        if frag != f"class_contracts.{cid}":
            errs.append(f"{rel}: pointer fragment {frag} != class_contracts.{cid}")
        b = s.get("f0_binding") or {}
        if b.get("declared_f0_artifact") != CANON or b.get("declared_f0_sha256") != ctx["hash"][CANON]:
            errs.append(f"{rel}: f0_binding does not match measured canonical")
        checked.append(f"{rel}:{cid}")
    return ("fail" if errs else "pass",
            "; ".join(errs) if errs else
            f"3/3 schemas resolve into the supplement and bind canonical {ctx['hash'][CANON][:12]}; "
            f"checked {checked}",
            list(SCHEMAS) + [CANON, SUPP])


def c8_destructive_simulation(ctx):
    """Structural simulation of byte-identical publication in either direction."""
    errs = []
    # canonical replaced by supplement bytes -> canonical-only roles lost
    sim = copy.deepcopy(ctx["supp"])
    lost_canon = [k for k in CANON_OWN_KEYS if k not in sim]
    if set(lost_canon) != set(CANON_OWN_KEYS):
        errs.append("supplement-as-canonical did not lose all canonical-only keys")
    # supplement replaced by canonical bytes -> supplement-only roles lost + pointer dangles
    sim2 = copy.deepcopy(ctx["canon"])
    lost_supp = [k for k in SUPP_OWN_KEYS if k not in sim2]
    if set(lost_supp) != set(SUPP_OWN_KEYS):
        errs.append("canonical-as-supplement did not lose all supplement-only keys")
    _, frag = parse_pointer(ctx["f2b"].get("class_contract_pointer"))
    dangles = not resolve_fragment(sim2, frag or "")[0]
    if not dangles:
        errs.append("pointer did not dangle under canonical-as-supplement simulation")
    return ("fail" if errs else "pass",
            "; ".join(errs) if errs else
            f"supplement-as-canonical loses {lost_canon}; canonical-as-supplement loses {lost_supp} "
            f"and dangles {frag}",
            [CANON, SUPP, F2B])


def c9_frozen_manifest_pins(ctx):
    """FROZEN.json files + logical_artifacts entries match measured bytes; mirrors declared NONE."""
    fr = ctx["frozen"]
    errs = []
    files = fr.get("files", {})
    for rel in (CANON, SUPP, F2B):
        ent = files.get(rel) or {}
        if ent.get("sha256") != ctx["hash"][rel]:
            errs.append(f"FROZEN files[{rel}] hash != measured")
        if ent.get("bytes") not in (None, len(ctx["raw"][rel])):
            errs.append(f"FROZEN files[{rel}] byte count != measured")
    la = fr.get("logical_artifacts", {})
    for name, rel in (("F0-declared-taxonomy", CANON), ("F0-class-contract-supplement", SUPP)):
        ent = la.get(name) or {}
        if ent.get("path") != rel or ent.get("sha256") != ctx["hash"][rel]:
            errs.append(f"FROZEN logical_artifacts[{name}] != measured {rel}")
        if not str(ent.get("mirrors", "")).startswith("NONE"):
            errs.append(f"FROZEN logical_artifacts[{name}] mirrors is not NONE")
    # soft drift note: the conflict evidence was written against an earlier manifest revision
    ev_rev = (ctx["conflict"].get("measured", {}).get("frozen_manifest", {}) or {}).get("revision")
    cur_rev = fr.get("revision")
    if ev_rev != cur_rev:
        ctx["notes"].append(
            f"manifest revision drift: conflict evidence cites FROZEN rev{ev_rev}, measured rev{cur_rev} "
            f"(both hash pins unchanged; evidence not re-based)")
    return ("fail" if errs else "pass",
            "; ".join(errs) if errs else
            f"FROZEN rev{cur_rev} pins canonical/supplement/F2b hashes == measured; both logical "
            f"artifacts declare mirrors NONE",
            [FROZEN, CANON, SUPP, F2B])


def c10_consistency_checker_dependency(ctx):
    """The consistency checker really consumes distinct keys from BOTH artifacts; evidence is pinned."""
    txt = ctx["consist_py"]
    required_tokens = ['class_ids', 'classes', 'class_contracts', 'genericity_axis', 'implication_ledger']
    missing = [t for t in required_tokens if t not in txt]
    errs = []
    if missing:
        errs.append(f"checker source lacks expected key access {missing}")
    fr_entry = (ctx["frozen"].get("files", {}) or {}).get(CONSIST) or {}
    if fr_entry.get("sha256") != ctx["hash"][CONSIST]:
        errs.append("consistency evidence hash != FROZEN-declared hash")
    rep = ctx["consist"]
    if rep.get("consistent") is not True:
        errs.append("pinned consistency evidence is not CONSISTENT")
    if len(rep.get("classes_compared") or []) != 4:
        errs.append("pinned consistency evidence does not compare 4 classes")
    # the checker writes its evidence file: recorded as a note so nobody runs it casually
    if ".write_text(" in txt:
        ctx["notes"].append(
            "check_taxonomy_consistency.py writes its evidence file; this audit inspected it "
            "statically and did not execute it (its output hash is unchanged and matches FROZEN)")
    return ("fail" if errs else "pass",
            "; ".join(errs) if errs else
            f"checker statically consumes canonical-only {['class_ids','classes']} and "
            f"supplement-only {['class_contracts','genericity_axis','implication_ledger']}; "
            f"pinned evidence {ctx['hash'][CONSIST][:12]} CONSISTENT over 4 classes",
            [CONSIST_PY, CONSIST, FROZEN])


def c11_conflict_evidence_quotes_live_fields(ctx):
    """The evidence file's quotes of schema pointers/bindings equal the live schema fields."""
    ev = ctx["conflict"].get("measured", {})
    errs = []
    ptrs = ev.get("schema_class_contract_pointers", {})
    for rel, s in ((F1, ctx["f1"]), (F2A, ctx["f2a"]), (F2B, ctx["f2b"])):
        if ptrs.get(rel) != s.get("class_contract_pointer"):
            errs.append(f"{rel}: quoted pointer != live pointer")
    binds = ev.get("schema_f0_binding", {})
    for rel, s in ((F1, ctx["f1"]), (F2A, ctx["f2a"]), (F2B, ctx["f2b"])):
        q = binds.get(rel) or {}
        live = s.get("f0_binding") or {}
        for k in ("declared_f0_artifact", "declared_f0_sha256", "class_contract_supplement"):
            if q.get(k) != live.get(k):
                errs.append(f"{rel}: quoted f0_binding[{k}] != live")
    dp = ctx["conflict"].get("dependency_proof", {}).get("measured_simulation", {})
    if dp.get("canonical_has_class_contracts") is not False:
        errs.append("quoted simulation canonical_has_class_contracts != False")
    if dp.get("authoring_has_class_ids") is not False:
        errs.append("quoted simulation authoring_has_class_ids != False")
    if ctx["conflict"].get("answer", "").strip()[:3].lower() != "no,":
        errs.append("conflict evidence answer is not the measured 'No'")
    return ("fail" if errs else "pass",
            "; ".join(errs) if errs else
            "evidence quotes match the live pointers/bindings of all three schemas and the "
            "measured key partition",
            [CONFLICT, F1, F2A, F2B])


CHECKS = [
    ("C1", "input pins + evidence-measurement agreement", c1_input_pins),
    ("C2", "canonical carries only F0-declared roles", c2_canonical_partition),
    ("C3", "supplement carries only supplement roles", c3_supplement_partition),
    ("C4", "F2b pointer resolves in supplement", c4_f2b_pointer_resolves_in_supplement),
    ("C5", "F2b pointer absent from canonical", c5_f2b_pointer_absent_from_canonical),
    ("C6", "F2b f0_binding matches measured canonical", c6_f2b_f0_binding_measured),
    ("C7", "all three schemas bind measured canonical + supplement", c7_all_schema_bindings),
    ("C8", "destructive publication simulation (structural)", c8_destructive_simulation),
    ("C9", "FROZEN manifest pins match measured bytes", c9_frozen_manifest_pins),
    ("C10", "consistency checker consumes both artifacts; evidence pinned", c10_consistency_checker_dependency),
    ("C11", "conflict evidence quotes live schema fields", c11_conflict_evidence_quotes_live_fields),
]


def run_checks(ctx):
    out = {}
    for cid, name, fn in CHECKS:
        status, detail, ev = fn(ctx)
        out[cid] = {"name": name, "status": status, "detail": detail, "evidence_refs": ev}
    return out


# --------------------------------------------------------------- controls ----
def mut_m1(ctx):
    ctx["canon"]["class_contracts"] = {"x": {}}
    return "C2"


def mut_m2(ctx):
    ctx["supp"].pop("class_contracts", None)
    return "C3"


def mut_m3(ctx):
    ctx["f2b"]["f0_binding"]["declared_f0_sha256"] = "0" * 64
    return "C6"


def mut_m4(ctx):
    ctx["f2b"]["class_contract_pointer"] = f"{CANON}#class_contracts.{CLASS}"
    return "C4"


def mut_m5(ctx):
    ctx["canon"].pop("classes", None)
    return "C2"


def mut_m6(ctx):
    ctx["supp"]["class_ids"] = []
    return "C3"


def mut_m7(ctx):
    ctx["frozen"]["logical_artifacts"]["F0-declared-taxonomy"]["sha256"] = "0" * 64
    return "C9"


def mut_m8(ctx):
    ctx["f2b"]["class_contract_pointer"] = "schemas/af_scc_c0_vacuum.yaml#class_contracts." + CLASS
    return "C4"


CONTROLS = [
    ("M1", "canonical gains supplement-only key class_contracts", mut_m1),
    ("M2", "supplement loses class_contracts", mut_m2),
    ("M3", "F2b declared_f0_sha256 corrupted", mut_m3),
    ("M4", "F2b pointer repointed at the canonical taxonomy", mut_m4),
    ("M5", "canonical loses its classes map", mut_m5),
    ("M6", "supplement gains canonical-only key class_ids", mut_m6),
    ("M7", "FROZEN logical-artifact hash corrupted", mut_m7),
    ("M8", "F2b pointer repointed at the schema itself", mut_m8),
]


def run_controls(baseline_status):
    results = {}
    for mid, desc, mut in CONTROLS:
        ctx = build_ctx()
        target = mut(ctx)
        res = run_checks(ctx)
        caught = res[target]["status"] == "fail"
        results[mid] = {
            "description": desc,
            "target_check": target,
            "status": "pass" if caught else "fail",
            "meaning": "planted defect caught" if caught else "PLANTED DEFECT NOT CAUGHT",
            "target_detail": res[target]["detail"],
            "unintended_failures": sorted(
                c for c, v in res.items() if v["status"] == "fail" and c != target),
        }
    n0_pass = all(v == "pass" for v in baseline_status.values())
    results["N0"] = {
        "description": "no-false-positive control: unmutated baseline",
        "target_check": "all",
        "status": "pass" if n0_pass else "fail",
        "meaning": "baseline clean" if n0_pass else "BASELINE FALSE POSITIVE",
        "target_detail": "all checks pass on unmutated inputs" if n0_pass else "baseline check(s) failed",
        "unintended_failures": [],
    }
    return results


# ------------------------------------------------------------- stability ----
def stability_sample(paths, window, interval):
    if window <= 0:
        return None
    samples = {p: [] for p in paths}
    t0 = time.time()
    while True:
        for p in paths:
            samples[p].append(digest((ROOT / p).read_bytes()))
        elapsed = time.time() - t0
        if elapsed >= window:
            break
        time.sleep(max(1.0, min(interval, window - elapsed)))
    out = {}
    for p, hs in samples.items():
        out[p] = {
            "samples": len(hs),
            "distinct_hashes": len(set(hs)),
            "first": hs[0],
            "last": hs[-1],
            "drift": len(set(hs)) > 1,
        }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--window", type=float, default=0.0)
    ap.add_argument("--interval", type=float, default=10.0)
    args = ap.parse_args()

    ctx = build_ctx()
    checks = run_checks(ctx)
    statuses = {k: v["status"] for k, v in checks.items()}
    controls = run_controls(statuses)
    all_checks_pass = all(s == "pass" for s in statuses.values())
    all_controls_pass = all(v["status"] == "pass" for v in controls.values())
    notes = list(ctx["notes"])

    verdict = "accept" if (all_checks_pass and all_controls_pass) else "revise"
    report = {
        "report_id": "W089-F2B-F0ADJ-02",
        "worker": "worker-089",
        "task_id": "W089-F2B-F0ADJ-02",
        "class_id": CLASS,
        "node_id": "F2b",
        "gate": "G-FORM",
        "related_gate": "G-F0",
        "created_at": now(),
        "verdict": verdict,
        "verdict_scope": (
            "Mechanical verification of the F0 mirror-conflict dependency claims as they bind "
            "AF-SCC-C0-VAC-GEN (F2b): input pins, key partition of the two taxonomy artifacts, "
            "F2b/sibling pointer resolution, f0_binding agreement with measured bytes, a structural "
            "destructive-publication simulation, FROZEN pin agreement, and the consistency checker's "
            "static dependency. It does NOT adjudicate REC-1 vs REC-2, does NOT review semantics, and "
            "is NOT a G-F0 or G-FORM gate accept."
        ),
        "target_pins": PINS,
        "measured": {
            rel: {"path": rel, "sha256": ctx["hash"][rel], "bytes": len(ctx["raw"][rel])}
            for rel in (F2B, F2A, F1, CANON, SUPP, FROZEN, CONFLICT, CONSIST, CONSIST_PY)
        },
        "checks": checks,
        "checks_passed": sum(1 for s in statuses.values() if s == "pass"),
        "checks_total": len(statuses),
        "controls": controls,
        "controls_caught": sum(1 for v in controls.values() if v["status"] == "pass"),
        "controls_total": len(controls),
        "notes": notes,
        "falsifier": (
            "Any of the following falsifies this report: (i) the measured sha256 of either taxonomy "
            "path differs from the value cited here or in f0_mirror_conflict.json; (ii) F2b's "
            "class_contract_pointer fragment resolves in the canonical declared-F0 taxonomy "
            "(falsifies 'load-bearing on the supplement'); (iii) the canonical taxonomy gains any of "
            "class_contracts/axis_registry/implication_ledger or the supplement gains any of "
            "class_ids/classes/transfer_rules (falsifies 'two different artifacts'); (iv) FROZEN.json's "
            "declared hashes for canonical/supplement/F2b cease to equal measured bytes; (v) any "
            "planted control stops being caught or the no-false-positive baseline fails."
        ),
        "next_falsifier": (
            "Re-run against a newer FROZEN revision or after any republication: a flip of C2/C3/C4/C5 "
            "or a C1 hash move voids the dependency proof for the newer revision and re-opens the "
            "REC-1/REC-2 adjudication."
        ),
        "stability": stability_sample([F2B, CANON, SUPP, FROZEN, F2A], args.window, args.interval),
        "evidence_refs": [
            f"{CANON}#{ctx['hash'][CANON][:12]}",
            f"{SUPP}#{ctx['hash'][SUPP][:12]}",
            f"{F2B}#{ctx['hash'][F2B][:12]}",
            f"{FROZEN}#{ctx['hash'][FROZEN][:12]}",
            f"{CONFLICT}#{ctx['hash'][CONFLICT][:12]}",
        ],
    }

    out = HERE / "f0adj_report.json"
    out.write_text(json.dumps(report, indent=2) + "\n")
    ctrl_dir = HERE / "controls"
    ctrl_dir.mkdir(exist_ok=True)
    for mid, v in controls.items():
        (ctrl_dir / f"{mid}.json").write_text(json.dumps(v, indent=2) + "\n")

    print(f"verdict={verdict} checks={report['checks_passed']}/{report['checks_total']} "
          f"controls={report['controls_caught']}/{report['controls_total']}")
    for cid, v in checks.items():
        print(f"  {cid} {v['status']:4s} {v['name']}")
    for mid, v in controls.items():
        print(f"  {mid} {v['status']:4s} -> {v['target_check']}: {v['description']}")
    for n in notes:
        print(f"  note: {n}")
    print(f"report: {out}")
    sys.exit(0 if verdict == "accept" else 1)


if __name__ == "__main__":
    main()
