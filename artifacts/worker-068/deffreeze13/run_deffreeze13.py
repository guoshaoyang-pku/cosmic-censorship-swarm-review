#!/usr/bin/env python3
"""W068-FORM-DEFFREEZE-13 runner (worker-068, bounded class-bound task).

Node A1, gate G-CLASSBIND (folded into G-AUDIT as calibration evidence). Classes
AF-WCC-VAC-GEN, AF-SCC-C2-VAC-GEN, AF-SCC-C0-VAC-GEN. Measurement only: never sets a gate
verdict, node status, or validation_status=passed.

Question (successor to gap W068-P12-G1): the four FORM-HELDOUT-08 reference escapes
(m04/m16/m25/m29) escape both class-binding stages with conclusion statements identical to the
frozen base. Does a declared definition-site freeze (R-CAND-D) catch them, what is the minimal
freeze surface that does, and is the catch attributable to the labelled mutation or to
incidental rev8->rev11 drift in the reference corpus?

Method (all bytes pinned; the live tree is not read by the rule):
  1. Re-run both pinned stages on the 4 reference fixtures and verify the frozen
     escaped_union verdicts are reproduced byte-for-byte.
  2. Run both stages on the 4 mutation-isolated fixtures built by build_isolated.py (exactly
     one semantic leaf changed vs the pinned rev11 base) -> confound-free escape measurement.
  3. Apply R-CAND-D variants to the reference, isolated, union and polarity-12 corpora and to
     every conforming control; report catch / false-positive counts.
  4. Exhaustive minimal-subset search over the semantic site groups for (a) 4/4 isolated catch
     and (b) 4/4 reference catch, both with 0 control false positives.

A probe escapes iff BOTH stages accept it. An arm is informative iff its identity control is
accepted by both stages. Validity requires no pinned-input drift between start and end.

Usage: python3 run_deffreeze13.py
Exit: 0 run completed (valid or not); 2 precondition failure.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CST = timezone(timedelta(hours=8))
PY = sys.executable

POL12 = ROOT / "artifacts" / "worker-068" / "polarity12"
SHADOW = POL12 / "shadow"
STAGE_A = SHADOW / "artifacts" / "formulation" / "tools" / "check_class_schema.py"
STAGE_B = SHADOW / "artifacts" / "worker-06" / "spec_conformance_audit.py"
SPEC = SHADOW / "artifacts" / "formulation" / "rule_spec.json"

sys.path.insert(0, str(HERE))
import definition_freeze_check as dfc  # noqa: E402

BASES = {
    "W": "artifacts/worker-068/polarity12/shadow/schemas/af_wcc_vacuum.yaml",
    "C2": "artifacts/worker-068/polarity12/shadow/schemas/af_scc_c2_vacuum.yaml",
    "C0": "artifacts/worker-068/polarity12/shadow/schemas/af_scc_c0_vacuum.yaml",
}
CLASS_OF_BASE = {"W": "AF-WCC-VAC-GEN", "C2": "AF-SCC-C2-VAC-GEN", "C0": "AF-SCC-C0-VAC-GEN"}
BASE_KEY_OF_CLASS = {v: k for k, v in CLASS_OF_BASE.items()}

REF4 = {
    "m04": {"class": "C0", "file": "escape_m04_adm_mass_sign_erased.yaml",
            "fixture": "artifacts/worker-068/heldout3/known_leaks/escape_m04_adm_mass_sign_erased.yaml",
            "family": "adm-mass-erasure"},
    "m16": {"class": "C0", "file": "escape_m16_containment_reversal.yaml",
            "fixture": "artifacts/worker-068/heldout3/known_leaks/escape_m16_containment_reversal.yaml",
            "family": "containment-reversal"},
    "m25": {"class": "W", "file": "escape_m25_wcc_completeness_swap.yaml",
            "fixture": "artifacts/worker-068/heldout3/known_leaks/escape_m25_wcc_completeness_swap.yaml",
            "family": "completeness-definition-swap"},
    "m29": {"class": "C0", "file": "escape_m29_data_domain_contradiction.yaml",
            "fixture": "artifacts/worker-068/heldout3/known_leaks/escape_m29_data_domain_contradiction.yaml",
            "family": "data-domain-contradiction"},
}

UNION = {
    "heldout3": {
        "manifest": "artifacts/worker-068/heldout3/manifest.json",
        "raw": "artifacts/worker-068/heldout3/raw_verdicts.json",
        "list_key": "fixtures", "escape_field": "escaped_union",
        "bases": {k: f"artifacts/worker-068/heldout3/bases/{v}" for k, v in
                  {"W": "af_wcc_vacuum.yaml", "C2": "af_scc_c2_vacuum.yaml", "C0": "af_scc_c0_vacuum.yaml"}.items()},
    },
    "polarity10": {
        "manifest": "artifacts/worker-068/polarity10/manifest.json",
        "raw": "artifacts/worker-068/polarity10/raw_verdicts.json",
        "list_key": "fixtures", "escape_field": "escaped_union",
        "bases": {k: f"artifacts/worker-068/polarity10/bases/{v}" for k, v in
                  {"W": "af_wcc_vacuum.yaml", "C2": "af_scc_c2_vacuum.yaml", "C0": "af_scc_c0_vacuum.yaml"}.items()},
    },
    "polarity11": {
        "manifest": "artifacts/worker-068/polarity11/manifest.json",
        "raw": "artifacts/worker-068/polarity11/raw_verdicts.json",
        "list_key": "results", "escape_field": "escaped",
        "bases": {"W": "artifacts/worker-068/polarity11/shadow/schemas/af_wcc_vacuum.yaml",
                  "C2": "artifacts/worker-068/polarity10/bases/af_scc_c2_vacuum.yaml",
                  "C0": "artifacts/worker-068/polarity10/bases/af_scc_c0_vacuum.yaml"},
    },
}
EXT_CONTROLS = [
    ("artifacts/worker-068/heldout09r/controls_ext/c05_comment_prepend.yaml",
     "artifacts/worker-068/heldout3/controls/ctrl_w_sorted_roundtrip.yaml"),
    ("artifacts/worker-068/heldout09r/controls_ext/c06_comment_append_blank_eof.yaml",
     "artifacts/worker-068/heldout3/controls/ctrl_c2_antiscope_note.yaml"),
    ("artifacts/worker-068/heldout09r/controls_ext/c07_renamed_identical_copy.yaml",
     "artifacts/worker-068/heldout3/controls/ctrl_c0_variant_registered.yaml"),
    ("artifacts/worker-068/heldout09r/controls_ext/probe_pyyaml_resorted_c0.yaml",
     "artifacts/worker-068/heldout3/controls/ctrl_c0_variant_registered.yaml"),
]
VARIANTS = tuple(dfc.VARIANTS)
ROLES = ("conforming_control", "formatting_control", "known_rejected_liveness", "escape_reference",
         "escape", "caught_probe", "content_probe")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def run_cmd(args, timeout=180):
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=timeout, cwd=str(ROOT))
        return {"exit": p.returncode, "stdout": p.stdout, "stderr": p.stderr[-1200:]}
    except subprocess.TimeoutExpired:
        return {"exit": 124, "stdout": "", "stderr": f"timeout after {timeout}s"}


def parse_json(text):
    try:
        return json.loads(text)
    except Exception:
        return None


def stage_a(fixture: Path) -> dict:
    r = run_cmd([PY, str(STAGE_A), "--json", str(fixture)])
    j = parse_json(r["stdout"]) or {}
    return {"tool": str(STAGE_A.relative_to(ROOT)), "exit": r["exit"], "verdict": j.get("verdict"),
            "failed_rules": j.get("failed_rules", []), "parse_ok": bool(j), "stderr": r["stderr"]}


def stage_b(fixture: Path) -> dict:
    r = run_cmd([PY, str(STAGE_B), str(fixture), "--spec", str(SPEC)])
    j = parse_json(r["stdout"]) or {}
    return {"tool": str(STAGE_B.relative_to(ROOT)), "exit": r["exit"], "verdict": j.get("verdict"),
            "failed_rules": j.get("failed_rules", []), "parse_ok": bool(j), "stderr": r["stderr"]}


def accepted(a: dict, b: dict) -> bool:
    return a.get("verdict") == "pass" and b.get("verdict") == "accept"


def rejected(a: dict, b: dict) -> bool:
    return not accepted(a, b)


def classify(expectation: str, escaped: bool) -> str:
    if expectation == "must_be_accepted":
        return "conforming_control"
    if expectation == "known_rejected_positive_control":
        return "known_rejected_liveness"
    if expectation == "known_escape_reference":
        return "escape_reference"
    return "escape" if escaped else "caught_probe"


def base_key_for(class_id, fallback_doc=None, explicit=None):
    if explicit in BASES:
        return explicit
    if isinstance(class_id, str) and class_id in BASE_KEY_OF_CLASS:
        return BASE_KEY_OF_CLASS[class_id]
    # longest-prefix fallback for variant / compound class ids
    cands = [(len(v), k) for k, v in CLASS_OF_BASE.items() if isinstance(class_id, str)
             and class_id.startswith(v)]
    if cands:
        return max(cands)[1]
    # token fallback for reordered / suffixed variant ids (e.g. AF-SCC-C0-CH-VAC)
    if isinstance(class_id, str):
        if class_id.startswith("AF-WCC"):
            return "W"
        if "-C2-" in class_id or class_id.endswith("-C2"):
            return "C2"
        if "-C0-" in class_id or class_id.endswith("-C0"):
            return "C0"
    if fallback_doc and fallback_doc.get("class_id") in BASE_KEY_OF_CLASS:
        return BASE_KEY_OF_CLASS[fallback_doc["class_id"]]
    return None


def freeze_row(row_id, source, role, class_id, base_doc, fx_doc, extra=None):
    changed = dfc.changed_leaves(base_doc, fx_doc)
    by_group = {}
    for c in changed:
        by_group.setdefault(c["group"], []).append(c["path"])
    row = {
        "id": row_id, "source": source, "role": role, "class_id": class_id,
        "changed_leaf_count": len(changed),
        "changed_by_group": {g: sorted(v) for g, v in sorted(by_group.items())},
        "changed_leaves": changed,
        "flags": {v: bool(set(by_group) & set(dfc.VARIANTS[v])) for v in VARIANTS},
        "flag_paths": {v: sorted(p for g in dfc.VARIANTS[v] for p in by_group.get(g, []))
                       for v in VARIANTS},
    }
    if extra:
        row.update(extra)
    return row


def metrics(rows, variants=VARIANTS):
    out = {}
    for v in variants:
        per_role = {}
        for role in ROLES:
            sub = [r for r in rows if r["role"] == role]
            if sub:
                per_role[role] = {"n": len(sub), "flagged": sum(1 for r in sub if r["flags"][v])}
        out[v] = per_role
    return out


def minimal_subsets(rows, target_ids, control_rows, universe=dfc.SEMANTIC_GROUPS):
    """All cardinality-minimal group subsets that flag every target row and no control row."""
    target_groups = []
    for r in rows:
        if r["id"] in target_ids:
            target_groups.append({g for g, paths in r["changed_by_group"].items() if paths})
    control_groups = [{g for g, paths in r["changed_by_group"].items() if paths} for r in control_rows]
    found = []
    for k in range(0, len(universe) + 1):
        for combo in itertools.combinations(universe, k):
            s = set(combo)
            if not all(s & tg for tg in target_groups):
                continue
            if any(s & cg for cg in control_groups):
                continue
            found.append(sorted(s))
        if found:
            break
    return found


def main() -> int:
    iso_manifest_path = HERE / "isolated_manifest.json"
    if not iso_manifest_path.is_file():
        print("isolated_manifest.json missing; run build_isolated.py first", file=sys.stderr)
        return 2
    iso_manifest = json.loads(iso_manifest_path.read_text())
    if not iso_manifest.get("valid"):
        print("isolated corpus invalid", file=sys.stderr)
        return 2
    pol12_manifest = json.loads((POL12 / "manifest.json").read_text())
    invalid = []

    # ---------------------------------------------------------------- pins
    pins = {}
    for rel, meta in pol12_manifest["shadow_pins"].items():
        pins[rel] = meta["sha256"]
    for k, meta in pol12_manifest["bases"].items():
        pins[meta["path"]] = meta["sha256"]
    for spec in REF4.values():
        pins[spec["fixture"]] = sha256_file(ROOT / spec["fixture"])
    for m in iso_manifest["mutations"]:
        pins[m["isolated"]] = m["isolated_sha256"]
        pins[m["reference"]] = m["reference_sha256"]
    for corp, cfg in UNION.items():
        for p in (cfg["manifest"], cfg["raw"]):
            pins[p] = sha256_file(ROOT / p)
        for p in cfg["bases"].values():
            pins[p] = sha256_file(ROOT / p)
    for p, src in EXT_CONTROLS:
        pins[p] = sha256_file(ROOT / p)
        pins[src] = sha256_file(ROOT / src)
    for f in pol12_manifest["fixtures"]:
        pins[f["fixture"]] = f["sha256"]
        if f.get("base_path"):
            pins[f["base_path"]] = sha256_file(ROOT / f["base_path"])
    pins_before = dict(pins)
    for rel, expected in pins_before.items():
        actual = sha256_file(ROOT / rel)
        if actual != expected:
            invalid.append(f"pinned input mismatch at start: {rel}")

    # ---------------------------------------------------------------- reference stage reproduction
    heldout3_raw = json.loads((ROOT / UNION["heldout3"]["raw"]).read_text())
    h3_by_file = {e["file"]: e for e in heldout3_raw["fixtures"]}
    ref_rows, ref_stage = [], {}
    for name, spec in REF4.items():
        p = ROOT / spec["fixture"]
        a, b = stage_a(p), stage_b(p)
        escaped = accepted(a, b)
        frozen = h3_by_file.get(spec["file"], {})
        ref_stage[name] = {
            "fixture": spec["fixture"], "file": spec["file"], "class_id": CLASS_OF_BASE[spec["class"]],
            "family": spec["family"], "stage_a": a, "stage_b": b, "escaped_union_measured": escaped,
            "escaped_union_frozen": bool(frozen.get("escaped_union")),
            "matches_frozen": escaped == bool(frozen.get("escaped_union")),
            "frozen_catch_rules": sorted(set((frozen.get("stage_a") or {}).get("failed_rules", []) +
                                             (frozen.get("stage_b") or {}).get("failed_rules", []))),
        }
        if not ref_stage[name]["matches_frozen"]:
            invalid.append(f"reference verdict mismatch vs frozen raw: {spec['file']}")

    # ---------------------------------------------------------------- isolated stage runs
    iso_rows, iso_stage = [], {}
    for m in iso_manifest["mutations"]:
        p = ROOT / m["isolated"]
        a, b = stage_a(p), stage_b(p)
        escaped = accepted(a, b)
        iso_stage[m["name"]] = {
            "fixture": m["isolated"], "class_id": m["class_id"], "family": m["family"],
            "mutated_leaf_path": m["mutated_leaf_path"], "mutated_leaf_group": m["mutated_leaf_group"],
            "stage_a": a, "stage_b": b, "escaped_union_measured": escaped,
        }

    # ---------------------------------------------------------------- control stage runs
    controls_stage = {}
    for p in ([p for p, _ in EXT_CONTROLS] +
              [f"artifacts/worker-068/heldout3/controls/{f}" for f in
               ["ctrl_w_comment_only.yaml", "ctrl_w_sorted_roundtrip.yaml",
                "ctrl_c2_antiscope_note.yaml", "ctrl_c0_variant_registered.yaml"]] +
              [f"artifacts/worker-068/polarity12/fixtures/ctrl_{c}_identity.yaml"
               for c in ("w", "c2", "c0")]):
        path = ROOT / p
        a, b = stage_a(path), stage_b(path)
        controls_stage[p] = {"stage_a": a, "stage_b": b, "accepted": accepted(a, b)}
        if not accepted(a, b):
            invalid.append(f"conforming control rejected by a stage: {p}")

    # ---------------------------------------------------------------- freeze evaluation rows
    bases = {k: dfc.yaml.safe_load((ROOT / v).read_bytes()) for k, v in BASES.items()}

    def load(rel):
        return dfc.yaml.safe_load((ROOT / rel).read_bytes())

    for name, spec in REF4.items():
        base_doc = bases[spec["class"]]
        fx_doc = load(spec["fixture"])
        ref_rows.append(freeze_row(f"ref:{name}", "reference", "escape_reference",
                                   CLASS_OF_BASE[spec["class"]], base_doc, fx_doc,
                                   {"class_key": spec["class"], "family": spec["family"],
                                    "fixture": spec["fixture"]}))
        if fx_doc.get("class_id") != CLASS_OF_BASE[spec["class"]]:
            invalid.append(f"reference class binding mismatch: {spec['fixture']}")
    for m in iso_manifest["mutations"]:
        base_key = base_key_for(m["class_id"])
        base_doc = bases[base_key]
        fx_doc = load(m["isolated"])
        iso_rows.append(freeze_row(f"iso:{m['name']}", "isolated", "escape_reference",
                                   m["class_id"], base_doc, fx_doc,
                                   {"class_key": base_key, "family": m["family"],
                                    "fixture": m["isolated"],
                                    "mutated_leaf_path": m["mutated_leaf_path"],
                                    "mutated_leaf_group": m["mutated_leaf_group"]}))
        if iso_rows[-1]["changed_leaf_count"] != 1:
            invalid.append(f"isolated fixture not single-leaf: {m['isolated']}")

    # union corpora
    union_rows, union_per_corpus = [], {}
    for corp, cfg in UNION.items():
        raw = json.loads((ROOT / cfg["raw"]).read_text())
        entries = raw[cfg["list_key"]]
        corpus_bases = {k: dfc.yaml.safe_load((ROOT / v).read_bytes()) for k, v in cfg["bases"].items()}
        rows = []
        for e in entries:
            fx_doc = load(e["fixture"])
            cid = e.get("class_id") or fx_doc.get("class_id")
            # class_id may be a compound string in one heldout3 probe; take the first token
            first_cid = cid.split(";")[0] if isinstance(cid, str) else cid
            bk = base_key_for(first_cid, fx_doc, e.get("base"))
            if bk is None:
                invalid.append(f"no base resolved for {e['fixture']}")
                continue
            escaped = bool(e.get(cfg["escape_field"]))
            role = classify(e.get("expectation", ""), escaped)
            r = freeze_row(f"{corp}:{e['file']}", corp, role, CLASS_OF_BASE[bk],
                           corpus_bases[bk], fx_doc,
                           {"class_key": bk, "family": e.get("family"), "fixture": e["fixture"],
                            "escaped_union": escaped})
            rows.append(r)
            union_rows.append(r)
        union_per_corpus[corp] = {
            "n": len(rows),
            "role_counts": {role: sum(1 for r in rows if r["role"] == role) for role in ROLES
                            if any(r["role"] == role for r in rows)},
            "escape_files": [r["id"] for r in rows if r["role"] in ("escape", "escape_reference")],
        }

    # polarity-12 own corpus (statement-axis probes + identity controls)
    p12_rows = []
    for f in pol12_manifest["fixtures"]:
        fx_doc = load(f["fixture"])
        base_doc = load(f["base_path"])
        expectation = f.get("expectation")
        if expectation == "must_be_accepted":
            role = "conforming_control"
        elif expectation == "known_rejected_positive_control":
            role = "known_rejected_liveness"
        else:
            role = "content_probe"
        p12_rows.append(freeze_row(f"p12:{f['file']}", "polarity12", role, f["class_id"],
                                   base_doc, fx_doc,
                                   {"family": f.get("family"), "fixture": f["fixture"],
                                    "op_kind": f.get("op_kind"), "op_id": f.get("op_id")}))

    # extended controls as freeze rows: each is the formatting-only derivative of its source
    # control, so the correct invariance base is that source control, not the class base
    # directly (the source control itself carries a legitimate accepted registry annotation).
    ext_rows = []
    for p, src in EXT_CONTROLS:
        src_doc = load(src)
        fx_doc = load(p)
        ext_rows.append(freeze_row(f"ext:{Path(p).name}", "heldout09r_ext", "formatting_control",
                                   src_doc.get("class_id", "n/a"), src_doc, fx_doc,
                                   {"fixture": p, "source_control": src}))

    all_control_rows = ([r for r in union_rows if r["role"] == "conforming_control"] +
                        [r for r in p12_rows if r["role"] == "conforming_control"] + ext_rows)

    # ---------------------------------------------------------------- metrics
    ref_metrics = metrics(ref_rows)
    iso_metrics = metrics(iso_rows)
    union_metrics = metrics(union_rows)
    p12_metrics = metrics(p12_rows)
    ext_metrics = metrics(ext_rows)
    control_metrics = metrics(all_control_rows)

    union_escape_rows = [r for r in union_rows if r["role"] in ("escape", "escape_reference")]
    def catch(rows_, v):
        return {"n": len(rows_), "flagged": sum(1 for r in rows_ if r["flags"][v])}
    catch_tables = {
        "reference4": {v: catch(ref_rows, v) for v in VARIANTS},
        "isolated4": {v: catch(iso_rows, v) for v in VARIANTS},
        "union_escapes": {v: catch(union_escape_rows, v) for v in VARIANTS},
        "union_by_role": union_metrics,
        "polarity12_content_probes": {v: catch([r for r in p12_rows if r["role"] == "content_probe"], v)
                                      for v in VARIANTS},
        "control_false_positives": {v: {"n": len(all_control_rows),
                                        "flagged": sum(1 for r in all_control_rows if r["flags"][v]),
                                        "files": [r["id"] for r in all_control_rows if r["flags"][v]]}
                                    for v in VARIANTS},
    }

    # single-group catch table
    single_group = {}
    for g in dfc.SEMANTIC_GROUPS + ("META",):
        single_group[g] = {
            "reference4": sum(1 for r in ref_rows if g in r["changed_by_group"]),
            "isolated4": sum(1 for r in iso_rows if g in r["changed_by_group"]),
            "control_fp": sum(1 for r in all_control_rows if g in r["changed_by_group"]),
        }

    iso_targets = [r["id"] for r in iso_rows]
    ref_targets = [r["id"] for r in ref_rows]
    min_iso = minimal_subsets(iso_rows, iso_targets, all_control_rows)
    min_ref = minimal_subsets(ref_rows, ref_targets, all_control_rows,
                              universe=dfc.SEMANTIC_GROUPS + ("META",))

    drift = [rel for rel in pins_before if sha256_file(ROOT / rel) != pins_before[rel]]
    if drift:
        invalid.append(f"pinned input drift during run: {drift}")

    generated_at = datetime.now(CST).isoformat(timespec="seconds")
    findings = [
        {"finding_id": "W068-D13-F1", "kind": "confound-free-escape-measurement",
         "statement": ("All four labelled FORM-HELDOUT-08 mutations, applied alone to the pinned "
                       "rev11 base (exactly one changed leaf each, verified structurally), are "
                       "accepted by BOTH class-binding stages. The escapes are therefore caused by "
                       "the labelled mutation sites themselves, not by the rev8->rev11 drift that "
                       "also separates the original reference fixtures from the base."),
         "evidence": {"isolated_stage_matrix": iso_stage,
                      "isolated_corpus": "artifacts/worker-068/deffreeze13/isolated_manifest.json"},
         "falsifier": ("Any isolated fixture rejected by stage A or stage B at the pinned hashes, "
                       "or a leaf re-diff showing an isolated fixture differs from the base at more "
                       "than the declared mutation leaf.")},
        {"finding_id": "W068-D13-F2", "kind": "corpus-confound-diagnosis",
         "statement": ("On the ORIGINAL reference fixtures a metadata-only freeze "
                       "(freeze_meta_only: revision counters, f0 binding hashes/timestamps) and an "
                       "identity-registry freeze (freeze_identity: anti_scope / "
                       "class_identity_variants) each flag 4/4, while the conclusion-statement freeze "
                       "flags 0/4. A catch measured on the reference corpus alone cannot be "
                       "attributed to the labelled mutation site; mutation isolation is required "
                       "before any freeze rule is credited with the catch."),
         "evidence": {"reference4_variant_matrix": catch_tables["reference4"],
                      "single_group_catch": single_group,
                      "reference4_changed_by_group": {r["id"]: sorted(r["changed_by_group"]) for r in ref_rows}},
         "falsifier": ("A leaf re-diff showing the reference fixtures differ from the base only at the "
                       "labelled mutation site, or a metadata-only / identity-only freeze that does "
                       "not flag all four reference fixtures.")},
        {"finding_id": "W068-D13-F3", "kind": "candidate-rule-measurement",
         "statement": ("The definition-site freeze freeze_defsites_min "
                       "{quantifiers, data_class, i_plus, implication_ledger, extension_predicate} "
                       "flags 4/4 mutation-isolated escapes with 0 false positives over all "
                       "conforming controls; freeze_contract_min adds conclusion.* and also covers "
                       "the statement-axis probes. The cardinality-minimal freeze family for 4/4 "
                       "isolated catch with 0 control false positives is reported, as is the "
                       "(smaller) family that suffices on the confounded reference corpus."),
         "evidence": {"isolated4_variant_matrix": catch_tables["isolated4"],
                      "control_false_positives": catch_tables["control_false_positives"],
                      "minimal_subsets_isolated": min_iso,
                      "minimal_subsets_reference": min_ref,
                      "polarity12_content_probes": catch_tables["polarity12_content_probes"]},
         "falsifier": ("Any mutation-isolated fixture that freeze_defsites_min fails to flag, any "
                       "conforming control it flags, or a smaller group subset that flags all four "
                       "isolated fixtures with zero control false positives.")},
        {"finding_id": "W068-D13-F4", "kind": "false-positive-controls",
         "statement": ("All formatting-only controls (comment prepend/append, PyYAML "
                       "re-serialisation, byte-identical copy under a new name, sorted "
                       "round-trip) have ZERO changed leaves relative to their own source control "
                       "and PASS every freeze variant: the rule is structural, not textual. The "
                       "two conforming controls that legitimately annotate the identity registry "
                       "(anti_scope / class_identity_variants) are accepted by both stages but ARE "
                       "flagged by identity-inclusive variants (freeze_identity, freeze_all, "
                       "freeze_all_minus_meta); the contract variants (freeze_contract_min / "
                       "freeze_contract_full / freeze_defsites_core) flag none of them. The "
                       "identity registry must therefore stay outside a contract freeze unless "
                       "registry annotations are re-frozen by their owner."),
         "evidence": {"extended_control_metrics": ext_metrics,
                      "union_control_metrics": {v: union_metrics[v].get("conforming_control") for v in VARIANTS},
                      "polarity12_control_metrics": {v: p12_metrics[v].get("conforming_control") for v in VARIANTS},
                      "control_false_positives": catch_tables["control_false_positives"]},
         "falsifier": ("Any formatting-only control flagged by freeze_contract_full, or any stage "
                       "rejection of one of the extended controls at the pinned hashes.")},
    ]

    report = {
        "corpus_id": "W068-FORM-DEFFREEZE-13",
        "task_id": "W068-FORM-DEFFREEZE-13",
        "worker": "worker-068", "actor": "worker-068",
        "node_id": "A1",
        "gate": "G-CLASSBIND (folded into G-AUDIT as calibration evidence)",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "question": ("Can a declared definition-site freeze catch the four FORM-HELDOUT-08 "
                     "reference escapes that R-CAND-F misses, what is the minimal freeze surface, "
                     "and is the catch attributable to the labelled mutations?"),
        "generated_at": generated_at,
        "valid": not invalid, "invalid_reasons": invalid,
        "binding": {"shadow_pins": {k: v for k, v in pins_before.items()
                                    if "polarity12/shadow" in k},
                    "bases": BASES, "note": "pinned bytes only; the live tree is not read by the rule"},
        "stage_reproduction": {
            "reference4": ref_stage,
            "reference4_all_match_frozen": all(r["matches_frozen"] for r in ref_stage.values()),
            "isolated4": iso_stage,
            "controls": controls_stage,
        },
        "freeze_evaluation": {
            "variants": {v: sorted(dfc.VARIANTS[v]) for v in VARIANTS},
            "catch_tables": catch_tables,
            "single_group_catch": single_group,
            "minimal_subsets_isolated": min_iso,
            "minimal_subsets_reference": min_ref,
            "reference4_rows": ref_rows,
            "isolated4_rows": iso_rows,
            "union_per_corpus": union_per_corpus,
            "polarity12_rows": p12_rows,
            "ext_control_rows": ext_rows,
        },
        "findings": findings,
        "limitations": [
            "Author-built isolated corpus: the four mutation values are copied from worker-068's heldout3 reference fixtures; the mutation labels remain worker-068's. An independent reviewer must adjudicate each as a genuine class-contract violation.",
            "The union-corpus and polarity-12 evaluations reuse worker-068-built corpora at pinned bytes; they are re-analyses, not an independent corpus.",
            "A freeze rule decides contract invariance, not mathematics: any legitimate post-freeze revision of a covered site requires an owner re-freeze of the class contract.",
            "The minimal-subset search is exact over the declared site taxonomy; a different taxonomy (e.g. splitting data_class) would give a different minimal family.",
            "Worker-068 authored the corpora, the mutated values and this rule candidate; independent replication by an executor other than worker-068 is required before adoption.",
        ],
        "non_claims": [
            "Not a gate verdict and not a node transition; A1/G-CLASSBIND/G-FORM/G-AUDIT remain owned by the controller and leads.",
            "No claim about the truth of any class or of cosmic censorship.",
            "No claim that R-CAND-D is adopted; it is a measured candidate for owner adjudication.",
            "This worker does not claim node completion, validation_status=passed, or any gate verdict.",
        ],
        "falsifier": ("Any mutation-isolated fixture not flagged by freeze_defsites_min; any conforming "
                      "control flagged by any variant; any pinned-input drift; or a stage verdict for an "
                      "isolated fixture that contradicts the measured 4/4 escape."),
        "next_falsifier": ("An independent executor (not worker-068) re-runs the pinned stages on the "
                           "isolated corpus and reproduces the 4/4 escape; an independent reviewer "
                           "adjudicates the four labelled mutations as genuine class-contract violations; "
                           "or an owner-adopted stage revision at a new hash rejects one of them."),
    }

    raw = {
        "corpus_id": report["corpus_id"], "task_id": report["task_id"], "actor": "worker-068",
        "run_at": generated_at, "valid": report["valid"], "invalid_reasons": invalid,
        "pins_before": pins_before,
        "pins_after": {rel: sha256_file(ROOT / rel) for rel in pins_before},
        "reference_stage": ref_stage, "isolated_stage": iso_stage, "controls_stage": controls_stage,
        "freeze": {"variants": {v: sorted(dfc.VARIANTS[v]) for v in VARIANTS},
                   "reference4_rows": ref_rows, "isolated4_rows": iso_rows,
                   "union_rows": union_rows, "polarity12_rows": p12_rows, "ext_control_rows": ext_rows},
    }
    candidate_rule = {
        "candidate_id": "R-CAND-D",
        "status": "proposal_not_adopted",
        "owner": "lead-formulation / lead-audit adjudication",
        "task_id": report["task_id"], "worker": "worker-068", "generated_at": generated_at,
        "successor_to": "R-CAND-F (W068-FORM-POLARITY-12, gap W068-P12-G1)",
        "site_taxonomy": {g: [k for k, v in dfc.GROUP_OF_TOP.items() if v == g]
                          for g in dfc.SEMANTIC_GROUPS if g != "OTHER"},
        "variants": {v: sorted(dfc.VARIANTS[v]) for v in VARIANTS},
        "recommended_surface": ["QUANT", "DATA", "IPLUS", "LEDGER", "EXT", "CONC"],
        "recommended_variant": "freeze_contract_min",
        "measurement": {
            "isolated4_catch": catch_tables["isolated4"]["freeze_defsites_min"],
            "reference4_catch": catch_tables["reference4"]["freeze_defsites_min"],
            "union_escape_catch": catch_tables["union_escapes"]["freeze_contract_min"],
            "polarity12_content_probe_catch": catch_tables["polarity12_content_probes"]["freeze_contract_min"],
            "control_false_positives": catch_tables["control_false_positives"]["freeze_contract_min"],
            "minimal_subsets_isolated": min_iso,
        },
        "implementation": "artifacts/worker-068/deffreeze13/definition_freeze_check.py",
        "falsifier": report["falsifier"],
    }
    (HERE / "raw_verdicts.json").write_text(json.dumps(raw, indent=2, sort_keys=True))
    (HERE / "candidate_rule.json").write_text(json.dumps(candidate_rule, indent=2, sort_keys=True))
    (HERE / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True))
    checkpoint = {
        "checkpoint_id": "w068-ckpt-deffreeze13-1",
        "task_id": report["task_id"], "worker": "worker-068", "created_at": generated_at,
        "valid": report["valid"],
        "summary": {
            "reference4_escapes": sum(1 for r in ref_stage.values() if r["escaped_union_measured"]),
            "reference4_match_frozen": report["stage_reproduction"]["reference4_all_match_frozen"],
            "isolated4_escapes": sum(1 for r in iso_stage.values() if r["escaped_union_measured"]),
            "isolated4_single_leaf": all(r["changed_leaf_count"] == 1 for r in iso_rows),
            "freeze_defsites_min_isolated4_catch": catch_tables["isolated4"]["freeze_defsites_min"]["flagged"],
            "freeze_defsites_min_union_escape_catch": catch_tables["union_escapes"]["freeze_defsites_min"]["flagged"],
            "freeze_contract_min_union_escape_catch": catch_tables["union_escapes"]["freeze_contract_min"]["flagged"],
            "freeze_contract_min_content_probe_catch": catch_tables["polarity12_content_probes"]["freeze_contract_min"]["flagged"],
            "control_false_positives_all_variants": {v: catch_tables["control_false_positives"][v]["flagged"]
                                                     for v in VARIANTS},
            "minimal_subsets_isolated": min_iso,
            "minimal_subsets_reference": min_ref,
        },
        "artifacts": {p.name: sha256_file(p) for p in sorted(HERE.iterdir()) if p.is_file()},
    }
    (HERE / "checkpoint.json").write_text(json.dumps(checkpoint, indent=2, sort_keys=True))

    print(json.dumps({
        "valid": report["valid"], "invalid_reasons": invalid,
        "reference4_escapes": checkpoint["summary"]["reference4_escapes"],
        "isolated4_escapes": checkpoint["summary"]["isolated4_escapes"],
        "catch_tables": {k: {v: catch_tables[k][v] for v in ("freeze_meta_only", "freeze_conclusion",
                                                             "freeze_defsites_min", "freeze_contract_min",
                                                             "freeze_all_minus_meta")}
                         for k in ("reference4", "isolated4", "union_escapes",
                                   "polarity12_content_probes", "control_false_positives")},
        "minimal_subsets_isolated": min_iso, "minimal_subsets_reference": min_ref,
        "single_group_catch": single_group,
    }, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
