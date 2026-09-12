#!/usr/bin/env python3
"""Worker-04 rev20 rebind of the F1 (AF-WCC-VAC-GEN) ambiguity suite.

Prior binding : artifacts/formulation/schemas/af_wcc_vacuum.yaml#sha256:f962c117ba11598f (FROZEN rev19, schema internal rev8)
New binding   : artifacts/formulation/schemas/af_wcc_vacuum.yaml#sha256:b65fcc0f0118980f (FROZEN rev20, schema internal rev9)

Delta surfaces introduced by rev9 (observed by exact content diff, not by reading the changelog):
  - NEW top-level block `class_identity_variants`: the set-based visibility reading is registered as
    variant SET, is_this_class=false, status=registered_variant_not_written.
  - `anti_scope.not_this_class` gained AF-WCC-SCALAR-SPH and the H2_loc variant entry.

What this does (no map mutation, no gate verdict, no status promotion):
  1. verifies the on-disk F1 schema hash and the FROZEN.json rev20 pin agree;
  2. snapshots both the prior (f962c117) and new (b65fcc0f) schemas under my own artifact tree;
  3. re-runs all 22 carried probes and computes exact deciding-field deltas vs f962c117;
  4. adds F1-AMB-23/24 covering the two rev9 delta surfaces;
  5. rewrites the canonical suite schemas/f1_falsifier_tests.jsonl and writes a delta report.

Usage: python3 artifacts/flash-04/f1_ambiguity/rebind_b65fcc0f.py
Exit: 0 = all probes pass; 2 = a probe failed (finding, printed); 3 = binding drift.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = ROOT / "artifacts/formulation/schemas/af_wcc_vacuum.yaml"
CANONICAL_SCHEMA_PATH = ROOT / "schemas/af_wcc_vacuum.yaml"
SUITE_PATH = ROOT / "schemas/f1_falsifier_tests.jsonl"
FROZEN_PATH = ROOT / "artifacts/formulation/FROZEN.json"
ADJUDICATION_PATH = ROOT / "artifacts/formulation/reviews/ADJUDICATION_flash04_ambiguity.md"
RULE_SPEC_PATH = ROOT / "artifacts/formulation/rule_spec.json"
ALIASES_PATH = ROOT / "artifacts/formulation/VOCAB_ALIASES.json"
TAXONOMY_PATH = ROOT / "artifacts/formulation/formulation_taxonomy.yaml"
INBOX_PATH = ROOT / "comms/inbox/deepseek-flash-04.jsonl"
REBIND_MOD_PATH = ROOT / "artifacts/flash-04/f1_ambiguity/rebind_f962c117.py"
PRIOR_SNAPSHOT = ROOT / "artifacts/flash-04/f1_ambiguity/schema_snapshots/af_wcc_vacuum.f962c117.yaml"
NEW_SNAPSHOT = ROOT / "artifacts/flash-04/f1_ambiguity/schema_snapshots/af_wcc_vacuum.b65fcc0f.yaml"
REPORT_PATH = ROOT / "artifacts/flash-04/f1_ambiguity/rebind_b65fcc0f_delta_report.json"
SUITE_VERSION_PATH = ROOT / "artifacts/flash-04/f1_ambiguity/versions/f1_falsifier_tests.b65fcc0f.prefreeze.jsonl"

NEW_SHA = "b65fcc0f0118980fe50b4a5eaf5fb637f4f744d0db095105fd8031db1dabcd94"
PRIOR_SHA = "f962c117ba11598f9d5c778cb015809961a371339612b52808c2b9c3446abe96"
CLASS_ID = "AF-WCC-VAC-GEN"
NODE_ID = "F1"
GATE = "G-FORM"
CST = timezone(timedelta(hours=8))


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


def flat(value) -> str:
    return json.dumps(value, default=str, ensure_ascii=False)


def getpath(doc, path: str):
    cur = doc
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("rb_f962c117", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def new_delta_tests(anchors: dict, probe) -> list[dict]:
    common = dict(
        artifact_version="0.3.0",
        author="deepseek-flash-04",
        artifact_kind="f1_ambiguity_probe",
        class_id=CLASS_ID,
        node_id=NODE_ID,
        gate=GATE,
        binding_sha256=NEW_SHA,
        binding_ref=anchors["schema_ref"],
        binding_frozen_revision=anchors["frozen_revision"],
        prior_binding_sha256=PRIOR_SHA,
        prior_binding_ref=anchors["prior_schema_ref"],
    )
    rows = []
    rows.append({
        **common,
        "test_id": "F1-AMB-23",
        "title": "Set-based visibility variant must not be bound to the WCC class",
        "ambiguity_kind": "variant_vs_class_visibility_reading",
        "spacetime_description": (
            "A vacuum development whose only incomplete causal geodesic gamma lies in the union "
            "J^-(I+) = union_{q in I+} J^-(q) but has no tail gamma([t0,T)) inside J^-(q) for any "
            "single q in I+. The single-q tail predicate says gamma is NOT visible (no visible "
            "singularity); the set-based reading says gamma IS visible. One datum, opposite verdicts."
        ),
        "question": "Which slot decides membership for this datum, and does the schema forbid scoring the set-based verdict as AF-WCC-VAC-GEN?",
        "does_it_satisfy_f1": "no",
        "satisfies_in_class": "yes under the class predicate (no single-q visible singularity); the datum would be a violation only under variant SET",
        "satisfies_conclusion": "the class conclusion (no visible singularity, single-q tail reading) holds for this datum; the set-based reading would report a counterexample",
        "deciding_field": "class_identity_variants",
        "deciding_field_alternates": ["visibility.definition", "visibility.predicate_name"],
        "deciding_field_contract": "visibility.predicate_name plus class_identity_variants",
        "deciding_field_status": "decided_variant_registry_not_this_class",
        "falsifier_strength": "decided",
        "schema_open_expected": False,
        "probe_results": [
            probe(anchors["_schema"], {"path": "class_identity_variants", "kind": "contains", "value": "set_based_visibility_reading"}),
            probe(anchors["_schema"], {"path": "class_identity_variants", "kind": "contains", "value": '"is_this_class": false'}),
            probe(anchors["_schema"], {"path": "class_identity_variants", "kind": "contains", "value": "registered_variant_not_written"}),
            probe(anchors["_schema"], {"path": "class_identity_variants", "kind": "contains", "value": "not as a class", "role": "corroborating"}),
            probe(anchors["_schema"], {"path": "visibility.definition", "kind": "contains", "value": "TAIL"}),
        ],
        "why": (
            "rev9 moves the set-based reading out of the class and into a registered variant pointer with "
            "is_this_class=false. Without a probe on that block, a solver could carry a set-based verdict into "
            "AF-WCC-VAC-GEN and the schema would look silent. The probe makes the non-equivalence machine-checkable "
            "at the field level; the mathematical non-equivalence remains a proof obligation (D1)."
        ),
        "next_falsifier": "A gate-accepted revision in which variant SET is bound to AF-WCC-VAC-GEN, or class_identity_variants is removed while variant SET stays live.",
        "falsifier": "An accepted reading in which class_identity_variants.SET.is_this_class is true, or a set-based visible-singularity result is scored under AF-WCC-VAC-GEN.",
    })
    rows.append({
        **common,
        "test_id": "F1-AMB-24",
        "title": "Scalar/spherical matter class is anti-scope, not a vacuum WCC instance",
        "ambiguity_kind": "matter_content_scope_leakage",
        "spacetime_description": (
            "A static spherically symmetric Einstein-scalar-field configuration (AF-WCC-SCALAR-SPH) with a "
            "future-incomplete causal geodesic visible from I+. It satisfies a WCC-shaped statement for the "
            "scalar class, but its matter content and symmetry are not the vacuum class's."
        ),
        "question": "Does the class exclude the scalar/spherical configuration at the field level, or can a scalar result be booked against AF-WCC-VAC-GEN?",
        "does_it_satisfy_f1": "no",
        "satisfies_in_class": "no (matter content is not vacuum; the class contract is vacuum Einstein)",
        "satisfies_conclusion": "not applicable to this class; the scalar class carries its own schema",
        "deciding_field": "anti_scope.not_this_class",
        "deciding_field_alternates": ["data_class.matter", "class_id"],
        "deciding_field_contract": "class_id plus anti_scope.not_this_class",
        "deciding_field_status": "decided_anti_scope_entry",
        "falsifier_strength": "decided",
        "schema_open_expected": False,
        "probe_results": [
            probe(anchors["_schema"], {"path": "anti_scope.not_this_class", "kind": "contains", "value": "AF-WCC-SCALAR-SPH"}),
            probe(anchors["_schema"], {"path": "anti_scope.not_this_class", "kind": "contains", "value": "different matter content and symmetry"}),
            probe(anchors["_schema"], {"path": "class_id", "kind": "equals", "value": CLASS_ID}),
            probe(anchors["_schema"], {"path": "data_class.matter", "kind": "equals", "value": "none"}),
        ],
        "why": (
            "rev9 adds AF-WCC-SCALAR-SPH to the anti-scope. The vacuum class and the scalar class have different "
            "ambient spaces and genericity manifolds, so a scalar counterexample cannot falsify this class. The "
            "probe pins the exclusion and the vacuum matter slot together, which is the pair a reviewer needs."
        ),
        "next_falsifier": "A gate-accepted revision that drops the AF-WCC-SCALAR-SPH anti-scope entry while data_class.matter stays none, or a scalar-matter result booked as AF-WCC-VAC-GEN.",
        "falsifier": "A gate-accepted binding in which AF-WCC-SCALAR-SPH data are scored under AF-WCC-VAC-GEN.",
    })
    return rows


def main() -> int:
    schema_sha = sha256_file(SCHEMA_PATH)
    if schema_sha != NEW_SHA:
        print(f"BINDING DRIFT: {SCHEMA_PATH} sha256={schema_sha} expected={NEW_SHA}")
        return 3
    frozen = json.loads(FROZEN_PATH.read_text())
    entry = frozen["files"]["artifacts/formulation/schemas/af_wcc_vacuum.yaml"]
    if entry["sha256"] != NEW_SHA:
        print(f"BINDING DRIFT: FROZEN.json declares {entry['sha256']} expected {NEW_SHA}")
        return 3
    if sha256_file(PRIOR_SNAPSHOT) != PRIOR_SHA:
        print(f"PRIOR SNAPSHOT DRIFT: {PRIOR_SNAPSHOT} does not hash {PRIOR_SHA}")
        return 3
    NEW_SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    if not NEW_SNAPSHOT.exists() or sha256_file(NEW_SNAPSHOT) != NEW_SHA:
        NEW_SNAPSHOT.write_bytes(SCHEMA_PATH.read_bytes())

    schema = yaml.safe_load(SCHEMA_PATH.read_text())
    prior = yaml.safe_load(PRIOR_SNAPSHOT.read_text())
    rb = load_module(REBIND_MOD_PATH)
    rb.NEW_SHA = NEW_SHA
    rb.PRIOR_SHA = PRIOR_SHA

    anchors = {
        "schema_ref": ref("artifacts/formulation/schemas/af_wcc_vacuum.yaml", NEW_SHA),
        "prior_schema_ref": ref("artifacts/formulation/schemas/af_wcc_vacuum.yaml", PRIOR_SHA),
        "frozen_ref": ref("artifacts/formulation/FROZEN.json", sha256_file(FROZEN_PATH)),
        "adjudication_ref": ref("artifacts/formulation/reviews/ADJUDICATION_flash04_ambiguity.md", sha256_file(ADJUDICATION_PATH)),
        "rule_spec_ref": ref("artifacts/formulation/rule_spec.json", sha256_file(RULE_SPEC_PATH)),
        "aliases_ref": ref("artifacts/formulation/VOCAB_ALIASES.json", sha256_file(ALIASES_PATH)),
        "taxonomy_ref": ref("artifacts/formulation/formulation_taxonomy.yaml", sha256_file(TAXONOMY_PATH)),
        "prior_suite_ref": ref("schemas/f1_falsifier_tests.jsonl", sha256_file(SUITE_PATH)),
        "prior_snapshot_ref": ref("artifacts/flash-04/f1_ambiguity/schema_snapshots/af_wcc_vacuum.f962c117.yaml", PRIOR_SHA),
        "frozen_revision": frozen.get("revision"),
        "_schema": schema,
    }
    base_evidence = [
        anchors["schema_ref"], anchors["frozen_ref"], anchors["adjudication_ref"],
        anchors["rule_spec_ref"], anchors["aliases_ref"], anchors["taxonomy_ref"],
        anchors["prior_snapshot_ref"], "comms/inbox/deepseek-flash-04.jsonl:1-3",
    ]

    old_rows = [json.loads(line) for line in SUITE_PATH.read_text().splitlines() if line.strip()]
    carried = [r for r in old_rows if r["test_id"].startswith("F1-AMB-") and int(r["test_id"].split("-")[-1]) <= 17]
    if len(old_rows) not in (22, 24) or len(carried) != 17:
        print(f"unexpected suite shape: {len(old_rows)} rows, {len(carried)} carried")
        return 3
    old_suite_sha = sha256_file(SUITE_PATH)
    archive = ROOT / f"artifacts/flash-04/f1_ambiguity/versions/f1_falsifier_tests.{old_suite_sha[:8]}.jsonl"
    if not archive.exists():
        archive.write_text(SUITE_PATH.read_text())

    out, delta_counts, failures, flips = [], {}, [], []
    for old in sorted(carried, key=lambda r: r["test_id"]):
        rec = dict(old)
        rec["artifact_version"] = "0.3.0"
        rec["prior_binding_sha256"] = PRIOR_SHA
        rec["prior_binding_ref"] = anchors["prior_schema_ref"]
        rec["prior_binding_at_authoring"] = old.get("binding_at_authoring")
        rec["binding_sha256"] = NEW_SHA
        rec["binding_ref"] = anchors["schema_ref"]
        rec["binding_frozen_revision"] = anchors["frozen_revision"]
        rec["binding_at_authoring"] = anchors["schema_ref"]
        rec["schema_under_test"] = "artifacts/formulation/schemas/af_wcc_vacuum.yaml"
        old_pass = {p["path"]: p["pass"] for p in old.get("probe_results", [])}
        probes = [rb.probe(schema, s) for s in rb.carried_probes(rec["test_id"])]
        rec["probe_results"] = probes
        for p in probes:
            if not p["pass"]:
                failures.append((rec["test_id"], p["path"], p["expected"]))
            if p["path"] in old_pass and old_pass[p["path"]] != p["pass"]:
                flips.append({"test_id": rec["test_id"], "path": p["path"], "old_pass": old_pass[p["path"]], "new_pass": p["pass"]})
        dec = rec["deciding_field"]
        old_val, new_val = getpath(prior, dec), getpath(schema, dec)
        changed = flat(old_val) != flat(new_val)
        if old_val is None and new_val is not None:
            status = "field_added"
        elif old_val is not None and new_val is None:
            status = "field_removed"
        elif changed:
            status = "field_content_changed"
        else:
            status = "unchanged"
        rec["delta_vs_f962c117"] = {
            "status": status,
            "changed_fields": [dec] if changed else [],
            "prior_excerpt": flat(old_val)[:200] if old_val is not None else None,
            "new_excerpt": flat(new_val)[:200] if new_val is not None else None,
        }
        rec["evidence_refs"] = base_evidence + [anchors["prior_suite_ref"]]
        out.append(rec)
        delta_counts[status] = delta_counts.get(status, 0) + 1

    for rec in rb.new_tests(anchors):
        rec = dict(rec)
        rec["artifact_version"] = "0.3.0"
        rec["prior_binding_sha256"] = PRIOR_SHA
        rec["prior_binding_ref"] = anchors["prior_schema_ref"]
        rec["binding_sha256"] = NEW_SHA
        rec["binding_ref"] = anchors["schema_ref"]
        rec["binding_frozen_revision"] = anchors["frozen_revision"]
        old_pass = {p["path"]: p["pass"] for p in rec.get("probe_results", [])}
        for p in rec["probe_results"]:
            if not p["pass"]:
                failures.append((rec["test_id"], p["path"], p["expected"]))
        dec = rec["deciding_field"]
        old_val, new_val = getpath(prior, dec), getpath(schema, dec)
        changed = flat(old_val) != flat(new_val)
        rec["delta_vs_f962c117"] = {
            "status": "field_content_changed" if changed else "unchanged",
            "changed_fields": [dec] if changed else [],
            "prior_excerpt": flat(old_val)[:200] if old_val is not None else None,
            "new_excerpt": flat(new_val)[:200] if new_val is not None else None,
        }
        rec["evidence_refs"] = base_evidence + ["ledger/theorems.jsonl"]
        out.append(rec)
        delta_counts[rec["delta_vs_f962c117"]["status"]] = delta_counts.get(rec["delta_vs_f962c117"]["status"], 0) + 1

    for rec in new_delta_tests(anchors, rb.probe):
        for p in rec["probe_results"]:
            if not p["pass"]:
                failures.append((rec["test_id"], p["path"], p["expected"]))
        dec = rec["deciding_field"]
        old_val, new_val = getpath(prior, dec), getpath(schema, dec)
        changed = flat(old_val) != flat(new_val)
        if old_val is None and new_val is not None:
            status = "field_added"
        elif changed:
            status = "field_content_changed"
        else:
            status = "unchanged"
        rec["delta_vs_f962c117"] = {
            "status": status,
            "changed_fields": [dec] if changed else [],
            "prior_excerpt": flat(old_val)[:200] if old_val is not None else None,
            "new_excerpt": flat(new_val)[:200] if new_val is not None else None,
            "notes": "rev9 delta surface: new block / new anti-scope entry.",
        }
        rec["evidence_refs"] = base_evidence
        out.append(rec)
        delta_counts[status] = delta_counts.get(status, 0) + 1

    out.sort(key=lambda r: r["test_id"])
    SUITE_PATH.write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in out))
    SUITE_VERSION_PATH.write_text(SUITE_PATH.read_text())
    suite_sha = sha256_file(SUITE_PATH)

    prior_keys, new_keys = set(prior), set(schema)
    canon_sha = sha256_file(CANONICAL_SCHEMA_PATH) if CANONICAL_SCHEMA_PATH.exists() else None
    report = {
        "report_id": "w04-f1-rebind-b65fcc0f",
        "created_at": now(),
        "actor": "deepseek-flash-04",
        "role": "bounded worker; no map mutation, no gate verdict, no status promotion",
        "assignment_ref": "comms/inbox/deepseek-flash-04.jsonl:1 (asg-2026-09-11-F1-deepseek-flash-04-13)",
        "class_id": CLASS_ID,
        "node_id": NODE_ID,
        "gate": GATE,
        "action": "re-run the F1 ambiguity suite against the current frozen hash and report deltas only",
        "binding": {
            "path": "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
            "sha256": NEW_SHA,
            "frozen_manifest_revision": frozen.get("revision"),
            "schema_internal_revision": schema.get("revision"),
            "snapshot": "artifacts/flash-04/f1_ambiguity/schema_snapshots/af_wcc_vacuum.b65fcc0f.yaml",
        },
        "prior_binding": {
            "path": "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
            "sha256": PRIOR_SHA,
            "frozen_manifest_revision": 19,
            "schema_internal_revision": prior.get("revision"),
            "snapshot": "artifacts/flash-04/f1_ambiguity/schema_snapshots/af_wcc_vacuum.f962c117.yaml",
        },
        "canonical_path_state": {
            "path": "schemas/af_wcc_vacuum.yaml",
            "sha256": canon_sha,
            "schema_internal_revision": (yaml.safe_load(CANONICAL_SCHEMA_PATH.read_text()).get("revision") if CANONICAL_SCHEMA_PATH.exists() else None),
            "matches_frozen_pin": canon_sha == NEW_SHA,
            "note": (
                "canonical-path policy (ASTRA_HANDOFF 2026-09-12): canonical is authoritative and the authoring tree "
                "must be published byte-identically. RESOLVED: the published copy matches the rev20 pin."
                if canon_sha == NEW_SHA else
                "canonical-path policy (ASTRA_HANDOFF 2026-09-12): canonical is authoritative and the authoring tree "
                "must be published byte-identically. STALE: the published copy does not match the rev20 pin."
            ),
        },
        "tests_total": len(out),
        "carried": len(carried),
        "new": len(out) - len(carried),
        "delta_counts": delta_counts,
        "added_top_level_blocks": sorted(new_keys - prior_keys),
        "removed_top_level_blocks": sorted(prior_keys - new_keys),
        "field_changes_observed": [
            {
                "field": "class_identity_variants",
                "tests": ["F1-AMB-23"],
                "note": "new rev9 block: set-based visibility reading registered as variant SET, is_this_class=false, not written.",
            },
            {
                "field": "anti_scope.not_this_class",
                "tests": ["F1-AMB-24"],
                "note": "rev9 adds AF-WCC-SCALAR-SPH and the H2_loc variant entry to the anti-scope.",
            },
        ],
        "probe_failures": [{"test_id": t, "path": p, "expected": e} for t, p, e in failures],
        "probe_flips_vs_f962c117": flips,
        "open_obligations_retained": [
            {"test": "F1-AMB-01", "field": "non_vacuity.condition", "status": "accepted open obligation"},
            {"test": "F1-AMB-02", "field": "genericity.excluded_set_status", "status": "unresolved"},
            {"test": "F1-AMB-03", "field": "genericity.excluded_set_status", "status": "unresolved"},
            {"test": "F1-AMB-15", "field": "conclusion.equivalent_standard_formulation.status", "status": "UNVERIFIED"},
        ],
        "suite_path": "schemas/f1_falsifier_tests.jsonl",
        "suite_sha256": suite_sha,
        "suite_version_copy": "artifacts/flash-04/f1_ambiguity/versions/f1_falsifier_tests.b65fcc0f.prefreeze.jsonl",
        "suite_records_with_ids_evidence_hash_falsifier": all(
            r.get("test_id") and r.get("evidence_refs") and r.get("binding_sha256") and r.get("falsifier") for r in out
        ),
        "evidence_refs": [
            anchors["schema_ref"], anchors["frozen_ref"], anchors["adjudication_ref"],
            anchors["rule_spec_ref"], anchors["aliases_ref"], anchors["taxonomy_ref"],
            anchors["prior_suite_ref"], anchors["prior_snapshot_ref"],
        ],
        "falsifier": (
            "A carried probe failing to resolve in b65fcc0f, a deciding-field verdict flipping without a FROZEN "
            "revision entry, or a class_identity_variants/anti_scope binding that leaks variant SET or scalar-matter "
            "content into AF-WCC-VAC-GEN."
        ),
        "verification_command": "python3 artifacts/flash-04/f1_ambiguity/rebind_b65fcc0f.py",
    }
    REPORT_PATH.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps({
        "schema_sha256_ok": True,
        "frozen_revision": frozen.get("revision"),
        "tests_total": report["tests_total"],
        "delta_counts": delta_counts,
        "added_top_level_blocks": report["added_top_level_blocks"],
        "probe_failures": report["probe_failures"],
        "probe_flips": flips,
        "canonical_path_matches_pin": report["canonical_path_state"]["matches_frozen_pin"],
        "suite_sha256": suite_sha,
        "report": str(REPORT_PATH.relative_to(ROOT)),
    }, indent=1))
    return 2 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
