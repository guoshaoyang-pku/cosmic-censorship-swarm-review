#!/usr/bin/env python3
"""W032-F1AMB25-STALE-VERIFY-01: independent recomputation of the F1 ambiguity suite's
stored probes against the canonical F0/F1 pair, focused on row F1-AMB-25.

Claim under test (worker-031, w031-f1-rebind-blocker-20260912T003602):
  schemas/f1_falsifier_tests.jsonl#56bcb4b3234b stores 84/84 probes as pass=true, but
  row F1-AMB-25's deciding field f0_binding.declared_f0_sha256 still expects the
  superseded F0 rev4 hash 276009f4..., so its equality probe is false against the live
  F0 rev5 canonical 0abb9ed8...; the suite therefore asserts a false outcome.

This checker is read-only. It recomputes from pinned byte copies under ./pinned and
verifies the live canonical files still hash to the same pins. Probe semantics mirror
the suite author's verifier (equals/contains/nonnull/path_exists/is_none/is_true with
json.dumps-based flattening) but the implementation is independent.

Exit 0 iff every pre-registered expectation (EXP1..EXP8) holds; exit 2 otherwise.
--selftest runs evaluator unit fixtures and exits 0/2.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]  # artifacts/worker-032/f1amb25 -> repo root
PINNED = HERE / "pinned"
CST = timezone(timedelta(hours=8))
# fixed so report bytes are reproducible; override with --created-at
REPORT_CREATED_AT = "2026-09-12T00:41:14+08:00"

SUITE_REL = "schemas/f1_falsifier_tests.jsonl"
F1_REL = "schemas/af_wcc_vacuum.yaml"
F0_REL = "research_map/formulation_taxonomy.yaml"
FROZEN_REL = "artifacts/formulation/FROZEN.json"
VENDOR_REL = "artifacts/worker-032/run/verify_freeze_current.py"

PINS = {
    "suite": (SUITE_REL, "56bcb4b3234bc86c324bec6e38f142c5ef39517f20d823b6a333f578b7d0851e"),
    "f1": (F1_REL, "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3"),
    "f0": (F0_REL, "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"),
    "frozen": (FROZEN_REL, "2f358f6722d920621a66c0259cb48d35a5e3c1b706f28adf37ed467325fcedf1"),
}
STALE_F0_REV4 = "276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc"
EXPECTED_MISMATCH_KEYS = [
    "F1-AMB-25|f0_binding.binding_note|contains",
    "F1-AMB-25|f0_binding.declared_f0_sha256|equals",
]

_TOKEN = re.compile(r"([^.\[\]]+)|\[(\d+)\]")


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def getpath(doc, path: str):
    cur = doc
    for name, idx in _TOKEN.findall(path):
        if name:
            if isinstance(cur, dict) and name in cur:
                cur = cur[name]
            else:
                return False, None
        else:
            if isinstance(cur, list) and int(idx) < len(cur):
                cur = cur[int(idx)]
            else:
                return False, None
    return True, cur


def flat(value) -> str:
    return json.dumps(value, default=str, ensure_ascii=False)


def evaluate(doc, spec: dict) -> dict:
    """Return {'found','pass','value'} for one stored probe spec."""
    found, value = getpath(doc, spec["path"])
    kind = spec["kind"]
    needle = spec.get("value", spec.get("expected"))
    if kind in ("path_exists", "nonnull"):
        ok = found and value is not None
    elif kind == "is_none":
        ok = (not found) or value is None
    elif kind == "is_true":
        ok = value is True
    elif kind == "equals":
        ok = found and value == needle
    elif kind == "contains":
        ok = found and value is not None and needle in flat(value)
    else:
        raise ValueError(f"unknown probe kind {kind!r}")
    return {"found": found, "pass": bool(ok), "value": None if not found else flat(value)}


def load_rows(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def recompute(rows, docs: dict) -> dict:
    """Re-evaluate every stored probe in every row. docs maps test_id -> artifact doc."""
    total = stored_pass = 0
    mismatches = []
    per_row = {}
    for r in rows:
        tid = r.get("test_id")
        doc = docs.get(tid)
        row_res = []
        for i, spec in enumerate(r.get("probe_results", [])):
            total += 1
            stored = spec.get("pass")
            if stored is True:
                stored_pass += 1
            if doc is None:
                got = {"found": False, "pass": False, "value": None}
            else:
                got = evaluate(doc, spec)
            row_res.append({"index": i, "path": spec.get("path"), "kind": spec.get("kind"),
                            "stored": stored, "recomputed": got["pass"]})
            if bool(stored) != got["pass"]:
                mismatches.append({"test_id": tid, "index": i, "path": spec.get("path"),
                                   "kind": spec.get("kind"), "stored": stored,
                                   "recomputed": got["pass"],
                                   "expected": spec.get("expected"),
                                   "observed": spec.get("observed_excerpt"),
                                   "live_value": got["value"]})
        per_row[tid] = row_res
    return {"probes_total": total, "stored_pass": stored_pass, "mismatches": mismatches,
            "per_row": per_row}


def cross_list(r) -> list:
    xas = r.get("cross_artifact")
    if isinstance(xas, dict):
        return [xas]
    if isinstance(xas, list):
        return xas
    return []


def cross_artifact_checks(rows, live_hashes: dict):
    stale = []
    checked = 0
    for r in rows:
        for xa in cross_list(r):
            checked += 1
            actual = live_hashes.get(xa.get("path"))
            if actual != xa.get("sha256"):
                stale.append({"test_id": r.get("test_id"), "path": xa.get("path"),
                              "stored": xa.get("sha256"), "actual": actual})
    return {"checked": checked, "stale": stale}


def selftest() -> int:
    doc = {"a": {"b": "hello", "h": "abc123", "n": None, "t": True, "lst": ["x", "y"]}}
    cases = [
        ({"path": "a.b", "kind": "equals", "expected": "hello"}, True),
        ({"path": "a.b", "kind": "equals", "expected": "other"}, False),
        ({"path": "a.b", "kind": "contains", "expected": "ell"}, True),
        ({"path": "a.lst", "kind": "contains", "expected": "y"}, True),
        ({"path": "a.h", "kind": "nonnull", "expected": None}, True),
        ({"path": "a.n", "kind": "nonnull", "expected": None}, False),
        ({"path": "a.n", "kind": "is_none", "expected": None}, True),
        ({"path": "a.t", "kind": "is_true", "expected": None}, True),
        ({"path": "a.missing", "kind": "path_exists", "expected": None}, False),
        ({"path": "a.lst[1]", "kind": "equals", "expected": "y"}, True),
    ]
    bad = []
    for spec, want in cases:
        got = evaluate(doc, spec)["pass"]
        if got != want:
            bad.append({"spec": spec, "want": want, "got": got})
    try:
        evaluate(doc, {"path": "a.b", "kind": "bogus"})
        bad.append({"spec": "unknown-kind", "want": "raises", "got": "no error"})
    except ValueError:
        pass
    print(json.dumps({"selftest": "PASS" if not bad else "FAIL", "cases": len(cases) + 1,
                      "bad": bad}, indent=1))
    return 0 if not bad else 2


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--out", default=str(HERE / "report.json"))
    ap.add_argument("--created-at", default=REPORT_CREATED_AT,
                    help="created_at recorded in the report; fixed by default for reproducibility")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    # ---- pins: measured from the pinned byte copies, verified against the live tree
    measured_live = {rel: (sha256_file(ROOT / rel) if (ROOT / rel).exists() else None)
                     for rel, _ in PINS.values()}
    drift = [{"pin": k, "path": rel, "pinned": pin, "live": measured_live.get(rel)}
             for k, (rel, pin) in PINS.items() if measured_live.get(rel) != pin]
    live_hashes = {}
    for rel in {x.get("path") for r in load_rows(PINNED / Path(SUITE_REL).name)
                for x in cross_list(r)}:
        live_hashes[rel] = sha256_file(ROOT / rel) if (ROOT / rel).exists() else None

    rows = load_rows(PINNED / Path(SUITE_REL).name)
    f1_doc = yaml.safe_load((PINNED / Path(F1_REL).name).read_text(encoding="utf-8"))
    docs = {r.get("test_id"): f1_doc for r in rows}

    rc = recompute(rows, docs)
    xa = cross_artifact_checks(rows, live_hashes)

    amb25 = next((r for r in rows if r.get("test_id") == "F1-AMB-25"), None)
    amb25_probes = [
        {"index": i, "path": p.get("path"), "kind": p.get("kind"), "stored": p.get("pass"),
         "expected": str(p.get("expected"))[:80], "observed": str(p.get("observed_excerpt"))[:80]}
        for i, p in enumerate((amb25 or {}).get("probe_results", []))
    ]
    mismatch_keys = sorted({f"{m['test_id']}|{m['path']}|{m['kind']}" for m in rc["mismatches"]})

    # ---- controls
    ctl_a_ok = False
    if amb25 is not None:
        repaired = copy.deepcopy(amb25)
        for p in repaired["probe_results"]:
            if p.get("path") == "f0_binding.declared_f0_sha256":
                p["expected"] = f1_doc["f0_binding"]["declared_f0_sha256"]
            if p.get("path") == "f0_binding.binding_note":
                p["expected"] = "rev12"
        ctl_a_ok = all(evaluate(f1_doc, p)["pass"] for p in repaired["probe_results"])
    mutated = copy.deepcopy(amb25) if amb25 else None
    ctl_b_ok = False
    if mutated is not None:
        for p in mutated["probe_results"]:
            if p.get("path") == "f0_binding.declared_f0_sha256":
                p["expected"] = "0" * 64
        got = evaluate(f1_doc, [p for p in mutated["probe_results"]
                                if p["path"] == "f0_binding.declared_f0_sha256"][0])
        ctl_b_ok = got["pass"] is False
    rc2 = recompute(rows, docs)
    ctl_c_ok = [m["test_id"] + m["path"] + str(m["kind"]) for m in rc2["mismatches"]] == \
               [m["test_id"] + m["path"] + str(m["kind"]) for m in rc["mismatches"]]

    f1_live = measured_live.get(F1_REL)
    amb25_binding_current = bool(amb25 and amb25.get("binding_sha256") == f1_live)

    expectations = [
        {"id": "EXP1", "what": "pinned suite sha256 equals the recorded pin",
         "ok": sha256_file(PINNED / Path(SUITE_REL).name) == PINS["suite"][1]},
        {"id": "EXP2", "what": "suite has 25 rows / 84 probes / 84 stored passes",
         "ok": len(rows) == 25 and rc["probes_total"] == 84 and rc["stored_pass"] == 84,
         "detail": {"rows": len(rows), "probes": rc["probes_total"], "stored_pass": rc["stored_pass"]}},
        {"id": "EXP3", "what": "recomputed mismatches are exactly AMB-25's two probes",
         "ok": mismatch_keys == EXPECTED_MISMATCH_KEYS,
         "detail": {"mismatch_keys": mismatch_keys}},
        {"id": "EXP4", "what": "exactly one stale cross-artifact binding: AMB-25 F0 rev4 vs live rev5",
         "ok": xa["checked"] == 1 and len(xa["stale"]) == 1
               and xa["stale"][0]["test_id"] == "F1-AMB-25"
               and xa["stale"][0]["stored"] == STALE_F0_REV4
               and xa["stale"][0]["actual"] == PINS["f0"][1],
         "detail": xa},
        {"id": "EXP5", "what": "AMB-25 deciding equality probe recomputes false",
         "ok": any(m["test_id"] == "F1-AMB-25" and m["path"] == "f0_binding.declared_f0_sha256"
                   and m["kind"] == "equals" and m["recomputed"] is False
                   for m in rc["mismatches"])},
        {"id": "EXP6", "what": "AMB-25 binding_sha256 equals the live F1 rev12 hash (F1 axis current)",
         "ok": amb25_binding_current},
        {"id": "EXP7", "what": "controls: repair-responsive, mutation-detecting, idempotent",
         "ok": ctl_a_ok and ctl_b_ok and ctl_c_ok,
         "detail": {"ctl_a_repair_responsive": ctl_a_ok, "ctl_b_mutation_detected": ctl_b_ok,
                    "ctl_c_idempotent": ctl_c_ok}},
        {"id": "EXP8", "what": "zero drift: live canonical files still equal the pins",
         "ok": not drift, "detail": drift},
    ]
    failures = [e["id"] for e in expectations if not e["ok"]]
    verdict = "stale_assertion_confirmed" if not failures else "expectations_failed"

    report = {
        "report_id": "w032-f1amb25-stale-verify",
        "created_at": args.created_at,
        "actor": "worker-032",
        "task_id": "W032-F1AMB25-STALE-VERIFY-01",
        "node_id": "F1",
        "gate": "G-FORM",
        "class_id": "AF-WCC-VAC-GEN",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN",
                      "AF-WCC-SCALAR-SPH"],
        "role": "bounded read-only worker verification; no map mutation, no gate verdict, "
                "no node status promotion",
        "pins": {k: {"path": v[0], "sha256": v[1]} for k, v in PINS.items()},
        "measured_live": measured_live,
        "drift": drift,
        "suite": {"rows": len(rows), "probes_total": rc["probes_total"],
                  "stored_pass": rc["stored_pass"], "recomputed_mismatches": len(rc["mismatches"])},
        "mismatches": rc["mismatches"],
        "cross_artifact": xa,
        "row_F1-AMB-25": {
            "binding_sha256": (amb25 or {}).get("binding_sha256"),
            "binding_current": amb25_binding_current,
            "cross_artifact": (amb25 or {}).get("cross_artifact"),
            "probes": amb25_probes,
            "next_falsifier": (amb25 or {}).get("next_falsifier"),
            "vendor_verifier_present": (ROOT / VENDOR_REL).exists(),
            "vendor_verifier_sha256": sha256_file(ROOT / VENDOR_REL)
            if (ROOT / VENDOR_REL).exists() else None,
        },
        "controls": {"ctl_a_repair_responsive": ctl_a_ok, "ctl_b_mutation_detected": ctl_b_ok,
                     "ctl_c_idempotent": ctl_c_ok},
        "expectations": expectations,
        "failures": failures,
        "verdict": verdict,
        "falsifier": "Re-run check_amb25.py against the pinned copies; falsified if "
                     "F1-AMB-25's f0_binding.declared_f0_sha256 equality probe recomputes true "
                     "against the live F0 canonical, or the stored-vs-recomputed mismatch set is "
                     "empty, or the AMB-25 cross_artifact hash matches the live F0 canonical, or "
                     "the pinned suite sha256 is not 56bcb4b3234b (row repaired/rebound).",
        "scope_limits": [
            "binds only the pinned hashes; any rewrite of suite/F0/F1/FROZEN retires this measurement",
            "probe semantics mirror the suite author's verifier; independent implementation, not independent semantics",
            "no claim about whether the other 24 rows' semantics are sufficient for G-FORM",
        ],
        "evidence_refs": [
            f"{SUITE_REL}#{PINS['suite'][1][:16]}",
            f"{F1_REL}#{PINS['f1'][1][:16]}",
            f"{F0_REL}#{PINS['f0'][1][:16]}",
            f"{FROZEN_REL}#{PINS['frozen'][1][:16]}",
        ],
    }
    Path(args.out).write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps({"verdict": verdict, "failures": failures,
                      "mismatches": len(rc["mismatches"]),
                      "stale_cross_artifacts": len(xa["stale"]),
                      "drift": len(drift), "out": args.out}, indent=1))
    return 0 if not failures else 2


if __name__ == "__main__":
    sys.exit(main())
