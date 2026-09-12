#!/usr/bin/env python3
"""W060-F2B-VERDICT-01: independent, hash-pinned structural verification of the
canonical F2b schema `schemas/af_scc_c0_vacuum.yaml` (class AF-SCC-C0-VAC-GEN).

Bounded worker task: WORKER-EVENTS-CANNOT-SET-DONE. This script produces machine
evidence only; it emits no gate verdict and no completion status.

What it checks, all at one pinned sha256:
  A. pin binding + double measurement (moving-target guard)
  B. G-FORM criterion field presence for F2b: exact quantifiers, topology,
     regularity, genericity, I+, visibility, conclusion_type
  C. class identity: class_id / regularity_token / sibling_disjoint_from / anti_scope
  D. class separation: run the canonical detector research_map/class_separation.py
     over the artifact text; classify every composite 'C0/C2' occurrence
  E. HF-B1 disposition: composite-regularity token outside a prohibition context
     (the finding from reviews/F2b-review-18.json at an earlier hash)
  F. HF-B2 disposition: artifact node_id vs the map node label, and the map's
     declared-vs-measured hash bookkeeping for the node
  G. VARIANT_REGISTRY consistency: variant parent classes, and no variant id in a
     class_ids surface
  H. canonical/authoring byte identity (canonical-path policy)
  I. negative controls on the detector itself (injected merge must flag, injected
     prohibition must not, injected wrong-family conclusion must flag)
  J. final re-measure: hash stability during the verification window

Usage:
  python3 verify_f2b.py --pin <sha256> [--canonical schemas/af_scc_c0_vacuum.yaml]
                        [--out <evidence.json>]
Exit codes: 0 all checks PASS; 1 one or more checks FAIL; 2 hash drifted from pin.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]  # artifacts/worker-060/f2b_independent_verdict -> repo root
sys.path.insert(0, str(ROOT / "research_map"))
import class_separation as cs  # noqa: E402

CLASS_ID = "AF-SCC-C0-VAC-GEN"
SIBLING = "AF-SCC-C2-VAC-GEN"
NODE_ID = "F2b"
GATE = "G-FORM"
FROZEN_CLASSES = {
    "AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH",
}


def now() -> str:
    return _dt.datetime.now().astimezone().isoformat(timespec="seconds")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def get(d, path, default=None):
    cur = d
    for k in path.split("."):
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


# --- B: G-FORM criterion field presence -------------------------------------
GATE_FIELDS = {
    "quantifiers": [
        "quantifiers.formal",
        "quantifiers.ordered",
        "quantifiers.domains.D0.definition",
        "quantifiers.domains.D1.definition",
        "quantifiers.domains.D2.definition",
        "quantifiers.domains.D3.definition",
        "quantifiers.negation",
        "quantifiers.quantifier_class",
    ],
    "topology": [
        "topology.spacetime_dimension",
        "topology.slice_topology",
        "topology.end_structure",
        "topology.conformal_boundary",
        "topology.I_plus_topology",
        "topology.extension_topology",
        "topology.forbidden",
    ],
    "regularity": [
        "regularity.data_regularity",
        "regularity.solution_regularity",
        "regularity.i_plus_regularity",
        "regularity.extension_regularity",
        "regularity.extension_regularity_exact",
        "regularity.must_not_conflate",
    ],
    "genericity": [
        "genericity.kind",
        "genericity.ambient_space",
        "genericity.topology_or_measure",
        "genericity.generic_set",
        "genericity.excluded_set",
        "genericity.is_part_of_class",
        "genericity.class_change_warning",
    ],
    "i_plus": [
        "i_plus.role",
        "i_plus.in_conclusion",
        "i_plus.definition",
        "i_plus.forbidden",
    ],
    "visibility": [
        "visibility.role",
        "visibility.reason",
        "visibility.visible_singularity_is_wcc",
        "visibility.forbidden_falsifier",
    ],
    "conclusion_type": ["conclusion.conclusion_type"],
}


def check_gate_fields(doc) -> dict:
    out = {}
    for section, paths in GATE_FIELDS.items():
        present, missing = [], []
        for p in paths:
            (present if get(doc, p) not in (None, "", [], {}) else missing).append(p)
        out[section] = {"present": present, "missing": missing,
                        "ok": not missing}
    out["ok"] = all(v["ok"] for v in out.values() if isinstance(v, dict))
    return out


# --- D/E: composite-token classification ------------------------------------
COMPOSITE = re.compile(
    r"c\s*0\s*(?:or|and|/|,|\+|\s)\s*c\s*2"
    r"|c\s*2\s*(?:or|and|/|,|\+|\s)\s*c\s*0"
    r"|c0c2|c2c0", re.I)

DENIAL = re.compile(
    r"\b(no|not|never|nor|without|must\s+not|may\s+not|do(?:es)?\s+not|is\s+not|"
    r"are\s+not|cannot|prohibit\w*|forbid\w*|excluded?)\b", re.I)
KEYLINE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*:")
NEGATIVE_KEYS = re.compile(
    r"(not_this_class|phrases_that_are_not|forbidden|must_not|anti_scope)", re.I)


def _nearest_key(lines, upto):
    for j in range(upto - 1, max(-1, upto - 40), -1):
        if j < 0:
            break
        m = KEYLINE.match(lines[j])
        if m and not lines[j].lstrip().startswith("-"):
            return m.group(1)
    return None


def classify_composites(text: str) -> list:
    lines = text.splitlines()
    rows = []
    for i, line in enumerate(lines, 1):
        for m in COMPOSITE.finditer(cs.norm(line)):
            nline = cs.norm(line)
            win = nline[max(0, m.start() - 100):m.end() + 100]
            if cs._BENIGN.search(nline[max(0, m.start() - 8):m.end() + 8]):
                kind = "benign_explicit_vs"
            elif cs._MERGE_ASSERT.search(win):
                am = cs._MERGE_ASSERT.search(win)
                if cs._NEG_BEFORE_ASSERT.search(win[:am.start()]):
                    kind = "negated_merge_assertion"
                else:
                    kind = "assertion"
            elif cs._PROHIBIT.search(win):
                kind = "prohibition"
            elif cs._SPLIT.search(win):
                kind = "split_context"
            elif DENIAL.search(win):
                kind = "denial_context"
            elif NEGATIVE_KEYS.search(_nearest_key(lines, i) or ""):
                kind = "mention_in_negative_section"
            else:
                kind = "bare_composite"
            rows.append({"line": i, "match": m.group(0), "kind": kind,
                         "context": win.strip()[:200]})
    return rows


def scan_class_ids_surfaces(doc) -> list:
    """Variant ids must never appear as a class_ids token; only frozen classes may."""
    bad = []

    def walk(o, path=""):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in ("class_id", "class_ids"):
                    toks = []
                    if isinstance(v, str):
                        toks = [t.strip() for t in re.split(r"[;,]", v) if t.strip()]
                    elif isinstance(v, list):
                        toks = [str(t).strip() for t in v]
                    for t in toks:
                        if t not in FROZEN_CLASSES:
                            bad.append({"path": f"{path}.{k}", "token": t})
                walk(v, f"{path}.{k}" if path else str(k))
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, f"{path}[{i}]")
    walk(doc)
    return bad


# --- I: negative controls ----------------------------------------------------
def negative_controls() -> dict:
    merge_assert = "These two readings are one class: C0 or C2 share one schema."
    plain_prohibition = "never write the composite regularity token; the split is mandatory"
    artifact_style_mention = "\"any 'C0 or C2' composite regularity\""
    benign = "the C0-vs-C2 distinction is required"
    known_conservative = "never write 'C0 or C2' as a single class"
    wcc_on_scc_out: list = []
    cs._scan_conclusion("a visible incomplete geodesic from I+",
                        "AF-SCC-C0-VAC-GEN", "control.wcc_on_scc", wcc_on_scc_out)
    scc_on_wcc_out: list = []
    cs._scan_conclusion("inextendible across the Cauchy horizon",
                        "AF-WCC-VAC-GEN", "control.scc_on_wcc", scc_on_wcc_out)
    return {
        "merge_assertion_flags": cs.findings_for_text(merge_assert, "control.merge"),
        "plain_prohibition_not_flagged": cs.findings_for_text(plain_prohibition, "control.prohibition"),
        "artifact_style_quoted_phrase_not_flagged": cs.findings_for_text(
            artifact_style_mention, "control.quoted_mention"),
        "benign_vs_not_flagged": cs.findings_for_text(benign, "control.benign"),
        "scc_conclusion_on_wcc_class_flags": scc_on_wcc_out,
        "wcc_conclusion_on_scc_class_flags": wcc_on_scc_out,
        "known_conservative_behavior": {
            "text": known_conservative,
            "flags": cs.findings_for_text(known_conservative, "control.conservative"),
            "expected": "FLAGGED_BY_DESIGN",
            "docstring_ref": "research_map/class_separation.py:10-14 (merge assertions are "
                             "flagged even when a negation word appears elsewhere in the sentence)",
        },
    }


# --- main --------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pin", required=True)
    ap.add_argument("--canonical", default="schemas/af_scc_c0_vacuum.yaml")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    canonical = ROOT / args.canonical
    authoring = ROOT / "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"
    out_path = Path(args.out) if args.out else (
        ROOT / "artifacts/worker-060/f2b_independent_verdict/evidence.json")
    if not out_path.is_absolute():
        out_path = ROOT / out_path

    t0 = now()
    pin_sha = args.pin.lower()
    body = canonical.read_bytes()
    measured0 = sha256_bytes(body)
    snapshot = None
    if measured0 != pin_sha:
        snapdir = out_path.parent / "snapshots"
        snapdir.mkdir(parents=True, exist_ok=True)
        snapshot = snapdir / f"af_scc_c0_vacuum.{measured0[:12]}.yaml"
        snapshot.write_bytes(body)
        ev = {
            "task_id": "W060-F2B-VERDICT-01",
            "actor": "worker-060", "started_at": t0, "finished_at": now(),
            "canonical_path": args.canonical,
            "pinned_sha256": pin_sha, "measured_sha256": measured0,
            "verdict": "MOVING_TARGET",
            "note": "canonical hash changed before the review snapshot; evidence "
                    "bound to the measured snapshot instead of the pin",
            "snapshot_path": str(snapshot.relative_to(ROOT)),
            "drift": {"at": now(), "pinned": pin_sha, "measured": measured0},
        }
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(ev, indent=1) + "\n")
        print(json.dumps(ev, indent=1))
        return 2

    import yaml  # noqa: E402
    doc = yaml.safe_load(body.decode("utf-8"))
    text = body.decode("utf-8")

    checks = {}
    # B
    checks["gate_fields"] = check_gate_fields(doc)
    # C
    checks["class_identity"] = {
        "class_id": get(doc, "class_id"),
        "regularity_token": get(doc, "class_components.regularity_token"),
        "sibling_disjoint_from": get(doc, "sibling_disjoint_from"),
        "conclusion_type": get(doc, "conclusion.conclusion_type"),
        "anti_scope_not_this_class_ids": [
            x.get("class_id") for x in get(doc, "anti_scope.not_this_class", [])
            if isinstance(x, dict)
        ],
        "ok": (
            get(doc, "class_id") == CLASS_ID
            and get(doc, "class_components.regularity_token") == "C0"
            and get(doc, "sibling_disjoint_from") == SIBLING
            and str(get(doc, "conclusion.conclusion_type", "")).startswith("scc_c0")
            and "c2" not in str(get(doc, "conclusion.conclusion_type", "")).lower()
            and SIBLING in [x.get("class_id") for x in get(doc, "anti_scope.not_this_class", [])
                            if isinstance(x, dict)]
        ),
    }
    # D
    hard_findings = cs.findings_for_text(text, args.canonical)
    checks["detector"] = {
        "n_findings": len(hard_findings),
        "findings": hard_findings,
        "regression": cs.regression(),
    }
    composites = classify_composites(text)
    checks["composite_occurrences"] = {
        "rows": composites,
        "assertion_rows": [r for r in composites if r["kind"] == "assertion"],
        "bare_rows": [r for r in composites if r["kind"] == "bare_composite"],
    }    # E: HF-B1
    bad_rows = [r for r in composites if r["kind"] in ("assertion", "bare_composite")]
    hf_b1_ok = (not hard_findings) and not bad_rows
    checks["HF_B1"] = {
        "finding": "composite 'C0/C2' token asserted as one class outside a prohibition/lint context",
        "verdict": "PASS" if hf_b1_ok else "FAIL",
        "ok": hf_b1_ok,
        "evidence": "detector hard findings=0 and no composite occurrence is an assertion or an "
                    "uncontextualised bare composite; every occurrence is a denial, a quoted "
                    "mention under a negative-section key, a prohibition, a split or benign",
        "offending_rows": bad_rows,
    }
    # F: HF-B2 + map bookkeeping
    m = json.loads((ROOT / "research_map/research_map.json").read_text())
    map_node = None
    for g in m.get("groups", []):
        for n in g.get("nodes", []):
            if n.get("id") == NODE_ID:
                map_node = n
    declared = (map_node or {}).get("artifact_sha256")
    measured_map = (map_node or {}).get("artifact_sha256_measured")
    declared_not_64_hex = bool(declared) and not re.fullmatch(r"[0-9a-f]{64}", str(declared))
    declared_zero_padded = bool(declared) and bool(
        re.fullmatch(r"[0-9a-f]{8,}0{16,}", str(declared)))
    advisories = []
    if declared_zero_padded:
        advisories.append({
            "id": "W060-ADV-MAP-PIN-PLACEHOLDER",
            "severity": "minor",
            "finding": "map node F2b artifact_sha256 is a zero-padded placeholder "
                       f"({str(declared)[:12]}...0 x48), so declared_hash_matches_measured is "
                       f"false while the canonical file measures {measured0}",
            "owner": "astra (controller map bookkeeping)",
            "detector": "verify_f2b.py::map_declared_zero_padded",
        })
    self_ids = [x.get("class_id") for x in get(doc, "anti_scope.not_this_class", [])
                if isinstance(x, dict) and x.get("class_id") == CLASS_ID]
    if self_ids:
        advisories.append({
            "id": "W060-ADV-ANTISCOPE-SELF-ID",
            "severity": "info",
            "finding": f"{len(self_ids)} anti_scope.not_this_class rows reuse this class's own "
                       "class_id for variant readings (parent_class/variant_id given in prose); "
                       "matches convergence-18 N-A4 labelling recommendation",
            "owner": "lead-formulation",
            "detector": "verify_f2b.py::anti_scope_not_this_class_ids",
        })
    checks["HF_B2"] = {
        "finding": "artifact node_id vs map node label; declared-vs-measured hash bookkeeping",
        "artifact_node_id": get(doc, "node_id"),
        "map_has_node": map_node is not None,
        "map_declared_artifact_sha256": declared,
        "map_declared_not_64_hex": declared_not_64_hex,
        "map_declared_zero_padded_placeholder": declared_zero_padded,
        "map_measured_artifact_sha256": measured_map,
        "map_declared_hash_matches_measured": (map_node or {}).get("declared_hash_matches_measured"),
        "measured_now": measured0,
        "artifact_label_matches_map_node": get(doc, "node_id") == NODE_ID and map_node is not None,
        "ok": get(doc, "node_id") == NODE_ID and map_node is not None,
    }
    # G
    reg = json.loads((ROOT / "artifacts/formulation/VARIANT_REGISTRY.json").read_text())
    variants = reg.get("variants", [])
    bad_parents = [v for v in variants if v.get("parent_class") not in FROZEN_CLASSES]
    variant_ids = sorted({v.get("variant_id") for v in variants})
    c0_variants = [v for v in variants if v.get("parent_class") == CLASS_ID]
    bad_ids = scan_class_ids_surfaces(doc)
    checks["variant_registry"] = {
        "registry_path": "artifacts/formulation/VARIANT_REGISTRY.json",
        "registry_sha256": sha256_file(ROOT / "artifacts/formulation/VARIANT_REGISTRY.json"),
        "n_variants": len(variants),
        "variant_ids": variant_ids,
        "c0_parent_variants": [(v.get("variant_id"), v.get("status")) for v in c0_variants],
        "bad_parents": bad_parents,
        "variant_token_in_class_ids_surface": bad_ids,
        "ok": not bad_parents and not bad_ids,
    }
    # H
    authoring_exists = authoring.exists()
    authoring_sha = sha256_file(authoring) if authoring_exists else None
    checks["publish_binding"] = {
        "canonical": args.canonical,
        "canonical_sha256": measured0,
        "authoring": str(authoring.relative_to(ROOT)),
        "authoring_exists": authoring_exists,
        "authoring_sha256": authoring_sha,
        "byte_identical": authoring_sha == measured0,
        "ok": authoring_sha == measured0,
    }
    # I
    controls = negative_controls()
    controls_ok = (
        bool(controls["merge_assertion_flags"])
        and not controls["plain_prohibition_not_flagged"]
        and not controls["artifact_style_quoted_phrase_not_flagged"]
        and not controls["benign_vs_not_flagged"]
        and bool(controls["scc_conclusion_on_wcc_class_flags"])
        and bool(controls["wcc_conclusion_on_scc_class_flags"])
    )
    controls["ok"] = controls_ok
    if controls["known_conservative_behavior"]["flags"]:
        advisories.append({
            "id": "W060-ADV-DETECTOR-CONSERVATIVE",
            "severity": "info",
            "finding": "class_separation.py flags a prohibition sentence that also contains an "
                       "assertion phrase ('never write ... as a single class'); documented as "
                       "by-design in the module docstring. Calibration input for A1-REBIND-01.",
            "owner": "lead-audit",
            "detector": "verify_f2b.py::negative_controls",
        })
    checks["negative_controls"] = {"detail": controls, "ok": controls_ok}
    # J
    final_sha = sha256_file(canonical)
    drifted = final_sha != measured0
    checks["stability"] = {
        "started_at": t0, "finished_at": now(),
        "pin": pin_sha, "start_measure": measured0, "final_measure": final_sha,
        "stable": not drifted, "ok": not drifted,
    }

    failed = [k for k, v in checks.items() if isinstance(v, dict) and v.get("ok") is False]
    verdict = "PASS" if not failed and not drifted else ("MOVING_TARGET" if drifted else "FAIL")
    snapshot = None
    snapdir = out_path.parent / "snapshots"
    snapdir.mkdir(parents=True, exist_ok=True)
    snapshot = snapdir / f"af_scc_c0_vacuum.{measured0[:12]}.yaml"
    if not snapshot.exists():
        shutil.copyfile(canonical, snapshot)

    ev = {
        "task_id": "W060-F2B-VERDICT-01",
        "actor": "worker-060",
        "role": "bounded_execution_worker",
        "node_id": NODE_ID,
        "class_id": CLASS_ID,
        "gate": GATE,
        "started_at": t0,
        "finished_at": now(),
        "canonical_path": args.canonical,
        "pinned_sha256": pin_sha,
        "measured_sha256": measured0,
        "final_measured_sha256": final_sha,
        "snapshot_path": str(snapshot.relative_to(ROOT)),
        "snapshot_sha256": sha256_file(snapshot),
        "verdict": verdict,
        "failed_checks": failed,
        "advisories": advisories,
        "checks": checks,
        "falsifier": (
            "At the reviewed sha256, any of: (a) a composite 'C0 or C2' token asserted as one "
            "class or a bare composite outside a prohibition context; (b) conclusion_type or "
            "conclusion prose importing the C2 family; (c) a missing G-FORM criterion block "
            "(quantifiers/topology/regularity/genericity/I+/visibility/conclusion_type); "
            "(d) a VARIANT_REGISTRY variant whose parent_class is not one of the four frozen "
            "classes, or a variant id appearing in a class_ids surface; (e) canonical/authoring "
            "divergence; (f) hash drift of the canonical path during the review window."
        ),
        "next_falsifier": (
            "Re-run this script with --pin <new canonical sha256>. A re-review is required at "
            "any hash different from the reviewed one; this verdict does not transfer."
        ),
        "authority_note": (
            "Worker evidence only. No gate verdict, no node completion, no validation_status "
            "promotion; controller/leads own those with artifact + independent review."
        ),
        "detector_refs": [
            "research_map/class_separation.py",
            "research_map/events.schema.json",
            "reviews/F2b-review-18.json#HF-B1,HF-B2",
            "reviews/convergence-18.json#prior_hard_failure_deltas",
        ],
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(ev, indent=1) + "\n")
    print(json.dumps({k: ev[k] for k in ("task_id", "node_id", "class_id",
                                         "measured_sha256", "verdict", "failed_checks")},
                     indent=1))
    return 0 if verdict == "PASS" else (2 if verdict == "MOVING_TARGET" else 1)


if __name__ == "__main__":
    raise SystemExit(main())
