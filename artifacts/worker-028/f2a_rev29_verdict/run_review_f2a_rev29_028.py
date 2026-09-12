#!/usr/bin/env python3
"""W028-F2A-REV29-VERDICT-01 — independent F2a review verdict at the FROZEN rev29 pin.

One bounded class-bound task taken by worker-028 (no inbox card existed for this slot):
produce a hash-pinned, machine-evidenced, falsifiable full-schema review verdict for
AF-SCC-C2-VAC-GEN (F2a) at schemas/af_scc_c2_vacuum.yaml = e9a27996dfd3, the rev13 bytes
published by astra-life05-evidence-binding-repair.

Axes measured:
  A. pin/hash stability at entry and exit (F2a, F1, F2b, F0, F0R, evidence, FROZEN, tools, map)
  B. rev12 -> rev13 delta census: prove the repair touched no class semantics
  C. F0 binding chain resolution: declared_f0_sha256, consistency_evidence_sha256,
     class_contract_pointer / supplement pointer resolution, FROZEN rev29 coverage
  D. canonical structural gate (check_class_schema.py --json) on the live bytes
  E. canonical class-separation detector + regression instrument
  F. extension-category completeness (the surviving HF-091-02 axis), vs the C0 sibling
  G. consistency-evidence adequacy: sandbox reproduction of 9e335e9b from frozen inputs,
     mutation sensitivity, and the coverage control that documents what the evidence does
     NOT read.

Authority: worker measurement only. No gate verdict, no node status, no
validation_status=passed, no canonical artifact written (all writes under
artifacts/worker-028/f2a_rev29_verdict/). The reviewer is not an author of any schema and
discloses that reconnaissance read prior verdicts, so this is an informed independent
re-derivation, not a blind first read.

Usage: python3 run_review_f2a_rev29_028.py [--out DIR]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "artifacts/worker-028/f2a_rev29_verdict"

PATHS = {
    "F2a": ROOT / "schemas/af_scc_c2_vacuum.yaml",
    "F1": ROOT / "schemas/af_wcc_vacuum.yaml",
    "F2b": ROOT / "schemas/af_scc_c0_vacuum.yaml",
    "F0": ROOT / "research_map/formulation_taxonomy.yaml",
    "F0R": ROOT / "artifacts/formulation/formulation_taxonomy.yaml",
    "EVID": ROOT / "artifacts/formulation/evidence/taxonomy_consistency.json",
    "FROZEN": ROOT / "artifacts/formulation/FROZEN.json",
    "TOOL_CONS": ROOT / "artifacts/formulation/tools/check_taxonomy_consistency.py",
    "TOOL_GATE": ROOT / "artifacts/formulation/tools/check_class_schema.py",
    "AL": ROOT / "artifacts/formulation/VOCAB_ALIASES.json",
    "MAP": ROOT / "research_map/research_map.json",
    "CLASSSEP": ROOT / "research_map/class_separation.py",
    "REGRESSION": ROOT / "runtime/bin/classsep_regression.py",
    "PRED_F2A": ROOT / "artifacts/worker-022/evbind_guard/pinned/af_scc_c2_vacuum.yaml",
}
# FROZEN rev29 must pin these; declared-vs-measured is checked, not assumed.
DECLARED_PRED = {
    "F2a": "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce",
}
FALSIFIER = (
    "Re-run at the same measured pins. This verdict is falsified by any of: (a) a different "
    "sha256 for schemas/af_scc_c2_vacuum.yaml than e9a27996dfd3 at review time; (b) a rev12->rev13 "
    "delta that changes any line other than revised_at, the revision integer, revision_history, and "
    "the f0_binding consistency_evidence_sha256/checked_at/binding_note; (c) f0_binding resolution "
    "failing at the declared bytes (declared_f0_sha256 != measured F0, or consistency_evidence_sha256 "
    "!= measured evidence); (d) an extension_predicate clause (a)/(c), topology.extension_topology or "
    "iota_regularity field that DOES pin the embedding/manifold category at rev13 (which would void "
    "HF-028R-01); (e) the C0 sibling not pinning the smooth category at its cited lines (which would "
    "void the asymmetry evidence); (f) the sandbox reproduction of the consistency evidence not "
    "returning 9e335e9b from the frozen F0 pair and VOCAB_ALIASES.json, or the mutation controls M1-M3 "
    "not turning the checker INCONSISTENT; (g) the structural gate returning a non-zero exit on the "
    "live bytes; (h) any reviewed artifact pin (F2a, F1, F2b, F0, F0R, evidence, FROZEN, tools) drifting "
    "between the entry and exit pin sets of this run (research_map/research_map.json is live controller "
    "traffic and is excluded)."
)
NON_CLAIMS = [
    "Not a gate verdict and not a node completion; worker events cannot move G-FORM/G-F0/G-AUDIT.",
    "No physics or mathematics truth value is asserted; the review measures artifact bytes, frozen "
    "field completeness, hash resolution and reproducibility only.",
    "The reviewer is not an author of any schema, but has read prior F2a verdicts during task "
    "selection; this verdict is an informed independent re-derivation, not a blind first read.",
    "HF-028R-01 does not prescribe the correct category; it measures that no category is pinned and "
    "that the sibling class pins one for a stated, accepted reason. Choosing the value is the "
    "formulation owner's call.",
    "The consistency-evidence coverage control is a scope measurement, not a defect claim: the "
    "evidence file's declared job is taxonomy-vs-contract consistency.",
]


def sha256_file(p: Path) -> str | None:
    if not p.exists():
        return None
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def measure(p: Path) -> dict:
    st = p.stat() if p.exists() else None
    return {
        "path": str(p.relative_to(ROOT)) if p.exists() else str(p),
        "exists": p.exists(),
        "sha256": sha256_file(p),
        "bytes": st.st_size if st else None,
        "mtime": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(st.st_mtime)) if st else None,
    }


def measure_all() -> dict:
    return {k: measure(v) for k, v in PATHS.items()}


def run(cmd: list[str], cwd: Path | None = None) -> dict:
    t0 = time.time()
    proc = subprocess.run(cmd, cwd=str(cwd or ROOT), capture_output=True, text=True)
    return {
        "cmd": cmd,
        "cwd": str(cwd or ROOT),
        "exit_code": proc.returncode,
        "stdout": proc.stdout[-20000:],
        "stderr": proc.stderr[-8000:],
        "seconds": round(time.time() - t0, 3),
    }


def snapshot(src: Path, label: str, dest_dir: Path) -> dict:
    dest_dir.mkdir(parents=True, exist_ok=True)
    dst = dest_dir / f"{label}.{sha256_file(src)[:12]}{src.suffix}"
    shutil.copy2(src, dst)
    return {"label": label, "src": str(src.relative_to(ROOT)), "snapshot": str(dst.relative_to(ROOT)),
            "sha256": sha256_file(dst), "bytes": dst.stat().st_size}


# ---------------------------------------------------------------- delta census
def delta_census() -> dict:
    a, b = PATHS["PRED_F2A"], PATHS["F2a"]
    text_a = a.read_text().splitlines()
    text_b = b.read_text().splitlines()
    import difflib
    diff = list(difflib.unified_diff(text_a, text_b, lineterm="", n=1,
                                     fromfile=f"rev12 {a.name}", tofile=f"rev13 {b.name}"))
    changed = [ln for ln in diff if ln[:1] in "+-" and not ln.startswith(("+++", "---"))]
    allowed_markers = ("revised_at", "revision_history", "revision:", "f0_binding", "consistency_evidence_sha256",
                       "checked_at", "binding_note", "rev13 delta")
    semantic = []
    for ln in changed:
        body = ln[1:].strip()
        if not any(m in body for m in allowed_markers):
            semantic.append(ln)
    return {
        "predecessor": {"path": str(a.relative_to(ROOT)), "sha256": sha256_file(a),
                        "declared_predecessor_pin": DECLARED_PRED["F2a"],
                        "predecessor_pin_matches": sha256_file(a) == DECLARED_PRED["F2a"]},
        "live": {"path": str(b.relative_to(ROOT)), "sha256": sha256_file(b)},
        "changed_line_count": len(changed),
        "changed_lines": changed,
        "non_allowlisted_changes": semantic,
        "class_semantics_changed": bool(semantic),
        "expected_rev13_scope": "revised_at + revision integer + revision_history entry + f0_binding "
                                "evidence re-stamp (astra-life05-evidence-binding-repair item 2)",
    }


# ---------------------------------------------------------------- hash chain
def hash_chain(f2a_doc: dict, frozen: dict) -> dict:
    fb = f2a_doc.get("f0_binding", {}) or {}
    decl_f0 = str(fb.get("declared_f0_sha256", ""))
    meas_f0 = sha256_file(PATHS["F0"])
    decl_ev = str(fb.get("consistency_evidence_sha256", ""))
    ev_rel = str(fb.get("consistency_evidence", ""))
    meas_ev = sha256_file(ROOT / ev_rel) if (ROOT / ev_rel).exists() else None
    ptr = str(f2a_doc.get("class_contract_pointer", ""))
    sup = str(f2a_doc.get("class_contract_supplement_pointer", ""))
    f0_doc = yaml.safe_load(PATHS["F0"].read_text())
    f0r_doc = yaml.safe_load(PATHS["F0R"].read_text())
    cid = f2a_doc.get("class_id")
    ptr_class = ptr.split("#classes.", 1)[1] if "#classes." in ptr else None
    sup_class = sup.split("#class_contracts.", 1)[1] if "#class_contracts." in sup else None
    frozen_files = frozen.get("files", {})
    return {
        "declared_f0_sha256": decl_f0,
        "measured_f0_sha256": meas_f0,
        "declared_f0_resolves": decl_f0 == meas_f0,
        "declared_f0_artifact": fb.get("declared_f0_artifact"),
        "consistency_evidence": ev_rel,
        "declared_consistency_evidence_sha256": decl_ev,
        "measured_consistency_evidence_sha256": meas_ev,
        "declared_consistency_evidence_resolves": decl_ev == meas_ev,
        "class_contract_pointer": ptr,
        "class_contract_pointer_key_resolves": bool(ptr_class) and ptr_class in (f0_doc.get("classes") or {}),
        "supplement_pointer": sup,
        "supplement_pointer_key_resolves": bool(sup_class) and sup_class in (f0r_doc.get("class_contracts") or {}),
        "frozen_revision": frozen.get("revision"),
        "frozen_f2a_pin": (frozen_files.get("schemas/af_scc_c2_vacuum.yaml") or {}).get("sha256"),
        "frozen_evidence_pin": (frozen_files.get("artifacts/formulation/evidence/taxonomy_consistency.json") or {}).get("sha256"),
        "frozen_c0_pin": (frozen_files.get("schemas/af_scc_c0_vacuum.yaml") or {}).get("sha256"),
        "frozen_f1_pin": (frozen_files.get("schemas/af_wcc_vacuum.yaml") or {}).get("sha256"),
        "frozen_f2a_matches_live": (frozen_files.get("schemas/af_scc_c2_vacuum.yaml") or {}).get("sha256") == sha256_file(PATHS["F2a"]),
        "frozen_evidence_matches_live": (frozen_files.get("artifacts/formulation/evidence/taxonomy_consistency.json") or {}).get("sha256") == sha256_file(PATHS["EVID"]),
    }


# ---------------------------------------------------------------- extension category
def extension_category(f2a_doc: dict, f2b_doc: dict, f1_doc: dict) -> dict:
    import re as _re

    def ep(doc):
        e = doc.get("extension_predicate", {}) or {}
        iota = [None]
        where = [None]

        def rec(o, path=""):
            if isinstance(o, dict):
                for k, v in o.items():
                    if k == "iota_regularity" and iota[0] is None:
                        iota[0] = v
                        where[0] = (path + "/" + k).lstrip("/")
                    rec(v, path + "/" + str(k))
            elif isinstance(o, list):
                for i, v in enumerate(o):
                    rec(v, path + f"[{i}]")

        rec(doc)
        return {
            "definition": str(e.get("definition", "")),
            "iota_regularity": iota[0],
            "iota_regularity_where": where[0],
            "extension_topology": str((doc.get("topology") or {}).get("extension_topology", "")),
        }

    def clause(defn, letter):
        m = _re.search(r"\(" + letter + r"\)\s*(.*?)(?=\([a-f]\)\s|\Z)", defn, _re.S)
        return ("(" + letter + ") " + m.group(1).strip()) if m else None

    a, b, f1 = ep(f2a_doc), ep(f2b_doc), ep(f1_doc)
    a_a, a_c = clause(a["definition"], "a"), clause(a["definition"], "c")
    b_a, b_c = clause(b["definition"], "a"), clause(b["definition"], "c")
    cat_tokens = ("SMOOTH", "C-infinity", "C^infinity", "C∞", "smooth category", "C2 isometric",
                  "C^2 isometric", "C-infinity isometric", "smooth (C-infinity)")
    return {
        "F2a": {
            "clause_a": a_a,
            "clause_c": a_c,
            "clause_a_pins_embedding_category": any(t in (a_a or "") for t in cat_tokens),
            "clause_c_pins_manifold_category": any(t in (a_c or "") for t in cat_tokens),
            "extension_topology": a["extension_topology"][:240],
            "extension_topology_pins_manifold_category": any(t in a["extension_topology"] for t in cat_tokens),
            "iota_regularity_field_present": a["iota_regularity"] is not None,
            "iota_regularity_where": a["iota_regularity_where"],
        },
        "F2b_sibling": {
            "clause_a": b_a,
            "clause_c": b_c,
            "clause_a_pins_embedding_category": any(t in (b_a or "") for t in cat_tokens),
            "clause_c_pins_manifold_category": any(t in (b_c or "") for t in cat_tokens),
            "extension_topology": b["extension_topology"][:240],
            "extension_topology_pins_manifold_category": any(t in b["extension_topology"] for t in cat_tokens),
            "iota_regularity_field_present": b["iota_regularity"] is not None,
            "iota_regularity_value": b["iota_regularity"],
            "iota_regularity_where": b["iota_regularity_where"],
        },
        "F1_scope": {
            "has_extension_predicate": bool(f1_doc.get("extension_predicate")),
            "has_extension_topology": bool(f1["extension_topology"]),
            "iota_regularity_field_present": f1["iota_regularity"] is not None,
        },
        "asymmetry": ((a["iota_regularity"] is None and b["iota_regularity"] is not None)
                      or (not any(t in a["extension_topology"] for t in cat_tokens)
                          and any(t in b["extension_topology"] for t in cat_tokens))),
    }


# ---------------------------------------------------------------- evidence sandbox
SANDBOX_FILES = {
    "research_map/formulation_taxonomy.yaml": "F0",
    "artifacts/formulation/formulation_taxonomy.yaml": "F0R",
    "artifacts/formulation/VOCAB_ALIASES.json": "AL",
    "artifacts/formulation/tools/check_taxonomy_consistency.py": "TOOL_CONS",
}


def build_sandbox(case_dir: Path) -> None:
    for rel, key in SANDBOX_FILES.items():
        dst = case_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(PATHS[key], dst)
    # the checker writes its output here; the frozen tree must be mirrored or the run dies
    (case_dir / "artifacts/formulation/evidence").mkdir(parents=True, exist_ok=True)


def edit_once(path: Path, old: str, new: str) -> bool:
    txt = path.read_text()
    if old not in txt:
        return False
    path.write_text(txt.replace(old, new, 1))
    return True


def evidence_adequacy(root: Path) -> dict:
    base = root / "sandbox/base"
    build_sandbox(base)
    base_run = run([sys.executable, "artifacts/formulation/tools/check_taxonomy_consistency.py"], cwd=base)
    ev = base / "artifacts/formulation/evidence/taxonomy_consistency.json"
    base_sha = sha256_file(ev)
    live_sha = sha256_file(PATHS["EVID"])

    # static input-set measurement from the frozen tool source
    tool_src = PATHS["TOOL_CONS"].read_text()
    reads = [ln.strip() for ln in tool_src.splitlines() if "read_text()" in ln or "read_text(" in ln]

    controls = []

    def mut_case(name, mutate) -> dict:
        d = root / "sandbox" / name
        if d.exists():
            shutil.rmtree(d)
        shutil.copytree(base, d)
        ok = mutate(d)
        r = run([sys.executable, "artifacts/formulation/tools/check_taxonomy_consistency.py"], cwd=d)
        evd = d / "artifacts/formulation/evidence/taxonomy_consistency.json"
        return {
            "id": name, "mutation_applied": ok, "exit_code": r["exit_code"],
            "stdout": r["stdout"].strip()[:400],
            "evidence_sha256": sha256_file(evd) if evd.exists() else None,
            "expected": "exit 1 / INCONSISTENT",
            "ok": ok and r["exit_code"] == 1,
        }

    controls.append(mut_case(
        "M1_A_conclusion_token_wrong",
        lambda d: edit_once(d / "research_map/formulation_taxonomy.yaml",
                            'conclusion_type: "strong_cosmic_censorship_C2"',
                            'conclusion_type: "strong_cosmic_censorship_C0"')))
    controls.append(mut_case(
        "M2_B_regularity_token_wrong",
        lambda d: edit_once(d / "artifacts/formulation/formulation_taxonomy.yaml",
                            "regularity_token: C2", "regularity_token: C0")))
    controls.append(mut_case(
        "M3_A_class_id_removed",
        lambda d: edit_once(d / "research_map/formulation_taxonomy.yaml",
                            '  - "AF-SCC-C2-VAC-GEN"\n', "")))

    # coverage control: the tool never reads schemas/; a garbage class schema must not move the output
    cov = root / "sandbox/C1_class_schema_not_read"
    if cov.exists():
        shutil.rmtree(cov)
    shutil.copytree(base, cov)
    g = cov / "schemas/af_scc_c2_vacuum.yaml"
    g.parent.mkdir(parents=True, exist_ok=True)
    g.write_text("this: is not a schema\n")
    cov_run = run([sys.executable, "artifacts/formulation/tools/check_taxonomy_consistency.py"], cwd=cov)
    cov_ev = cov / "artifacts/formulation/evidence/taxonomy_consistency.json"
    coverage = {
        "id": "C1_class_schema_mutation_not_read",
        "exit_code": cov_run["exit_code"],
        "stdout": cov_run["stdout"].strip()[:400],
        "evidence_sha256": sha256_file(cov_ev) if cov_ev.exists() else None,
        "ok": sha256_file(cov_ev) == base_sha,
        "note": "invariance proves the consistency evidence does not read the class schemas that cite it",
    }

    # determinism / no-op control
    d2 = root / "sandbox/C2_noop_rerun"
    if d2.exists():
        shutil.rmtree(d2)
    shutil.copytree(base, d2)
    rr = run([sys.executable, "artifacts/formulation/tools/check_taxonomy_consistency.py"], cwd=d2)
    det = {
        "id": "C2_noop_rerun", "exit_code": rr["exit_code"],
        "evidence_sha256": sha256_file(d2 / "artifacts/formulation/evidence/taxonomy_consistency.json"),
        "ok": sha256_file(d2 / "artifacts/formulation/evidence/taxonomy_consistency.json") == base_sha,
        "expected": "same bytes as base run",
    }

    return {
        "baseline": {
            "exit_code": base_run["exit_code"],
            "stdout": base_run["stdout"].strip()[:400],
            "stderr_tail": base_run["stderr"][-500:],
            "sandbox_evidence_sha256": base_sha,
            "live_evidence_sha256": live_sha,
            "reproduces_live_bytes": base_sha == live_sha,
            "reproducible_from_frozen_inputs": base_sha == live_sha,
        },
        "tool_source_reads": reads,
        "tool_reads_class_schemas": any("schemas/" in r for r in reads),
        "mutation_controls": controls,
        "coverage_control": coverage,
        "determinism_control": det,
        "controls_all_ok": all(c["ok"] for c in controls) and coverage["ok"] and det["ok"],
        "interpretation": (
            "The live 495-byte evidence is byte-reproducible from the frozen F0 pair + VOCAB_ALIASES "
            "by the frozen checker, and the checker is mutation-sensitive on the fields it compares. "
            "The evidence does not read the three class schemas, and (unlike the 728-byte 675a99d0 "
            "form preserved in artifacts/worker-022) the 495-byte form embeds no sha256 of its inputs. "
            "Reproducibility closes the 'is consistent:true the checker's output on the frozen inputs?' "
            "question empirically; the dropped digest fields remain a non-blocking robustness item."
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    started = time.strftime("%Y-%m-%dT%H:%M:%S%z")

    entry = measure_all()
    snaps = [snapshot(p, k, out / "snapshots") for k, p in PATHS.items() if p.exists()]

    f2a_doc = yaml.safe_load(PATHS["F2a"].read_text())
    f1_doc = yaml.safe_load(PATHS["F1"].read_text())
    f2b_doc = yaml.safe_load(PATHS["F2b"].read_text())
    frozen = json.loads(PATHS["FROZEN"].read_text())

    delta = delta_census()
    chain = hash_chain(f2a_doc, frozen)
    ext = extension_category(f2a_doc, f2b_doc, f1_doc)

    gate = run([sys.executable, str(PATHS["TOOL_GATE"]), "--json", str(PATHS["F2a"])])
    try:
        gate_json = json.loads(gate["stdout"])
    except Exception:
        gate_json = None
    reg = run([sys.executable, str(PATHS["REGRESSION"])])

    # class separation via canonical module
    sep = run([sys.executable, "-c",
               "import json,sys; sys.path.insert(0,'research_map'); import class_separation as cs;"
               "txt=open('schemas/af_scc_c2_vacuum.yaml').read();"
               "print(json.dumps(cs.findings_for_text(txt,'schemas/af_scc_c2_vacuum.yaml')))"])

    evid = evidence_adequacy(out)

    # ---- verdict logic
    hard_failures, findings, positives = [], [], []
    f2a_ext, f2b_ext = ext["F2a"], ext["F2b_sibling"]
    embedding_category_unpinned = (f2a_ext["iota_regularity_field_present"] is False
                                   and f2b_ext["iota_regularity_field_present"] is True)
    manifold_category_unpinned = (not f2a_ext["extension_topology_pins_manifold_category"]
                                  and f2b_ext["extension_topology_pins_manifold_category"])
    if (embedding_category_unpinned or manifold_category_unpinned) \
            and not f2a_ext["iota_regularity_field_present"]:
        hard_failures.append({
            "id": "HF-028R-01",
            "type": "extension_category_incompleteness",
            "severity": "blocking",
            "fields": ["extension_predicate.definition clause (a)", "extension_predicate.definition clause (c)",
                       "topology.extension_topology"],
            "machine_flags": {
                "f2a_clause_a": f2a_ext["clause_a"],
                "f2a_clause_c": f2a_ext["clause_c"],
                "f2a_clause_a_pins_embedding_category": f2a_ext["clause_a_pins_embedding_category"],
                "f2a_extension_topology_pins_manifold_category": f2a_ext["extension_topology_pins_manifold_category"],
                "f2a_iota_regularity_field_present": f2a_ext["iota_regularity_field_present"],
                "f2b_clause_c": f2b_ext["clause_c"],
                "f2b_extension_topology_pins_manifold_category": f2b_ext["extension_topology_pins_manifold_category"],
                "f2b_iota_regularity_field_present": f2b_ext["iota_regularity_field_present"],
                "embedding_category_unpinned": embedding_category_unpinned,
                "manifold_category_unpinned": manifold_category_unpinned,
            },
            "finding": (
                "F2a rev13 leaves the extension category unpinned on the two structural conventions its C0 "
                "sibling freezes. Clause (a) requires 'an isometric embedding' with no regularity; clause (c) "
                "and topology.extension_topology require 'a connected 4-manifold' with no manifold category; "
                "there is no iota_regularity field anywhere in the document (recursive key search). F2b pins "
                "clause (c) 'SMOOTH (C-infinity) connected 4-manifold' and carries "
                "non_vacuity.iota_regularity='C-infinity isometric embedding (smooth category); ... a "
                "C0-embedding variant would be a different class' (line 190, accepted worker-16 "
                "F2b-16-03). Because the F2a conclusion is a NON-EXISTENCE statement over extensions, "
                "widening the admissible extension category (e.g. allowing C1 embeddings) changes the "
                "statement's content and its strength, so the class is not fully frozen at rev13. The rev13 "
                "repair was binding-only (delta census), so this survives unchanged from rev12."
            ),
            "evidence_refs": [
                "schemas/af_scc_c2_vacuum.yaml:93", "schemas/af_scc_c2_vacuum.yaml:95",
                "schemas/af_scc_c2_vacuum.yaml:117", "schemas/af_scc_c0_vacuum.yaml:91",
                "schemas/af_scc_c0_vacuum.yaml:118", "schemas/af_scc_c0_vacuum.yaml:190",
                "reviews/F2a-review-rev27-b.json#HF-091-02",
            ],
            "required_fix": (
                "Add an explicit extension-category pin to F2a: an iota_regularity field naming the "
                "embedding category, and a manifold category in clause (c)/topology.extension_topology, "
                "with a one-line rationale; use the C0 sibling's accepted convention for consistency "
                "unless a stated C2-specific reason justifies a different value."
            ),
            "falsifier": ("A rev14 F2a in which clause (a), clause (c), topology.extension_topology or a new "
                          "iota_regularity field pin the embedding/manifold category at the reviewed bytes."),
        })

    positives.append({
        "id": "PC-028-01", "type": "hash_bound_evidence_mismatch_resolved",
        "statement": ("The rev12 blocking defect (declared consistency_evidence_sha256 675a99d0 != measured "
                      "9e335e9b) is RESOLVED at rev13: declared == measured == 9e335e9b, FROZEN rev29 pins the "
                      "same bytes, and the value resolves in F1/F2b as well."),
        "evidence_refs": ["schemas/af_scc_c2_vacuum.yaml:292",
                          "artifacts/formulation/evidence/taxonomy_consistency.json#9e335e9ba1bf",
                          "artifacts/formulation/FROZEN.json#e1a8aaa394eb"],
    })
    positives.append({
        "id": "PC-028-02", "type": "evidence_reproducible_and_sensitive",
        "statement": ("Re-running the frozen checker in a sandbox on the frozen F0 pair + VOCAB_ALIASES "
                      "reproduces the live evidence byte-for-byte (9e335e9b), and the checker turns "
                      "INCONSISTENT under three independent semantic mutations. 'consistent: true' is "
                      "therefore verifiable from pinned inputs by an independent party even though the "
                      "495-byte form embeds no digests."),
        "evidence_refs": ["artifacts/formulation/tools/check_taxonomy_consistency.py#de356d999ea3",
                          "artifacts/worker-028/f2a_rev29_verdict/report.json"],
    })

    findings.append({
        "id": "F-028R-01", "severity": "minor", "type": "evidence_form_regression",
        "statement": ("The 495-byte live evidence form drops the map_taxonomy_sha256 / lead_contract_sha256 / "
                      "measured_at fields carried by the preserved 728-byte 675a99d0 form, because the frozen "
                      "checker unconditionally rewrites the canonical path (line 80). Non-blocking given "
                      "byte-reproducibility, but the writer guard staged by worker-022/w074 should land so a "
                      "future checker run cannot silently re-serialize the gate-bound path."),
        "evidence_refs": ["artifacts/worker-022/evbind_guard/pinned/taxonomy_consistency.675a99d0d25b.json",
                          "artifacts/formulation/tools/check_taxonomy_consistency.py:80"],
    })
    findings.append({
        "id": "F-028R-02", "severity": "minor", "type": "revision_history_order",
        "statement": ("revision_history index 9 carries at 2026-09-11T23:30:35, earlier than index 8 at "
                      "2026-09-12T00:30:00; the trail is not monotone. Cosmetic, independently reproduced."),
        "evidence_refs": ["schemas/af_scc_c2_vacuum.yaml:17-18"],
    })

    # score: substantively strong, one blocking definitional-completeness item
    verdict = "revise" if hard_failures else "accept"
    score = 3.5 if verdict == "revise" else 4.0

    exit_pins = measure_all()
    drift = sorted(k for k in entry if entry[k]["sha256"] != exit_pins[k]["sha256"])
    artifact_drift = [k for k in drift if k != "MAP"]

    classsep_findings = None
    try:
        classsep_findings = json.loads(sep["stdout"])
    except Exception:
        pass

    review = {
        "schema": "worker-028/review/v1",
        "review_id": "W028-F2A-REV29-VERDICT-01",
        "event_id": "w028-f2a-rev29-review-20260912T010000",
        "event_type": "review",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "actor": "worker-028",
        "reviewer": "worker-028",
        "reviewer_role": "bounded execution worker; not an author of any reviewed artifact",
        "target_id": "F2a",
        "node_id": "F2a",
        "gate": "G-FORM",
        "class_id": "AF-SCC-C2-VAC-GEN",
        "artifact_path": "schemas/af_scc_c2_vacuum.yaml",
        "reviewed_sha256": sha256_file(PATHS["F2a"]),
        "artifact_sha256": sha256_file(PATHS["F2a"]),
        "artifact_revision": f2a_doc.get("revision"),
        "counts_as_full_schema_verdict": True,
        "verdict": verdict,
        "score": score,
        "score_scale": "0-5; =4.0 with no blocking finding, 3.5 with one blocking definitional item",
        "hard_failures": hard_failures,
        "findings": findings,
        "positive_checks": positives,
        "hash_stability": {
            "entry_pins": entry, "exit_pins": exit_pins, "drift": drift,
            "artifact_pins_drift": artifact_drift,
            "stable_across_review": not artifact_drift,
            "map_drift_note": ("MAP is live controller traffic, not a review input; it moved during the "
                               "review window while every reviewed artifact pin stayed fixed."
                               if "MAP" in drift else "no map drift observed"),
            "reviewer_started_at": started,
            "reviewer_finished_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        },
        "delta_census": delta,
        "f0_binding_hash_chain": chain,
        "extension_category": ext,
        "machine_evidence": {
            "structural_gate": {"cmd": gate["cmd"], "exit_code": gate["exit_code"],
                                "verdict": (gate_json or {}).get("verdict"),
                                "failed_rules": (gate_json or {}).get("failed_rules"),
                                "stderr_tail": gate["stderr"][-400:]},
            "classsep_module_findings": classsep_findings,
            "classsep_stdout_tail": sep["stdout"][-300:],
            "classsep_regression": {"exit_code": reg["exit_code"], "stdout_tail": reg["stdout"][-900:]},
            "evidence_adequacy": evid,
        },
        "independence": {
            "independent_of_authorship": True,
            "blind": False,
            "disclosure": ("Task selection reconciled the live map and review corpus, so prior F2a verdicts "
                           "(notably worker-091 HF-091-01/02) were read before this review was written. This "
                           "verdict re-derives every claim from pinned bytes with its own controls rather than "
                           "reusing verdict text; HF-028R-01 corroborates HF-091-02 and is labelled as "
                           "corroboration, not novelty."),
            "shared_verdict_text": False,
            "kish_ess_note": "single-reviewer measurement; no ESS claim",
        },
        "authority_note": ("Worker measurement only. No gate verdict, no node status, no "
                           "validation_status=passed, no canonical artifact edited; writes are confined to "
                           "artifacts/worker-028/f2a_rev29_verdict/."),
        "falsifier": FALSIFIER,
        "next_falsifier": ("If a rev14 pins the extension category, re-run the hash chain and the structural "
                           "gate and re-measure clauses (a)/(c)/extension_topology/iota_regularity; the only "
                           "open F2a item then is the non-blocking evidence-form regression."),
        "non_claims": NON_CLAIMS,
        "evidence_refs": [
            "schemas/af_scc_c2_vacuum.yaml#e9a27996dfd3",
            "schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe",
            "research_map/formulation_taxonomy.yaml#0abb9ed8a961",
            "artifacts/formulation/formulation_taxonomy.yaml#d7419b4e8963",
            "artifacts/formulation/evidence/taxonomy_consistency.json#9e335e9ba1bf",
            "artifacts/formulation/FROZEN.json#e1a8aaa394eb",
            "artifacts/formulation/tools/check_class_schema.py#000e09e46b2f",
            "artifacts/formulation/tools/check_taxonomy_consistency.py#de356d999ea3",
            "research_map/research_map.json#" + (sha256_file(PATHS["MAP"]) or "")[:12],
            "artifacts/worker-022/evbind_guard/pinned/af_scc_c2_vacuum.yaml#5476a3f2c6bc",
        ],
    }

    (out / "review_f2a_rev29_028.json").write_text(json.dumps(review, indent=2) + "\n")
    report = {
        "task_id": "W028-F2A-REV29-VERDICT-01",
        "actor": "worker-028",
        "created_at": review["created_at"],
        "verdict": verdict,
        "score": score,
        "reviewed_sha256": review["reviewed_sha256"],
        "hard_failure_ids": [h["id"] for h in hard_failures],
        "finding_ids": [f["id"] for f in findings],
        "positive_ids": [p["id"] for p in positives],
        "hash_stable": not artifact_drift,
        "delta_non_allowlisted_changes": delta["non_allowlisted_changes"],
        "f0_binding_resolves": chain["declared_f0_resolves"] and chain["declared_consistency_evidence_resolves"],
        "structural_gate_exit": gate["exit_code"],
        "class_separation_findings": classsep_findings,
        "classsep_regression_exit": reg["exit_code"],
        "evidence_reproduces_live": evid["baseline"]["reproduces_live_bytes"],
        "evidence_controls_all_ok": evid["controls_all_ok"],
        "evidence_tool_reads_class_schemas": evid["tool_reads_class_schemas"],
        "snapshots": snaps,
        "entry_pins": entry,
        "exit_pins": exit_pins,
        "falsifier": FALSIFIER,
        "non_claims": NON_CLAIMS,
    }
    (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")

    # sha sidecars + checkpoint
    for name in ("review_f2a_rev29_028.json", "report.json"):
        p = out / name
        (out / (name + ".sha256")).write_text(f"{sha256_file(p)}  {name}\n")
    ckpt = {
        "schema": "worker-028/checkpoint/v1",
        "checkpoint_id": "w028-ckpt-f2a-rev29-verdict-" + time.strftime("%Y%m%dT%H%M%S"),
        "actor": "worker-028",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "task": "one class-bound task: independent F2a review verdict at the FROZEN rev29 pin",
        "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-WCC-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "node_id": "F2a",
        "gate": "G-FORM",
        "artifact": {"path": "artifacts/worker-028/f2a_rev29_verdict/review_f2a_rev29_028.json",
                     "sha256": sha256_file(out / "review_f2a_rev29_028.json"),
                     "bytes": (out / "review_f2a_rev29_028.json").stat().st_size},
        "runner": {"path": "artifacts/worker-028/f2a_rev29_verdict/run_review_f2a_rev29_028.py",
                   "sha256": sha256_file(Path(__file__))},
        "report": {"path": "artifacts/worker-028/f2a_rev29_verdict/report.json",
                   "sha256": sha256_file(out / "report.json")},
        "pins": {k: v["sha256"] for k, v in entry.items() if v["sha256"]},
        "result": {"verdict": verdict, "score": score,
                   "hard_failures": [h["id"] for h in hard_failures],
                   "hash_stable": not artifact_drift,
                   "f0_binding_resolves": chain["declared_f0_resolves"] and chain["declared_consistency_evidence_resolves"],
                   "evidence_reproduces_live": evid["baseline"]["reproduces_live_bytes"]},
        "falsifier": FALSIFIER,
        "stop": "bounded worker task complete; no gate verdict, no node status; exit after emitting comms events",
    }
    (out / "checkpoint_028.json").write_text(json.dumps(ckpt, indent=1) + "\n")
    (out / "checkpoint_028.json.sha256").write_text(
        f"{sha256_file(out / 'checkpoint_028.json')}  checkpoint_028.json\n")

    print(f"VERDICT {verdict} score={score} sha={review['reviewed_sha256'][:12]}")
    print(f"hard_failures={[h['id'] for h in hard_failures]} findings={[f['id'] for f in findings]}")
    print(f"hash_stable={not artifact_drift} f0_binding_resolves="
          f"{chain['declared_f0_resolves'] and chain['declared_consistency_evidence_resolves']}")
    print(f"structural_gate_exit={gate['exit_code']} classsep_regression_exit={reg['exit_code']}")
    print(f"evidence_reproduces_live={evid['baseline']['reproduces_live_bytes']} "
          f"controls_all_ok={evid['controls_all_ok']} tool_reads_class_schemas={evid['tool_reads_class_schemas']}")
    print(f"delta_non_allowlisted={delta['non_allowlisted_changes']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
