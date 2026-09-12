#!/usr/bin/env python3
"""WP13-F1-GATE: machine-checkable acceptance gate for a class-bound formulation schema.

Task: proposals/flash-13/WP13-F1-GATE.yaml
Class under test (default): AF-WCC-VAC-GEN  (asymptotically flat, weak cosmic censorship,
vacuum, generic data).  Node: F1.  Executor: deepseek-flash-13.

WHAT THIS IS
  A deterministic structural lint over a schema document. It decides 12 named rules and exits
  0 only if every rule passes. Rule R09 is lexical class-leakage detection; it is NOT a semantic
  checker. The gate says "this document has the required class-bound structure"; it does NOT say
  the formulation is correct, non-vacuous, or physically true.

WHAT THIS IS NOT
  - not a proof assistant and not a citation verifier (R11 only checks that primary sources are
    either marked verified or explicitly unresolved);
  - not an authority: the F1 node owner (lead-formulation) binds this gate, the audit lead
    reviews it, and the research map is not modified by running it.

USAGE
  python3 check_schema.py [--expect-class AF-WCC-VAC-GEN] [--require-file PATH]... [--pin PATH:SHA256]... SCHEMA
  exit 0 = accept, 1 = reject, 2 = usage/input error.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - environment check
    yaml = None

GATE_ID = "WP13-F1-GATE"
GATE_VERSION = "0.1"

RULE_TEXT = {
    "R01": "schema parses as a mapping with schema_version and class_id",
    "R02": "class_id matches expected class and class_components decomposes it",
    "R03": "explicit ordered forall/exists quantifiers with domains",
    "R04": "topology: 3+1, one asymptotically flat end, conformal compactification, not closed/periodic",
    "R05": "data_class: vacuum, constraints, numeric Sobolev index/weight/decay, no vague qualifiers",
    "R06": "genericity has a named kind, a condition, and an excluded set",
    "R07": "i_plus completeness and visibility predicate + negation are defined",
    "R08": "conclusion_type not inflated; conclusion is the negation of visibility",
    "R09": "no cross-class leakage tokens outside exempt sections",
    "R10": "falsifier names a witness_type and a concrete test",
    "R11": "evidence_refs present; primary sources marked verified or unresolved",
    "R12": "declared artifact file exists and hash matches when pinned",
}

ALLOWED_CONCLUSION_TYPES = {"open_problem", "formal_model", "conditional_theorem"}
GENERICITY_KINDS = {
    "open_dense",
    "residual",
    "full_measure",
    "meager_complement",
    "symmetry_breaking",
    "stable_under_perturbation",
}
EXEMPT_KEYS = {"excluded_classes", "non_claims", "out_of_scope"}

# Lexical leakage blocks for class AF-WCC-VAC-GEN. Kept deliberately conservative: multi-word /
# qualified tokens only. History: v0.1 of this file blocked the bare stem "inextendib" and was
# falsified by its own conforming fixture, because "future-inextendible null generators of I+" is
# standard WCC completeness language. The stem is now qualified to SCC-specific phrases; the
# false positive is recorded in RESULTS.md as evidence the fixture corpus has teeth.
LEAK_TOKENS = {
    "AF-SCC (strong censorship / extendibility)": [
        "cauchy horizon",
        "mass inflation",
        "blue-shift instability",
        "blueshift instability",
        "strong cosmic censorship",
        "c^2-inextendib",
        "c0-inextendib",
        "c^0-inextendib",
        "inextendibility of the maximal development",
        "maximal development is inextendible",
        "extendible spacetime",
        "extension beyond the horizon",
        "continuation beyond the horizon",
    ],
    "AF-WCC-SCALAR-SPH (scalar / spherical)": [
        "scalar field",
        "klein-gordon",
        "spherical symmetry",
        "spherically symmetric",
        "self-gravitating scalar",
        "wave equation",
    ],
    "non-vacuum matter": [
        "maxwell field",
        "electromagnetic field",
        "perfect fluid",
        "stress-energy tensor",
        "matter field",
    ],
}

VAGUE_TOKENS = [
    "sufficiently decay",
    "sufficiently fast",
    "suitable",
    "appropriate",
    "reasonable",
    "nice",
    "well-behaved",
    "as needed",
]

# Conclusion-direction checks (R08).
NEGATION_PHRASES = [
    "no naked",
    "not visible",
    "hidden from",
    "i+ is complete",
    "future null infinity is complete",
    "no future-directed causal curve",
    "fails to reach",
    "cannot reach",
]
INFLATION_PHRASES = [
    "maximal development exists",
    "there exists a development",
    "numerical evidence",
    "converges",
    "we prove",
    "is proven",
    "has been proven",
]

TOPOLOGY_FORBIDDEN = [
    "closed universe",
    "compact without boundary",
    "periodic boundary",
    "cosmological",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def iter_strings(obj, path="$"):
    """Yield (json-path, string) for every string leaf."""
    if isinstance(obj, str):
        yield path, obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from iter_strings(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from iter_strings(v, f"{path}[{i}]")


def drop_keys(obj, keys):
    if isinstance(obj, dict):
        return {k: drop_keys(v, keys) for k, v in obj.items() if k not in keys}
    if isinstance(obj, list):
        return [drop_keys(v, keys) for v in obj]
    return obj


def nonempty_str(x) -> bool:
    return isinstance(x, str) and bool(x.strip())


def numeric(x) -> bool:
    if isinstance(x, bool):
        return False
    if isinstance(x, (int, float)):
        return True
    if isinstance(x, str):
        try:
            float(x.strip().split()[0])
            return True
        except (ValueError, IndexError):
            return False
    return False


class Gate:
    def __init__(self, expect_class: str, require_files, pins):
        self.expect_class = expect_class
        self.require_files = [Path(p) for p in (require_files or [])]
        self.pins = pins or []
        self.failed = []
        self.warnings = []
        self.checked = []

    def fail(self, rule, detail):
        self.failed.append({"rule": rule, "detail": detail})

    def warn(self, rule, detail):
        self.warnings.append({"rule": rule, "detail": detail})

    def run(self, doc, source: Path):
        for rule in sorted(RULE_TEXT):
            self.checked.append(rule)

        # ---- R01 parse and envelope -------------------------------------------------
        if not isinstance(doc, dict):
            self.fail("R01", "top level is not a mapping")
            return
        for key in ("schema_version", "class_id"):
            if not nonempty_str(doc.get(key)):
                self.fail("R01", f"missing/non-string {key}")

        # ---- R02 class binding ------------------------------------------------------
        cid = doc.get("class_id")
        if nonempty_str(cid) and cid != self.expect_class:
            self.fail("R02", f"class_id={cid!r} != expected {self.expect_class!r}")
        comp = doc.get("class_components")
        if not isinstance(comp, dict):
            self.fail("R02", "class_components is not a mapping")
        else:
            for key in ("asymptotic_flatness", "censorship", "matter", "genericity"):
                if not nonempty_str(comp.get(key)):
                    self.fail("R02", f"class_components.{key} missing/empty")
            if nonempty_str(comp.get("matter")) and comp["matter"].strip().lower() != "vacuum":
                self.fail("R02", f"class_components.matter={comp['matter']!r} is not vacuum")

        # ---- R03 quantifiers --------------------------------------------------------
        qo = doc.get("quantifier_order")
        if not isinstance(qo, list) or len(qo) < 2:
            self.fail("R03", "quantifier_order must be a list with >= 2 entries")
        else:
            seen = set()
            for i, q in enumerate(qo):
                if not isinstance(q, dict):
                    self.fail("R03", f"quantifier_order[{i}] is not a mapping")
                    continue
                kind = str(q.get("quantifier", "")).strip().lower()
                if kind not in {"forall", "exists"}:
                    self.fail("R03", f"quantifier_order[{i}].quantifier={kind!r} not forall/exists")
                else:
                    seen.add(kind)
                for key in ("variable", "domain"):
                    if not nonempty_str(q.get(key)):
                        self.fail("R03", f"quantifier_order[{i}].{key} missing/empty")
            if seen != {"forall", "exists"}:
                self.fail("R03", f"quantifier_order missing {'forall' if 'forall' not in seen else 'exists'}")
        fs = doc.get("formal_statement")
        if not nonempty_str(fs):
            self.fail("R03", "formal_statement missing/empty")
        elif not any(tok in fs.lower() for tok in ("∀", "∃", "for all", "for every", "there exists")):
            self.fail("R03", "formal_statement contains no explicit quantifier phrase")

        # ---- R04 topology -----------------------------------------------------------
        topo = doc.get("topology")
        if not isinstance(topo, dict):
            self.fail("R04", "topology is not a mapping")
        else:
            for key in ("manifold", "dimension", "asymptotic_end", "compactification"):
                if not nonempty_str(topo.get(key)):
                    self.fail("R04", f"topology.{key} missing/empty")
            dim = str(topo.get("dimension", ""))
            if "3+1" not in dim and dim.strip() not in {"4", "3+1d"}:
                self.fail("R04", f"topology.dimension={dim!r} is not 3+1")
            ends = topo.get("ends")
            if not (isinstance(ends, int) and not isinstance(ends, bool) and ends >= 1):
                self.fail("R04", f"topology.ends={ends!r} is not an integer >= 1")
            if "conformal" not in str(topo.get("compactification", "")).lower():
                self.fail("R04", "topology.compactification does not mention a conformal completion")
            for _, s in iter_strings(topo):
                low = s.lower()
                for bad in TOPOLOGY_FORBIDDEN:
                    if bad in low:
                        self.fail("R04", f"topology contains forbidden token {bad!r}")

        # ---- R05 data class ---------------------------------------------------------
        dc = doc.get("data_class")
        if not isinstance(dc, dict):
            self.fail("R05", "data_class is not a mapping")
        else:
            if str(dc.get("matter", "")).strip().lower() != "vacuum":
                self.fail("R05", f"data_class.matter={dc.get('matter')!r} is not vacuum")
            cons = " ".join(str(c).lower() for c in dc.get("constraints", []) if isinstance(c, str)) \
                if isinstance(dc.get("constraints"), list) else ""
            for need in ("constraint",):
                if need not in cons:
                    self.fail("R05", "data_class.constraints does not name the constraint equations")
            if "hamiltonian" not in cons:
                self.fail("R05", "data_class.constraints lacks the Hamiltonian constraint")
            if "momentum" not in cons:
                self.fail("R05", "data_class.constraints lacks the momentum constraint")
            if not numeric(dc.get("sobolev_index")):
                self.fail("R05", f"data_class.sobolev_index={dc.get('sobolev_index')!r} is not numeric")
            if not nonempty_str(dc.get("weight")) or not any(ch.isdigit() for ch in str(dc.get("weight"))):
                self.fail("R05", "data_class.weight must be a named/numeric weight with a value")
            if not numeric(dc.get("decay_rate", None)) and not nonempty_str(dc.get("decay_rate")):
                self.fail("R05", "data_class.decay_rate missing/empty")
            if not nonempty_str(dc.get("norm")):
                self.fail("R05", "data_class.norm missing/empty")
            for _, s in iter_strings(dc):
                low = s.lower()
                for bad in VAGUE_TOKENS:
                    if bad in low:
                        self.fail("R05", f"data_class contains vague qualifier {bad!r}")

        # ---- R06 genericity ---------------------------------------------------------
        gen = doc.get("genericity")
        if not isinstance(gen, dict):
            self.fail("R06", "genericity is not a mapping")
        else:
            kind = str(gen.get("kind", "")).strip().lower()
            if kind not in GENERICITY_KINDS:
                self.fail("R06", f"genericity.kind={kind!r} not in {sorted(GENERICITY_KINDS)}")
            if not nonempty_str(gen.get("condition")):
                self.fail("R06", "genericity.condition missing/empty")
            exc = gen.get("excluded")
            if isinstance(exc, list):
                exc_ok = any(nonempty_str(x) for x in exc)
            else:
                exc_ok = nonempty_str(exc)
            if not exc_ok:
                self.fail("R06", "genericity.excluded missing/empty")

        # ---- R07 I+ and visibility --------------------------------------------------
        ip = doc.get("i_plus")
        if not isinstance(ip, dict):
            self.fail("R07", "i_plus is not a mapping")
        else:
            for key in ("definition", "completeness_condition"):
                if not nonempty_str(ip.get(key)):
                    self.fail("R07", f"i_plus.{key} missing/empty")
        vis = doc.get("visibility")
        if not isinstance(vis, dict):
            self.fail("R07", "visibility is not a mapping")
        else:
            for key in ("singularity_definition", "predicate", "negation"):
                if not nonempty_str(vis.get(key)):
                    self.fail("R07", f"visibility.{key} missing/empty")
            if nonempty_str(vis.get("predicate")) and "causal curve" not in vis["predicate"].lower():
                self.fail("R07", "visibility.predicate does not mention a causal curve")
            if nonempty_str(vis.get("negation")) and "no" not in vis["negation"].lower():
                self.fail("R07", "visibility.negation is not phrased as a negation")

        # ---- R08 conclusion ---------------------------------------------------------
        ctype = str(doc.get("conclusion_type", "")).strip()
        if ctype not in ALLOWED_CONCLUSION_TYPES:
            self.fail("R08", f"conclusion_type={ctype!r} not in {sorted(ALLOWED_CONCLUSION_TYPES)}")
        concl = doc.get("conclusion")
        if not nonempty_str(concl):
            self.fail("R08", "conclusion missing/empty")
        else:
            low = concl.lower()
            if not any(p in low for p in NEGATION_PHRASES):
                self.fail("R08", "conclusion is not phrased as the negation of visibility")
            for bad in INFLATION_PHRASES:
                if bad in low:
                    self.fail("R08", f"conclusion contains inflated/out-of-class phrase {bad!r}")

        # ---- R09 class leakage ------------------------------------------------------
        scan = drop_keys(doc, EXEMPT_KEYS)
        for _, s in iter_strings(scan):
            low = s.lower()
            for family, tokens in LEAK_TOKENS.items():
                for tok in tokens:
                    if tok in low:
                        self.fail("R09", f"leakage token {tok!r} from {family}")

        # ---- R10 falsifier ----------------------------------------------------------
        fal = doc.get("falsifier")
        if not isinstance(fal, dict):
            self.fail("R10", "falsifier is not a mapping")
        else:
            wt = str(fal.get("witness_type", "")).strip().lower()
            test = fal.get("test")
            if wt in {"", "none", "n/a", "not applicable", "na"}:
                self.fail("R10", f"falsifier.witness_type={wt!r} is empty or none")
            if not nonempty_str(test):
                self.fail("R10", "falsifier.test missing/empty")
            elif len(test.strip()) < 20:
                self.fail("R10", "falsifier.test is too short to be a concrete test")

        # ---- R11 evidence refs ------------------------------------------------------
        refs = doc.get("evidence_refs")
        if not isinstance(refs, list) or not refs:
            self.fail("R11", "evidence_refs must be a non-empty list")
        else:
            for i, r in enumerate(refs):
                if not isinstance(r, dict):
                    self.fail("R11", f"evidence_refs[{i}] is not a mapping")
                    continue
                if str(r.get("kind", "")) not in {"internal_file", "primary_source", "definition"}:
                    self.fail("R11", f"evidence_refs[{i}].kind={r.get('kind')!r} invalid")
                if not nonempty_str(r.get("locator")):
                    self.fail("R11", f"evidence_refs[{i}].locator missing/empty")
                if r.get("kind") == "primary_source":
                    st = str(r.get("verification_status", "")).strip().lower()
                    if st not in {"verified", "unresolved"}:
                        self.fail("R11", f"evidence_refs[{i}] primary_source lacks verification_status")
                    elif st == "unresolved":
                        self.warn("R11", f"evidence_refs[{i}] primary source is explicitly unresolved")

        # ---- R12 artifact existence / hash pin --------------------------------------
        for p in self.require_files:
            if not p.exists():
                self.fail("R12", f"required artifact file missing: {p}")
        for pin in self.pins:
            if ":" not in pin:
                self.fail("R12", f"pin {pin!r} is not PATH:SHA256")
                continue
            pstr, expected = pin.rsplit(":", 1)
            p = Path(pstr)
            if not p.exists():
                self.fail("R12", f"pinned artifact missing: {p}")
            else:
                actual = sha256_file(p)
                if actual != expected:
                    self.fail("R12", f"hash mismatch for {p}: {actual} != {expected}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=f"{GATE_ID} schema acceptance gate v{GATE_VERSION}")
    ap.add_argument("schema", help="schema YAML/JSON to check")
    ap.add_argument("--expect-class", default="AF-WCC-VAC-GEN")
    ap.add_argument("--require-file", action="append", default=[],
                    help="declared artifact path that must exist (repeatable)")
    ap.add_argument("--pin", action="append", default=[],
                    help="PATH:SHA256 that must match exactly (repeatable)")
    ap.add_argument("--json-out", default=None)
    args = ap.parse_args(argv)

    src = Path(args.schema)
    if not src.exists():
        print(f"INPUT ERROR: {src} does not exist", file=sys.stderr)
        return 2
    if yaml is None:
        print("INPUT ERROR: PyYAML unavailable", file=sys.stderr)
        return 2
    try:
        doc = yaml.safe_load(src.read_text())
    except yaml.YAMLError as e:
        doc = None
        print(f"R01 FAIL: YAML parse error: {e}", file=sys.stderr)

    gate = Gate(args.expect_class, args.require_file, args.pin)
    gate.run(doc, src)

    verdict = "accept" if not gate.failed else "reject"
    report = {
        "gate": GATE_ID,
        "gate_version": GATE_VERSION,
        "target": str(src),
        "target_sha256": sha256_file(src),
        "class_expected": args.expect_class,
        "verdict": verdict,
        "rules_checked": gate.checked,
        "failed_rules": gate.failed,
        "warnings": gate.warnings,
        "rules": RULE_TEXT,
        "limitations": "structural lint only; R09 is lexical; not a correctness or citation check",
    }
    print(f"{GATE_ID} v{GATE_VERSION} target={src}")
    print(f"verdict={verdict}  sha256={report['target_sha256'][:16]}...")
    for f in gate.failed:
        print(f"  FAIL {f['rule']}: {f['detail']}")
    for w in gate.warnings:
        print(f"  WARN {w['rule']}: {w['detail']}")
    print(f"passed_rules={len(gate.checked) - len({f['rule'] for f in gate.failed})}/{len(gate.checked)}")
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(report, indent=2) + "\n")
    return 0 if verdict == "accept" else 1


if __name__ == "__main__":
    sys.exit(main())
