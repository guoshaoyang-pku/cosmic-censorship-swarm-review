#!/usr/bin/env python3
"""GFORM-XDATA-057: cross-schema check of F1/F2a/F2b at the canonical hashes.

Task (class-bound): AF-WCC-VAC-GEN, AF-SCC-C2-VAC-GEN, AF-SCC-C0-VAC-GEN
Nodes: F1, F2a, F2b.  Gate: G-FORM.  Actor: worker-057.

Measures, deterministically and from the canonical files only:

  A. shared data class: is the (matter, Lambda, equations, constraints,
     s, delta, norm, decay, symmetry) core tuple shared by F1/F2a/F2b?
     (G-FORM unmet item: "no single frozen data class (s,delta,norm) is shared
     by F1/F2a/F2b, which disables the licensed C0=>C2 transfer")
  B. the four hard failures recorded against the PREVIOUS hashes:
     HF-A1 dangling extension_predicate reference,
     HF-A2 forall/quantifier mismatch,
     HF-B1 composite-regularity exemption (F2b),
     HF-B2 node_id mismatch (F2b).
  C. single-class-only and review-binding status at the current hashes.

The script writes report.json next to itself and prints a summary.  It never
mutates a schema, the map, or another agent's artifact.  Exit code 0 means the
check ran; findings are in the report, not in the exit code.

Reproduce:  python3 artifacts/worker-057/xdata_check/check_shared_data_class.py
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]  # repo root (ai4math-swarm)
OUT = Path(__file__).resolve().parent
CST = timezone(timedelta(hours=8))

SCHEMAS = [
    "schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
]

# (node_id, class_id) expected for each canonical file
EXPECTED = {
    "schemas/af_wcc_vacuum.yaml": ("F1", "AF-WCC-VAC-GEN"),
    "schemas/af_scc_c2_vacuum.yaml": ("F2a", "AF-SCC-C2-VAC-GEN"),
    "schemas/af_scc_c0_vacuum.yaml": ("F2b", "AF-SCC-C0-VAC-GEN"),
}

FROZEN_CLASSES = [
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
]

# Core of the shared data class.  `status` / citation bookkeeping fields are
# deliberately excluded: they record verification state, not the class.
CORE_FIELDS = [
    "data_class.matter",
    "data_class.cosmological_constant",
    "data_class.equations",
    "data_class.constraints.hamiltonian",
    "data_class.constraints.momentum",
    "data_class.regularity_class.sobolev_variant.s",
    "data_class.regularity_class.sobolev_variant.delta",
    "data_class.regularity_class.sobolev_variant.spaces",
    "data_class.asymptotic_decay.metric",
    "data_class.asymptotic_decay.second_fundamental_form",
    "data_class.symmetry",
]

# Declaration surfaces where a composite class assertion would bind.
DECLARATION_SURFACES = [
    "class_id",
    "class_components",
    "quantifiers",
    "class_boundary",
    "extension_predicate",
    "topology",
    "data_class",
    "regularity",
    "genericity",
    "conclusion",
    "implication_ledger",
    "falsifier",
    "anti_scope",
]

COMPOSITE_RE = re.compile(
    r"(?:\bC0\s*(?:/|or|and|,)\s*C2\b)"
    r"|(?:\bC2\s*(?:/|or|and|,)\s*C0\b)"
    r"|(?:AF-SCC-[A-Z0-9-]+\s*(?:;|,|\band\b)\s*AF-SCC-[A-Z0-9-]+)"
)
NEGATION_MARKERS = (
    "no ",
    "not ",
    "never",
    "neither",
    "must not",
    "forbidden",
    "do not",
    "does not",
    "distinct",
    "different",
    "separate",
)
# Key paths that are negative by construction: a composite mention here names a
# forbidden pattern, it does not assert a composite class.
NEGATIVE_PATH_MARKERS = (
    "forbidden",
    "anti_scope",
    "not_this_class",
    "phrases_that_are_not",
    "must_not_conflate",
    "schema_falsifiers",
    "weakenings",
)
BRACKETED_HISTORY_RE = re.compile(r"\[[^\]]*\]")
CONTAINMENT_RE = re.compile(
    r"contain|subset|nest|implication runs|entails", re.IGNORECASE
)
QUANT_TOKENS = [
    ("not_exists", re.compile(r"\bnot\s+exists\b", re.IGNORECASE)),
    ("forall", re.compile(r"\bfor\s+all\b|\bforall\b", re.IGNORECASE)),
    ("exists", re.compile(r"\bexists\b|\bthere\s+exists\b", re.IGNORECASE)),
]
# Single non-overlapping alternation: "not exists" must consume as ONE token, not
# also match the inner "exists" (which produced a spurious trailing token).
QUANT_SCAN_RE = re.compile(
    r"\bnot\s+exists\b|\bfor\s+all\b|\bforall\b|\bthere\s+exists\b|\bexists\b",
    re.IGNORECASE,
)


def _token_kind(tok: str) -> str:
    t = re.sub(r"\s+", " ", tok.strip().lower())
    if t.startswith("not"):
        return "not_exists"
    if t.startswith("for"):
        return "forall"
    return "exists"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def get_path(doc, dotted: str):
    """Resolve a dotted path against nested dicts/lists.  Returns (found, value)."""
    cur = doc
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        elif isinstance(cur, list):
            try:
                cur = cur[int(part)]
            except (ValueError, IndexError):
                return False, None
        else:
            return False, None
    return True, cur


def find_line(lines, needle: str) -> list:
    """1-based line numbers containing needle (substring, first 80 chars)."""
    if not isinstance(needle, str) or not needle:
        return []
    key = needle.strip().splitlines()[0].strip()
    if len(key) > 80:
        key = key[:80]
    return [i + 1 for i, ln in enumerate(lines) if key and key in ln]


def value_repr(v) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    return str(v)


def normalize(v) -> str:
    """Whitespace collapse + strip one trailing parenthetical annotation."""
    s = re.sub(r"\s+", " ", value_repr(v)).strip()
    s = re.sub(r"\s*\([^()]*\)\s*$", "", s).strip()
    return s


def walk_strings(node, path=""):
    """Yield (dotted_path, key, value) for every str leaf."""
    if isinstance(node, dict):
        for k, v in node.items():
            yield from walk_strings(v, f"{path}.{k}" if path else str(k))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from walk_strings(v, f"{path}.{i}")
    elif isinstance(node, str):
        yield path, path.split(".")[-1], node


def surface_of(dotted: str) -> str:
    return dotted.split(".")[0]


def walk_scalars(node, path=""):
    """Yield (dotted_path, value) for every scalar leaf (str/bool/int/float/None)."""
    if isinstance(node, dict):
        for k, v in node.items():
            yield from walk_scalars(v, f"{path}.{k}" if path else str(k))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from walk_scalars(v, f"{path}.{i}")
    elif not isinstance(node, (dict, list)):
        yield path, node


def check_a_shared_data_class(docs, lines_by_path, hashes):
    per_file, exact_equal, normalized_equal, annotation_only, material = {}, [], [], [], []
    non_core = {}
    for p in SCHEMAS:
        d = docs[p]
        per_file[p] = {}
        for f in CORE_FIELDS:
            ok, v = get_path(d, f)
            per_file[p][f] = value_repr(v) if ok else "<MISSING>"
        # data_class keys outside the core fields (documented divergences)
        dc = d.get("data_class", {}) or {}
        core_top = {f.split(".")[1] for f in CORE_FIELDS}
        non_core[p] = sorted(k for k in dc.keys() if k not in core_top)

    # Full leaf-level comparison of non-core data_class fields, recorded so the
    # lead sees the complete divergence set even though it does not enter the
    # core-tuple verdict.
    leaves = {p: {} for p in SCHEMAS}
    for p in SCHEMAS:
        for dotted, val in walk_scalars(docs[p].get("data_class", {}), "data_class"):
            leaves[p][dotted] = value_repr(val)
    non_core_comparison = []
    for f in sorted(set().union(*[set(v) for v in leaves.values()])):
        if f in CORE_FIELDS:
            continue
        vals = {p: leaves[p].get(f, "<ABSENT>") for p in SCHEMAS}
        norm = {p: (None if v == "<ABSENT>" else normalize(v)) for p, v in vals.items()}
        present = [v for v in norm.values() if v is not None]
        if len(set(vals.values())) == 1:
            status = "identical"
        elif len(present) > 1 and len(set(present)) == 1:
            status = "normalized_equal"
        elif len(present) <= 1:
            status = "present_in_one_file_only"
        else:
            status = "divergent"
        non_core_comparison.append(
            {"path": f, "status": status, "values": vals}
        )

    for f in CORE_FIELDS:
        vals = {p: per_file[p][f] for p in SCHEMAS}
        if len(set(vals.values())) == 1:
            exact_equal.append(f)
            normalized_equal.append(f)
            continue
        norm = {p: normalize(v) for p, v in vals.items()}
        if len(set(norm.values())) == 1:
            normalized_equal.append(f)
            annotation_only.append(
                {
                    "field": f,
                    "values": vals,
                    "normalization": "whitespace collapse + one trailing parenthetical annotation stripped",
                }
            )
        else:
            material.append({"field": f, "values": vals, "normalized": norm})

    if len(exact_equal) == len(CORE_FIELDS):
        verdict = "shared_core_tuple_exact"
    elif len(normalized_equal) == len(CORE_FIELDS):
        verdict = "shared_core_tuple_modulo_annotations"
    else:
        verdict = "not_shared"

    return {
        "core_fields": CORE_FIELDS,
        "per_file": per_file,
        "measured_sha256": {p: hashes[p] for p in SCHEMAS},
        "exact_equal_fields": exact_equal,
        "normalized_equal_fields": normalized_equal,
        "annotation_only_differences": annotation_only,
        "material_differences": material,
        "non_core_data_class_keys": non_core,
        "non_core_comparison": non_core_comparison,
        "non_core_comparison_note": (
            "Non-core data_class scalars are recorded for completeness and do NOT enter the "
            "core-tuple verdict. status=divergent marks a wording or content difference the "
            "lead may still need to adjudicate as class-neutral or class-changing."
        ),
        "verdict": verdict,
        "verdict_basis": (
            "%d/%d core fields byte-identical, %d/%d equal after annotation "
            "normalization, %d material differences"
            % (
                len(exact_equal),
                len(CORE_FIELDS),
                len(normalized_equal),
                len(CORE_FIELDS),
                len(material),
            )
        ),
        "transfer_license": {
            "required": "one shared frozen data class (s,delta,norm) across F1/F2a/F2b",
            "status": (
                "condition_met_modulo_annotations"
                if verdict == "shared_core_tuple_modulo_annotations"
                else ("condition_met_exactly" if verdict == "shared_core_tuple_exact" else "condition_not_met")
            ),
            "note": (
                "This is a measurement, not a gate verdict. The C0=>C2 transfer also "
                "requires the lead to declare the annotation-only difference "
                "class-identity-neutral (the 'spaces' string differs only by the "
                "suffix '(weighted Sobolev)' in F1)."
            ),
            "material_differences": material,
        },
    }


def check_hf_a1_dangling(docs, lines_by_path):
    checked, dangling = [], []
    for p in SCHEMAS:
        d = docs[p]
        for dotted, key, val in walk_strings(d):
            is_ref = key == "definition_ref" or key.endswith("_ref")
            if not (is_ref and isinstance(val, str)):
                continue
            if val.startswith("http"):
                checked.append({"file": p, "at": dotted, "ref": val, "kind": "external_url"})
                continue
            if "#" in val and "/" in val.split("#", 1)[0]:
                fpart, anchor = val.split("#", 1)
                target = ROOT / fpart
                kind, ok, why = "file_anchor", target.exists(), ""
                if not target.exists():
                    why = "file missing"
                elif anchor and target.suffix in (".yaml", ".yml", ".json"):
                    try:
                        tdoc = yaml.safe_load(target.read_text())
                        found, _ = get_path(tdoc, anchor)
                        ok, why = found, "" if found else "anchor path missing in target"
                    except Exception as exc:  # pragma: no cover
                        ok, why = False, f"target unparsable: {exc}"
                rec = {"file": p, "at": dotted, "ref": val, "kind": kind, "resolved": ok}
                if why:
                    rec["reason"] = why
                (checked if ok else dangling).append(rec)
            elif "/" in val:
                target = ROOT / val
                ok = target.exists()
                rec = {"file": p, "at": dotted, "ref": val, "kind": "file", "resolved": ok}
                if not ok:
                    rec["reason"] = "file missing"
                (checked if ok else dangling).append(rec)
            else:
                found, _ = get_path(d, val)
                rec = {"file": p, "at": dotted, "ref": val, "kind": "internal_path", "resolved": found}
                if not found:
                    rec["reason"] = "dotted path missing in same schema"
                (checked if found else dangling).append(rec)
    evidence = []
    for rec in dangling:
        ln = find_line(lines_by_path[rec["file"]], rec["ref"])
        evidence.append(
            "%s:%s dangling %s ref %r (%s)"
            % (rec["file"], ln[0] if ln else "?", rec["kind"], rec["ref"], rec.get("reason", ""))
        )
    return {
        "probe_id": "HF-A1",
        "name": "dangling internal/reference pointers (was: extension_predicate)",
        "method": (
            "every key named definition_ref or *_ref is classified (external_url | file | "
            "file#anchor | internal dotted path) and resolved against the same schema, the "
            "repo tree, or the anchor target"
        ),
        "result": "fires" if dangling else "clear",
        "checked_count": len(checked),
        "dangling_count": len(dangling),
        "dangling": dangling,
        "evidence": evidence,
    }


def statement_quantifier_sequence(text: str):
    text = "" if text is None else str(text)
    return [_token_kind(m.group(0)) for m in QUANT_SCAN_RE.finditer(text)]


def check_hf_a2_quantifier_order(docs, lines_by_path):
    per_file, any_mismatch, any_abbreviation = {}, False, False
    for p in SCHEMAS:
        d = docs[p]
        ordered = [q.get("kind") for q in d.get("quantifiers", {}).get("ordered", [])]
        sf = d.get("conclusion", {}).get("statement_formal", "")
        seq = statement_quantifier_sequence(sf)
        if ordered == seq:
            verdict = "match"
        elif _is_subsequence(ordered, seq) or _is_subsequence(seq, ordered):
            verdict = "abbreviation_observed"
        else:
            verdict = "mismatch"
        if verdict == "mismatch":
            any_mismatch = True
        if verdict == "abbreviation_observed":
            any_abbreviation = True
        binders = {}
        for q in d.get("quantifiers", {}).get("ordered", []):
            b = str(q.get("binder", ""))
            binders[b] = b in sf if b else None
        per_file[p] = {
            "ordered_kinds": ordered,
            "statement_kinds": seq,
            "statement_formal": sf,
            "verdict": verdict,
            "binder_tokens_present_in_statement": binders,
            "evidence": [
                "%s:%s quantifiers.ordered" % (p, _first_line(lines_by_path[p], "ordered:")),
                "%s:%s conclusion.statement_formal"
                % (p, _first_line(lines_by_path[p], "statement_formal:")),
            ],
        }
    return {
        "probe_id": "HF-A2",
        "name": "quantifier-order match between quantifiers.ordered and conclusion.statement_formal",
        "method": (
            "quantifier kinds (forall | exists | not_exists) scanned left-to-right in "
            "statement_formal are compared with quantifiers.ordered; 'abbreviation_observed' "
            "means one list is a strict subsequence of the other (a quantifier is folded into "
            "an atomic predicate) and is reported for lead adjudication under the gate "
            "criterion 'exact quantifiers', NOT counted as a hard failure; 'mismatch' means "
            "neither list is a subsequence of the other"
        ),
        "result": (
            "fires"
            if any_mismatch
            else ("abbreviation_observed" if any(v["verdict"] == "abbreviation_observed" for v in per_file.values()) else "clear")
        ),
        "per_file": per_file,
    }


def _is_subsequence(small, big):
    it = iter(big)
    return all(x in it for x in small)


def _first_line(lines, needle, default=1):
    ln = find_line(lines, needle)
    return ln[0] if ln else default


def check_hf_b1_composite(docs, lines_by_path):
    mentions, assertional = [], []
    for p in SCHEMAS:
        d = docs[p]
        for dotted, key, val in walk_strings(d):
            if surface_of(dotted) not in DECLARATION_SURFACES:
                continue
            for m in COMPOSITE_RE.finditer(val):
                start = max(0, m.start() - 90)
                ctx = val[start : m.end() + 90].replace("\n", " ")
                negative_path = any(mk in dotted for mk in NEGATIVE_PATH_MARKERS)
                negated = negative_path or any(mk in val.lower() for mk in NEGATION_MARKERS)
                rec = {
                    "file": p,
                    "at": dotted,
                    "match": m.group(0),
                    "context": ctx,
                    "classified": (
                        "negated_or_metalinguistic_mention"
                        if negated
                        else "assertional_mention"
                    ),
                    "context_reason": (
                        "key path is negative by construction (%s)"
                        % next(mk for mk in NEGATIVE_PATH_MARKERS if mk in dotted)
                        if negative_path
                        else ("negation marker in the same scalar" if negated else "positive declaration path")
                    ),
                }
                ln = find_line(lines_by_path[p], m.group(0))
                rec["line"] = ln[0] if ln else None
                mentions.append(rec)
                if not negated:
                    assertional.append(rec)
    return {
        "probe_id": "HF-B1",
        "name": "composite C0/C2 class mention in a declaration surface (was: composite-regularity exemption)",
        "method": (
            "regex scan of declaration surfaces for 'C0 or/and/,/ C2', 'C2 or/and/,/ C0', and "
            "adjacent AF-SCC-* class tokens; each hit is classified by negation markers in the "
            "same scalar.  A negated mention is NOT treated as a composite assertion "
            "(audit_evidence.py CF-16 false positive is the standing warning)"
        ),
        "result": "fires" if assertional else "clear",
        "mention_count": len(mentions),
        "assertional_count": len(assertional),
        "mentions": mentions,
        "evidence": [
            "%s:%s assertional: %r" % (r["file"], r["line"], r["match"]) for r in assertional
        ],
    }


def check_hf_b1b_containment_contradiction(docs, lines_by_path):
    findings = []
    for p in SCHEMAS:
        d = docs[p]
        ledger = d.get("implication_ledger", {}) or {}
        containment = ledger.get("extension_class_containment")
        if not isinstance(containment, str) or not CONTAINMENT_RE.search(containment):
            continue
        # bullets that deny containment between the same axis tokens
        for dotted, key, val in walk_strings(d):
            if "must_not_conflate" not in dotted and "forbidden" not in dotted:
                continue
            # Bracketed text is historical annotation (e.g. "[R2 major: the earlier
            # 'no containment with C2 is asserted' was wrong]") and must not be read
            # as a live denial.
            low = BRACKETED_HISTORY_RE.sub(" ", val).lower()
            denies = (
                ("c2" in low and "c0" in low)
                or ("h2_loc" in low or "h2loc" in low)
            ) and (
                "no containment" in low
                or "not comparable" in low
                or "incomparable" in low
                or "no implication" in low
                or "does not assert" in low
            )
            if denies:
                ln_c = find_line(lines_by_path[p], containment)
                ln_v = find_line(lines_by_path[p], val)
                findings.append(
                    {
                        "file": p,
                        "at": dotted,
                        "denial_text": val,
                        "ledger_text": containment,
                        "denial_line": ln_v[0] if ln_v else None,
                        "ledger_line": ln_c[0] if ln_c else None,
                        "classification": "contradiction_candidate",
                    }
                )
    evidence = [
        "%s:%s denies ('%s') while %s:%s asserts ('%s')"
        % (
            f["file"],
            f["denial_line"],
            f["denial_text"][:110],
            f["file"],
            f["ledger_line"],
            f["ledger_text"][:110],
        )
        for f in findings
    ]
    return {
        "probe_id": "HF-B1b",
        "name": "regularity bullet denying containment vs implication_ledger asserting it",
        "method": (
            "within one schema: if implication_ledger.extension_class_containment asserts a "
            "C2/C0/H2_loc nesting, any must_not_conflate/forbidden bullet that denies "
            "containment or comparability on the same tokens is reported as a "
            "contradiction_candidate with both line numbers"
        ),
        "result": "fires" if findings else "clear",
        "count": len(findings),
        "findings": findings,
        "evidence": evidence,
    }


def check_hf_b2_binding(docs):
    per_file = {}
    fires = []
    for p in SCHEMAS:
        d = docs[p]
        exp_node, exp_class = EXPECTED[p]
        got_node, got_class = d.get("node_id"), d.get("class_id")
        checks = {
            "node_id_matches_filename": got_node == exp_node,
            "class_id_matches_filename": got_class == exp_class,
            "class_id_is_frozen_single_token": isinstance(got_class, str)
            and got_class in FROZEN_CLASSES
            and ";" not in got_class,
        }
        if not all(checks.values()):
            fires.append(p)
        per_file[p] = {
            "expected_node": exp_node,
            "measured_node": got_node,
            "expected_class": exp_class,
            "measured_class": got_class,
            "checks": checks,
        }
    return {
        "probe_id": "HF-B2",
        "name": "node_id / class_id / filename binding (was: F2b node_id mismatch)",
        "method": "exact equality of node_id and class_id against the canonical filename mapping",
        "result": "fires" if fires else "clear",
        "per_file": per_file,
        "evidence": ["%s: node_id=%r class_id=%r" % (p, per_file[p]["measured_node"], per_file[p]["measured_class"]) for p in SCHEMAS],
    }


def check_single_class(docs):
    per_file, fires = {}, []
    for p in SCHEMAS:
        d = docs[p]
        cid = d.get("class_id")
        cb = d.get("class_boundary") or {}
        comps = d.get("class_components") or {}
        reg = str(comps.get("regularity_token", "none"))
        rebuilt = "AF-%s-VAC-GEN" % str(comps.get("censorship", ""))
        if reg != "none":
            rebuilt = "AF-%s-%s-VAC-GEN" % (str(comps.get("censorship", "")), reg)
        checks = {
            "class_id_single_token": isinstance(cid, str) and ";" not in cid,
            "class_id_frozen": cid in FROZEN_CLASSES,
            "one_class_only_equals_class_id": (cb.get("one_class_only") in (None, cid)),
            "merge_forbidden_true_if_present": (cb.get("merge_forbidden") in (None, True)),
            "components_reconstruct_class_id": rebuilt == cid,
        }
        if not all(checks.values()):
            fires.append(p)
        per_file[p] = {"class_id": cid, "checks": checks, "class_components": comps}
    return {
        "probe_id": "SINGLE-CLASS-ONLY",
        "name": "one class per schema; no composite C0/C2 declaration",
        "method": "single frozen class token, class_boundary.one_class_only == class_id, merge_forbidden true, components reconstruct the token",
        "result": "fires" if fires else "clear",
        "per_file": per_file,
    }


def check_review_binding(docs, hashes):
    per_file = {}
    for p in SCHEMAS:
        d = docs[p]
        rs = d.get("review_status") or {}
        per_file[p] = {
            "measured_sha256": hashes[p],
            "verdict": rs.get("verdict"),
            "independent_reviewers": rs.get("independent_reviewers") or [],
            "requested_reviewers": rs.get("requested_reviewers") or [],
            "gate": rs.get("gate"),
        }
    return {
        "probe_id": "REVIEW-BINDING",
        "name": "review verdict availability at the measured canonical hashes",
        "method": "read review_status from each schema; an accept binds only at the measured sha256",
        "result": "informational",
        "per_file": per_file,
        "note": (
            "A gate needs independent accept verdicts that cite the measured hashes; the "
            "schema-embedded review_status is the author's record, not a reviewer verdict."
        ),
    }


def main():
    docs, lines_by_path, hashes, bytes_by_path, target_meta = {}, {}, {}, {}, {}
    for p in SCHEMAS:
        path = ROOT / p
        raw = path.read_text()
        docs[p] = yaml.safe_load(raw)
        lines_by_path[p] = raw.splitlines()
        hashes[p] = sha256_file(path)
        bytes_by_path[p] = len(raw.encode())
        target_meta[p] = {
            "sha256": hashes[p],
            "bytes": bytes_by_path[p],
            "revision": docs[p].get("revision"),
            "revised_at": docs[p].get("revised_at"),
            "filesystem_mtime": datetime.fromtimestamp(path.stat().st_mtime, CST).isoformat(
                timespec="seconds"
            ),
        }

    probes = [
        check_hf_a1_dangling(docs, lines_by_path),
        check_hf_a2_quantifier_order(docs, lines_by_path),
        check_hf_b1_composite(docs, lines_by_path),
        check_hf_b1b_containment_contradiction(docs, lines_by_path),
        check_hf_b2_binding(docs),
        check_single_class(docs),
        check_review_binding(docs, hashes),
    ]
    fires = [pr["probe_id"] for pr in probes if pr["result"] == "fires"]

    measurements = {
        "shared_data_class": check_a_shared_data_class(docs, lines_by_path, hashes),
        "hard_failure_probes": probes,
        "summary": {
            "probes_run": len(probes),
            "probes_firing": fires,
            "shared_data_class_verdict": None,  # filled below
            "inputs": target_meta,
        },
    }
    measurements["summary"]["shared_data_class_verdict"] = measurements["shared_data_class"]["verdict"]
    measurements_sha = hashlib.sha256(
        json.dumps(measurements, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()

    report = {
        "report_version": "1.0",
        "task": {
            "task_id": "GFORM-XDATA-057",
            "actor": "worker-057",
            "node_ids": ["F1", "F2a", "F2b"],
            "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
            "gate": "G-FORM",
            "objective": (
                "At the current canonical hashes, measure (A) whether F1/F2a/F2b share one "
                "frozen data class core tuple, and (B) whether the four hard failures recorded "
                "against the previous hashes (HF-A1 dangling extension_predicate, HF-A2 forall "
                "mismatch, HF-B1 composite-regularity exemption, HF-B2 node_id mismatch) persist."
            ),
            "scope_limit": (
                "Structural machine-check only. No truth value is assigned to any schema; no "
                "gate verdict is set; annotation-only vs material differences are reported, and "
                "the shared-class judgment needed by G-FORM remains a lead adjudication."
            ),
        },
        "created_at": datetime.now(CST).isoformat(timespec="seconds"),
        "created_at_basis": "wall clock at write time (CF-14 clock discipline)",
        "repo_root": ".",
        "inputs": {p: {"sha256": hashes[p], "bytes": bytes_by_path[p]} for p in SCHEMAS},
        "target_revision": target_meta,
        "moving_target_note": (
            "The canonical schemas were revised on disk at 00:19:14 during this check (an "
            "earlier measurement bound 68392dd8/4f97273e/a2aef5ac; this report binds only to "
            "the hashes in target_revision). Any later revision falsifies this report for the "
            "recorded hashes and requires a re-run."
        ),
        "measurements": measurements,
        "measurements_sha256": measurements_sha,
        "reproduce": "python3 artifacts/worker-057/xdata_check/check_shared_data_class.py",
        "falsifier": (
            "Re-hash the three canonical files and re-run this script: if any measured sha256 "
            "differs from the recorded inputs, or if any probe result or shared-class verdict "
            "changes, this report is falsified for the recorded hashes.  For the HF-B1b finding "
            "specifically: falsified if schemas/af_scc_c0_vacuum.yaml#%s no longer contains the "
            "'No containment with C2 or C0 is asserted here' denial while its "
            "implication_ledger still asserts the E_C0 contains E_H2loc contains E_C2 nesting."
            % hashes["schemas/af_scc_c0_vacuum.yaml"][:12]
        ),
    }

    out_json = OUT / "report.json"
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + "\n")
    report_sha = sha256_file(out_json)

    # ---- human summary -------------------------------------------------
    sc = measurements["shared_data_class"]
    md = []
    md.append("# GFORM-XDATA-057 — cross-schema check (worker-057)\n")
    md.append("Gate: **G-FORM** · nodes F1/F2a/F2b · classes AF-WCC-VAC-GEN / AF-SCC-C2-VAC-GEN / AF-SCC-C0-VAC-GEN\n")
    md.append("Measured inputs (canonical paths):\n")
    for p in SCHEMAS:
        md.append(
            "- `%s#%s` (rev %s, %d bytes, mtime %s)"
            % (
                p,
                hashes[p][:12],
                target_meta[p].get("revision"),
                bytes_by_path[p],
                target_meta[p].get("filesystem_mtime"),
            )
        )
    md.append("")
    md.append("## A. Shared data class\n")
    md.append("- verdict: **%s** (%s)" % (sc["verdict"], sc["verdict_basis"]))
    for d in sc["annotation_only_differences"]:
        md.append("  - annotation-only: `%s`" % d["field"])
    for d in sc["material_differences"]:
        md.append("  - MATERIAL: `%s`" % d["field"])
    md.append("- transfer-license condition: **%s**" % sc["transfer_license"]["status"])
    md.append("")
    md.append("## B. Hard-failure probes at these hashes\n")
    for pr in probes:
        md.append("- **%s** (%s): `%s`" % (pr["probe_id"], pr["name"], pr["result"]))
        for ev in pr.get("evidence", [])[:6]:
            md.append("    - %s" % ev)
    md.append("")
    md.append("## C. Review binding\n")
    for p, r in probes[-1]["per_file"].items():
        md.append("- `%s#%s`: verdict=%s, independent_reviewers=%d, gate=%s"
                  % (p, r["measured_sha256"][:12], r["verdict"], len(r["independent_reviewers"]), r["gate"]))
    md.append("")
    md.append("## Falsifier\n")
    md.append(report["falsifier"])
    md.append("")
    (OUT / "REPORT.md").write_text("\n".join(md) + "\n")
    report_md_sha = sha256_file(OUT / "REPORT.md")

    print("measurements_sha256 =", measurements_sha)
    print("report.json        sha256 =", report_sha)
    print("REPORT.md          sha256 =", report_md_sha)
    print("shared_data_class  =", sc["verdict"], "| fires:", fires or "none")
    return 0


if __name__ == "__main__":
    sys.exit(main())
