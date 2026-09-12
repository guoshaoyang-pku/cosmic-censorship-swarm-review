#!/usr/bin/env python3
"""Declared checker for the F0 genericity axis vs the class conclusion (CF-21).

WHY THIS EXISTS
---------------
Controller finding CF-21 (pass 05, 2026-09-12T00:48:44+08:00) records that the
AF-WCC-SCALAR-SPH class has `axes.genericity_kind: unresolved` /
`genericity_value_status: unresolved_pending_L1` while its rev5 conclusion
quantifies over "a comeager set G of data", and that four reviewers split on
whether that is blocking: "No declared checker compares the field, so the
suites pass either way."  This script is that declared checker.  It is
advisory worker tooling: it emits evidence, never a gate verdict.

DECLARED RULES (all machine-decidable on the two frozen input shapes)
--------------------------------------------------------------------
Inputs (read-only):
  * research_map/formulation_taxonomy.yaml       (F0 declared taxonomy)
  * schemas/af_wcc_vacuum.yaml                   (F1)
  * schemas/af_scc_c2_vacuum.yaml                (F2a)
  * schemas/af_scc_c0_vacuum.yaml                (F2b)
  * artifacts/formulation/VOCAB_ALIASES.json     (token aliases)

G1  (hard) every class declares axes.genericity_kind from the taxonomy's own
    field_vocabulary.genericity_kind.allowed list (or a token that resolves to
    an allowed token through VOCAB_ALIASES.json).
G1b (soft) the taxonomy's own field rule says a generic-quantified claim must
    name genericity_kind AND genericity_topology; F0 carries no per-class
    genericity_topology field.  Reported as advisory, discharged in the binding
    schemas for the three owned classes and nowhere for the fourth.
G2  (hard) a class whose canonical genericity_kind is `unresolved` may not
    carry a conclusion that asserts a specific genericity quantifier
    (comeager/residual, full measure, dense open) unless the conclusion is
    explicitly marked provisional/blocked.
G3  (hard) quantifier-family match: every specific quantifier token asserted in
    the conclusion must belong to the family of the class's canonical kind.
G4  (hard) bare "generic data/set/family" wording is not machine-readable (the
    taxonomy's own rule); a conclusion using it must also name a specific
    quantifier token.
G5  (hard) if a hypothesis is flagged `unresolved: true` and its text states the
    genericity notion must be named before a claim is filed, the class may not
    carry a specific-quantifier conclusion unless the class records a
    machine-readable claim block (`claim_status: blocked_by_unresolved_hypothesis`
    or `conclusion.provisional: true`).
G6  (hard) provisional values must be discharged: a class whose canonical kind
    is not `unresolved` must have exactly one binding schema (F1/F2a/F2b) whose
    genericity.kind resolves to the same canonical kind.
S1  (hard) each schema's genericity.kind is present and resolves via the alias
    table.
S2  (hard) each schema's class_id is one of the four frozen class ids.
S3  (hard) schema canonical kind == taxonomy canonical kind for the same class.
S4  (soft) each schema names topology_or_measure and generic_set.

CONTROLS
--------
The checker mutates copies in memory (no frozen byte is written) and asserts a
declared expected verdict for each mutant.  Exit code is 0 only when every
control behaves as declared (fail-closed self-test), 3 on input drift, 2 on a
control deviation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    import yaml
except Exception as exc:  # pragma: no cover
    print(json.dumps({"error": f"pyyaml unavailable: {exc}"}))
    sys.exit(4)

CST = timezone(timedelta(hours=8))
FROZEN_CLASSES = [
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
]
TAXONOMY = "research_map/formulation_taxonomy.yaml"
SCHEMAS = [
    "schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
]
ALIASES = "artifacts/formulation/VOCAB_ALIASES.json"

QUANTIFIER_TOKENS = {
    "residual_comeager": [
        r"\bcomeager\b", r"\bco-meager\b", r"\bresidual\b", r"\bBaire\b",
    ],
    "full_measure": [
        r"\bfull[-\s]measure\b", r"\bmeasure[-\s]one\b",
    ],
    "open_dense_escape": [
        r"\bdense[-\s]open\b", r"\bopen[-\s]dense\b",
    ],
}
BARE_GENERIC = re.compile(r"\bgeneric\s+(?:data|set|family|initial\s+data)\b", re.I)
UNRESOLVED_CLAIM_TEXT = re.compile(
    r"must be named|before any claim|unresolved|provisional", re.I
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now_iso() -> str:
    return datetime.now(CST).replace(microsecond=0).isoformat()


def load_alias_table(root: Path) -> dict:
    raw = json.loads((root / ALIASES).read_text())
    table = raw.get("genericity_kind", {})
    alias2canon = {}
    for canon, aliases in table.items():
        alias2canon[canon] = canon
        for a in aliases:
            alias2canon[a] = canon
    return alias2canon


def canon_kind(kind, alias2canon: dict):
    if not isinstance(kind, str):
        return None
    return alias2canon.get(kind.strip())


def asserted_tokens(text: str) -> list:
    found = []
    for canon, pats in QUANTIFIER_TOKENS.items():
        for pat in pats:
            if re.search(pat, text, re.I):
                found.append((canon, pat))
                break
    return found


def find_line(raw: str, needle: str):
    idx = raw.find(needle)
    if idx < 0:
        return None
    return raw.count("\n", 0, idx) + 1


def finding(rule, severity, cls, message, evidence, falsifier=None):
    f = {
        "rule": rule,
        "severity": severity,
        "class_id": cls,
        "message": message,
        "evidence_refs": evidence,
    }
    if falsifier:
        f["falsifier"] = falsifier
    return f


def check_taxonomy(doc: dict, alias2canon: dict, raw: str, taxonomy_sha: str,
                   schema_docs: dict, schema_shas: dict) -> list:
    out = []
    classes = (doc or {}).get("classes") or {}
    vocab = (((doc or {}).get("field_vocabulary") or {}).get("genericity_kind") or {}).get("allowed") or []
    if not isinstance(classes, dict) or not classes:
        return [finding("G0", "hard", None,
                        "no top-level `classes` mapping: cannot evaluate the genericity axis",
                        [f"{TAXONOMY}#{taxonomy_sha[:12]}"])]

    # S2: schema class ids
    for path, sdoc in schema_docs.items():
        cid = (sdoc or {}).get("class_id")
        if cid not in FROZEN_CLASSES:
            out.append(finding("S2", "hard", cid,
                               f"schema class_id {cid!r} is not one of the four frozen class ids",
                               [f"{path}#{schema_shas[path][:12]}"]))

    for cid in FROZEN_CLASSES:
        cls = classes.get(cid)
        if not isinstance(cls, dict):
            out.append(finding("G0", "hard", cid,
                               "class id from the frozen set is absent from classes{}",
                               [f"{TAXONOMY}#{taxonomy_sha[:12]}"]))
            continue
        axes = cls.get("axes") or {}
        kind_raw = axes.get("genericity_kind")
        status = cls.get("genericity_value_status")
        conclusion = cls.get("conclusion") or {}
        ctext = str(conclusion.get("text") or "")
        ctype = conclusion.get("type")
        cref = [f"{TAXONOMY}#{taxonomy_sha[:12]}",
                f"{TAXONOMY}:classes.{cid}.axes.genericity_kind",
                f"{TAXONOMY}:classes.{cid}.conclusion.text"]

        # G1: kind present + resolvable
        if kind_raw is None:
            out.append(finding("G1", "hard", cid,
                               "axes.genericity_kind is absent; the class's genericity axis is unnamed",
                               cref,
                               "Add a token from field_vocabulary.genericity_kind.allowed and re-run."))
            canon = None
        else:
            canon = canon_kind(kind_raw, alias2canon)
            if kind_raw not in vocab and canon is None:
                out.append(finding("G1", "hard", cid,
                                   f"genericity_kind {kind_raw!r} is neither in the taxonomy's allowed "
                                   f"list {vocab} nor an alias in VOCAB_ALIASES.json",
                                   cref,
                                   "Provide an allowed token or register the alias; re-run."))
        if not status:
            out.append(finding("G1", "hard", cid,
                               "genericity_value_status is absent",
                               cref))

        # G1b: per-class genericity_topology (soft; discharged by the schemas)
        if "genericity_topology" not in axes:
            out.append(finding(
                "G1b", "soft", cid,
                "no per-class genericity_topology field in F0 (the taxonomy's own field rule requires "
                "a generic-quantified claim to name genericity_kind AND genericity_topology); the "
                "topology lives in the binding schema for owned classes",
                cref))

        # tokens asserted in the conclusion
        toks = asserted_tokens(ctext)
        tok_families = {t[0] for t in toks}
        token_str = ", ".join(sorted(tok_families)) or "none"

        # G4: bare generic wording without a specific quantifier
        if BARE_GENERIC.search(ctext) and not tok_families:
            out.append(finding("G4", "hard", cid,
                               "conclusion uses bare 'generic data/set' wording with no specific "
                               "genericity quantifier token (the taxonomy rule: 'generic' alone is "
                               "not a machine-readable value)",
                               cref,
                               "Name a specific quantifier token in the conclusion and re-run."))

        # G2: unresolved kind may not carry a specific-quantifier conclusion
        if canon == "unresolved" or (isinstance(kind_raw, str) and kind_raw.startswith("unresolved")):
            if toks:
                out.append(finding(
                    "G2", "hard", cid,
                    f"genericity_kind is unresolved ({kind_raw!r}) but the conclusion asserts a "
                    f"specific genericity quantifier ({token_str}); the class's own conclusion field "
                    f"carries no provisional/blocked marker",
                    cref + [f"{TAXONOMY}:classes.{cid}.genericity_value_status"],
                    "Either name the kind (a concrete or provisional_* token) or mark the "
                    "conclusion provisional/blocked; re-run."))
        # G3: family match when the kind resolves
        elif canon is not None and toks and canon not in tok_families:
            out.append(finding(
                "G3", "hard", cid,
                f"conclusion asserts quantifier family {token_str} but the declared kind resolves "
                f"to {canon}; a quantifier may not be stronger/different from the class's own axis",
                cref,
                "Repair either the axis or the conclusion so the families match; re-run."))

        # G5: unresolved hypothesis text vs filed claim
        unlabeled = []
        for hyp in cls.get("hypotheses") or []:
            if not isinstance(hyp, dict):
                continue
            if hyp.get("unresolved") and re.search(r"genericity", str(hyp.get("text", "")), re.I) \
                    and UNRESOLVED_CLAIM_TEXT.search(str(hyp.get("text", ""))):
                unlabeled.append(hyp.get("id") or "?")
        blocked = (
            cls.get("claim_status") == "blocked_by_unresolved_hypothesis"
            or conclusion.get("provisional") is True
            or conclusion.get("claim_status") == "blocked_by_unresolved_hypothesis"
        )
        if unlabeled and toks and not blocked:
            h4_line = find_line(raw, "must be named before any claim is filed")
            out.append(finding(
                "G5", "hard", cid,
                f"hypothesis(es) {unlabeled} flagged unresolved and state the genericity notion must "
                f"be named before a claim is filed, yet the class carries a specific-quantifier "
                f"conclusion and records no machine-readable claim block",
                cref + ([f"{TAXONOMY}:{h4_line}"] if h4_line else []),
                "Clear the unresolved flag in a revision, or set conclusion.provisional/claim_status "
                "so the block is machine-readable; re-run."))

        # G6: provisional discharge by a binding schema
        if canon is not None and canon != "unresolved":
            bound = [p for p, sdoc in schema_docs.items()
                     if (sdoc or {}).get("class_id") == cid
                     and canon_kind(((sdoc or {}).get("genericity") or {}).get("kind"), alias2canon) == canon]
            if len(bound) != 1:
                out.append(finding(
                    "G6", "hard", cid,
                    f"canonical kind {canon} has {len(bound)} binding schema(s) resolving to the same "
                    f"kind; provisional values must be discharged by exactly one F-node schema",
                    cref + [f"{p}#{schema_shas[p][:12]}" for p in SCHEMAS],
                    "Publish/repair the binding schema for this class and re-run."))

    # schema-side rules
    for cid in FROZEN_CLASSES:
        for path in SCHEMAS:
            sdoc = schema_docs.get(path) or {}
            if sdoc.get("class_id") != cid:
                continue
            sref = [f"{path}#{schema_shas[path][:12]}",
                    f"{path}:genericity.kind"]
            g = sdoc.get("genericity") or {}
            skind = g.get("kind")
            scanon = canon_kind(skind, alias2canon)
            if skind is None or scanon is None:
                out.append(finding("S1", "hard", cid,
                                   f"schema genericity.kind {skind!r} missing or not resolvable via "
                                   f"VOCAB_ALIASES.json",
                                   sref))
                continue
            tcanon = canon_kind(((classes.get(cid) or {}).get("axes") or {}).get("genericity_kind"),
                                alias2canon)
            if tcanon is not None and tcanon != scanon:
                out.append(finding("S3", "hard", cid,
                                   f"schema kind {skind!r} resolves to {scanon} but the taxonomy class "
                                   f"kind resolves to {tcanon}",
                                   sref + [f"{TAXONOMY}:classes.{cid}.axes.genericity_kind"]))
            if not g.get("topology_or_measure") or not g.get("generic_set"):
                out.append(finding("S4", "soft", cid,
                                   "schema does not name topology_or_measure and generic_set",
                                   sref))
    return out


def verdict_of(findings) -> str:
    return "FAIL" if any(f["severity"] == "hard" for f in findings) else "PASS"


def per_class(findings) -> dict:
    out = {}
    for cid in FROZEN_CLASSES:
        rows = [f for f in findings if f["class_id"] == cid]
        out[cid] = {
            "verdict": "FAIL" if any(r["severity"] == "hard" for r in rows) else "PASS",
            "hard": [r["rule"] for r in rows if r["severity"] == "hard"],
            "soft": [r["rule"] for r in rows if r["severity"] == "soft"],
        }
    return out


def clone(x):
    return json.loads(json.dumps(x))


def controls(tax, schemas, alias2canon, raw, tax_sha, schema_shas):
    """In-memory mutants; each declares its expected per-class / overall verdict."""
    results = []

    def run(t, s):
        sc = {p: (s.get(p) or {}) for p in s}
        sc_sha = {p: schema_shas.get(p, "0" * 64) for p in s}
        f = check_taxonomy(t, alias2canon, raw, tax_sha, sc, sc_sha)
        return f, verdict_of(f), per_class(f)

    # C01 positive control: a real repair of the scalar class (named kind + cleared H4 +
    #      a binding schema) must PASS everywhere.
    t = clone(tax)
    sc = clone(schemas)
    sp = t["classes"]["AF-WCC-SCALAR-SPH"]
    sp["axes"]["genericity_kind"] = "residual_comeager"
    sp["genericity_value_status"] = "frozen_owned_by_F0"
    for hyp in sp.get("hypotheses", []):
        if isinstance(hyp, dict) and hyp.get("unresolved") and "genericity" in str(hyp.get("text", "")).lower():
            hyp["unresolved"] = False
            hyp["text"] = "Genericity notion: residual/comeager on the symmetry-reduced data space (repaired)."
    sc["schemas/af_wcc_scalar_sph.yaml"] = {
        "class_id": "AF-WCC-SCALAR-SPH",
        "genericity": {
            "kind": "residual_comeager",
            "topology_or_measure": "subspace topology on the symmetry-reduced data space",
            "generic_set": "G = countable intersection of open dense subsets; complement meager",
        },
    }
    f, v, pc = run(t, sc)
    results.append({
        "control_id": "C01",
        "description": "repaired scalar class (named kind, H4 flag cleared, binding schema added)",
        "expected_overall": "PASS",
        "observed_overall": v,
        "observed_hard": [r["rule"] + ":" + str(r["class_id"]) for r in f if r["severity"] == "hard"],
        "status": "PASS" if v == "PASS" else "FAIL",
        "note": ("binding schema for the scalar class supplied in-memory because no F-node "
                 "owns the class in the current map"),
    })

    # C02 cosmetic repair only: rename the axis, leave H4 unresolved and no schema.
    t = clone(tax)
    sp = t["classes"]["AF-WCC-SCALAR-SPH"]
    sp["axes"]["genericity_kind"] = "provisional_baire_residual"
    sp["genericity_value_status"] = "provisional_owned_by_F0"
    f, v, pc = run(t, schemas)
    rules = sorted({r["rule"] for r in f if r["severity"] == "hard" and r["class_id"] == "AF-WCC-SCALAR-SPH"})
    ok = v == "FAIL" and "G5" in rules and "G6" in rules
    results.append({
        "control_id": "C02",
        "description": "cosmetic rename of the scalar axis (H4 still unresolved, still unowned)",
        "expected_overall": "FAIL",
        "expected_rules": ["G5", "G6"],
        "observed_overall": v,
        "observed_rules": rules,
        "status": "PASS" if ok else "FAIL",
    })

    # C03 quantifier mismatch inside an otherwise healthy class.
    t = clone(tax)
    c = t["classes"]["AF-WCC-VAC-GEN"]["conclusion"]
    c["text"] = c["text"].replace("comeager", "full measure")
    f, v, pc = run(t, schemas)
    rules = sorted({r["rule"] for r in f if r["severity"] == "hard" and r["class_id"] == "AF-WCC-VAC-GEN"})
    ok = v == "FAIL" and "G3" in rules
    results.append({
        "control_id": "C03",
        "description": "F1 conclusion says full measure while the axis/schema say residual_comeager",
        "expected_overall": "FAIL",
        "expected_rules": ["G3"],
        "observed_overall": v,
        "observed_rules": rules,
        "status": "PASS" if ok else "FAIL",
    })

    # C04 missing axis field: must fail closed, not crash.
    t = clone(tax)
    del t["classes"]["AF-SCC-C2-VAC-GEN"]["axes"]["genericity_kind"]
    f, v, pc = run(t, schemas)
    rules = sorted({r["rule"] for r in f if r["severity"] == "hard" and r["class_id"] == "AF-SCC-C2-VAC-GEN"})
    ok = v == "FAIL" and "G1" in rules
    results.append({
        "control_id": "C04",
        "description": "AF-SCC-C2-VAC-GEN axes.genericity_kind deleted",
        "expected_overall": "FAIL",
        "expected_rules": ["G1"],
        "observed_overall": v,
        "observed_rules": rules,
        "status": "PASS" if ok else "FAIL",
    })

    # C05 bare generic wording.
    t = clone(tax)
    t["classes"]["AF-SCC-C0-VAC-GEN"]["conclusion"]["text"] = (
        "For generic data in the class, the MGHD is future-inextendible as a C0 Lorentzian manifold.")
    f, v, pc = run(t, schemas)
    rules = sorted({r["rule"] for r in f if r["severity"] == "hard" and r["class_id"] == "AF-SCC-C0-VAC-GEN"})
    ok = v == "FAIL" and "G4" in rules
    results.append({
        "control_id": "C05",
        "description": "F2b conclusion uses bare 'generic data' with no quantifier token",
        "expected_overall": "FAIL",
        "expected_rules": ["G4"],
        "observed_overall": v,
        "observed_rules": rules,
        "status": "PASS" if ok else "FAIL",
    })

    # C06 empty document: must fail closed, not crash.
    try:
        f, v, pc = run({}, schemas)
        ok = v == "FAIL" and any(r["rule"] == "G0" for r in f)
        observed = v
    except Exception as exc:  # pragma: no cover
        ok, observed = False, f"exception:{exc}"
    results.append({
        "control_id": "C06",
        "description": "empty taxonomy document",
        "expected_overall": "FAIL",
        "expected_rules": ["G0"],
        "observed_overall": observed,
        "observed_rules": ["G0"] if ok else [],
        "status": "PASS" if ok else "FAIL",
    })

    # C07 schema kind that contradicts the taxonomy axis.
    sc = clone(schemas)
    sc["schemas/af_scc_c2_vacuum.yaml"] = clone(sc["schemas/af_scc_c2_vacuum.yaml"])
    sc["schemas/af_scc_c2_vacuum.yaml"]["genericity"]["kind"] = "full_measure"
    f, v, pc = run(clone(tax), sc)
    rules = sorted({r["rule"] for r in f if r["severity"] == "hard" and r["class_id"] == "AF-SCC-C2-VAC-GEN"})
    ok = v == "FAIL" and "S3" in rules and "G6" in rules
    results.append({
        "control_id": "C07",
        "description": "F2a schema kind set to full_measure against a residual_comeager taxonomy axis",
        "expected_overall": "FAIL",
        "expected_rules": ["S3", "G6"],
        "observed_overall": v,
        "observed_rules": rules,
        "status": "PASS" if ok else "FAIL",
    })
    return results


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parents[3]
    inputs = [TAXONOMY] + SCHEMAS + [ALIASES]
    before = {p: {"sha256": sha256_file(root / p), "bytes": (root / p).stat().st_size}
              for p in inputs}

    tax = yaml.safe_load((root / TAXONOMY).read_text())
    raw = (root / TAXONOMY).read_text()
    alias2canon = load_alias_table(root)
    schema_docs = {p: yaml.safe_load((root / p).read_text()) for p in SCHEMAS}

    tax_sha = before[TAXONOMY]["sha256"]
    schema_shas = {p: before[p]["sha256"] for p in SCHEMAS}

    findings = check_taxonomy(tax, alias2canon, raw, tax_sha, schema_docs, schema_shas)
    baseline = verdict_of(findings)
    ctl = controls(tax, schema_docs, alias2canon, raw, tax_sha, schema_shas)

    after = {p: {"sha256": sha256_file(root / p), "bytes": (root / p).stat().st_size}
             for p in inputs}
    drift = {p: {"before": before[p]["sha256"], "after": after[p]["sha256"]}
             for p in inputs if before[p]["sha256"] != after[p]["sha256"]}

    ctl_ok = all(c["status"] == "PASS" for c in ctl)
    report = {
        "checker": "check_genericity_consistency.py",
        "checker_version": "1.0",
        "task": "W094-GENERICITY-CONSISTENCY-01 (CF-21)",
        "actor": "worker-094",
        "created_at": now_iso(),
        "advisory": "worker evidence only; no gate verdict, no node status, no frozen byte written",
        "inputs": before,
        "rules": {
            "G1": "axes.genericity_kind present and in the allowed vocabulary or an alias",
            "G1b": "soft: per-class genericity_topology named in F0",
            "G2": "unresolved kind may not carry a specific-quantifier conclusion",
            "G3": "conclusion quantifier family must match the canonical kind",
            "G4": "bare 'generic' wording is not machine-readable",
            "G5": "unresolved 'must be named before any claim' hypothesis requires a machine-readable claim block",
            "G6": "non-unresolved kinds must be discharged by exactly one binding schema",
            "S1/S2/S3/S4": "schema-side kind presence, class id, taxonomy agreement, topology naming",
        },
        "baseline": {
            "verdict": baseline,
            "hard_failure_count": sum(1 for f in findings if f["severity"] == "hard"),
            "soft_finding_count": sum(1 for f in findings if f["severity"] == "soft"),
            "per_class": per_class(findings),
            "findings": findings,
        },
        "controls": {
            "verdict": "PASS" if ctl_ok else "FAIL",
            "count": len(ctl),
            "results": ctl,
        },
        "drift_after_run": drift,
        "evidence_lines": {
            "scalar_genericity_kind": find_line(raw, 'genericity_kind: "unresolved"'),
            "scalar_conclusion_comeager": find_line(raw, "For a comeager set G of data in the class"),
            "scalar_h4_must_be_named": find_line(raw, "must be named before any claim is filed"),
            "d3_discharge_record": find_line(raw, "confirmed discharged for ALL FOUR classes"),
        },
        "falsifier": (
            "Re-run this checker after the formulation owner repins or repairs the taxonomy: if "
            "AF-WCC-SCALAR-SPH declares a concrete/provisional kind with a binding schema (or an "
            "explicit provisional/blocked marker on its conclusion) and the baseline becomes PASS "
            "with all controls still behaving as declared, this finding is void. A file rewrite "
            "alone is not a falsifier; the finding binds the measured sha256 values in `inputs`."
        ),
        "next_falsifier": (
            "Re-run: python3 artifacts/worker-094/genericity_consistency/check_genericity_consistency.py "
            "--out artifacts/worker-094/genericity_consistency/run/report.json"
        ),
    }
    out_path = Path(args.out) if args.out else (root / "artifacts/worker-094/genericity_consistency/run/report.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=1, sort_keys=False) + "\n")

    summary = {
        "baseline": baseline,
        "hard_failures": [{"rule": f["rule"], "class_id": f["class_id"]} for f in findings if f["severity"] == "hard"],
        "controls": report["controls"]["verdict"],
        "drift": drift,
        "report": str(out_path),
    }
    print(json.dumps(summary, indent=1))
    if drift:
        return 3
    if not ctl_ok:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
