#!/usr/bin/env python3
"""W031-F1-FALSIFIER-BINDING-ADJUDICATION-01.

Independent, instrument-based adjudication of the contested binding of
`schemas/f1_falsifier_tests.jsonl` (class AF-WCC-VAC-GEN, node F1, gate G-FORM).

Question under adjudication (lead-audit F1 review, 2026-09-12T00:26:00+08:00):
    "schemas/f1_falsifier_tests.jsonl bound to superseded hash b65fcc0f"

Competing claim (deepseek-flash-04, 00:20:49 / 00:27:20):
    the suite binds the current canonical schema 9a8bd4c9 with 84/84 probes passing.

Method: pin all inputs by sha256, fail closed on drift; classify every sha256-like
token in the suite by its JSON-pointer role (operative binding vs prior-binding /
delta provenance); independently re-resolve all stored probe paths against the
pinned schema YAML and re-evaluate every probe; re-measure inputs at the end.

Authority: worker adjudication input only. No gate verdict, no node status, no
schema or suite edit, no review of F1 beyond the suite-binding contract.
"""
import argparse
import copy
import hashlib
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    print("FATAL: PyYAML required", file=sys.stderr)
    sys.exit(3)

REPO = Path(__file__).resolve().parents[3]

PINS = {
    "suite": (
        "schemas/f1_falsifier_tests.jsonl",
        "c4c477adcb7ab88995c417e8c8c9ef4b9b0415e569babefb61894df3b8425ec2",
    ),
    "f1_schema": (
        "schemas/af_wcc_vacuum.yaml",
        "9a8bd4c9680042a40894f6085f183661500966f2d787a6bf28a7098a271ed503",
    ),
    "f0_taxonomy": (
        "research_map/formulation_taxonomy.yaml",
        "276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc",
    ),
    "frozen_manifest": (
        "artifacts/formulation/FROZEN.json",
        "2554e276a0db70579ce36f7e665c9af81a1707bdc99e33758e861bec1d2df2e3",
    ),
}

SUPERSEDED = {
    "b65fcc0f0118980fe50b4a5eaf5fb637f4f744d0db095105fd8031db1dabcd94": "F1 superseded rev (prior binding)",
    "f512af5f": "F1 superseded rev (snapshot)",
    "f962c117": "F1 superseded rev",
    "66bf917bd368ebd96ee46baa31fb435df106cb4e10152fa0baee8bdd51dfc232": "F0 taxonomy superseded rev3",
    "af24e9c396060e6bff2b2cbf781814f587d60ba0e74fc0764918fa5757ec983b": "FROZEN manifest superseded rev25",
}
SHA_RE = re.compile(r"\b[0-9a-f]{64}\b")
MISSING = object()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def measure_pins():
    out = {}
    for key, (rel, pin) in PINS.items():
        p = REPO / rel
        if not p.exists():
            out[key] = {"path": rel, "exists": False, "expected": pin, "measured": None, "match": False}
            continue
        m = sha256_file(p)
        out[key] = {
            "path": rel,
            "exists": True,
            "expected": pin,
            "measured": m,
            "bytes": p.stat().st_size,
            "match": m == pin,
        }
    return out


def resolve(doc, dotted):
    cur = doc
    for seg in dotted.split("."):
        if isinstance(cur, dict) and seg in cur:
            cur = cur[seg]
        elif isinstance(cur, list) and seg.isdigit() and int(seg) < len(cur):
            cur = cur[int(seg)]
        else:
            return MISSING
    return cur


def recompute_probe(doc, probe):
    """Return (decidable, recomputed_pass, detail)."""
    kind = probe.get("kind")
    expected = probe.get("expected")
    value = resolve(doc, probe.get("path", ""))
    if kind == "path_exists":
        return True, value is not MISSING, "resolved" if value is not MISSING else "unresolved"
    if value is MISSING:
        return True, False, "path does not resolve"
    if kind == "contains":
        return True, str(expected) in json.dumps(value), None
    if kind == "equals":
        return True, json.dumps(value, sort_keys=True) == json.dumps(expected, sort_keys=True), None
    if kind == "is_true":
        return True, value is True, None
    if kind == "is_none":
        return True, value is None, None
    if kind == "nonnull":
        return True, value is not None, None
    return False, None, f"kind {kind!r} not independently decidable by this instrument"


