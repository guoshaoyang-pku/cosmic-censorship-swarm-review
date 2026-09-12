#!/usr/bin/env python3
"""Worker-04 general delta rebind of the F1 (AF-WCC-VAC-GEN) ambiguity suite.

Carries every existing row to the CURRENT canonical F1 schema binding, re-runs all stored
probes against it, recomputes observed excerpts and deciding-field deltas, optionally adds
the cross-artifact declared-F0 integrity probe, then writes the suite, a frozen version copy
and a delta report.

Reads : schemas/af_wcc_vacuum.yaml (canonical, authoritative)
        artifacts/formulation/schemas/af_wcc_vacuum.yaml (authoring mirror)
        artifacts/formulation/FROZEN.json
        schemas/f1_falsifier_tests.jsonl (current suite)
Writes: schemas/f1_falsifier_tests.jsonl
        artifacts/flash-04/f1_ambiguity/versions/f1_falsifier_tests.<new8>.jsonl
        artifacts/flash-04/f1_ambiguity/schema_snapshots/af_wcc_vacuum.<new8>.yaml
        artifacts/flash-04/f1_ambiguity/rebind_current_delta_report.json
No map mutation, no gate verdict, no status promotion.

Usage: python3 artifacts/flash-04/f1_ambiguity/rebind_current.py
Exit: 0 = rebind done or already current; 2 = a probe failed; 3 = binding drift.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
CANON_SCHEMA = ROOT / "schemas/af_wcc_vacuum.yaml"
AUTH_SCHEMA = ROOT / "artifacts/formulation/schemas/af_wcc_vacuum.yaml"
FROZEN = ROOT / "artifacts/formulation/FROZEN.json"
SUITE = ROOT / "schemas/f1_falsifier_tests.jsonl"
F0 = ROOT / "research_map/formulation_taxonomy.yaml"
SNAP_DIR = ROOT / "artifacts/flash-04/f1_ambiguity/schema_snapshots"
VERSION_DIR = ROOT / "artifacts/flash-04/f1_ambiguity/versions"
REPORT = ROOT / "artifacts/flash-04/f1_ambiguity/rebind_current_delta_report.json"
ADJUDICATION = ROOT / "artifacts/formulation/reviews/ADJUDICATION_flash04_ambiguity.md"
RULE_SPEC = ROOT / "artifacts/formulation/rule_spec.json"
ALIASES = ROOT / "artifacts/formulation/VOCAB_ALIASES.json"
TAXONOMY_AUTHOR = ROOT / "artifacts/formulation/formulation_taxonomy.yaml"
INBOX = ROOT / "comms/inbox/deepseek-flash-04.jsonl"

CLASS_ID = "AF-WCC-VAC-GEN"
NODE_ID = "F1"
GATE = "G-FORM"
CST = timezone(timedelta(hours=8))
OPEN_OBLIGATIONS = ("F1-AMB-01", "F1-AMB-02", "F1-AMB-03", "F1-AMB-15")


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


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


def run_probe(doc, spec: dict) -> dict:
    """Re-run a stored probe against a schema; returns the stored-row shape."""
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


def new_f0_test(new_sha: str, schema: dict, schema_ref: str, frozen_ref: str, f0_sha: str,
                f0_ref: str, adjudication_ref: str) -> dict:
    common = dict(
        artifact_version="0.4.0",
        author="deepseek-flash-04",
        artifact_kind="f1_ambiguity_probe",
        class_id=CLASS_ID,
        node_id=NODE_ID,
        gate=GATE,
        binding_sha256=new_sha,
        binding_ref=schema_ref,
        binding_at_authoring=schema_ref,
    )
    probe_specs = [
        {"path": "f0_binding.declared_f0_sha256", "kind": "equals", "value": f0_sha,
         "role": "deciding_field"},
        {"path": "f0_binding.declared_f0_artifact", "kind": "equals",
         "value": "research_map/formulation_taxonomy.yaml", "role": "corroborating"},
        {"path": "f0_binding.rule", "kind": "contains", "value": "must be refreshed",
         "role": "corroborating"},
        {"path": "f0_binding.binding_note", "kind": "contains", "value": "astra-classscope-02",
         "role": "corroborating"},
        {"path": "class_identity_variants", "kind": "contains",
         "value": "registered_variant_not_written", "role": "corroborating"},
    ]
    return {
        **common,
        "test_id": "F1-AMB-25",
        "title": "Declared-F0 hash staleness: class contract bound to an unstated F0 revision",
        "ambiguity_kind": "declared_f0_binding_staleness",
        "spacetime_description": (
            "A vacuum AF datum whose class assignment depends on the declared F0 contract rather than on geometry: "
            "the astra-classscope-02 amendment moved the set-based visibility reading into class_identity_variants "
            "(variant SET, is_this_class=false) and added AF-WCC-SCALAR-SPH to anti_scope. A datum sitting on that "
            "boundary (a set-based-visible singularity, or a scalar/spherical configuration) is in-class under F0 "
            "rev3 readings and out-of-class under the rev4 readings. The test datum is therefore the F0 contract pair "
            "itself: which revision is in force decides the WCC class verdict for that datum."
        ),
        "question": "Does the schema pin the F0 contract by hash, so a reviewer can tell which F0 revision decides membership for a boundary datum?",
        "does_it_satisfy_f1": "ambiguous",
        "satisfies_in_class": "yes under the declared F0 rev4 contract (variant SET not written, scalar class anti-scope); indeterminate if f0_binding.declared_f0_sha256 is stale",
        "satisfies_conclusion": "not applicable to the boundary datum until the F0 binding is pinned; the class conclusion is carried by the schema statement, not by this row",
        "deciding_field": "f0_binding.declared_f0_sha256",
        "deciding_field_alternates": ["f0_binding.declared_f0_artifact", "f0_binding.rule"],
        "deciding_field_contract": "f0_binding.declared_f0_sha256 plus f0_binding.rule",
        "deciding_field_status": "decided_by_cross_artifact_hash_equality",
        "falsifier_strength": "decided",
        "schema_open_expected": False,
        "probe_results": [run_probe(schema, s) for s in probe_specs],
        "cross_artifact": [{"path": "research_map/formulation_taxonomy.yaml", "sha256": f0_sha}],
        "why": (
            "The rev10 delta surface is entirely in f0_binding: the declared F0 hash was refreshed from 66bf917b to "
            "the rev4 taxonomy hash after the astra-classscope-02 amendment. A nonnull probe cannot detect a stale "
            "declared hash, so this row adds an equality probe against the measured F0 artifact hash and records the "
            "same pair as a cross_artifact binding that the verifier re-checks against disk."
        ),
        "next_falsifier": "Run C9 in verify_freeze_current.py: if research_map/formulation_taxonomy.yaml stops hashing to the stored cross_artifact sha, this row (and the schema's f0_binding) must be refreshed before any G-FORM verdict.",
        "falsifier": "An F0 amendment that changes research_map/formulation_taxonomy.yaml without refreshing f0_binding.declared_f0_sha256, or a schema whose declared F0 hash does not equal the on-disk F0 artifact.",
        "evidence_refs": [schema_ref, frozen_ref, f0_ref, adjudication_ref, "comms/inbox/deepseek-flash-04.jsonl:1-3"],
    }


def main() -> int:
    if not (CANON_SCHEMA.exists() and SUITE.exists() and FROZEN.exists()):
        print("missing canonical schema, suite or FROZEN manifest")
        return 3
    new_sha = sha256_file(CANON_SCHEMA)
    frozen = json.loads(FROZEN.read_text())
    frozen_rev = frozen.get("revision")
    canon_pin = frozen.get("files", {}).get("schemas/af_wcc_vacuum.yaml", {}).get("sha256")
    auth_pin = frozen.get("files", {}).get("artifacts/formulation/schemas/af_wcc_vacuum.yaml", {}).get("sha256")
    if canon_pin != new_sha:
        print(f"CANONICAL BINDING DRIFT: FROZEN rev{frozen_rev} pins {canon_pin} but canonical is {new_sha}")
        return 3

    rows = [json.loads(line) for line in SUITE.read_text().splitlines() if line.strip()]
    old_bindings = sorted({r["binding_sha256"] for r in rows})
    if len(old_bindings) != 1:
        print(f"suite has mixed bindings: {old_bindings}")
        return 3
    old_sha = old_bindings[0]
    old_snapshot = SNAP_DIR / f"af_wcc_vacuum.{old_sha[:8]}.yaml"
    if not old_snapshot.exists():
        print(f"prior schema snapshot missing: {old_snapshot}")
        return 3

    schema = yaml.safe_load(CANON_SCHEMA.read_text())
    prior = yaml.safe_load(old_snapshot.read_text())
    schema_ref = ref("schemas/af_wcc_vacuum.yaml", new_sha)
    prior_ref = ref("schemas/af_wcc_vacuum.yaml", old_sha)
    frozen_ref = ref("artifacts/formulation/FROZEN.json", sha256_file(FROZEN))
    adjudication_ref = ref("artifacts/formulation/reviews/ADJUDICATION_flash04_ambiguity.md", sha256_file(ADJUDICATION))
    f0_sha = sha256_file(F0)
    f0_ref = ref("research_map/formulation_taxonomy.yaml", f0_sha)

    SNAP_DIR.mkdir(parents=True, exist_ok=True)
    new_snapshot = SNAP_DIR / f"af_wcc_vacuum.{new_sha[:8]}.yaml"
    if not new_snapshot.exists() or sha256_file(new_snapshot) != new_sha:
        new_snapshot.write_bytes(CANON_SCHEMA.read_bytes())

    base_evidence = [schema_ref, frozen_ref, f0_ref, adjudication_ref,
                     ref("artifacts/formulation/rule_spec.json", sha256_file(RULE_SPEC)),
                     ref("artifacts/formulation/VOCAB_ALIASES.json", sha256_file(ALIASES)),
                     ref("artifacts/formulation/formulation_taxonomy.yaml", sha256_file(TAXONOMY_AUTHOR)),
                     "comms/inbox/deepseek-flash-04.jsonl:1-3"]

    out, failures, flips, delta_counts, field_changes = [], [], [], {}, []
    for old in rows:
        rec = dict(old)
        old_pass = {p["path"]: p["pass"] for p in old.get("probe_results", [])}
        rec["artifact_version"] = "0.4.0"
        rec["binding_sha256"] = new_sha
        rec["binding_ref"] = schema_ref
        rec["binding_at_authoring"] = schema_ref
        rec["binding_frozen_revision"] = frozen_rev
        rec["prior_binding_sha256"] = old_sha
        rec["prior_binding_ref"] = prior_ref
        rec["prior_binding_at_authoring"] = old.get("binding_at_authoring", prior_ref)
        rec["probe_results"] = [run_probe(schema, p) for p in old.get("probe_results", [])]
        for p in rec["probe_results"]:
            if not p["pass"]:
                failures.append([rec["test_id"], p["path"], p["expected"]])
            if p["path"] in old_pass and old_pass[p["path"]] != p["pass"]:
                flips.append({"test_id": rec["test_id"], "path": p["path"],
                              "old_pass": old_pass[p["path"]], "new_pass": p["pass"]})
        dec = rec["deciding_field"]
        old_val, new_val = getpath(prior, dec), getpath(schema, dec)
        changed = flat(old_val) != flat(new_val)
        status = ("field_added" if old_val is None and new_val is not None
                  else "field_content_changed" if changed else "unchanged")
        rec[f"delta_vs_{old_sha[:8]}"] = {
            "status": status,
            "changed_fields": [dec] if changed else [],
            "prior_excerpt": flat(old_val)[:200] if old_val is not None else None,
            "new_excerpt": flat(new_val)[:200] if new_val is not None else None,
        }
        if changed:
            field_changes.append({"field": dec, "tests": [rec["test_id"]],
                                  "prior": flat(old_val)[:160], "new": flat(new_val)[:160]})
        rec["evidence_refs"] = base_evidence
        delta_counts[status] = delta_counts.get(status, 0) + 1
        out.append(rec)

    if "F1-AMB-25" not in {r["test_id"] for r in out}:
        out.append(new_f0_test(new_sha, schema, schema_ref, frozen_ref, f0_sha, f0_ref, adjudication_ref))

    out.sort(key=lambda r: r["test_id"])
    # fail-closed guard: the canonical file, freeze pin or declared-F0 hash must not move while we build
    frozen_now = json.loads(FROZEN.read_text())
    pin_now = frozen_now.get("files", {}).get("schemas/af_wcc_vacuum.yaml", {}).get("sha256")
    f0_now = sha256_file(F0)
    declared_now = getpath(schema, "f0_binding.declared_f0_sha256")
    if sha256_file(CANON_SCHEMA) != new_sha or pin_now != new_sha:
        print(f"BINDING MOVED DURING REBIND: canonical={sha256_file(CANON_SCHEMA)[:16]} pin={pin_now and pin_now[:16]} expected={new_sha[:16]}; nothing written")
        return 3
    if declared_now != f0_now:
        print(f"DECLARED-F0 MOVED DURING REBIND: declared={declared_now and declared_now[:16]} disk={f0_now[:16]}; nothing written")
        return 3
    SUITE.write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in out))
    suite_sha = sha256_file(SUITE)
    VERSION_DIR.mkdir(parents=True, exist_ok=True)
    version_copy = VERSION_DIR / f"f1_falsifier_tests.{new_sha[:8]}.jsonl"
    version_copy.write_text(SUITE.read_text())

    report = {
        "report_id": "w04-f1-rebind-current",
        "created_at": now(),
        "actor": "deepseek-flash-04",
        "role": "bounded worker; no map mutation, no gate verdict, no status promotion",
        "assignment_ref": "comms/inbox/deepseek-flash-04.jsonl:1 (asg-2026-09-11-F1-deepseek-flash-04-13)",
        "node_id": NODE_ID,
        "class_id": CLASS_ID,
        "gate": GATE,
        "action": "carry the F1 ambiguity suite to the current frozen canonical schema and report deltas only",
        "binding": {
            "path": "schemas/af_wcc_vacuum.yaml",
            "sha256": new_sha,
            "frozen_manifest_revision": frozen_rev,
            "schema_internal_revision": schema.get("revision"),
            "snapshot": str(new_snapshot.relative_to(ROOT)),
            "frozen_pin_matches": canon_pin == new_sha,
        },
        "prior_binding": {
            "sha256": old_sha,
            "snapshot": str(old_snapshot.relative_to(ROOT)),
            "schema_internal_revision": prior.get("revision"),
        },
        "mirror_state": {
            "path": "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
            "sha256": sha256_file(AUTH_SCHEMA),
            "frozen_pin": auth_pin,
            "equals_canonical": sha256_file(AUTH_SCHEMA) == new_sha,
        },
        "f0_binding_state": {
            "declared_f0_artifact": "research_map/formulation_taxonomy.yaml",
            "declared_f0_sha256": getpath(schema, "f0_binding.declared_f0_sha256"),
            "measured_f0_sha256": f0_sha,
            "match": getpath(schema, "f0_binding.declared_f0_sha256") == f0_sha,
        },
        "tests_total": len(out),
        "carried": len(rows),
        "new": len(out) - len(rows),
        "delta_counts": delta_counts,
        "field_changes_observed": field_changes,
        "probe_failures": failures,
        "probe_flips_vs_" + old_sha[:8]: flips,
        "open_obligations_retained": [{"test": t, "field": next((r["deciding_field"] for r in out if r["test_id"] == t), None),
                                       "status": next((r.get("deciding_field_status") for r in out if r["test_id"] == t), None)}
                                      for t in OPEN_OBLIGATIONS],
        "suite_path": "schemas/f1_falsifier_tests.jsonl",
        "suite_sha256": suite_sha,
        "suite_version_copy": str(version_copy.relative_to(ROOT)),
        "suite_records_with_ids_evidence_hash_falsifier": all(
            r.get("test_id") and r.get("evidence_refs") and r.get("binding_sha256") and r.get("falsifier") for r in out),
        "evidence_refs": [schema_ref, frozen_ref, f0_ref, adjudication_ref,
                          ref("schemas/f1_falsifier_tests.jsonl", suite_sha)],
        "falsifier": "A carried probe failing to resolve in the new binding, a deciding-field verdict flipping without a FROZEN revision entry, or a declared F0 hash that does not equal the on-disk F0 artifact.",
        "verification_command": "python3 artifacts/flash-04/f1_ambiguity/verify_freeze_current.py",
    }
    REPORT.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps({
        "rebind": "done",
        "frozen_revision": frozen_rev,
        "old_binding": old_sha[:16],
        "new_binding": new_sha[:16],
        "tests_total": len(out),
        "new_tests": len(out) - len(rows),
        "delta_counts": delta_counts,
        "probe_failures": len(failures),
        "probe_flips": len(flips),
        "f0_match": report["f0_binding_state"]["match"],
        "suite_sha256": suite_sha,
        "report": str(REPORT.relative_to(ROOT)),
        "report_sha256": sha256_file(REPORT),
    }, indent=1))
    return 2 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
