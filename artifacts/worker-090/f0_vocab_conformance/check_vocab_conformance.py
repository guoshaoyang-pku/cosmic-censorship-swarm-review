#!/usr/bin/env python3
"""W090-F0-VOCAB-CONFORMANCE-01 -- independent, hash-pinned vocabulary conformance audit of the
frozen rev12 F1/F2a/F2b class schemas against the canonical F0 rev5 taxonomy vocabulary.

Task: worker-090, node F2a (primary class AF-SCC-C2-VAC-GEN), gate G-FORM, corroborating
scope F1/F2b. Read-only: the canonical tree is never written. Controls run on sandbox copies
under this artifact directory only.

What it measures (all mechanical, no prose inference):
  A. F0 self-consistency: every vocabulary-valued token in F0's own classes[*].axes is a member
     of F0's own field_vocabulary[*].allowed.
  B. Per-schema conformance of the vocabulary-valued fields:
       conclusion.conclusion_type        vs field_vocabulary.conclusion_type.allowed
       genericity.kind                   vs field_vocabulary.genericity_kind.allowed
       class_components.regularity_token vs field_vocabulary.regularity_token.allowed
       class_components.censorship       vs field_vocabulary.family.allowed
     Each observed token is classified as one of:
       exact            token is a member of the F0 allowed list;
       alias_resolvable token is a registry alias whose registry canonical is F0-allowed;
       inverted         token is a registry CANONICAL whose aliases (not it) are F0-allowed;
       unregistered     neither of the above.
  C. Registry binding: whether each schema declares the alias registry it depends on
     (a text occurrence of VOCAB_ALIASES.json / genericity.vocabulary_aliases_ref).
  D. Sanity: duplicate top-level YAML keys (a parser hazard) in each compared file.

Exit code 0 iff the pin is stable across the run and all controls produce their pre-committed
expected classifications. A nonzero exit means the measurement is void, not that a gate passed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]  # .../ai4math-swarm/artifacts/worker-090/f0_vocab_conformance/<file>
CST = timezone(timedelta(hours=8))

F0 = "research_map/formulation_taxonomy.yaml"
REGISTRY = "artifacts/formulation/VOCAB_ALIASES.json"
SCHEMAS = {
    "F1": "schemas/af_wcc_vacuum.yaml",
    "F2a": "schemas/af_scc_c2_vacuum.yaml",
    "F2b": "schemas/af_scc_c0_vacuum.yaml",
}
FROZEN = "artifacts/formulation/FROZEN.json"
PINNED = [F0, REGISTRY, FROZEN] + list(SCHEMAS.values())

NULLISH = {None, "none", "null", "None"}


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_path(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def measure(paths, root: Path = ROOT) -> dict:
    return {str(p): sha256_path(root / p) for p in paths}


class DupKeyLoader(yaml.SafeLoader):
    """SafeLoader that records duplicate mapping keys instead of silently last-winning."""


def _construct_mapping(loader, node, deep=False):
    loader.flatten_mapping(node)
    seen, dups = set(), []
    for k_node, _ in node.value:
        try:
            k = loader.construct_object(k_node, deep=deep)
        except Exception:
            continue
        if isinstance(k, (str, int, float, bool)) or k is None:
            if k in seen:
                dups.append(k)
            seen.add(k)
    loader._dups = getattr(loader, "_dups", [])
    loader._dups.extend(dups)
    return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)


DupKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping
)


def load_yaml(p: Path):
    loader = DupKeyLoader(p.read_text())
    try:
        doc = loader.get_single_data()
    finally:
        loader.dispose()
    dups = getattr(loader, "_dups", [])
    return doc, sorted({str(d) for d in dups})


def load_json(p: Path):
    return json.loads(p.read_text())


def line_of(path: Path, needle: str):
    """First 1-based text line containing needle (plain substring), else None."""
    if needle is None:
        return None
    for i, line in enumerate(path.read_text().splitlines(), 1):
        if needle in line:
            return i
    return None


def norm(value):
    """Normalise a declared vocabulary value; 'none'/absent regularity means the null token."""
    if value is None:
        return None
    s = str(value).strip()
    if s in NULLISH:
        return None
    return s


def allowed_set(f0_doc, axis):
    spec = (f0_doc.get("field_vocabulary") or {}).get(axis) or {}
    out = []
    for v in spec.get("allowed", []) or []:
        out.append(None if v is None else str(v))
    return out


def registry_maps(reg_doc, axis):
    """Return (canonical -> aliases, alias -> canonical) restricted to one axis."""
    canon_to_aliases, alias_to_canon = {}, {}
    for canon, aliases in (reg_doc.get(axis) or {}).items():
        canon_to_aliases[str(canon)] = [str(a) for a in aliases]
        for a in aliases:
            alias_to_canon[str(a)] = str(canon)
    return canon_to_aliases, alias_to_canon


def classify(token, allowed, canon_to_aliases, alias_to_canon):
    """One of exact | alias_resolvable | inverted | unregistered | null_token."""
    if token is None:
        if None in allowed or "none" in [str(a).lower() for a in allowed if a is not None]:
            return "null_token"
        return "unregistered"
    if token in allowed:
        return "exact"
    if token in alias_to_canon and alias_to_canon[token] in allowed:
        return "alias_resolvable"
    if token in canon_to_aliases:
        if any(a in allowed for a in canon_to_aliases[token]):
            return "inverted"
    return "unregistered"


def schema_rows(name, path: Path, f0_doc, reg_doc):
    doc, dups = load_yaml(path)
    rows = []
    pointers = []
    text = path.read_text()
    for needle in ("VOCAB_ALIASES.json", "vocabulary_aliases_ref"):
        if needle in text:
            pointers.append({"needle": needle, "line": line_of(path, needle)})
    axes = [
        ("conclusion_type", (doc.get("conclusion") or {}).get("conclusion_type"),
         "conclusion.conclusion_type"),
        ("genericity_kind", (doc.get("genericity") or {}).get("kind"),
         "genericity.kind"),
        ("regularity_token", (doc.get("class_components") or {}).get("regularity_token"),
         "class_components.regularity_token"),
        ("family", (doc.get("class_components") or {}).get("censorship"),
         "class_components.censorship"),
    ]
    for axis, raw, loc in axes:
        tok = norm(raw)
        allowed = allowed_set(f0_doc, axis)
        c2a, a2c = registry_maps(reg_doc, axis)
        cls = classify(tok, allowed, c2a, a2c)
        raw_txt = "null" if raw is None else str(raw)
        rows.append({
            "schema": name,
            "path": str(path.relative_to(ROOT)),
            "class_id": doc.get("class_id"),
            "axis": axis,
            "field": loc,
            "declared": raw_txt,
            "declared_normalised": tok,
            "line": line_of(path, str(raw)),
            "f0_allowed": allowed,
            "registry_canonical_of_declared": a2c.get(tok) if tok else None,
            "registry_aliases_of_declared": c2a.get(tok) if tok else None,
            "classification": cls,
            "registry_pointer_declared": bool(pointers),
        })
    component_codes = {
        "asymptotics_code": (doc.get("class_components") or {}).get("asymptotics"),
        "matter_code": (doc.get("class_components") or {}).get("matter"),
        "genericity_code": (doc.get("class_components") or {}).get("genericity"),
    }
    return doc, rows, pointers, dups, component_codes


def f0_self_rows(f0_doc, reg_doc):
    rows = []
    for cid in sorted((f0_doc.get("classes") or {}).keys()):
        axes = ((f0_doc.get("classes") or {}).get(cid) or {}).get("axes") or {}
        for axis in ("conclusion_type", "genericity_kind", "regularity_token", "family",
                     "matter_model", "symmetry", "asymptotics"):
            if axis not in axes:
                continue
            tok = norm(axes[axis])
            allowed = allowed_set(f0_doc, axis)
            c2a, a2c = registry_maps(reg_doc, axis)
            rows.append({
                "class_id": cid,
                "axis": axis,
                "declared": "null" if axes[axis] is None else str(axes[axis]),
                "declared_normalised": tok,
                "f0_allowed": allowed,
                "registry_canonical_of_declared": a2c.get(tok) if tok else None,
                "registry_aliases_of_declared": c2a.get(tok) if tok else None,
                "classification": classify(tok, allowed, c2a, a2c),
                "line": line_of(ROOT / F0, str(axes[axis])),
            })
    return rows


def audit(root: Path):
    """Run the full audit against a filesystem root. Returns (result_dict, ok_flag)."""
    f0_path, reg_path = root / F0, root / REGISTRY
    f0_doc, f0_dups = load_yaml(f0_path)
    reg_doc = load_json(reg_path)

    self_rows = f0_self_rows(f0_doc, reg_doc)
    matrix, pointers_by_schema, dups_by_schema, codes = [], {}, {}, {}
    for name, rel in SCHEMAS.items():
        _, rows, pointers, dups, component_codes = schema_rows(name, root / rel, f0_doc, reg_doc)
        matrix.extend(rows)
        pointers_by_schema[name] = pointers
        dups_by_schema[name] = dups
        codes[name] = component_codes

    def count(rows, key="classification"):
        out = {}
        for r in rows:
            out[r[key]] = out.get(r[key], 0) + 1
        return dict(sorted(out.items()))

    findings = []
    inverted = [f"{r['schema']}:{r['axis']}={r['declared']}" for r in matrix
                if r["classification"] == "inverted"]
    if inverted:
        findings.append({
            "id": "W090-VOCAB-01",
            "severity": "major",
            "statement": ("Authority inversion: the observed token is the canonical key of "
                          "VOCAB_ALIASES.json while F0's allowed list contains only its aliases, "
                          "so exact F0 membership and registry canonicity disagree."),
            "instances": sorted(inverted),
        })
    unreg = [f"{r['schema']}:{r['axis']}={r['declared']}" for r in matrix
             if r["classification"] == "unregistered"]
    if unreg:
        findings.append({
            "id": "W090-VOCAB-02",
            "severity": "major",
            "statement": "Token used by a frozen schema is neither F0-allowed nor alias-resolvable.",
            "instances": sorted(unreg),
        })
    alias_used = [f"{r['schema']}:{r['axis']}={r['declared']}" for r in matrix
                  if r["classification"] == "alias_resolvable"]
    findings.append({
        "id": "W090-VOCAB-03",
        "severity": "info",
        "statement": ("Registry-alias tokens accepted only through VOCAB_ALIASES.json; the alias "
                      "policy reserves aliases for consistency checks, so each is a candidate "
                      "canonicalisation target rather than an exact F0 value."),
        "instances": sorted(alias_used),
    })
    unbound = sorted(n for n, p in pointers_by_schema.items() if not p)
    if unbound:
        findings.append({
            "id": "W090-VOCAB-04",
            "severity": "major",
            "statement": ("Schema depends on the alias registry for at least one non-exact token "
                          "but declares no registry pointer, so the dependency is implicit."),
            "instances": unbound,
        })
    self_bad = [f"{r['class_id']}:{r['axis']}={r['declared']}" for r in self_rows
                if r["classification"] not in ("exact", "null_token")]
    findings.append({
        "id": "W090-VOCAB-05",
        "severity": "blocker" if self_bad else "info",
        "statement": ("F0 self-consistency of classes[*].axes against F0 field_vocabulary: "
                      + ("VIOLATIONS present." if self_bad else "clean (all tokens exact).")),
        "instances": sorted(self_bad),
    })
    alias_in_f0 = [f"{r['class_id']}:{r['axis']}={r['declared']} (registry canonical: "
                   f"{r['registry_canonical_of_declared']})" for r in self_rows
                   if r["registry_canonical_of_declared"]
                   and r["registry_canonical_of_declared"] != r["declared_normalised"]]
    if alias_in_f0:
        findings.append({
            "id": "W090-VOCAB-06",
            "severity": "major",
            "statement": ("The canonical taxonomy's own class descriptors carry registry-ALIAS "
                          "tokens; under the registry policy ('accepted aliases ... must never "
                          "appear in a new canonical artifact') each is a canonicalisation target."),
            "instances": sorted(alias_in_f0),
        })

    result = {
        "task_id": "W090-F0-VOCAB-CONFORMANCE-01",
        "actor": "worker-090",
        "created_at": now(),
        "cst_note": "all timestamps +08:00",
        "method": ("read canonical bytes; extract vocabulary-valued fields structurally with "
                   "PyYAML; classify against F0 field_vocabulary.allowed using the declared "
                   "VOCAB_ALIASES.json registry; no prose inference, no canonical writes"),
        "authority": {
            "f0_artifact": F0,
            "alias_registry": REGISTRY,
            "alias_policy": reg_doc.get("policy"),
            "rejected_ambiguous_tokens": reg_doc.get("rejected_ambiguous_tokens"),
        },
        "pins": measure(PINNED, root),
        "f0_self_consistency": {"rows": self_rows, "violations": sorted(self_bad),
                                "classification_counts": count(self_rows)},
        "matrix": matrix,
        "component_codes_informational": codes,
        "registry_binding": pointers_by_schema,
        "duplicate_top_level_keys": {**{F0: f0_dups}, **dups_by_schema},
        "summary": {
            "by_classification": count(matrix),
            "by_schema": {n: count([r for r in matrix if r["schema"] == n]) for n in SCHEMAS},
            "inverted": sorted(inverted),
            "unregistered": sorted(unreg),
            "alias_resolvable": sorted(alias_used),
            "schemas_without_registry_pointer": unbound,
        },
        "findings": findings,
        "non_claims": [
            "Not a full-schema verdict; quantifiers, topology, physics and class semantics are out of scope.",
            "No canonical artifact was written or edited by this audit.",
            "The audit does not decide which authority wins (F0 allowed list vs registry canonical); "
            "it measures that they disagree and names the instances.",
            "component codes (VAC/AF/GEN) are reported for information only; they are not "
            "field_vocabulary values and are not scored.",
        ],
        "falsifier": (
            "Falsified if, at the pinned hashes, (a) any token classified unregistered/inverted is a "
            "member of the F0 allowed list for its axis, (b) any token classified exact is absent "
            "from both the allowed list and the registry alias table, (c) a schema classified "
            "registry-pointer-absent in fact contains a VOCAB_ALIASES.json reference, or (d) any "
            "control below does not reproduce its pre-committed expected classification."
        ),
    }
    result["classifications_ok"] = not unreg
    return result, not self_bad


def run_controls(root: Path):
    """Sandbox mutation controls. Each copies the compared inputs, applies one mutation, and
    asserts the classifier output changes exactly as pre-committed."""
    base = ROOT / "artifacts/worker-090/f0_vocab_conformance"
    controls, sandbox_root = [], base / "sandbox"
    if sandbox_root.exists():
        shutil.rmtree(sandbox_root)

    def make_box(tag: str) -> Path:
        box = sandbox_root / tag
        for rel in PINNED:
            src, dst = ROOT / rel, box / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        return box

    def find(res, schema, axis):
        for r in res["matrix"]:
            if r["schema"] == schema and r["axis"] == axis:
                return r
        raise KeyError(f"{schema}/{axis}")

    # baseline: unmutated sandbox must reproduce the canonical classifications
    box = make_box("C0_baseline")
    base_res, _ = audit(box)
    canonical, _ = audit(ROOT)
    same = [(r["schema"], r["axis"], r["classification"]) for r in base_res["matrix"]] == \
           [(r["schema"], r["axis"], r["classification"]) for r in canonical["matrix"]]
    controls.append({"id": "C0", "kind": "negative",
                     "mutation": "none (sandbox copy of canonical bytes)",
                     "expected": "identical classification vector to canonical run",
                     "observed": "identical" if same else "DIFFERS", "pass": bool(same)})

    def mutate_and_classify(tag, rel, old, new, check):
        box = make_box(tag)
        p = box / rel
        txt = p.read_text()
        assert old in txt, f"control {tag}: anchor not found in {rel}"
        p.write_text(txt.replace(old, new, 1))
        res, _ = audit(box)
        obs = check(res)
        controls.append({"id": tag, "kind": "sensitivity", "mutation": f"{rel}: {old!r} -> {new!r}",
                         "expected": check.__doc__, "observed": obs,
                         "pass": obs == check.__doc__})

    def expect_unregistered(res):
        """unregistered"""
        return find(res, "F2a", "conclusion_type")["classification"]

    mutate_and_classify("C1", SCHEMAS["F2a"],
                        "conclusion_type: scc_c2_future_inextendibility",
                        "conclusion_type: totally_bogus_token",
                        expect_unregistered)

    def expect_exact(res):
        """exact"""
        return find(res, "F2a", "genericity_kind")["classification"]

    mutate_and_classify("C2", SCHEMAS["F2a"],
                        "kind: residual_comeager", "kind: provisional_baire_residual",
                        expect_exact)

    def expect_exact_conclusion(res):
        """exact"""
        return find(res, "F2a", "conclusion_type")["classification"]

    mutate_and_classify("C3", F0,
                        '      - "strong_cosmic_censorship_C2"\n',
                        '      - "strong_cosmic_censorship_C2"\n'
                        '      - "scc_c2_future_inextendibility"\n',
                        expect_exact_conclusion)

    def expect_unregistered_after_registry_removal(res):
        """unregistered"""
        return find(res, "F1", "genericity_kind")["classification"]

    mutate_and_classify("C4", REGISTRY,
                        '"residual_comeager": [',
                        '"residual_comeager_X": [',
                        expect_unregistered_after_registry_removal)

    def expect_unregistered_after_allowed_removal(res):
        """unregistered"""
        return find(res, "F1", "conclusion_type")["classification"]

    mutate_and_classify("C5", F0,
                        '      - "weak_cosmic_censorship"\n',
                        '',
                        expect_unregistered_after_allowed_removal)

    # C6: pin-drift guard -- the audit's own pin map must change when bytes change
    box = make_box("C6_drift")
    p = box / SCHEMAS["F2a"]
    p.write_text(p.read_text() + "\n# drift\n")
    res, _ = audit(box)
    drifted = res["pins"][SCHEMAS["F2a"]] != canonical["pins"][SCHEMAS["F2a"]]
    controls.append({"id": "C6", "kind": "guard", "mutation": "append one comment byte to F2a",
                     "expected": "pin digest changes", "observed": "changed" if drifted else "same",
                     "pass": bool(drifted)})

    # C7: duplicate-key detector sensitivity
    box = make_box("C7_dupkey")
    p = box / SCHEMAS["F2a"]
    p.write_text("class_id: DUP\n" + p.read_text())
    res_dup, _ = audit(box)
    dups = res_dup["duplicate_top_level_keys"].get("F2a", [])
    controls.append({"id": "C7", "kind": "guard",
                     "mutation": "prepend duplicate top-level class_id key to F2a",
                     "expected": "['class_id']", "observed": json.dumps(dups), "pass": dups == ["class_id"]})

    all_pass = all(c["pass"] for c in controls)
    return {"task_id": "W090-F0-VOCAB-CONFORMANCE-01", "actor": "worker-090",
            "created_at": now(), "controls": controls, "n_controls": len(controls),
            "all_pass": all_pass,
            "note": ("Controls run on copies under artifacts/worker-090/f0_vocab_conformance/sandbox; "
                     "the canonical tree is untouched.")}, all_pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path(__file__).with_name("results.json")))
    ap.add_argument("--controls", default=str(Path(__file__).with_name("controls.json")))
    args = ap.parse_args()

    before = measure(PINNED)
    result, self_ok = audit(ROOT)
    controls, ctrl_ok = run_controls(ROOT)
    after = measure(PINNED)
    result["pins_after"] = after
    result["pin_stable"] = before == after and result["pins"] == before
    result["exit_ok"] = bool(result["pin_stable"] and ctrl_ok)
    if not result["pin_stable"]:
        result["findings"].append({
            "id": "W090-VOCAB-00", "severity": "blocker",
            "statement": "Pin drift during the run; the measurement is void and must be re-run.",
            "instances": sorted(k for k in before if before[k] != after.get(k)),
        })

    Path(args.out).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    Path(args.controls).write_text(json.dumps(controls, indent=2, sort_keys=True) + "\n")
    print(f"pin_stable={result['pin_stable']} controls_all_pass={ctrl_ok} "
          f"exit_ok={result['exit_ok']} f0_self_ok={self_ok}")
    print("summary:", json.dumps(result["summary"], sort_keys=True))
    sys.exit(0 if result["exit_ok"] else 1)


if __name__ == "__main__":
    main()