def walk_strings(obj, pointer=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk_strings(v, f"{pointer}/{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk_strings(v, f"{pointer}/{i}")
    elif isinstance(obj, str):
        yield pointer, obj


def role_of(pointer):
    leaf = pointer.rsplit("/", 1)[-1]
    if "prior_binding" in leaf or pointer.startswith("/prior_binding"):
        return "prior_binding_provenance"
    if leaf.startswith("delta_vs_") or "/delta_vs_" in pointer:
        return "delta_provenance"
    if "binding_sha256" in leaf or "binding_ref" in leaf or "binding_at_authoring" in leaf:
        return "operative_binding"
    if "evidence_refs" in pointer or "cross_artifact" in pointer:
        return "evidence_pointer"
    if "schema_snapshot" in pointer or "snapshot" in pointer:
        return "snapshot_pointer"
    return "other"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path(__file__).with_name("report.json")))
    args = ap.parse_args()

    pins_before = measure_pins()
    if not all(v["match"] for v in pins_before.values()):
        print("FATAL: input drift at start; refusing to adjudicate on unpinned bytes", file=sys.stderr)
        print(json.dumps(pins_before, indent=1), file=sys.stderr)
        sys.exit(2)

    suite_path = REPO / PINS["suite"][0]
    f1_path = REPO / PINS["f1_schema"][0]
    f0_path = REPO / PINS["f0_taxonomy"][0]
    frozen_path = REPO / PINS["frozen_manifest"][0]

    rows = [json.loads(line) for line in suite_path.read_text().splitlines() if line.strip()]
    f1 = yaml.safe_load(f1_path.read_text())
    frozen = json.loads(frozen_path.read_text())

    checks = []

    def add(cid, desc, ok, detail, severity="blocking"):
        checks.append(
            {"id": cid, "description": desc, "status": "pass" if ok else "fail",
             "severity": severity, "detail": detail}
        )

    # C1 suite integrity
    f1_pin = PINS["f1_schema"][1]
    f0_pin = PINS["f0_taxonomy"][1]

    def missing_row_fields(rs):
        out = []
        for r in rs:
            for f in ("test_id", "class_id", "spacetime_description", "does_it_satisfy_f1", "deciding_field"):
                if not r.get(f):
                    out.append({"test_id": r.get("test_id"), "field": f})
        return out

    def stale_operative(rs):
        bad = []
        for r in rs:
            for field in ("binding_sha256", "binding_ref", "binding_at_authoring"):
                v = str(r.get(field) or "")
                ok = (v == f1_pin) if field == "binding_sha256" else (f1_pin[:12] in v)
                if not ok:
                    bad.append({"test_id": r.get("test_id"), "field": field, "value": v[:80]})
        return bad

    def probe_disagreement_count(rs, doc):
        bad = 0
        for r in rs:
            for p in r.get("probe_results") or []:
                dec, repass, _ = recompute_probe(doc, p)
                if dec and repass != bool(p.get("pass")):
                    bad += 1
        return bad

    def c6_holds(rs, declared_hash, f0_pin_hash):
        cross = [
            e
            for r in rs
            for e in (r.get("cross_artifact") or [])
            if e.get("path") == PINS["f0_taxonomy"][0]
        ]
        amb25 = next((r for r in rs if r.get("test_id") == "F1-AMB-25"), None)
        return bool(
            declared_hash == f0_pin_hash
            and cross
            and all(e["sha256"] == f0_pin_hash for e in cross)
            and amb25 is not None
            and ((amb25.get("cross_artifact") or [{}])[0].get("sha256") == f0_pin_hash)
        )

    test_ids = [r.get("test_id") for r in rows]
    class_ids = sorted({r.get("class_id") for r in rows})
    add(
        "C1-suite-integrity",
        "suite parses; test ids unique; every row declares the frozen class",
        len(rows) == 25 and len(set(test_ids)) == 25 and class_ids == ["AF-WCC-VAC-GEN"],
        {"rows": len(rows), "unique_test_ids": len(set(test_ids)), "class_ids": class_ids},
    )

    # C2 operative binding
    stale_operative_rows = stale_operative(rows)
    add(
        "C2-operative-binding",
        "every row's operative binding fields (binding_sha256/binding_ref/binding_at_authoring) "
        "reference the pinned current canonical schema, not a superseded hash",
        not stale_operative_rows,
        {"rows_checked": len(rows), "stale_operative_rows": stale_operative_rows},
    )

    # C3 token census by role
    census = []
    for r in rows:
        for pointer, text in walk_strings(r, f"/{r.get('test_id')}"):
            for token in SHA_RE.findall(text):
                if token == f1_pin:
                    cls = "current_f1_schema"
                elif token == PINS["f0_taxonomy"][1]:
                    cls = "current_f0_taxonomy"
                elif token in SUPERSEDED:
                    cls = "superseded_reference"
                else:
                    cls = "unclassified"
                census.append(
                    {
                        "json_pointer": pointer,
                        "token": token,
                        "classification": cls,
                        "role": role_of(pointer),
                        "note": SUPERSEDED.get(token),
                    }
                )
    from collections import Counter

    census_counts = Counter((c["role"], c["classification"]) for c in census)
    stale_in_operative_role = [
        c for c in census if c["role"] == "operative_binding" and c["classification"] != "current_f1_schema"
    ]
    add(
        "C3-token-census",
        "every sha256-like token in the suite is classified; no superseded token appears in an "
        "operative-binding role",
        not stale_in_operative_role and all(c["classification"] != "unclassified" for c in census),
        {
            "tokens_total": len(census),
            "counts_by_role_and_class": {f"{k[0]}|{k[1]}": v for k, v in sorted(census_counts.items())},
            "stale_in_operative_role": stale_in_operative_role,
            "unclassified": [c for c in census if c["classification"] == "unclassified"],
        },
    )

    # C4 required-field completeness (the property worker-090's finding touched)
    missing_fields = missing_row_fields(rows)
    add(
        "C4-row-completeness",
        "every row carries the re-binding fields (test_id, class_id, spacetime_description, "
        "does_it_satisfy_f1, deciding_field)",
        not missing_fields,
        {"rows_checked": len(rows), "missing": missing_fields},
    )

    # C5 independent probe recomputation
    probe_stats = {"total": 0, "decidable": 0, "not_decidable": 0, "agree": 0, "disagree": 0}
    disagreements = []
    undecidable = []
    for r in rows:
        for p in r.get("probe_results") or []:
            probe_stats["total"] += 1
            dec, repass, note = recompute_probe(f1, p)
            if not dec:
                probe_stats["not_decidable"] += 1
                undecidable.append({"test_id": r.get("test_id"), "path": p.get("path"), "kind": p.get("kind"), "note": note})
                continue
            probe_stats["decidable"] += 1
            if repass == bool(p.get("pass")):
                probe_stats["agree"] += 1
            else:
                probe_stats["disagree"] += 1
                disagreements.append(
                    {
                        "test_id": r.get("test_id"),
                        "path": p.get("path"),
                        "kind": p.get("kind"),
                        "expected": p.get("expected"),
                        "stored_pass": p.get("pass"),
                        "recomputed_pass": repass,
                        "note": note,
                    }
                )
    add(
        "C5-probe-recomputation",
        "all stored probes independently re-resolved against the pinned schema YAML; recomputed "
        "pass/fail agrees with the stored value, and all recomputed probes pass",
        probe_stats["disagree"] == 0
        and probe_stats["not_decidable"] == 0
        and probe_stats["decidable"] == probe_stats["total"]
        and all(
            bool(p.get("pass"))
            for r in rows
            for p in (r.get("probe_results") or [])
        ),
        {"stats": probe_stats, "disagreements": disagreements, "undecidable": undecidable},
    )

    # C6 cross-artifact F0 binding equality (F1-AMB-25 contract)
    declared = ((f1.get("f0_binding") or {}).get("declared_f0_sha256"))
    suite_cross = []
    for r in rows:
        for entry in r.get("cross_artifact") or []:
            if entry.get("path") == PINS["f0_taxonomy"][0]:
                suite_cross.append({"test_id": r.get("test_id"), "sha256": entry.get("sha256")})
    amb25 = next((r for r in rows if r.get("test_id") == "F1-AMB-25"), None)
    add(
        "C6-cross-artifact-f0",
        "schema f0_binding.declared_f0_sha256, the suite cross-artifact entry for F0, and the "
        "F1-AMB-25 equality probe all equal the pinned canonical taxonomy hash",
        c6_holds(rows, declared, f0_pin),
        {
            "declared_f0_sha256": declared,
            "pinned_f0_sha256": f0_pin,
            "suite_cross_artifact_entries": suite_cross,
            "F1-AMB-25_present": amb25 is not None,
        },
    )

    # C7 frozen-manifest context (observation, non-blocking)
    frozen_rev = frozen.get("revision")
    frozen_f1 = ((frozen.get("files") or {}).get("schemas/af_wcc_vacuum.yaml") or {}).get("sha256")
    suite_frozen_revs = sorted({r.get("binding_frozen_revision") for r in rows if r.get("binding_frozen_revision")})
    add(
        "C7-frozen-manifest-context",
        "live FROZEN manifest names the pinned F1 hash; suite's declared frozen revision is recorded "
        "as a context observation (not an operative binding)",
        frozen_f1 == f1_pin,
        {
            "live_frozen_revision": frozen_rev,
            "live_frozen_f1_sha256": frozen_f1,
            "pinned_f1_sha256": f1_pin,
            "suite_binding_frozen_revision_values": suite_frozen_revs,
            "observation": (
                "suite pins FROZEN revision 25 while the live manifest is revision 26; rev26 keeps "
                "schemas/af_wcc_vacuum.yaml at the pinned 9a8bd4c9 hash, so this is a provenance-pin "
                "lag, not an operative stale binding"
            ),
        },
        severity="advisory",
    )

    # Negative controls: each blocking check must detect a planted defect, else it is vacuous.
    controls = []

    m = copy.deepcopy(rows)
    m[0]["binding_sha256"] = "b65fcc0f0118980fe50b4a5eaf5fb637f4f744d0db095105fd8031db1dabcd94"
    controls.append(
        {
            "id": "K1-stale-operative-binding",
            "planted": "row0 binding_sha256 -> b65fcc0f (superseded F1 rev)",
            "expected": "detected",
            "detected": len(stale_operative(m)) > 0,
        }
    )

    m = copy.deepcopy(rows)
    m[0]["probe_results"][0]["path"] = "no_such_path_planted_by_control"
    controls.append(
        {
            "id": "K2-unresolvable-probe-path",
            "planted": "row0 probe0 path -> nonexistent path (stored pass stays true)",
            "expected": "detected",
            "detected": probe_disagreement_count(m, f1) > 0,
        }
    )

    m = copy.deepcopy(rows)
    m[0]["probe_results"][0]["expected"] = "PLANTED-STRING-NOT-IN-SCHEMA"
    controls.append(
        {
            "id": "K3-mutated-probe-expectation",
            "planted": "row0 probe0 expected -> planted string (stored pass stays true)",
            "expected": "detected",
            "detected": probe_disagreement_count(m, f1) > 0,
        }
    )

    m = copy.deepcopy(rows)
    for r in m:
        for entry in r.get("cross_artifact") or []:
            if entry.get("path") == PINS["f0_taxonomy"][0]:
                entry["sha256"] = "0" * 64
    controls.append(
        {
            "id": "K4-f0-equality-mutation",
            "planted": "all F0 cross-artifact hashes -> 0*64",
            "expected": "detected",
            "detected": not c6_holds(m, declared, f0_pin),
        }
    )

    m = copy.deepcopy(rows)
    m[0].pop("deciding_field", None)
    controls.append(
        {
            "id": "K5-missing-required-field",
            "planted": "row0 deciding_field removed",
            "expected": "detected",
            "detected": len(missing_row_fields(m)) > 0,
        }
    )

    controls_ok = all(c["detected"] for c in controls)

    # Verdict on the contested finding
    reproduced = bool(stale_operative_rows) or bool(stale_in_operative_role)
    adjudication = {
        "finding_under_test": (
            "lead-audit F1 review 2026-09-12T00:26:00+08:00: "
            "'schemas/f1_falsifier_tests.jsonl bound to superseded hash b65fcc0f'"
        ),
        "verdict": "REPRODUCED" if reproduced else "REFUTED_AT_PINNED_HASH",
        "reason": (
            "no operative-binding field references b65fcc0f; the 24 b65fcc0f occurrences are "
            "prior_binding_* / delta_vs_* provenance fields, which exist by design"
            if not reproduced
            else "at least one operative-binding field references a superseded hash"
        ),
        "operative_binding_rows_current": len(rows) - len(stale_operative_rows),
        "operative_binding_rows_total": len(rows),
        "b65fcc0f_occurrences": sum(1 for c in census if c["token"].startswith("b65fcc0f")),
        "b65fcc0f_roles": sorted({c["role"] for c in census if c["token"].startswith("b65fcc0f")}),
        "score_scope": "binding contract of the falsifier suite only; NOT a full-schema F1 verdict",
    }

    pins_after = measure_pins()
    drift = {
        k: {"before": pins_before[k]["measured"], "after": pins_after[k]["measured"],
            "stable": pins_before[k]["measured"] == pins_after[k]["measured"]}
        for k in PINS
    }
    stable = all(v["stable"] for v in drift.values()) and all(v["match"] for v in pins_after.values())

    report = {
        "artifact_type": "f1_falsifier_binding_adjudication",
        "artifact_version": "1.0.0",
        "artifact_id": "artifacts/worker-031/f1_falsifier_binding/report.json",
        "task": {
            "task_id": "W031-F1-FALSIFIER-BINDING-ADJUDICATION-01",
            "node_id": "F1",
            "gate": "G-FORM",
            "class_ids": ["AF-WCC-VAC-GEN"],
            "authority": "worker independent measurement/adjudication input only; no gate verdict, "
                         "no node status, no schema edit",
        },
        "pins": pins_before,
        "checks": checks,
        "controls": controls,
        "controls_ok": controls_ok,
        "token_census": census,
        "adjudication": adjudication,
        "falsifier": (
            "Re-run this instrument at the pinned hashes; the adjudication is falsified if any "
            "operative binding field references a hash other than 9a8bd4c96, if any stored probe "
            "fails independent recomputation against the pinned schema, if the F0 equality probe "
            "does not hold at the pinned taxonomy hash, or if any input hash has moved. A control "
            "that stops detecting its planted defect also voids the adjudication."
        ),
        "reopen_rule": (
            "Any change to the sha256 of schemas/f1_falsifier_tests.jsonl, schemas/af_wcc_vacuum.yaml, "
            "research_map/formulation_taxonomy.yaml or artifacts/formulation/FROZEN.json makes this "
            "report stale and requires a re-run before citation."
        ),
        "drift": drift,
        "stable": stable,
        "generator": "worker-031",
        "instrument": "artifacts/worker-031/f1_falsifier_binding/check_binding.py",
    }

    Path(args.out).write_text(json.dumps(report, indent=1) + "\n")

    blocking_fail = [c["id"] for c in checks if c["status"] == "fail" and c["severity"] == "blocking"]
    print(json.dumps({
        "report": args.out,
        "stable": stable,
        "controls_ok": controls_ok,
        "blocking_failures": blocking_fail,
        "adjudication": adjudication["verdict"],
        "checks": {c["id"]: c["status"] for c in checks},
    }, indent=1))

    if not stable:
        sys.exit(2)
    if blocking_fail or not controls_ok:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
