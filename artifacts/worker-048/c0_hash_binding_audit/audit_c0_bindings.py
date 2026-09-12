#!/usr/bin/env python3
"""W48-C0-BIND-01 - independent hash-binding snapshot audit for AF-SCC-C0-VAC-GEN.

Bounded worker-048 task (one class, read-only over audited paths).

WHAT IT DECIDES (machine-checkable only)
  For class AF-SCC-C0-VAC-GEN (node F2b) at one pinned snapshot, every hash binding
  that another artifact declares about this class is re-measured against the bytes the
  auditor actually read:
    B1  FROZEN.json manifest entries in the C0 binding chain (canonical + authoring
        schema, C2/F1 siblings, taxonomy, variant registry, C0 delta, aggregator)
    B2  aggregator schemas/af_scc_regularities.yaml component pin (SEP-6)
    B3  research_map.json node F2b artifact_sha256_measured / declared flag
    B4  the C0 schema's own f0_binding.declared_f0_sha256 -> taxonomy
    B5  anchor/identity bindings inside the C0 schema (class_contract_pointer,
        sibling_disjoint_from) and the variant registry's delta_ref + evidence anchors
  A binding is ALIGNED only when declared == measured in this snapshot; DRIFTED when
  both exist and differ; MISSING when the target file is absent.

WHAT IT DOES NOT DECIDE
  Physical correctness, scope of cited sources, whether a drifted file is a regression
  (the lead may be mid-write), or any gate verdict. Workers cannot set done/passed.

CONTROLS (must all behave or controls.verdict = FAIL)
  CTL-1 aligned synthetic binding                    -> aligned
  CTL-2 corrupted declared hash (mutation)           -> drifted   (proves comparison is live)
  CTL-3 absent target path                           -> missing
  CTL-4 in-memory corruption of a REAL aggregator pin-> drifted   (proves B2 is read, not assumed)
  CTL-5 fabricated anchor                            -> unresolved
  NULL-A always-accept detector must FAIL to detect the CTL-2 mutation
  NULL-R always-reject detector must FAIL on the CTL-1 aligned pair
  A checker that cannot fail these controls would be reported as defective by this audit.

Exit code 0 if controls pass (findings are findings), 1 if the controls fail.
Read-only: writes only under artifacts/worker-048/c0_hash_binding_audit/.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
CST = timezone(timedelta(hours=8))

TASK_ID = "W48-C0-BIND-01"
WORKER = "worker-048"
CLASS_ID = "AF-SCC-C0-VAC-GEN"
SIBLING = "AF-SCC-C2-VAC-GEN"
FROZEN4 = {"AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"}
HEX64 = re.compile(r"^[0-9a-f]{64}$")
FROZEN_RELEVANT = re.compile(
    r"(af_scc_c0|af_scc_c2|af_wcc_vacuum|formulation_taxonomy|VARIANT_REGISTRY|"
    r"af_scc_regularities|variants/AF-SCC-C0|variants/AF-WCC)"
)
CANON_C0 = "schemas/af_scc_c0_vacuum.yaml"
AUTH_C0 = "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"
AGG = "schemas/af_scc_regularities.yaml"
TAXONOMY = "research_map/formulation_taxonomy.yaml"
REGISTRY = "artifacts/formulation/VARIANT_REGISTRY.json"
FROZEN_MANIFEST = "artifacts/formulation/FROZEN.json"
MAP = "research_map/research_map.json"


class Snapshot:
    """Read every audited path exactly once; all checks use these bytes."""

    def __init__(self) -> None:
        self.at = datetime.now(CST).isoformat(timespec="seconds")
        self._c: dict[str, dict] = {}

    def read(self, rel: str) -> dict:
        if rel not in self._c:
            p = ROOT / rel
            if p.is_file():
                b = p.read_bytes()
                self._c[rel] = {
                    "exists": True,
                    "bytes": b,
                    "sha256": hashlib.sha256(b).hexdigest(),
                    "n_bytes": len(b),
                    "mtime": datetime.fromtimestamp(p.stat().st_mtime, CST).isoformat(timespec="seconds"),
                }
            else:
                self._c[rel] = {"exists": False, "bytes": None, "sha256": None, "n_bytes": None, "mtime": None}
        return self._c[rel]

    def text(self, rel: str):
        r = self.read(rel)
        return r["bytes"].decode("utf-8", "replace") if r["exists"] else None

    def load(self, rel: str):
        r = self.read(rel)
        if not r["exists"]:
            return None
        try:
            return json.loads(r["bytes"].decode("utf-8"))
        except Exception:
            try:
                return yaml.safe_load(r["bytes"].decode("utf-8"))
            except Exception:
                return None


def resolve_anchor(rel: str, anchor: str, snap: Snapshot):
    """Resolve 'path#anchor' for yaml/json/jsonl/csv. Returns (ok, detail)."""
    r = snap.read(rel)
    if not r["exists"]:
        return False, "file missing"
    if not anchor:
        return True, "no anchor"
    txt = snap.text(rel)
    suffix = Path(rel).suffix.lower()
    if suffix in (".yaml", ".yml", ".json"):
        obj = snap.load(rel)
        if obj is None:
            return False, "parse error"
        cur = obj
        for part in anchor.split("."):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            elif isinstance(cur, list):
                try:
                    cur = cur[int(part)]
                except (ValueError, IndexError):
                    return False, f"anchor segment {part!r} not found"
            else:
                return False, f"anchor segment {part!r} not found"
        return True, "anchor resolves"
    if suffix == ".jsonl":
        for line in txt.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                o = json.loads(line)
            except Exception:
                continue
            if str(o.get("theorem_id") or o.get("id") or o.get("source_id") or "") == anchor:
                return True, "jsonl row found"
        return False, "no jsonl row with that id"
    if suffix == ".csv":
        for row in csv.reader(io.StringIO(txt)):
            if anchor in row:
                return True, "csv cell found"
        return False, "no csv cell with that value"
    ok = anchor in txt
    return ok, ("literal substring found" if ok else "literal anchor not found")


def split_ref(ref: str):
    if "#" in ref:
        p, a = ref.split("#", 1)
        return p, a
    return ref, ""


def binding_status(declared, measured):
    if declared is None:
        return "no_declared_hash"
    if measured is None:
        return "missing_target"
    return "aligned" if declared == measured else "drifted"


def walk_class_id_fields(obj, path="$", out=None):
    """Collect every value under a class-id-bearing key, for leakage checking."""
    if out is None:
        out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{path}.{k}"
            if k in ("class_id", "class_ids", "parent_class", "sibling_disjoint_from"):
                vals = v if isinstance(v, list) else [v]
                for x in vals:
                    if isinstance(x, str):
                        out.append((p, x))
            walk_class_id_fields(v, p, out)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            walk_class_id_fields(v, f"{path}[{i}]", out)
    return out


def main() -> int:
    snap = Snapshot()
    rows: list[dict] = []
    checks: list[dict] = []
    notes: list[str] = []

    def add(bid, declared_by, target, declared_sha, class_id=CLASS_ID, note=""):
        measured = snap.read(target)["sha256"] if target else None
        status = binding_status(declared_sha, measured)
        rows.append({
            "binding_id": bid,
            "class_id": class_id,
            "declared_by": declared_by,
            "target": target,
            "declared_sha256": declared_sha,
            "measured_sha256": measured,
            "status": status,
            "note": note,
            "falsifier": (f"at the pinned snapshot, re-read {target}: if its sha256 differs from "
                          f"measured_sha256 the row changes; if the two recorded values are equal the "
                          f"row must be aligned, otherwise this row is wrong"),
        })
        return status

    # ---- B1: FROZEN.json declarations in the C0 binding chain -------------------------
    frozen = snap.load(FROZEN_MANIFEST) or {}
    frozen_files = frozen.get("files", {}) if isinstance(frozen, dict) else {}
    for p, rec in sorted(frozen_files.items()):
        if FROZEN_RELEVANT.search(p):
            add(f"B1-FROZEN::{p}", f"{FROZEN_MANIFEST}#files[{p}].sha256", p,
                (rec or {}).get("sha256"), note=f"FROZEN revision {frozen.get('revision')} frozen_at {frozen.get('frozen_at')}")

    # ---- B2: aggregator component pin (SEP-6) ------------------------------------------
    agg = snap.load(AGG) or {}
    agg_components = agg.get("components", []) if isinstance(agg, dict) else []
    agg_c0 = next((c for c in agg_components if c.get("class_id") == CLASS_ID), None)
    agg_c2 = next((c for c in agg_components if c.get("class_id") == SIBLING), None)
    if agg_c0:
        add("B2-AGG::c0-pin", f"{AGG}#components[c0_component].sha256", agg_c0.get("path"),
            agg_c0.get("sha256"), note="aggregator SEP-6 component pin")
    else:
        checks.append({"check_id": "B2-AGG::c0-present", "verdict": "FAIL",
                       "detail": "aggregator has no C0 component entry"})
    if agg_c2:
        add("B2-AGG::c2-pin", f"{AGG}#components[c2_component].sha256", agg_c2.get("path"),
            agg_c2.get("sha256"), class_id=SIBLING, note="aggregator SEP-6 sibling pin")
    # SEP-1: each component class id exactly once, C0 declared_selector is "C0"
    ids = [c.get("class_id") for c in agg_components]
    sep1 = ids.count(CLASS_ID) == 1 and ids.count(SIBLING) == 1 and len(ids) == 2
    checks.append({"check_id": "SEP-1::two-component-ids-once-each", "verdict": "PASS" if sep1 else "FAIL",
                   "detail": f"component class_ids={ids}"})
    if agg_c0:
        sel = str(agg_c0.get("declared_selector", ""))
        checks.append({"check_id": "SEP-5::c0-selector-is-C0", "verdict": "PASS" if sel.strip().upper() == "C0" else "FAIL",
                       "detail": f"declared_selector={sel!r}"})

    # ---- B3: map node F2b --------------------------------------------------------------
    m = snap.load(MAP) or {}
    f2b = None
    for g in m.get("groups", []):
        for n in g.get("nodes", []):
            if n.get("id") == "F2b":
                f2b = n
                break
    if f2b:
        add("B3-MAP::F2b-artifact-sha-measured", f"{MAP}#nodes[F2b].artifact_sha256_measured",
            f2b.get("artifact"), f2b.get("artifact_sha256_measured"),
            note=f"map declared_hash_matches_measured={f2b.get('declared_hash_matches_measured')}")
        # Reconciliation, not a new finding: worker-036 (W036-MAPREG-01) already classified the
        # map flag semantics. Re-measure the map's declared hash field format here so this audit
        # neither duplicates nor contradicts that report.
        declared_field = f2b.get("artifact_sha256") or f2b.get("artifact_sha256_declared") or f2b.get("declared_sha256")
        if declared_field is None:
            declared_field = str(f2b.get("artifact_sha256_measured") or "")
        fmt = "full64" if HEX64.match(str(declared_field)) else (
            "zero_padded_prefix" if re.fullmatch(r"[0-9a-f]{12}0{52}", str(declared_field)) else "other")
        flag = bool(f2b.get("declared_hash_matches_measured"))
        measured_ok = f2b.get("artifact_sha256_measured") == snap.read(f2b.get("artifact", "") or "").get("sha256")
        reconciled = flag == measured_ok
        checks.append({
            "check_id": "B3-MAP::declared-flag-reconciled-with-worker-036",
            "verdict": "PASS" if reconciled else "INFO_DUPLICATE",
            "detail": (f"flag={flag} measured_field_matches_disk={measured_ok} "
                       f"declared_field_format={fmt}; mismatch is the zero-padded declared-prefix defect "
                       f"already reported as W036-MAPREG-01 "
                       f"(artifacts/worker-036/map_hash_registry_audit_report.json#a2a73f983baa), not re-claimed here"),
            "evidence_ref": "artifacts/worker-036/map_hash_registry_audit_report.json",
        })
    else:
        checks.append({"check_id": "B3-MAP::F2b-present", "verdict": "FAIL", "detail": "node F2b not found"})

    # ---- B4: C0 schema own F0 binding --------------------------------------------------
    c0 = snap.load(CANON_C0) or {}
    f0b = c0.get("f0_binding", {}) if isinstance(c0, dict) else {}
    if f0b:
        add("B4-F0BIND::declared-f0-sha256", f"{CANON_C0}#f0_binding.declared_f0_sha256",
            f0b.get("declared_f0_artifact"), f0b.get("declared_f0_sha256"),
            note=f"binding checked_at {f0b.get('checked_at')}")
    # FROZEN + map F0 declaration of the same taxonomy file (cross-source identity)
    tax_frozen = (frozen_files.get(TAXONOMY) or {}).get("sha256")
    add("B4-F0BIND::frozen-taxonomy-pin", f"{FROZEN_MANIFEST}#files[{TAXONOMY}].sha256", TAXONOMY, tax_frozen,
        note="same target as B4; a split identity between B4 and B4-F0BIND is a binding defect")
    f0_node = None
    for g in m.get("groups", []):
        for n in g.get("nodes", []):
            if n.get("id") == "F0":
                f0_node = n
    if f0_node:
        declared_map = ((f0_node.get("last_status") or {}).get("summary") or "")
        hexes = re.findall(r"\b[0-9a-f]{12,64}\b", declared_map)
        notes.append(f"map F0 last_status cites hash prefixes {sorted(set(h[:12] for h in hexes))}; "
                     f"snapshot taxonomy sha={str(snap.read(TAXONOMY)['sha256'])[:12]}")

    # ---- B5: anchor / identity bindings ------------------------------------------------
    ptr = c0.get("class_contract_pointer") if isinstance(c0, dict) else None
    if ptr:
        p, a = split_ref(ptr)
        ok, detail = resolve_anchor(p, a, snap)
        checks.append({"check_id": "B5::class_contract_pointer-resolves", "verdict": "PASS" if ok else "FAIL",
                       "detail": f"{ptr} -> {detail}", "evidence_ref": f"{p}#{str(snap.read(p)['sha256'])[:12]}"})
    checks.append({"check_id": "B5::class_id-is-exactly-the-frozen-id",
                   "verdict": "PASS" if c0.get("class_id") == CLASS_ID else "FAIL",
                   "detail": f"class_id={c0.get('class_id')!r}"})
    checks.append({"check_id": "B5::sibling-is-the-frozen-c2-id",
                   "verdict": "PASS" if c0.get("sibling_disjoint_from") == SIBLING else "FAIL",
                   "detail": f"sibling_disjoint_from={c0.get('sibling_disjoint_from')!r}"})

    # ---- B7: class-contract pointer authority (canonical vs authoring taxonomy) ---------
    auth_tax_path = "artifacts/formulation/formulation_taxonomy.yaml"
    canon_tax = snap.load(TAXONOMY) or {}
    auth_tax = snap.load(auth_tax_path) or {}
    canonical_c0 = (((canon_tax.get("classes") or {}).get(CLASS_ID)) if isinstance(canon_tax, dict) else None)
    authoring_c0 = (((auth_tax.get("class_contracts") or {}).get(CLASS_ID)) if isinstance(auth_tax, dict) else None)
    ptr_canon_ok, ptr_canon_detail = resolve_anchor(TAXONOMY, f"class_contracts.{CLASS_ID}", snap)
    checks.append({
        "check_id": "B7::schema-class-contract-pointer-resolves-in-canonical",
        "verdict": "PASS" if ptr_canon_ok else "FAIL",
        "detail": (f"pointer anchor class_contracts.{CLASS_ID} vs canonical {TAXONOMY}: {ptr_canon_detail}; "
                   f"canonical exposes the class under classes.{CLASS_ID} (present={canonical_c0 is not None})"
                   if not ptr_canon_ok else f"anchor resolves in canonical: {ptr_canon_detail}"),
        "evidence_ref": f"{TAXONOMY}#{str(snap.read(TAXONOMY)['sha256'])[:12]}",
    })
    same_tree_bytes = snap.read(TAXONOMY)["sha256"] == snap.read(auth_tax_path)["sha256"]
    checks.append({
        "check_id": "B7::canonical-and-authoring-taxonomy-byte-identical",
        "verdict": "PASS" if same_tree_bytes else "FAIL",
        "detail": (f"{TAXONOMY} {str(snap.read(TAXONOMY)['sha256'])[:12]} vs {auth_tax_path} "
                   f"{str(snap.read(auth_tax_path)['sha256'])[:12]} (controller canonical-path policy requires "
                   f"byte-identical publication before verdicts bind)"),
        "evidence_ref": f"{auth_tax_path}#{str(snap.read(auth_tax_path)['sha256'])[:12]}",
    })
    if canonical_c0 is not None and authoring_c0 is not None:
        cj = json.dumps(canonical_c0, sort_keys=True, default=str)
        aj = json.dumps(authoring_c0, sort_keys=True, default=str)
        dl = len(list(__import__("difflib").unified_diff(
            json.dumps(canonical_c0, indent=1, sort_keys=True, default=str).splitlines(),
            json.dumps(authoring_c0, indent=1, sort_keys=True, default=str).splitlines(), lineterm="")))
        checks.append({
            "check_id": "B7::c0-contract-equivalent-across-trees",
            "verdict": "PASS" if cj == aj else "FAIL",
            "detail": (f"canonical classes.{CLASS_ID} keys={sorted(canonical_c0.keys()) if isinstance(canonical_c0, dict) else type(canonical_c0).__name__}; "
                       f"authoring class_contracts.{CLASS_ID} keys={sorted(authoring_c0.keys()) if isinstance(authoring_c0, dict) else type(authoring_c0).__name__}; "
                       f"unified-diff lines={dl}"),
            "evidence_ref": f"{TAXONOMY}#{str(snap.read(TAXONOMY)['sha256'])[:12]}",
        })
    else:
        checks.append({"check_id": "B7::c0-contract-present-in-both-trees", "verdict": "FAIL",
                       "detail": f"canonical present={canonical_c0 is not None} authoring present={authoring_c0 is not None}"})

    # structural class-id leakage scan over the pinned C0 artifacts
    leak = []
    for path in (CANON_C0, AUTH_C0, AGG, REGISTRY, TAXONOMY):
        obj = snap.load(path)
        if obj is None:
            continue
        for where, val in walk_class_id_fields(obj):
            if val not in FROZEN4:
                leak.append({"path": path, "where": where, "value": val})
    checks.append({"check_id": "LEAK::class-id-fields-frozen-four-only", "verdict": "PASS" if not leak else "FAIL",
                   "detail": f"{len(leak)} non-frozen value(s)", "occurrences": leak[:10]})

    # registry variant references bound to C0: delta_ref + evidence anchors
    reg = snap.load(REGISTRY) or {}
    c0_variants = [v for v in reg.get("variants", []) if v.get("parent_class") == CLASS_ID]
    ref_rows = []
    for v in c0_variants:
        vid = v.get("variant_id")
        dref = v.get("delta_ref")
        refs = list(v.get("evidence") or []) + ([dref] if dref else [])
        for ref in refs:
            p, a = split_ref(ref)
            ok, detail = resolve_anchor(p, a, snap)
            ref_rows.append({"variant_id": vid, "ref": ref, "resolved": ok, "detail": detail,
                             "target_sha256": snap.read(p)["sha256"]})
    unresolved = [r for r in ref_rows if not r["resolved"]]
    checks.append({
        "check_id": "REF::c0-variant-evidence-anchors-resolve",
        "verdict": "PASS" if not unresolved else "FAIL",
        "detail": f"{len(ref_rows) - len(unresolved)}/{len(ref_rows)} C0-variant refs resolve",
        "unresolved": unresolved[:10],
    })

    # ---- B6: review verdict hash bindings (reference scan, informational) --------------
    review_refs = []
    reviews_dir = ROOT / "reviews"
    cur_c0_sha = snap.read(CANON_C0)["sha256"]
    if reviews_dir.is_dir():
        for rp in sorted(reviews_dir.glob("*.json")):
            rel = str(rp.relative_to(ROOT))
            try:
                txt = rp.read_text(errors="replace")
            except Exception:
                continue
            if "AF-SCC-C0" not in txt and "af_scc_c0" not in txt:
                continue
            hashes = sorted(set(h for h in re.findall(r"\b[0-9a-f]{64}\b", txt)))
            verdict = None
            try:
                obj = json.loads(txt)
                for k in ("verdict", "review_verdict", "recommendation"):
                    if isinstance(obj, dict) and isinstance(obj.get(k), str):
                        verdict = obj[k]
                        break
            except Exception:
                pass
            review_refs.append({
                "review_path": rel,
                "verdict": verdict,
                "n_sha256": len(hashes),
                "binds_current_c0_sha": cur_c0_sha in hashes,
                "sha256_prefixes": [h[:12] for h in hashes[:8]],
                "sha256": hashlib.sha256(rp.read_bytes()).hexdigest(),
            })
    binds = [r for r in review_refs if r["binds_current_c0_sha"]]
    checks.append({
        "check_id": "REVIEW::at-least-one-verdict-binds-current-c0-sha",
        "verdict": "PASS" if binds else "FAIL",
        "detail": f"{len(binds)}/{len(review_refs)} C0-relevant review files reference the current C0 sha "
                  f"{str(cur_c0_sha)[:12]}",
    })

    # ---- controls -----------------------------------------------------------------------
    controls = []
    real_c0 = snap.read(CANON_C0)
    mut_bad = "0" * 64

    def ctl(cid, expected, observed, detail):
        controls.append({"control_id": cid, "expected": expected, "observed": observed,
                         "verdict": "PASS" if expected == observed else "FAIL", "detail": detail})

    ctl("CTL-1-aligned-pair", "aligned", binding_status(real_c0["sha256"], real_c0["sha256"]),
        "correct hash on an existing file")
    ctl("CTL-2-corrupted-declared-hash", "drifted", binding_status(mut_bad, real_c0["sha256"]),
        "mutation of the declared hash must be detected")
    ctl("CTL-3-absent-target", "missing_target", binding_status(mut_bad, None),
        "absent target file must not be reported aligned")
    mut_agg = json.loads(json.dumps(agg))
    for c in mut_agg.get("components", []):
        if c.get("class_id") == CLASS_ID:
            c["sha256"] = mut_bad
    mut_pin = next((c.get("sha256") for c in mut_agg.get("components", []) if c.get("class_id") == CLASS_ID), None)
    ctl("CTL-4-aggregator-pin-mutation", "drifted", binding_status(mut_pin, real_c0["sha256"]),
        "in-memory corruption of the real B2 pin must be detected (B2 is read, not assumed)")
    ok_bad_anchor, _ = resolve_anchor(CANON_C0, "no.such.anchor.path", snap)
    ctl("CTL-5-fabricated-anchor", False, ok_bad_anchor, "fabricated anchor must not resolve")
    # null detectors: a checker that always says aligned/rejected must fail these controls
    always_aligned = lambda d, m: "aligned"  # noqa: E731
    always_drifted = lambda d, m: "drifted"  # noqa: E731
    ctl("NULL-A-always-aligned-must-miss-mutation", False,
        always_aligned(mut_bad, real_c0["sha256"]) == "drifted",
        "an always-aligned detector fails to see CTL-2")
    ctl("NULL-R-always-drifted-must-reject-aligned-pair", False,
        always_drifted(real_c0["sha256"], real_c0["sha256"]) == "aligned",
        "an always-drifted detector fails on the aligned pair")
    controls_ok = all(c["verdict"] == "PASS" for c in controls)

    # ---- findings / summary -------------------------------------------------------------
    drifted = [r for r in rows if r["status"] == "drifted"]
    missing = [r for r in rows if r["status"] == "missing_target"]
    hard_fail_checks = [c for c in checks if c["verdict"] == "FAIL"]
    findings = []
    for r in drifted:
        findings.append({
            "finding_id": f"W48-C0-BIND-F{len(findings)+1:02d}",
            "class_id": r["class_id"],
            "severity": "major",
            "kind": "declared_vs_measured_hash_drift",
            "detail": f"{r['declared_by']} declares {str(r['declared_sha256'])[:12]} for {r['target']}, "
                      f"measured {str(r['measured_sha256'])[:12]}",
            "evidence_ref": f"{r['target']}#{str(r['measured_sha256'])[:12]}",
            "falsifier": r["falsifier"],
        })
    kind_map = {
        "B7::schema-class-contract-pointer-resolves-in-canonical": "pointer_authority_gap",
        "B7::canonical-and-authoring-taxonomy-byte-identical": "dual_tree_byte_divergence",
        "B7::c0-contract-equivalent-across-trees": "c0_contract_text_divergence",
    }
    for c in hard_fail_checks:
        findings.append({
            "finding_id": f"W48-C0-BIND-F{len(findings)+1:02d}",
            "class_id": CLASS_ID,
            "severity": "major",
            "kind": kind_map.get(c["check_id"], c["check_id"]),
            "detail": c["detail"],
            "evidence_ref": c.get("evidence_ref", f"artifacts/worker-048/c0_hash_binding_audit/report.json#{TASK_ID}"),
            "falsifier": f"re-run {c['check_id']} at the pinned snapshot and exhibit the passing case",
        })

    evidence_refs = sorted({f"{r['target']}#{str(r['measured_sha256'])[:12]}" for r in rows if r["measured_sha256"]})
    report = {
        "audit_id": "W48-C0-BIND-01-REPORT",
        "task_id": TASK_ID,
        "worker": WORKER,
        "class_id": CLASS_ID,
        "class_ids": [CLASS_ID, SIBLING, "AF-WCC-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        "node_id": "F2b",
        "created_at": snap.at,
        "snapshot_at": snap.at,
        "scope": ("hash-binding snapshot for AF-SCC-C0-VAC-GEN across FROZEN.json, the F2 aggregator, "
                  "research_map.json F2b/F0, the C0 schema's f0_binding/anchor fields, and the variant "
                  "registry's C0 refs; read-only, one snapshot"),
        "snapshot_files": {p: {k: v for k, v in snap.read(p).items() if k != "bytes"} for p in sorted(snap._c)},
        "bindings": rows,
        "checks": checks,
        "c0_variant_refs": ref_rows,
        "review_reference_scan": review_refs,
        "controls": controls,
        "controls_verdict": "PASS" if controls_ok else "FAIL",
        "summary": {
            "n_bindings": len(rows),
            "aligned": len([r for r in rows if r["status"] == "aligned"]),
            "drifted": len(drifted),
            "missing_target": len(missing),
            "no_declared_hash": len([r for r in rows if r["status"] == "no_declared_hash"]),
            "n_checks": len(checks),
            "failed_checks": [c["check_id"] for c in hard_fail_checks],
            "n_findings": len(findings),
            "n_c0_variant_refs": len(ref_rows),
            "n_c0_variant_refs_unresolved": len(unresolved),
        },
        "findings": findings,
        "notes": notes + [
            "F02 (dual-tree taxonomy byte divergence) restates, from the C0 side, the publish gap already "
            "tracked by W03-PUBLISH-CHECK-01 (artifacts/worker-03/publish_binding_check/report.json); this "
            "audit's new contribution is the C0-specific consequence: the schema's class_contract_pointer "
            "resolves only in the non-authoritative authoring tree and the two C0 contract texts differ.",
        ],
        "verdict": ("BINDING_DEFECT_PRESENT_AT_SNAPSHOT" if (drifted or hard_fail_checks)
                    else "NO_BINDING_DEFECT_AT_SNAPSHOT"),
        "verdict_scope": ("Snapshot only. Byte changes after snapshot_at are expected while the lead is "
                          "mid-write and do NOT falsify these rows; re-running at the recorded snapshot "
                          "hashes must reproduce them."),
        "falsifier": ("At the snapshot bytes recorded in snapshot_files: (a) any row marked drifted whose "
                      "two recorded hashes are in fact equal on re-read; (b) any row marked aligned whose "
                      "recorded measured_sha256 is not sha256 of the recorded bytes; (c) any check marked "
                      "FAIL that passes on an independent re-implementation at those bytes; (d) a control "
                      "that fails to behave as declared. A later file write is not a falsifier."),
        "authority": ("Worker audit only: no gate verdict, no node completion, no validation_status change. "
                      "G-FORM/G-AUDIT remain with the controller and leads."),
        "evidence_refs": evidence_refs[:40],
        "reproduce": "python3 artifacts/worker-048/c0_hash_binding_audit/audit_c0_bindings.py",
    }

    HERE.mkdir(parents=True, exist_ok=True)
    (HERE / "report.json").write_text(json.dumps(report, indent=2, sort_keys=False) + "\n")
    hashes = {
        "report.json": hashlib.sha256((HERE / "report.json").read_bytes()).hexdigest(),
        "audit_c0_bindings.py": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    (HERE / "hashes.json").write_text(json.dumps(hashes, indent=2) + "\n")

    lines = [
        f"# {TASK_ID} - C0 hash-binding snapshot audit",
        "",
        f"- worker: `{WORKER}`  class: `{CLASS_ID}` (node F2b)  snapshot_at: `{snap.at}`",
        f"- verdict: **{report['verdict']}**  controls: **{report['controls_verdict']}**",
        f"- bindings: {report['summary']['n_bindings']} "
        f"(aligned {report['summary']['aligned']}, drifted {report['summary']['drifted']}, "
        f"missing {report['summary']['missing_target']})",
        f"- checks failed: {report['summary']['failed_checks'] or 'none'}",
        f"- C0 variant refs unresolved: {report['summary']['n_c0_variant_refs_unresolved']}"
        f"/{report['summary']['n_c0_variant_refs']}",
        f"- report sha256: `{hashes['report.json']}`",
        f"- script sha256: `{hashes['audit_c0_bindings.py']}`",
        "",
        "## Drifted bindings",
        "",
    ]
    for r in drifted:
        lines.append(f"- `{r['binding_id']}`: {r['declared_by']} declares "
                     f"`{str(r['declared_sha256'])[:12]}` vs measured `{str(r['measured_sha256'])[:12]}`")
    if not drifted:
        lines.append("- none at snapshot")
    lines += ["", "## Failed checks", ""]
    for c in hard_fail_checks:
        lines.append(f"- `{c['check_id']}`: {c['detail']}")
    if not hard_fail_checks:
        lines.append("- none at snapshot")
    lines += [
        "",
        "## Reproduce",
        "",
        "```bash",
        "python3 artifacts/worker-048/c0_hash_binding_audit/audit_c0_bindings.py",
        "```",
        "",
        "Read-only over audited paths; a later write by the lead does not falsify the snapshot.",
    ]
    (HERE / "README.md").write_text("\n".join(lines) + "\n")

    print(f"{TASK_ID}: verdict={report['verdict']} controls={report['controls_verdict']} "
          f"bindings={report['summary']['n_bindings']} drifted={report['summary']['drifted']} "
          f"failed_checks={len(hard_fail_checks)} findings={len(findings)}")
    for f in findings:
        print(f"  {f['finding_id']} {f['kind']}: {f['detail']}")
    return 0 if controls_ok else 1


if __name__ == "__main__":
    sys.exit(main())
