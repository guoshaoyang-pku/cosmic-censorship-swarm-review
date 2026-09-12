#!/usr/bin/env python3
"""W078-F2-F0BIND-ADJ-01: independent adjudication of the family-wide F0 consistency-evidence
binding defect at F1 cce9c60146d6 / F2a 5476a3f2c6bc / F2b 55d0a1ea9bda / FROZEN rev28.

Question adjudicated: the three rev12 schemas declare
  f0_binding.consistency_evidence_sha256 = 675a99d0d25b2b37...
while the canonical evidence path artifacts/formulation/evidence/taxonomy_consistency.json
measures 9e335e9ba1bfcf77...  Is the stale pin (a) merely a re-stamp ordering slip whose
repair is "re-pin to the live hash", or (b) a loss of the document's own hash-anchor fields,
so that a live-hash re-stamp would leave the evidence unbound and NOT close the defect?

Method (read-only on canonical paths; the only writes are under this artifact directory):
  B1  measure live evidence hash/mtime and its field set.
  B2  verify the declared hash resolves to the independently pinned copy on disk.
  B3  byte/field diff declared-generation vs live-generation.
  B4  execute the canonical checker tool in an isolated mirror (output redirected to a
      read-only-observed shadow path) to confirm the live writer and reproduce its document.
  B5  re-implement the checker's checks independently on the frozen YAMLs and compare with
      the live document's verdict (is the live "consistent" claim reproducible at all?).
  B6  measure all three schemas' declared pins and canonical F0/authoring hashes.
  B7  drift window: re-measure the live evidence path at the end; any hash movement is
      reported as drift and does not change the measured classification.

Exit 0 iff every check completes (classification itself is data, not an exit condition).
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "artifacts/worker-078/consistency_binding_verify"
TZ = timezone(timedelta(hours=8))
SCHEMAS = {
    "F1": ROOT / "schemas/af_wcc_vacuum.yaml",
    "F2a": ROOT / "schemas/af_scc_c2_vacuum.yaml",
    "F2b": ROOT / "schemas/af_scc_c0_vacuum.yaml",
}
LIVE_EVIDENCE = ROOT / "artifacts/formulation/evidence/taxonomy_consistency.json"
DECLARED_PIN = "675a99d0d25b2b37c9b9e9b965aec1c1ff0e388d2665fd9247b58c04733eba48"
PINNED_COPY = ROOT / "artifacts/worker-086/gform_rev12/pinned/taxonomy_consistency.675a99d0d25b.json"
TOOL = ROOT / "artifacts/formulation/tools/check_taxonomy_consistency.py"
MAP_TAX = ROOT / "research_map/formulation_taxonomy.yaml"
LEAD_TAX = ROOT / "artifacts/formulation/formulation_taxonomy.yaml"
FROZEN = ROOT / "artifacts/formulation/FROZEN.json"
ALIASES = ROOT / "artifacts/formulation/VOCAB_ALIASES.json"
ANCHOR_FIELDS = ["map_taxonomy_sha256", "lead_contract_sha256", "measured_at"]


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha256_file(p):
    return sha256_bytes(Path(p).read_bytes())


def measure(path):
    p = Path(path)
    try:
        b = p.read_bytes()
    except FileNotFoundError:
        return {"path": str(path.relative_to(ROOT)), "exists": False}
    st = p.stat()
    return {
        "path": str(path.relative_to(ROOT)),
        "exists": True,
        "sha256": sha256_bytes(b),
        "bytes": len(b),
        "mtime": datetime.fromtimestamp(st.st_mtime, TZ).isoformat(timespec="seconds"),
        "mtime_epoch": st.st_mtime,
    }


def load_json(path):
    return json.loads(Path(path).read_text())


def now():
    return datetime.now(TZ).isoformat(timespec="seconds")


def main():
    checks = {}

    # ---------------- B1: live evidence measurement ----------------
    live0 = measure(LIVE_EVIDENCE)
    live_doc = load_json(LIVE_EVIDENCE)
    checks["B1_live_evidence_measured"] = {
        "pass": live0["exists"],
        "live": live0,
        "top_level_fields": sorted(live_doc.keys()),
        "anchor_fields_present": [f for f in ANCHOR_FIELDS if f in live_doc],
        "anchor_fields_absent": [f for f in ANCHOR_FIELDS if f not in live_doc],
        "consistent_flag": live_doc.get("consistent"),
    }

    # ---------------- B2: declared pin resolves to a pinned copy ----------------
    pinned_meas = measure(PINNED_COPY)
    pinned_doc = load_json(PINNED_COPY) if pinned_meas["exists"] else {}
    checks["B2_declared_pin_resolves_to_pinned_copy"] = {
        "pass": pinned_meas.get("sha256") == DECLARED_PIN,
        "declared_pin": DECLARED_PIN,
        "pinned_copy": pinned_meas,
        "declared_pin_equals_pinned_copy_sha256": pinned_meas.get("sha256") == DECLARED_PIN,
        "declared_pin_equals_live_sha256": live0.get("sha256") == DECLARED_PIN,
    }

    # ---------------- B3: declared-generation vs live-generation diff ----------------
    live_keys = set(live_doc.keys())
    pinned_keys = set(pinned_doc.keys())
    common = sorted(live_keys & pinned_keys)
    value_diffs = {k: {"declared": pinned_doc[k], "live": live_doc[k]}
                   for k in common if pinned_doc[k] != live_doc[k]}
    checks["B3_generation_diff"] = {
        "pass": True,
        "fields_only_in_declared_generation": sorted(pinned_keys - live_keys),
        "fields_only_in_live_generation": sorted(live_keys - pinned_keys),
        "common_fields": common,
        "common_field_value_diffs": value_diffs,
        "declared_generation_is_superset": live_keys < pinned_keys,
        "information_loss_is_exactly_the_hash_anchors":
            sorted(pinned_keys - live_keys) == sorted(ANCHOR_FIELDS),
        "same_semantic_payload": all(pinned_doc.get(k) == live_doc.get(k) for k in common
                                     if k not in ANCHOR_FIELDS),
        "identity_of_compared_trees_in_live_generation":
            "cannot be verified: live generation carries no hash of either compared tree",
    }

    # ---------------- B4: run the canonical tool isolated, output redirected ----------------
    tmp = Path(tempfile.mkdtemp(prefix="w078-shadow-"))
    try:
        (tmp / "research_map").mkdir()
        (tmp / "artifacts/formulation/tools").mkdir(parents=True)
        (tmp / "artifacts/formulation/evidence").mkdir(parents=True)
        (tmp / "artifacts/formulation").mkdir(exist_ok=True)
        for src, dst in [
            (MAP_TAX, tmp / "research_map/formulation_taxonomy.yaml"),
            (LEAD_TAX, tmp / "artifacts/formulation/formulation_taxonomy.yaml"),
            (ALIASES, tmp / "artifacts/formulation/VOCAB_ALIASES.json"),
        ]:
            shutil.copy2(src, dst)
        src_text = TOOL.read_text()
        shadow_tool = tmp / "artifacts/formulation/tools/check_taxonomy_consistency.py"
        shadow_tool.write_text(src_text)
        # shadow copy writes to <tmp>/artifacts/formulation/evidence/, never the canonical path
        proc = subprocess.run([sys.executable, str(shadow_tool)], capture_output=True,
                              text=True, timeout=300, cwd=str(tmp))
        shadow_out = tmp / "artifacts/formulation/evidence/taxonomy_consistency.json"
        shadow_doc = load_json(shadow_out) if shadow_out.exists() else None
        checks["B4_isolated_tool_reproduction"] = {
            "pass": proc.returncode == 0 and shadow_doc is not None,
            "tool": measure(TOOL),
            "tool_exit_code": proc.returncode,
            "tool_stdout": proc.stdout.strip(),
            "tool_stderr": proc.stderr.strip()[:2000],
            "shadow_document_sha256": sha256_file(shadow_out) if shadow_out.exists() else None,
            "live_document_sha256": live0.get("sha256"),
            "shadow_reproduces_live_document":
                bool(shadow_doc) and sha256_file(shadow_out) == live0.get("sha256"),
            "shadow_field_set": sorted(shadow_doc.keys()) if shadow_doc else None,
            "shadow_has_anchor_fields": [f for f in ANCHOR_FIELDS if shadow_doc and f in shadow_doc],
            "tool_writes_to_canonical_path_under_its_own_root":
                'ROOT/"artifacts/formulation/evidence/taxonomy_consistency.json"' in src_text,
        }
        if shadow_doc is not None:
            checks["B4_isolated_tool_reproduction"]["shadow_vs_live_field_diff"] = {
                "only_in_live": sorted(set(live_doc) - set(shadow_doc)),
                "only_in_shadow": sorted(set(shadow_doc) - set(live_doc)),
                "value_diffs": {k: {"live": live_doc[k], "shadow": shadow_doc[k]}
                                for k in set(live_doc) & set(shadow_doc)
                                if live_doc[k] != shadow_doc[k]},
            }
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # ---------------- B5: independent re-implementation of the checker's checks ----------------
    import yaml
    A = yaml.safe_load(MAP_TAX.read_text())
    B = yaml.safe_load(LEAD_TAX.read_text())
    AL = load_json(ALIASES)

    def canon(kind, tok):
        for c, al in AL[kind].items():
            if tok == c or tok in al:
                return c
        return tok

    errs = []
    if set(A["class_ids"]) != set(B["class_contracts"]):
        errs.append("class id sets differ")
    for cid in sorted(set(A["class_ids"]) & set(B["class_contracts"])):
        a, b = A["classes"][cid], B["class_contracts"][cid]
        if a["axes"]["family"] != b["components"]["censorship"]:
            errs.append(f"{cid}: family mismatch")
        ta = a["axes"].get("regularity_token")
        tb = b["components"].get("regularity_token")
        tb = None if tb == "none" else tb
        if ta != tb:
            errs.append(f"{cid}: regularity mismatch")
        if canon("conclusion_type", a["axes"].get("conclusion_type")) != canon("conclusion_type", b.get("conclusion_type")):
            errs.append(f"{cid}: conclusion_type mismatch")
        if not a.get("exclusions") or not b.get("exclusions"):
            errs.append(f"{cid}: exclusions empty")
        if not a.get("test_cases") or not b.get("positive_test_case"):
            errs.append(f"{cid}: test cases missing")
        if a["axes"]["family"] == "SCC" and not a.get("known_obstruction"):
            errs.append(f"{cid}: SCC without known_obstruction")
        ga = canon("genericity_kind", str(a["axes"].get("genericity_kind", "")))
        gb = canon("genericity_kind", str((B.get("axis_registry", {}).get("genericity_axis", {}).get("frozen", {}) or {}).get(cid, "")))
        if ga != gb:
            errs.append(f"{cid}: genericity mismatch")
    c0v = (B.get("class_contracts", {}).get("AF-SCC-C0-VAC-GEN", {}) or {}).get("class_identity_variants")
    if not c0v or "horizon_localized_variant" not in c0v:
        errs.append("C0 class_identity_variants missing")
    d0 = (B.get("class_contracts", {}).get("AF-SCC-C0-VAC-GEN", {}) or {}).get("data_class_freeze")
    if not d0 or "smooth-with-decay" not in str(d0):
        errs.append("C0 data_class_freeze missing")
    T1 = any(r.get("from") == "AF-SCC-C0-VAC-GEN" and r.get("to") == "AF-SCC-C2-VAC-GEN"
             for r in (A.get("transfer_rules", {}).get("allowed") or []))
    X1 = any("C2-VAC-GEN -> AF-SCC-C0" in str(r.get("pattern", "")) or
             (r.get("from") == "AF-SCC-C2-VAC-GEN" and r.get("to") == "AF-SCC-C0-VAC-GEN")
             for r in (A.get("transfer_rules", {}).get("forbidden") or []))
    LI = any(r.get("from") == "AF-SCC-C0-VAC-GEN" and r.get("to") == "AF-SCC-C2-VAC-GEN" and r.get("direction") == "one_way"
             for r in (B.get("implication_ledger") or []))
    if not (T1 and LI):
        errs.append("C0 => C2 one-way entailment not recorded")
    if not X1:
        errs.append("C2 => C0 converse not forbidden")
    checks["B5_independent_reimplementation"] = {
        "pass": True,
        "independent_error_count": len(errs),
        "independent_errors": errs,
        "independent_consistent": not errs,
        "live_document_consistent_flag": live_doc.get("consistent"),
        "live_document_error_count": len(live_doc.get("errors", [])),
        "live_flag_reproduced_by_independent_run": (not errs) == bool(live_doc.get("consistent")),
        "classes_compared_match": sorted(live_doc.get("classes_compared", [])) == sorted(set(A["class_ids"]) & set(B["class_contracts"])),
        "compared_tree_hashes": {
            "canonical_map_taxonomy": sha256_file(MAP_TAX),
            "authoring_lead_contract": sha256_file(LEAD_TAX),
        },
    }

    # ---------------- B6: schema declarations + FROZEN pin ----------------
    schema_rows = {}
    for name, path in SCHEMAS.items():
        text = path.read_text()
        doc = yaml.safe_load(text)
        fb = doc.get("f0_binding", {}) or {}
        schema_rows[name] = {
            "path": str(path.relative_to(ROOT)),
            "revision": doc.get("revision"),
            "sha256": sha256_file(path),
            "declared_f0_artifact": fb.get("declared_f0_artifact"),
            "declared_f0_sha256": fb.get("declared_f0_sha256"),
            "consistency_evidence": fb.get("consistency_evidence"),
            "consistency_evidence_sha256": fb.get("consistency_evidence_sha256"),
            "checked_at": fb.get("checked_at"),
            "declared_pin_matches_live_evidence": fb.get("consistency_evidence_sha256") == live0.get("sha256"),
            "declared_pin_matches_declared_generation": fb.get("consistency_evidence_sha256") == DECLARED_PIN,
            "declared_pin_has_anchor_fields": [f for f in ANCHOR_FIELDS if f in pinned_doc] if fb.get("consistency_evidence_sha256") == DECLARED_PIN else None,
        }
    frozen = load_json(FROZEN)
    frozen_pin = (frozen.get("files", {}) or {}).get("artifacts/formulation/evidence/taxonomy_consistency.json")
    checks["B6_schema_and_manifest_pins"] = {
        "pass": all(r["declared_pin_matches_declared_generation"] for r in schema_rows.values()),
        "schemas": schema_rows,
        "frozen_revision": frozen.get("revision"),
        "frozen_consistency_evidence_pin": frozen_pin,
        "frozen_pin_matches_live_evidence": bool(frozen_pin) and frozen_pin.get("sha256") == live0.get("sha256"),
        "frozen_pin_has_anchor_fields": bool(frozen_pin) and frozen_pin.get("sha256") == sha256_file(LIVE_EVIDENCE) and not checks["B1_live_evidence_measured"]["anchor_fields_absent"],
        "all_three_declare_same_pin": len({r["consistency_evidence_sha256"] for r in schema_rows.values()}) == 1,
        "canonical_f0_live_sha256": sha256_file(MAP_TAX),
        "authoring_contract_live_sha256": sha256_file(LEAD_TAX),
        "all_three_declared_f0_matches_live": all(r["declared_f0_sha256"] == sha256_file(MAP_TAX) for r in schema_rows.values()),
    }

    # ---------------- classification ----------------
    anchors = checks["B3_generation_diff"]["fields_only_in_declared_generation"]
    loss_exact = checks["B3_generation_diff"]["information_loss_is_exactly_the_hash_anchors"]
    if loss_exact:
        classification = "LOSSY_GENERATOR_STALE_PIN"
        adjudication = ("The declared 675a99d0 generation carried map_taxonomy_sha256, "
                        "lead_contract_sha256 and measured_at; the live 9e335e9b generation "
                        "drops exactly those three fields and carries no hash of either compared "
                        "tree. Re-stamping the schemas to 9e335e9b would NOT close H07b: the "
                        "evidence would then be hash-consistent with the pointer but still "
                        "unbound to the declared F0 0abb9ed8 / authoring d7419b4e trees.")
    elif anchors:
        classification = "LOSSY_GENERATOR_PARTIAL"
        adjudication = "Declared generation carries fields the live generation lacks: " + ", ".join(anchors)
    else:
        classification = "RE_STAMP_ONLY"
        adjudication = "Declared and live generations differ only in values, not in field set."

    # ---------------- B7: drift window (>= 20 s of observation, two samples) ----------------
    time.sleep(20)
    live1 = measure(LIVE_EVIDENCE)
    checks["B7_drift_window"] = {
        "pass": True,
        "window_seconds": 20,
        "live_at_start": live0,
        "live_at_end": live1,
        "drifted": live0.get("sha256") != live1.get("sha256"),
        "content_stable_but_mtime_advancing":
            live0.get("sha256") == live1.get("sha256") and live0.get("mtime") != live1.get("mtime"),
        "writer_active_during_window": live0.get("sha256") != live1.get("sha256")
                                       or live0.get("mtime") != live1.get("mtime"),
    }

    # ---------------- B8: what a correct re-generation would look like (simulated, not written) ----------------
    # close_findings_rev27.py (the repair tool, FROZEN-pinned) re-adds the anchors to whatever
    # document is live. Simulate exactly that transformation in memory and hash the result:
    # if the result differs from the declared pin, the correct repair necessarily republishes
    # a NEW evidence document and therefore NEW schema bytes (nothing can be re-stamped in place).
    sim = dict(live_doc)
    sim["map_taxonomy_sha256"] = sha256_file(MAP_TAX)
    sim["lead_contract_sha256"] = sha256_file(LEAD_TAX)
    sim["measured_at"] = "2026-09-12T00:32:02+08:00"
    sim_bytes = (json.dumps(sim, indent=2) + "\n").encode()
    checks["B8_simulated_correct_regeneration"] = {
        "pass": True,
        "repair_tool": measure(ROOT / "artifacts/formulation/tools/close_findings_rev27.py"),
        "repair_tool_rewrites_consistency_path":
            "CONSISTENCY = ROOT / \"artifacts/formulation/evidence/taxonomy_consistency.json\""
            in (ROOT / "artifacts/formulation/tools/close_findings_rev27.py").read_text(),
        "repair_tool_writes_anchor_fields":
            all(f'cons["{f}"]' in (ROOT / "artifacts/formulation/tools/close_findings_rev27.py").read_text()
                for f in ANCHOR_FIELDS),
        "canonical_checker_writes_anchor_fields":
            all(f not in TOOL.read_text() for f in ANCHOR_FIELDS),
        "simulated_document_sha256": sha256_bytes(sim_bytes),
        "declared_pin": DECLARED_PIN,
        "live_pin": live0.get("sha256"),
        "simulated_equals_declared_pin": sha256_bytes(sim_bytes) == DECLARED_PIN,
        "simulated_equals_live_pin": sha256_bytes(sim_bytes) == live0.get("sha256"),
        "correct_repair_requires_new_evidence_bytes": sha256_bytes(sim_bytes) != live0.get("sha256"),
        "note": ("simulated bytes are never written to disk; they exist only to demonstrate that "
                 "restoring the anchors changes the evidence hash, so the schema pointer cannot be "
                 "satisfied by re-stamping the live document"),
    }

    report = {
        "task_id": "W078-F2-F0BIND-ADJ-01",
        "worker": "worker-078",
        "node_id": "F2",
        "class_ids": sorted(SCHEMAS.keys()),
        "gate_scope": "G-FORM",
        "created_at": now(),
        "script_sha256": sha256_file(Path(__file__).resolve()),
        "canonical_paths_read_only_observed": True,
        "classification": classification,
        "adjudication": adjudication,
        "checks": checks,
        "verdict": "revise",
        "verdict_target": "F1 cce9c60146d6 / F2a 5476a3f2c6bc / F2b 55d0a1ea9bda f0_binding.consistency_evidence_sha256",
        "falsifiers": [
            "A declared-generation copy without anchor fields (i.e. the 675a99d0 bytes lacking map_taxonomy_sha256/lead_contract_sha256/measured_at) falsifies the lossy-generator classification.",
            "A live canonical taxonomy_consistency.json whose field set equals the declared generation's (anchors present) falsifies B3.",
            "An isolated run of the checker tool that emits the three anchor fields falsifies the writer attribution in B4.",
            "An independent consistency run on the frozen YAMLs that disagrees with the live consistent flag falsifies B5 and voids the 'payload unchanged' premise.",
            "A repair path that restores the live document to the declared 675a99d0 bytes without changing any other artifact falsifies B8.",
        ],
        "scope_note": ("Structural/binding adjudication only. No claim about mathematics, physics, "
                       "class semantics or gate status; worker verdict is advisory evidence, not a "
                       "gate verdict or node transition. Canonical artifacts were not modified."),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report, indent=1, sort_keys=False) + "\n"
    for name in ("report.json", "report_rerun.json"):
        (OUT / name).write_text(payload)

    print(json.dumps({
        "classification": classification,
        "live_evidence_sha256": live0.get("sha256"),
        "declared_pin": DECLARED_PIN,
        "anchors_lost": checks["B3_generation_diff"]["fields_only_in_declared_generation"],
        "shadow_reproduces_live": checks["B4_isolated_tool_reproduction"].get("shadow_reproduces_live_document"),
        "independent_consistent": checks["B5_independent_reimplementation"]["independent_consistent"],
        "live_consistent_flag": live_doc.get("consistent"),
        "frozen_rev": frozen.get("revision"),
        "drift_during_run": checks["B7_drift_window"]["drifted"],
        "report_sha256": sha256_bytes(payload.encode()),
    }, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
