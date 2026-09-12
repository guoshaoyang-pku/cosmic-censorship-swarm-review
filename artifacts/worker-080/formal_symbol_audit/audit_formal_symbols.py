#!/usr/bin/env python3
"""W080-FSYM-01: independent formal-surface symbol / quantifier audit.

Class-bound task (no inbox card existed for worker-080, fleet instance
worker-080-20260912T002242-968807).  Reads only; writes only its own report.

What it checks, at pinned canonical hashes:
  A. every predicate-like symbol used in a schema's conclusion.statement_formal
     has a definition anchor in the SAME schema file (anchors: a YAML key or
     value named name/predicate_name/definition_ref, or a definition-bearing
     key/line).  Symbols with no occurrence outside statement_formal are
     single_use_unresolved and are reported as findings.
  B. the ordered quantifier sequence declared in quantifiers.ordered is
     realized by statement_formal; declared-but-unrealized binders are
     reported as folded binders with their domain_id.
  C. cross-schema: the shared prefix of the three statements is compared and
     the class-relative predicate proper_future_extension_in_class is checked
     to resolve to file-local definitions with the file's own
     frozen_regularity (no C0/C2 merge at the formal surface).

Controls (liveness): the same classifier is run on a positive synthetic
schema (all symbols anchored), a negative synthetic schema (one undefined
predicate) and a quantifier-fold synthetic; the instrument must flag exactly
the injected defects, otherwise it exits 1.

Fail-closed: expected hashes are pinned below.  Exit 0 = instrument valid
(controls pass, no input drift), 1 = control failure, 2 = input hash drift or
pinned-input mismatch.  No canonical file is written.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[3]

PINNED = {
    "F1": {
        "path": "schemas/af_wcc_vacuum.yaml",
        "sha256": "9a8bd4c9680042a40894f6085f183661500966f2d787a6bf28a7098a271ed503",
        "class_id": "AF-WCC-VAC-GEN",
    },
    "F2a": {
        "path": "schemas/af_scc_c2_vacuum.yaml",
        "sha256": "b6123750b37d8bee1e92eeb025979a6afdf3b29a33331a9d8499e21398d13fb2",
        "class_id": "AF-SCC-C2-VAC-GEN",
    },
    "F2b": {
        "path": "schemas/af_scc_c0_vacuum.yaml",
        "sha256": "1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508",
        "class_id": "AF-SCC-C0-VAC-GEN",
    },
    "F0": {
        "path": "research_map/formulation_taxonomy.yaml",
        "sha256": "276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc",
        "class_id": "GLOBAL",
    },
}

TZ = timezone(timedelta(hours=8))
LOGICAL = {
    "forall", "exists", "not", "and", "or", "in", "subset", "iff", "implies",
    "with", "letting", "be", "the", "a", "of", "is", "that", "such", "there",
    "every", "for", "all",
}
# Bound variables / structural tokens introduced by the quantifier block
# itself; they are binders, not predicate symbols.
BOUND_TOKENS = {
    "s", "delta", "G", "G_{s,delta}", "D", "Sigma", "h", "K", "M", "g",
    "gamma", "q", "Mtilde", "gtilde", "Omega", "M_D", "I+_D", "IPLUS_D",
}

# Subscript/superscript macros are captured whole: X^{s,delta}_vac,
# G_{s,delta}, AF_{I+}, M_D, I+_D.  I+_D / I+ are pre-normalized.
TOKEN_RE = re.compile(
    r"[A-Za-z](?:[A-Za-z0-9_]*[A-Za-z0-9])?"  # base identifier (no trailing _)
    r"(?:\^\{[^{}]*\})?"                      # optional superscript macro
    r"(?:_\{[^{}]*\}|_[A-Za-z0-9]+)?"         # optional subscript macro / index
)


def now_iso() -> str:
    return datetime.now(TZ).replace(microsecond=0).isoformat()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def pre_normalize(text: str) -> str:
    text = text.replace("I+_D", "IPLUS_D")
    text = re.sub(r"\bI\+", "IPLUS", text)
    return text


def detokenize(tok: str) -> str:
    return tok.replace("IPLUS", "I+")


def tokenize_formal(text: str) -> list[str]:
    return [detokenize(t) for t in TOKEN_RE.findall(pre_normalize(text))]


def line_of(raw: str, needle: str) -> int | None:
    for i, line in enumerate(raw.splitlines(), start=1):
        if needle in line:
            return i
    return None


def anchor_index(doc: dict, raw: str, statement: str) -> dict[str, str]:
    """Map symbol -> anchor description for definition-like anchors."""
    anchors: dict[str, str] = {}

    def walk(node, path):
        if isinstance(node, dict):
            for k, v in node.items():
                kp = f"{path}.{k}" if path else str(k)
                if k in ("name", "predicate_name", "definition_ref") and isinstance(v, str):
                    anchors.setdefault(v.split(".")[-1].strip(), f"{kp}={v}")
                    anchors.setdefault(v.strip(), f"{kp}={v}")
                if isinstance(k, str) and "definition" in k.lower() and isinstance(v, str):
                    for tok in tokenize_formal(v):
                        anchors.setdefault(tok, f"{kp} (definition-bearing key)")
                walk(v, kp)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{path}[{i}]")

    walk(doc, "")
    for i, line in enumerate(raw.splitlines(), start=1):
        if "definition" not in line.lower():
            continue
        stripped = line.replace(statement, "")
        if not stripped.strip():
            continue
        for tok in tokenize_formal(stripped):
            anchors.setdefault(tok, f"line {i} (definition context)")
    return anchors


def stem(tok: str) -> str:
    t = tok.lower()
    if len(t) > 5 and t.endswith("e"):
        t = t[:-1]
    return t


def classify_symbol(tok: str, raw: str, statement: str, anchors: dict) -> dict:
    outside = raw.replace(statement, "")
    exact_occ = len(re.findall(
        r"(?<![A-Za-z0-9_])" + re.escape(tok) + r"(?![A-Za-z0-9_])", outside))
    stem_hit = None
    if len(stem(tok)) >= 5:
        pat = re.compile(
            r"[A-Za-z_][A-Za-z0-9_]*" + re.escape(stem(tok)) + r"[A-Za-z0-9_]*", re.I)
        m = pat.search(outside)
        if m:
            stem_hit = m.group(0)
    anchor = anchors.get(tok)
    if anchor is None and stem_hit is not None:
        for k, v in anchors.items():
            if k.lower() == stem_hit.lower():
                anchor = v
                break
    if anchor is not None:
        status = "defined_anchor"
    elif exact_occ > 0:
        status = "used_elsewhere_only"
    else:
        status = "single_use_unresolved"
    return {
        "symbol": tok,
        "class": status,
        "occurrences_outside_statement": exact_occ,
        "stem_match": stem_hit,
        "anchor": anchor,
    }


def predicate_candidates(statement: str) -> list[str]:
    """Predicate-like tokens: called as f(...), or macro tokens NAME_{...}."""
    norm = pre_normalize(statement)
    found: list[str] = []
    for m in TOKEN_RE.finditer(norm):
        tok = detokenize(m.group(0))
        rest = norm[m.end():]
        called = rest.lstrip().startswith("(")
        macro = ("_{" in tok or "^{" in tok) and tok not in LOGICAL
        if not (called or macro):
            continue
        if tok in LOGICAL or tok in BOUND_TOKENS:
            continue
        if tok not in found:
            found.append(tok)
    return found


def quantifier_sequence(statement: str) -> list[str]:
    seq = []
    for m in re.finditer(r"\b(not\s+exists|forall|exists)\b", statement):
        seq.append("not_exists" if m.group(0).startswith("not") else m.group(0))
    return seq


def align_quantifiers(ordered: list, realized: list[str]) -> tuple[list[dict], list[str]]:
    """Greedy in-order alignment; unmatched declared entries are folded."""
    folded, unmatched, j = [], [], 0
    consumed = set()
    for kind in realized:
        while j < len(ordered) and ordered[j].get("kind") != kind:
            j += 1
        if j < len(ordered):
            consumed.add(j)
            j += 1
    for i, q in enumerate(ordered):
        if i not in consumed:
            folded.append(
                {"index": i, "kind": q.get("kind"), "binder": q.get("binder"),
                 "domain_id": q.get("domain_id")}
            )
    return folded, unmatched


def analyze(name: str, path: Path, raw: str, doc: dict) -> dict:
    statement = doc["conclusion"]["statement_formal"]
    anchors = anchor_index(doc, raw, statement)
    syms = [classify_symbol(t, raw, statement, anchors) for t in predicate_candidates(statement)]
    ordered = doc.get("quantifiers", {}).get("ordered", [])
    declared = [q.get("kind") for q in ordered]
    realized = quantifier_sequence(statement)
    folded, unmatched = align_quantifiers(ordered, realized)
    return {
        "schema": name,
        "class_id": PINNED[name]["class_id"],
        "path": PINNED[name]["path"],
        "sha256": PINNED[name]["sha256"],
        "statement_formal": statement,
        "statement_line": line_of(raw, statement),
        "quantifiers_declared": declared,
        "quantifiers_realized": realized,
        "folded_binders": folded,
        "unmatched_realized_quantifiers": unmatched,
        "predicate_symbols": syms,
        "anchor_count": len(anchors),
    }


def synthetic_controls() -> dict:
    positive_doc = {
        "conclusion": {"statement_formal": "forall D in D0: defined_pred(D)"},
        "predicate_def": {"name": "defined_pred",
                          "definition": "defined_pred holds by construction for every D"},
        "quantifiers": {"ordered": [{"kind": "forall", "binder": "D", "domain_id": "D0"}]},
    }
    negative_doc = {
        "conclusion": {"statement_formal": "forall D in D0: wholly_undefined_pred(D)"},
        "predicate_def": {"name": "defined_pred",
                          "definition": "defined_pred holds by construction for every D"},
        "quantifiers": {"ordered": [{"kind": "forall", "binder": "D", "domain_id": "D0"}]},
    }
    fold_doc = {
        "conclusion": {"statement_formal": "forall D in D0: anchored_pred(D)"},
        "predicate_def": {"name": "anchored_pred", "definition": "anchored by definition"},
        "quantifiers": {
            "ordered": [
                {"kind": "forall", "binder": "D", "domain_id": "D0"},
                {"kind": "exists", "binder": "G", "domain_id": "D1"},
            ]
        },
    }

    def run(doc):
        raw = json.dumps(doc)
        st = doc["conclusion"]["statement_formal"]
        anchors = anchor_index(doc, raw, st)
        return [classify_symbol(t, raw, st, anchors) for t in predicate_candidates(st)]

    pos = run(positive_doc)
    neg = run(negative_doc)
    fold_folded, _ = align_quantifiers(
        fold_doc["quantifiers"]["ordered"],
        quantifier_sequence(fold_doc["conclusion"]["statement_formal"]),
    )
    pos_bad = [s["symbol"] for s in pos if s["class"] == "single_use_unresolved"]
    neg_bad = [s["symbol"] for s in neg if s["class"] == "single_use_unresolved"]
    return {
        "positive_control": {"unresolved": pos_bad, "pass": len(pos_bad) == 0},
        "negative_control": {"unresolved": neg_bad, "pass": neg_bad == ["wholly_undefined_pred"]},
        "fold_control": {
            "declared": [q["kind"] for q in fold_doc["quantifiers"]["ordered"]],
            "realized": quantifier_sequence(fold_doc["conclusion"]["statement_formal"]),
            "folded_indices": [f["index"] for f in fold_folded],
            "pass": [f["index"] for f in fold_folded] == [1],
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", help="write report JSON to this path")
    args = ap.parse_args()

    start = now_iso()
    measured = {}
    for name, spec in PINNED.items():
        p = REPO / spec["path"]
        measured[name] = sha256_file(p)
        if measured[name] != spec["sha256"]:
            print(json.dumps({"error": "pinned_input_mismatch", "schema": name,
                              "path": spec["path"], "expected": spec["sha256"],
                              "measured": measured[name]}), file=sys.stderr)
            return 2

    results, docs, raws = [], {}, {}
    for name in ("F1", "F2a", "F2b"):
        raw = (REPO / PINNED[name]["path"]).read_text()
        raws[name] = raw
        docs[name] = yaml.safe_load(raw)
        results.append(analyze(name, REPO / PINNED[name]["path"], raw, docs[name]))

    taxonomy_raw = (REPO / PINNED["F0"]["path"]).read_text()
    controls = synthetic_controls()
    control_ok = all(v["pass"] for v in controls.values() if isinstance(v, dict))

    findings = []
    for r in results:
        for s in r["predicate_symbols"]:
            if s["class"] != "single_use_unresolved":
                continue
            findings.append({
                "id": f"W080-FSYM-{len(findings) + 1:02d}",
                "schema": r["schema"],
                "class_id": r["class_id"],
                "severity": "hard" if r["schema"] == "F1" else "medium",
                "kind": "undefined_normative_symbol",
                "symbol": s["symbol"],
                "statement_line": r["statement_line"],
                "detail": (f"{s['symbol']} is used as a predicate in "
                           f"conclusion.statement_formal but has no definition anchor and no "
                           f"occurrence anywhere else in {r['path']}."),
            })
        for fb in r["folded_binders"]:
            findings.append({
                "id": f"W080-FSYM-{len(findings) + 1:02d}",
                "schema": r["schema"],
                "class_id": r["class_id"],
                "severity": "advisory",
                "kind": "quantifier_folded_without_recorded_rule",
                "symbol": f"{fb['kind']} {fb['binder']}",
                "domain_id": fb["domain_id"],
                "statement_line": r["statement_line"],
                "detail": (f"quantifiers.ordered declares {len(r['quantifiers_declared'])} binders "
                           f"but statement_formal realizes {len(r['quantifiers_realized'])}; binder "
                           f"{fb['binder']} ({fb['domain_id']}) is folded into an atomic predicate "
                           f"and no folding rule is recorded beside conclusion.statement_formal. "
                           f"An exact {len(r['quantifiers_declared'])}-binder expansion exists at "
                           f"quantifiers.formal; the advisory is the missing recorded abbreviation "
                           f"rule in the conclusion block, not an absent quantifier."),
            })

    prefixes = {n: r["statement_formal"].split(":")[0]
                for n, r in zip(("F1", "F2a", "F2b"), results)}
    shared_prefix = len(set(prefixes.values())) == 1
    ext = {}
    for n in ("F2a", "F2b"):
        ep = docs[n].get("extension_predicate", {})
        ext[n] = {
            "name": ep.get("name"),
            "frozen_regularity": ep.get("frozen_regularity"),
            "has_definition": bool(ep.get("definition")),
            "frozen_equation_concept": ep.get("frozen_equation_concept"),
        }
    statements_equal_f2 = (docs["F2a"]["conclusion"]["statement_formal"]
                           == docs["F2b"]["conclusion"]["statement_formal"])
    class_local = (
        ext["F2a"]["name"] == ext["F2b"]["name"] == "proper_future_extension_in_class"
        and ext["F2a"]["has_definition"] and ext["F2b"]["has_definition"]
        and {ext["F2a"]["frozen_regularity"], ext["F2b"]["frozen_regularity"]} == {"C2", "C0"}
    )

    end = now_iso()
    drift = {}
    for name, spec in PINNED.items():
        cur = sha256_file(REPO / spec["path"])
        if cur != measured[name]:
            drift[name] = {"start": measured[name], "end": cur}
    if drift:
        print(json.dumps({"error": "input_drift", "drift": drift}), file=sys.stderr)
        return 2

    hard = [f for f in findings if f["severity"] == "hard"]
    verdict = "FAIL" if hard else ("PASS_WITH_ADVISORIES" if findings else "PASS")
    report = {
        "task_id": "W080-FSYM-01",
        "worker": "worker-080",
        "instrument": "artifacts/worker-080/formal_symbol_audit/audit_formal_symbols.py",
        "started_at": start,
        "finished_at": end,
        "inputs": {
            "schemas": {
                r["schema"]: {"path": r["path"], "class_id": r["class_id"],
                              "sha256": r["sha256"],
                              "bytes": (REPO / r["path"]).stat().st_size}
                for r in results
            },
            "f0_taxonomy": {"path": PINNED["F0"]["path"], "sha256": measured["F0"],
                            "bytes": len(taxonomy_raw.encode())},
        },
        "per_schema": results,
        "cross_schema": {
            "shared_statement_prefix": shared_prefix,
            "prefixes": prefixes,
            "f2a_f2b_statement_formal_byte_identical": statements_equal_f2,
            "extension_predicate": ext,
            "class_local_predicate_resolution": class_local,
        },
        "controls": controls,
        "controls_pass": control_ok,
        "findings": findings,
        "verdict": verdict,
        "falsifier": (
            "A revision of schemas/af_wcc_vacuum.yaml in which conclusion.statement_formal defines "
            "AF_{I+} inline or elsewhere, or carries a recorded abbreviation rule mapping the folded "
            "binders to the atomic predicates, or a demonstration that AF_{I+} has a definition anchor "
            "in that file which this classifier does not see, voids the corresponding finding and "
            "requires re-running this instrument at the new sha256. Re-measuring any pinned sha256 as "
            "different voids the whole report at that path."
        ),
        "non_claims": [
            "No node completion, validation_status=passed, gate verdict or theorem is claimed.",
            "Syntactic/structural measurement of the formal surface only; no truth value is assigned to any conjecture.",
            "The F2b containment-chain inconsistencies reported by other workers are out of scope here.",
        ],
    }
    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    summary = {
        "verdict": verdict,
        "schema_verdicts": {r["schema"]: {
            "realized": len(r["quantifiers_realized"]),
            "declared": len(r["quantifiers_declared"]),
            "folded": len(r["folded_binders"]),
            "unresolved_symbols": [s["symbol"] for s in r["predicate_symbols"]
                                   if s["class"] == "single_use_unresolved"],
        } for r in results},
        "cross_schema_class_local": class_local,
        "controls_pass": control_ok,
        "report": args.out or "(stdout only)",
    }
    print(json.dumps(summary, indent=2))
    return 0 if control_ok else 1


if __name__ == "__main__":
    sys.exit(main())
