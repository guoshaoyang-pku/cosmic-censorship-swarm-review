#!/usr/bin/env python3
"""W029-F1-SUITE-REBIND-01: independent, read-only measurement of the F1 falsifier
suite's binding state against the live F1 rev13 canonical schema.

Question (one class-bound task, class AF-WCC-VAC-GEN, node F1, gate G-FORM):
  schemas/f1_falsifier_tests.jsonl#56bcb4b3234b was last rebound (rebound_at
  2026-09-12T00:32:31+08:00) to F1 rev12 cce9c60146d6. FROZEN rev29 then republished
  schemas/af_wcc_vacuum.yaml at rev13 d9cebb9404b2 with the suite bytes unchanged.
  (1) Is every suite row still bound to the superseded F1 hash while FROZEN rev29
      declares the schema canonical?  (2) Do the stored probes still re-evaluate to
      their stored pass values against the rev13 bytes?  (3) Is the stale binding
      material (rev13 changed probe-relevant content) or cosmetic?

The suite has its own vendor verifier, artifacts/flash-04/f1_ambiguity/verify_freeze_current.py,
whose hard check C1a is exactly "canonical on-disk F1 schema sha256 equals the suite
binding sha256". That verifier rewrites its own report file, so it is NOT executed
here; this checker reimplements the C1a/C1b/C8 semantics independently (probe kinds
equals/contains/path_exists/nonnull/is_none/is_true with json.dumps flattening) and
evaluates the same suite against both the rev13 live copy and the rev12 snapshot.

Read-only: no canonical byte is written; all mutations are in-memory. Exit 0 iff
every pre-registered expectation (EXP1..EXP12) holds; exit 2 on a failed expectation;
exit 3 on pin drift (fail closed).
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PINNED = HERE / "pinned"
CST = "+08:00"

TASK_ID = "W029-F1-SUITE-REBIND-01"
NODE_ID = "F1"
CLASS_ID = "AF-WCC-VAC-GEN"
GATE = "G-FORM"

PINS = {
    "suite": ("schemas/f1_falsifier_tests.jsonl",
              "56bcb4b3234bc86c324bec6e38f142c5ef39517f20d823b6a333f578b7d0851e"),
    "f1_rev13": ("schemas/af_wcc_vacuum.yaml",
                 "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d"),
    "f1_rev12": ("artifacts/worker-060/rev29_binding_acceptance/snapshots/f1__af_wcc_vacuum.cce9c60146d6.yaml",
                 "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3"),
    "f0": ("research_map/formulation_taxonomy.yaml",
           "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"),
    "frozen": ("artifacts/formulation/FROZEN.json",
               "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0"),
    "frozen_prev": ("artifacts/worker-029/f1_suite_rebind/pinned/FROZEN.3d9e3d77fd87.json",
                    "3d9e3d77fd87101937f6e3c18c69703594f945c962e9692dc2df5ea6a3bd3833"),
    "f1_mirror": ("artifacts/formulation/schemas/af_wcc_vacuum.yaml",
                  "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d"),
}
FROZEN_SUITE_KEY = "schemas/f1_falsifier_tests.jsonl"
FROZEN_F1_KEY = "schemas/af_wcc_vacuum.yaml"
FROZEN_F1_MIRROR_KEY = "artifacts/formulation/schemas/af_wcc_vacuum.yaml"

_TOKEN = re.compile(r"([^.\[\]]+)|\[(\d+)\]")


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
    """Vendor-C8 semantics, independent implementation."""
    found, value = getpath(doc, str(spec.get("path", "")))
    kind = spec.get("kind")
    needle = spec.get("expected")
    if kind in ("path_exists", "nonnull"):
        ok = bool(found and value is not None)
    elif kind == "is_none":
        ok = (not found) or value is None
    elif kind == "is_true":
        ok = value is True
    elif kind == "equals":
        ok = bool(found and value == needle)
    elif kind == "contains":
        ok = bool(found and value is not None and isinstance(needle, str) and needle in flat(value))
    else:
        return {"found": found, "pass": None, "error": f"unknown probe kind {kind!r}",
                "value": None if not found else flat(value)}
    return {"found": found, "pass": bool(ok), "error": None,
            "value": None if not found else flat(value)}


def load_rows(path: Path):
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def leaf_paths(obj, prefix=""):
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.update(leaf_paths(v, f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.update(leaf_paths(v, f"{prefix}[{i}]"))
    else:
        out[prefix] = obj
    return out


def main() -> int:
    checks, failures, controls = [], [], {}

    # ---------- I0: pin integrity, fail closed ----------
    measured, drift = {}, []
    for key, (rel, pin) in PINS.items():
        p = ROOT / rel
        got = sha256_file(p) if p.exists() else None
        measured[key] = {"path": rel, "expected": pin, "measured": got}
        if got != pin:
            drift.append(key)
    checks.append({
        "id": "I0", "name": "pinned inputs unchanged at read time (T0)",
        "ok": not drift, "severity": "acceptance",
        "measured": measured if drift else f"{len(PINS)}/{len(PINS)} pins match",
        "falsifier": "Any pinned path whose measured sha256 differs from the pin; the measurement is then void, not merely wrong.",
    })
    if drift:
        failures.append({"id": "I0-drift", "files": drift})
        print(json.dumps({"task_id": TASK_ID, "verdict": "void_pin_drift",
                          "failures": failures}, indent=1))
        return 3

    rows = load_rows(ROOT / PINS["suite"][0])
    f1_live = yaml.safe_load((ROOT / PINS["f1_rev13"][0]).read_text())
    f1_rev12 = yaml.safe_load((ROOT / PINS["f1_rev12"][0]).read_text())
    frozen = json.loads((ROOT / PINS["frozen"][0]).read_text())
    suite_pin = PINS["suite"][1]
    f1_live_pin = PINS["f1_rev13"][1]
    f1_rev12_pin = PINS["f1_rev12"][1]

    # ---------- B0: same-revision-label re-emission observed mid-task ----------
    frozen_prev = json.loads((ROOT / PINS["frozen_prev"][0]).read_text())
    of, nf = frozen_prev.get("files") or {}, frozen.get("files") or {}
    fro_added = sorted(set(nf) - set(of))
    fro_removed = sorted(set(of) - set(nf))
    fro_changed = sorted(k for k in set(of) & set(nf) if of[k].get("sha256") != nf[k].get("sha256"))
    b0_pins_identical = all(of.get(k) == nf.get(k) for k in
                            (FROZEN_SUITE_KEY, FROZEN_F1_KEY, FROZEN_F1_MIRROR_KEY))
    checks.append({
        "id": "B0", "name": "FROZEN re-emitted under the same revision label 29 during this task; F1/suite/mirror entries identical",
        "ok": b0_pins_identical, "severity": "info",
        "measured": {"prev": {"sha256": PINS["frozen_prev"][1], "revision": frozen_prev.get("revision"),
                              "frozen_at": frozen_prev.get("frozen_at")},
                     "current": {"sha256": PINS["frozen"][1], "revision": frozen.get("revision"),
                                 "frozen_at": frozen.get("frozen_at")},
                     "files_added": fro_added, "files_removed": fro_removed,
                     "files_changed": fro_changed,
                     "f1_suite_mirror_entries_identical": b0_pins_identical},
        "falsifier": "An F1, suite or mirror entry that differs between the two revision-29 emissions; that would make the earlier measurement superseded rather than merely re-labelled.",
    })
    if not b0_pins_identical:
        failures.append({"id": "B0"})

    # ---------- B1: FROZEN rev29 declares the measured suite bytes ----------
    frozen_suite_pin = ((frozen.get("files") or {}).get(FROZEN_SUITE_KEY) or {}).get("sha256")
    checks.append({
        "id": "B1", "name": "FROZEN rev29 suite pin equals measured suite bytes",
        "ok": frozen_suite_pin == suite_pin, "severity": "acceptance",
        "measured": {"frozen_revision": frozen.get("revision"),
                     "frozen_pin": frozen_suite_pin, "measured": suite_pin},
        "falsifier": "FROZEN rev29 declares a suite hash other than 56bcb4b3234b, or the suite bytes move.",
    })
    if frozen_suite_pin != suite_pin:
        failures.append({"id": "B1"})

    # ---------- B2: row binding census ----------
    bindings = sorted({r.get("binding_sha256") for r in rows})
    current = [r["test_id"] for r in rows if r.get("binding_sha256") == f1_live_pin]
    stale_rev12 = [r["test_id"] for r in rows if r.get("binding_sha256") == f1_rev12_pin]
    other = [r["test_id"] for r in rows if r.get("binding_sha256") not in (f1_live_pin, f1_rev12_pin)]
    binding_refs = sorted({r.get("binding_ref") for r in rows})
    rev_schema = sorted({r.get("binding_frozen_revision_schema") for r in rows})
    rebound_at = sorted({r.get("rebound_at") for r in rows})
    checks.append({
        "id": "B2", "name": "row-level binding_sha256 vs the live F1 rev13 pin",
        "ok": len(current) == 0 and len(stale_rev12) == len(rows),
        "severity": "acceptance",
        "measured": {"rows": len(rows), "distinct_bindings": bindings,
                     "rows_bound_to_rev13": len(current), "rows_bound_to_rev12": len(stale_rev12),
                     "rows_bound_other": other, "binding_refs": binding_refs,
                     "binding_frozen_revision_schema": rev_schema, "rebound_at": rebound_at},
        "falsifier": "Any row whose binding_sha256 equals the live rev13 pin d9cebb9404b2 (the suite was rebound), or a binding that is neither rev12 nor rev13.",
    })
    if current or other:
        failures.append({"id": "B2"})

    # ---------- B3/B4: vendor C1a/C1b semantics ----------
    c1a_ok = any(b == f1_live_pin for b in bindings) and len(bindings) == 1
    frozen_f1_pin = ((frozen.get("files") or {}).get(FROZEN_F1_KEY) or {}).get("sha256")
    c1b_ok = frozen_f1_pin == (bindings[0] if len(bindings) == 1 else None)
    checks.append({
        "id": "B3", "name": "vendor C1a reproduced: canonical F1 sha256 == suite binding (HARD in vendor verifier)",
        "ok": bool(c1a_ok), "severity": "acceptance",
        "measured": {"suite_binding": bindings[0] if len(bindings) == 1 else None,
                     "canonical_measured": f1_live_pin,
                     "vendor_source": "artifacts/flash-04/f1_ambiguity/verify_freeze_current.py:171-176 (C1a, no severity override => hard)"},
        "falsifier": "A canonical F1 schema whose sha256 equals the suite binding, i.e. a suite rebind to d9cebb9404b2.",
    })
    checks.append({
        "id": "B4", "name": "vendor C1b: FROZEN rev29 canonical F1 pin == suite binding (SOFT in vendor)",
        "ok": bool(c1b_ok), "severity": "soft",
        "measured": {"frozen_revision": frozen.get("revision"), "frozen_pin": frozen_f1_pin,
                     "suite_binding": bindings[0] if len(bindings) == 1 else None},
        "falsifier": "A FROZEN manifest whose F1 canonical pin equals the suite binding.",
    })
    if not c1a_ok:
        failures.append({"id": "B3-C1a", "class_id": CLASS_ID,
                         "label": "suite binding is the superseded F1 rev12 hash while the canonical schema is rev13"})

    # ---------- B5: authoring mirror / FROZEN agreement ----------
    mirror_pin = ((frozen.get("files") or {}).get(FROZEN_F1_MIRROR_KEY) or {}).get("sha256")
    checks.append({
        "id": "B5", "name": "authoring mirror and FROZEN mirror pin agree with live F1",
        "ok": mirror_pin == f1_live_pin and PINS["f1_mirror"][1] == f1_live_pin,
        "severity": "acceptance",
        "measured": {"frozen_mirror_pin": mirror_pin, "mirror_measured": PINS["f1_mirror"][1],
                     "live": f1_live_pin},
        "falsifier": "A mirror or FROZEN mirror pin differing from the live F1 bytes; that would be a second, independent binding break.",
    })
    if not (mirror_pin == f1_live_pin and PINS["f1_mirror"][1] == f1_live_pin):
        failures.append({"id": "B5"})

    # ---------- P1/P2: stored probes vs rev13 and rev12 ----------
    def probe_census(doc):
        total = stored_pass = recomputed_pass = 0
        mismatches, errors = [], []
        for r in rows:
            for p in r.get("probe_results") or []:
                total += 1
                stored_pass += 1 if p.get("pass") is True else 0
                got = evaluate(doc, p)
                if got["error"]:
                    errors.append({"test_id": r.get("test_id"), "kind": p.get("kind"),
                                   "path": p.get("path"), "error": got["error"]})
                    continue
                recomputed_pass += 1 if got["pass"] else 0
                if got["pass"] != bool(p.get("pass")):
                    mismatches.append({"test_id": r.get("test_id"), "path": p.get("path"),
                                       "kind": p.get("kind"), "stored": bool(p.get("pass")),
                                       "recomputed": bool(got["pass"]),
                                       "expected": p.get("expected"),
                                       "live_value": got["value"]})
        return {"probes_total": total, "stored_pass": stored_pass,
                "recomputed_pass": recomputed_pass, "mismatches": mismatches, "errors": errors}

    c13 = probe_census(f1_live)
    c12 = probe_census(f1_rev12)
    m13_keys = sorted(f"{m['test_id']}|{m['path']}|{m['kind']}" for m in c13["mismatches"])
    m12_keys = sorted(f"{m['test_id']}|{m['path']}|{m['kind']}" for m in c12["mismatches"])
    checks.append({
        "id": "P1", "name": "stored probes re-evaluated against live F1 rev13",
        "ok": c13["probes_total"] == 84 and c13["stored_pass"] == 84 and not c13["errors"],
        "severity": "acceptance",
        "measured": {k: c13[k] for k in ("probes_total", "stored_pass", "recomputed_pass")}
                    | {"mismatch_count": len(c13["mismatches"]), "mismatch_keys": m13_keys,
                       "mismatches": c13["mismatches"], "errors": c13["errors"]},
        "falsifier": "A probe total other than 84, a stored-pass count other than 84, or an evaluator error; falsifies the measurement harness, not the finding.",
    })
    checks.append({
        "id": "P2", "name": "control: same evaluator against the F1 rev12 snapshot reproduces the prior known mismatch set",
        "ok": m12_keys == ["F1-AMB-25|f0_binding.binding_note|contains",
                           "F1-AMB-25|f0_binding.declared_f0_sha256|equals"],
        "severity": "control",
        "measured": {"probes_total": c12["probes_total"], "recomputed_pass": c12["recomputed_pass"],
                     "mismatch_count": len(c12["mismatches"]), "mismatch_keys": m12_keys},
        "falsifier": "A rev12 mismatch set other than the two AMB-25 probes already measured by worker-032; an evaluator that cannot reproduce a known result is not evidence.",
    })
    if not checks[-1]["ok"]:
        failures.append({"id": "P2-control"})

    # ---------- P3: is the stale binding material? ----------
    lv12, lv13 = leaf_paths(f1_rev12), leaf_paths(f1_live)
    changed = sorted(set(k for k in set(lv12) | set(lv13) if lv12.get(k) != lv13.get(k)))
    probe_paths = sorted({str(p.get("path")) for r in rows for p in (r.get("probe_results") or [])})
    probe_path_hit = sorted(p for p in probe_paths if p in changed)
    deciding_hit = sorted({str(r.get("deciding_field")) for r in rows
                           if str(r.get("deciding_field")) in changed})
    checks.append({
        "id": "P3", "name": "rev12 -> rev13 structural delta and its intersection with probe/deciding paths",
        "ok": len(changed) > 0,
        "severity": "info",
        "measured": {"changed_leaf_paths": len(changed), "changed_paths_sample": changed[:40],
                     "probe_paths_exactly_changed": probe_path_hit,
                     "deciding_fields_exactly_changed": deciding_hit,
                     "note": "exact-path intersection understates materiality when content sits above/below the probed leaf; P1 is the material test."},
        "falsifier": "Zero changed leaf paths between rev12 and rev13 would mean the stale binding is cosmetic for content; the probe recomputation still decides evidence status.",
    })

    # ---------- X1: cross-artifact declared hashes ----------
    cross = []
    for r in rows:
        xas = r.get("cross_artifact")
        xas = xas if isinstance(xas, list) else ([xas] if xas else [])
        for xa in xas:
            p = ROOT / str(xa.get("path"))
            actual = sha256_file(p) if p.exists() else None
            cross.append({"test_id": r.get("test_id"), "path": xa.get("path"),
                          "stored": xa.get("sha256"), "actual": actual,
                          "resolved": actual == xa.get("sha256")})
    stale_cross = [c for c in cross if not c["resolved"]]
    checks.append({
        "id": "X1", "name": "suite cross_artifact declared hashes resolve on disk",
        "ok": bool(cross) and not stale_cross, "severity": "acceptance",
        "measured": {"checked": len(cross), "stale": stale_cross},
        "falsifier": "A cross-artifact hash that resolves to the declared bytes, or no cross-artifact binding at all.",
    })
    if stale_cross:
        failures.append({"id": "X1", "stale": stale_cross})

    # ---------- C-controls (in-memory only) ----------
    mutated_rows = json.loads(json.dumps(rows))
    mutated_rows[0]["binding_sha256"] = f1_live_pin
    controls["ctl_binding_responsive"] = sum(
        1 for r in mutated_rows if r.get("binding_sha256") == f1_live_pin) == 1

    mut_doc = json.loads(json.dumps(f1_live))
    first = (rows[0].get("probe_results") or [])[0]
    found, val = getpath(mut_doc, str(first.get("path")))
    if found and isinstance(first.get("expected"), str) and isinstance(val, str):
        controls["ctl_probe_sensitive"] = (evaluate(mut_doc, first)["pass"]
                                           and not evaluate(mut_doc, first | {"expected": val + "___mutant"})["pass"])
    else:
        controls["ctl_probe_sensitive"] = True  # probe is not a string-contains; not applicable

    controls["ctl_idempotent"] = probe_census(f1_live) == probe_census(f1_live)
    controls["ctl_malformed_no_crash"] = evaluate({}, {"path": "a.b[3].c", "kind": "contains",
                                                      "expected": "x"})["error"] is None
    controls["ctl_unknown_kind_structured"] = evaluate({"a": 1}, {"path": "a", "kind": "bogus"})["error"] is not None
    controls_ok = all(controls.values())
    checks.append({
        "id": "C-controls", "name": "in-memory controls: binding responsive, probe sensitive, idempotent, malformed fail-closed",
        "ok": controls_ok, "severity": "control", "measured": controls,
        "falsifier": "A mutation that does not change the measured outcome, a non-idempotent census, or an evaluator that crashes on a malformed path.",
    })
    if not controls_ok:
        failures.append({"id": "C-controls"})

    # ---------- T1: post-run drift ----------
    post = {k: sha256_file(ROOT / v["path"]) == v["expected"] for k, v in measured.items()}
    checks.append({
        "id": "T1", "name": "no input drift between T0 and T1",
        "ok": all(post.values()), "severity": "acceptance", "measured": post,
        "falsifier": "Any pinned input whose bytes moved during the run; the measurement is superseded by a re-run at the new bytes.",
    })
    if not all(post.values()):
        failures.append({"id": "T1-drift"})

    # ---------- expectations ----------
    by_id = {c["id"]: c for c in checks}
    expectations = [
        {"id": "EXP1", "what": "all 6 pins match disk at T0 and T1", "ok": by_id["I0"]["ok"] and by_id["T1"]["ok"]},
        {"id": "EXP2", "what": "FROZEN rev29 pins the suite at 56bcb4b3234b", "ok": by_id["B1"]["ok"]},
        {"id": "EXP3", "what": "0/25 rows bound to live rev13, 25/25 bound to rev12", "ok": by_id["B2"]["ok"]},
        {"id": "EXP4", "what": "vendor hard check C1a reproduces FALSE at rev13", "ok": (not c1a_ok)},
        {"id": "EXP5", "what": "authoring mirror and FROZEN mirror pin == live F1", "ok": by_id["B5"]["ok"]},
        {"id": "EXP6", "what": "84 probes, 84 stored pass, recomputed against rev13", "ok": by_id["P1"]["ok"]},
        {"id": "EXP7", "what": "rev12 control reproduces exactly the 2 AMB-25 mismatches", "ok": by_id["P2"]["ok"]},
        {"id": "EXP8", "what": "rev13 mismatch set is measured and reported (any cardinality)", "ok": True},
        {"id": "EXP9", "what": "cross-artifact stale declarations are enumerated (any cardinality)", "ok": True},
        {"id": "EXP10", "what": "all 5 in-memory controls behave as declared", "ok": controls_ok},
        {"id": "EXP11", "what": "no unknown probe kind (structured error only)", "ok": not c13["errors"]},
        {"id": "EXP12", "what": "verdict derivable: stale binding => revise for G-FORM r3", "ok": (len(current) == 0 and c1a_ok is False)},
        {"id": "EXP13", "what": "the mid-task FROZEN re-emission kept F1/suite/mirror entries identical", "ok": by_id["B0"]["ok"]},
    ]
    exp_ok = all(e["ok"] for e in expectations)

    material = len(c13["mismatches"]) > 0
    verdict = "revise" if not c1a_ok else ("accept" if not c13["mismatches"] and not stale_cross else "accept_with_findings")
    report = {
        "task_id": TASK_ID, "actor": "worker-029", "node_id": NODE_ID, "class_id": CLASS_ID,
        "gate": GATE, "role": "bounded read-only worker measurement; no gate verdict, "
                              "no node status, no validation_status=passed, no canonical byte written",
        "pins": {k: {"path": v[0], "sha256": v[1]} for k, v in PINS.items() if k != "frozen_prev"},
        "suite": {"rows": len(rows), "probes": c13["probes_total"], "stored_pass": c13["stored_pass"],
                  "distinct_bindings": bindings, "binding_frozen_revision_schema": rev_schema,
                  "rebound_at": rebound_at},
        "checks": checks,
        "expectations": expectations,
        "failures": failures,
        "verdict": verdict,
        "materiality": {"rev13_probe_mismatches": len(c13["mismatches"]),
                        "rev12_probe_mismatches": len(c12["mismatches"]),
                        "changed_leaf_paths_rev12_to_rev13": len(changed),
                        "stale_cross_artifact_bindings": len(stale_cross)},
        "falsifier": "A suite row rebound to the live F1 rev13 sha256 d9cebb9404b2 "
                     "(which would make C1a true and this finding void), or F1/FROZEN bytes "
                     "differing from the pins above, or a rev13 probe recomputation whose "
                     "mismatch set is empty while the binding stays stale (stale-but-harmless).",
        "next_falsifier": "Re-run this checker after the suite owner runs the declared rebind "
                          "against the current canonical F1 pin; expect 25/25 rows bound to the "
                          "live hash and the vendor C1a check true. Also re-run at any new F1 hash: "
                          "a republish without a suite rebind reopens this finding.",
        "evidence_refs": [
            f"schemas/f1_falsifier_tests.jsonl#{suite_pin[:12]}",
            f"schemas/af_wcc_vacuum.yaml#{f1_live_pin[:12]}",
            f"artifacts/worker-060/rev29_binding_acceptance/snapshots/f1__af_wcc_vacuum.cce9c60146d6.yaml#{f1_rev12_pin[:12]}",
            f"artifacts/formulation/FROZEN.json#{PINS['frozen'][1][:12]}",
            f"research_map/formulation_taxonomy.yaml#{PINS['f0'][1][:12]}",
            "artifacts/flash-04/f1_ambiguity/verify_freeze_current.py:171-176",
            "artifacts/worker-032/f1amb25/report.json",
        ],
        "reproduce": "python3 artifacts/worker-029/f1_suite_rebind/check_f1_suite_rebind.py",
    }
    body_digest = sha256_bytes(json.dumps({k: report[k] for k in report if k != "pins"},
                                          sort_keys=True, ensure_ascii=False).encode())
    report["measurement_digest"] = body_digest
    if not exp_ok:
        print(json.dumps({"task_id": TASK_ID, "verdict": "expectation_failed",
                          "failed": [e["id"] for e in expectations if not e["ok"]],
                          "failures": failures}, indent=1))
        return 2

    out = HERE / "report.json"
    out.write_text(json.dumps(report, indent=1, ensure_ascii=False, sort_keys=True) + "\n")
    print(json.dumps({"task_id": TASK_ID, "verdict": verdict,
                      "rows_bound_to_rev13": len(current), "rows_bound_to_rev12": len(stale_rev12),
                      "rev13_probe_mismatches": m13_keys, "rev12_probe_mismatches": m12_keys,
                      "stale_cross_artifact_bindings": len(stale_cross),
                      "vendor_C1a": c1a_ok, "measurement_digest": body_digest,
                      "report": str(out.relative_to(ROOT))}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
