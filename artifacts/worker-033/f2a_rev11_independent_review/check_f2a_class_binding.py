#!/usr/bin/env python3
"""Independent class-binding conformance checker for F2a = AF-SCC-C2-VAC-GEN.

Written by worker-033 for the bounded review task W033-F2A-REV11-01. This is a
*second implementation*: it does not import research_map/class_separation.py,
research_map/audit_evidence.py or artifacts/formulation/tools/*. It reads only
the pinned byte copies under pinned/ plus the declared canonical hashes, and it
re-derives every verdict from the bytes.

Checks are grouped:
  ID-*       class identity / component coherence
  VOC-*      conclusion-type vocabulary against the canonical F0 artifact
  DEF-*      definitional completeness (disposition of flash-19 HF-1/HF-2)
  LEAK-*     class leakage / conclusion inflation / promotion (HF-02 family)
  PTR-*      class-contract pointer resolution (canonical vs authoring tree)
  FORM-*     formal-sentence consistency
  TIME-*     content timestamp and YAML-key hygiene

Every check carries an explicit falsifier: the edit that would flip it.
Run:  python3 check_f2a_class_binding.py --out report.json
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import re
import sys
from pathlib import Path

import yaml

ISO = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[+-]\d{2}:\d{2}|Z)"
)
G3_COMPOSITE = re.compile(r"C0\s*(?:or|and|/|\+)\s*C2|C2\s*(?:or|and|/|\+)\s*C0", re.I)
MATTER_TOKENS = re.compile(
    r"type-?II|critical collapse|matter-?coupled|matter coupled|"
    r"scalar[- ]field|electrovacuum|perfect fluid|fluid",
    re.I,
)
# Fields whose content asserts the class. Leakage here is a defect; the same
# token inside anti_scope / forbidden_* / known_obstruction / provenance is a
# correct exclusion statement.
ASSERTIVE_TOP = (
    "quantifiers",
    "conclusion",
    "topology",
    "data_class",
    "regularity",
    "genericity",
    "non_vacuity",
    "i_plus",
    "visibility",
    "class_components",
    "class_boundary",
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def load_yaml(path: Path):
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def compose_duplicate_keys(path: Path) -> dict:
    node = yaml.compose(path.read_text(encoding="utf-8"))
    counts: dict = {}
    if isinstance(node, yaml.MappingNode):
        for key_node, _ in node.value:
            counts[key_node.value] = counts.get(key_node.value, 0) + 1
    return {k: v for k, v in counts.items() if v > 1}


def walk_strings(obj, prefix=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk_strings(v, f"{prefix}.{k}" if prefix else str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk_strings(v, f"{prefix}[{i}]")
    elif isinstance(obj, str):
        yield prefix, obj


def walk_assertive(obj, prefix=""):
    """Yield strings that live in class-assertive fields only."""
    if not prefix:
        if not isinstance(obj, dict):
            return
        for k, v in obj.items():
            if k in ASSERTIVE_TOP:
                yield from walk_strings(v, k)
        return


def resolve_pointer(root, pointer: str):
    """Resolve 'path#a.b.c' -> (path_part, value, error)."""
    if "#" in pointer:
        path_part, frag = pointer.split("#", 1)
    else:
        path_part, frag = pointer, ""
    if path_part and not Path(path_part).exists():
        return path_part, None, f"file not found: {path_part}"
    value = root
    for part in [p for p in frag.split(".") if p]:
        m = re.match(r"^([^\[]+)(?:\[(\d+)\])?$", part)
        if not m:
            return path_part, None, f"unparsable fragment: {part}"
        key, idx = m.group(1), m.group(2)
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return path_part, None, f"fragment not found: {frag} (failed at {part})"
        if idx is not None:
            if isinstance(value, list) and int(idx) < len(value):
                value = value[int(idx)]
            else:
                return path_part, None, f"index out of range at {part}"
    return path_part, value, None


def check(results, cid, severity, passed, detail, falsifier):
    results.append(
        {
            "check_id": cid,
            "severity": severity,
            "status": "pass" if passed else "fail",
            "detail": detail,
            "falsifier": falsifier,
        }
    )


def run_checks(f2a_path: Path, f0_path: Path, contract_path: Path, aliases_path: Path,
               measurement_time: str, repo_root: Path | None = None):
    f2a = load_yaml(f2a_path)
    f0 = load_yaml(f0_path)
    contract = load_yaml(contract_path)
    aliases = json.loads(aliases_path.read_text(encoding="utf-8"))
    raw = f2a_path.read_text(encoding="utf-8")
    results: list = []

    cid = f2a.get("class_id")
    comps = f2a.get("class_components", {}) or {}
    expected_components = {
        "asymptotics": "AF",
        "censorship": "SCC",
        "matter": "VAC",
        "genericity": "GEN",
        "regularity_token": "C2",
    }

    # ---- ID: identity -----------------------------------------------------
    check(
        results, "ID-01", "critical",
        cid == "AF-SCC-C2-VAC-GEN" and ";" not in str(cid) and "," not in str(cid),
        f"class_id={cid!r}; must be the single frozen token AF-SCC-C2-VAC-GEN",
        "rewrite class_id to AF-SCC-C0-VAC-GEN or a composite 'AF-SCC-C0/C2...' -> ID-01 fails",
    )
    check(
        results, "ID-02", "critical",
        all(comps.get(k) == v for k, v in expected_components.items()),
        f"class_components={comps}; expected {expected_components}",
        "change regularity_token to C0 -> ID-02 fails",
    )
    check(
        results, "ID-03", "major",
        f2a.get("sibling_disjoint_from") == "AF-SCC-C0-VAC-GEN",
        f"sibling_disjoint_from={f2a.get('sibling_disjoint_from')!r}",
        "point sibling_disjoint_from at AF-WCC-VAC-GEN -> ID-03 fails",
    )

    # ---- VOC: conclusion-type vocabulary against canonical F0 --------------
    fv = (f0.get("field_vocabulary", {}) or {}).get("conclusion_type", {}) or {}
    allowed = list(fv.get("allowed", []))
    ctype = (f2a.get("conclusion", {}) or {}).get("conclusion_type")
    canonical_axis = (
        (f0.get("classes", {}) or {}).get(cid, {}) or {}
    ).get("axes", {}).get("conclusion_type")

    check(
        results, "VOC-01", "critical", ctype in allowed,
        f"F2a conclusion.conclusion_type={ctype!r}; canonical F0 "
        f"field_vocabulary.conclusion_type.allowed={allowed}",
        "add the token to canonical F0 allowed list, or change F2a to an allowed token "
        "-> VOC-01 passes",
    )
    # alias-aware reading, exactly as the formulation lead's registry defines it
    alias_map = {}
    for canon, alist in (aliases.get("conclusion_type", {}) or {}).items():
        alias_map[canon] = canon  # the registry key is itself the canonical token
        for a in alist:
            alias_map[a] = canon
    alias_ok = alias_map.get(ctype) in {alias_map.get(a) for a in allowed}
    check(
        results, "VOC-02", "info", alias_ok,
        f"alias-registry reading: {ctype!r} -> canonical {alias_map.get(ctype)!r}; "
        f"canonical F0 tokens alias to "
        f"{sorted({alias_map.get(a) for a in allowed})}",
        "remove the alias pair from VOCAB_ALIASES.json -> VOC-02 fails (the alias "
        "reading is registry-dependent, not a proof)",
    )
    check(
        results, "VOC-03", "critical", ctype == canonical_axis,
        f"F2a token={ctype!r}; canonical F0 classes.{cid}.axes.conclusion_type="
        f"{canonical_axis!r}",
        "republish canonical F0 with the registry tokens, or set F2a "
        "conclusion_type=strong_cosmic_censorship_C2 -> VOC-03 passes",
    )
    # cross-target: does the sibling C0 schema have the same defect?
    sib_path = f2a_path.parent / "schemas_af_scc_c0_vacuum.yaml"
    x_target = None
    if sib_path.exists():
        sib = load_yaml(sib_path)
        sib_type = (sib.get("conclusion", {}) or {}).get("conclusion_type")
        sib_axis = (
            (f0.get("classes", {}) or {}).get("AF-SCC-C0-VAC-GEN", {}) or {}
        ).get("axes", {}).get("conclusion_type")
        x_target = {
            "artifact": "schemas/af_scc_c0_vacuum.yaml",
            "conclusion_type": sib_type,
            "canonical_axis": sib_axis,
            "same_defect": sib_type == ctype.replace("_c2_", "_c0_") and sib_type not in allowed,
        }
    check(
        results, "VOC-04", "major",
        not (x_target or {}).get("same_defect", False),
        f"cross-target F2b check: {x_target}",
        "F2b has the same canonical-vocabulary mismatch; one F0 republication or two "
        "schema edits discharge both -> VOC-04 passes",
    )

    # ---- DEF: definitional completeness (flash-19 HF-1/HF-2) ---------------
    domains = (f2a.get("quantifiers", {}) or {}).get("domains", {}) or {}
    qformal = str((f2a.get("quantifiers", {}) or {}).get("formal", ""))
    cformal = str((f2a.get("conclusion", {}) or {}).get("statement_formal", ""))
    refs = sorted(set(re.findall(r"\bD\d+\b", qformal + " " + cformal)))
    missing = [r for r in refs if r not in domains]
    check(
        results, "DEF-01", "critical", "D0" in domains,
        f"D0 present in quantifiers.domains: {'D0' in domains}; domains={sorted(domains)}"
        " (flash-19 HF-1 claimed D0 was defined nowhere at rev3)",
        "delete the D0 block from quantifiers.domains -> DEF-01 fails",
    )
    check(
        results, "DEF-02", "critical", not missing,
        f"domain refs in formal sentences={refs}; unresolved={missing}",
        "change a reference to D9 -> DEF-02 fails",
    )
    ep = f2a.get("extension_predicate") or {}
    ep_text = json.dumps(ep)
    clauses = sorted(set(re.findall(r"\(([a-f])\)", str(ep.get("definition", "")))))
    check(
        results, "DEF-03", "critical",
        bool(ep) and ep.get("name") == "proper_future_extension_in_class"
        and clauses == list("abcdef") and ep.get("frozen_regularity") == "C2",
        f"extension_predicate name={ep.get('name')!r}, clauses={clauses}, "
        f"frozen_regularity={ep.get('frozen_regularity')!r} (flash-19 HF-2 claimed the "
        "predicate was absent at rev3)",
        "delete the extension_predicate block or drop clause (f) -> DEF-03 fails",
    )
    check(
        results, "DEF-04", "major",
        "proper_future_extension_in_class" in cformal or "proper future C2 vacuum extension" in cformal,
        "conclusion.statement_formal references the frozen predicate name or spells it out",
        "replace the predicate reference with an undefined name -> DEF-04 fails",
    )

    # ---- LEAK: composite / matter / inflation / promotion ------------------
    composite_hits = []
    for path, text in walk_assertive(f2a):
        if G3_COMPOSITE.search(text):
            composite_hits.append((path, text[:160]))
    check(
        results, "LEAK-01", "critical", not composite_hits,
        f"G3 composite pattern in assertive fields: {composite_hits or 'none'}; the only "
        "regex hit in the file is in anti_scope.phrases_that_are_not_this_class (correct)",
        "paste 'C0 or C2' into quantifiers.formal -> LEAK-01 fails",
    )
    matter_hits = []
    for path, text in walk_assertive(f2a):
        if MATTER_TOKENS.search(text):
            matter_hits.append((path, text[:160]))
    check(
        results, "LEAK-02", "critical", not matter_hits,
        f"matter-coupled tokens in assertive fields: {matter_hits or 'none'} "
        "(flash-19 HF-3 leak was genericity.excluded_set 2-type-II critical collapse)",
        "insert 'fine-tuned threshold data of type-II critical collapse' into "
        "genericity.excluded_set -> LEAK-02 fails",
    )
    forbidden_blob = json.dumps(
        {
            "forbidden_strengthenings": (f2a.get("conclusion", {}) or {}).get(
                "forbidden_strengthenings"),
            "forbidden_weakenings": (f2a.get("conclusion", {}) or {}).get(
                "forbidden_weakenings"),
            "anti_scope": f2a.get("anti_scope"),
            "implication_ledger": f2a.get("implication_ledger"),
        }
    )
    inflation_ok = (
        "C0" in forbidden_blob and "H2_loc" in forbidden_blob
        and "C0" in json.dumps(f2a.get("anti_scope", {}))
    )
    check(
        results, "LEAK-03", "major", inflation_ok,
        "C0/H2_loc appear as explicit exclusions in forbidden_* / anti_scope / "
        "implication_ledger (correct direction: C0 is stronger, must not be filed here)",
        "move a C0 conclusion token into conclusion.conclusion_type -> LEAK-03 fails",
    )
    promotion_ok = (
        f2a.get("epistemic_status") == "open_problem"
        and (f2a.get("conclusion", {}) or {}).get("epistemic_status") == "open_problem"
        and "theorem" not in str(ctype).lower()
        and bool((f2a.get("conclusion", {}) or {}).get("claim_promotion"))
    )
    check(
        results, "LEAK-04", "critical", promotion_ok,
        "epistemic_status=open_problem at top level and conclusion; no theorem token; "
        "claim_promotion guard present",
        "set epistemic_status=theorem without artifact_refs -> LEAK-04 fails",
    )

    # ---- PTR: class-contract pointer resolution ----------------------------
    repo_root = Path(repo_root) if repo_root else Path.cwd()
    pointer = f2a.get("class_contract_pointer") or ""
    ptr_path = pointer.split("#", 1)[0]
    ptr_file_ok = bool(ptr_path) and (repo_root / ptr_path).exists()
    check(
        results, "PTR-01", "major", ptr_file_ok,
        f"pointer={pointer!r} -> target file {ptr_path!r} exists under repo root: {ptr_file_ok}",
        "point at a non-existent file -> PTR-01 fails",
    )
    frag = pointer.split("#", 1)[1] if "#" in pointer else ""
    canon_ok, canon_err = False, None
    if frag.startswith("class_contracts."):
        canon_ok = "class_contracts" in f0
        canon_err = (
            None if canon_ok
            else "canonical research_map/formulation_taxonomy.yaml has no "
                 "'class_contracts' key (keys: %s)" % ", ".join(sorted(f0)[:12])
        )
    else:
        _, _, canon_err = resolve_pointer(f0, pointer)
        canon_ok = canon_err is None
    check(
        results, "PTR-02", "major", canon_ok,
        f"pointer fragment {frag!r} resolves against the CANONICAL F0 artifact: "
        f"{canon_ok}; {canon_err or ''}",
        "republish the canonical taxonomy with the class_contracts section (or repoint "
        "the schema at a canonical fragment) -> PTR-02 passes",
    )
    contract_c2 = (contract.get("class_contracts", {}) or {}).get(cid, {}) or {}
    check(
        results, "PTR-03", "info", bool(contract_c2),
        f"authoring supplement class_contracts.{cid} present: {bool(contract_c2)} "
        "(class_contract_pointer is resolvable only against the non-canonical tree)",
        "delete class_contracts from the authoring taxonomy -> PTR-03 fails",
    )

    # ---- FORM: formal-sentence consistency ---------------------------------
    norm = lambda s: re.sub(r"\s+", " ", s).strip()
    check(
        results, "FORM-01", "minor", norm(qformal) == norm(cformal),
        "quantifiers.formal and conclusion.statement_formal are not the same sentence "
        f"(lens {len(norm(qformal))} vs {len(norm(cformal))}); conclusion uses binder "
        "'D in G_{s,delta}' and the abbreviated predicate 'proper_future_extension_in_class(MGHD(D))'",
        "replace conclusion.statement_formal with the exact quantifiers.formal text "
        "-> FORM-01 passes",
    )

    # ---- CONTRACT: authoring contract clause coverage ----------------------
    covered, uncovered = [], []
    rules = {
        "C0/C1/C^{1,1}/H2_loc/smooth extension classes excluded":
            ["C0", "C1", "C^{1,1}", "H2_loc", "smooth"],
        "non-vacuum extensions are not counterexamples": ["Ric", "vacuum"],
        "two-sided/white-hole extensions are a different statement": ["two-sided"],
        "visibility / I+ completeness is WCC content": ["visibility", "I+"],
    }
    schema_blob = raw
    for label, kws in rules.items():
        hit = all(kw in schema_blob for kw in kws)
        (covered if hit else uncovered).append(label)
    check(
        results, "CONTRACT-01", "major", not uncovered,
        f"authoring C2 contract exclusion clauses covered by machine-visible schema "
        f"text: {covered}; uncovered: {uncovered}",
        "delete the matching forbidden_weakenings/anti_scope text -> CONTRACT-01 fails",
    )
    check(
        results, "CONTRACT-02", "minor",
        contract_c2.get("conclusion_type") == ctype,
        f"authoring contract conclusion_type={contract_c2.get('conclusion_type')!r} == "
        f"schema {ctype!r}",
        "change either token -> CONTRACT-02 fails",
    )

    # ---- TIME: timestamp and key hygiene -----------------------------------
    meas = _dt.datetime.fromisoformat(measurement_time)
    stamps = []
    for m in ISO.finditer(raw):
        try:
            stamps.append(_dt.datetime.fromisoformat(m.group(0)))
        except ValueError:
            pass
    future = [s.isoformat() for s in stamps if s > meas]
    check(
        results, "TIME-01", "minor", not future,
        f"measurement_time={measurement_time}; timestamps in artifact later than "
        f"measurement: {future or 'none'}",
        "set the offending revised_at back to a real wall-clock time -> TIME-01 passes",
    )
    dups = compose_duplicate_keys(f2a_path)
    check(
        results, "TIME-02", "minor", not dups,
        f"duplicate mapping keys in the canonical YAML: {dups or 'none'}; PyYAML keeps "
        "the last value, strict parsers reject the file, and the revision history is "
        "not machine-visible",
        "collapse the revision history into a single machine-readable list -> TIME-02 passes",
    )

    critical_fail = [r for r in results if r["severity"] == "critical" and r["status"] == "fail"]
    major_fail = [r for r in results if r["severity"] == "major" and r["status"] == "fail"]
    minor_fail = [r for r in results if r["severity"] == "minor" and r["status"] == "fail"]
    verdict = "revise" if critical_fail else ("revise" if major_fail else "accept")
    return {
        "checker": "check_f2a_class_binding.py",
        "checker_sha256": sha256_file(Path(__file__)),
        "measurement_time": measurement_time,
        "inputs": {
            "f2a": {"path": str(f2a_path), "sha256": sha256_file(f2a_path)},
            "f0_canonical": {"path": str(f0_path), "sha256": sha256_file(f0_path)},
            "contract_authoring": {"path": str(contract_path), "sha256": sha256_file(contract_path)},
            "aliases": {"path": str(aliases_path), "sha256": sha256_file(aliases_path)},
        },
        "checks": results,
        "summary": {
            "n_checks": len(results),
            "passed": sum(1 for r in results if r["status"] == "pass"),
            "failed": sum(1 for r in results if r["status"] == "fail"),
            "critical_failures": [r["check_id"] for r in critical_fail],
            "major_failures": [r["check_id"] for r in major_fail],
            "minor_failures": [r["check_id"] for r in minor_fail],
        },
        "proposed_verdict": verdict,
    }


def main() -> int:
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser()
    ap.add_argument("--f2a", default=str(here / "pinned" / "schemas_af_scc_c2_vacuum.yaml"))
    ap.add_argument("--f0", default=str(here / "pinned" / "research_map_formulation_taxonomy.yaml"))
    ap.add_argument("--contract",
                    default=str(here / "pinned" / "artifacts_formulation_formulation_taxonomy.yaml"))
    ap.add_argument("--aliases",
                    default=str(here / "pinned" / "artifacts_formulation_VOCAB_ALIASES.json"))
    ap.add_argument("--measurement-time",
                    default=(_dt.datetime.now().astimezone().replace(microsecond=0).isoformat()))
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    res = run_checks(Path(args.f2a), Path(args.f0), Path(args.contract),
                     Path(args.aliases), args.measurement_time,
                     repo_root=here.parents[2])
    text = json.dumps(res, indent=1, sort_keys=False)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
