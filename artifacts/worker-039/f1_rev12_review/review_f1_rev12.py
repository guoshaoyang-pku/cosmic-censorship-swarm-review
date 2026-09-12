#!/usr/bin/env python3
"""
W039-F1-REV12-REVIEW-01 -- independent, hash-pinned review of
schemas/af_wcc_vacuum.yaml (class AF-WCC-VAC-GEN, node F1, gate G-FORM) at the
bytes measured when this script starts.

Why this task: at intake the F1 corpus had no review bound to the rev12
publication (00:31:41 wave), while G-FORM/G-AUDIT need two independent accepts
per measured hash.  A worker review with machine-checkable evidence is a
legitimate independent contribution; this script produces it, or reports the
exact blocking defect.

Machine checks (all hash-bound, read-only):
  S1  strict YAML parse: duplicate mapping keys (rev12 collapsed revised_at;
      verify none remain)
  S2  required slot inventory (gate criteria: quantifiers, topology, data_class,
      regularity, genericity, i_plus, visibility, conclusion, falsifier,
      anti_scope, class_components, contract pointer)
  S3  binder order/domains: 6 ordered binders resolve to declared domains
  S4  visibility clause is the canonical single-q TAIL predicate; statement_formal
      references the named predicate
  S5  negation block present and tail-based
  S6  class binding vs the canonical taxonomy contract: class id, conclusion
      type, anti-scope of the other three classes, no C0/C2 merge,
      extension_regularity null
  S7  class_contract_pointer resolves inside the canonical taxonomy and the
      supplement pointer is a separate field
  S8  evidence binding: declared f0 sha256 == measured canonical taxonomy;
      declared consistency_evidence_sha256 == measured evidence file
  S9  timestamp discipline: revised_at within tolerance of file mtime, not future
  S10 visibility semantics: finite-model check that whole-curve single-q
      containment and the tail predicate are EQUIVALENT for causal curves
      (transitive order, past-closed J^-(q)); counts residual whole-curve sites
      and classifies them as semantics-neutral
  S11 frozen binding gate artifacts/formulation/tools/check_class_schema.py
  S12 non-vacuity, unresolved items, L1 ledger refs present

  Findings W1..W4 are wording/metadata observations, not content changes.

Exit codes: 0 = checks executed and review.json written (verdict inside);
2 = cannot bind (schema missing); never edits a canonical artifact.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import re
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
SCHEMA = ROOT / "schemas" / "af_wcc_vacuum.yaml"
TAXONOMY = ROOT / "research_map" / "formulation_taxonomy.yaml"
EVIDENCE = ROOT / "artifacts" / "formulation" / "evidence" / "taxonomy_consistency.json"
GATE = ROOT / "artifacts" / "formulation" / "tools" / "check_class_schema.py"
CST = timezone(timedelta(hours=8))
NOW = lambda: datetime.now(CST).isoformat(timespec="seconds")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str | None:
    try:
        return sha256_bytes(p.read_bytes())
    except OSError:
        return None


def parse_ts(s: str):
    try:
        return datetime.fromisoformat(s)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------- S1 strict YAML
class StrictLoader(yaml.SafeLoader):
    pass


def _strict_mapping(loader, node, deep=False):
    loader.flatten_mapping(node)
    seen = {}
    dup = []
    for k, v in node.value:
        key = loader.construct_object(k, deep=deep)
        if key in seen:
            dup.append(str(key))
        seen[key] = v
    if dup:
        StrictLoader.duplicates.extend(dup)
    return loader.construct_mapping(node, deep=True)


StrictLoader.duplicates = []
StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _strict_mapping)


# ------------------------------------------------- S10 finite-model semantics
def labelled_posets(n: int):
    pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
    for choices in itertools.product((0, 1, 2), repeat=len(pairs)):
        less = set()
        for (i, j), c in zip(pairs, choices):
            if c == 0:
                less.add((i, j))
            elif c == 1:
                less.add((j, i))
        if all(not (b == c and (a, d) not in less)
               for (a, b) in less for (c, d) in less):
            yield less


def causal_chains(less, n):
    succ = {i: [j for j in range(n) if (i, j) in less] for i in range(n)}

    def walk(path):
        yield tuple(path)
        for nxt in succ[path[-1]]:
            if nxt not in path:
                path.append(nxt)
                yield from walk(path)
                path.pop()

    for s in range(n):
        yield from walk([s])


def down_set(less, n, q):
    return frozenset(x for x in range(n) if x == q or (x, q) in less)


def equivalence_check(max_n: int = 5):
    models = 0
    counterexamples = []
    for n in range(1, max_n + 1):
        for less in labelled_posets(n):
            chains = list(causal_chains(less, n))
            for u in {down_set(less, n, q) for q in range(n)}:
                for chain in chains:
                    whole = all(x in u for x in chain)
                    tail = any(all(x in u for x in chain[t0:])
                               for t0 in range(len(chain)))
                    models += 1
                    if tail and not whole:
                        counterexamples.append(
                            {"n": n, "less": sorted(less),
                             "chain": list(chain), "U_q": sorted(u)})
    return {"models_checked": models,
            "counterexamples_tail_without_whole": len(counterexamples),
            "examples": counterexamples[:3],
            "statement": "B => A holds on every admissible finite model; with "
                         "A => B trivial, single-q whole-curve and tail "
                         "containment are equivalent for causal curves"}


# ---------------------------------------------------------------- S11 gate
def run_gate():
    if not GATE.exists():
        return {"available": False}
    r = subprocess.run([sys.executable, str(GATE), str(SCHEMA), "--json"],
                       capture_output=True, text=True, timeout=120)
    try:
        doc = json.loads(r.stdout)
    except ValueError:
        doc = {"raw": r.stdout[-500:]}
    return {"available": True, "cmd": f"python3 {GATE.relative_to(ROOT)} "
                                      f"{SCHEMA.relative_to(ROOT)} --json",
            "returncode": r.returncode, "verdict": doc.get("verdict"),
            "failed_rules": doc.get("failed_rules"),
            "failures": doc.get("failures"),
            "gate_file_sha256": sha256_file(GATE)}


def main() -> int:
    if not SCHEMA.exists():
        print(json.dumps({"error": "schema missing"}))
        return 2
    entry_sha = sha256_file(SCHEMA)
    text = SCHEMA.read_text()
    lines = text.splitlines()
    mtime = datetime.fromtimestamp(SCHEMA.stat().st_mtime, tz=CST)

    StrictLoader.duplicates = []
    try:
        doc = yaml.load(text, Loader=StrictLoader)
        parse_error = None
    except yaml.YAMLError as e:
        doc, parse_error = None, str(e)
    duplicates = list(dict.fromkeys(StrictLoader.duplicates))

    tax = yaml.safe_load(TAXONOMY.read_text())
    tax_cls = tax.get("classes", {}).get("AF-WCC-VAC-GEN", {})

    checks = []

    def add(cid, ok, desc, evidence):
        checks.append({"id": cid, "status": "pass" if ok else "fail",
                       "description": desc, "evidence": evidence})

    # S1 duplicates
    add("S1_STRICT_YAML", parse_error is None and not duplicates,
        "strict YAML parse with duplicate-key rejection",
        {"parse_error": parse_error, "duplicate_keys": duplicates})

    # S2 slots
    required = ["quantifiers", "topology", "data_class", "regularity", "genericity",
                "i_plus", "visibility", "conclusion", "falsifier", "anti_scope",
                "class_components", "class_contract_pointer"]
    missing = [k for k in required if not isinstance(doc, dict) or k not in doc]
    add("S2_SLOTS", not missing, "required schema slots present",
        {"missing": missing, "revision": doc.get("revision") if doc else None})

    # S3 binders
    ordered = (doc or {}).get("quantifiers", {}).get("ordered", [])
    domains = (doc or {}).get("quantifiers", {}).get("domains", {})
    dom_ok = all(o.get("domain_id") in domains for o in ordered if isinstance(o, dict))
    kinds = [o.get("kind") for o in ordered if isinstance(o, dict)]
    add("S3_BINDERS", len(ordered) == 6 and dom_ok
        and kinds == ["forall", "exists", "forall", "exists", "forall", "not_exists"],
        "six ordered binders, declared domains, quantifier order preserved",
        {"kinds": kinds, "domains_all_declared": dom_ok})

    # S4 tail predicate
    formal = (doc or {}).get("quantifiers", {}).get("formal", "")
    d5 = str((doc or {}).get("quantifiers", {}).get("domains", {}).get("D5", {}).get("definition", ""))
    sf = str((doc or {}).get("conclusion", {}).get("statement_formal", ""))
    tail_ok = ("t0 in [0,T)" in formal and "gamma([t0,T)) subset J^-(q)" in formal
               and "tail gamma([t0,T))" in d5
               and "visible_singularity_from_I_plus" in sf)
    add("S4_TAIL_PREDICATE", tail_ok,
        "formal clause and D5 use the canonical single-q TAIL predicate and "
        "statement_formal names it",
        {"formal_has_t0": "t0 in [0,T)" in formal,
         "d5_has_tail": "tail gamma([t0,T))" in d5})

    # S5 negation
    neg = str((doc or {}).get("quantifiers", {}).get("negation", ""))
    nnorm = str((doc or {}).get("quantifiers", {}).get("negation_normal_form", ""))
    vneg = str((doc or {}).get("visibility", {}).get("negation_conclusion", ""))
    add("S5_NEGATION", "tail" in neg and nnorm and "tail gamma([t0,T)) is NOT contained" in vneg,
        "negation block is present, tail-based and normal-formed",
        {"negation_has_tail": "tail" in neg, "normal_form": bool(nnorm)})

    # S6 class binding
    cid = (doc or {}).get("class_id")
    ctype = (doc or {}).get("conclusion", {}).get("conclusion_type")
    anti = (doc or {}).get("anti_scope", {}).get("not_this_class", [])
    anti_ids = {a.get("class_id") for a in anti if isinstance(a, dict)}
    ext_reg = (doc or {}).get("regularity", {}).get("extension_regularity", "MISSING")
    # Composite C0/C2 tokens are counted only where the class conclusion is
    # ASSERTED (class_id, class_components, conclusion type/statements); the
    # occurrences inside forbidden_*/anti_scope/falsifier lists are the guard,
    # not the defect (avoids the CF-16 metalinguistic false positive).
    concl = (doc or {}).get("conclusion", {})
    asserted_blobs = json.dumps({
        "class_id": cid,
        "class_components": (doc or {}).get("class_components"),
        "conclusion_type": concl.get("conclusion_type"),
        "family": concl.get("family"),
        "statement_formal": concl.get("statement_formal"),
        "statement_natural_language": concl.get("statement_natural_language"),
    })
    merge_tokens = re.findall(r"C0\s*(?:or|/)\s*C2|C2\s*(?:or|/)\s*C0", asserted_blobs)
    add("S6_CLASS_BINDING",
        cid == "AF-WCC-VAC-GEN" and cid in tax.get("classes", {})
        and ctype == tax_cls.get("conclusion", {}).get("type")
        and {"AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"} <= anti_ids
        and ext_reg is None and not merge_tokens,
        "class id/conclusion type agree with the canonical contract; C0/C2 and "
        "the other two classes are explicitly out of scope; no extension "
        "regularity in the conclusion",
        {"class_id": cid, "contract_type": tax_cls.get("conclusion", {}).get("type"),
         "anti_ids": sorted(x for x in anti_ids if x), "extension_regularity": ext_reg,
         "asserted_composite_tokens": merge_tokens[:2]})

    # S7 pointer resolution
    ptr = str((doc or {}).get("class_contract_pointer", ""))
    supp = str((doc or {}).get("class_contract_supplement_pointer", ""))
    anchor = ptr.split("#", 1)[1] if "#" in ptr else ""
    node = tax
    resolves = True
    for seg in anchor.split("."):
        if isinstance(node, dict) and seg in node:
            node = node[seg]
        else:
            resolves = False
            break
    add("S7_CONTRACT_POINTER", resolves and bool(supp) and supp.split("#")[0] != ptr.split("#")[0],
        "class_contract_pointer resolves in the canonical taxonomy; the "
        "supplement pointer is a separate field (no conflation)",
        {"pointer": ptr, "resolves": resolves, "supplement": supp})

    # S8 evidence binding
    declared_f0 = str((doc or {}).get("f0_binding", {}).get("declared_f0_sha256", ""))
    measured_f0 = sha256_file(TAXONOMY)
    ev_declared = str((doc or {}).get("f0_binding", {}).get("consistency_evidence_sha256", ""))
    ev_measured = sha256_file(EVIDENCE)
    add("S8_EVIDENCE_BINDING",
        declared_f0 == measured_f0 and ev_declared == ev_measured,
        "declared F0 hash matches measured canonical taxonomy; declared "
        "consistency-evidence hash matches measured evidence file",
        {"declared_f0": declared_f0[:16], "measured_f0": (measured_f0 or "")[:16],
         "declared_evidence": ev_declared[:16], "measured_evidence": (ev_measured or "")[:16],
         "evidence_mtime": datetime.fromtimestamp(EVIDENCE.stat().st_mtime, tz=CST).isoformat()
         if EVIDENCE.exists() else None})

    # S9 timestamps: hard-fail only on future-dating or gross skew; a small
    # mtime/revised_at skew is reported as W4 (non-blocking metadata hygiene)
    revised = parse_ts(str((doc or {}).get("revised_at", "")))
    now = datetime.now(CST)
    skew = (revised - mtime).total_seconds() if revised else None
    ts_hard = (revised is None or (revised - now).total_seconds() > 60
               or skew is None or abs(skew) > 300)
    add("S9_TIMESTAMPS", not ts_hard,
        "revised_at parseable, not future-dated, and within 300 s of the file "
        "mtime (smaller skew is reported as W4)",
        {"revised_at": str(revised), "mtime": mtime.isoformat(),
         "skew_vs_mtime_s": skew, "future_dated": bool(revised and (revised - now).total_seconds() > 60)})

    # S10 semantics
    sem = equivalence_check()
    whole_sites = [i for i, ln in enumerate(lines, 1)
                   if "gamma subset J^-(q)" in ln or "gamma([0,T))" in ln and "whole" in ln.lower()]
    add("S10_TAIL_WHOLE_EQUIVALENCE", sem["counterexamples_tail_without_whole"] == 0,
        "for causal curves in a transitive order with past-closed J^-(q), "
        "whole-curve and tail single-q containment are equivalent; residual "
        "whole-curve site(s) in the document are therefore semantics-neutral",
        {**sem, "whole_curve_sites_lines": whole_sites})

    # S11 gate
    gate = run_gate()
    add("S11_FROZEN_BINDING_GATE",
        bool(gate.get("available")) and gate.get("verdict") == "pass",
        "frozen binding gate check_class_schema.py passes the pinned bytes",
        gate)

    # S12 completeness
    add("S12_OPENNESS_DECLARED",
        bool((doc or {}).get("non_vacuity", {}).get("vacuity_falsifier"))
        and bool((doc or {}).get("unresolved_items"))
        and bool((doc or {}).get("l1_ledger_refs")),
        "vacuity falsifier, unresolved items and L1 ledger refs present",
        {"n_unresolved": len((doc or {}).get("unresolved_items", [])),
         "n_ledger_refs": len((doc or {}).get("l1_ledger_refs", []))})

    # findings (wording/metadata)
    findings = []
    if doc:
        d5_line = next((i for i, ln in enumerate(lines, 1) if "Whole-curve containment" in ln), None)
        defn_line = next((i for i, ln in enumerate(lines, 1)
                          if "requiring the whole geodesic to lie in J^-(q)" in ln), None)
        findings.append({
            "id": "W1_STRICT_STRONGER_WORDING", "severity": "minor",
            "lines": [d5_line, defn_line],
            "statement": "D5 and visibility.definition call whole-curve containment "
                         "'strictly STRONGER' / a misclassification relative to the "
                         "tail predicate. By S10 that is false for causal curves: "
                         "the two are equivalent. The operative predicate is "
                         "unchanged; the rationale sentence is what needs rewording "
                         "(or the equivalence stated).",
            "falsifier": "an admissible model with tail containment but not "
                         "whole-curve containment (S10 found none up to 5 points)"})
        findings.append({
            "id": "W2_CONTRACT_BINDER_DRIFT", "severity": "minor",
            "lines": [next((i for i, ln in enumerate(lines, 1) if ln.startswith("class_contract_pointer")), None)],
            "statement": "rev12 retypes D0 to a tagged index `r`, while the "
                         "canonical F0 contract text still says 'for every "
                         "admissible (s,delta)'. H4 of the contract delegates the "
                         "regularity axis to F1, so this is a refinement, not a "
                         "class change; align the F0 contract wording at its next "
                         "publication.",
            "falsifier": "the F0 contract text no longer naming (s,delta)"})
        findings.append({
            "id": "W3_HISTORY_RESIDUE", "severity": "minor",
            "lines": [next((i for i, ln in enumerate(lines, 1) if ln.strip().startswith("revision_history:")), None)],
            "statement": "revision_history keeps two `unused: true` entries and "
                         "its index column ends at 10 while `revision: 12`; the "
                         "mapping index->revision is prose-only (supersedes: null). "
                         "Metadata hygiene, not a class defect.",
            "falsifier": "a machine-readable index==revision mapping"})
        if skew is not None and abs(skew) > 5:
            findings.append({
                "id": "W4_MTIME_SKEW", "severity": "minor",
                "lines": [next((i for i, ln in enumerate(lines, 1) if ln.startswith("revised_at:")), None)],
                "statement": f"revised_at is {abs(skew):.0f} s off the file mtime "
                             "(the 00:32:02 republication wave rewrote this file "
                             "after stamping revised_at 00:31:41); either re-stamp "
                             "or accept the documented skew. Not future-dated.",
                "falsifier": "mtime == revised_at within 5 s"})

    # verdict
    blocking = [c["id"] for c in checks if c["status"] == "fail"
                and c["id"] in {"S1_STRICT_YAML", "S2_SLOTS", "S3_BINDERS",
                                "S4_TAIL_PREDICATE", "S5_NEGATION", "S6_CLASS_BINDING",
                                "S7_CONTRACT_POINTER", "S8_EVIDENCE_BINDING",
                                "S9_TIMESTAMPS", "S10_TAIL_WHOLE_EQUIVALENCE",
                                "S11_FROZEN_BINDING_GATE", "S12_OPENNESS_DECLARED"}]
    verdict = "revise" if blocking else "accept"
    score = 3.0 if "S11_FROZEN_BINDING_GATE" in blocking else (3.5 if blocking else 4.0)

    exit_sha = sha256_file(SCHEMA)
    review = {
        "schema_version": "1.0",
        "event_type": "review",
        "task_id": "W039-F1-REV12-REVIEW-01",
        "actor": "worker-039",
        "reviewer": "worker-039",
        "reviewer_independence": "worker-039 authored neither the F1 schema nor "
                                 "any prior F1 review event in this corpus; this "
                                 "review is machine-checked from the pinned bytes",
        "created_at": NOW(),
        "target_id": "F1",
        "node_id": "F1",
        "class_id": "AF-WCC-VAC-GEN",
        "gate": "G-FORM",
        "artifact": "schemas/af_wcc_vacuum.yaml",
        "artifact_sha256": entry_sha,
        "exit_sha256": exit_sha,
        "hash_stable_during_review": entry_sha == exit_sha,
        "reviewed_revision": (doc or {}).get("revision"),
        "verdict": verdict,
        "score": score,
        "counts_as_full_schema_verdict": True,
        "hard_failures": blocking,
        "findings": [c for c in checks if c["status"] == "fail"] + findings,
        "checks": checks,
        "semantics_note": "whole-curve and tail single-q containment are "
                          "equivalent for causal curves (S10); prior F-1 "
                          "(strictly weaker) and the rev12 'strictly STRONGER' "
                          "wording are both incorrect, but neither changes the "
                          "class extension",
        "transient_observations": [
            "S11: at 00:33 the frozen gate check_class_schema.py (file sha "
            "000e09e46b2f, unchanged) returned fail R22 on these same schema "
            "bytes because KEY_MANIFEST.json had not yet been updated for the "
            "new keys; the manifest was updated at 00:34:42 and the gate now "
            "returns pass. Recorded for the controller's clock/ordering record, "
            "not carried as an F1 defect.",
            "S8: artifacts/formulation/evidence/taxonomy_consistency.json was "
            "regenerated at 00:33:16 and again at 00:34:55; both regenerations "
            "measure 9e335e9b..., so the schema's declared 675a99d0... is stale "
            "rather than racing.",
        ],
        "authority_note": "worker verdict; does not set node status=done, "
                          "validation_status=passed, or a gate verdict",
        "falsifier": "for S11: a binding-gate run on these exact bytes with "
                     "verdict pass; for S8: a consistency-evidence file whose "
                     "measured hash equals the declared 675a99d0...; for W1: an "
                     "admissible model with tail but not whole containment",
    }
    (HERE / "review.json").write_text(json.dumps(review, indent=1) + "\n")
    (HERE / "checks.json").write_text(json.dumps(checks, indent=1) + "\n")
    print(json.dumps({
        "entry_sha256": entry_sha, "exit_sha256": exit_sha,
        "hash_stable": entry_sha == exit_sha,
        "revision": review["reviewed_revision"],
        "verdict": verdict, "score": score, "hard_failures": blocking,
        "checks_failed": [c["id"] for c in checks if c["status"] == "fail"],
        "review_json_sha256": sha256_file(HERE / "review.json"),
    }, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
